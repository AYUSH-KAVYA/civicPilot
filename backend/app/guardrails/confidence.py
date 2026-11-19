"""
CivicPilot Guardrails: Confidence Threshold
Routes cases with confidence below CONFIDENCE_THRESHOLD to NEEDS_HUMAN with a structured reasoning packet.
Source of truth: docs/CONTRACT.md Section 1, 8.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from backend.app.core.config import get_settings
from backend.app.core.events import emit_event
from backend.app.schemas import AgentName, CaseState, CaseStatus, Phase


def is_low_confidence(confidence: float, threshold: Optional[float] = None) -> bool:
    """Check if a confidence score is below the configured threshold."""
    if threshold is None:
        threshold = get_settings().CONFIDENCE_THRESHOLD
    return float(confidence) < float(threshold)


def build_reasoning_packet(
    state: CaseState | Dict[str, Any],
    confidence: float,
    agent_name: str,
    threshold: Optional[float] = None,
    custom_rationale: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a comprehensive reasoning packet for human officer review."""
    if threshold is None:
        threshold = get_settings().CONFIDENCE_THRESHOLD

    raw_data: Dict[str, Any] = {}
    intake_data: Dict[str, Any] = {}
    triage_data: Dict[str, Any] = {}

    if isinstance(state, dict):
        raw_data = state.get("raw") or {}
        intake_data = state.get("intake") or {}
        triage_data = state.get("triage") or {}
        case_id = state.get("id", "unknown")
    else:
        raw_data = state.raw.model_dump() if state.raw else {}
        intake_data = state.intake.model_dump() if state.intake else {}
        triage_data = state.triage.model_dump() if state.triage else {}
        case_id = state.id

    missing_info = intake_data.get("missing_info", [])
    category = intake_data.get("category", "unclassified")
    text = raw_data.get("text", "")
    triage_rationale = triage_data.get("rationale") or custom_rationale or "Insufficient clarity in grievance text"

    packet = {
        "case_id": case_id,
        "flagged_by_agent": agent_name,
        "confidence": round(float(confidence), 3),
        "threshold": round(float(threshold), 3),
        "deficit": round(float(threshold) - float(confidence), 3),
        "grievance_snippet": text[:200] if text else "",
        "detected_category": category,
        "missing_information": missing_info,
        "triage_rationale": triage_rationale,
        "suggested_actions": [
            "Contact citizen for clarifying details",
            "Manually assign department and urgency",
            "Dispatch field inspector for site survey",
        ],
    }
    return packet


async def check_and_apply_confidence_guardrail(
    state: CaseState | Dict[str, Any],
    confidence: float,
    agent_name: AgentName | str,
    ctx: Any = None,
    threshold: Optional[float] = None,
    db: Any = None,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Evaluate confidence against CONFIDENCE_THRESHOLD.
    If below threshold:
    - Mutates state: status -> NEEDS_HUMAN, flags.needs_human -> True, flags.human_reason set.
    - Emits a Phase.guardrail audit event with the reasoning packet.
    Returns (triggered: bool, reasoning_packet: Optional[Dict]).
    """
    if threshold is None:
        threshold = get_settings().CONFIDENCE_THRESHOLD

    if not is_low_confidence(confidence, threshold):
        return False, None

    agent_str = agent_name.value if isinstance(agent_name, AgentName) else str(agent_name)
    packet = build_reasoning_packet(state, confidence, agent_str, threshold)

    reason = (
        f"Low confidence ({confidence:.2f} < {threshold:.2f}) from {agent_str} agent. "
        f"Reasoning: {packet.get('triage_rationale')}"
    )

    case_id = state.get("id") if isinstance(state, dict) else state.id

    # Mutate state
    if isinstance(state, dict):
        state["status"] = CaseStatus.NEEDS_HUMAN.value
        flags = state.setdefault("flags", {})
        flags["needs_human"] = True
        flags["human_reason"] = reason
        flags["reasoning_packet"] = packet
    else:
        state.status = CaseStatus.NEEDS_HUMAN
        state.flags.needs_human = True
        state.flags.human_reason = reason

    # Emit guardrail event
    session = db or getattr(ctx, "db", None)
    await emit_event(
        case_id=case_id,
        agent=AgentName.orchestrator,
        phase=Phase.guardrail,
        summary=f"Guardrail tripped: Confidence {confidence:.2f} < {threshold:.2f} routed to NEEDS_HUMAN",
        detail=packet,
        reason=reason,
        db=session,
    )

    return True, packet
