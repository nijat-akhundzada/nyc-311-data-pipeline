# Operational runbook — TARGET COMMANDS, NOT YET IMPLEMENTED

Intended future workflow: copy `.env.example` to `.env` (do not commit real tokens); `docker compose up --build -d db`; migrate schema; `docker compose run --rm pipeline python -m nyc311_pipeline run --mode backfill --start 2025-01-01 --end 2025-02-01`; `docker compose run --rm pipeline python -m nyc311_pipeline run --mode incremental`; inspect run_history and gold, invoke analytics; enable scheduler. All commands and service names must be replaced by **verified commands** before final submission.

Required documented failure drills: stop ingestion mid-page and resume; start pipeline while DB is unavailable; inject invalid fixture > threshold, compare silver/gold checksums and quarantine before/after. Run-history fields and meaningful logs must show each outcome.
