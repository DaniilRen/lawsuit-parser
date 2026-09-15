import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path


class ConfigManager:
    def __init__(self, config_path: str = "src/config/settings.json"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self._resolve_env_variables(config)
        return config
    
    def _resolve_env_variables(self, config: Dict[str, Any]) -> None:
        for key, value in config.items():
            if isinstance(value, dict):
                self._resolve_env_variables(value)
            elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                config[key] = os.getenv(env_var, '')
    
    def get_sources(self) -> Dict[str, Any]:
        return self.config.get('sources', {})
    
    def get_enabled_sources(self) -> Dict[str, Any]:
        return {k: v for k, v in self.get_sources().items() if v.get('enabled', False)}
    
    def get_source_config(self, source_name: str) -> Optional[Dict[str, Any]]:
        return self.get_sources().get(source_name)
    
    def get_source_module_name(self, source_name: str) -> Optional[str]:
        config = self.get_source_config(source_name)
        return config.get('module') if config else None
    
    def get_source_class_name(self, source_name: str) -> Optional[str]:
        config = self.get_source_config(source_name)
        return config.get('class') if config else None
    
    def get_enabled_source_names(self) -> List[str]:
        return list(self.get_enabled_sources().keys())
    
    def get_db_config(self) -> Dict[str, Any]:
        return self.config.get('database', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        return self.config.get('logging', {})
    
    def get_processing_config(self) -> Dict[str, Any]:
        return self.config.get('processing', {})
    
    def get_cache_config(self) -> Dict[str, Any]:
        return self.config.get('cache', {})
    
    def reload(self) -> None:
        self.config = self.load_config()
    
    def update_source(self, source_name: str, config: Dict[str, Any]) -> None:
        if 'sources' not in self.config:
            self.config['sources'] = {}
        self.config['sources'][source_name] = config
        self._save_config()
    
    def enable_source(self, source_name: str) -> None:
        if source_name in self.get_sources():
            self.config['sources'][source_name]['enabled'] = True
            self._save_config()
    
    def disable_source(self, source_name: str) -> None:
        if source_name in self.get_sources():
            self.config['sources'][source_name]['enabled'] = False
            self._save_config()
    
    def _save_config(self) -> None:
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)