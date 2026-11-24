WITH distribution AS (
    SELECT b.borough_id, b.borough, count(*) AS requests,
           count(*) FILTER (WHERE f.metric_eligible) AS eligible_closed_requests
    FROM gold.fact_service_requests f
    JOIN gold.dim_borough b USING (borough_id)
    GROUP BY b.borough_id, b.borough
)
SELECT borough, requests, eligible_closed_requests,
       dense_rank() OVER (ORDER BY requests DESC) AS borough_volume_rank,
       round(100.0 * requests / sum(requests) OVER (), 2) AS percent_of_loaded_requests
FROM distribution
ORDER BY requests DESC, borough NULLS LAST;
