"""
CivicPilot Guardrails Package.
Exposes confidence checks, risk-tiered approvals, PII masking, completeness checks,
and prompt-injection hygiene.
"""

from backend.app.guardrails.completeness import (
    AuditCompletenessError,
    assert_event_emitted,
    verify_event_completeness,
)
from backend.app.guardrails.confidence import (
    build_reasoning_packet,
    check_and_apply_confidence_guardrail,
    is_low_confidence,
)
from backend.app.guardrails.injection import (
    is_suspected_injection,
    sanitize_citizen_text,
    wrap_untrusted_input,
)
from backend.app.guardrails.pii import (
    mask_all_pii_text,
    mask_contact,
    mask_pii_data,
    mask_pii_string,
    sanitize_log_record,
)
from backend.app.guardrails.risk_tiers import (
    ApprovalRequiredException,
    enforce_risk_tier,
)

__all__ = [
    "is_low_confidence",
    "build_reasoning_packet",
    "check_and_apply_confidence_guardrail",
    "enforce_risk_tier",
    "ApprovalRequiredException",
    "mask_contact",
    "mask_pii_string",
    "mask_pii_data",
    "mask_all_pii_text",
    "sanitize_log_record",
    "verify_event_completeness",
    "assert_event_emitted",
    "AuditCompletenessError",
    "is_suspected_injection",
    "sanitize_citizen_text",
    "wrap_untrusted_input",
]
