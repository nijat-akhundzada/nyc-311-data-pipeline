"""A single transaction publishes Silver, Gold, run success and the watermark."""

from psycopg.types.json import Jsonb

from nyc311_pipeline.gold.publish import publish_gold
from nyc311_pipeline.validation.records import QualityError, quality_gate


def check_observations(conn, run_id):
    bad = conn.execute(
        """
        SELECT v.unique_key,v.raw_id,b.raw_hash,b.payload,v.source_updated_at,v.observed_at,
          CASE WHEN v.source_updated_at<s.source_updated_at THEN 'stale_observation'
               WHEN v.source_updated_at=s.source_updated_at AND v.business_hash<>s.business_hash
                 THEN 'conflicting_source_versions' ELSE 'observation_time_conflict' END
        FROM ops.validation_stage v JOIN silver.service_requests s USING(unique_key)
        JOIN bronze.raw_service_requests b ON b.raw_id=v.raw_id
        LEFT JOIN gold.dim_service_request_state d ON d.unique_key=v.unique_key AND d.is_current
        WHERE v.run_id=%s AND v.outcome='valid' AND
          (v.source_updated_at<s.source_updated_at OR
           (v.source_updated_at=s.source_updated_at AND v.business_hash<>s.business_hash) OR
           (v.state_hash<>d.state_hash AND v.observed_at<=d.valid_from))
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    if bad:
        # Quarantine must survive a rejected publication; no domain table is changed.
        conn.execute(
            """INSERT INTO ops.quarantine
            (run_id,unique_key,raw_id,raw_hash,payload,reasons,observed_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (run_id,raw_hash) DO NOTHING""",
            (run_id, bad[0], bad[1], bad[2], Jsonb(bad[3]), [bad[6]], bad[5]),
        )
        raise QualityError(bad[6])


def publish(conn, run_id, settings, counts):
    quality_gate(counts["evaluated"], counts["invalid"], settings["threshold"])
    if conn.execute(
        "SELECT 1 FROM ops.validation_stage WHERE run_id=%s "
        "AND 'conflicting_source_versions'=ANY(reasons)",
        (run_id,),
    ).fetchone():
        raise QualityError("conflicting_source_versions")
    check_observations(conn, run_id)
    with conn.transaction():
        run = conn.execute(
            "SELECT ingest_complete,published_at FROM ops.pipeline_runs WHERE run_id=%s FOR UPDATE",
            (run_id,),
        ).fetchone()
        if run[1] is not None:
            return
        if (
            not run[0]
            or conn.execute(
                "SELECT 1 FROM ops.ingest_checkpoints WHERE run_id=%s AND NOT exhausted", (run_id,)
            ).fetchone()
        ):
            raise QualityError("incomplete_ingestion")
        conn.execute(
            """
            INSERT INTO silver.service_requests
              (unique_key,created_at,closed_at,created_source,closed_source,agency,agency_name,
               complaint_type,status,status_key,borough,incident_zip,resolution_action_updated_at,
               source_updated_at,observed_at,raw_id,business_hash,state_hash,metric_eligible,
               metric_reason,resolution_seconds,published_run_id)
            SELECT unique_key,(normalized->>'created_date_utc')::timestamptz,
               (normalized->>'closed_date_utc')::timestamptz,normalized->>'created_date_source',
               normalized->>'closed_date_source',normalized->>'agency',normalized->>'agency_name',
               normalized->>'complaint_type',normalized->>'status',normalized->>'status_key',
               normalized->>'borough',normalized->>'incident_zip',
               (normalized->>'resolution_action_updated_date_utc')::timestamptz,
               source_updated_at,observed_at,raw_id,business_hash,state_hash,
               (normalized->>'metric_eligible')::boolean,normalized->>'metric_reason',
               (normalized->>'resolution_seconds')::double precision,%s
            FROM ops.validation_stage WHERE run_id=%s AND outcome='valid'
            ON CONFLICT(unique_key) DO UPDATE SET
              created_at=EXCLUDED.created_at,closed_at=EXCLUDED.closed_at,
              created_source=EXCLUDED.created_source,closed_source=EXCLUDED.closed_source,
              agency=EXCLUDED.agency,agency_name=EXCLUDED.agency_name,
              complaint_type=EXCLUDED.complaint_type,status=EXCLUDED.status,status_key=EXCLUDED.status_key,
              borough=EXCLUDED.borough,incident_zip=EXCLUDED.incident_zip,
              resolution_action_updated_at=EXCLUDED.resolution_action_updated_at,
              source_updated_at=EXCLUDED.source_updated_at,observed_at=EXCLUDED.observed_at,
              raw_id=EXCLUDED.raw_id,business_hash=EXCLUDED.business_hash,state_hash=EXCLUDED.state_hash,
              metric_eligible=EXCLUDED.metric_eligible,metric_reason=EXCLUDED.metric_reason,
              resolution_seconds=EXCLUDED.resolution_seconds,published_run_id=EXCLUDED.published_run_id
            WHERE EXCLUDED.source_updated_at>silver.service_requests.source_updated_at
            """,
            (run_id, run_id),
        )
        publish_gold(conn, run_id)
        upper = None
        if settings["update_upper_utc"] is not None:
            upper = settings["update_upper_utc"]
            conn.execute(
                """INSERT INTO ops.publication_watermarks
                (cohort_id,dataset_id,updated_through,run_id) VALUES (%s,'erm2-nwe9',%s,%s)
                ON CONFLICT(cohort_id) DO UPDATE SET updated_through=EXCLUDED.updated_through,
                    run_id=EXCLUDED.run_id,published_at=clock_timestamp()
                WHERE EXCLUDED.updated_through>ops.publication_watermarks.updated_through""",
                (settings["cohort_id"], upper, run_id),
            )
        conn.execute(
            """UPDATE ops.pipeline_runs SET status='succeeded',phase='finished',
            published_at=clock_timestamp(),finished_at=clock_timestamp(),
            heartbeat_at=clock_timestamp(),error_category=NULL,retryable=false,
            successful_update_upper_utc=%s WHERE run_id=%s""",
            (upper, run_id),
        )
