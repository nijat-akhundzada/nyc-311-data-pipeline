"""Deterministic tests validating Dockerfile and compose.yaml specifications."""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_dockerfile_multi_stage_and_non_root() -> None:
    """Dockerfile must specify a multi-stage build and run as a non-root user."""
    dockerfile_path = REPO_ROOT / "Dockerfile"
    assert dockerfile_path.is_file(), "Dockerfile must exist at repository root"

    content = dockerfile_path.read_text(encoding="utf-8")

    # Multi-stage verification
    assert "AS builder" in content, "Dockerfile must define builder stage"
    assert "AS runtime" in content, "Dockerfile must define runtime stage"

    # Non-root security check
    assert "useradd" in content, "Dockerfile must create dedicated non-root user"
    assert "10001" in content, "Dockerfile must use specific non-root UID/GID (10001)"
    assert "USER appuser" in content, "Dockerfile must switch to non-root appuser"

    # Must not end as root
    user_directives = [
        line.strip() for line in content.splitlines() if line.strip().startswith("USER")
    ]
    assert len(user_directives) >= 1
    assert user_directives[-1] == "USER appuser"


def test_compose_postgres_service_and_named_volume() -> None:
    """compose.yaml must define PostgreSQL 16 with healthcheck and persistent named volume."""
    compose_path = REPO_ROOT / "compose.yaml"
    assert compose_path.is_file(), "compose.yaml must exist at repository root"

    with compose_path.open("r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    # Validate services
    assert "services" in compose, "compose.yaml must define services"
    services = compose["services"]

    # db service checks
    assert "db" in services, "compose.yaml must define 'db' service"
    db_service = services["db"]
    assert "image" in db_service
    assert "postgres:16" in db_service["image"], "db service must use PostgreSQL 16"

    # Healthcheck check
    assert "healthcheck" in db_service, "db service must declare healthcheck"
    healthcheck = db_service["healthcheck"]
    assert "test" in healthcheck
    test_cmd = str(healthcheck["test"])
    assert "pg_isready" in test_cmd, "healthcheck must use pg_isready"

    # Volume check
    assert "volumes" in db_service, "db service must mount persistent volume"
    volume_mounts = db_service["volumes"]
    data_mount = next((v for v in volume_mounts if "/var/lib/postgresql/data" in v), None)
    assert data_mount is not None, "db service must mount to /var/lib/postgresql/data"
    assert data_mount.startswith(
        "postgres_data:"
    ), "volume mount must use postgres_data named volume"

    # Top-level named volume
    assert "volumes" in compose, "compose.yaml must declare top-level volumes"
    assert "postgres_data" in compose["volumes"], "postgres_data named volume must exist"

    # app service check (under profile, depends on db health)
    assert "app" in services, "compose.yaml must define app verification service"
    app_service = services["app"]
    assert app_service.get("profiles") == [
        "app"
    ], "app service must be isolated under 'app' profile"
    assert "depends_on" in app_service
    assert "db" in app_service["depends_on"]
    assert app_service["depends_on"]["db"]["condition"] == "service_healthy"


def test_unavailable_database_connection_failure() -> None:
    """Connecting to an unavailable database must fail with psycopg.OperationalError."""
    # Port 54329 is closed/unavailable
    unavailable_dsn = "postgresql://nyc311:wrong@127.0.0.1:54329/nonexistent"
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(unavailable_dsn, connect_timeout=1)
