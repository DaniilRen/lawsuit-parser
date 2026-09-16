from typing import Dict, Any, Optional, List
import re
import asyncio
import os
import shutil
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

from src.parsers.base_parser import BaseParser


class FedresursParser(BaseParser):
    WORK_DIR = Path(__file__).parent / "fedresurs_working_dir"
    BASE_URL = "https://fedresurs.ru"
    SEARCH_URL = "https://fedresurs.ru/entities?searchString={inn}"

    def __init__(self, source_name: str, config: Dict[str, Any]):
        super().__init__(source_name, config)
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self._ensure_work_dir()

    def _ensure_work_dir(self):
        self.WORK_DIR.mkdir(parents=True, exist_ok=True)
        gitkeep = self.WORK_DIR / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    def _clean_work_dir(self):
        for item in self.WORK_DIR.iterdir():
            if item.name == ".gitkeep":
                continue
            if item.name == "browser_profile":
                continue
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except:
                pass

    async def _setup_browser(self):
        self.playwright = await async_playwright().start()

        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-features=IsolateOrigins,site-per-process',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-infobars',
            '--window-size=1920,1080',
        ]

        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=launch_args,
            ignore_default_args=['--enable-automation'],
        )

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            extra_http_headers={
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            },
        )

        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en']
            });
            if (!window.chrome) {
                window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
            }
        """)

        self.page = await self.context.new_page()

    async def _close(self):
        try:
            if self.page:
                await self.page.close()
        except:
            pass
        try:
            if self.context:
                await self.context.close()
        except:
            pass
        try:
            if self.browser:
                await self.browser.close()
        except:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except:
            pass

    async def _search_and_get_company_url(self, inn: str) -> Optional[str]:
        search_url = self.SEARCH_URL.format(inn=inn)

        try:
            await self.page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await self.page.wait_for_timeout(8000)
        except Exception as e:
            raise Exception(f"Failed to open search page: {str(e)}")

        try:
            await self.page.wait_for_selector(
                '.u-card-result, .tab-content, app-entity-search-result-card-company',
                timeout=15000
            )
        except:
            return None

        try:
            company_url = await self.page.evaluate("""
                (() => {
                    const links = document.querySelectorAll(
                        '.u-card-result a.underlined, .u-card-result__name a, app-entity-search-result-card-company a.underlined'
                    );
                    for (const a of links) {
                        const href = a.getAttribute('href') || '';
                        if (href.includes('/companies/')) {
                            return href;
                        }
                    }
                    return null;
                })()
            """)
        except:
            company_url = None

        if not company_url:
            return None

        if company_url.startswith('/'):
            company_url = self.BASE_URL + company_url

        return company_url

    async def _extract_result_card(self) -> Dict[str, Any]:
        try:
            card = await self.page.evaluate("""
                (() => {
                    const card = document.querySelector('.u-card-result');
                    if (!card) return null;

                    const nameEl = card.querySelector('.u-card-result__name a, a.underlined');
                    const name = nameEl ? nameEl.textContent.trim() : null;

                    const addrEl = card.querySelector('.u-card-result__value_adr, [class*="value_adr"]');
                    const address = addrEl ? addrEl.textContent.trim() : null;

                    const statusEl = card.querySelector('.item-status');
                    const status = statusEl ? statusEl.textContent.trim() : null;

                    const activityEl = card.querySelector('.u-card-result__value_activity, [class*="value_activity"]');
                    const activity = activityEl ? activityEl.textContent.trim() : null;

                    let inn = null;
                    let ogrn = null;

                    card.querySelectorAll('.u-card-result__item-id').forEach(el => {
                        const label = el.querySelector('.u-card-result__point');
                        const value = el.querySelector('.u-card-result__value');
                        if (!label || !value) return;
                        const labelText = label.textContent.trim();
                        const valueText = value.textContent.trim();
                        if (labelText.includes('ИНН')) inn = valueText;
                        if (labelText.includes('ОГРН')) ogrn = valueText;
                    });

                    return { name, address, status, activity, inn, ogrn };
                })()
            """)
            return card or {}
        except:
            return {}

    async def _extract_detail_items(self) -> List[Dict[str, Any]]:
        try:
            items = await self.page.evaluate("""
                (() => {
                    const out = [];
                    const pageItems = document.querySelectorAll('information-page-item.card-item, information-page-item');

                    pageItems.forEach(item => {
                        const header = item.getAttribute('header') || '';
                        const selector = item.getAttribute('selector') || '';

                        const fields = [];

                        item.querySelectorAll('.ieb-name, [class*="ieb-name"]').forEach(nameEl => {
                            const txt = (nameEl.textContent || '').replace(/\\s+/g, ' ').trim();
                            if (txt) {
                                fields.push({ label: 'ФИО', value: txt });
                            }
                        });

                        if (fields.length === 0) {
                            item.querySelectorAll('.info-header span, .info-header [class*="name"]').forEach(nameEl => {
                                const txt = (nameEl.textContent || '').replace(/\\s+/g, ' ').trim();
                                if (txt && txt.length > 3 && !fields.some(f => f.value === txt)) {
                                    fields.push({ label: 'ФИО', value: txt });
                                }
                            });
                        }

                        item.querySelectorAll('.identifier-name').forEach(labelEl => {
                            const valueEl = labelEl.parentElement.querySelector('.identifier-value');
                            if (valueEl) {
                                fields.push({
                                    label: labelEl.textContent.trim(),
                                    value: valueEl.textContent.trim()
                                });
                            }
                        });

                        item.querySelectorAll('.info-item-name').forEach(labelEl => {
                            const valueEl = labelEl.parentElement.querySelector('.info-item-value');
                            if (!valueEl) return;
                            const secondaryEl = valueEl.querySelector('.secondary-text');
                            let primary = valueEl.cloneNode(true);
                            if (secondaryEl) {
                                const clonedSecondary = primary.querySelector('.secondary-text');
                                if (clonedSecondary) clonedSecondary.remove();
                            }
                            const primaryText = (primary.textContent || '').replace(/\\s+/g, ' ').trim();
                            const secondaryText = secondaryEl ? secondaryEl.textContent.trim() : '';

                            let value = primaryText;
                            if (secondaryText) {
                                value = primaryText ? `${primaryText} (${secondaryText})` : secondaryText;
                            }

                            fields.push({
                                label: labelEl.textContent.trim(),
                                value: value
                            });
                        });

                        out.push({
                            header: header,
                            selector: selector,
                            fields: fields,
                            empty: fields.length === 0,
                        });
                    });

                    return out;
                })()
            """)
            return items or []
        except:
            return []

    async def _parse_company_page(self, company_url: str) -> Dict[str, Any]:
        try:
            await self.page.goto(company_url, wait_until='domcontentloaded', timeout=30000)
            await self.page.wait_for_timeout(8000)
        except Exception as e:
            raise Exception(f"Failed to open company page: {str(e)}")

        try:
            await self.page.wait_for_selector(
                'information-page-item.card-item, .paragraph-header',
                timeout=15000
            )
        except:
            pass

        data: Dict[str, Any] = {
            'url': company_url,
            'extracted_at': datetime.now().isoformat(),
        }

        m = re.search(r'/companies/([a-f0-9-]+)', company_url)
        if m:
            data['company_guid'] = m.group(1)

        try:
            title = await self.page.title()
            if title:
                data['page_title'] = title.strip()
        except:
            pass

        try:
            heading = await self.page.query_selector(
                'h1, .company-header__name, [class*="company-name"], [class*="entity-name"]'
            )
            if heading:
                name = (await heading.text_content() or '').strip()
                if name:
                    data['detail_company_name'] = name
        except:
            pass

        items = await self._extract_detail_items()
        data['items'] = [it for it in items if not it.get('empty')]
        data['empty_sections'] = [it['header'] for it in items if it.get('empty')]

        return data

    def _build_normalized(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        search_card = raw.get('search_card', {}) or {}

        normalized: Dict[str, Any] = {
            'inn': raw.get('inn', ''),
            'company_name': (
                raw.get('detail_company_name')
                or search_card.get('name')
                or raw.get('page_title', '')
            ),
            'ogrn': search_card.get('ogrn', ''),
            'status': search_card.get('status', ''),
            'search_address': search_card.get('address', ''),
            'search_activity': search_card.get('activity', ''),
        }

        section_map = {
            'Общая информация': {
                'Полное наименование': 'full_name',
                'Сокращенное наименование': 'short_name',
                'Уставный капитал': 'authorized_capital',
                'Адрес по данным ЕГРЮЛ': 'legal_address',
                'Адрес по данным компании': 'company_address',
                'Дата регистрации': 'registration_date',
                'Правовая форма (ОКОПФ)': 'legal_form',
                'Вид деятельности (ОКВЭД)': 'main_activity',
            },
            'Единоличный исполнительный орган': {
                'ФИО': 'director_name',
                'ИНН': 'director_inn',
                'Должность': 'director_position',
                'Дата внесения данных в ЕГРЮЛ': 'director_entry_date',
            },
        }

        for item in raw.get('items', []):
            header = item.get('header', '')
            mapping = section_map.get(header)
            if not mapping:
                continue
            for field in item.get('fields', []):
                label = field.get('label', '')
                value = field.get('value', '')
                key = mapping.get(label)
                if key and value and key not in normalized:
                    normalized[key] = value

        return normalized

    async def _get_company_info_async(self, inn: str) -> Dict[str, Any]:
        if not re.match(r'^\d{10,12}$', inn):
            raise ValueError(f"Invalid INN format: {inn}")

        self._clean_work_dir()
        await self._setup_browser()

        try:
            company_url = await self._search_and_get_company_url(inn)

            if not company_url:
                await self._close()
                return {
                    'inn': inn,
                    'found': False,
                    'extracted_at': datetime.now().isoformat(),
                }

            search_card = await self._extract_result_card()
            detail = await self._parse_company_page(company_url)

            await self._close()
            return {
                'inn': inn,
                'found': True,
                'company_guid': detail.get('company_guid'),
                'company_url': company_url,
                'search_card': search_card,
                'items': detail.get('items', []),
                'empty_sections': detail.get('empty_sections', []),
                'detail_company_name': detail.get('detail_company_name'),
                'page_title': detail.get('page_title'),
                'extracted_at': detail.get('extracted_at'),
            }

        except Exception as e:
            await self._close()
            raise Exception(f"Failed to parse INN {inn}: {str(e)}")

        finally:
            self._clean_work_dir()

    def parse(self, inn: str) -> Dict[str, Any]:
        try:
            raw = asyncio.run(self._get_company_info_async(inn))
            return self._normalize_data(raw)
        except Exception as e:
            raise Exception(f"Failed to parse INN {inn}: {str(e)}")

    def _normalize_data(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        if not raw.get('found'):
            return {
                'inn': raw.get('inn', ''),
                'found': False,
                'company_name': '',
                'extracted_at': raw.get('extracted_at'),
            }

        normalized = self._build_normalized(raw)

        return {
            'inn': raw.get('inn', ''),
            'found': True,
            'company_name': normalized.get('company_name', ''),
            'full_name': normalized.get('full_name', ''),
            'short_name': normalized.get('short_name', ''),
            'ogrn': normalized.get('ogrn', ''),
            'status': normalized.get('status', ''),
            'registration_date': normalized.get('registration_date', ''),
            'legal_address': normalized.get('legal_address', ''),
            'company_address': normalized.get('company_address', ''),
            'authorized_capital': normalized.get('authorized_capital', ''),
            'main_activity': normalized.get('main_activity', ''),
            'legal_form': normalized.get('legal_form', ''),
            'director_name': normalized.get('director_name', ''),
            'director_inn': normalized.get('director_inn', ''),
            'director_position': normalized.get('director_position', ''),
            'director_entry_date': normalized.get('director_entry_date', ''),
            'company_guid': raw.get('company_guid', ''),
            'company_url': raw.get('company_url', ''),
            'empty_sections': raw.get('empty_sections', []),
            'sections': self._compact_sections(raw.get('items', [])),
            'extracted_at': raw.get('extracted_at'),
        }

    def _compact_sections(self, items: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
        out: Dict[str, Dict[str, str]] = {}
        for item in items:
            header = item.get('header', '')
            if not header:
                continue
            fields = item.get('fields', [])
            if not fields:
                continue
            out[header] = {f['label']: f['value'] for f in fields}
        return out

    def get_data_schema(self) -> Dict[str, Any]:
        return {
            'inn': {'type': 'string', 'required': True},
            'found': {'type': 'boolean', 'required': True},
            'company_name': {'type': 'string', 'required': False},
            'full_name': {'type': 'string', 'required': False},
            'short_name': {'type': 'string', 'required': False},
            'ogrn': {'type': 'string', 'required': False},
            'status': {'type': 'string', 'required': False},
            'registration_date': {'type': 'string', 'required': False},
            'legal_address': {'type': 'string', 'required': False},
            'company_address': {'type': 'string', 'required': False},
            'authorized_capital': {'type': 'string', 'required': False},
            'main_activity': {'type': 'string', 'required': False},
            'legal_form': {'type': 'string', 'required': False},
            'director_name': {'type': 'string', 'required': False},
            'director_inn': {'type': 'string', 'required': False},
            'director_position': {'type': 'string', 'required': False},
            'director_entry_date': {'type': 'string', 'required': False},
            'company_guid': {'type': 'string', 'required': False},
            'company_url': {'type': 'string', 'required': False},
            'empty_sections': {'type': 'array', 'required': False},
            'sections': {'type': 'object', 'required': False},
            'extracted_at': {'type': 'string', 'required': False},
        }