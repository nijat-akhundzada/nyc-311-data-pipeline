# Failure and recovery report — NOT YET EXECUTED

For each scenario retain actual date, command, run_id, log excerpt (redacted), bronze/silver/gold counts before and after, expected vs observed behavior, and verdict.

1. Kill ingestion container mid-run; restart and inspect durable checkpoint. Confirm no lost/duplicated logical records.
2. Start pipeline while DB not ready; confirm health/readiness or bounded retry and successful subsequent run.
3. Inject malformed fixture with > configured bad-rate; verify quarantine reasons, failed run and **identical** published silver/gold snapshot.
