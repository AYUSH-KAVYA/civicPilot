"""
Tests for audit events, PII masking, and SSE streaming broadcast.
"""

import pytest

from backend.app.core.events import (
    emit_event,
    mask_contact,
    mask_pii_data,
    mask_pii_string,
)
from backend.app.schemas import AgentName, Phase


def test_mask_contact():
    assert mask_contact("alice@example.com") == "a***e@example.com"
    assert mask_contact("+1-555-123-4567") == "***-***-4567"


def test_mask_pii_string():
    text = "Please reach citizen John at john.doe@civic.org or call 555-888-9999 immediately."
    masked = mask_pii_string(text)
    assert "john.doe@civic.org" not in masked
    assert "[EMAIL_MASKED]" in masked
    assert "555-888-9999" not in masked
    assert "[PHONE_MASKED]" in masked


def test_mask_pii_nested_data():
    raw_data = {
        "user": {"email": "test@domain.com", "phone": "123-456-7890"},
        "notes": ["Call 987-654-3210 for access", "All clean"],
    }
    cleaned = mask_pii_data(raw_data)
    assert cleaned["user"]["email"] == "[EMAIL_MASKED]"
    assert cleaned["user"]["phone"] == "[PHONE_MASKED]"
    assert "[PHONE_MASKED]" in cleaned["notes"][0]


@pytest.mark.asyncio
async def test_emit_event_persists_and_masks(db_session):
    event = await emit_event(
        case_id="case-test-1",
        agent=AgentName.intake,
        phase=Phase.perceive,
        summary="Citizen contact: contact@metro.com",
        detail={"phone": "555-000-1111", "status": "ok"},
        db=db_session,
    )
    assert event.case_id == "case-test-1"
    assert "contact@metro.com" not in event.summary
    assert "[EMAIL_MASKED]" in event.summary
    assert event.detail["phone"] == "[PHONE_MASKED]"
