from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import (
    hash_refresh,
    make_access_token,
    new_refresh_token,
    verify_password,
)
from app.db.base import get_db
from app.db.models import RefreshToken, User

router = APIRouter(tags=["auth"])
MAX_FAILS = 5
LOCK_MINUTES = 15


class LoginIn(BaseModel):
    email: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _issue(db: Session, user: User) -> dict:
    s = get_settings()
    raw, h = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=h,
            expires_at=datetime.now(UTC) + timedelta(days=s.refresh_token_days),
        )
    )
    db.commit()
    return {
        "access_token": make_access_token(user.id, user.role),
        "refresh_token": raw,
        "token_type": "bearer",
        "expires_in": s.access_token_minutes * 60,
    }


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    bad = ApiError(401, "invalid_credentials", "Email or password is incorrect.")
    if user is None or not user.is_active:
        raise bad
    now = datetime.now(UTC)
    if user.locked_until and _aware(user.locked_until) > now:
        raise ApiError(423, "account_locked", "Too many failed attempts. Try again later.")
    if not verify_password(body.password, user.password_hash):
        user.failed_logins += 1
        if user.failed_logins >= MAX_FAILS:
            user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            user.failed_logins = 0
        db.commit()
        raise bad
    user.failed_logins, user.locked_until = 0, None
    return _issue(db, user)


def _find_refresh(db: Session, raw: str) -> RefreshToken | None:
    return db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh(raw)))


@router.post("/auth/refresh")
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    row = _find_refresh(db, body.refresh_token)
    if row is None or row.revoked or _aware(row.expires_at) < datetime.now(UTC):
        raise ApiError(401, "invalid_token", "Refresh token is invalid or expired.")
    row.revoked = True  # rotate on every use
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise ApiError(401, "unauthenticated", "Account not available.")
    return _issue(db, user)


@router.post("/auth/logout", status_code=204)
def logout(body: RefreshIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    row = _find_refresh(db, body.refresh_token)
    if row:
        row.revoked = True
        db.commit()


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "unit_id": user.unit_id,
        "region_id": user.region_id,
    }
