"""Lead-authorized Bronze v1 boundary; no publication or source-completeness claim."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from .ingestion.models import (
    ApiPageRequest,
    CreationCursor,
    Cursor,
    IngestionError,
    UpdateCursor,
    source_time,
    utc_text,
    utc_time,
)
from .ingestion.query import PROJECTION


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def cursor_document(cursor: Cursor | None) -> dict[str, str] | None:
    if cursor is None:
        return None
    if isinstance(cursor, CreationCursor):
        return dict(
            kind="creation",
            created_date_source=cursor.created_date_source,
            unique_key=cursor.unique_key,
        )
    return dict(
        kind="update", updated_at_utc=utc_text(cursor.updated_at_utc), unique_key=cursor.unique_key
    )


def parse_cursor(value: dict[str, str] | None) -> Cursor | None:
    if value is None:
        return None
    if value.get("kind") == "creation":
        return CreationCursor(value["created_date_source"], value["unique_key"])
    if value.get("kind") == "update":
        return UpdateCursor(value["updated_at_utc"], value["unique_key"])
    raise IngestionError("configuration")


@dataclass(frozen=True)
class IngestScope:
    """Explicit source-wall-time intervals, not implicit UTC/DST conversion.

    Each interval has a stable zero-based segment ID. Page size and policy are
    frozen; invocation record caps are deliberately absent from scope identity.
    """

    intervals: tuple[tuple[str, str], ...]
    kind: Literal["creation", "update"] = "creation"
    page_size: int = 1000
    update_lower_utc: datetime | str | None = None
    update_upper_utc: datetime | str | None = None
    dataset_id: str = "erm2-nwe9"

    def __post_init__(self) -> None:
        if (
            self.dataset_id != "erm2-nwe9"
            or not isinstance(self.intervals, tuple)
            or not self.intervals
        ):
            raise IngestionError("configuration")
        previous_end = None
        for interval in self.intervals:
            if not isinstance(interval, tuple) or len(interval) != 2:
                raise IngestionError("configuration")
            start, end = interval
            self.request_for_bounds(start, end)
            if previous_end is not None and source_time(start) < previous_end:
                raise IngestionError("configuration")
            previous_end = source_time(end)
        if self.kind == "update":
            object.__setattr__(self, "update_lower_utc", utc_time(self.update_lower_utc))
            object.__setattr__(self, "update_upper_utc", utc_time(self.update_upper_utc))

    def request_for_bounds(self, start: str, end: str, **kwargs: Any) -> ApiPageRequest:
        return ApiPageRequest(
            self.kind,
            start,
            end,
            limit=kwargs.pop("limit", self.page_size),
            update_lower_utc=self.update_lower_utc,
            update_upper_utc=self.update_upper_utc,
            **kwargs,
        )

    def request(self, segment_id: str, **kwargs: Any) -> ApiPageRequest:
        if segment_id not in self.segment_ids:
            raise IngestionError("configuration")
        return self.request_for_bounds(*self.intervals[int(segment_id)], **kwargs)

    @property
    def segment_ids(self) -> tuple[str, ...]:
        return tuple(str(i) for i in range(len(self.intervals)))

    def document(self) -> dict[str, Any]:
        return dict(
            contract_version="bronze-v1",
            dataset_id=self.dataset_id,
            kind=self.kind,
            intervals=self.intervals,
            page_size=self.page_size,
            update_lower_utc=utc_text(self.update_lower_utc)
            if self.update_lower_utc is not None
            else None,
            update_upper_utc=utc_text(self.update_upper_utc)
            if self.update_upper_utc is not None
            else None,
            source_event_timezone="America/New_York",
            timezone_policy="provisional-wall-v1",
            client_policy="adr001-strict-v1",
            projection=PROJECTION,
        )

    @property
    def scope_id(self) -> str:
        return fingerprint(self.document())

    @classmethod
    def from_document(cls, value: dict[str, Any]) -> "IngestScope":
        scope = cls(
            tuple(tuple(i) for i in value["intervals"]),
            kind=value["kind"],
            page_size=value["page_size"],
            update_lower_utc=value["update_lower_utc"],
            update_upper_utc=value["update_upper_utc"],
            dataset_id=value["dataset_id"],
        )
        if canonical_json(scope.document()) != canonical_json(value):
            raise IngestionError("configuration")
        return scope


@dataclass(frozen=True)
class Checkpoint:
    run_id: UUID
    segment_id: str
    page_no: int = 0
    cursor: Cursor | None = None
    generation: datetime | None = None
    exhausted: bool = False

    def document(self) -> dict[str, Any]:
        return dict(
            run_id=str(self.run_id),
            segment_id=self.segment_id,
            page_no=self.page_no,
            cursor=cursor_document(self.cursor),
            generation=utc_text(self.generation) if self.generation else None,
            exhausted=self.exhausted,
        )

    @classmethod
    def from_document(cls, value: dict[str, Any]) -> "Checkpoint":
        return cls(
            UUID(value["run_id"]),
            value["segment_id"],
            value["page_no"],
            parse_cursor(value["cursor"]),
            utc_time(value["generation"]) if value["generation"] else None,
            value["exhausted"],
        )


@dataclass(frozen=True)
class CommitResult:
    checkpoint: Checkpoint
    received_count: int
    inserted_raw_versions: int
    page_no: int
    replayed: bool = False


@dataclass(frozen=True)
class IngestRun:
    run_id: UUID
    scope: IngestScope
    status: str
    ingest_complete: bool
    received_count: int
    raw_inserted_count: int
    generation: datetime | None


class StorageError(RuntimeError):
    """Sanitized DB boundary. A connection error does not imply rollback."""

    category = "storage"

    def __init__(self, *, retryable: bool = False) -> None:
        self.retryable = retryable
        super().__init__(self.category)


class RunConflict(StorageError):
    category = "run_conflict"
