"""Coordination, notifications, import, intelligence, admin, attachments, live stream, performance reports."""
import asyncio
import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require
from app.api.v1 import records as rec
from app.core import roles as R
from app.core.audit import write_audit
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import hash_password
from app.db.base import get_db, session_factory
from app.db.models import (
    Attachment, Category, Complaint, CoordinationMessage, CoordinationThread, CoordinationThreadComplaint,
    Institution, InstitutionAlias, ImportJob, Notification, Overlap, Setting, Unit, User,
)
from app.engine.normalize import normalize
from app.services import ask as ask_svc
from app.services import complaints as svc
from app.services import dashboard as dash
from app.services import imports as imp
from app.services import intelligence as intel
from app.services import notifications as notif
from app.services import pdfbrief, summary
from app.services.settings import DEFAULTS, all_settings

router = APIRouter()
OFF = R.OFFICER


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


# ---------- notifications ----------
@router.get("/notifications")
def my_notifications(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = list(db.scalars(select(Notification).where(Notification.user_id == user.id)
                           .order_by(Notification.created_at.desc()).limit(100)))
    return {"unread": sum(1 for n in rows if n.read_at is None),
            "items": [{"id": n.id, "kind": n.kind, "ref_type": n.ref_type, "ref_id": n.ref_id, "message": n.message,
                       "created_at": n.created_at.isoformat(), "read": n.read_at is not None} for n in rows]}


@router.post("/notifications/{nid}/read")
def read_notification(nid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    n = db.get(Notification, nid)
    if n is None or n.user_id != user.id:
        raise ApiError(404, "not_found", "Notification not found.")
    n.read_at = svc.now()
    db.commit()
    return {"ok": True}


@router.post("/admin/jobs/sla")
def run_sla(db: Session = Depends(get_db), user: User = Depends(require(R.ADMIN))):
    stats = notif.run_sla_job(db)
    write_audit(db, user.id, "SLA_JOB_RUN", "system", "sla", stats)
    db.commit()
    return stats


# ---------- coordination handshake ----------
class ThreadIn(BaseModel):
    complaint_ids: list[str] = Field(min_length=2)
    message: str = Field(min_length=3)


def _thread_row(db: Session, t: CoordinationThread, with_messages: bool = False) -> dict:
    units = {u.id: u.code for u in db.scalars(select(Unit))}
    users = {u.id: u for u in db.scalars(select(User))}
    cids = [x.complaint_id for x in db.scalars(select(CoordinationThreadComplaint).where(CoordinationThreadComplaint.thread_id == t.id))]
    cs = [db.get(Complaint, c) for c in cids]
    row = {"id": t.id, "status": t.status, "institution_id": t.institution_id,
           "institution": db.get(Institution, t.institution_id).canonical_name, "due_at": _utc(t.due_at).isoformat(),
           "outcome": t.outcome, "resolution_note": t.resolution_note, "opened_by": users[t.opened_by].name,
           "units": sorted({units[c.unit_id] for c in cs}),
           "cases": [{"id": c.id, "case_id": c.case_id, "unit": units[c.unit_id], "title": c.title} for c in cs]}
    if with_messages:
        row["messages"] = [{"id": m.id, "author": users[m.author_user_id].name,
                            "unit": units.get(users[m.author_user_id].unit_id), "body": m.body,
                            "posted_at": m.posted_at.isoformat()}
                           for m in db.scalars(select(CoordinationMessage).where(CoordinationMessage.thread_id == t.id)
                                               .order_by(CoordinationMessage.posted_at))]
    return row


def _participant_units(db: Session, t: CoordinationThread) -> set[str]:
    return {db.get(Complaint, x.complaint_id).unit_id for x in db.scalars(
        select(CoordinationThreadComplaint).where(CoordinationThreadComplaint.thread_id == t.id))}


def _can_see_thread(db: Session, user: User, t: CoordinationThread) -> bool:
    return user.role in (R.MANAGEMENT, R.ADMIN, R.AUDITOR, R.COMPETENT_AUTHORITY) or user.unit_id in _participant_units(db, t)


@router.get("/coordination")
def list_threads(db: Session = Depends(get_db), user: User = Depends(require(*OFF, R.MANAGEMENT, R.ADMIN, R.AUDITOR, R.COMPETENT_AUTHORITY))):
    rows = [t for t in db.scalars(select(CoordinationThread).order_by(CoordinationThread.created_at.desc())) if _can_see_thread(db, user, t)]
    return {"items": [_thread_row(db, t) for t in rows]}


@router.post("/coordination", status_code=201)
def open_thread(body: ThreadIn, db: Session = Depends(get_db), user: User = Depends(require(*OFF))):
    cs = [rec.get_complaint(db, c) for c in body.complaint_ids]
    if len({c.institution_id for c in cs}) != 1 or cs[0].institution_id is None:
        raise ApiError(422, "different_institutions", "All cases must belong to the same college.")
    if len({c.unit_id for c in cs}) < 2:
        raise ApiError(422, "one_unit", "A coordination thread needs cases from at least two units.")
    if user.unit_id not in {c.unit_id for c in cs} and user.role != R.REGIONAL_OFFICER:
        raise ApiError(403, "forbidden", "You can only open a thread that includes a case from your own unit.")
    days = int(all_settings(db)["coordination_days"])
    t = CoordinationThread(institution_id=cs[0].institution_id, opened_by=user.id, due_at=svc.now() + timedelta(days=days))
    db.add(t)
    db.flush()
    for c in cs:
        db.add(CoordinationThreadComplaint(thread_id=t.id, complaint_id=c.id))
        c.on_hold_for_coordination = True
        svc.add_event(db, c, "COORDINATION_REQUESTED", user, body.message)
    db.add(CoordinationMessage(thread_id=t.id, author_user_id=user.id, body=body.message, posted_at=svc.now()))
    for other in {c.unit_id for c in cs} - {user.unit_id}:
        for officer in db.scalars(select(User).where(User.unit_id == other, User.role.in_((R.UNIT_OFFICER, R.UNIT_SUPERVISOR)))):
            notif.notify(db, officer.id, "COORDINATION_REQUEST", "coordination", t.id,
                         f"{user.name} asked to coordinate on {db.get(Institution, t.institution_id).canonical_name}", dedupe_hours=1)
    write_audit(db, user.id, "COORDINATION_OPENED", "coordination", t.id, {"cases": [c.case_id for c in cs]})
    db.commit()
    return _thread_row(db, t, True)


@router.get("/coordination/{tid}")
def get_thread(tid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = db.get(CoordinationThread, tid)
    if t is None or not _can_see_thread(db, user, t):
        raise ApiError(404, "not_found", "Thread not found.")
    return _thread_row(db, t, True)


class MessageIn(BaseModel):
    body: str = Field(min_length=1)


@router.post("/coordination/{tid}/messages", status_code=201)
def post_message(tid: str, body: MessageIn, db: Session = Depends(get_db), user: User = Depends(require(*OFF))):
    t = db.get(CoordinationThread, tid)
    if t is None or user.unit_id not in _participant_units(db, t):
        raise ApiError(404, "not_found", "Thread not found.")
    if t.status != "OPEN":
        raise ApiError(409, "thread_closed", "This thread is closed.")
    db.add(CoordinationMessage(thread_id=t.id, author_user_id=user.id, body=body.body, posted_at=svc.now()))
    for u in _participant_units(db, t) - {user.unit_id}:
        for officer in db.scalars(select(User).where(User.unit_id == u, User.role.in_((R.UNIT_OFFICER, R.UNIT_SUPERVISOR)))):
            notif.notify(db, officer.id, "COORDINATION_MESSAGE", "coordination", t.id, f"New note from {user.name}", dedupe_hours=1)
    db.commit()
    return _thread_row(db, t, True)


class ResolveIn(BaseModel):
    outcome: str
    note: str = Field(min_length=3)


@router.post("/coordination/{tid}/resolve")
def resolve_thread(tid: str, body: ResolveIn, db: Session = Depends(get_db), user: User = Depends(require(*OFF))):
    t = db.get(CoordinationThread, tid)
    if t is None or user.unit_id not in _participant_units(db, t):
        raise ApiError(404, "not_found", "Thread not found.")
    if body.outcome not in ("PROCEED_TOGETHER", "DEFER_TO_A", "DEFER_TO_B", "NOT_RELATED"):
        raise ApiError(422, "invalid_outcome", "Unknown outcome.")
    if t.status != "OPEN":
        raise ApiError(409, "thread_closed", "This thread is already closed.")
    t.status, t.outcome, t.resolution_note = "RESOLVED", body.outcome, body.note
    for x in db.scalars(select(CoordinationThreadComplaint).where(CoordinationThreadComplaint.thread_id == t.id)):
        c = db.get(Complaint, x.complaint_id)
        c.on_hold_for_coordination = False
        svc.add_event(db, c, "REMARK", user, f"Coordination resolved: {body.outcome.replace('_', ' ').lower()}. {body.note}")
    write_audit(db, user.id, "COORDINATION_RESOLVED", "coordination", t.id, {"outcome": body.outcome, "note": body.note})
    db.commit()
    return _thread_row(db, t, True)


# ---------- intelligence ----------
@router.get("/clusters")
def get_clusters(db: Session = Depends(get_db), _: User = Depends(require(R.MANAGEMENT, R.ADMIN, R.COMPETENT_AUTHORITY, *OFF))):
    return {"items": intel.clusters(db)}


@router.get("/risk/ranking")
def risk_ranking(limit: int = Query(15, le=100), db: Session = Depends(get_db),
                 _: User = Depends(require(R.MANAGEMENT, R.ADMIN, R.AUDITOR, R.COMPETENT_AUTHORITY))):
    return {"items": intel.ranking(db, limit), "note": "Score is a ranking aid based on complaint data only."}


@router.get("/institutions/{iid}/risk")
def inst_risk(iid: str, db: Session = Depends(get_db), _: User = Depends(require(R.MANAGEMENT, R.ADMIN, R.AUDITOR, R.COMPETENT_AUTHORITY))):
    i = db.get(Institution, iid)
    if i is None:
        raise ApiError(404, "not_found", "Institution not found.")
    return intel.risk_score(db, i)


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=300)


@router.post("/ask")
def ask(body: AskIn, db: Session = Depends(get_db), _: User = Depends(require(*OFF, R.MANAGEMENT, R.ADMIN, R.COMPETENT_AUTHORITY))):
    return ask_svc.ask(db, body.question)


@router.post("/overlaps/{oid}/summary")
def overlap_summary(oid: str, db: Session = Depends(get_db), _: User = Depends(require(*OFF, R.MANAGEMENT, R.ADMIN, R.COMPETENT_AUTHORITY))):
    o = db.get(Overlap, oid)
    if o is None:
        raise ApiError(404, "not_found", "Overlap not found.")
    return summary.summarise(db, o)


@router.get("/overlaps/{oid}/brief.pdf")
def overlap_brief(oid: str, db: Session = Depends(get_db), user: User = Depends(require(*OFF, R.MANAGEMENT, R.ADMIN, R.COMPETENT_AUTHORITY))):
    o = db.get(Overlap, oid)
    if o is None:
        raise ApiError(404, "not_found", "Overlap not found.")
    write_audit(db, user.id, "BRIEF_EXPORTED", "overlap", o.id, {})
    db.commit()
    return Response(pdfbrief.brief_pdf(db, o, user.name), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=joint-case-brief-{o.id[:8]}.pdf"})


@router.get("/complaints/{cid}/overlaps")
def complaint_overlaps(cid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = rec.get_complaint(db, cid)
    m = rec._maps(db)
    rows = db.scalars(select(Overlap).where(or_(Overlap.complaint_a_id == c.id, Overlap.complaint_b_id == c.id)))
    return {"items": [rec.overlap_row(o, m, db, brief=True) for o in rows]}


# ---------- institutions (admin) ----------
class InstIn(BaseModel):
    canonical_name: str = Field(min_length=3)
    aicte_id: str | None = None
    state: str | None = None
    district: str | None = None
    pincode: str | None = None
    region_code: str | None = None
    address: str | None = None
    type: str | None = None


@router.post("/institutions", status_code=201)
def create_inst(body: InstIn, db: Session = Depends(get_db), user: User = Depends(require(R.ADMIN))):
    from app.db.models import Region
    if body.aicte_id and db.scalar(select(Institution).where(Institution.aicte_id == body.aicte_id)):
        raise ApiError(409, "duplicate_aicte_id", "That AICTE ID already exists.")
    reg = db.scalar(select(Region).where(Region.code == body.region_code)) if body.region_code else None
    i = Institution(aicte_id=body.aicte_id, canonical_name=body.canonical_name, normalized_name=normalize(body.canonical_name),
                    state=body.state, district=body.district, pincode=body.pincode, address=body.address, type=body.type,
                    region_id=reg.id if reg else None, is_synthetic=True)
    db.add(i)
    db.flush()
    write_audit(db, user.id, "INSTITUTION_CREATED", "institution", i.id, {"name": i.canonical_name})
    db.commit()
    return {"id": i.id, "name": i.canonical_name}


@router.patch("/institutions/{iid}")
def patch_inst(iid: str, body: dict, db: Session = Depends(get_db), user: User = Depends(require(R.ADMIN))):
    i = db.get(Institution, iid)
    if i is None:
        raise ApiError(404, "not_found", "Institution not found.")
    for k in ("canonical_name", "state", "district", "pincode", "address", "type", "short_name"):
        if k in body and isinstance(body[k], str):
            setattr(i, k, body[k])
    if "canonical_name" in body:
        i.normalized_name = normalize(i.canonical_name)
    write_audit(db, user.id, "INSTITUTION_UPDATED", "institution", i.id, {k: body[k] for k in body if k != "id"})
    db.commit()
    return {"id": i.id, "name": i.canonical_name}


@router.delete("/institutions/{iid}/aliases/{alias_id}", status_code=204)
def delete_alias(iid: str, alias_id: str, db: Session = Depends(get_db), user: User = Depends(require(R.ADMIN))):
    a = db.get(InstitutionAlias, alias_id)
    if a is None or a.institution_id != iid:
        raise ApiError(404, "not_found", "Alias not found.")
    write_audit(db, user.id, "ALIAS_REMOVED", "institution", iid, {"alias": a.alias})
    db.delete(a)
    db.commit()


# ---------- complaint edit + attachments ----------
@router.patch("/complaints/{cid}")
def patch_complaint(cid: str, body: dict, db: Session = Depends(get_db), user: User = Depends(require(*OFF, R.ADMIN))):
    c = rec.get_complaint(db, cid)
    rec.own_or_supervisor(user, c)
    changed = {}
    for k in ("title", "description", "priority"):
        if isinstance(body.get(k), str) and body[k].strip():
            setattr(c, k, body[k])
            changed[k] = body[k]
    if body.get("expected_disposal_on"):
        if not str(body.get("remark", "")).strip():
            raise ApiError(422, "remark_required", "A remark is required to change the expected disposal date.")
        c.expected_disposal_on = date.fromisoformat(body["expected_disposal_on"])
        changed["expected_disposal_on"] = body["expected_disposal_on"]
    if not changed:
        raise ApiError(422, "nothing_to_change", "No editable field was provided.")
    svc.add_event(db, c, "REMARK", user, body.get("remark") or "Case details edited", payload={"changed": list(changed)})
    db.commit()
    return rec.complaint_row(c, rec._maps(db), rec.has_overlap_ids(db))


ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "text/plain"}


@router.post("/complaints/{cid}/attachments", status_code=201)
async def add_attachment(cid: str, file: UploadFile = File(...), db: Session = Depends(get_db),
                         user: User = Depends(require(*OFF, R.ADMIN))):
    c = rec.get_complaint(db, cid)
    rec.own_or_supervisor(user, c)
    data = await file.read()
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise ApiError(413, "file_too_large", "File is too large.")
    if file.content_type not in ALLOWED_TYPES:
        raise ApiError(415, "unsupported_type", "Only PDF, PNG, JPEG and plain text files are accepted.")
    sha = hashlib.sha256(data).hexdigest()
    folder = Path("data/uploads")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / sha).write_bytes(data)
    a = Attachment(complaint_id=c.id, filename=(file.filename or "file")[:255], content_type=file.content_type,
                   size_bytes=len(data), sha256=sha, storage_key=sha, uploaded_by=user.id)
    db.add(a)
    svc.add_event(db, c, "REMARK", user, f"Attached {a.filename}", payload={"sha256": sha})
    db.commit()
    return {"id": a.id, "filename": a.filename, "size_bytes": a.size_bytes, "sha256": sha}


@router.get("/complaints/{cid}/attachments")
def list_attachments(cid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = rec.get_complaint(db, cid)
    if not rec.can_see_detail(db, user, c):
        raise ApiError(403, "forbidden", "Details visible after coordination is accepted.")
    return {"items": [{"id": a.id, "filename": a.filename, "size_bytes": a.size_bytes, "sha256": a.sha256}
                      for a in db.scalars(select(Attachment).where(Attachment.complaint_id == c.id))]}


# ---------- import wizard ----------
@router.post("/imports", status_code=201)
async def upload_import(file: UploadFile = File(...), unit_id: str | None = Form(None), db: Session = Depends(get_db),
                        user: User = Depends(require(R.ADMIN, *OFF))):
    uid = unit_id if user.role == R.ADMIN and unit_id else user.unit_id
    if not uid:
        raise ApiError(422, "unit_required", "Choose the unit these cases belong to.")
    job = imp.create_job(db, user, uid, file.filename or "upload.csv", await file.read(), get_settings().max_upload_mb)
    db.commit()
    return _job_row(job, with_sample=True)


def _job_row(j: ImportJob, with_sample=False) -> dict:
    d = {"id": j.id, "filename": j.filename, "status": j.status, "columns": j.columns_json, "mapping": j.mapping_json,
         "rows_total": j.rows_total, "rows_ok": j.rows_ok, "rows_error": j.rows_error, "report": j.report_json,
         "fields": imp.FIELDS, "required": imp.REQUIRED}
    if with_sample:
        d["sample"] = j.raw_rows_json[:5]
    return d


def _job(db: Session, jid: str, user: User) -> ImportJob:
    j = db.get(ImportJob, jid)
    if j is None or (user.role != R.ADMIN and j.created_by != user.id):
        raise ApiError(404, "not_found", "Import not found.")
    return j


class MapIn(BaseModel):
    mapping: dict[str, str | None]


@router.post("/imports/{jid}/map")
def map_import(jid: str, body: MapIn, db: Session = Depends(get_db), user: User = Depends(require(R.ADMIN, *OFF))):
    j = _job(db, jid, user)
    if j.status == "COMMITTED":
        raise ApiError(409, "already_committed", "This import is already committed.")
    bad = [v for v in body.mapping.values() if v and v not in j.columns_json]
    if bad:
        raise ApiError(422, "unknown_column", f"Column not in the file: {bad[0]}")
    j.mapping_json = {f: body.mapping.get(f) for f in imp.FIELDS}
    j.status = "UPLOADED"
    db.commit()
    return _job_row(j)


@router.post("/imports/{jid}/dry-run")
def dry_run_import(jid: str, db: Session = Depends(get_db), user: User = Depends(require(R.ADMIN, *OFF))):
    j = _job(db, jid, user)
    imp.dry_run(db, j)
    db.commit()
    return _job_row(j)


@router.post("/imports/{jid}/commit")
def commit_import(jid: str, db: Session = Depends(get_db), user: User = Depends(require(R.ADMIN))):
    j = _job(db, jid, user)
    imp.commit(db, j, user)
    db.commit()
    return _job_row(j)


@router.get("/imports/{jid}")
def get_import(jid: str, db: Session = Depends(get_db), user: User = Depends(require(R.ADMIN, *OFF))):
    return _job_row(_job(db, jid, user))


# ---------- admin: users, settings, scenarios, AI switches ----------
@router.get("/admin/users")
def admin_users(db: Session = Depends(get_db), _: User = Depends(require(R.ADMIN))):
    units = {u.id: u.code for u in db.scalars(select(Unit))}
    return {"items": [{"id": u.id, "email": u.email, "name": u.name, "role": u.role, "unit": units.get(u.unit_id),
                       "is_active": u.is_active} for u in db.scalars(select(User).order_by(User.name))]}


class UserIn(BaseModel):
    email: str
    name: str
    role: str
    password: str = Field(min_length=10)
    unit_code: str | None = None


@router.post("/admin/users", status_code=201)
def admin_create_user(body: UserIn, db: Session = Depends(get_db), user: User = Depends(require(R.ADMIN))):
    if body.role not in R.ALL_ROLES:
        raise ApiError(422, "invalid_role", "Unknown role.")
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise ApiError(409, "duplicate_email", "A user with that email already exists.")
    unit = db.scalar(select(Unit).where(Unit.code == body.unit_code)) if body.unit_code else None
    if body.role in (R.UNIT_OFFICER, R.UNIT_SUPERVISOR) and unit is None:
        raise ApiError(422, "unit_required", "Unit officers and supervisors need a unit.")
    u = User(email=body.email.lower(), name=body.name, role=body.role, password_hash=hash_password(body.password),
             unit_id=unit.id if unit else None)
    db.add(u)
    db.flush()
    write_audit(db, user.id, "USER_CREATED", "user", u.id, {"email": u.email, "role": u.role})
    db.commit()
    return {"id": u.id}


@router.patch("/admin/users/{uid}")
def admin_patch_user(uid: str, body: dict, db: Session = Depends(get_db), user: User = Depends(require(R.ADMIN))):
    u = db.get(User, uid)
    if u is None:
        raise ApiError(404, "not_found", "User not found.")
    if u.id == user.id and body.get("is_active") is False:
        raise ApiError(409, "self_lockout", "You cannot deactivate your own account.")
    if "role" in body:
        if body["role"] not in R.ALL_ROLES:
            raise ApiError(422, "invalid_role", "Unknown role.")
        u.role = body["role"]
    if "is_active" in body:
        u.is_active = bool(body["is_active"])
    write_audit(db, user.id, "USER_UPDATED", "user", u.id, {k: body[k] for k in ("role", "is_active") if k in body})
    db.commit()
    return {"id": u.id, "role": u.role, "is_active": u.is_active}


@router.get("/admin/settings")
def get_settings_all(db: Session = Depends(get_db), _: User = Depends(require(R.ADMIN))):
    return {"items": all_settings(db)}


@router.put("/admin/settings/{key}")
def put_setting(key: str, body: dict, db: Session = Depends(get_db), user: User = Depends(require(R.ADMIN))):
    if key not in DEFAULTS:
        raise ApiError(404, "unknown_setting", "Unknown setting.")
    if "value" not in body or type(body["value"]) is not type(DEFAULTS[key]):
        raise ApiError(422, "invalid_value", f"Value must be of type {type(DEFAULTS[key]).__name__}.")
    row = db.scalar(select(Setting).where(Setting.key == key))
    old = row.value_json if row else DEFAULTS[key]
    if row:
        row.value_json, row.updated_by = body["value"], user.id
    else:
        db.add(Setting(key=key, value_json=body["value"], updated_by=user.id))
    write_audit(db, user.id, "SETTING_CHANGED", "setting", key, {"old": old, "new": body["value"]})
    db.commit()
    return {"key": key, "value": body["value"]}


@router.post("/admin/ai/{feature}")
def ai_switch(feature: str, body: dict, db: Session = Depends(get_db), user: User = Depends(require(R.ADMIN))):
    key = {"llm": "ai_llm_enabled", "embeddings": "ai_embeddings_enabled"}.get(feature)
    if key is None:
        raise ApiError(404, "unknown_feature", "Unknown AI feature.")
    return put_setting(key, {"value": bool(body.get("enabled"))}, db, user)


SCENARIOS = {
    "conflict_demo": "Two units act on the same new college: RB records a show-cause notice, PGRC opens a case.",
    "variant_name_demo": "PGRC receives a complaint that spells a college name differently from the registry entry RB already uses.",
    "sla_pressure_demo": "A case that is already past its time limit with no next action.",
}


@router.get("/admin/scenarios")
def list_scenarios(_: User = Depends(require(R.ADMIN))):
    return {"items": [{"id": k, "description": v} for k, v in SCENARIOS.items()]}


@router.post("/admin/scenarios/{sid}/load")
def load_scenario(sid: str, db: Session = Depends(get_db), user: User = Depends(require(R.ADMIN))):
    if sid not in SCENARIOS:
        raise ApiError(404, "unknown_scenario", "Unknown scenario.")
    if db.scalar(select(Complaint).where(Complaint.is_synthetic.is_(False)).limit(1)):
        raise ApiError(409, "real_data_present", "Scenarios load only into a database that holds synthetic data alone.")
    from app.engine.institution import resolve
    rb, pg = (db.scalar(select(Unit).where(Unit.code == c)) for c in ("RB", "PGRC"))
    cat = db.scalar(select(Category).where(Category.code == "UNAPPROVED_INTAKE"))
    tag = hashlib.sha1(f"{sid}{datetime.now(UTC).isoformat()}".encode()).hexdigest()[:6]
    inst = Institution(canonical_name=f"Demo Scenario Institute {tag.upper()}, Pune", normalized_name=normalize(f"Demo Scenario Institute {tag}, Pune"),
                       state="Maharashtra", district="Pune", aicte_id=f"9-{int(tag, 16)}", is_synthetic=True)
    db.add(inst)
    db.flush()
    officer = db.scalar(select(User).where(User.unit_id == rb.id, User.role == R.UNIT_OFFICER))
    c1 = svc.create_complaint(db, officer, unit_id=rb.id, reference_no=f"RB/SCN/{tag}", category_id=cat.id, title="Admissions above approved intake",
                              description="Scenario case", institution_id=inst.id, institution_text_raw=inst.canonical_name, aicte_id_raw=None)
    c1.state, c1.owner_user_id = "UNDER_PROCESS", officer.id
    if sid in ("conflict_demo", "variant_name_demo"):
        c1.last_action_text = "Show-cause notice issued" if sid == "conflict_demo" else "Reply sought from institution"
    if sid == "sla_pressure_demo":
        c1.due_on = c1.expected_disposal_on = date.today() - timedelta(days=12)
    else:
        text = inst.canonical_name if sid == "conflict_demo" else f"Demo Scenario Inst. {tag.upper()} Pune"
        po = db.scalar(select(User).where(User.unit_id == pg.id, User.role == R.UNIT_OFFICER))
        c2 = svc.create_complaint(db, po, unit_id=pg.id, reference_no=f"PGRC/SCN/{tag}", category_id=cat.id, title="Students report extra seats filled",
                                  description="Scenario case", institution_id=None, institution_text_raw=text, aicte_id_raw=None)
        iid, _, _ = resolve(db, text, None)
        c2.institution_id = iid
        c2.state, c2.owner_user_id = "UNDER_PROCESS", po.id
        from app.engine.overlap import scan_complaint
        scan_complaint(db, c2, user.id)
    write_audit(db, user.id, "SCENARIO_LOADED", "scenario", sid, {"institution": inst.canonical_name})
    db.commit()
    return {"loaded": sid, "institution_id": inst.id, "institution": inst.canonical_name}


# ---------- performance report (monthly / quarterly) ----------
@router.get("/reports/performance")
def performance(period: str = "monthly", date_from: date | None = None, date_to: date | None = None,
                db: Session = Depends(get_db), user: User = Depends(require(R.MANAGEMENT, R.ADMIN, R.COMPETENT_AUTHORITY, R.AUDITOR, *OFF))):
    if period not in ("monthly", "quarterly"):
        raise ApiError(422, "invalid_period", "period must be monthly or quarterly.")
    rows = dash.scoped(db, user)
    end = date_to or date.today()
    start = date_from or (end - timedelta(days=365))
    key = (lambda d: f"{d.year}-{d.month:02d}") if period == "monthly" else (lambda d: f"{d.year}-Q{(d.month - 1) // 3 + 1}")
    out: dict[str, dict] = {}
    for c in rows:
        if start <= c.received_on <= end:
            g = out.setdefault(key(c.received_on), {"period": key(c.received_on), "received": 0, "disposed": 0, "open": 0, "overdue": 0})
            g["received"] += 1
            g["disposed"] += c.state == "DISPOSED"
            g["open"] += c.state != "DISPOSED"
            g["overdue"] += dash.is_overdue(c, date.today())
    data = sorted(out.values(), key=lambda g: g["period"])
    for g in data:
        g["disposal_rate"] = round(g["disposed"] / g["received"], 3) if g["received"] else 0
    return {"period": period, "from": start.isoformat(), "to": end.isoformat(), "rows": data, "synthetic": True}


# ---------- live stream (Server-Sent Events) ----------
async def _events(request: Request, user_id: str, max_events: int | None):
    last, sent = None, 0
    while True:
        if await request.is_disconnected():
            return
        with session_factory()() as db:
            user = db.get(User, user_id)
            s = dash.summary(db, user)["counters"] if user else {}
            n = db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))) or 0
        payload = {"counters": s, "unread": n, "at": datetime.now(UTC).isoformat()}
        marker = json.dumps([s, n], sort_keys=True)
        kind = "counters_changed" if marker != last else "heartbeat"
        last = marker
        yield f"event: {kind}\ndata: {json.dumps(payload)}\n\n"
        sent += 1
        if max_events and sent >= max_events:
            return
        await asyncio.sleep(5 if max_events is None else 0.05)


@router.get("/stream")
async def stream(request: Request, max_events: int | None = Query(None, le=50), user: User = Depends(current_user)):
    return StreamingResponse(_events(request, user.id, max_events), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
