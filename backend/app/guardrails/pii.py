"""
CivicPilot Guardrails: PII Masking Helpers
Re-exports and extends PII masking utilities used across all agent logs,
state serialization, and LLM prompts.
Source of truth: docs/CONTRACT.md Section 5.
"""

from __future__ import annotations

import re
from typing import Any

from backend.app.core.events import (
    EMAIL_REGEX,
    PHONE_REGEX,
    mask_contact,
    mask_pii_data,
    mask_pii_string,
)

__all__ = [
    "EMAIL_REGEX",
    "PHONE_REGEX",
    "mask_contact",
    "mask_pii_string",
    "mask_pii_data",
    "mask_all_pii_text",
    "sanitize_log_record",
]

# Additional identifiers: SSN, Aadhaar / National ID, credit cards
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CARD_REGEX = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")


def mask_all_pii_text(text: str) -> str:
    """Mask email, phone numbers, SSNs, and credit cards in text."""
    if not text:
        return text
    text = mask_pii_string(text)
    text = SSN_REGEX.sub("[SSN_MASKED]", text)
    text = CARD_REGEX.sub("[CARD_MASKED]", text)
    return text


def sanitize_log_record(record: Any) -> Any:
    """Recursively mask PII in dicts, lists, or strings for audit logs."""
    return mask_pii_data(record)
