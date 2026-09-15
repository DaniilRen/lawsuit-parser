from fastapi import APIRouter, Depends

from src.api.dependencies import get_config_manager, get_query_service


router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
async def list_sources(
    config=Depends(get_config_manager),
    query=Depends(get_query_service),
):
    configured = config.get_sources()
    registered = {s['source_name']: s for s in query.list_registered_sources()}

    items = []
    for name, cfg in configured.items():
        items.append({
            'name': name,
            'enabled': bool(cfg.get('enabled', False)),
            'module': cfg.get('module', ''),
            'class': cfg.get('class', ''),
            'registered': name in registered,
        })

    return {"ok": True, "data": {"items": items, "total": len(items)}}