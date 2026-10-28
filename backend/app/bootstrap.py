"""First start on a fresh machine (for example a new Render deploy): create the tables and load the demo data.

Does nothing when the database already has users, so a restart never wipes anything. Set AUTO_SEED=false to disable.
"""
import os
from pathlib import Path

from sqlalchemy import inspect, select

from app.db.base import Base, get_engine, session_factory

ROOT = Path(__file__).resolve().parent.parent


def ensure_database() -> str:
    import app.db.models  # noqa: F401  (registers the tables)
    from app.db.models import User

    if os.environ.get("AUTO_SEED", "true").lower() in ("0", "false", "no"):
        return "disabled"
    engine = get_engine()
    (ROOT / "data").mkdir(exist_ok=True)
    Base.metadata.create_all(engine)
    with session_factory()() as db:
        if inspect(engine).has_table("users") and db.scalar(select(User.id).limit(1)):
            return "existing"
        from app import seed

        seed.seed(db, 42, ROOT / "data" / "ground_truth.json")
    return "seeded"
