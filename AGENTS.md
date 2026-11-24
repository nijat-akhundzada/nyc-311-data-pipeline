# Instructions for coding agents — NYC 311 pipeline

**First read in order:** `context/project-overview.md`, `context/architecture.md`, `context/code-standards.md`, `context/ai-workflow-rules.md`, `context/contracts/README.md`, `context/team-workflow.md`, `context/specs/00-build-plan.md`, the **assigned approved spec**, applicable ADRs, then current code/tests.

## Hard gates
- Merged implementation exists. Distinguish verified behavior, proposed contracts and branch-only evidence; descriptions alone are not proof.
- Only work on the one spec assigned by the human. A spec marked `BLOCKED` or pending approval is **not** permission to code.
- **Ownership:** Nijat: API/recovery cursor/schema drift/validation/quality/silver and integration; Nizami: migrations/bronze storage/gold SCD2/bulk/performance/analytics; Firuz: Docker/CI/scheduling/run history/recovery demonstrations. Shared contracts are lead-controlled.
- On contract conflicts, stop and open a question in the PR; do not silently invent integration APIs.
- Every persisted publish must be replay-safe, and failure must never expose partial silver/gold publication. Preserve quarantined bad rows and record a reason.
- Do not hardcode credentials or commit `.env`, secrets, datasets, virtualenvs, performance output with sensitive content.
- Honor the source API's rate limits; tests use fixtures, not live network by default.
- Never rewrite applied migrations, force push `main`, bypass CI, merge own PR, or claim a test passed without running it.
- PRs must name the spec, evidence, test commands and results, caveats, and cross-boundary changes.

## Git authorization
For this team project, the member prompts explicitly authorize a coding agent to **commit, push its feature branch and open a draft PR** after local verification. Agents must never push directly to `main`, merge, approve their own PR, alter branch protection, or use destructive git commands. If remote/credentials/gh CLI are absent, stop after local commits and give manual push/PR instructions. Never invent a PR URL.

## Source-of-truth priority
Approved spec > accepted ADR > overview/architecture > contracts > standards/workflow > implementation > tracker. Surface conflicts to Nijat.

## Work cycle
Read → verify dependencies → inspect → implement bounded change → test → update docs → atomic conventional commits → push branch → draft PR → human review. Update progress state only after merge, or label local status accurately.
