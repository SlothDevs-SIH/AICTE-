"""Load real AICTE-approved institutions into the college registry (public reference data, not complaint data).

Source: the public approved-institutes list on facilities.aicte-india.org. The endpoint and the field order are
taken from a public extractor script (github.com/practicotech/aicte-india-institutes). The site could not be reached
from the machine this was written on, so the live fetch is verified only by running it on the deployment; parsing is
tested against a fixture. Rows can also come from a local JSON file saved from that endpoint.
"""
import csv
import io
import json
import re
import threading
from datetime import UTC, datetime
from urllib.parse import quote_plus

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import session_factory
from app.db.models import Institution, InstitutionAlias, Region
from app.engine.normalize import normalize
from app.seed import REGIONS

URL = ("https://facilities.aicte-india.org/dashboard/pages/php/approvedinstituteserver.php?method=fetchdata"
       "&year={year}&program=1&level=1&institutiontype=1&Women=1&Minority=1&state={state}&course=1")
COLS = ["AICTE ID", "Institute Name", "Address", "District", "Institution Type", "Women Only Institution",
        "Minority Institution", "Institute ID"]
STATES = [s for _, _, states in REGIONS for s in states]
ALL_STATES = [  # every state and union territory the AICTE list uses
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chandigarh", "Chhattisgarh", "Dadra and Nagar Haveli",
    "Daman and Diu", "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand",
    "Karnataka", "Kerala", "Ladakh", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal"]


def _key(k: str) -> str:
    return re.sub(r"[^a-z]", "", str(k).lower())


def fetch_state(state: str, year: str | None = None) -> list:
    import httpx

    y = year or f"{datetime.now().year - 1}-{datetime.now().year}"
    r = httpx.get(URL.format(year=y, state=quote_plus(state)), timeout=60, follow_redirects=True)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict):  # tolerate {"data": [...]} style wrappers
        data = data.get("data") or data.get("rows") or []
    return data


def _row_dict(row) -> dict:
    if isinstance(row, (list, tuple)):
        return {_key(c): v for c, v in zip(COLS, row)}
    return {_key(k): v for k, v in row.items()}


def load_rows(db: Session, rows: list, state: str) -> dict:
    """Insert or update institutions from rows (lists in COLS order, or dicts keyed by COLS)."""
    region_of = {st: code for code, _, sts in REGIONS for st in sts}
    regions = {r.code: r.id for r in db.scalars(select(Region))}
    stats = {"added": 0, "updated": 0, "skipped": 0}
    for row in rows:
        d = _row_dict(row)
        name, aid = str(d.get("institutename") or "").strip(), str(d.get("aicteid") or "").strip()
        if not name or not aid:
            stats["skipped"] += 1
            continue
        inst = db.scalar(select(Institution).where(Institution.aicte_id == aid))
        fields = dict(canonical_name=name, normalized_name=normalize(name), type=d.get("institutiontype"),
                      state=state, district=d.get("district"), address=d.get("address"),
                      region_id=regions.get(region_of.get(state, "")), is_synthetic=False)
        if inst:
            for k, v in fields.items():
                setattr(inst, k, v)
            stats["updated"] += 1
        else:
            inst = Institution(aicte_id=aid, **fields)
            db.add(inst)
            db.flush()
            db.add(InstitutionAlias(institution_id=inst.id, alias=name, normalized_alias=normalize(name), source="import"))
            stats["added"] += 1
    db.commit()
    return stats


def run(db: Session, file: str | None = None, states: list[str] | None = None) -> dict:
    total = {"added": 0, "updated": 0, "skipped": 0}
    if file:
        data = json.loads(open(file, encoding="utf-8").read())  # {"State": [rows]}
        batches = list(data.items())
    else:
        batches = [(s, fetch_state(s)) for s in (states or ALL_STATES)]
    for state, rows in batches:
        for k, v in load_rows(db, rows, state).items():
            total[k] += v
    return total


# ---- background job, so a web request never waits for 35 downloads ----
JOB: dict = {"state": "idle", "done_states": 0, "total_states": 0, "added": 0, "updated": 0, "skipped": 0,
             "errors": [], "started_at": None, "finished_at": None}
_lock = threading.Lock()


def _work(states: list[str]) -> None:
    for s in states:
        try:
            rows = fetch_state(s)
            with session_factory()() as db:
                st = load_rows(db, rows, s)
            for k in ("added", "updated", "skipped"):
                JOB[k] += st[k]
            if not rows:
                JOB["errors"].append(f"{s}: the list came back empty")
        except Exception as e:  # one state failing must not stop the others
            JOB["errors"].append(f"{s}: {type(e).__name__}: {str(e)[:160]}")
        JOB["done_states"] += 1
    JOB["state"] = "finished"
    JOB["finished_at"] = datetime.now(UTC).isoformat()


def start_job(states: list[str] | None = None) -> dict:
    with _lock:
        if JOB["state"] == "running":
            return JOB
        states = states or ALL_STATES
        JOB.update(state="running", done_states=0, total_states=len(states), added=0, updated=0, skipped=0,
                   errors=[], started_at=datetime.now(UTC).isoformat(), finished_at=None)
    threading.Thread(target=_work, args=(states,), daemon=True).start()
    return JOB


