# Contributions and review evidence

Assignment roles remain intact; final integrated work was explicitly assigned by
the lead and requires cross-owner review. Names and planned responsibilities are
not a claim that each person authored all code in that scope.

| Member | Responsibility | Observed GitHub contribution |
|---|---|---|
| Nijat Akhundzadeh (`nijat-akhundzada`) | Lead; API, cursor/recovery, validation, quality, Silver, integration | PRs #1/#3 contracts, #4 client, #7 Bronze integration, #8 durable extraction, #9 functional pipeline; this final branch |
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
PR #2 was closed without merging per the lead; it is not delivery evidence.
PR authors/merge SHAs and formal review queries:
[github-history.json](evidence/final/github-history.json).

The reviewed endpoints returned **no submitted formal reviews** for these eight
merged PRs. A merge or user-stated approval does not demonstrate substantive
teammate code review. Discussion/off-platform review is not inferred from empty
review lists. Combined issue/inline/review timelines for PR #5, #6 and #9
also returned no comments. Nizami must personally review analytics/SQL/index tradeoffs and
publication/SCD2 implications; Firuz must personally review drill isolation,
cron setup/cleanup and lifecycle evidence. Record actual human comments/decisions
on the final PR. No agent approves or merges its own work.

Main-protection API inspection returned **403 Resource not accessible by integration**;
protection settings are **NOT VERIFIED**, not disabled or verified. The lead must
inspect settings and supply evidence of required reviews/checks. Do not weaken
settings to make this submission pass.

## Git exercises actually evidenced

Published histories are retained. Normal merge commits include `fbc7503` (database
foundation into client), `adcf34a` (CI/main reconciliation and shared fixtures),
`62f3b63` (Bronze dependency update), and the PR merge commits above. These demonstrate
feature-branch integration and conflict resolution without force-pushing main.
This branch starts from merged main `71e76a2`; phase commits use conventional subjects.

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
