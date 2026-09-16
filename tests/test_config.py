import json
import pytest

from src.config.config_manager import ConfigManager


@pytest.fixture
def config_file(tmp_path):
    data = {
        'sources': {
            'test_source': {
                'enabled': True,
                'module': 'test_parser',
                'class': 'TestParser',
            },
            'disabled_source': {
                'enabled': False,
                'module': 'other_parser',
                'class': 'OtherParser',
            },
        },
        'database': {
            'host': 'localhost',
            'port': 5432,
            'name': 'test_db',
        },
        'logging': {'level': 'DEBUG'},
        'processing': {'parallel_sources': True, 'max_workers': 3},
    }
    path = tmp_path / 'settings.json'
    path.write_text(json.dumps(data))
    return str(path)


class TestConfigManager:
    def test_load_config(self, config_file):
        cm = ConfigManager(config_file)
        assert 'test_source' in cm.get_sources()
        assert 'disabled_source' in cm.get_sources()

    def test_get_enabled_sources(self, config_file):
        cm = ConfigManager(config_file)
        enabled = cm.get_enabled_sources()
        assert 'test_source' in enabled
        assert 'disabled_source' not in enabled
        assert len(enabled) == 1

    def test_get_enabled_source_names(self, config_file):
        cm = ConfigManager(config_file)
        assert cm.get_enabled_source_names() == ['test_source']

    def test_get_source_config(self, config_file):
        cm = ConfigManager(config_file)
        cfg = cm.get_source_config('test_source')
        assert cfg is not None
        assert cfg['module'] == 'test_parser'

    def test_get_missing_source_returns_none(self, config_file):
        cm = ConfigManager(config_file)
        assert cm.get_source_config('nonexistent') is None

    def test_get_db_config(self, config_file):
        cm = ConfigManager(config_file)
        db = cm.get_db_config()
        assert db['host'] == 'localhost'
        assert db['port'] == 5432

    def test_get_logging_config(self, config_file):
        cm = ConfigManager(config_file)
        assert cm.get_logging_config()['level'] == 'DEBUG'

    def test_get_processing_config(self, config_file):
        cm = ConfigManager(config_file)
        assert cm.get_processing_config()['parallel_sources'] is True

    def test_missing_config_file_raises(self):
        with pytest.raises(FileNotFoundError):
            ConfigManager('/nonexistent/path/settings.json')