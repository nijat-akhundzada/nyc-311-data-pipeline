"""Bounded retry decisions, independent of transport and real sleeping."""

import math
import re
from collections.abc import Callable
from datetime import datetime

from .freshness import http_date
from .models import IngestionError

MAX_ATTEMPTS = 4
CONNECT_SECONDS = 5.0
ATTEMPT_SECONDS = 30.0
PAGE_SECONDS = 180.0
RETRY_STATUSES = frozenset({202, 408, 429, 500, 502, 503, 504})


def retry_delay(
    attempt: int,
    retry_after: str | None,
    now: datetime,
    jitter: Callable[[float], float],
) -> tuple[float, bool]:
    ceiling = min(30.0, float(2 ** (attempt - 1)))
    noise = jitter(ceiling)
    if not math.isfinite(noise) or not 0 <= noise <= ceiling:
        raise IngestionError("configuration")
    if retry_after is None:
        return noise, False
    value = retry_after.strip()
    if re.fullmatch(r"[0-9]+", value):
        # A huge but valid minimum wait must not become an early retry.
        seconds = math.inf if len(value) > 12 else float(value)
        return seconds + noise, False
    try:
        seconds = max(0.0, (http_date(value) - now).total_seconds())
        return seconds + noise, False
    except IngestionError:
        return noise, True
