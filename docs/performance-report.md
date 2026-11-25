# Measured analytics performance — 24 November 2026

## Final scale benchmark (1,002,639 genuine Gold facts)

The final dataset reached **1,002,639 genuine Gold facts** and 1,033,290 distinct
Bronze IDs. Dimension counts were 603 dates, 15 agencies, 183 complaint types,
7 boroughs and 1,002,639 request states. The 1M scale target is **achieved**.

The resolution query reads metric eligibility, reason and duration for all facts
grouped by agency. The [agency covering index](../sql/performance/03_agency_resolution_index.sql)
tests whether PostgreSQL can read those values directly from the index. The experiment
removed the prior optional date index, kept the underlying data, SQL and settings fixed.
`VACUUM (ANALYZE)` refreshed facts and `ANALYZE` collected dimension statistics.
Each phase ran one untimed result fetch and three warm
`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` executions per query. Result row counts
and SHA-256 matched across phases for all five statements.

| Workload | Result rows | Before runs, ms | After runs, ms | Median before → after, ms | Speedup |
|---|---:|---|---|---:|---:|
| Agency volume | 14 | 121.010 / 195.960 / 178.632 | 126.371 / 114.309 / 130.131 | 178.632 → 126.371 | 1.414× (29.3% faster) |
| Monthly complaint trends | 728 | 181.425 / 176.523 / 131.121 | 125.261 / 120.856 / 114.517 | 176.523 → 120.856 | 1.461× (31.5% faster) |
| Borough shares | 6 | 119.259 / 111.468 / 111.732 | 128.741 / 154.961 / 123.601 | 111.732 → 128.741 | 0.868× (15.2% slower) |
| Agency resolution | 14 | 801.278 / 776.006 / 642.469 | 482.081 / 405.635 / 410.614 | 776.006 → 410.614 | 1.890× (47.1% faster) |
| Selective daily resolution | 13 | 2.963 / 3.252 / 2.762 | 2.640 / 2.685 / 2.863 | 2.963 → 2.685 | 1.104× (9.4% faster) |

The candidate occupies **49,758,208 bytes** (~49.8 MB). The agency-resolution
median ratio was **1.890×**, a **47.1%** decrease in median execution time (from 776.006 ms
down to 410.614 ms).
PostgreSQL used an index-only scan with zero heap fetches in all three after
plans. The other queries showed mixed timing changes: borough shares had a slight regression
due to plan variation, while monthly complaint trends and agency volume experienced concurrent benefits.
See plan nodes and buffer counts in the
[benchmark JSON](evidence/final/performance.json) under `final_submission`.
PostgreSQL 16.14 ran in Docker on Apple M1, with 8 virtual CPUs and
5,158,379,520 bytes of memory available to the VM. Settings were
128 MB shared buffers, 4 MB work memory, 4 GB effective cache, random page cost
4 and two parallel workers per gather. The optional index remains an experiment.

Reproduce with the benchmark candidate absent:

```sh
DATABASE_URL="$DATABASE_URL" python scripts/benchmark-analytics.py --apply-index --candidate agency
```

## Original 13,126-fact benchmark

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

The scale and performance benchmark has been successfully verified on **1,002,639 genuine Gold facts**, demonstrating a 1.890× speedup (47.1% runtime reduction) on the agency resolution analytical workload via an index-only scan, with identical query result SHA-256 digests across all measured queries.
