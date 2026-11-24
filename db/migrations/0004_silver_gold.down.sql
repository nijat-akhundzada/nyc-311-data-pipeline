DROP TABLE ops.publication_watermarks;
DROP TABLE gold.fact_service_requests;
DROP TABLE gold.dim_service_request_state;
DROP TABLE gold.dim_borough;
DROP TABLE gold.dim_complaint_type;
DROP TABLE gold.dim_agency;
DROP TABLE gold.dim_date;
DROP TABLE silver.service_requests;
-- Do not drop a possibly pre-existing shared btree_gist extension.
