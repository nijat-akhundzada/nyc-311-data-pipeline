# Spec 08 — Analytics Performance

**Owner:** Nizami  
**Status:** FINAL ITERATION LEAD-AUTHORIZED; branch evidence pending human review  
**Type:** Implementation  
**Dependencies:** 06 + million-row real source load  

See the final integrated authorization in `00-build-plan.md`. Earlier separate
branch gates do not block this explicitly assigned final iteration. Acceptance
requires actual evidence; no full completion or peer approval is inferred.

## Objective
Analytical SQL plus defensible before/after performance measurements.

## Required implementation tasks
1. Create >=4 meaningful SQL analyses using CTEs and window functions over gold (e.g. agency volume/rank, weekly trends, borough ranking, resolution times)
2. Load at least ~1,000,000 real records with documented source window and provenance (no duplication to inflate)
3. Run baseline EXPLAIN (ANALYZE, BUFFERS) under recorded hardware/config/row counts
4. Identify one or more slow SQL queries and tune using justified index, partition, or rewrite
5. Rerun exact same workload and input; capture query plans, medians of >=3 cold/warm comparable runs and speedups
6. Explain trade-offs and verify no change in query results; do not fabricate performance figures

## Files and boundaries
- `sql/analytics/`
- `sql/performance/`
- `docs/performance-report.md`
- `tests/integration/test_analytics.py`

## Acceptance criteria
- [ ] SQL uses both CTEs and window functions
- [ ] Actual before/after execution and speedup documented with plans
- [ ] At least 1M real source records loaded and counted

## Required verification
- Focused pytest tests (unit/integration), formatting/lint, plus a specific manual end-to-end check where relevant. Record exact commands and results in PR.
- Test unhappy paths and prove no unintended row-count or downstream changes.
- Where infrastructure/source access is missing, disclose missing evidence; do not mark pass.

## PR handoff
- Branch `feat/08-analytics-performance-nizami` (shorten if preferred).
- Conventional atomic commits; open draft PR to `main`; use PR template; request human peer review.
- Do not change another owner’s directory or common contract without review and documented approval.
