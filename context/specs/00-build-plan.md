# Build plan — ordered delivery units

## Proposed limited Spec 03 exception — approval required before activation

The lead requested a client-only exception on 2026-11-23. After human review/approval and merge of this documentation amendment, Nijat may implement only pure SoQL generation, typed creation/update cursors, bounded HTTP retries, freshness-header validation and deterministic fixture-based unit tests under Spec 03. ADR-001 engineering acceptance and source-evidence completion are distinct; neither full Spec 01 completion nor production source guarantees are inferred from this exception.

No database writes, repositories/checkpoint persistence, durable recovery claims, silver/gold publication, scheduler or production CLI wiring are permitted. Firuz's tooling/dependency lock must be available or explicitly coordinated; it is not permission to edit his files. Nizami's and Firuz's existing foundation scopes remain unchanged. Full Spec 03 retains accepted Spec 01, reviewed DB contracts and full Spec 05 integration dependencies; no Spec 04–11 dependency is released by client-only tests. See Spec 03's bounded acceptance checklist and `docs/spec01-contract-review.md` for actual approval records. Until the amendment is approved, this is proposed permission only; no code is implemented in this documentation task.

## Full delivery plan — existing gates

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

Under the foundation-only exception before 01 acceptance, only 02 tooling/container/Postgres test infrastructure and 05 migration framework/empty namespaces may proceed. The separate Spec 03 client-only exception above remains conditional on this amendment's human review/approval/merge and coordinated tooling; it does not expand either foundation scope. Coordinate the single pyproject/lock through Firuz; Nizami can use an isolated local PostgreSQL instance before 02 merges, then verify against its Compose/CI service. Bronze/ops domain tables, typed silver, durable ingestion/checkpoint integration, publication, gold/SCD2 and scheduling remain outside both exceptions. See each spec for its partial acceptance criteria.
