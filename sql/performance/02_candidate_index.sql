-- Apply only after capturing baseline. No existing index is dropped.
CREATE INDEX IF NOT EXISTS fact_eligible_date_agency_cover
ON gold.fact_service_requests (created_date_key, agency_id)
INCLUDE (resolution_seconds) WHERE metric_eligible;
