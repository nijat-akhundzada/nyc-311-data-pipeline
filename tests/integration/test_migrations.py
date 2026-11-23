"""PostgreSQL 16 integration tests for the Spec 05 migration foundation.

Every test uses a disposable database created by the ``isolated_db`` fixture.
No bronze/silver/gold domain tables, ops run tables or source data are created.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
import pytest

from nyc311_pipeline.storage.migrations import (
    MIGRATION_LOCK_KEY,
    MigrationChecksumError,
    MigrationError,
    MigrationLockError,
    apply_migrations,
    migration_status,
    rollback_migrations,
)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"
DOMAIN_SCHEMAS = ("bronze", "silver", "gold", "ops")


def _copy_migrations(
    tmp_path: Path, extra: dict[int, tuple[str, str]] | None = None
) -> Path:
    directory = tmp_path / "migrations"
    directory.mkdir()
    for source in sorted(MIGRATIONS_DIR.glob("*.sql")):
        (directory / source.name).write_text(
            source.read_text(encoding="utf-8"), encoding="utf-8"
        )
    for version, (name, script) in (extra or {}).items():
        (directory / f"{version:04d}_{name}.up.sql").write_text(
            script, encoding="utf-8"
        )
    return directory


def _domain_tables(conn: psycopg.Connection) -> list[tuple[str, str]]:
    return conn.execute(
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE table_schema IN ('bronze', 'silver', 'gold', 'ops') ORDER BY table_schema, table_name"
    ).fetchall()


def test_server_is_postgresql_16(maintenance_dsn: str) -> None:
    with psycopg.connect(maintenance_dsn) as conn:
        version = conn.execute("SHOW server_version").fetchone()[0]
    assert version.startswith("16."), (
        f"Spec 05 integration tests target PostgreSQL 16, got {version}"
    )


def test_fresh_migrations_create_four_empty_namespaces(isolated_db: str) -> None:
    result = apply_migrations(isolated_db, migrations_dir=MIGRATIONS_DIR)

    assert result.applied == ("0001_create_namespaces",)
    assert result.skipped == ()
    with psycopg.connect(isolated_db) as conn:
        schemas = {
            row[0]
            for row in conn.execute(
                "SELECT schema_name FROM information_schema.schemata"
            )
        }
        assert set(DOMAIN_SCHEMAS) <= schemas
        assert _domain_tables(conn) == []
        rows = conn.execute(
            "SELECT version, name, checksum FROM _migration.applied_migrations ORDER BY version"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == 1
        assert rows[0][1] == "create_namespaces"
        assert len(rows[0][2]) == 64


def test_reapplying_migrations_is_a_noop(isolated_db: str) -> None:
    apply_migrations(isolated_db, migrations_dir=MIGRATIONS_DIR)
    with psycopg.connect(isolated_db) as conn:
        before = conn.execute(
            "SELECT version, name, checksum, applied_at FROM _migration.applied_migrations"
        ).fetchall()

    second = apply_migrations(isolated_db, migrations_dir=MIGRATIONS_DIR)
    third = apply_migrations(isolated_db, migrations_dir=MIGRATIONS_DIR)

    assert second.applied == ()
    assert second.skipped == ("0001_create_namespaces",)
    assert third.applied == ()
    with psycopg.connect(isolated_db) as conn:
        after = conn.execute(
            "SELECT version, name, checksum, applied_at FROM _migration.applied_migrations"
        ).fetchall()
        assert after == before
        assert _domain_tables(conn) == []


def test_failing_migration_rolls_back_and_corrected_migration_can_run(
    isolated_db: str, tmp_path: Path
) -> None:
    directory = _copy_migrations(
        tmp_path,
        {
            2: (
                "bad_probe",
                "CREATE TABLE bronze.failed_probe (id integer);\nSELECT 1 / 0;\n",
            ),
            3: ("fixed_probe", "CREATE TABLE bronze.fixed_probe (id integer);\n"),
        },
    )

    with pytest.raises(MigrationError, match="0002_bad_probe"):
        apply_migrations(isolated_db, migrations_dir=directory)

    with psycopg.connect(isolated_db) as conn:
        assert (
            conn.execute("SELECT to_regclass('bronze.failed_probe')").fetchone()[0]
            is None
        )
        assert conn.execute(
            "SELECT version FROM _migration.applied_migrations ORDER BY version"
        ).fetchall() == [(1,)]

    (directory / "0002_bad_probe.up.sql").unlink()
    corrected = apply_migrations(isolated_db, migrations_dir=directory)

    assert corrected.applied == ("0003_fixed_probe",)
    with psycopg.connect(isolated_db) as conn:
        assert (
            conn.execute("SELECT to_regclass('bronze.fixed_probe')").fetchone()[0]
            is not None
        )
        assert conn.execute(
            "SELECT version FROM _migration.applied_migrations ORDER BY version"
        ).fetchall() == [
            (1,),
            (3,),
        ]


def test_rollback_removes_namespace_and_ledger_entry(isolated_db: str) -> None:
    apply_migrations(isolated_db, migrations_dir=MIGRATIONS_DIR)

    result = rollback_migrations(
        isolated_db, target_version=0, migrations_dir=MIGRATIONS_DIR
    )

    assert result.rolled_back == ("0001_create_namespaces",)
    with psycopg.connect(isolated_db) as conn:
        schemas = {
            row[0]
            for row in conn.execute(
                "SELECT schema_name FROM information_schema.schemata"
            )
        }
        assert not set(DOMAIN_SCHEMAS) & schemas
        assert (
            conn.execute(
                "SELECT count(*) FROM _migration.applied_migrations"
            ).fetchone()[0]
            == 0
        )

    assert apply_migrations(isolated_db, migrations_dir=MIGRATIONS_DIR).applied == (
        "0001_create_namespaces",
    )


def test_edited_applied_migration_is_rejected(isolated_db: str, tmp_path: Path) -> None:
    directory = _copy_migrations(tmp_path)
    apply_migrations(isolated_db, migrations_dir=directory)

    script = directory / "0001_create_namespaces.up.sql"
    script.write_text(
        script.read_text(encoding="utf-8") + "-- edited after apply\n", encoding="utf-8"
    )

    with pytest.raises(MigrationChecksumError, match="changed after application"):
        apply_migrations(isolated_db, migrations_dir=directory)


def test_concurrent_migrations_serialize_without_duplicate_application(
    isolated_db: str, tmp_path: Path
) -> None:
    directory = _copy_migrations(
        tmp_path, {2: ("slow_probe", "SELECT pg_sleep(0.4);\n")}
    )

    def run() -> tuple[str, ...]:
        return apply_migrations(isolated_db, migrations_dir=directory).applied

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run) for _ in range(2)]
        results = [future.result(timeout=30) for future in futures]

    assert sorted(label for labels in results for label in labels) == [
        "0001_create_namespaces",
        "0002_slow_probe",
    ]
    with psycopg.connect(isolated_db) as conn:
        rows = conn.execute(
            "SELECT version, count(*) FROM _migration.applied_migrations GROUP BY version ORDER BY version"
        ).fetchall()
        assert rows == [(1, 1), (2, 1)]
        assert _domain_tables(conn) == []


def test_lock_contention_fails_with_clear_error(isolated_db: str) -> None:
    with psycopg.connect(isolated_db, autocommit=True) as holder:
        holder.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK_KEY,))
        try:
            with pytest.raises(MigrationLockError, match="another migration process"):
                apply_migrations(isolated_db, lock_timeout_seconds=0.1)
        finally:
            holder.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK_KEY,))

    report = migration_status(isolated_db)
    assert report.applied == ()
    assert [migration.label for migration in report.pending] == [
        "0001_create_namespaces"
    ]
