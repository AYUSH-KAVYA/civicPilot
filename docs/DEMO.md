# CivicPilot — Demo Script

> **Audience**: Hackathon judges, city tech leads, stakeholders  
> **Duration**: ~10 minutes total (3 scenarios + Case 1042)  
> **Setup**: Officer dashboard open at http://localhost:3000/officer, Demo Controls tab visible  
> **Tip**: Set `SIM_TIME_SCALE=60` in the backend so multi-hour SLAs play out in seconds during the demo.

---

## Before You Begin

| Checklist | Done? |
|---|---|
| Backend running (`uvicorn` or Docker Compose) | ☐ |
| Frontend running (`npm run dev` or Vercel) | ☐ |
| `SIM_TIME_SCALE=60` set for clock acceleration | ☐ |
| Browser open at `/officer/demo` with the 4 scenario buttons visible | ☐ |
| Second browser tab open at `/report` for citizen perspective | ☐ |
| Screen mirrored / shared | ☐ |

---

## Scenario 1 — Happy Path: Water Leak (Urgent)

> **What this shows**: The nominal 6-step loop working flawlessly from report to verified closure.

### Talking Points
> *"A citizen reports a burst pipe. Watch how CivicPilot handles everything — classify, plan, dispatch, follow up — without a single human touch."*

### Minute-by-Minute Script

| Time | Action | What the Audience Sees |
|---|---|---|
| **0:00** | Switch to `/report` tab. Type: *"There's water gushing out of a broken pipe at 42 Elm Street. The road is flooded."* Upload a sample leak photo. Click **Submit**. | **Report page** — form submits, case ID appears, status badge shows `NEW`. |
| **0:05** | Switch to `/officer/cases` tab. | **Case list** refreshes via SSE; new card appears at top with `INTAKE` badge and Water department icon. |
| **0:15** | Click into the case. Watch the **Timeline** panel. | 🟣 **perceive** event appears: *"Intake agent parsing media and geocoding location."* `parse_media` and `geo_lookup` tool call cards expand showing JSON args → results (ward 7, Water dept). |
| **0:30** | Timeline continues auto-scrolling. | 🔵 **reason** event: *"Triage agent querying policy KB."* `policy_search` card shows SOP chunk from `water-sop.md` — SLA: 4 hours. Urgency badge changes to **HIGH**. Confidence meter shows 0.87. |
| **0:45** | | 🟦 **plan** event: *"Planner created 4-step plan."* Plan panel on right side populates: steps for create_ticket, assign_crew, notify citizen, schedule_check. Risk tier badges: all **routine** (green). |
| **1:00** | | 🟢 **act** event: Ticket `TKT-2041` created. Crew `W-07` assigned. Citizen SMS sent: *"Your case CP-XXXX has been assigned…"* Steps tick to ✅ **done** one by one. Status badge changes to `IN_PROGRESS`. |
| **1:30** | In **Demo Controls**, click **Crew Check-In** button (sandbox signal). | Timeline: *"Crew W-07 checked in at Elm Street."* Map panel shows crew marker moving toward the incident pin. |
| **2:00** | Click **Upload Repair Photo** in Demo Controls. | 🟡 **evaluate** event: *"Evaluator verifying photo evidence."* Photo thumbnail appears in timeline. Confidence meter 0.94. Plan step `repair_complete` → ✅ done. Status → `AWAITING_CONFIRMATION`. |
| **2:15** | Switch to `/track/[case-id]` tab (citizen tracking). | **Citizen tracking page** shows *"Repair completed — please confirm."* with **Confirm closure** and **Reopen** buttons. |
| **2:30** | Click **Confirm closure**. | Status badge snaps to `CLOSED` 🎉. Resolution time shown. Officer dashboard case card moves to Closed bucket. |

### Presenter Tips
- Keep the **Timeline** and **Plan** panels side-by-side (use the split-pane layout).
- Point out the **phase colour legend** in the UI (purple=perceive, blue=reason, green=act).
- Highlight the **confidence meter** rising from 0 to 0.87 as evidence is processed.

---

