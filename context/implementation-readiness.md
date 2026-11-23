# Implementation readiness — 2026-11-23

Status: foundation-only implementation authorized by the lead on 2026-11-23 through amended Specs 00/02/05; no implementation performed here. ADR-001 remains PROPOSED. The university assignment remains the assessment source of truth. Full Spec 02/05 acceptance and all source-dependent work retain their existing gates. The preparation notes below are superseded by each amended spec's explicit foundation boundaries and acceptance checklist.

Current review note: PR #1's foundation documentation is merged. PR #3 separately proposes a client-only Spec 03 exception; it remains inactive until human review/approval/merge and tooling coordination. The full integration blockers below are unchanged; see Specs 00/01/03 and `docs/spec01-contract-review.md` for the conditional slice and actual approval record.

## Ready for bounded independent preparation

| Owner | Exact first tasks | Boundary and evidence |
|---|---|---|
| Nijat | Extend the successful small creation/update tie-boundary checks across sufficiently fresh source refreshes; investigate the identity/freshness discrepancy; resolve timezone/DST; retain a small redacted repeated-observation log across daily refreshes | Keep ADR proposed until evidence/review; no production ingestion implementation. Distinguish API tests from DB crash-resume proof. |
| Firuz | Implement only the approved Spec 02 tooling, fixture-only CI, non-root image and Postgres health/volume foundation | Follow the foundation acceptance checklist; coordinate pyproject/lock with Nijat/Nizami. Application health/CLI and scheduling remain excluded. |
| Nizami | Implement only the approved Spec 05 migration framework, empty namespaces and isolated PostgreSQL tests | Follow fresh/repeat/rollback/concurrency checks. Domain tables and storage APIs remain blocked on reviewed shared contracts. |

Practical defaults to review: psycopg 3 plus a small ordered SQL migration runner with a migration ledger/advisory lock; avoid adding an ORM solely for migrations. Keep one dependency lock owned through Spec 02. These are recommendations, not accepted ADR choices. Infrastructure tests need PostgreSQL/Docker, not the live public API.

## Blocked implementation

- Full Spec 02 acceptance includes an actual application healthcheck; do not claim that part before a real entry point exists.
- Spec 03 API synchronization depends on verified creation/update ordering, source consistency policy, UTC conversion and reviewed cursor contracts. Durable crash-resume is a later integration test, not demonstrated by HTTP pages.
- Source-specific bronze dedupe, checkpoint schema and typed silver DDL in Spec 05 require frozen shared semantics. Silver publication (04), gold/SCD2 (06), orchestration/history (07), analytics/performance (08), recovery (09) and integration (10) retain existing dependencies.
- Genuine SCD2 evidence needs the same request observed changing tracked attributes across real snapshots. Different requests with different statuses, advancing system metadata and disappearance alone do not meet that requirement.

## Required specification amendments before work assignment

1. Specs 00/02/05 now contain the lead-authorized foundation-only exceptions. Assign only those portions, retain one spec per implementation PR and separate partial versus full acceptance; Spec 01's source gate remains effective for all other work.
2. Correct Spec 05 task 3: `ops.run_history` conflicts with lead-controlled contracts/architecture naming `ops.pipeline_runs`. Resolve in the reviewed Spec 01 contract; do not create both names.
3. Expand Spec 01 acceptance to explicitly cover text-key ties, source freshness headers, update-cursor filtering, exact timezone/DST rules and genuine repeated-observation evidence. Keep unsupported/unverified outcomes visible.
4. Update Spec 03 and contracts after approval with distinct creation/update/reconciliation scopes, overlap/frozen bounds, out-of-date response policy, bounded transient-error retry and non-snapshot limitations. Never persist progress for a DNS/HTTP failure.
5. Refine Specs 04/06/08 after contract review with metric eligibility, observation-time validity, one-current-version joins and closure-time limitations. Close time measures agency-recorded closure, not independently verified fulfillment.

## Source fallback and deadline

If live source remains unreliable, stop repeated probing, retain request IDs/timestamps and retry later with bounded backoff or an optional environment token; do not use token acquisition as proof of correctness. Use deterministic fixtures to build approved infrastructure. A bounded full reconciliation of the selected cohort is a candidate fallback if update extraction is unsupported; quantify its cost before adoption. A dated official export from the same source can support a backfill if provenance is recorded, but cannot establish live incrementals or genuine prior state history. Alternate-source adoption needs a new evidence-backed decision; no second API is silently added.

Target 24–25 November for approved implementation/integration and 26 November for demonstrations/submission. Escalate missing source/SCD2 evidence promptly rather than fabricate compliance or claim all remaining work will fit.

## Local Git and GitHub handoff

The lead supplied `https://github.com/nijat-akhundzada/nyc-311-data-pipeline.git`; `origin` was configured after inspecting local state, and remote refs were empty before publication. Initial commit `702a7f8` was pushed normally to `origin/main`; local `main` tracks it and remote SHA verification matched. Subsequent documentation changes use a feature branch and human PR review. No force push, merge or branch-protection change was performed. Configure required lint/unit/integration checks when those jobs actually exist.
