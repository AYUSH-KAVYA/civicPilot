"""
CivicPilot Evaluation Metrics (Slide 12).
Computes the 6 comparative evaluation metrics between the simulated manual baseline
and the autonomous CivicPilot system:
1. completion_rate: % of reported grievances successfully resolved
2. routing_accuracy: % of grievances assigned to the correct municipal department
3. time_to_first_action: Mean duration (seconds/minutes) to first operational tool call
4. time_to_resolution: Mean total duration (hours) to verified case closure
5. escalation_precision: Precision of SLA/urgency escalations [TP / (TP + FP)]
6. human_effort_per_case: Mean clerk/officer intervention time (minutes) per case
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any, Dict, List


def compute_metrics(eval_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute aggregate metrics from a list of per-case evaluation records.
    """
    total = len(eval_records)
    if total == 0:
        return {
            "test_set_size": 0,
            "completion_rate": 0.0,
            "routing_accuracy": 0.0,
            "time_to_first_action_sec": 0.0,
            "time_to_resolution_sec": 0.0,
            "escalation_precision": 0.0,
            "human_effort_minutes": 0.0,
        }

    completed_count = sum(1 for r in eval_records if r.get("completed"))
    routing_correct_count = sum(1 for r in eval_records if r.get("routing_correct"))

    ttfa_list = [float(r.get("time_to_first_action_sec", 0.0)) for r in eval_records]
    ttr_list = [float(r.get("time_to_resolution_sec", 0.0)) for r in eval_records]
    effort_list = [float(r.get("human_effort_minutes", 0.0)) for r in eval_records]

    # Escalation precision: True positives / Total escalations
    total_escalated = sum(1 for r in eval_records if r.get("escalated"))
    accurate_escalated = sum(1 for r in eval_records if r.get("escalation_accurate"))
    escalation_precision = (
        round(accurate_escalated / total_escalated, 3) if total_escalated > 0 else 1.0
    )

    return {
        "test_set_size": total,
        "completion_rate": round(completed_count / total, 3),
        "completion_rate_pct": f"{round(completed_count / total * 100, 1)}%",
        "routing_accuracy": round(routing_correct_count / total, 3),
        "routing_accuracy_pct": f"{round(routing_correct_count / total * 100, 1)}%",
        "time_to_first_action_sec": round(sum(ttfa_list) / total, 2),
        "time_to_first_action_min": round(sum(ttfa_list) / (total * 60.0), 2),
        "time_to_resolution_sec": round(sum(ttr_list) / total, 2),
        "time_to_resolution_hours": round(sum(ttr_list) / (total * 3600.0), 2),
        "escalation_precision": escalation_precision,
        "escalation_precision_pct": f"{round(escalation_precision * 100, 1)}%",
        "human_effort_minutes": round(sum(effort_list) / total, 1),
    }


def compare_systems(
    baseline_records: List[Dict[str, Any]],
    civicpilot_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate Slide 12 comparative scorecard between Manual Baseline and CivicPilot.
    """
    baseline_metrics = compute_metrics(baseline_records)
    civicpilot_metrics = compute_metrics(civicpilot_records)

    test_size = len(baseline_records)

    # Compute deltas
    ttfa_speedup = (
        round(baseline_metrics["time_to_first_action_sec"] / max(0.001, civicpilot_metrics["time_to_first_action_sec"]), 1)
    )
    ttr_reduction_pct = round(
        (1.0 - (civicpilot_metrics["time_to_resolution_sec"] / max(0.001, baseline_metrics["time_to_resolution_sec"]))) * 100,
        1,
    )
    human_effort_savings_pct = round(
        (1.0 - (civicpilot_metrics["human_effort_minutes"] / max(0.001, baseline_metrics["human_effort_minutes"]))) * 100,
        1,
    )

    comparison = {
        "test_set_size": test_size,
        "slide_12_scorecard": {
            "completion_rate": {
                "manual_baseline": baseline_metrics["completion_rate_pct"],
                "civicpilot": civicpilot_metrics["completion_rate_pct"],
                "improvement": f"+{round((civicpilot_metrics['completion_rate'] - baseline_metrics['completion_rate']) * 100, 1)}%",
            },
            "routing_accuracy": {
                "manual_baseline": baseline_metrics["routing_accuracy_pct"],
                "civicpilot": civicpilot_metrics["routing_accuracy_pct"],
                "improvement": f"+{round((civicpilot_metrics['routing_accuracy'] - baseline_metrics['routing_accuracy']) * 100, 1)}%",
            },
            "time_to_first_action": {
                "manual_baseline": f"{baseline_metrics['time_to_first_action_min']} min",
                "civicpilot": f"{civicpilot_metrics['time_to_first_action_sec']} sec",
                "speedup": f"{ttfa_speedup}x faster",
            },
            "time_to_resolution": {
                "manual_baseline": f"{baseline_metrics['time_to_resolution_hours']} hrs",
                "civicpilot": f"{civicpilot_metrics['time_to_resolution_hours']} hrs",
                "reduction": f"-{ttr_reduction_pct}%",
            },
            "escalation_precision": {
                "manual_baseline": baseline_metrics["escalation_precision_pct"],
                "civicpilot": civicpilot_metrics["escalation_precision_pct"],
                "improvement": f"+{round((civicpilot_metrics['escalation_precision'] - baseline_metrics['escalation_precision']) * 100, 1)}%",
            },
            "human_effort_per_case": {
                "manual_baseline": f"{baseline_metrics['human_effort_minutes']} min",
                "civicpilot": f"{civicpilot_metrics['human_effort_minutes']} min",
                "savings": f"-{human_effort_savings_pct}%",
            },
        },
        "baseline_summary": baseline_metrics,
        "civicpilot_summary": civicpilot_metrics,
    }
    return comparison


def export_metrics_csv(comparison: Dict[str, Any]) -> str:
    """Format slide 12 comparison table as CSV text."""
    scorecard = comparison.get("slide_12_scorecard", {})
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Metric", "Simulated Manual Baseline", "CivicPilot Multi-Agent", "Delta / Improvement"])

    rows = [
        ("Completion Rate", "completion_rate", "improvement"),
        ("Routing Accuracy", "routing_accuracy", "improvement"),
        ("Time to First Action", "time_to_first_action", "speedup"),
        ("Time to Resolution", "time_to_resolution", "reduction"),
        ("Escalation Precision", "escalation_precision", "improvement"),
        ("Human Effort per Case", "human_effort_per_case", "savings"),
    ]

    for label, key, delta_key in rows:
        data = scorecard.get(key, {})
        writer.writerow([
            label,
            data.get("manual_baseline", ""),
            data.get("civicpilot", ""),
            data.get(delta_key, ""),
        ])

    return output.getvalue()
