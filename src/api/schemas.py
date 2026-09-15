from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    inn: str = Field(..., description="Taxpayer Identification Number (10 or 12 digits)")
    sources: Optional[List[str]] = Field(None, description="Specific source names; empty means all enabled")
    parallel: bool = Field(False, description="Run parsers in parallel")


class ParseBatchRequest(BaseModel):
    inns: List[str] = Field(..., min_items=1)
    sources: Optional[List[str]] = None
    parallel: bool = False


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    ok: bool = False
    error: ErrorBody


class DataResponse(BaseModel):
    ok: bool = True
    data: Any