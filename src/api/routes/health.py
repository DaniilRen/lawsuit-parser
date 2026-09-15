from fastapi import APIRouter, Depends
from sqlalchemy import text

from src.api.dependencies import get_db


router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db=Depends(get_db)):
    db_status = "connected"
    db_error = None

    session = None
    try:
        session = db.get_session()
        session.execute(text("SELECT 1"))
        session.close()
        session = None
    except Exception as e:
        db_status = "error"
        db_error = f"{type(e).__name__}: {str(e)}"
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                pass

    data = {
        "status": "ok",
        "database": db_status,
    }
    if db_error:
        data["database_error"] = db_error

    return {"ok": True, "data": data}