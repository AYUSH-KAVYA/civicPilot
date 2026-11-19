# CivicPilot Deployment & Setup Guide

This document describes how to deploy the CivicPilot backend on **Render** using a hosted **Supabase** PostgreSQL database with `pgvector`, and configure scheduled timer evaluation via external cron.

---

## 1. Supabase Database Setup

1. **Create Project**:
   - Go to [Supabase](https://supabase.com) and create a new project (e.g. `civicpilot-db`).
   - Securely save your database password.

2. **Enable pgvector**:
   - In your Supabase dashboard, navigate to **Database** -> **Extensions**.
   - Search for `vector` and toggle it **ON**, or open the **SQL Editor** and run:
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector;
     ```

3. **Get Connection String**:
   - Navigate to **Project Settings** -> **Database** -> **Connection string** -> **URI**.
   - Use the **Transaction Pooler** (port 6543) or **Session Pooler** (port 5432).
   - Format for CivicPilot:
     ```
     postgresql+asyncpg://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
     ```
   *(CivicPilot automatically translates `postgres://` or `postgresql://` to `postgresql+asyncpg://` if needed)*.

4. **Storage Bucket (Optional for Image Uploads)**:
   - Navigate to **Storage** -> **New Bucket**.
   - Name the bucket `civicpilot-uploads`.
   - Toggle **Public bucket** ON.
   - Under **Project Settings** -> **API**, copy your `Project URL` and `service_role secret` for `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`.

5. **Run Migrations & Seed**:
   From your local environment with `DATABASE_URL` set to the Supabase connection string:
   ```bash
   export DATABASE_URL="postgresql+asyncpg://..."
   python -m backend.app.db.init_db
   ```
   This creates all 15 tables and seeds the 6 departments, 10 wards, 10 offices, 15 response crews, and SLA policies.

---

## 2. Render Web Service Deployment

1. **Connect GitHub Repo**:
   - Log into [Render](https://render.com).
   - Click **New** -> **Web Service** (or use the Blueprint from `render.yaml`).
   - Connect the `civicPilot` repository.

2. **Configuration**:
   - **Environment**: `Docker`
   - **Dockerfile Path**: `./Dockerfile`
   - **Health Check Path**: `/api/health`

3. **Environment Variables**:
   Add the following in Render's **Environment** tab:

   | Variable | Value / Description |
   |---|---|
   | `DATABASE_URL` | Your Supabase connection string |
   | `JWT_SECRET` | Strong random 32+ character secret string |
   | `OFFICER_PASSWORD` | Password for city officer dashboard login |
   | `GEMINI_API_KEY` | Google Gemini API key (or leave empty if `MOCK_LLM=true`) |
   | `MOCK_LLM` | `false` (or `true` if running without Gemini key) |
   | `CONFIDENCE_THRESHOLD` | `0.65` |
   | `SIM_TIME_SCALE` | `1` (or `60` to accelerate SLAs for live demos) |
   | `FRONTEND_ORIGIN` | Your frontend URL (e.g. `https://your-frontend.vercel.app` or `*`) |
   | `NOMINATIM_USER_AGENT` | `CivicPilot-Prod/1.0 (contact: dispatch@metroville.gov)` |
   | `SUPABASE_URL` | *(Optional)* Supabase Project URL |
   | `SUPABASE_SERVICE_KEY` | *(Optional)* Supabase service_role key |
   | `RESEND_API_KEY` | *(Optional)* Resend API key for citizen email notifications |

4. **Deploy**:
   - Click **Create Web Service**.
   - Once deployed, test the health check:
     ```bash
     curl https://your-civicpilot-service.onrender.com/api/health
     ```
   - Access the interactive OpenAPI docs at:
     ```
     https://your-civicpilot-service.onrender.com/docs
     ```

---

## 3. Keep-Alive & Timer Ticking (UptimeRobot / cron-job.org)

Render free instances spin down after 15 minutes of inactivity. Additionally, scheduled SLA timers need periodic evaluation. Setting up an external ping solves both issues:

### Option A: Using cron-job.org (Recommended - Supports POST)
1. Register a free account at [cron-job.org](https://cron-job.org).
2. Create **Job 1 (SLA Timers & Deadlines)**:
   - **Title**: `CivicPilot Timer Tick`
   - **URL**: `https://your-civicpilot-service.onrender.com/api/tick`
   - **Method**: `POST`
   - **Schedule**: Every 5 minutes (`*/5 * * * *`)
3. Create **Job 2 (Keep-Alive Health Check)**:
   - **Title**: `CivicPilot Keep Alive`
   - **URL**: `https://your-civicpilot-service.onrender.com/api/health`
   - **Method**: `GET`
   - **Schedule**: Every 5 minutes

### Option B: Using UptimeRobot
1. Register at [UptimeRobot](https://uptimerobot.com).
2. Click **Add New Monitor**:
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `CivicPilot Health Ping`
   - **URL**: `https://your-civicpilot-service.onrender.com/api/health`
   - **Monitoring Interval**: `5 minutes`

---

## 4. Local Development with Docker Compose

To run the complete stack locally (API + PostgreSQL with pgvector):
```bash
docker compose up --build
```
This automatically boots PostgreSQL with `pgvector`, applies table schemas, seeds initial master data, and starts the API at `http://localhost:8000`.

---

## 5. Frontend Deployment (Vercel)

The CivicPilot frontend is a Next.js 14 App Router application. The recommended host is [Vercel](https://vercel.com) — zero-config for Next.js.

### 5.1 Connect the GitHub Repository

1. Log into [Vercel](https://vercel.com) and click **Add New → Project**.
2. Select your GitHub organisation/account and import the `civicPilot` repository.
3. Vercel auto-detects Next.js. Set the **Root Directory** to `frontend`.
4. Click **Deploy**.

### 5.2 Environment Variables

In your Vercel project, go to **Settings → Environment Variables** and add:

| Variable | Value | Environment |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://your-civicpilot-service.onrender.com` | Production, Preview |
| `NEXT_PUBLIC_USE_MOCKS` | `false` | Production |
| `NEXT_PUBLIC_USE_MOCKS` | `true` | Preview *(optional — lets PR previews work without a backend)* |

> **Important**: `NEXT_PUBLIC_API_URL` must point to the deployed backend URL (from Section 2 above), not `localhost`.

### 5.3 Custom Domain

1. In your Vercel project, go to **Settings → Domains**.
2. Click **Add Domain** and enter your domain (e.g. `civicpilot.metroville.gov`).
3. Follow the DNS instructions (add a CNAME pointing to `cname.vercel-dns.com`).
4. Vercel provisions TLS automatically.
5. Update the backend's `FRONTEND_ORIGIN` env var on Render to match your custom domain so CORS allows requests.

### 5.4 Preview Deployments for Pull Requests

Vercel automatically creates a unique preview URL for every PR opened against the `main` branch (or `feat/p4-frontend`). To make previews useful without requiring a live backend:

1. In Vercel **Settings → Environment Variables**, set `NEXT_PUBLIC_USE_MOCKS=true` for the **Preview** environment.
2. Each PR gets a URL like `https://civicpilot-git-feat-p4-frontend-yourteam.vercel.app`.
3. Reviewers can open the preview URL and exercise all UI flows using mock data — no backend required.
4. For PRs that need real backend integration, override `NEXT_PUBLIC_USE_MOCKS` to `false` on the specific deployment via Vercel's deployment-level env override.

### 5.5 Deployment Checklist

- [ ] `NEXT_PUBLIC_API_URL` set to production backend URL
- [ ] `NEXT_PUBLIC_USE_MOCKS=false` in Production environment
- [ ] `FRONTEND_ORIGIN` on Render updated to match Vercel domain
- [ ] Custom domain DNS propagated (allow up to 48 h)
- [ ] Health check: open the Vercel URL and log in as officer — the cases list should load live data
