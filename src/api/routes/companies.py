from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_parser_service, get_query_service
from src.api.errors import ApiError, ErrorCode
from src.utils.validators import validate_inn


router = APIRouter(prefix="/companies", tags=["companies"])


def _parse_sources(sources: str) -> list:
    if not sources:
        return []
    return [s.strip() for s in sources.split(',') if s.strip()]


@router.get("")
async def list_companies(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    query=Depends(get_query_service),
):
    data = query.list_companies(limit=limit, offset=offset)
    return {"ok": True, "data": data}


@router.get("/{inn}")
async def get_company(inn: str, query=Depends(get_query_service)):
    if not validate_inn(inn):
        raise ApiError(400, ErrorCode.INVALID_INN, f"INN '{inn}' is not valid")

    data = query.get_company(inn)
    if not data:
        raise ApiError(404, ErrorCode.NOT_FOUND, f"Company '{inn}' has never been parsed")

    return {"ok": True, "data": data}


@router.get("/{inn}/latest")
async def get_latest(
    inn: str,
    sources: str = Query(''),
    query=Depends(get_query_service),
):
    if not validate_inn(inn):
        raise ApiError(400, ErrorCode.INVALID_INN, f"INN '{inn}' is not valid")

    source_list = _parse_sources(sources) or None
    data = query.get_latest(inn, sources=source_list)
    if not data:
        raise ApiError(404, ErrorCode.NOT_FOUND, f"No data found for INN '{inn}'")

    return {"ok": True, "data": data}


@router.get("/{inn}/history")
async def get_history(
    inn: str,
    sources: str = Query(''),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    query=Depends(get_query_service),
):
    if not validate_inn(inn):
        raise ApiError(400, ErrorCode.INVALID_INN, f"INN '{inn}' is not valid")

    source_list = _parse_sources(sources) or None
    data = query.get_history(inn, sources=source_list, limit=limit, offset=offset)

    if not data['items']:
        raise ApiError(404, ErrorCode.NOT_FOUND, f"No history found for INN '{inn}'")

    return {"ok": True, "data": data}


@router.get("/{inn}/diff")
async def get_diff(
    inn: str,
    from_session: int = Query(..., alias='from'),
    to_session: int = Query(..., alias='to'),
    sources: str = Query(''),
    query=Depends(get_query_service),
    service=Depends(get_parser_service),
):
    if not validate_inn(inn):
        raise ApiError(400, ErrorCode.INVALID_INN, f"INN '{inn}' is not valid")

    from_row = query.get_session(from_session)
    if not from_row:
        raise ApiError(404, ErrorCode.NOT_FOUND, f"Session {from_session} not found")

    to_row = query.get_session(to_session)
    if not to_row:
        raise ApiError(404, ErrorCode.NOT_FOUND, f"Session {to_session} not found")

    source_list = _parse_sources(sources) or None
    diff = service.diff_sessions(
        inn=inn,
        from_session_id=from_session,
        to_session_id=to_session,
        sources=source_list,
    )

    return {"ok": True, "data": diff}


@router.get("/{inn}/diff/latest")
async def get_diff_latest(
    inn: str,
    sources: str = Query(''),
    query=Depends(get_query_service),
    service=Depends(get_parser_service),
):
    if not validate_inn(inn):
        raise ApiError(400, ErrorCode.INVALID_INN, f"INN '{inn}' is not valid")

    history = query.get_history(inn, sources=_parse_sources(sources) or None, limit=2, offset=0)
    if len(history['items']) < 2:
        raise ApiError(404, ErrorCode.NOT_FOUND, "Not enough sessions to compare")

    latest = history['items'][0]['session_id']
    previous = history['items'][1]['session_id']

    diff = service.diff_sessions(
        inn=inn,
        from_session_id=previous,
        to_session_id=latest,
        sources=_parse_sources(sources) or None,
    )

    return {"ok": True, "data": diff}