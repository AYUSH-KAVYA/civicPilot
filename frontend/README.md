# CivicPilot Frontend

Citizen and officer interfaces for CivicPilot. See the project [README](../docs/README.md) for architecture, full setup, environment variables, and deployment. The API contract is [CONTRACT.md](../docs/CONTRACT.md).

## Run with mock data

```sh
npm install
printf 'NEXT_PUBLIC_USE_MOCKS=true\nNEXT_PUBLIC_API_URL=http://localhost:8000\n' > .env.local
npm run dev
```

The in-memory fixture store runs without a backend. Mock cases and events reset when the frontend process restarts. Metrics show empty states unless the API returns measured values.

## Run with the API

Set `NEXT_PUBLIC_USE_MOCKS=false` and `NEXT_PUBLIC_API_URL` before starting or building. The API must allow the frontend origin through its CORS configuration. Officer routes require a JWT; citizen tracking actions require the case access token.

## Commands

- `npm run dev` — local development server
- `npm run lint` — ESLint
- `npm run build` — production build
- `npm run start` — serve the production build