## Scenario 2 — Disruption: Road Pothole (Ticket Rejected)

> **What this shows**: The adaptation loop — CivicPilot recovers from a mid-flight failure without human intervention.

### Talking Points
> *"The Roads department rejects the ticket — a common real-world failure. CivicPilot detects the rejection, re-routes to a different office, and completes the job."*

### Minute-by-Minute Script

| Time | Action | What the Audience Sees |
|---|---|---|
| **0:00** | Click **Run Disruption Scenario** in Demo Controls. | Report auto-submitted: *"Large pothole on South Bridge Road, causing tyre damage."* Status: `INTAKE`. |
| **0:15** | | Triage completes. Urgency: **MEDIUM**. Department: Roads. Status: `TRIAGED → PLANNED`. |
| **0:30** | Click **Reject Ticket** in Demo Controls (sandbox signal). | 🔴 Timeline event: *"Roads dept rejected ticket TKT-2042: 'Duplicate work order in progress.'"* Status badge flips to `AT_RISK` with orange indicator. Plan step `create_ticket` → ❌ failed. |
| **0:45** | | 🟠 **adapt** event: *"Orchestrator triggered replanning. Reason: ticket rejected by primary department."* Adaptation card expands showing old plan vs. new plan diff. |
| **1:00** | | 🟦 **plan** event: *"Planner v2 — re-routed to Roads District Office B."* New plan appears with updated `assign_crew` step. Status: `IN_PROGRESS`. |
| **1:30** | | New crew `R-12` assigned. Citizen notification sent: *"Your case has been re-assigned to District Office B."* |
| **2:30** | Click **Upload Repair Photo** in Demo Controls. | Evaluator confirms fill complete. Status → `AWAITING_CONFIRMATION`. Citizen confirms → `CLOSED`. |

### Presenter Tips
- Pause on the **adaptation card** — it shows the old plan crossed out and the new plan alongside the reason. This is the core AI differentiator.
- Point out the `AT_RISK` badge changing colour in the case list — judges scanning the list will notice immediately.

---

## Scenario 3 — Ambiguity: Vague Report (Guardrail Triggered)

> **What this shows**: CivicPilot is not reckless. When confidence is too low, it escalates to a human instead of guessing.

### Talking Points
> *"An officer gets a vague noise complaint with no location. The system's confidence falls below the threshold, the guardrail fires, and the officer gets a full reasoning packet to make an informed decision."*

### Minute-by-Minute Script

| Time | Action | What the Audience Sees |
|---|---|---|
| **0:00** | Click **Run Ambiguity Scenario** in Demo Controls. | Report submitted: *"There's some kind of problem near my house. It smells bad sometimes."* No location, no image. Status: `INTAKE`. |
| **0:30** | | 🟣 perceive: `parse_media` extracts: category=Unknown, missing_info=["location", "category", "description"]. Confidence meter fills only to **0.41**. |
| **0:35** | | 🔴 **guardrail** event fires: *"Confidence 0.41 < threshold 0.65. Stopping automated processing."* Red guardrail banner appears in Timeline. |
| **0:40** | | Status badge → `NEEDS_HUMAN` 🔴. Case appears in **Approvals / Needs-Human queue** with high-priority indicator. |
| **0:45** | Switch to `/officer/approvals`. | **Approvals page** shows the case. Click the case card to expand the **Reasoning Packet**: intake summary, extracted fields, what's missing, why confidence is low, suggested questions for the citizen. |
| **1:00** | In the reasoning packet, click **Add Note & Resolve**. Type: *"Called citizen — confirmed location: 14 Canal Road. Category: Sanitation (blocked drain)."* Click **Resolve**. | POST to `/api/cases/{id}/resolve`. Status flips to `TRIAGED`. Orchestrator resumes with officer's note as context. Normal flow continues. |
| **1:30** | | Triage runs with the officer's note, assigns Sanitation dept. Confidence 0.91. Plan created. IN_PROGRESS. |

