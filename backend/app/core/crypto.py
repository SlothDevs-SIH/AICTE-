"""Field encryption and masking for personal data (BACKEND_PLAN 3.6, 9.3)."""
import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().pii_encryption_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str | None) -> str | None:
    return _fernet().encrypt(value.encode()).decode() if value else None


def decrypt(token: str | None) -> str | None:
    return _fernet().decrypt(token.encode()).decode() if token else None


def mask_name(v: str | None) -> str | None:
    if not v:
        return None
    return " ".join(p[0] + "*" * (len(p) - 1) for p in v.split())


def mask_phone(v: str | None) -> str | None:
    return None if not v else "*" * (len(v) - 3) + v[-3:]


def mask_email(v: str | None) -> str | None:
    if not v or "@" not in v:
        return None
    user, dom = v.split("@", 1)
    return user[0] + "***@" + dom
