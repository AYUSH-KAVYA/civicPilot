import json
import math
import os
from pathlib import Path
from typing import Optional


DATASET = Path(__file__).parents[1] / "eval" / "datasets" / "grievances.json"


def _distance(lat1, lng1, lat2, lng2) -> Optional[float]:
    if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
        return None
    return math.hypot(float(lat1) - float(lat2), float(lng1) - float(lng2)) * 111_000


async def similar_cases(text: str, lat: float, lng: float, radius_m: int, k: int) -> list[dict]:
    if not DATASET.exists():
        return []
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    matches = []
    text_tokens = set((text or "").lower().split())
    for case in cases:
        distance = _distance(lat, lng, case.get("lat"), case.get("lng"))
        if distance is not None and distance > radius_m:
            continue
        case_tokens = set(case.get("text", "").lower().split())
        overlap = len(text_tokens & case_tokens) / max(1, len(text_tokens | case_tokens))
        matches.append({
            "id": case["id"],
            "text": case["text"],
            "department_id": case["true_department"],
            "urgency": case["true_urgency"],
            "address": case.get("address"),
            "distance_m": round(distance) if distance is not None else None,
            "similarity": round(overlap, 3),
        })
    matches.sort(key=lambda item: item["similarity"], reverse=True)
    return matches[:k]
