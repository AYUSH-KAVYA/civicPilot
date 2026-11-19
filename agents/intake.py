from dataclasses import dataclass
from typing import Any, Optional

from tools.parse_media import parse_media


@dataclass
class AgentResult:
    state_patch: dict
    next: Optional[str]
    confidence: float


async def run(state: Any, ctx: Any) -> AgentResult:
    raw = getattr(state, "raw", None)
    text = getattr(raw, "text", "") if raw else ""
    image_urls = getattr(raw, "image_urls", []) if raw else []
    language_hint = getattr(raw, "language", None) if raw else None

    result = await parse_media(text, image_urls, language_hint, getattr(ctx, "llm", None))
    await ctx.emit(
        getattr(state, "id", "unknown"),
        "intake",
        "perceive",
        "Parsed citizen report into intake fields",
        {"intake": result, "citizen_text_treated_as_untrusted": True},
    )

    needs_location = "location" in result["missing_info"]
    if needs_location:
        await ctx.emit(
            getattr(state, "id", "unknown"),
            "citizen",
            "message",
            "Requested missing report location",
            {"template": "location_request", "reason": "location_missing"},
        )

    confidence = float(result["confidence"])
    return AgentResult(
        state_patch={"status": "INTAKE", "intake": result},
        next="await_location" if needs_location else "triage",
        confidence=confidence,
    )
