import pytest
from unittest.mock import Mock, patch

from src.parsers.base_parser import BaseParser
from src.parsers.parser_factory import ParserFactory


class TestBaseParser:
    def test_abstract_methods(self):
        with pytest.raises(TypeError):
            BaseParser('test', {})
    
    def test_normalize_inn(self):
        class TestParser(BaseParser):
            def parse(self, inn):
                return {}
            
            def validate_data(self, data):
                return True
        
        parser = TestParser('test', {})
        
        assert parser.normalize_inn('123 456 7890') == '1234567890'
        assert parser.normalize_inn('123-456-7890') == '1234567890'
        assert parser.normalize_inn(' 1234567890 ') == '1234567890'


class TestParserFactory:
    @pytest.fixture
    def mock_config_manager(self):
        config = Mock()
        config.get_source_config.return_value = {
            'enabled': True,
            'url': 'http://test.com',
            'parser_class': 'TestParser'
        }
        config.get_sources.return_value = {
            'source1': {'enabled': True, 'parser_class': 'TestParser'},
            'source2': {'enabled': False, 'parser_class': 'TestParser'}
        }
        return config
    
    def test_get_parser_not_found(self, mock_config_manager):
        factory = ParserFactory(mock_config_manager)
        parser = factory.get_parser('nonexistent')
        assert parser is None