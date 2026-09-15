import os
from typing import Optional

from fastapi import Header, HTTPException

from src.config.config_manager import ConfigManager
from src.database.db_manager import DatabaseManager
from src.services.parser_service import ParserService
from src.services.query_service import QueryService


_config_manager: Optional[ConfigManager] = None
_db_manager: Optional[DatabaseManager] = None
_parser_service: Optional[ParserService] = None
_query_service: Optional[QueryService] = None


def init_services(config_path: str = "src/config/settings.json") -> None:
    global _config_manager, _db_manager, _parser_service, _query_service
    _config_manager = ConfigManager(config_path)
    _db_manager = DatabaseManager(_config_manager.get_db_config())
    _parser_service = ParserService(_db_manager, _config_manager)
    _query_service = QueryService(_db_manager)


def get_config_manager() -> ConfigManager:
    if _config_manager is None:
        raise RuntimeError("Services not initialized")
    return _config_manager


def get_db() -> DatabaseManager:
    if _db_manager is None:
        raise RuntimeError("Services not initialized")
    return _db_manager


def get_parser_service() -> ParserService:
    if _parser_service is None:
        raise RuntimeError("Services not initialized")
    return _parser_service


def get_query_service() -> QueryService:
    if _query_service is None:
        raise RuntimeError("Services not initialized")
    return _query_service


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    expected = os.getenv('API_KEY', '').strip()
    if not expected:
        return
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")