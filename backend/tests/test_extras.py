import io
from datetime import date, timedelta

from sqlalchemy import select

from app.db.base import session_factory
from app.db.models import Complaint, Notification, Overlap, Unit

API = "/api/v1"


def _two_unit_pair(client, tokens):
    """An institution where RB and PGRC both have open cases (from the seed)."""
    items = client.get(f"{API}/overlaps?status=SUGGESTED", headers=tokens["officer.rb"]).json()["items"]
    o = next(i for i in items if i["severity"] == "RELATED")
    return o


def test_stream_sends_counters_and_heartbeat(client, tokens):
    r = client.get(f"{API}/stream?max_events=2", headers=tokens["management"])
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    assert "event: counters_changed" in r.text and "event: heartbeat" in r.text


def test_sla_job_creates_alerts_and_respects_advisory_escalation(client, tokens):
    r = client.post(f"{API}/admin/jobs/sla", headers=tokens["admin"])
    assert r.status_code == 200
    stats = r.json()
    assert stats["sla_breached"] > 0
    assert stats["auto_escalated"] == 0  # advisory by default
    mine = client.get(f"{API}/notifications", headers=tokens["officer.rb"]).json()
    assert mine["items"] and any(n["kind"] in ("SLA_BREACHED", "REMINDER", "SLA_APPROACHING") for n in mine["items"])
    # running again does not duplicate (dedupe)
    again = client.post(f"{API}/admin/jobs/sla", headers=tokens["admin"]).json()
    assert again["sla_breached"] == 0
    nid = mine["items"][0]["id"]
    assert client.post(f"{API}/notifications/{nid}/read", headers=tokens["officer.rb"]).status_code == 200
    assert client.post(f"{API}/notifications/{nid}/read", headers=tokens["officer.pgrc"]).status_code == 404


def test_alert_budget_caps_non_conflict_alerts(client, tokens):
    from app.services.notifications import notify
    with session_factory()() as db:
        uid = db.scalar(select(Complaint.owner_user_id).where(Complaint.owner_user_id.is_not(None)).limit(1))
        before = db.query(Notification).filter(Notification.user_id == uid).count()
        for i in range(60):
            notify(db, uid, "REMINDER", "complaint", f"budget-{i}", "x")
        db.flush()
        added = db.query(Notification).filter(Notification.user_id == uid).count() - before
        assert added <= 20
        c = notify(db, uid, "CONFLICT", "complaint", "budget-conflict", "never suppressed")
        assert c is not None
        db.rollback()


def test_auto_escalation_off_by_default_and_audited_when_on(client, tokens):
    s = client.get(f"{API}/admin/settings", headers=tokens["admin"]).json()["items"]
    assert s["auto_escalate"] is False
    bad = client.put(f"{API}/admin/settings/auto_escalate", json={"value": "yes"}, headers=tokens["admin"])
    assert bad.status_code == 422
    assert client.put(f"{API}/admin/settings/auto_escalate", json={"value": True}, headers=tokens["officer.rb"]).status_code == 403
    assert client.put(f"{API}/admin/settings/auto_escalate", json={"value": True}, headers=tokens["admin"]).status_code == 200
    stats = client.post(f"{API}/admin/jobs/sla", headers=tokens["admin"]).json()
    assert stats["auto_escalated"] >= 0
    audit = client.get(f"{API}/audit?action=SETTING_CHANGED", headers=tokens["auditor"]).json()["items"]
    assert audit
    if stats["auto_escalated"]:
        assert client.get(f"{API}/audit?action=AUTO_ESCALATED", headers=tokens["auditor"]).json()["items"]
    client.put(f"{API}/admin/settings/auto_escalate", json={"value": False}, headers=tokens["admin"])


