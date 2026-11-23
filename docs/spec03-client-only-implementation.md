# Spec 03 — client-only implementation evidence

Local implementation complete for the limited client slice; pending human review/merge. **Full Spec 03 is NOT complete.** No database repository/writes, persisted checkpoint, quarantine storage, multi-page runner, production CLI, publication, scheduler or SCD2 implementation is included. Source-contract verification and genuine source-change evidence remain incomplete; ADR-001 remains PROPOSED.

## Authorization, base and tooling

Nijat explicitly approved the limited exception and reported PR #3 merged. GitHub confirmed [PR #3](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/3) merged as `c8d1f11413d97a3a7ca0f145c49826b9251933f7`. Branch `feat/03-api-client-only-nijat` starts from that fetched main. This implementation does not infer Nizami/Firuz approval of broader domain contracts.

Main contained no pyproject/lock or Firuz implementation branch; no open PR provided tooling. After raising the prompt's prerequisite, the lead confirmed Firuz had not started and agreed to proceed with isolated temporary tooling. No repository manifest, lock, Docker/CI configuration or teammate file was created/edited. Python 3.12.11 and a hash-locked environment under `/tmp/nyc311-spec03-tooling` were used; Firuz still owns shared tooling integration.

Temporary bootstrap (executed): `uv venv --cache-dir /tmp/nyc311-spec03-tooling/cache --python python3 /tmp/nyc311-spec03-tooling/venv`; then `uv pip compile --cache-dir /tmp/nyc311-spec03-tooling/cache --python /tmp/nyc311-spec03-tooling/venv/bin/python --generate-hashes /tmp/nyc311-spec03-tooling/requirements.in -o /tmp/nyc311-spec03-tooling/requirements.lock`; then `uv pip sync --cache-dir /tmp/nyc311-spec03-tooling/cache --python /tmp/nyc311-spec03-tooling/venv/bin/python --require-hashes /tmp/nyc311-spec03-tooling/requirements.lock`.

Direct pins in the temporary requirements input: HTTPX 0.28.1, pytest 8.3.5, ruff 0.11.13. Resolved transitive pins: anyio 4.16.0, certifi 2026.11.20, h11 0.16.0, httpcore 1.0.9, idna 3.20, iniconfig 2.3.1, packaging 26.3, pluggy 1.7.0, typing-extensions 4.16.0. Temporary hash-lock SHA-256: `25debba246232fffe91eae1bd769a88c382d4ef218b1313a7364bcc35438a10f`. Environment, cache and lock are outside git; the versions above document this measured run, not a replacement shared dependency policy. Sandbox DNS initially blocked PyPI; the authorized escalated dependency resolution/install succeeded. This is tooling access, not source-API validation.

## Implemented behavior

- Frozen typed request/cursor values with explicit bounds, source-wall-time creation values and normalized UTC update cursors; opaque text IDs remain unchanged. No source-event timezone conversion is inferred.
- Pure fixed-projection SoQL queries with escaped literals, half-open windows and creation/update keyset predicates. No offsets, source preflight execution or automatic scope selection.
- `await ApiClient.fetch_page(request)` inside `async with ApiClient(...)` fetches **one logical page**. An injected HTTPX transport supports offline tests. Concurrent calls on the same adapter are rejected; no run lifecycle or database lock is implemented.
- asyncio cancellation contexts bound total attempt/page I/O to 30s/180s, separately from HTTPX's 5s connect/per-I/O limits. Injected monotonic/wall clocks, sleeper and jitter drive deterministic retry policy tests. Maximum four attempts; Retry-After is never shortened, and a wait plus a full attempt must fit the remaining page budget.
- Strict mandatory freshness markers and pinned generation; stale/lagging views retry, unknown metadata and generation changes fail. Markers remain conservative proxies, not provider snapshot isolation.
- Whole-page envelope, selected-field type, key/order and passed-bound checks precede any returned Page. Invalid JSON, duplicate fields, nonfinite JSON constants and invalid content decoding fail safely. Empty pages alone are exhausted; short pages remain nonterminal. Returned next cursors are candidates only, never durable checkpoints.
- Tokens are explicit constructor inputs sent only in `X-App-Token`; redirects/environment-derived proxy settings are disabled. Errors expose sanitized categories/request IDs without source body/transport-message text. A narrow HTTPX log filter replaces this source's request summaries to keep query literals out of logs, without changing log levels or unrelated traffic.

Modules: ingestion/models.py (transport values/errors), query.py, cursor.py, freshness.py, retry.py, client.py and the ingestion package exports. All raw fixtures in tests/unit/test_ingestion.py are synthetic; no real service-request records were fetched or committed.

## Actual verification — 2026-11-23

```sh
PYTHONPATH=src /tmp/nyc311-spec03-tooling/venv/bin/python -m pytest tests/unit/test_ingestion.py -q
# 146 passed in 0.25s

/tmp/nyc311-spec03-tooling/venv/bin/ruff check --isolated --target-version py312 --select E,F,I,UP,B src/nyc311_pipeline/ingestion tests/unit/test_ingestion.py
# All checks passed!

/tmp/nyc311-spec03-tooling/venv/bin/ruff format --isolated --target-version py312 --check src/nyc311_pipeline/ingestion tests/unit/test_ingestion.py
# 8 files already formatted
```

The isolated flag prevents implicitly borrowing unrelated/global lint config while shared tooling is absent. Existing formatting/lint issues found during editing were corrected before these final checks. No repository pre-commit configuration or application CI workflow existed to execute; no CI result is claimed. The test environment and source path are explicit because packaging/tooling remains Firuz's foundation responsibility.

Tests cover both keysets/ties/escaping, malformed/mismatched inputs, empty/short/oversize/invalid pages, update ordering independent of creation time, optional omissions, stale/missing/invalid/generation headers, all configured retryable statuses and representative permanent statuses, DNS/transport/TLS distinctions, retry exhaustion/jitter/deadlines, Retry-After seconds/date/invalid/oversized values, body-read cancellation, caller cancellation/one-in-flight guard, redaction and the no-persistence import boundary. Default-network transport is disabled in tests. Timeout cancellation tests schedule cancellation without real waits; clock-driven retry cases do not sleep in real time.

## Handoff and remaining gates

Review this as **Spec 03 CLIENT-ONLY**, not a claim of resumable persisted ingestion. Human review/merge remains required. Firuz should review async client/error/testing integration and coordinate the shared dependency lock/CI before production wiring; no changes to his files are bundled. Nizami's full domain repository/checkpoint/page-receipt work remains a separate prerequisite for durable recovery. Later orchestration must adapt its Scope/checkpoint to ApiPageRequest and await the client; there is no runner here.

No live-source freshness/identity discrepancy, publisher timezone/DST, late updates/deletion/full replacement or genuine SCD2 evidence was resolved by these fixtures. No million-row load, database integration, container recovery, quality gate or silver/gold atomicity test was executed. Full-spec acceptance checkboxes and progress tracker were left unchanged.

Protocol references: [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/), [mock transports](https://www.python-httpx.org/advanced/transports/), [Python 3.12 total timeout contexts](https://docs.python.org/3.12/library/asyncio-task.html#asyncio.timeout). These informed execution/test design, not verification of NYC's source semantics.