# ---- a list saved from the AICTE dashboard (Excel or CSV) or as JSON, uploaded by an administrator ----
ID_KEYS = ("aicteid", "aicteidpermanent", "permanentid", "aicteapprovalid", "aicteapplicationid", "institutionid", "id")
NAME_KEYS = ("institutename", "institutionname", "nameoftheinstitute", "nameoftheinstitution", "instituteinstitutionname", "institute", "name")
STATE_KEYS = ("state", "statename", "stateut")
DISTRICT_KEYS = ("district", "districtname", "city")
TYPE_KEYS = ("institutiontype", "institutetype", "type", "typeofinstitution")
ADDRESS_KEYS = ("address", "institutionaddress", "instituteaddress", "addressline")


def _first(d: dict, keys: tuple, contains: tuple = ()) -> str | None:
    """The first non-empty value among the known column names, else any column whose name contains all of `contains`."""
    for k in keys:
        v = d.get(k)
        if v not in (None, "") and str(v).strip():
            return str(v).strip()
    if contains:
        for k, v in d.items():
            if all(c in k for c in contains) and v not in (None, "") and str(v).strip():
                return str(v).strip()
    return None


def records_from_file(filename: str, data: bytes) -> list[dict]:
    """Rows of a CSV, Excel (.xlsx) or JSON file as dicts keyed by simplified column names (letters only, lower case)."""
    name = (filename or "").lower()
    if name.endswith(".xlsx"):
        from openpyxl import load_workbook

        out: list[dict] = []
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        for ws in wb.worksheets:
            it = ws.iter_rows(values_only=True)
            head = None
            for row in it:
                if head is None:  # the first row that has an institute-name style column is the header
                    keys = [_key(c) if c is not None else "" for c in row]
                    if any(k in NAME_KEYS for k in keys):
                        head = keys
                    continue
                if any(v not in (None, "") for v in row):
                    out.append({head[i]: v for i, v in enumerate(row) if i < len(head) and head[i]})
        return out
    if name.endswith(".json"):
        j = json.loads(data.decode("utf-8-sig"))
        if isinstance(j, dict):  # {"State": [rows]} as saved from the AICTE endpoint
            out = []
            for st, rows in j.items():
                for r in rows or []:
                    d = _row_dict(r)
                    d.setdefault("state", st)
                    out.append(d)
            return out
        return [_row_dict(r) for r in j]
    text = data.decode("utf-8-sig", errors="replace")
    return [{_key(k): v for k, v in r.items() if k} for r in csv.DictReader(io.StringIO(text))]


def load_records(db: Session, records: list[dict], default_state: str | None = None) -> dict:
    """Insert or update institutions from keyed rows. Reads the existing IDs once, so it is fast on a remote database."""
    region_of = {st: code for code, _, sts in REGIONS for st in sts}
    regions = {r.code: r.id for r in db.scalars(select(Region))}
    existing = {i.aicte_id: i for i in db.scalars(select(Institution).where(Institution.aicte_id.is_not(None)))}
    stats = {"added": 0, "updated": 0, "skipped": 0}
    for d in records:
        aid = _first(d, ID_KEYS, ("aicte", "id")) or _first(d, (), ("permanent", "id"))
        name = _first(d, NAME_KEYS, ("name", "institut")) or _first(d, (), ("name", "college"))
        if not aid or not name:
            stats["skipped"] += 1
            continue
        state = _first(d, STATE_KEYS) or default_state
        if state:
            state = next((s for s in ALL_STATES if s.lower() == state.lower()), state.title())
        fields = dict(canonical_name=name[:300], normalized_name=normalize(name)[:300], type=(_first(d, TYPE_KEYS) or "")[:60] or None,
                      state=(state or None), district=(_first(d, DISTRICT_KEYS) or "")[:80] or None,
                      address=_first(d, ADDRESS_KEYS), region_id=regions.get(region_of.get(state or "", "")), is_synthetic=False)
        inst = existing.get(aid)
        if inst:
            for k, v in fields.items():
                setattr(inst, k, v)
            stats["updated"] += 1
        else:
            inst = Institution(aicte_id=aid[:40], **fields)
            db.add(inst)
            existing[aid] = inst
            stats["added"] += 1
    db.flush()
    for inst in existing.values():  # one alias per new institution, so spelling searches find it
        if inst.id and not db.scalar(select(InstitutionAlias.id).where(InstitutionAlias.institution_id == inst.id).limit(1)):
            db.add(InstitutionAlias(institution_id=inst.id, alias=inst.canonical_name, normalized_alias=inst.normalized_name, source="import"))
    db.commit()
    return stats


def start_file_job(filename: str, data: bytes) -> dict:
    """Parse and load an uploaded list in the background; progress is read from JOB like the web import."""
    with _lock:
        if JOB["state"] == "running":
            return JOB
        JOB.update(state="running", done_states=0, total_states=1, added=0, updated=0, skipped=0, errors=[],
                   started_at=datetime.now(UTC).isoformat(), finished_at=None)

    def work():
        try:
            records = records_from_file(filename, data)
            if not records:
                JOB["errors"].append("No rows found. The file needs a header row with columns such as AICTE ID and Institute Name.")
            with session_factory()() as db:
                st = load_records(db, records)
            for k in ("added", "updated", "skipped"):
                JOB[k] += st[k]
            if records and st["added"] + st["updated"] == 0:
                JOB["errors"].append("No row had both an AICTE ID and an institute name. Check the column headings.")
        except Exception as e:  # a bad file must show as a message, not a crash
            JOB["errors"].append(f"{type(e).__name__}: {str(e)[:200]}")
        JOB["done_states"] = 1
        JOB["state"] = "finished"
        JOB["finished_at"] = datetime.now(UTC).isoformat()

    threading.Thread(target=work, daemon=True).start()
    return JOB
