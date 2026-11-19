# CivicPilot End-to-End Tests (P4 Ownership)

This directory contains automated end-to-end integration and scenario tests using **Playwright**.

The tests validate the complete multi-agent grievance resolution system across citizen reporting, the 6-step loop, and municipal officer supervision.

---

## Tested Scenarios

The suite directly tests all core user journeys and benchmark scenarios matching the presentation deck:

1. **Happy Path Scenario (Case #1001)**:
   - Citizen files an urgent water leak grievance at `/report`.
   - AI intake parses damage and geocodes coordinates.
   - Plan DAG created with routine risk tier.
   - Work order and nearest crew dispatched.
   - Citizen tracks live loop progress and submits supplemental evidence.

2. **Disruption Scenario (Case #1002)**:
   - Roads department rejects work order in `/officer/cases/1002`.
   - **Adaptation Rule (a)** triggers in the audit trail.
   - Policy Knowledge Base is queried and work order is automatically replanned.

3. **Ambiguity Scenario (Case #1003)**:
   - Vague report triggers the **Confidence Guardrail** (`confidence < 0.65`).
   - Execution halts safely into the `NEEDS_HUMAN` queue.
   - Officer inspects agent reasoning packet in `/officer/approvals` and resolves the case.

4. **Case 1042 Benchmark (Case #1042)**:
   - Downed power line within 50m of elementary school flagged at **CRITICAL** risk tier.
   - Plan step `s1` (100m perimeter evacuation & utility shutoff) halts in `awaiting_approval`.
   - Officer reviews risk-tiered authorization in `/officer/approvals` and clicks **Approve & Dispatch**.
   - Autonomous execution resumes and critical response team is mobilized.

5. **Slide 12 Scorecard & Metrics**:
   - Validates all 6 measurable metrics (Completion Rate, Routing Accuracy, Time to First Action, Time to Resolution, Escalation Precision, Human Effort per Case).
   - Verifies explicit labeling of the Simulated Manual Baseline.
   - Confirms benchmark test-set size of 60 cases.

---

## How to Run Locally

### 1. Install Dependencies
```bash
cd e2e
npm install
npx playwright install --with-deps chromium
```

### 2. Run Tests Against Local Frontend
With the Next.js frontend running on `http://localhost:3000` (or let Playwright auto-start it via `webServer`):
```bash
npm test
```

### 3. Run Tests with Interactive UI
```bash
npm run test:ui
```

### 4. Run Tests Against a Deployed Vercel URL
Set the `PLAYWRIGHT_TEST_BASE_URL` environment variable:
```bash
PLAYWRIGHT_TEST_BASE_URL=https://your-civicpilot.vercel.app npm test
```
