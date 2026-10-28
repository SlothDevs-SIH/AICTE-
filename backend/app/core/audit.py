"""Hash-chained audit log (BACKEND_PLAN section 8). Tamper-evident, not tamper-proof."""
import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog

GENESIS = "0" * 64


def _canon(d: dict) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), default=str)


def _digest(prev: str, seq: int, at: str, actor, action, etype, eid, payload) -> str:
    body = _canon({"seq": seq, "at": at, "actor": actor, "action": action,
                   "etype": etype, "eid": eid, "payload": payload})
    return hashlib.sha256((prev + body).encode()).hexdigest()


def write_audit(db: Session, actor_id, action: str, entity_type: str, entity_id: str,
                payload: dict | None = None) -> AuditLog:
    last = db.scalar(select(AuditLog).order_by(AuditLog.seq.desc()).limit(1))
    seq = (last.seq + 1) if last else 1
    prev = last.entry_hash if last else GENESIS
    now = datetime.now(UTC).replace(microsecond=0)
    payload = payload or {}
    h = _digest(prev, seq, now.isoformat(), actor_id, action, entity_type, entity_id, payload)
    row = AuditLog(seq=seq, occurred_at=now, actor_user_id=actor_id, action=action,
                   entity_type=entity_type, entity_id=entity_id, payload_json=payload,
                   prev_hash=prev, entry_hash=h)
    db.add(row)
    db.flush()
    return row


def verify_chain(db: Session) -> dict:
    prev, count = GENESIS, 0
    for row in db.scalars(select(AuditLog).order_by(AuditLog.seq)):
        count += 1
        at = (row.occurred_at if row.occurred_at.tzinfo else row.occurred_at.replace(tzinfo=UTC)).astimezone(UTC)
        expect = _digest(prev, row.seq, at.isoformat(), row.actor_user_id, row.action,
                         row.entity_type, row.entity_id, row.payload_json)
        if row.seq != count or row.prev_hash != prev or row.entry_hash != expect:
            return {"intact": False, "entries_checked": count, "first_broken_seq": row.seq,
                    "head_hash": prev}
        prev = row.entry_hash
    return {"intact": True, "entries_checked": count, "first_broken_seq": None, "head_hash": prev}
