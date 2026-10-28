import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy import DateTime, String

from app.core.config import get_settings


def _now() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class RowMixin:
    """id (UUID, not guessable), created_at, updated_at on every table."""
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


_engine = None
_Session = None


def normalize_url(url: str) -> str:
    """Hosts hand out postgres:// or postgresql:// URLs; SQLAlchemy needs the driver named (psycopg 3)."""
    for old in ("postgres://", "postgresql://"):
        if url.startswith(old):
            return "postgresql+psycopg://" + url[len(old):]
    return url


def _pool_kw() -> dict:
    import os

    n = os.environ.get("DB_POOL_SIZE")
    return {"pool_size": int(n), "max_overflow": 0} if n else {}


def get_engine():
    global _engine, _Session
    if _engine is None:
        url = normalize_url(get_settings().database_url)
        if url.startswith("sqlite"):
            kw = {"connect_args": {"check_same_thread": False}}
        else:  # a hosted PostgreSQL closes idle connections, so check one before using it
            kw = {"pool_pre_ping": True, "pool_recycle": 1800, **_pool_kw()}
        _engine = create_engine(url, **kw)
        _Session = sessionmaker(_engine, expire_on_commit=False)
        from app.bootstrap import add_missing_columns  # an older database file gets the newer columns on first use

        add_missing_columns(_engine)
    return _engine


def reset_engine() -> None:
    global _engine, _Session
    if _engine is not None:
        _engine.dispose()
    _engine = _Session = None


def session_factory():
    get_engine()
    return _Session


def get_db():
    db = session_factory()()
    try:
        yield db
    finally:
        db.close()
