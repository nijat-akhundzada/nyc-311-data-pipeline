"""Opt-in Docker recovery evidence; requires a dedicated disposable Compose database.

Set DRILL_COMPOSE_FILE, DRILL_ENV_FILE, DRILL_ADMIN_URL (host DSN), and
DRILL_CONTAINER_URL (same database from Compose network). No production defaults.
Output contains synthetic counts and run metadata only, never DSNs or payloads.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import psycopg

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "nyc311-final-drills"
COMPOSE = [
    "docker",
    "compose",
    "-p",
    PROJECT,
    "-f",
    os.environ["DRILL_COMPOSE_FILE"],
    "--env-file",
    os.environ["DRILL_ENV_FILE"],
]
EVIDENCE = {}


def command(args, expected=0):
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if result.returncode != expected:
        raise RuntimeError(f"unexpected exit {result.returncode}: {result.stderr[-500:]}")
    return result


def cli(*args, expected=0):
    return command(
        COMPOSE + ["--profile", "pipeline", "run", "--rm", "--no-deps", "pipeline", *args],
        expected,
    )


def snapshot(conn):
    # Entire published rows, dimensions and watermarks, not just equal counts.
    tables = [
        "silver.service_requests",
        "gold.fact_service_requests",
        "gold.dim_date",
        "gold.dim_agency",
        "gold.dim_complaint_type",
        "gold.dim_borough",
        "gold.dim_service_request_state",
        "ops.publication_watermarks",
    ]
    return {
        table: conn.execute(
            f"SELECT count(*), md5(coalesce(string_agg(to_jsonb(t)::text, '' "
            f"ORDER BY to_jsonb(t)::text), '')) FROM {table} t"
        ).fetchone()
        for table in tables
    }


def state(conn, run_id):
    row = conn.execute(
        "SELECT status,phase,received_count,raw_inserted_count,published_at "
        "FROM ops.pipeline_runs WHERE run_id=%s",
        (run_id,),
    ).fetchone()
    return dict(zip(["status", "phase", "received", "inserted", "published_at"], row, strict=True))


def run():
    if os.environ.get("DRILL_CONFIRM_DISPOSABLE") != "yes":
        raise RuntimeError("set DRILL_CONFIRM_DISPOSABLE=yes for this isolated drill")
    cli("migrate")
    with psycopg.connect(os.environ["DRILL_ADMIN_URL"], autocommit=True) as conn:
        if conn.execute("SELECT count(*) FROM ops.pipeline_runs").fetchone()[0]:
            raise RuntimeError("drill requires a fresh database, refusing existing run history")
    identity = str(uuid4())
    base = [
        "docker",
        "run",
        "--detach",
        "--network",
        PROJECT + "_default",
        "--env",
        "DATABASE_URL=" + os.environ["DRILL_CONTAINER_URL"],
        "--mount",
        f"type=bind,source={ROOT / 'fixtures'},target=/fixtures,readonly",
        "--mount",
        f"type=bind,source={ROOT / 'scripts/drills'},target=/drills,readonly",
        "--entrypoint",
        "python",
    ]
    container = command(
        base + ["nyc311-final:local", "/drills/slow-fixture-run.py", "--run-id", identity]
    ).stdout.strip()
    with psycopg.connect(os.environ["DRILL_ADMIN_URL"], autocommit=True) as conn:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            row = conn.execute(
                "SELECT page_no,exhausted FROM ops.ingest_checkpoints WHERE run_id=%s",
                (identity,),
            ).fetchone()
            if row and row[0] >= 1 and not row[1]:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("no durable page before kill deadline")
        command(["docker", "kill", "--signal", "KILL", container])
        assert command(["docker", "wait", container]).stdout.strip() == "137"
        killed = state(conn, identity)
        checkpoint = list(row)
        resumed = command(
            base
            + [
                "nyc311-final:local",
                "/drills/slow-fixture-run.py",
                "--run-id",
                identity,
                "--resume",
            ]
        ).stdout.strip()
        assert command(["docker", "wait", resumed]).stdout.strip() == "0"
        after = state(conn, identity)
        counts = conn.execute(
            "SELECT (SELECT count(*) FROM bronze.raw_service_requests),"
            "(SELECT count(*) FROM silver.service_requests),"
            "(SELECT count(*) FROM gold.fact_service_requests),"
            "(SELECT count(DISTINCT unique_key) FROM gold.fact_service_requests)"
        ).fetchone()
        assert counts == (20, 20, 20, 20) and after["status"] == "succeeded"
        EVIDENCE["kill_resume"] = {
            "run_id": identity,
            "killed_exit": 137,
            "resume_exit": 0,
            "checkpoint_before_kill": checkpoint,
            "before": killed,
            "after": after,
            "bronze_silver_gold_distinct_gold": counts,
        }
        before = snapshot(conn)
        bad = cli(
            "run",
            "--mode",
            "backfill",
            "--start",
            "2025-01-01",
            "--end",
            "2026-01-01",
            "--fixture",
            "/fixtures/quality-failure.json",
            expected=4,
        )
        report = json.loads(bad.stdout)
        assert before == snapshot(conn)
        quarantine = conn.execute(
            "SELECT count(*),array_agg(DISTINCT reasons) FROM ops.quarantine WHERE run_id=%s",
            (report["run_id"],),
        ).fetchone()
        assert quarantine[0] == 2
        EVIDENCE["quality_gate"] = {
            "exit": 4,
            "report": report,
            "quarantine": quarantine,
            "before": before,
            "after": snapshot(conn),
            "published_rows_identical": True,
        }
    command(COMPOSE + ["stop", "db"])
    started = time.monotonic()
    try:
        unavailable = cli(
            "run",
            "--mode",
            "backfill",
            "--start",
            "2025-01-01",
            "--end",
            "2026-01-01",
            "--fixture",
            "/fixtures/valid.json",
            expected=5,
        )
        EVIDENCE["database_unavailable"] = {
            "exit": 5,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "report": json.loads(unavailable.stdout),
            "attempts_contract": 3,
        }
    finally:
        command(COMPOSE + ["up", "-d", "--wait", "db"])
    recovered = cli(
        "run",
        "--mode",
        "incremental",
        "--start",
        "2025-01-01",
        "--end",
        "2026-01-01",
        "--initial-lower",
        "2026-11-22",
        "--fixture",
        "/fixtures/valid.json",
    )
    report = json.loads(recovered.stdout)
    assert report["published"] and report["status"] == "succeeded"
    EVIDENCE["database_unavailable"]["subsequent_success"] = report
    command(["docker", "rm", container, resumed])
    print(json.dumps(EVIDENCE, indent=2, default=str))


if __name__ == "__main__":
    run()
