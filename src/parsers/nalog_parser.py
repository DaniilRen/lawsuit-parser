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

            await self._extract_company_name(company_info)
            await self._extract_status(company_info)
            await self._parse_other_info_panel(company_info)
            await self._extract_all_company_fields(company_info)

            if len(company_info) < 5:
                await self._extract_general(company_info)

            if company_info:
                company_info['parsed_at'] = datetime.now().isoformat()
                company_info['url'] = self.page.url
        except:
            pass
        return company_info

    async def _extract_company_name(self, company_info):
        try:
            name_selectors = [
                '.pb-company-name',
                '.company-name',
                'h1.pb-panel__title',
                '.pb-panel__title',
                'h1'
            ]
            for selector in name_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        name = await element.text_content()
                        name = name.strip()
                        if name and len(name) > 2:
                            company_info['Наименование'] = name
                            return
                except:
                    continue
        except:
            pass

    async def _extract_status(self, company_info):
        try:
            status = await self.page.evaluate('''
                () => {
                    const selectors = [
                        '.pb-company-status',
                        '.pb-company-status__text',
                        '.pb-otch-status',
                        '.pb-company-card__status',
                        '[class*="company-status"]',
                        '[class*="companyStatus"]'
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const text = (el.textContent || '').trim();
                            if (text && text.length < 200) return text;
                        }
                    }
                    return null;
                }
            ''')
            if status:
                company_info['Статус'] = status
        except:
            pass

    async def _parse_other_info_panel(self, company_info):
        try:
            await self.page.wait_for_selector('#pnlCompanyOtherInfo', timeout=5000)
        except:
            return

        await self.page.wait_for_timeout(2000)

        try:
            items = await self.page.query_selector_all(
                '#pnlCompanyOtherInfo > .pb-company-multicolumn-item'
            )
            for item in items:
                try:
                    await self._parse_other_info_item(item, company_info)
                except:
                    continue
        except:
            pass

    async def _parse_other_info_item(self, item, company_info):
        try:
            item_id = await item.get_attribute('id') or ''

            header = None
            header_el = await item.query_selector('.pb-company-block-header span')
            if not header_el:
                header_el = await item.query_selector('.pb-company-block-header')
            if header_el:
                header = (await header_el.text_content() or '').strip()
            if not header:
                header = item_id
            if not header:
                return

            fields = {}
            data_rows = {}

            field_containers = await item.query_selector_all('.pb-company-field')
            for field in field_containers:
                try:
                    name_el = await field.query_selector('.pb-company-field-name')
                    value_el = await field.query_selector('.pb-company-field-value')

                    if name_el and value_el:
                        name = (await name_el.text_content() or '').strip().rstrip(':')
                        value = (await value_el.text_content() or '').strip()
                        value = self._clean_value(value)
                        if name and value:
                            if name in fields:
                                if not isinstance(fields[name], list):
                                    fields[name] = [fields[name]]
                                fields[name].append(value)
                            else:
                                fields[name] = value
                    elif value_el:
                        value = (await value_el.text_content() or '').strip()
                        value = self._clean_value(value)
                        if value:
                            if 'main' not in fields:
                                fields['main'] = value
                            else:
                                idx = 1
                                while f'extra_{idx}' in fields:
                                    idx += 1
                                fields[f'extra_{idx}'] = value
                except:
                    continue

            if not fields:
                try:
                    captured = await item.evaluate('''
                        (el) => {
                            const out = { meta: null, values: [], statusText: null };

                            const headerEl = el.querySelector('.pb-company-block-header span');
                            const headerText = headerEl ? headerEl.textContent.trim() : null;

                            const metaEl = el.querySelector('.pb-company-block__row .text-secondary');
                            if (metaEl) out.meta = metaEl.textContent.trim();

                            const rows = el.querySelectorAll('.pb-company-block__row');
                            rows.forEach(row => {
                                const rowClone = row.cloneNode(true);

                                const m = rowClone.querySelector('.text-secondary');
                                if (m) m.remove();

                                const h = rowClone.querySelector('.pb-company-block-header');
                                if (h) h.remove();

                                const imgs = rowClone.querySelectorAll('img, svg, a.print-none, [class*="print-none"]');
                                imgs.forEach(x => x.remove());

                                const txt = (rowClone.textContent || '').trim().replace(/\\s+/g, ' ');
                                if (txt && txt.length > 0 && txt !== headerText) {
                                    out.values.push(txt);
                                }
                            });

                            const statusEl = el.querySelector('.pb-otch-status, [class*="otch-status"], [class*="company-status"]');
                            if (statusEl) out.statusText = statusEl.textContent.trim();

                            return out;
                        }
                    ''')

                    if captured.get('meta'):
                        fields['_meta'] = self._clean_value(captured['meta'])

                    for v in captured.get('values', []):
                        v = self._clean_value(v)
                        if v and v not in fields.values():
                            key = 'note' if 'note' not in fields else f'note_{len(fields)}'
                            fields[key] = v

                    if captured.get('statusText'):
                        fields['status'] = self._clean_value(captured['statusText'])
                except:
                    pass

            if fields or item_id:
                company_info[f'__panel__{header}'] = {
                    'id': item_id,
                    'fields': fields,
                    'empty': not fields,
                }
        except:
            pass
        
    async def _extract_all_company_fields(self, company_info):
        try:
            fields = await self.page.evaluate('''
                () => {
                    const skip = document.querySelector('#pnlCompanyOtherInfo');
                    const result = [];
                    document.querySelectorAll('.pb-company-field').forEach(f => {
                        if (skip && skip.contains(f)) return;
                        const nameEl = f.querySelector('.pb-company-field-name');
                        const valueEl = f.querySelector('.pb-company-field-value');
                        if (valueEl) {
                            result.push({
                                name: nameEl ? nameEl.textContent.trim() : null,
                                value: valueEl.textContent.trim()
                            });
                        }
                    });
                    return result;
                }
            ''')

            for field in fields:
                name = field.get('name')
                value = field.get('value')
                if not value:
                    continue

                value = self._clean_value(value)

                if name:
                    name = name.rstrip(':').strip()
                    if name in company_info:
                        existing = company_info[name]
                        if not isinstance(existing, list):
                            company_info[name] = [existing]
                        company_info[name].append(value)
                    else:
                        company_info[name] = value
        except:
            pass

    def _clean_value(self, value: str) -> str:
        if not value:
            return ''
        value = re.sub(r'[ \t]+', ' ', value)
        value = re.sub(r'\s*\n\s*', ' ', value)
        value = re.sub(r'\s{2,}', ' ', value)
        return value.strip()

    async def _extract_general(self, company_info):
        try:
            html = await self.page.content()
            patterns = {
                'Полное наименование': r'Полное наименование[:\s]+([^<]+?)(?:\n|$)',
                'Сокращенное наименование': r'Сокращенное наименование[:\s]+([^<]+?)(?:\n|$)',
                'ОГРН': r'ОГРН[:\s]+(\d{13,15})',
                'Дата регистрации': r'Дата регистрации[:\s]+(\d{2}\.\d{2}\.\d{4})',
                'Способ образования': r'Способ образования[:\s]+([^<]+?)(?:\n|$)',
                'КПП': r'КПП[:\s]+(\d{9})',
                'Адрес организации': r'Адрес организации[:\s]+([^<]+?)(?:\n|$)',
                'Наименование налогового органа': r'Наименование налогового органа[:\s]+([^<]+?)(?:\n|$)',
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

    def _pick(self, raw_data: Dict[str, Any], *keys):
        for k in keys:
            v = raw_data.get(k)
            if v:
                if isinstance(v, list):
                    return v
                return v
        return ''

    def _normalize_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        inn = raw_data.get('inn', '')

        normalized = {
            'inn': inn,
            'company_name': self._pick(raw_data, 'Наименование', 'Полное наименование'),
            'full_name': self._pick(raw_data, 'Полное наименование'),
            'short_name': self._pick(raw_data, 'Сокращенное наименование'),
            'ogrn': self._pick(raw_data, 'ОГРН'),
            'registration_date': self._pick(raw_data, 'Дата регистрации'),
            'legal_address': self._pick(
                raw_data,
                'Адрес организации',
                'Адрес',
                'Адрес (место нахождения)',
                'Адрес места нахождения',
                'Адрес места нахождения организации',
            ),
            'status': self._pick(raw_data, 'Статус'),
            'kpp': self._pick(raw_data, 'КПП'),
            'main_activity': self._pick(
                raw_data,
                'Основной вид деятельности',
                'Основной вид деятельности (ОКВЭД заявительный)',
                'Виды деятельности',
                'Основной ОКВЭД',
            ),
            'additional_activities': self._pick(
                raw_data,
                'Дополнительный вид деятельности',
                'Дополнительные виды деятельности',
            ),
            'tax_office': self._pick(
                raw_data,
                'Наименование налогового органа',
                'Наименование налогового органа, осуществившего постановку на учёт',
            ),
            'registration_tax_office': self._pick(
                raw_data,
                'Наименование налогового органа, осуществляющего регистрацию по месту нахождения организации',
            ),
            'registration_date_tax': self._pick(
                raw_data,
                'Дата постановки на учёт',
                'Дата постановки на учет',
            ),
            'authorized_capital': self._pick(
                raw_data,
                'Уставный капитал',
                'Сведения об уставном капитале (складочном капитале, уставном фонде, паевых взносах)',
            ),
            'msp_status': self._pick(raw_data, 'Сведения о субъекте МСП'),
            'publication_info': self._pick(
                raw_data,
                'Сведения о публикации',
                'Сведения о публикации сообщений в журнале «Вестник государственной регистрации»',
            ),
            'formation_method': self._pick(raw_data, 'Способ образования'),
            'data_entry_date': self._pick(
                raw_data,
                'Дата внесения сведений',
                'Дата внесения сведений в Единый реестр субъектов малого и среднего предпринимательства',
            ),
            'other_info': self._extract_other_info(raw_data),
            'raw_data': raw_data,
        }
        return normalized

    def _extract_other_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        other_info = {}
        known_keys = {
            'inn', 'Наименование', 'Полное наименование', 'Сокращенное наименование',
            'ОГРН', 'Дата регистрации', 'Адрес организации', 'Статус', 'КПП',
            'Основной вид деятельности', 'Дополнительный вид деятельности',
            'Наименование налогового органа', 'Уставный капитал',
            'Сведения о субъекте МСП', 'Сведения о публикации', 'Способ образования',
            'Дата внесения сведений', 'parsed_at', 'url'
        }

        for key, value in raw_data.items():
            if key.startswith('__panel__'):
                header = key[len('__panel__'):]
                other_info[header] = value
            elif key in known_keys:
                continue
            else:
                if '_ungrouped' not in other_info:
                    other_info['_ungrouped'] = {}
                other_info['_ungrouped'][key] = value

        return other_info

    def get_data_schema(self) -> Dict[str, Any]:
        return {
            'inn': {'type': 'string', 'required': True},
            'company_name': {'type': 'string', 'required': True},
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
            'registration_tax_office': {'type': 'string', 'required': False},
            'registration_date_tax': {'type': 'string', 'required': False},
            'authorized_capital': {'type': 'string', 'required': False},
            'msp_status': {'type': 'string', 'required': False},
            'publication_info': {'type': 'string', 'required': False},
            'formation_method': {'type': 'string', 'required': False},
            'data_entry_date': {'type': 'string', 'required': False},
            'other_info': {'type': 'object', 'required': False},
            'raw_data': {'type': 'object', 'required': False}
        }