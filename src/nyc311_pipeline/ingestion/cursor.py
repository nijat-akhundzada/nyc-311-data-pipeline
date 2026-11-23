"""Validate an entire page before returning a candidate cursor (never a checkpoint)."""

from datetime import datetime
from typing import Any

from .models import (
    ApiPageRequest,
    CreationCursor,
    Cursor,
    IngestionError,
    UpdateCursor,
    source_time,
    utc_time,
    validate_key,
)

_TEXT_FIELDS = (
    "agency",
    "agency_name",
    "complaint_type",
    "descriptor",
    "status",
    "borough",
    "incident_zip",
)
_DATE_FIELDS = ("closed_date", "resolution_action_updated_date")


def cursor_key(cursor: Cursor) -> tuple[datetime, str]:
    if isinstance(cursor, CreationCursor):
        return source_time(cursor.created_date_source), cursor.unique_key
    return utc_time(cursor.updated_at_utc), cursor.unique_key


def validate_records(
    payload: Any, request: ApiPageRequest
) -> tuple[tuple[dict[str, Any], ...], Cursor | None]:
    if not isinstance(payload, list) or len(payload) > request.limit:
        raise IngestionError("source_contract")
    previous = cursor_key(request.cursor) if request.cursor is not None else None
    next_cursor = request.cursor
    for row in payload:
        if not isinstance(row, dict):
            raise IngestionError("source_contract")
        try:
            key = validate_key(row.get("unique_key"))
            created = source_time(row.get("created_date"))
            for name in _TEXT_FIELDS:
                if row.get(name) is not None and not isinstance(row[name], str):
                    raise IngestionError("configuration")
            for name in _DATE_FIELDS:
                if row.get(name) is not None:
                    source_time(row[name])
            if row.get(":updated_at") is not None:
                utc_time(row[":updated_at"])
            current: Cursor = CreationCursor(row["created_date"], key)
            if request.kind == "update":
                updated = utc_time(row.get(":updated_at"))
                current = UpdateCursor(updated, key)
        except IngestionError:
            raise IngestionError("source_contract") from None
        if (
            not source_time(request.creation_start_source)
            <= created
            < source_time(request.creation_end_source)
        ):
            raise IngestionError("source_order")
        if request.kind == "update" and not (
            request.update_lower_utc <= updated < request.update_upper_utc
        ):
            raise IngestionError("source_order")
        current_key = cursor_key(current)
        if previous is not None and current_key <= previous:
            raise IngestionError("source_order")
        previous, next_cursor = current_key, current
    return tuple(payload), next_cursor
