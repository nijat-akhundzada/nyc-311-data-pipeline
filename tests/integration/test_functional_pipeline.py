"""PostgreSQL + actual API transport fixtures through all three layers."""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from nyc311_pipeline.bronze_contracts import RunConflict
from nyc311_pipeline.cli import utc_bound
from nyc311_pipeline.orchestration.pipeline import execute
from nyc311_pipeline.storage.bronze import BronzeRepository
from nyc311_pipeline.storage.migrations import apply_migrations
from nyc311_pipeline.testing.fixture_source import FixtureSource
from nyc311_pipeline.validation.records import QualityError

ROOT = Path(__file__).resolve().parents[2]
START, END = utc_bound("2025-01-01"), utc_bound("2026-01-01")


@pytest.fixture
def pipeline_db(isolated_db):
    apply_migrations(isolated_db)
    return isolated_db


def document(
    count=20,
    bad=0,
    status="Closed",
    updated="2026-11-23T00:00:00Z",
    observed="2026-11-24T12:00:00Z",
):
    value = json.loads((ROOT / "fixtures/valid.json").read_text())
    value["records"] = value["records"][:count]
    value["observed_at"] = observed
    for i, row in enumerate(value["records"]):
        row["status"], row[":updated_at"] = status, updated
        if i < bad:
            row["closed_date"] = "2025-01-14T12:00:00"
    return value


async def run(conn, doc=None, **kwargs):
    source = FixtureSource(doc or document())
    try:
        return await execute(
            conn,
            source,
            start=START,
            end=END,
            fixture_hash=source.fixture_hash,
            now=datetime(2026, 11, 24, 12, tzinfo=UTC),
            **kwargs,
        )
    finally:
        await source.aclose()


def domain_snapshot(conn):
    return tuple(
        conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in [
            "silver.service_requests",
            "gold.fact_service_requests",
            "gold.dim_service_request_state",
            "gold.dim_agency",
            "gold.dim_date",
            "ops.publication_watermarks",
        ]
    )


def published_rows(conn):
    return tuple(
        conn.execute(f"SELECT to_jsonb(t) FROM {table} t ORDER BY to_jsonb(t)::text").fetchall()
        for table in [
            "silver.service_requests",
            "gold.fact_service_requests",
            "gold.dim_service_request_state",
            "gold.dim_agency",
            "gold.dim_date",
            "gold.dim_borough",
            "gold.dim_complaint_type",
            "ops.publication_watermarks",
        ]
    )


@pytest.mark.asyncio
async def test_fresh_publish_and_identical_replay(pipeline_db):
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        first = await run(conn, page_size=7)
        assert first["status"] == "succeeded" and first["published"] and first["valid_count"] == 20
        before = domain_snapshot(conn)
        rows_before = published_rows(conn)
        assert before[:3] == (20, 20, 20)
        await run(conn, page_size=3)
        assert domain_snapshot(conn) == before
        assert published_rows(conn) == rows_before
        assert conn.execute("SELECT count(*) FROM bronze.raw_service_requests").fetchone()[0] == 20
        assert (
            conn.execute(
                "SELECT min(resolution_seconds) FROM gold.fact_service_requests"
            ).fetchone()[0]
            == 7200
        )


@pytest.mark.asyncio
async def test_exact_5_percent_pass_and_quarantine(pipeline_db):
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        result = await run(conn, document(bad=1))
        assert (
            result["published"] and result["invalid_count"] == 1 and result["evaluated_count"] == 20
        )
        assert domain_snapshot(conn)[:3] == (19, 19, 19)
        assert conn.execute("SELECT reasons FROM ops.quarantine").fetchone()[0] == [
            "closed_before_created"
        ]


