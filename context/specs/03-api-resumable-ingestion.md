# Spec 03 — Api Resumable Ingestion

**Owner:** Nijat  
**Status:** PLANNED / NOT IMPLEMENTED  
**Type:** Implementation  
**Dependencies:** 01 accepted; DB contract with 05; 05 merged for full integration  

## Objective
Stable paginated ingestion, retry handling and resumable checkpoints.

## Required implementation tasks
1. Implement httpx API client with bounded timeout/retries, Retry-After and 429/5xx handling; fail on 4xx other than 429
2. Use frozen upper-bound and approved keyset pagination (no offset-only approach)
3. Commit bronze page + cursor atomically via Nizami repository, restart at last committed cursor
4. Support CLI incremental and `[start,end)` backfill windows with independent checkpoints; enforce valid date constraints
5. Support mutable-record refresh/lookback per ADR and idempotent dedupe/upsert
6. Detect field additions/removals/type shifts, log schema drift with masking and fail on breaking changes
7. Test page boundary ties, identical replay, simulated termination, 429/503 and malformed API payload

## Files and boundaries
- `src/nyc311_pipeline/ingestion/`
- `tests/unit/test_ingestion.py`
- `tests/integration/test_resume.py`

## Acceptance criteria
- [ ] Interrupted run resumes without skipped/duplicated logical rows
- [ ] Two identical runs leave logical bronze state unchanged
- [ ] No live API requirement in unit/CI tests

## Required verification
- Focused pytest tests (unit/integration), formatting/lint, plus a specific manual end-to-end check where relevant. Record exact commands and results in PR.
- Test unhappy paths and prove no unintended row-count or downstream changes.
- Where infrastructure/source access is missing, disclose missing evidence; do not mark pass.

## PR handoff
- Branch `feat/03-api-resumable-ingestion-nijat` (shorten if preferred).
- Conventional atomic commits; open draft PR to `main`; use PR template; request human peer review.
- Do not change another owner’s directory or common contract without review and documented approval.
