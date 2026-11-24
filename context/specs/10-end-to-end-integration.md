# Spec 10 — End To End Integration

**Owner:** Nijat  
**Status:** CURRENT SLICE LEAD-AUTHORIZED; implementation subject to human review  
**Type:** Implementation  
**Dependencies:** 02–09  

## Current integration authorization

The lead's 2026-11-24 task authorizes the functional pipeline slice on one integration
branch; `context/contracts/functional-v1.md` records exact policy and retained risks.
Older dependency/one-spec branch gates are superseded for this task only. No source
evidence, peer approval or full assignment completion is inferred.

## Objective
Assemble owned modules and verify full pipeline.

## Required implementation tasks
1. Wire CLI → orchestration → ingestion → bronze → validation → silver/gold publish → analytics, respecting contracts
2. Ensure incremental/backfill arguments, logging, exit codes and stats match documented public interfaces
3. Add end-to-end fixtures and source-independent integration tests for replay, backfill, gate failure, recovery
4. Run actual representative load and inspect star facts/quality/run history; coordinate fixes by owner in reviewed PRs
5. Refresh documentation with verified commands and observed behavior; avoid adding unrequested features

## Files and boundaries
- `src/nyc311_pipeline/cli.py`
- `src/nyc311_pipeline/__main__.py`
- `tests/e2e/`
- `docs/runbook.md`

## Acceptance criteria
- [ ] End-to-end local compose demo succeeds
- [ ] Replay and date range correctness assertions recorded
- [ ] All tests CI green, outstanding issues recorded

## Required verification
- Focused pytest tests (unit/integration), formatting/lint, plus a specific manual end-to-end check where relevant. Record exact commands and results in PR.
- Test unhappy paths and prove no unintended row-count or downstream changes.
- Where infrastructure/source access is missing, disclose missing evidence; do not mark pass.

## PR handoff
- Branch `feat/10-end-to-end-integration-nijat` (shorten if preferred).
- Conventional atomic commits; open draft PR to `main`; use PR template; request human peer review.
- Do not change another owner’s directory or common contract without review and documented approval.
