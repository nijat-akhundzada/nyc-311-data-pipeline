# Release Gate NN — [Release]

- Status: Draft
- Candidate: [commit/tag/image digest]

## Decision

Return exactly one outcome: **READY**, **READY WITH ACCEPTED RISKS**, or **NOT READY**.

## Required evidence

| Gate | Required proof | Result |
|---|---|---|
| Functional | [Acceptance/E2E evidence] | Pending |
| Contracts/data | [Validation/migration evidence] | Pending |
| Security | [Scan/isolation evidence] | Pending |
| Reliability | [Retry/recovery evidence] | Pending |
| Performance | [Measured environment evidence] | Pending |
| Operations | [Monitoring/backup/rollback evidence] | Pending |

## Evidence rules

- Repository configuration is not proof that runtime behavior succeeded.
- Local tests are not substitutes for required staging or production-like evidence.
- Missing evidence is BLOCKED, not PASS.
- Identify the exact immutable candidate evaluated.

## Verify when done

- [ ] Every mandatory gate has evidence or an explicit blocker.
- [ ] Accepted risks have an owner and rationale.
- [ ] No release/tag/deployment occurs when the result is NOT READY.