def test_coordination_handshake_two_users(client, tokens):
    o = _two_unit_pair(client, tokens)
    ids = [o["a"]["id"], o["b"]["id"]]
    opened = client.post(f"{API}/coordination", headers=tokens["officer.rb"],
                         json={"complaint_ids": ids, "message": "Please hold your notice, we have one pending."})
    assert opened.status_code == 201, opened.text
    tid = opened.json()["id"]
    # the other unit is notified and can read the thread and the cases
    theirs = client.get(f"{API}/coordination/{tid}", headers=tokens["officer.pgrc"])
    assert theirs.status_code == 200 and len(theirs.json()["messages"]) == 1
    other_case = next(c for c in (o["a"], o["b"]) if c["unit"] == "RB")
    assert client.get(f"{API}/complaints/{other_case['id']}", headers=tokens["officer.pgrc"]).json()["detail_visible"] is True
    note = client.post(f"{API}/coordination/{tid}/messages", json={"body": "Agreed, we will wait."}, headers=tokens["officer.pgrc"])
    assert note.status_code == 201 and len(note.json()["messages"]) == 2
    # a unit outside the thread cannot read or post
    assert client.get(f"{API}/coordination/{tid}", headers=tokens["regional.west"]).status_code == 404
    assert client.post(f"{API}/coordination/{tid}/messages", json={"body": "hi"}, headers=tokens["regional.west"]).status_code == 404
    res = client.post(f"{API}/coordination/{tid}/resolve", headers=tokens["officer.pgrc"],
                      json={"outcome": "PROCEED_TOGETHER", "note": "Joint notice to be issued by RB"})
    assert res.status_code == 200 and res.json()["status"] == "RESOLVED"
    assert client.post(f"{API}/coordination/{tid}/messages", json={"body": "late"}, headers=tokens["officer.rb"]).status_code == 409
    with session_factory()() as db:
        assert not db.get(Complaint, ids[0]).on_hold_for_coordination
    # same-unit cases cannot open a thread
    same = client.get(f"{API}/complaints?unit=RB&limit=2", headers=tokens["officer.rb"]).json()["items"]
    assert client.post(f"{API}/coordination", headers=tokens["officer.rb"],
                       json={"complaint_ids": [same[0]["id"], same[1]["id"]], "message": "x y z"}).status_code == 422


def test_coordination_expiry_alerts_supervisor(client, tokens):
    from datetime import UTC, datetime
    from app.db.models import CoordinationThread
    items = client.get(f"{API}/overlaps?status=SUGGESTED", headers=tokens["officer.rb"]).json()["items"]
    o = next(i for i in items if i["id"] and i["a"]["id"] and not _held(i))
    t = client.post(f"{API}/coordination", headers=tokens["officer.rb"],
                    json={"complaint_ids": [o["a"]["id"], o["b"]["id"]], "message": "Need to talk about this"}).json()
    with session_factory()() as db:
        row = db.get(CoordinationThread, t["id"])
        row.due_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()
    stats = client.post(f"{API}/admin/jobs/sla", headers=tokens["admin"]).json()
    assert stats["threads_expired"] >= 1
    assert client.get(f"{API}/coordination/{t['id']}", headers=tokens["officer.rb"]).json()["status"] == "EXPIRED"


def _held(o):
    with session_factory()() as db:
        return db.get(Complaint, o["a"]["id"]).on_hold_for_coordination or db.get(Complaint, o["b"]["id"]).on_hold_for_coordination


def test_risk_components_and_fairness(client, tokens):
    r = client.get(f"{API}/risk/ranking?limit=100", headers=tokens["management"]).json()
    assert r["note"].startswith("Score is a ranking aid")
    top = r["items"][0]
    assert {c["name"] for c in top["components"]} == {"volume", "ageing", "multi_unit", "repeat", "severity", "open_conflicts", "trend"}
    assert abs(sum(c["points"] for c in top["components"]) - top["score"]) < 0.5
    assert client.get(f"{API}/risk/ranking", headers=tokens["officer.rb"]).status_code == 403
    # fairness: score uses no size or name; a small institution with old conflicting cases can outrank a big one
    from app.services.intelligence import risk_score
    from app.db.models import Institution, Category
    with session_factory()() as db:
        cat = db.scalar(select(Category))
        units = [u.id for u in db.scalars(select(Unit))][:2]
        big = Institution(canonical_name="Fairness Big College", normalized_name="fairness big college", is_synthetic=True)
        small = Institution(canonical_name="Fairness Small College", normalized_name="fairness small college", is_synthetic=True)
        db.add_all([big, small]); db.flush()
        for i in range(8):
            db.add(Complaint(case_id=f"FAIR-B-{i}", reference_no=f"FB{i}", unit_id=units[0], institution_id=big.id, category_id=cat.id,
                             title="t", received_on=date.today() - timedelta(days=5), state="UNDER_PROCESS", is_synthetic=True))
        for i, u in enumerate(units):
            db.add(Complaint(case_id=f"FAIR-S-{i}", reference_no=f"FS{i}", unit_id=u, institution_id=small.id, category_id=cat.id,
                             title="t", received_on=date.today() - timedelta(days=170), state="UNDER_PROCESS", is_synthetic=True))
        db.flush()
        a, b = db.scalars(select(Complaint).where(Complaint.institution_id == small.id)).all()
        a.last_action_text = "Show-cause notice issued"
        from app.engine.overlap import scan_complaint
        scan_complaint(db, a)
        db.flush()
        assert risk_score(db, small)["score"] > risk_score(db, big)["score"]
        db.rollback()


