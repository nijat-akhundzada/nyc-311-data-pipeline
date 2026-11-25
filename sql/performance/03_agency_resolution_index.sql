-- Optional experiment for the full-table resolution-by-agency query.
CREATE INDEX fact_agency_resolution_cover
ON gold.fact_service_requests (agency_id)
INCLUDE (metric_eligible, metric_reason, resolution_seconds);
