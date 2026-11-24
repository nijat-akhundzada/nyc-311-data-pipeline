#!/usr/bin/env python3
"""Resumable loading campaign script to reach at least 1,000,000 genuine Gold facts.

Executes existing CLI commands with bounded retries, finite 90-minute budget,
progress logging, and safe termination.
"""

import json
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
PROGRESS_JSON = ROOT / "docs/evidence/final/campaign-progress.json"
PROGRESS_TXT = ROOT / "docs/evidence/final/campaign-progress.txt"
DEFAULT_DSN = "postgresql://nyc311_final:final_local_test_only@127.0.0.1:55440/nyc311_real"
TARGET_GOLD_FACTS = 1_000_000
BUDGET_SECONDS = 90 * 60  # 90 minutes
MAX_CONSECUTIVE_FAILURES = 5

stop_requested = False


def sig_handler(signum, frame):
    global stop_requested
    print(
        f"\n[Campaign] Signal {signum} received, stopping after current window...",
        file=sys.stderr,
    )
    stop_requested = True


signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)


def get_db_counts(dsn: str) -> dict:
    with psycopg.connect(dsn, autocommit=True, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    (SELECT count(*) FROM bronze.raw_service_requests),
                    (SELECT count(DISTINCT unique_key) FROM bronze.raw_service_requests),
                    (SELECT count(*) FROM silver.service_requests),
                    (SELECT count(*) FROM gold.fact_service_requests),
                    (SELECT count(*) FROM ops.quarantine),
                    (
                        SELECT count(*) FROM gold.dim_service_request_state
                        WHERE valid_to IS NOT NULL
                    )
            """)
            row = cur.fetchone()
            return {
                "bronze_total": row[0],
                "bronze_distinct_ids": row[1],
                "silver_count": row[2],
                "gold_count": row[3],
                "quarantine_count": row[4],
                "state_historical_count": row[5],
            }


def get_loaded_days(dsn: str) -> set[date]:
    with psycopg.connect(dsn, autocommit=True, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT d.year, d.month, d.day, count(f.unique_key)
                FROM gold.fact_service_requests f
                JOIN gold.dim_date d ON f.created_date_key = d.date_key
                GROUP BY d.year, d.month, d.day
                HAVING count(f.unique_key) >= 3000
            """)
            return {date(r[0], r[1], r[2]) for r in cur.fetchall()}


