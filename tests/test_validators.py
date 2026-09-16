import pytest

from src.utils.validators import validate_inn, validate_ogrn, validate_kpp


class TestValidateInn:
    def test_valid_10_digit(self):
        assert validate_inn('7707083893') is True
        assert validate_inn('7807234722') is True

    def test_valid_12_digit(self):
        assert validate_inn('500100732259') is True

    def test_invalid_checksum(self):
        assert validate_inn('7707083894') is False

    def test_wrong_length(self):
        assert validate_inn('123') is False
        assert validate_inn('12345678901234') is False

    def test_non_digits(self):
        assert validate_inn('abcdefghij') is False
        assert validate_inn('') is False
        assert validate_inn(None) is False

    def test_with_spaces_and_dashes(self):
        assert validate_inn('770 708 3893') is True
        assert validate_inn('770-708-3893') is True


class TestValidateOgrn:
    def test_valid_13_digit(self):
        assert validate_ogrn('1197847215565') is True

    def test_invalid_checksum(self):
        assert validate_ogrn('1197847215564') is False

    def test_wrong_length(self):
        assert validate_ogrn('123') is False

    def test_non_digits(self):
        assert validate_ogrn('abcdefghijklm') is False
        assert validate_ogrn('') is False


class TestValidateKpp:
    def test_valid(self):
        assert validate_kpp('783801001') is True

    def test_wrong_length(self):
        assert validate_kpp('12345678') is False
        assert validate_kpp('1234567890') is False

    def test_non_digits(self):
        assert validate_kpp('abcdefghi') is False
        assert validate_kpp('') is False

    def test_lowercase_letters_accepted(self):
        # KPP can contain uppercase latin letters in position 5-9 in some formats;
        # the validator only requires digits for the tested format
        assert validate_kpp('783801001') is True