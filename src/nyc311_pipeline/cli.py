"""Small JSON CLI. Secrets come from the environment; diagnostics never include payloads."""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID, uuid4

import psycopg

from .bronze_contracts import StorageError
from .ingestion.client import ApiClient
from .ingestion.models import IngestionError, utc_time
from .orchestration.pipeline import execute, report
from .storage.migrations import (
    DEFAULT_MIGRATIONS_DIR,
    MigrationError,
    apply_migrations,
    migration_status,
)
from .testing.fixture_source import FixtureSource
from .validation.records import PipelineError, quality_gate


def utc_bound(value: str):
    try:
        if len(value) == 10:
            return datetime.fromisoformat(value).replace(tzinfo=UTC)
        return utc_time(value)
    except (ValueError, IngestionError):
        raise argparse.ArgumentTypeError(
            "use YYYY-MM-DD or an offset-aware ISO timestamp"
        ) from None


def positive(value):
    try:
        result = int(value)
        if result <= 0:
            raise ValueError
        return result
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer") from None


def threshold_value(value):
    try:
        value = str(Decimal(value))
        quality_gate(1, 0, value)
        return value
    except (PipelineError, InvalidOperation):
        raise argparse.ArgumentTypeError("threshold must be finite and between 0 and 1") from None


def parser():
    root = argparse.ArgumentParser(prog="python -m nyc311_pipeline")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate")
    commands.add_parser("health")
    status = commands.add_parser("report")
    status.add_argument("--run-id", type=UUID, required=True)
    run = commands.add_parser("run")
    run.add_argument("--mode", choices=["backfill", "incremental"])
    run.add_argument("--start", type=utc_bound)
    run.add_argument("--end", type=utc_bound)
    run.add_argument("--initial-lower", type=utc_bound)
    run.add_argument("--resume-run-id", type=UUID)
    run.add_argument("--page-size", type=positive)
    run.add_argument("--max-records", type=positive)
    run.add_argument("--quality-threshold", type=threshold_value)
    run.add_argument("--fixture", help="explicit synthetic HTTP fixture; never default")
    return root


def connect(dsn):
    # Bounded startup recovery, no infinite DB polling.
    for attempt in range(3):
        try:
            return psycopg.connect(dsn, autocommit=True, connect_timeout=5)
        except psycopg.OperationalError:
            if attempt == 2:
                raise StorageError(retryable=True) from None
            time.sleep(attempt + 1)


def migrations_directory():
    if DEFAULT_MIGRATIONS_DIR.is_dir():
        return DEFAULT_MIGRATIONS_DIR
    return Path("/app/db/migrations")


def emit(value, *, diagnostic=False):
    print(
        json.dumps(value, default=str, sort_keys=True),
        file=sys.stderr if diagnostic else sys.stdout,
    )


async def run_command(conn, args, identity):
    fixture = FixtureSource.from_path(args.fixture) if args.fixture else None
    client = fixture or ApiClient(app_token=os.environ.get("SOCRATA_APP_TOKEN"))
    try:
        return await execute(
            conn,
            client,
            start=args.start,
            end=args.end,
            mode=args.mode,
            page_size=args.page_size,
            initial_lower=args.initial_lower,
            threshold=args.quality_threshold,
            max_records=args.max_records,
            resume_run_id=args.resume_run_id,
            run_id=identity,
            fixture_hash=fixture.fixture_hash if fixture else None,
        )
    finally:
        await client.aclose()


def main(argv=None):
    root = parser()
    args = root.parse_args(argv)
    if args.command == "run":
        if not args.resume_run_id and (args.start is None or args.end is None):
            root.error("new runs require --start and --end")
        if args.page_size and args.page_size > 5000:
            root.error("--page-size must be <= 5000")
    if args.command == "run" and not args.resume_run_id and args.quality_threshold is None:
        try:
            args.quality_threshold = threshold_value(
                os.environ.get("QUALITY_MAX_INVALID_RATE", "0.05")
            )
        except argparse.ArgumentTypeError:
            root.error("invalid QUALITY_MAX_INVALID_RATE")
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        emit(dict(category="configuration", published=False))
        return 2
    identity = (args.resume_run_id or uuid4()) if args.command == "run" else None
    if identity:
        emit(dict(event="pipeline_requested", run_id=str(identity)), diagnostic=True)
    try:
        with connect(dsn) as conn:
            if args.command == "migrate":
                result = apply_migrations(dsn, migrations_dir=migrations_directory())
                emit(dict(applied=result.applied, skipped=result.skipped))
            elif args.command == "health":
                conn.execute("SELECT 1")
                if (
                    not 160000
                    <= int(conn.execute("SHOW server_version_num").fetchone()[0])
                    < 170000
                ):
                    raise PipelineError("postgresql_16_required")
                if migration_status(dsn, migrations_dir=migrations_directory()).pending:
                    raise PipelineError("pending_migrations")
                emit(dict(healthy=True))
            elif args.command == "report":
                emit(report(conn, args.run_id))
            else:
                emit(asyncio.run(run_command(conn, args, identity)))
        return 0
    except (
        IngestionError,
        StorageError,
        PipelineError,
        psycopg.Error,
        MigrationError,
        ValueError,
        OSError,
        KeyError,
        TypeError,
    ) as error:
        category = getattr(error, "category", "storage")
        if isinstance(error, (ValueError, OSError, KeyError, TypeError)):
            category = "configuration"
        code = (
            2
            if category in {"configuration", "run_conflict", "missing_run_settings"}
            else (3 if isinstance(error, IngestionError) else getattr(error, "code", 5))
        )
        emit(
            dict(
                run_id=str(identity) if identity else None,
                status="unknown" if isinstance(error, (StorageError, psycopg.Error)) else "failed",
                category=category,
                retryable=getattr(error, "retryable", False),
                published=None if isinstance(error, (StorageError, psycopg.Error)) else False,
            )
        )
        return code
