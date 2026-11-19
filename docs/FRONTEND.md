# Frontend Guide

The P4 frontend is a Next.js App Router application in `frontend/`. It uses TypeScript, Tailwind, shadcn-style UI primitives, Leaflet, and Recharts. The API client and types in `frontend/src/lib/api/` follow the shared [CONTRACT.md](CONTRACT.md); do not change the contract in this folder.

## Run with no backend

```sh
cd frontend
npm install
printf 'NEXT_PUBLIC_USE_MOCKS=true\nNEXT_PUBLIC_API_URL=http://localhost:8000\n' > .env.local
npm run dev
```

Fixtures and the in-memory `mockStore` provide cases, events, notifications, approvals, and demo actions. Mock stream subscriptions emit new events in-process. No service worker is required. Mock data is reset when the frontend process restarts; metric values are intentionally empty unless returned by an API.

## Run against the API

Set `NEXT_PUBLIC_USE_MOCKS=false` and `NEXT_PUBLIC_API_URL` before starting/building the frontend. Officer endpoints use the saved officer Bearer token. Citizen case reads, events, messages, and confirmation use the per-case access token. The live event hook sends the bearer token in an authenticated fetch stream, parses SSE frames, and falls back to polling if the stream fails.

## Main modules

- `src/lib/api/types.ts` — TypeScript data models aligned with the shared contract and backend response variants.
- `src/lib/api/endpoints.ts` — typed REST calls and mock-mode routing.
- `src/lib/api/client.ts` — API origin, officer JWT, and normalized unauthorized handling.
- `src/lib/hooks/useSSE.ts` — event stream and polling fallback.
- `src/lib/mocks/` — in-memory fixture store, realistic case/event/approval fixtures.
- `src/app/` — citizen, officer, landing, and metrics routes.
- `src/components/` — reusable citizen and case views.

## Validation

```sh
npm run lint
npm run build
```

Browser tests and Vercel deployment instructions are in [README.md](README.md) and [DEPLOY.md](DEPLOY.md).
