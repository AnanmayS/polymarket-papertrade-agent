# Deployment

## Recommended shape

- Frontend: deploy to Vercel as a static React app.
- Backend API: deploy to an always-on Python host such as Render web service, Railway service, or Fly.io machine.
- Database: use managed Postgres.
- Scheduling: use an external scheduler or cron job that triggers one cycle at a time.

This repo should not rely on an in-process scheduler in production. The backend now rejects `SCHEDULER_ENABLED=true` and `AUTO_RUN_ON_STARTUP=true` when `APP_ENV=production`.

## What goes where

### Vercel

Good fit:

- `frontend/`

Not a good fit:

- long-lived FastAPI scheduler loop
- autonomous trading worker owned by a web process

Vercel cron jobs can call a URL, so they can trigger the backend if you deploy the backend somewhere else.

### Render / Railway / Fly.io

Good fit:

- FastAPI backend
- managed Postgres
- scheduled one-shot jobs

Recommended production model:

1. Run the backend API as a normal web service.
2. Keep the scheduler disabled in the app process.
3. Trigger `POST /engine/run-cycle` with a bearer token, or run `python scripts/run_cycle_once.py` on a cron schedule.

## Required production environment variables

Set these on the backend service:

```bash
APP_ENV=production
DATABASE_URL=postgresql+psycopg://...
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
ENGINE_CONTROL_TOKEN=replace-with-a-long-random-secret
USE_LIVE_POLYMARKET_DATA=true
SEED_DEMO_DATA=false
SCHEDULER_ENABLED=false
AUTO_RUN_ON_STARTUP=false
```

Set this on the frontend:

```bash
VITE_API_BASE_URL=https://your-backend.example.com
```

## Triggering a cycle

### Option 1: HTTP trigger

Use an external cron job to call:

```bash
curl -X POST https://your-backend.example.com/engine/run-cycle \
  -H "Authorization: Bearer $ENGINE_CONTROL_TOKEN"
```

### Option 2: One-shot job

Run the backend task directly:

```bash
cd backend
python scripts/run_cycle_once.py
```

This is the cleanest option for Railway cron jobs or any platform that starts a task, waits for it to finish, and then exits.

## Notes

- `/health` no longer exposes the full database URL.
- Engine control routes require a token in production.
- Public read routes remain open for the dashboard.
- This project is still paper-trading only. Deploying it will not place live Polymarket orders.
