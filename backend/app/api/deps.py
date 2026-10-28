import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.db.base import get_db
from app.db.models import User


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise ApiError(401, "unauthenticated", "Sign in required.")
    try:
        payload = decode_access_token(auth[7:])
    except jwt.PyJWTError:
        raise ApiError(401, "invalid_token", "Token is invalid or expired.") from None
    user = db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise ApiError(401, "unauthenticated", "Account not available.")
    return user


def staff_user(user: User = Depends(current_user)) -> User:
    """AICTE staff only. People who signed up as complainants, institution representatives or have not chosen yet
    can reach their own pages, never the case files."""
    from app.core.roles import ALL_ROLES

    if user.role not in ALL_ROLES:
        raise ApiError(403, "forbidden", "This area is for AICTE staff.")
    return user


def require(*roles: str):
    """Dependency factory: the backend enforces roles; the UI only hides what a role cannot use."""

    def dep(user: User = Depends(current_user)) -> User:
        if roles and user.role not in roles:
            raise ApiError(403, "forbidden", "Your role cannot do this.")
        return user

    return dep
