"""
CLI Scenario Runner for CivicPilot.
Usage:
    python scenarios/run.py happy
    python scenarios/run.py disruption
    python scenarios/run.py ambiguity
    python scenarios/run.py case1042
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Set SQLite fallback if no live Postgres is running
if "DATABASE_URL" not in os.environ or "localhost:5432" in os.environ.get("DATABASE_URL", ""):
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///civicpilot_demo.db"
    os.environ["MOCK_LLM"] = os.getenv("MOCK_LLM", "true")

from backend.app.db.models import Base
from backend.app.db.seed import seed_database
from backend.app.db.session import engine
from backend.app.scenarios.runner import run_scenario


async def main() -> None:
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        await seed_database()
    except Exception:
        pass

    scenario = sys.argv[1] if len(sys.argv) > 1 else "happy"
    print(f"==================================================")
    print(f"Running CivicPilot Demo Scenario: {scenario.upper()}")
    print(f"==================================================")

    res = await run_scenario(scenario_name=scenario, sim_scale=120.0, step_delay_sec=0.2)

    print(f"\nScenario: {res['scenario']}")
    print(f"Case ID: {res['case_id']}")
    print(f"Final Status: {res['final_status']}")
    print(f"Total Audit Events: {res['total_events']}\n")
    print("Timeline Events:")
    for ev in res["events"]:
        print(f"  [{ev['phase'].upper():<10}] ({ev['agent']:<12}) {ev['summary']}")


if __name__ == "__main__":
    asyncio.run(main())
