"""
CivicPilot Evaluation Package.
Exposes benchmark runner, baseline simulator, and Slide 12 metrics calculator.
"""

from backend.app.eval.baseline import SimulatedManualBaseline, load_baseline_config
from backend.app.eval.metrics import compare_systems, compute_metrics, export_metrics_csv
from backend.app.eval.runner import run_evaluation_suite

__all__ = [
    "run_evaluation_suite",
    "SimulatedManualBaseline",
    "load_baseline_config",
    "compute_metrics",
    "compare_systems",
    "export_metrics_csv",
]