@pytest.mark.asyncio
async def test_gate_failure_does_not_touch_any_published_data(pipeline_db):
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        await run(conn)
        before = domain_snapshot(conn)
        rows_before = published_rows(conn)
        with pytest.raises(QualityError, match="quality_threshold"):
            await run(conn, document(bad=2))
        assert domain_snapshot(conn) == before
        assert published_rows(conn) == rows_before
        assert conn.execute("SELECT count(*) FROM ops.quarantine").fetchone()[0] == 2
        assert conn.execute(
            "SELECT status,published_at FROM ops.pipeline_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone() == ("failed", None)


@pytest.mark.asyncio
async def test_zero_candidates_fail_and_capped_run_never_publishes(pipeline_db):
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        with pytest.raises(QualityError):
            await run(conn, document(count=0))
        capped = await run(conn, max_records=3)
        assert capped["status"] == "paused" and not capped["published"]
        assert domain_snapshot(conn)[:3] == (0, 0, 0)
        resumed = await run(conn, resume_run_id=capped["run_id"])
        assert resumed["published"] and domain_snapshot(conn)[:3] == (20, 20, 20)


@pytest.mark.asyncio
async def test_scd2_changed_then_reverted_no_fabricated_intervals(pipeline_db):
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        await run(conn, document(count=1, status="Open"))
        await run(
            conn,
            document(
                count=1,
                status="Closed",
                updated="2026-11-24T01:00:00Z",
                observed="2026-11-25T12:00:00Z",
            ),
        )
        await run(
            conn,
            document(
                count=1,
                status="Open",
                updated="2026-11-25T01:00:00Z",
                observed="2026-11-26T12:00:00Z",
            ),
        )
        rows = conn.execute(
            "SELECT status_key,valid_from,valid_to,is_current FROM "
            "gold.dim_service_request_state ORDER BY valid_from"
        ).fetchall()
        assert [r[0] for r in rows] == ["open", "closed", "open"]
        assert rows[0][2] == rows[1][1] and rows[1][2] == rows[2][1] and rows[2][2] is None
        assert [r[3] for r in rows] == [False, False, True]
        assert conn.execute("SELECT count(*) FROM gold.fact_service_requests").fetchone()[0] == 1
        assert conn.execute(
            "SELECT f.state_id=d.state_id FROM gold.fact_service_requests f JOIN "
            "gold.dim_service_request_state d ON d.unique_key=f.unique_key WHERE "
            "d.is_current"
        ).fetchone()[0]
        # The database rejects overlaps even for direct SQL.
        with pytest.raises(psycopg.Error):
            conn.execute(
                "INSERT INTO "
                "gold.dim_service_request_state(unique_key,state_hash,valid_from,valid_to,"
                "is_current,observed_run_id) "
                "SELECT "
                "unique_key,state_hash,valid_from,valid_to,false,observed_run_id "
                "FROM gold.dim_service_request_state WHERE NOT is_current LIMIT 1"
            )


@pytest.mark.asyncio
async def test_incremental_watermark_advances_only_on_atomic_success(pipeline_db):
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        first = await run(conn, mode="incremental", initial_lower=utc_bound("2026-11-01"))
        watermark = conn.execute(
            "SELECT updated_through FROM ops.publication_watermarks"
        ).fetchone()[0]
        assert first["successful_update_upper_utc"] == watermark
        changed = document(
            count=1, status="Open", updated="2026-11-24T01:00:00Z", observed="2026-11-25T00:00:00Z"
        )
        result = await run(conn, changed, mode="incremental")
        assert result["published"]
        assert (
            conn.execute(
                "SELECT count(*) FROM gold.dim_service_request_state WHERE unique_key='SYN-000'"
            ).fetchone()[0]
            == 2
        )
        with pytest.raises(QualityError):
            await run(conn, document(bad=2), mode="incremental")
        assert (
            conn.execute("SELECT updated_through FROM ops.publication_watermarks").fetchone()[0]
            == watermark
        )


@pytest.mark.asyncio
async def test_publication_fault_rolls_back_silver_gold_status_and_watermark(
    pipeline_db, monkeypatch
):
    import nyc311_pipeline.silver.publish as publication

    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        await run(conn)
        before = domain_snapshot(conn)
        rows_before = published_rows(conn)
        original = publication.publish_gold

        def fail_after_gold(connection, run_id):
            original(connection, run_id)
            raise psycopg.OperationalError("synthetic failure after gold")

        monkeypatch.setattr(publication, "publish_gold", fail_after_gold)
        identity = uuid4()
        changed = document(
            count=1, status="Open", updated="2026-11-24T01:00:00Z", observed="2026-11-25T12:00:00Z"
        )
        with pytest.raises(psycopg.Error):
            await run(
                conn,
                changed,
                mode="incremental",
                initial_lower=utc_bound("2026-11-01"),
                run_id=identity,
            )
        assert domain_snapshot(conn) == before
        assert published_rows(conn) == rows_before
        assert conn.execute(
            "SELECT status,published_at,retryable FROM ops.pipeline_runs WHERE run_id=%s",
            (identity,),
        ).fetchone() == ("failed", None, True)
        monkeypatch.setattr(publication, "publish_gold", original)
        assert (await run(conn, changed, resume_run_id=identity))["published"]
        assert conn.execute("SELECT count(*) FROM ops.publication_watermarks").fetchone()[0] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["stale", "equal_conflict", "old_observation"])
