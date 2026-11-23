# ADR-001 — Source API and cross-team contracts

**Status:** PROPOSED — Nijat must ACCEPT before work starts. **Date:** 2026-11-23.

## Decision proposal
Use NYC Open Data **311 Service Requests (2020 to Present)** dataset `erm2-nwe9`, Socrata JSON API `https://data.cityofnewyork.us/resource/erm2-nwe9.json`. Single public source satisfies source-count requirement when queried across sufficient range. Use keyset pagination over `created_date,unique_key`, persist cursor with bronze page, backfill UTC `[start,end)`, quality threshold 5%, stage then publish silver+gold atomically. SCD2 models **observed successive** `unique_key` attribute changes, not inferred historical versions.

## Must verify (Spec 01 smoke test)
- API endpoint available; dataset actually contains ≥1M usable real records in chosen span.
- Queryable stable `created_date`, `unique_key`; sort/cursor correctness; data dictionary; numeric vs string ID type; timezone.
- Rate limiting/token requirements, update behavior and possible deletion, `:updated_at` availability; decide rolling lookback for modified records.
- Tracked SCD2 fields that genuinely change on repeated pulls; if insufficient, propose stronger source-backed dimension before implementation.
- Allowed column names and privacy policy; no raw free-text in logs.

## Tradeoffs
Current-state API exports cannot reconstruct earlier status history. Dates backfill **creation dates**, not arbitrary prior versions. Full source may be large; stream pages and stage in PostgreSQL, never load all data in memory. No third-party paid account assumed; app token optional and secret by environment.

## Acceptance
Nijat edits this ADR to `ACCEPTED`, records API smoke-test findings and contract choices, then merges PR before dependent specs. If any assumptions fail, record alternate API and modify specs rather than patching behavior silently.

## Discovery evidence and provisional decisions — 2026-11-23

Status remains PROPOSED. The assignment was read; the human confirmed the analytical objective in `context/project-discovery.md`. See `docs/source-smoke-test.md` for successful metadata/count evidence and three failed HTTP 503 row probes. No contracts are frozen.

- Source metadata declares `unique_key` as text and event dates as `calendar_date` (floating timestamps). Preserve IDs unchanged and compare consistently as text; verify pagination ties before approval. Required analytical fields/types must be checked for incompatible drift; additive fields may be tolerated. Exclude addresses, coordinates and resolution free text from silver/gold by default; restrict bronze access.
- Prefer a bounded 2025 backfill: its live raw count was 3,655,759. Recount the exact approved range and eventually measure validated fact count. Backfill returns current representations of requests created in a range, not earlier snapshots.
- Retain proposed creation keyset `(created_date, unique_key)`, frozen upper bound and atomic bronze-plus-checkpoint commit. A frozen bound is not a source snapshot; sort-key corrections require reconciliation. Live ordering, ties, null keys and replay remain unverified.
- Prefer separate update keyset `(:updated_at, unique_key)` with a frozen update bound if supported and verified. Propose a configurable 48-hour overlap plus periodic reconciliation of the selected creation cohort. Compare tracked content, so metadata-only updates and full source replacements do not fabricate SCD2 versions. Reconcile identities separately; absence is not automatically deletion.
- If update metadata is unavailable, re-read the entire bounded analytical cohort in durable creation-date partitions. Disclose the cost/freshness tradeoff. A creation-date lookback alone misses old requests changing today and cannot be advertised as complete update detection.
- **Contract conflict to resolve:** source event dates have no offset while the current contract says UTC. Proposed interpretation is `America/New_York`, converted to UTC internally after publisher confirmation. Preserve source strings for pagination. Define UTC-window conversion and DST rules before freeze; never append `Z` blindly. Propose quarantine with reasons for ambiguous/nonexistent event times until a defensible interpretation is established. System update timestamps have separate fixed-timestamp semantics if available.
- Retain `dim_service_request_state`, natural key `unique_key`, tracking normalized status, agency and complaint type. Workflow/reassignment/reclassification changes are meaningful only when actually observed. Version boundaries use observation time; process observations chronologically and never promote stale observations. Identical replay creates no version. Retain non-overlapping half-open ranges and exactly one current row.
- One latest request fact references the current state version; preserve old versions for observed-history analysis. Do not infer pre-observation states or multiply fact counts by joining all versions. See `docs/data-model.md`.

Before acceptance, Nijat and Nizami must review timezone/DST and fact/state relationships; Firuz must review separate cursor scopes and checkpoint/history fields. Verify endpoint update queries, ordering and genuine tracked changes across repeated observations. These are explicit open review questions for the Spec 01 PR; no integration APIs are invented here.

References: [system fields](https://dev.socrata.com/docs/system-fields), [floating timestamps](https://dev.socrata.com/docs/datatypes/floating_timestamp), [tokens](https://dev.socrata.com/docs/app-tokens), [NYC dataset changes](https://www.nyc.gov/opendata/news/all-news/311-Service-Requests-Updates). System-field documentation warns that full replacement can update all row timestamps. Token documentation does not establish a guaranteed endpoint-specific quota; no deliberate throttling test was performed.

## Follow-up technical audit — recommendation remains DO NOT ACCEPT

The follow-up evidence in `docs/source-smoke-test.md` supersedes the earlier unavailable-query findings: bounded creation ordering/resume and equal-timestamp key comparisons succeeded; `:updated_at` selection, range filtering, ordering and an equal-update-timestamp resume also succeeded. This establishes query support, not complete incremental correctness or durable recovery. A deliberate invalid column returned HTTP 400, distinct from intermittent HTTP 503 and DNS failures.

Some successful responses explicitly reported `X-SODA2-Data-Out-Of-Date: true`; an identity observed in an unfiltered query was absent on direct lookup. Root cause remains unknown. Proposed conservative policy for review: never advance durable progress from a response explicitly flagged stale; retry boundedly, then fail the source phase without publishing. Capture request IDs and freshness markers; do not infer deletion from a single absent lookup. An absent freshness flag is not proof of snapshot consistency. Reconciliation remains required even with frozen update bounds.

Still blocked: publisher timezone/DST confirmation, reproducibility against sufficiently fresh source views across refreshes, verified update coverage semantics, a genuine tracked same-request attribute change, and lead/cross-owner approval of the final public contract. The service-request state SCD2 remains a candidate, not a demonstrated requirement pass. No historical status reconstruction or fulfillment-time claim is justified. [NYC's metric definitions](https://www.nyc.gov/site/311reporting/faq/faq.page) explain that closure measures agency-recorded closure rather than actual fulfillment.

Parallel foundation work is identified in `context/implementation-readiness.md`; current spec dependency gates remain effective until explicitly amended/approved. No source contract, infrastructure scope exception or ADR acceptance is inferred from successful small probes.
