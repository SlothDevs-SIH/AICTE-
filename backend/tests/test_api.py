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


def test_planned_routes_say_so(client, tokens):
    r = client.get(f"{API}/stream", headers=tokens["auditor"])
    assert r.status_code == 501
    assert r.json()["error"]["details"]["planned_phase"]


def test_dashboard_counters_equal_database(client, tokens):
    s = client.get(f"{API}/dashboard/summary", headers=tokens["management"]).json()["counters"]
    with session_factory()() as db:
        rows = list(db.scalars(select(Complaint)))
    today = date.today()
    assert s["total_received"] == len(rows)
    assert s["disposed"] == sum(c.state == "DISPOSED" for c in rows)
    assert s["escalated"] == sum(c.state == "ESCALATED" for c in rows)
    assert s["beyond_timeline"] == sum(bool(c.due_on and c.due_on < today and c.state != "DISPOSED") for c in rows)
    assert s["pending"] == sum(c.state in ("RECEIVED", "ASSIGNED") for c in rows)


def test_unit_officer_dashboard_is_scoped(client, tokens):
    mgmt = client.get(f"{API}/dashboard/summary", headers=tokens["management"]).json()["counters"]["total_received"]
    rb = client.get(f"{API}/dashboard/summary", headers=tokens["officer.rb"]).json()
    assert rb["counters"]["total_received"] < mgmt
    assert "RB" in rb["caption"]


def test_planted_scenarios(client, seeded):
    import json
    from pathlib import Path

    truth = json.loads(Path("data/test_ground_truth.json").read_text(encoding="utf-8"))
    with session_factory()() as db:
        cases = {c.case_id: c for c in db.scalars(select(Complaint))}
        insts = {i.id: i for i in db.scalars(select(Institution))}
        from app.db.models import Overlap

        pairs = {frozenset((o.complaint_a_id, o.complaint_b_id)): o for o in db.scalars(select(Overlap))}
    for s in truth["scenarios"]:
        if s["kind"] == "conflict_pair":
            o = pairs[frozenset(cases[c].id for c in s["cases"])]
            assert o.severity == "CONFLICT"
        if s["kind"] == "decoy":
            c = cases[s["case"]]
            assert c.institution_id is None or insts[c.institution_id].canonical_name != s["must_not_link_to"]


def test_overlap_always_has_receipt_and_label(client, tokens):
    items = client.get(f"{API}/overlaps", headers=tokens["officer.rb"]).json()["items"]
    assert items
    one = client.get(f"{API}/overlaps/{items[0]['id']}", headers=tokens["officer.rb"]).json()
    assert one["receipt"]["layers"]["L4_rules"]["reasons"]
    assert one["label"] == "Potential Overlapping Cases – Coordination Required"


def test_other_unit_detail_is_hidden_but_summary_visible(client, tokens):
    rows = client.get(f"{API}/complaints?unit=PGRC&limit=200", headers=tokens["officer.rb"]).json()["items"]
    unlinked = [r for r in rows if r["overlap_severity"] is None]
    assert unlinked
    d = client.get(f"{API}/complaints/{unlinked[0]['id']}", headers=tokens["officer.rb"]).json()
    assert d["detail_visible"] is False and "description" not in d
    mine = client.get(f"{API}/complaints?unit=RB&limit=1", headers=tokens["officer.rb"]).json()["items"][0]
    d2 = client.get(f"{API}/complaints/{mine['id']}", headers=tokens["officer.rb"]).json()
    assert d2["detail_visible"] is True
    assert "*" in (d2["complainant"]["name"] or "*")  # masked by default


def test_reveal_pii_needs_reason_and_is_audited(client, tokens):
    mine = client.get(f"{API}/complaints?unit=RB&limit=1", headers=tokens["officer.rb"]).json()["items"][0]
    bad = client.post(f"{API}/complaints/{mine['id']}/reveal-pii", json={"reason": "x"}, headers=tokens["officer.rb"])
    assert bad.status_code == 422
    ok = client.post(f"{API}/complaints/{mine['id']}/reveal-pii",
                     json={"reason": "Need to call complainant for clarification"}, headers=tokens["officer.rb"])
    assert ok.status_code == 200 and "*" not in ok.json()["name"]
    with session_factory()() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "PII_REVEALED"))
    assert client.post(f"{API}/complaints/{mine['id']}/reveal-pii", json={"reason": "audit read check ok"},
                       headers=tokens["auditor"]).status_code == 403


def test_role_enforced_on_backend(client, tokens):
    assert client.get(f"{API}/audit", headers=tokens["officer.rb"]).status_code == 403
    assert client.get(f"{API}/audit", headers=tokens["auditor"]).status_code == 200
    body = {"reference_no": "X1", "category_id": "x", "title": "Some title"}
    assert client.post(f"{API}/complaints", json=body, headers=tokens["management"]).status_code == 403


