"""Runtime settings (BACKEND_PLAN 6.6, 12). Values live in the settings table; defaults are here."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Setting

DEFAULTS: dict[str, object] = {
    "pending_reminder_days": 7,
    "sla_warn_fraction": 0.8,
    "escalation_grace_days": 3,
    "auto_escalate": False,  # escalation is advisory unless an admin turns this on (principle P2)
    "alert_budget_per_day": 20,
    "coordination_days": 5,
    "cluster_min_size": 3,
    "cluster_window_days": 90,
    "issue_threshold": 0.5,
    "ai_llm_enabled": False,
    "ai_issue_matching": False,
    "ai_embeddings_enabled": False,
    "risk_weights": {"volume": 0.20, "ageing": 0.20, "multi_unit": 0.15, "repeat": 0.15,
                     "severity": 0.15, "open_conflicts": 0.10, "trend": 0.05},
}


def get_setting(db: Session, key: str):
    row = db.scalar(select(Setting).where(Setting.key == key))
    return row.value_json if row is not None else DEFAULTS[key]


def all_settings(db: Session) -> dict:
    return {k: get_setting(db, k) for k in DEFAULTS}
