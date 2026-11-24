-- The exclusion constraint enforces SCD2 nonoverlap even for direct concurrent SQL.
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE TABLE silver.service_requests (
    unique_key text COLLATE "C" PRIMARY KEY,
    created_at timestamptz NOT NULL,
    closed_at timestamptz,
    created_source text NOT NULL,
    closed_source text,
    agency text, agency_name text, complaint_type text, status text, status_key text,
    borough text, incident_zip text,
    resolution_action_updated_at timestamptz,
    source_updated_at timestamptz NOT NULL,
    observed_at timestamptz NOT NULL,
    raw_id bigint NOT NULL REFERENCES bronze.raw_service_requests(raw_id),
    business_hash text NOT NULL,
    state_hash text NOT NULL,
    metric_eligible boolean NOT NULL,
    metric_reason text,
    resolution_seconds double precision CHECK (resolution_seconds >= 0),
    published_run_id uuid NOT NULL REFERENCES ops.pipeline_runs(run_id),
    CHECK (closed_at IS NULL OR closed_at >= created_at),
    CHECK (NOT metric_eligible OR (closed_at IS NOT NULL AND resolution_seconds IS NOT NULL))
);
CREATE TABLE gold.dim_date (
    date_key date PRIMARY KEY, year integer NOT NULL, month integer NOT NULL,
    day integer NOT NULL, iso_weekday integer NOT NULL
);
CREATE TABLE gold.dim_agency (
    agency_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agency_code text UNIQUE NULLS NOT DISTINCT,
    agency_name text
);
CREATE TABLE gold.dim_complaint_type (
    complaint_type_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    complaint_type text UNIQUE NULLS NOT DISTINCT
);
CREATE TABLE gold.dim_borough (
    borough_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    borough text UNIQUE NULLS NOT DISTINCT
);
INSERT INTO gold.dim_agency (agency_code) VALUES (NULL);
INSERT INTO gold.dim_complaint_type (complaint_type) VALUES (NULL);
INSERT INTO gold.dim_borough (borough) VALUES (NULL);
CREATE TABLE gold.dim_service_request_state (
    state_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unique_key text COLLATE "C" NOT NULL,
    status_key text, agency text, complaint_type text,
    state_hash text NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    is_current boolean NOT NULL,
    observed_run_id uuid NOT NULL REFERENCES ops.pipeline_runs(run_id),
    UNIQUE (state_id,unique_key),
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (is_current = (valid_to IS NULL)),
    EXCLUDE USING gist (unique_key WITH =, tstzrange(valid_from,valid_to,'[)') WITH &&)
);
CREATE UNIQUE INDEX one_current_request_state ON gold.dim_service_request_state (unique_key)
WHERE is_current;
CREATE TABLE gold.fact_service_requests (
    unique_key text COLLATE "C" PRIMARY KEY REFERENCES silver.service_requests(unique_key),
    created_date_key date NOT NULL REFERENCES gold.dim_date(date_key),
    closed_date_key date REFERENCES gold.dim_date(date_key),
    agency_id bigint NOT NULL REFERENCES gold.dim_agency(agency_id),
    complaint_type_id bigint NOT NULL REFERENCES gold.dim_complaint_type(complaint_type_id),
    borough_id bigint NOT NULL REFERENCES gold.dim_borough(borough_id),
    state_id bigint NOT NULL,
    resolution_seconds double precision CHECK (resolution_seconds >= 0),
    metric_eligible boolean NOT NULL,
    metric_reason text,
    published_run_id uuid NOT NULL REFERENCES ops.pipeline_runs(run_id),
    FOREIGN KEY (state_id,unique_key) REFERENCES gold.dim_service_request_state(state_id,unique_key)
);
CREATE INDEX fact_created_date ON gold.fact_service_requests(created_date_key);
CREATE INDEX fact_agency ON gold.fact_service_requests(agency_id);
CREATE INDEX fact_complaint_type ON gold.fact_service_requests(complaint_type_id);
CREATE INDEX fact_borough ON gold.fact_service_requests(borough_id);
CREATE TABLE ops.publication_watermarks (
    cohort_id text PRIMARY KEY,
    dataset_id text NOT NULL,
    updated_through timestamptz NOT NULL,
    run_id uuid NOT NULL REFERENCES ops.pipeline_runs(run_id),
    published_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
