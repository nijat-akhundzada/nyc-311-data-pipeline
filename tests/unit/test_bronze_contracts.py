"""Synthetic contract/serialization tests; no source data or network."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from nyc311_pipeline.bronze_contracts import (
    Checkpoint,
    IngestScope,
    cursor_document,
    fingerprint,
    parse_cursor,
)
from nyc311_pipeline.ingestion.models import CreationCursor, IngestionError, UpdateCursor

INTERVAL = (("2025-01-01T00:00:00", "2025-01-02T00:00:00"),)


def test_frozen_scope_round_trip_and_separate_kinds():
    scope = IngestScope(INTERVAL)
    assert IngestScope.from_document(scope.document()) == scope
    update = IngestScope(
        INTERVAL,
        "update",
        update_lower_utc="2026-01-01T00:00:00Z",
        update_upper_utc="2026-01-02T00:00:00Z",
    )
    assert update.scope_id != scope.scope_id
    assert IngestScope(INTERVAL, page_size=2).scope_id != scope.scope_id
    assert scope.segment_ids == ("0",)
    assert update.request("0").kind == "update"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"intervals": ()},
        {"intervals": list(INTERVAL)},
        {"page_size": True},
        {"page_size": 0},
        {"page_size": 5001},
        {"dataset_id": "other"},
        {"kind": "other"},
        {"kind": "update"},
        {"intervals": INTERVAL + INTERVAL},
        {"intervals": ((INTERVAL[0][1], INTERVAL[0][0]),)},
    ],
)
def test_invalid_scopes_rejected(kwargs):
    with pytest.raises(IngestionError):
        IngestScope(**(dict(intervals=INTERVAL) | kwargs))


@pytest.mark.parametrize(
    "cursor",
    [
        None,
        CreationCursor("2025-01-01T12:00:00.000", "0010"),
        UpdateCursor("2026-01-01T01:00:00+01:00", "10"),
    ],
)
def test_typed_cursor_and_checkpoint_round_trip(cursor):
    assert parse_cursor(cursor_document(cursor)) == cursor
    cp = Checkpoint(uuid4(), "0", 1, cursor, datetime(2026, 1, 1, tzinfo=UTC))
    assert Checkpoint.from_document(cp.document()) == cp


def test_raw_hash_includes_metadata_and_preserves_json_types():
    assert fingerprint({"b": 2, "a": 1}) == fingerprint({"a": 1, "b": 2})
    assert fingerprint({"a": "1"}) != fingerprint({"a": 1})
    assert fingerprint({"a": 1, ":updated_at": "x"}) != fingerprint({"a": 1})
    with pytest.raises(ValueError):
        fingerprint({"a": float("nan")})


def test_unknown_segment_and_mutated_config_fail():
    scope = IngestScope(INTERVAL)
    with pytest.raises(IngestionError):
        scope.request("01")
    with pytest.raises(IngestionError):
        IngestScope.from_document(scope.document() | {"client_policy": "permissive"})
