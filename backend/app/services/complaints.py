"""Complaint lifecycle (BACKEND_PLAN 3.3). Every change writes an event and an audit entry."""
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.errors import ApiError
from app.db.models import Category, Complaint, ComplaintEvent, Unit, User
from app.engine.overlap import scan_complaint

# (from, to) -> roles allowed ("owner" handled in the router by scope)
TRANSITIONS = {
    ("RECEIVED", "ASSIGNED"), ("ASSIGNED", "UNDER_PROCESS"), ("UNDER_PROCESS", "TRANSFERRED"),
    ("TRANSFERRED", "ASSIGNED"), ("UNDER_PROCESS", "DISPOSED"), ("UNDER_PROCESS", "ESCALATED"),
    ("ESCALATED", "ESCALATED"), ("ESCALATED", "UNDER_PROCESS"), ("ESCALATED", "DISPOSED"),
    ("DISPOSED", "REOPENED"), ("REOPENED", "UNDER_PROCESS"),
}


def now() -> datetime:
    return datetime.now(UTC)


def add_event(db: Session, c: Complaint, kind: str, actor: User | None, remark: str | None = None,
              from_state: str | None = None, to_state: str | None = None, payload: dict | None = None):
    ev = ComplaintEvent(
        complaint_id=c.id, kind=kind, from_state=from_state, to_state=to_state,
        actor_user_id=actor.id if actor else None, remark=remark, payload_json=payload,
        occurred_at=now(),
    )
    db.add(ev)
    if kind in ("ACTION_TAKEN", "STATE_CHANGED", "TRANSFERRED", "ESCALATED", "DE_ESCALATED"):
        c.last_action_at = ev.occurred_at
        c.last_action_by = actor.id if actor else None
        c.last_action_text = remark or f"{kind.replace('_', ' ').title()}: {to_state or ''}".strip()
    write_audit(db, actor.id if actor else None, kind, "complaint", c.id,
                {"case_id": c.case_id, "from": from_state, "to": to_state, "remark": remark})


def next_case_id(db: Session) -> str:
    year = date.today().year
    n = db.scalar(select(func.count()).select_from(Complaint)) or 0
    return f"SMV-{year}-{n + 1:06d}"


def create_complaint(db: Session, actor: User | None, *, unit_id: str, reference_no: str,
                     category_id: str, title: str, description: str, institution_id: str | None,
                     institution_text_raw: str | None, aicte_id_raw: str | None,
                     received_on: date | None = None, priority: str = "NORMAL",
                     case_id: str | None = None, is_synthetic: bool = True) -> Complaint:
    cat = db.get(Category, category_id)
    if cat is None:
        raise ApiError(422, "unknown_category", "Category does not exist.")
    if db.get(Unit, unit_id) is None:
        raise ApiError(422, "unknown_unit", "Unit does not exist.")
    dup = db.scalar(select(Complaint).where(Complaint.unit_id == unit_id,
                                            Complaint.reference_no == reference_no))
    if dup:
        raise ApiError(409, "duplicate_reference", "This unit already has that reference number.")
    received = received_on or date.today()
    due = received + timedelta(days=cat.sla_days)
    c = Complaint(
        case_id=case_id or next_case_id(db), reference_no=reference_no, unit_id=unit_id,
        institution_id=institution_id, institution_text_raw=institution_text_raw,
        aicte_id_raw=aicte_id_raw, category_id=category_id, title=title, description=description,
        received_on=received, due_on=due, expected_disposal_on=due, state="RECEIVED",
        priority=priority, is_synthetic=is_synthetic,
    )
    db.add(c)
    db.flush()
    add_event(db, c, "RECEIVED", actor, to_state="RECEIVED")
    c.last_action_text, c.last_action_at = "Complaint received", now()
    scan_complaint(db, c, actor.id if actor else None)
    return c


def transition(db: Session, c: Complaint, actor: User, to_state: str, remark: str | None,
               owner_user_id: str | None = None) -> Complaint:
    if (c.state, to_state) not in TRANSITIONS:
        raise ApiError(409, "invalid_transition", f"Cannot move from {c.state} to {to_state}.",
                       **{"from": c.state, "to": to_state})
    if to_state in ("DISPOSED", "REOPENED", "TRANSFERRED") and not (remark or "").strip():
        raise ApiError(422, "remark_required", "A remark or reason is required for this change.")
    old = c.state
    if to_state == "ASSIGNED":
        c.owner_user_id = owner_user_id or actor.id
    if to_state == "UNDER_PROCESS" and old == "ESCALATED":
        c.escalation_level, c.escalated_to_user_id = 0, None
        c.state = to_state
        add_event(db, c, "DE_ESCALATED", actor, remark, old, to_state)
        return c
    c.state = to_state
    add_event(db, c, "STATE_CHANGED", actor, remark, old, to_state)
    return c


def transfer(db: Session, c: Complaint, actor: User, target_unit_id: str, remark: str) -> Complaint:
    if not (remark or "").strip():
        raise ApiError(422, "remark_required", "A remark is required to transfer a case.")
    target = db.get(Unit, target_unit_id)
    if target is None:
        raise ApiError(422, "unknown_unit", "Target unit does not exist.")
    if c.state not in ("UNDER_PROCESS", "ASSIGNED"):
        raise ApiError(409, "invalid_transition", f"Cannot transfer a case that is {c.state}.")
    old_unit = c.unit_id
    old_state = c.state
    c.state, c.unit_id, c.owner_user_id = "TRANSFERRED", target.id, None
    add_event(db, c, "TRANSFERRED", actor, remark, old_state, "TRANSFERRED",
              {"from_unit_id": old_unit, "to_unit_id": target.id})
    scan_complaint(db, c, actor.id)
    return c


def escalate(db: Session, c: Complaint, actor: User, level: int, to_user_id: str | None,
             reason: str) -> Complaint:
    if level not in (2, 3):
        raise ApiError(422, "invalid_level", "Escalation level must be 2 or 3.")
    if not (reason or "").strip():
        raise ApiError(422, "remark_required", "A reason is required to escalate.")
    if c.state == "ESCALATED" and level <= c.escalation_level:
        raise ApiError(409, "invalid_transition", "A case can only be escalated to a higher level.")
    if c.state not in ("UNDER_PROCESS", "ESCALATED"):
        raise ApiError(409, "invalid_transition", f"Cannot escalate a case that is {c.state}.")
    old = c.state
    c.state, c.escalation_level, c.escalated_to_user_id = "ESCALATED", level, to_user_id
    add_event(db, c, "ESCALATED", actor, reason, old, "ESCALATED", {"level": level})
    return c


def set_next_action(db: Session, c: Complaint, actor: User, text: str, due_on: date | None):
    c.next_action_text, c.next_action_due_on = text, due_on
    add_event(db, c, "NEXT_ACTION_SET", actor, text, payload={"due_on": str(due_on) if due_on else None})


def add_remark(db: Session, c: Complaint, actor: User, text: str):
    if not text.strip():
        raise ApiError(422, "remark_required", "Remark cannot be empty.")
    add_event(db, c, "REMARK", actor, text)
    if c.state == "ASSIGNED":
        transition(db, c, actor, "UNDER_PROCESS", "First remark added")
