"""
CivicPilot Adaptation Rules (CONTRACT.md Section 1, 6).
Implements the 5 adaptation rules from the deck, each logging an adapt event with its reason:
(a) department rejects the ticket: re-read policy via policy_search and re-route through planner.replan;
(b) deadline about to be missed: escalate one level and re-prioritise;
(c) citizen adds new evidence: re-run triage and replan;
(d) duplicate complaints cluster (vector similarity plus geo radius): merge into one area-level work order and set flags.merged_into;
(e) citizen disputes closure: reopen, increment reopen_count and flag for human review.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.app.core.events import emit_event
from backend.app.schemas import (
    AgentName,
    CaseState,
    CaseStatus,
    Phase,
    Urgency,
)

logger = logging.getLogger("civicpilot.adaptation")

URGENCY_ESCALATION = {
    Urgency.low.value: Urgency.medium.value,
    Urgency.medium.value: Urgency.high.value,
    Urgency.high.value: Urgency.critical.value,
    Urgency.critical.value: Urgency.critical.value,
}


async def _emit(
    ctx: Any,
    case_id: str,
    agent: AgentName | str,
    phase: Phase | str,
    summary: str,
    detail: Optional[Dict[str, Any]] = None,
    tool_name: Optional[str] = None,
    reason: Optional[str] = None,
) -> Any:
    emit_fn = getattr(ctx, "emit", None)
    if emit_fn and callable(emit_fn):
        return await emit_fn(
            case_id=case_id,
            agent=agent,
            phase=phase,
            summary=summary,
            detail=detail,
            tool_name=tool_name,
            reason=reason,
            db=getattr(ctx, "db", None),
        )
    return await emit_event(
        case_id=case_id,
        agent=agent,
        phase=phase,
        summary=summary,
        detail=detail,
        tool_name=tool_name,
        reason=reason,
        db=getattr(ctx, "db", None),
    )


# ---------------------------------------------------------------------------
# Rule (a): Department Rejects Ticket
# ---------------------------------------------------------------------------

async def adapt_ticket_rejection(
    state: CaseState | Dict[str, Any],
    reason: str,
    ctx: Any,
) -> Dict[str, Any]:
    """
    (a) Department rejects ticket:
    1. Log adapt event with rejection reason.
    2. Re-read municipal policy via policy_search.
    3. Re-route through planner.replan with escalation office replacement.
    """
    case_id = state.get("id") if isinstance(state, dict) else state.id

    await _emit(
        ctx=ctx,
        case_id=case_id,
        agent=AgentName.orchestrator,
        phase=Phase.adapt,
        summary=f"Adaptation: Ticket rejected by department ({reason}). Re-reading policy and re-routing.",
        detail={"reason": reason, "rule": "ticket_rejection"},
        tool_name="policy_search",
        reason=f"Department rejection: {reason}",
    )

    # 1. Re-read policy via policy_search
    query = f"rejection escalation re-route {reason}"
    policy_results: List[Dict[str, Any]] = []
    try:
        from kb.search import policy_search
        policy_results = await policy_search(query=query, k=3)
    except Exception as e:
        logger.warning(f"policy_search during adaptation fallback: {e}")

    # 2. Re-plan through planner.replan
    try:
        from agents.planner import replan as planner_replan
        new_plan = await planner_replan(
            state,
            reason=f"Ticket rejected: {reason}",
            evidence={
                "disruption": "ticket_rejection",
                "reason": reason,
                "policy_results": policy_results,
            },
        )
        plan_dict = new_plan.model_dump() if hasattr(new_plan, "model_dump") else new_plan
    except Exception as e:
        logger.error(f"planner.replan error: {e}")
        plan_dict = state.get("plan") if isinstance(state, dict) else state.plan.model_dump()

    # Mark rejected tickets as handled
    tickets = state.get("tickets", []) if isinstance(state, dict) else getattr(state, "tickets", [])
    for t in tickets:
        if isinstance(t, dict) and t.get("status") == "rejected":
            t["rejection_handled"] = True
        elif hasattr(t, "status") and t.status == "rejected":
            setattr(t, "rejection_handled", True)

    # Update state
    if isinstance(state, dict):
        state["plan"] = plan_dict
        state["status"] = CaseStatus.PLANNED.value
    else:
        state.plan = plan_dict
        state.status = CaseStatus.PLANNED

    return state if isinstance(state, dict) else state.model_dump()


# ---------------------------------------------------------------------------
# Rule (b): Deadline About to be Missed / Crew No-Show
# ---------------------------------------------------------------------------

async def adapt_deadline_imminent(
    state: CaseState | Dict[str, Any],
    reason: str,
    ctx: Any,
) -> Dict[str, Any]:
    """
    (b) Deadline about to be missed or crew no-show:
    1. Log adapt event.
    2. Escalate urgency one level (low->medium->high->critical).
    3. Re-prioritise tickets and replan crew reassignment.
    """
    case_id = state.get("id") if isinstance(state, dict) else state.id
    db = getattr(ctx, "db", None)

    # Extract current urgency
    triage = state.get("triage") if isinstance(state, dict) else state.triage
    if hasattr(triage, "urgency"):
        curr_urgency = triage.urgency.value if hasattr(triage.urgency, "value") else str(triage.urgency)
    elif isinstance(triage, dict):
        curr_urgency = triage.get("urgency", "medium")
    else:
        curr_urgency = "medium"

    new_urgency = URGENCY_ESCALATION.get(curr_urgency, Urgency.critical.value)

    await _emit(
        ctx=ctx,
        case_id=case_id,
        agent=AgentName.orchestrator,
        phase=Phase.adapt,
        summary=f"Adaptation: Deadline at risk ({reason}). Escalated urgency from {curr_urgency} to {new_urgency}.",
        detail={
            "prior_urgency": curr_urgency,
            "escalated_urgency": new_urgency,
            "reason": reason,
            "rule": "deadline_imminent",
        },
        reason=f"Imminent SLA breach / disruption: {reason}",
    )

    # Update state triage urgency and status
    if isinstance(state, dict):
        if "triage" in state and state["triage"]:
            state["triage"]["urgency"] = new_urgency
        state["status"] = CaseStatus.AT_RISK.value
    else:
        if state.triage:
            state.triage.urgency = Urgency(new_urgency)
        state.status = CaseStatus.AT_RISK

    # Update open tickets priority
    tools = getattr(ctx, "tools", None)
    tickets = state.get("tickets", []) if isinstance(state, dict) else (state.tickets or [])
    for tkt in tickets:
        tkt_id = tkt.get("id") if isinstance(tkt, dict) else getattr(tkt, "id", None)
        if tkt_id and tools and hasattr(tools, "call"):
            try:
                await tools.call(
                    "update_ticket",
                    {"ticket_id": tkt_id, "priority": new_urgency, "notes": [f"Escalated priority to {new_urgency} due to {reason}"]},
                    case_id=case_id,
                    agent=AgentName.orchestrator,
                    db=db,
                )
            except Exception:
                pass

    # Call replan if disruption is crew_no_show
    if "crew" in reason.lower() or "no_show" in reason.lower():
        try:
            from agents.planner import replan as planner_replan
            new_plan = await planner_replan(
                state,
                reason=reason,
                evidence={"disruption": "crew_no_show"},
            )
            plan_dict = new_plan.model_dump() if hasattr(new_plan, "model_dump") else new_plan
            if isinstance(state, dict):
                state["plan"] = plan_dict
            else:
                state.plan = plan_dict
        except Exception as e:
            logger.warning(f"Replan on crew no show: {e}")

    return state if isinstance(state, dict) else state.model_dump()


# ---------------------------------------------------------------------------
# Rule (c): Citizen Adds New Evidence
# ---------------------------------------------------------------------------

async def adapt_new_evidence(
    state: CaseState | Dict[str, Any],
    new_text: str,
    new_images: Optional[List[str]],
    ctx: Any,
) -> Dict[str, Any]:
    """
    (c) Citizen adds new evidence:
    1. Log adapt event.
    2. Incorporate evidence into state.raw and re-run triage.
    3. Re-route through planner.replan.
    """
    case_id = state.get("id") if isinstance(state, dict) else state.id

    await _emit(
        ctx=ctx,
        case_id=case_id,
        agent=AgentName.orchestrator,
        phase=Phase.adapt,
        summary="Adaptation: Citizen submitted supplemental evidence. Re-running triage and replanning.",
        detail={
            "new_text_snippet": new_text[:150] if new_text else "",
            "new_images_count": len(new_images or []),
            "rule": "new_evidence",
        },
        reason="Citizen provided supplemental report evidence",
    )

    # 1. Update raw input
    if isinstance(state, dict):
        raw = state.setdefault("raw", {})
        existing_text = raw.get("text", "")
        raw["text"] = f"{existing_text}\n[Supplemental Evidence]: {new_text}".strip()
        if new_images:
            imgs = raw.setdefault("image_urls", [])
            imgs.extend(new_images)
    else:
        state.raw.text = f"{state.raw.text}\n[Supplemental Evidence]: {new_text}".strip()
        if new_images:
            state.raw.image_urls.extend(new_images)

    # 2. Re-run triage
    try:
        from agents.triage import run as triage_run
        triage_res = await triage_run(state, ctx)
        if hasattr(triage_res, "state_patch") and "triage" in triage_res.state_patch:
            if isinstance(state, dict):
                state["triage"] = triage_res.state_patch["triage"]
            else:
                state.triage = triage_res.state_patch["triage"]
    except Exception as e:
        logger.warning(f"Re-triage error: {e}")

    # 3. Re-plan
    try:
        from agents.planner import replan as planner_replan
        new_plan = await planner_replan(
            state,
            reason="Citizen supplemental evidence incorporated",
            evidence={"disruption": "new_evidence", "text": new_text},
        )
        plan_dict = new_plan.model_dump() if hasattr(new_plan, "model_dump") else new_plan
        if isinstance(state, dict):
            state["plan"] = plan_dict
            state["status"] = CaseStatus.PLANNED.value
        else:
            state.plan = plan_dict
            state.status = CaseStatus.PLANNED
    except Exception as e:
        logger.warning(f"Replan error: {e}")

    return state if isinstance(state, dict) else state.model_dump()


# ---------------------------------------------------------------------------
# Rule (d): Duplicate Complaints Cluster
# ---------------------------------------------------------------------------

async def adapt_duplicate_cluster(
    state: CaseState | Dict[str, Any],
    cluster_primary_id: str,
    similarity_score: float,
    ctx: Any,
) -> Dict[str, Any]:
    """
    (d) Duplicate complaints cluster (vector similarity plus geo radius):
    1. Log adapt event.
    2. Set flags.merged_into = cluster_primary_id.
    3. Transition case to CLOSED (merged into area-level work order).
    """
    case_id = state.get("id") if isinstance(state, dict) else state.id
    db = getattr(ctx, "db", None)

    await _emit(
        ctx=ctx,
        case_id=case_id,
        agent=AgentName.orchestrator,
        phase=Phase.adapt,
        summary=f"Adaptation: Duplicate grievance clustered with Case #{cluster_primary_id} ({round(similarity_score * 100)}% match). Merged into area work order.",
        detail={
            "merged_into": cluster_primary_id,
            "similarity_score": round(similarity_score, 3),
            "rule": "duplicate_cluster",
        },
        reason=f"Geospatial and vector similarity cluster match with {cluster_primary_id}",
    )

    if isinstance(state, dict):
        flags = state.setdefault("flags", {})
        flags["merged_into"] = cluster_primary_id
        state["status"] = CaseStatus.CLOSED.value
    else:
        state.flags.merged_into = cluster_primary_id
        state.status = CaseStatus.CLOSED

    # Notify citizen of merge
    tools = getattr(ctx, "tools", None)
    if tools and hasattr(tools, "call"):
        try:
            await tools.call(
                "notify",
                {
                    "case_id": case_id,
                    "channel": "chat",
                    "template": "duplicate_merge_notice",
                    "vars": {"primary_case_id": cluster_primary_id},
                },
                case_id=case_id,
                agent=AgentName.orchestrator,
                db=db,
            )
        except Exception:
            pass

    return state if isinstance(state, dict) else state.model_dump()


# ---------------------------------------------------------------------------
# Rule (e): Citizen Disputes Closure
# ---------------------------------------------------------------------------

async def adapt_dispute_closure(
    state: CaseState | Dict[str, Any],
    comment: Optional[str],
    ctx: Any,
) -> Dict[str, Any]:
    """
    (e) Citizen disputes closure:
    1. Log adapt event.
    2. Reopen case, increment reopen_count.
    3. Flag for human review: flags.needs_human = True, status = REOPENED.
    """
    case_id = state.get("id") if isinstance(state, dict) else state.id
    dispute_comment = comment or "Citizen rejected repair confirmation without notes."

    await _emit(
        ctx=ctx,
        case_id=case_id,
        agent=AgentName.orchestrator,
        phase=Phase.adapt,
        summary=f"Adaptation: Citizen disputed closure: '{dispute_comment[:100]}'. Case reopened for human supervisor review.",
        detail={
            "comment": dispute_comment,
            "rule": "dispute_closure",
        },
        reason=dispute_comment,
    )

    if isinstance(state, dict):
        flags = state.setdefault("flags", {})
        current_reopen = flags.get("reopen_count", 0)
        flags["reopen_count"] = current_reopen + 1
        flags["needs_human"] = True
        flags["human_reason"] = f"Citizen disputed repair closure: {dispute_comment}"
        state["status"] = CaseStatus.REOPENED.value
    else:
        state.flags.reopen_count += 1
        state.flags.needs_human = True
        state.flags.human_reason = f"Citizen disputed repair closure: {dispute_comment}"
        state.status = CaseStatus.REOPENED

    return state if isinstance(state, dict) else state.model_dump()