async def test_source_order_conflicts_do_not_overwrite(pipeline_db, case):
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        await run(conn, document(count=1))
        before = domain_snapshot(conn)
        rows_before = published_rows(conn)
        updated = (
            "2026-11-22T00:00:00Z"
            if case == "stale"
            else "2026-11-23T00:00:00Z"
            if case == "equal_conflict"
            else "2026-11-24T00:00:00Z"
        )
        with pytest.raises(QualityError):
            await run(conn, document(count=1, status="Open", updated=updated))
        assert domain_snapshot(conn) == before
        assert published_rows(conn) == rows_before
        assert conn.execute("SELECT count(*) FROM ops.quarantine").fetchone()[0] == 1


@pytest.mark.asyncio
async def test_latest_candidate_count_and_dst_quarantine(pipeline_db):
    value = document(count=2)
    value["records"][0]["created_date"] = "2025-11-02T01:30:00"
    value["records"][0]["closed_date"] = None
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        with pytest.raises(QualityError):
            await run(conn, value)
        assert conn.execute("SELECT reasons FROM ops.quarantine").fetchone()[0] == [
            "created_date:ambiguous_local_time"
        ]


@pytest.mark.asyncio
async def test_competing_runner_rejected_before_any_publication(pipeline_db):
    with psycopg.connect(pipeline_db, autocommit=True) as first:
        with BronzeRepository(first).dataset_lock():
            with psycopg.connect(pipeline_db, autocommit=True) as second:
                with pytest.raises(RunConflict):
                    await run(second)
        assert domain_snapshot(first)[:3] == (0, 0, 0)


