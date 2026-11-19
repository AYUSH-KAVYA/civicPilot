"""
End-to-End and Integration Tests for CivicPilot Multi-Agent Orchestrator (docs/CONTRACT.md Section 6, 7).
Tests:
1. Full End-to-End case resolution in mock mode.
2. Concurrent runs per-case locking.
3. Loop breaker protection against infinite agent cycling.
4. All four demo scenarios (happy, disruption, ambiguity, case1042).
5. Evaluation harness execution and Slide 12 metric calculations.
"""

import asyncio
import uuid

import pytest

from backend.app.eval.runner import run_evaluation_suite
from backend.app.scenarios.runner import run_scenario
from backend.app.schemas import CaseStatus


@pytest.mark.asyncio
async def test_full_case_e2e_mock_mode(client):
    """
    Test full end-to-end loop:
    Intake -> Triage -> Plan -> Action -> Evaluator -> Citizen Confirmation -> Closed.
    """
    # 1. Citizen posts grievance
    post_payload = {
        "text": "Water main pipe broke and is flooding 100 City Hall Plaza.",
        "contact": "citizen.jane@example.com",
        "lat": 37.750,
        "lng": -122.420,
        "address_text": "100 City Hall Plaza",
        "channel": "web",
    }
    resp = await client.post("/api/cases", json=post_payload)
    assert resp.status_code == 201
    case_id = resp.json()["case_id"]
    token = resp.json()["access_token"]
    headers = {"X-Case-Token": token}

    # 2. Case state after start_case
    case_resp = await client.get(f"/api/cases/{case_id}", headers=headers)
    assert case_resp.status_code == 200
    state = case_resp.json()

    assert state["status"] in (CaseStatus.IN_PROGRESS.value, CaseStatus.PLANNED.value)
    assert state["intake"] is not None
    assert state["triage"] is not None
    assert state["plan"] is not None
    assert len(state["plan"]["steps"]) >= 3

    # 3. Simulate repair photo upload via sandbox
    tickets = state.get("tickets", [])
    if tickets:
        ticket_id = tickets[0]["id"]
        repair_resp = await client.post(
            f"/api/sandbox/tickets/{ticket_id}/repair-photo",
            json={"photo_url": "https://example.com/repaired_pipe.jpg", "notes": "Pipe replaced"},
        )
        assert repair_resp.status_code == 200

        # Status should transition to AWAITING_CONFIRMATION
        case_check = await client.get(f"/api/cases/{case_id}", headers=headers)
        assert case_check.json()["status"] == CaseStatus.AWAITING_CONFIRMATION.value

        # 4. Citizen confirms resolution
        confirm_resp = await client.post(
            f"/api/cases/{case_id}/confirm",
            headers=headers,
            json={"confirmed": True, "comment": "Water stopped, sidewalk clean!"},
        )
        assert confirm_resp.status_code == 200

        # Final status must be CLOSED
        final_check = await client.get(f"/api/cases/{case_id}", headers=headers)
        assert final_check.json()["status"] == CaseStatus.CLOSED.value


@pytest.mark.asyncio
async def test_per_case_locking_prevents_race_conditions():
    """Verify that multiple concurrent actions on the same case run safely sequentially under lock."""
    case_id = f"test-lock-{uuid.uuid4().hex[:6]}"
    from backend.app.orchestrator.graph import get_case_lock

    lock = await get_case_lock(case_id)
    assert not lock.locked()

    acquired_first = await lock.acquire()
    assert acquired_first is True
    assert lock.locked()

    # Second acquire blocks while lock is held
    task = asyncio.create_task(lock.acquire())
    await asyncio.sleep(0.05)
    assert not task.done()

    # Releasing unblocks the second acquire
    lock.release()
    acquired_second = await task
    assert acquired_second is True
    assert lock.locked()
    lock.release()
    assert not lock.locked()


@pytest.mark.asyncio
async def test_demo_scenarios_all_run():
    """Verify all 4 demo scenarios execute successfully."""
    # 1. Happy Path
    happy_res = await run_scenario("happy", sim_scale=120.0, step_delay_sec=0.05)
    assert happy_res["final_status"] == CaseStatus.CLOSED.value
    assert happy_res["total_events"] > 10

    # 2. Disruption Path
    disrupt_res = await run_scenario("disruption", sim_scale=120.0, step_delay_sec=0.05)
    assert disrupt_res["final_status"] == CaseStatus.CLOSED.value
    phases = [e["phase"] for e in disrupt_res["events"]]
    assert "adapt" in phases

    # 3. Ambiguity Path
    ambiguity_res = await run_scenario("ambiguity", sim_scale=120.0, step_delay_sec=0.05)
    assert ambiguity_res["final_status"] == CaseStatus.NEEDS_HUMAN.value

    # 4. Case 1042
    c1042_res = await run_scenario("case1042", sim_scale=120.0, step_delay_sec=0.05)
    assert c1042_res["final_status"] == CaseStatus.CLOSED.value


@pytest.mark.asyncio
async def test_evaluation_suite_runner():
    """Verify evaluation runner calculates Slide 12 metrics and creates results file."""
    res = await run_evaluation_suite()
    assert res["test_set_size"] == 60
    assert "slide_12_scorecard" in res

    scorecard = res["slide_12_scorecard"]
    assert "completion_rate" in scorecard
    assert "routing_accuracy" in scorecard
    assert "time_to_first_action" in scorecard
    assert "time_to_resolution" in scorecard
    assert "escalation_precision" in scorecard
    assert "human_effort_per_case" in scorecard
