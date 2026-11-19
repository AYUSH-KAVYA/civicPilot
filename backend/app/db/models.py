"""
SQLAlchemy ORM Models for CivicPilot.
Covers: cases, citizens, case_events, tickets, crews, departments, wards, offices,
notifications, approvals, timers, policy_chunks, case_embeddings, eval_runs, eval_results.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from backend.app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class CompatibleVector(TypeDecorator):
    """
    Transparently uses pgvector.sqlalchemy.Vector(768) on PostgreSQL,
    and falls back to JSON on SQLite/other dialects.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(768))
            except Exception:
                return dialect.type_descriptor(JSON())
        return dialect.type_descriptor(JSON())


# ---------------------------------------------------------------------------
# Organization & Master Data
# ---------------------------------------------------------------------------

class DepartmentModel(Base):
    __tablename__ = "departments"

    id = Column(String(64), primary_key=True)  # e.g. "water", "roads"
    name = Column(String(128), nullable=False)
    code = Column(String(32), nullable=False, unique=True)
    contact_email = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    sla_hours_default = Column(Float, default=24.0)

    crews = relationship("CrewModel", back_populates="department")
    policy_chunks = relationship("PolicyChunkModel", back_populates="department")


class WardModel(Base):
    __tablename__ = "wards"

    id = Column(String(64), primary_key=True)  # e.g. "ward-1"
    name = Column(String(128), nullable=False)
    office_id = Column(String(64), nullable=True)
    boundary_geojson = Column(JSON, nullable=False)  # GeoJSON Polygon/MultiPolygon


class OfficeModel(Base):
    __tablename__ = "offices"

    id = Column(String(64), primary_key=True)  # e.g. "office-ward-1"
    name = Column(String(128), nullable=False)
    ward_id = Column(String(64), ForeignKey("wards.id"), nullable=True, index=True)
    address = Column(String(255), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)


class CrewModel(Base):
    __tablename__ = "crews"

    id = Column(String(64), primary_key=True)  # e.g. "crew-water-01"
    department_id = Column(String(64), ForeignKey("departments.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    status = Column(String(32), default="available", index=True)  # available, assigned, offline
    contact = Column(String(128), nullable=True)

    department = relationship("DepartmentModel", back_populates="crews")
    tickets = relationship("TicketModel", back_populates="crew")


# ---------------------------------------------------------------------------
# Grievance Cases & Citizens
# ---------------------------------------------------------------------------

class CaseModel(Base):
    __tablename__ = "cases"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    status = Column(String(32), nullable=False, default="NEW", index=True)
    urgency = Column(String(16), nullable=True, index=True)
    department_id = Column(String(64), ForeignKey("departments.id"), nullable=True, index=True)
    ward_id = Column(String(64), ForeignKey("wards.id"), nullable=True, index=True)
    office_id = Column(String(64), ForeignKey("offices.id"), nullable=True)
    deadline_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # State JSON containing full CaseState schema
    state = Column(JSON, nullable=False)

    citizen = relationship("CitizenModel", back_populates="case", uselist=False, cascade="all, delete-orphan")
    events = relationship("CaseEventModel", back_populates="case", cascade="all, delete-orphan", order_by="CaseEventModel.ts")
    tickets = relationship("TicketModel", back_populates="case", cascade="all, delete-orphan")
    notifications = relationship("NotificationModel", back_populates="case", cascade="all, delete-orphan")
    approvals = relationship("ApprovalModel", back_populates="case", cascade="all, delete-orphan")
    timers = relationship("TimerModel", back_populates="case", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_cases_status_dept", "status", "department_id"),
    )


class CitizenModel(Base):
    __tablename__ = "citizens"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    raw_contact = Column(String(255), nullable=False)  # stored separately from masked
    masked_contact = Column(String(255), nullable=False)
    language = Column(String(16), default="en", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    case = relationship("CaseModel", back_populates="citizen")


class CaseEventModel(Base):
    __tablename__ = "case_events"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    agent = Column(String(32), nullable=False)
    phase = Column(String(32), nullable=False)
    summary = Column(String(512), nullable=False)
    detail = Column(JSON, nullable=True)
    tool_name = Column(String(64), nullable=True)
    reason = Column(Text, nullable=True)

    case = relationship("CaseModel", back_populates="events")

    __table_args__ = (
        Index("idx_case_events_case_ts", "case_id", "ts"),
    )


class TicketModel(Base):
    __tablename__ = "tickets"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(String(64), ForeignKey("departments.id"), nullable=False, index=True)
    crew_id = Column(String(64), ForeignKey("crews.id"), nullable=True, index=True)
    status = Column(String(32), default="open", nullable=False, index=True)
    priority = Column(String(16), default="medium", nullable=False)
    due_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    case = relationship("CaseModel", back_populates="tickets")
    crew = relationship("CrewModel", back_populates="tickets")


class NotificationModel(Base):
    __tablename__ = "notifications"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(32), nullable=False)  # sms, chat, email
    template = Column(String(64), nullable=False)
    vars = Column(JSON, default=dict, nullable=False)
    recipient_masked = Column(String(255), nullable=False)
    status = Column(String(32), default="sent", nullable=False)  # queued, sent, failed
    sent_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    case = relationship("CaseModel", back_populates="notifications")


class ApprovalModel(Base):
    __tablename__ = "approvals"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id = Column(String(64), nullable=True)
    risk_tier = Column(String(32), default="critical", nullable=False)
    status = Column(String(32), default="pending", nullable=False, index=True)  # pending, approved, rejected
    rationale = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decided_by = Column(String(128), nullable=True)
    note = Column(Text, nullable=True)

    case = relationship("CaseModel", back_populates="approvals")


class TimerModel(Base):
    __tablename__ = "timers"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    run_at = Column(DateTime(timezone=True), nullable=False, index=True)
    reason = Column(String(255), nullable=False)
    status = Column(String(32), default="pending", nullable=False, index=True)  # pending, fired, cancelled
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    case = relationship("CaseModel", back_populates="timers")


class PolicyChunkModel(Base):
    __tablename__ = "policy_chunks"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    department_id = Column(String(64), ForeignKey("departments.id"), nullable=False, index=True)
    doc_title = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    sla_hours = Column(Float, nullable=True)
    escalation_rule = Column(Text, nullable=True)
    embedding = Column(CompatibleVector, nullable=True)

    department = relationship("DepartmentModel", back_populates="policy_chunks")


class CaseEmbeddingModel(Base):
    __tablename__ = "case_embeddings"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    embedding = Column(CompatibleVector, nullable=True)


class EvalRunModel(Base):
    __tablename__ = "eval_runs"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    name = Column(String(128), nullable=False)
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), default="running", nullable=False)  # running, completed, failed
    config = Column(JSON, default=dict, nullable=False)

    results = relationship("EvalResultModel", back_populates="run", cascade="all, delete-orphan")


class EvalResultModel(Base):
    __tablename__ = "eval_results"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    run_id = Column(String(64), ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(64), nullable=True, index=True)
    metric = Column(String(64), nullable=False)
    score = Column(Float, nullable=False)
    details = Column(JSON, default=dict, nullable=False)

    run = relationship("EvalRunModel", back_populates="results")
