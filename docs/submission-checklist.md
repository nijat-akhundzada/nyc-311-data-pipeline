# Submission requirement matrix — deadline 26 November 2026

**Recommendation: NOT READY for full assignment submission.** Implementation and
manual evidence on the final branch require human review; no automatic merge or
source-verification approval. PASS is scoped to the evidence described here.

| Requirement | Status | Exact evidence / remaining gap |
|---|---|---|
| Public API, pagination, retries/rate limits, resume | PARTIAL | Existing client/unit/repository tests, real bounded publications and actual kill resume. Cross-view generation consistency blocks reliable large extraction. |
| Bronze → Silver → Gold and quality quarantine | PASS | Real 71,492 Bronze / 42,738 Silver / 42,738 Gold; three real quarantines. Synthetic >5% gate leaves published hashes unchanged. [Counts](evidence/final/real-load-counts.json), [recovery](failure-recovery-report.md). |
| Gold star schema and SCD2 implementation | PARTIAL | Existing schema/current fact, exclusion/FK constraints and transition/replay tests. **Zero genuine source-backed tracked changes** observed; 42,738 initial real states only; 20 real IDs re-observed unchanged. |
| Idempotent incremental and historical backfill | PARTIAL | Fixture replay/incremental/watermark tests and cron pass; real date-window publications pass. Complete real update/deletion/replacement capture is unverified. |
| Roughly 1M+ genuine source records | FAIL | 71,492 distinct source IDs extracted, 42,738 published; no inflated/synthetic scale data. Latest official export HEAD returned 503; no versioned archive verified. [Real load](final-verification.md). |
| CTE/window analytics | PASS | Four executable queries, real PostgreSQL outputs and meaningful fixture integration test. [SQL](../sql/analytics/README.md). |
| Performance optimization with measured plans | PARTIAL | Three before/after real timings, identical results, modest 1.160× full-day median ratio; sparse regression retained. Only 13,126 facts. [Report/plans](performance-report.md). |
| Actual killed-container recovery | PASS | SIGKILL exit 137, checkpoint page 1 → resumed success exit 0, 20 unique facts. [Recovery](failure-recovery-report.md). |
| DB unavailable at pipeline startup | PASS | Actual run exit 5, bounded retryable failure, restart then successful run; named-volume rows survived. [Recovery](failure-recovery-report.md). |
| Malformed batch without partial publication | PASS | Exit 4, 2/20 invalid, retained quarantine; identical hashes across Silver/Gold/watermarks. [Recovery](failure-recovery-report.md). |
| Schedule and canonical run history | PASS | Actual host cron at 04:31:03Z; run `8e82e869-325a-40e1-8101-07bcc0a22829` published 20 synthetic requests. Temporary job removed. [Cron](scheduling-evidence.md). |
| Multi-stage non-root Docker, health, volume | PASS | Fresh image UID 10001, PostgreSQL 16.14 healthy; fresh DB migrations/publication, persistence across restart. [Verification](final-verification.md). |
| Unit/integration, Ruff, hooks and context | PASS | 273 tests (205 unit, 68 PostgreSQL integration), no skips/failures; final commands/results in [verification](final-verification.md). |
| Final-head GitHub Actions | NOT VERIFIED | PR #10 CI passed; the new scale branch/head still requires a PR CI run; never substitute local results. CI selects all existing unit/integration tests, including analytics. |
| Feature branches and conventional commit history | PASS | Preserved original team/merge commits and phase commits; [contributions](contributions.md). |
| Real teammate code reviews and protected main | NOT VERIFIED | Formal review lists empty; PR #5/#6/#9 timelines empty. Main-protection query denied (403). Human evidence required. |
| README, names/roles, model, commands, reports | PASS | [README](../README.md), [runbook](runbook.md), model, analytics, performance/recovery/source evidence and contribution history. |
| No committed credentials/datasets | PARTIAL | New evidence contains no source payloads/DSNs; local credentials and real dataset remain outside Git. Targeted tracked-file checks are not a comprehensive historic secret audit. |
| Individual explanation and final release approval | NOT VERIFIED | Each student must explain assigned/AI-assisted work; only the human lead approves submission. |

ADR-001 remains **PROPOSED**. Publisher timezone semantics, full update completeness
and genuine SCD2 observations are not upgraded by engineering tests.

Next actions: obtain stable fresh source views or approve a defensible immutable
export contract; finish real scale loading and repeat benchmarks; collect genuine
changes separately; obtain Nizami/Firuz reviews, verify branch protection and green
final-head CI. Preserve truthful partial evidence if external blockers persist.
