from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import get_settings
from app.db.base import get_db
from app.db.models import User

router = APIRouter(tags=["system"])

ADAPTERS = {"concept_matching": "built", "embeddings": "not_built", "llm": "not_built"}


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


@router.get("/public/overview")
def public_overview(db: Session = Depends(get_db)):
    """Landing-page numbers read live from the running database. No personal data, no case text."""
    from sqlalchemy import func, select

    from app.db.models import Complaint, Institution, Overlap, Unit

    conflict = db.scalar(select(Overlap).where(Overlap.severity == "CONFLICT", Overlap.status != "DISMISSED")
                         .order_by(Overlap.detected_at.desc()))
    sample = None
    if conflict:
        a, b = db.get(Complaint, conflict.complaint_a_id), db.get(Complaint, conflict.complaint_b_id)
        sample = {"institution": db.get(Institution, conflict.institution_id).canonical_name,
                  "units": [db.get(Unit, a.unit_id).code, db.get(Unit, b.unit_id).code],
                  "reasons": conflict.receipt_json["layers"]["L4_rules"]["reasons"]}
    n = lambda q: db.scalar(q) or 0  # noqa: E731
    return {
        "complaints": n(select(func.count()).select_from(Complaint)),
        "complaints_simulated": n(select(func.count()).select_from(Complaint).where(Complaint.is_synthetic.is_(True))),
        "colleges": n(select(func.count()).select_from(Institution)),
        "colleges_real": n(select(func.count()).select_from(Institution).where(Institution.is_synthetic.is_(False))),
        "open_overlaps": n(select(func.count()).select_from(Overlap).where(Overlap.status.in_(("SUGGESTED", "CONFIRMED", "LINKED")))),
        "sample_conflict": sample,
    }


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
