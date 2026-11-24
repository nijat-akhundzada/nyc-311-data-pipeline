"""Synthetic validation and quality boundaries; no network/database."""

import pytest

from nyc311_pipeline.validation.records import (
    PipelineError,
    QualityError,
    local_to_utc,
    quality_gate,
    validate,
)


def record(**changes):
    return (
        dict(
            unique_key="SYN-1",
            created_date="2025-01-15T12:00:00",
            closed_date="2025-01-15T14:00:00",
            status=" Closed ",
            agency=" syn ",
            **{":updated_at": "2026-11-23T00:00:00Z"},
        )
        | changes
    )


def test_normalize_and_metric():
    result = validate(record())
    assert not result.reasons
    assert result.data["agency"] == "SYN" and result.data["status_key"] == "closed"
    assert result.data["created_date_utc"] == "2025-01-15T17:00:00Z"
    assert result.data["resolution_seconds"] == 7200
    assert result.state_hash == validate(record(status="closed", agency="SYN")).state_hash


@pytest.mark.parametrize(
    "value,reason",
    [
        ("2025-03-09T02:30:00", "nonexistent_local_time"),
        ("2025-11-02T01:30:00", "ambiguous_local_time"),
    ],
)
def test_dst_rejected(value, reason):
    with pytest.raises(ValueError, match=reason):
        local_to_utc(value)
    assert "created_date:" + reason in validate(record(created_date=value)).reasons


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"unique_key": None}, "missing_unique_key"),
        ({"created_date": None}, "created_date:invalid_timestamp"),
        ({"closed_date": "2025-01-14T00:00:00"}, "closed_before_created"),
        ({"agency": 42}, "agency:invalid_type"),
        ({":updated_at": None}, "missing_or_invalid_source_updated_at"),
    ],
)
def test_invalid_reasons(change, reason):
    assert reason in validate(record(**change)).reasons


def test_closed_without_closure_is_valid_but_metric_ineligible():
    result = validate(record(closed_date=None))
    assert not result.reasons and not result.data["metric_eligible"]
    assert result.data["metric_reason"] == "closed_without_closed_date"


def test_exact_threshold_and_zero():
    quality_gate(20, 1)
    quality_gate(100, 5)
    for total, bad in [(20, 2), (0, 0)]:
        with pytest.raises(QualityError):
            quality_gate(total, bad)
    for invalid in ["NaN", "Infinity", "-0.01", "1.01"]:
        with pytest.raises(PipelineError):
            quality_gate(20, 1, invalid)
