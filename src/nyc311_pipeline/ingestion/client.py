"""Async, one-page source adapter with cancellable total deadlines. No persistence."""

import asyncio
import json
import logging
import random
import re
import ssl
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from types import MappingProxyType

import httpx

from .cursor import validate_records
from .freshness import http_date, validate_freshness
from .models import ApiPageRequest, IngestionError, Page, utc_text, utc_time
from .query import build_query
from .retry import (
    ATTEMPT_SECONDS,
    CONNECT_SECONDS,
    MAX_ATTEMPTS,
    PAGE_SECONDS,
    RETRY_STATUSES,
    retry_delay,
)

SOURCE_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
_LOG = logging.getLogger(__name__)


class _SourceRequestLogFilter(logging.Filter):
    """Remove source query literals from HTTPX's optional INFO request summary."""

    def filter(self, record: logging.LogRecord) -> bool:
        if SOURCE_URL in record.getMessage():
            record.msg, record.args = "nyc311_http_response", ()
        return True


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _security_failure(error: BaseException) -> bool:
    seen: set[int] = set()
    while id(error) not in seen:
        if isinstance(error, ssl.SSLError):
            return True
        seen.add(id(error))
        parent = error.__cause__ or error.__context__
        if parent is None:
            return False
        error = parent
    return False


def _invalid_constant(_: str) -> None:
    raise ValueError


class ApiClient:
    """Use ``async with`` and ``await fetch_page(request)``; one caller at a time.

    The injected clock/sleeper/jitter make retry decisions deterministic. asyncio
    timeout contexts independently cancel real I/O, unlike per-socket timeouts.
    """

    def __init__(
        self,
        *,
        app_token: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
        jitter: Callable[[float], float] = lambda ceiling: random.uniform(0, ceiling),
    ) -> None:
        if app_token is not None and (
            not isinstance(app_token, str)
            or not app_token.isascii()
            or any(ord(c) < 32 or ord(c) == 127 for c in app_token)
        ):
            raise IngestionError("configuration")
        self._token = app_token
        http_log = logging.getLogger("httpx")
        if not any(
            isinstance(item, _SourceRequestLogFilter) for item in http_log.filters
        ):
            http_log.addFilter(_SourceRequestLogFilter())
        self._http = httpx.AsyncClient(
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
            headers={"X-App-Token": app_token} if app_token else {},
        )
        self._clock, self._now = monotonic, utc_now
        self._sleep, self._jitter = sleeper, jitter
        self._busy = False

    async def __aenter__(self) -> "ApiClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    def _request_id(self, response: httpx.Response) -> str | None:
        value = response.headers.get("X-Socrata-RequestId", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
            return None
        if self._token and self._token in value:
            return None
        return value

    async def fetch_page(self, request: ApiPageRequest) -> Page:
        if (
            not isinstance(request, ApiPageRequest)
            or self._busy
            or self._http.is_closed
        ):
            raise IngestionError("configuration")
        self._busy = True
        deadline = self._clock() + PAGE_SECONDS
        try:
            async with asyncio.timeout(PAGE_SECONDS):
                return await self._fetch(request, deadline)
        except TimeoutError:
            raise IngestionError("api_transport", retryable=True) from None
        finally:
            self._busy = False

    async def _fetch(self, request: ApiPageRequest, deadline: float) -> Page:
        params = build_query(request)
        for attempt in range(1, MAX_ATTEMPTS + 1):
            remaining = deadline - self._clock()
            if remaining <= 0:
                raise IngestionError("api_transport", retryable=True)
            started = self._clock()
            response = None
            request_id = None
            try:
                async with asyncio.timeout(min(ATTEMPT_SECONDS, remaining)):
                    response = await self._http.get(
                        SOURCE_URL,
                        params=params,
                        timeout=httpx.Timeout(
                            min(ATTEMPT_SECONDS, remaining),
                            connect=min(CONNECT_SECONDS, remaining),
                        ),
                    )
                    request_id = self._request_id(response)
                    if (
                        self._clock() - started >= ATTEMPT_SECONDS
                        or self._clock() >= deadline
                    ):
                        raise TimeoutError
                    if response.status_code != 200:
                        raise IngestionError(
                            "api_http",
                            retryable=response.status_code in RETRY_STATUSES,
                        )
                    generation = validate_freshness(
                        response.headers, request.pinned_generation
                    )
                    try:
                        payload = json.loads(
                            response.content,
                            parse_constant=_invalid_constant,
                            object_pairs_hook=_unique_object,
                        )
                    except (ValueError, UnicodeError, RecursionError):
                        raise IngestionError("source_contract") from None
                    records, cursor = validate_records(payload, request)
                    page = Page(
                        records=records,
                        next_cursor=cursor,
                        exhausted=not records,
                        received_at_utc=utc_time(self._now()),
                        generation=generation,
                        request_id=request_id,
                        http_metadata=MappingProxyType(
                            {
                                "status_code": "200",
                                "out_of_date": "false",
                                "truth_last_modified": utc_text(generation),
                                "secondary_last_modified": utc_text(
                                    http_date(
                                        response.headers[
                                            "X-SODA2-Secondary-Last-Modified"
                                        ],
                                    )
                                ),
                            }
                        ),
                    )
                    if (
                        self._clock() - started >= ATTEMPT_SECONDS
                        or self._clock() >= deadline
                    ):
                        raise TimeoutError
                    return page
            except TimeoutError:
                error = IngestionError(
                    "api_transport", retryable=True, request_id=request_id
                )
            except httpx.DecodingError:
                error = IngestionError("source_contract", request_id=request_id)
            except httpx.TransportError as exc:
                retryable = isinstance(
                    exc,
                    httpx.TimeoutException
                    | httpx.NetworkError
                    | httpx.RemoteProtocolError,
                ) and not _security_failure(exc)
                error = IngestionError("api_transport", retryable=retryable)
            except IngestionError as exc:
                error = IngestionError(
                    exc.category, retryable=exc.retryable, request_id=request_id
                )
            if not error.retryable or attempt == MAX_ATTEMPTS:
                raise error from None
            delay, invalid = retry_delay(
                attempt,
                response.headers.get("Retry-After") if response is not None else None,
                utc_time(self._now()),
                self._jitter,
            )
            if invalid:
                _LOG.warning(
                    "invalid_retry_after", extra={"category": "invalid_retry_after"}
                )
            # Do not start a wait/attempt which cannot fit the remaining budget.
            if delay + ATTEMPT_SECONDS > deadline - self._clock():
                raise error from None
            await self._sleep(delay)
            if deadline - self._clock() < ATTEMPT_SECONDS:
                raise error from None
        raise AssertionError("unreachable retry state")