def test_clusters_found(client, tokens):
    items = client.get(f"{API}/clusters", headers=tokens["management"]).json()["items"]
    for c in items:
        assert c["size"] >= 3 and c["label"].startswith(f"{c['size']} similar complaints in ")


def test_ask_returns_filters_only(client, tokens):
    r = client.post(f"{API}/ask", json={"question": "overdue PGRC cases older than 60 days"}, headers=tokens["management"]).json()
    f = r["parsed_filters"]
    assert f["unit"] == "PGRC" and f["overdue"] == "true" and f["older_than_days"] == 60
    assert r["used_ai"] is False
    bad = client.post(f"{API}/ask", json={"question": "'; DROP TABLE users; --"}, headers=tokens["management"]).json()
    assert bad["needs_manual_filters"] is True
    from app.services.ask import validate
    with session_factory()() as db:
        assert validate(db, {"unit": "XX", "state": "UNDER_PROCESS", "sql": "drop", "region": "ZZ"}) == {"state": "UNDER_PROCESS"}


def test_summary_template_and_llm_guard(client, tokens, monkeypatch):
    o = _two_unit_pair(client, tokens)
    off = client.post(f"{API}/overlaps/{o['id']}/summary", headers=tokens["officer.rb"]).json()
    assert off["kind"] == "Template summary" and o["a"]["case_id"] in off["text"]
    assert client.put(f"{API}/admin/settings/ai_llm_enabled", json={"value": True}, headers=tokens["admin"]).status_code == 200
    from app.adapters import llm
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "complete", lambda s, u, max_tokens=400: "This is fraud by SMV-2026-999999 over 777 days.")
    bad = client.post(f"{API}/overlaps/{o['id']}/summary", headers=tokens["officer.rb"]).json()
    assert bad["kind"] == "Template summary" and "did not pass" in bad["reason"]
    good_text = f"Two units hold open cases at this college. See {o['a']['case_id']} and {o['b']['case_id']} before acting."
    monkeypatch.setattr(llm, "complete", lambda s, u, max_tokens=400: good_text)
    ok = client.post(f"{API}/overlaps/{o['id']}/summary", headers=tokens["officer.rb"]).json()
    assert ok["kind"] == "AI-written" and ok["text"] == good_text
    monkeypatch.setattr(llm, "complete", lambda s, u, max_tokens=400: None)
    assert client.post(f"{API}/overlaps/{o['id']}/summary", headers=tokens["officer.rb"]).json()["kind"] == "Template summary"
    client.put(f"{API}/admin/settings/ai_llm_enabled", json={"value": False}, headers=tokens["admin"])


def test_brief_pdf(client, tokens):
    o = _two_unit_pair(client, tokens)
    r = client.get(f"{API}/overlaps/{o['id']}/brief.pdf", headers=tokens["officer.rb"])
    assert r.status_code == 200 and r.content.startswith(b"%PDF") and r.headers["content-type"] == "application/pdf"
    assert client.get(f"{API}/overlaps/{o['id']}/brief.pdf", headers=tokens["auditor"]).status_code == 403


CSV = (
    "Ref,Subject,Details,Type,College,Received\n"
    "IMP-001,Refund pending,Fees not returned,Fee refund,{inst},2026-09-01\n"
    "IMP-002,No category,,Nonsense type,{inst},2026-09-02\n"
    ",Missing ref,,Fee refund,{inst},2026-09-03\n"
    "IMP-004,Bad date,,Fee refund,{inst},31/31/2026\n"
    "IMP-001,Duplicate in file,,Fee refund,{inst},2026-09-05\n"
)


