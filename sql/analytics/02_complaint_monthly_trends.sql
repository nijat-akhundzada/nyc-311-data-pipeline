-- UTC creation months, including zero-volume months within the loaded date extent.
WITH extent AS (
    SELECT date_trunc('month', min(created_date_key)) AS first_month,
           date_trunc('month', max(created_date_key)) AS last_month
    FROM gold.fact_service_requests
), months AS (
    SELECT generate_series(first_month, last_month, interval '1 month')::date AS month
    FROM extent
), observed AS (
    SELECT complaint_type_id, date_trunc('month', created_date_key)::date AS month,
           count(*) AS requests
    FROM gold.fact_service_requests
    GROUP BY complaint_type_id, date_trunc('month', created_date_key)::date
), grid AS (
    SELECT c.complaint_type_id, c.complaint_type, m.month, coalesce(o.requests, 0) AS requests
    FROM gold.dim_complaint_type c CROSS JOIN months m
    LEFT JOIN observed o USING (complaint_type_id, month)
    WHERE EXISTS (SELECT 1 FROM observed x WHERE x.complaint_type_id=c.complaint_type_id)
), changes AS (
    SELECT *, lag(requests) OVER (PARTITION BY complaint_type_id ORDER BY month) AS previous_month
    FROM grid
)
SELECT complaint_type, month, requests, previous_month,
       requests - previous_month AS change_in_requests,
       round(100.0 * (requests - previous_month) / nullif(previous_month, 0), 2) AS percent_change
FROM changes
ORDER BY complaint_type NULLS LAST, month;
