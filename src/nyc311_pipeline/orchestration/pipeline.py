"""Small modular monolith: one locked session, durable Bronze, staged validation, atomic publish."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import psycopg

from nyc311_pipeline.bronze_contracts import IngestScope, RunConflict, fingerprint
from nyc311_pipeline.ingestion.models import utc_text, utc_time
from nyc311_pipeline.ingestion.service import ingest
from nyc311_pipeline.silver.publish import publish
from nyc311_pipeline.storage.bronze import BronzeRepository
from nyc311_pipeline.validation.records import (
    POLICY,
    SOURCE_ZONE,
    TZDATA_VERSION,
    PipelineError,
    quality_gate,
)
from nyc311_pipeline.validation.staging import stage_run


def report(conn, run_id: UUID) -> dict:
    from psycopg.rows import dict_row

    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """SELECT run_id,status,phase,ingest_complete,published_at,started_at,heartbeat_at,
            finished_at,received_count,
            raw_inserted_count,evaluated_count,valid_count,invalid_count,outside_scope_count,
            retryable,error_category,successful_update_upper_utc
            FROM ops.pipeline_runs WHERE run_id=%s""",
            (run_id,),
        )
        result = cursor.fetchone()
    if result is None:
        raise RunConflict()
    result["published"] = result["published_at"] is not None
    result["checkpoints"] = [
        dict(segment_id=r[0], page_no=r[1], exhausted=r[2])
        for r in conn.execute(
            "SELECT segment_id,page_no,exhausted FROM ops.ingest_checkpoints "
            "WHERE run_id=%s ORDER BY segment_id",
            (run_id,),
        ).fetchall()
    ]
    return result


def bounds(start: datetime, end: datetime) -> tuple[tuple[str, str], ...]:
    if start >= end:
        raise PipelineError("configuration")
    # NY's modern DST offset change is one hour. Superset handles a backwards
    # wall clock even for sub-hour UTC windows; validation applies exact UTC scope.
    wall_start = start.astimezone(SOURCE_ZONE).replace(tzinfo=None)
    wall_end = end.astimezone(SOURCE_ZONE).replace(tzinfo=None)
    return (
        (
            (min(wall_start, wall_end) - timedelta(hours=2)).isoformat(),
            (max(wall_start, wall_end) + timedelta(hours=2)).isoformat(),
        ),
    )


def make_plan(conn, start, end, mode, page_size, initial_lower, threshold, fixture_hash, now):
    if mode not in {"backfill", "incremental"}:
        raise PipelineError("configuration")
    quality_gate(1, 0, str(threshold))
    start, end, now = utc_time(start), utc_time(end), utc_time(now)
    cohort_id = fingerprint(["erm2-nwe9", utc_text(start), utc_text(end), "NY-wall-v1"])
    lower = upper = None
    if mode == "incremental":
        watermark = conn.execute(
            "SELECT updated_through FROM ops.publication_watermarks WHERE cohort_id=%s",
            (cohort_id,),
        ).fetchone()
        lower = watermark[0] - timedelta(hours=48) if watermark else utc_time(initial_lower)
        upper = now - timedelta(minutes=5)
    scope = IngestScope(
        bounds(start, end),
        kind="update" if mode == "incremental" else "creation",
        page_size=page_size,
        update_lower_utc=lower,
        update_upper_utc=upper,
    )
    settings = dict(
        policy=POLICY,
        start_utc=utc_text(start),
        end_utc=utc_text(end),
        threshold=str(threshold),
        fixture_hash=fixture_hash,
        tzdata_version=TZDATA_VERSION,
        cohort_id=cohort_id,
        update_upper_utc=utc_text(upper) if upper else None,
    )
    return scope, settings


def fail_run(conn, run_id, category, retryable):
    if conn.closed:
        return
    try:
        with conn.transaction():
            previous = conn.execute(
                "SELECT status FROM ops.pipeline_runs "
                "WHERE run_id=%s AND published_at IS NULL FOR UPDATE",
                (run_id,),
            ).fetchone()
            if previous:
                conn.execute(
                    """UPDATE ops.pipeline_runs SET status='failed',error_category=%s,
                    retryable=%s,finished_at=clock_timestamp(),heartbeat_at=clock_timestamp()
                    WHERE run_id=%s""",
                    (category, retryable, run_id),
                )
                if previous[0] != "failed":
                    conn.execute(
                        "INSERT INTO ops.run_events(run_id,event,category,retryable) "
                        "VALUES (%s,'failed',%s,%s)",
                        (run_id, category, retryable),
                    )
    except psycopg.Error:
        pass  # Never claim a failure write succeeded on an unavailable connection.


async def execute(
    conn,
    client,
    *,
    start=None,
    end=None,
    mode=None,
    page_size=None,
    initial_lower=None,
    threshold=None,
    max_records=None,
    resume_run_id=None,
    run_id=None,
    fixture_hash=None,
    now=None,
):
    identity = resume_run_id or run_id or uuid4()
    repo = BronzeRepository(conn)
    with repo.dataset_lock():
        if resume_run_id:
            run = repo.load_run(identity)
            row = conn.execute(
                "SELECT config FROM ops.run_settings WHERE run_id=%s", (identity,)
            ).fetchone()
            if row is None:
                raise PipelineError("missing_run_settings")
            scope, settings = run.scope, row[0]
            if (
                settings["fixture_hash"] != fixture_hash
                or settings["policy"] != POLICY
                or settings["tzdata_version"] != TZDATA_VERSION
            ):
                raise RunConflict()
            if page_size is not None and page_size != scope.page_size:
                raise RunConflict()
            if threshold is not None and threshold != settings["threshold"]:
                raise RunConflict()
            if mode is not None and (mode == "incremental") != (scope.kind == "update"):
                raise RunConflict()
            if initial_lower is not None and utc_time(initial_lower) != scope.update_lower_utc:
                raise RunConflict()
            if start is not None and utc_time(start) != utc_time(settings["start_utc"]):
                raise RunConflict()
            if end is not None and utc_time(end) != utc_time(settings["end_utc"]):
                raise RunConflict()
            if report(conn, identity)["published"]:
                return report(conn, identity)
            failure = conn.execute(
                "SELECT status,retryable FROM ops.pipeline_runs WHERE run_id=%s", (identity,)
            ).fetchone()
            if failure[0] == "failed" and not failure[1]:
                raise RunConflict()
        else:
            if conn.execute("""SELECT 1 FROM ops.pipeline_runs r
                JOIN ops.run_settings s USING(run_id)
                WHERE r.dataset_id='erm2-nwe9' AND r.published_at IS NULL
                AND (r.status IN ('pending','running','paused') OR r.retryable)""").fetchone():
                raise RunConflict()
            scope, settings = make_plan(
                conn,
                start,
                end,
                mode or "backfill",
                page_size or 1000,
                initial_lower,
                threshold or "0.05",
                fixture_hash,
                now or datetime.now(UTC),
            )
            repo.begin_run(identity, scope, settings=settings)
        try:
            if not repo.load_run(identity).ingest_complete:
                result = await ingest(
                    client,
                    repo,
                    scope,
                    resume_run_id=identity,
                    max_records=max_records,
                    acquire_lock=False,
                )
                if not result.run.ingest_complete:
                    return report(conn, identity)
            conn.execute(
                "UPDATE ops.pipeline_runs SET status='running',phase='validate',"
                "retryable=false,error_category=NULL,finished_at=NULL,"
                "heartbeat_at=clock_timestamp() WHERE run_id=%s",
                (identity,),
            )
            counts = stage_run(conn, identity, settings)
            conn.execute(
                "UPDATE ops.pipeline_runs SET phase='publish' WHERE run_id=%s", (identity,)
            )
            publish(conn, identity, settings, counts)
            return report(conn, identity)
        except Exception as error:
            fail_run(
                conn,
                identity,
                getattr(error, "category", "storage"),
                getattr(error, "retryable", isinstance(error, psycopg.Error)),
            )
            raise
