"""
CivicPilot Guardrails: Risk Tiers Enforcement
Enforces safety rules across the 3 risk tiers:
- routine: auto execution
- sensitive: auto execution + logged audit event + supervisor notification
- critical: requires officer approval, creates ApprovalModel, pauses until handle_approval resumes.
Source of truth: docs/CONTRACT.md Section 3.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.clock import now as clock_now
from backend.app.core.events import emit_event
from backend.app.db.models import ApprovalModel
from backend.app.db.session import AsyncSessionLocal
from backend.app.schemas import AgentName, Phase, PlanStep, RiskTier, StepStatus


class ApprovalRequiredException(Exception):
    """Raised when a critical tier step is paused waiting for human officer approval."""
    def __init__(self, approval_id: str, step_id: str, rationale: str) -> None:
        self.approval_id = approval_id
        self.step_id = step_id
        self.rationale = rationale
        super().__init__(f"Step '{step_id}' paused for critical approval (Approval ID: {approval_id})")


async def enforce_risk_tier(
    step: PlanStep | Dict[str, Any],
    case_id: str,
    ctx: Any = None,
    db: Optional[AsyncSession] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Evaluate step risk tier:
    - critical: creates ApprovalModel record, sets step status to awaiting_approval, emits guardrail event. Returns (requires_approval=True, approval_id).
    - sensitive: emits guardrail notification event, notifies supervisor. Returns (requires_approval=False, None).
    - routine: returns (requires_approval=False, None).
    """
    if isinstance(step, dict):
        step_id = step.get("id", "step-unknown")
        step_title = step.get("title", step_id)
        raw_tier = step.get("risk_tier", "routine")
    else:
        step_id = step.id
        step_title = step.title
        raw_tier = step.risk_tier

    tier_str = raw_tier.value if isinstance(raw_tier, RiskTier) else str(raw_tier).lower()
    session = db or getattr(ctx, "db", None)

    if tier_str == RiskTier.critical.value:
        # Create approval record
        approval_id = f"appr-{uuid.uuid4().hex[:8]}"
        rationale = f"Critical risk action '{step_title}' ({step_id}) requires human officer approval before execution."

        # Mark step as awaiting_approval
        if isinstance(step, dict):
            step["status"] = StepStatus.awaiting_approval.value
        else:
            step.status = StepStatus.awaiting_approval

        async def _persist_approval(s: AsyncSession) -> None:
            approval_record = ApprovalModel(
                id=approval_id,
                case_id=case_id,
                step_id=step_id,
                risk_tier=RiskTier.critical.value,
                status="pending",
                rationale=rationale,
                requested_at=clock_now(),
            )
            s.add(approval_record)
            await s.commit()

        if session is not None:
            await _persist_approval(session)
        else:
            async with AsyncSessionLocal() as new_session:
                await _persist_approval(new_session)

        # Emit guardrail audit event
        await emit_event(
            case_id=case_id,
            agent=AgentName.action,
            phase=Phase.guardrail,
            summary=f"Critical risk tier guardrail: Approval requested for step '{step_title}'",
            detail={
                "approval_id": approval_id,
                "step_id": step_id,
                "step_title": step_title,
                "risk_tier": "critical",
                "rationale": rationale,
            },
            tool_name="approval",
            reason=rationale,
            db=session,
        )

        return True, approval_id

    elif tier_str == RiskTier.sensitive.value:
        # Sensitive tier: auto-runs but logs event and notifies supervisor
        await emit_event(
            case_id=case_id,
            agent=AgentName.action,
            phase=Phase.guardrail,
            summary=f"Sensitive risk tier guardrail: Supervisor notified for step '{step_title}'",
            detail={
                "step_id": step_id,
                "step_title": step_title,
                "risk_tier": "sensitive",
                "notification_type": "supervisor_notice",
            },
            tool_name="notify",
            reason="Step classified as sensitive tier",
            db=session,
        )

        # Notify tool invocation if tools available
        tools = getattr(ctx, "tools", None)
        if tools and hasattr(tools, "call"):
            try:
                await tools.call(
                    "notify",
                    {
                        "case_id": case_id,
                        "channel": "chat",
                        "template": "supervisor_alert",
                        "vars": {"step": step_title, "step_id": step_id},
                    },
                    case_id=case_id,
                    agent=AgentName.action,
                    db=session,
                )
            except Exception:
                pass  # tool call failure handled gracefully

        return False, None

    else:
        # Routine: auto allowed
        return False, None
