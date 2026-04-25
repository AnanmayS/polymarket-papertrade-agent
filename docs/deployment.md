# Deployment

## Recommended shape

- Frontend: deploy to Vercel as a static React app.
- Backend API: deploy to an always-on Railway service.
- Database: use managed Postgres.
- Scheduling: use a Railway cron service that triggers one cycle at a time.

This repo should not rely on an in-process scheduler in production. The backend now rejects `SCHEDULER_ENABLED=true` and `AUTO_RUN_ON_STARTUP=true` when `APP_ENV=production`.

## What goes where

### Vercel

Good fit:

- `frontend/`

Not a good fit:

- long-lived FastAPI scheduler loop
- autonomous trading worker owned by a web process

Vercel cron jobs can call a URL, so they can trigger the backend if you deploy the backend somewhere else.

### Railway

Good fit:

- FastAPI backend
- managed Postgres
- scheduled one-shot jobs

Recommended production model:

1. Run the backend API as a normal web service.
2. Keep the scheduler disabled in the app process.
3. Run `python scripts/run_cycle_once.py` in a separate Railway cron service.

### Railway service layout

Use one Railway project with these backend resources:

- `backend` web service
- `backend-cycle` cron service
- `Postgres` database service

Recommended service settings:

- Root directory: `/backend`
- Service source: this repo
- Healthcheck path for the web service: `/health`
- Cron schedule for the cycle service: `*/10 * * * *`
- Start command override for the cycle service: `python scripts/run_cycle_once.py`

Both application services should share the same environment variables and attached Postgres service.

## Required production environment variables

Set these on the backend service:

```bash
APP_ENV=production
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
ENGINE_CONTROL_TOKEN=replace-with-a-long-random-secret
USE_LIVE_POLYMARKET_DATA=true
SEED_DEMO_DATA=false
SCHEDULER_ENABLED=false
AUTO_RUN_ON_STARTUP=false
```

`DATABASE_URL` should come from Railway's Postgres service. Railway may expose it as `postgresql://...` or `postgres://...`; the backend normalizes both to `postgresql+psycopg://...`.

Set this on the frontend:

```bash
VITE_API_BASE_URL=https://your-backend.example.com
```

## Triggering a cycle

Run the backend task directly:

```bash
cd backend
python scripts/run_cycle_once.py
```

This is the recommended Railway cron path because the task starts, completes one cycle, and exits cleanly.

## Notes

- `/health` no longer exposes the full database URL.
- Engine control routes require a token in production.
- Public read routes remain open for the dashboard.
- Managed Postgres URLs like `postgresql://...` and `postgres://...` are normalized to `postgresql+psycopg://...` by the backend config for SQLAlchemy compatibility.
- This project is still paper-trading only. Deploying it will not place live Polymarket orders.
