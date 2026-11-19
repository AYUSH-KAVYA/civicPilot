from datetime import datetime, timezone

import pytest

from agents.intake import run as intake_run
from agents.triage import run as triage_run
from agents.planner import build_plan, replan


class Clock:
    def now(self):
        return datetime(2026, 11, 19, tzinfo=timezone.utc)


class Tools:
    async def call(self, name, args, case_id, agent):
        if name == "geo_lookup":
            return {"ward_id": "ward-7", "office_id": "roads-office"}
        return []


class Context:
    llm = None
    tools = Tools()
    clock = Clock()

    async def emit(self, *args, **kwargs):
        return None


class State:
    pass


@pytest.mark.asyncio
async def test_intake_treats_vague_report_and_requests_location():
    state = State()
    state.id = "case-1"
    state.raw = type("Raw", (), {"text": "broken", "image_urls": [], "language": "en"})()
    result = await intake_run(state, Context())
    assert "location" in result.state_patch["intake"]["missing_info"]
    assert result.next == "await_location"


@pytest.mark.asyncio
async def test_triage_and_planner_golden_case():
    state = State()
    state.id = "case-2"
    state.raw = type("Raw", (), {
        "text": "Live wire near school",
        "lat": 28.61,
        "lng": 77.20,
        "address_text": "Main Road",
    })()
    state.intake = {
        "category": "electricity",
        "summary": "Live wire near school",
        "location": {"address": "Main Road", "lat": 28.61, "lng": 77.20},
        "visible_damage": ["fallen wire"],
        "nearby_sensitive_sites": ["school"],
        "language_detected": "en",
        "missing_info": [],
        "confidence": 0.82,
    }
    triage = await triage_run(state, Context())
    state.triage = triage.state_patch["triage"]
    assert triage.state_patch["triage"]["urgency"] == "critical"
    assert triage.state_patch["triage"]["department_id"] == "electricity"

    plan = await build_plan(state, Context())
    assert plan.version == 1
    assert {step.tool for step in plan.steps} >= {"create_ticket", "assign_crew", "notify", "schedule_check"}


@pytest.mark.asyncio
async def test_replan_keeps_completed_steps_and_increments_version():
    state = State()
    state.plan = {
        "version": 2,
        "steps": [
            {"id": "done", "title": "Done", "tool": "create_ticket", "args": {},
             "depends_on": [], "due_at": "2026-11-20T00:00:00Z",
             "fallback": None, "risk_tier": "routine", "status": "done", "result": {"ok": True}},
            {"id": "pending", "title": "Pending", "tool": "assign_crew", "args": {},
             "depends_on": ["done"], "due_at": "2026-11-20T00:00:00Z",
             "fallback": None, "risk_tier": "routine", "status": "pending", "result": None},
        ],
    }
    revised = await replan(state, "Ticket rejected", {"disruption": "ticket_rejection"})
    assert revised.version == 3
    assert revised.steps[0].status == "done"
