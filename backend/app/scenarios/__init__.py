"""
CivicPilot Scenarios Package.
Exposes the demo scenario timelines, handlers, and runner:
- happy: Urgent leak to verified closure
- disruption: Ticket rejection, re-plan, re-route
- ambiguity: Low-confidence case halted for officer
- case1042: High voltage wire near school requiring supervisor approval
"""

from backend.app.scenarios.handlers import handle_scenario_run
from backend.app.scenarios.runner import run_scenario
from backend.app.scenarios.timeline import SCENARIO_CONFIGS

__all__ = [
    "run_scenario",
    "handle_scenario_run",
    "SCENARIO_CONFIGS",
]
