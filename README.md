# NYC 311 Data Engineering Pipeline

**Team:** Nijat Akhundzadeh (lead), Nizami, Firuz. **Deadline:** 26 November 2026.

Functional review branch: Python 3.12, direct psycopg 3 SQL and PostgreSQL 16.
Purpose: analyze NYC 311 request volumes, agency performance and recorded
resolution times. It has resumable Bronze ingestion, staged validation/quarantine,
a 5% quality gate, atomic Silver/Gold publication and observed-time SCD2.
**ADR-001 remains PROPOSED:** publisher timezone, complete change capture and genuine
source SCD2 observations are still unverified. Synthetic examples are not real history.

## Run a deterministic demonstration

Use a disposable demo database; fixtures are explicitly synthetic. From the checkout:

```sh
cp .env.example .env  # Set local PostgreSQL credentials; never commit this file.
docker compose up -d --wait db
docker compose --profile pipeline build pipeline
docker compose --profile pipeline run --rm pipeline migrate
docker compose --profile pipeline run --rm pipeline health
docker compose --profile pipeline run --rm pipeline run --mode backfill \
  --start 2025-01-01 --end 2026-01-01 --fixture /fixtures/valid.json
# Publishes 20 synthetic requests. Repeating it creates no extra facts/SCD2 versions.
docker compose --profile pipeline run --rm pipeline run --mode backfill \
  --start 2025-01-01 --end 2026-01-01 --fixture /fixtures/quality-failure.json
# Expected exit 4: 10% invalid, quarantine retained, published data unchanged.
```

Omit `--fixture` only for real API extraction. For a small live check add
`--max-records 3`; a capped/incomplete run is paused and **never published**.
Read the emitted run UUID, then resume with the same source/fixture:

```sh
docker compose --profile pipeline run --rm pipeline report --run-id UUID
docker compose --profile pipeline run --rm pipeline run --resume-run-id UUID \
  --fixture /fixtures/valid.json
```

Incremental mode requires a creation cohort. The first incremental needs an explicit
UTC lower bound; later runs use its published watermark with a 48-hour overlap:

```sh
docker compose --profile pipeline run --rm pipeline run --mode incremental \
  --start 2025-01-01 --end 2026-01-01 --initial-lower 2026-11-01
```

That real-source command is uncapped; choose a practical cohort before running it.
Update upper bounds freeze at run start minus five minutes. Bounds are UTC, end-exclusive.
Run settings/quality policy are frozen; only the invocation cap may change on resume.

## Correctness and operation

- Raw identity: source ID plus canonical projected JSON hash. Page receipts make
  retries idempotent; raw/association/checkpoint writes commit together.
- Validation streams bounded batches. New York event-time interpretation is
  provisional; DST gaps/folds quarantine. Exactly 5% invalid passes; over 5% or zero
  evaluated fails. Required API sort/envelope violations abort before staging.
- Silver, all Gold dimensions/facts, run success and update watermark commit in
  **one transaction**, protected by the existing dataset lock.
- Gold has one fact per request, date/agency/complaint/borough dimensions and request
  state SCD2. Only changed status/agency/complaint produces a new observed version.
  Unknown categories have dimension members; unsupported historical states are never invented.
- A host-cron wrapper is provided in `scripts/scheduled-run.sh` and
  `docker/scheduler.crontab.example`. It is not installed automatically.

See [runbook](docs/runbook.md), [data model](docs/data-model.md),
[engineering contract](context/contracts/functional-v1.md) and
[actual verification](docs/functional-pipeline-verification.md).

## Development and delivery

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.lock
.venv/bin/pip install --no-deps --no-build-isolation -e .
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest tests/unit -q
# TEST_DATABASE_URL must reference a disposable PostgreSQL 16 maintenance database.
.venv/bin/pytest tests/integration -q
```

Migration 0001/0002 and original team commits are preserved; changes are delivered by
conventional commits and a human-reviewed feature PR. CI success is required before
merge and is never inferred from local tests. Students must understand every line.
Remaining major work: roughly one million real validated facts, analytical SQL and
EXPLAIN measurements, real kill/startup/schedule evidence, source/SCD2 observations
and submission preparation. No scale/performance or assignment completion is claimed.
