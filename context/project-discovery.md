# Project discovery — 2026-11-23

Status: discovery documented; no implementation authorization or completed Spec 01 implied.

## Product definition and users

Human-confirmed objective: analyze NYC 311 service-request volumes, resolution times, and service performance across agencies, complaint types, boroughs, and time. Build a local scheduled Python/PostgreSQL batch pipeline for student operators, SQL analysts and university assessors. The reviewed `docs/source-assignment.pdf` governs assessed requirements. Nijat owns ingestion/validation/silver/integration; Nizami owns storage/gold/analytics/performance; Firuz owns Docker/CI/scheduling/history/recovery. Shared contracts require lead and cross-owner review.

## Core journeys and measurable goals

1. Load a bounded creation-date range; replay with identical logical data and no duplicate state versions.
2. Synchronize new and changed existing requests; resume after the last durable page following interruption.
3. Preserve rejected records with reasons; failed quality gates expose no new silver/gold publication.
4. Query volume, closure performance and trends using CTEs and windows.
5. Reproduce at least one million real validated request facts, measured optimization, scheduled run history and all required recovery demonstrations.

Source counts are not loaded/validated fact counts. Completion requires database counts and measured evidence under the existing specs.

## Scope and defaults with rationale

- One API, batch CLI, local Docker Compose/PostgreSQL, environment secrets and operator-only access. No web UI, public hosting, user accounts or multi-tenancy; these add no value to the assignment.
- Candidate historical window: calendar 2025, whose live raw count exceeds the scale target. Recount the precise approved UTC-converted span. Use recent requests for repeated mutable-state observations. Limit scope rather than loading all history before the deadline.
- Bronze preserves received versions/provenance with atomic page checkpoints. Silver holds latest typed validated requests. Gold has one request fact and date, agency, complaint-type, borough and observed-state dimensions; see `docs/data-model.md`.
- Volume counts distinct request identities, never SCD2 rows. Resolution time is nonnegative elapsed creation-to-closure duration for closed requests with usable timestamps. Exclude open requests from duration denominators and report them separately. Missing closure on an open request is legitimate. Report closed requests with missing/invalid closure separately; finalize quarantine policy in Spec 04.
- Report mean/median/p90 duration, creation-cohort closure share and open age at a fixed observation cutoff, with denominators and freshness. These are descriptive measures; no official SLA or causal agency ranking is implied.
- Creation trends use creation dates; closure throughput uses closure dates. Historical daily backlog and exact pre-observation state history cannot be reconstructed from current-state exports and are deferred.
- Keep the proposed strict >5% invalid gate and safe failure on zero evaluated rows pending contract review. Stream/stage bounded batches; prefer measured indexes before partitioning. Use one lightweight scheduler and fixture-based CI tests.

## Constraints, unresolved decisions and next spec

See ADR-001 and the partial source report for evidence. Source timezone/DST, pagination ties, update metadata, rate-limit behavior and genuine repeated state changes remain unverified. No further product input is needed now; these require technical evidence and human acceptance of Spec 01. Do not accept ADR-001, freeze contracts or unblock downstream specs based on a count query alone. If genuine state changes cannot be observed, disclose missing SCD2 evidence rather than invent history.

Retain the existing overview, architecture, contracts, standards, workflow, build plan and traceability documents. Apply relevant backend-profile practices for transactions, idempotency, readiness and observability; frontend, microservices and SaaS profiles are unnecessary. Continue Spec 01 audit/decision workflow, then the existing dependency order and ownership. Target 24–25 November for approved implementation/integration and reserve 26 November for demonstrations/submission; this is a planning target, not a feasibility guarantee. Tracker completion remains unchanged.
