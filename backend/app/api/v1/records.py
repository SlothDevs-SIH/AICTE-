"""Institutions, complaints, dashboard, overlaps, Action Gate, audit, escalations, reports."""
import csv
import io
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require
from app.core import roles as R
from app.core.audit import verify_chain, write_audit
from app.core.crypto import decrypt, mask_email, mask_name, mask_phone
from app.core.errors import ApiError
from app.db.base import get_db
from app.db.models import (
    AuditLog, Category, Complaint, ComplaintEvent, GateCheck, Institution, InstitutionAlias,
    Overlap, Region, Unit, User,
)
from app.engine.institution import match_institution
from app.engine.normalize import normalize
from app.engine.overlap import OPEN_STATES, gate_check, has_action
from app.services import complaints as svc
from app.services import dashboard as dash

router = APIRouter()
OFFICERS = R.OFFICER
SEE_ALL_DETAIL = (R.MANAGEMENT, R.COMPETENT_AUTHORITY, R.ADMIN, R.AUDITOR)


# ---------- serializers ----------
def _maps(db: Session):
    return (
        {u.id: u for u in db.scalars(select(Unit))},
        {c.id: c for c in db.scalars(select(Category))},
        {i.id: i for i in db.scalars(select(Institution))},
        {u.id: u for u in db.scalars(select(User))},
    )


def has_overlap_ids(db: Session) -> dict[str, str]:
    out: dict[str, str] = {}
    for o in db.scalars(select(Overlap).where(Overlap.status.in_(("SUGGESTED", "CONFIRMED", "LINKED")))):
        for cid in (o.complaint_a_id, o.complaint_b_id):
            if out.get(cid) != "CONFLICT":
                out[cid] = o.severity
    return out


def complaint_row(c: Complaint, m, overlaps: dict[str, str]) -> dict:
    units, cats, insts, users = m
    inst = insts.get(c.institution_id) if c.institution_id else None
    today = date.today()
    return {
        "id": c.id, "case_id": c.case_id, "reference_no": c.reference_no, "title": c.title,
        "unit": units[c.unit_id].code, "unit_id": c.unit_id,
        "institution_id": c.institution_id,
        "institution": inst.canonical_name if inst else (c.institution_text_raw or "Unresolved"),
        "institution_text_raw": c.institution_text_raw,
        "category": cats[c.category_id].name, "state": c.state, "priority": c.priority,
        "owner": users[c.owner_user_id].name if c.owner_user_id in users else None,
        "received_on": c.received_on.isoformat(),
        "due_on": c.due_on.isoformat() if c.due_on else None,
        "expected_disposal_on": c.expected_disposal_on.isoformat() if c.expected_disposal_on else None,
        "overdue": dash.is_overdue(c, today), "escalation_level": c.escalation_level,
        "last_action_text": c.last_action_text,
        "last_action_at": c.last_action_at.isoformat() if c.last_action_at else None,
        "next_action_text": c.next_action_text,
        "next_action_due_on": c.next_action_due_on.isoformat() if c.next_action_due_on else None,
        "overlap_severity": overlaps.get(c.id), "is_synthetic": c.is_synthetic,
    }


def can_see_detail(db: Session, user: User, c: Complaint) -> bool:
    if user.role in SEE_ALL_DETAIL or c.unit_id == user.unit_id:
        return True
    linked = db.scalars(select(Overlap).where(
        Overlap.status.in_(("CONFIRMED", "LINKED")),
        or_(Overlap.complaint_a_id == c.id, Overlap.complaint_b_id == c.id)))
    mine = {x.id for x in db.scalars(select(Complaint).where(Complaint.unit_id == user.unit_id))}
    if any((o.complaint_a_id in mine or o.complaint_b_id in mine) for o in linked):
        return True
    # a unit taking part in a coordination thread about this case may read it
    from app.db.models import CoordinationThreadComplaint as TC
    for tc in db.scalars(select(TC).where(TC.complaint_id == c.id)):
        sibling = db.scalars(select(TC).where(TC.thread_id == tc.thread_id))
        if any(s.complaint_id in mine for s in sibling):
            return True
    return False


def get_complaint(db: Session, cid: str) -> Complaint:
    c = db.get(Complaint, cid) or db.scalar(select(Complaint).where(Complaint.case_id == cid))
    if c is None:
        raise ApiError(404, "not_found", "Case not found.")
    return c


