"""
Demo Scenarios API Router for CivicPilot.
POST /api/demo/scenarios/{happy|disruption|ambiguity|case1042}/run
Triggers live end-to-end demo flows for presentations and tests.
Source of truth: docs/CONTRACT.md Section 7.
"""

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.core.orchestrator_bridge as orchestrator
from backend.app.core.auth import create_case_access_token
from backend.app.core.clock import now as clock_now
from backend.app.db.models import ApprovalModel, CaseModel, CitizenModel
from backend.app.db.session import get_db
from backend.app.schemas import CaseStatus

router = APIRouter(prefix="/demo", tags=["Demo Scenarios"])


@router.post("/scenarios/{scenario}/run")
async def run_scenario(
    scenario: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Execute a pre-scripted multi-agent demo scenario:
    - happy: Standard water main leak resolved smoothly.
    - disruption: Crew no-show triggers escalation and SLA alert.
    - ambiguity: Unclear complaint triggers clarification request.
    - case1042: High-risk exposed electrical wire requiring supervisor approval.
    """
    valid_scenarios = {"happy", "disruption", "ambiguity", "case1042"}
    if scenario not in valid_scenarios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scenario '{scenario}'. Valid scenarios: {sorted(list(valid_scenarios))}",
        )

    case_id = f"demo-{scenario}-{uuid.uuid4().hex[:6]}"
    access_token = create_case_access_token(case_id)
    created_at = clock_now()

    if scenario == "happy":
        text = "Major water pipe burst near City Hall Plaza. Clean water is gushing into the street."
        lat, lng = 37.750, -122.420
        contact = "citizen.jane@example.com"

    elif scenario == "disruption":
        text = "Large road collapse and crater on North Boulevard blocking the bus lane."
        lat, lng = 37.760, -122.420
        contact = "+1-555-0199"

    elif scenario == "ambiguity":
        text = "Something smells really weird and there is a problem near the corner."
        lat, lng = 37.740, -122.420
        contact = "concerned_neighbor@example.com"

    else:  # case1042
        text = "EMERGENCY: High voltage electrical power line snapped and is sparking on the sidewalk next to Lincoln Elementary School."
        lat, lng = 37.752, -122.423
        contact = "principal.smith@metroville.gov"

    # Create Case State
    state_dict: Dict[str, Any] = {
        "id": case_id,
        "created_at": created_at.isoformat(),
        "updated_at": created_at.isoformat(),
        "status": CaseStatus.NEW.value,
        "deadline_at": None,
        "citizen": {"contact_masked": "c***@example.com", "language": "en"},
        "raw": {
            "text": text,
            "image_urls": ["/demo/leak.jpg"],
            "lat": lat,
            "lng": lng,
            "address_text": "City Hall Plaza, Metroville",
            "channel": "web",
        },
        "intake": None,
        "triage": None,
        "plan": None,
        "tickets": [],
        "flags": {"needs_human": False, "human_reason": None, "reopen_count": 0, "merged_into": None, "duplicate_of": []},
    }

    case = CaseModel(
        id=case_id,
        created_at=created_at,
        updated_at=created_at,
        status=CaseStatus.NEW.value,
        state=state_dict,
    )
    db.add(case)

    citizen = CitizenModel(
        id=f"cit-{uuid.uuid4().hex[:6]}",
        case_id=case_id,
        raw_contact=contact,
        masked_contact="c***@example.com",
        language="en",
        created_at=created_at,
    )
    db.add(citizen)
    await db.commit()

    # Run orchestrator start
    await orchestrator.start_case(case_id, db=db)

    # For case1042: add a pending critical approval requirement
    if scenario == "case1042":
        approval = ApprovalModel(
            id=f"appr-{uuid.uuid4().hex[:6]}",
            case_id=case_id,
            step_id="step-high-voltage-isolation",
            risk_tier="critical",
            status="pending",
            rationale="Critical risk: High-voltage electrical wire sparking near elementary school requires supervisor approval to isolate power grid quadrant.",
            requested_at=clock_now(),
        )
        db.add(approval)
        await db.commit()

    return {
        "scenario": scenario,
        "case_id": case_id,
        "access_token": access_token,
        "status": "initiated",
    }
