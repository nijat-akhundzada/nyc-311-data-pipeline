"""CLI parsing and UTC window selection, without network access."""

from datetime import UTC, datetime

import pytest

from nyc311_pipeline.cli import main, utc_bound
from nyc311_pipeline.orchestration.pipeline import bounds


def test_utc_windows_superset_handles_fall_back():
    start, end = utc_bound("2025-11-02T05:45:00Z"), utc_bound("2025-11-02T06:15:00Z")
    interval = bounds(start, end)[0]
    assert interval[0] < "2025-11-02T01:15:00" < interval[1]
    assert utc_bound("2025-01-01") == datetime(2025, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    "argv",
    [
        ["run"],
        ["run", "--start", "bad"],
        ["run", "--start", "2025-01-01", "--end", "2025-01-02", "--max-records", "0"],
        ["run", "--start", "2025-01-01", "--end", "2025-01-02", "--quality-threshold", "NaN"],
    ],
)
def test_cli_invalid_arguments_exit_2(argv):
    with pytest.raises(SystemExit) as caught:
        main(argv)
    assert caught.value.code == 2


def test_database_startup_retries_are_bounded(monkeypatch):
    import psycopg

    import nyc311_pipeline.cli as cli
    from nyc311_pipeline.bronze_contracts import StorageError

    attempts, sleeps = [], []

    def unavailable(*args, **kwargs):
        attempts.append(kwargs)
        raise psycopg.OperationalError("synthetic unavailable database")

    monkeypatch.setattr(cli.psycopg, "connect", unavailable)
    monkeypatch.setattr(cli.time, "sleep", sleeps.append)
    with pytest.raises(StorageError):
        cli.connect("synthetic-only")
    assert len(attempts) == 3 and sleeps == [1, 2]


def test_missing_database_configuration_exit_2(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main(["health"]) == 2
    assert '"category": "configuration"' in capsys.readouterr().out


def test_invalid_environment_threshold_rejected_before_database(monkeypatch):
    monkeypatch.setenv("QUALITY_MAX_INVALID_RATE", "NaN")
    with pytest.raises(SystemExit) as caught:
        main(["run", "--start", "2025-01-01", "--end", "2026-01-01"])
    assert caught.value.code == 2
