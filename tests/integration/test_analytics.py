"""Execute submission SQL against the real PostgreSQL publication of synthetic fixtures."""

import json
from pathlib import Path

import psycopg
import pytest

from nyc311_pipeline.cli import utc_bound
from nyc311_pipeline.orchestration.pipeline import execute
from nyc311_pipeline.storage.migrations import apply_migrations
from nyc311_pipeline.testing.fixture_source import FixtureSource

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_analytics_denominators_rank_trends_and_duration(isolated_db):
    apply_migrations(isolated_db)
    doc = json.loads((ROOT / "fixtures/valid.json").read_text())
    # Two unequal agency/borough groups, three months with a missing middle month.
    for i, record in enumerate(doc["records"]):
        record["agency"] = "A" if i < 15 else "B"
        record["borough"] = "QUEENS" if i < 15 else "BRONX"
        if i >= 15:
            record["created_date"] = "2025-03-15T12:00:00"
            record["closed_date"] = "2025-03-15T14:00:00"
    source = FixtureSource(doc)
    try:
        with psycopg.connect(isolated_db, autocommit=True) as conn:
            result = await execute(
                conn,
                source,
                start=utc_bound("2025-01-01"),
                end=utc_bound("2026-01-01"),
                fixture_hash=source.fixture_hash,
            )
            assert result["published"]
            queries = sorted((ROOT / "sql/analytics").glob("*.sql"))
            results = [conn.execute(path.read_text()).fetchall() for path in queries]
            agency, trends, borough, resolution = results
            assert [(r[0], r[2], r[4], float(r[5])) for r in agency] == [
                ("A", 15, 1, 75.0),
                ("B", 5, 2, 25.0),
            ]
            assert sum(r[2] for r in trends if r[1].month == 2) == 0
            assert all(r[3] == 0 and r[5] is None for r in trends if r[1].month == 3)
            assert [(r[0], r[1], r[3]) for r in borough] == [("QUEENS", 15, 1), ("BRONX", 5, 2)]
            assert sum(r[1] for r in resolution) == sum(r[2] for r in resolution) == 20
            assert all(float(r[4]) == float(r[5]) == float(r[6]) == 2 for r in resolution)
    finally:
        await source.aclose()
