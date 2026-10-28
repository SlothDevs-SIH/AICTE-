"""Every read endpoint, as every kind of user: nothing may crash (5xx), and the protected ones must stay protected."""
import re

import pytest
from sqlalchemy import select

from app.db.base import session_factory
from app.db.models import Complaint, CoordinationThread, Institution, InstitutionAlias, Overlap
from app.main import app

API = "/api/v1"
ROLES = ["officer.rb", "officer.pgrc", "supervisor.rb", "management", "authority", "admin", "auditor", "regional.west"]


def _ids():
    with session_factory()() as db:
        c = db.scalars(select(Complaint)).first()
        ov = db.scalars(select(Overlap)).first()
        th = db.scalars(select(CoordinationThread)).first()
        inst = db.scalars(select(Institution)).first()
        al = db.scalars(select(InstitutionAlias)).first()
        return {"cid": c.id, "oid": ov.id if ov else "x", "tid": th.id if th else "x", "iid": inst.id, "jid": "x",
                "nid": "x", "kind": "status", "alias_id": al.id if al else "x", "uid": "x", "sid": "x", "key": "auto_escalate",
                "check_id": "x", "feature": "llm", "path": "x"}


def _get_routes():
    out = []
    for path, ops in app.openapi()["paths"].items():
        if "get" in ops and not path.endswith("/brief.pdf") and path != f"{API}/stream" and "/docs" not in path:
            out.append(path)
    return sorted(out)


@pytest.mark.parametrize("who", ROLES)
def test_no_read_endpoint_crashes_for_any_staff_role(client, tokens, who):
    ids = _ids()
    bad = []
    for path in _get_routes():
        url = re.sub(r"\{(\w+)\}", lambda m: ids.get(m.group(1), "x"), path)
        r = client.get(url, headers=tokens[who])
        if r.status_code >= 500:
            bad.append((path, r.status_code, r.text[:120]))
    assert not bad, bad


def test_every_read_endpoint_refuses_anonymous_visitors(client):
    ids = _ids()
    open_paths = {f"{API}/healthz", f"{API}/readyz", f"{API}/public/overview", f"{API}/public/config"}
    leaks = []
    for path in _get_routes():
        if path in open_paths or not path.startswith(API):
            continue
        url = re.sub(r"\{(\w+)\}", lambda m: ids.get(m.group(1), "x"), path)
        if client.get(url).status_code != 401:
            leaks.append(path)
    assert not leaks, leaks


def test_public_overview_has_no_personal_data(client):
    body = client.get(f"{API}/public/overview").json()
    text = str(body).lower()
    assert "@" not in text and "password" not in text and "phone" not in text
