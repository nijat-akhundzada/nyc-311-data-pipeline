-- Lead-authorized bounded Spec 05 domain slice. No downstream publication.
CREATE TABLE ops.pipeline_runs (
    run_id uuid PRIMARY KEY,
    dataset_id text COLLATE "C" NOT NULL,
    contract_version text NOT NULL,
    mode text NOT NULL CHECK (mode IN ('backfill', 'incremental')),
    scope_id text NOT NULL CHECK (scope_id ~ '^[0-9a-f]{64}$'),
    config jsonb NOT NULL CHECK (jsonb_typeof(config) = 'object'),
    status text NOT NULL CHECK (status IN ('pending', 'running', 'paused', 'failed', 'succeeded')),
    phase text NOT NULL DEFAULT 'ingest' CHECK (phase IN ('ingest', 'validate', 'publish', 'finished')),
    generation timestamptz,
    ingest_complete boolean NOT NULL DEFAULT false,
    received_count bigint NOT NULL DEFAULT 0 CHECK (received_count >= 0),
    raw_inserted_count bigint NOT NULL DEFAULT 0 CHECK (raw_inserted_count >= 0 AND raw_inserted_count <= received_count),
    retryable boolean NOT NULL DEFAULT false,
    error_category text,
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    heartbeat_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    finished_at timestamptz,
    published_at timestamptz,
    successful_update_upper_utc timestamptz,
    CHECK (status <> 'succeeded' OR (ingest_complete AND published_at IS NOT NULL)),
    CHECK (published_at IS NOT NULL OR successful_update_upper_utc IS NULL)
);
CREATE UNIQUE INDEX pipeline_runs_one_unfinished_ingest ON ops.pipeline_runs (dataset_id)
WHERE NOT ingest_complete AND (status IN ('pending', 'running', 'paused') OR retryable);
CREATE INDEX pipeline_runs_scope ON ops.pipeline_runs (dataset_id, scope_id, started_at);

CREATE FUNCTION ops.protect_ingest_run_identity() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF ROW(NEW.dataset_id, NEW.contract_version, NEW.mode, NEW.scope_id, NEW.config)
       IS DISTINCT FROM ROW(OLD.dataset_id, OLD.contract_version, OLD.mode, OLD.scope_id, OLD.config)
       OR (OLD.generation IS NOT NULL AND NEW.generation IS DISTINCT FROM OLD.generation) THEN
        RAISE EXCEPTION 'immutable ingestion identity';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER pipeline_runs_immutable BEFORE UPDATE ON ops.pipeline_runs
FOR EACH ROW EXECUTE FUNCTION ops.protect_ingest_run_identity();

CREATE TABLE bronze.raw_service_requests (
    raw_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_id text COLLATE "C" NOT NULL,
    unique_key text COLLATE "C" NOT NULL CHECK (length(btrim(unique_key)) > 0),
    raw_hash text NOT NULL CHECK (raw_hash ~ '^[0-9a-f]{64}$'),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object' AND payload->>'unique_key' = unique_key),
    first_observed_at timestamptz NOT NULL,
    UNIQUE (dataset_id, unique_key, raw_hash)
);
CREATE TABLE ops.ingest_checkpoints (
    run_id uuid NOT NULL REFERENCES ops.pipeline_runs(run_id),
    segment_id text COLLATE "C" NOT NULL,
    page_no bigint NOT NULL DEFAULT 0 CHECK (page_no >= 0),
    cursor jsonb CHECK (cursor IS NULL OR (jsonb_typeof(cursor) = 'object' AND cursor->>'kind' IN ('creation', 'update'))),
    generation timestamptz,
    exhausted boolean NOT NULL DEFAULT false,
    PRIMARY KEY (run_id, segment_id),
    CHECK (page_no > 0 OR (cursor IS NULL AND generation IS NULL AND NOT exhausted)),
    CHECK (page_no = 0 OR generation IS NOT NULL)
);
CREATE TABLE ops.ingest_page_receipts (
    run_id uuid NOT NULL,
    segment_id text COLLATE "C" NOT NULL,
    page_no bigint NOT NULL CHECK (page_no > 0),
    page_hash text NOT NULL CHECK (page_hash ~ '^[0-9a-f]{64}$'),
    checkpoint_before jsonb NOT NULL,
    checkpoint_after jsonb NOT NULL,
    received_count integer NOT NULL CHECK (received_count BETWEEN 0 AND 5000),
    inserted_raw_versions integer NOT NULL CHECK (inserted_raw_versions BETWEEN 0 AND received_count),
    received_at timestamptz NOT NULL,
    request_id text,
    http_metadata jsonb NOT NULL,
    PRIMARY KEY (run_id, segment_id, page_no),
    FOREIGN KEY (run_id, segment_id) REFERENCES ops.ingest_checkpoints(run_id, segment_id)
);
CREATE TABLE ops.run_records (
    run_id uuid NOT NULL,
    segment_id text COLLATE "C" NOT NULL,
    page_no bigint NOT NULL,
    row_ordinal integer NOT NULL CHECK (row_ordinal > 0),
    raw_id bigint NOT NULL REFERENCES bronze.raw_service_requests(raw_id),
    source_updated_at timestamptz,
    observed_at timestamptz NOT NULL,
    PRIMARY KEY (run_id, segment_id, page_no, row_ordinal),
    FOREIGN KEY (run_id, segment_id, page_no) REFERENCES ops.ingest_page_receipts(run_id, segment_id, page_no)
);
CREATE INDEX run_records_raw ON ops.run_records (raw_id);
CREATE TABLE ops.run_events (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES ops.pipeline_runs(run_id),
    event text NOT NULL CHECK (event IN ('started', 'resumed', 'paused', 'failed', 'ingest_complete')),
    category text,
    retryable boolean NOT NULL DEFAULT false,
    observed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX run_events_run ON ops.run_events (run_id, event_id);
