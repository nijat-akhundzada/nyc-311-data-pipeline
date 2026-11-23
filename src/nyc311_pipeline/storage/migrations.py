"""Small ordered SQL migration runner for the NYC 311 database foundation.

The runner is intentionally source-independent: it owns only migration
bookkeeping (a private ``_migration`` schema and its ledger table) and applies
numbered ``*.up.sql`` / ``*.down.sql`` files in version order.  A session-level
PostgreSQL advisory lock serialises concurrent invocations; each migration and
its ledger row are committed in the same transaction, so a failed script cannot
leave a partial schema change or a false "applied" record.

This module is not a pipeline repository and creates no domain tables.  Domain
DDL remains blocked on the reviewed shared contract (Spec 01).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql

MIGRATION_SCHEMA = "_migration"
LEDGER_TABLE = "applied_migrations"
DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "db" / "migrations"

_FILENAME_RE = re.compile(
    r"^(?P<version>\d{4,})_(?P<name>[a-z0-9][a-z0-9_]*)\.(?P<direction>up|down)\.sql$"
)


def _derive_lock_key(namespace: str) -> int:
    """Derive a stable signed bigint; keep this namespace distinct from run locks."""
    digest = hashlib.sha256(namespace.encode("utf-8")).digest()[:8]
    return int.from_bytes(digest, byteorder="big", signed=True)


MIGRATION_LOCK_KEY = _derive_lock_key("nyc311:migrations")


class MigrationError(RuntimeError):
    """A migration could not be discovered, validated or applied."""


class MigrationLockError(MigrationError):
    """Another migration invocation holds the exclusive advisory lock."""


class MigrationChecksumError(MigrationError):
    """An already applied migration file changed after it was recorded."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    up_path: Path
    down_path: Path | None
    checksum: str

    @property
    def label(self) -> str:
        return f"{self.version:04d}_{self.name}"


@dataclass(frozen=True)
class LedgerEntry:
    version: int
    name: str
    checksum: str
    applied_at: datetime


@dataclass(frozen=True)
class MigrationRunResult:
    applied: tuple[str, ...]
    skipped: tuple[str, ...] = ()


@dataclass(frozen=True)
class RollbackResult:
    rolled_back: tuple[str, ...]
    kept: tuple[str, ...] = ()


@dataclass(frozen=True)
class MigrationStatus:
    applied: tuple[LedgerEntry, ...]
    pending: tuple[Migration, ...]


def redact_dsn(dsn: str) -> str:
    """Return a DSN safe to print (password replaced, other fields retained)."""
    parts = urlsplit(dsn)
    if parts.password is None:
        return dsn
    host = parts.hostname or ""
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    netloc = f"{parts.username or ''}:***@{host}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def discover_migrations(
    directory: Path | str = DEFAULT_MIGRATIONS_DIR,
) -> tuple[Migration, ...]:
    """Parse, validate and order migration files by numeric version prefix."""
    root = Path(directory)
    if not root.is_dir():
        raise MigrationError(f"migrations directory does not exist: {root}")

    ups: dict[int, tuple[str, Path]] = {}
    downs: dict[int, tuple[str, Path]] = {}
    for path in sorted(root.glob("*.sql")):
        match = _FILENAME_RE.fullmatch(path.name)
        if match is None:
            raise MigrationError(f"unexpected migration filename: {path.name}")
        version = int(match.group("version"))
        name = match.group("name")
        direction = match.group("direction")
        target = ups if direction == "up" else downs
        if version in target:
            raise MigrationError(
                f"duplicate {direction} migration for version {version}: {path.name}"
            )
        target[version] = (name, path)

    for version, (name, path) in downs.items():
        if version not in ups:
            raise MigrationError(f"down migration has no up migration: {path.name}")
        if ups[version][0] != name:
            raise MigrationError(
                f"down migration name {name!r} does not match up migration "
                f"{ups[version][0]!r} for version {version}"
            )

    if not ups:
        raise MigrationError(f"no up migrations found in {root}")

    return tuple(
        Migration(
            version=version,
            name=ups[version][0],
            up_path=ups[version][1],
            down_path=downs.get(version, (None, None))[1],
            checksum=_sha256(ups[version][1]),
        )
        for version in sorted(ups)
    )


def _ledger_ident() -> sql.Identifier:
    return sql.Identifier(MIGRATION_SCHEMA, LEDGER_TABLE)


