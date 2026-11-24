# Functional Bronze → Silver → Gold verification

Review branch `feat/functional-bronze-silver-gold-pipeline`, based on merged PRs #1–#8
at main `c0299e4`. The lead explicitly authorized this single integration branch.
No peer approval, merge, complete assignment or genuine source SCD2 change is claimed.
ADR-001 remains PROPOSED. See `context/contracts/functional-v1.md` for accepted engineering risks.

## Implemented and preserved

New forward migrations: 0003 validation stage/quarantine/frozen run settings and
quality counters; 0004 typed Silver, six Gold dimensions/fact and publication watermarks.
0001/0002 and the migration ledger/framework are unchanged. No new Python dependencies.
Existing API retries/freshness/query/cursors/receipts/CAS remain. Two backwards-compatible
integration additions: optional whole-run external lock in ingestion, and atomic
run-settings insertion in the existing Bronze begin_run transaction.

New modules: `validation/records.py`, `validation/staging.py`, `silver/publish.py`,
`gold/publish.py`, `orchestration/pipeline.py`, `cli.py`, `__main__.py`, and explicit
`testing/fixture_source.py`. Quarantine/staging and Silver/Gold writes are batched;
Python does not accumulate the complete production dataset. PostgreSQL WITH HOLD
cursors may use server-side temporary storage; million-row performance is not measured.

The canonical run table is still ops.pipeline_runs. One session advisory lock spans
extraction, validation and publication. A single transaction publishes Silver, Gold,
run success and incremental watermark; failure recording is a separate audit write.
Capped extraction stays paused/unpublished. Source generation changes fail rather
than reset checkpoints. Publication-commit uncertainty reports unknown and is resolved
by canonical run report/resume, never a claim that a connection error proves rollback.

## Actual tests

Environment: Python 3.12.11, shared locked pytest 9.2.0/Ruff 0.17.6, PostgreSQL 16.14,
Docker 28.5.1/Compose 2.40.3-desktop.1. Disposable DBs in isolated project
`nyc311-pr6-verify`, loopback port 55439. Test credentials are synthetic, never real secrets.

```sh
TEST_DATABASE_URL=<disposable-PG16-maintenance-DSN> pytest tests -q -ra
# 267 passed, 0 failed, 0 skipped: 202 unit + 65 PostgreSQL integration
ruff check .
ruff format --check .
PRE_COMMIT_HOME=<temporary-cache> pre-commit run --all-files
bash scripts/validate-context.sh
git diff --check
sh -n scripts/scheduled-run.sh
```

The final full suite passes. An intermediate run reported 1 failed/260 passed due
to a missing import in a newly added synthetic test; corrected to a plain dictionary
copy, then reran the focused case and complete suite. No skipped test is counted passed.

Coverage: valid/invalid timestamps/fields; exact 5% versus over-threshold; zero-input;
DST folds/gaps; quarantined raw payload/reasons; UTC outside-scope exclusion; fresh
load/replay; changed/reverted/all tracked attributes; unknown dimension members;
no duplicate facts or concurrent/current/overlapping state versions; stale/equal
source updates; publication failures after Gold and at the final success update;
watermark rollback; caps/resume and dataset-lock contention; CLI arguments/exit
codes/report/health; bounded startup retries. Complete published rows, not only counts,
are compared on failed publication. Original 227 tests are retained, with the original
0002 migration test explicitly scoped to its original two-migration boundary.

A 1,001-record synthetic test interrupts validation after 1,000 staged candidates:
that batch survives, Silver/Gold stay empty, and explicit resume publishes 1,001 facts
without re-fetching Bronze (three original page receipts). This proves bounded-batch
recovery mechanics, not assessment-scale throughput or a real killed-container drill.

## Dockerized fresh-database proof

The actual Compose pipeline CLI, UID 10001, was run against a freshly created
PostgreSQL database with explicit `/fixtures` read-only mounting. Dockerfile remains
multi-stage/non-root; only the new pipeline Compose profile was added.

