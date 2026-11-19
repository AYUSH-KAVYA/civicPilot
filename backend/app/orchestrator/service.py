"""
CivicPilot Orchestrator Public API Service.
Implements the contract interfaces (docs/CONTRACT.md Section 6):
- start_case(case_id)
- resume_case(case_id, reason, payload=None)
- handle_citizen_message(case_id, text, image_urls=None)
- handle_citizen_confirmation(case_id, confirmed, comment=None)
- handle_approval(approval_id, decision, officer, note=None)
- handle_sandbox_signal(case_id, signal)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.adaptation.rules import (
    adapt_deadline_imminent,
    adapt_dispute_closure,
    adapt_new_evidence,
    adapt_ticket_rejection,
)
from backend.app.core.clock import now as clock_now
from backend.app.core.events import emit_event
from backend.app.db.models import ApprovalModel, CaseModel
from backend.app.db.session import AsyncSessionLocal
from backend.app.guardrails.injection import wrap_untrusted_input
from backend.app.orchestrator.context import AgentContext
from backend.app.orchestrator.graph import AgentGraph, get_case_lock
from backend.app.schemas import (
    AgentName,
    CaseStatus,
    Phase,
    StepStatus,
)

logger = logging.getLogger("civicpilot.orchestrator.service")


async def start_case(case_id: str, db: Optional[AsyncSession] = None) -> None:
    """
    Initiate the multi-agent resolution graph for a newly reported case.
    Executes intake -> triage -> plan -> action.
    """
    logger.info(f"Starting case: {case_id}")
    graph = AgentGraph(case_id=case_id, db=db)
    await graph.run(start_node="intake")


async def resume_case(
    case_id: str,
    reason: str,
    payload: Optional[Dict[str, Any]] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    """
    Resume an existing case after a scheduled timer, officer action, or webhook trigger.
    """
    logger.info(f"Resuming case {case_id} (Reason: {reason})")
    await emit_event(
        case_id=case_id,
        agent=AgentName.orchestrator,
        phase=Phase.adapt if "sla" in reason or "timer" in reason else Phase.act,
        summary=f"Case resumed: {reason}",
        detail=payload,
        reason=reason,
        db=db,
    )

    # Determine start node based on resume reason
    start_node = "evaluator"
    if "action" in reason.lower() or "retry" in reason.lower() or "approval" in reason.lower():
        start_node = "action"
    elif "replan" in reason.lower():
        start_node = "planner"
    elif "verify" in reason.lower() or "sla" in reason.lower():
        start_node = "evaluator"

    graph = AgentGraph(case_id=case_id, db=db)
    await graph.run(start_node=start_node, payload=payload)


async def handle_citizen_message(
    case_id: str,
    text: str,
    image_urls: Optional[List[str]] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    """
    Handle supplemental messages or new evidence from a citizen.
    Triggers Adaptation Rule (c): new evidence -> re-triage and replan.
    """
    logger.info(f"Handling citizen message for case {case_id}")
    clean_info = wrap_untrusted_input(text)

    await emit_event(
        case_id=case_id,
        agent=AgentName.citizen,
        phase=Phase.message,
        summary="Citizen sent supplemental message / evidence",
        detail={
            "text": text,
            "image_urls": image_urls or [],
            "prompt_hygiene": clean_info["is_suspicious"],
        },
        db=db,
    )

    # Under case lock: apply adaptation rule (c) and resume graph
    lock = await get_case_lock(case_id)
    async with lock:
        async def _execute(session: AsyncSession) -> None:
            case = await session.get(CaseModel, case_id)
            if not case:
                return

            state = dict(case.state)
            ctx = AgentContext.create(db=session)

            # Rule (c): new evidence
            updated_state = await adapt_new_evidence(state, text, image_urls, ctx)
            case.state = updated_state
            case.updated_at = clock_now()
            session.add(case)
            await session.commit()

        if db is not None:
            await _execute(db)
        else:
            async with AsyncSessionLocal() as session:
                await _execute(session)

    # Resume graph execution with action
    graph = AgentGraph(case_id=case_id, db=db)
    await graph.run(start_node="action")


async def handle_citizen_confirmation(
    case_id: str,
    confirmed: bool,
    comment: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    """
    Handle citizen confirmation of repair work.
    - If confirmed: transitions case to CLOSED.
    - If rejected (dispute): triggers Adaptation Rule (e) -> REOPENED + flags.needs_human.
    """
    logger.info(f"Citizen confirmation for case {case_id}: confirmed={confirmed}")

    lock = await get_case_lock(case_id)
    async with lock:
        async def _execute(session: AsyncSession) -> None:
            case = await session.get(CaseModel, case_id)
            if not case:
                return

            state = dict(case.state)
            ctx = AgentContext.create(db=session)

            if confirmed:
                state["status"] = CaseStatus.CLOSED.value
                case.status = CaseStatus.CLOSED.value
                case.state = state
                case.updated_at = clock_now()
                session.add(case)
                await session.commit()

                await emit_event(
                    case_id=case_id,
                    agent=AgentName.citizen,
                    phase=Phase.evaluate,
                    summary=f"Citizen confirmed resolution: '{comment or 'Satisfied with repair'}'. Case CLOSED.",
                    detail={"confirmed": True, "comment": comment},
                    reason="Citizen confirmed repair verification",
                    db=session,
                )
            else:
                # Rule (e): Citizen disputes closure
                updated_state = await adapt_dispute_closure(state, comment, ctx)
                case.status = CaseStatus.REOPENED.value
                case.state = updated_state
                case.updated_at = clock_now()
                session.add(case)
                await session.commit()

        if db is not None:
            await _execute(db)
        else:
            async with AsyncSessionLocal() as session:
                await _execute(session)


async def handle_approval(
    approval_id: str,
    decision: str,
    officer: str,
    note: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    """
    Handle municipal officer decision (approve/reject) on a critical-tier approval request.
    On approval: unblocks paused step and resumes Action agent.
    """
    logger.info(f"Handling approval {approval_id}: decision={decision} by officer={officer}")

    case_id: Optional[str] = None
    step_id: Optional[str] = None

    async def _execute(session: AsyncSession) -> None:
        nonlocal case_id, step_id
        approval = await session.get(ApprovalModel, approval_id)
        if not approval:
            raise ValueError(f"Approval request '{approval_id}' not found.")

        case_id = approval.case_id
        step_id = approval.step_id

        approval.status = "approved" if decision == "approve" else "rejected"
        approval.decided_at = clock_now()
        approval.decided_by = officer
        approval.note = note
        session.add(approval)

        # Update case state step status
        case = await session.get(CaseModel, case_id)
        if case:
            state = dict(case.state)
            plan = state.get("plan", {})
            steps = plan.get("steps", [])
            for s in steps:
                if s.get("id") == step_id:
                    if decision == "approve":
                        s["status"] = StepStatus.pending.value
                    else:
                        s["status"] = StepStatus.failed.value
                        s["result"] = {"error": f"Rejected by officer: {note or 'No rationale given'}"}

            case.state = state
            case.updated_at = clock_now()
            session.add(case)

        await session.commit()

        await emit_event(
            case_id=case_id,
            agent=AgentName.officer,
            phase=Phase.guardrail,
            summary=f"Officer {officer} decided '{decision.upper()}' on approval {approval_id}",
            detail={"approval_id": approval_id, "decision": decision, "officer": officer, "note": note},
            reason=f"Officer {decision}",
            db=session,
        )

    if db is not None:
        await _execute(db)
    else:
        async with AsyncSessionLocal() as session:
            await _execute(session)

    # If approved, resume the graph from action
    if decision == "approve" and case_id:
        graph = AgentGraph(case_id=case_id, db=db)
        await graph.run(start_node="action")


async def handle_sandbox_signal(
    case_id: str,
    signal: Dict[str, Any],
    db: Optional[AsyncSession] = None,
) -> None:
    """
    Handle live sandbox signals (e.g., ticket_rejected, crew_checked_in, crew_no_show, repair_photo_uploaded).
    Dispatches to appropriate adaptation rule or evaluator.
    """
    signal_type = signal.get("type", "unknown")
    logger.info(f"Sandbox signal for case {case_id}: {signal_type}")

    await emit_event(
        case_id=case_id,
        agent=AgentName.sandbox,
        phase=Phase.adapt if "rejected" in signal_type or "no_show" in signal_type else Phase.act,
        summary=f"Sandbox simulation signal: {signal_type}",
        detail=signal,
        db=db,
    )

    if signal_type == "ticket_rejected":
        # Rule (a): Department rejects ticket
        reason = signal.get("reason", "Department unable to service ticket")
        lock = await get_case_lock(case_id)
        async with lock:
            async def _execute_rejection(session: AsyncSession) -> None:
                case = await session.get(CaseModel, case_id)
                if not case:
                    return
                state = dict(case.state)
                # Mark ticket as rejected
                for t in state.get("tickets", []):
                    if t.get("id") == signal.get("ticket_id") or not signal.get("ticket_id"):
                        t["status"] = "rejected"

                ctx = AgentContext.create(db=session)
                updated_state = await adapt_ticket_rejection(state, reason, ctx)
                case.state = updated_state
                case.updated_at = clock_now()
                session.add(case)
                await session.commit()

            if db is not None:
                await _execute_rejection(db)
            else:
                async with AsyncSessionLocal() as session:
                    await _execute_rejection(session)

        # Resume action
        graph = AgentGraph(case_id=case_id, db=db)
        await graph.run(start_node="action")

    elif signal_type == "crew_no_show":
        # Rule (b): Deadline at risk / crew no show
        reason = signal.get("reason", "Assigned crew failed to report to site within SLA")
        lock = await get_case_lock(case_id)
        async with lock:
            async def _execute_no_show(session: AsyncSession) -> None:
                case = await session.get(CaseModel, case_id)
                if not case:
                    return
                state = dict(case.state)
                ctx = AgentContext.create(db=session)
                updated_state = await adapt_deadline_imminent(state, reason, ctx)
                case.state = updated_state
                case.updated_at = clock_now()
                session.add(case)
                await session.commit()

            if db is not None:
                await _execute_no_show(db)
            else:
                async with AsyncSessionLocal() as session:
                    await _execute_no_show(session)

        # Resume action with escalated plan
        graph = AgentGraph(case_id=case_id, db=db)
        await graph.run(start_node="action")

    elif signal_type == "repair_photo_uploaded":
        # Repair photo uploaded -> trigger evaluator vision verification
        photo_url = signal.get("photo_url", "")
        lock = await get_case_lock(case_id)
        async with lock:
            async def _execute_photo(session: AsyncSession) -> None:
                case = await session.get(CaseModel, case_id)
                if not case:
                    return
                state = dict(case.state)
                flags = state.setdefault("flags", {})
                flags["repair_photo_url"] = photo_url
                # Also record in tickets notes
                for t in state.get("tickets", []):
                    t.setdefault("notes", []).append(f"repair_photo:{photo_url}")
                case.state = state
                session.add(case)
                await session.commit()

            if db is not None:
                await _execute_photo(db)
            else:
                async with AsyncSessionLocal() as session:
                    await _execute_photo(session)

        graph = AgentGraph(case_id=case_id, db=db)
        await graph.run(start_node="evaluator")

    elif signal_type == "crew_checked_in":
        # Crew checked in on site
        notes = signal.get("notes", "Crew reported on site")
        lock = await get_case_lock(case_id)
        async with lock:
            async def _execute_checkin(session: AsyncSession) -> None:
                case = await session.get(CaseModel, case_id)
                if not case:
                    return
                state = dict(case.state)
                for t in state.get("tickets", []):
                    t.setdefault("notes", []).append(f"crew_checkin:{notes}")
                case.state = state
                session.add(case)
                await session.commit()

            if db is not None:
                await _execute_checkin(db)
            else:
                async with AsyncSessionLocal() as session:
                    await _execute_checkin(session)
