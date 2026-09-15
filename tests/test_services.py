import pytest
from unittest.mock import Mock, patch

from src.services.parser_service import ParserService
from src.services.validation_service import ValidationService


class TestParserService:
    @pytest.fixture
    def mock_config_manager(self):
        config = Mock()
        config.get_sources.return_value = {
            'source1': {'enabled': True, 'parser_class': 'Source1Parser'},
            'source2': {'enabled': False, 'parser_class': 'Source2Parser'}
        }
        config.get_processing_config.return_value = {
            'parallel_sources': False,
            'max_workers': 3,
            'timeout_per_source': 60
        }
        return config
    
    @pytest.fixture
    def mock_db_manager(self):
        return Mock()
    
    @pytest.fixture
    def parser_service(self, mock_db_manager, mock_config_manager):
        return ParserService(mock_db_manager, mock_config_manager)
    
    def test_parse_company_invalid_inn(self, parser_service):
        result = parser_service.parse_company_sync('invalid')
        assert result['success'] == False
        assert 'Invalid INN' in result['error']


class TestValidationService:
    def test_validate_inn_10(self):
        service = ValidationService()
        assert service.validate_inn('1234567890') == False
    
    def test_validate_inn_12(self):
        service = ValidationService()
        assert service.validate_inn('123456789012') == False
    
    def test_validate_company_data(self):
        service = ValidationService()
        
        valid_data = {
            'inn': '1234567890',
            'name': 'Test Company',
            'legal_address': 'Test Address'
        }
        
        assert service.validate_company_data(valid_data) == True
        
        invalid_data = {
            'name': 'Test Company'
        }
        
        assert service.validate_company_data(invalid_data) == False