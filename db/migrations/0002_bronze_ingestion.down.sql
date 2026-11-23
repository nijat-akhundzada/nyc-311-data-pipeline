-- Explicit destructive rollback only; never run automatically against real ingestion.
DROP TABLE ops.run_events;
DROP TABLE ops.run_records;
DROP TABLE ops.ingest_page_receipts;
DROP TABLE ops.ingest_checkpoints;
DROP TABLE bronze.raw_service_requests;
DROP TABLE ops.pipeline_runs;
DROP FUNCTION ops.protect_ingest_run_identity();
