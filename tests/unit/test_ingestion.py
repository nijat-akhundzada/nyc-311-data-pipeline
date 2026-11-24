"""Synthetic transport fixtures only: no NYC records, network or database access."""

import ast
import asyncio
import logging
import ssl
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path

import httpx
import pytest

from nyc311_pipeline.ingestion import (
    ApiClient,
    ApiPageRequest,
    CreationCursor,
    IngestionError,
    UpdateCursor,
    build_query,
)
from nyc311_pipeline.ingestion import client as client_module
from nyc311_pipeline.ingestion.query import literal

NOW = datetime(2026, 11, 23, 12, tzinfo=UTC)
GENERATION = datetime(2026, 11, 23, 2, tzinfo=UTC)
CREATED = "2025-01-01T12:00:00.000"
UPDATED = "2026-11-22T12:00:00.000Z"
FRESH = {
    "X-SODA2-Data-Out-Of-Date": "false",
    "X-SODA2-Truth-Last-Modified": format_datetime(GENERATION, usegmt=True),
    "X-SODA2-Secondary-Last-Modified": format_datetime(GENERATION, usegmt=True),
    "X-Socrata-RequestId": "synthetic-request-1",
}
_UNSET = object()


def row(key="10", created=CREATED, updated=UPDATED):
    return {
        "unique_key": key,
        "created_date": created,
        ":updated_at": updated,
        "status": "Synthetic",
        "agency": "FIXTURE",
    }


def request(kind="creation", **overrides):
    fields = dict(
        kind=kind,
        creation_start_source="2025-01-01T00:00:00.000",
        creation_end_source="2025-01-02T00:00:00.000",
    )
    if kind == "update":
        fields.update(
            update_lower_utc="2026-11-22T00:00:00Z",
            update_upper_utc="2026-11-23T00:00:00Z",
        )
    fields.update(overrides)
    return ApiPageRequest(**fields)


def ok(payload=_UNSET, headers=None):
    return httpx.Response(
        200,
        json=[row()] if payload is _UNSET else payload,
        headers=FRESH if headers is None else headers,
    )


class Clock:
    def __init__(self):
        self.elapsed = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.elapsed

    def now(self):
        return NOW + timedelta(seconds=self.elapsed)

    async def sleep(self, delay):
        self.sleeps.append(delay)
        self.elapsed += delay


@pytest.fixture(autouse=True)
def no_live_network(monkeypatch):
    async def deny(*args, **kwargs):
        pytest.fail("live network is forbidden in client unit tests")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", deny)


def fetch(req=None, sequence=None, *, clock=None, calls=None, jitter=lambda _: 0, token=None):
    clock = clock or Clock()
    calls = calls if calls is not None else []
    items = sequence if sequence is not None else [ok()]

    async def handler(http_request):
        item = items[min(len(calls), len(items) - 1)]
        calls.append((clock.elapsed, http_request))
        if isinstance(item, BaseException):
            raise item
        if callable(item):
            item = item(http_request)
            if asyncio.iscoroutine(item):
                item = await item
        return item

    async def run():
        async with ApiClient(
            transport=httpx.MockTransport(handler),
            app_token=token,
            monotonic=clock.monotonic,
            utc_now=clock.now,
            sleeper=clock.sleep,
            jitter=jitter,
        ) as client:
            return await client.fetch_page(req or request())

    return asyncio.run(run())


def expect_error(category, req=None, sequence=None, **kwargs):
    with pytest.raises(IngestionError) as caught:
        fetch(req, sequence, **kwargs)
    assert caught.value.category == category
    return caught.value


def test_creation_query_initial_and_resumed():
    initial = build_query(request(limit=3))
    assert initial["$where"] == (
        "created_date >= '2025-01-01T00:00:00.000' AND created_date < '2025-01-02T00:00:00.000'"
    )
    assert initial["$order"] == "created_date ASC,unique_key ASC"
    assert initial["$limit"] == "3"
    assert "$offset" not in initial
    query = build_query(request(cursor=CreationCursor(CREATED, "10")))
    assert query["$where"].endswith(
        "(created_date > '2025-01-01T12:00:00.000' OR "
        "(created_date = '2025-01-01T12:00:00.000' AND unique_key > '10'))"
    )
    assert "descriptor,status,borough,incident_zip" in query["$select"]
    assert "incident_address" not in query["$select"]


