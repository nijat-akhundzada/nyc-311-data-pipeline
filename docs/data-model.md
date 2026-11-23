# Data model — DESIGN DRAFT ONLY

- `bronze.raw_service_requests`: immutable received payload/identity, ingestion batch metadata, dedupe fingerprint.
- `ops.ingest_checkpoints`: per scope cursor and frozen run bound.
- `ops.pipeline_runs`: status, mode, counts, start/finish, errors, restart marker.
- `ops.quarantine`: invalid raw record, reasons and run reference.
- `silver.service_requests`: normalized typed source fields, natural unique key and timestamps.
- `gold.dim_date`, `gold.dim_agency`, `gold.dim_service_request_state` (Type 2), `gold.fact_service_requests`: star model, 1 row per request at chosen grain; exact cardinality/join strategy finalized in Spec 05/06.

Spec 05 foundation (partial, lead-approved): ordered SQL migrations and a private
`_migration.applied_migrations` ledger now exist, and migration `0001` creates only
the four empty `bronze`, `silver`, `gold`, `ops` namespaces. No physical domain
table exists yet. Do not mistake the list above for an ERD of a running DB; see
`docs/spec05-foundation-verification.md` for executed checks.

The old `ops.run_history` name in the design note below conflicts with the lead's
canonical `ops.pipeline_runs` proposal. It remains unresolved: no run-history
table was created in the foundation scope, and the lead must approve the name
before any domain DDL.

## Discovery defaults — pending cross-owner review

Fact grain: exactly one latest published request per `unique_key`, an accumulating lifecycle fact with creation/closure timestamps, request count (=1), eligible elapsed resolution seconds and observation/run provenance. Calculate open age at a fixed observation cutoff. Proposed dimensions: date (creation and nullable closure roles), agency, complaint type, borough and service-request state (SCD2). Use explicit unknown members for missing optional categories. Physical DDL and keys remain Nizami's Spec 05/06 work.

State natural key is `unique_key`, tracking normalized status, agency and complaint type. Only genuine successive observed differences create versions. Validity is observation-time `[valid_from, valid_to)`, not inferred source-effective time, with exactly one current row. The latest fact references that current version; old dimension versions remain available for observed-history analysis. Historical classification must use the relevant state-version attributes rather than current agency/complaint classifications. Never join all state versions into request-volume aggregates.

SQL acceptance targets: daily/monthly volume and period change with CTEs and `LAG`; agency/complaint mean, median and p90 resolution with eligible counts; creation-cohort closure share at a fixed cutoff; closure-day throughput; open-age bands; ranked complaint volumes by borough using window ranking; observed state transitions explicitly limited to the observation period. Metric denominators and exclusions follow `context/project-discovery.md`. Official SLA, causal rankings and reconstructed pre-observation backlog are deferred.

## Spec 01 contract review note

Proposed version 1 at `context/contracts/README.md` supplies the logical field/normalization contract and requires durable run-to-raw associations even for duplicate raw versions. It also separates raw hashes (including source metadata) from tracked SCD2 hashes, canonicalizes operations history as `ops.pipeline_runs`, and defines stale/conflicting observation handling plus one publication transaction. This is a review proposal, not physical DDL or a change to Nizami's foundation scope. Genuine same-request source change evidence and publisher timezone/DST semantics remain missing; no SCD2 acceptance is claimed.