def test_import_wizard_reports_bad_rows_and_commit_is_idempotent(client, tokens):
    rows = client.get(f"{API}/complaints?unit=PGRC&limit=200", headers=tokens["officer.rb"]).json()["items"]
    inst = next(r["institution"] for r in rows if r["institution_id"] and r["state"] == "UNDER_PROCESS")
    data = CSV.format(inst='"' + inst + '"').encode()
    up = client.post(f"{API}/imports", headers=tokens["officer.rb"], files={"file": ("cases.csv", io.BytesIO(data), "text/csv")})
    assert up.status_code == 201
    job = up.json()
    assert job["mapping"]["reference_no"] == "Ref" and job["mapping"]["title"] == "Subject" and job["sample"]
    dry = client.post(f"{API}/imports/{job['id']}/dry-run", headers=tokens["officer.rb"]).json()
    rep = dry["report"]
    assert rep["rows_ok"] == 1 and rep["rows_error"] == 4
    assert {e["row"] for e in rep["errors"]} == {3, 4, 5, 6}
    assert rep["institution_matches"]["linked"] == 1 and rep["rows_that_would_raise_overlap_alerts"] == 1
    before = client.get(f"{API}/complaints?case_id=IMP-&limit=50", headers=tokens["officer.rb"]).json()["total"]
    assert client.post(f"{API}/imports/{job['id']}/commit", headers=tokens["officer.rb"]).status_code == 403
    c1 = client.post(f"{API}/imports/{job['id']}/commit", headers=tokens["admin"]).json()
    assert c1["report"]["created"] == 1
    c2 = client.post(f"{API}/imports/{job['id']}/commit", headers=tokens["admin"]).json()
    assert c2["report"]["created"] == 1  # unchanged, nothing created twice
    after = client.get(f"{API}/complaints?case_id=IMP-&limit=50", headers=tokens["officer.rb"]).json()["total"]
    assert after == before + 1
    again = client.post(f"{API}/imports", headers=tokens["officer.rb"], files={"file": ("cases.csv", io.BytesIO(data), "text/csv")}).json()
    assert client.post(f"{API}/imports/{again['id']}/dry-run", headers=tokens["officer.rb"]).json()["report"]["duplicate_file"] is True


def test_import_unquoted_comma_is_a_row_error_not_a_crash(client, tokens):
    data = b"Ref,Subject,Type,College,Received\nU-1,Subject,Fee refund,Some College, Pune,2026-09-01\n"
    job = client.post(f"{API}/imports", headers=tokens["officer.rb"], files={"file": ("u.csv", io.BytesIO(data), "text/csv")}).json()
    rep = client.post(f"{API}/imports/{job['id']}/dry-run", headers=tokens["officer.rb"]).json()["report"]
    assert rep["rows_error"] == 1 and "more cells" in rep["errors"][0]["errors"][0]


def test_import_rejects_bad_files(client, tokens):
    r = client.post(f"{API}/imports", headers=tokens["officer.rb"], files={"file": ("x.csv", io.BytesIO(b"a,b\n"), "text/csv")})
    assert r.status_code == 422 and r.json()["error"]["code"] == "empty_file"
    r = client.post(f"{API}/imports", headers=tokens["officer.rb"], files={"file": ("x.csv", io.BytesIO(b"\xff\xfe\x00bad"), "text/csv")})
    assert r.status_code == 422


def test_admin_users_and_scenarios(client, tokens):
    assert client.get(f"{API}/admin/users", headers=tokens["officer.rb"]).status_code == 403
    mk = client.post(f"{API}/admin/users", headers=tokens["admin"], json={
        "email": "new.officer@demo.samanvay.in", "name": "New Officer", "role": "unit_officer", "password": "Another#Pass123", "unit_code": "RB"})
    assert mk.status_code == 201
    login = client.post(f"{API}/auth/login", json={"email": "new.officer@demo.samanvay.in", "password": "Another#Pass123"})
    assert login.status_code == 200
    assert client.post(f"{API}/admin/users", headers=tokens["admin"], json={
        "email": "x@demo.samanvay.in", "name": "X", "role": "unit_officer", "password": "Another#Pass123"}).status_code == 422
    uid = mk.json()["id"]
    assert client.patch(f"{API}/admin/users/{uid}", headers=tokens["admin"], json={"is_active": False}).status_code == 200
    assert client.post(f"{API}/auth/login", json={"email": "new.officer@demo.samanvay.in", "password": "Another#Pass123"}).status_code == 401
    sc = client.post(f"{API}/admin/scenarios/conflict_demo/load", headers=tokens["admin"]).json()
    gate = client.post(f"{API}/gate/check", headers=tokens["officer.pgrc"], json={"institution_id": sc["institution_id"], "action_type": "ISSUE_NOTICE"}).json()
    assert gate["result"] == "CONFLICT"
    assert client.post(f"{API}/admin/scenarios/nope/load", headers=tokens["admin"]).status_code == 404
    with session_factory()() as db:
        db.add(Complaint(case_id="REAL-1", reference_no="REAL1", unit_id=db.scalar(select(Unit.id)), category_id=db.scalar(select(Complaint.category_id)),
                         title="real", received_on=date.today(), is_synthetic=False))
        db.commit()
    refused = client.post(f"{API}/admin/scenarios/conflict_demo/load", headers=tokens["admin"])
    assert refused.status_code == 409 and refused.json()["error"]["code"] == "real_data_present"
    with session_factory()() as db:
        db.delete(db.scalar(select(Complaint).where(Complaint.case_id == "REAL-1")))
        db.commit()