def test_update_query_utc_and_typed_cursor():
    cursor = UpdateCursor("2026-11-22T07:00:00-05:00", "10")
    query = build_query(request("update", cursor=cursor))
    assert cursor.updated_at_utc == datetime(2026, 11, 22, 12, tzinfo=UTC)
    assert query["$order"] == ":updated_at ASC,unique_key ASC"
    assert ":updated_at >= '2026-11-22T00:00:00Z'" in query["$where"]
    assert ":updated_at < '2026-11-23T00:00:00Z'" in query["$where"]
    assert query["$where"].endswith(
        "(:updated_at > '2026-11-22T12:00:00Z' OR "
        "(:updated_at = '2026-11-22T12:00:00Z' AND unique_key > '10'))"
    )


def test_literal_escaping_and_opaque_identity():
    key = "x' OR '1'='1"
    assert literal(key) == "'x'' OR ''1''=''1'"
    assert CreationCursor(CREATED, key).unique_key == key
    assert (
        "unique_key > 'x'' OR ''1''=''1'"
        in build_query(request(cursor=CreationCursor(CREATED, key)))["$where"]
    )


@pytest.mark.parametrize("key", ["", " ", 10, None, "x\n", "x\r", "x\0", "x\x7f"])
def test_invalid_keys(key):
    with pytest.raises(IngestionError, match="configuration"):
        CreationCursor(CREATED, key)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "2025-01-01",
        "2025-99-01T00:00:00",
        42,
        "2025-01-01T00:00:00Z",
        "2025-01-01T00:00:00-05:00",
    ],
)
def test_creation_time_requires_valid_naive_source_value(value):
    with pytest.raises(IngestionError, match="configuration"):
        CreationCursor(value, "10")


@pytest.mark.parametrize("value", ["", "not-a-date", CREATED, 42, None])
def test_update_time_requires_aware_value(value):
    with pytest.raises(IngestionError, match="configuration"):
        UpdateCursor(value, "10")


@pytest.mark.parametrize(
    "fields",
    [
        {"limit": 0},
        {"limit": 5001},
        {"limit": True},
        {"limit": 1.5},
        {"kind": "offset"},
        {"creation_end_source": "2025-01-01T00:00:00.000"},
        {"creation_start_source": "2025-01-03T00:00:00"},
        {"pinned_generation": "2026-11-23T00:00:00"},
        {"update_lower_utc": UPDATED},
        {"cursor": UpdateCursor(UPDATED, "10")},
        {"cursor": CreationCursor("2024-12-31T23:59:59", "10")},
        {"cursor": CreationCursor("2025-01-02T00:00:00", "10")},
    ],
)
def test_invalid_creation_request(fields):
    with pytest.raises(IngestionError, match="configuration"):
        request(**fields)


@pytest.mark.parametrize(
    "fields",
    [
        {"update_lower_utc": None},
        {"update_upper_utc": None},
        {"update_upper_utc": "2026-11-22T00:00:00Z"},
        {"cursor": CreationCursor(CREATED, "10")},
        {"cursor": UpdateCursor("2026-11-23T00:00:00Z", "10")},
        {"cursor": UpdateCursor("2026-11-21T00:00:00Z", "10")},
    ],
)
def test_invalid_update_request(fields):
    with pytest.raises(IngestionError, match="configuration"):
        request("update", **fields)


def test_request_frozen_and_limit_edges():
    for limit in [1, 5000]:
        req = request(limit=limit)
        assert build_query(req)["$limit"] == str(limit)
        with pytest.raises(FrozenInstanceError):
            req.limit = 5


