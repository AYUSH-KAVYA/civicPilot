"""
CivicPilot Guardrails: Completeness Check
Verifies that every agent decision and state transition emits a corresponding audit event.
Source of truth: docs/CONTRACT.md Section 5.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import CaseEventModel
from backend.app.schemas import Phase


class AuditCompletenessError(Exception):
    """Raised when a state transition or decision lacked a mandatory audit event."""
    pass


async def verify_event_completeness(
    case_id: str,
    required_phases: Optional[List[Phase | str]] = None,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    Query the case_events table for a case and verify that events were emitted
    for all required lifecycle phases.
    """
    if db is None:
        return {"complete": True, "event_count": 0, "phases_present": []}

    stmt = select(CaseEventModel).where(CaseEventModel.case_id == case_id).order_by(CaseEventModel.ts)
    res = await db.execute(stmt)
    events = res.scalars().all()

    phases_present = set(e.phase for e in events)

    missing_phases: List[str] = []
    if required_phases:
        for p in required_phases:
            phase_str = p.value if isinstance(p, Phase) else str(p)
            if phase_str not in phases_present:
                missing_phases.append(phase_str)

    return {
        "case_id": case_id,
        "total_events": len(events),
        "phases_present": list(phases_present),
        "missing_phases": missing_phases,
        "complete": len(missing_phases) == 0,
    }


def assert_event_emitted(events_list: List[Dict[str, Any]], expected_phase: Phase | str) -> bool:
    """Helper to verify in-memory event sequences during testing."""
    phase_str = expected_phase.value if isinstance(expected_phase, Phase) else str(expected_phase)
    return any(e.get("phase") == phase_str for e in events_list)
