DROP TABLE ops.quarantine;
DROP TABLE ops.validation_stage;
DROP TABLE ops.run_settings;
DROP FUNCTION ops.immutable_run_settings();
ALTER TABLE ops.pipeline_runs DROP COLUMN outside_scope_count,
    DROP COLUMN invalid_count CASCADE, DROP COLUMN valid_count CASCADE, DROP COLUMN evaluated_count CASCADE;
