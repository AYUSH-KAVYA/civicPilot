# CivicPilot

CivicPilot is an autonomous multi-agent grievance resolution system that takes citizen issues from initial report through verified closure across municipal domains (Water, Roads, Sanitation, Electricity, Parks, Public Health).

Loop architecture: **Perceive -> Reason -> Plan -> Act -> Evaluate -> Adapt**.

---

## Part 1: Backend Foundation, REST API, Tools & Sandbox (P1)

P1 owns the foundational FastAPI application, database layer with `pgvector`, audit event stream (SSE), the four operational tools, the department simulator sandbox, and deployment infrastructure.

### Key Capabilities Built by P1:
1. **Source of Truth Schemas (`backend/app/schemas.py`)**:
   - Complete Pydantic models for `CaseState`, `PlanStep`, `CaseEvent`, `Ticket`, `Approval`, and all domain enums defined in `docs/CONTRACT.md`.
2. **Database & Master Data (`backend/app/db/`)**:
   - 15 SQLAlchemy async tables supporting PostgreSQL with `pgvector` and SQLite fallback.
   - Initial Alembic migration (`backend/alembic/versions/`).
   - Automated seeding script: 6 city departments, 10 wards with GeoJSON polygons, 10 offices, 15 response crews with coordinates, and SLA policy documents.
3. **Simulation Clock (`backend/app/core/clock.py`)**:
   - `clock.now()` honours `SIM_TIME_SCALE` (e.g. 60x speed) so multi-hour/multi-day SLAs play out in minutes during live demos.
4. **Audit Trail & SSE Streaming (`backend/app/core/events.py`)**:
   - `emit_event()` automatically masks citizen PII (phone numbers, emails) from summaries and details.
   - Real-time Server-Sent Events (SSE) broadcast stream per case (`GET /api/cases/{id}/stream`) and globally for officers (`GET /api/events/stream`).
5. **Tool Registry & 4 Operational Tools (`backend/app/tools/`)**:
   - `tools.call()` dispatcher with retries, timeouts, and automatic `tool_call`/`tool_result` event emissions.
   - `geo_lookup`: Point-in-polygon with Shapely over ward boundaries, plus Nominatim geocoding with graceful fallback.
   - `ticketing`: Ticket creation, nearest-available crew assignment via Haversine distance, updates, and crew listing.
   - `notify`: Citizen sandbox notification inbox in DB, plus optional live Resend email integration when `RESEND_API_KEY` is present.
   - `scheduler`: Manages scheduled verification checks in the `timers` table, runs background timer processing, and handles `POST /api/tick` external cron pings.
6. **Department Sandbox (`backend/app/sandbox/`)**:
   - Interactive simulation endpoints for live demos: ticket rejection, crew check-in, crew no-show, and repair photo upload.
7. **REST API (`backend/app/api/`)**:
   - Comprehensive endpoints for cases, citizen messaging, confirmations, officer approvals, demo scenarios, eval runs, and metrics summary (`GET /api/metrics/summary`).
   - Dual authentication: Bearer JWT for municipal officers, and case-scoped tokens for citizens.

---

## Part 3: Orchestration, Agents, Adaptation, Guardrails & Evaluation (P3)

P3 implements the core agent execution graph, Action & Evaluator agents, the 5 deck adaptation rules, safety guardrails, runnable live-demo scenarios, and the comparative evaluation harness.

### Key Capabilities Built by P3:

1. **Async Multi-Agent Orchestrator (`backend/app/orchestrator/`, `orchestrator/`)**:
   - Asynchronous directed agent graph executing the Perceive -> Reason -> Plan -> Act -> Evaluate -> Adapt loop.
   - Per-case concurrency lock (`asyncio.Lock`) preventing race conditions during asynchronous events.
   - State persistence after *every* node transition with audit event emission.
   - Per-node execution timeouts (30s) and exponential-backoff retries.
   - Maximum-iteration loop breaker (25 iterations) halting infinite agent loops cleanly into `NEEDS_HUMAN`.
   - Complete public contract API: `start_case`, `resume_case`, `handle_citizen_message`, `handle_citizen_confirmation`, `handle_approval`, `handle_sandbox_signal`.

2. **Action Agent (`backend/app/agents/action.py`, `agents/action.py`)**:
   - Evaluates dependency order (`depends_on`) before executing each plan step via `tools.call`.
   - Dynamic parameter resolution across inter-step dependencies (`ticket_id`, `run_at`, `department_id`).
   - Automatic execution of step fallbacks upon tool errors.
   - Safety risk tier enforcement: routine steps auto-run; sensitive steps notify supervisors; critical steps create an `ApprovalModel` and pause execution in `awaiting_approval`.

