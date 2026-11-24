"""Durability tests use isolated PostgreSQL and entirely synthetic records."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest

from nyc311_pipeline.bronze_contracts import IngestScope, RunConflict, StorageError
from nyc311_pipeline.ingestion.models import CreationCursor, IngestionError, Page, utc_text
from nyc311_pipeline.storage.bronze import BronzeRepository
from nyc311_pipeline.storage.migrations import apply_migrations, rollback_migrations

GEN = datetime(2026, 1, 1, tzinfo=UTC)
SCOPE = IngestScope((("2025-01-01T00:00:00", "2025-01-02T00:00:00"),), page_size=100)


def row(key="10"):
    return {"unique_key": key, "created_date": "2025-01-01T12:00:00", "status": "Synthetic"}


def page(records=None, cursor=None):
    records = [row()] if records is None else records
    return Page(
        tuple(records),
        CreationCursor(records[-1]["created_date"], records[-1]["unique_key"])
        if records
        else cursor,
        not records,
        GEN,
        GEN,
        "fixture",
        {
            "out_of_date": "false",
            "truth_last_modified": utc_text(GEN),
            "secondary_last_modified": utc_text(GEN),
            "status_code": "200",
        },
    )


@pytest.fixture
def bronze_db(isolated_db):
    apply_migrations(isolated_db)
    return isolated_db


@pytest.fixture
def repo(bronze_db):
    with psycopg.connect(bronze_db, autocommit=True) as conn:
        repository = BronzeRepository(conn)
        with repository.dataset_lock():
            yield repository


def start(repo, scope=SCOPE):
    run_id = uuid4()
    repo.begin_run(run_id, scope)
    return run_id, repo.load_checkpoint(run_id, "0")


def counts(repo):
    return tuple(
        repo.connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in ["bronze.raw_service_requests", "ops.run_records", "ops.ingest_page_receipts"]
    )


def complete(repo, run_id, checkpoint):
    result = repo.commit_page(run_id, checkpoint, page([], checkpoint.cursor))
    assert result.checkpoint.exhausted
    repo.finish_ingestion(run_id, outcome="completed")


def test_domain_migration_up_replay_and_down(bronze_db):
    assert apply_migrations(bronze_db).applied == ()
    with psycopg.connect(bronze_db) as conn:
        tables = conn.execute(
            "SELECT table_schema,table_name FROM information_schema.tables "
            "WHERE table_schema IN ('bronze','silver','gold','ops')"
        ).fetchall()
        assert len(tables) == 6
        assert all(schema not in {"silver", "gold"} for schema, _ in tables)
    assert rollback_migrations(bronze_db, target_version=1).rolled_back == (
        "0002_bronze_ingestion",
    )
    assert apply_migrations(bronze_db).applied == ("0002_bronze_ingestion",)


def test_atomic_fresh_page_and_exhaustion(repo):
    run_id, cp = start(repo)
    result = repo.commit_page(run_id, cp, page([row("10"), row("2")]))
    assert result.received_count == result.inserted_raw_versions == 2
    assert repo.load_checkpoint(run_id, "0") == result.checkpoint
    assert counts(repo) == (2, 2, 1)
    complete(repo, run_id, result.checkpoint)
    run = repo.load_run(run_id)
    assert run.ingest_complete and run.status == "paused" and run.received_count == 2
    assert repo.connection.execute(
        "SELECT published_at,successful_update_upper_utc FROM ops.pipeline_runs"
    ).fetchone() == (None, None)


def test_lost_ack_receipt_replay_excludes_receive_metadata(repo):
    run_id, cp = start(repo)
    original = page()
    committed = repo.commit_page(run_id, cp, original)
    replay = repo.commit_page(
        run_id,
        cp,
        replace(original, received_at_utc=GEN + timedelta(days=1), request_id="different"),
    )
    assert replay.replayed and replay.checkpoint == committed.checkpoint
    assert counts(repo) == (1, 1, 1)
    assert repo.load_run(run_id).received_count == 1
    # Old exact receipts remain resolvable after subsequent pages.
    complete(repo, run_id, committed.checkpoint)
    assert repo.commit_page(run_id, cp, original).replayed


def test_new_run_associates_existing_versions_without_duplicate_payload(repo):
    run_id, cp = start(repo)
    committed = repo.commit_page(run_id, cp, page())
    complete(repo, run_id, committed.checkpoint)
    other, initial = start(repo)
    replay = repo.commit_page(other, initial, page())
    assert replay.received_count == 1 and replay.inserted_raw_versions == 0
    assert counts(repo) == (1, 2, 3)


def test_conflicting_receipt_and_stale_cas_rejected(repo):
    run_id, cp = start(repo)
    repo.commit_page(run_id, cp, page())
    with pytest.raises(RunConflict):
        repo.commit_page(run_id, cp, page([row("20")]))
    with pytest.raises(RunConflict):
        repo.commit_page(run_id, replace(cp, page_no=5), page([row("30")]))
    assert counts(repo) == (1, 1, 1)


def test_rollback_after_all_page_writes_then_safe_retry(repo):
    run_id, cp = start(repo)
    repo.connection.execute("""CREATE FUNCTION ops.fail_counter() RETURNS trigger LANGUAGE plpgsql
        AS $$ BEGIN IF NEW.received_count > OLD.received_count THEN
        RAISE EXCEPTION 'synthetic failure'; END IF; RETURN NEW; END $$;
        CREATE TRIGGER fail_counter BEFORE UPDATE ON ops.pipeline_runs
        FOR EACH ROW EXECUTE FUNCTION ops.fail_counter();""")
    with pytest.raises(StorageError):
        repo.commit_page(run_id, cp, page())
    assert counts(repo) == (0, 0, 0)
    assert repo.load_checkpoint(run_id, "0") == cp
    assert repo.load_run(run_id).generation is None
    repo.connection.execute("DROP TRIGGER fail_counter ON ops.pipeline_runs")
    assert repo.commit_page(run_id, cp, page()).inserted_raw_versions == 1


@pytest.mark.parametrize("bad", ["generation", "stale", "order", "cursor", "exhaustion"])
def test_invalid_pages_cannot_advance(repo, bad):
    run_id, cp = start(repo)
    p = page()
    if bad == "generation":
        first = repo.commit_page(run_id, cp, p)
        cp = first.checkpoint
        p = replace(page([row("20")]), generation=GEN + timedelta(days=1))
    elif bad == "stale":
        p = replace(p, http_metadata=p.http_metadata | {"out_of_date": "true"})
    elif bad == "order":
        p = page([row("2"), row("10")])
    elif bad == "cursor":
        p = replace(p, next_cursor=None)
    else:
        p = replace(p, exhausted=True)
    before = counts(repo)
    with pytest.raises(IngestionError):
        repo.commit_page(run_id, cp, p)
    assert repo.load_checkpoint(run_id, "0") == cp and counts(repo) == before


def test_multiple_segments_pin_one_generation(repo):
    scope = IngestScope(SCOPE.intervals + (("2025-01-02T00:00:00", "2025-01-03T00:00:00"),))
    run_id, cp = start(repo, scope)
    repo.commit_page(run_id, cp, page([]))
    second = repo.load_checkpoint(run_id, "1")
    with pytest.raises(IngestionError, match="source_generation_changed"):
        repo.commit_page(run_id, second, replace(page([]), generation=GEN + timedelta(days=1)))
    assert repo.load_checkpoint(run_id, "1") == second
    repo.commit_page(run_id, second, page([]))
    assert repo.finish_ingestion(run_id, outcome="completed").ingest_complete


def test_resume_config_and_lifecycle_guardrails(repo):
    run_id, cp = start(repo)
    with pytest.raises(RunConflict):
        repo.begin_run(uuid4(), SCOPE)
    with pytest.raises(RunConflict):
        repo.begin_run(run_id, replace(SCOPE, page_size=2), resume=True)
    with pytest.raises(RunConflict):
        repo.finish_ingestion(run_id, outcome="completed")
    repo.finish_ingestion(run_id, outcome="failed", category="api_transport", retryable=True)
    assert repo.begin_run(run_id, SCOPE, resume=True).status == "running"
    assert repo.load_checkpoint(run_id, "0") == cp
    repo.finish_ingestion(run_id, outcome="failed", category="source_generation_changed")
    with pytest.raises(RunConflict):
        repo.begin_run(run_id, SCOPE, resume=True)
    assert repo.connection.execute(
        "SELECT event,category FROM ops.run_events ORDER BY event_id"
    ).fetchall() == [
        ("started", None),
        ("failed", "api_transport"),
        ("resumed", None),
        ("failed", "source_generation_changed"),
    ]


def test_concurrent_dataset_writer_fails_and_then_stale_page_conflicts(bronze_db):
    with (
        psycopg.connect(bronze_db, autocommit=True) as a,
        psycopg.connect(bronze_db, autocommit=True) as b,
    ):
        first, second = BronzeRepository(a), BronzeRepository(b)

        def contender():
            with second.dataset_lock():
                raise AssertionError("must not acquire active lock")

        with first.dataset_lock():
            run_id, cp = start(first)
            with ThreadPoolExecutor(max_workers=1) as pool:
                with pytest.raises(RunConflict):
                    pool.submit(contender).result(timeout=5)
            first.commit_page(run_id, cp, page())
        with second.dataset_lock():
            with pytest.raises(RunConflict):
                second.commit_page(run_id, cp, page([row("20")]))
            assert second.commit_page(run_id, cp, page()).replayed


def test_restart_before_and_after_commit(bronze_db):
    run_id = uuid4()
    with psycopg.connect(bronze_db, autocommit=True) as conn:
        repo = BronzeRepository(conn)
        with repo.dataset_lock():
            repo.begin_run(run_id, SCOPE)
            cp = repo.load_checkpoint(run_id, "0")
    # New connection after death before commit: nothing progressed.
    with psycopg.connect(bronze_db, autocommit=True) as conn:
        repo = BronzeRepository(conn)
        with repo.dataset_lock():
            repo.begin_run(run_id, SCOPE, resume=True)
            assert repo.load_checkpoint(run_id, "0") == cp
            committed = repo.commit_page(run_id, cp, page())
    # New connection after death after commit: continue from durable cursor.
    with psycopg.connect(bronze_db, autocommit=True) as conn:
        repo = BronzeRepository(conn)
        with repo.dataset_lock():
            repo.begin_run(run_id, SCOPE, resume=True)
            assert repo.load_checkpoint(run_id, "0") == committed.checkpoint
            assert repo.commit_page(run_id, cp, page()).replayed
            assert counts(repo) == (1, 1, 1)


def test_caller_transactions_and_unlocked_mutations_rejected(bronze_db):
    with psycopg.connect(bronze_db) as conn:
        with pytest.raises(StorageError):
            BronzeRepository(conn)
    with psycopg.connect(bronze_db, autocommit=True) as conn:
        repo = BronzeRepository(conn)
        with pytest.raises(RunConflict):
            repo.begin_run(uuid4(), SCOPE)
        with repo.dataset_lock(), conn.transaction():
            with pytest.raises(StorageError):
                repo.begin_run(uuid4(), SCOPE)


def test_run_identity_and_generation_immutable(repo):
    run_id, cp = start(repo)
    repo.commit_page(run_id, cp, page())
    for column, value in [("scope_id", "0" * 64), ("generation", GEN + timedelta(days=1))]:
        with pytest.raises(psycopg.Error):
            repo.connection.execute(
                f"UPDATE ops.pipeline_runs SET {column}=%s WHERE run_id=%s", (value, run_id)
            )


def test_page_writes_are_batched_not_per_record(bronze_db):
    class CountingConnection:
        def __init__(self, connection):
            self.connection = connection
            self.statements = []

        def __getattr__(self, name):
            return getattr(self.connection, name)

        def execute(self, statement, *args, **kwargs):
            self.statements.append(statement)
            return self.connection.execute(statement, *args, **kwargs)

    with psycopg.connect(bronze_db, autocommit=True) as conn:
        counted = CountingConnection(conn)
        repo = BronzeRepository(counted)
        with repo.dataset_lock():
            run_id, cp = start(repo)
            counted.statements.clear()
            repo.commit_page(run_id, cp, page([row(f"{i:04d}") for i in range(100)]))
            assert len(counted.statements) == 8
            assert sum(s.startswith("INSERT") for s in counted.statements) == 3
            assert counts(repo) == (100, 100, 1)


def test_update_cursor_and_changed_attributes_in_synthetic_fixture(repo):
    from nyc311_pipeline.ingestion.models import UpdateCursor

    scope = IngestScope(
        SCOPE.intervals,
        kind="update",
        update_lower_utc="2025-12-01T00:00:00Z",
        update_upper_utc="2026-01-01T00:00:00Z",
    )
    run_id, cp = start(repo, scope)
    for hour, status in [(1, "Synthetic A"), (2, "Synthetic B")]:
        updated = f"2025-12-01T0{hour}:00:00Z"
        record = row() | {":updated_at": updated, "status": status}
        p = replace(page([record]), next_cursor=UpdateCursor(updated, "10"))
        cp = repo.commit_page(run_id, cp, p).checkpoint
    assert counts(repo) == (2, 2, 2)
    assert isinstance(repo.load_checkpoint(run_id, "0").cursor, UpdateCursor)
    assert (
        repo.connection.execute(
            "SELECT count(DISTINCT source_updated_at) FROM ops.run_records"
        ).fetchone()[0]
        == 2
    )
    # Synthetic version storage is not source-observed SCD2 evidence.
