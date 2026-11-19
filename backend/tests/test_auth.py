"""
Tests for officer JWT and citizen case-scoped tokens.
"""

import pytest
from fastapi import HTTPException

from backend.app.core.auth import (
    create_case_access_token,
    create_officer_token,
    verify_case_access_token,
    verify_officer_token,
)


def test_officer_token_lifecycle():
    token = create_officer_token("officer-123", role="supervisor")
    payload = verify_officer_token(token)
    assert payload["sub"] == "officer-123"
    assert payload["role"] == "supervisor"
    assert payload["type"] == "officer"


def test_citizen_token_lifecycle():
    case_id = "case-xyz-987"
    token = create_case_access_token(case_id)
    resolved_id = verify_case_access_token(token, expected_case_id=case_id)
    assert resolved_id == case_id


def test_citizen_token_mismatch_fails():
    case_id = "case-original"
    token = create_case_access_token(case_id)
    with pytest.raises(HTTPException) as exc_info:
        verify_case_access_token(token, expected_case_id="case-different")
    assert exc_info.value.status_code == 403


def test_invalid_token_fails():
    with pytest.raises(HTTPException):
        verify_officer_token("invalid.token.string")
