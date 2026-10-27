"""Optional language-model adapter. Off unless ANTHROPIC_API_KEY is set AND the admin switch is on.

Every caller must have a deterministic fallback and must validate what comes back.
Not exercised against the real service in this repository (no key was available); the tests use a fake.
"""
import os

import httpx

MODEL = os.environ.get("LLM_MODEL", "claude-haiku-5-5")


def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def complete(system: str, user: str, max_tokens: int = 400) -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": max_tokens, "system": system,
                  "messages": [{"role": "user", "content": user}]},
            timeout=20,
        )
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json().get("content", []))
    except Exception:  # any failure means "use the template"
        return None
