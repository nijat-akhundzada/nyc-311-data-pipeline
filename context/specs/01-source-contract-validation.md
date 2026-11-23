# Spec 01 — Source Contract Validation

**Owner:** Nijat  
**Status:** AUDIT PARTIAL / NOT ACCEPTED; contract proposal in review  
**Type:** Decision + audit  
**Dependencies:** None  

## Lead-authorized durable Bronze slice — 2026-11-24

The project lead explicitly authorizes the minimum durable Bronze implementation
in the current task, risk-accepting the engineering policies in
`context/contracts/bronze-v1.md`. This supersedes older source/full-spec dependency
blocks **only** for Spec 05 raw/run/checkpoint/receipt/association persistence and
Spec 03 bounded ingestion/resume using the existing client. Separate dependent
feature PRs preserve the one-spec implementation workflow. No teammate approval
is inferred; Nizami reviews storage/transactions and Firuz reviews the temporary
canonical-table ingestion lifecycle adapter. No earlier owner implementation or
applied migration may be rewritten.

ADR-001 remains PROPOSED; full Spec 01 and full Specs 03/05 are not complete.
No Silver/Gold, quarantine/quality publication, scheduler, successful watermark
advancement, fabricated SCD2 history or production pipeline runner is authorized
by this slice. See the Bronze contract for exact interfaces and limitations.

## Objective
Confirm source, scope, semantics, privacy and freeze common contract.

## Proposed acceptance split and bounded implementation exception

The lead has selected NYC 311 for continued work despite incomplete evidence. Engineering contract acceptance is a separate human decision from source-verification completion; the risk amendment in ADR-001 does not tick evidence checkboxes or claim full Spec 01 completion. Engineering review may accept explicitly recorded assumptions/mitigations without claiming publisher semantics or complete change capture are proven. Nijat's selection decision is recorded; Nizami/Firuz contract decisions remain pending in `docs/spec01-contract-review.md`.

After this documentation amendment is reviewed, approved and merged, Nijat may implement only Spec 03 pure query generation, typed cursors, bounded HTTP client/retries, freshness validation and deterministic fixture-only unit tests. This exception does not require full source-evidence closure; it does require the approved bounded client policy and coordinated tooling. It grants no DB writes, durable checkpoint/recovery claims, publication or production CLI integration. Full-spec/source-dependent gates outside this exception and the existing Spec 02/05 foundation scopes remain unchanged. The implementation prompt is a gated draft, not active authorization during this task.

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
- [ ] Full downstream work remains gated; approved foundation scopes remain intact, and only a separately reviewed/approved Spec 03 client-only exception may bypass full Spec 01 completion
- [ ] Creation/update keysets verified at equal timestamps, including repeatability across fresh source views; distinguish source query evidence from durable recovery tests
- [ ] Event timezone, UTC-window conversion and DST policy confirmed and documented; system update timestamps treated separately
- [ ] Source freshness, late-update/replacement/deletion limitations and fallback policy reviewed
- [ ] Genuine same-request tracked attribute change observed; SCD2 historical limitations explicitly retained

## Local audit progress — not acceptance

As of 2026-11-23, earlier bounded count, metadata, creation/update ordering and tie-resume probes have supporting evidence in `docs/source-smoke-test.md`. The targeted follow-up made only two request definitions, each attempted normally and once outside the sandbox; all four attempts failed at DNS resolution, with no HTTP response/new source observation. Stale-response flags, cross-query identity inconsistency, fresh repeatability, timezone semantics and missing genuine state changes prevent acceptance. No checkbox is marked complete. Nijat's approved foundation exceptions remain intact; this audit does not alter Spec 02/05 scopes or promote full-spec readiness.

## Review deliverables and boundaries

- `context/contracts/README.md`: proposed version 1 with explicit cursors, page receipts/transactions, freshness/retry/DST rules, layer contracts, canonical ops.pipeline_runs, lifecycle and CLI errors. Nijat/Nizami/Firuz review required before freeze.
- ADR-001: PROPOSED with gate-by-gate missing evidence, implementation risks and fallback; no acceptance inferred from defaults.
- `docs/spec03-ingestion-handoff.md`: full integration design remains contingent; Spec 03 now proposes a separate client-only exception, with its own activation/acceptance conditions. `prompts/team/NIJAT-SPEC03-CLIENT-ONLY.md` is gated until amendment approval.
- `context/sessions/2026-11-23-spec01-contract-review.md`: Git/PR inspection, exact downstream readiness and next evidence task. No tracker completion or source-dependent implementation is claimed.

## Required verification
- Focused pytest tests (unit/integration), formatting/lint, plus a specific manual end-to-end check where relevant. Record exact commands and results in PR.
- Test unhappy paths and prove no unintended row-count or downstream changes.
- Where infrastructure/source access is missing, disclose missing evidence; do not mark pass.

## PR handoff
- Branch `feat/01-source-contract-validation-nijat` (shorten if preferred).
- Conventional atomic commits; open draft PR to `main`; use PR template; request human peer review.
- Do not change another owner’s directory or common contract without review and documented approval.