def test_creation_page_text_tie_order_and_preserved_wall_time():
    calls = []
    page = fetch(sequence=[ok([row("10"), row("2")])], calls=calls)
    assert page.next_cursor == CreationCursor(CREATED, "2")
    assert page.records[0]["created_date"] == CREATED
    assert page.received_at_utc == NOW
    assert page.generation == GENERATION
    assert page.request_id == "synthetic-request-1"
    assert not page.exhausted
    assert len(calls) == 1
    assert calls[0][1].extensions["timeout"]["connect"] == 5
    assert calls[0][1].extensions["timeout"]["read"] == 30
    with pytest.raises(TypeError):
        page.http_metadata["out_of_date"] = "true"


def test_update_page_ties_and_offset_normalization():
    req = request("update", cursor=UpdateCursor(UPDATED, "10"))
    page = fetch(req, [ok([row("2", updated="2026-11-22T07:00:00-05:00")])])
    assert page.next_cursor == UpdateCursor(UPDATED, "2")


@pytest.mark.parametrize("kind", ["creation", "update"])
def test_empty_page_retains_supplied_cursor(kind):
    cursor = CreationCursor(CREATED, "10") if kind == "creation" else UpdateCursor(UPDATED, "10")
    req = request(kind, cursor=cursor)
    page = fetch(req, [ok([])])
    assert page.exhausted and page.records == ()
    assert page.next_cursor == cursor
    expect_error("source_freshness_unknown", req, [ok([], headers={})])


def test_optional_fields_missing_and_short_page_not_terminal():
    record = {"unique_key": "fixture-only", "created_date": CREATED}
    page = fetch(request(limit=100), [ok([record])])
    assert len(page.records) == 1 and not page.exhausted
    assert page.records[0] == record


def test_client_does_not_localize_ambiguous_event_time():
    req = request(
        creation_start_source="2025-11-02T00:00:00",
        creation_end_source="2025-11-03T00:00:00",
    )
    page = fetch(req, [ok([row(created="2025-11-02T01:30:00")])])
    assert page.next_cursor.created_date_source == "2025-11-02T01:30:00"


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        "text",
        [None],
        [1],
        [[]],
        [{}],
        [{"unique_key": 10, "created_date": CREATED}],
        [{"unique_key": "10"}],
        [row(created="invalid")],
        [dict(row(), agency=123)],
        [dict(row(), closed_date=42)],
        [dict(row(), closed_date="2025-01-01T13:00:00Z")],
        [dict(row(), **{":updated_at": "2026-11-22T00:00:00"})],
    ],
)
def test_invalid_payloads_fail_without_retry(payload):
    calls = []
    error = expect_error("source_contract", sequence=[ok(payload)], calls=calls)
    assert len(calls) == 1 and not error.retryable


@pytest.mark.parametrize("body", [b"{", b"\xff", b"[NaN]", b"[Infinity]"])
def test_invalid_json(body):
    expect_error("source_contract", sequence=[httpx.Response(200, content=body, headers=FRESH)])


def test_row_limit_and_missing_update_key():
    expect_error("source_contract", request(limit=1), [ok([row("1"), row("2")])])
    expect_error(
        "source_contract",
        request("update"),
        [ok([{"unique_key": "10", "created_date": CREATED}])],
    )


@pytest.mark.parametrize(
    "payload",
    [
        [row("10"), row("10")],
        [row("2"), row("10")],
        [row(created="2025-01-02T00:00:00")],
        [row(created="2024-12-31T23:59:59")],
        [row("10", "2025-01-01T13:00:00"), row("2", CREATED)],
    ],
)
def test_creation_order_or_bounds_violation(payload):
    calls = []
    expect_error("source_order", sequence=[ok(payload)], calls=calls)
    assert len(calls) == 1


@pytest.mark.parametrize("kind", ["creation", "update"])
def test_row_equal_to_cursor_is_not_skipped(kind):
    cursor = CreationCursor(CREATED, "10") if kind == "creation" else UpdateCursor(UPDATED, "10")
    expect_error("source_order", request(kind, cursor=cursor), [ok([row()])])


@pytest.mark.parametrize("updated", ["2026-11-21T23:59:59Z", "2026-11-23T00:00:00Z"])
def test_update_bounds(updated):
    expect_error("source_order", request("update"), [ok([row(updated=updated)])])


