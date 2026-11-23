# Team agent workflow

1. Human lead approves spec and resolves ADR blockers. Agent reads `AGENTS.md`, contracts, specific spec, current files.
2. Agent works on **one owned spec** in `feat/<number>-<slug>-<member>` branch; draft short plan and dependency checklist.
3. Implement and add deterministic tests; run focused checks, then full suite/compose if available; capture exact outputs.
4. Commit atomic conventional changes and push **only feature branch** (explicitly authorized by assigned team prompt). Open **draft PR** with `.github/pull_request_template.md`; use `gh pr create --draft ...` if configured.
5. Request at least one teammate review; Nijat performs final review and merge. Required CI pass; never self-approve/self-merge.
6. If tool permissions or credentials unavailable, give exact commands without pretending actions succeeded.
7. Keep tracker truthful; team lead marks Done after merge. Never rewrite main history.
8. Students must understand and explain every committed line; AI implementation is a draft subject to author validation.
