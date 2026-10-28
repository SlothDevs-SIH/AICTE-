import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-0123")
os.environ.setdefault("PII_ENCRYPTION_KEY", "test-pii-key")
os.environ["DATABASE_URL"] = "sqlite:///./data/test.db"

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base, get_engine, reset_engine, session_factory
from app.main import app

PASSWORD = "Demo@12345"


@pytest.fixture(scope="session")
def seeded():
    from pathlib import Path

    import app.db.models  # noqa: F401
    from app import seed

    Path("data").mkdir(exist_ok=True)
    reset_engine()
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with session_factory()() as db:
        seed.seed(db, 42, Path("data/test_ground_truth.json"))
    yield
    reset_engine()


@pytest.fixture(scope="session")
def client(seeded):
    return TestClient(app)


def login(client, who: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"email": f"{who}@demo.samanvay.in", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def tokens(client):
    return {w: login(client, w) for w in (
        "officer.rb", "officer.pgrc", "supervisor.rb", "management", "authority", "admin", "auditor", "regional.west")}


@pytest.fixture(autouse=True)
def _no_real_model(monkeypatch):
    """Tests never call a real model, whatever keys the machine has; a test that needs a key sets its own."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
