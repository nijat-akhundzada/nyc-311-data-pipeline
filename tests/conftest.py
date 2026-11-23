"""Shared test setup for source-independent PostgreSQL integration tests.

``TEST_DATABASE_URL`` must point to a maintenance database on a disposable
PostgreSQL 16 server.  Each integration test creates and drops its own uniquely
named database, so no schema residue or source data is left behind.  No live API
or application secret is ever used.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from psycopg import sql

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

MAINTENANCE_DSN_ENV = "TEST_DATABASE_URL"


def _database_dsn(maintenance_dsn: str, database_name: str) -> str:
    parts = urlsplit(maintenance_dsn)
    return urlunsplit(
        (parts.scheme, parts.netloc, f"/{database_name}", parts.query, parts.fragment)
    )


@pytest.fixture(scope="session")
def maintenance_dsn() -> str:
    dsn = os.environ.get(MAINTENANCE_DSN_ENV)
    if not dsn:
        pytest.skip(
            f"{MAINTENANCE_DSN_ENV} is not set; PostgreSQL integration tests require "
            "a disposable PostgreSQL 16 maintenance database"
        )
    return dsn


@pytest.fixture
def isolated_db(maintenance_dsn: str):
    """Yield a DSN for a fresh, disposable database that is dropped afterwards."""
    name = f"nyc311_test_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(maintenance_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        yield _database_dsn(maintenance_dsn, name)
    finally:
        with psycopg.connect(maintenance_dsn, autocommit=True) as admin:
            admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (name,),
            )
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    sql.Identifier(name)
                )
            )
