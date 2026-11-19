from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class PlanFallback(BaseModel):
    tool: str
    args: dict = Field(default_factory=dict)


class PlanStep(BaseModel):
    id: str
    title: str
    tool: str
    args: dict = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    due_at: str
    fallback: Optional[PlanFallback] = None
    risk_tier: str
    status: str = "pending"
    result: Any = None


class Plan(BaseModel):
    version: int = 1
    steps: list[PlanStep] = Field(default_factory=list)


async def run(state: Any, ctx: Any) -> Any:
    plan = await build_plan(state, ctx)
    await ctx.emit(
        getattr(state, "id", "unknown"),
        "planner",
        "plan",
        "Built resilient resolution plan",
        {"plan": plan.model_dump()},
    )
    try:
        triage = getattr(state, "triage", None)
        triage = triage.model_dump() if hasattr(triage, "model_dump") else triage or {}
        risk_tier = "critical" if triage.get("urgency") == "critical" else "sensitive"
    except Exception:
        risk_tier = "routine"
    if risk_tier == "critical":
        for step in plan.steps:
            if step.tool in ("create_ticket", "assign_crew"):
                step.risk_tier = "critical"
    return type("PlanAgentResult", (), {
        "state_patch": {"status": "PLANNED", "plan": plan.model_dump()},
        "next": "action",
        "confidence": 0.9,
    })()


async def build_plan(state: Any, ctx: Any) -> Plan:
    now = _now(ctx)
    triage = getattr(state, "triage", None)
    triage = triage.model_dump() if hasattr(triage, "model_dump") else triage or {}
    deadline_hours = int(triage.get("deadline_hours", 72))
    case_id = getattr(state, "id", "unknown")
    department = triage.get("department_id", "roads")
    urgency = triage.get("urgency", "medium")
    risk = "critical" if urgency == "critical" else "sensitive" if urgency == "high" else "routine"

    def iso(hours: int) -> str:
        return (now + timedelta(hours=hours)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    steps = [
        PlanStep(id="create-ticket", title="Create department ticket", tool="create_ticket",
                  args={"department_id": department, "priority": urgency, "case_id": case_id},
                  due_at=iso(max(1, deadline_hours // 12)),
                  fallback=PlanFallback(tool="notify", args={"template": "ticket_creation_retry"}),
                  risk_tier=risk),
        PlanStep(id="assign-crew", title="Assign nearest suitable crew", tool="assign_crew",
                  args={"crew_id": "nearest", "department_id": department},
                  depends_on=["create-ticket"], due_at=iso(max(2, deadline_hours // 6)),
                  fallback=PlanFallback(tool="notify", args={"template": "crew_assignment_delay"}),
                  risk_tier=risk),
        PlanStep(id="notify-citizen", title="Notify citizen of resolution plan", tool="notify",
                  args={"channel": "chat", "template": "plan_received", "case_id": case_id},
                  depends_on=["create-ticket"], due_at=iso(1),
                  fallback=PlanFallback(tool="notify", args={"channel": "sms", "template": "plan_received"}),
                  risk_tier="sensitive"),
        PlanStep(id="schedule-check", title="Schedule repair verification check", tool="schedule_check",
                  args={"case_id": case_id, "reason": "verify_resolution"},
                  depends_on=["assign-crew"], due_at=iso(max(4, deadline_hours // 2)),
                  fallback=PlanFallback(tool="notify", args={"template": "verification_reschedule"}),
                  risk_tier="routine"),
    ]
    return Plan(version=1, steps=steps)


async def replan(state: Any, reason: str, evidence: dict) -> Plan:
    current = getattr(state, "plan", None)
    if hasattr(current, "model_dump"):
        plan_data = current.model_dump()
        current = Plan.model_validate(plan_data)
    elif isinstance(current, dict):
        current = Plan.model_validate(current)
    else:
        current = Plan(version=1)

    completed = {step.id: step for step in current.steps if step.status == "done"}
    remaining = [step for step in current.steps if step.status != "done"]
    now = _now_from_state(state)
    due = (now + timedelta(hours=24)).isoformat().replace("+00:00", "Z")

    if evidence.get("disruption") == "ticket_rejection":
        replacement = PlanStep(
            id="retry-ticket", title="Retry ticket through escalation office",
            tool="create_ticket", args={"escalated": True, "reason": reason},
            depends_on=[], due_at=due, fallback=PlanFallback(tool="notify", args={"template": "officer_escalation"}),
            risk_tier="sensitive",
        )
        remaining.insert(0, replacement)
    elif evidence.get("disruption") in ("crew_no_show", "crew_checked_in"):
        replacement = PlanStep(
            id="reassign-crew", title="Reassign or check crew status",
            tool="assign_crew", args={"crew_id": "nearest", "reason": reason},
            depends_on=["create-ticket"], due_at=due,
            fallback=PlanFallback(tool="notify", args={"template": "crew_reassignment"}),
            risk_tier="sensitive",
        )
        remaining.insert(1, replacement)

    kept = list(completed.values())
    for step in kept:
        remaining = [item for item in remaining if item.id != step.id]
    plan = Plan(version=current.version + 1, steps=kept + remaining)
    return plan


def _now(ctx):
    clock = getattr(ctx, "clock", None)
    if clock is not None:
        now = clock.now() if hasattr(clock, "now") else getattr(clock, "now", None)
        if callable(now):
            value = now()
            if hasattr(value, "astimezone"):
                return value
    try:
        from core.clock import now
        value = now()
        if hasattr(value, "astimezone"):
            return value
    except Exception:
        pass
    return datetime.now(timezone.utc)


def _now_from_state(state):
    updated = getattr(state, "updated_at", None)
    if isinstance(updated, datetime):
        return updated
    return datetime.now(timezone.utc)
