# Spec 01 — Source Contract Validation

**Owner:** Nijat  
**Status:** PLANNED / NOT IMPLEMENTED  
**Type:** Decision + audit  
**Dependencies:** None  

## Objective
Confirm source, scope, semantics, privacy and freeze common contract.

## Required implementation tasks
1. Perform live sample request and API field/type inventory without committing personal records
2. Establish >=1M real records via official count query; record query and result, not an invented number
3. Test pagination ordering and edge cases including equal timestamps and unique_key lexical/numeric behavior
4. Assess rate limits, Retry-After, token optionality, changed source records and availability of update timestamps
5. Decide SCD2 dimension and explicitly explain lack of historical snapshots
6. Update ADR-001 to ACCEPTED or document alternative source, then freeze contracts and CLI

## Files and boundaries
- `docs/source-smoke-test.md`
- `context/decisions/ADR-001-source-and-contracts.md`
- `context/contracts/README.md`

## Acceptance criteria
- [ ] Source queries, URLs, field inventory, sample redacted response and exact verification date recorded
- [ ] No downstream work approved while source/contract is unverified
- [ ] Creation/update keysets verified at equal timestamps, including repeatability across fresh source views; distinguish source query evidence from durable recovery tests
- [ ] Event timezone, UTC-window conversion and DST policy confirmed and documented; system update timestamps treated separately
- [ ] Source freshness, late-update/replacement/deletion limitations and fallback policy reviewed
- [ ] Genuine same-request tracked attribute change observed; SCD2 historical limitations explicitly retained

## Local audit progress — not acceptance

As of 2026-11-23, bounded count, metadata, creation/update ordering and tie-resume probes have supporting evidence in `docs/source-smoke-test.md`. Intermittent HTTP 503/DNS failures, stale-response flags, cross-query identity inconsistency, timezone semantics and missing genuine state-change observations prevent acceptance. No checkbox is marked complete and no downstream spec is unblocked. See `context/implementation-readiness.md` for proposed source-independent foundation boundaries; those require explicit spec amendments before implementation.

## Required verification
- Focused pytest tests (unit/integration), formatting/lint, plus a specific manual end-to-end check where relevant. Record exact commands and results in PR.
- Test unhappy paths and prove no unintended row-count or downstream changes.
- Where infrastructure/source access is missing, disclose missing evidence; do not mark pass.

## PR handoff
- Branch `feat/01-source-contract-validation-nijat` (shorten if preferred).
- Conventional atomic commits; open draft PR to `main`; use PR template; request human peer review.
- Do not change another owner’s directory or common contract without review and documented approval.
