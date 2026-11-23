# Project overview

**Deadline:** 2026-11-26 (teacher PDF). **Grading:** project 30% of course grade, team 60/100 and individual 40/100. **Team:** Nijat (lead/member 1), Nizami (member 2), Firuz (member 3).

## Requirements from assignment
One public API; Python ingestion with pagination, retries, rate-limit handling and restart cursor; quarantine invalid records with reasons; configurable failure threshold halting downstream publish; PostgreSQL bronze/silver/gold and gold star schema with genuine SCD Type 2; repeatable incremental and bounded historical backfill; ~1M+ records; optimization supported by measured `EXPLAIN ANALYZE`; killed-container/DB-not-ready/malformed-input demonstrations; scheduled pipeline and persisted run history; gold analytics with CTEs/window functions; multi-stage non-root Docker, health checks, named volumes; branch protection, peer-reviewed PRs, conventional commits, pre-commit/pytest/integration/CI; final report + documentation.

## Product scope
Primary analytical objective: analyze NYC 311 service-request volumes, resolution times, and service performance across agencies, complaint types, boroughs, and time. See `context/project-discovery.md` for discovery decisions and metric definitions.

Batch-only CLI/service, **no web UI**. Single selected API source: NYC 311 `erm2-nwe9`, retained by Nijat on 2026-11-23 with source-verification evidence still incomplete. Engineering acceptance, limited implementation permission and completed verification are separate decisions (ADR-001). CI must be green to merge. Bounded date-query support has sample evidence; complete incremental/backfill correctness remains to be demonstrated. **SCD2 must be driven by observed attribute changes**, never synthetic examples disguised as production data.

## Demo definition
Demonstrate first load, second identical replay, incremental change, date-range backfill, malformed-quality abort without gold changes, killed container resume, DB startup recovery, >=1M data rows, scheduled run, analytical SQL, and before/after performance timing. Capture measured evidence, not screenshots of aspirations.

## Explicit assumptions needing verification
- NYC Open Data endpoint and fields/quotas, sufficient volume for selected ranges, mutation/update semantics.
- Default gate threshold proposed as `invalid_count / evaluated_count > 0.05` (strictly greater; 0 records fails safely); lead can revise via ADR.
- SCD2 dimension proposed `dim_service_request_state` tracking state fields; lead validates historical change observation and meaningfulness in Spec 01. Alternative e.g. agency metadata **only if supported by real observed changes**.
