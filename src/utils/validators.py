import re
from typing import Optional


def validate_inn(inn: str) -> bool:
    inn = inn.replace(' ', '').replace('-', '').strip()
    
    if not inn.isdigit():
        return False
    
    if len(inn) == 10:
        return _validate_inn_10(inn)
    elif len(inn) == 12:
        return _validate_inn_12(inn)
    else:
        return False


def _validate_inn_10(inn: str) -> bool:
    weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    control_sum = sum(int(inn[i]) * weights[i] for i in range(9))
    control_digit = control_sum % 11
    if control_digit == 10:
        control_digit = 0
    return control_digit == int(inn[9])


def _validate_inn_12(inn: str) -> bool:
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


def validate_ogrn(ogrn: str) -> bool:
    ogrn = ogrn.replace(' ', '').replace('-', '').strip()
    
    if not ogrn.isdigit():
        return False
    
    if len(ogrn) == 13:
        return _validate_ogrn_13(ogrn)
    elif len(ogrn) == 15:
        return _validate_ogrn_15(ogrn)
    else:
        return False


def _validate_ogrn_13(ogrn: str) -> bool:
    ogrn_without_check = ogrn[:-1]
    check_sum = sum(int(d) for d in ogrn_without_check)
    check_digit = check_sum % 10
    if check_digit == 10:
        check_digit = 0
    return check_digit == int(ogrn[-1])


def _validate_ogrn_15(ogrn: str) -> bool:
    ogrn_without_check = ogrn[:-1]
    check_sum = sum(int(d) for d in ogrn_without_check)
    check_digit = check_sum % 10
    if check_digit == 10:
        check_digit = 0
    return check_digit == int(ogrn[-1])


def validate_kpp(kpp: str) -> bool:
    kpp = kpp.replace(' ', '').replace('-', '').strip().upper()
    
    if len(kpp) != 9:
        return False
    
    if not kpp[:4].isnumeric():
        return False
    
    if not kpp[4:9].isnumeric():
        return False
    
    return True


def normalize_phone(phone: str) -> str:
    phone = re.sub(r'[^\d+]', '', phone)
    
    if phone.startswith('8') and len(phone) == 11:
        phone = '+7' + phone[1:]
    elif phone.startswith('7') and len(phone) == 11:
        phone = '+7' + phone[1:]
    elif len(phone) == 10:
        phone = '+7' + phone
    
    return phone


def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))