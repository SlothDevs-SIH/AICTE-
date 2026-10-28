"""Self sign-up: e-mail verification, choosing who you are, the portal, and keeping outsiders away from case files."""
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.adapters import mailer
from app.db.base import session_factory
from app.db.models import EmailToken, User

API = "/api/v1"
PW = "Sturdy-pass-2026"


def _email() -> str:
    return f"user.{uuid.uuid4().hex[:8]}@example.org"


def _signup(client, email=None, name="Asha Rao", pw=PW):
    email = email or _email()
    mailer.OUTBOX.clear()
    r = client.post(f"{API}/auth/register", json={"name": name, "email": email, "password": pw})
    return email, r


def _token_from_outbox() -> str:
    m = re.search(r"verify\?token=([\w\-]+)", mailer.OUTBOX[-1]["text"])
    assert m, mailer.OUTBOX[-1]
    return m.group(1)


def _verified(client, email=None):
    email, r = _signup(client, email)
    assert r.status_code == 202, r.text
    assert client.post(f"{API}/auth/verify-email", json={"token": _token_from_outbox()}).status_code == 200
    return email


def _login(client, email, pw=PW):
    r = client.post(f"{API}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_signup_sends_link_and_blocks_login_until_verified(client):
    email, r = _signup(client)
    assert r.status_code == 202 and mailer.OUTBOX and mailer.OUTBOX[-1]["to"] == email
    assert "dev_link" not in r.json()  # no way to read the link from the response
    bad = client.post(f"{API}/auth/login", json={"email": email, "password": PW})
    assert bad.status_code == 403 and bad.json()["error"]["code"] == "email_not_verified"
    wrong = client.post(f"{API}/auth/login", json={"email": email, "password": "not-the-password-1"})
    assert wrong.status_code == 401  # a wrong password never learns whether the address exists
    token = _token_from_outbox()
    ok = client.post(f"{API}/auth/verify-email", json={"token": token})
    assert ok.status_code == 200 and ok.json()["verified"] is True
    again = client.post(f"{API}/auth/verify-email", json={"token": token})
    assert again.status_code == 400  # a link works once
    h = _login(client, email)
    me = client.get(f"{API}/me", headers=h).json()
    assert me["role"] == "new" and me["email_verified"] is True


def test_weak_password_bad_email_and_unknown_token(client):
    assert client.post(f"{API}/auth/register", json={"name": "Asha", "email": _email(), "password": "short1"}).status_code == 422
    assert client.post(f"{API}/auth/register", json={"name": "Asha", "email": _email(), "password": "onlyletterspassword"}).status_code == 422
    assert client.post(f"{API}/auth/register", json={"name": "Asha", "email": "not-an-email", "password": PW}).status_code == 422
    assert client.post(f"{API}/auth/verify-email", json={"token": "x" * 40}).status_code == 400


def test_expired_link_is_refused(client):
    email, _ = _signup(client)
    with session_factory()() as db:
        t = db.scalar(select(EmailToken).join(User, User.id == EmailToken.user_id).where(User.email == email))
        t.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    assert client.post(f"{API}/auth/verify-email", json={"token": _token_from_outbox()}).status_code == 400


def test_existing_address_gets_the_same_answer_and_no_mail(client):
    email = _verified(client)
    mailer.OUTBOX.clear()
    r = client.post(f"{API}/auth/register", json={"name": "Someone Else", "email": email, "password": "Another-pass-77"})
    assert r.status_code == 202 and not mailer.OUTBOX
    assert "email_sent" not in r.json()
    _login(client, email)  # the original password still works


def test_resend_is_throttled(client):
    email, _ = _signup(client)
    r = client.post(f"{API}/auth/resend-verification", json={"email": email})
    assert r.status_code == 429
    assert client.post(f"{API}/auth/resend-verification", json={"email": "nobody@example.org"}).status_code == 202


def test_dev_link_only_when_explicitly_allowed(client, monkeypatch):
    monkeypatch.setenv("DEV_SHOW_VERIFY_LINK", "true")
    _, r = _signup(client)
    assert "verify?token=" in r.json().get("dev_link", "")


def test_admin_emails_list_makes_an_administrator(client, monkeypatch):
    email = _email()
    monkeypatch.setenv("ADMIN_EMAILS", f"someone@else.org, {email.upper()}")
    _verified(client, email)
    assert client.get(f"{API}/me", headers=_login(client, email)).json()["role"] == "admin"


def test_new_users_and_outsiders_cannot_read_case_files(client):
    email = _verified(client)
    h = _login(client, email)
    for path in ("/complaints", "/dashboard/summary", "/dashboard/by-institution", "/overlaps", "/audit", "/reports/status",
                 "/coordination", "/risk/ranking", "/notifications/../clusters", "/escalations", "/admin/users", "/admin/role-requests"):
        assert client.get(f"{API}{path}", headers=h).status_code == 403, path
    assert client.post(f"{API}/complaints", json={}, headers=h).status_code == 403
    assert client.get(f"{API}/institutions?q=college", headers=h).status_code == 200  # the public college list
    assert client.get(f"{API}/reference", headers=h).status_code == 200
    # once they are complainants it is still closed
    assert client.post(f"{API}/me/role", json={"account_type": "complainant"}, headers=h).status_code == 200
    assert client.get(f"{API}/complaints", headers=h).status_code == 403
    assert client.get(f"{API}/stream?max_events=1", headers=h).status_code == 403


def test_complainant_files_and_tracks_their_own_complaint(client, tokens):
    a, b = _verified(client), _verified(client)
    ha, hb = _login(client, a), _login(client, b)
    for h in (ha, hb):
        assert client.post(f"{API}/me/role", json={"account_type": "complainant"}, headers=h).json()["role"] == "complainant"
    assert client.post(f"{API}/me/role", json={"account_type": "staff", "role": "unit_officer"}, headers=ha).status_code == 409
    ref = client.get(f"{API}/reference", headers=ha).json()
    inst = client.get(f"{API}/institutions?limit=1", headers=ha).json()["items"][0]
    body = {"title": "Hostel deposit not returned", "description": "I left the college in June and the deposit is still held.",
            "category_id": ref["categories"][0]["id"], "institution_id": inst["id"]}
    r = client.post(f"{API}/portal/complaints", json=body, headers=ha)
    assert r.status_code == 201, r.text
    mine = r.json()
    assert mine["case_id"].startswith("SMV-") and mine["status"] == "Received"
    assert [x["id"] for x in client.get(f"{API}/portal/my/complaints", headers=ha).json()["items"]] == [mine["id"]]
    assert client.get(f"{API}/portal/my/complaints", headers=hb).json()["items"] == []
    assert client.get(f"{API}/portal/my/complaints/{mine['id']}", headers=hb).status_code == 404  # someone else's
    detail = client.get(f"{API}/portal/my/complaints/{mine['id']}", headers=ha).json()
    assert detail["description"].startswith("I left") and detail["timeline"] and "remark" not in str(detail["timeline"])
    # the officers of the Grievance Cell see it, flagged as a real submission
    seen = client.get(f"{API}/complaints?q=Hostel deposit not returned", headers=tokens["officer.pgrc"]).json()
    assert any(c["case_id"] == mine["case_id"] for c in seen["items"])
    assert client.post(f"{API}/portal/complaints", json={**body, "institution_id": None}, headers=ha).status_code == 422
    # staff accounts have no portal
    assert client.get(f"{API}/portal/my/complaints", headers=tokens["officer.pgrc"]).status_code == 403


def test_staff_request_waits_for_an_administrator(client, tokens):
    email = _verified(client)
    h = _login(client, email)
    assert client.post(f"{API}/me/role", json={"account_type": "staff", "role": "admin"}, headers=h).status_code == 422
    assert client.post(f"{API}/me/role", json={"account_type": "staff", "role": "unit_officer"}, headers=h).status_code == 422  # no unit
    r = client.post(f"{API}/me/role", json={"account_type": "staff", "role": "unit_officer", "unit_code": "RB", "note": "RB desk"}, headers=h)
    assert r.status_code == 200 and r.json()["role"] == "pending" and r.json()["request"]["status"] == "pending"
    assert client.get(f"{API}/complaints", headers=h).status_code == 403  # still locked out
    ids = [x["user_id"] for x in client.get(f"{API}/admin/role-requests", headers=tokens["admin"]).json()["items"]]
    uid = client.get(f"{API}/me", headers=h).json()["id"]
    assert uid in ids
    assert client.get(f"{API}/admin/role-requests", headers=tokens["officer.rb"]).status_code == 403
    ok = client.post(f"{API}/admin/role-requests/{uid}/approve", json={}, headers=tokens["admin"])
    assert ok.status_code == 200 and ok.json()["role"] == "unit_officer"
    me = client.get(f"{API}/me", headers=h).json()
    assert me["role"] == "unit_officer" and me["unit_id"] and me["request"] is None
    assert client.get(f"{API}/complaints", headers=h).status_code == 200  # the same login now opens the files
    assert client.post(f"{API}/admin/role-requests/{uid}/approve", json={}, headers=tokens["admin"]).status_code == 404


def test_rejected_request_can_be_made_again(client, tokens):
    email = _verified(client)
    h = _login(client, email)
    client.post(f"{API}/me/role", json={"account_type": "staff", "role": "auditor"}, headers=h)
    uid = client.get(f"{API}/me", headers=h).json()["id"]
    assert client.post(f"{API}/admin/role-requests/{uid}/reject", json={"reason": "x"}, headers=tokens["admin"]).status_code == 422
    assert client.post(f"{API}/admin/role-requests/{uid}/reject", json={"reason": "Not on the auditors list"}, headers=tokens["admin"]).status_code == 200
    me = client.get(f"{API}/me", headers=h).json()
    assert me["role"] == "new" and me["request"]["status"] == "rejected" and "auditors" in me["request"]["reason"]
    assert client.post(f"{API}/me/role", json={"account_type": "complainant"}, headers=h).json()["role"] == "complainant"


def test_institution_representative_sees_counts_not_details(client, tokens):
    email = _verified(client)
    h = _login(client, email)
    with session_factory()() as db:
        from app.db.models import Complaint
        c = db.scalars(select(Complaint).where(Complaint.institution_id.is_not(None))).first()
        inst_id = c.institution_id
    assert client.post(f"{API}/me/role", json={"account_type": "institution"}, headers=h).status_code == 422
    assert client.post(f"{API}/me/role", json={"account_type": "institution", "institution_id": inst_id}, headers=h).json()["role"] == "pending"
    uid = client.get(f"{API}/me", headers=h).json()["id"]
    assert client.get(f"{API}/portal/institution/complaints", headers=h).status_code == 403  # not approved yet
    assert client.post(f"{API}/admin/role-requests/{uid}/approve", json={}, headers=tokens["admin"]).json()["role"] == "institution_rep"
    out = client.get(f"{API}/portal/institution/complaints", headers=h).json()
    assert out["items"] and out["open"] + out["closed"] <= len(out["items"])
    assert set(out["items"][0]) == {"case_id", "category", "state", "status", "received_on", "expected_disposal_on"}
    assert client.get(f"{API}/me", headers=h).json()["institution_name"]


def test_mail_failure_never_breaks_sign_up(client, monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "key-for-test")
    from app.adapters import mailer as m

    def boom(*a, **k):
        raise RuntimeError("network down key-for-test")

    monkeypatch.setattr(m.httpx, "post", boom)
    _, r = _signup(client)
    assert r.status_code == 202 and r.json()["email_sent"] is False
    assert "key-for-test" not in str(r.json())  # the key never appears in an answer


@pytest.mark.parametrize("env,url", [("BREVO_API_KEY", "api.brevo.com"), ("RESEND_API_KEY", "api.resend.com")])
def test_mail_providers_get_the_right_request(client, monkeypatch, env, url):
    monkeypatch.setenv(env, "k-123")
    monkeypatch.setenv("MAIL_FROM", "sender@example.org")
    from app.adapters import mailer as m
    seen = {}

    class Resp:
        status_code = 200
        text = ""
        def raise_for_status(self): pass

    def fake(u, headers=None, json=None, timeout=None):
        seen.update(url=u, headers=headers, body=json)
        return Resp()

    monkeypatch.setattr(m.httpx, "post", fake)
    res = m.send("to@example.org", "Subject", "Body text")
    assert res["sent"] is True and url in seen["url"]
    assert "to@example.org" in str(seen["body"]) and "sender@example.org" in str(seen["body"])


@pytest.fixture(autouse=True)
def _keep_shared_data_synthetic():
    """Portal complaints are real data by design; mark them synthetic again so later tests (scenario loading) still run."""
    yield
    from app.db.models import Complaint
    with session_factory()() as db:
        for c in db.scalars(select(Complaint).where(Complaint.source == "portal")):
            c.is_synthetic = True
        db.commit()
