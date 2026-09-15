from fastapi import APIRouter, Depends

from src.api.dependencies import get_parser_service
from src.api.errors import ApiError, ErrorCode
from src.api.schemas import ParseBatchRequest, ParseRequest
from src.utils.validators import validate_inn


router = APIRouter(prefix="/parses", tags=["parses"])


@router.post("")
async def create_parse(
    body: ParseRequest,
    service=Depends(get_parser_service),
):
    if not validate_inn(body.inn):
        raise ApiError(400, ErrorCode.INVALID_INN, f"INN '{body.inn}' is not valid")

    source = body.sources[0] if body.sources and len(body.sources) == 1 else None

    if body.sources and len(body.sources) > 1:
        for src in body.sources:
            parser = service.parser_factory.get_parser(src)
            if parser is None:
                raise ApiError(404, ErrorCode.SOURCE_NOT_FOUND, f"Source '{src}' is not available")

    try:
        result = await service.parse_company(
            inn=body.inn,
            source_name=source,
            parallel=body.parallel,
        )
    except Exception as e:
        raise ApiError(500, ErrorCode.PARSE_FAILED, f"Parse failed: {str(e)}")

    return {"ok": True, "data": result}


@router.post("/batch")
async def create_parse_batch(
    body: ParseBatchRequest,
    service=Depends(get_parser_service),
):
    invalid = [inn for inn in body.inns if not validate_inn(inn)]
    if invalid:
        raise ApiError(
            400,
            ErrorCode.INVALID_INN,
            "One or more INNs are invalid",
            details={"invalid_inns": invalid},
        )

    results = []
    for inn in body.inns:
        try:
            result = await service.parse_company(inn=inn, parallel=body.parallel)
            results.append({"inn": inn, "session_id": result.get("session_id"), "success": result.get("success", False)})
        except Exception as e:
            results.append({"inn": inn, "error": str(e), "success": False})

    return {"ok": True, "data": {"results": results, "total": len(results)}}