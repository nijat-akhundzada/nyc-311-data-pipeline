"""Opt-in measured benchmark; creates the documented optional index on DATABASE_URL.

Run only after ingestion stops, with --apply-index on a development database.
The index is a standalone deployment experiment, not a rewritten migration.
"""

import argparse
import hashlib
import json
import os
import statistics
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-index", action="store_true", required=True)
    parser.parse_args()
    query = (ROOT / "sql/performance/01_selective_resolution.sql").read_text()
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        if conn.execute("SELECT to_regclass('gold.fact_eligible_date_agency_cover')").fetchone()[0]:
            raise RuntimeError("candidate index already exists; refusing an invalid baseline")
        conn.execute("VACUUM (ANALYZE) gold.fact_service_requests")
        environment = dict(
            conn.execute(
                "SELECT name,setting FROM pg_settings WHERE name IN "
                "('shared_buffers','work_mem','max_parallel_workers_per_gather',"
                "'effective_cache_size','random_page_cost')"
            ).fetchall()
        )
        counts = {
            table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in [
                "bronze.raw_service_requests",
                "silver.service_requests",
                "gold.fact_service_requests",
            ]
        }
        samples = {}
        hashes = []
        for phase in ("before", "after"):
            if phase == "after":
                conn.execute((ROOT / "sql/performance/02_candidate_index.sql").read_text())
            # One untimed warm-up in each phase; no cold-cache claims.
            rows = conn.execute(query).fetchall()
            hashes.append(hashlib.sha256(json.dumps(rows, default=str).encode()).hexdigest())
            plans = [
                conn.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query).fetchone()[0][0]
                for _ in range(3)
            ]
            samples[phase] = {
                "execution_ms": [p["Execution Time"] for p in plans],
                "median_ms": statistics.median(p["Execution Time"] for p in plans),
                "plans": plans,
                "result_rows": len(rows),
                "result_sha256": hashes[-1],
            }
        assert hashes[0] == hashes[1], "optimization changed results"
        analytics = {
            path.name: len(conn.execute(path.read_text()).fetchall())
            for path in sorted((ROOT / "sql/analytics").glob("*.sql"))
        }
        result = {
            "postgresql": conn.execute("SELECT version()").fetchone()[0],
            "settings": environment,
            "counts": counts,
            "samples": samples,
            "identical_results": True,
            "analytics_result_row_counts": analytics,
            "speedup": samples["before"]["median_ms"] / samples["after"]["median_ms"],
            "index_bytes": conn.execute(
                "SELECT pg_relation_size('gold.fact_eligible_date_agency_cover')"
            ).fetchone()[0],
        }
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
