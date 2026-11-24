"""Actual API adapter + actual PostgreSQL, with HTTPX synthetic fixtures only."""

import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from uuid import uuid4

import httpx
import psycopg
import pytest

from nyc311_pipeline.bronze_contracts import IngestScope, RunConflict, StorageError
from nyc311_pipeline.ingestion.client import ApiClient
from nyc311_pipeline.ingestion.models import IngestionError, source_time
from nyc311_pipeline.ingestion.service import ingest
from nyc311_pipeline.storage.bronze import BronzeRepository
from nyc311_pipeline.storage.migrations import apply_migrations

GEN = datetime(2026, 1, 1, tzinfo=UTC)
SCOPE = IngestScope((("2025-01-01T00:00:00", "2025-01-02T00:00:00"),), page_size=2)
ROWS = [
    {"unique_key": key, "created_date": "2025-01-01T12:00:00", "status": "Synthetic"}
    for key in ["10", "2", "3", "4"]
]


class FixtureSource:
    def __init__(self, rows=None):
        self.rows = ROWS if rows is None else rows
        self.requests = []
        self.generation = GEN
        self.out_of_date = "false"
        self.malformed = False
        self.unavailable = False

    def handle(self, request):
        self.requests.append(request)
        if self.unavailable:
            raise httpx.ConnectError("synthetic transport failure")
        headers = {
            "X-SODA2-Data-Out-Of-Date": self.out_of_date,
            "X-SODA2-Truth-Last-Modified": format_datetime(self.generation, usegmt=True),
            "X-SODA2-Secondary-Last-Modified": format_datetime(self.generation, usegmt=True),
        }
        where = request.url.params["$where"]
        start = re.search("created_date >= '([^']+)'", where)[1]
        end = re.search("created_date < '([^']+)'", where)[1]
        key = re.search("unique_key > '([^']+)'", where)
        records = [
            r
            for r in self.rows
            if source_time(start) <= source_time(r["created_date"]) < source_time(end)
            and (key is None or r["unique_key"] > key[1])
        ]
        records = sorted(records, key=lambda r: (source_time(r["created_date"]), r["unique_key"]))
        return httpx.Response(
            200,
            json={} if self.malformed else records[: int(request.url.params["$limit"])],
            headers=headers,
        )

    def client(self):
        async def no_wait(seconds):
            pass

        return ApiClient(
            transport=httpx.MockTransport(self.handle), sleeper=no_wait, jitter=lambda ceiling: 0
        )


@pytest.fixture
def ingestion_db(isolated_db):
    apply_migrations(isolated_db)
    return isolated_db


def snapshot(conn):
    return conn.execute(
        "SELECT received_count,raw_inserted_count,status,ingest_complete,"
        "published_at,successful_update_upper_utc FROM ops.pipeline_runs"
    ).fetchone()


@pytest.mark.asyncio
async def test_fresh_equal_timestamp_extraction_and_completed_resume(ingestion_db):
    source = FixtureSource()
    with psycopg.connect(ingestion_db, autocommit=True) as conn:
        repo = BronzeRepository(conn)
        async with source.client() as client:
            result = await ingest(client, repo, SCOPE)
            assert result.outcome == "completed" and result.received_this_invocation == 4
            assert not result.published
            assert len(source.requests) == 3  # Two full pages and the required empty page.
            assert snapshot(conn) == (4, 4, "paused", True, None, None)
            assert conn.execute(
                "SELECT payload->>'unique_key' FROM ops.run_records r "
                "JOIN bronze.raw_service_requests b USING(raw_id) "
                "ORDER BY page_no,row_ordinal"
            ).fetchall() == [("10",), ("2",), ("3",), ("4",)]
            again = await ingest(client, repo, SCOPE, resume_run_id=result.run.run_id)
            assert again.received_this_invocation == 0 and len(source.requests) == 3


@pytest.mark.asyncio
async def test_cap_then_new_connection_resume_preserves_scope_and_counts(ingestion_db):
    source = FixtureSource()
    async with source.client() as client:
        with psycopg.connect(ingestion_db, autocommit=True) as conn:
            result = await ingest(client, BronzeRepository(conn), SCOPE, max_records=3)
            assert result.outcome == "paused" and not result.run.ingest_complete
            assert snapshot(conn) == (3, 3, "paused", False, None, None)
            assert [r.url.params["$limit"] for r in source.requests] == ["2", "1"]
        with psycopg.connect(ingestion_db, autocommit=True) as conn:
            result = await ingest(
                client,
                BronzeRepository(conn),
                SCOPE,
                resume_run_id=result.run.run_id,
                max_records=10,
            )
            assert result.outcome == "completed" and result.received_this_invocation == 1
            assert snapshot(conn) == (4, 4, "paused", True, None, None)
            assert (
                conn.execute("SELECT count(*) FROM bronze.raw_service_requests").fetchone()[0] == 4
            )


