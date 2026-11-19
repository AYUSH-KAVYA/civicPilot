# CivicPilot Frontend (Part 4 Scope)

The user interface for **CivicPilot**, an autonomous multi-agent grievance resolution system that takes citizen grievances from initial report through verified closure across municipal domains (Water, Roads, Sanitation, Electricity, Parks, Public Health).

---

## Architecture & Capabilities

Built with **Next.js 16 (App Router)**, **TypeScript**, **Tailwind CSS**, **shadcn/ui**, **Leaflet** for geospatial crew maps, and **Recharts** for evaluation analytics.

### Pages & Routes

1. **Landing Page (`/`)**:
   - Visual interactive pitch of the six-step multi-agent loop: **Perceive &rarr; Reason &rarr; Plan &rarr; Act &rarr; Evaluate &rarr; Adapt**.
   - Subsystem architecture breakdown: Orchestrator, Five Agents, Six Operational Tools, Policy Knowledge Base (pgvector), and Safety Guardrails.
   - Quick CTAs to report issues, launch the officer console, or inspect Case 1042.

2. **Citizen Reporting & Tracking Portal (`/report` & `/track/[id]`)**:
   - Multimodal grievance submission with text, photo upload, interactive Leaflet location picker (draggable pin & address search), browser GPS geocoding, and voice input via the Web Speech API.
   - Multilingual language selector (English, Spanish, Chinese, Vietnamese, Tagalog).
   - Live **StatusTracker** visualizing loop progress, SLA deadline countdown, assigned work orders, and crew details.
   - Simulated **NotificationInbox** receiving SMS and webhook alerts dispatched via the `notify` tool.
   - **EvidenceUpload** enabling supplemental citizen evidence and triggering Adaptation Rule (c).
   - **ConfirmClosure** allowing citizens to confirm satisfactory resolution or dispute closure (Adaptation Rule e).

3. **Officer Live Command Center (`/officer/cases`)**:
   - Real-time case feed updating via Server-Sent Events (SSE) with automatic polling fallback.
   - Live KPI counters: Open Grievances, At-Risk cases, Needs Human review, and Closed cases.
   - Multidimensional filtering by Status, Municipal Department, Urgency, and full-text keyword search.

4. **Case Detail Centerpiece (`/officer/cases/[id]`)**:
   - Live timeline of events colour-coded by loop phases (Perceive, Reason, Plan, Act, Evaluate, Adapt, Guardrail, Tool Calls).
   - Expandable tool calls displaying formatted JSON arguments and return payloads.
   - Executable DAG resolution plan showing dependencies, statuses, fallbacks, and risk tiers.
   - AI Confidence & Guardrails meters verifying threshold compliance (&ge;0.65).
   - Policy Knowledge Base citations displaying semantic search similarity scores, SLA limits, and escalation rules.
   - Interactive spatial Leaflet map showing incident coordinates, nearby sensitive infrastructure (e.g. schools, hospitals), and field crew positions.
   - In-flight sandbox disturbance buttons (Reject Ticket, Crew No-Show, Crew Check-In, Upload Repair Photo).

5. **Risk-Tiered Approvals & Needs-Human Queue (`/officer/approvals`)**:
   - Governance authorization queue for `sensitive` and `critical` risk-tiered steps (e.g., Case 1042 evacuation & grid isolation sign-off).
   - Agent reasoning packet inspector displaying context, rationale, and protocol citations.
   - One-click Approve and Reject actions.
   - Needs-Human queue allowing officers to clarify ambiguous reports and unblock autonomous execution.

6. **Interactive Demo & Simulation Controller (`/officer/demo`)**:
   - One-click launchers for the 3 deck scenarios (**Happy Path**, **Road Disruption**, **Ambiguity Gate**) and the **Case 1042** critical benchmark.
   - Simulated clock displaying `SIM_TIME_SCALE` (60x acceleration).
   - External cron ping trigger (`POST /api/tick`).
   - Live terminal log stream of simulation events.

7. **Slide 12 Metrics & Evaluation Scorecard (`/officer/metrics`)**:
   - Complete 6-metric comparative scorecard: Completion Rate, Routing Accuracy, Time to First Action, Time to Resolution, Escalation Precision, and Human Effort per Case.
   - Explicitly labeled Simulated Manual Baseline vs. CivicPilot.
   - Test-set size indicator (60 benchmark cases).
   - Comparative BarCharts using Recharts.
   - Interactive button to run the evaluation benchmark harness (`POST /api/eval/run`).

---

## Mock Mode (`NEXT_PUBLIC_USE_MOCKS=true`)

The frontend runs 100% autonomously without a live backend:

- Setting `NEXT_PUBLIC_USE_MOCKS=true` activates in-memory realistic fixtures and simulated event streaming.
- Submitting grievances, approving critical actions, injecting disruptions, and resolving edge cases updates the in-memory state reactively.
- Switching `NEXT_PUBLIC_USE_MOCKS=false` directs all API calls to the live FastAPI backend specified by `NEXT_PUBLIC_API_URL`.

---

## Local Development

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Run local development server
npm run dev

# 3. Build for production
npm run build

# 4. Start production server
npm run start
```
