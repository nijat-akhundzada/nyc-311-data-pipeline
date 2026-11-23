# Spec 02 — Docker Ci Foundation

**Owner:** Firuz  
**Status:** FOUNDATION SCOPE APPROVED / NOT IMPLEMENTED; full scope gated  
**Type:** Implementation  
**Dependencies:** foundation: no source dependency; full scope: 01 accepted  

## Objective
Reproducible developer/CI setup and production-sensible container.

## Approved foundation scope — 2026-11-23

Firuz may implement pyproject/lock and package import stub, ruff/pre-commit, deterministic pytest smoke checks, GitHub Actions jobs named `lint`, `unit`, `integration` with PostgreSQL 16, a multi-stage non-root image, and PostgreSQL-only Compose health/readiness and named-volume setup. Coordinate dependency additions with Nijat/Nizami; Firuz owns the shared pyproject/lock. A real DB connectivity check may back the infrastructure integration job before Spec 05; do not present it as pipeline integration coverage.

No source API access, application run/health CLI, ingestion, scheduler, run history or domain schema is included. Do not add a dummy always-healthy pipeline service to satisfy a check. Application health/readiness and pipeline service wiring remain gated by accepted Spec 01 and a real implemented entry point. Foundation PRs retain this spec's branch/review workflow and report partial completion only.

### Foundation acceptance criteria

- [ ] Locked install, ruff check/format, pre-commit and deterministic pytest checks pass; commands/results recorded without live API or real credentials.
- [ ] Multi-stage image builds; runtime UID is verified non-root and package import succeeds. No functioning pipeline is claimed.
- [ ] PostgreSQL healthcheck/readiness succeeds when ready and fails for an unavailable DB; a disposable test marker survives container recreation on the named volume without deleting that volume.
- [ ] PR CI runs `lint`, `unit`, `integration`; controlled lint/test failure produces a failing check. Missing remote CI evidence is disclosed, not marked passed.
- [ ] Integration uses isolated PostgreSQL/fixtures. Migration tests are wired when Spec 05 foundation is available; no domain-table or source contract is invented.

The full acceptance criteria below remain mandatory for full-spec completion; passing this foundation checklist does not accept Spec 01 or complete Spec 02.

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