def test_update_order_is_system_time_not_creation_time():
    page = fetch(
        request("update"),
        [
            ok(
                [
                    row("10", "2025-01-01T13:00:00", "2026-11-22T12:00:00Z"),
                    row("2", "2025-01-01T11:00:00", "2026-11-22T13:00:00Z"),
                ]
            )
        ],
    )
    assert page.next_cursor == UpdateCursor("2026-11-22T13:00:00Z", "2")
    expect_error(
        "source_order",
        request("update"),
        [
            ok(
                [
                    row("10", updated="2026-11-22T13:00:00Z"),
                    row("2", updated=UPDATED),
                ]
            )
        ],
    )


@pytest.mark.parametrize(
    "field",
    [
        "X-SODA2-Data-Out-Of-Date",
        "X-SODA2-Truth-Last-Modified",
        "X-SODA2-Secondary-Last-Modified",
    ],
)
def test_missing_freshness_is_permanent(field):
    headers = dict(FRESH)
    headers.pop(field)
    calls = []
    error = expect_error("source_freshness_unknown", sequence=[ok(headers=headers)], calls=calls)
    assert len(calls) == 1 and not error.retryable


@pytest.mark.parametrize(
    "changes",
    [
        {"X-SODA2-Data-Out-Of-Date": "maybe"},
        {"X-SODA2-Data-Out-Of-Date": ""},
        {"X-SODA2-Truth-Last-Modified": "bad"},
        {"X-SODA2-Secondary-Last-Modified": "bad"},
        {"X-SODA2-Truth-Last-Modified": "Mon, 23 Nov 2026 02:00:00"},
    ],
)
def test_invalid_freshness(changes):
    expect_error("source_freshness_unknown", sequence=[ok(headers=FRESH | changes)])


def test_case_insensitive_headers_and_flags():
    headers = {k.lower(): v for k, v in FRESH.items()}
    headers["x-soda2-data-out-of-date"] = "  FALSE  "
    assert fetch(sequence=[ok(headers=headers)]).generation == GENERATION


@pytest.mark.parametrize(
    "changes",
    [
        {"X-SODA2-Data-Out-Of-Date": "true"},
        {
            "X-SODA2-Secondary-Last-Modified": format_datetime(
                GENERATION - timedelta(days=1), usegmt=True
            )
        },
    ],
)
def test_stale_or_lagging_secondary_retries(changes):
    calls = []
    clock = Clock()
    page = fetch(
        sequence=[ok(headers=FRESH | changes), ok()],
        calls=calls,
        clock=clock,
        jitter=lambda cap: cap,
    )
    assert page.generation == GENERATION and len(calls) == 2 and clock.sleeps == [1]


@pytest.mark.parametrize(
    "flag,secondary", [("true", GENERATION), ("false", GENERATION - timedelta(days=2))]
)
def test_stale_different_generation_retries_without_accepting_it(flag, secondary):
    calls = []
    clock = Clock()
    old = FRESH | {
        "X-SODA2-Data-Out-Of-Date": flag,
        "X-SODA2-Truth-Last-Modified": format_datetime(GENERATION - timedelta(days=1), usegmt=True),
        "X-SODA2-Secondary-Last-Modified": format_datetime(secondary, usegmt=True),
    }
    page = fetch(
        request(pinned_generation=GENERATION),
        sequence=[ok(headers=old), ok()],
        calls=calls,
        clock=clock,
    )
    assert page.generation == GENERATION and len(calls) == 2
    assert calls[0][1].url == calls[1][1].url


def test_fresh_generation_change_still_fails_immediately():
    calls = []
    error = expect_error(
        "source_generation_changed",
        request(pinned_generation=GENERATION - timedelta(days=1)),
        [ok()],
        calls=calls,
    )
    assert len(calls) == 1 and not error.retryable


