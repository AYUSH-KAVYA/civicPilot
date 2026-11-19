"""
Tests for the four P1 tools: geo_lookup, ticketing, notify, scheduler, and tool registry.
"""

from datetime import timedelta

import pytest

from backend.app.core.clock import now as clock_now
from backend.app.db.models import CaseModel
from backend.app.schemas import CaseStatus
from backend.app.tools.registry import tools


@pytest.mark.asyncio
async def test_geo_lookup_known_point(db_session):
    # Metroville center: 37.750, -122.420 falls in ward-1
    result = await tools.call(
        "geo_lookup",
        {"lat": 37.750, "lng": -122.420},
        case_id="case-geo-test",
        db=db_session,
    )
    assert "ward_id" in result
    assert result["ward_id"] == "ward-1"
    assert "Downtown" in result["ward_name"]
    assert "office_id" in result


@pytest.mark.asyncio
async def test_ticketing_lifecycle_and_nearest_crew(db_session):
    # Create test case in DB
    case = CaseModel(
        id="case-tkt-test",
        status=CaseStatus.NEW.value,
        state={"raw": {"lat": 37.750, "lng": -122.420}},
    )
    db_session.add(case)
    await db_session.commit()

    # Create ticket with nearest crew
    ticket = await tools.call(
        "create_ticket",
        {
            "case_id": "case-tkt-test",
            "department_id": "water",
            "priority": "high",
            "crew_id": "nearest",
        },
        case_id="case-tkt-test",
        db=db_session,
    )
    assert ticket["department_id"] == "water"
    assert ticket["crew_id"] is not None
    assert ticket["status"] == "assigned"

    ticket_id = ticket["id"]

    # Update ticket
    updated = await tools.call(
        "update_ticket",
        {"ticket_id": ticket_id, "status": "in_progress", "note": "Crew on site"},
        case_id="case-tkt-test",
        db=db_session,
    )
    assert updated["status"] == "in_progress"

    # Get ticket
    fetched = await tools.call("get_ticket", {"ticket_id": ticket_id}, case_id="case-tkt-test", db=db_session)
    assert fetched["id"] == ticket_id


@pytest.mark.asyncio
async def test_notify_tool(db_session):
    res = await tools.call(
        "notify",
        {
            "case_id": "case-notif-test",
            "channel": "chat",
            "template": "case_received",
            "vars": {"case_id": "case-notif-test"},
        },
        case_id="case-notif-test",
        db=db_session,
    )
    assert res["status"] in ("sent", "sent_sandbox_only")
    assert "case-notif-test" in res["message"]


@pytest.mark.asyncio
async def test_scheduler_tool_and_timer_firing(db_session):
    now = clock_now()
    # Timer in the past (due immediately)
    run_at = now - timedelta(seconds=1)

    # Schedule check
    timer_res = await tools.call(
        "schedule_check",
        {"case_id": "case-sched-test", "run_at": run_at, "reason": "SLA check"},
        case_id="case-sched-test",
        db=db_session,
    )
    assert timer_res["status"] == "pending"

    # Process due timers
    from backend.app.tools.scheduler import process_due_timers
    fired = await process_due_timers(db=db_session)
    fired_ids = [f["id"] for f in fired]
    assert timer_res["id"] in fired_ids
