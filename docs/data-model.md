# Implemented functional data model (review branch)

Migration 0001/0002 and their ledger/checkpoint framework are unchanged. New forward
migrations 0003/0004 extend that foundation; no prior applied migration is rewritten.

| Layer | Tables / grain |
| --- | --- |
| Bronze | `bronze.raw_service_requests`: one canonical JSON version per dataset/source ID/hash |
| Ingestion audit | `ops.pipeline_runs`, checkpoints, receipts, run_records, run_events |
| Configuration | `ops.run_settings`: immutable UTC cohort/quality/fixture/timezone policy per run |
| Validation | `ops.validation_stage`: one reduced latest candidate per run/source ID; valid, invalid or outside_scope |
| Quarantine | `ops.quarantine`: original payload/reference and sorted reasons, unique run/raw hash |
| Silver | `silver.service_requests`: one latest valid typed request per opaque source ID |
| Gold dimensions | `dim_date` (UTC creation/closure date roles), `dim_agency`, `dim_complaint_type`, `dim_borough`, `dim_service_request_state` |
| Gold fact | `fact_service_requests`: exactly one current request, eligible recorded-closure duration |
| Publication | `ops.publication_watermarks`: successful update upper per immutable UTC creation cohort |

Validation reduces each source ID to its greatest source-updated observation. Tied,
conflicting normalized versions abort. Python uses bounded batches and a PostgreSQL
WITH HOLD cursor; staging and quarantine writes are batched. Outside-scope valid
rows are audited/excluded from the quality denominator. Invalid candidates preserve
raw values/reasons. No descriptor/address/location/free text reaches Silver/Gold.

Event time is provisionally America/New_York using packaged pinned tzdata. Raw source
wall values remain available; folds/gaps are rejected, not guessed. Null categories
join a single unknown dimension member, without invented source labels.

State SCD2 tracks `(casefolded status, uppercase agency, trimmed complaint type)`.
Ranges are observed-time `[valid_from,valid_to)`; a PostgreSQL exclusion constraint
prevents overlaps, a partial unique index permits only one current version, and the
fact's composite FK ties state ID to the same request. Identical replay and metadata-only
updates create no version. Changed/reverted values require a strictly later actual
observation and newer source update. No pre-observation source history is reconstructed.

One transaction publishes Silver, all Gold data, run success and successful incremental
watermark. Failed gates/transactions cannot expose a partial run. Consumers needing
multi-query snapshot consistency should use repeatable-read. Raw, staged and quarantine
rows may survive failed publication for audit/recovery. No source disappearance deletes
a fact. Large-scale indexing/EXPLAIN and actual source transition evidence remain future work.
