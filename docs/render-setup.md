# Render Setup Guide

> Move from Railway to Render in ~15 minutes. Free tier — PostgreSQL included.

## Prerequisites

- A GitHub account with push access to this repo
- A Render account (sign up at https://render.com — no credit card needed for free tier)

---

## Step 1 — Deploy via Blueprint (fastest path)

Render Blueprint reads `render.yaml` from the repo and provisions everything in one shot.

1. Go to https://dashboard.render.com/blueprints
2. Click **"New Blueprint Instance"**
3. Connect your GitHub account and select `AnanmayS/polymarket-papertrade-agent`
4. Render reads `render.yaml` and shows three resources:
   - `polymarket-backend` (web service)
   - `polymarket-daily-cycle` (cron job)
   - `polymarket-pg` (PostgreSQL)
5. Click **"Apply"**

Render will spin up the database first, then build and deploy both services.
Wait 2–3 minutes for the first build.

## Step 2 — Set ENGINE_CONTROL_TOKEN

The `render.yaml` creates the env var but doesn't set its value (it's `sync: false`).

1. Go to https://dashboard.render.com
2. Click **"polymarket-backend"** web service
3. Go to **Environment** tab
4. Find `ENGINE_CONTROL_TOKEN` — click **"Override"**
5. Generate a secret:
   ```bash
   openssl rand -hex 32
   ```
   or use a password manager to generate a 64-character hex string
6. Paste it, click **Save**
7. Click **"Manual Deploy" → "Clear build cache & deploy"** (or just redeploy)

## Step 3 — Verify it works

```bash
# Health check (use your actual backend URL)
curl https://polymarket-backend.onrender.com/health

# Expected:
# {"status":"ok","app":"Polymarket Paper Trading Agent","environment":"production",...}
```

## Step 4 — Set up keep-awake (cron-job.org)

Render's free web service sleeps after 15 minutes of inactivity.  
A free cron-job.org ping every 10 minutes keeps it warm.

1. Go to https://cron-job.org
2. Sign up (free, no credit card)
3. Click **"Create Cronjob"**
4. Fill in:

| Field | Value |
|---|---|
| **Title** | `polymarket-backend-keepalive` |
| **URL** | `https://polymarket-backend.onrender.com/health` |
| **Schedule** | `Every 10 Minutes` |
| **Request Method** | `GET` |

5. Click **"Create Cronjob"**

That's it. The pings start immediately.

---

## Step 5 — Verify the daily cron cycle is running

Render's cron job `polymarket-daily-cycle` runs at **14:00 UTC** daily.

To test it manually now:
1. Go to https://dashboard.render.com
2. Click **"polymarket-daily-cycle"**
3. Click **"Run Now"** (top right)
4. Check the logs — you should see:
   ```
   Starting job...
   {'scan': ..., 'signals': ..., 'risk': ..., 'trades': ..., 'settled': ...}
   Job completed
   ```

---

## Files changed from the Railway setup

| What changed | Notes |
|---|---|
| `render.yaml` (new) | Blueprint — replaces Railway manual config |
| `docs/deployment.md` (rewritten) | Render instructions instead of Railway |
| `docs/render-setup.md` (this file) | Step-by-step guide |

No code changes required — the existing Dockerfile, health endpoint, and config all work with Render as-is.

---

## Troubleshooting

### Build fails
- Check build logs on the Render dashboard
- Common issue: `psycopg` binary compilation fails on ARM. The `psycopg[binary]` in requirements.txt should handle this. If it still fails, add `postgresql-client` to the Dockerfile.

### Health check failing
- First deploy takes 2–3 minutes
- Check that the `DATABASE_URL` is injected (it comes from the blueprint's `fromDatabase` reference)
- The `/health` endpoint runs `SELECT 1` — if the DB connection string is wrong, it won't respond

### Cron job runs but no trades
- If `USE_LIVE_POLYMARKET_DATA=true` but Polymarket has no active sports markets matching your filters, no trades are placed
- Check the cron job logs on the Render dashboard
- Try lowering `MIN_LIQUIDITY` and `MIN_VOLUME` temporarily via the Render env vars

### Service won't wake up
- cron-job.org pings every 10 min. The service wakes in ~5–30s on the first ping after sleep
- If you just deployed, the first ping might time out waiting for the build to finish. This is normal — the second ping will work
