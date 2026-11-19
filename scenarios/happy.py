import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.scenarios.runner import run_scenario

if __name__ == "__main__":
    asyncio.run(run_scenario("happy", sim_scale=120.0))
