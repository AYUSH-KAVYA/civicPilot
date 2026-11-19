"""
Root eval/runner.py shim and CLI runner for evaluation suite.
Usage:
    python eval/runner.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

if "DATABASE_URL" not in os.environ or "localhost:5432" in os.environ.get("DATABASE_URL", ""):
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///civicpilot_eval.db"
    os.environ["MOCK_LLM"] = os.getenv("MOCK_LLM", "true")

from backend.app.db.models import Base
from backend.app.db.session import engine
from backend.app.eval.runner import run_evaluation_suite


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("=================================================================")
    print("Running CivicPilot Benchmark Evaluation Suite (Dataset N=60)")
    print("=================================================================\n")

    res = await run_evaluation_suite()

    print(f"Test Set Size: {res['test_set_size']} grievances")
    print(f"Eval Run ID: {res['run_id']}\n")

    scorecard = res["slide_12_scorecard"]
    print(f"{'Metric':<25} | {'Manual Baseline':<16} | {'CivicPilot':<16} | {'Delta / Improvement':<18}")
    print("-" * 82)
    for m, vals in scorecard.items():
        label = m.replace("_", " ").title()
        b_val = vals.get("manual_baseline", "")
        c_val = vals.get("civicpilot", "")
        d_val = vals.get("improvement") or vals.get("speedup") or vals.get("reduction") or vals.get("savings", "")
        print(f"{label:<25} | {b_val:<16} | {c_val:<16} | {d_val:<18}")

    print("\nResults exported to eval/eval_results.json and eval/eval_results.csv")


if __name__ == "__main__":
    asyncio.run(main())
