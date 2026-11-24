# Spec 05 — Database Bronze Ops

**Owner:** Nizami  
**Status:** BOUNDED BRONZE SLICE LEAD-AUTHORIZED / IMPLEMENTED ON REVIEW BRANCH; full scope gated  
**Type:** Implementation  
**Dependencies:** foundation: isolated PostgreSQL 16; full scope: 01 accepted and reviewed shared DB contracts  

## Lead-authorized durable Bronze slice — 2026-11-24

The project lead explicitly authorizes the minimum durable Bronze implementation
in the current task, risk-accepting the engineering policies in
`context/contracts/bronze-v1.md`. This supersedes older source/full-spec dependency
blocks **only** for Spec 05 raw/run/checkpoint/receipt/association persistence and
Spec 03 bounded ingestion/resume using the existing client. Separate dependent
feature PRs preserve the one-spec implementation workflow. No teammate approval
is inferred; Nizami reviews storage/transactions and Firuz reviews the temporary
canonical-table ingestion lifecycle adapter. No earlier owner implementation or
applied migration may be rewritten.

ADR-001 remains PROPOSED; full Spec 01 and full Specs 03/05 are not complete.
No Silver/Gold, quarantine/quality publication, scheduler, successful watermark
advancement, fabricated SCD2 history or production pipeline runner is authorized
by this slice. See the Bronze contract for exact interfaces and limitations.

## Objective
PostgreSQL schemas and efficient bulk storage interfaces.

## Approved foundation scope — 2026-11-23

Nizami may implement a small ordered migration framework with a migration ledger and exclusive migration lock, one initial migration creating empty `bronze`, `silver`, `gold`, `ops` namespaces, and isolated PostgreSQL integration tests. Migration bookkeeping is infrastructure metadata, not a pipeline domain contract. Choose and document one lightweight migration approach; coordinate any dependency additions through Firuz's Spec 02 pyproject/lock ownership. An isolated PostgreSQL 16 instance is sufficient initially; verify compatibility with Spec 02 Compose/CI when available, without editing Firuz's files independently.

No bronze data tables, pipeline run/checkpoint/quarantine tables, typed silver, gold model, COPY/upsert repository interfaces or source cursor rules are authorized by this exception. The historical `ops.run_history` naming conflict is now resolved by the lead's bounded Bronze contract in favor of `ops.pipeline_runs`; no second history table is permitted. Full scope retains accepted Spec 01 as a dependency.

### Foundation acceptance criteria

- [ ] Fresh PostgreSQL 16 database receives the four namespaces and migration bookkeeping using documented commands.
- [ ] Reapplying migrations is a safe no-op with one ledger entry per migration; applied migrations are never rewritten.
- [ ] A failing test migration rolls back its changes and is not marked applied; a subsequent corrected pending migration can run.
- [ ] Two concurrent migration invocations serialize safely (or one exits with a clear lock failure), without duplicate application or partial schema state.
- [ ] Tests use isolated/disposable databases, leave no source-dependent tables and require no live API or secrets. Record exact commands/results; run the tests in Spec 02 CI when available.

Foundation acceptance is partial only; the full criteria below (page replay, cursor atomicity and bulk behavior) remain blocked until reviewed source/DB contracts and later implementation exist.

## Required implementation tasks
1. Write forward migrations for bronze/silver/gold/ops and constraints/indexes
2. Create bronze JSONB raw table with source identity, fingerprints, timestamps, run tracking; choose deterministic conflict keys
3. Create ops.pipeline_runs, ops.ingest_checkpoints and ops.quarantine with statuses/counts/reasons
4. Create silver normalized typed schema matching source contract
5. Expose transaction-scoped bulk COPY or batched upsert API and atomic page+checkpoint repository methods
6. Add schema constraints and rollback-safe migrations, and test concurrency/checkpoint integrity
7. Coordinate names and signatures with Nijat/Firuz before PR

## Files and boundaries
- `db/migrations/`
- `src/nyc311_pipeline/storage/`
- `tests/integration/test_storage.py`
- `docs/data-model.md`

## Acceptance criteria
- [ ] Fresh DB migrations pass and rerun safely
- [ ] Duplicate page replay cannot multiply rows
- [ ] DB persistence and atomic cursor behavior demonstrated
- [ ] Bulk load does not issue one statement per row

## Required verification
- Focused pytest tests (unit/integration), formatting/lint, plus a specific manual end-to-end check where relevant. Record exact commands and results in PR.
- Test unhappy paths and prove no unintended row-count or downstream changes.
- Where infrastructure/source access is missing, disclose missing evidence; do not mark pass.

## PR handoff
- Branch `feat/05-database-bronze-ops-nizami` (shorten if preferred).
- Conventional atomic commits; open draft PR to `main`; use PR template; request human peer review.
- Do not change another owner’s directory or common contract without review and documented approval.
