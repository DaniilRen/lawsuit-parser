from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_query_service
from src.api.errors import ApiError, ErrorCode


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    query=Depends(get_query_service),
):
    data = query.list_sessions(limit=limit, offset=offset)
    return {"ok": True, "data": data}


@router.get("/{session_id}")
async def get_session(session_id: int, query=Depends(get_query_service)):
    data = query.get_session(session_id)
    if not data:
        raise ApiError(404, ErrorCode.NOT_FOUND, f"Session {session_id} not found")
    return {"ok": True, "data": data}


@router.get("/{session_id}/data")
async def get_session_data(session_id: int, query=Depends(get_query_service)):
    data = query.get_session_data(session_id)
    if not data:
        raise ApiError(404, ErrorCode.NOT_FOUND, f"Session {session_id} not found")
    return {"ok": True, "data": data}