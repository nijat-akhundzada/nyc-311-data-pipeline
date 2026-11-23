# Spec 05 — Database Bronze Ops

**Owner:** Nizami  
**Status:** PLANNED / NOT IMPLEMENTED  
**Type:** Implementation  
**Dependencies:** 01 accepted  

## Objective
PostgreSQL schemas and efficient bulk storage interfaces.

## Required implementation tasks
1. Write forward migrations for bronze/silver/gold/ops and constraints/indexes
2. Create bronze JSONB raw table with source identity, fingerprints, timestamps, run tracking; choose deterministic conflict keys
3. Create ops.run_history, ops.ingest_checkpoints and ops.quarantine with statuses/counts/reasons
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