def test_stale_generation_mismatch_exhausts_existing_four_attempt_budget():
    calls = []
    stale = FRESH | {"X-SODA2-Data-Out-Of-Date": "true"}
    error = expect_error(
        "source_stale",
        request(pinned_generation=GENERATION - timedelta(days=1)),
        [ok(headers=stale)] * 4,
        calls=calls,
    )
    assert error.retryable and len(calls) == 4
    assert len({str(call[1].url) for call in calls}) == 1


@pytest.mark.parametrize("status", [202, 408, 429, 500, 502, 503, 504])
def test_retryable_http_status_then_success(status):
    calls = []
    clock = Clock()
    page = fetch(sequence=[httpx.Response(status), ok()], calls=calls, clock=clock)
    assert len(calls) == 2 and not page.exhausted and clock.sleeps == [0]


@pytest.mark.parametrize("status", [201, 204, 301, 400, 401, 403, 404, 409, 418, 501])
def test_other_http_errors_fail_immediately(status):
    calls = []
    error = expect_error(
        "api_http",
        sequence=[httpx.Response(status, text="DO_NOT_LOG_BODY")],
        calls=calls,
    )
    assert len(calls) == 1 and not error.retryable


@pytest.mark.parametrize(
    "error_type",
    [
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.ReadError,
        httpx.WriteError,
        httpx.RemoteProtocolError,
    ],
)
def test_transient_transport_errors(error_type):
    calls = []
    page = fetch(sequence=[error_type("SECRET_RAW_ERROR"), ok()], calls=calls)
    assert len(calls) == 2 and page.request_id == "synthetic-request-1"


def test_tls_and_permanent_transport_errors_not_retried():
    cert = httpx.ConnectError("SECRET_RAW_ERROR")
    cert.__cause__ = ssl.SSLCertVerificationError("SECRET_CERT")
    for failure in [
        cert,
        httpx.LocalProtocolError("SECRET"),
        httpx.UnsupportedProtocol("SECRET"),
    ]:
        calls = []
        error = expect_error("api_transport", sequence=[failure], calls=calls)
        assert len(calls) == 1 and not error.retryable and "SECRET" not in str(error)


@pytest.mark.parametrize("mode", ["http", "stale", "transport"])
def test_four_attempts_and_exponential_jitter_ceiling(mode):
    failure = {
        "http": httpx.Response(503),
        "stale": ok(headers=FRESH | {"X-SODA2-Data-Out-Of-Date": "true"}),
        "transport": httpx.ConnectError("dns"),
    }[mode]
    calls = []
    clock = Clock()
    error = expect_error(
        {"http": "api_http", "stale": "source_stale", "transport": "api_transport"}[mode],
        sequence=[failure],
        calls=calls,
        clock=clock,
        jitter=lambda cap: cap,
    )
    assert error.retryable and len(calls) == 4 and clock.sleeps == [1, 2, 4]
    assert [at for at, _ in calls] == [0, 1, 3, 7]


@pytest.mark.parametrize(
    "header", ["10", format_datetime(NOW + timedelta(seconds=10), usegmt=True)]
)
def test_retry_after_minimum_is_not_shortened(header):
    clock = Clock()
    calls = []
    fetch(
        sequence=[httpx.Response(429, headers={"Retry-After": header}), ok()],
        clock=clock,
        calls=calls,
        jitter=lambda _: 0.5,
    )
    assert clock.sleeps == [10.5] and calls[1][0] == 10.5


@pytest.mark.parametrize("header", ["bad-secret", "-5", "1.5", "NaN", ""])
def test_invalid_retry_after_backoff_and_safe_warning(header, caplog):
    clock = Clock()
    with caplog.at_level(logging.WARNING):
        fetch(
            sequence=[httpx.Response(429, headers={"Retry-After": header}), ok()],
            clock=clock,
            jitter=lambda cap: cap,
        )
    assert clock.sleeps == [1]
    assert "invalid_retry_after" in caplog.text and "bad-secret" not in caplog.text


@pytest.mark.parametrize(
    "header",
    ["151", "9" * 100, format_datetime(NOW + timedelta(seconds=151), usegmt=True)],
)
def test_retry_after_cannot_fit_total_budget(header):
    clock = Clock()
    calls = []
    error = expect_error(
        "api_http",
        sequence=[httpx.Response(429, headers={"Retry-After": header})],
        clock=clock,
        calls=calls,
    )
    assert error.retryable and len(calls) == 1 and clock.sleeps == []


