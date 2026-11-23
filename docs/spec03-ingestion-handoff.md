# Spec 03 — review-only ingestion handoff

**Status: DRAFT / BLOCKED.** Prepared during Spec 01 to make cross-owner review concrete; this is not approved Spec 03 and contains no implementation. Do not implement until Spec 01/ADR-001 and version 1 contracts are accepted. The existing Spec 03 remains unchanged. Nizami's approved foundation covers infrastructure only, not the domain repository needed here. References: `context/contracts/README.md`, `context/specs/03-api-resumable-ingestion.md`, `docs/source-smoke-test.md`.

**Current amendment:** the paragraph above and full handoff below describe the original full-integration gate. A separate client-only permission is now proposed in Specs 00/01/03; it activates only after that documentation is reviewed/approved/merged and does not unblock this full handoff. Use `prompts/team/NIJAT-SPEC03-CLIENT-ONLY.md` for that bounded slice. Do not implement service.py, shared DB types, repository integration, run lifecycle or CLI from this document under the exception.

## Entry gates and dependencies

- Human accepts source policy/ADR-001 and shared types/interfaces after Nizami/Firuz review; merge the Spec 01 PR.
- Nijat explicitly approves the detailed Spec 03 implementation assignment. Client/fixture-only work may then start; integration/publication cannot be claimed until domain Spec 05 repository contracts and migrations are implemented/reviewed/merged.
- Firuz supplies locked package/tooling and PostgreSQL CI infrastructure. Coordinate dependency changes through Firuz rather than editing his branch. Nizami supplies atomic `commit_page`, checkpoint loading, page receipts, quarantine storage and durable run associations; empty namespaces alone do not meet this dependency.
- No source-backed SCD2 demonstration is implied by deterministic test fixtures. Genuine observation evidence remains a separate Spec 01/06 requirement.

## Exact proposed responsibilities

| Module | Responsibility | External boundary |
|---|---|---|
| `src/nyc311_pipeline/contracts.py` | Nijat-owned shared Scope/RunConfig, typed cursors, Checkpoint, Page/CommitResult/RunResult and protocols in proposed version 1 | Freeze names/field types with owners before implementation |
| `ingestion/query.py` | Allowlisted projection, source interval construction, tested SoQL escaping, strict creation/update predicates | Pure functions; no HTTP/DB |
| `ingestion/client.py` | HTTPX lifecycle, token header, bounded fetch, JSON/type/header checks | `fetch_page(request: ApiPageRequest)`; future runner adapts frozen scope/segment/cursor to the request; no persistence |
| `ingestion/retry.py` | Retry classification, deadlines, injected clock/randomness, Retry-After parsing | No global sleeps in unit tests; no quota invention |
| `ingestion/freshness.py` | Parse generation/freshness markers, pin/compare policy | Reject explicit stale/unknown views before page acceptance |
| `ingestion/cursor.py` | Exact source timestamp parsing/order validation, next-cursor construction | Cursor uses wall time for creation, UTC for updates, text key for both |
| `ingestion/service.py` | Segment loop, resume/config checks, invoke repository, counters/cap/empty-page completion | Orchestrates ingestion only; never writes silver/gold or independently updates lifecycle/checkpoint truth |
| `tests/unit/test_ingestion.py` | Deterministic transport/query/header/error cases | HTTPX fixture transport; no live public API |
| `tests/integration/test_resume.py` | Domain repository durability/replay/recovery tests | Isolated PostgreSQL; Nizami contract implementation required |

These are proposed public modules for review; do not import storage/private internals or add a second run-history manager. CLI/pipeline wiring remains Nijat's integration scope; lifecycle implementation remains Firuz's Spec 07, with any minimal pre-07 adapter explicitly assigned/reviewed before use. Do not quietly absorb Spec 07 into Spec 03.

## Algorithms and interfaces

1. Validate RunConfig and acquire/reuse the runner's dataset lock. Create or explicitly resume a persisted run; compare config hash, contract version and interval plan. Resume retains original bounds; invocation cap is operational and does not change the source scope.
2. Preflight field/type/freshness and missing-sort-key policies exactly as proposed version 1; these queries still need fresh source verification before approval. Pin the first accepted source generation. Incompatible/missing contract data fails visibly; no best-effort offset fallback.
3. Iterate persisted segments in fixed order. Load each checkpoint from `BronzeRepository.load_checkpoint`; skip only durably exhausted segments. Build the appropriate strict keyset query from frozen scope, segment and saved cursor.
4. Fetch at most page_size (or remaining invocation cap). For creation use source wall-time bounds/order plus source timestamp/key cursor; for update use cohort + frozen UTC update window/order plus update timestamp/key cursor. HTTP parameters are encoded; reviewed identifiers are static and literals escaped.
5. Enforce timeout/deadline/freshness/schema/order checks before accepting a Page. No cursor, count or source-success watermark changes on rejected responses. Retain source request IDs and sanitized metadata; never log source bodies/token.
6. Call `commit_page(run_id, expected_checkpoint, page)`. That short transaction inserts/dedupes raw versions, associates every received row with this run, stores page receipt/hash, advances only this segment cursor and updates ingest counters. Confirmed commit is the only advance point.
7. If commit acknowledgement is lost, reload durable checkpoint/receipt: matching committed page means continue; unchanged checkpoint permits idempotent commit retry; conflicting receipt aborts. Do not assume a connection exception proves rollback. No re-fetch-and-skip logic.
8. A fresh empty page is durably marked exhausted; a short nonempty page is not terminal. At `max-records`, pause the run with persisted cursor and no publication/watermark. When all segments exhaust, mark ingest_complete and hand the durable stage to later validation/publish orchestration.
9. Update source-success bounds only in the eventual silver+gold+run-success transaction after whole-scope quality PASS. Spec 03 alone may demonstrate bronze completion, never claim final publication or full-pipeline success without downstream implementations.

