"""
CivicPilot Scenario Route Handlers.
Exposes the core execution handler for POST /api/demo/scenarios/{scenario}/run.
Source of truth: docs/CONTRACT.md Section 7.
"""

from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.scenarios.runner import run_scenario


async def handle_scenario_run(scenario: str, db: AsyncSession, autoplay: bool = True) -> Dict[str, Any]:
    """Execute scenario and return structured result."""
    return await run_scenario(scenario_name=scenario, db=db)
