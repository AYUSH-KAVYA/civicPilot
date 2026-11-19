"""
CivicPilot Data Schemas
Source of truth for all data models and interfaces defined in docs/CONTRACT.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums (CONTRACT.md Section 3)
# ---------------------------------------------------------------------------

class CaseStatus(str, Enum):
    NEW = "NEW"
    INTAKE = "INTAKE"
    TRIAGED = "TRIAGED"
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    AT_RISK = "AT_RISK"
    NEEDS_HUMAN = "NEEDS_HUMAN"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"


class Urgency(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class RiskTier(str, Enum):
    routine = "routine"      # auto
    sensitive = "sensitive"  # auto + logged + supervisor notified
    critical = "critical"    # needs officer approval


class StepStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"
    skipped = "skipped"
    awaiting_approval = "awaiting_approval"


class Phase(str, Enum):
    perceive = "perceive"
    reason = "reason"
    plan = "plan"
    act = "act"
    evaluate = "evaluate"
    adapt = "adapt"
    guardrail = "guardrail"
    tool_call = "tool_call"
    tool_result = "tool_result"
    message = "message"


class AgentName(str, Enum):
    orchestrator = "orchestrator"
    intake = "intake"
    triage = "triage"
    planner = "planner"
    action = "action"
    evaluator = "evaluator"
    sandbox = "sandbox"
    citizen = "citizen"
    officer = "officer"
    system = "system"


class Channel(str, Enum):
    web = "web"
    chat = "chat"
    voice = "voice"
    email = "email"


class ApprovalDecision(str, Enum):
    approve = "approve"
    reject = "reject"


# ---------------------------------------------------------------------------
# Case Sub-Models (CONTRACT.md Section 4)
# ---------------------------------------------------------------------------

class CitizenInfo(BaseModel):
    contact_masked: str
    language: str = "en"


class RawInput(BaseModel):
    text: str
    image_urls: List[str] = Field(default_factory=list)
    lat: Optional[float] = None
    lng: Optional[float] = None
    address_text: Optional[str] = None
    channel: Channel = Channel.web


class LocationInfo(BaseModel):
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None


class IntakeData(BaseModel):
    category: str
    summary: str
    location: LocationInfo
    visible_damage: List[str] = Field(default_factory=list)
    nearby_sensitive_sites: List[str] = Field(default_factory=list)
    language_detected: str = "en"
    missing_info: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class TriageData(BaseModel):
    urgency: Urgency
    department_id: str
    ward_id: str
    office_id: str
    deadline_hours: float
    policy_refs: List[str] = Field(default_factory=list)
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)


class StepFallback(BaseModel):
    tool: str
    args: Dict[str, Any] = Field(default_factory=dict)


class PlanStep(BaseModel):
    id: str
    title: str
    tool: str
    args: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    due_at: Optional[datetime] = None
    fallback: Optional[StepFallback] = None
    risk_tier: RiskTier = RiskTier.routine
    status: StepStatus = StepStatus.pending
    result: Optional[Any] = None


class Plan(BaseModel):
    version: int = 1
    steps: List[PlanStep] = Field(default_factory=list)


class Ticket(BaseModel):
    id: str
    department_id: str
    status: str = "open"
    crew_id: Optional[str] = None
    priority: str = "medium"
    due_at: Optional[datetime] = None
    notes: List[str] = Field(default_factory=list)


class CaseFlags(BaseModel):
    needs_human: bool = False
    human_reason: Optional[str] = None
    reopen_count: int = 0
    merged_into: Optional[str] = None
    duplicate_of: List[str] = Field(default_factory=list)


class CaseState(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    status: CaseStatus = CaseStatus.NEW
    deadline_at: Optional[datetime] = None
    citizen: CitizenInfo
    raw: RawInput
    intake: Optional[IntakeData] = None
    triage: Optional[TriageData] = None
    plan: Optional[Plan] = None
    tickets: List[Ticket] = Field(default_factory=list)
    flags: CaseFlags = Field(default_factory=CaseFlags)

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Audit Events (CONTRACT.md Section 5)
# ---------------------------------------------------------------------------

class CaseEvent(BaseModel):
    id: str
    case_id: str
    ts: datetime
    agent: AgentName
    phase: Phase
    summary: str
    detail: Optional[Dict[str, Any]] = None
    tool_name: Optional[str] = None
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Agent Results (CONTRACT.md Section 6)
# ---------------------------------------------------------------------------

class AgentResult(BaseModel):
    state_patch: Dict[str, Any] = Field(default_factory=dict)
    next: Optional[str] = None
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------

class Approval(BaseModel):
    id: str
    case_id: str
    step_id: Optional[str] = None
    risk_tier: RiskTier = RiskTier.critical
    status: str = "pending"  # pending, approved, rejected
    rationale: Optional[str] = None
    requested_at: datetime
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# REST API Request/Response Schemas (CONTRACT.md Section 7)
# ---------------------------------------------------------------------------

class CaseCreateResponse(BaseModel):
    case_id: str
    access_token: str


class CaseCreateJSON(BaseModel):
    text: str
    image_urls: List[str] = Field(default_factory=list)
    lat: Optional[float] = None
    lng: Optional[float] = None
    address_text: Optional[str] = None
    language: str = "en"
    contact: str  # raw contact (email or phone)
    channel: Channel = Channel.web


class CitizenMessageRequest(BaseModel):
    text: str
    image_urls: List[str] = Field(default_factory=list)


class CitizenConfirmRequest(BaseModel):
    confirmed: bool
    comment: Optional[str] = None


class ApprovalDecisionRequest(BaseModel):
    decision: ApprovalDecision
    note: Optional[str] = None


class OfficerResolveRequest(BaseModel):
    note: str


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str


class SandboxRejectRequest(BaseModel):
    reason: str


class SandboxCrewCheckinRequest(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    notes: Optional[str] = None


class SandboxCrewNoShowRequest(BaseModel):
    reason: Optional[str] = None


class SandboxRepairPhotoRequest(BaseModel):
    photo_url: str
    notes: Optional[str] = None


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class MetricsSummary(BaseModel):
    total_cases: int
    cases_by_status: Dict[str, int]
    cases_by_department: Dict[str, int]
    cases_by_urgency: Dict[str, int]
    avg_time_to_first_action_sec: float
    open_approvals: int
    active_tickets: int


class Notification(BaseModel):
    id: str
    case_id: str
    channel: str
    template: str
    vars: Dict[str, Any] = Field(default_factory=dict)
    recipient_masked: str
    status: str
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Crew(BaseModel):
    id: str
    department_id: str
    name: str
    lat: float
    lng: float
    status: str = "available"  # available, assigned, offline
    contact: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class Ward(BaseModel):
    id: str
    name: str
    office_id: str
    boundary_geojson: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class Office(BaseModel):
    id: str
    name: str
    ward_id: str
    address: str
    lat: float
    lng: float

    model_config = ConfigDict(from_attributes=True)


class Department(BaseModel):
    id: str
    name: str
    code: str
    contact_email: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
