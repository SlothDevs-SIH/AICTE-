from datetime import date

from sqlalchemy import select

from app.core.audit import verify_chain
from app.db.base import session_factory
from app.db.models import AuditLog, Complaint, Institution

from .conftest import PASSWORD

API = "/api/v1"


def test_health_and_ready(client):
    assert client.get(f"{API}/healthz").json() == {"status": "ok"}
    r = client.get(f"{API}/readyz")
    assert r.status_code == 200 and r.json()["checks"]["database"] == "ok"
    assert "X-Request-ID" in r.headers


def test_unauthenticated_is_401_with_envelope(client):
    r = client.get(f"{API}/complaints")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"
    assert r.json()["error"]["request_id"]


def test_wrong_password_is_generic(client):
    r = client.post(f"{API}/auth/login", json={"email": "officer.rb@demo.samanvay.in", "password": "nope"})
    r2 = client.post(f"{API}/auth/login", json={"email": "ghost@demo.samanvay.in", "password": "nope"})
    assert r.status_code == r2.status_code == 401
    assert r.json()["error"]["message"] == r2.json()["error"]["message"]


def test_refresh_rotates(client):
    r = client.post(f"{API}/auth/login", json={"email": "auditor@demo.samanvay.in", "password": PASSWORD}).json()
    new = client.post(f"{API}/auth/refresh", json={"refresh_token": r["refresh_token"]})
    assert new.status_code == 200
    again = client.post(f"{API}/auth/refresh", json={"refresh_token": r["refresh_token"]})
    assert again.status_code == 401


def test_unmatched_case_can_be_linked_and_alias_is_remembered(client, tokens):
    ref = client.get(f"{API}/reference", headers=tokens["officer.rb"]).json()
    rows = client.get(f"{API}/complaints?unit=PGRC&limit=200", headers=tokens["officer.rb"]).json()["items"]
    target = next(r for r in rows if r["institution_id"])
    odd = "Compltly Diffrent Wrtten Naem Of College"
    made = client.post(f"{API}/complaints", headers=tokens["officer.rb"], json={
        "reference_no": "RB/TEST/0003", "category_id": ref["categories"][0]["id"],
        "title": "Case with an unrecognisable name", "institution_text_raw": odd}).json()
    assert made["complaint"]["institution_id"] is None
    r = client.post(f"{API}/complaints/{made['complaint']['id']}/institution", headers=tokens["officer.rb"],
                    json={"institution_id": target["institution_id"]})
    assert r.status_code == 200 and r.json()["alias_saved"] is True
    again = client.post(f"{API}/complaints/{made['complaint']['id']}/institution", headers=tokens["officer.rb"],
                        json={"institution_id": target["institution_id"]})
    assert again.status_code == 409
    sug = client.get(f"{API}/institutions/suggest?text={odd}", headers=tokens["officer.rb"]).json()["items"]
    assert sug and sug[0]["institution_id"] == target["institution_id"]