def cli(dsn, *args):
    return subprocess.run(
        [sys.executable, "-m", "nyc311_pipeline", *args],
        cwd=ROOT,
        env=dict(os.environ, DATABASE_URL=dsn, PYTHONPATH=str(ROOT / "src")),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_cli_fresh_db_publish_report_health_and_gate_failure(isolated_db):
    assert cli(isolated_db, "health").returncode == 5
    assert cli(isolated_db, "migrate").returncode == 0
    assert cli(isolated_db, "health").returncode == 0
    result = cli(
        isolated_db,
        "run",
        "--start",
        "2025-01-01",
        "--end",
        "2026-01-01",
        "--fixture",
        "fixtures/valid.json",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert data["published"] and data["status"] == "succeeded"
    assert cli(isolated_db, "report", "--run-id", data["run_id"]).returncode == 0
    bad = cli(
        isolated_db,
        "run",
        "--start",
        "2025-01-01",
        "--end",
        "2026-01-01",
        "--fixture",
        "fixtures/quality-failure.json",
    )
    assert bad.returncode == 4 and json.loads(bad.stdout)["published"] is False


@pytest.mark.asyncio
async def test_failure_at_success_transition_rolls_back_everything(pipeline_db):
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        await run(conn)
        before = published_rows(conn)
        conn.execute("""CREATE FUNCTION ops.fail_success() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.status='succeeded' THEN RAISE EXCEPTION 'synthetic late fault';
            END IF; RETURN NEW; END $$;
            CREATE TRIGGER fail_success BEFORE UPDATE ON ops.pipeline_runs
            FOR EACH ROW EXECUTE FUNCTION ops.fail_success()""")
        identity = uuid4()
        changed = document(
            count=1, status="Open", updated="2026-11-24T00:00:00Z", observed="2026-11-25T12:00:00Z"
        )
        with pytest.raises(psycopg.Error):
            await run(
                conn,
                changed,
                mode="incremental",
                initial_lower=utc_bound("2026-11-01"),
                run_id=identity,
            )
        assert published_rows(conn) == before
        assert conn.execute(
            "SELECT published_at,successful_update_upper_utc FROM ops.pipeline_runs "
            "WHERE run_id=%s",
            (identity,),
        ).fetchone() == (None, None)
        conn.execute("DROP TRIGGER fail_success ON ops.pipeline_runs")
        assert (await run(conn, changed, resume_run_id=identity))["published"]


def test_full_migration_rollback_and_reapply(pipeline_db):
    from nyc311_pipeline.storage.migrations import rollback_migrations

    result = rollback_migrations(pipeline_db, target_version=0)
    assert len(result.rolled_back) == 4
    assert len(apply_migrations(pipeline_db).applied) == 4


@pytest.mark.asyncio
async def test_outside_scope_excluded_and_metadata_only_update_no_scd2(pipeline_db):
    value = document(count=2)
    value["records"][0]["created_date"] = "2024-12-31T18:00:00"
    value["records"][0]["closed_date"] = None
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        result = await run(conn, value)
        assert result["outside_scope_count"] == 1 and result["evaluated_count"] == 1
        assert domain_snapshot(conn)[:3] == (1, 1, 1)
        value["records"][1][":updated_at"] = "2026-11-24T00:00:00Z"
        value["observed_at"] = "2026-11-25T00:00:00Z"
        assert (await run(conn, value))["published"]
        assert domain_snapshot(conn)[:3] == (1, 1, 1)


@pytest.mark.asyncio
async def test_equal_update_conflict_aborts_even_when_invalid_fraction_is_5_percent(pipeline_db):
    value = document()
    conflicting = value["records"][0].copy()
    conflicting.update(created_date="2025-01-16T12:00:00", closed_date=None, status="Open")
    value["records"].append(conflicting)
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        with pytest.raises(QualityError, match="conflicting_source_versions"):
            await run(conn, value)
        assert conn.execute(
            "SELECT evaluated_count,invalid_count FROM ops.pipeline_runs"
        ).fetchone() == (20, 1)
        assert conn.execute("SELECT count(*) FROM ops.quarantine").fetchone()[0] == 2
        assert domain_snapshot(conn)[:3] == (0, 0, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value", [("agency", "OTHER-SYN"), ("complaint_type", "Other synthetic")]
)
async def test_other_tracked_attributes_create_one_new_state(pipeline_db, field, value):
    first = document(count=1)
    second = document(count=1, updated="2026-11-24T00:00:00Z", observed="2026-11-25T12:00:00Z")
    second["records"][0][field] = value
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        await run(conn, first)
        await run(conn, second)
        assert domain_snapshot(conn)[:3] == (1, 1, 2)
        assert (
            conn.execute(
                "SELECT count(*) FROM gold.dim_service_request_state WHERE is_current"
            ).fetchone()[0]
            == 1
        )


@pytest.mark.asyncio
async def test_missing_optional_categories_use_single_unknown_members(pipeline_db):
    value = document(count=2)
    for row in value["records"]:
        for field in ["agency", "agency_name", "complaint_type", "borough", "status"]:
            row.pop(field)
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        await run(conn, value)
        assert conn.execute("SELECT count(*) FROM gold.dim_agency").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM gold.dim_complaint_type").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM gold.dim_borough").fetchone()[0] == 1
        assert (
            conn.execute(
                "SELECT count(*) FROM gold.fact_service_requests WHERE NOT metric_eligible"
            ).fetchone()[0]
            == 2
        )


@pytest.mark.asyncio
async def test_interrupted_validation_resumes_durable_batches_without_refetch(
    pipeline_db, monkeypatch
):
    import nyc311_pipeline.validation.staging as staging

    value = document(count=1)
    template = value["records"][0]
    value["records"] = [template | {"unique_key": f"SYN-{i:04d}"} for i in range(1001)]
    original = staging.save_batch
    calls = []

    def interrupt_second_batch(conn, run_id, batch):
        calls.append(len(batch))
        if len(calls) == 2:
            raise psycopg.OperationalError("synthetic validation interruption")
        return original(conn, run_id, batch)

    monkeypatch.setattr(staging, "save_batch", interrupt_second_batch)
    identity = uuid4()
    with psycopg.connect(pipeline_db, autocommit=True) as conn:
        with pytest.raises(psycopg.Error):
            await run(conn, value, run_id=identity)
        assert conn.execute("SELECT count(*) FROM ops.validation_stage").fetchone()[0] == 1000
        assert domain_snapshot(conn)[:3] == (0, 0, 0)
        assert conn.execute(
            "SELECT received_count,ingest_complete,retryable FROM ops.pipeline_runs"
        ).fetchone() == (1001, True, True)
        monkeypatch.setattr(staging, "save_batch", original)
        result = await run(conn, value, resume_run_id=identity)
        assert result["published"] and result["received_count"] == 1001
        assert domain_snapshot(conn)[:3] == (1001, 1001, 1001)
        assert conn.execute("SELECT count(*) FROM ops.ingest_page_receipts").fetchone()[0] == 3
