from typing import Dict, Any, Optional
import importlib
import inspect
import logging

from src.parsers.base_parser import BaseParser


class ParserFactory:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.parsers = {}
        self.parser_modules = {}
        self.logger = logging.getLogger(__name__)
    
    def _load_parser_module(self, source_name: str):
        if source_name in self.parser_modules:
            return self.parser_modules[source_name]
        
        source_config = self.config_manager.get_source_config(source_name)
        if not source_config:
            return None
        
        module_name = source_config.get('module')
        if not module_name:
            return None
        
        try:
            module = importlib.import_module(f"src.parsers.{module_name}")
            self.parser_modules[source_name] = module
            return module
        except ImportError as e:
            self.logger.warning(f"Parser module '{module_name}' not found for source '{source_name}'")
            return None
    
    def get_parser(self, source_name: str) -> Optional[BaseParser]:
        if source_name in self.parsers:
            return self.parsers[source_name]
        
        source_config = self.config_manager.get_source_config(source_name)
        if not source_config:
            return None
        
        if not source_config.get('enabled', False):
            return None
        
        module = self._load_parser_module(source_name)
        if not module:
            return None
        
        class_name = source_config.get('class')
        if not class_name:
            return None
        
        parser_class = getattr(module, class_name, None)
        if not parser_class:
            self.logger.warning(f"Parser class '{class_name}' not found in module for source '{source_name}'")
            return None
        
        if not inspect.isclass(parser_class) or not issubclass(parser_class, BaseParser):
            self.logger.warning(f"Class '{class_name}' is not a valid BaseParser subclass")
            return None
        
        parser_instance = parser_class(source_name, source_config)
        self.parsers[source_name] = parser_instance
        return parser_instance
    
    def get_all_parsers(self, enabled_only: bool = True) -> Dict[str, BaseParser]:
        sources = self.config_manager.get_sources()
        if enabled_only:
            sources = {k: v for k, v in sources.items() if v.get('enabled', False)}
        
        parsers = {}
        for source_name in sources:
            parser = self.get_parser(source_name)
            if parser:
                parsers[source_name] = parser
            else:
                self.logger.info(f"Skipping source '{source_name}': parser not available")
        
        return parsers
    
    def get_enabled_source_names(self) -> list:
        return list(self.get_all_parsers(enabled_only=True).keys())
    
    def get_available_source_names(self) -> list:
        return list(self.config_manager.get_sources().keys())