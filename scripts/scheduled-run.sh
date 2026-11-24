#!/bin/sh
# Host cron invokes one bounded incremental run; PostgreSQL rejects overlaps.
set -eu
cd "$(dirname "$0")/.."
: "${COHORT_START:?Set COHORT_START to the UTC creation-cohort start}"
: "${COHORT_END:?Set COHORT_END to the UTC creation-cohort end}"
set -- run --mode incremental --start "$COHORT_START" --end "$COHORT_END"
# Explicit opt-in only for an isolated, synthetic scheduler demonstration.
if [ -n "${SCHEDULE_FIXTURE:-}" ]; then
  set -- "$@" --fixture "$SCHEDULE_FIXTURE"
fi
exec docker compose --profile pipeline run --rm pipeline "$@"
