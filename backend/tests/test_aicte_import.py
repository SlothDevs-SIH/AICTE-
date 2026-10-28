from sqlalchemy import select

from app.aicte_import import load_rows
from app.db.models import Institution
from app.db.base import session_factory

# Same field order the public AICTE endpoint returns. Names here are invented for the test, not real records.
ROWS = [["1-100000001", "Test Institute of Engineering, Pune", "Some Road", "Pune", "Private", "No", "No", "9"],
        ["", "No id", "", "", "", "", "", ""]]


def test_rows_load_idempotently_and_are_marked_real():
    with session_factory()() as db:
        first = load_rows(db, ROWS, "Maharashtra")
        second = load_rows(db, ROWS, "Maharashtra")
        inst = db.scalar(select(Institution).where(Institution.aicte_id == "1-100000001"))
        assert first == {"added": 1, "updated": 0, "skipped": 1}
        assert second == {"added": 0, "updated": 1, "skipped": 1}
        assert inst.is_synthetic is False and inst.state == "Maharashtra" and inst.region_id
        db.delete(inst)
        db.commit()


def test_dict_rows_with_other_key_styles_and_background_work(monkeypatch):
    from app import aicte_import

    rows = [{"aicteid": "1-100000002", "institutename": "Second Test Institute", "district": "North Goa",
             "institutiontype": "Private", "address": "x"}]
    monkeypatch.setattr(aicte_import, "fetch_state", lambda s: rows if s == "Goa" else (_ for _ in ()).throw(RuntimeError("down")))
    aicte_import.JOB.update(state="running", done_states=0, total_states=2, added=0, updated=0, skipped=0, errors=[])
    aicte_import._work(["Goa", "Kerala"])
    assert aicte_import.JOB["state"] == "finished" and aicte_import.JOB["added"] == 1
    assert len(aicte_import.JOB["errors"]) == 1 and "Kerala" in aicte_import.JOB["errors"][0]  # one failure does not stop the rest
    with session_factory()() as db:
        inst = db.scalar(select(Institution).where(Institution.aicte_id == "1-100000002"))
        assert inst and inst.district == "North Goa" and inst.is_synthetic is False
        db.delete(inst)
        db.commit()


def test_import_job_is_admin_only(client, tokens):
    assert client.post("/api/v1/admin/jobs/import-aicte", headers=tokens["officer.rb"]).status_code == 403
    assert client.get("/api/v1/admin/jobs/import-aicte", headers=tokens["officer.rb"]).status_code == 403
    assert client.get("/api/v1/admin/jobs/import-aicte", headers=tokens["admin"]).status_code == 200
