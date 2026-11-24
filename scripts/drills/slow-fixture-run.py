"""Opt-in container-kill drill. Synthetic fixtures only; never the production runner."""

import argparse
import asyncio
import os
from uuid import UUID

import psycopg

from nyc311_pipeline.cli import utc_bound
from nyc311_pipeline.orchestration.pipeline import execute
from nyc311_pipeline.testing.fixture_source import FixtureSource


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    source = FixtureSource.from_path("/fixtures/valid.json")
    original_fetch = source.fetch_page

    async def slow_fetch(request):
        await asyncio.sleep(1)
        return await original_fetch(request)

    source.fetch_page = slow_fetch
    try:
        with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
            result = await execute(
                conn,
                source,
                start=utc_bound("2025-01-01"),
                end=utc_bound("2026-01-01"),
                page_size=2,
                fixture_hash=source.fixture_hash,
                **{("resume_run_id" if args.resume else "run_id"): args.run_id},
            )
            print(result, flush=True)
    finally:
        await source.aclose()


if __name__ == "__main__":
    asyncio.run(main())
