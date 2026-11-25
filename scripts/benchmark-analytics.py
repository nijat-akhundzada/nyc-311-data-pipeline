"""Capture three before/after plans for each analytics query and the selective workload.

Run with --apply-index on a disposable copy after ingestion stops. The selected
candidate index remains on that copy.
"""

import argparse
import hashlib
import json
import os
import statistics
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = {
    "date": ("02_candidate_index.sql", "fact_eligible_date_agency_cover"),
    "agency": ("03_agency_resolution_index.sql", "fact_agency_resolution_cover"),
}


def measure(conn, query):
    # Fetch the results as an untimed warm-up, then measure three comparable executions.
    rows = conn.execute(query).fetchall()
    digest = hashlib.sha256(json.dumps(rows, default=str).encode()).hexdigest()
    plans = [
        conn.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query).fetchone()[0][0]
        for _ in range(3)
    ]
    execution_ms = [plan["Execution Time"] for plan in plans]
    return {
        "execution_ms": execution_ms,
        "median_ms": statistics.median(execution_ms),
        "plans": plans,
        "result_rows": len(rows),
        "result_sha256": digest,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-index", action="store_true", required=True)
    parser.add_argument(
        "--candidate", choices=CANDIDATES, default="date", help="index experiment (default: date)"
    )
    args = parser.parse_args()
    index_file, index_name = CANDIDATES[args.candidate]
    query = (ROOT / "sql/performance/01_selective_resolution.sql").read_text()
    analytics = {
        path.name: path.read_text() for path in sorted((ROOT / "sql/analytics").glob("*.sql"))
    }
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        index_relation = f"gold.{index_name}"
        if conn.execute("SELECT to_regclass(%s)", (index_relation,)).fetchone()[0]:
            raise RuntimeError("candidate index already exists; refusing an invalid baseline")
        conn.execute("VACUUM (ANALYZE) gold.fact_service_requests")
        conn.execute(
            "ANALYZE gold.dim_date, gold.dim_agency, gold.dim_complaint_type, gold.dim_borough"
        )
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
                "gold.dim_date",
                "gold.dim_agency",
                "gold.dim_complaint_type",
                "gold.dim_borough",
                "gold.dim_service_request_state",
            ]
        }
        samples = {}
        analytics_samples = {name: {} for name in analytics}
        for phase in ("before", "after"):
            if phase == "after":
                conn.execute((ROOT / "sql/performance" / index_file).read_text())
            samples[phase] = measure(conn, query)
            for name, statement in analytics.items():
                analytics_samples[name][phase] = measure(conn, statement)
        for name, comparison in {"selective resolution": samples, **analytics_samples}.items():
            if comparison["before"]["result_sha256"] != comparison["after"]["result_sha256"]:
                raise RuntimeError(f"optimization changed results for {name}")

        result = {
            "postgresql": conn.execute("SELECT version()").fetchone()[0],
            "candidate_index": index_relation,
            "settings": environment,
            "counts": counts,
            "distinct_bronze_ids": conn.execute(
                "SELECT count(DISTINCT unique_key) FROM bronze.raw_service_requests"
            ).fetchone()[0],
            "samples": samples,
            "identical_results": True,
            "analytics_result_row_counts": {
                name: comparison["before"]["result_rows"]
                for name, comparison in analytics_samples.items()
            },
            "analytics_samples": analytics_samples,
            "speedup": samples["before"]["median_ms"] / samples["after"]["median_ms"],
            "index_bytes": conn.execute(
                "SELECT pg_relation_size(%s)", (index_relation,)
            ).fetchone()[0],
        }
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
