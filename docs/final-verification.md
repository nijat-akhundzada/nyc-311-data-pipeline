# Final iteration evidence — 24 November 2026

**Branch-only evidence pending human review. Submission recommendation: NOT READY.**
Deadline 26 November 2026. Assignment source: [teacher PDF](source-assignment.pdf).
PR #9 is merged; this iteration uses the existing modular Python/psycopg system,
not a new ingestion framework. ADR-001 remains **PROPOSED**. No applied SQL migration,
shared dependency tooling, API freshness policy or publication contract was changed.

## Real source and publication

[Exact counts and canonical run history](evidence/final/real-load-counts.json).
Source: NYC Open Data dataset `erm2-nwe9`, all records genuine; **zero synthetic
rows in this database**. Dates below are UTC and end-exclusive. Bronze also
contains conservative wall-time padding and rows from failed extraction runs;
Bronze extraction is not evidence of downstream publication.

| Requested window | Run ID | Outcome | Received | Valid published candidates |
|---|---|---|---:|---:|
| 15 Jan 2025 17:00–17:05 | f9c17b1a-46c2-40f8-8597-104b08ede921 | succeeded | 2,495 | 43 |
| 1–8 Jan 2025 | 9d7e3f44-a216-48ef-98fd-b67bb48ad3eb | generation changed, exit 3 | 5,000 | 0 |
| 1 Jan 2025 17:00–18:00 | d49e9309-6c97-4347-ad49-6c2e8cb08951 | succeeded | 2,499 | 526 |
| 2–3 Jan 2025 | 2710fd95-db45-47ae-9bf4-f95a1524145b | succeeded | 14,827 | 12,557 |
| 3–4 Jan 2025 | a890d7cf-f0ac-4770-b968-3da7958e1004 | generation changed, exit 3 | 5,000 | 0 |

Small first publication elapsed about 9.35s from DB timestamps. Weekly attempt
31.586s, shorter-hour invocation 17.684s, successful day about 15.08s, final daily
attempt 17.251s. These are observed invocation/timestamp durations, not API latency
benchmarks. Page size 5,000; pages and staging stream in bounded batches through
existing durable checkpoints. No million-row Python buffer, duplicated source IDs
or generated scale data was used.

**Final source-only counts: 27,392 Bronze rows / 27,392 distinct source IDs;
13,126 Silver / 13,126 Gold / 13,126 distinct published IDs.** Gold metric-eligible:
13,003. Two real invalid candidates quarantined for `closed_before_created` in the
successful daily run (2/12,559, below 5%). No failed extraction published partial data.
All 13,126 real request states have only an initial observed version; **zero genuine
tracked transitions observed**. Synthetic transition tests do not satisfy that gap.

### Source blocker and bulk investigation

A three-row bounded initial source check accepted fresh matching generation
`2026-11-24T02:42:04Z`; all three exposed update metadata and validated. The weekly
and a subsequent daily full run failed on cross-page generation changes. Smaller
windows can succeed, but repeatable large extraction was not demonstrated. No
freshness checks were disabled, failing run was not force-resumed, and no watermark
was advanced by failed extraction. Client retries remain bounded (four attempts
for retryable transport/status/staleness); generation change is terminal and needs
a newly audited run. These tests do not demonstrate complete incremental capture,
source deletions or replacement semantics.

[Actual bounded HTTP requests and headers](evidence/final/source-headers-and-export.json)
include two one-row keyset views returning HTTP 200 **and**
`X-SODA2-Data-Out-Of-Date: true`; truth/secondary timestamps were 23 November.
Do not classify those responses as fresh merely because HTTP succeeded.

Official export investigated:
`https://data.cityofnewyork.us/api/views/erm2-nwe9/rows.csv?accessType=DOWNLOAD`.
A streamed request with Range returned 200 CSV, no confirmed byte-range support,
and stale=true. Only its first decoded chunk (56,346 bytes) was inspected, then
the stream closed; no bulk dataset downloaded. Response also advertised a
22 December 2026 sunset and a publisher deprecation link; inspect it before future
use. **Fallback not production-ready:** a complete immutable official export could
avoid cross-page source views, but requires a separately reviewed manifest/checksum,
metadata/update compatibility and restart contract. Current export freshness and
snapshot semantics are unverified. No unreviewed CSV adapter was added merely to
reach scale. Keep real load evidence; retry bounded backfills when fresh stable
views return, or obtain publisher guidance/approved immutable export. Million-row
requirement remains unmet, rather than manufacturing successful validation.

