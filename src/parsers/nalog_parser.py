from typing import Dict, Any
import re
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

from src.parsers.base_parser import BaseParser


class NalogParser(BaseParser):
    def __init__(self, source_name: str, config: Dict[str, Any]):
        super().__init__(source_name, config)
        self.browser = None
        self.page = None
        self.playwright = None

    async def _setup_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        self.page = await self.browser.new_page(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

    async def _wait_for_results(self) -> bool:
        try:
            selectors = [
                '.pnl-search-result-group',
                '.pb-panel',
                '#resultul',
                '.company-name',
                '.result-item',
                '[data-group="ul"]',
                '.search-result-item',
                '.org-item'
            ]
            for selector in selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    return True
                except:
                    continue
            body = await self.page.text_content('body')
            if 'По заданным критериям поиска сведений не найдено' in body:
                return False
            if 'Организации' in body and 'ИНН' in body:
                return True
            return False
        except:
            return False

    async def _find_company_token(self):
        try:
            token = await self.page.evaluate('''
                () => {
                    const elements = document.querySelectorAll('[onclick]');
                    for (let el of elements) {
                        const onclick = el.getAttribute('onclick') || '';
                        const match = onclick.match(/company\\.html\\?token=([A-F0-9]+)/);
                        if (match) return match[1];
                    }
                    const links = document.querySelectorAll('a[href*="company"]');
                    for (let link of links) {
                        const href = link.getAttribute('href') || '';
                        const match = href.match(/token=([A-F0-9]+)/);
                        if (match) return match[1];
                    }
                    const scripts = document.querySelectorAll('script');
                    for (let script of scripts) {
                        const content = script.textContent || '';
                        const match = content.match(/token["']?\\s*[:=]\\s*["']?([A-F0-9]+)["']?/);
                        if (match) return match[1];
                    }
                    return null;
                }
            ''')
            return token
        except:
            return None

    async def _parse_company_page(self):
        company_info = {}
        try:
            await self.page.wait_for_timeout(3000)
            await self._extract_with_specific_classes(company_info)
            if len(company_info) < 5:
                await self._extract_general(company_info)
            if company_info:
                company_info['parsed_at'] = datetime.now().isoformat()
                company_info['url'] = self.page.url
        except:
            pass
        return company_info

    async def _extract_with_specific_classes(self, company_info):
        try:
            rows = await self.page.query_selector_all('.pb-company-block__row.pb-company-multicolumn-item')
            for row in rows:
                try:
                    row_text = await row.text_content()
                    row_text = row_text.strip()
                    if not row_text:
                        continue
                    label_element = await row.query_selector('.pb-company-block__row-label, .pb-company-block__label, [class*="label"]')
                    if label_element:
                        label = await label_element.text_content()
                        label = label.strip().rstrip(':')
                        value_element = await row.query_selector('.pb-company-block__row-value, .pb-company-block__value, [class*="value"]')
                        if value_element:
                            value = await value_element.text_content()
                            value = value.strip()
                        else:
                            value = row_text.replace(label, '').strip()
                            if value.startswith(':'):
                                value = value[1:].strip()
                        if label and value:
                            company_info[label] = value
                    else:
                        if ':' in row_text:
                            parts = row_text.split(':', 1)
                            if len(parts) == 2:
                                label = parts[0].strip()
                                value = parts[1].strip()
                                if label and value:
                                    company_info[label] = value
                except:
                    continue
            if not company_info:
                rows = await self.page.query_selector_all('.pb-company-block__row')
                for row in rows:
                    try:
                        row_text = await row.text_content()
                        row_text = row_text.strip()
                        if not row_text:
                            continue
                        if ':' in row_text:
                            parts = row_text.split(':', 1)
                            if len(parts) == 2:
                                label = parts[0].strip()
                                value = parts[1].strip()
                                if label and value:
                                    company_info[label] = value
                    except:
                        continue
        except:
            pass

    async def _extract_general(self, company_info):
        try:
            html = await self.page.content()
            patterns = {
                'Полное наименование': r'Полное наименование[:\s]+([^<]+?)(?:\n|$)',
                'Сокращенное наименование': r'Сокращенное наименование[:\s]+([^<]+?)(?:\n|$)',
                'ОГРН': r'ОГРН[:\s]+(\d{13,15})',
                'Дата регистрации': r'Дата регистрации[:\s]+(\d{2}\.\d{2}\.\d{4})',
                'Способ образования': r'Способ образования[:\s]+([^<]+?)(?:\n|$)',
                'ИНН': r'ИНН[:\s]+(\d{10,12})',
                'КПП': r'КПП[:\s]+(\d{9})',
                'Основной вид деятельности': r'Основной вид деятельности[:\s]+([^<]+?)(?:\n|$)',
                'Дополнительный вид деятельности': r'Дополнительный вид деятельности[:\s]+([^<]+?)(?:\n|$)',
                'Адрес организации': r'Адрес организации[:\s]+([^<]+?)(?:\n|$)',
                'Наименование налогового органа': r'Наименование налогового органа[:\s]+([^<]+?)(?:\n|$)',
                'Сведения о публикации': r'Сведения о публикации[:\s]+([^<]+?)(?:\n|$)',
                'Уставный капитал': r'Уставный капитал[:\s]+([^<]+?)(?:\n|$)',
                'Сведения о субъекте МСП': r'Сведения о субъекте МСП[:\s]+([^<]+?)(?:\n|$)',
                'Дата внесения сведений': r'Дата внесения сведений[:\s]+(\d{2}\.\d{2}\.\d{4})'
            }
            for key, pattern in patterns.items():
                if key not in company_info:
                    match = re.search(pattern, html, re.DOTALL)
                    if match:
                        value = match.group(1).strip()
                        if value:
                            company_info[key] = value
        except:
            pass

    async def _get_company_info_async(self, inn: str):
        if not re.match(r'^\d{10,12}$', inn):
            raise ValueError(f"Invalid INN format: {inn}")

        await self._setup_browser()
        search_url = f"https://pb.nalog.ru/search.html#t=1786543421887&mode=search-all&queryAll={inn}&page=1&pageSize=10"
        
        for attempt in range(self.retry_count):
            try:
                await self.page.goto(search_url, wait_until='domcontentloaded', timeout=15000)
                await self.page.wait_for_timeout(3000)
                
                if not await self._wait_for_results():
                    body = await self.page.text_content('body')
                    if 'По заданным критериям поиска сведений не найдено' in body:
                        raise Exception(f"No results found for INN: {inn}")
                    continue
                
                token = await self._find_company_token()
                if token:
                    company_url = f"https://pb.nalog.ru/company.html?token={token}"
                    try:
                        await self.page.goto(company_url, wait_until='domcontentloaded', timeout=15000)
                        await self.page.wait_for_timeout(3000)
                        company_info = await self._parse_company_page()
                        if company_info and len(company_info) > 1:
                            company_info['inn'] = inn
                            await self._close()
                            return company_info
                    except:
                        pass
                
                if attempt < self.retry_count - 1:
                    await self.page.wait_for_timeout((2 ** attempt) * 1000)
                    
            except Exception as e:
                if attempt < self.retry_count - 1:
                    await self.page.wait_for_timeout((2 ** attempt) * 1000)
                else:
                    await self._close()
                    raise
        
        await self._close()
        raise Exception(f"All retry attempts failed for INN: {inn}")

    async def _close(self):
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass

    def parse(self, inn: str) -> Dict[str, Any]:
        try:
            result = asyncio.run(self._get_company_info_async(inn))
            normalized_data = self._normalize_data(result)
            return normalized_data
            
        except Exception as e:
            raise Exception(f"Failed to parse INN {inn}: {str(e)}")
        finally:
            try:
                asyncio.run(self._close())
            except:
                pass

    def _normalize_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {
            'inn': raw_data.get('inn', ''),
            'full_name': raw_data.get('Полное наименование', ''),
            'short_name': raw_data.get('Сокращенное наименование', ''),
            'ogrn': raw_data.get('ОГРН', ''),
            'registration_date': raw_data.get('Дата регистрации', ''),
            'legal_address': raw_data.get('Адрес организации', ''),
            'status': raw_data.get('Статус', ''),
            'kpp': raw_data.get('КПП', ''),
            'main_activity': raw_data.get('Основной вид деятельности', ''),
            'additional_activities': raw_data.get('Дополнительный вид деятельности', ''),
            'tax_office': raw_data.get('Наименование налогового органа', ''),
            'authorized_capital': raw_data.get('Уставный капитал', ''),
            'msp_status': raw_data.get('Сведения о субъекте МСП', ''),
            'publication_info': raw_data.get('Сведения о публикации', ''),
            'formation_method': raw_data.get('Способ образования', ''),
            'data_entry_date': raw_data.get('Дата внесения сведений', ''),
            'raw_data': raw_data
        }
        return normalized

    def get_data_schema(self) -> Dict[str, Any]:
        return {
            'inn': {'type': 'string', 'required': True},
            'full_name': {'type': 'string', 'required': False},
            'short_name': {'type': 'string', 'required': False},
            'ogrn': {'type': 'string', 'required': False},
            'registration_date': {'type': 'string', 'required': False},
            'legal_address': {'type': 'string', 'required': False},
            'status': {'type': 'string', 'required': False},
            'kpp': {'type': 'string', 'required': False},
            'main_activity': {'type': 'string', 'required': False},
            'additional_activities': {'type': 'string', 'required': False},
            'tax_office': {'type': 'string', 'required': False},
            'authorized_capital': {'type': 'string', 'required': False},
            'msp_status': {'type': 'string', 'required': False},
            'publication_info': {'type': 'string', 'required': False},
            'formation_method': {'type': 'string', 'required': False},
            'data_entry_date': {'type': 'string', 'required': False},
            'raw_data': {'type': 'object', 'required': False}
        }