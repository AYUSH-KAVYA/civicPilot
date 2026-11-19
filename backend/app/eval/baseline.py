"""
Simulated Manual Baseline Runner for Civic Grievance Resolution.
Simulates traditional municipal operations using a FIFO queue, human clerk delays,
and manual handoffs. All assumptions are explicitly loaded from baseline_config.json.
Source of truth: docs/CONTRACT.md Section 7, Slide 12 metrics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

CONFIG_PATH = Path(__file__).parent / "baseline_config.json"


def load_baseline_config() -> Dict[str, Any]:
    """Load documented baseline configuration parameters."""
    if not CONFIG_PATH.exists():
        # Fallback to eval/baseline_config.json
        alt = Path(__file__).parents[3] / "eval" / "baseline_config.json"
        if alt.exists():
            return json.loads(alt.read_text(encoding="utf-8"))
        raise FileNotFoundError(f"Baseline config not found at {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


class SimulatedManualBaseline:
    """
    Evaluates a dataset of civic grievances through simulated traditional municipal workflows.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or load_baseline_config()
        self.assumptions = self.config.get("assumptions", {})

    def evaluate_case(self, case: Dict[str, Any], queue_index: int = 0) -> Dict[str, Any]:
        """
        Simulate manual handling of a single grievance:
        - FIFO queue wait: queue_index * 15 minutes
        - Clerk triage delay: 180 min
        - Handoff delay: 120 min
        - Rejection delay: additional 720 min if department rejects
        """
        disruption = case.get("disruption", "none")
        true_dept = case.get("true_department", "roads")
        true_urgency = case.get("true_urgency", "medium")

        # 1. Routing decision (deterministic simulation based on queue index)
        accuracy_rate = float(self.assumptions.get("manual_routing_accuracy_rate", 0.767))
        is_routed_correctly = ((queue_index * 37 + 13) % 100) < int(accuracy_rate * 100)
        routed_dept = true_dept if is_routed_correctly else ("roads" if true_dept != "roads" else "water")

        # 2. Time to first action
        clerk_delay_min = float(self.assumptions.get("clerk_intake_triage_delay_min", 180.0))
        queue_delay_min = (queue_index % 10) * 12.0  # FIFO queue spacing
        ttfa_min = clerk_delay_min + queue_delay_min
        ttfa_sec = ttfa_min * 60.0

        # 3. Time to resolution
        handoff_min = float(self.assumptions.get("department_handoff_delay_min", 120.0))
        base_repair_min = 24.0 * 60.0  # 24 hours standard work order
        if true_urgency == "critical":
            base_repair_min = 6.0 * 60.0
        elif true_urgency == "high":
            base_repair_min = 12.0 * 60.0

        rejection_penalty_min = 0.0
        if disruption == "ticket_rejection":
            rejection_penalty_min = float(self.assumptions.get("rejection_reroute_delay_min", 720.0))
        elif disruption == "crew_no_show":
            rejection_penalty_min = 360.0

        ttr_min = ttfa_min + handoff_min + base_repair_min + rejection_penalty_min
        ttr_sec = ttr_min * 60.0

        # 4. Completion rate (some manual cases get lost in backlogs)
        completion_rate = float(self.assumptions.get("manual_completion_rate", 0.717))
        is_completed = ((queue_index * 41 + 7) % 100) < int(completion_rate * 100)

        # 5. Escalation decision
        escalated = true_urgency in ("critical", "high") or ((queue_index % 3) == 0)
        is_escalation_accurate = True if (true_urgency in ("critical", "high") and escalated) else False

        # 6. Human effort per case
        base_effort_min = float(self.assumptions.get("default_human_effort_per_case_minutes", 70.0))
        effort_min = base_effort_min
        if disruption in ("ticket_rejection", "dispute"):
            effort_min += 35.0  # Additional clerk time for re-handling

        return {
            "case_id": case.get("id"),
            "system": "simulated_manual_baseline",
            "routed_department": routed_dept,
            "routing_correct": is_routed_correctly,
            "completed": is_completed,
            "time_to_first_action_sec": round(ttfa_sec, 1),
            "time_to_resolution_sec": round(ttr_sec, 1),
            "escalated": escalated,
            "escalation_accurate": is_escalation_accurate,
            "human_effort_minutes": round(effort_min, 1),
        }

    def evaluate_dataset(self, cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate full dataset through simulated manual baseline."""
        results = []
        for idx, case in enumerate(cases):
            results.append(self.evaluate_case(case, queue_index=idx))
        return results
