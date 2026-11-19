"""
CivicPilot Adaptation Package.
Exposes the 5 deck adaptation rules:
- adapt_ticket_rejection
- adapt_deadline_imminent
- adapt_new_evidence
- adapt_duplicate_cluster
- adapt_dispute_closure
"""

from backend.app.adaptation.rules import (
    adapt_deadline_imminent,
    adapt_dispute_closure,
    adapt_duplicate_cluster,
    adapt_new_evidence,
    adapt_ticket_rejection,
)

__all__ = [
    "adapt_ticket_rejection",
    "adapt_deadline_imminent",
    "adapt_new_evidence",
    "adapt_duplicate_cluster",
    "adapt_dispute_closure",
]
