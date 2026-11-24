# Measured analytics performance — 24 November 2026

## Final readiness benchmark

The final snapshot contained **277,791 genuine Gold facts** and 299,204 distinct
Bronze IDs. Dimension counts were 485 dates, 15 agencies, 169 complaint types,
7 boroughs and 277,791 request states. The scale target remains open.

The resolution query reads metric eligibility, reason and duration for all facts
grouped by agency. The [agency covering index](../sql/performance/03_agency_resolution_index.sql)
tests whether PostgreSQL can read those values from the index. The experiment
restored a snapshot in a disposable database, removed the prior optional date
index from that copy, and kept the underlying data, SQL and settings fixed.
`VACUUM (ANALYZE)` refreshed facts and `ANALYZE` collected dimension statistics.
Each phase ran one untimed result fetch and three warm
`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` executions per query. Result row counts
and SHA-256 matched across phases for all five statements.

| Workload | Result rows | Before runs, ms | After runs, ms | Median before → after, ms |
|---|---:|---|---|---:|
| Agency volume | 14 | 38.088 / 32.752 / 32.830 | 33.513 / 34.672 / 31.849 | 32.830 → 33.513 |
| Monthly complaint trends | 168 | 32.821 / 35.711 / 38.581 | 33.667 / 41.749 / 34.629 | 35.711 → 34.629 |
| Borough shares | 6 | 32.337 / 32.308 / 31.685 | 31.288 / 31.693 / 31.727 | 32.308 → 31.693 |
| Agency resolution | 14 | 138.489 / 119.810 / 155.034 | 92.999 / 94.929 / 103.982 | 138.489 → 94.929 |
| Selective daily resolution | 13 | 2.474 / 2.404 / 2.401 | 2.510 / 2.458 / 2.418 | 2.404 → 2.458 |

The candidate occupies **13,803,520 bytes**. The agency-resolution
median ratio was **1.459×**, a **31.5%** decrease in median execution time.
PostgreSQL used an index-only scan with zero heap fetches in all three after
plans. The other queries showed mixed timing changes. See plan nodes and buffer counts in the
[benchmark JSON](evidence/final/performance.json) under `final_submission`.
PostgreSQL 16.14 ran in Docker Desktop on Apple M1, with 8 virtual CPUs and
5,158,379,520 bytes of memory available to the VM. Settings were
128 MB shared buffers, 4 MB work memory, 4 GB effective cache, random page cost
4 and two parallel workers per gather. The optional index remains an experiment.

Reproduce with a disposable snapshot and the benchmark candidate absent:

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

Rebenchmark on at least one million actual facts before claiming the assignment's
scale/performance requirement. Current figures are too small for broad conclusions.
