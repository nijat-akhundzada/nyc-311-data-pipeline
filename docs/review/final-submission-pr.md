# Final submission readiness

## Scope and ownership

[Spec 11, submission release gate](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/blob/main/context/specs/11-submission-release-gate.md).
Nijat led the final verification, source campaign and documentation. Base
`6c98a8f` includes [PR #11](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/11)
and its [passing PR checks](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45355202036).
Nizami owns review of the benchmark and index experiment. Firuz owns review of
Docker, scheduling and run-history evidence.

## Changes and measured outcomes

- Resumed `88f90c05-4851-44b6-8853-3a588118e198` from 10,000 retained rows and
  checkpoint page 2 on its original generation. It completed page 5 and
  published 13,341 requests. Continued independent daily windows through Jan 30
  UTC within the bounded campaign.
- Verified **299,204 distinct Bronze IDs, 277,791 published Silver requests,
  277,791 Gold facts and 86 quarantines** in the retained real-data volume.
- Sampled 268 previously published non-closed requests. Accepted views covered
  168 IDs from the baseline generation with zero tracked differences. Genuine
  source-backed SCD2 remains PARTIAL.
- Extended the existing benchmark to record three warm before/after plans for
  all four analytics queries. The optional agency covering index changed the
  resolution-query median from 138.489 ms to 94.929 ms. All result hashes match.
- Updated the README, evidence, performance report and requirement matrix.
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

**NOT READY.** The campaign ended 722,209 facts short of one million. Stale views
and HTTP 503s consumed source attempts within the finite budget. A publisher
snapshot suitable for restartable import remains unverified. No later-generation
SCD2 comparison was accepted. ADR-001 stays PROPOSED.

GitHub reported main unprotected and listed no active branch rules. Real human
review and feature-head CI are pending. Please reproduce one relevant check,
review the result for your ownership area and record feedback before merge.