def test_exact_remaining_attempt_budget_and_past_date():
    clock = Clock()
    calls = []
    fetch(
        sequence=[httpx.Response(429, headers={"Retry-After": "150"}), ok()],
        clock=clock,
        calls=calls,
    )
    assert calls[1][0] == 150
    clock = Clock()
    fetch(
        sequence=[
            httpx.Response(
                429,
                headers={"Retry-After": format_datetime(NOW - timedelta(seconds=1), usegmt=True)},
            ),
            ok(),
        ],
        clock=clock,
    )
    assert clock.sleeps == [0]


def test_clock_overrun_never_accepts_page_or_starts_another_attempt():
    clock = Clock()
    calls = []

    def late(_):
        clock.elapsed = 180
        return ok()

    error = expect_error("api_transport", sequence=[late], clock=clock, calls=calls)
    assert error.retryable and len(calls) == 1 and clock.sleeps == []


def test_total_attempt_deadline_cancels_stream_read_without_real_sleep(monkeypatch):
    original_timeout = asyncio.timeout
    budgets = []

    def timeout(seconds):
        budgets.append(seconds)
        return original_timeout(0 if seconds == 30 else seconds)

    monkeypatch.setattr(client_module.asyncio, "timeout", timeout)

    class SlowStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"["
            await asyncio.Future()

    calls = []
    error = expect_error(
        "api_transport",
        sequence=[lambda _: httpx.Response(200, headers=FRESH, stream=SlowStream())],
        calls=calls,
    )
    assert error.retryable and len(calls) == 4
    assert budgets == [180, 30, 30, 30, 30]


def test_outer_page_deadline_cancels_waiting_transport(monkeypatch):
    original_timeout = asyncio.timeout

    def timeout(seconds):
        return original_timeout(0 if seconds == 180 else seconds)

    monkeypatch.setattr(client_module.asyncio, "timeout", timeout)

    async def waiting(_):
        await asyncio.Future()

    calls = []
    error = expect_error("api_transport", sequence=[waiting], calls=calls)
    assert error.retryable and len(calls) == 1


def test_no_concurrent_fetch_and_caller_cancellation_releases_guard():
    async def run():
        clock = Clock()
        entered = asyncio.Event()
        release = asyncio.Event()

        async def handler(_):
            entered.set()
            await release.wait()
            return ok()

        async with ApiClient(
            transport=httpx.MockTransport(handler),
            monotonic=clock.monotonic,
            utc_now=clock.now,
            sleeper=clock.sleep,
            jitter=lambda _: 0,
        ) as client:
            pending = asyncio.create_task(client.fetch_page(request()))
            await entered.wait()
            with pytest.raises(IngestionError, match="configuration"):
                await client.fetch_page(request())
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
            release.set()
            assert (await client.fetch_page(request())).generation == GENERATION
        with pytest.raises(IngestionError, match="configuration"):
            await client.fetch_page(request())

    asyncio.run(run())


def test_token_header_only_and_sanitized_diagnostics(caplog):
    calls = []
    token = "SYNTHETIC_TOKEN_NEVER_LOG"
    headers = FRESH | {"X-Socrata-RequestId": token}
    with caplog.at_level(logging.INFO):
        error = expect_error(
            "api_http",
            sequence=[httpx.Response(400, headers=headers, text=token + " SECRET_BODY")],
            calls=calls,
            token=token,
        )
    req = calls[0][1]
    assert req.headers["X-App-Token"] == token and token not in str(req.url)
    assert error.request_id is None
    assert token not in caplog.text + repr(error) and "SECRET_BODY" not in caplog.text
    error = expect_error("api_transport", sequence=[httpx.LocalProtocolError(token)], token=token)
    assert token not in str(error)


