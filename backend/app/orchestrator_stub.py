"""
Orchestrator Stub for CivicPilot.
Provides a functional, end-to-end implementation of the Orchestrator public API
(CONTRACT.md Section 6) so the entire backend, sandbox, and API work seamlessly
before P3's full agent orchestrator is merged.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.clock import now as clock_now
from backend.app.core.events import emit_event
from backend.app.db.models import ApprovalModel, CaseModel
from backend.app.db.session import AsyncSessionLocal
from backend.app.schemas import AgentName, CaseStatus, Phase, StepStatus, Urgency
from backend.app.tools.registry import tools


async def start_case(case_id: str, db: Optional[AsyncSession] = None) -> None:
    """Triggered on new case creation. Runs intake -> triage -> plan -> action."""
    async def _run(session: AsyncSession) -> None:
        case = await session.get(CaseModel, case_id)
        if not case:
            return

        state = dict(case.state)

        # 1. Perceive / Intake Phase
        await emit_event(
            case_id=case_id,
            agent=AgentName.intake,
            phase=Phase.perceive,
            summary=f"Citizen grievance received via {state.get('raw', {}).get('channel', 'web')}",
            detail={"text": state.get("raw", {}).get("text", "")},
            db=session,
        )

        raw_text = state.get("raw", {}).get("text", "").lower()
        raw_lat = state.get("raw", {}).get("lat")
        raw_lng = state.get("raw", {}).get("lng")
        address_text = state.get("raw", {}).get("address_text")

        # Geo lookup
        geo_result = await tools.call(
            "geo_lookup",
            {"lat": raw_lat, "lng": raw_lng, "address_text": address_text},
            case_id=case_id,
            agent=AgentName.intake,
            db=session,
        )

        # Categorize
        if any(w in raw_text for w in ["water", "pipe", "leak", "sewer", "flood", "drain"]):
            dept_id = "water"
            category = "Water Supply & Leaks"
            urgency = Urgency.high
            deadline_hrs = 12.0
        elif any(w in raw_text for w in ["light", "pole", "wire", "electric", "power", "dark"]):
            dept_id = "electricity"
            category = "Street Lighting & Power"
            urgency = Urgency.critical
            deadline_hrs = 6.0
        elif any(w in raw_text for w in ["garbage", "trash", "waste", "dump", "clean"]):
            dept_id = "sanitation"
            category = "Sanitation & Trash"
            urgency = Urgency.medium
            deadline_hrs = 8.0
        elif any(w in raw_text for w in ["tree", "park", "branch", "playground"]):
            dept_id = "parks"
            category = "Parks & Forestry"
            urgency = Urgency.low
            deadline_hrs = 48.0
        elif any(w in raw_text for w in ["mosquito", "pest", "rodent", "health"]):
            dept_id = "public_health"
            category = "Public Health & Pest Control"
            urgency = Urgency.medium
            deadline_hrs = 16.0
        else:
            dept_id = "roads"
            category = "Road Hazards & Potholes"
            urgency = Urgency.medium
            deadline_hrs = 24.0

        # Update intake and triage fields
        state["intake"] = {
            "category": category,
            "summary": state.get("raw", {}).get("text", "")[:100],
            "location": {
                "address": geo_result.get("formatted_address", "Metroville"),
                "lat": geo_result.get("lat"),
                "lng": geo_result.get("lng"),
            },
            "visible_damage": ["Physical obstruction or hazard observed"],
            "nearby_sensitive_sites": [],
            "language_detected": "en",
            "missing_info": [],
            "confidence": 0.88,
        }

        state["triage"] = {
            "urgency": urgency.value,
            "department_id": dept_id,
            "ward_id": geo_result.get("ward_id", "ward-1"),
            "office_id": geo_result.get("office_id", "office-ward-1"),
            "deadline_hours": deadline_hrs,
            "policy_refs": [f"policy-{dept_id[:3]}-01"],
            "rationale": f"Triaged to {dept_id} based on reported issue keywords.",
            "confidence": 0.92,
        }

        # Emit Triage Event
        await emit_event(
            case_id=case_id,
            agent=AgentName.triage,
            phase=Phase.reason,
            summary=f"Triaged to {dept_id.upper()} department (Ward {geo_result.get('ward_name', 'Ward 1')}), SLA: {deadline_hrs}h",
            detail=state["triage"],
            db=session,
        )

        # 2. Plan Phase
        due_at = clock_now() + timedelta(hours=deadline_hrs)
        state["status"] = CaseStatus.IN_PROGRESS.value
        state["deadline_at"] = due_at.isoformat()

        step_ticket_id = f"step-{uuid.uuid4().hex[:6]}"
        step_notify_id = f"step-{uuid.uuid4().hex[:6]}"
        step_check_id = f"step-{uuid.uuid4().hex[:6]}"

        state["plan"] = {
            "version": 1,
            "steps": [
                {
                    "id": step_ticket_id,
                    "title": f"Dispatch field crew from {dept_id}",
                    "tool": "create_ticket",
                    "args": {"department_id": dept_id, "priority": urgency.value, "crew_id": "nearest"},
                    "depends_on": [],
                    "due_at": due_at.isoformat(),
                    "risk_tier": "routine",
                    "status": "done",
                    "result": None,
                },
                {
                    "id": step_notify_id,
                    "title": "Send acknowledgement and SLA notification to citizen",
                    "tool": "notify",
                    "args": {"channel": "chat", "template": "case_triaged"},
                    "depends_on": [step_ticket_id],
                    "due_at": None,
                    "risk_tier": "routine",
                    "status": "done",
                    "result": None,
                },
                {
                    "id": step_check_id,
                    "title": "Schedule SLA compliance verification check",
                    "tool": "schedule_check",
                    "args": {"reason": "SLA compliance verification check"},
                    "depends_on": [step_notify_id],
                    "due_at": due_at.isoformat(),
                    "risk_tier": "routine",
                    "status": "pending",
                    "result": None,
                },
            ],
        }

        await emit_event(
            case_id=case_id,
            agent=AgentName.planner,
            phase=Phase.plan,
            summary=f"Action plan version 1 established with 3 steps. Assigned deadline: {due_at.strftime('%Y-%m-%d %H:%M UTC')}",
            detail=state["plan"],
            db=session,
        )

        # 3. Action Phase: Create ticket & assign crew
        await tools.call(
            "create_ticket",
            {
                "case_id": case_id,
                "department_id": dept_id,
                "priority": urgency.value,
                "crew_id": "nearest",
            },
            case_id=case_id,
            agent=AgentName.action,
            db=session,
        )

        # Send notification to citizen
        await tools.call(
            "notify",
            {
                "case_id": case_id,
                "channel": "chat",
                "template": "case_triaged",
                "vars": {
                    "department": dept_id.upper(),
                    "ward": geo_result.get("ward_name", "Ward 1"),
                    "urgency": urgency.value,
                    "deadline_hours": str(deadline_hrs),
                },
            },
            case_id=case_id,
            agent=AgentName.action,
            db=session,
        )

        # Schedule check
        await tools.call(
            "schedule_check",
            {
                "case_id": case_id,
                "run_at": due_at,
                "reason": "SLA deadline compliance check",
            },
            case_id=case_id,
            agent=AgentName.action,
            db=session,
        )

        # Update case model columns
        case.status = CaseStatus.IN_PROGRESS.value
        case.urgency = urgency.value
        case.department_id = dept_id
        case.ward_id = geo_result.get("ward_id")
        case.office_id = geo_result.get("office_id")
        case.deadline_at = due_at
        case.state = state
        session.add(case)
        await session.commit()

    if db is not None:
        await _run(db)
    else:
        async with AsyncSessionLocal() as session:
            await _run(session)


async def resume_case(
    case_id: str,
    reason: str,
    payload: Optional[Dict[str, Any]] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    """Called by timers or external signals when a scheduled check triggers."""
    async def _run(session: AsyncSession) -> None:
        case = await session.get(CaseModel, case_id)
        if not case:
            return

        await emit_event(
            case_id=case_id,
            agent=AgentName.orchestrator,
            phase=Phase.evaluate,
            summary=f"Case resumed: {reason}",
            detail=payload or {"reason": reason},
            reason=reason,
            db=session,
        )

        # Check if case is overdue
        if case.deadline_at and clock_now() > case.deadline_at and case.status == CaseStatus.IN_PROGRESS.value:
            case.status = CaseStatus.AT_RISK.value
            state = dict(case.state)
            state["status"] = CaseStatus.AT_RISK.value
            case.state = state
            session.add(case)
            await session.commit()

            await emit_event(
                case_id=case_id,
                agent=AgentName.evaluator,
                phase=Phase.adapt,
                summary="SLA breach detected! Case escalated to AT_RISK status.",
                detail={"deadline_at": case.deadline_at.isoformat(), "current_time": clock_now().isoformat()},
                db=session,
            )

    if db is not None:
        await _run(db)
    else:
        async with AsyncSessionLocal() as session:
            await _run(session)


async def handle_citizen_message(
    case_id: str,
    text: str,
    image_urls: Optional[List[str]] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    """Citizen provides additional information or feedback."""
    async def _run(session: AsyncSession) -> None:
        case = await session.get(CaseModel, case_id)
        if not case:
            return

        await emit_event(
            case_id=case_id,
            agent=AgentName.citizen,
            phase=Phase.message,
            summary="Citizen provided follow-up message/evidence.",
            detail={"text": text, "image_urls": image_urls or []},
            db=session,
        )

        state = dict(case.state)
        raw = state.setdefault("raw", {})
        raw_msgs = raw.setdefault("followups", [])
        raw_msgs.append({"text": text, "image_urls": image_urls or [], "ts": clock_now().isoformat()})
        case.state = state
        session.add(case)
        await session.commit()

    if db is not None:
        await _run(db)
    else:
        async with AsyncSessionLocal() as session:
            await _run(session)


async def handle_citizen_confirmation(
    case_id: str,
    confirmed: bool,
    comment: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    """Citizen verifies whether the repair was resolved successfully."""
    async def _run(session: AsyncSession) -> None:
        case = await session.get(CaseModel, case_id)
        if not case:
            return

        state = dict(case.state)
        flags = state.setdefault("flags", {})

        if confirmed:
            case.status = CaseStatus.CLOSED.value
            state["status"] = CaseStatus.CLOSED.value
            summary_msg = "Citizen confirmed resolution. Case successfully closed."
        else:
            reopen_count = flags.get("reopen_count", 0) + 1
            flags["reopen_count"] = reopen_count
            case.status = CaseStatus.REOPENED.value
            state["status"] = CaseStatus.REOPENED.value
            flags["needs_human"] = True
            flags["human_reason"] = f"Citizen rejected resolution: {comment or 'Unresolved issue'}"
            summary_msg = f"Citizen rejected repair. Case reopened (count: {reopen_count}). Escalated to supervisor."

        case.state = state
        session.add(case)
        await session.commit()

        await emit_event(
            case_id=case_id,
            agent=AgentName.citizen,
            phase=Phase.evaluate,
            summary=summary_msg,
            detail={"confirmed": confirmed, "comment": comment},
            db=session,
        )

        # Notify citizen of resolution or reopening
        template = "case_closed" if confirmed else "needs_info"
        await tools.call(
            "notify",
            {"case_id": case_id, "channel": "chat", "template": template, "vars": {"case_id": case_id}},
            case_id=case_id,
            agent=AgentName.action,
            db=session,
        )

    if db is not None:
        await _run(db)
    else:
        async with AsyncSessionLocal() as session:
            await _run(session)


async def handle_approval(
    approval_id: str,
    decision: str,  # approve | reject
    officer: str,
    note: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    """Officer approves or rejects a high-risk step."""
    async def _run(session: AsyncSession) -> None:
        approval = await session.get(ApprovalModel, approval_id)
        if not approval:
            raise KeyError(f"Approval '{approval_id}' not found.")

        approval.status = "approved" if decision == "approve" else "rejected"
        approval.decided_at = clock_now()
        approval.decided_by = officer
        approval.note = note
        session.add(approval)

        case = await session.get(CaseModel, approval.case_id)
        if case and case.state:
            state = dict(case.state)
            if approval.step_id and state.get("plan"):
                for step in state["plan"].get("steps", []):
                    if step.get("id") == approval.step_id:
                        step["status"] = StepStatus.running.value if decision == "approve" else StepStatus.skipped.value
            case.state = state
            session.add(case)

        await session.commit()

        await emit_event(
            case_id=approval.case_id,
            agent=AgentName.officer,
            phase=Phase.guardrail,
            summary=f"Supervisor {decision.upper()} step approval (decision by {officer}).",
            detail={"approval_id": approval_id, "decision": decision, "officer": officer, "note": note},
            db=session,
        )

    if db is not None:
        await _run(db)
    else:
        async with AsyncSessionLocal() as session:
            await _run(session)


async def handle_sandbox_signal(
    case_id: str,
    signal: Dict[str, Any],
    db: Optional[AsyncSession] = None,
) -> None:
    """
    Handles live simulator signals:
    - ticket_rejected: department rejects ticket
    - crew_checked_in: crew reports arrival on site
    - crew_no_show: crew failed to show up
    - repair_photo_uploaded: repair photo submitted for verification
    """
    async def _run(session: AsyncSession) -> None:
        sig_type = signal.get("type")
        case = await session.get(CaseModel, case_id)
        if not case:
            return

        state = dict(case.state)
        flags = state.setdefault("flags", {})

        if sig_type == "ticket_rejected":
            reason = signal.get("reason", "Department unable to fulfill ticket")
            flags["needs_human"] = True
            flags["human_reason"] = f"Sandbox ticket rejected: {reason}"
            case.status = CaseStatus.NEEDS_HUMAN.value
            state["status"] = CaseStatus.NEEDS_HUMAN.value
            summary = f"Department rejected ticket: {reason}. Case marked as NEEDS_HUMAN."

        elif sig_type == "crew_checked_in":
            notes = signal.get("notes", "Crew arrived at site.")
            summary = f"Field crew checked in on site. {notes}"

        elif sig_type == "crew_no_show":
            reason = signal.get("reason", "Crew uncontactable / vehicle breakdown")
            case.status = CaseStatus.AT_RISK.value
            state["status"] = CaseStatus.AT_RISK.value
            summary = f"Crew NO-SHOW reported: {reason}. Status escalated to AT_RISK."

        elif sig_type == "repair_photo_uploaded":
            photo_url = signal.get("photo_url", "")
            notes = signal.get("notes", "Repairs completed on site.")
            case.status = CaseStatus.AWAITING_CONFIRMATION.value
            state["status"] = CaseStatus.AWAITING_CONFIRMATION.value
            summary = "Field crew uploaded repair photo. Awaiting citizen confirmation."
            # Notify citizen
            await tools.call(
                "notify",
                {
                    "case_id": case_id,
                    "channel": "chat",
                    "template": "repair_completed",
                    "vars": {"case_id": case_id, "photo_url": photo_url},
                },
                case_id=case_id,
                agent=AgentName.sandbox,
                db=session,
            )
        else:
            summary = f"Received sandbox signal: {sig_type}"

        case.state = state
        session.add(case)
        await session.commit()

        await emit_event(
            case_id=case_id,
            agent=AgentName.sandbox,
            phase=Phase.adapt,
            summary=summary,
            detail=signal,
            db=session,
        )

    if db is not None:
        await _run(db)
    else:
        async with AsyncSessionLocal() as session:
            await _run(session)
