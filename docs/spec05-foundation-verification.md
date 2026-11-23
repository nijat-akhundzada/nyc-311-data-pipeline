# Spec 05 foundation — migration framework verification

**Status:** PARTIAL foundation evidence only (lead-approved foundation exception dated
2026-11-23). ADR-001 remains PROPOSED and full Spec 05 acceptance remains gated.
No source-dependent schema, run history, checkpoint/quarantine table, silver type,
gold model, SCD2 or repository API was implemented.

## Chosen approach

- **Ordered SQL files:** `db/migrations/<version>_<name>.{up,down}.sql`, discovered and
  sorted by numeric prefix (`0001`, `0002`, …). One coherent schema change per
  version. Applied files must not be edited or deleted.
- **Runner:** `src/nyc311_pipeline/storage/migrations.py`, a small psycopg 3 module
  with `upgrade`, `down --target` and `status`. No ORM is used.
- **Ledger:** private infrastructure schema `_migration.applied_migrations`
  (`version` PK, `name`, SHA-256 of the up script, `applied_at`). It is not a
  pipeline domain contract and does not use a `bronze`/`ops` namespace.
- **Exclusive lock:** session-level `pg_advisory_lock` with the stable key derived
  from SHA-256(`nyc311:migrations`), deliberately a different namespace from the
  future dataset run lock. A configurable `lock_timeout` turns contention into a
  clear `MigrationLockError` instead of an indefinite wait.
- **Atomicity:** each up/down script and its ledger insert/delete run in one
  psycopg transaction. A failing script rolls back its DDL and leaves no ledger
  row; a checksum mismatch on an applied version aborts loudly.
- **Only migration 0001** creates `bronze`, `silver`, `gold` and `ops` — four
  **empty** schemas. Its down script drops them with `RESTRICT` semantics.

## Dependency handoff to Firuz (Spec 02 owner)

This branch does **not** create or modify `pyproject.toml`, lock files, Docker or
CI configuration. Verification used an isolated virtual environment outside the
repository with: `psycopg[binary] == 3.3.9`, `pytest == 9.2.0`,
`ruff == 0.17.6` on Python 3.12.0. Firuz should add these as the shared runtime,
test and lint dependencies (and wire the `integration` job to PostgreSQL 16);
no extra driver is needed because the runner uses psycopg directly.

## Isolated test design

`tests/conftest.py` reads `TEST_DATABASE_URL` (maintenance DB on a disposable
PostgreSQL 16 server). Each integration test creates a uniquely named database,
runs there, and force-drops it in `finally`; nothing is left behind and no
network API, fixture dataset or secret is used. Without the variable the
integration module skips with an explicit message — a skip is not a pass.
Unit tests of migration discovery/checksums need no database.

## Verified commands and results

All commands were run from the repository root on Windows PowerShell. The
throwaway local PostgreSQL password is supplied through an environment variable
and is deliberately not written into this repository.

### 1. Isolated PostgreSQL 16 server

```powershell
docker pull postgres:16
$env:PGPASSWORD = Read-Host 'Throwaway local PostgreSQL password (not committed)'
docker run -d --name nyc311-spec05-pg16 `
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD="$env:PGPASSWORD" `
  -p 55432:5432 postgres:16
docker exec nyc311-spec05-pg16 pg_isready -U postgres
docker exec nyc311-spec05-pg16 psql -U postgres -tAc 'SHOW server_version'
```

Observed:

```text
Status: Downloaded newer image for postgres:16
/var/run/postgresql:5432 - accepting connections
16.16 (Debian 16.16-1.pgdg13+1)
```

### 2. Lint and format

```powershell
ruff format --check src/nyc311_pipeline/storage/migrations.py tests/conftest.py `
  tests/integration/test_migrations.py tests/unit/test_migration_discovery.py
ruff check src/nyc311_pipeline/storage/migrations.py tests/conftest.py `
  tests/integration/test_migrations.py tests/unit/test_migration_discovery.py
```

Observed: `4 files already formatted` and `All checks passed!`.

### 3. Unit + integration tests (fresh, repeat, rollback, failure, concurrency)

```powershell
$env:PYTHONPATH = 'src'
$env:TEST_DATABASE_URL = "postgresql://postgres:$env:PGPASSWORD@localhost:55432/postgres"
python -m pytest tests/unit tests/integration -v
```

Observed (PostgreSQL 16.16, 13 tests):