## Executed independent requirements

- Four analytical CTE/window queries and meaningful PostgreSQL assertions:
  [analytics](../sql/analytics/README.md).
- Real plans and three comparable timings each phase, modest 1.160× full-day ratio;
  slower sparse experiment retained: [performance](performance-report.md).
- Actual container SIGKILL/resume, bounded DB outage recovery and failed 10% batch
  with identical published hashes: [recovery](failure-recovery-report.md).
- Actual cron-triggered, fixture-backed successful incremental with canonical
  timestamps; temporary entry removed: [scheduling](scheduling-evidence.md).
- Fresh image built successfully; UID **10001**. Fresh drill DB migrated 0001–0004
  and published 20 synthetic facts; replay stable; volume survived DB stop/restart.
  PostgreSQL **16.14**. Real and drill projects/volumes are distinct.

## Reproduce Docker isolation

The existing Compose file uses fixed names. To protect a running project, make a
copy outside Git and set unique project/container/volume names and host ports,
absolute build context and absolute fixture bind source. The verification copies
were `/tmp/nyc311-final/real.yaml` and `drills.yaml`; protected local `.env` files
held throwaway credentials and were never committed. Preserve the named real-data
volume `nyc311_final_real_data`; drill volume is `nyc311_final_drills_data`.

```sh
docker compose -p nyc311-final-real -f /tmp/nyc311-final/real.yaml \
  --env-file /tmp/nyc311-final/real.env up -d --wait db
docker compose -p nyc311-final-real -f /tmp/nyc311-final/real.yaml \
  --env-file /tmp/nyc311-final/real.env --profile pipeline run --rm pipeline health
# Use the same prefix for report/run. Omit --fixture for genuine source requests.
```

These temporary absolute paths describe this execution environment; a fresh
checkout must create its own isolated configuration. Do not `down -v` the real
project or reuse someone else's PostgreSQL port/volume. Recovery scripts require
explicit disposable consent and a fresh DB; see their report for environment names.

## Verification commands and actual local results

Python 3.12.11, pinned development dependencies in an external temporary venv.
`TEST_DATABASE_URL` referenced the disposable PostgreSQL 16 maintenance database;
each integration test creates/drops its own UUID-named DB. No live network tests.

```sh
pytest -q
ruff check .
ruff format --check .
pre-commit run --all-files
bash scripts/validate-context.sh
sh -n scripts/scheduled-run.sh
git diff --check
```

Full suite: **268 passed, 0 failed, 0 skipped** (202 unit / 66 integration),
24.58s on the first run; final rerun **268 passed in 24.40s**. Ruff lint/format,
all seven pre-commit hooks, shell syntax, context and whitespace checks passed.
Local success must never be represented as GitHub Actions success. Existing CI selects all `tests/unit` and
`tests/integration`, including the new analytics test. Destructive manual drills
are intentionally outside CI.

## Remaining release gates

One-million genuine records and scale benchmark, genuine observed source SCD2
transition, full publisher/timezone/update semantics, substantive cross-owner peer
reviews, verified main protection and final-head green GitHub Actions remain
separate gates. Only the human lead declares submission ready. See
[submission matrix](submission-checklist.md) and [contribution evidence](contributions.md).

## Remote delivery result

Feature branch pushed successfully with upstream tracking. Draft PR creation via
the GitHub connector returned **403 Resource not accessible by integration**;
`gh auth status` confirmed no authenticated GitHub CLI. No PR URL or review is
invented. GitHub Actions queries for code/documentation head `5a81439` and the
branch returned **zero runs**. The workflow triggers PRs to main and pushes to
main; a feature push alone does not trigger it. Final-head CI is **NOT VERIFIED**.

Open the [prepared comparison](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/compare/main...feat/final-analytics-recovery-submission?expand=1)
and create a **draft** PR targeting main using
[the prepared title/body](review/final-submission-pr.md), or after authenticating:

```sh
gh pr create --draft --base main --head feat/final-analytics-recovery-submission \
  --title 'feat(submission): add measured analytics and verified recovery evidence' \
  --body-file docs/review/final-submission-pr.md
```

Then inspect all lint/unit/integration Actions jobs on the latest head, fix actual
failures through normal feature commits, and obtain Nizami/Firuz review. Do not
merge automatically or interpret local results as remote CI success.