@pytest.mark.parametrize("value", ["unsafe request id", "unsafe\nrequest", "x" * 129])
def test_invalid_request_id_not_exposed(value):
    page = fetch(sequence=[ok(headers=FRESH | {"X-Socrata-RequestId": value})])
    assert page.request_id is None


def test_no_token_by_default_and_redirect_not_followed():
    calls = []
    expect_error(
        "api_http",
        sequence=[httpx.Response(302, headers={"Location": "https://not-source.invalid"})],
        calls=calls,
    )
    assert len(calls) == 1 and "X-App-Token" not in calls[0][1].headers


def test_ingestion_import_boundary_has_no_persistence_or_cli_modules():
    root = Path(__file__).resolve().parents[2] / "src" / "nyc311_pipeline" / "ingestion"
    forbidden = {
        "psycopg",
        "sqlalchemy",
        "sqlite3",
        "storage",
        "orchestration",
        "subprocess",
    }
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(set(name.split(".")) & forbidden for name in names)
    # Durable Bronze orchestration is now lead-authorized. The transport client
    # must still remain independent of service/shared persistence contracts.
    client_tree = ast.parse((root / "client.py").read_text())
    assert not any(
        isinstance(node, ast.ImportFrom)
        and (node.module or "").split(".")[-1] in {"service", "bronze_contracts"}
        for node in ast.walk(client_tree)
    )


@pytest.mark.parametrize("token", ["bad\r\nheader", "\u00e9-secret", 42])
def test_invalid_token_configuration_does_not_expose_value(token):
    with pytest.raises(IngestionError, match="configuration") as caught:
        ApiClient(app_token=token)
    assert str(token) not in str(caught.value)


def test_duplicate_json_fields_rejected():
    body = b'[{"unique_key":"10","unique_key":"2","created_date":"2025-01-01T12:00:00"}]'
    expect_error("source_contract", sequence=[httpx.Response(200, headers=FRESH, content=body)])


def test_unicode_control_key_rejected():
    with pytest.raises(IngestionError, match="configuration"):
        CreationCursor(CREATED, "fixture\u0085key")


def test_httpx_source_request_summaries_do_not_log_query_literals(caplog):
    key = "synthetic-sensitive-key"
    req = request(cursor=CreationCursor(CREATED, key))
    with caplog.at_level(logging.INFO):
        fetch(req, [ok([])])
        logging.getLogger("httpx").info("unrelated-summary-kept")
    assert key not in caplog.text
    assert "$where" not in caplog.text and "%24where" not in caplog.text
    assert "nyc311_http_response" in caplog.text
    assert "unrelated-summary-kept" in caplog.text


def test_oversleep_cannot_issue_a_late_retry():
    class OversleepClock(Clock):
        async def sleep(self, delay):
            self.sleeps.append(delay)
            self.elapsed = 151

    clock = OversleepClock()
    calls = []
    error = expect_error("api_http", sequence=[httpx.Response(503)], clock=clock, calls=calls)
    assert error.retryable and len(calls) == 1


def test_retry_after_not_carried_to_subsequent_transport_failure():
    clock = Clock()
    calls = []
    fetch(
        sequence=[
            httpx.Response(429, headers={"Retry-After": "10"}),
            httpx.ConnectError("synthetic DNS failure"),
            ok(),
        ],
        clock=clock,
        calls=calls,
    )
    assert clock.sleeps == [10, 0]
    assert [at for at, _ in calls] == [0, 10, 10]


def test_invalid_content_encoding_and_excessive_json_depth_are_safe_failures():
    calls = []
    error = expect_error(
        "source_contract", sequence=[httpx.DecodingError("SECRET_BODY")], calls=calls
    )
    assert len(calls) == 1 and not error.retryable
    assert "SECRET_BODY" not in str(error)
    deep_json = b"[" * 2000 + b"0" + b"]" * 2000
    expect_error(
        "source_contract",
        sequence=[httpx.Response(200, headers=FRESH, content=deep_json)],
    )


def test_unpaired_unicode_surrogate_cannot_enter_query():
    with pytest.raises(IngestionError, match="configuration"):
        CreationCursor(CREATED, "synthetic\ud800key")
