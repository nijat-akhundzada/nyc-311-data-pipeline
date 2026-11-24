-- Current request volume, not reconstructed historical backlog or an SLA ranking.
WITH agency_volume AS (
    SELECT a.agency_id, a.agency_code, a.agency_name, count(*) AS requests,
           count(*) FILTER (WHERE f.metric_eligible) AS eligible_closed_requests
    FROM gold.fact_service_requests f
    JOIN gold.dim_agency a USING (agency_id)
    GROUP BY a.agency_id, a.agency_code, a.agency_name
)
SELECT agency_code, agency_name, requests, eligible_closed_requests,
       dense_rank() OVER (ORDER BY requests DESC) AS volume_rank,
       round(100.0 * requests / sum(requests) OVER (), 2) AS percent_of_requests
FROM agency_volume
ORDER BY requests DESC, agency_code NULLS LAST;
