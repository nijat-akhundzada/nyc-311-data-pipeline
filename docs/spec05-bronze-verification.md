# Spec 05 durable Bronze slice — review evidence

Status: implemented on feature branch, **not merged/peer-approved**. Lead authorization
and exact engineering interface: `context/contracts/bronze-v1.md`. Nizami remains
storage owner; Firuz remains lifecycle/CI owner. Their approval is not assumed.
ADR-001 stays PROPOSED; full Specs 01/03/05 and assignment demonstration are incomplete.

## Changes

New migration 0002 creates six tables: `bronze.raw_service_requests`,
`ops.pipeline_runs`, `ops.ingest_checkpoints`, `ops.ingest_page_receipts`,
`ops.run_records`, `ops.run_events`. Existing migration 0001/ledger/runner are unchanged.
Original framework tests now explicitly copy only 0001 to test its empty namespaces;
new tests exercise the full chain including down-to-0001 and re-upgrade.

New `bronze_contracts.py` exposes immutable Scope, typed Checkpoint, CommitResult,
IngestRun and sanitized errors. `storage/bronze.py` provides dataset-lock context,
begin/resume adapter, checkpoint loading, atomic page commit and ingestion-only
finalization. No downstream tables, successful publication or second history manager.

The first page pins generation atomically. Exact receipts replay their original
results even after later pages, without re-counting or requiring response metadata
to match. Conflicting receipts/CAS fail. Raw identity is source ID plus full canonical
projected JSON hash. New runs associate existing raw versions without duplicating
payloads. One 100-row commit uses eight statements, including three set-based inserts;
there is no row-by-row DB write loop or assessment-scale performance claim.

## Actual tests

Environment: Python 3.12.11, shared locked pytest 9.2.0/Ruff 0.17.6, temporary venv
`/tmp/nyc311-pr6-venv`. PostgreSQL 16.14 in isolated Compose project
`nyc311-pr6-verify`, host loopback port 55439, synthetic credential only. No production
volume/DSN is used and no live API participates in deterministic tests.

Executed:

```sh
ruff check .
ruff format --check .
TEST_DATABASE_URL=<isolated-PG16-DSN> pytest tests -q -ra
PRE_COMMIT_HOME=<temporary-cache> pre-commit run --all-files
bash scripts/validate-context.sh
git diff --check
```

Measured full suite: **204 passed, zero skipped** (175 unit + 29 PostgreSQL integration).
Lint/format, context/whitespace and all seven pre-commit hooks passed. Tests cover
receipt replay/ambiguous acknowledgement, new-run logical dedupe, fresh/empty pages,
equal-timestamp opaque text ordering, multiple segments, typed updates, immutable
configuration/generation, interrupted connection restart before/after commit,
concurrent dataset-lock rejection and stale checkpoint conflicts. A trigger forces
failure at the final counter update: raw/association/receipt writes and the cursor
all roll back. Replay then succeeds after removing the synthetic trigger.

All original team commits remain ancestors of latest main. Applied SQL files,
existing client implementation, dependency locks, Docker and CI are not rewritten.

## Outstanding review / evidence

- Nizami: DDL/indexes, transaction ownership, batching/CAS and receipt contract.
- Firuz: canonical run-table adapter, ingestion-complete paused state and audit events;
  later RunTracker must reuse this table/session lock.
- Source freshness/header stability, publisher timezone/DST and complete updates,
  missing-key/schema preflight, replacements/deletions and genuine SCD2 observations
  remain unverified. Fixtures do not demonstrate those properties.
- Spec 05 still lacks quarantine, staged validation, Silver/Gold/atomic publication,
  candidate reduction/quality interfaces and measured million-row bulk throughput.
- Docker and remote CI results for the final combined implementation are recorded
  separately; this test report alone does not assert either passed.
