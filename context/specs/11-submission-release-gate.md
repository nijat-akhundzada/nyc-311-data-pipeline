# Spec 11 — Submission Release Gate

**Owner:** Nijat + Nizami + Firuz  
**Status:** FINAL ITERATION LEAD-AUTHORIZED; branch evidence pending human review  
**Type:** Release gate  
**Dependencies:** 10  

See the final integrated authorization in `00-build-plan.md`. Earlier separate
branch gates do not block this explicitly assigned final iteration. Acceptance
requires actual evidence; no full completion or peer approval is inferred.

## Objective
Check rubric and completeness before handing in.

## Required implementation tasks
1. Verify every line in docs/submission-checklist.md with observed evidence
2. Record GitHub PRs from each member, peer review comments and protected main settings
3. README must explain real setup/run, model, validation rules, idempotency and Git exercises; name all three
4. Attach performance report before/after numbers, EXPLAIN plans, at least 1M count proof
5. Record killed container/DB readiness/malformed drill outputs
6. Run fresh-clone compose commands and CI; confirm no credentials in repo or history and no history rewrite
7. Each student explains their assigned module and verifies AI-generated code personally

## Files and boundaries
- `README.md`
- `docs/performance-report.md`
- `docs/submission-checklist.md`
- `docs/failure-recovery-report.md`

## Acceptance criteria
- [ ] Every rubric requirement has actual evidence link
- [ ] Final gate explicitly READY or NOT READY, with blockers
- [ ] Only human declares submission ready

## Required verification
- Focused pytest tests (unit/integration), formatting/lint, plus a specific manual end-to-end check where relevant. Record exact commands and results in PR.
- Test unhappy paths and prove no unintended row-count or downstream changes.
- Where infrastructure/source access is missing, disclose missing evidence; do not mark pass.

## PR handoff
- Branch `feat/11-submission-release-gate-nijat` (shorten if preferred).
- Conventional atomic commits; open draft PR to `main`; use PR template; request human peer review.
- Do not change another owner’s directory or common contract without review and documented approval.
