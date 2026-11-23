# Operational runbook — TARGET COMMANDS, NOT YET IMPLEMENTED

Intended future workflow: copy `.env.example` to `.env` (do not commit real tokens); `docker compose up --build -d db`; migrate schema; `docker compose run --rm pipeline python -m nyc311_pipeline run --mode backfill --start 2025-01-01 --end 2025-02-01`; `docker compose run --rm pipeline python -m nyc311_pipeline run --mode incremental`; inspect run_history and gold, invoke analytics; enable scheduler. All commands and service names must be replaced by **verified commands** before final submission.

Required documented failure drills: stop ingestion mid-page and resume; start pipeline while DB is unavailable; inject invalid fixture > threshold, compare silver/gold checksums and quarantine before/after. Run-history fields and meaningful logs must show each outcome.

## Durable Bronze slice (review branch only)

Use the unchanged migration CLI before constructing the repository:
`python -m nyc311_pipeline.storage.migrations upgrade` with `DATABASE_URL` supplied
through the environment. In the image, add `--migrations-dir /app/db/migrations`
before `upgrade`. Never edit an applied SQL migration.

The bounded programmatic entry point is `ingestion.service.ingest`, not a production
pipeline CLI. Allocate and retain a UUID before calling it; pass a dedicated psycopg
connection opened with `autocommit=True` to `BronzeRepository`. Construct an immutable
`IngestScope` with explicit source-wall-time intervals and page size, then use
`async with ApiClient(app_token=os.environ.get('SOCRATA_APP_TOKEN'))` and await
`ingest(client, repository, scope, run_id=identity, max_records=100)`.

To resume, reopen the dedicated connection, rebuild the **same** scope and pass
`resume_run_id=identity` instead of `run_id`. The service acquires the dataset lock.
Caps may change; source bounds/page size/policy may not. Read the persisted run and
checkpoint for progress; source failures raise categorized errors. A lost DB session
may leave running metadata and requires explicit resume. Generation change requires
a new audited extraction, never cursor reset. A completed extraction stays
unpublished: no Silver/Gold result or pipeline success is promised.

Contract and evidence: `context/contracts/bronze-v1.md`,
`docs/spec03-bronze-ingestion-verification.md`. Review gates and remaining source
risks remain in force; do not schedule this as a complete production pipeline.