## Retry/freshness details

Follow version 1 exactly: one request at a time, four attempts including first, 5s connect/30s attempt/180s page deadline, bounded exponential full jitter. Retry transport timeout/DNS/reset, HTTP 202/408/429/500/502/503/504 and explicit stale view; fail on other HTTP errors, TLS verification error, malformed JSON/envelope, schema/order violations. Honor Retry-After delta/date without shortening; if it cannot fit the remaining deadline, stop retryably. Generation change invalidates the run, not just a page. Unknown/missing required freshness markers fail explicitly. No successful real Retry-After behavior has been observed; fixtures test client decisions only.

## Idempotency and recovery guarantees to prove

- Same source snapshot + same scope cannot multiply logical raw versions or dimension versions. Run-audit identities/receipts may differ; counts are not fabricated from insert counts.
- Raw identity `(dataset_id, unique_key, raw_hash)`; source metadata belongs in the raw hash but not the SCD2 tracked hash. Run associations exist even for a duplicate raw version. A legitimate A→B→A can be represented without pretending an unchanged replay is a new change.
- Crash before page commit leaves both raw association and checkpoint unchanged. Crash after commit resumes after it; an acknowledged page cannot be reapplied to increment counts twice.
- Invalid/HTTP stale/unknown generation responses never advance a cursor. A changed generation on resume requires a failed audited run and fresh extraction of its frozen scope under a new run ID.
- Reconciliation has independent segments/checkpoints, finds corrections beyond creation lookbacks and does not automatically delete missing identities. Full replacement can require re-extraction; no exact source snapshot or capture of every intermediate state is guaranteed.

## Required deterministic tests

Unit: initial and resumed predicates for both cursor kinds; equal timestamps; variable-width text IDs (`"10"` precedes `"2"` under the proposed comparison, without claiming live collation proof); SoQL quote escaping; UTC-bound transition splitting; ambiguous/nonexistent event times; empty/short pages; optional omitted fields; changed required type; duplicate/decreasing/out-of-window keys; malformed JSON; missing key/update metadata; stale/missing/mismatched freshness; generation changes; every retryable status plus permanent 400/401/403/404; 429 Retry-After seconds/date/invalid/too-long; attempt/deadline exhaustion; DNS versus HTTP classification; capped pause/config mismatch. Inject time/randomness; assert no retries exceed limits or happen earlier than Retry-After.

PostgreSQL integration: fresh domain migrations; same page commit twice; identical snapshot in a new run creates associations but no new raw versions; page receipt compare-and-swap conflict; forced transaction rollback before checkpoint; commit-acknowledgement loss with reload; simulated process death before/after durable commit; multi-segment independent recovery; concurrent dataset lock contenders; missing-sort-key rejection retains reason without cursor advance; complete/paused/failed run counts; exhausted segment survives restart. Confirm no silver/gold changes during ingestion tests. Coordinate test-owned temporary schema/data with Nizami; never edit applied migrations.

Later downstream integration, not a Spec 03-only claim: over-threshold/zero-input failure, all-or-nothing silver/gold publication, failed publish watermark rollback, unchanged SCD2 replay and genuine source-change demonstration. These depend on Specs 04/05/06/07/10 and remain blocked.

## Acceptance and evidence handoff

- [ ] All unit cases run with recorded commands/results under Firuz's locked tooling; no live network dependency.
- [ ] Domain repository integration cases run against PostgreSQL with recorded before/after raw/association/checkpoint counts; no partial durable page.
- [ ] Retry/freshness errors produce correct proposed categories/exit semantics and zero cursor advancement.
- [ ] Interrupted ingestion resumes frozen scope without skipped/duplicated logical rows; capped run is visibly paused/unpublished.
- [ ] Breaking source changes fail with redacted diagnostics; quarantine retains rejected record/reasons where applicable.
- [ ] Human reviews one-spec PR and cross-owner boundaries; full CLI/publication claims remain with their later dependencies.

Future commands after implementation: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest tests/unit/test_ingestion.py`, `uv run pytest tests/integration/test_resume.py` with isolated test DB configuration. These are target commands, NOT checks already run. Spec 09 supplies actual opt-in container kill/DB startup demonstrations; a unit exception is not equivalent evidence.
