#!/bin/sh
# Host cron invokes one bounded incremental run; PostgreSQL rejects overlaps.
set -eu
cd "$(dirname "$0")/.."
: "${COHORT_START:?Set COHORT_START to the UTC creation-cohort start}"
: "${COHORT_END:?Set COHORT_END to the UTC creation-cohort end}"
exec docker compose --profile pipeline run --rm pipeline run --mode incremental \
  --start "$COHORT_START" --end "$COHORT_END"
