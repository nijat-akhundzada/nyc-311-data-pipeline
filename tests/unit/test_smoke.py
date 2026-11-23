"""Deterministic smoke tests for the NYC 311 data pipeline package foundation."""

from __future__ import annotations

import importlib


def test_package_import() -> None:
    """The nyc311_pipeline package must be importable and expose a version."""
    pkg = importlib.import_module("nyc311_pipeline")
    assert hasattr(pkg, "__version__")
    assert isinstance(pkg.__version__, str)
    assert pkg.__version__ == "0.1.0"


def test_core_dependencies_importable() -> None:
    """Core runtime dependencies must be installed and importable."""
    for module_name in ("httpx", "psycopg", "pydantic"):
        mod = importlib.import_module(module_name)
        assert mod is not None


def test_deterministic_smoke() -> None:
    """Deterministic smoke test verifying Python 3.12+ runtime environment."""
    import sys

    assert sys.version_info >= (3, 12)
