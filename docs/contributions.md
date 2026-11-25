# Contributions and review evidence

Assignment roles remain intact; final integrated work was explicitly assigned by
the lead and requires cross-owner review. Names and planned responsibilities are
not a claim that each person authored all code in that scope.

| Member | Responsibility | Observed GitHub contribution |
|---|---|---|
| Nijat Akhundzadeh (`nijat-akhundzada`) | Lead; API, cursor/recovery, validation, quality, Silver, integration | PRs #1/#3 contracts, #4 client, #7 Bronze integration, #8 durable extraction, #9 functional pipeline; PR #10 final analytics/recovery/submission; PR #11 source scale and stale-response retry |
| Nizami (`NizoDotNet`) | Database/migrations, Bronze storage, Gold/SCD2, bulk/performance, analytics | PR #5 database migration foundation |
| Firuz (`FiruzHedarov`) | Docker/CI, scheduling/run history, recovery demonstrations | PR #6 tooling/Docker/CI foundation |

Verified merged PRs:
[#1](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/1),
[#3](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/3),
[#4](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/4),
[#5](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/5),
[#6](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/6),
[#7](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/7),
[#8](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/8),
[#9](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/9).
PR #10 is also [merged](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/10);
its [CI run](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45349465274)
completed successfully. [PR #11](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/pull/11)
merged at `6c98a8f`. Its [PR CI](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45355202036)
and the subsequent [main CI](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/actions/runs/45355638854)
both succeeded. The PR #11 review endpoint returned an empty list.

PR #2 was closed without merging per the lead; it is not delivery evidence.
PR authors/merge SHAs and formal review queries:
[github-history.json](evidence/final/github-history.json).

The reviewed endpoints returned **no submitted formal reviews** for the
inspected merged PRs. A merge or user-stated approval does not demonstrate substantive
teammate code review. Discussion/off-platform review is not inferred from empty
review lists. Combined issue/inline/review timelines for PR #5, #6 and #9
also returned no comments. Nizami must personally review analytics/SQL/index tradeoffs and
publication/SCD2 implications; Firuz must personally review drill isolation,
cron setup/cleanup and lifecycle evidence. Record actual human comments/decisions
on the final PR. No agent approves or merges its own work.

On 24 November 2026 the public GitHub branch endpoint reported
`protected: false`, classical protection disabled and no required checks. The
branch-rules endpoint returned an empty list. The protected-main requirement was
**FAIL** at that point. The detailed protection endpoint requires authentication.
[Branch status](https://api.github.com/repos/nijat-akhundzada/nyc-311-data-pipeline/branches/main)
[Active branch rules](https://api.github.com/repos/nijat-akhundzada/nyc-311-data-pipeline/rules/branches/main)

On 25 November 2026, main branch protection was verified (**PASS**) under
[ruleset 28075415](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/rules/28075415). The lead intentionally set required human approvals
to 0. Teammate reviews remain **NOT VERIFIED**.

## Git exercises actually evidenced

Published histories are retained. Normal merge commits include `fbc7503` (database
foundation into client), `adcf34a` (CI/main reconciliation and shared fixtures),
`62f3b63` (Bronze dependency update), and the PR merge commits above. These demonstrate
feature-branch integration and conflict resolution without force-pushing main.
The final readiness branch starts from merged main `6c98a8f`. Its phase commits
use conventional subjects.

Read-only inspection commands for the defense:

```sh
git log --graph --oneline --all
git log --merges --oneline origin/main
git shortlog -sn origin/main
git show adcf34a -- tests/conftest.py
```

No reset/revert/cherry-pick exercise is claimed merely because Git supports it.
No applied migrations were rewritten. Each student must explain the code,
transactions, tests, evidence limits and AI-assisted contributions personally;
that oral/individual-assessment requirement cannot be satisfied by an agent.
