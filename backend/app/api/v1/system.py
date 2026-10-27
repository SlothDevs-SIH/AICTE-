from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import get_settings
from app.db.base import get_db
from app.db.models import User

router = APIRouter(tags=["system"])

ADAPTERS = {"embeddings": "not_built", "llm": "not_built"}


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # readiness must never raise
        database = "down"
    body = {
        "status": "ready" if database == "ok" else "not_ready",
        "checks": {"database": database},
        "adapters": ADAPTERS,
    }
    return JSONResponse(body, status_code=200 if database == "ok" else 503)


@router.get("/meta")
def meta(_: User = Depends(current_user)):
    s = get_settings()
    return {
        "version": s.version,
        "environment": s.environment,
        "phase": s.phase,
        "data_is_synthetic": True,
        "adapters": ADAPTERS,
    }
