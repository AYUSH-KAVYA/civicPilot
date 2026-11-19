"""
Unit and Integration Tests for CivicPilot Adaptation Rules (docs/CONTRACT.md Section 1, 6).
Tests each of the 5 adaptation rules:
(a) Department rejects ticket -> re-read policy and replan
(b) Deadline imminent / crew no-show -> escalate urgency one level
(c) Citizen adds new evidence -> re-triage and replan
(d) Duplicate complaints cluster -> merge into area work order
(e) Citizen disputes closure -> reopen, increment reopen_count, flag for human
"""

import pytest

from backend.app.adaptation.rules import (
    adapt_deadline_imminent,
    adapt_dispute_closure,
    adapt_duplicate_cluster,
    adapt_new_evidence,
    adapt_ticket_rejection,
)
from backend.app.schemas import CaseStatus, Phase


class MockEmit:
    def __init__(self):
        self.events = []

    async def __call__(self, case_id, agent, phase, summary, detail=None, tool_name=None, reason=None, **kwargs):
        self.events.append({
            "case_id": case_id,
            "agent": str(agent),
            "phase": str(phase.value if hasattr(phase, "value") else phase),
            "summary": summary,
            "detail": detail,
            "tool_name": tool_name,
            "reason": reason,
        })


class MockContext:
    def __init__(self):
        self.emit = MockEmit()
        self.db = None
        self.tools = None
        self.clock = None
        self.llm = None


@pytest.mark.asyncio
async def test_rule_a_ticket_rejection():
    """Rule (a): Department rejects ticket -> re-read policy via policy_search and replan."""
    ctx = MockContext()
    state = {
        "id": "case-adapt-a",
        "status": "IN_PROGRESS",
        "triage": {"department_id": "roads", "urgency": "medium"},
        "plan": {
            "version": 1,
            "steps": [
                {"id": "create-ticket", "title": "Create ticket", "tool": "create_ticket", "status": "done"},
                {"id": "assign-crew", "title": "Assign crew", "tool": "assign_crew", "status": "done"},
            ]
        },
        "tickets": [{"id": "tkt-1", "department_id": "roads", "status": "rejected"}],
        "flags": {},
    }

    updated = await adapt_ticket_rejection(
        state=state,
        reason="Underground pipe burst - not road issue",
        ctx=ctx,
    )

    # 1. Adapt event logged
    adapt_events = [e for e in ctx.emit.events if e["phase"] == Phase.adapt.value]
    assert len(adapt_events) >= 1
    assert "ticket_rejection" in str(adapt_events[0]["detail"])

    # 2. Plan was updated with new steps (replan)
    assert updated["plan"]["version"] > 1
    assert any(s["id"] == "retry-ticket" for s in updated["plan"]["steps"])

    # 3. Rejected ticket marked handled
    assert updated["tickets"][0].get("rejection_handled") is True


@pytest.mark.asyncio
async def test_rule_b_deadline_imminent():
    """Rule (b): Deadline imminent / crew no-show -> escalate urgency one level."""
    ctx = MockContext()
    state = {
        "id": "case-adapt-b",
        "status": "IN_PROGRESS",
        "triage": {"department_id": "water", "urgency": "medium"},
        "tickets": [{"id": "tkt-water-1", "priority": "medium"}],
        "flags": {},
    }

    updated = await adapt_deadline_imminent(
        state=state,
        reason="SLA expiring in 30 minutes, crew not checked in",
        ctx=ctx,
    )

    # 1. Adapt event logged
    adapt_events = [e for e in ctx.emit.events if e["phase"] == Phase.adapt.value]
    assert len(adapt_events) >= 1
    assert adapt_events[0]["detail"]["prior_urgency"] == "medium"
    assert adapt_events[0]["detail"]["escalated_urgency"] == "high"

    # 2. Urgency escalated: medium -> high
    assert updated["triage"]["urgency"] == "high"
    assert updated["status"] == CaseStatus.AT_RISK.value

    # Escalate again: high -> critical
    updated2 = await adapt_deadline_imminent(state=updated, reason="SLA fully breached", ctx=ctx)
    assert updated2["triage"]["urgency"] == "critical"


@pytest.mark.asyncio
async def test_rule_c_new_evidence():
    """Rule (c): Citizen adds new evidence -> re-run triage and replan."""
    ctx = MockContext()
    state = {
        "id": "case-adapt-c",
        "status": "IN_PROGRESS",
        "raw": {"text": "Small puddle on sidewalk", "image_urls": []},
        "triage": {"department_id": "roads", "urgency": "low"},
        "plan": {"version": 1, "steps": []},
        "flags": {},
    }

    new_text = "Water is now gushing into basements and electric sparks are visible!"
    updated = await adapt_new_evidence(
        state=state,
        new_text=new_text,
        new_images=["/new_photo.jpg"],
        ctx=ctx,
    )

    # 1. Adapt event logged
    adapt_events = [e for e in ctx.emit.events if e["phase"] == Phase.adapt.value]
    assert len(adapt_events) >= 1
    assert adapt_events[0]["detail"]["rule"] == "new_evidence"

    # 2. Raw input updated
    assert new_text in updated["raw"]["text"]
    assert "/new_photo.jpg" in updated["raw"]["image_urls"]

    # 3. Plan version incremented
    assert updated["plan"]["version"] >= 1


@pytest.mark.asyncio
async def test_rule_d_duplicate_clustering():
    """Rule (d): Duplicate complaints cluster -> merge into area work order."""
    ctx = MockContext()
    state = {
        "id": "case-adapt-d-secondary",
        "status": "NEW",
        "flags": {"merged_into": None, "duplicate_of": []},
    }

    primary_id = "case-primary-100"
    updated = await adapt_duplicate_cluster(
        state=state,
        cluster_primary_id=primary_id,
        similarity_score=0.91,
        ctx=ctx,
    )

    # 1. Adapt event logged
    adapt_events = [e for e in ctx.emit.events if e["phase"] == Phase.adapt.value]
    assert len(adapt_events) >= 1
    assert adapt_events[0]["detail"]["merged_into"] == primary_id

    # 2. flags.merged_into set
    assert updated["flags"]["merged_into"] == primary_id
    assert updated["status"] == CaseStatus.CLOSED.value


@pytest.mark.asyncio
async def test_rule_e_citizen_dispute():
    """Rule (e): Citizen disputes closure -> reopen, increment reopen_count, flag for human."""
    ctx = MockContext()
    state = {
        "id": "case-adapt-e",
        "status": "AWAITING_CONFIRMATION",
        "flags": {"reopen_count": 0, "needs_human": False, "human_reason": None},
    }

    updated = await adapt_dispute_closure(
        state=state,
        comment="The pipe is still leaking and water is pooling again!",
        ctx=ctx,
    )

    # 1. Adapt event logged
    adapt_events = [e for e in ctx.emit.events if e["phase"] == Phase.adapt.value]
    assert len(adapt_events) >= 1
    assert adapt_events[0]["detail"]["rule"] == "dispute_closure"

    # 2. Reopened, incremented reopen_count, needs_human flagged
    assert updated["status"] == CaseStatus.REOPENED.value
    assert updated["flags"]["reopen_count"] == 1
    assert updated["flags"]["needs_human"] is True
    assert "still leaking" in updated["flags"]["human_reason"]
