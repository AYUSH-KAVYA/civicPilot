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
