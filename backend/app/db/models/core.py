"""Schema from BACKEND_PLAN section 3. Portable types only (SQLite now, PostgreSQL later)."""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RowMixin

FK = lambda t: ForeignKey(f"{t}.id")  # noqa: E731


class Unit(RowMixin, Base):
    __tablename__ = "units"
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30))  # bureau | cell | regional


class Region(RowMixin, Base):
    __tablename__ = "regions"
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    states: Mapped[list] = mapped_column(JSON, default=list)


class Category(RowMixin, Base):
    __tablename__ = "categories"
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    severity_weight: Mapped[int] = mapped_column(Integer, default=1)
    sla_days: Mapped[int] = mapped_column(Integer, default=30)


class User(RowMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30))
    unit_id: Mapped[str | None] = mapped_column(FK("units"), nullable=True)
    region_id: Mapped[str | None] = mapped_column(FK("regions"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefreshToken(RowMixin, Base):
    __tablename__ = "refresh_tokens"
    user_id: Mapped[str] = mapped_column(FK("users"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Institution(RowMixin, Base):
    __tablename__ = "institutions"
    aicte_id: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    canonical_name: Mapped[str] = mapped_column(String(300))
    normalized_name: Mapped[str] = mapped_column(String(300), index=True)
    short_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    state: Mapped[str | None] = mapped_column(String(60), nullable=True)
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    region_id: Mapped[str | None] = mapped_column(FK("regions"), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (Index("ix_inst_state_district", "state", "district"),)


class InstitutionAlias(RowMixin, Base):
    __tablename__ = "institution_aliases"
    institution_id: Mapped[str] = mapped_column(FK("institutions"))
    alias: Mapped[str] = mapped_column(String(300))
    normalized_alias: Mapped[str] = mapped_column(String(300), index=True)
    source: Mapped[str] = mapped_column(String(30), default="seed")  # seed|import|officer_confirmed
    confirmed_by: Mapped[str | None] = mapped_column(FK("users"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("institution_id", "normalized_alias"),)


class Complaint(RowMixin, Base):
    __tablename__ = "complaints"
    case_id: Mapped[str] = mapped_column(String(30), unique=True)  # SMV-2026-000123
    reference_no: Mapped[str] = mapped_column(String(60))
    unit_id: Mapped[str] = mapped_column(FK("units"))
    institution_id: Mapped[str | None] = mapped_column(FK("institutions"), nullable=True)
    institution_text_raw: Mapped[str | None] = mapped_column(String(300), nullable=True)
    aicte_id_raw: Mapped[str | None] = mapped_column(String(40), nullable=True)
    category_id: Mapped[str] = mapped_column(FK("categories"))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    language_hint: Mapped[str | None] = mapped_column(String(10), nullable=True)
    received_on: Mapped[date] = mapped_column(Date)
    due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_disposal_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="RECEIVED", index=True)
    owner_user_id: Mapped[str | None] = mapped_column(FK("users"), nullable=True)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    escalated_to_user_id: Mapped[str | None] = mapped_column(FK("users"), nullable=True)
    last_action_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_action_by: Mapped[str | None] = mapped_column(FK("users"), nullable=True)
    next_action_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action_due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(10), default="NORMAL")
    source: Mapped[str] = mapped_column(String(10), default="manual")
    import_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    on_hold_for_coordination: Mapped[bool] = mapped_column(Boolean, default=False)
    complainant_name_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    complainant_phone_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    complainant_email_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("unit_id", "reference_no"),)


class ComplaintEvent(RowMixin, Base):
    __tablename__ = "complaint_events"
    complaint_id: Mapped[str] = mapped_column(FK("complaints"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    from_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    actor_user_id: Mapped[str | None] = mapped_column(FK("users"), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Setting(RowMixin, Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), unique=True)
    value_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
    updated_by: Mapped[str | None] = mapped_column(FK("users"), nullable=True)
