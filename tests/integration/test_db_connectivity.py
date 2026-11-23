"""Infrastructure integration test verifying PostgreSQL 16 connectivity and isolation.

Note: This verifies database readiness and infrastructure connectivity.
It does NOT assert pipeline or domain integration coverage (which remains
gated on Specs 01 and 05).
"""

from __future__ import annotations

import psycopg
import pytest


@pytest.mark.integration
def test_postgres_version_16(maintenance_dsn: str) -> None:
    """The PostgreSQL server must be version 16+."""
    with psycopg.connect(maintenance_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SHOW server_version_num;")
            row = cur.fetchone()
            assert row is not None
            version_num = int(row[0])
            # PostgreSQL 16.x has server_version_num >= 160000 and < 170000
            assert version_num >= 160000, f"Expected PostgreSQL 16+, got {version_num}"


@pytest.mark.integration
def test_isolated_database_crud(isolated_db: str) -> None:
    """A fresh, disposable database allows table creation, insert, and query."""
    with psycopg.connect(isolated_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE _infra_healthcheck (
                    id serial PRIMARY KEY,
                    marker text NOT NULL
                );
                """
            )
            cur.execute(
                "INSERT INTO _infra_healthcheck (marker) VALUES (%s) RETURNING id;",
                ("readiness_probe",),
            )
            row = cur.fetchone()
            assert row is not None
            inserted_id = row[0]
            conn.commit()

            cur.execute("SELECT marker FROM _infra_healthcheck WHERE id = %s;", (inserted_id,))
            result = cur.fetchone()
            assert result is not None
            assert result[0] == "readiness_probe"
