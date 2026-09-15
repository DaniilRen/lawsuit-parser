from typing import Dict, Any, Optional, List
import re
import asyncio
import os
import shutil
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import pdfplumber

from src.parsers.base_parser import BaseParser


class EgrulParser(BaseParser):
    WORK_DIR = Path(__file__).parent / "egrul_working_dir"
    BASE_URL = "https://egrul.nalog.ru/index.html"

    def __init__(self, source_name: str, config: Dict[str, Any]):
        super().__init__(source_name, config)
        self.browser = None
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
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except:
                pass

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
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            accept_downloads=True
        )

    async def _close(self):
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass

    async def _search_and_download(self, inn: str) -> Optional[Path]:
        try:
            await self.page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=20000)
            await self.page.wait_for_timeout(2000)
        except Exception as e:
            raise Exception(f"Failed to open EGRUL page: {str(e)}")

        try:
            search_input = await self.page.wait_for_selector(
                '#query, input[name="query"], input[type="text"]',
                timeout=10000
            )
            await search_input.click()
            await search_input.fill(inn)
            await self.page.wait_for_timeout(500)
            await search_input.press('Enter')
        except Exception as e:
            raise Exception(f"Failed to enter INN: {str(e)}")

        try:
            await self.page.wait_for_selector('#resultContent .res-row', timeout=15000)
            await self.page.wait_for_timeout(2000)
        except:
            body = await self.page.text_content('body')
            if 'не найдено' in body.lower() or 'отсутствуют' in body.lower():
                raise Exception(f"No results found for INN: {inn}")
            raise Exception("Search results did not appear")

        try:
            download_button = await self.page.wait_for_selector(
                '#resultContent .res-row .btn-excerpt, '
                '#resultContent .res-row button.op-excerpt',
                timeout=10000
            )
        except Exception as e:
            raise Exception(f"Download button not found: {str(e)}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        expected_pdf = self.WORK_DIR / f"ul-{inn}-{timestamp}.pdf"

        try:
            async with self.page.expect_download(timeout=60000) as download_info:
                await download_button.click()
            download = await download_info.value
        except Exception as e:
            existing = sorted(self.WORK_DIR.glob("*.pdf"), key=os.path.getmtime)
            if existing:
                return existing[-1]
            raise Exception(f"Download did not start: {str(e)}")

        try:
            await download.save_as(str(expected_pdf))
            return expected_pdf
        except Exception as e:
            suggested = download.suggested_filename
            fallback = self.WORK_DIR / suggested
            try:
                await download.save_as(str(fallback))
                return fallback
            except:
                raise Exception(f"Failed to save PDF: {str(e)}")

    def _extract_tables(self, pdf_path: Path) -> List[List[str]]:
        rows: List[List[str]] = []
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables() or []
                    for table in tables:
                        for row in table:
                            if row is None:
                                continue
                            cleaned = []
                            for cell in row:
                                if cell is None:
                                    cleaned.append("")
                                else:
                                    c = str(cell).replace("\n", " ")
                                    c = re.sub(r"\s+", " ", c).strip()
                                    cleaned.append(c)
                            if any(c for c in cleaned):
                                rows.append(cleaned)
        except Exception as e:
            raise Exception(f"Failed to extract PDF tables: {str(e)}")
        return rows

    def _extract_raw_text(self, pdf_path: Path) -> str:
        parts = []
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    parts.append(t)
        except:
            pass
        return "\n".join(parts)

    def _find_table_value(self, rows: List[List[str]], label: str, value_regex: Optional[str] = None) -> Optional[str]:
        for row in rows:
            for idx, cell in enumerate(row):
                if cell and label in cell:
                    for j in range(idx + 1, len(row)):
                        candidate = row[j]
                        if not candidate:
                            continue
                        if candidate == label:
                            continue
                        if value_regex:
                            m = re.search(value_regex, candidate)
                            if m:
                                return m.group(1).strip()
                        else:
                            if not re.fullmatch(r"\d+", candidate):
                                return candidate.strip()
        return None

    def _parse_pdf(self, pdf_path: Path, inn: str) -> Dict[str, Any]:
        rows = self._extract_tables(pdf_path)
        raw_text = self._extract_raw_text(pdf_path)

        data: Dict[str, Any] = {
            'inn': inn,
            'source_format': 'egrul_pdf',
            'extracted_at': datetime.now().isoformat(),
        }

        data['full_name'] = self._extract_name_from_rows(rows, 'Полное наименование на русском языке')
        data['short_name'] = self._extract_name_from_rows(rows, 'Сокращенное наименование на русском языке')
        data['full_name_en'] = self._extract_name_from_rows(rows, 'Полное наименование на английском языке')
        data['short_name_en'] = self._extract_name_from_rows(rows, 'Сокращенное наименование на английском языке')

        if not data['full_name']:
            data['full_name'] = self._extract_name_from_raw(raw_text, 'Полное наименование на русском языке')
        if not data['short_name']:
            data['short_name'] = self._extract_name_from_raw(raw_text, 'Сокращенное наименование на русском языке')

        data['ogrn'] = self._find_table_value(rows, 'ОГРН', r'(\d{13,15})') or self._extract_from_raw(raw_text, r'ОГРН\s*[:\s]*(\d{13,15})')
        data['kpp'] = self._find_table_value(rows, 'КПП юридического лица', r'(\d{9})') or self._extract_from_raw(raw_text, r'КПП\s+юридического лица\s*[:\s]*(\d{9})')
        data['inn_company'] = self._find_table_value(rows, 'ИНН юридического лица', r'(\d{10,12})') or inn

        data['registration_date'] = self._find_table_value(rows, 'Дата регистрации', r'(\d{2}\.\d{2}\.\d{4})')
        data['formation_method'] = self._find_table_value(rows, 'Способ образования')
        data['legal_address'] = self._extract_address(rows, raw_text)
        data['tax_office'] = self._extract_tax_office(rows)
        data['tax_registration_date'] = self._find_table_value(rows, 'Дата постановки на учет в налоговом органе', r'(\d{2}\.\d{2}\.\d{4})')

        data['director'] = self._extract_director(rows)
        data['authorized_capital'] = self._extract_capital(rows)
        data['insurer_info'] = self._extract_insurer(rows)
        data['registrar'] = self._extract_registrar(rows)

        data['main_activity'] = self._extract_main_activity(rows)

        data['status'] = self._detect_status(raw_text)
        data['has_invalid_info'] = self._detect_invalid_info(raw_text)

        data['records'] = self._extract_records(rows, raw_text)

        return data

    def _extract_name_from_rows(self, rows: List[List[str]], label: str) -> Optional[str]:
        for row in rows:
            for idx, cell in enumerate(row):
                if not cell:
                    continue
                if label in cell:
                    if '|' in cell:
                        parts = cell.split('|', 1)
                        if len(parts) == 2 and parts[1].strip():
                            return parts[1].strip()
                    for j in range(idx + 1, len(row)):
                        candidate = row[j]
                        if not candidate:
                            continue
                        if candidate == label:
                            continue
                        if re.fullmatch(r"\d+", candidate):
                            continue
                        if len(candidate) > 3:
                            return candidate.strip()
        return None

    def _extract_name_from_raw(self, text: str, label: str) -> Optional[str]:
        pattern = re.escape(label) + r'\s*\n\s*([^\n]{5,})'
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip()
        return None

    def _extract_from_raw(self, text: str, pattern: str) -> Optional[str]:
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip()
        return None

    def _extract_address(self, rows: List[List[str]], raw_text: str) -> Optional[str]:
        for row in rows:
            for idx, cell in enumerate(row):
                if cell and 'Адрес юридического лица' in cell:
                    parts = []
                    for j in range(idx + 1, len(row)):
                        c = row[j]
                        if not c:
                            continue
                        parts.append(c)
                    if parts:
                        addr = " ".join(parts)
                        addr = re.sub(r"\s+", " ", addr).strip()
                        addr = re.sub(r"\s+\d{1,3}$", "", addr).strip()
                        if len(addr) > 10:
                            return addr

        m = re.search(
            r'Адрес юридического лица\s*\n?\s*(?:11\s*\|\s*)?([^\n|]+)',
            raw_text
        )
        if m:
            addr = re.sub(r"\s+", " ", m.group(1)).strip()
            addr = re.sub(r"\s+\d{1,3}$", "", addr).strip()
            if len(addr) > 10:
                return addr

        return None

    def _extract_tax_office(self, rows: List[List[str]]) -> Optional[str]:
        for row in rows:
            for idx, cell in enumerate(row):
                if cell and 'Сведения о налоговом органе' in cell:
                    for j in range(idx + 1, len(row)):
                        c = row[j]
                        if not c:
                            continue
                        if 'Межрайонная' in c or 'Инспекция' in c or 'Управление' in c:
                            return c.strip()
                if cell and 'Наименование налогового органа' in cell:
                    for j in range(idx + 1, len(row)):
                        c = row[j]
                        if c and ('Межрайонная' in c or 'Инспекция' in c):
                            return c.strip()
        return None

    def _extract_director(self, rows: List[List[str]]) -> Dict[str, Any]:
        director: Dict[str, Any] = {}

        for i, row in enumerate(rows):
            joined = " | ".join(row)
            if 'Фамилия Имя Отчество' in joined:
                for idx, cell in enumerate(row):
                    if 'Фамилия Имя Отчество' in cell:
                        for j in range(idx + 1, len(row)):
                            c = row[j]
                            if c and not re.fullmatch(r"\d+", c) and len(c) > 3:
                                director['name'] = c.strip()
                                break
                        break

                for j in range(i, min(i + 5, len(rows))):
                    for cell in rows[j]:
                        m = re.search(r'ИНН\s*[:\s]*(\d{10,12})', cell or '')
                        if m:
                            director['inn'] = m.group(1)
                            break
                    if 'inn' in director:
                        break
                break

        for row in rows:
            for idx, cell in enumerate(row):
                if cell and cell == 'Должность':
                    for j in range(idx + 1, len(row)):
                        c = row[j]
                        if c and not re.fullmatch(r"\d+", c):
                            director['position'] = c.strip()
                            break
                    if 'position' in director:
                        break
            if 'position' in director:
                break

        return director

    def _extract_capital(self, rows: List[List[str]]) -> Dict[str, Any]:
        capital: Dict[str, Any] = {}
        for row in rows:
            for idx, cell in enumerate(row):
                if cell and cell.strip() == 'Вид':
                    for j in range(idx + 1, len(row)):
                        c = row[j]
                        if c and ('КАПИТАЛ' in c.upper() or 'ФОНД' in c.upper()):
                            capital['type'] = c.strip()
                            break
        amount = self._find_table_value(rows, 'Размер (в рублях)', r'(\d+)')
        if amount:
            capital['amount_rub'] = amount
        return capital

    def _extract_insurer(self, rows: List[List[str]]) -> Dict[str, Any]:
        insurer: Dict[str, Any] = {}
        reg = self._find_table_value(rows, 'Регистрационный номер страхователя', r'(\d+)')
        if reg:
            insurer['registration_number'] = reg
        for row in rows:
            for idx, cell in enumerate(row):
                if cell and 'Наименование территориального органа Социального Фонда' in cell:
                    for j in range(idx + 1, len(row)):
                        c = row[j]
                        if c and len(c) > 5:
                            insurer['sfr_office'] = c.strip()
                            break
        return insurer

    def _extract_registrar(self, rows: List[List[str]]) -> Dict[str, Any]:
        registrar: Dict[str, Any] = {}
        for row in rows:
            joined = " | ".join(row)
            if 'АКЦИОНЕРНОЕ ОБЩЕСТВО "РЕЕСТР"' in joined or ('"РЕЕСТР"' in joined and 'Полное наименование' in joined):
                for idx, cell in enumerate(row):
                    if cell and '"РЕЕСТР"' in cell:
                        registrar['full_name'] = cell.strip()
                        break
        for row in rows:
            for idx, cell in enumerate(row):
                if cell == 'ОГРН':
                    for j in range(idx + 1, len(row)):
                        c = row[j]
                        if c and re.fullmatch(r"\d{13}", c):
                            registrar['ogrn'] = c
                            break
                if cell == 'ИНН':
                    for j in range(idx + 1, len(row)):
                        c = row[j]
                        if c and re.fullmatch(r"\d{10}", c):
                            registrar['inn'] = c
                            break
        return registrar

    def _extract_main_activity(self, rows: List[List[str]]) -> Optional[str]:
        code_re = re.compile(r'^\d{2}\.\d{2}(?:\.\d+)?\s+\S')
        for row in rows:
            for idx, cell in enumerate(row):
                if not cell:
                    continue
                if 'Код и наименование вида деятельности' in cell:
                    inline = cell.replace('Код и наименование вида деятельности', '').strip()
                    candidate = None
                    if inline and code_re.match(inline):
                        candidate = inline
                    else:
                        for j in range(idx + 1, len(row)):
                            c = row[j]
                            if c and code_re.match(c):
                                candidate = c.strip()
                                break
                    if candidate:
                        candidate = re.sub(r'\s+\d+\s*$', '', candidate).strip()
                        candidate = re.sub(r'\s*ГРН.*$', '', candidate).strip()
                        if code_re.match(candidate):
                            return candidate
        return None

    def _detect_status(self, text: str) -> str:
        if re.search(r'прекращени[ея]\s+деятельности', text, re.IGNORECASE):
            return 'прекращена'
        if re.search(r'в\s+процессе\s+реорганизации', text, re.IGNORECASE):
            return 'реорганизация'
        if re.search(r'ликвидац', text, re.IGNORECASE):
            return 'ликвидация'
        return 'действующая'

    def _detect_invalid_info(self, text: str) -> Optional[bool]:
        if re.search(r'недостоверност[ьи]\s+сведений', text, re.IGNORECASE):
            return True
        return None

    def _extract_records(self, rows: List[List[str]], raw_text: str) -> List[str]:
        records: List[str] = []
        for row in rows:
            for idx, cell in enumerate(row):
                if cell and 'Причина внесения записи в ЕГРЮЛ' in cell:
                    inline = cell.replace('Причина внесения записи в ЕГРЮЛ', '').strip()
                    candidate = None
                    if inline and len(inline) > 5:
                        candidate = inline
                    else:
                        for j in range(idx + 1, len(row)):
                            c = row[j]
                            if c and len(c) > 5:
                                candidate = c.strip()
                                break
                    if candidate:
                        candidate = re.sub(r'\s+', ' ', candidate).strip()
                        if candidate not in records:
                            records.append(candidate)

        if not records:
            pattern = re.compile(
                r'Причина внесения записи в ЕГРЮЛ\s*\n\s*([^\n]{5,})',
                re.MULTILINE
            )
            for m in pattern.finditer(raw_text):
                r = m.group(1).strip()
                if r and r not in records:
                    records.append(r)

        return records

    async def _get_company_info_async(self, inn: str) -> Dict[str, Any]:
        if not re.match(r'^\d{10,12}$', inn):
            raise ValueError(f"Invalid INN format: {inn}")

        self._clean_work_dir()
        await self._setup_browser()

        try:
            pdf_path = await self._search_and_download(inn)
            if not pdf_path or not pdf_path.exists():
                raise Exception("PDF file was not created")

            data = self._parse_pdf(pdf_path, inn)
            await self._close()
            return data

        except Exception as e:
            await self._close()
            raise Exception(f"Failed to parse INN {inn}: {str(e)}")

        finally:
            self._clean_work_dir()

    def parse(self, inn: str) -> Dict[str, Any]:
        try:
            result = asyncio.run(self._get_company_info_async(inn))
            return self._normalize_data(result)
        except Exception as e:
            raise Exception(f"Failed to parse INN {inn}: {str(e)}")

    def _normalize_data(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'inn': raw.get('inn', ''),
            'company_name': raw.get('full_name') or raw.get('short_name') or '',
            'full_name': raw.get('full_name', ''),
            'short_name': raw.get('short_name', ''),
            'full_name_en': raw.get('full_name_en', ''),
            'short_name_en': raw.get('short_name_en', ''),
            'ogrn': raw.get('ogrn', ''),
            'kpp': raw.get('kpp', ''),
            'registration_date': raw.get('registration_date', ''),
            'formation_method': raw.get('formation_method', ''),
            'legal_address': raw.get('legal_address', ''),
            'tax_office': raw.get('tax_office', ''),
            'tax_registration_date': raw.get('tax_registration_date', ''),
            'status': raw.get('status', ''),
            'authorized_capital': raw.get('authorized_capital', {}),
            'director': raw.get('director', {}),
            'insurer_info': raw.get('insurer_info', {}),
            'registrar': raw.get('registrar', {}),
            'main_activity': raw.get('main_activity', ''),
            'has_invalid_info': raw.get('has_invalid_info'),
            'records': raw.get('records', []),
            'raw_data': raw,
        }

    def get_data_schema(self) -> Dict[str, Any]:
        return {
            'inn': {'type': 'string', 'required': True},
            'company_name': {'type': 'string', 'required': True},
            'full_name': {'type': 'string', 'required': False},
            'short_name': {'type': 'string', 'required': False},
            'full_name_en': {'type': 'string', 'required': False},
            'short_name_en': {'type': 'string', 'required': False},
            'ogrn': {'type': 'string', 'required': False},
            'kpp': {'type': 'string', 'required': False},
            'registration_date': {'type': 'string', 'required': False},
            'formation_method': {'type': 'string', 'required': False},
            'legal_address': {'type': 'string', 'required': False},
            'tax_office': {'type': 'string', 'required': False},
            'tax_registration_date': {'type': 'string', 'required': False},
            'status': {'type': 'string', 'required': False},
            'authorized_capital': {'type': 'object', 'required': False},
            'director': {'type': 'object', 'required': False},
            'insurer_info': {'type': 'object', 'required': False},
            'registrar': {'type': 'object', 'required': False},
            'main_activity': {'type': 'string', 'required': False},
            'has_invalid_info': {'type': 'boolean', 'required': False},
            'records': {'type': 'array', 'required': False},
            'raw_data': {'type': 'object', 'required': False},
        }