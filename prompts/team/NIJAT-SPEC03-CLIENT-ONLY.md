# Nijat — limited Spec 03 client-only implementation prompt

**DRAFT / INACTIVE until the documentation amendment is human-reviewed, approved and merged.** This task only authors the prompt; it does not execute it. After activation, copy the text below into a new Codex session. Never treat the presence of this file as approval. The review ledger must link the actual approval/final reviewed commit; if unavailable, report the missing prerequisite before changing code.

```text
You are Nijat's coding agent for NYC 311 Spec 03, CLIENT-ONLY EXCEPTION.

Read AGENTS.md and its ordered context files, Specs 00/01/03, ADR-001's latest risk amendment, context/contracts/README.md, docs/spec01-contract-review.md, source-smoke-test.md and the current code/tests. Read the full-ingestion handoff only to understand exclusions; its DB/service/lifecycle tasks are NOT authorized by this slice.

Activation prerequisites:
- Confirm actual human approval and merge of the client-only documentation amendment; inspect the linked final commit/review, not an unchecked checklist or silence. Source selection is approved, but source verification remains incomplete and broader DB/lifecycle contracts may still be proposed.
- Confirm Firuz's approved locked tooling provides Python >=3.12, HTTPX, pytest and ruff, or obtain an explicitly coordinated dependency update through Firuz. Do not edit pyproject/lock/CI yourself or create a competing manifest. If unavailable, give the exact missing tooling dependency and stop before implementation.
- Inspect Git/PR state. Preserve teammate changes. Fetch current main and create a new branch feat/03-api-client-only-nijat (use a fresh suffixed branch if already occupied). Never modify teammate branches, force-push, merge or self-approve.

Authorized scope only:
1. Pure allowlisted SoQL generation for creation/update keysets, fixed bounds and a bounded limit.
2. Typed creation/update cursors and transport-only ApiPageRequest/Page value types.
3. One-logical-page HTTP client with bounded retries/timeouts/Retry-After.
4. Strict freshness/generation/header and response-envelope/key/order validation.
5. Deterministic synthetic fixture unit tests, no real network.

Allowed implementation paths:
- src/nyc311_pipeline/ingestion/{__init__,models,query,cursor,client,retry,freshness}.py
- tests/unit/test_ingestion.py
- small labeled synthetic fixtures under tests/fixtures/ingestion/
- a concise owned Spec 03 implementation note for commands/results if needed.

Do not write DB data, create migrations/repositories/run tables, persist checkpoints or quarantine, implement service.py/multi-page orchestration, shared DB contracts.py, run lifecycle/locks, reconciliation executor, Silver/Gold/SCD2 publication, scheduler or production CLI. Do not change storage/, db/, ops/, Docker/CI/config/lock files or other owners' scopes. Return a candidate next cursor only: no durable resume, idempotent DB loading or end-to-end claim is authorized.

Transport contract:
- ApiPageRequest has kind, one naive source-wall-time creation interval, matching nullable typed cursor, integer limit 1..5000 and nullable pinned generation; update requests additionally have aware UTC lower/upper update bounds. Bounds are explicit and increasing, never inferred from a live clock or stored watermark. Keep the reviewed field projection fixed.
- CreationCursor retains original floating created_date text and opaque text unique_key; validate naive timestamp syntax without attaching UTC. UpdateCursor requires an aware timestamp normalized to UTC Z and text key. Never cast source IDs to integers or change them. Reject mismatched cursor kinds.
- build_query(request) is pure. Creation: interval >= start and < end plus (created_date > last OR (created_date = last AND unique_key > key)); order created_date ASC,unique_key ASC. Update: same cohort plus :updated_at >= lower AND :updated_at < upper and analogous update/key predicate; order :updated_at ASC,unique_key ASC. No offset fallback. Pass HTTP parameters separately; identifiers come from an allowlist and string literals use Socrata single quotes with embedded apostrophes doubled (official text datatype documentation). Test quote injection and reject unsuitable control characters rather than generating malformed queries.
- ApiClient.fetch_page(request) returns only a validated Page: raw records, next_cursor (last row or unchanged for empty), exhausted only for an empty response, received_at_utc, generation, request_id and sanitized metadata. A future runner adapts Scope/segment/checkpoints; do not implement it here. Choose/document the HTTP client execution strategy so the declared total attempt/page deadlines are actually enforced; a per-socket timeout alone is not a total deadline. Keep the API typed and fixture-testable.
- Require a JSON list of objects, at most the requested limit, required cursor fields/types, strictly increasing keys above the supplied cursor and within passed query bounds. Reject malformed/out-of-order/duplicate keys with typed source-contract/order errors; do not silently skip records. Creation values remain wall-time values; full UTC eligibility/DST conversion is later validation work.

Exact retry/freshness policy:
- One in-flight request; maximum four attempts including first, 5s connect, 30s total per attempt and 180s total per logical page using a monotonic deadline. Dependency-inject HTTP transport, clock, sleeper and jitter; unit tests must not use real waits.
- Retry transport DNS/timeout/reset, HTTP 202/408/429/500/502/503/504 and explicit stale/lagging-secondary responses. Fail without retry for other HTTP errors, TLS verification failure, invalid envelope/required types/order, missing/invalid mandatory freshness metadata and a changed pinned generation.
- After failed attempt n, jitter is in [0,min(30,2**(n-1))] seconds. Valid Retry-After delta-seconds or HTTP-date is a minimum wait plus nonnegative jitter; never shorten it. If required wait/next attempt cannot fit the remaining deadline, fail retryably without issuing early. Invalid/negative header uses normal backoff and a sanitized metadata warning. No live quota/Retry-After guarantee is claimed.
- Parse case-insensitive header names, stripped true/false flag values and aware UTC truth/secondary HTTP-date values. Require explicit false out-of-date flag and secondary >= truth. First acceptable response returns generation; supplied pinned generation must match. Missing/invalid markers raise source_freshness_unknown; stale/lagging response retries within budget; generation change raises source_generation_changed immediately. No accepted Page/next cursor on failure.
- Optional SOCRATA_APP_TOKEN is sent only as a header. Redact credentials/URLs carrying secrets and do not log bodies, free text or raw requests. Errors contain stable category, retryable flag and sanitized request ID/message.

Evidence boundaries:
- America/New_York is the selected provisional engineering interpretation; publisher timezone/DST remains unverified. This slice does not implement Silver conversion/quarantine. Current snapshots cannot reconstruct unobserved states, and this work must not create SCD2 history.
- Unit tests prove our behavior under fixtures, not provider freshness, complete incremental coverage, real state changes or durability. Use labeled synthetic fixtures; no source downloads or real service-request payloads.

Required focused tests:
- Initial/resumed creation/update predicates, inclusive/exclusive bounds, quote escaping, empty/malformed/mismatched cursor, limits and variable-width text IDs/ties.
- Valid/empty/short pages, records above limit, malformed JSON/root/records, missing or incompatible cursor fields, duplicate/decreasing/out-of-bounds keys; no accepted Page on failure.
- Fresh/stale/unknown/invalid headers, truth/secondary lag and pinned-generation change, including empty response freshness. Do not relax freshness to pass tests.
- Each retryable and permanent error classification, transport versus HTTP distinction, 429 seconds/date/invalid/negative/too-long Retry-After, no early retry, exact attempt and total-time ceilings, stale budget exhaustion and redaction. All clocks/transport/randomness deterministic.
- Prove no storage/CLI/lifecycle coupling; no public API access is needed by tests. Do not add redundant tests of every implementation detail; test the behavioral boundaries above.

Verification and Git handoff:
- Run focused tests with Firuz's actual locked runner, e.g. uv run pytest tests/unit/test_ingestion.py; run uv run ruff check on changed Python paths and uv run ruff format --check on changed Python paths. Run any existing required hooks/checks. These are future commands, not previously passed results; adapt to the established repository toolchain and record exact commands/output.
- Inspect git diff and status; ensure only allowed paths changed, no credentials/datasets and no unstaged teammate changes included. Stage explicit paths only and run git diff --cached --check.
- Make atomic conventional commits (e.g. feat(ingestion): add bounded client-only API adapter). Push only the feature branch and open a draft PR using the repository template if authenticated; otherwise supply the comparison URL/manual commands. Name Spec 03 CLIENT-ONLY, activation approval/base, test outputs, unverified source assumptions and exclusions. Request human review; do not merge/self-approve/bypass CI.
- Report partial client-slice completion only. Do not mark full Spec 03 Done, claim checkpoint recovery/production integration or advance the tracker without the required human merge workflow.
```
