from typing import Any, Dict, Optional

from fastapi import HTTPException


class ApiError(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details or {}


class ErrorCode:
    INVALID_INN = 'INVALID_INN'
    INVALID_REQUEST = 'INVALID_REQUEST'
    NOT_FOUND = 'NOT_FOUND'
    PARSE_FAILED = 'PARSE_FAILED'
    SOURCE_NOT_FOUND = 'SOURCE_NOT_FOUND'
    DATABASE_ERROR = 'DATABASE_ERROR'
    INTERNAL_ERROR = 'INTERNAL_ERROR'
    UNAUTHORIZED = 'UNAUTHORIZED'