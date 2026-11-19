"""
CivicPilot Scenario Runner.
Executes the live-demo scenarios using SIM_TIME_SCALE so multi-hour timelines
play out cleanly in ~3 minutes (or seconds during tests).
Source of truth: docs/CONTRACT.md Section 6, 7.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.core.orchestrator_bridge as orchestrator
from backend.app.core.auth import create_case_access_token
from backend.app.core.clock import clock
from backend.app.db.models import ApprovalModel, CaseEventModel, CaseModel, CitizenModel
from backend.app.db.session import AsyncSessionLocal
from backend.app.scenarios.timeline import SCENARIO_CONFIGS
from backend.app.schemas import CaseStatus

logger = logging.getLogger("civicpilot.scenarios")


async def run_scenario(
    scenario_name: str,
    sim_scale: float = 60.0,
    db: Optional[AsyncSession] = None,
    step_delay_sec: float = 0.5,
) -> Dict[str, Any]:
    """
    Execute a full demo scenario end-to-end.
    Returns dictionary with case_id, final_status, and full list of audit events.
    """
    if scenario_name not in SCENARIO_CONFIGS:
        raise ValueError(f"Unknown scenario '{scenario_name}'. Valid: {list(SCENARIO_CONFIGS.keys())}")

    cfg = SCENARIO_CONFIGS[scenario_name]
    case_id = f"demo-{scenario_name}-{uuid.uuid4().hex[:6]}"
    access_token = create_case_access_token(case_id)

    # Set simulation clock scale
    clock.reset(scale=sim_scale)
    now = clock.now()

    # Build initial case state
    state_dict: Dict[str, Any] = {
        "id": case_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "status": CaseStatus.NEW.value,
        "deadline_at": None,
        "citizen": {
            "contact_masked": "c***@example.com",
            "language": "en",
        },
        "raw": {
            "text": cfg["text"],
            "image_urls": cfg.get("image_urls", []),
            "lat": cfg.get("lat"),
            "lng": cfg.get("lng"),
            "address_text": cfg.get("address"),
            "channel": cfg.get("channel", "web"),
        },
        "intake": None,
        "triage": None,
        "plan": None,
        "tickets": [],
        "flags": {
            "needs_human": False,
            "human_reason": None,
            "reopen_count": 0,
            "merged_into": None,
            "duplicate_of": [],
        },
    }

    async def _setup_case(session: AsyncSession) -> None:
        case = CaseModel(
            id=case_id,
            created_at=now,
            updated_at=now,
            status=CaseStatus.NEW.value,
            state=state_dict,
        )
        session.add(case)

        citizen = CitizenModel(
            id=f"cit-{uuid.uuid4().hex[:6]}",
            case_id=case_id,
            raw_contact=cfg.get("contact", "citizen@example.com"),
            masked_contact="c***@example.com",
            language="en",
            created_at=now,
        )
        session.add(citizen)
        await session.commit()

    if db is not None:
        await _setup_case(db)
    else:
        async with AsyncSessionLocal() as session:
            await _setup_case(session)

    logger.info(f"--- [Scenario {scenario_name.upper()}] Starting case {case_id} ---")

    # 1. Start case (Perceive -> Reason -> Plan -> Act)
    await orchestrator.start_case(case_id, db=db)
    await asyncio.sleep(step_delay_sec)

    # --- Scenario-specific timeline flow ---

    if scenario_name == "happy":
        # Simulate field crew check-in
        logger.info("--- [Scenario HAPPY] Crew arriving at leak site ---")
        await orchestrator.handle_sandbox_signal(
            case_id=case_id,
            signal={"type": "crew_checked_in", "notes": "Crew arrived on site, isolated water line"},
            db=db,
        )
        await asyncio.sleep(step_delay_sec)

        # Simulate repair completion and photo upload
        logger.info("--- [Scenario HAPPY] Repair complete, photo uploaded ---")
        await orchestrator.handle_sandbox_signal(
            case_id=case_id,
            signal={"type": "repair_photo_uploaded", "photo_url": cfg["repair_photo_url"]},
            db=db,
        )
        await asyncio.sleep(step_delay_sec)

        # Citizen confirms resolution
        logger.info("--- [Scenario HAPPY] Citizen confirming resolution ---")
        await orchestrator.handle_citizen_confirmation(
            case_id=case_id,
            confirmed=True,
            comment=cfg.get("citizen_comment"),
            db=db,
        )

    elif scenario_name == "disruption":
        # Simulate department ticket rejection
        logger.info("--- [Scenario DISRUPTION] Department rejecting ticket ---")
        await orchestrator.handle_sandbox_signal(
            case_id=case_id,
            signal={"type": "ticket_rejected", "reason": cfg["rejection_reason"]},
            db=db,
        )
        await asyncio.sleep(step_delay_sec)

        # Crew re-assigned and completed
        logger.info("--- [Scenario DISRUPTION] Re-routed crew repairing crater ---")
        await orchestrator.handle_sandbox_signal(
            case_id=case_id,
            signal={"type": "repair_photo_uploaded", "photo_url": cfg["repair_photo_url"]},
            db=db,
        )
        await asyncio.sleep(step_delay_sec)

        # Citizen confirms
        await orchestrator.handle_citizen_confirmation(
            case_id=case_id,
            confirmed=True,
            comment=cfg.get("citizen_comment"),
            db=db,
        )

    elif scenario_name == "ambiguity":
        # Ambiguity case stops automatically at NEEDS_HUMAN due to confidence guardrail
        logger.info("--- [Scenario AMBIGUITY] Case halted for human officer ---")

    elif scenario_name == "case1042":
        # Fetch pending approval
        logger.info("--- [Scenario CASE 1042] Critical risk tier approval check ---")
        approval_id: Optional[str] = None

        async def _find_approval(session: AsyncSession) -> Optional[str]:
            stmt = select(ApprovalModel).where(
                ApprovalModel.case_id == case_id,
                ApprovalModel.status == "pending",
            )
            res = (await session.execute(stmt)).scalars().first()
            return res.id if res else None

        if db is not None:
            approval_id = await _find_approval(db)
        else:
            async with AsyncSessionLocal() as session:
                approval_id = await _find_approval(session)

        # If not pre-created by plan, create approval record for demonstration
        if not approval_id:
            approval_id = f"appr-{uuid.uuid4().hex[:8]}"
            async def _create_approval(session: AsyncSession) -> None:
                appr = ApprovalModel(
                    id=approval_id,
                    case_id=case_id,
                    step_id="step-high-voltage-isolation",
                    risk_tier="critical",
                    status="pending",
                    rationale=f"High-voltage electrical hazard near sensitive site ({cfg.get('sensitive_site')})",
                    requested_at=clock.now(),
                )
                session.add(appr)
                await session.commit()

            if db is not None:
                await _create_approval(db)
            else:
                async with AsyncSessionLocal() as session:
                    await _create_approval(session)

        # Officer reviews and approves
        logger.info(f"--- [Scenario CASE 1042] Officer {cfg['officer_name']} approving emergency isolation ---")
        await orchestrator.handle_approval(
            approval_id=approval_id,
            decision="approve",
            officer=cfg.get("officer_name", "Officer"),
            note=cfg.get("officer_note"),
            db=db,
        )
        await asyncio.sleep(step_delay_sec)

        # Complete repair
        await orchestrator.handle_sandbox_signal(
            case_id=case_id,
            signal={"type": "repair_photo_uploaded", "photo_url": cfg["repair_photo_url"]},
            db=db,
        )
        await asyncio.sleep(step_delay_sec)

        # Citizen confirms
        await orchestrator.handle_citizen_confirmation(
            case_id=case_id,
            confirmed=True,
            comment=cfg.get("citizen_comment"),
            db=db,
        )

    # Fetch final state and events
    final_case = None
    events = []

    async def _fetch_summary(session: AsyncSession):
        nonlocal final_case, events
        final_case = await session.get(CaseModel, case_id)
        stmt = select(CaseEventModel).where(CaseEventModel.case_id == case_id).order_by(CaseEventModel.ts)
        events = (await session.execute(stmt)).scalars().all()

    if db is not None:
        await _fetch_summary(db)
    else:
        async with AsyncSessionLocal() as session:
            await _fetch_summary(session)

    events_data = [
        {
            "phase": e.phase,
            "agent": e.agent,
            "summary": e.summary,
            "ts": e.ts.isoformat() if e.ts else None,
            "tool_name": e.tool_name,
            "reason": e.reason,
        }
        for e in events
    ]

    return {
        "scenario": scenario_name,
        "case_id": case_id,
        "access_token": access_token,
        "final_status": final_case.status if final_case else "UNKNOWN",
        "total_events": len(events_data),
        "events": events_data,
    }
