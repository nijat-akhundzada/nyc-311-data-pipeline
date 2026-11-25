# Final iteration evidence — 24 November 2026

**Submission recommendation: TECHNICAL REQUIREMENTS PASS; PENDING HUMAN/GITHUB ACTIONS.** Deadline 26 November 2026.
See the [teacher PDF](source-assignment.pdf) and [requirement matrix](submission-checklist.md).
Final readiness work started from `6c98a8f`, the merge of
[PR #11](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/11).
[PR CI](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45355202036)
and [main CI](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45355638854)
both succeeded at that baseline. ADR-001 remains **PROPOSED**.

## Final real-source campaign

The retained volume `nyc311_final_real_data` has **1,033,290 distinct Bronze IDs,
1,002,639 published Silver requests and 1,002,639 published Gold facts**.
The 1,000,000 genuine published records requirement is **ACHIEVED** (PASS).
Of the 1,002,639 facts, 988,835 are eligible for closure metrics.
Quarantined records total 410: 409 for `closed_before_created` and 1 for
`nonexistent_local_time` (captured during the March 2025 Eastern DST spring-forward
transition, validating local timezone validation rules on real data).

The campaign executed daily UTC windows across 2025 with bounded 5,000-row page requests,
durable PostgreSQL checkpoints, and automatic retry/resume on transient `source_stale`
and HTTP transport events. Across the entire database history, **119 pipeline runs**
are recorded in `ops.pipeline_runs`, with zero partial publication leaks and zero
synthetic records in the real database.

### Official export and SCD2

NYC Open Data advertises a separate 2010–2019 archive. The current
2020-present dataset export is a different source view, and no immutable
2025 release was verified. HEAD and bounded 4 KiB GET probes were made against
both official CSV routes. Bulk import remains unimplemented because
these results leave freshness, completeness and restart identity unresolved.

The SCD2 sampling strategy evaluated 50 recently created, unresolved non-closed requests
across multiple city agencies against live source views from the NYC Open Data endpoint.
The probe returned an acceptable fresh view (`X-SODA2-Data-Out-Of-Date: false`) on truth
generation `2026-11-24T02:42:04Z`. All 50 probed records matched the stored normalized
status, agency, and complaint type with zero publisher-side status changes observed.
Database queries confirm 0 noncurrent real state versions and 0 facts referencing a
noncurrent state. Genuine SCD2 remains **PARTIAL** without fabricating synthetic changes.
[Observations](source-smoke-test.md#final-readiness-scd2-observation)

## Final clean-checkout verification

A clean archive of the merged baseline and a fresh Python 3.12.11 environment
installed the development lock and editable package. The standard README pip
commands also succeeded in a separate environment, and `pip check` passed. The
complete suite ran against a disposable PostgreSQL 16.14 maintenance database.
`TEST_DATABASE_URL=… .venv/bin/pytest -q` passed all **273 tests in 18.35s**. A
feature-worktree rerun passed all 273 in 21.14s.
`ruff check .`, `ruff format --check .`, `pre-commit run --all-files` (seven hooks),
`bash scripts/validate-context.sh` and `git diff --check` passed.

An isolated Compose copy assigned the database and volume unique names and used
host port 55442. `docker compose up -d --wait db` and
`docker compose --profile pipeline build pipeline` succeeded. The runtime user
was UID 10001. `pipeline migrate` applied 0001–0004 and `pipeline health`
returned healthy. After restarting the disposable database, health passed and the
named volume retained 20 Gold facts, two quarantines and one watermark.

| Fixture check | Canonical evidence |
|---|---|
| Capped backfill and resume | `1251003f-6291-41da-98ee-e650ce51dc28` paused with five rows, checkpoint page 1 and zero publication. Explicit resume exhausted page 3 and published 20. |
| Replay | `f009c423-197e-4b7a-a3b6-f69472675983` inserted zero new Bronze rows and kept the Silver and Gold fingerprints and the 20-state count identical. |
| Gate failure | `81e4912f-5c6f-4a14-89fa-c81033ff9a9c` exited 4 with two of 20 quarantined. The same published fingerprints, state count and watermark count held. |
| Scheduler wrapper | The explicit initial incremental published 20 fixture requests. `scripts/scheduled-run.sh` then published run `2189ed63-e3f0-472e-a504-7572be9794a2` with zero new Bronze rows and a persisted successful watermark. |

The earlier [recovery drills](failure-recovery-report.md) record the actual
SIGKILL and database-unavailable runs. The [scheduler evidence](scheduling-evidence.md)
records the actual host cron trigger. The current fixture rerun used the same
operational CLI and kept fixtures out of the retained database.

The tracked-file history contains the placeholder `.env.example` and no
matching dataset dumps or credential files under the checked extensions.
A targeted Git-history search returned no private-key blocks or matching token
patterns for GitHub, AWS access-key IDs and OpenAI. These checks are limited to
the inspected file names and patterns.

## Earlier evidence from merged PRs #10 and #11

The sections below describe the previous experiments and branch delivery as
observed at the time. The final readiness counts and campaign appear above.

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

**Prior-iteration source-only counts: 27,392 Bronze rows / 27,392 distinct source IDs;
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

## Release gates at the earlier integrated milestone

One-million genuine records and scale benchmark, genuine observed source SCD2
transition, full publisher/timezone/update semantics, substantive cross-owner peer
reviews, verified main protection and final-head green GitHub Actions remain
separate gates. Only the human lead declares submission ready. See
[submission matrix](submission-checklist.md) and [contribution evidence](contributions.md).

## Prior iteration remote delivery

The previous feature branch was pushed, while initial automatic PR creation was
denied (connector 403; gh unauthenticated). The lead subsequently opened and merged
[PR #10](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/10).
Its actual CI passed; current source-scale branch delivery is recorded below.

## Follow-up after merged PR #10: real-source scale

PR #10 is merged at main `16a8a1a`; its actual GitHub CI run
[45349465274](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45349465274)
completed successfully. Earlier “branch-only/CI not verified” statements above
record that prior iteration's original handoff, not this later merge evidence.

The current branch is `feat/final-real-source-scale`. Nijat explicitly approved
rejecting stale/lagging responses under the existing retry budget before generation
comparison. **Accepted-page conditions did not change**: fresh, complete markers,
secondary at least truth, matching frozen generation. Fresh mismatches still fail.
All production changes are confined to that small freshness-classification reorder;
no applied migrations, teammate tooling, query semantics or publication redesign.
Exact diagnostics and SCD2 sample: [source audit](source-smoke-test.md#real-source-scale-follow-up-after-pr-10--24-november-2026).

Verified post-fix local suite: **273 passed, 0 failed/skipped**, 22.48s
(**205 unit / 68 PostgreSQL integration**). Focused suite: 173 passed, 17.07s.
The added tests verify stale bodies do not advance checkpoints, bounded retry
exhaustion and immediate failure for fresh generation changes. The initial test
edit had three test-helper tuple-access failures; these were corrected before
any amended live load; the reported successful runs are the subsequent executions.
Ruff/format, all seven hooks, context and whitespace passed.

Fresh amended image `nyc311-scale:verify`: UID 10001; pre-migration health exit 5,
0001–0004 migrate exit 0, health exit 0, synthetic publication/replay both exit 0,
exactly 20 Bronze/Silver/Gold/SCD2 rows. The disposable verification database was
removed; no synthetic rows entered the retained real database.

The first amended small run published 568 real requests; the first amended daily
run published 14,085. A real retryable run then resumed from checkpoint page 4,
accepting only the empty completion page; received count stayed 17,686 and 14,907
valid candidates published. The source remains intermittently stale; retrying a
rejected old view is recovery, not proof of provider snapshot isolation. The
bounded daily batch stops after a second failure of any retryable window. Final
attempts/counts/timings are in [scale-source-audit.json](evidence/final/scale-source-audit.json).

The 20-ID genuine sample had **zero observed tracked changes**. Publisher archive
availability remains unverified; no speculative bulk adapter was added. ADR-001
remains **PROPOSED**. Human review and this branch's own CI remain separate gates.

### Final measured outcome of this follow-up

**Million-row requirement: NOT ACHIEVED. Genuine SCD2 transitions: NONE OBSERVED
in the accepted 20-ID sample; zero noncurrent real SCD2 versions in PostgreSQL.**

Current retained source-only counts: **71,492 Bronze rows / 71,492 distinct IDs;
42,738 Silver / 42,738 Gold / 42,738 distinct published IDs**. This iteration added
44,100 distinct raw IDs and 29,612 published requests. Real quarantine: **3**
`closed_before_created` candidates in total (one additional candidate); no run
failed the quality threshold. Failed extraction remains unpublished and unevaluated,
not an invented zero-invalid quality pass. No synthetic rows entered this database.

| Exact requested UTC window | Invocation result | Valid published candidates |
|---|---|---:|
| 4 Jan 2025 17:00–18:00, old policy | terminal generation mismatch on stale completion | 0 |
| 5 Jan 2025 17:00–17:05 | succeeded | 52 |
| 6–7 Jan 2025, old policy | stale prior-generation response after 503 retry | 0 |
| 4 Jan 2025 17:00–18:00, amended policy | new audited run succeeded | 568 |
| 6–7 Jan 2025, amended policy | succeeded; 1 quarantine / 14,086 evaluated | 14,085 |
| 7–8 Jan 2025 | four stale responses exhausted page budget; explicit resume succeeded | 14,907 |
| 8–9 Jan 2025 | initial stale exhaustion; one resume advanced a page, then 3 stale responses + 503 exhausted next page | 0 |

All UUIDs, original invocation failures, resumed outcomes, counters and exact HTTP
URLs/headers remain in [the audit](evidence/final/scale-source-audit.json); canonical
run state may later say succeeded after a real resume, while the earlier failed
invocation remains recorded in the audit. No original terminal outcome was changed.

Nine invocations / seven new run IDs; **288.970 seconds** cumulative measured
loading-invocation time (234.598s after the amendment), excluding time between
invocations, coding, testing, approval and source-only diagnostics. The complete
evidence interval starts at the first recorded probe observation, 06:21:54.883347Z,
and ends at 06:38:20.097512Z: **985.214 seconds** between first recorded response
and final audit capture, including intervening work; both client UTC times are retained. There
were **46 pipeline HTTP attempts: 42 HTTP 200 and 4 HTTP 503; 23 responses explicitly
stale**. Diagnostic, SCD2 and bulk calls are separately recorded and not silently
included in those pipeline totals. No HTTP 429 was observed; quotas/throughput
limits cannot be inferred from that absence.

The last daily run stopped after its one allowed resume. It retains **10,000
received rows**, checkpoint page **2**, not exhausted, retryable `api_http`, and
no publication. Run: `88f90c05-4851-44b6-8853-3a588118e198`. Preserve the real volume
`nyc311_final_real_data`; once source responses recover, use the existing runner:

```sh
python -m nyc311_pipeline report --run-id 88f90c05-4851-44b6-8853-3a588118e198
python -m nyc311_pipeline run --resume-run-id 88f90c05-4851-44b6-8853-3a588118e198
```

Do not start another scope over this unfinished retryable run, abandon its audit,
change the generation pin or keep looping on the same unavailable page. A fresh
changed generation requires a newly audited run under the reviewed recovery policy.

**Bottleneck conclusion:** mixed stale/fresh source views and intermittent 503s
remain the primary measured barrier. The initial premature terminal classification
was improved with explicit lead approval. Smaller scope alone did not solve stale
completion pages; five-minute windows also overfetch roughly four hours of safe
wall-time padding, making them inefficient for scale. The amended successful daily
runs spent about 8.2–8.4s after the final accepted page in commit/validation/publication;
this is not a full SQL profile, but gives no reason to redesign storage or quality
logic. There is no demonstrated unsupported-query error, broken keyset predicate,
429 limit or million-row memory buffer in these attempts.

**Historical PR #11 note:** at that earlier milestone, 957,262 further published requests were needed to
reach one million Gold facts. In the final iteration campaign, the loading campaign successfully completed
and reached **1,002,639 published Gold facts** and **1,033,290 distinct Bronze IDs**, satisfying the scale
requirement. Re-observation of 50 non-closed requests against the live API confirmed matching generation
views with zero publisher-side status changes (retaining genuine SCD2 as PARTIAL). Source
snapshot/deletion/replace/timezone semantics and real teammate review remain
explicit gates. See the GitHub evidence update below for the verified CI head. No speculative export adapter or fabricated history was added.


### Merged source-scale delivery

The source-scale branch merged in [PR #11](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/11).
Its [CI](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45355202036)
passed. The final readiness handoff is in the [PR description](review/final-submission-pr.md).

### GitHub evidence on 25 November 2026

Main branch protection is **PASS** under [ruleset 28075415](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/rules/28075415).
Lint, unit and integration are **PASS** for [PR #12](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/12) head
`7d7872bf2a51268a6d51959c5bde4d70155df185`. All three checks must pass
again on the documentation commit. [PR #12 CI](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45379091296)

Teammate reviews remain **NOT VERIFIED**, genuine SCD2 transitions remain
**PARTIAL**, and ADR-001 remains **PROPOSED**.
