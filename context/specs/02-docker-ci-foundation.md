# Spec 02 — Docker Ci Foundation

**Owner:** Firuz  
**Status:** PLANNED / NOT IMPLEMENTED  
**Type:** Implementation  
**Dependencies:** 01 accepted  

## Objective
Reproducible developer/CI setup and production-sensible container.

## Required implementation tasks
1. Create pyproject.toml/lock and package stub; coordinate dependencies with owners
2. Multi-stage Dockerfile, non-root runtime, healthcheck and named Postgres volume in compose
3. Use DB readiness/health dependencies and explicit `docker compose` profiles for scheduler/test if helpful
4. Add .env.example with placeholders and .gitignore safeguards
5. Add pre-commit hooks, ruff config, pytest minimal smoke checks
6. Add GitHub Actions named lint, unit, integration with PostgreSQL service; do not require live API or real credentials
7. Document commands and add optional CI cache without leaking secrets

## Files and boundaries
- `Dockerfile`
- `compose.yaml`
- `.github/workflows/ci.yml`
- `.pre-commit-config.yaml`
- `pyproject.toml`
- `.env.example`
- `tests/unit/test_smoke.py`

## Acceptance criteria
- [ ] Docker builds and non-root user verified with actual command output
- [ ] Postgres persists through container recreation
- [ ] CI jobs run on PR and fail if lint/tests fail
- [ ] Healthchecks actually validate process/DB state rather than always return true

## Required verification
- Focused pytest tests (unit/integration), formatting/lint, plus a specific manual end-to-end check where relevant. Record exact commands and results in PR.
- Test unhappy paths and prove no unintended row-count or downstream changes.
- Where infrastructure/source access is missing, disclose missing evidence; do not mark pass.

## PR handoff
- Branch `feat/02-docker-ci-foundation-firuz` (shorten if preferred).
- Conventional atomic commits; open draft PR to `main`; use PR template; request human peer review.
- Do not change another owner’s directory or common contract without review and documented approval.