class SimulatedDeath(RuntimeError):
    pass


@pytest.mark.asyncio
@pytest.mark.parametrize("after_commit", [False, True])
async def test_process_restart_before_or_after_commit(ingestion_db, monkeypatch, after_commit):
    source, identity = FixtureSource(), uuid4()
    async with source.client() as client:
        with psycopg.connect(ingestion_db, autocommit=True) as conn:
            repo = BronzeRepository(conn)
            original = repo.commit_page

            def die(*args):
                if after_commit:
                    original(*args)
                raise SimulatedDeath()

            monkeypatch.setattr(repo, "commit_page", die)
            with pytest.raises(SimulatedDeath):
                await ingest(client, repo, SCOPE, run_id=identity)
            assert repo.load_checkpoint(identity, "0").page_no == int(after_commit)
        with psycopg.connect(ingestion_db, autocommit=True) as conn:
            result = await ingest(client, BronzeRepository(conn), SCOPE, resume_run_id=identity)
            assert result.outcome == "completed" and snapshot(conn)[:2] == (4, 4)
            assert conn.execute("SELECT count(*) FROM ops.run_records").fetchone()[0] == 4


@pytest.mark.asyncio
async def test_lost_commit_ack_uses_exact_receipt_not_refetch(ingestion_db, monkeypatch):
    source = FixtureSource()
    with psycopg.connect(ingestion_db, autocommit=True) as conn:
        repo = BronzeRepository(conn)
        original, attempts = repo.commit_page, []

        def lose_ack(*args):
            result = original(*args)
            attempts.append(result)
            if len(attempts) == 1:
                raise StorageError(retryable=True)
            return result

        monkeypatch.setattr(repo, "commit_page", lose_ack)
        async with source.client() as client:
            result = await ingest(client, repo, SCOPE)
        assert result.outcome == "completed" and attempts[1].replayed
        assert len(source.requests) == 3 and len(attempts) == 4
        assert snapshot(conn)[:2] == (4, 4)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["stale", "malformed", "transport"])
async def test_source_failures_leave_no_checkpoint_or_raw_progress(ingestion_db, failure):
    source, identity = FixtureSource(), uuid4()
    source.out_of_date = "true" if failure == "stale" else "false"
    source.malformed = failure == "malformed"
    source.unavailable = failure == "transport"
    with psycopg.connect(ingestion_db, autocommit=True) as conn:
        repo = BronzeRepository(conn)
        async with source.client() as client:
            with pytest.raises(IngestionError):
                await ingest(client, repo, SCOPE, run_id=identity)
        assert snapshot(conn) == (0, 0, "failed", False, None, None)
        assert repo.load_checkpoint(identity, "0").page_no == 0
        assert conn.execute("SELECT count(*) FROM ops.ingest_page_receipts").fetchone()[0] == 0
        assert len(source.requests) == (1 if failure == "malformed" else 4)
        if failure != "malformed":
            source.out_of_date, source.unavailable = "false", False
            async with source.client() as client:
                assert (
                    await ingest(client, repo, SCOPE, resume_run_id=identity)
                ).outcome == "completed"


@pytest.mark.asyncio
async def test_generation_change_on_resume_fails_run_without_new_rows(ingestion_db):
    source = FixtureSource()
    with psycopg.connect(ingestion_db, autocommit=True) as conn:
        repo = BronzeRepository(conn)
        async with source.client() as client:
            paused = await ingest(client, repo, SCOPE, max_records=1)
            source.generation += timedelta(days=1)
            with pytest.raises(IngestionError, match="source_generation_changed"):
                await ingest(client, repo, SCOPE, resume_run_id=paused.run.run_id)
            assert snapshot(conn) == (1, 1, "failed", False, None, None)
            assert repo.load_checkpoint(paused.run.run_id, "0").page_no == 1
            with pytest.raises(RunConflict):
                await ingest(client, repo, SCOPE, resume_run_id=paused.run.run_id)
            # Explicit new run and same bounds: prior Bronze versions remain auditable.
            finished = await ingest(client, repo, SCOPE)
            assert finished.outcome == "completed" and finished.run.raw_inserted_count == 3


@pytest.mark.asyncio
async def test_changed_scope_resume_rejected_without_request(ingestion_db):
    source = FixtureSource()
    with psycopg.connect(ingestion_db, autocommit=True) as conn:
        repo = BronzeRepository(conn)
        async with source.client() as client:
            paused = await ingest(client, repo, SCOPE, max_records=1)
            before = len(source.requests)
            with pytest.raises(RunConflict):
                await ingest(
                    client, repo, replace(SCOPE, page_size=3), resume_run_id=paused.run.run_id
                )
            assert len(source.requests) == before and snapshot(conn)[:2] == (1, 1)


