# Spec 04 — Validation Silver Quality

**Owner:** Nijat  
**Status:** CURRENT SLICE LEAD-AUTHORIZED; implementation subject to human review  
**Type:** Implementation  
**Dependencies:** 03, 05  

## Current integration authorization

The lead's 2026-11-24 task authorizes the functional pipeline slice on one integration
branch; `context/contracts/functional-v1.md` records exact policy and retained risks.
Older dependency/one-spec branch gates are superseded for this task only. No source
evidence, peer approval or full assignment completion is inferred.

## Objective
Validation, quarantine, quality gate and transactional silver publication.

## Required implementation tasks
1. Validate required identity/time, enum-like status, sensible values and source schema according to ADR
2. Write every invalid row to ops.quarantine with reason codes and source/run references; do not silently drop
3. Normalize approved silver fields and keep PII/free-text out of gold
4. Calculate run-level invalid fraction; fail when > 0.05 by default; define zero-total behavior as explicit failure
5. Stage valid records; do not mutate published silver/gold until gate passes
6. Ensure silver and gold publish in one consistent committed boundary with Nizami gold loader (coordinate interface)
7. Tests: valid/invalid/missing keys, threshold at/either side of 5%, failure leaves downstream snapshot identical

## Files and boundaries
- `src/nyc311_pipeline/validation/`
- `src/nyc311_pipeline/silver/`
- `tests/unit/test_quality.py`
- `tests/integration/test_quality_gate.py`

## Acceptance criteria
- [ ] Rejected input persisted with reason
- [ ] At threshold pass; over threshold fail and no downstream changes
- [ ] Successful rerun idempotent

## Required verification
- Focused pytest tests (unit/integration), formatting/lint, plus a specific manual end-to-end check where relevant. Record exact commands and results in PR.
- Test unhappy paths and prove no unintended row-count or downstream changes.
- Where infrastructure/source access is missing, disclose missing evidence; do not mark pass.

## PR handoff
- Branch `feat/04-validation-silver-quality-nijat` (shorten if preferred).
- Conventional atomic commits; open draft PR to `main`; use PR template; request human peer review.
- Do not change another owner’s directory or common contract without review and documented approval.
