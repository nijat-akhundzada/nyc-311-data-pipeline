# fix(ingestion): recover rejected stale views within the existing retry budget

Base `main` (`16a8a1a`, merged PR #10); head `feat/final-real-source-scale`.
Nijat explicitly approved the narrow stale-response retry amendment during this
iteration. ADR-001 remains PROPOSED. Human review/merge only.

## Demonstrated problem and bounded change

Real page traces showed a fresh 24 November page followed by an explicitly stale
23 November view. Generation-first classification made this terminal before the
existing stale retry could execute. Reject stale/lagging views first using the
same four-attempt/180-second page budget, then compare the pin on fresh responses.
Fresh mismatches/unknown markers still fail. Rejected rows/cursors never commit.
No migration, query selection, identity, accepted-page trust criterion, quality
threshold, checkpoint, database tooling or publication transaction change.

## Actual real-source outcome

- **71,492 distinct genuine Bronze IDs / 42,738 Silver / 42,738 Gold.** Added
  44,100 distinct raw IDs and 29,612 published requests; zero synthetic scale rows.
- Previously failing small window now published 568; Jan 6 published 14,085 with
  one invalid quarantine; Jan 7 resumed at the durable cursor, accepted only an
  empty completion page, and published 14,907 without inflating received counts.
- Jan 8 exhausted stale retries; its one allowed resume advanced another durable
  page, then exhausted the next page on three stale responses and HTTP 503.
  The batch stopped. Run `88f90c05-4851-44b6-8853-3a588118e198` retains 10,000
  received rows/checkpoint page 2, retryable/unpublished. No bypass/abandonment.
- Nine invocations, 288.970s cumulative active loading time; 46 pipeline HTTP
  attempts (42 HTTP 200, 4 HTTP 503; 23 explicitly stale). Exact URLs/headers saved.
- Twenty previously published non-closed requests freshly compared: **zero tracked
  changes**. Genuine SCD2 remains unproven. No versioned official export verified.

## Verification

**273 passed, 0 failed/skipped** (205 unit, 68 PostgreSQL integration), 22.48s.
Focused suite: 173 passed. Unit tests cover stale/lagging old views, identical
request retry, four-attempt exhaustion and terminal fresh mismatch. PostgreSQL
tests prove no stale-body checkpoint advancement and no failed-run publication.
Ruff lint/format, seven pre-commit hooks, context/whitespace passed. Rebuilt image
UID 10001; fresh disposable DB health/migrate/publication/replay passed with exactly
20 synthetic rows per layer; DB removed. Real-data volume preserved separately.

Evidence updated in the existing source audit, final verification, runbook,
checklist, README and payload-free `docs/evidence/final/scale-source-audit.json`.
Prior performance figures remain labeled as the original 13,126-fact experiment.

## Remaining gates and reviewers

**Million-row target NOT achieved; no genuine tracked transition observed.** Source
staleness/503 availability remains the blocker after the approved classification
fix. Resume the retained run only when fresh responses recover, then complete
independent bounded runs. Recheck the sample across a later publisher generation;
repeat scale benchmarks after genuine volume succeeds. Publisher timezone/snapshot/
change-feed completeness, peer reviews/protection and final-head CI remain open.

Nizami: raw/dedup/count evidence, no migration rewrite, observed-time state limits.
Firuz: unchanged retry budget, checkpoint recovery boundaries, test/CI compatibility.
Nijat: approved policy, source traces and honest remaining requirements. Record
actual decisions, never assumed approvals.

Branch push succeeded. Connector draft-PR creation returned 403; gh unauthenticated.
Merged PR #10 CI passed, but this branch had zero Actions runs at inspection.
Create this draft PR manually, then verify all jobs on its latest head. Do not merge
automatically or claim prior-main CI proves this code head.
