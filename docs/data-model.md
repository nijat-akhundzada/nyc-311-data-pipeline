# Data model — DESIGN DRAFT ONLY

- `bronze.raw_service_requests`: immutable received payload/identity, ingestion batch metadata, dedupe fingerprint.
- `ops.ingest_checkpoints`: per scope cursor and frozen run bound.
- `ops.pipeline_runs`: status, mode, counts, start/finish, errors, restart marker.
- `ops.quarantine`: invalid raw record, reasons and run reference.
- `silver.service_requests`: normalized typed source fields, natural unique key and timestamps.
- `gold.dim_date`, `gold.dim_agency`, `gold.dim_service_request_state` (Type 2), `gold.fact_service_requests`: star model, 1 row per request at chosen grain; exact cardinality/join strategy finalized in Spec 05/06.

No physical tables or migrations exist yet. Do not mistake this file for an ERD of a running DB.

## Discovery defaults — pending cross-owner review

Fact grain: exactly one latest published request per `unique_key`, an accumulating lifecycle fact with creation/closure timestamps, request count (=1), eligible elapsed resolution seconds and observation/run provenance. Calculate open age at a fixed observation cutoff. Proposed dimensions: date (creation and nullable closure roles), agency, complaint type, borough and service-request state (SCD2). Use explicit unknown members for missing optional categories. Physical DDL and keys remain Nizami's Spec 05/06 work.

State natural key is `unique_key`, tracking normalized status, agency and complaint type. Only genuine successive observed differences create versions. Validity is observation-time `[valid_from, valid_to)`, not inferred source-effective time, with exactly one current row. The latest fact references that current version; old dimension versions remain available for observed-history analysis. Historical classification must use the relevant state-version attributes rather than current agency/complaint classifications. Never join all state versions into request-volume aggregates.

SQL acceptance targets: daily/monthly volume and period change with CTEs and `LAG`; agency/complaint mean, median and p90 resolution with eligible counts; creation-cohort closure share at a fixed cutoff; closure-day throughput; open-age bands; ranked complaint volumes by borough using window ranking; observed state transitions explicitly limited to the observation period. Metric denominators and exclusions follow `context/project-discovery.md`. Official SLA, causal rankings and reconstructed pre-observation backlog are deferred.
