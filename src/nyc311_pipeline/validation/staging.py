"""Bounded Python batches; PostgreSQL holds the immutable run's read cursor."""

from itertools import groupby
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from nyc311_pipeline.bronze_contracts import fingerprint
from nyc311_pipeline.ingestion.models import utc_text, utc_time

from .records import QualityError, validate

CANDIDATES = """
WITH observations AS (
 SELECT b.unique_key,b.raw_id,b.raw_hash,b.payload,r.source_updated_at,
        min(r.observed_at) AS observed_at
 FROM ops.run_records r JOIN bronze.raw_service_requests b USING(raw_id)
 WHERE r.run_id=%s GROUP BY b.raw_id,r.source_updated_at
), ranked AS (
 SELECT *,max(source_updated_at) OVER (PARTITION BY unique_key) AS latest FROM observations
)
SELECT unique_key,raw_id,raw_hash,payload,source_updated_at,observed_at FROM ranked
WHERE source_updated_at IS NOT DISTINCT FROM latest
ORDER BY unique_key COLLATE "C",raw_id
"""


def save_rejections(conn, run_id, batch):
    if not batch:
        return
    conn.execute(
        """
        INSERT INTO ops.quarantine
          (run_id,unique_key,raw_id,raw_hash,payload,reasons,observed_at)
        SELECT %s,x.unique_key,x.raw_id,x.raw_hash,x.payload,x.reasons,x.observed_at
        FROM jsonb_to_recordset(%s) AS x(unique_key text,raw_id bigint,raw_hash text,
                                       payload jsonb,reasons text[],observed_at timestamptz)
        ON CONFLICT (run_id,raw_hash) DO UPDATE SET reasons=ARRAY(
          SELECT DISTINCT x FROM unnest(ops.quarantine.reasons || EXCLUDED.reasons) x ORDER BY x)
        """,
        (run_id, Jsonb(list(batch.values()))),
    )


def stage_run(conn, run_id: UUID, settings: dict, batch_size: int = 1000) -> dict:
    if not 1 <= batch_size <= 5000:
        raise ValueError("batch_size")
    # WITH HOLD survives batch write commits. No dataset is accumulated in Python.
    rejections = {}

    def reject(row, reasons):
        previous = rejections.get(row[2], {})
        rejections[row[2]] = dict(
            unique_key=row[0],
            raw_id=row[1],
            raw_hash=row[2],
            payload=row[3],
            reasons=sorted(set(previous.get("reasons", [])) | set(reasons)),
            observed_at=utc_text(row[5]),
        )
        if len(rejections) >= batch_size:
            with conn.transaction():
                save_rejections(conn, run_id, rejections)
            rejections.clear()

    def flush(batch):
        with conn.transaction():
            save_rejections(conn, run_id, rejections)
            save_batch(conn, run_id, batch)
        rejections.clear()

    cursor = conn.cursor(name="validation_" + uuid4().hex, withhold=True)
    try:
        with conn.transaction():
            cursor.execute(CANDIDATES, (run_id,))

        def rows():
            while batch := cursor.fetchmany(batch_size):
                yield from batch

        pending = []
        for key, variants in groupby(rows(), key=lambda row: row[0]):
            first = None
            for other in variants:
                if first is None:
                    first = other
                    result = validate(first[3])
                    reasons = set(result.reasons)
                    signature = result.business_hash
                    continue
                alternative = validate(other[3])
                if (alternative.business_hash, alternative.reasons) != (signature, result.reasons):
                    reasons.add("conflicting_source_versions")
                    reject(first, reasons)
                    reject(other, reasons | set(alternative.reasons))
                elif alternative.reasons:
                    reject(other, alternative.reasons)
            outside = False
            if not reasons:
                created = utc_time(result.data["created_date_utc"])
                outside = not (
                    utc_time(settings["start_utc"]) <= created < utc_time(settings["end_utc"])
                )
            if reasons:
                reject(first, reasons)
            outcome = "invalid" if reasons else "outside_scope" if outside else "valid"
            item = dict(
                unique_key=key,
                raw_id=first[1],
                source_updated_at=utc_text(first[4]) if first[4] else None,
                observed_at=utc_text(first[5]),
                outcome=outcome,
                reasons=sorted(reasons),
                normalized=result.data if not reasons else None,
                business_hash=result.business_hash,
                state_hash=result.state_hash,
            )
            item["stage_hash"] = fingerprint(item)
            pending.append(item)
            if len(pending) >= batch_size:
                flush(pending)
                pending.clear()
        if pending:
            flush(pending)
    finally:
        cursor.close()
    counts = conn.execute(
        """
        SELECT count(*) FILTER (WHERE outcome <> 'outside_scope'),
               count(*) FILTER (WHERE outcome='valid'), count(*) FILTER (WHERE outcome='invalid'),
               count(*) FILTER (WHERE outcome='outside_scope')
        FROM ops.validation_stage WHERE run_id=%s
        """,
        (run_id,),
    ).fetchone()
    expected = conn.execute(
        """SELECT count(DISTINCT b.unique_key) FROM ops.run_records r
        JOIN bronze.raw_service_requests b USING(raw_id) WHERE r.run_id=%s""",
        (run_id,),
    ).fetchone()[0]
    if counts[0] + counts[3] != expected:
        raise QualityError("incomplete_validation")
    conn.execute(
        """UPDATE ops.pipeline_runs SET evaluated_count=%s,valid_count=%s,invalid_count=%s,
        outside_scope_count=%s,heartbeat_at=clock_timestamp() WHERE run_id=%s""",
        (*counts, run_id),
    )
    return dict(zip(("evaluated", "valid", "invalid", "outside_scope"), counts, strict=True))


def save_batch(conn, run_id, batch):
    with conn.transaction():
        result = conn.execute(
            """
            INSERT INTO ops.validation_stage
              (run_id,unique_key,raw_id,source_updated_at,observed_at,outcome,reasons,normalized,
               business_hash,state_hash,stage_hash)
            SELECT %s,x.unique_key,x.raw_id,x.source_updated_at,x.observed_at,x.outcome,x.reasons,
                   x.normalized,x.business_hash,x.state_hash,x.stage_hash
            FROM jsonb_to_recordset(%s) AS x(unique_key text,raw_id bigint,
                source_updated_at timestamptz,
                observed_at timestamptz,outcome text,reasons text[],normalized jsonb,
                business_hash text,state_hash text,stage_hash text)
            ON CONFLICT(run_id,unique_key) DO UPDATE SET stage_hash=EXCLUDED.stage_hash
            WHERE ops.validation_stage.stage_hash=EXCLUDED.stage_hash RETURNING unique_key
            """,
            (run_id, Jsonb(batch)),
        ).fetchall()
        if len(result) != len(batch):
            raise QualityError("conflicting_validation_replay")
