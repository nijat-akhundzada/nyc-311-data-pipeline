-- Fixed workload: eligible closures in one UTC day; same SQL/results before and after.
WITH selected AS (
    SELECT agency_id, resolution_seconds
    FROM gold.fact_service_requests
    WHERE metric_eligible AND created_date_key >= DATE '2025-01-02'
                          AND created_date_key < DATE '2025-01-03'
), summary AS (
    SELECT agency_id, count(*) AS requests, avg(resolution_seconds) AS mean_seconds
    FROM selected GROUP BY agency_id
)
SELECT agency_id, requests, mean_seconds,
       dense_rank() OVER (ORDER BY requests DESC) AS volume_rank
FROM summary ORDER BY requests DESC, agency_id;
