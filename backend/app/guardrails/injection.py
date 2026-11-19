"""
CivicPilot Guardrails: Prompt-Injection Hygiene
Ensures citizen text and images are treated as untrusted data and never instructions.
Source of truth: docs/CONTRACT.md Section 9.
"""

from __future__ import annotations

import re
from typing import Dict

# Suspicious phrases commonly used in LLM prompt injection attempts
SUSPICIOUS_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(an?\s+)?admin", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?system\s+prompt", re.IGNORECASE),
    re.compile(r"print\s+all\s+(hidden\s+)?instructions", re.IGNORECASE),
    re.compile(r"sudo\s+mode", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"<\|im_end\|>", re.IGNORECASE),
]


def is_suspected_injection(text: str) -> bool:
    """Return True if text contains common prompt injection attack signatures."""
    if not text:
        return False
    return any(pattern.search(text) for pattern in SUSPICIOUS_PATTERNS)


def sanitize_citizen_text(text: str) -> str:
    """
    Sanitize citizen text to prevent breaking delimiter boundaries.
    Does not delete the user's grievance, but escapes delimiters and wraps cleanly.
    """
    if not text:
        return ""
    # Strip any artificial XML closing tags that attempt prompt breakouts
    sanitized = text.replace("</CITIZEN_REPORT>", "[TAG_ESCAPED]")
    sanitized = sanitized.replace("</citizen_report>", "[TAG_ESCAPED]")
    return sanitized.strip()


def wrap_untrusted_input(text: str, channel: str = "web") -> Dict[str, str]:
    """
    Safely wrap citizen text in structured boundary delimiters with untrusted data flags.
    """
    cleaned = sanitize_citizen_text(text)
    wrapped = (
        f"<CITIZEN_REPORT channel=\"{channel}\" untrusted=\"true\">\n"
        f"{cleaned}\n"
        f"</CITIZEN_REPORT>"
    )
    return {
        "raw_text": text,
        "sanitized_text": cleaned,
        "wrapped_prompt_segment": wrapped,
        "is_suspicious": str(is_suspected_injection(text)).lower(),
    }
