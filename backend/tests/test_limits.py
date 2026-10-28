"""Sign-up limits and the CAPTCHA check."""
import uuid

import pytest

from app.adapters import captcha
from app.core import ratelimit

API = "/api/v1"
PW = "Sturdy-pass-2026"


@pytest.fixture(autouse=True)
def _limits_on(monkeypatch):
    monkeypatch.setenv("RATE_LIMITS", "on")
    ratelimit.reset()
    yield
    ratelimit.reset()


def _reg(client, email=None, **extra):
    return client.post(f"{API}/auth/register", json={"name": "Asha Rao", "email": email or f"u.{uuid.uuid4().hex[:8]}@example.org", "password": PW, **extra})


def test_one_network_cannot_sign_up_endlessly(client):
    codes = [_reg(client).status_code for _ in range(12)]
    assert codes[:10] == [202] * 10 and codes[10:] == [429, 429]
    r = _reg(client)
    assert r.json()["error"]["code"] == "rate_limited" and "Try again" in r.json()["error"]["message"]


def test_one_address_cannot_be_hammered(client):
    email = f"same.{uuid.uuid4().hex[:6]}@example.org"
    codes = [_reg(client, email).status_code for _ in range(6)]
    assert codes == [202, 202, 202, 202, 429, 429]


def test_forgot_password_and_login_are_limited(client):
    codes = [client.post(f"{API}/auth/forgot-password", json={"email": f"x{i}@example.org"}).status_code for i in range(12)]
    assert codes[-1] == 429 and codes[0] == 202
    ratelimit.reset()
    bad = [client.post(f"{API}/auth/login", json={"email": "nobody@example.org", "password": "wrong-password-1"}).status_code for _ in range(42)]
    assert bad[0] == 401 and bad[-1] == 429


def test_the_forwarded_address_is_the_one_the_proxy_added(client):
    for _ in range(10):
        assert client.post(f"{API}/auth/register", json={"name": "Asha Rao", "email": f"u.{uuid.uuid4().hex[:8]}@example.org", "password": PW}, headers={"x-forwarded-for": "9.9.9.9, 10.0.0.1"}).status_code == 202
    other = client.post(f"{API}/auth/register", json={"name": "Asha Rao", "email": f"u.{uuid.uuid4().hex[:8]}@example.org", "password": PW}, headers={"x-forwarded-for": "9.9.9.9, 10.0.0.2"})
    assert other.status_code == 202  # a different last hop is a different caller; the first entry is client-supplied and ignored


def test_captcha_is_checked_only_when_configured(client, monkeypatch):
    assert client.get(f"{API}/public/config").json() == {"captcha": None}
    assert _reg(client).status_code == 202
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "secret-for-test")
    monkeypatch.setenv("TURNSTILE_SITE_KEY", "site-key-for-test")
    cfg = client.get(f"{API}/public/config").json()["captcha"]
    assert cfg == {"provider": "turnstile", "site_key": "site-key-for-test"} and "secret" not in str(cfg)
    assert _reg(client).json()["error"]["code"] == "captcha_failed"  # no token

    seen = {}

    class Resp:
        def __init__(self, ok): self.ok = ok
        def json(self): return {"success": self.ok}

    def fake(url, data=None, timeout=None):
        seen.update(url=url, data=data)
        return Resp(data["response"] == "good-token")

    monkeypatch.setattr(captcha.httpx, "post", fake)
    assert _reg(client, captcha_token="bad-token").status_code == 400
    ok = _reg(client, captcha_token="good-token")
    assert ok.status_code == 202 and seen["url"].endswith("/siteverify") and seen["data"]["secret"] == "secret-for-test"
    forgot = client.post(f"{API}/auth/forgot-password", json={"email": "a@example.org"})
    assert forgot.status_code == 400
    assert client.post(f"{API}/auth/forgot-password", json={"email": "a@example.org", "captcha_token": "good-token"}).status_code == 202


def test_captcha_fails_closed_when_the_service_is_down(client, monkeypatch):
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "s")
    monkeypatch.setenv("TURNSTILE_SITE_KEY", "k")

    def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(captcha.httpx, "post", boom)
    assert _reg(client, captcha_token="anything").status_code == 503
