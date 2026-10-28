"""CAPTCHA check (Cloudflare Turnstile, free). Off unless TURNSTILE_SECRET_KEY is set; the page needs TURNSTILE_SITE_KEY."""
import os

import httpx

from app.core.errors import ApiError

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def enabled() -> bool:
    return bool(os.environ.get("TURNSTILE_SECRET_KEY") and os.environ.get("TURNSTILE_SITE_KEY"))


def site_key() -> str | None:
    return os.environ.get("TURNSTILE_SITE_KEY") if enabled() else None


def require(token: str | None, ip: str | None) -> None:
    """Raise unless the visitor passed the check (or no check is configured)."""
    if not enabled():
        return
    bad = ApiError(400, "captcha_failed", "Please complete the check that proves you are a person, then try again.")
    if not token:
        raise bad
    try:
        r = httpx.post(VERIFY_URL, data={"secret": os.environ["TURNSTILE_SECRET_KEY"], "response": token, **({"remoteip": ip} if ip else {})}, timeout=10)
        ok = bool(r.json().get("success"))
    except Exception:  # noqa: BLE001 - if the check service cannot be reached, fail closed
        raise ApiError(503, "captcha_unavailable", "The check service could not be reached. Try again in a moment.") from None
    if not ok:
        raise bad
