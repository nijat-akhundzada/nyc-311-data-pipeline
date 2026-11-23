# Architecture — proposed and subject to Spec 01 approval

```text
NYC 311 Socrata API
   | HTTP retries + 429 Retry-After + stable keyset cursor
   v
ingestion ---> PostgreSQL bronze.raw_service_requests (JSONB, dedupe key)
   |                    | persisted ingest checkpoints
   v                    v
validation ------> ops.quarantine (reason + source + run_id)
   | quality gate PASS only
   v
PostgreSQL silver.service_requests (typed, normalized, transactional publish)
   |
   v
gold loader ---> gold.dim_date + dim_agency + dim_service_request_state (SCD2)
                 + gold.fact_service_requests
   |
   v
SQL analytics and EXPLAIN ANALYZE evidence

orchestrator --> ops.pipeline_runs + scheduled jobs + failure drill logs
```

## Bounded ownership
- `src/nyc311_pipeline/ingestion`, `validation`, `silver`: **Nijat**.
- `db/migrations`, `src/nyc311_pipeline/storage`, `gold`, `sql/analytics`, `sql/performance`: **Nizami**.
- `docker/`, `.github/workflows/`, orchestration, `ops/run_history.py`, scripts for recovery: **Firuz**.
- `src/nyc311_pipeline/cli.py`, configuration and cross-module contracts: **Nijat** coordinates; each owner provides an interface as agreed in `context/contracts/README.md`.

## Proposed stack
Python 3.12+, httpx, Pydantic 2, psycopg 3 or SQLAlchemy 2 (one choice in ADR), PostgreSQL 16+, pytest, ruff, pre-commit, Docker Compose, GitHub Actions, lightweight external scheduler (cron-like container or APScheduler, **not both**). `uv` optional if team agrees; lock and reproducibility required. No FastAPI UI or extra services required.

## Data invariants
1. Record identity: source `unique_key` is retained unchanged; bronze dedupes source id and content version; no UUID substitution for source IDs.
2. Cursor: stable lexicographic `(created_date, unique_key)` ordering; checkpoint advanced **only after durable bronze page commit**. Watermark and backfill scopes are separate; freeze high watermark at run start. For mutable source changes, a rolling lookback or source `updated_at` strategy is required and tested.
3. Validation quarantines each rejected record with deterministic reasons. A rejected run cannot publish **any** changes to silver/gold; bronze and quarantine may remain for audit/recovery.
4. Publish silver/gold as one consistent run boundary or use versioned run visibility: consumers cannot see partially published data. Prefer single DB transaction for staging-to-silver/gold after quality gate, with batch staging if scale demands.
5. Gold fact rows must never reference multiple concurrent/current SCD2 rows. Type 2 ranges are non-overlapping, `valid_from` inclusive and `valid_to` exclusive, exactly one current row per natural key.
6. Idempotency: identical source snapshot + same backfill/replay ⇒ same **logical** bronze/silver/gold data and dimension versions (ignore run audit timestamps/IDs). Changes create a new SCD2 version only on genuine tracked attribute change.
7. Retry only transient failures; obey Retry-After and bounded exponential backoff with jitter. Unknown API contract changes fail visibly; never silently drop fields needed by analytics.
8. Backfill bounded by UTC start-inclusive/end-exclusive range of source `created_date`, with event-time zone conversion clearly documented.

## Deployment, privacy and security
Local docker compose only. Environment-based secrets; `.env.example` with fake placeholders. Health checks and DB readiness retries; DB persistent named volume; application runs non-root. No personal identifying fields are needed in gold; minimize/exclude free-text/PII columns in silver/gold and avoid logging request bodies.

## Pending design choices
Source availability/API rate quota and exact field names; resilient mutable-record synchronization; gold SCD2 entity; storage library; scheduler. Spec 01 records approved choices before other specs are unblocked.
