"""Set-based star loading. The caller owns the transaction and dataset lock."""

AFFECTED = """SELECT s.* FROM silver.service_requests s
 JOIN ops.validation_stage v USING(unique_key) WHERE v.run_id=%s AND v.outcome='valid'"""


def publish_gold(conn, run_id):
    conn.execute(
        """WITH affected AS ("""
        + AFFECTED
        + """)
        INSERT INTO gold.dim_date
        SELECT d,extract(year FROM d),extract(month FROM d),extract(day FROM d),
                extract(isodow FROM d)
        FROM (SELECT (created_at AT TIME ZONE 'UTC')::date d FROM affected UNION
              SELECT (closed_at AT TIME ZONE 'UTC')::date FROM affected
              WHERE closed_at IS NOT NULL) x
        ON CONFLICT DO NOTHING""",
        (run_id,),
    )
    conn.execute(
        """WITH affected AS ("""
        + AFFECTED
        + """)
        INSERT INTO gold.dim_agency (agency_code,agency_name)
        SELECT DISTINCT ON (agency) agency,CASE WHEN agency IS NOT NULL THEN agency_name END
        FROM affected ORDER BY agency,source_updated_at DESC,agency_name NULLS LAST
        ON CONFLICT (agency_code) DO UPDATE SET agency_name=COALESCE(EXCLUDED.agency_name,
            gold.dim_agency.agency_name)""",
        (run_id,),
    )
    conn.execute(
        """WITH affected AS ("""
        + AFFECTED
        + """)
        INSERT INTO gold.dim_complaint_type (complaint_type)
        SELECT DISTINCT complaint_type FROM affected ON CONFLICT DO NOTHING""",
        (run_id,),
    )
    conn.execute(
        """WITH affected AS ("""
        + AFFECTED
        + """)
        INSERT INTO gold.dim_borough (borough)
        SELECT DISTINCT borough FROM affected ON CONFLICT DO NOTHING""",
        (run_id,),
    )
    conn.execute(
        """WITH affected AS ("""
        + AFFECTED
        + """)
        UPDATE gold.dim_service_request_state d SET valid_to=s.observed_at,is_current=false
        FROM affected s WHERE d.unique_key=s.unique_key AND d.is_current
        AND d.state_hash<>s.state_hash""",
        (run_id,),
    )
    conn.execute(
        """WITH affected AS ("""
        + AFFECTED
        + """)
        INSERT INTO gold.dim_service_request_state
          (unique_key,status_key,agency,complaint_type,state_hash,valid_from,is_current,
                observed_run_id)
        SELECT s.unique_key,s.status_key,s.agency,s.complaint_type,s.state_hash,
                s.observed_at,true,%s
        FROM affected s WHERE NOT EXISTS (SELECT 1 FROM gold.dim_service_request_state d
                                         WHERE d.unique_key=s.unique_key AND d.is_current)""",
        (run_id, run_id),
    )
    conn.execute(
        """WITH affected AS ("""
        + AFFECTED
        + """)
        INSERT INTO gold.fact_service_requests
          (unique_key,created_date_key,closed_date_key,agency_id,complaint_type_id,borough_id,
           state_id,resolution_seconds,metric_eligible,metric_reason,published_run_id)
        SELECT s.unique_key,(s.created_at AT TIME ZONE 'UTC')::date,
               (s.closed_at AT TIME ZONE 'UTC')::date,a.agency_id,c.complaint_type_id,b.borough_id,
               d.state_id,s.resolution_seconds,s.metric_eligible,s.metric_reason,%s
        FROM affected s
        JOIN gold.dim_agency a ON a.agency_code IS NOT DISTINCT FROM s.agency
        JOIN gold.dim_complaint_type c ON c.complaint_type IS NOT DISTINCT FROM s.complaint_type
        JOIN gold.dim_borough b ON b.borough IS NOT DISTINCT FROM s.borough
        JOIN gold.dim_service_request_state d ON d.unique_key=s.unique_key AND d.is_current
        ON CONFLICT (unique_key) DO UPDATE SET
          created_date_key=EXCLUDED.created_date_key,closed_date_key=EXCLUDED.closed_date_key,
          agency_id=EXCLUDED.agency_id,complaint_type_id=EXCLUDED.complaint_type_id,
          borough_id=EXCLUDED.borough_id,state_id=EXCLUDED.state_id,
          resolution_seconds=EXCLUDED.resolution_seconds,metric_eligible=EXCLUDED.metric_eligible,
          metric_reason=EXCLUDED.metric_reason,published_run_id=EXCLUDED.published_run_id
        WHERE ROW(gold.fact_service_requests.created_date_key,
                gold.fact_service_requests.closed_date_key,
                  gold.fact_service_requests.agency_id,gold.fact_service_requests.complaint_type_id,
                  gold.fact_service_requests.borough_id,gold.fact_service_requests.state_id,
                  gold.fact_service_requests.resolution_seconds,gold.fact_service_requests.metric_eligible,
                  gold.fact_service_requests.metric_reason)
          IS DISTINCT FROM ROW(EXCLUDED.created_date_key,EXCLUDED.closed_date_key,
                EXCLUDED.agency_id,
                  EXCLUDED.complaint_type_id,EXCLUDED.borough_id,EXCLUDED.state_id,
                  EXCLUDED.resolution_seconds,EXCLUDED.metric_eligible,EXCLUDED.metric_reason)""",
        (run_id, run_id),
    )