def get_unfinished_retryable_run(dsn: str):
    with psycopg.connect(dsn, autocommit=True, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.run_id, r.status, r.error_category
                FROM ops.pipeline_runs r
                JOIN ops.run_settings s USING(run_id)
                WHERE r.dataset_id='erm2-nwe9' AND r.published_at IS NULL
                AND (r.status IN ('pending','running','paused') OR r.retryable)
                ORDER BY r.started_at DESC
                LIMIT 1
            """)
            return cur.fetchone()


def run_cli_command(cmd: list[str], env: dict) -> tuple[int, dict]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    payload = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                pass
    return proc.returncode, payload


def resume_with_retries(run_id: str, env: dict, max_attempts: int = 3) -> tuple[bool, dict]:
    python_bin = sys.executable
    resume_cmd = [python_bin, "-m", "nyc311_pipeline", "run", "--resume-run-id", run_id]
    for attempt in range(1, max_attempts + 1):
        print(
            f"[Campaign] Attempting resume for run {run_id} (attempt {attempt}/{max_attempts})..."
        )
        code, out = run_cli_command(resume_cmd, env)
        if code == 0 and out.get("published"):
            return True, out
        retryable = out.get("retryable", False)
        cat = out.get("category") or out.get("error_category")
        print(
            f"[Campaign] Resume attempt {attempt} failed "
            f"(code {code}, cat={cat}, retryable={retryable})."
        )
        if not retryable:
            return False, out
        if attempt < max_attempts:
            wait_s = attempt * 6
            print(f"[Campaign] Waiting {wait_s}s before next resume attempt...")
            time.sleep(wait_s)
    return False, out


def save_progress(record: dict):
    PROGRESS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_JSON, "w") as f:
        json.dump(record, f, indent=2, default=str)

    counts = record.get("counts", {})
    with open(PROGRESS_TXT, "w") as f:
        f.write("NYC 311 Loading Campaign Progress\n")
        f.write(f"Updated At: {record.get('timestamp')}\n")
        f.write(
            f"Gold Facts: {counts.get('gold_count', 0):,} / {TARGET_GOLD_FACTS:,} "
            f"({record.get('remaining_facts', 0):,} remaining)\n"
        )
        f.write(f"Bronze Distinct IDs: {counts.get('bronze_distinct_ids', 0):,}\n")
        f.write(f"Quarantine Count: {counts.get('quarantine_count', 0):,}\n")
        f.write(f"Last Completed Window: {record.get('last_completed_window')}\n")
        f.write(f"Unfinished Run ID: {record.get('unfinished_run_id')}\n")
        f.write(
            f"Elapsed Time: {record.get('elapsed_seconds', 0):.1f}s / {BUDGET_SECONDS}s budget\n"
        )
        f.write(f"Campaign Status: {record.get('status')}\n")
        f.write(f"Exact Resume Command: {record.get('resume_command')}\n")


def main():
    global stop_requested
    dsn = os.environ.get("DATABASE_URL", DEFAULT_DSN)
    env = dict(os.environ, DATABASE_URL=dsn)
    python_bin = sys.executable

    start_time = time.time()
    counts = get_db_counts(dsn)
    print(f"[Campaign] Initial database counts: {counts}")

    if counts["gold_count"] >= TARGET_GOLD_FACTS:
        print(
            f"[Campaign] Target already reached: {counts['gold_count']:,} "
            f"Gold facts >= {TARGET_GOLD_FACTS:,}."
        )
        return

    loaded_days = get_loaded_days(dsn)
    print(f"[Campaign] Found {len(loaded_days)} days already loaded in Gold with >=3000 facts.")

    # Check for unfinished retryable run
    unfinished = get_unfinished_retryable_run(dsn)
    if unfinished:
        run_id, status, error_cat = str(unfinished[0]), unfinished[1], unfinished[2]
        print(
            f"[Campaign] Resuming existing retryable run {run_id} "
            f"(status: {status}, error: {error_cat})..."
        )
        res_ok, rout = resume_with_retries(run_id, env, max_attempts=3)
        if res_ok:
            counts = get_db_counts(dsn)
            print(f"[Campaign] Initial resume SUCCEEDED. Gold: {counts['gold_count']:,}")
        else:
            print(f"[Campaign] Could not resolve existing retryable run {run_id}. Stopping.")
            return

    # Date range for 2025: Feb 1 to Dec 31
    start_date = date(2025, 2, 1)
    end_date = date(2025, 12, 31)
    curr = start_date

    consecutive_failures = 0
    last_completed_window = None

    while curr < end_date and not stop_requested:
        elapsed = time.time() - start_time
        if elapsed >= BUDGET_SECONDS:
            print(f"[Campaign] Budget expired ({elapsed:.1f}s >= {BUDGET_SECONDS}s). Stopping.")
            break

        if counts["gold_count"] >= TARGET_GOLD_FACTS:
            print(
                f"[Campaign] TARGET ACHIEVED! {counts['gold_count']:,} "
                f"Gold facts >= {TARGET_GOLD_FACTS:,}."
            )
            break

        window_start = curr.isoformat()
        window_end = (curr + timedelta(days=1)).isoformat()
        curr += timedelta(days=1)

        if curr - timedelta(days=1) in loaded_days:
            print(f"[Campaign] Skipping already-loaded day: {window_start}")
            continue

        time_str = datetime.now(UTC).strftime("%H:%M:%S")
        print(
            f"\n[Campaign] [{time_str}] Window {window_start} -> {window_end} "
            f"| Gold: {counts['gold_count']:,} | Elapsed: {elapsed / 60:.1f}m"
        )

        cmd = [
            python_bin,
            "-m",
            "nyc311_pipeline",
            "run",
            "--mode",
            "backfill",
            "--start",
            window_start,
            "--end",
            window_end,
            "--page-size",
            "5000",
        ]
        code, out = run_cli_command(cmd, env)

        published = out.get("published", False)
        run_id = out.get("run_id")

        if code == 0 and published:
            consecutive_failures = 0
            last_completed_window = f"{window_start} to {window_end}"
            counts = get_db_counts(dsn)
            loaded_days.add(curr - timedelta(days=1))
            print(
                f"[Campaign] Window SUCCEEDED: published {out.get('valid_count', 0):,} facts. "
                f"New Gold total: {counts['gold_count']:,}"
            )
        else:
            retryable = out.get("retryable", False)
            cat = out.get("category") or out.get("error_category")
            print(
                f"[Campaign] Window FAILED (code {code}, cat={cat}, "
                f"retryable={retryable}, run_id={run_id})"
            )

            if retryable and run_id:
                res_ok, rout = resume_with_retries(run_id, env, max_attempts=3)
                if res_ok:
                    consecutive_failures = 0
                    last_completed_window = f"{window_start} to {window_end}"
                    counts = get_db_counts(dsn)
                    loaded_days.add(curr - timedelta(days=1))
                    print(
                        f"[Campaign] Explicit resume SUCCEEDED: "
                        f"published {rout.get('valid_count', 0):,} facts. "
                        f"New Gold total: {counts['gold_count']:,}"
                    )
                else:
                    consecutive_failures += 1
                    print(f"[Campaign] Explicit resume failed after retries for {run_id}.")
                    print(
                        "[Campaign] Halting to avoid run conflicts with unfinished retryable run."
                    )
                    break
            else:
                consecutive_failures += 1
                if cat == "source_generation_changed":
                    print(
                        "[Campaign] Source generation changed on provider side. "
                        "Continuing with fresh generation..."
                    )
                    time.sleep(3)

        unfinished_run = get_unfinished_retryable_run(dsn)
        unfinished_id = str(unfinished_run[0]) if unfinished_run else None

        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "status": (
                "in_progress" if counts["gold_count"] < TARGET_GOLD_FACTS else "target_reached"
            ),
            "last_completed_window": last_completed_window,
            "unfinished_run_id": unfinished_id,
            "counts": counts,
            "target_facts": TARGET_GOLD_FACTS,
            "remaining_facts": max(0, TARGET_GOLD_FACTS - counts["gold_count"]),
            "elapsed_seconds": time.time() - start_time,
            "budget_seconds": BUDGET_SECONDS,
            "resume_command": (
                f"python -m nyc311_pipeline run --resume-run-id {unfinished_id}"
                if unfinished_id
                else "python scripts/run-campaign.py"
            ),
        }
        save_progress(record)

        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            print(
                f"[Campaign] {consecutive_failures} consecutive failures encountered. "
                "Stopping campaign for safety."
            )
            break

    counts = get_db_counts(dsn)
    final_status = "target_reached" if counts["gold_count"] >= TARGET_GOLD_FACTS else "stopped"
    unfinished_run = get_unfinished_retryable_run(dsn)
    unfinished_id = str(unfinished_run[0]) if unfinished_run else None
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "status": final_status,
        "last_completed_window": last_completed_window,
        "unfinished_run_id": unfinished_id,
        "counts": counts,
        "target_facts": TARGET_GOLD_FACTS,
        "remaining_facts": max(0, TARGET_GOLD_FACTS - counts["gold_count"]),
        "elapsed_seconds": time.time() - start_time,
        "budget_seconds": BUDGET_SECONDS,
        "resume_command": (
            f"python -m nyc311_pipeline run --resume-run-id {unfinished_id}"
            if unfinished_id
            else "python scripts/run-campaign.py"
        ),
    }
    save_progress(record)
    print(f"\n[Campaign] Final summary: {final_status}")
    print(f"[Campaign] Gold facts: {counts['gold_count']:,} / {TARGET_GOLD_FACTS:,}")
    print(f"[Campaign] Bronze distinct IDs: {counts['bronze_distinct_ids']:,}")
    print(f"[Campaign] Silver count: {counts['silver_count']:,}")
    print(f"[Campaign] Quarantines: {counts['quarantine_count']:,}")


if __name__ == "__main__":
    main()
