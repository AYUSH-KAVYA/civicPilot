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
