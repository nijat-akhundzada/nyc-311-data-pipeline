"""Conservative observed-header policy, not provider snapshot isolation."""

from collections.abc import Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from .models import IngestionError


def http_date(value: str) -> datetime:
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.utcoffset() is None:
            raise ValueError
        return parsed.astimezone(UTC)
    except (ValueError, TypeError, OverflowError, IndexError):
        raise IngestionError("source_freshness_unknown") from None


def validate_freshness(headers: Mapping[str, str], pinned: datetime | None) -> datetime:
    fields = {key.lower(): value for key, value in headers.items()}
    try:
        flag = fields["x-soda2-data-out-of-date"].strip().lower()
        truth = http_date(fields["x-soda2-truth-last-modified"])
        secondary = http_date(fields["x-soda2-secondary-last-modified"])
    except KeyError:
        raise IngestionError("source_freshness_unknown") from None
    if flag not in ("true", "false"):
        raise IngestionError("source_freshness_unknown")
    if pinned is not None and truth != pinned:
        raise IngestionError("source_generation_changed")
    if flag == "true" or secondary < truth:
        raise IngestionError("source_stale", retryable=True)
    return truth
