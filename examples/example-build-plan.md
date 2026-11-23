# Example — Build Plan

This is a small API example showing dependency order, not a prescribed architecture.

| Unit | Type | Outcome | Depends on |
|---:|---|---|---|
| 01 | Decision | Authentication and account lifecycle are approved | Existing product context |
| 02 | Implementation | Shared API and error conventions are contracted | 01 |
| 03 | Implementation | Account registration and login work securely | 01, 02 |
| 04 | Implementation | Projects can be created and read by their owners | 02, 03 |
| 05 | Audit | Authorization and cross-account isolation are verified | 04 |
| 06 | Implementation | Production observability and recovery controls exist | 04 |
| 07 | Release gate | Release evidence is evaluated | 05, 06 |

Notice that the plan resolves a product decision before code, establishes shared contracts before feature endpoints, and does not call repository configuration alone “production ready.”
