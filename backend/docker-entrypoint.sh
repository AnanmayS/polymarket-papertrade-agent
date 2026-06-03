#!/bin/bash
# Entrypoint — runs the web server by default, or the daily cycle if RUN_MODE=cron
set -e

if [ "$RUN_MODE" = "cron" ]; then
    echo "Starting daily paper-trading cycle..."
    exec python scripts/run_cycle_once.py
else
    echo "Starting web server..."
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi
