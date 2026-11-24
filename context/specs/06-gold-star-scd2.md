# Spec 06 — Gold Star Scd2

**Owner:** Nizami  
**Status:** CURRENT SLICE LEAD-AUTHORIZED; implementation subject to human review  
**Type:** Implementation  
**Dependencies:** 04, 05  

## Current integration authorization

The lead's 2026-11-24 task authorizes the functional pipeline slice on one integration
branch; `context/contracts/functional-v1.md` records exact policy and retained risks.
Older dependency/one-spec branch gates are superseded for this task only. No source
evidence, peer approval or full assignment completion is inferred.

## Objective
Analytics-ready star with real observed SCD Type 2 history.

## Required implementation tasks
1. Implement gold fact_service_requests with appropriate grain and dimension foreign keys
2. Implement dim_date, dim_agency and dim_service_request_state SCD2 (or approved replacement)
3. Use natural key + checksum of tracked attributes, valid_from inclusive/valid_to exclusive, is_current, unique current index
4. Close prior version only when actual observed attributes change; never generate versions for unchanged replay
5. Ensure dimension version joins pick the applicable version at defined load/observation time and cannot multiply fact counts
6. Publish gold in the silver/gold transaction boundary; effective-dating semantics documented
7. Test initial, unchanged, changed, reverted values, concurrent updates, backfill, no overlapping intervals

## Files and boundaries
- `db/migrations/`
- `src/nyc311_pipeline/gold/`
- `tests/integration/test_scd2.py`
- `docs/data-model.md`

## Acceptance criteria
- [ ] SCD2 history captures verified observed changes
- [ ] No duplicate current versions or overlapping periods
- [ ] Replay leaves logical fact/dimension counts and versions unchanged

## Required verification
- Focused pytest tests (unit/integration), formatting/lint, plus a specific manual end-to-end check where relevant. Record exact commands and results in PR.
- Test unhappy paths and prove no unintended row-count or downstream changes.
- Where infrastructure/source access is missing, disclose missing evidence; do not mark pass.

## PR handoff
- Branch `feat/06-gold-star-scd2-nizami` (shorten if preferred).
- Conventional atomic commits; open draft PR to `main`; use PR template; request human peer review.
- Do not change another owner’s directory or common contract without review and documented approval.
