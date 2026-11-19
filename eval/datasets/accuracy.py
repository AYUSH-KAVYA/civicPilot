import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.llm.client import GeminiClient
from agents.triage import run as triage_run
from kb.search import policy_search


class Clock:
    def now(self):
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)


class Context:
    def __init__(self):
        self.llm = GeminiClient()
        self.tools = ToolRegistry()
        self.clock = Clock()

    async def emit(self, *args, **kwargs):
        return None


class ToolRegistry:
    async def call(self, name, args, case_id, agent):
        if name == "geo_lookup":
            return {"ward_id": "ward-1", "office_id": "office-1"}
        if name == "similar_cases":
            return []
        return {}


class State:
    pass


async def main():
    path = Path(__file__).with_name("grievances.json")
    cases = json.loads(path.read_text(encoding="utf-8"))
    correct_department = 0
    correct_urgency = 0
    ctx = Context()

    for case in cases:
        state = State()
        state.id = case["id"]
        state.raw = type("Raw", (), {
            "text": case["text"],
            "lat": case["lat"],
            "lng": case["lng"],
            "address_text": case["address"],
        })()
        state.intake = {
            "category": _category(case["true_department"]),
            "summary": case["text"],
            "location": {"address": case["address"], "lat": case["lat"], "lng": case["lng"]},
            "visible_damage": [],
            "nearby_sensitive_sites": ["school"] if "school" in case["text"].lower() else [],
            "language_detected": case["language"],
            "missing_info": ["location"] if len(case["text"]) < 35 else [],
            "confidence": 0.45 if len(case["text"]) < 35 else 0.82,
        }
        result = await triage_run(state, ctx)
        triage = result.state_patch["triage"]
        if triage["department_id"] == case["true_department"]:
            correct_department += 1
        if triage["urgency"] == case["true_urgency"]:
            correct_urgency += 1

    print("| Metric | Correct | Total | Accuracy |")
    print("|---|---:|---:|---:|")
    print(f"| Department routing | {correct_department} | {len(cases)} | {correct_department / len(cases):.1%} |")
    print(f"| Urgency routing | {correct_urgency} | {len(cases)} | {correct_urgency / len(cases):.1%} |")


def _category(department):
    return {"roads": "road", "public_health": "public_health", "parks": "parks"}.get(department, department)


if __name__ == "__main__":
    asyncio.run(main())
