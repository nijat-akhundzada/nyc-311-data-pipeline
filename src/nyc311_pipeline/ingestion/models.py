"""Transport-only values. Nothing here represents durable progress."""

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

Category = Literal[
    "configuration",
    "api_transport",
    "api_http",
    "source_freshness_unknown",
    "source_stale",
    "source_generation_changed",
    "source_contract",
    "source_order",
]


class IngestionError(Exception):
    """Safe boundary error: never incorporates source bodies or transport messages."""

    def __init__(
        self,
        category: Category,
        *,
        retryable: bool = False,
        request_id: str | None = None,
    ) -> None:
        self.category = category
        self.retryable = retryable
        self.request_id = request_id
        super().__init__(category)


def validate_key(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or any(unicodedata.category(c) in {"Cc", "Cs"} for c in value)
    ):
        raise IngestionError("configuration")
    return value


def source_time(value: object) -> datetime:
    """Parse source wall time without inventing a zone or changing cursor text."""
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?",
        value,
        flags=re.ASCII,
    ):
        raise IngestionError("configuration")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise IngestionError("configuration") from None


def utc_time(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
        if not isinstance(parsed, datetime) or parsed.utcoffset() is None:
            raise ValueError
        return parsed.astimezone(UTC)
    except (ValueError, TypeError, OverflowError):
        raise IngestionError("configuration") from None


def utc_text(value: datetime) -> str:
    return utc_time(value).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class CreationCursor:
    created_date_source: str
    unique_key: str
    kind: Literal["creation"] = field(default="creation", init=False)

    def __post_init__(self) -> None:
        source_time(self.created_date_source)
        validate_key(self.unique_key)


@dataclass(frozen=True, slots=True)
class UpdateCursor:
    updated_at_utc: datetime | str
    unique_key: str
    kind: Literal["update"] = field(default="update", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "updated_at_utc", utc_time(self.updated_at_utc))
        validate_key(self.unique_key)


Cursor = CreationCursor | UpdateCursor


@dataclass(frozen=True, slots=True)
class ApiPageRequest:
    kind: Literal["creation", "update"]
    creation_start_source: str
    creation_end_source: str
    cursor: Cursor | None = None
    limit: int = 1000
    pinned_generation: datetime | None = None
    update_lower_utc: datetime | str | None = None
    update_upper_utc: datetime | str | None = None

    def __post_init__(self) -> None:
        start, end = (
            source_time(self.creation_start_source),
            source_time(self.creation_end_source),
        )
        if self.kind not in ("creation", "update") or start >= end:
            raise IngestionError("configuration")
        if type(self.limit) is not int or not 1 <= self.limit <= 5000:
            raise IngestionError("configuration")
        if self.pinned_generation is not None:
            object.__setattr__(self, "pinned_generation", utc_time(self.pinned_generation))
        if self.kind == "creation":
            if self.update_lower_utc is not None or self.update_upper_utc is not None:
                raise IngestionError("configuration")
            if self.cursor is not None:
                if not isinstance(self.cursor, CreationCursor):
                    raise IngestionError("configuration")
                if not start <= source_time(self.cursor.created_date_source) < end:
                    raise IngestionError("configuration")
        else:
            lower, upper = (
                utc_time(self.update_lower_utc),
                utc_time(self.update_upper_utc),
            )
            object.__setattr__(self, "update_lower_utc", lower)
            object.__setattr__(self, "update_upper_utc", upper)
            if lower >= upper:
                raise IngestionError("configuration")
            if self.cursor is not None:
                if not isinstance(self.cursor, UpdateCursor):
                    raise IngestionError("configuration")
                if not lower <= utc_time(self.cursor.updated_at_utc) < upper:
                    raise IngestionError("configuration")


@dataclass(frozen=True, slots=True)
class Page:
    records: tuple[Mapping[str, Any], ...]
    next_cursor: Cursor | None
    exhausted: bool
    received_at_utc: datetime
    generation: datetime
    request_id: str | None
    http_metadata: Mapping[str, str]