def ledger_exists(conn: psycopg.Connection[Any]) -> bool:
    qualified = f"{MIGRATION_SCHEMA}.{LEDGER_TABLE}"
    return bool(conn.execute("SELECT to_regclass(%s)", (qualified,)).fetchone()[0])


def read_ledger(conn: psycopg.Connection[Any]) -> tuple[LedgerEntry, ...]:
    statement = sql.SQL(
        "SELECT version, name, checksum, applied_at FROM {} ORDER BY version"
    ).format(_ledger_ident())
    return tuple(LedgerEntry(*row) for row in conn.execute(statement).fetchall())


def _bootstrap(conn: psycopg.Connection[Any]) -> None:
    with conn.transaction():
        conn.execute(
            sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                sql.Identifier(MIGRATION_SCHEMA)
            )
        )
        conn.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {} (
                    version BIGINT PRIMARY KEY,
                    name TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            ).format(_ledger_ident())
        )


def _acquire_lock(conn: psycopg.Connection[Any], lock_timeout_seconds: float) -> None:
    timeout_ms = max(1, int(lock_timeout_seconds * 1000))
    try:
        conn.execute(
            "SELECT set_config('lock_timeout', %s, false)", (f"{timeout_ms}ms",)
        )
        conn.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK_KEY,))
    except psycopg.errors.LockNotAvailable as exc:
        raise MigrationLockError(
            "another migration process holds the exclusive migration lock; "
            f"retry after it finishes (lock_timeout={lock_timeout_seconds}s, "
            f"key={MIGRATION_LOCK_KEY})"
        ) from exc


def _release_lock(conn: psycopg.Connection[Any]) -> None:
    try:
        conn.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK_KEY,))
    except psycopg.Error:
        # The session is ending anyway; a lost lock cannot outlive the connection.
        pass


def _validate_applied(
    applied: tuple[LedgerEntry, ...], by_version: dict[int, Migration], directory: Path
) -> None:
    for entry in applied:
        migration = by_version.get(entry.version)
        if migration is None:
            raise MigrationError(
                f"applied migration {entry.version} is missing from {directory}; "
                "applied migrations must not be deleted or rewritten"
            )
        if migration.checksum != entry.checksum:
            raise MigrationChecksumError(
                f"applied migration {migration.label} changed after application "
                f"(ledger={entry.checksum}, file={migration.checksum})"
            )


def apply_migrations(
    dsn: str,
    *,
    migrations_dir: Path | str = DEFAULT_MIGRATIONS_DIR,
    lock_timeout_seconds: float = 10.0,
) -> MigrationRunResult:
    """Apply every pending migration; safe to call repeatedly and concurrently."""
    migrations = discover_migrations(migrations_dir)
    with psycopg.connect(dsn, autocommit=True) as conn:
        _acquire_lock(conn, lock_timeout_seconds)
        try:
            _bootstrap(conn)
            by_version = {migration.version: migration for migration in migrations}
            applied = read_ledger(conn)
            _validate_applied(applied, by_version, Path(migrations_dir))
            applied_versions = {entry.version for entry in applied}

            newly_applied: list[str] = []
            skipped: list[str] = []
            for migration in migrations:
                if migration.version in applied_versions:
                    skipped.append(migration.label)
                    continue
                try:
                    with conn.transaction():
                        conn.execute(migration.up_path.read_text(encoding="utf-8"))
                        conn.execute(
                            sql.SQL(
                                "INSERT INTO {} (version, name, checksum) VALUES (%s, %s, %s)"
                            ).format(_ledger_ident()),
                            (migration.version, migration.name, migration.checksum),
                        )
                except psycopg.Error as exc:
                    raise MigrationError(
                        f"migration {migration.label} failed; its database changes were "
                        f"rolled back and no ledger row was written: {exc}"
                    ) from exc
                newly_applied.append(migration.label)
            return MigrationRunResult(tuple(newly_applied), tuple(skipped))
        finally:
            _release_lock(conn)


