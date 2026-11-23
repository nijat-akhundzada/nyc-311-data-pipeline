# Build plan — ordered delivery units

**All specs require human approval and one PR per spec.** `01` is decision + API smoke test, a gating dependency. Technical specs should be accepted in PR order where dependencies require it.

**Foundation-only exception authorized by the lead on 2026-11-23:** Firuz may begin Spec 02 foundation work and Nizami may begin Spec 05 foundation work as bounded below while ADR-001 remains PROPOSED. This authorizes only those portions; full acceptance and all source-dependent implementation still require accepted Spec 01. Keep partial foundation evidence separate from full-spec completion and retain human PR review; do not mark either spec Done after a foundation-only PR.

| # | Owner | Spec | Dependencies | Evidence |
|---|---|---|---|---|
| 01 | Nijat | `01-source-contract-validation.md` | none | accepted ADR, source smoke report |
| 02 | Firuz | `02-docker-ci-foundation.md` | foundation: source-independent; full: 01 | nonroot docker, CI lint/test |
| 03 | Nijat | `03-api-resumable-ingestion.md` | 01 (and 05 for DB integration) | cursor/retry tests |
| 04 | Nijat | `04-validation-silver-quality.md` | 03, 05 | quarantine/gate tests |
| 05 | Nizami | `05-database-bronze-ops.md` | foundation: source-independent; full: 01 | migration, bulk test |
| 06 | Nizami | `06-gold-star-scd2.md` | 04, 05 | SCD2/replay proof |
| 07 | Firuz | `07-orchestration-history.md` | 02, 03, 05 | schedule/history proof |
| 08 | Nizami | `08-analytics-performance.md` | 06 | ≥1M count, before/after |
| 09 | Firuz | `09-failure-recovery.md` | 04, 06, 07 | kill/startup/malformed drills |
| 10 | Nijat | `10-end-to-end-integration.md` | 02–09 | end-to-end correctness |
| 11 | All / Nijat | `11-submission-release-gate.md` | 10 | complete evidence |

**Working in parallel:** After 01, specs 02, 03 (client/fixtures without DB binding), 05 can run in parallel. After 05 and 03, 04 and 07 may progress. Each specification's acceptance criteria override informal chat instructions. Target interface and shared SQL design live in `context/contracts/README.md`.

Before 01 acceptance, only 02 tooling/container/Postgres test infrastructure and 05 migration framework/empty namespaces may proceed. Coordinate the single pyproject/lock through Firuz; Nizami can use an isolated local PostgreSQL instance before 02 merges, then verify against its Compose/CI service. Bronze/ops domain tables, typed silver, ingestion, publication, gold/SCD2 and scheduling are outside the exception. See each spec for foundation acceptance criteria.
