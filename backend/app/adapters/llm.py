"""Optional language-model adapter. Off unless a key is set AND the relevant admin switch is on.

Provider: Google Gemini when GEMINI_API_KEY is set (preferred), otherwise Anthropic when ANTHROPIC_API_KEY is set.
Every caller must have a deterministic fallback and must validate what comes back; any failure returns None.
Not exercised against a real service in this repository (no key was available); the tests use fakes.
"""
import os

import httpx

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def provider() -> str | None:
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def model_name() -> str:
    default = "gemini-3.8-flash" if provider() == "gemini" else "claude-haiku-5-5"
    return os.environ.get("LLM_MODEL", default)


def available() -> bool:
    return provider() is not None


def _gemini(system: str, user: str, max_tokens: int) -> str:
    def call(with_thinking_off: bool) -> httpx.Response:
        config: dict = {"maxOutputTokens": max(max_tokens, 512), "temperature": 0}
        if with_thinking_off:  # no hidden "thinking" tokens, so the short answer is not cut off
            config["thinkingConfig"] = {"thinkingBudget": 0}
        return httpx.post(
            GEMINI_URL.format(model=model_name()),
            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "content-type": "application/json"},
            json={"systemInstruction": {"parts": [{"text": system}]},
                  "contents": [{"role": "user", "parts": [{"text": user}]}], "generationConfig": config},
            timeout=40,
        )

    r = call(True)
    if r.status_code == 400:  # some models do not accept that setting; ask again without it
        r = call(False)
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def _anthropic(system: str, user: str, max_tokens: int) -> str:
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": model_name(), "max_tokens": max_tokens, "system": system,
              "messages": [{"role": "user", "content": user}]},
        timeout=20,
    )
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json().get("content", []))


_last_error: str | None = None


def last_error() -> str | None:
    """Why the most recent call returned nothing (never includes keys or personal data), for the Admin screen."""
    return _last_error


def _describe(exc: Exception) -> str:
    text = type(exc).__name__
    resp = getattr(exc, "response", None)
    if resp is not None:
        text += f" {resp.status_code}: {resp.text[:300]}"
    elif str(exc):
        text += f": {str(exc)[:200]}"
    for k in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        if os.environ.get(k):
            text = text.replace(os.environ[k], "***")
    return text


def complete(system: str, user: str, max_tokens: int = 400) -> str | None:
    global _last_error
    p = provider()
    if not p:
        _last_error = "no model key is set on the server"
        return None
    try:
        out = (_gemini if p == "gemini" else _anthropic)(system, user, max_tokens)
        _last_error = None if out else f"{p} returned an empty answer"
        return out
    except Exception as e:  # any failure means "use the template"
        _last_error = f"{p} ({model_name()}): {_describe(e)}"
        return None
