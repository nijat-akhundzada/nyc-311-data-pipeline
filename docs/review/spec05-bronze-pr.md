# feat(storage): durable Bronze domain and atomic page repository (Spec 05)

Base `main`; head `feat/05-bronze-domain-foundation-nijat`.

## Spec / ownership

Lead-authorized bounded Spec 05 slice; Nizami retains storage ownership and reviews
this new implementation. Firuz reviews the canonical run-table adapter. No peer
approval is assumed. Depends on merged PRs #4/#5/#6.

## Changes and contracts

Migration 0002 adds six Bronze/ops tables; immutable scope/cursor/checkpoint types;
atomic batched commits with generation pinning, page receipts, raw dedupe, associations,
CAS and durable counters. `ops.pipeline_runs` is the only run-history truth. Original
0001/runner/client/tooling/locks remain unchanged. Original migration tests stay at
their 0001 boundary; new domain tests cover all migrations. ADR-001 remains PROPOSED.

## Verification

`pytest tests -q -ra` with isolated PostgreSQL 16.14: **204 passed, zero skipped**
(175 unit + 29 integration). `ruff check .`, `ruff format --check .`, all seven
pre-commit hooks, context/whitespace checks passed. Failure at final counter update
rolls back every page write. Receipt replay, stale CAS, lock contention, new-run raw
version dedupe and constant eight-statement/100-row batch verified. Exact commands
and boundaries: `docs/spec05-bronze-verification.md`, `context/contracts/bronze-v1.md`.
Remote CI is pending PR creation; do not infer it from local results.

## Reviewer checklist / limits

Nizami: DDL/indexes, transaction ownership, raw/version counts, CAS and receipts.
Firuz: ingestion-only adapter, completed-extraction paused state, audit events and
same-session lock/recovery boundary. Human review and actual green CI required.
No Silver/Gold, quarantine/quality publish, successful watermark, scheduling or SCD2.
Full Spec 05 and source verification remain incomplete. Do not merge automatically.