def own_or_supervisor(user: User, c: Complaint):
    if user.role == R.ADMIN:
        return
    if user.role not in OFFICERS or (c.unit_id != user.unit_id and user.role != R.REGIONAL_OFFICER):
        raise ApiError(403, "forbidden", "You can only change cases in your own unit.")


# ---------- institutions ----------
@router.get("/institutions")
def list_institutions(q: str | None = None, state: str | None = None, region: str | None = None,
                      limit: int = Query(50, le=200), db: Session = Depends(get_db),
                      _: User = Depends(current_user)):
    regions = {r.id: r for r in db.scalars(select(Region))}
    rows = list(db.scalars(select(Institution)))
    if state:
        rows = [i for i in rows if (i.state or "").casefold() == state.casefold()]
    if region:
        rows = [i for i in rows if i.region_id in regions and regions[i.region_id].code == region]
    if q:
        hits = {c.institution_id: c.score for c in match_institution(db, q, q, limit=50)}
        nq = normalize(q)
        rows = [i for i in rows if i.id in hits or nq in i.normalized_name or q.casefold() in (i.aicte_id or "").casefold()]
    return {"items": [_inst(i, regions) for i in rows[:limit]], "total": len(rows)}


def _inst(i: Institution, regions: dict) -> dict:
    r = regions.get(i.region_id) if i.region_id else None
    return {"id": i.id, "aicte_id": i.aicte_id, "name": i.canonical_name, "short_name": i.short_name,
            "type": i.type, "state": i.state, "district": i.district, "pincode": i.pincode,
            "region": r.code if r else None, "address": i.address}


@router.get("/institutions/suggest")
def suggest(text: str, aicte_id: str | None = None, db: Session = Depends(get_db),
            _: User = Depends(require(*OFFICERS, R.ADMIN))):
    c = match_institution(db, text, aicte_id)
    return {"items": [{"institution_id": x.institution_id, "name": x.name, "match_score": x.score,
                       "layer": x.layer, "evidence": x.evidence} for x in c]}


@router.get("/institutions/{iid}")
def get_institution(iid: str, db: Session = Depends(get_db), _: User = Depends(current_user)):
    i = db.get(Institution, iid)
    if i is None:
        raise ApiError(404, "not_found", "Institution not found.")
    regions = {r.id: r for r in db.scalars(select(Region))}
    aliases = db.scalars(select(InstitutionAlias).where(InstitutionAlias.institution_id == iid))
    return {**_inst(i, regions), "aliases": [{"id": a.id, "alias": a.alias, "source": a.source} for a in aliases]}


class AliasIn(BaseModel):
    alias: str = Field(min_length=2)


@router.post("/institutions/{iid}/aliases", status_code=201)
def add_alias(iid: str, body: AliasIn, db: Session = Depends(get_db),
              user: User = Depends(require(*OFFICERS, R.ADMIN))):
    if db.get(Institution, iid) is None:
        raise ApiError(404, "not_found", "Institution not found.")
    n = normalize(body.alias)
    if db.scalar(select(InstitutionAlias).where(InstitutionAlias.institution_id == iid,
                                                InstitutionAlias.normalized_alias == n)):
        raise ApiError(409, "duplicate_alias", "This alias already exists.")
    a = InstitutionAlias(institution_id=iid, alias=body.alias, normalized_alias=n,
                         source="officer_confirmed", confirmed_by=user.id, confirmed_at=svc.now())
    db.add(a)
    write_audit(db, user.id, "ALIAS_ADDED", "institution", iid, {"alias": body.alias})
    db.commit()
    return {"id": a.id, "alias": a.alias, "source": a.source}