def rollback_migrations(
    dsn: str,
    *,
    target_version: int,
    migrations_dir: Path | str = DEFAULT_MIGRATIONS_DIR,
    lock_timeout_seconds: float = 10.0,
) -> RollbackResult:
    """Roll back applied migrations newer than ``target_version``, newest first.

    Intended for disposable/local databases: domain DDL is dropped with
    ``RESTRICT`` semantics, and the corresponding ledger rows are removed in the
    same transaction as each down script.
    """
    if target_version < 0:
        raise MigrationError("target_version must be >= 0")
    migrations = discover_migrations(migrations_dir)
    with psycopg.connect(dsn, autocommit=True) as conn:
        _acquire_lock(conn, lock_timeout_seconds)
        try:
            _bootstrap(conn)
            by_version = {migration.version: migration for migration in migrations}
            applied = read_ledger(conn)
            _validate_applied(applied, by_version, Path(migrations_dir))

            rolled_back: list[str] = []
            kept: list[str] = []
            for entry in sorted(applied, key=lambda item: item.version, reverse=True):
                if entry.version <= target_version:
                    kept.append(by_version[entry.version].label)
                    continue
                migration = by_version[entry.version]
                if migration.down_path is None:
                    raise MigrationError(
                        f"migration {migration.label} has no down script; cannot roll back"
                    )
                try:
                    with conn.transaction():
                        conn.execute(migration.down_path.read_text(encoding="utf-8"))
                        conn.execute(
                            sql.SQL(
                                "DELETE FROM {} WHERE version = %s AND checksum = %s"
                            ).format(_ledger_ident()),
                            (entry.version, entry.checksum),
                        )
                except psycopg.Error as exc:
                    raise MigrationError(
                        f"rollback of {migration.label} failed; changes were rolled back "
                        f"and its ledger row was kept: {exc}"
                    ) from exc
                rolled_back.append(migration.label)
            return RollbackResult(tuple(rolled_back), tuple(kept))
        finally:
            _release_lock(conn)


def migration_status(
    dsn: str, *, migrations_dir: Path | str = DEFAULT_MIGRATIONS_DIR
) -> MigrationStatus:
    """Report applied and pending migrations without changing the database."""
    migrations = discover_migrations(migrations_dir)
    with psycopg.connect(dsn, autocommit=True) as conn:
        applied = read_ledger(conn) if ledger_exists(conn) else ()
    applied_versions = {entry.version for entry in applied}
    pending = tuple(m for m in migrations if m.version not in applied_versions)
    return MigrationStatus(applied=applied, pending=pending)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m nyc311_pipeline.storage.migrations",
        description="Apply ordered SQL migrations with an exclusive advisory lock.",
    )
    parser.add_argument(
        "--dsn",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL DSN (default: DATABASE_URL environment variable)",
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=DEFAULT_MIGRATIONS_DIR,
        help=f"directory containing numbered *.{{up,down}}.sql files (default: {DEFAULT_MIGRATIONS_DIR})",
    )
    parser.add_argument(
        "--lock-timeout-seconds",
        type=float,
        default=10.0,
        help="how long to wait for the exclusive migration lock (default: 10)",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("upgrade", help="apply all pending migrations")
    down_parser = subcommands.add_parser("down", help="roll back newer migrations")
    down_parser.add_argument(
        "--target",
        type=int,
        default=0,
        help="keep migrations with version <= target (default: 0, roll back all)",
    )
    subcommands.add_parser("status", help="show applied and pending migrations")

    args = parser.parse_args(argv)
    if not args.dsn:
        parser.error("--dsn or DATABASE_URL is required")

    try:
        if args.command == "upgrade":
            result = apply_migrations(
                args.dsn,
                migrations_dir=args.migrations_dir,
                lock_timeout_seconds=args.lock_timeout_seconds,
            )
            print(f"applied: {', '.join(result.applied) or '(none)'}")
            print(f"already applied: {', '.join(result.skipped) or '(none)'}")
        elif args.command == "down":
            result = rollback_migrations(
                args.dsn,
                target_version=args.target,
                migrations_dir=args.migrations_dir,
                lock_timeout_seconds=args.lock_timeout_seconds,
            )
            print(f"rolled back: {', '.join(result.rolled_back) or '(none)'}")
            print(f"kept: {', '.join(result.kept) or '(none)'}")
        else:
            report = migration_status(args.dsn, migrations_dir=args.migrations_dir)
            for entry in report.applied:
                print(
                    f"applied {entry.version:04d}_{entry.name} {entry.checksum} {entry.applied_at}"
                )
            for migration in report.pending:
                print(f"pending {migration.label}")
            if not report.applied and not report.pending:
                print("no migrations found")
    except (MigrationError, psycopg.Error) as exc:
        print(
            f"migration command failed against {redact_dsn(args.dsn)}: {exc}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
