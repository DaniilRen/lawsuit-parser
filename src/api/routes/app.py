import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.dependencies import init_services, verify_api_key
from src.api.errors import ApiError
from src.api.routes import health, sources, parses, companies, sessions


def create_app(config_path: str = "src/config/settings.json") -> FastAPI:
    init_services(config_path)

    app = FastAPI(
        title="Company Info Parser API",
        version="1.0.0",
        description="HTTP API for parsing and querying company data",
    )

    api_key_required = bool(os.getenv('API_KEY', '').strip())

    if api_key_required:
        from fastapi import Depends
        app.router.dependencies = [Depends(verify_api_key)]

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "ok": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(exc),
                    "details": {},
                },
            },
        )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(sources.router, prefix="/api/v1")
    app.include_router(parses.router, prefix="/api/v1")
    app.include_router(companies.router, prefix="/api/v1")
    app.include_router(sessions.router, prefix="/api/v1")

    return app