@router.get("/institutions/{iid}/360")
def college_360(iid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    i = db.get(Institution, iid)
    if i is None:
        raise ApiError(404, "not_found", "Institution not found.")
    m = _maps(db)
    ov = has_overlap_ids(db)
    cs = list(db.scalars(select(Complaint).where(Complaint.institution_id == iid)
                         .order_by(Complaint.received_on.desc())))
    overlaps = list(db.scalars(select(Overlap).where(Overlap.institution_id == iid)))
    regions = {r.id: r for r in db.scalars(select(Region))}
    return {
        "institution": _inst(i, regions),
        "cases": [complaint_row(c, m, ov) for c in cs],
        "open_units": sorted({m[0][c.unit_id].code for c in cs if c.state in OPEN_STATES}),
        "overlaps": [overlap_row(o, m, db, brief=True) for o in overlaps],
        "summary": {"total": len(cs), "open": sum(1 for c in cs if c.state in OPEN_STATES),
                    "disposed": sum(1 for c in cs if c.state == "DISPOSED")},
    }


# ---------- complaints ----------
@router.get("/reference")
def reference(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return {
        "units": [{"id": u.id, "code": u.code, "name": u.name} for u in db.scalars(select(Unit))],
        "regions": [{"id": r.id, "code": r.code, "name": r.name} for r in db.scalars(select(Region))],
        "categories": [{"id": c.id, "code": c.code, "name": c.name, "sla_days": c.sla_days}
                       for c in db.scalars(select(Category))],
        "states": ["RECEIVED", "ASSIGNED", "UNDER_PROCESS", "TRANSFERRED", "ESCALATED", "DISPOSED", "REOPENED"],
    }


@router.get("/complaints")
def list_complaints(
    institution_id: str | None = None, aicte_id: str | None = None, unit: str | None = None,
    region: str | None = None, category: str | None = None, state: str | None = None,
    overdue: bool | None = None, escalated: bool | None = None, has_overlap: bool | None = None,
    received_from: date | None = None, received_to: date | None = None,
    q: str | None = None, case_id: str | None = None, due_soon: bool | None = None,
    older_than_days: int | None = None,
    limit: int = Query(50, le=200), offset: int = 0,
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    m = _maps(db)
    units, cats, insts, _ = m
    regions = {r.id: r.code for r in db.scalars(select(Region))}
    ov = has_overlap_ids(db)
    today = date.today()
    rows = list(db.scalars(select(Complaint).order_by(Complaint.received_on.desc(), Complaint.case_id)))

    def keep(c: Complaint) -> bool:
        inst = insts.get(c.institution_id) if c.institution_id else None
        if institution_id and c.institution_id != institution_id: return False
        if aicte_id and not (inst and (inst.aicte_id or "").casefold() == aicte_id.casefold()
                             or (c.aicte_id_raw or "").casefold() == aicte_id.casefold()): return False
        if unit and units[c.unit_id].code != unit: return False
        if region and not (inst and regions.get(inst.region_id) == region): return False
        if category and cats[c.category_id].code != category: return False
        if state and c.state != state: return False
        if overdue is not None and dash.is_overdue(c, today) != overdue: return False
        if escalated is not None and (c.state == "ESCALATED") != escalated: return False
        if has_overlap is not None and (c.id in ov) != has_overlap: return False
        if received_from and c.received_on < received_from: return False
        if received_to and c.received_on > received_to: return False
        if older_than_days is not None and (today - c.received_on).days <= older_than_days: return False
        if case_id and case_id.casefold() not in c.case_id.casefold() and case_id.casefold() not in c.reference_no.casefold(): return False
        if due_soon and not (c.due_on and c.state != "DISPOSED" and 0 <= (c.due_on - today).days <= 7): return False
        if q:
            hay = " ".join([c.title, c.case_id, c.reference_no, c.institution_text_raw or "",
                            inst.canonical_name if inst else ""]).casefold()
            if q.casefold() not in hay and normalize(q) not in normalize(hay): return False
        return True

    matched = [c for c in rows if keep(c)]
    return {"items": [complaint_row(c, m, ov) for c in matched[offset:offset + limit]],
            "total": len(matched), "limit": limit, "offset": offset}


class ComplaintIn(BaseModel):
    reference_no: str = Field(min_length=1)
    category_id: str
    title: str = Field(min_length=3)
    description: str = ""
    institution_id: str | None = None
    institution_text_raw: str | None = None
    aicte_id_raw: str | None = None
    unit_id: str | None = None
    received_on: date | None = None
    priority: str = "NORMAL"
    complainant_name: str | None = None
    complainant_phone: str | None = None
    complainant_email: str | None = None


@router.post("/complaints", status_code=201)
def create_complaint(body: ComplaintIn, db: Session = Depends(get_db),
                     user: User = Depends(require(*OFFICERS, R.ADMIN))):
    from app.core.crypto import encrypt
    from app.engine.institution import resolve

    unit_id = body.unit_id if user.role == R.ADMIN and body.unit_id else user.unit_id
    if not unit_id:
        raise ApiError(422, "unit_required", "A unit is required to create a case.")
    inst_id, cands, status = body.institution_id, [], "chosen_by_officer"
    if not inst_id:
        inst_id, cands, status = resolve(db, body.institution_text_raw, body.aicte_id_raw)
    c = svc.create_complaint(
        db, user, unit_id=unit_id, reference_no=body.reference_no, category_id=body.category_id,
        title=body.title, description=body.description, institution_id=inst_id,
        institution_text_raw=body.institution_text_raw, aicte_id_raw=body.aicte_id_raw,
        received_on=body.received_on, priority=body.priority, is_synthetic=True)
    c.complainant_name_enc = encrypt(body.complainant_name)
    c.complainant_phone_enc = encrypt(body.complainant_phone)
    c.complainant_email_enc = encrypt(body.complainant_email)
    db.commit()
    m, ov = _maps(db), has_overlap_ids(db)
    return {"complaint": complaint_row(c, m, ov), "institution_match": {
        "status": status, "candidates": [{"institution_id": x.institution_id, "name": x.name,
        "match_score": x.score, "layer": x.layer, "evidence": x.evidence} for x in cands]}}


@router.get("/complaints/{cid}")
def complaint_detail(cid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = get_complaint(db, cid)
    m, ov = _maps(db), has_overlap_ids(db)
    row = complaint_row(c, m, ov)
    if not can_see_detail(db, user, c):
        return {**row, "detail_visible": False,
                "note": "Details visible after coordination is accepted or the cases are linked."}
    reveal = user.role in (R.UNIT_OFFICER, R.UNIT_SUPERVISOR, R.REGIONAL_OFFICER, R.MANAGEMENT,
                           R.COMPETENT_AUTHORITY, R.ADMIN)
    pii = {"name": mask_name(decrypt(c.complainant_name_enc)),
           "phone": mask_phone(decrypt(c.complainant_phone_enc)),
           "email": mask_email(decrypt(c.complainant_email_enc)), "masked": True,
           "can_reveal": reveal}
    return {**row, "detail_visible": True, "description": c.description,
            "language_hint": c.language_hint, "complainant": pii,
            "on_hold_for_coordination": c.on_hold_for_coordination}


class RevealIn(BaseModel):
    reason: str = Field(min_length=10)


@router.post("/complaints/{cid}/reveal-pii")
def reveal_pii(cid: str, body: RevealIn, db: Session = Depends(get_db),
               user: User = Depends(require(*OFFICERS, R.MANAGEMENT, R.COMPETENT_AUTHORITY, R.ADMIN))):
    c = get_complaint(db, cid)
    if not can_see_detail(db, user, c):
        raise ApiError(403, "forbidden", "You cannot see this case in detail.")
    write_audit(db, user.id, "PII_REVEALED", "complaint", c.id, {"reason": body.reason, "case_id": c.case_id})
    db.commit()
    return {"name": decrypt(c.complainant_name_enc), "phone": decrypt(c.complainant_phone_enc),
            "email": decrypt(c.complainant_email_enc)}


@router.get("/complaints/{cid}/events")
def events(cid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = get_complaint(db, cid)
    if not can_see_detail(db, user, c):
        raise ApiError(403, "forbidden", "Details visible after coordination is accepted.")
    users = {u.id: u for u in db.scalars(select(User))}
    units = {u.id: u.code for u in db.scalars(select(Unit))}
    rows = db.scalars(select(ComplaintEvent).where(ComplaintEvent.complaint_id == c.id)
                      .order_by(ComplaintEvent.occurred_at, ComplaintEvent.created_at))
    return {"items": [{"id": e.id, "kind": e.kind, "from_state": e.from_state, "to_state": e.to_state,
                       "actor": users[e.actor_user_id].name if e.actor_user_id in users else "System",
                       "actor_unit": units.get(users[e.actor_user_id].unit_id) if e.actor_user_id in users else None,
                       "remark": e.remark, "payload": e.payload_json,
                       "occurred_at": e.occurred_at.isoformat()} for e in rows]}


class TransitionIn(BaseModel):
    to_state: str
    remark: str | None = None
    owner_user_id: str | None = None


@router.post("/complaints/{cid}/transition")
def do_transition(cid: str, body: TransitionIn, db: Session = Depends(get_db),
                  user: User = Depends(require(*OFFICERS, R.COMPETENT_AUTHORITY, R.ADMIN))):
    c = get_complaint(db, cid)
    if user.role != R.COMPETENT_AUTHORITY:
        own_or_supervisor(user, c)
    if body.to_state == "DISPOSED":
        _gate_for_close(db, c, user)
    svc.transition(db, c, user, body.to_state, body.remark, body.owner_user_id)
    db.commit()
    return complaint_row(c, _maps(db), has_overlap_ids(db))


def _gate_for_close(db: Session, c: Complaint, user: User):
    """Closing a case is a regulatory action: the Action Gate must have been decided first."""
    if not c.institution_id:
        return
    g = gate_check(db, c.institution_id, c.id, c.unit_id)
    if g["result"] == "CONFLICT":
        ok = db.scalar(select(GateCheck).where(
            GateCheck.complaint_id == c.id, GateCheck.action_type == "CLOSE_CASE",
            GateCheck.actor_user_id == user.id, GateCheck.choice.is_not(None)))
        if ok is None:
            raise ApiError(409, "gate_required",
                           "Another unit has a conflicting action on this institution. "
                           "Run the Action Gate and record a decision before closing.",
                           gate=g)


class TransferIn(BaseModel):
    target_unit_id: str
    remark: str


@router.post("/complaints/{cid}/transfer")
def do_transfer(cid: str, body: TransferIn, db: Session = Depends(get_db),
                user: User = Depends(require(*OFFICERS, R.ADMIN))):
    c = get_complaint(db, cid)
    own_or_supervisor(user, c)
    svc.transfer(db, c, user, body.target_unit_id, body.remark)
    db.commit()
    return complaint_row(c, _maps(db), has_overlap_ids(db))


class EscalateIn(BaseModel):
    level: int
    to_user_id: str | None = None
    reason: str


@router.post("/complaints/{cid}/escalate")
def do_escalate(cid: str, body: EscalateIn, db: Session = Depends(get_db),
                user: User = Depends(require(*OFFICERS))):
    c = get_complaint(db, cid)
    own_or_supervisor(user, c)
    if body.to_user_id is None:
        target_role = R.UNIT_SUPERVISOR if body.level == 2 else R.COMPETENT_AUTHORITY
        q = select(User).where(User.role == target_role, User.is_active.is_(True))
        if body.level == 2:
            q = q.where(User.unit_id == c.unit_id)
        t = db.scalar(q)
        body.to_user_id = t.id if t else None
    svc.escalate(db, c, user, body.level, body.to_user_id, body.reason)
    db.commit()
    return complaint_row(c, _maps(db), has_overlap_ids(db))


class NextActionIn(BaseModel):
    text: str = Field(min_length=3)
    due_on: date | None = None


@router.post("/complaints/{cid}/next-action")
def next_action(cid: str, body: NextActionIn, db: Session = Depends(get_db),
                user: User = Depends(require(*OFFICERS, R.ADMIN))):
    c = get_complaint(db, cid)
    own_or_supervisor(user, c)
    svc.set_next_action(db, c, user, body.text, body.due_on)
    db.commit()
    return complaint_row(c, _maps(db), has_overlap_ids(db))


class RemarkIn(BaseModel):
    text: str = Field(min_length=1)


@router.post("/complaints/{cid}/remarks", status_code=201)
def remark(cid: str, body: RemarkIn, db: Session = Depends(get_db),
           user: User = Depends(require(*OFFICERS, R.ADMIN))):
    c = get_complaint(db, cid)
    own_or_supervisor(user, c)
    svc.add_remark(db, c, user, body.text)
    db.commit()
    return {"ok": True}


@router.get("/escalations")
def escalations(db: Session = Depends(get_db),
                user: User = Depends(require(R.UNIT_SUPERVISOR, R.COMPETENT_AUTHORITY, R.MANAGEMENT, R.ADMIN))):
    rows = list(db.scalars(select(Complaint).where(Complaint.state == "ESCALATED")))
    if user.role == R.UNIT_SUPERVISOR:
        rows = [c for c in rows if c.unit_id == user.unit_id and c.escalation_level == 2]
    if user.role == R.COMPETENT_AUTHORITY:
        rows = [c for c in rows if c.escalation_level == 3]
    m, ov = _maps(db), has_overlap_ids(db)
    return {"items": [complaint_row(c, m, ov) for c in rows]}


# ---------- dashboard ----------
@router.get("/dashboard/summary")
def d_summary(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return dash.summary(db, user)


@router.get("/dashboard/by-institution")
def d_inst(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return {"items": dash.by_institution(db, user)}


@router.get("/dashboard/ageing")
def d_age(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return {"items": dash.ageing(db, user)}


@router.get("/dashboard/workload")
def d_work(db: Session = Depends(get_db), user: User = Depends(require(R.MANAGEMENT, *OFFICERS, R.ADMIN, R.COMPETENT_AUTHORITY))):
    rows = dash.scoped(db, user)
    units = {u.id: u.code for u in db.scalars(select(Unit))}
    users = {u.id: u.name for u in db.scalars(select(User))}
    openr = [c for c in rows if c.state in OPEN_STATES]
    by_unit: dict[str, int] = {}
    by_owner: dict[str, int] = {}
    for c in openr:
        by_unit[units[c.unit_id]] = by_unit.get(units[c.unit_id], 0) + 1
        if c.owner_user_id:
            by_owner[users[c.owner_user_id]] = by_owner.get(users[c.owner_user_id], 0) + 1
    return {"by_unit": [{"unit": k, "open": v} for k, v in sorted(by_unit.items())],
            "by_owner": [{"owner": k, "open": v} for k, v in sorted(by_owner.items(), key=lambda x: -x[1])]}


# ---------- overlaps ----------
def overlap_row(o: Overlap, m, db: Session, brief: bool = False) -> dict:
    units, cats, insts, users = m
    a, b = db.get(Complaint, o.complaint_a_id), db.get(Complaint, o.complaint_b_id)

    def side(c: Complaint) -> dict:
        return {"id": c.id, "case_id": c.case_id, "unit": units[c.unit_id].code, "title": c.title,
                "state": c.state, "category": cats[c.category_id].name,
                "last_action_text": c.last_action_text, "received_on": c.received_on.isoformat()}
    row = {"id": o.id, "institution_id": o.institution_id,
           "institution": insts[o.institution_id].canonical_name, "type": o.overlap_type,
           "severity": o.severity, "match_score": o.match_score, "status": o.status,
           "detected_at": o.detected_at.isoformat(), "a": side(a), "b": side(b),
           "label": "Potential Overlapping Cases – Coordination Required"}
    if not brief:
        row["receipt"] = o.receipt_json
        row["decision_reason"] = o.decision_reason
    return row


@router.get("/overlaps")
def list_overlaps(status: str | None = None, severity: str | None = None,
                  institution_id: str | None = None, unit: str | None = None,
                  db: Session = Depends(get_db),
                  user: User = Depends(require(*OFFICERS, R.MANAGEMENT, R.ADMIN, R.AUDITOR, R.COMPETENT_AUTHORITY))):
    m = _maps(db)
    q = select(Overlap).order_by(Overlap.detected_at.desc())
    rows = [o for o in db.scalars(q)
            if (not status or o.status == status) and (not severity or o.severity == severity)
            and (not institution_id or o.institution_id == institution_id)]
    items = [overlap_row(o, m, db, brief=True) for o in rows]
    if unit:
        items = [i for i in items if unit in (i["a"]["unit"], i["b"]["unit"])]
    return {"items": items, "total": len(items)}


@router.get("/overlaps/{oid}")
def get_overlap(oid: str, db: Session = Depends(get_db),
                _: User = Depends(require(*OFFICERS, R.MANAGEMENT, R.ADMIN, R.AUDITOR, R.COMPETENT_AUTHORITY))):
    o = db.get(Overlap, oid)
    if o is None:
        raise ApiError(404, "not_found", "Overlap not found.")
    return overlap_row(o, _maps(db), db)


class DecisionIn(BaseModel):
    decision: str
    reason: str = Field(min_length=3)
    save_alias: bool = False


@router.post("/overlaps/{oid}/decision")
def decide_overlap(oid: str, body: DecisionIn, db: Session = Depends(get_db),
                   user: User = Depends(require(*OFFICERS, R.COMPETENT_AUTHORITY, R.ADMIN))):
    o = db.get(Overlap, oid)
    if o is None:
        raise ApiError(404, "not_found", "Overlap not found.")
    status = {"CONFIRM": "CONFIRMED", "DISMISS": "DISMISSED", "LINK": "LINKED", "UNLINK": "UNLINKED"}.get(body.decision)
    if status is None:
        raise ApiError(422, "invalid_decision", "Decision must be CONFIRM, DISMISS, LINK or UNLINK.")
    if body.decision == "UNLINK" and o.status not in ("CONFIRMED", "LINKED"):
        raise ApiError(409, "invalid_transition", "Only a confirmed or linked overlap can be unlinked.")
    o.status, o.decided_by, o.decided_at, o.decision_reason = status, user.id, svc.now(), body.reason
    write_audit(db, user.id, f"OVERLAP_{status}", "overlap", o.id, {"reason": body.reason})
    for cid in (o.complaint_a_id, o.complaint_b_id):
        c = db.get(Complaint, cid)
        svc.add_event(db, c, "OVERLAP_LINKED", user, f"Overlap {status.lower()}: {body.reason}")
    db.commit()
    return overlap_row(o, _maps(db), db)


# ---------- Action Gate ----------
class GateIn(BaseModel):
    institution_id: str | None = None
    complaint_id: str | None = None
    action_type: str = "ISSUE_NOTICE"


@router.post("/gate/check")
def gate_run(body: GateIn, db: Session = Depends(get_db),
             user: User = Depends(require(*OFFICERS, R.COMPETENT_AUTHORITY))):
    c = get_complaint(db, body.complaint_id) if body.complaint_id else None
    inst_id = body.institution_id or (c.institution_id if c else None)
    if not inst_id:
        raise ApiError(422, "institution_required", "Choose an institution or a case that has one.")
    res = gate_check(db, inst_id, c.id if c else None, user.unit_id)
    chk = GateCheck(actor_user_id=user.id, institution_id=inst_id, complaint_id=c.id if c else None,
                    action_type=body.action_type, result=res["result"], snapshot_json=res)
    db.add(chk)
    db.flush()
    write_audit(db, user.id, "GATE_CHECKED", "gate_check", chk.id,
                {"result": res["result"], "action": body.action_type, "cases_shown": len(res["other_cases"])})
    db.commit()
    return {"check_id": chk.id, **res, "action_type": body.action_type,
            "choices": ["REQUEST_COORDINATION", "LINK", "PROCEED"] if res["result"] != "CLEAR" else ["PROCEED"]}


class GateDecisionIn(BaseModel):
    choice: str
    justification: str | None = None


@router.post("/gate/{check_id}/decision")
def gate_decide(check_id: str, body: GateDecisionIn, db: Session = Depends(get_db),
                user: User = Depends(require(*OFFICERS, R.COMPETENT_AUTHORITY))):
    chk = db.get(GateCheck, check_id)
    if chk is None or chk.actor_user_id != user.id:
        raise ApiError(404, "not_found", "Gate check not found.")
    if body.choice not in ("REQUEST_COORDINATION", "LINK", "PROCEED"):
        raise ApiError(422, "invalid_choice", "Choice must be REQUEST_COORDINATION, LINK or PROCEED.")
    if body.choice == "PROCEED" and chk.result == "CONFLICT" and len((body.justification or "").strip()) < 15:
        raise ApiError(422, "justification_required",
                       "Proceeding despite a conflict needs a written justification (at least 15 characters).")
    chk.choice, chk.justification, chk.decided_at = body.choice, body.justification, svc.now()
    if body.choice == "REQUEST_COORDINATION" and chk.complaint_id:
        c = db.get(Complaint, chk.complaint_id)
        c.on_hold_for_coordination = True
        svc.add_event(db, c, "COORDINATION_REQUESTED", user, body.justification or "Coordination requested")
    write_audit(db, user.id, "GATE_DECIDED", "gate_check", chk.id,
                {"choice": body.choice, "result": chk.result, "justification": body.justification})
    db.commit()
    return {"check_id": chk.id, "result": chk.result, "choice": chk.choice}


# ---------- audit ----------
@router.get("/audit")
def audit(action: str | None = None, entity_type: str | None = None,
          limit: int = Query(100, le=500), db: Session = Depends(get_db),
          _: User = Depends(require(R.AUDITOR, R.ADMIN, R.COMPETENT_AUTHORITY))):
    q = select(AuditLog).order_by(AuditLog.seq.desc()).limit(limit)
    if action:
        q = q.where(AuditLog.action == action)
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    users = {u.id: u.name for u in db.scalars(select(User))}
    return {"items": [{"seq": a.seq, "at": a.occurred_at.isoformat(),
                       "actor": users.get(a.actor_user_id, "System"), "action": a.action,
                       "entity_type": a.entity_type, "entity_id": a.entity_id,
                       "payload": a.payload_json, "entry_hash": a.entry_hash} for a in db.scalars(q)]}


@router.get("/audit/verify")
def audit_verify(db: Session = Depends(get_db),
                 _: User = Depends(require(R.AUDITOR, R.ADMIN, R.COMPETENT_AUTHORITY))):
    return verify_chain(db)


# ---------- reports (json / csv) ----------
@router.get("/reports/{kind}")
def report(kind: str, format: str = "json", institution_id: str | None = None,
           db: Session = Depends(get_db),
           user: User = Depends(require(R.MANAGEMENT, R.ADMIN, R.COMPETENT_AUTHORITY, R.AUDITOR, *OFFICERS))):
    m = _maps(db)
    units, cats, insts, _ = m
    regions = {r.id: r.code for r in db.scalars(select(Region))}
    rows = dash.scoped(db, user)
    today = date.today()

    def group(keyf, label):
        out: dict[str, dict] = {}
        for c in rows:
            k = keyf(c) or "Unresolved"
            g = out.setdefault(k, {label: k, "total": 0, "open": 0, "disposed": 0, "overdue": 0, "escalated": 0})
            g["total"] += 1
            g["open"] += c.state in OPEN_STATES
            g["disposed"] += c.state == "DISPOSED"
            g["overdue"] += dash.is_overdue(c, today)
            g["escalated"] += c.state == "ESCALATED"
        for g in out.values():
            g["disposal_rate"] = round(g["disposed"] / g["total"], 3) if g["total"] else 0
        return sorted(out.values(), key=lambda g: -g["total"])

    if kind == "by_unit":
        data = group(lambda c: units[c.unit_id].code, "unit")
    elif kind == "by_region":
        data = group(lambda c: regions.get(insts[c.institution_id].region_id) if c.institution_id else None, "region")
    elif kind == "by_status":
        data = group(lambda c: c.state, "status")
    elif kind == "by_category":
        data = group(lambda c: cats[c.category_id].name, "category")
    elif kind == "by_institution":
        data = group(lambda c: insts[c.institution_id].canonical_name if c.institution_id else None, "institution")
    elif kind == "ageing":
        data = dash.ageing(db, user)
    elif kind == "disposal_rate":
        t = len(rows)
        data = [{"total": t, "disposed": sum(c.state == "DISPOSED" for c in rows),
                 "disposal_rate": round(sum(c.state == "DISPOSED" for c in rows) / t, 3) if t else 0}]
    elif kind == "overlaps":
        data = list_overlaps(None, None, None, None, db, user)["items"]
        data = [{"institution": o["institution"], "type": o["type"], "severity": o["severity"], "status": o["status"],
                 "case_a": o["a"]["case_id"], "unit_a": o["a"]["unit"], "case_b": o["b"]["case_id"], "unit_b": o["b"]["unit"]} for o in data]
    elif kind == "institution_history":
        if not institution_id:
            raise ApiError(422, "institution_required", "institution_id is required for this report.")
        data = [complaint_row(c, m, {}) for c in rows if c.institution_id == institution_id]
        data = [{k: r[k] for k in ("case_id", "unit", "category", "state", "received_on", "last_action_text")} for r in data]
    else:
        raise ApiError(404, "unknown_report", "Unknown report kind.")
    if format == "csv":
        buf = io.StringIO()
        buf.write("# SYNTHETIC DATA - generated for demonstration only\n")
        if data:
            w = csv.DictWriter(buf, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)
        return Response(buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={kind}.csv"})
    return {"kind": kind, "generated_at": datetime.now(UTC).isoformat(), "synthetic": True,
            "caption": dash.scope_caption(db, user), "rows": data}


# ---------- resolve an unmatched case (officer decision + Alias Memory) ----------
class LinkInstitutionIn(BaseModel):
    institution_id: str
    save_alias: bool = True


@router.post("/complaints/{cid}/institution")
def link_institution(cid: str, body: LinkInstitutionIn, db: Session = Depends(get_db),
                     user: User = Depends(require(*OFFICERS, R.ADMIN))):
    c = get_complaint(db, cid)
    own_or_supervisor(user, c)
    inst = db.get(Institution, body.institution_id)
    if inst is None:
        raise ApiError(404, "not_found", "Institution not found.")
    if c.institution_id:
        raise ApiError(409, "already_linked", "This case is already linked to a college.")
    c.institution_id = inst.id
    saved = False
    raw = (c.institution_text_raw or "").strip()
    if body.save_alias and raw and normalize(raw) != inst.normalized_name:
        n = normalize(raw)
        if not db.scalar(select(InstitutionAlias).where(
                InstitutionAlias.institution_id == inst.id, InstitutionAlias.normalized_alias == n)):
            db.add(InstitutionAlias(institution_id=inst.id, alias=raw, normalized_alias=n,
                                    source="officer_confirmed", confirmed_by=user.id, confirmed_at=svc.now()))
            saved = True
    svc.add_event(db, c, "REMARK", user, f"Linked to college: {inst.canonical_name}",
                  payload={"alias_saved": saved})
    from app.engine.overlap import scan_complaint
    new = scan_complaint(db, c, user.id)
    db.commit()
    return {"complaint": complaint_row(c, _maps(db), has_overlap_ids(db)), "alias_saved": saved,
            "new_overlaps": len(new)}
