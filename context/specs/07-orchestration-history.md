# Spec 07 — Orchestration History

**Owner:** Firuz  
**Status:** PLANNED / NOT IMPLEMENTED  
**Type:** Implementation  
**Dependencies:** 02, 03, 05  

## Objective
Scheduled runs, durable run tracking and coordination.

## Required implementation tasks
1. Implement cron-like scheduler chosen by ADR, invoking CLI in controlled container
2. Log every requested run status pending/running/succeeded/failed with counts/checkpoint/time/errors
3. Prevent overlapping runs of same scope using Postgres advisory lock or lease with stale recovery
4. Track recoverable interrupted run and heartbeat; support resuming from saved checkpoint
5. Startup waits for DB health; bounded retry and failure exit; no tight infinite polling
6. No credentials in logs; include clear operational docs and manual trigger path
7. Tests for overlapping scheduler instances, failed run history, restart and retry

## Files and boundaries
- `src/nyc311_pipeline/orchestration/`
- `src/nyc311_pipeline/ops/`
- `docs/runbook.md`
- `tests/integration/test_orchestration.py`

## Acceptance criteria
- [ ] One scheduled run recorded with timestamps and outcome
- [ ] No double-publication on concurrent triggers
- [ ] Missed DB readiness recovers or fails visibly

## Required verification
- Focused pytest tests (unit/integration), formatting/lint, plus a specific manual end-to-end check where relevant. Record exact commands and results in PR.
- Test unhappy paths and prove no unintended row-count or downstream changes.
- Where infrastructure/source access is missing, disclose missing evidence; do not mark pass.

## PR handoff
- Branch `feat/07-orchestration-history-firuz` (shorten if preferred).
- Conventional atomic commits; open draft PR to `main`; use PR template; request human peer review.
- Do not change another owner’s directory or common contract without review and documented approval.
