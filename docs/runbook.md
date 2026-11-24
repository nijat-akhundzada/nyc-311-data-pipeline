# Functional pipeline runbook

Commands validated with synthetic fixtures and bounded real publication on PostgreSQL 16.
Initialize Docker/local credentials as shown in README; fixtures must use a disposable DB.

## Commands

The Compose `pipeline` service runs as UID 10001 and invokes `python -m nyc311_pipeline`.
It waits for PostgreSQL health; CLI connection retries are bounded to three attempts.

```sh
docker compose --profile pipeline run --rm pipeline migrate
docker compose --profile pipeline run --rm pipeline health
docker compose --profile pipeline run --rm pipeline run --mode backfill \
  --start 2025-01-01 --end 2026-01-01 --fixture /fixtures/valid.json
```

Host equivalent: export `DATABASE_URL`, then use `python -m nyc311_pipeline` with the
same arguments (fixture paths are relative to the host checkout, e.g. `fixtures/valid.json`).
`migrate` automatically finds repository or image SQL assets. Never rewrite applied SQL.

Date-only bounds are UTC midnight. Offset-aware ISO bounds are accepted; naive datetime
bounds are rejected. A conservative wall-time superset is fetched; exact UTC eligibility
is checked during validation. Ambiguous/nonexistent New York events quarantine rather
than being guessed away. Valid outside-scope records are audited, not quality candidates.

`--page-size` is 1..5000. `--max-records N` caps newly received rows per invocation;
paused extraction has `ingest_complete=false,published=false` even if its last page
was short. Only a fresh accepted empty page proves exhaustion. Re-run with
`run --resume-run-id UUID` and the same fixture when applicable. Source bounds,
page size, fixture hash, timezone version and threshold must remain unchanged.
`report --run-id UUID` shows canonical status, counters, timestamps and checkpoint summaries.

Incremental: `run --mode incremental --start ... --end ... --initial-lower ...`.
The first run requires the explicit UTC update lower bound; subsequent invocations
omit it and use the cohort's successfully published upper minus 48 hours. Upper is
frozen at run start minus five minutes. Backfill does not fabricate an update watermark.
A zero-candidate incremental fails the required zero-input gate and advances nothing.
Use periodic complete bounded backfills as reconciliation; never infer deletions.

## Outcomes and recovery

Exit 0 means an invocation completed: inspect `published` and `ingest_complete` to
distinguish capped pause from successful publication. Exit 2 is configuration/conflict,
3 source/transport/freshness/order, 4 quality/source-observation conflict, 5 storage/migration.
Storage/commit uncertainty reports `published=null,status=unknown`; resolve with `report`
after DB recovery, never assume rollback solely from a connection exception.

The same dataset advisory lock covers extraction, validation and publication. A second
run is rejected; unfinished functional work requires explicit resume. Session loss
releases the lock. Source generation changes are terminal; start a new audited run
with the same frozen cohort after reviewing source consistency. Quality failure leaves
Bronze/quarantine and prior Silver/Gold intact. Corrected data requires a new run.
Retryable publication failure resumes retained Bronze/staging without re-fetching it.
Successful-run resume reports its existing result and does not publish again.

Default invalid threshold is 0.05. `--quality-threshold` or `QUALITY_MAX_INVALID_RATE`
sets it for new runs; the frozen value wins on resume. Exactly 5% passes, greater fails,
zero evaluated fails; conflicting equal source updates always fail regardless of percentage.
Status `Closed` without closure remains valid for volumes but metric-ineligible.

## Cron

After one successful incremental, configure `COHORT_START`/`COHORT_END` and adapt
`docker/scheduler.crontab.example` to the actual checkout. The executable
`scripts/scheduled-run.sh` invokes the same non-root Compose CLI. Cron time uses the
host's timezone; choose deliberately. A temporary actual host cron invocation was demonstrated with explicit synthetic
fixtures and removed; existing jobs were preserved. Production installation remains
a deliberate deployment step. Interrupted/capped/retryable work must be resumed
explicitly before new triggers. See `docs/scheduling-evidence.md` for exact run
metadata and install/inspect/disable commands. Never set SCHEDULE_FIXTURE for a
production source run.

Schema preflight, provider snapshot/update/deletion semantics and genuine SCD2 evidence
remain open in ADR-001. See `docs/functional-pipeline-verification.md` for actual results.

## Final iteration evidence

See [final verification](final-verification.md) for real windows and counts,
[analytics](../sql/analytics/README.md), [measured plans](performance-report.md),
[executed recovery](failure-recovery-report.md) and
[release gates](submission-checklist.md). Source generation changes terminate a
run without publication; start a new audited bounded window only after reviewing
source freshness. Never remove the generation check merely to reach the volume target.

## Lead-approved stale retry and scale operations

Explicitly stale/lagging responses are now rejected within the existing four-attempt
page budget before generation comparison. A **fresh** mismatching generation still
terminates extraction. Do not change the pin, accept old pages, increase the page
limit beyond 5,000 or rewrite a terminal failure to make a load complete.

Use bounded independently completed UTC creation windows, e.g. one day at a time:

```sh
python -m nyc311_pipeline run --mode backfill --start 2025-01-08 \
  --end 2025-01-09 --page-size 5000
python -m nyc311_pipeline report --run-id UUID
# Only when that canonical run is retryable and source freshness permits:
python -m nyc311_pipeline run --resume-run-id UUID
```

The measured operator batch allows at most one separate explicit resume per
retryable window, then stops on another failure; it does not introduce a new
production runner/retry framework. Resuming retains the original cursor/settings/
pin and may receive only the empty completion page. Do not count HTTP retries,
page receipts, failed-run Bronze or replayed IDs as extra published facts. Inspect
`count(DISTINCT unique_key)` and Gold/Silver counts, plus quarantine. Keep the
source-only database/volume separate from all synthetic Docker demonstrations.
