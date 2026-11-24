-- Recorded agency closure duration, not verified fulfillment or causal agency quality.
WITH durations AS (
    SELECT a.agency_id, a.agency_code, count(*) AS all_requests,
           count(*) FILTER (WHERE f.metric_eligible) AS eligible_requests,
           count(*) FILTER (WHERE f.metric_reason='closed_without_closed_date') AS missing_closure,
           avg(f.resolution_seconds) FILTER (WHERE f.metric_eligible) / 3600.0 AS mean_hours,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_seconds)
               FILTER (WHERE f.metric_eligible) / 3600.0 AS median_hours,
           percentile_cont(0.9) WITHIN GROUP (ORDER BY f.resolution_seconds)
               FILTER (WHERE f.metric_eligible) / 3600.0 AS p90_hours
    FROM gold.fact_service_requests f JOIN gold.dim_agency a USING (agency_id)
    GROUP BY a.agency_id, a.agency_code
)
SELECT agency_code, all_requests, eligible_requests, missing_closure,
       mean_hours, median_hours, p90_hours,
       dense_rank() OVER (ORDER BY p90_hours NULLS LAST) AS p90_duration_rank
FROM durations
ORDER BY p90_hours NULLS LAST, agency_code NULLS LAST;
