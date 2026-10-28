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
    default = "gemini-2.5-flash" if provider() == "gemini" else "claude-haiku-5-5"
    return os.environ.get("LLM_MODEL", default)


def available() -> bool:
    return provider() is not None


def _gemini(system: str, user: str, max_tokens: int) -> str:
    r = httpx.post(
        GEMINI_URL.format(model=model_name()),
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "content-type": "application/json"},
        json={"systemInstruction": {"parts": [{"text": system}]},
              "contents": [{"role": "user", "parts": [{"text": user}]}],
              # no hidden "thinking" tokens, so the short answer is not cut off
              "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0,
                                   "thinkingConfig": {"thinkingBudget": 0}}},
        timeout=25,
    )
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


def complete(system: str, user: str, max_tokens: int = 400) -> str | None:
    p = provider()
    if not p:
        return None
    try:
        return (_gemini if p == "gemini" else _anthropic)(system, user, max_tokens)
    except Exception:  # any failure means "use the template"
        return None
