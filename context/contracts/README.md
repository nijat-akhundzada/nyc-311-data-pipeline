# Integration contracts — version 0 (proposed; freeze in Spec 01)

Owners must inspect these definitions before coding. **Contract changes require Nijat's approval and cross-owner PR review.** Do not rely on undocumented module imports.

## CLI target
`python -m nyc311_pipeline run --mode incremental [--max-records N]`
`python -m nyc311_pipeline run --mode backfill --start 2025-01-01 --end 2025-02-01 [--max-records N]`
`python -m nyc311_pipeline health`
`python -m nyc311_pipeline report --run-id <uuid>`

`--max-records` is **demo/testing cap**, not a fabricated-source option. All times UTC. End is exclusive. Exit codes: 0 success, 2 bad configuration, 3 API failure, 4 data quality fail, 5 storage failure. These are target interfaces until implemented.

## Source payload
Socrata REST GET `/resource/erm2-nwe9.json`. Fields to verify: `unique_key`, `created_date`, `closed_date`, `agency`, `complaint_type`, `descriptor`, `status`, `borough`, `incident_zip`; `:updated_at` may be available as system metadata but **must be verified**. Preserve raw JSONB as received.

## Stable pagination
Use server-side `$where` plus `$order=created_date ASC,unique_key ASC` (stable typed cast where necessary), `$limit` bounded by config, and cursor predicate `(created_date > last_date OR (created_date = last_date AND unique_key > last_key))`. Include frozen `created_date < run_upper_bound` and backfill window. Do not use pure `$offset` for massive mutable datasets; verify semantics against actual API in a smoke test. Store cursor with run + scope, and atomic page durability semantics. If `unique_key` is represented as text, compare consistently as text or numeric after confirming types. Missing sort keys are quarantined or cause explicit fail as configured, never skipped silently.

## Interfaces (suggested Python protocols)
- `ApiClient.fetch_page(cursor, window, limit) -> Page(records, next_cursor, raw_http_metadata)`
- `BronzeRepository.commit_page(run_id, page, cursor) -> persisted_count` (atomic data+cursor)
- `Validator.validate(record) -> ValidRecord | Rejection(reason_codes, source_id, raw_record)`
- `QualityGate.evaluate(valid_count, invalid_count) -> PASS | FAIL`
- `SilverPublisher.publish(validated_stage, run_id, tx)`
- `GoldPublisher.publish(silver_scope, run_id, tx)`
- `RunTracker.start/heartbeat/checkpoint/finish` (persistent DB records)
- `PipelineRunner.run(mode, start, end, max_records) -> RunResult`

## Ops and SQL ownership
PostgreSQL schemas `bronze`, `silver`, `gold`, `ops` with migrations; `ops.pipeline_runs`, `ops.ingest_checkpoints`, `ops.quarantine`. Nizami designs DDL with Nijat and Firuz review. Fields needed: run UUID, mode/scope, status, attempted/accepted/rejected counts, cursor, started/finished timestamps, error category, heartbeat, source upper-bound. Do not duplicate checkpoint truth between owner modules.

## Publish transaction
Stage raw pages and validation result per run. Gate after evaluating the **entire selected run**; on pass, update silver, SCD2 and gold atomically under a DB transaction and commit the run as published. On fail, record quarantine + failed run, discard pending publish staging, leave prior silver/gold unchanged. At scale perform streaming validation and bounded staging rather than load 1M into RAM.

## Change detection
Gold SCD2 source natural key default `unique_key`, tracked fields e.g. `status`, `agency` and `complaint_type` with normalized hash. This models state history per service request rather than pretending to have true prior state snapshots: **the API's current data cannot retroactively reconstruct past states**. SCD2 changes only when successive observed API snapshots differ. Document this explicitly in final README.
