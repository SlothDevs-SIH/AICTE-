"""Small in-memory request limits for sign-up, sign-in and password reset.

Counts live in this process only: they reset when the server restarts and are not shared between several servers. That is
enough to slow down a script on a single small deployment; a larger one would need a shared store.
"""
import os
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.errors import ApiError

_hits: dict[str, deque] = defaultdict(deque)


def enabled() -> bool:
    return os.environ.get("RATE_LIMITS", "on").lower() not in ("off", "0", "false", "no")


def client_ip(request: Request) -> str:
    """The caller's address. Behind a host's proxy the last X-Forwarded-For entry is the one the proxy added."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def reset() -> None:
    _hits.clear()


def check(key: str, limit: int, window_seconds: int, what: str = "attempts") -> None:
    """Count one hit for `key`; refuse when more than `limit` happened in the last `window_seconds`."""
    if not enabled():
        return
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > window_seconds:
        q.popleft()
    if len(q) >= limit:
        wait = int(window_seconds - (now - q[0])) + 1
        raise ApiError(429, "rate_limited", f"Too many {what}. Try again in about {max(1, wait // 60)} minute(s).")
    q.append(now)
