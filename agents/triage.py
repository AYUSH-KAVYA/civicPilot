from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional

from pydantic import BaseModel, Field

from kb.search import policy_search


class TriageDecision(BaseModel):
    urgency: str
    department_id: str
    ward_id: Optional[str] = None
    office_id: Optional[str] = None
    deadline_hours: int
    policy_refs: list[str] = Field(default_factory=list)
    rationale: str
    confidence: float = Field(ge=0, le=1)


@dataclass
class AgentResult:
    state_patch: dict
    next: Optional[str]
    confidence: float


async def run(state: Any, ctx: Any) -> AgentResult:
    intake = getattr(state, "intake", None)
    raw = getattr(state, "raw", None)
    if hasattr(intake, "model_dump"):
        intake_data = intake.model_dump()
    elif isinstance(intake, dict):
        intake_data = intake
    else:
        intake_data = {}

    lat = getattr(raw, "lat", None) if raw else None
    lng = getattr(raw, "lng", None) if raw else None
    address = getattr(raw, "address_text", None) if raw else None
    location = intake_data.get("location") or {}
    lat = lat if lat is not None else location.get("lat")
    lng = lng if lng is not None else location.get("lng")
    address = address or location.get("address")

    geo = await _call_tool(ctx, "geo_lookup", {
        "lat": lat, "lng": lng, "address_text": address
    }, state)

    department_hint = intake_data.get("category") or "roads"
    department_map = {
        "road": "roads", "water": "water", "sanitation": "sanitation",
        "electricity": "electricity", "parks": "parks",
        "public_health": "public_health",
    }
    department_id = department_map.get(department_hint, department_hint)
    query = f"{intake_data.get('summary', '')} {' '.join(intake_data.get('visible_damage', []))}"
    chunks = await policy_search(query, department_id=department_id, k=4)
    similar = await _similar_cases(ctx, intake_data.get("summary", ""), lat, lng, state)

    text = f"{intake_data.get('summary', '')} {' '.join(intake_data.get('visible_damage', []))}".lower()
    sensitive = [str(v).lower() for v in intake_data.get("nearby_sensitive_sites", [])]
    urgent_terms = ("live wire", "collapsed", "injury", "fire", "smoke", "flood", "gas", "electrocution")
    sensitive_present = bool(sensitive) or any(site in sensitive for site in ("school", "hospital", "clinic"))
    hazard_present = any(term in text for term in urgent_terms)
    urgency = "critical" if sensitive_present or hazard_present else "high" if "major" in text or similar else "medium"
    deadline_hours = 4 if urgency == "critical" else 24 if urgency == "high" else 72
    if chunks:
        sla = next((c.get("sla_hours") for c in chunks if c.get("sla_hours")), None)
        if sla:
            deadline_hours = min(deadline_hours, int(sla))

    refs = [c["chunk_id"] for c in chunks]
    rationale = (
        f"Routed to {department_id} based on the reported service category"
        + (" and a sensitive or safety-critical site" if sensitive_present or hazard_present else "")
        + ("; matched prior cases at or near this location" if similar else "")
        + "."
    )
    decision = TriageDecision(
        urgency=urgency,
        department_id=department_id,
        ward_id=geo.get("ward_id"),
        office_id=geo.get("office_id"),
        deadline_hours=deadline_hours,
        policy_refs=refs,
        rationale=rationale,
        confidence=_calibrate(intake_data.get("confidence", 0.7), len(chunks), bool(similar)),
    )

    for chunk in chunks:
        await ctx.emit(
            getattr(state, "id", "unknown"),
            "triage",
            "reason",
            f"Used policy chunk {chunk['chunk_id']} for routing",
            {"chunk_id": chunk["chunk_id"], "department_id": department_id, "query": query},
            tool_name="policy_search",
            reason=chunk.get("doc_title"),
        )

    return AgentResult(
        state_patch={"status": "TRIAGED", "triage": decision.model_dump()},
        next="planner",
        confidence=decision.confidence,
    )


async def _call_tool(ctx, name, args, state):
    tools = getattr(ctx, "tools", None)
    if tools is not None and hasattr(tools, "call"):
        return await tools.call(name, args, getattr(state, "id", "unknown"), "triage")
    return {"ward_id": None, "office_id": None}


async def _similar_cases(ctx, text, lat, lng, state):
    tools = getattr(ctx, "tools", None)
    if tools is not None and hasattr(tools, "call"):
        return await tools.call(
            "similar_cases",
            {"text": text, "lat": lat, "lng": lng, "radius_m": 500, "k": 5},
            getattr(state, "id", "unknown"),
            "triage",
        )
    try:
        from kb.similar_cases import similar_cases
        return await similar_cases(text, lat, lng, 500, 5)
    except Exception:
        return []


def _calibrate(intake_confidence: float, policy_count: int, has_similar: bool) -> float:
    confidence = float(intake_confidence) * 0.75
    confidence += min(policy_count, 4) * 0.05
    confidence += 0.05 if has_similar else 0
    return round(max(0.35, min(0.95, confidence)), 2)
