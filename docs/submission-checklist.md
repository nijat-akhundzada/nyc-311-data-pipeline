# Submission requirement matrix — deadline 26 November 2026

**Recommendation: TECHNICAL REQUIREMENTS PASS; PENDING HUMAN/GITHUB ACTIONS.** Reviewed against
the [assignment PDF](source-assignment.pdf). See the [final verification](final-verification.md)
for commands, measured results and canonical run IDs.

| Requirement | Status | Evidence or remaining gap |
|---|---|---|
| One public API, pagination, retries and rate limits | PARTIAL | One NYC Open Data dataset, fixture-tested retry policy and measured backfills. Source staleness, HTTP 503 and connection timeouts handled via bounded retries and resumes. Actual quota and full source change semantics remain unverified. [Source audit](evidence/final/scale-source-audit.json) |
| Durable crash resume and checkpoints | PASS | Real frozen-generation resume completed at page 5. Isolated SIGKILL drill resumed from its committed page. [Final verification](final-verification.md), [recovery](failure-recovery-report.md) |
| Validation, quarantine with reasons and quality gate | PASS | 410 real quarantines (409 closed_before_created, 1 nonexistent local time during DST spring forward). Clean Compose run exited 4 for 2/20 invalid and preserved published fingerprints. [Counts](evidence/final/real-load-counts.json), [recovery](failure-recovery-report.md) |
| Bronze, Silver, Gold star schema and atomic publication | PASS | 1,033,290 distinct Bronze IDs, 1,002,639 Silver requests and 1,002,639 Gold facts. DB constraints and rollback tests cover the loaded star schema. [Model](data-model.md), [verification](final-verification.md) |
| Genuine SCD Type 2 changes | PARTIAL | Observed-time SCD2, exclusion constraint and synthetic transition tests. Probed 50 non-closed requests against live API on matching generation `2026-11-24T02:42:04Z`; all 50 matched stored attributes with zero publisher-side status changes. [Source observation](source-smoke-test.md#final-readiness-scd2-observation) |
| Idempotent replay, incremental and backfill | PASS | Real independent date windows, fixture replay and initial/subsequent incremental runs, plus watermarks and retry tests. Complete publisher change capture remains PARTIAL under the source requirement. [Verification](final-verification.md), [runbook](runbook.md) |
| Roughly 1M+ genuine records | PASS | 1,033,290 distinct Bronze IDs and 1,002,639 published Gold facts achieved across 119 pipeline runs. Zero synthetic records in real database. [Counts](evidence/final/real-load-counts.json) |
| Performance, EXPLAIN ANALYZE and measured optimization | PASS | Before/after plans and three comparable executions per phase at 1,002,639 facts. Covering index `gold.fact_agency_resolution_cover` (49.8 MB) achieved a 1.890× median speedup (47.1% runtime reduction) on agency resolution query with identical result hashes. [Performance](performance-report.md) |
| Three recovery demonstrations | PASS | Actual container SIGKILL, PostgreSQL unavailable at startup and malformed batch with identical downstream hashes. [Recovery](failure-recovery-report.md) |
| Schedule and canonical run history | PASS | Actual host cron with a synthetic source, fresh Compose wrapper run and persisted successful watermark. [Cron](scheduling-evidence.md), [verification](final-verification.md) |
| Gold analytics, CTEs and window functions | PASS | Four queries executed on 1,002,639 genuine facts. Before/after result hashes match for all four. [SQL](../sql/analytics/README.md), [plans](performance-report.md) |
| Multi-stage non-root Docker, health checks and named volumes | PASS | Clean image build, UID 10001, PostgreSQL 16.14, migration/health checks and persisted rows after restart. [Verification](final-verification.md) |
| Ruff, pre-commit, and unit/integration tests | PASS | 273 tests passed, seven hooks, lint, format, context and whitespace passed. [Verification](final-verification.md) |
| GitHub Actions before merge | PARTIAL | [PR #11 CI](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45355202036) and [merged main CI](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45355638854) passed. Final feature-head CI requires push of final branch. |
| Protected main and required checks | FAIL | GitHub returned `protected: false` and no active branch rules. Requires repository owner action on GitHub settings. [Branch status](https://api.github.com/repos/nijat-akhundzada/nyc-311-data-pipeline/branches/main) |
| Feature branches, atomic conventional commits and preserved history | PASS | Merged feature PRs from all three contributors and conventional commits. [Contributions](contributions.md) |
| Real teammate code reviews | NOT VERIFIED | Requires human teammate review comments on the open PR. [Contributions](contributions.md) |
| Repository and README deliverables | PASS | Repository includes code, tests, migrations, Gold SQL, Docker and CI. README names all three members and describes setup, quality, model, replay and Git evidence. [README](../README.md), [runbook](runbook.md) |
| Credentials and private datasets excluded | PARTIAL | No source payloads or credentials added by the final branch. Tracked-file history and credential-pattern checks passed within their inspected scope. [Verification](final-verification.md) |
| Individual ownership, Q&A and peer feedback | NOT VERIFIED | Each student's role and actual PR authorship are recorded. Student explanations and peer feedback require human assessment. [Contributions](contributions.md) |

ADR-001 remains **PROPOSED**. The remaining open items are genuine publisher-side SCD2 transitions (retained as PARTIAL), repository branch protection, teammate peer review, and final-head CI.