3. **Evaluator Agent (`backend/app/agents/evaluator.py`, `agents/evaluator.py`)**:
   - Compares reality against plan steps and deadlines using `clock.now()` to determine if a case is `on track`, `at risk`, `failed`, or `verified`.
   - Schedules periodic monitoring checks using `schedule_check`.
   - Inspects and verifies uploaded repair photos using the Gemini vision model (with mock fallback).
   - Manages state transitions: `IN_PROGRESS` -> `AWAITING_CONFIRMATION` -> `CLOSED`.

4. **Five Adaptation Rules (`backend/app/adaptation/`, `adaptation/`)**:
   - **Rule (a) Ticket Rejection**: Re-reads policy via `policy_search` and re-routes through `planner.replan`.
   - **Rule (b) Deadline Imminent / Crew No-Show**: Escalates urgency one level (`low` -> `medium` -> `high` -> `critical`) and reprioritizes work orders.
   - **Rule (c) Supplemental Citizen Evidence**: Incorporates new text/photos into state, re-runs triage, and replans.
   - **Rule (d) Duplicate Complaints Cluster**: Detects spatial and vector duplicate clusters, merges into active area work order, and sets `flags.merged_into`.
   - **Rule (e) Citizen Disputes Closure**: Reopens case (`REOPENED`), increments `reopen_count`, and flags for officer review (`flags.needs_human = True`).

5. **Safety Guardrails (`backend/app/guardrails/`, `guardrails/`)**:
   - **Confidence Threshold**: Any report below `CONFIDENCE_THRESHOLD = 0.65` immediately halts into `NEEDS_HUMAN` with a structured reasoning packet.
   - **Risk Tiers Enforcement**: Rigorous boundaries for `routine`, `sensitive`, and `critical` operations.
   - **PII Masking**: Comprehensive regex scrubbing for emails, phone numbers, SSNs, and credit card numbers across all logs and details.
   - **Prompt-Injection Hygiene**: Citizen input is treated strictly as untrusted data, sanitized, and isolated within `<CITIZEN_REPORT>` tags.
   - **Audit Completeness Check**: Verifies that every state transition and agent decision emits a corresponding audit event.

6. **Live Demo Scenarios (`backend/app/scenarios/`, `scenarios/`)**:
   - Powered by `SIM_TIME_SCALE` so multi-hour/multi-day timelines play out in ~3 minutes (or seconds during tests):
     - **Happy Path (`scenarios/happy.py`)**: Urgent water leak resolved to verified closure.
     - **Disruption (`scenarios/disruption.py`)**: Ticket rejected by roads department, automatically adapted, re-routed, and resolved.
     - **Ambiguity (`scenarios/ambiguity.py`)**: Vague citizen report stopped safely by confidence guardrail for human triage.
     - **Case 1042 (`scenarios/case1042.py`)**: High-voltage electrical wire sparking near elementary school requiring supervisor approval.
   - Unified CLI runner: `python scenarios/run.py [happy|disruption|ambiguity|case1042]`.

7. **Slide 12 Evaluation Harness (`backend/app/eval/`, `eval/`)**:
   - Replays P2's 60-grievance dataset (`eval/datasets/grievances.json`) with injected disruptions.
   - Compares the **Simulated Manual Baseline** (FIFO queue, clerk delays, handoff delays in `baseline_config.json`) against **CivicPilot**.
   - Computes all 6 metrics from Slide 12:
     1. Completion Rate
     2. Routing Accuracy
     3. Time to First Action
     4. Time to Resolution
     5. Escalation Precision
     6. Human Effort per Case
   - Persists benchmark records into `eval_runs` and `eval_results` database tables.
   - Exports results to `eval/eval_results.json` and `eval/eval_results.csv`.
   - CLI runner: `python eval/runner.py`.

---

## Getting Started

### Local Setup (Virtual Environment)
```bash
# 1. Create and activate venv
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r backend/requirements-dev.txt

# 3. Initialize database tables and seed data
python -m backend.app.db.init_db

# 4. Start API server
uvicorn backend.app.main:app --reload --port 8000
```
Interactive Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Local Setup (Docker Compose)
```bash
docker compose up --build
```
Runs PostgreSQL 16 with `pgvector` alongside the FastAPI backend with database migrations and seeds pre-applied.

### Running Tests and Linting
```bash
pytest -v backend/tests
ruff check backend
```

---

## Deployment
Refer to [`docs/DEPLOY.md`](docs/DEPLOY.md) for step-by-step instructions on deploying the backend to **Render** and the database to **Supabase** with `pgvector`.
