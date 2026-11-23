# feat(ingestion): resume bounded extraction from durable Bronze checkpoints (Spec 03)

Initially base `feat/05-bronze-domain-foundation-nijat`;
head `feat/03-durable-bronze-ingestion-nijat`. Review only the service delta.
After the Spec 05 PR is human-approved/merged, merge main normally into this branch
and retarget this PR to main; require actual CI before merge. No published-history rewrite.

## Spec / ownership

Nijat, lead-authorized bounded Spec 03 slice. Depends on the Spec 05 domain PR,
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
Remote CI is **not verified**. Existing workflow targets PRs to main; stacked-base
checks start only after retargeting to main. Require real human review and green CI.

## Remaining scope

Source/schema/missing-key preflight, true UTC/DST handling/quarantine, comprehensive
incremental/reconciliation, validation/quality, publication, lifecycle/scheduler,
real kill demonstrations, source SCD2 observation and assessment-scale loading remain
outstanding. Fixtures are not production history or complete change-capture evidence.
