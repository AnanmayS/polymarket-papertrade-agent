# Deployment

## Recommended shape

- **Frontend:** deploy to Vercel as a static React app (already done).
- **Backend API:** deploy to Render as a Docker web service.
- **Database:** use Render's free managed PostgreSQL (included in the blueprint).
- **Scheduling:** use a Render cron job that triggers one cycle per day.
- **Keep-awake:** use cron-job.org to ping `/health` every 10 minutes so the free web service stays warm.

This repo should not rely on an in-process scheduler in production. The backend now rejects `SCHEDULER_ENABLED=true` and `AUTO_RUN_ON_STARTUP=true` when `APP_ENV=production`.

## What goes where

| Component    | Platform  | Free tier limits                     |
|-------------|-----------|--------------------------------------|
| Frontend    | Vercel    | Unlimited static sites               |
| Backend API | Render    | 1 web service (sleeps after 15 min)  |
| PostgreSQL  | Render    | 1 GB persistent storage              |
| Cron cycle  | Render    | 1 cron job (free, doesn't sleep)     |
| Keep-awake  | cron-job.org | 1,000 pings/month, free            |

## Render Blueprint

A `render.yaml` is checked in at the project root. It defines:

1. **`polymarket-backend`** — FastAPI web service via Docker
2. **`polymarket-daily-cycle`** — cron job running `python scripts/run_cycle_once.py` daily at 14:00 UTC
3. **`polymarket-pg`** — managed PostgreSQL database

## Setup (first time)

Follow the step-by-step guide in [docs/render-setup.md](render-setup.md).

## Environment variables

### Backend web service (automated via blueprnit)

| Variable | Value | Notes |
|---|---|---|
| `APP_ENV` | `production` | Locks scheduler off, requires control token |
| `USE_LIVE_POLYMARKET_DATA` | `true` | Fetches live Polymarket sports data |
| `SEED_DEMO_DATA` | `false` | No demo data needed in production |
| `SENTIMENT_ENABLED` | `true` | |
| `SCHEDULER_ENABLED` | `false` | Cron job handles scheduling |
| `AUTO_RUN_ON_STARTUP` | `false` | |
| `CORS_ALLOWED_ORIGINS` | `https://frontend-ananmays-projects-52b5594c.vercel.app` | Your frontend URL |
| `DATABASE_URL` | _(from Render PG)_ | Auto-injected by the blueprint |
| `ENGINE_CONTROL_TOKEN` | _(you set this)_ | Required for production. Generate one with `openssl rand -hex 32` |

### Frontend (Vercel)

| Variable | Value | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | `https://polymarket-backend.onrender.com` | Your Render backend URL |
| `VITE_ENABLE_ENGINE_CONTROLS` | `false` | Keep dashboard read-only |
| `ENABLE_PUBLIC_ENGINE_CONTROLS` | `false` | |

## Triggering a cycle

The Render cron job runs daily at 14:00 UTC. To trigger manually:

```bash
# Via Render dashboard — click "Run Now" on the cron job
# Or locally:
cd backend
python scripts/run_cycle_once.py
```

## Keep-awake (cron-job.org)

Render's free web service goes to sleep after 15 minutes of inactivity.
Set up a free cron-job.org job that pings `https://polymarket-backend.onrender.com/health`
every **10 minutes** to keep it warm.

This prevents the 5–30 second cold start on the next frontend request
or the daily cron cycle.

## Notes

- `/health` runs a `SELECT 1` against the database — it's a true readiness check.
- Engine control routes require a token in production.
- The frontend run-cycle proxy is disabled by default, so public visitors cannot trigger agent cycles from the dashboard.
- Public read routes remain open for the dashboard.
- Managed PostgreSQL URLs are normalized to `postgresql+psycopg://` by the backend config automatically.
- This project is still paper-trading only. Deploying it will not place live Polymarket orders.
