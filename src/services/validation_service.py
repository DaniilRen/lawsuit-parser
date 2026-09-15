from typing import Dict, Any, Optional
from datetime import datetime
import re


class ValidationService:
    def __init__(self):
        self.inn_patterns = {
            '10': re.compile(r'^\d{10}$'),
            '12': re.compile(r'^\d{12}$')
        }
    
    def validate_inn(self, inn: str) -> bool:
        inn = inn.replace(' ', '').replace('-', '').strip()
        
        if not inn.isdigit():
            return False
        
        if len(inn) == 10:
            return self._validate_inn_10(inn)
        elif len(inn) == 12:
            return self._validate_inn_12(inn)
        else:
            return False
    
    def _validate_inn_10(self, inn: str) -> bool:
        weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        control_sum = sum(int(inn[i]) * weights[i] for i in range(9))
        control_digit = control_sum % 11
        if control_digit == 10:
            control_digit = 0
        return control_digit == int(inn[9])
    
    def _validate_inn_12(self, inn: str) -> bool:
        weights_1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        control_sum_1 = sum(int(inn[i]) * weights_1[i] for i in range(10))
        control_digit_1 = control_sum_1 % 11
        if control_digit_1 == 10:
            control_digit_1 = 0
        
        if control_digit_1 != int(inn[10]):
            return False
        
        weights_2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        control_sum_2 = sum(int(inn[i]) * weights_2[i] for i in range(11))
        control_digit_2 = control_sum_2 % 11
        if control_digit_2 == 10:
            control_digit_2 = 0
        
        return control_digit_2 == int(inn[11])
    
    def validate_company_data(self, data: Dict[str, Any]) -> bool:
        required_fields = ['inn', 'name']
        for field in required_fields:
            if field not in data or not data[field]:
                return False
        
        if not self.validate_inn(data['inn']):
            return False
        
        if 'registration_date' in data and data['registration_date']:
            if not self._validate_date(data['registration_date']):
                return False
        
        return True
    
    def _validate_date(self, date_value) -> bool:
        if isinstance(date_value, datetime):
            return True
        
        if isinstance(date_value, str):
            date_patterns = [
                r'^\d{4}-\d{2}-\d{2}$',
                r'^\d{2}\.\d{2}\.\d{4}$',
                r'^\d{2}/\d{2}/\d{4}$',
                r'^\d{2}-\d{2}-\d{4}$'
            ]
            for pattern in date_patterns:
                if re.match(pattern, date_value):
                    try:
                        if '-' in date_value:
                            datetime.strptime(date_value, '%Y-%m-%d')
                        elif '.' in date_value:
                            datetime.strptime(date_value, '%d.%m.%Y')
                        elif '/' in date_value:
                            datetime.strptime(date_value, '%d/%m/%Y')
                        return True
                    except ValueError:
                        continue
        return False
    
    def clean_company_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = {}
        
        if 'inn' in data:
            cleaned['inn'] = data['inn'].replace(' ', '').replace('-', '').strip()
        
        if 'name' in data:
            cleaned['name'] = data['name'].strip()
        
        if 'legal_address' in data:
            cleaned['legal_address'] = data['legal_address'].strip()
        
        if 'registration_date' in data and data['registration_date']:
            if isinstance(data['registration_date'], str):
                cleaned['registration_date'] = self._parse_date(data['registration_date'])
            else:
                cleaned['registration_date'] = data['registration_date']
        
        if 'status' in data:
            cleaned['status'] = data['status'].strip().lower()
        
        additional_fields = ['additional_data', 'okpo', 'ogrn', 'kpp', 'director', 'phone', 'email']
        for field in additional_fields:
            if field in data and data[field]:
                if field == 'additional_data':
                    cleaned[field] = data[field]
                else:
                    if 'additional_data' not in cleaned:
                        cleaned['additional_data'] = {}
                    cleaned['additional_data'][field] = data[field]
        
        return cleaned
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        date_str = date_str.strip()
        formats = [
            '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d', 
            '%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None
    
    def normalize_phone(self, phone: str) -> str:
        phone = re.sub(r'[^\d+]', '', phone)
        if phone.startswith('8') and len(phone) == 11:
            phone = '+7' + phone[1:]
        elif phone.startswith('7') and len(phone) == 11:
            phone = '+7' + phone[1:]
        elif len(phone) == 10:
            phone = '+7' + phone
        return phone
    
    def validate_email(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))