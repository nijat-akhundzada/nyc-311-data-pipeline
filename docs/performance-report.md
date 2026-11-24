# Measured analytics performance — 24 November 2026

Later real-source work increased published counts to 42,738; the measurements below
remain the original fixed 13,126-fact experiment. They were not rerun or relabeled
as a larger-scale benchmark.

**PARTIAL assignment evidence: real data, but only 13,126 facts, not one million.**
All four [analytics queries](../sql/analytics/README.md) executed on that database:
agency volume/ranking (13 result rows), complaint monthly trends (126), borough
shares (6), and recorded resolution performance (13). Each uses a CTE and window
function. The integration test checks unequal rankings/shares, zero-volume months,
undefined percentage change after zero, and eligible closure durations.

## Comparable full-day workload

[SQL](../sql/performance/01_selective_resolution.sql) selects eligible requests
created on 2 January 2025 UTC, aggregates counts/mean duration by agency and ranks
volume. Before/after SQL and data were identical. PostgreSQL 16.14, aarch64 Alpine,
Docker Desktop overlayfs, 8 allocated CPUs, 5,158,379,520 bytes allocated memory.
`shared_buffers=128MB`, `work_mem=4MB`, `effective_cache_size=4GB`,
`random_page_cost=4`, parallel workers per gather 2. Concurrent source loading had
stopped; no synthetic records were in this database. Host scheduling/cache noise remains.

The [optional partial covering index](../sql/performance/02_candidate_index.sql)
orders eligible facts by creation date and agency and includes duration. It enables
index-only retrieval for repeated date-filtered agency summaries. It is a standalone
experiment, not an applied migration change. Storage cost: 548,864 bytes; inserts
and updates also incur index maintenance. Do not add redundant indexes indiscriminately.

| Warm execution, milliseconds | Before | After |
|---|---:|---:|
| Run 1 | 2.816 | 2.368 |
| Run 2 | 2.747 | 2.276 |
| Run 3 | 2.535 | 2.539 |
| Median | 2.747 | 2.368 |

Median ratio: **1.160×**, about **13.8%** less execution time. This is a modest,
small-data observation, not a significant or scale-independent performance claim.
One untimed warm-up per phase, then three `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`
executions. `VACUUM (ANALYZE)` preceded baseline; no cold-cache claims. Before/after
result SHA-256 matches. Full plans, actual rows, buffers, settings and hashes:
[performance.json](evidence/final/performance.json). Reproduce on a development
DB without that optional index:

```sh
DATABASE_URL="$DATABASE_URL" python scripts/benchmark-analytics.py --apply-index
```

The script refuses an already-indexed baseline and never drops an existing index.
The candidate index must be absent to repeat the comparison. Do not drop applied
migration indexes. On a fresh DB use `psql "$DATABASE_URL" -f sql/analytics/01_agency_volume.sql`.

## Retained negative experiment

An initial sparse 15 January query scanned only 43 eligible facts. Medians were
0.155ms before and 0.569ms after (ratio 0.272×); therefore the index did **not** improve
that measured workload. The experiment's optional index was removed before the
full-day baseline; no migration or data was changed. Complete original plans:
[performance-sparse-rejected.json](evidence/final/performance-sparse-rejected.json).
The full-day workload is explicitly different and is compared only to its own baseline.

Rebenchmark on at least one million actual facts before claiming the assignment's
scale/performance requirement. Current figures are too small for broad conclusions.
