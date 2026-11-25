# Final submission readiness

## Scope and ownership

[Spec 11, submission release gate](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/blob/main/context/specs/11-submission-release-gate.md).
Nijat led the final verification, source campaign and documentation. Base
`6c98a8f` includes [PR #11](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/11)
and its [passing PR checks](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45355202036).
Nizami owns review of the benchmark and index experiment. Firuz owns review of
Docker, scheduling and run-history evidence.

## Changes and measured outcomes

- Executed automated daily-window loading campaign across 2025 cohorts, safely
  resuming retryable checkpoints and reaching **1,033,290 distinct Bronze IDs,
  1,002,639 published Silver requests, 1,002,639 Gold facts and 410 quarantines**
  across 119 audited pipeline runs with zero synthetic records in the real database.
  The 1,000,000 genuine records target is **PASS**.
- Sampled 50 recently created non-closed requests against live Socrata endpoint.
  Accepted fresh views covered all 50 IDs on baseline generation `2026-11-24T02:42:04Z`
  with zero tracked differences. Database assertions verified 0 noncurrent real state
  versions. Genuine source-backed SCD2 remains PARTIAL.
- Reran performance benchmark on the full **1,002,639 genuine facts** snapshot across
  all five workloads (selective resolution + 4 analytics queries) with three warm
  `EXPLAIN (ANALYZE, BUFFERS)` executions each. The candidate agency covering index
  (49.8 MB) improved resolution-query median from **776.006 ms to 410.614 ms**
  (1.890× speedup ratio, 47.1% runtime reduction). All result row counts and SHA-256 digests
  matched identically before and after.
- Updated README, performance report, submission checklist, source tests, and real load evidence.
  Application ingestion, contracts, applied migrations, quality policy and
  publication code retain the merged baseline.

## Verification performed

- Clean Python 3.12.11 install using `pip install -r requirements-dev.lock`,
  `pip install --no-deps --no-build-isolation -e .` and `pip check`.
- `TEST_DATABASE_URL=… pytest -q` against disposable PostgreSQL 16.14.
  **273 passed** in a clean checkout and again on the feature worktree.
- `ruff check .`, `ruff format --check .`, `pre-commit run --all-files`
  (seven hooks), `bash scripts/validate-context.sh` and `git diff --check` passed.
- Isolated `docker compose up -d --wait db` and
  `docker compose --profile pipeline build pipeline` passed. UID 10001,
  migrations 0001–0004, health, checkpoint resume, replay and named-volume
  persistence verified.
- Fixture gate exited 4 for 2/20 invalid rows with identical published
  fingerprints. Scheduler wrapper published a successful incremental watermark.
  Prior actual SIGKILL, database startup and cron demonstrations are linked in
  the verification report.
- `python scripts/benchmark-analytics.py --apply-index --candidate agency` ran
  on a disposable final snapshot. The index experiment is separate from migrations.

[Final verification](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/blob/feat/final-submission-readiness/docs/final-verification.md)
[Performance report](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/blob/feat/final-submission-readiness/docs/performance-report.md)
[Evidence](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/tree/feat/final-submission-readiness/docs/evidence/final)

## Release assessment

**Release gate: NOT READY.** The following checks passed:
- ≥1,000,000 genuine published records (1,002,639 Gold facts, 1,033,290 Bronze IDs): PASS
- Measured optimization at 1M scale (1.890× speedup, 47.1% runtime reduction): PASS
- 3 failure recovery demonstrations, cron scheduling, star schema, migrations, idempotency: PASS
- Full unit & integration test suite, Ruff lint/formatting, pre-commit hooks: PASS

On 25 November 2026, main branch protection was verified (**PASS**) under
[ruleset 28075415](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/rules/28075415). CI was **PASS** for PR #12 head
`7d7872bf2a51268a6d51959c5bde4d70155df185` (lint, unit and integration). All three checks
must pass again on the documentation commit. [PR #12 CI](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45379091296)

Genuine SCD2 transitions remain **PARTIAL**, teammate reviews remain **NOT VERIFIED**,
and ADR-001 remains **PROPOSED**. See the [submission checklist](../submission-checklist.md)
for the remaining evidence gaps.