```sh
docker build -t nyc311-functional:verify .
# On the isolated Compose copy / disposable database:
docker compose ... --profile pipeline run --rm pipeline migrate
docker compose ... --profile pipeline run --rm pipeline health
docker compose ... --profile pipeline run --rm pipeline run --mode backfill \
  --start 2025-01-01 --end 2026-01-01 --fixture /fixtures/valid.json
```

Actual initial proof:

- Health before migrations exits 5; migrate applies 0001–0004; health then exits 0.
- Valid fixture exits 0: **20 Silver, 20 facts, 20 observed state versions**, run
  succeeded/published. Identical new-run replay leaves published-row hashes unchanged.
- Quality-failure fixture exits **4**: **2 quarantined / 20 evaluated (10%)**;
  Silver/fact/state row hashes remain exactly unchanged. No partial publication.
- Cap 3 exits 0 with paused/incomplete/unpublished status. Explicit resume succeeds;
  facts/versions/hashes remain unchanged on this replay dataset.
- Initial incremental with explicit lower publishes one cohort watermark atomically.

This satisfies the required fresh-database deterministic end-to-end completion
criterion. Synthetic fixture states are **not** real historical source evidence.
Runtime logs/commands were retained under `/tmp/nyc311-functional-docker-proof.log`;
source payloads and real secrets were not logged or committed.

## Bounded real-source evidence

One real-source run used UTC cohort `[2025-01-15,2025-01-16)`, its conservative
New York wall-time superset, page size/cap **3**, existing ApiClient and a 15-second
outer live deadline. Actual result: **one HTTP attempt, HTTP 200, 3 received**, run
`f57dc0ca-aed3-42bd-8401-38fbbbb1a333`, paused, incomplete, **unpublished**.
No full real-source validation/publication or SCD2 transition is asserted. The
private disposable live database was removed and no raw source record entered Git.

## Delivery and remaining evidence

Separate conventional phase commits on one feature branch preserve all team history.
Remote CI must be checked after PR creation; local results are not GitHub Actions
success. If GitHub write access is unavailable, the comparison URL and comprehensive
PR description are provided rather than inventing a PR or green check.

Remaining: ~1M real validated facts; CTE/window analytics; measured EXPLAIN optimization;
real kill/DB-startup/cron-run demonstrations and deployment; source preflight and
fresh-view/change-capture/timezone confirmation; genuine same-ID SCD2 observations;
peer review, actual remote CI and submission. The cron example/wrapper is supplied,
not installed on the user's machine. API envelope/sort-key contract errors fail
before Bronze/staging; they are not represented as quarantined data-quality candidates.

Final rebuilt image re-ran the proof against fresh DB `nyc311_functional_demo_final`:
all expected exit codes and unchanged published-row hashes were verified again,
including resume of an already-published run. Image config ID:
`sha256:794bce3b2789f90177605924d7ad2eb61696b02c7d4f817a0a99423ac0227cc5`.
Final proof log: `/tmp/nyc311-functional-docker-proof-final.log`.

Final review added a missing-update sibling safeguard: an unorderable version is
retained for validation/quarantine rather than silently hidden by another dated
version of the same request. The PostgreSQL regression rejects the conflict,
retains both rejected payloads and publishes nothing. This is an additional
conventional correctness-fix commit after the five requested phase commits.

GitHub draft PR creation was attempted and returned HTTP 403 (resource not accessible
by integration). The GitHub CLI has no authenticated host. No Actions run was recorded
for the pushed implementation head; remote CI is unverified and human review remains
required. The prepared PR body is `docs/review/functional-pipeline-pr.md`.

The guarded final image also re-passed the complete fresh-DB Docker proof against
`nyc311_functional_demo_guarded`. `docker image inspect` returned image ID
`sha256:f74cc32c511b7d7a721d90e008ec85206adb1168d9efa976bb7baf5c32a19fd5`;
log `/tmp/nyc311-functional-docker-proof-guarded.log` ended with
`DOCKER_FRESH_DB_END_TO_END_AND_QUALITY_FAILURE_VERIFIED` (exit 0).
