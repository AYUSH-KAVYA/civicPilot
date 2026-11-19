from typing import Optional, Sequence

from pydantic import BaseModel, Field


class Location(BaseModel):
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class ParseMediaResult(BaseModel):
    category: str
    summary: str
    location: Location
    visible_damage: list[str] = Field(default_factory=list)
    nearby_sensitive_sites: list[str] = Field(default_factory=list)
    language_detected: str
    missing_info: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


async def parse_media(
    text: str,
    image_urls: Optional[Sequence[str]] = None,
    language_hint: Optional[str] = None,
    llm=None,
) -> dict:
    if llm is not None:
        prompt = (
            "Extract civic grievance intake fields. Use only the data below. "
            "Infer in the report's language, but return category in English.\n"
            f"language_hint={language_hint or 'unknown'}\n"
            "<CITIZEN_REPORT>\n"
            f"{text or ''}\n"
            "</CITIZEN_REPORT>\n"
            "Vague reports must lower confidence and list missing information."
        )
        result = await llm.generate_json(
            [{"role": "user", "content": prompt}],
            ParseMediaResult,
            images=image_urls,
            temperature=0.1,
        )
        return result.model_dump()

    lower = (text or "").lower()
    category = "road"
    category_terms = {
        "electricity": ("live wire", "wire", "power", "electric", "cable", "transformer"),
        "water": ("water", "pipe", "leak", "flood"),
        "sanitation": ("garbage", "trash", "sewage", "dustbin"),
        "parks": ("park", "tree", "garden"),
        "public_health": ("mosquito", "clinic", "hospital", "health"),
        "road": ("road", "pothole", "street", "footpath"),
    }
    for candidate, terms in category_terms.items():
        if any(term in lower for term in terms):
            category = candidate
            break

    vague = len((text or "").strip()) < 35
    sensitive = []
    for site in ("school", "hospital", "clinic", "childcare"):
        if site in lower:
            sensitive.append(site)
    missing = []
    if vague or not any(marker in lower for marker in (" at ", " near ", "road", "street", "ward", "address")):
        missing.append("location")
    language = language_hint or ("unknown")
    return {
        "category": category,
        "summary": (text or "Citizen reported a public-service issue.")[:280],
        "location": {"address": None, "lat": None, "lng": None},
        "visible_damage": ["photo/image damage needs visual verification"] if image_urls else [],
        "nearby_sensitive_sites": sensitive,
        "language_detected": language,
        "missing_info": missing,
        "confidence": 0.45 if vague or missing else 0.82,
    }