def test_institution_admin_and_complaint_edit_and_attachment(client, tokens):
    made = client.post(f"{API}/institutions", headers=tokens["admin"], json={"canonical_name": "Test Registry College, Nashik", "aicte_id": "7-1234567", "state": "Maharashtra"})
    assert made.status_code == 201
    assert client.post(f"{API}/institutions", headers=tokens["admin"], json={"canonical_name": "Another One", "aicte_id": "7-1234567"}).status_code == 409
    assert client.post(f"{API}/institutions", headers=tokens["officer.rb"], json={"canonical_name": "Nope College"}).status_code == 403
    iid = made.json()["id"]
    assert client.patch(f"{API}/institutions/{iid}", headers=tokens["admin"], json={"district": "Nashik"}).status_code == 200
    al = client.post(f"{API}/institutions/{iid}/aliases", headers=tokens["officer.rb"], json={"alias": "TRC Nashik"}).json()
    assert client.delete(f"{API}/institutions/{iid}/aliases/{al['id']}", headers=tokens["admin"]).status_code == 204
    mine = client.get(f"{API}/complaints?unit=RB&limit=1", headers=tokens["officer.rb"]).json()["items"][0]
    e = client.patch(f"{API}/complaints/{mine['id']}", headers=tokens["officer.rb"], json={"title": "Edited title for this case"})
    assert e.status_code == 200 and e.json()["title"] == "Edited title for this case"
    assert client.patch(f"{API}/complaints/{mine['id']}", headers=tokens["officer.rb"], json={"expected_disposal_on": "2027-01-01"}).status_code == 422
    assert client.patch(f"{API}/complaints/{mine['id']}", headers=tokens["officer.pgrc"], json={"title": "Not my case at all"}).status_code == 403
    up = client.post(f"{API}/complaints/{mine['id']}/attachments", headers=tokens["officer.rb"], files={"file": ("note.txt", io.BytesIO(b"hello"), "text/plain")})
    assert up.status_code == 201 and len(up.json()["sha256"]) == 64
    exe = client.post(f"{API}/complaints/{mine['id']}/attachments", headers=tokens["officer.rb"], files={"file": ("x.exe", io.BytesIO(b"MZ"), "application/x-msdownload")})
    assert exe.status_code == 415
    assert len(client.get(f"{API}/complaints/{mine['id']}/attachments", headers=tokens["officer.rb"]).json()["items"]) == 1


def test_performance_report_and_overlaps_for_case(client, tokens):
    m = client.get(f"{API}/reports/performance?period=monthly", headers=tokens["management"]).json()
    q = client.get(f"{API}/reports/performance?period=quarterly", headers=tokens["management"]).json()
    total = client.get(f"{API}/dashboard/summary", headers=tokens["management"]).json()["counters"]["total_received"]
    in_window = sum(r["received"] for r in m["rows"])
    assert in_window == sum(r["received"] for r in q["rows"]) and in_window <= total
    assert all("-Q" in r["period"] for r in q["rows"])
    assert client.get(f"{API}/reports/performance?period=weekly", headers=tokens["management"]).status_code == 422
    o = _two_unit_pair(client, tokens)
    assert client.get(f"{API}/complaints/{o['a']['id']}/overlaps", headers=tokens["officer.rb"]).json()["items"]


def test_issue_similarity_is_lexical_and_says_so():
    from app.services.intelligence import issue_similarity
    a = Complaint(title="Fee refund pending since admission cancelled", description="")
    b = Complaint(title="Refund of fees not returned after withdrawal", description="")
    c = Complaint(title="Money paid at admission still not given back", description="")
    s_ab, ev = issue_similarity(a, b)
    s_ac, _ = issue_similarity(a, c)
    # Honest limit: word overlap cannot tell "refund" from "money given back". Both pairs describe the same
    # issue, both score far below the 0.5 threshold, and the scores are not ordered by meaning.
    assert ev["method"].startswith("lexical")
    assert s_ab < 0.5 and s_ac < 0.5
