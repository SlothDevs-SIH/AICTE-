from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RowMixin


class Overlap(RowMixin, Base):
    __tablename__ = "overlaps"
    complaint_a_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"))
    complaint_b_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"))
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"))
    overlap_type: Mapped[str] = mapped_column(String(4))
    severity: Mapped[str] = mapped_column(String(10))  # CONFLICT | RELATED | SYSTEMIC
    match_score: Mapped[float] = mapped_column(Float)
    receipt_json: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(12), default="SUGGESTED")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    engine_version: Mapped[str] = mapped_column(String(20))
    __table_args__ = (UniqueConstraint("complaint_a_id", "complaint_b_id"),)


class GateCheck(RowMixin, Base):
    __tablename__ = "gate_checks"
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"))
    complaint_id: Mapped[str | None] = mapped_column(ForeignKey("complaints.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(30))
    result: Mapped[str] = mapped_column(String(10))
    snapshot_json: Mapped[dict] = mapped_column(JSON)
    choice: Mapped[str | None] = mapped_column(String(24), nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(RowMixin, Base):
    __tablename__ = "notifications"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    ref_type: Mapped[str] = mapped_column(String(20))
    ref_id: Mapped[str] = mapped_column(String(36))
    message: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(RowMixin, Base):
    __tablename__ = "audit_log"
    seq: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(40))
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(36))
    payload_json: Mapped[dict] = mapped_column(JSON)
    prev_hash: Mapped[str] = mapped_column(String(64))
    entry_hash: Mapped[str] = mapped_column(String(64))


class CoordinationThread(RowMixin, Base):
    __tablename__ = "coordination_threads"
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"))
    opened_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(10), default="OPEN")  # OPEN | RESOLVED | EXPIRED
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class CoordinationThreadComplaint(RowMixin, Base):
    __tablename__ = "coordination_thread_complaints"
    thread_id: Mapped[str] = mapped_column(ForeignKey("coordination_threads.id"), index=True)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"), index=True)


class CoordinationMessage(RowMixin, Base):
    __tablename__ = "coordination_messages"
    thread_id: Mapped[str] = mapped_column(ForeignKey("coordination_threads.id"), index=True)
    author_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Attachment(RowMixin, Base):
    __tablename__ = "attachments"
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(120))
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class ImportJob(RowMixin, Base):
    __tablename__ = "import_jobs"
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"))
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(12), default="UPLOADED")  # UPLOADED|DRY_RUN|COMMITTED|FAILED
    columns_json: Mapped[list] = mapped_column(JSON, default=list)
    mapping_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_rows_json: Mapped[list] = mapped_column(JSON, default=list)
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_ok: Mapped[int] = mapped_column(Integer, default=0)
    rows_error: Mapped[int] = mapped_column(Integer, default=0)
    report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