### Presenter Tips
- Emphasise the **guardrail firing** — this is a safety feature, not a failure. CivicPilot is honest about uncertainty.
- Show the **reasoning packet** up close — the fact that the AI explains *why* it's uncertain (not just that it is) is the differentiator.
- If running live, you can manually type a vague report in the citizen interface to make the demo feel real.

---

## Scenario 4 — Case 1042: High-Voltage Wire Near School (Critical)

> **What this shows**: Risk-tiered approval. CivicPilot requires a human sign-off before acting on a critical case.

### Talking Points
> *"A downed power line near a primary school. This is life-safety critical. CivicPilot correctly escalates for officer approval before dispatching any crew — it won't act autonomously on this."*

### Minute-by-Minute Script

| Time | Action | What the Audience Sees |
|---|---|---|
| **0:00** | Click **Run Case 1042** in Demo Controls. | Report: *"Fallen high-voltage power line across the gate of St. Mary's Primary School. Sparking. Children arriving in 20 minutes."* Status: `INTAKE`. |
| **0:15** | | 🟣 perceive: location geocoded, nearby sensitive sites: **School (50m)**. `nearby_sensitive_sites` field populates in Intake panel. |
| **0:20** | | 🔵 reason: Triage. Policy KB returns `electricity-sop.md` critical escalation rule. Urgency: **CRITICAL** (red badge). Department: Electricity Emergency. |
| **0:30** | | 🟦 plan: Planner creates plan. Step `dispatch_emergency_crew` has risk_tier = **critical** (red badge). Step status → `awaiting_approval`. Yellow approval banner appears: *"Supervisor approval required before dispatching."* |
| **0:35** | | Approval request appears in `/officer/approvals` queue. Priority: CRITICAL. Notification badge in nav shows 1. |
| **0:45** | Switch to `/officer/approvals`. Click the approval card. Review the plan step details, rationale, policy ref. Click **Approve**. | POST `/api/approvals/{id}` with `{decision: "approve"}`. Approval card moves to Approved. |
| **1:00** | Switch back to case detail. | Plan step `dispatch_emergency_crew` → ✅ running. Emergency crew `E-01` assigned. Status: `IN_PROGRESS`. Citizen notified: *"Emergency crew dispatched — ETA 8 minutes."* |
| **2:00** | Click **Upload Repair Photo** in Demo Controls (line secured, area cordoned). | Evaluator verifies. Confidence 0.96. Status → `AWAITING_CONFIRMATION`. |
| **2:10** | Officer resolves from dashboard (no citizen confirmation needed for critical). | Status → `CLOSED`. Total elapsed: 2:10 sim-time. |

### Presenter Tips
- Point out that **the system did not act** without approval — this is the trust-and-safety story.
- Show the **risk tier badge** progression: green (routine) → red (critical) for different plan steps.
- The **SIM_TIME_SCALE** makes this scenario feel urgent — real-time clock acceleration adds drama.

---

## Quick Reference — UI Panels per Phase

| Phase | Where to look in the UI |
|---|---|
| `perceive` | Timeline (purple events) + Intake panel (right column) |
| `reason` | Timeline (blue events) + Triage panel (confidence meter, policy refs) |
| `plan` | Plan panel (step cards, risk tier badges, dependencies) |
| `act` | Timeline (green events) + Tickets panel + Map (crew pin) |
| `evaluate` | Timeline (amber events) + Plan step status badges |
| `adapt` | Timeline (orange adaptation card with old/new plan diff) |
| `guardrail` | Red guardrail banner in timeline + NEEDS_HUMAN status badge |
| `tool_call` | Expandable JSON cards in timeline (click to expand args/results) |

---

## General Presenter Tips

- **Use split-screen**: Timeline on the left, Plan/Approvals on the right.
- **Zoom in** on the confidence meter when talking about guardrails.
- **Demo Controls panel** (`/officer/demo`) is your backstage — keep it in a third monitor or hidden tab.
- If a scenario runs too fast (SIM_TIME_SCALE=60), reduce to `SIM_TIME_SCALE=10` for more visible step transitions.
- Each scenario auto-runs and auto-posts events — you are narrating, not clicking through forms.
