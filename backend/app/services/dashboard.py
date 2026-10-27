"""Dashboard counters, defined once (BACKEND_PLAN 3.3). Definitions are our interpretation (V-B9)."""
from collections import Counter
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import roles as R
from app.db.models import Complaint, ComplaintEvent, Institution, Unit, User

OPEN = ("RECEIVED", "ASSIGNED", "UNDER_PROCESS", "ESCALATED", "REOPENED", "TRANSFERRED")


def scoped(db: Session, user: User) -> list[Complaint]:
    q = select(Complaint)
    if user.role in (R.UNIT_OFFICER, R.UNIT_SUPERVISOR) and user.unit_id:
        q = q.where(Complaint.unit_id == user.unit_id)
    rows = list(db.scalars(q))
    if user.role == R.REGIONAL_OFFICER and user.region_id:
        ids = {i.id for i in db.scalars(select(Institution).where(Institution.region_id == user.region_id))}
        rows = [c for c in rows if c.institution_id in ids]
    return rows


def scope_caption(db: Session, user: User) -> str:
    if user.role in (R.UNIT_OFFICER, R.UNIT_SUPERVISOR) and user.unit_id:
        u = db.get(Unit, user.unit_id)
        return f"Showing: {u.code if u else 'your unit'}, all regions"
    if user.role == R.REGIONAL_OFFICER:
        return "Showing: your region, all units"
    return "Showing: all units, all regions"


def is_overdue(c: Complaint, today: date) -> bool:
    return bool(c.due_on and c.due_on < today and c.state != "DISPOSED")


def summary(db: Session, user: User) -> dict:
    rows, today = scoped(db, user), date.today()
    ids = [c.id for c in rows]
    transferred_ids = set()
    if ids:
        transferred_ids = set(db.scalars(select(ComplaintEvent.complaint_id).where(
            ComplaintEvent.kind == "TRANSFERRED", ComplaintEvent.complaint_id.in_(ids))))
    by_state = Counter(c.state for c in rows)
    due_soon = [c for c in rows if c.due_on and c.state != "DISPOSED"
                and 0 <= (c.due_on - today).days <= 7]
    units = {u.id: u.code for u in db.scalars(select(Unit))}
    return {
        "caption": scope_caption(db, user),
        "counters": {
            "total_received": len(rows),
            "pending": by_state["RECEIVED"] + by_state["ASSIGNED"],
            "under_process": by_state["UNDER_PROCESS"],
            "disposed": by_state["DISPOSED"],
            "transferred": len(transferred_ids),
            "escalated": by_state["ESCALATED"],
            "beyond_timeline": sum(is_overdue(c, today) for c in rows),
            "due_soon": len(due_soon),
        },
        "by_unit": [
            {"unit": code, "total": sum(1 for c in rows if c.unit_id == uid),
             "open": sum(1 for c in rows if c.unit_id == uid and c.state in OPEN)}
            for uid, code in units.items()
        ],
    }


def ageing(db: Session, user: User) -> list[dict]:
    today = date.today()
    buckets = [("0-7 days", 0, 7), ("8-30 days", 8, 30), ("31-90 days", 31, 90), ("90+ days", 91, 10**6)]
    open_rows = [c for c in scoped(db, user) if c.state in OPEN]
    return [{"bucket": n, "count": sum(1 for c in open_rows if lo <= (today - c.received_on).days <= hi)}
            for n, lo, hi in buckets]


def by_institution(db: Session, user: User) -> list[dict]:
    rows = scoped(db, user)
    insts = {i.id: i for i in db.scalars(select(Institution))}
    units = {u.id: u.code for u in db.scalars(select(Unit))}
    groups: dict[str, list[Complaint]] = {}
    for c in rows:
        if c.institution_id:
            groups.setdefault(c.institution_id, []).append(c)
    out = []
    for iid, cs in groups.items():
        inst = insts[iid]
        out.append({
            "institution_id": iid, "name": inst.canonical_name, "aicte_id": inst.aicte_id,
            "state": inst.state, "total": len(cs),
            "by_status": dict(Counter(c.state for c in cs)),
            "units": sorted({units[c.unit_id] for c in cs if c.state in OPEN}),
        })
    return sorted(out, key=lambda r: (-len(r["units"]), -r["total"]))