@pytest.mark.asyncio
async def test_lost_session_requires_new_lock_and_explicit_resume(ingestion_db, monkeypatch):
    source, identity = FixtureSource(), uuid4()
    with psycopg.connect(ingestion_db, autocommit=True) as conn:
        repo = BronzeRepository(conn)
        original = repo.commit_page

        def die_after_commit(*args):
            original(*args)
            conn.close()
            raise StorageError(retryable=True)

        monkeypatch.setattr(repo, "commit_page", die_after_commit)
        async with source.client() as client:
            with pytest.raises(StorageError):
                await ingest(client, repo, SCOPE, run_id=identity)
    with psycopg.connect(ingestion_db, autocommit=True) as conn:
        repo = BronzeRepository(conn)
        assert repo.load_checkpoint(identity, "0").page_no == 1
        assert repo.load_run(identity).status == "running"  # Failure write was impossible.
        async with source.client() as client:
            assert (
                await ingest(client, repo, SCOPE, resume_run_id=identity)
            ).outcome == "completed"
        assert snapshot(conn)[:2] == (4, 4)


@pytest.mark.asyncio
async def test_storage_rollback_records_failed_ingestion_without_progress(ingestion_db):
    source, identity = FixtureSource(), uuid4()
    with psycopg.connect(ingestion_db, autocommit=True) as conn:
        conn.execute("""CREATE FUNCTION ops.fail_counter() RETURNS trigger LANGUAGE plpgsql
            AS $$ BEGIN IF NEW.received_count > OLD.received_count THEN
            RAISE EXCEPTION 'synthetic failure'; END IF; RETURN NEW; END $$;
            CREATE TRIGGER fail_counter BEFORE UPDATE ON ops.pipeline_runs
            FOR EACH ROW EXECUTE FUNCTION ops.fail_counter();""")
        repo = BronzeRepository(conn)
        async with source.client() as client:
            with pytest.raises(StorageError):
                await ingest(client, repo, SCOPE, run_id=identity)
        assert snapshot(conn) == (0, 0, "failed", False, None, None)
        assert repo.load_checkpoint(identity, "0").page_no == 0
        assert conn.execute("SELECT count(*) FROM bronze.raw_service_requests").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM ops.run_records").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM ops.ingest_page_receipts").fetchone()[0] == 0
        assert len(source.requests) == 1


@pytest.mark.asyncio
async def test_disjoint_segments_share_generation_and_exhaust_independently(ingestion_db):
    source = FixtureSource()
    scope = replace(
        SCOPE, intervals=SCOPE.intervals + (("2025-01-02T00:00:00", "2025-01-03T00:00:00"),)
    )
    with psycopg.connect(ingestion_db, autocommit=True) as conn:
        repo = BronzeRepository(conn)
        async with source.client() as client:
            result = await ingest(client, repo, scope)
        assert result.outcome == "completed" and len(source.requests) == 4
        for segment in scope.segment_ids:
            cp = repo.load_checkpoint(result.run.run_id, segment)
            assert cp.generation == GEN and cp.exhausted


@pytest.mark.asyncio
async def test_update_mode_persists_typed_cursor_without_publication_watermark(ingestion_db):
    scope = replace(
        SCOPE,
        kind="update",
        page_size=1,
        update_lower_utc="2025-12-01T00:00:00Z",
        update_upper_utc="2026-01-01T00:00:00Z",
    )
    records = [
        ROWS[0] | {":updated_at": f"2025-12-0{i}T00:00:00Z", "status": status}
        for i, status in [(1, "Synthetic A"), (2, "Synthetic B")]
    ]
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(
            200,
            json=records[len(calls) - 1 : len(calls)],
            headers={
                "X-SODA2-Data-Out-Of-Date": "false",
                "X-SODA2-Truth-Last-Modified": format_datetime(GEN, usegmt=True),
                "X-SODA2-Secondary-Last-Modified": format_datetime(GEN, usegmt=True),
            },
        )

    with psycopg.connect(ingestion_db, autocommit=True) as conn:
        repo = BronzeRepository(conn)
        async with ApiClient(transport=httpx.MockTransport(handle)) as client:
            result = await ingest(client, repo, scope)
        assert result.outcome == "completed" and snapshot(conn) == (
            2,
            2,
            "paused",
            True,
            None,
            None,
        )
        cp = repo.load_checkpoint(result.run.run_id, "0")
        assert cp.cursor.kind == "update" and cp.exhausted
        assert ":updated_at > '2025-12-01T00:00:00Z'" in calls[1].url.params["$where"]
