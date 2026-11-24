"""Provisional New York wall times, with explicit fold/gap rejection."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from importlib.metadata import version
from importlib.resources import files
from zoneinfo import ZoneInfo

from nyc311_pipeline.bronze_contracts import fingerprint
from nyc311_pipeline.ingestion.models import IngestionError, source_time, utc_text, utc_time

with files("tzdata").joinpath("zoneinfo/America/New_York").open("rb") as _zone_file:
    SOURCE_ZONE = ZoneInfo.from_file(_zone_file, key="America/New_York")
TZDATA_VERSION = version("tzdata")
POLICY = "functional-v1"


class PipelineError(RuntimeError):
    code = 5
    retryable = False

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


class QualityError(PipelineError):
    code = 4


def local_to_utc(value: str) -> datetime:
    wall = source_time(value)
    candidates = set()
    for fold in (0, 1):
        candidate = wall.replace(tzinfo=SOURCE_ZONE, fold=fold).astimezone(UTC)
        if candidate.astimezone(SOURCE_ZONE).replace(tzinfo=None) == wall:
            candidates.add(candidate)
    if len(candidates) != 1:
        raise ValueError("ambiguous_local_time" if candidates else "nonexistent_local_time")
    return candidates.pop()


def text(value: object, *, upper: bool = False) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or "\x00" in value:
        raise ValueError("invalid_type")
    value.encode("utf-8")
    result = value.strip() or None
    return result.upper() if result and upper else result


@dataclass(frozen=True)
class Validation:
    data: dict | None
    reasons: tuple[str, ...]
    business_hash: str | None = None
    state_hash: str | None = None


def validate(record: dict) -> Validation:
    reasons = set()
    data = {}
    try:
        key = record.get("unique_key")
        if not isinstance(key, str) or not key.strip():
            raise ValueError
        data["unique_key"] = key
    except ValueError:
        reasons.add("missing_unique_key")
    for field in ("created_date", "closed_date", "resolution_action_updated_date"):
        value = record.get(field)
        data[field + "_source"] = value
        if value is None and field != "created_date":
            data[field + "_utc"] = None
            continue
        try:
            data[field + "_utc"] = utc_text(local_to_utc(value))
        except ValueError as error:
            reasons.add(field + ":" + str(error))
        except (IngestionError, TypeError, OverflowError):
            reasons.add(field + ":invalid_timestamp")
    for field in ("agency", "agency_name", "complaint_type", "status", "borough", "incident_zip"):
        try:
            data[field] = text(record.get(field), upper=field == "agency")
        except (ValueError, UnicodeError):
            reasons.add(field + ":invalid_type")
    try:
        data["source_updated_at"] = utc_text(utc_time(record.get(":updated_at")))
    except IngestionError:
        reasons.add("missing_or_invalid_source_updated_at")
    created, closed = data.get("created_date_utc"), data.get("closed_date_utc")
    if created and closed and utc_time(closed) < utc_time(created):
        reasons.add("closed_before_created")
    if reasons:
        return Validation(None, tuple(sorted(reasons)))
    data["status_key"] = (data["status"] or "").casefold() or None
    data["metric_eligible"] = data["status_key"] == "closed" and closed is not None
    data["metric_reason"] = (
        "closed_without_closed_date" if data["status_key"] == "closed" and closed is None else None
    )
    data["resolution_seconds"] = (
        (utc_time(closed) - utc_time(created)).total_seconds() if data["metric_eligible"] else None
    )
    business = {
        k: v
        for k, v in data.items()
        if k not in {"source_updated_at", "status"} and not k.endswith("_source")
    }
    tracked = [data["status_key"], data["agency"], data["complaint_type"]]
    return Validation(data, (), fingerprint(business), fingerprint(tracked))


def quality_gate(evaluated: int, invalid: int, threshold: str = "0.05") -> None:
    limit = Decimal(threshold)
    if not limit.is_finite() or not 0 <= limit <= 1:
        raise PipelineError("configuration")
    if evaluated <= 0 or invalid < 0 or invalid > evaluated:
        raise QualityError("zero_or_invalid_quality_counts")
    if Decimal(invalid) > Decimal(evaluated) * limit:
        raise QualityError("quality_threshold_exceeded")
