# Executed container recovery — 24 November 2026

**PASS for all three bounded synthetic demonstrations.** These were real Docker
process/network failures against disposable PostgreSQL 16 resources, not mocked
claims. No destructive action touched the source-only database or other projects.
Raw evidence: [recovery.json](evidence/final/recovery.json).

Project `nyc311-final-drills`, container `nyc311-final-drills-db`, named volume
`nyc311_final_drills_data`; runtime image freshly built as `nyc311-final:local`,
UID 10001. Initial DB empty; migrations 0001–0004 applied using the image CLI.
The slow wrapper changes only fixture page timing; all checkpoints and publications
use existing production components. No applied migration or runner behavior changed.

## 1. SIGKILL and durable resume

Run `bcf3d3f0-72f2-478f-bf02-a630f41fc5d2` used 20 synthetic fixture IDs with page
size 2. Before kill: checkpoint page 1, not exhausted, received/inserted 2,
status running/ingest, no publication. `docker kill --signal KILL CONTAINER` followed
by `docker wait CONTAINER` returned **137**. A new container invoked the same script
with `--run-id UUID --resume`; exit **0**, same run succeeded, received/inserted 20.
Final Bronze/Silver/Gold/distinct Gold keys: **20/20/20/20**. Resume used persisted
cursor and pinned fixture hash; no lost page, extra logical fact or fake new run.

## 2. PostgreSQL unavailable

Stopped only the drill DB using `docker compose ... stop db`. Then invoked the
actual `pipeline run --mode incremental --start 2025-01-01 --end 2026-01-01
--fixture /fixtures/valid.json` with `--no-deps` to exercise CLI readiness rather
than Compose's health gate. Exit **5**, categorized retryable storage, unknown
publication (conservative response), bounded elapsed recorded in JSON. Existing
unit tests assert three attempts and sleeps 1/2 seconds; this drill verifies the
actual failure boundary, not a separately instrumented attempt count.

Restarted with `up -d --wait db`; same invocation succeeded under new run
`39075f85-d618-45f1-8f61-a6beac49eeec`, exit **0**, 20 valid/published. Named-volume
persistence verified by surviving rows: **22 Bronze / 20 Silver / 20 Gold**.
The extra two raw versions belong to the malformed-input drill and remain audited.
The failed-start UUID did not imply a durable run row while the DB was down.

## 3. Malformed batch above 5%

After valid baseline, `run --mode backfill --start 2025-01-01 --end 2026-01-01
--fixture /fixtures/quality-failure.json` exited **4**, failed/unpublished.
Two of 20 candidates (10%) quarantined for `closed_before_created`. Every published
row in Silver, all six Gold tables, and publication watermarks was hashed before
and after; hashes and counts match exactly. Bronze/quarantine retained for audit.
The precise run UUID and both snapshots are in JSON.

## Reproduction and isolation

Use a **fresh dedicated** Compose project named `nyc311-final-drills`, PostgreSQL
16 database and unique volume/container/port names. Derive the existing Compose
configuration with these names; never reuse the normal project DB. Export
`DRILL_COMPOSE_FILE`, `DRILL_ENV_FILE`, `DRILL_ADMIN_URL` (host DSN),
`DRILL_CONTAINER_URL` (same database via `db:5432`) and
`DRILL_CONFIRM_DISPOSABLE=yes`, then:

```sh
docker build -t nyc311-final:local .
python scripts/drills/container-recovery.py > recovery.json
```

The script refuses existing run history and requires explicit disposable consent.
It mounts the repository fixture/script directories read-only. It is opt-in and
never runs destructively in CI. Repeated whole-drill execution requires a fresh
isolated DB. Remove only your drill containers/volume after retaining evidence;
keep the real-source volume. Example configuration and fresh setup procedure:
[final verification](final-verification.md).
