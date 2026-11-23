# Spec 01 — risk decision and cross-owner review

Status: review requested/prepared; actual owner decisions pending. This is not an approval record by inference. No source experiments or application code were generated for this amendment. Deadline: 26 November 2026.

## Actual decisions and evidence

| Decision | Actual record | State |
|---|---|---|
| Retain NYC 311 as selected source | Nijat's instruction on 2026-11-23 explicitly retains it despite incomplete verification | SELECTED; not source-verification approval |
| Engineering contract/risk acceptance | No acceptance decision supplied or recorded in inspected PR data | PENDING |
| Nizami domain-contract review | No decision supplied; PR #1 review/comment APIs returned empty lists | NOT RECEIVED; no approval assumed |
| Firuz lifecycle/client-policy review | No decision supplied; PR #1 review/comment APIs returned empty lists | NOT RECEIVED; no approval assumed |
| Limited Spec 03 activation | Lead requested the proposal, with implementation after documentation review/approval | PENDING documentation approval/merge; no code authorized in this task |
| Source evidence / genuine SCD2 | Existing audit is partial and no genuine same-request tracked change is evidenced | OPEN; never waived by fixture tests |

For each actual review record: owner, APPROVE/CHANGES REQUESTED/DEFER, exact reviewed commit, date, evidence/comment URL, unresolved items and permitted scope. Approval of one topic does not approve all topics. A new material contract change requires renewed review. Do not replace pending with approve based on silence, a passing CI check or lead source selection. No GitHub reviewer handles were provided; this document and the PR description carry the request, without guessing accounts or inventing review decisions.

## Nizami — requested review checklist

- [ ] Database interfaces and transaction ownership: short page transaction versus caller-owned silver/gold publication transaction; no storage commits inside caller-owned tx.
- [ ] Checkpoint durability/idempotency: raw identity/run associations, compare-and-swap page receipts, commit-acknowledgement loss, restart and separate successful watermark.
- [ ] Canonical operations: ops.pipeline_runs, ops.ingest_checkpoints, ops.quarantine and proposed run associations; resolve future ops.run_history reference without creating a duplicate table.
- [ ] Silver/Gold publication: complete staged quality gate, one transaction with run success/watermark, rollback and consumer visibility.
- [ ] SCD2: request-state natural key/tracked tuple, observed-time half-open boundaries/current-fact relationship, older/conflicting observations and separate genuine-source evidence.

Decision: NOT RECEIVED. Reviewed commit/date/link: not supplied. Unresolved items remain integration blockers; the limited no-DB exception does not settle them.

## Firuz — requested review checklist

- [ ] Run lifecycle/locking: canonical statuses, dataset session lock, interrupted-run ownership, phase/count ownership and no overlapping publication.
- [ ] Retry/failure policy: exact attempt/deadline/Retry-After rules, sanitized typed errors, stale/unknown/generation-change distinctions.
- [ ] Recovery boundaries: HTTP retry is not durable checkpoint recovery; lost DB commit acknowledgements and container/DB-startup drills remain later integration evidence.
- [ ] CI/testing: provide/coordinate locked HTTPX/pytest/ruff tooling; deterministic transport/clock fixtures, no public API/secrets, no claim that client tests prove pipeline integration.
- [ ] Scheduler boundary: later Spec 07 invokes approved runner/CLI, not the transport client; no scheduling or lifecycle implementation enters the limited Spec 03 scope.

Decision: NOT RECEIVED. Reviewed commit/date/link: not supplied. Tooling coordination is an activation prerequisite; this request does not modify Firuz's foundation files or branches.

## Approval/activation record (to be completed by humans)

- Amendment PR and final reviewed commit: PENDING.
- Human peer review identity/date/comment: PENDING.
- Nijat decision on bounded client policy and risk record: PENDING.
- Cross-owner decisions above: record independently; no silent approval of DB/lifecycle scope.
- Human merge and approved implementation base: PENDING.
- Active permission: NONE YET. After the documentation amendment is reviewed/approved/merged and tooling coordinated, only the five capabilities enumerated in Spec 03 become assignable. No database/publication/CLI permission is inferred.

## Git reconciliation and precise workflow

Inspected after fetch on 2026-11-23: main=702a7f8; PR #1 foundation head=09222a5, open/unmerged/mergeable, zero recorded reviews/comments; Spec 01 head=56c7281, one commit ahead and zero behind main. Repository open-PR search returned only PR #1; no Spec 01 PR was found. Read-only three-way merge simulation of existing foundation and Spec 01 branches reported no content conflicts. No teammate implementation branch was modified; ongoing foundation implementation is human-reported, not declared complete here.

This amendment branch `docs/01-risk-accepted-client-scope` descends from preserved Spec 01 commit 56c7281 and carries that proposal plus the narrow amendment. Its PR targets main and is the single combined Spec 01 decision/review change; the old Spec 01 ref is preserved, not rewritten. No redundant original Spec 01 PR needs to be opened. PR #1 remains separate and must be human-reviewed/merged independently. The amendment intentionally leaves Spec 02/05 files untouched and places its Spec 00 changes away from PR #1's foundation additions; recheck a three-way merge after edits to identify any content conflict.

1. Push the amendment branch normally; open a draft PR to main (or supply the comparison URL if write access is unavailable). Include this checklist and explicit pending approvals.
2. Human reviews PR #1's foundation scopes and the amendment's engineering/client-only decision; this agent does not merge either. PR #1 currently needs a real filled description/reviewer rather than its empty template.
3. After PR #1 or other main updates merge, fetch and merge origin/main normally into this documentation branch, resolve any actual conflict preserving both exceptions and teammate scopes, rerun checks and renew review if semantics changed. Never force-push/rebase a published shared branch for this task.
4. Record actual owner decisions/lead approval and final commit. Human merges the reviewed documentation amendment; no tracker/full-spec completion is inferred.
5. Only then create `feat/03-api-client-only-nijat` from current main (or a new equivalent name if it exists). Use the gated prompt. Coordinate Firuz's dependency lock/tooling; never borrow/edit a teammate's implementation branch. Implement only the client slice, run focused tests/lint, make conventional commits and open a human-reviewed draft PR. Full DB integration remains blocked on Spec 01 full acceptance/reviewed domain contracts and Nizami's full Spec 05 repository work.

Remaining evidence/integration blockers: trustworthy repeated fresh source views and the identity discrepancy; publisher timezone/DST and update/deletion semantics; genuine same-request SCD2 observations; cross-owner DB/lifecycle decisions; domain migrations/repository, validation/publication and actual recovery/performance/load/schedule demonstrations. The risk amendment changes permission boundaries, not those facts.
