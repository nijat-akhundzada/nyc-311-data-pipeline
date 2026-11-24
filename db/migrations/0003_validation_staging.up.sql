-- Forward-only validation infrastructure. Raw rows/receipts remain untouched.
ALTER TABLE ops.pipeline_runs
    ADD COLUMN evaluated_count bigint NOT NULL DEFAULT 0 CHECK (evaluated_count >= 0),
    ADD COLUMN valid_count bigint NOT NULL DEFAULT 0 CHECK (valid_count >= 0),
    ADD COLUMN invalid_count bigint NOT NULL DEFAULT 0 CHECK (invalid_count >= 0),
    ADD COLUMN outside_scope_count bigint NOT NULL DEFAULT 0 CHECK (outside_scope_count >= 0),
    ADD CHECK (evaluated_count = valid_count + invalid_count);
CREATE TABLE ops.run_settings (
    run_id uuid PRIMARY KEY REFERENCES ops.pipeline_runs(run_id),
    config jsonb NOT NULL,
    config_hash text NOT NULL CHECK (config_hash ~ '^[0-9a-f]{64}$')
);
CREATE FUNCTION ops.immutable_run_settings() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW IS DISTINCT FROM OLD THEN RAISE EXCEPTION 'immutable run settings'; END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER immutable_settings BEFORE UPDATE ON ops.run_settings
FOR EACH ROW EXECUTE FUNCTION ops.immutable_run_settings();
CREATE TABLE ops.validation_stage (
    run_id uuid NOT NULL REFERENCES ops.pipeline_runs(run_id),
    unique_key text COLLATE "C" NOT NULL,
    raw_id bigint NOT NULL REFERENCES bronze.raw_service_requests(raw_id),
    source_updated_at timestamptz,
    observed_at timestamptz NOT NULL,
    outcome text NOT NULL CHECK (outcome IN ('valid','invalid','outside_scope')),
    reasons text[] NOT NULL,
    normalized jsonb,
    business_hash text,
    state_hash text,
    stage_hash text NOT NULL,
    PRIMARY KEY (run_id, unique_key),
    CHECK ((outcome = 'invalid') = (cardinality(reasons) > 0)),
    CHECK (outcome <> 'valid' OR normalized IS NOT NULL)
);
CREATE TABLE ops.quarantine (
    quarantine_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES ops.pipeline_runs(run_id),
    unique_key text COLLATE "C",
    raw_id bigint REFERENCES bronze.raw_service_requests(raw_id),
    raw_hash text NOT NULL,
    payload jsonb NOT NULL,
    reasons text[] NOT NULL CHECK (cardinality(reasons) > 0),
    observed_at timestamptz NOT NULL,
    UNIQUE (run_id, raw_hash)
);
