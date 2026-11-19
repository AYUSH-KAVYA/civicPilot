"""
CivicPilot Demo Scenarios: Timeline Specifications.
Defines the 3 live-demo scenarios plus Case 1042:
1. happy path: urgent water leak to verified closure.
2. disruption: ticket rejected, re-plan, re-route.
3. ambiguity: low confidence, handed to officer with reasoning.
4. case1042: high-voltage sparking wire near school requiring supervisor approval.
Source of truth: docs/CONTRACT.md Section 7.
"""

from typing import Any, Dict

SCENARIO_CONFIGS: Dict[str, Dict[str, Any]] = {
    "happy": {
        "title": "Happy Path: Urgent Water Leak to Verified Resolution",
        "description": "Standard high-urgency water leak resolved cleanly through autonomous perception, triage, planning, action, photo verification, and citizen confirmation.",
        "text": "Major water pipe burst near City Hall Plaza. Clean water is gushing into the street and flooding the curb.",
        "category": "water",
        "lat": 37.750,
        "lng": -122.420,
        "address": "100 City Hall Plaza, Metroville",
        "contact": "citizen.jane@example.com",
        "channel": "web",
        "image_urls": ["/demo/water_leak_before.jpg"],
        "expected_phases": ["perceive", "reason", "plan", "act", "evaluate"],
        "repair_photo_url": "/demo/water_leak_repaired.jpg",
        "citizen_comment": "Water has stopped completely, drain is clear. Thank you!",
    },
    "disruption": {
        "title": "Disruption Recovery: Ticket Rejection & Escalation",
        "description": "Cross-department misdirection triggers ticket rejection, policy re-reading, automated re-planning, and rapid resolution.",
        "text": "Deep crater and water pooling on North Boulevard blocking the outbound express bus lane.",
        "category": "roads",
        "lat": 37.760,
        "lng": -122.420,
        "address": "450 North Boulevard, Metroville",
        "contact": "+1-555-0199",
        "channel": "chat",
        "image_urls": ["/demo/crater_road.jpg"],
        "rejection_reason": "Roads department: sub-surface water main failure caused cave-in. Must be routed to Water & Utilities.",
        "repair_photo_url": "/demo/road_repaired.jpg",
        "citizen_comment": "Bus lane reopened and pothole repaved.",
    },
    "ambiguity": {
        "title": "Ambiguity Guardrail: Low Confidence Hand-off",
        "description": "Vague citizen complaint fails confidence threshold (< 0.65) and safely halts for human officer triage with full reasoning packet.",
        "text": "Something smells really weird and there is a problem near the corner.",
        "category": "unknown",
        "lat": 37.740,
        "lng": -122.420,
        "address": "Corner of 5th and Elm",
        "contact": "concerned_neighbor@example.com",
        "channel": "voice",
        "image_urls": [],
        "expected_phases": ["perceive", "reason", "guardrail"],
    },
    "case1042": {
        "title": "Case 1042: High Voltage Sparking Line Near Elementary School",
        "description": "Critical tier electrical hazard near sensitive site (school) requires human officer approval before executing grid quadrant isolation.",
        "text": "EMERGENCY: High voltage electrical power line snapped and is sparking on the sidewalk next to Lincoln Elementary School playground.",
        "category": "electricity",
        "lat": 37.752,
        "lng": -122.423,
        "address": "1200 Lincoln Way (Near Lincoln Elementary School)",
        "contact": "principal.smith@metroville.gov",
        "channel": "web",
        "image_urls": ["/demo/sparking_wire.jpg"],
        "sensitive_site": "Lincoln Elementary School",
        "critical_step_id": "step-high-voltage-isolation",
        "officer_name": "Supervisor Miller",
        "officer_note": "Emergency isolation of Power Grid Quadrant 4 authorized. Field crew dispatched with safety protocol.",
        "repair_photo_url": "/demo/power_line_secured.jpg",
        "citizen_comment": "Power restored safely, danger tape removed and line replaced.",
    },
}
