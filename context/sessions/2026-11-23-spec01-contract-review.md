# Spec 01 contract review — 2026-11-23

## Assignment and Git/PR inspection

Nijat assigned Spec 01 source-contract validation, conditional ADR review and contingent Spec 03 preparation. No application implementation. Nizami's approved Spec 05 foundation and Firuz's approved Spec 02 foundation were not changed. Their work-in-progress status is human-reported; no implementation completion or test result is inferred from it.

Initial local branch was `docs/foundation-scope-exceptions` at `09222a5`, clean. Fetched origin normally; `origin/main` was `702a7f8`. Created `feat/01-source-contract-validation-nijat` from origin/main, not from a teammate's branch. GitHub search (`is:pr is:open`, repository scope, limit 20) returned only [PR #1](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/1), foundation exceptions, open/unmerged with head `09222a5` and base `702a7f8`. Its description was still the unfilled template; it was not edited. No merge, review approval, teammate branch change or tracker completion was performed. PR #1's unmerged state does not revoke the lead's explicit foundation authorization, but its documentation still needs human review/merge.

## Evidence and resulting decisions

- Only two new read-only request definitions, both tied to unresolved consistency/timezone questions; normal and one escalated attempt each. All four failed during DNS resolution. No HTTP response, API failure status, record, freshness marker or new SCD2 observation was obtained.
- Historical successful count/order/update/tie probes were not repeated. The report preserves them without claiming that mixed freshness views prove a snapshot or complete CDC.
- Official Socrata timestamp/system-field/response documentation was reviewed. NYC's website Eastern-time style rule was found but is not accepted as a dataset-specific guarantee. No publisher-specific DST statement was found.
- Python standard-library round-trip checks of the proposed New York DST policy passed for one normal, one nonexistent and one ambiguous wall time. This checks a design algorithm, not source semantics or a running pipeline.
- Proposed contract version 1 is review-ready, not frozen: exact cursor/scope structures, hash/association/page-receipt semantics, bounded retries, strict freshness/generation policy, UTC/DST rules, layer/quality/publication boundaries, canonical ops.pipeline_runs and CLI/errors are explicit.
- ADR-001 remains PROPOSED; Spec 01 remains AUDIT PARTIAL / NOT ACCEPTED. A review-only Spec 03 handoff is drafted without altering/approving Spec 03 or implementing it.

## Cross-owner questions before contract approval

1. Nijat: obtain/record authoritative event-time semantics or explicitly review the assumption and its remaining evidence gate; approve UTC scope conversion/DST quarantine, strict freshness behavior, capped pause semantics and reconciliation mode. No source assumption is silently accepted.
2. Nizami: review raw/run association storage, page-receipt compare-and-swap and ambiguous-commit recovery, older/conflicting observation policy, current-fact/state relationship and the single publication transaction. This is future domain work, not an extension of the foundation assignment.
3. Firuz: review dataset-wide locking, unfinished-run/recovery lifecycle, typed errors and phase/count ownership; coordinate the minimal lifecycle dependency before client integration without absorbing Spec 07 into Spec 03.
4. Resolve the future Spec 05 domain-phase ops.run_history reference to canonical ops.pipeline_runs; do not implement both. No current migration or owner spec was changed by this audit.

## Exact readiness of Specs 03–11

| Spec | Current readiness | Blocking dependency / evidence |
|---|---|---|
| 03 | BLOCKED for implementation; contingent detailed handoff is DRAFT | Accepted/merged Spec 01 and reviewed version 1 contracts; client-only assignment needs explicit approval. Full DB integration additionally requires Spec 05 domain migrations/repository, not merely foundation namespaces, and compatible tooling/lifecycle adapters. |
| 04 | BLOCKED | Spec 03 plus domain Spec 05; complete-run validation/quarantine and atomic publication contracts. |
| 05 | APPROVED FOUNDATION ONLY; human reports implementation in progress | Existing foundation scope is unchanged. Full bronze/ops/silver storage and repository implementation require accepted Spec 01 and cross-owner domain contract review. |
| 06 | BLOCKED | Specs 04 and full 05; approved state/fact contract and genuine observed-change evidence. Fixtures can test algorithms later but cannot satisfy production-history proof. |
| 07 | BLOCKED | Full Spec 02 service wiring, Spec 03, domain Spec 05 and reviewed lifecycle/locking. Firuz's foundation is not scheduler/history implementation. |
| 08 | BLOCKED | Spec 06 plus an actual approximately 1M+ real validated/published data load; reproducible SQL and measured EXPLAIN evidence. Raw source count alone is insufficient. |
| 09 | BLOCKED | Specs 04, 06, 07; real kill/startup/malformed demonstrations with persistent counts and no partial publication. |
| 10 | BLOCKED | Specs 02–09 integrated/accepted; implementation and end-to-end evidence do not exist in this audit. |
| 11 | NOT READY | Spec 10 plus every submission artifact/evidence and human release decision. |

## Next task for Nijat

Perform the bounded fresh-view/identity audit described at the end of docs/source-smoke-test.md when transport recovers, then retain a minimal baseline across an actual daily refresh for genuine same-request attribute differences. Do not repeat the raw count/old successful query syntax just to accumulate calls. In parallel, review version 1 with Nizami/Firuz using the questions above; keep ADR proposed while essential evidence remains missing. If the source remains unusable, record the blocker and bring the documented bounded reconciliation/official-export limitations to a human source decision. The next implementation task is Spec 03 client/fixture work only AFTER Spec 01/contracts are accepted and Nijat explicitly assigns it; do not begin domain integration against empty foundation namespaces.

## Verification and caveats

Executed source diagnostic commands and exact results are in docs/source-smoke-test.md. Local `python3` zoneinfo round-trip assertions passed (normal=1, spring gap=0, fall fold=2 UTC candidates). `bash scripts/validate-context.sh`, `git diff --check`, staged whitespace checks and documentation-scope/link/fence checks are recorded in the PR handoff after actual execution. No application pytest, PostgreSQL integration, Docker, ruff or CI result is claimed by this documentation-only work. ADR and shared contract checkboxes remain unchecked. No new source records, credentials or implementation files are committed.
