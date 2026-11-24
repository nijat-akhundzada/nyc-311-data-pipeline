# Spec 09 — Failure Recovery

**Owner:** Firuz  
**Status:** FINAL ITERATION LEAD-AUTHORIZED; branch evidence pending human review  
**Type:** Implementation  
**Dependencies:** 04, 06, 07  

See the final integrated authorization in `00-build-plan.md`. Earlier separate
branch gates do not block this explicitly assigned final iteration. Acceptance
requires actual evidence; no full completion or peer approval is inferred.

## Objective
Reproducible failure drills meeting assignment.

## Required implementation tasks
1. Script intentional kill of ingestion container mid-run and restart; verify checkpoint progression and no duplication
2. Start pipeline before PostgreSQL ready; demonstrate wait/retry or explicit recoverable failure then success
3. Feed deterministic malformed fixture batch above threshold; show quarantine rows, failed run and unchanged silver/gold
4. Record commands, expected vs actual results, run IDs, row counts and negative assertions
5. Make drills opt-in for local/demo, never automatically kill developer services in CI
6. Exercise duplicate replay and scheduler lock where practical

## Files and boundaries
- `scripts/drills/`
- `tests/integration/test_recovery.py`
- `docs/failure-recovery-report.md`

## Acceptance criteria
- [ ] Each of three required scenarios reproducibly demonstrated
- [ ] Measurements and logs reflect actual execution
- [ ] No partial downstream publication during fault

## Required verification
- Focused pytest tests (unit/integration), formatting/lint, plus a specific manual end-to-end check where relevant. Record exact commands and results in PR.
- Test unhappy paths and prove no unintended row-count or downstream changes.
- Where infrastructure/source access is missing, disclose missing evidence; do not mark pass.

## PR handoff
- Branch `feat/09-failure-recovery-firuz` (shorten if preferred).
- Conventional atomic commits; open draft PR to `main`; use PR template; request human peer review.
- Do not change another owner’s directory or common contract without review and documented approval.
