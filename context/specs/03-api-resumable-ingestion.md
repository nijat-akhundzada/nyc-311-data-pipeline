# Spec 03 — Api Resumable Ingestion

**Owner:** Nijat  
**Status:** BOUNDED BRONZE SLICE LEAD-AUTHORIZED / IMPLEMENTED ON REVIEW BRANCH; full scope gated  
**Type:** Implementation  
**Dependencies:** limited scope: this amendment reviewed/approved/merged and coordinated tooling; full scope: 01 accepted, reviewed DB contract with 05 and 05 merged for full integration  

## Lead-authorized durable Bronze slice — 2026-11-24

The project lead explicitly authorizes the minimum durable Bronze implementation
in the current task, risk-accepting the engineering policies in
`context/contracts/bronze-v1.md`. This supersedes older source/full-spec dependency
blocks **only** for Spec 05 raw/run/checkpoint/receipt/association persistence and
Spec 03 bounded ingestion/resume using the existing client. Separate dependent
feature PRs preserve the one-spec implementation workflow. No teammate approval
is inferred; Nizami reviews storage/transactions and Firuz reviews the temporary
canonical-table ingestion lifecycle adapter. No earlier owner implementation or
applied migration may be rewritten.

ADR-001 remains PROPOSED; full Spec 01 and full Specs 03/05 are not complete.
No Silver/Gold, quarantine/quality publication, scheduler, successful watermark
advancement, fabricated SCD2 history or production pipeline runner is authorized
by this slice. See the Bronze contract for exact interfaces and limitations.

## Objective
Stable paginated ingestion, retry handling and resumable checkpoints.

## Proposed client-only permission — Nijat

Activate only after human review/approval and merge of this documentation amendment. Pending source-verification evidence does not block this narrow exception once approved; it still blocks claims of proven source reliability or full-spec completion. Follow the bounded client policy in ADR-001 and the client subset of `context/contracts/README.md`. Do not activate the draft prompt merely because a branch was pushed or this text exists locally. Record approval identity/date/commit/PR link in `docs/spec01-contract-review.md`.

Allowed files: `src/nyc311_pipeline/ingestion/{__init__,models,query,cursor,client,retry,freshness}.py`, `tests/unit/test_ingestion.py`, and small synthetic HTTP fixtures under `tests/fixtures/ingestion/`. Use transport-only models; do not implement shared DB protocols or a full runner. `ApiClient.fetch_page(request: ApiPageRequest) -> Page` receives explicit immutable bounds/cursor/limit/generation and returns only a candidate next cursor, never a durable checkpoint.

Allowed work: pure allowlisted/escaped SoQL generation for creation/update bounds and strict text-key predicates; typed source-wall-time creation and UTC update cursors; one-page HTTPX client with bounded retries; JSON/key/order/freshness checks; deterministic unit tests with injected HTTP transport/time/jitter. Selected source event timezone is America/New_York as a provisional interpretation; preserve source wall-time cursor values and never claim publisher/DST confirmation. Silver timezone conversion/quarantine and scope orchestration remain outside this slice.

Explicit exclusions: database connections/writes/migrations, repositories or persisted checkpoints, run lifecycle/locking, multi-page run orchestration, reconciliation execution, quarantine persistence, silver/gold/SCD2 publication, scheduler, production CLI and durable recovery/idempotency claims. Do not modify `storage/`, `db/`, `ops/`, orchestration, Docker/CI/pyproject/lock files, or teammate branches. Coordinate required HTTPX/pytest/ruff dependencies with Firuz; do not create a competing dependency manifest if tooling is unavailable. Metadata/null-key preflight execution and live API tests are not required or authorized by this slice; pure generation/fixture validation is enough.

### Client-only acceptance criteria (partial, not full Spec 03)

- [ ] Exact creation/update predicates, bounds, literal escaping, text-key ties and cursor parsing/order errors pass fixture-only tests; no offset fallback or numeric ID casts.
- [ ] HTTP client returns validated records/metadata and a candidate next cursor; short nonempty pages are not treated as exhaustion. Invalid/stale/unknown-freshness responses return no accepted Page/cursor.
- [ ] Four-attempt/30s attempt/180s page deadlines, 5s connect, retry classifications and Retry-After behavior match the ADR amendment. Injected clocks/transport/jitter prove limits without real waits or network.
- [ ] Freshness false/true/missing/invalid flags, truth/secondary mismatch and generation changes have explicit outcomes; conservative markers are not presented as a snapshot guarantee.
- [ ] Tokens/bodies are absent from diagnostics; failures have typed sanitized categories. Synthetic fixtures are labeled and never presented as genuine SCD2 observations.
- [ ] Focused unit tests, ruff check/format and any required existing hooks pass with exact commands/results. Human reviews the one-spec feature PR; no full Spec 03 checkbox is marked complete from client-only results.

Use a new branch `feat/03-api-client-only-nijat` from updated main after amendment merge. Gated implementation prompt: `prompts/team/NIJAT-SPEC03-CLIENT-ONLY.md`. The full tasks/acceptance criteria below remain gated and unchanged in scope; the generic required integration verification applies to full integration, not this no-DB exception. For the limited slice, replace broad task 1's status shorthand with the exact retry classification in ADR-001 (including HTTP 408 retry).

## Required implementation tasks
1. Implement httpx API client with bounded timeout/retries, Retry-After and 429/5xx handling; fail on 4xx other than 429
2. Use frozen upper-bound and approved keyset pagination (no offset-only approach)
3. Commit bronze page + cursor atomically via Nizami repository, restart at last committed cursor
4. Support CLI incremental and `[start,end)` backfill windows with independent checkpoints; enforce valid date constraints
5. Support mutable-record refresh/lookback per ADR and idempotent dedupe/upsert
6. Detect field additions/removals/type shifts, log schema drift with masking and fail on breaking changes
7. Test page boundary ties, identical replay, simulated termination, 429/503 and malformed API payload

## Files and boundaries
- `src/nyc311_pipeline/ingestion/`
- `tests/unit/test_ingestion.py`
- `tests/integration/test_resume.py`

## Acceptance criteria
- [ ] Interrupted run resumes without skipped/duplicated logical rows
- [ ] Two identical runs leave logical bronze state unchanged
- [ ] No live API requirement in unit/CI tests

## Required verification
- Focused pytest tests (unit/integration), formatting/lint, plus a specific manual end-to-end check where relevant. Record exact commands and results in PR.
- Test unhappy paths and prove no unintended row-count or downstream changes.
- Where infrastructure/source access is missing, disclose missing evidence; do not mark pass.

## PR handoff
- Branch `feat/03-api-resumable-ingestion-nijat` (shorten if preferred).
- Conventional atomic commits; open draft PR to `main`; use PR template; request human peer review.
- Do not change another owner’s directory or common contract without review and documented approval.
