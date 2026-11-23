# Assignment → evidence traceability

| Teacher requirement | Planned spec | Proof to retain |
|---|---|---|
| Pagination, rate limits, retries, resumable ingestion | 03 | replay and crash-resume test + cursor logs |
| Quarantine, no silent drops, quality threshold and atomic hold | 04 | malformed input and no-gold-change asserts |
| Bronze/silver/gold and star + SCD2 | 05, 06 | migration SQL, ER diagram, history overlap test |
| Incremental, backfill, idempotent | 03, 04, 06, 10 | before/after row counts/checksums |
| >=1M real rows | 08, 10 | source count and SQL `COUNT(*)`, provenance |
| Measured optimization | 08 | EXPLAIN ANALYZE plan/timing before and after |
| Kill container, DB startup, malformed data | 09 | deterministic failure drills and outcomes |
| Run history + schedule | 07 | run rows and scheduler logs |
| Gold CTE + windows analytics | 08 | `.sql` files and reproducible query output |
| Multi-stage/non-root/health/volumes | 02 | docker inspection + compose status |
| CI, hooks, pytest | 02, 10 | CI runs and local commands |
| Feature branches/reviews/protected main | All | PR links, review comments, GitHub ruleset screenshot |
| README, member names, report | 11 | final README, benchmark report |
