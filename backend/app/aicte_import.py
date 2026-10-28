"""Load real AICTE-approved institutions into the college registry (public reference data, not complaint data).

Source: the public approved-institutes list on facilities.aicte-india.org. The endpoint and the field order are
taken from a public extractor script (github.com/practicotech/aicte-india-institutes). This machine could not
reach that site when the importer was written, so the live fetch has NOT been run here; the parsing is tested
against a fixture of the same shape. Rows can also come from a local JSON file saved from that endpoint.
"""
import json
from datetime import datetime
from urllib.parse import quote_plus

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Institution, InstitutionAlias, Region
from app.engine.normalize import normalize
from app.seed import REGIONS

URL = ("https://facilities.aicte-india.org/dashboard/pages/php/approvedinstituteserver.php?method=fetchdata"
       "&year={year}&program=1&level=1&institutiontype=1&Women=1&Minority=1&state={state}&course=1")
COLS = ["AICTE ID", "Institute Name", "Address", "District", "Institution Type", "Women Only Institution",
        "Minority Institution", "Institute ID"]
STATES = [s for _, _, states in REGIONS for s in states]


def fetch_state(state: str, year: str | None = None) -> list:
    import httpx

    y = year or f"{datetime.now().year - 1}-{datetime.now().year}"
    r = httpx.get(URL.format(year=y, state=quote_plus(state)), timeout=60)
    r.raise_for_status()
    return r.json()


def load_rows(db: Session, rows: list, state: str) -> dict:
    """Insert or update institutions from rows (lists in COLS order, or dicts keyed by COLS)."""
    region_of = {st: code for code, _, sts in REGIONS for st in sts}
    regions = {r.code: r.id for r in db.scalars(select(Region))}
    stats = {"added": 0, "updated": 0, "skipped": 0}
    for row in rows:
        d = dict(zip(COLS, row)) if isinstance(row, (list, tuple)) else row
        name, aid = (d.get("Institute Name") or "").strip(), (d.get("AICTE ID") or "").strip()
        if not name or not aid:
            stats["skipped"] += 1
            continue
        inst = db.scalar(select(Institution).where(Institution.aicte_id == aid))
        fields = dict(canonical_name=name, normalized_name=normalize(name), type=d.get("Institution Type"),
                      state=state, district=d.get("District"), address=d.get("Address"),
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
        batches = [(s, fetch_state(s)) for s in (states or STATES)]
    for state, rows in batches:
        for k, v in load_rows(db, rows, state).items():
            total[k] += v
    return total
