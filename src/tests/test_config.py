import pytest
import json
import tempfile
from pathlib import Path

from src.config.config_manager import ConfigManager


class TestConfigManager:
    def test_load_config(self, tmp_path):
        config_data = {
            'sources': {
                'test_source': {
                    'enabled': True,
                    'url': 'http://test.com'
                }
            },
            'database': {
                'host': 'localhost',
                'port': 5432
            }
        }
        
        config_file = tmp_path / 'settings.json'
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        config_manager = ConfigManager(str(config_file))
        assert config_manager.get_sources()['test_source']['enabled'] == True
        assert config_manager.get_db_config()['host'] == 'localhost'
    
    def test_get_enabled_sources(self, tmp_path):
        config_data = {
            'sources': {
                'source1': {'enabled': True, 'url': 'http://source1.com'},
                'source2': {'enabled': False, 'url': 'http://source2.com'},
                'source3': {'enabled': True, 'url': 'http://source3.com'}
            }
        }
        
        config_file = tmp_path / 'settings.json'
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        config_manager = ConfigManager(str(config_file))
        enabled = config_manager.get_enabled_sources()
        
        assert 'source1' in enabled
        assert 'source2' not in enabled
        assert 'source3' in enabled
        assert len(enabled) == 2
    
    def test_update_source(self, tmp_path):
        config_data = {
            'sources': {
                'test_source': {
                    'enabled': True,
                    'url': 'http://test.com'
                }
            }
        }
        
        config_file = tmp_path / 'settings.json'
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        config_manager = ConfigManager(str(config_file))
        
        config_manager.update_source('test_source', {
            'enabled': False,
            'url': 'http://newtest.com',
            'timeout': 60
        })
        
        updated = config_manager.get_source_config('test_source')
        assert updated['enabled'] == False
        assert updated['url'] == 'http://newtest.com'
        assert updated['timeout'] == 60