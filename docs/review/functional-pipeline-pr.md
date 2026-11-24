# feat(pipeline): complete functional Bronze Silver Gold integration

Base `main`; head `feat/functional-bronze-silver-gold-pipeline`. Lead-authorized
single integration PR for Spec 04/06 and minimum 07/10. Nizami/Firuz human review
remains required; no approval is assumed. Depends on merged PRs #1–#8.

## Result

Fresh PostgreSQL database can migrate and execute API → durable Bronze → staged
validation/quarantine → quality gate → atomic Silver/Gold publication → canonical
run success and incremental watermark. Direct psycopg SQL, existing dependencies,
small modular monolith; no replacement ingestion/storage framework.

- 0003: validation staging, quarantine, immutable run settings and quality counts.
- 0004: typed Silver; date/agency/complaint/borough/request-state dimensions;
  one-request fact; publication watermark. DB exclusion/current/composite-FK
  constraints protect observed-time SCD2. No applied 0001/0002 rewrite.
- Provisional New York normalization with deterministic DST gap/fold reasons;
  distinct-candidate quality gate (exactly 5% passes, greater/zero fails).
- SCD2 changes only on tracked status/agency/complaint, supports A→B→A and replay.
  No fabricated states or source-history claims.
- One transaction covers Silver, all Gold writes, run success and successful update
  watermark. Capped/incomplete extraction never publishes.
- CLI migrate/health/report/backfill/incremental/resume/cap; host-cron wrapper;
  actual non-root Compose pipeline profile and explicit synthetic fixture source.

## Verification / evidence

Full suite: **267 passed, 0 failed, 0 skipped** (202 unit + 65 PostgreSQL integration).
Ruff lint/format, seven pre-commit hooks, context/whitespace and shell syntax checks.
Docker fresh-DB end-to-end: 20 published requests, identical replay, 10%-invalid
quality failure (exit 4, two quarantines, unchanged published-row hashes), capped
pause/resume and initial incremental watermark. SQL failure injection after Gold
and at final success update rolls back every published table and watermark.
Validation restart after 1,000 staged rows resumes to 1,001 facts without refetch.
Bounded real-source run: one HTTP 200, three rows, capped/unpublished; not real full
publication evidence. Exact commands/results: docs/functional-pipeline-verification.md.

## Risks and review

ADR-001 stays PROPOSED; publisher semantics/source completeness and genuine SCD2
changes remain missing. Fixtures are clearly synthetic. Large-scale loading,
analytics/performance and real recovery/scheduling demonstrations remain. Remote
GitHub Actions must be green on final head; local checks are not remote CI evidence.
Nizami: DDL/batching/current-fact SCD2/atomic publication. Firuz: whole-run lock,
canonical lifecycle, bounded startup/recovery, scheduling/CI. Human review/merge only.
