"""In-app notifications and the SLA / reminder / escalation job (BACKEND_PLAN 7.3).

Escalation is advisory by default: the job tells a supervisor, a person escalates.
With the setting auto_escalate turned on, the job escalates to Level 2 and records actor "system".
"""
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.db.models import Complaint, ComplaintEvent, CoordinationThread, Notification, User
from app.services.settings import get_setting

OPEN = ("RECEIVED", "ASSIGNED", "UNDER_PROCESS", "ESCALATED", "REOPENED", "TRANSFERRED")


def _now() -> datetime:
    return datetime.now(UTC)


def notify(db: Session, user_id: str | None, kind: str, ref_type: str, ref_id: str, message: str,
           dedupe_hours: int = 24) -> Notification | None:
    """Create a notification unless the same one was sent recently or the daily budget is used up."""
    if not user_id:
        return None
    since = _now() - timedelta(hours=dedupe_hours)
    same = db.scalar(select(Notification).where(
        Notification.user_id == user_id, Notification.kind == kind, Notification.ref_id == ref_id,
        Notification.created_at >= since))
    if same:
        return None
    day = _now() - timedelta(hours=24)
    sent = db.scalar(select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id, Notification.created_at >= day, Notification.kind != "CONFLICT")) or 0
    if kind != "CONFLICT" and sent >= int(get_setting(db, "alert_budget_per_day")):
        return None  # alert budget (P8); CONFLICT alerts are never suppressed
    n = Notification(user_id=user_id, kind=kind, ref_type=ref_type, ref_id=ref_id, message=message)
    db.add(n)
    return n


def _supervisor(db: Session, unit_id: str) -> User | None:
    return db.scalar(select(User).where(User.role == "unit_supervisor", User.unit_id == unit_id,
                                        User.is_active.is_(True)))


def run_sla_job(db: Session, today: date | None = None) -> dict:
    today = today or date.today()
    remind = int(get_setting(db, "pending_reminder_days"))
    warn_frac = float(get_setting(db, "sla_warn_fraction"))
    grace = int(get_setting(db, "escalation_grace_days"))
    auto = bool(get_setting(db, "auto_escalate"))
    stats = {"reminders": 0, "sla_approaching": 0, "sla_breached": 0, "escalation_alerts": 0,
             "auto_escalated": 0, "threads_expired": 0}
    for c in db.scalars(select(Complaint).where(Complaint.state.in_(OPEN))):
        label = f"{c.case_id}: {c.title}"
        last = db.scalar(select(func.max(ComplaintEvent.occurred_at)).where(ComplaintEvent.complaint_id == c.id))
        idle = (_now() - (last if last and last.tzinfo else (last or _now()).replace(tzinfo=UTC))).days
        if c.state in ("RECEIVED", "ASSIGNED", "UNDER_PROCESS") and idle >= remind:
            if notify(db, c.owner_user_id, "REMINDER", "complaint", c.id,
                      f"No activity for {idle} days on {label}", dedupe_hours=remind * 24):
                stats["reminders"] += 1
        if c.due_on:
            total = max(1, (c.due_on - c.received_on).days)
            used = (today - c.received_on).days
            if today <= c.due_on and used / total >= warn_frac:
                if notify(db, c.owner_user_id, "SLA_APPROACHING", "complaint", c.id,
                          f"{int(used / total * 100)}% of the time limit used on {label} (due {c.due_on})"):
                    stats["sla_approaching"] += 1
            if today > c.due_on:
                sup = _supervisor(db, c.unit_id)
                a = notify(db, c.owner_user_id, "SLA_BREACHED", "complaint", c.id, f"Past time limit: {label} (due {c.due_on})")
                b = notify(db, sup.id if sup else None, "SLA_BREACHED", "complaint", c.id, f"Past time limit: {label} (due {c.due_on})")
                stats["sla_breached"] += bool(a or b)
                if (today - c.due_on).days > grace and c.state != "ESCALATED":
                    if auto and c.state == "UNDER_PROCESS":
                        c.state, c.escalation_level = "ESCALATED", 2
                        c.escalated_to_user_id = sup.id if sup else None
                        db.add(ComplaintEvent(complaint_id=c.id, kind="ESCALATED", from_state="UNDER_PROCESS",
                                              to_state="ESCALATED", actor_user_id=None, occurred_at=_now(),
                                              remark=f"Automatic escalation: more than {grace} days past due",
                                              payload_json={"level": 2, "actor": "system"}))
                        write_audit(db, None, "AUTO_ESCALATED", "complaint", c.id, {"case_id": c.case_id})
                        stats["auto_escalated"] += 1
                    elif notify(db, sup.id if sup else None, "ESCALATION_SUGGESTED", "complaint", c.id,
                                f"Consider escalating {label}: {(today - c.due_on).days} days past due"):
                        stats["escalation_alerts"] += 1
    for t in db.scalars(select(CoordinationThread).where(CoordinationThread.status == "OPEN")):
        due = t.due_at if t.due_at.tzinfo else t.due_at.replace(tzinfo=UTC)
        if due < _now():
            t.status = "EXPIRED"
            write_audit(db, None, "COORDINATION_EXPIRED", "coordination", t.id, {})
            opener = db.get(User, t.opened_by)
            sup = _supervisor(db, opener.unit_id) if opener and opener.unit_id else None
            notify(db, sup.id if sup else t.opened_by, "COORDINATION_EXPIRED", "coordination", t.id,
                   "A coordination request passed its deadline without an outcome")
            stats["threads_expired"] += 1
    db.commit()
    return stats
