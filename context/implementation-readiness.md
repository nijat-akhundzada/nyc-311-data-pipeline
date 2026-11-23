# Implementation readiness — 2026-11-23

Status: planning handoff only. ADR-001 remains PROPOSED. No pipeline code, migrations, Docker configuration or CI jobs were implemented. The university assignment remains the assessment source of truth. Existing Spec 02/05 dependencies still require accepted Spec 01; the partial splits below are proposed amendments, not blanket implementation approval.

## Ready for bounded independent preparation

| Owner | Exact first tasks | Boundary and evidence |
|---|---|---|
| Nijat | Extend the successful small creation/update tie-boundary checks across sufficiently fresh source refreshes; investigate the identity/freshness discrepancy; resolve timezone/DST; retain a small redacted repeated-observation log across daily refreshes | Keep ADR proposed until evidence/review; no production ingestion implementation. Distinguish API tests from DB crash-resume proof. |
| Firuz | Prepare Spec 02 foundation scope: Python 3.12 package/tooling plan, ruff/pre-commit, fixture-only pytest/CI job design, multi-stage non-root image and Postgres health/volume design | All can be designed without source semantics. Following explicit approval of the split, implement tooling and Postgres-only Compose/test infrastructure; do not invent working pipeline health/CLI or schedule behavior. Coordinate pyproject/lock ownership with Nijat/Nizami. |
| Nizami | Prepare Spec 05 foundation scope: PostgreSQL 16 migration runner choice, isolated temporary-DB test plan, empty bronze/silver/gold/ops namespace migration design | Following explicit approval of the split, implement migration framework and namespace-only initial migration with fresh/repeat/rollback checks. Run-history/bronze/checkpoint/quarantine tables require reviewed shared field/naming/transaction contracts first. |

Practical defaults to review: psycopg 3 plus a small ordered SQL migration runner with a migration ledger/advisory lock; avoid adding an ORM solely for migrations. Keep one dependency lock owned through Spec 02. These are recommendations, not accepted ADR choices. Infrastructure tests need PostgreSQL/Docker, not the live public API.

## Blocked implementation

- Full Spec 02 acceptance includes an actual application healthcheck; do not claim that part before a real entry point exists.
- Spec 03 API synchronization depends on verified creation/update ordering, source consistency policy, UTC conversion and reviewed cursor contracts. Durable crash-resume is a later integration test, not demonstrated by HTTP pages.
- Source-specific bronze dedupe, checkpoint schema and typed silver DDL in Spec 05 require frozen shared semantics. Silver publication (04), gold/SCD2 (06), orchestration/history (07), analytics/performance (08), recovery (09) and integration (10) retain existing dependencies.
- Genuine SCD2 evidence needs the same request observed changing tracked attributes across real snapshots. Different requests with different statuses, advancing system metadata and disappearance alone do not meet that requirement.

## Required specification amendments before work assignment

1. Amend 00/02/05 with explicit foundation-only dependency exceptions if the lead approves parallel implementation. Keep one PR per assigned spec and separate partial versus full acceptance; do not globally remove Spec 01's gate. This document identifies safe work but does not approve those exceptions.
2. Correct Spec 05 task 3: `ops.run_history` conflicts with lead-controlled contracts/architecture naming `ops.pipeline_runs`. Resolve in the reviewed Spec 01 contract; do not create both names.
3. Expand Spec 01 acceptance to explicitly cover text-key ties, source freshness headers, update-cursor filtering, exact timezone/DST rules and genuine repeated-observation evidence. Keep unsupported/unverified outcomes visible.
4. Update Spec 03 and contracts after approval with distinct creation/update/reconciliation scopes, overlap/frozen bounds, out-of-date response policy, bounded transient-error retry and non-snapshot limitations. Never persist progress for a DNS/HTTP failure.
5. Refine Specs 04/06/08 after contract review with metric eligibility, observation-time validity, one-current-version joins and closure-time limitations. Close time measures agency-recorded closure, not independently verified fulfillment.

## Source fallback and deadline

If live source remains unreliable, stop repeated probing, retain request IDs/timestamps and retry later with bounded backoff or an optional environment token; do not use token acquisition as proof of correctness. Use deterministic fixtures to build approved infrastructure. A bounded full reconciliation of the selected cohort is a candidate fallback if update extraction is unsupported; quantify its cost before adoption. A dated official export from the same source can support a backfill if provenance is recorded, but cannot establish live incrementals or genuine prior state history. Alternate-source adoption needs a new evidence-backed decision; no second API is silently added.

Target 24–25 November for approved implementation/integration and 26 November for demonstrations/submission. Escalate missing source/SCD2 evidence promptly rather than fabricate compliance or claim all remaining work will fit.

## Local Git and GitHub handoff

Git was already initialized on unborn `main`; no remote was configured. The requested initial conventional commit establishes the reviewed scaffold and discovery baseline locally. No remote creation/push or branch-protection action is authorized without an explicit destination. Future changes use feature branches and human review. After the human provides a destination, inspect it before adding `origin`; publish only as explicitly authorized and configure required lint/unit/integration checks when those jobs actually exist.
