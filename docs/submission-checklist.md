# Submission requirement matrix — deadline 26 November 2026

**Recommendation: NOT READY for full assignment submission.** Reviewed against
the [assignment PDF](source-assignment.pdf). See the [final verification](final-verification.md)
for commands, measured results and canonical run IDs.

| Requirement | Status | Evidence or remaining gap |
|---|---|---|
| One public API, pagination, retries and rate limits | PARTIAL | One NYC Open Data dataset, fixture-tested retry policy and measured backfills. Source staleness, HTTP 503 and a connection timeout limited reliable throughput. Actual quota and full source change semantics remain unverified. [Source audit](evidence/final/scale-source-audit.json) |
| Durable crash resume and checkpoints | PASS | Real frozen-generation resume completed at page 5. Isolated SIGKILL drill resumed from its committed page. [Final verification](final-verification.md), [recovery](failure-recovery-report.md) |
| Validation, quarantine with reasons and quality gate | PASS | 86 real quarantines. Clean Compose run exited 4 for 2/20 invalid and preserved published fingerprints. [Counts](evidence/final/real-load-counts.json), [recovery](failure-recovery-report.md) |
| Bronze, Silver, Gold star schema and atomic publication | PASS | 299,204 distinct Bronze IDs, 277,791 Silver requests and 277,791 Gold facts. DB constraints and rollback tests cover the loaded star schema. [Model](data-model.md), [verification](final-verification.md) |
| Genuine SCD Type 2 changes | PARTIAL | Observed-time SCD2, exclusion constraint and synthetic transition tests. 168 matching source observations from the original generation, zero later-generation comparisons and zero verified genuine transitions. [Source observation](source-smoke-test.md#final-readiness-scd2-observation) |
| Idempotent replay, incremental and backfill | PASS | Real independent date windows, fixture replay and initial/subsequent incremental runs, plus watermarks and retry tests. Complete publisher change capture remains PARTIAL under the source requirement. [Verification](final-verification.md), [runbook](runbook.md) |
| Roughly 1M+ genuine records | FAIL | 299,204 distinct Bronze IDs and 277,791 published facts. 722,209 additional distinct facts needed. [Counts](evidence/final/real-load-counts.json) |
| Performance, EXPLAIN ANALYZE and measured optimization | PARTIAL | Before/after plans and three comparable executions per phase at 277,791 facts. Million-row performance remains unmeasured. [Performance](performance-report.md) |
| Three recovery demonstrations | PASS | Actual container SIGKILL, PostgreSQL unavailable at startup and malformed batch with identical downstream hashes. [Recovery](failure-recovery-report.md) |
| Schedule and canonical run history | PASS | Actual host cron with a synthetic source, fresh Compose wrapper run and persisted successful watermark. [Cron](scheduling-evidence.md), [verification](final-verification.md) |
| Gold analytics, CTEs and window functions | PASS | Four queries executed on 277,791 genuine facts. Before/after result hashes match for all four. [SQL](../sql/analytics/README.md), [plans](performance-report.md) |
| Multi-stage non-root Docker, health checks and named volumes | PASS | Clean image build, UID 10001, PostgreSQL 16.14, migration/health checks and persisted rows after restart. [Verification](final-verification.md) |
| Ruff, pre-commit, and unit/integration tests | PASS | 273 tests passed, seven hooks, lint, format, context and whitespace passed. [Verification](final-verification.md) |
| GitHub Actions before merge | PARTIAL | [PR #11 CI](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45355202036) and [merged main CI](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45355638854) passed. Final feature-head CI requires separate evidence. |
| Protected main and required checks | FAIL | GitHub returned `protected: false` and no active branch rules. [Branch status](https://api.github.com/repos/nijat-akhundzada/nyc-311-data-pipeline/branches/main), [active rules](https://api.github.com/repos/nijat-akhundzada/nyc-311-data-pipeline/rules/branches/main) |
| Feature branches, atomic conventional commits and preserved history | PASS | Merged feature PRs from all three contributors and conventional commits. [Contributions](contributions.md) |
| Real teammate code reviews | NOT VERIFIED | The inspected PR review lists, including PR #11, were empty. Submission needs review evidence from teammates. [Contributions](contributions.md) |
| Repository and README deliverables | PASS | Repository includes code, tests, migrations, Gold SQL, Docker and CI. README names all three members and describes setup, quality, model, replay and Git evidence. [README](../README.md), [runbook](runbook.md) |
| Credentials and private datasets excluded | PARTIAL | No source payloads or credentials added by the final branch. Tracked-file history and credential-pattern checks passed within their inspected scope. [Verification](final-verification.md) |
| Individual ownership, Q&A and peer feedback | NOT VERIFIED | Each student's role and actual PR authorship are recorded. Student explanations and peer feedback require human assessment. [Contributions](contributions.md) |

ADR-001 remains **PROPOSED**. The outstanding release gates are one million
published facts, a genuine SCD2 transition, main protection, real peer review
and final-head CI.
