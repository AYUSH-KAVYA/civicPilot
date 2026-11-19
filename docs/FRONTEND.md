# CivicPilot — Frontend Developer Guide

> **Stack**: Next.js 14 (App Router) · TypeScript · Tailwind CSS · shadcn/ui · Zustand · MSW · Recharts · React-Leaflet

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Page Map](#2-page-map)
3. [Running Locally](#3-running-locally)
4. [Environment Variables](#4-environment-variables)
5. [Mock Mode](#5-mock-mode)
6. [Adding New Mock Fixtures](#6-adding-new-mock-fixtures)
7. [Component Library](#7-component-library)
8. [State Management](#8-state-management)
9. [SSE / Real-Time Updates](#9-sse--real-time-updates)
10. [Type System](#10-type-system)
11. [Testing](#11-testing)
12. [Contributing](#12-contributing)

---

## 1. Architecture Overview

```
frontend/
├── src/
│   ├── app/                   # Next.js 14 App Router pages
│   │   ├── page.tsx           # Landing page
│   │   ├── report/            # Citizen report flow
│   │   ├── track/[id]/        # Citizen case tracking
│   │   └── officer/           # Officer dashboard (auth-gated)
│   │       ├── login/
│   │       ├── cases/
│   │       │   └── [id]/
│   │       ├── approvals/
│   │       ├── demo/
│   │       └── metrics/
│   ├── components/            # Reusable UI components
│   │   ├── ui/                # shadcn/ui primitives (auto-generated)
│   │   ├── case/              # Case-specific components
│   │   ├── timeline/          # Event timeline + phase cards
│   │   ├── map/               # Leaflet map wrapper
│   │   └── layout/            # Nav, sidebar, shell
│   ├── lib/
│   │   ├── api/
│   │   │   ├── types.ts       # All contract types (from CONTRACT §3–§5)
│   │   │   ├── client.ts      # Axios instance with auth interceptor
│   │   │   └── endpoints.ts   # Typed API call functions
│   │   ├── hooks/
│   │   │   ├── useSSE.ts      # SSE hook with polling fallback
│   │   │   ├── useCases.ts    # Case list with live updates
│   │   │   └── useApprovals.ts
│   │   ├── mocks/
│   │   │   ├── browser.ts     # MSW browser setup
│   │   │   ├── handlers.ts    # MSW request handlers
│   │   │   └── fixtures/      # Static fixture data
│   │   │       ├── cases.ts
│   │   │       ├── events.ts
│   │   │       └── case1042.ts
│   │   └── stores/
│   │       └── authStore.ts   # Zustand auth store
│   └── styles/
│       └── globals.css        # Tailwind base + custom CSS vars
├── public/
│   └── mockServiceWorker.js   # MSW service worker (auto-generated)
├── .env.local                 # Local environment (not committed)
├── .env.local.example         # Template to copy
├── next.config.ts
├── tailwind.config.ts
└── tsconfig.json
```

### Data Flow

```
API (real or MSW mock)
        │
   Axios client  ──────────────────► REST responses
   useSSE hook   ──────────────────► SSE / EventSource
        │
   Zustand stores  (auth, cases cache)
        │
   React components  (server components for static, client components for live)
```

---

## 2. Page Map

| Route | File | Auth | Description |
|---|---|---|---|
| `/` | `app/page.tsx` | Public | Landing page — 6-step loop overview, CTA buttons |
| `/report` | `app/report/page.tsx` | Public | Citizen report form (text, photo upload, location picker, language selector) |
| `/track/[id]` | `app/track/[id]/page.tsx` | Case token | Citizen tracking — live status, confirm closure or reopen |
| `/officer/login` | `app/officer/login/page.tsx` | Public | Officer login form → JWT stored in localStorage |
| `/officer/cases` | `app/officer/cases/page.tsx` | Officer JWT | Case list with filters (status, dept, urgency), live badge counts |
| `/officer/cases/[id]` | `app/officer/cases/[id]/page.tsx` | Officer JWT | Case detail — Timeline, Plan, Map, Intake/Triage panels |
| `/officer/approvals` | `app/officer/approvals/page.tsx` | Officer JWT | Pending approvals + NEEDS_HUMAN queue with reasoning packets |
| `/officer/demo` | `app/officer/demo/page.tsx` | Officer JWT | Demo control panel — scenario buttons, sandbox signals, sim clock |
| `/officer/metrics` | `app/officer/metrics/page.tsx` | Officer JWT | Eval metrics — accuracy, resolution time, escalation rate vs baseline |

---

## 3. Running Locally

### With a real backend

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.local.example .env.local
# Edit .env.local:
#   NEXT_PUBLIC_API_URL=http://localhost:8000
#   NEXT_PUBLIC_USE_MOCKS=false

# 3. Start dev server
npm run dev
# → http://localhost:3000
```

The backend must be running at the URL specified in `NEXT_PUBLIC_API_URL`.

### Mock mode (no backend)

```bash
cd frontend

echo "NEXT_PUBLIC_USE_MOCKS=true" > .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" >> .env.local

npm run dev
```

### Build for production

```bash
npm run build
npm start
```

### Lint and type-check

```bash
npm run lint       # ESLint
npm run type-check # tsc --noEmit
```

---

## 4. Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000` | Backend API base URL |
| `NEXT_PUBLIC_USE_MOCKS` | No | `false` | `true` → enables MSW mock service worker |

> All `NEXT_PUBLIC_` variables are baked into the browser bundle at build time. Never put secrets here.

The officer auth token is stored in `localStorage` under the key `officer_token` and attached to every officer-route request by the Axios interceptor in `src/lib/api/client.ts`.

---

## 5. Mock Mode

### How it works

When `NEXT_PUBLIC_USE_MOCKS=true`, the app registers a [MSW (Mock Service Worker)](https://mswjs.io/) browser-side service worker at startup. The worker intercepts all fetch and XHR requests matching the API URL patterns and returns fixture data — no network traffic leaves the browser.

The MSW setup is in `src/lib/mocks/browser.ts` and activated in `src/app/layout.tsx`:

```ts
// src/app/layout.tsx (simplified)
if (process.env.NEXT_PUBLIC_USE_MOCKS === 'true') {
  const { worker } = await import('@/lib/mocks/browser')
  await worker.start({ onUnhandledRequest: 'bypass' })
}
```

### Pre-seeded fixture cases

| Case ID | Status | Scenario |
|---|---|---|
| `CP-1001` | `IN_PROGRESS` | Water leak — Elm Street |
| `CP-1002` | `AT_RISK` | Road pothole — South Bridge (disruption) |
| `CP-1003` | `NEEDS_HUMAN` | Ambiguous noise/smell complaint |
| `CP-1004` | `AWAITING_CONFIRMATION` | Sanitation — blocked drain |
| `CP-1005` | `CLOSED` | Electricity fault — resolved |
| `CP-1042` | `PLANNED` | High-voltage wire near school (critical) |

Each case has 20+ events covering the full `perceive → reason → plan → act → evaluate → adapt` loop, including tool_call cards with expandable JSON args/results and adaptation events with before/after plan diffs.

---

## 6. Adding New Mock Fixtures

### Step 1 — Add a case fixture

Edit `src/lib/mocks/fixtures/cases.ts` and add a new entry to the `mockCases` array:

```ts
// src/lib/mocks/fixtures/cases.ts
export const mockCases: CaseState[] = [
  // ... existing cases ...
  {
    id: 'CP-2001',
    created_at: '2026-11-19T10:00:00Z',
    updated_at: '2026-11-19T10:30:00Z',
    status: 'TRIAGED',
    deadline_at: '2026-11-19T14:00:00Z',
    citizen: { contact_masked: '+91 98***4567', language: 'en' },
    raw: {
      text: 'Broken park bench near the playground.',
      image_urls: [],
      lat: 12.9716,
      lng: 77.5946,
      address_text: 'Cubbon Park, Bengaluru',
      channel: 'web',
    },
    intake: {
      category: 'Parks',
      summary: 'Broken bench near playground, minor injury risk.',
      location: { address: 'Cubbon Park', lat: 12.9716, lng: 77.5946 },
      visible_damage: ['broken_furniture'],
      nearby_sensitive_sites: [],
      language_detected: 'en',
      missing_info: [],
      confidence: 0.82,
    },
    triage: {
      urgency: 'low',
      department_id: 'parks',
      ward_id: 'ward-05',
      office_id: 'office-parks-central',
      deadline_hours: 72,
      policy_refs: ['parks-sop.md#section-3'],
      rationale: 'Non-urgent parks maintenance. 72-hour SLA.',
      confidence: 0.82,
    },
    plan: { version: 1, steps: [] },
    tickets: [],
    flags: { needs_human: false, human_reason: null, reopen_count: 0, merged_into: null, duplicate_of: [] },
  },
]
```

### Step 2 — Add events for the case

Edit `src/lib/mocks/fixtures/events.ts` and add entries to `mockEventsByCase`:

```ts
export const mockEventsByCase: Record<string, CaseEvent[]> = {
  // ... existing entries ...
  'CP-2001': [
    {
      id: 'evt-2001-1',
      case_id: 'CP-2001',
      ts: '2026-11-19T10:00:05Z',
      agent: 'intake',
      phase: 'perceive',
      summary: 'Intake agent parsing report text.',
      detail: { text_length: 42 },
    },
    // Add more events...
  ],
}
```

### Step 3 — Add an MSW handler (if needed)

If the new case needs special endpoint behaviour, add a handler in `src/lib/mocks/handlers.ts`:

```ts
// src/lib/mocks/handlers.ts
http.get('/api/cases/CP-2001', () => {
  return HttpResponse.json(mockCases.find(c => c.id === 'CP-2001'))
})
```

The default catch-all handlers already handle `GET /api/cases/{id}` by looking up the fixture by ID, so this step is only needed for custom responses.

### Step 4 — Verify

Restart the dev server (`npm run dev`) and navigate to `/officer/cases`. Your new case should appear in the list. Click it to verify the timeline renders correctly.

---

## 7. Component Library

CivicPilot uses [shadcn/ui](https://ui.shadcn.com/) components (Radix UI primitives + Tailwind styling). These live in `src/components/ui/` and are **not modified directly** — extend them in domain-specific wrapper components.

### Key Custom Components

| Component | Path | Description |
|---|---|---|
| `PhaseEvent` | `components/timeline/PhaseEvent.tsx` | Single timeline event card with phase colour and expand/collapse |
| `ToolCallCard` | `components/timeline/ToolCallCard.tsx` | Expandable JSON args + results for tool_call events |
| `AdaptationCard` | `components/timeline/AdaptationCard.tsx` | Before/after plan diff for adapt events |
| `GuardrailBanner` | `components/timeline/GuardrailBanner.tsx` | Red banner with reason for guardrail events |
| `PlanPanel` | `components/case/PlanPanel.tsx` | Step cards with status badges, risk tier colours, dependency lines |
| `ConfidenceMeter` | `components/case/ConfidenceMeter.tsx` | Animated 0–1 progress bar with threshold marker |
| `CaseMap` | `components/map/CaseMap.tsx` | Leaflet map with incident pin and crew marker |
| `CaseCard` | `components/case/CaseCard.tsx` | Case list card with status badge and live event feed |
| `ApprovalCard` | `components/case/ApprovalCard.tsx` | Reasoning packet with approve/reject buttons |
| `ScenarioButton` | `components/demo/ScenarioButton.tsx` | Demo control panel trigger |

### Phase Colour Tokens (Tailwind)

| Phase | Tailwind class prefix | Hex |
|---|---|---|
| `perceive` | `phase-perceive` / purple-600 | `#9333EA` |
| `reason` | `phase-reason` / blue-600 | `#2563EB` |
| `plan` | `phase-plan` / indigo-600 | `#4F46E5` |
| `act` | `phase-act` / green-600 | `#16A34A` |
| `evaluate` | `phase-evaluate` / amber-600 | `#D97706` |
| `adapt` | `phase-adapt` / orange-600 | `#EA580C` |
| `guardrail` | `phase-guardrail` / red-600 | `#DC2626` |
| `tool_call` | `phase-tool` / cyan-600 | `#0891B2` |
| `message` | `phase-message` / gray-500 | `#6B7280` |

---

## 8. State Management

CivicPilot uses [Zustand](https://zustand-demo.pmnd.rs/) for global client state.

### Auth Store (`src/lib/stores/authStore.ts`)

```ts
interface AuthStore {
  token: string | null
  login: (password: string) => Promise<void>  // POST /api/auth/login
  logout: () => void
  isAuthenticated: boolean
}
```

The token is persisted to `localStorage` (key: `officer_token`) via the Zustand `persist` middleware.

### Local state

Component-level state uses standard `useState` / `useReducer`. Case data is fetched with `useSWR` or inline `useEffect` + Axios and not stored globally (the SSE hook keeps it fresh).

---

## 9. SSE / Real-Time Updates

The `useSSE` hook (`src/lib/hooks/useSSE.ts`) handles live event streaming:

```ts
const { events, status } = useSSE(caseId)
// status: 'connecting' | 'connected' | 'polling' | 'error'
```

Behaviour:
- Connects to `GET /api/cases/{id}/stream` as an `EventSource`.
- Falls back to polling `GET /api/cases/{id}/events` every 3 seconds if `EventSource` is not supported or the SSE connection fails.
- Automatically reconnects with exponential backoff (up to 30 s) on disconnect.
- In mock mode, MSW simulates streaming by returning new events progressively.

The case detail page (`/officer/cases/[id]`) uses `useSSE` to append new `PhaseEvent` cards to the timeline in real time without a page refresh.

---

## 10. Type System

All contract types live in `src/lib/api/types.ts`, generated from `docs/CONTRACT.md` §3–§5.

```ts
// Key enums
type CaseStatus = 'NEW' | 'INTAKE' | 'TRIAGED' | 'PLANNED' | 'IN_PROGRESS'
                | 'AT_RISK' | 'NEEDS_HUMAN' | 'AWAITING_CONFIRMATION'
                | 'CLOSED' | 'REOPENED'

type Urgency = 'critical' | 'high' | 'medium' | 'low'

type Phase = 'perceive' | 'reason' | 'plan' | 'act' | 'evaluate'
           | 'adapt' | 'guardrail' | 'tool_call' | 'tool_result' | 'message'

type StepStatus = 'pending' | 'running' | 'done' | 'failed' | 'skipped' | 'awaiting_approval'

type RiskTier = 'routine' | 'sensitive' | 'critical'

// Key interfaces — see types.ts for full field lists
interface CaseState { ... }   // CONTRACT §4
interface CaseEvent { ... }   // CONTRACT §5
interface PlanStep { ... }
interface Ticket { ... }
interface Approval { ... }
```

If the backend contract changes, update `src/lib/api/types.ts` first, then fix any TypeScript errors that surface — the type system is your single source of truth.

---

## 11. Testing

### Unit tests (Vitest)

```bash
npm run test          # run all unit tests
npm run test:watch    # watch mode
```

Unit tests live alongside their source files as `*.test.ts` / `*.test.tsx`.

### E2E tests (Playwright)

```bash
# From the repo root
npx playwright test --config=e2e/playwright.config.ts
```

E2E tests are in `e2e/` (P4 scope). They run against either the live backend or mock mode (`NEXT_PUBLIC_USE_MOCKS=true`). See `e2e/README.md` for details.

---

## 12. Contributing

1. Branch from `feat/p4-frontend`: `git checkout -b feat/p4-<topic>`
2. Respect CODEOWNERS — only touch `frontend/`, `docs/`, `e2e/`.
3. Run `npm run lint && npm run type-check` before committing.
4. Keep mock fixtures in sync when adding new API endpoints.
5. Write a `*.test.tsx` for every new component or hook.
6. Open a PR with at least 1 reviewer (required by `CODEOWNERS`).
7. Rebase on `feat/p4-frontend` before merging.
