# Submission gate checklist (26 Nov 2026)

- [ ] Repository contains Python code, tests, versioned migrations, query SQL, Docker and CI
- [ ] All three named in final README: Nijat Akhundzadeh, Nizami, Firuz
- [ ] One source API used; documented pagination, bounded retries, 429 handling, resumability
- [ ] Bronze/silver/gold, rejection quarantine, bad-rate threshold, no failed-run downstream publish
- [ ] Incremental and date-bounded historical backfill; logical replay produces identical results
- [ ] Real SCD Type 2 with a changed natural key and unchanged replay test
- [ ] >=1M **real** rows measured and documented
- [ ] Gold star schema; analytics queries using both CTE and window functions
- [ ] Performance BEFORE and AFTER execution plans and raw measured timings
- [ ] Kill-container, DB-not-ready and bad-input drills actually demonstrated
- [ ] Run-history records and scheduled execution demonstrated
- [ ] Multi-stage Docker, non-root, healthchecks, named volume, no secrets in Git
- [ ] Hooks, pytest unit/integration and GitHub CI passed
- [ ] Protected main, feature branches, substantive peer reviews and conventional commits evidenced
- [ ] README explains actual commands, model, rules, idempotency and git exercises
- [ ] Each author can explain their contribution; final tests from clean clone pass

**Gate:** NOT READY until evidence replaces each box. Record PR links, CI links and benchmark outputs in final README.