```text
tests/unit/test_migration_discovery.py::test_discovery_orders_versions_and_returns_checksums PASSED
tests/unit/test_migration_discovery.py::test_duplicate_versions_are_rejected PASSED
tests/unit/test_migration_discovery.py::test_malformed_filename_is_rejected PASSED
tests/unit/test_migration_discovery.py::test_down_without_matching_up_is_rejected PASSED
tests/unit/test_migration_discovery.py::test_redact_dsn_hides_password PASSED
tests/integration/test_migrations.py::test_server_is_postgresql_16 PASSED
tests/integration/test_migrations.py::test_fresh_migrations_create_four_empty_namespaces PASSED
tests/integration/test_migrations.py::test_reapplying_migrations_is_a_noop PASSED
tests/integration/test_migrations.py::test_failing_migration_rolls_back_and_corrected_migration_can_run PASSED
tests/integration/test_migrations.py::test_rollback_removes_namespace_and_ledger_entry PASSED
tests/integration/test_migrations.py::test_edited_applied_migration_is_rejected PASSED
tests/integration/test_migrations.py::test_concurrent_migrations_serialize_without_duplicate_application PASSED
tests/integration/test_migrations.py::test_lock_contention_fails_with_clear_error PASSED
============================== 13 passed in 3.04s ==============================
```

These cover: four empty namespaces plus one ledger row on a fresh DB; a repeated
application that is a no-op with an unchanged `applied_at`; a deliberately failing
`0002` script whose DDL and ledger row are both absent afterwards while corrected
`0003` then applies; explicit `down --target 0` and successful re-upgrade; rejection
of an edited applied file; two simultaneous upgrade threads applying each version
exactly once; and a clear lock error when another session holds the advisory lock.

### 4. Manual CLI lifecycle on a dedicated database

```powershell
docker exec nyc311-spec05-pg16 psql -U postgres -c 'CREATE DATABASE spec05_cli_sequence;'
$dsn = "postgresql://postgres:$env:PGPASSWORD@localhost:55432/spec05_cli_sequence"
python -m nyc311_pipeline.storage.migrations --dsn $dsn status
python -m nyc311_pipeline.storage.migrations --dsn $dsn upgrade
python -m nyc311_pipeline.storage.migrations --dsn $dsn status
python -m nyc311_pipeline.storage.migrations --dsn $dsn upgrade
```

Observed (each exit 0):

```text
pending 0001_create_namespaces
applied: 0001_create_namespaces
already applied: (none)
applied 0001_create_namespaces 06d1985295687fbc86fae5823526f7b438256ad5d7b03db97d12352fe8cd4a35 2026-11-23 17:44:55.782747+00:00
applied: (none)
already applied: 0001_create_namespaces
```

Direct database inspection after those commands:

```powershell
docker exec nyc311-spec05-pg16 psql -U postgres -d spec05_cli_sequence `
  -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('bronze','silver','gold','ops','_migration') ORDER BY 1;" `
  -c "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema IN ('bronze','silver','gold','ops');" `
  -c "SELECT version, name FROM _migration.applied_migrations ORDER BY version;"
```

```text
 _migration | bronze | gold | ops | silver        (5 rows)
 (0 rows)                                        <-- no domain tables
 1 | create_namespaces                           (1 row)
```

Rollback and re-check:

```powershell
python -m nyc311_pipeline.storage.migrations --dsn $dsn down --target 0
python -m nyc311_pipeline.storage.migrations --dsn $dsn status
```

```text
rolled back: 0001_create_namespaces
kept: (none)
pending 0001_create_namespaces
```

A follow-up `psql` query showed zero of the four domain schemas and zero ledger rows.

### 5. Concurrent CLI invocations

On a second fresh database, two `upgrade` commands were started simultaneously
against the same DSN; both exited 0:

```text
invocation A: applied: 0001_create_namespaces / already applied: (none)
invocation B: applied: (none) / already applied: 0001_create_namespaces
```

## Boundaries and remaining gaps

- No domain table exists: the four namespaces are intentionally empty. The
  `ops.run_history` vs `ops.pipeline_runs` conflict is **not** resolved here; no
  run-history table was created and the lead must approve the canonical name
  before any domain DDL.
- CI did not exist when these checks ran; Firuz must add the `integration` job.
  This local PostgreSQL 16 evidence is not a claim that CI passed.
- No live source API, secret, dataset, checkpoint, bronze repository, silver
  publication, gold/SCD2 or scheduling code is included.
- Cleanup of local evidence container: `docker rm -f nyc311-spec05-pg16`.
