import pytest
from src.utils.validators import validate_inn, validate_ogrn, validate_kpp, normalize_phone


class TestValidators:
    def test_validate_inn(self):
        assert validate_inn('1234567890') == False
        assert validate_inn('123456789012') == False
        assert validate_inn('invalid') == False
        assert validate_inn('123 456 7890') == False
    
    def test_validate_ogrn(self):
        assert validate_ogrn('1234567890123') == False
        assert validate_ogrn('123456789012345') == False
        assert validate_ogrn('invalid') == False
    
    def test_validate_kpp(self):
        assert validate_kpp('123456789') == False
        assert validate_kpp('12345678') == False
        assert validate_kpp('invalid') == False
    
    def test_normalize_phone(self):
        assert normalize_phone('81234567890') == '+71234567890'
        assert normalize_phone('71234567890') == '+71234567890'
        assert normalize_phone('1234567890') == '+71234567890'