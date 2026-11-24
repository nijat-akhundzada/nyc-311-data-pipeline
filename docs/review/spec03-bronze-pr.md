# feat(ingestion): resume bounded extraction from durable Bronze checkpoints (Spec 03)

Requested base: `main`; head: `feat/03-durable-bronze-ingestion-nijat`.
PR #7 is merged as `78de720`. A normal main merge (`62f3b63`) preserves both
histories without conflicts. PR #8 initially still targeted the old parent branch;
the connector's retarget request returned 403. Change the base to main in GitHub
and require green CI on the final pushed head. No published-history rewrite.

## Spec / ownership

Nijat, lead-authorized bounded Spec 03 slice. Builds on the merged Spec 05 domain PR #7,
not merely the older namespace foundation. Nizami/Firuz review interfaces; their
approval is not assumed. ADR-001 remains PROPOSED; full Spec 03 is incomplete.

## Changes / contracts

Async ingestion loop reuses existing ApiClient and public BronzeStore protocol.
Loads durable checkpoints, commits accepted pages, explicitly resumes immutable
scope, requires empty-page exhaustion, enforces invocation caps, pins generation
across segments, and resolves ambiguous acknowledgement using the retained Page
and receipt. Lost sessions require reconnect/lock/explicit resume. No second run
manager, production pipeline CLI, successful watermark or Silver/Gold publication.
The old no-service phase assertion now preserves transport-import isolation while
allowing the explicitly authorized service. Client implementation remains unchanged.

## Actual verification

Combined `pytest tests -q -ra`: **227 passed, zero failed/skipped** (184 unit + 43
PostgreSQL integration) against PG16.14. Ruff lint/format, seven pre-commit hooks,
context and whitespace passed. Non-root Docker image builds, applies 0001/0002,
pauses at three rows and resumes to four from a new app container after DB container
recreation on the same named volume. Negative DB readiness exits 2. One live accepted
page persisted 1 raw/association/receipt, paused/unpublished; ephemeral DB removed.

Full commands/counts/run IDs/image ID/caveats: `docs/spec03-bronze-ingestion-verification.md`.
Post-merge re-verification: **184 unit + 43 PostgreSQL integration passed**, zero
failed/skipped; Ruff/format, seven hooks, context and whitespace passed.
Remote CI is **not yet verified**: the existing workflow targets PRs to main.
Retarget PR #8 before expecting checks. Require real human review and green CI.

## Remaining scope

Source/schema/missing-key preflight, true UTC/DST handling/quarantine, comprehensive
incremental/reconciliation, validation/quality, publication, lifecycle/scheduler,
real kill demonstrations, source SCD2 observation and assessment-scale loading remain
outstanding. Fixtures are not production history or complete change-capture evidence.
