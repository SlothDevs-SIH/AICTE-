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


def _wait_job(client, headers):
    import time

    for _ in range(100):
        j = client.get("/api/v1/admin/jobs/import-aicte", headers=headers).json()
        if j["state"] != "running":
            return j
        time.sleep(0.1)
    raise AssertionError("import did not finish")


CSV = ("S.No,AICTE Permanent ID,Name of the Institute,State,District,Institution Type,Address\n"
       "1,1-900000001,Sample Institute of Technology Alpha,Maharashtra,Pune,Private,Road 1\n"
       "2,1-900000002,Sample College of Pharmacy Beta,karnataka,Mysuru,Government,Road 2\n"
       "3,,No id here,Goa,,,\n")


def test_uploaded_csv_is_loaded_with_other_column_names(client, tokens):
    from sqlalchemy import select

    h = tokens["admin"]
    assert client.post("/api/v1/admin/jobs/import-aicte-file", files={"file": ("list.csv", CSV, "text/csv")}, headers=tokens["officer.rb"]).status_code == 403
    assert client.post("/api/v1/admin/jobs/import-aicte-file", files={"file": ("list.txt", "x", "text/plain")}, headers=h).status_code == 422
    assert client.post("/api/v1/admin/jobs/import-aicte-file", files={"file": ("list.csv", CSV, "text/csv")}, headers=h).status_code == 200
    j = _wait_job(client, h)
    assert j["added"] == 2 and j["skipped"] == 1 and not j["errors"], j
    with session_factory()() as db:
        i = db.scalar(select(Institution).where(Institution.aicte_id == "1-900000002"))
        assert i.state == "Karnataka" and i.district == "Mysuru" and i.is_synthetic is False and i.region_id
    client.post("/api/v1/admin/jobs/import-aicte-file", files={"file": ("list.csv", CSV, "text/csv")}, headers=h)
    again = _wait_job(client, h)
    assert again["added"] == 0 and again["updated"] == 2  # loading the same list twice changes nothing
    with session_factory()() as db:
        for i in db.scalars(select(Institution).where(Institution.aicte_id.in_(["1-900000001", "1-900000002"]))):
            db.delete(i)
        db.commit()


def test_uploaded_excel_and_a_useless_file(client, tokens):
    import io

    from openpyxl import Workbook
    from sqlalchemy import select

    h = tokens["admin"]
    wb = Workbook()
    ws = wb.active
    ws.append(["Report generated on 28 Oct"])  # a title row above the real header
    ws.append(["AICTE ID", "Institute Name", "State", "District"])
    ws.append(["1-900000003", "Sample Polytechnic Gamma", "Goa", "North Goa"])
    buf = io.BytesIO()
    wb.save(buf)
    assert client.post("/api/v1/admin/jobs/import-aicte-file", files={"file": ("list.xlsx", buf.getvalue(), "application/octet-stream")}, headers=h).status_code == 200
    assert _wait_job(client, h)["added"] == 1
    client.post("/api/v1/admin/jobs/import-aicte-file", files={"file": ("list.csv", "foo,bar\n1,2\n", "text/csv")}, headers=h)
    bad = _wait_job(client, h)
    assert bad["errors"] and bad["added"] == 0
    with session_factory()() as db:
        for i in db.scalars(select(Institution).where(Institution.aicte_id == "1-900000003")):
            db.delete(i)
        db.commit()