def test_create_complaint_resolves_variant_and_flags_overlap(client, tokens):
    ref = client.get(f"{API}/reference", headers=tokens["officer.rb"]).json()
    cat = ref["categories"][0]["id"]
    # take an institution that currently has an open PGRC case only
    rows = client.get(f"{API}/complaints?unit=PGRC&limit=200", headers=tokens["officer.rb"]).json()["items"]
    target = next(r for r in rows if r["institution_id"] and r["state"] == "UNDER_PROCESS")
    r = client.post(f"{API}/complaints", headers=tokens["officer.rb"], json={
        "reference_no": "RB/TEST/0001", "category_id": cat, "title": "Test complaint at same college",
        "institution_text_raw": target["institution"], "complainant_name": "Test Person"})
    assert r.status_code == 201, r.text
    new = r.json()["complaint"]
    assert new["institution_id"] == target["institution_id"]
    assert r.json()["institution_match"]["status"] == "linked"
    assert new["overlap_severity"] in ("RELATED", "CONFLICT")
    dup = client.post(f"{API}/complaints", headers=tokens["officer.rb"], json={
        "reference_no": "RB/TEST/0001", "category_id": cat, "title": "Again please"})
    assert dup.status_code == 409


def test_lifecycle_rules(client, tokens):
    ref = client.get(f"{API}/reference", headers=tokens["officer.rb"]).json()
    r = client.post(f"{API}/complaints", headers=tokens["officer.rb"], json={
        "reference_no": "RB/TEST/0002", "category_id": ref["categories"][0]["id"], "title": "Lifecycle case"})
    cid = r.json()["complaint"]["id"]
    h = tokens["officer.rb"]
    bad = client.post(f"{API}/complaints/{cid}/transition", json={"to_state": "DISPOSED", "remark": "x"}, headers=h)
    assert bad.status_code == 409 and bad.json()["error"]["code"] == "invalid_transition"
    assert client.post(f"{API}/complaints/{cid}/transition", json={"to_state": "ASSIGNED"}, headers=h).status_code == 200
    assert client.post(f"{API}/complaints/{cid}/remarks", json={"text": "Started examination"}, headers=h).status_code == 201
    row = client.get(f"{API}/complaints/{cid}", headers=h).json()
    assert row["state"] == "UNDER_PROCESS"
    esc = client.post(f"{API}/complaints/{cid}/escalate", json={"level": 2, "reason": ""}, headers=h)
    assert esc.status_code == 422
    esc = client.post(f"{API}/complaints/{cid}/escalate", json={"level": 2, "reason": "No reply received"}, headers=h)
    assert esc.status_code == 200 and esc.json()["state"] == "ESCALATED"
    ev = client.get(f"{API}/complaints/{cid}/events", headers=h).json()["items"]
    assert [e["kind"] for e in ev][0] == "RECEIVED" and "ESCALATED" in [e["kind"] for e in ev]


def test_gate_requires_justification_on_conflict_and_close_is_gated(client, tokens):
    import json
    from pathlib import Path

    truth = json.loads(Path("data/test_ground_truth.json").read_text(encoding="utf-8"))
    pair = next(s for s in truth["scenarios"] if s["kind"] == "conflict_pair")
    with session_factory()() as db:
        pgrc_case = [db.scalar(select(Complaint).where(Complaint.case_id == c)) for c in pair["cases"]]
        from app.db.models import Unit
        pgrc_id = db.scalar(select(Unit).where(Unit.code == "PGRC")).id
        target = next(c for c in pgrc_case if c.unit_id == pgrc_id)
        tid, inst = target.id, target.institution_id
    h = tokens["officer.pgrc"]
    g = client.post(f"{API}/gate/check", json={"complaint_id": tid, "action_type": "CLOSE_CASE"}, headers=h).json()
    assert g["result"] == "CONFLICT" and g["other_cases"]
    short = client.post(f"{API}/gate/{g['check_id']}/decision", json={"choice": "PROCEED", "justification": "ok"}, headers=h)
    assert short.status_code == 422
    # closing before deciding the gate is refused
    blocked = client.post(f"{API}/complaints/{tid}/transition",
                          json={"to_state": "DISPOSED", "remark": "Closing"}, headers=h)
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] in ("gate_required", "invalid_transition")
    done = client.post(f"{API}/gate/{g['check_id']}/decision",
                       json={"choice": "REQUEST_COORDINATION", "justification": "Coordinate with RB first"}, headers=h)
    assert done.status_code == 200


def test_audit_chain_intact_and_tamper_detected(client, tokens):
    assert client.get(f"{API}/audit/verify", headers=tokens["auditor"]).json()["intact"] is True
    with session_factory()() as db:
        row = db.scalar(select(AuditLog).order_by(AuditLog.seq).offset(5).limit(1))
        original = dict(row.payload_json)
        row.payload_json = {**original, "tampered": True}
        db.commit()
        res = verify_chain(db)
        assert res["intact"] is False and res["first_broken_seq"] == row.seq
        row.payload_json = original
        db.commit()
        assert verify_chain(db)["intact"] is True


def test_csv_report_declares_synthetic(client, tokens):
    r = client.get(f"{API}/reports/by_unit?format=csv", headers=tokens["management"])
    assert r.status_code == 200 and r.text.startswith("# SYNTHETIC DATA")


def test_normalize_and_matcher_basics():
    from app.engine.normalize import normalize

    assert normalize("Shri Ramdeo Inst. of Tech., Nagpur") == normalize("SHRI RAMDEO INSTITUTE OF TECHNOLOGY NAGPUR")


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
