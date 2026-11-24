# feat(submission): add measured analytics and verified recovery evidence

Base `main`; head `feat/final-analytics-recovery-submission`. Lead-authorized final
Spec 08/09/11 iteration and remaining 07/10 verification after merged PR #9.
Original team history and migrations 0001–0004 are unchanged. ADR-001 stays PROPOSED.
Human cross-owner review and merge only.

## Result and evidence

- Four CTE/window analytics SQL files, PostgreSQL assertion test and definitions.
- Actual real API publication: **27,392 distinct Bronze IDs / 13,126 Silver /
  13,126 Gold**, two real quarantines. Three successful bounded runs; weekly and
  subsequent daily windows stopped on source-generation changes. Official export
  probe also stale. **One million real records not achieved.**
- Three before/after measured full-day plans on that source-only DB; medians
  **2.747ms / 2.368ms (1.160×)**, identical results. Optional covering index, no
  migration rewrite. Slower sparse experiment retained; no scale claim.
- Actual container SIGKILL exit 137 then durable resume exit 0, 20 unique facts.
  DB-down actual run exit 5 then restart/success; malformed 10% batch exit 4 with
  two quarantines and every published-table hash unchanged. Isolated resources.
- Actual host cron triggered existing incremental runner; canonical successful run
  `8e82e869-325a-40e1-8101-07bcc0a22829`. Explicit synthetic fixture mode; temporary
  job removed and existing crontab preserved.
- README/runbook, source/performance/recovery/scheduling reports, contribution and
  requirement matrix. Metadata-only JSON evidence; dataset/credentials outside Git.

## Actual local verification

`pytest -q`: **268 passed, zero failed/skipped**, final run 24.40s
(202 unit + 66 PostgreSQL 16 integration).
`ruff check .`, `ruff format --check .`, `pre-commit run --all-files` (seven hooks),
`bash scripts/validate-context.sh`, `sh -n scripts/scheduled-run.sh`,
`git diff --check`: passed. Fresh Docker build, UID 10001, fresh database migrated
and fixture-published; named-volume rows survived restart. PostgreSQL 16.14.
GitHub Actions on final head must be checked separately; local checks are not CI.

## Cross-boundary review and release risks

Nizami: analytics denominators, observed-time state joins, measured plans/index
tradeoffs and source-only counts. Firuz: disposable drill guards, kill/startup
boundaries, cron fixture opt-in/cleanup and CI inclusion. Nijat: source generation
failures, genuine-change evidence gap and release limitations. Actual peer decisions
must be recorded; no submitted review is inferred from merged PRs.

**Not submission-ready:** missing million-row scale, genuine observed source SCD2
transition, full publisher/timezone/update guarantees, final-head green CI and
human review/protection evidence. Branch protection inspection returned 403.
No scheduler framework, application redesign or relaxed source checks introduced.
See `docs/final-verification.md` and `docs/submission-checklist.md`.

Remote handoff: branch pushed; automatic draft creation denied (GitHub connector
403) and gh unauthenticated. No branch Actions runs recorded at inspection. Open
this draft PR manually; final-head CI must run and pass after PR creation.
