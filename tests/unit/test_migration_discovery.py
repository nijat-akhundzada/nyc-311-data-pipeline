"""Database-free checks for migration file discovery and checksums."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from nyc311_pipeline.storage.migrations import (
    MigrationError,
    discover_migrations,
    redact_dsn,
)


def _write(directory: Path, name: str, body: str = "SELECT 1;\n") -> None:
    # write_bytes keeps the checksum assertion independent of platform newlines.
    (directory / name).write_bytes(body.encode("utf-8"))


def test_discovery_orders_versions_and_returns_checksums(tmp_path: Path) -> None:
    _write(tmp_path, "0002_second.up.sql", "SELECT 2;\n")
    _write(tmp_path, "0001_first.up.sql", "SELECT 1;\n")
    _write(tmp_path, "0001_first.down.sql", "SELECT -1;\n")

    migrations = discover_migrations(tmp_path)

    assert [migration.label for migration in migrations] == [
        "0001_first",
        "0002_second",
    ]
    assert migrations[0].down_path is not None
    assert migrations[1].down_path is None
    assert migrations[0].checksum == hashlib.sha256(b"SELECT 1;\n").hexdigest()


def test_duplicate_versions_are_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "0001_first.up.sql")
    _write(tmp_path, "0001_other.up.sql")

    with pytest.raises(MigrationError, match="duplicate up migration"):
        discover_migrations(tmp_path)


def test_malformed_filename_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "0001_first.up.sql")
    _write(tmp_path, "notes.sql")

    with pytest.raises(MigrationError, match="unexpected migration filename"):
        discover_migrations(tmp_path)


def test_down_without_matching_up_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "0001_first.up.sql")
    _write(tmp_path, "0002_orphan.down.sql")

    with pytest.raises(MigrationError, match="no up migration"):
        discover_migrations(tmp_path)


def test_redact_dsn_hides_password() -> None:
    dsn = "postgresql://user:secret@localhost:5432/nyc311"
    assert redact_dsn(dsn) == "postgresql://user:***@localhost:5432/nyc311"
