# Roles, ownership and PR protocol

| Member | Primary assigned assessment role | Specs / directories | Review expectation |
|---|---|---|---|
| **Nijat Akhundzadeh (lead, #1)** | API ingestion, restart, API changes, validation/gate, silver; end-to-end coordination | 01 (lead), 03, 04, 10; `ingestion/`, `validation/`, `silver/`, CLI/contracts | Review every PR; final merge |
| **Nizami (#2)** | PostgreSQL modeling, gold/SCD2, bulk loading, query optimization, analytics | 05, 06, 08; `db/`, `storage/`, `gold/`, `sql/` | Review Nijat/Firuz PRs and DB compatibility |
| **Firuz (#3)** | Docker/CI, schedule/run tracking, recovery tests | 02, 07, 09; `docker/`, `.github/`, `orchestration/`, `ops/`, recovery scripts | Review Nizami/Nijat PRs and deployment behavior |

## Branching
As verified on 25 November 2026, `main` requires pull requests, conversation
resolution, up-to-date branches and passing `lint`, `unit` and `integration`
checks. Force pushes and branch deletion are blocked, and there are no bypass
actors. The project lead intentionally set required human approvals to 0 in GitHub.
The team's review protocol below still applies. [Ruleset 28075415](https://github.com/nijat-akhundzada/nyc-311-data-pipeline/rules/28075415)

Each contributor: `git switch main && git pull --ff-only && git switch -c feat/05-db-foundation-nizami`; implement ONE spec; `git add <explicit paths>`; `git commit -m 'feat(db): ...'`; `git push -u origin <branch>`; `gh pr create --draft --base main --head <branch> --title 'feat(db): ...' --body-file ...`. Never add all files without checking `git status` and `git diff --cached`.

## Dependency management
Spec 01 freezes source and public contracts. After 01, Firuz can implement 02 while Nijat 03 and Nizami 05 work on independent files. DB foundation 05 is required for integration of 03/04 and gold. PRs may open as drafts before prerequisites merge but must rebase/merge `main` normally after approvals; **never force push main**.

## Review evidence
Author posts implementation summary, tests and output, schema/API change notes, risk, sample run IDs, negative tests. Reviewer reads diff, asks substantive questions and reproduces at least one check. Do not use AI-only approvals as substitute for real teammate code review. Nijat merges once approval, CI and spec acceptance pass.

## Deadline
26 Nov 2026. Prioritize correctness, recovery, measured perf and documentation; reduce bells/whistles rather than faking results. Reserve final day for full dataset and evidence.
