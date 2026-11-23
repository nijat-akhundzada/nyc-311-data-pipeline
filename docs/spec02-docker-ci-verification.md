# Spec 02 — Docker and CI Foundation Verification Report

**Owner:** Firuz  
**Status:** PARTIAL foundation evidence only (lead-approved foundation exception dated 2026-11-23).  
ADR-001 remains PROPOSED and full Spec 02 acceptance remains gated on Spec 01 acceptance and real pipeline CLI implementation.

---

## 1. Scope and Chosen Approach

In accordance with the lead-authorized foundation scope (Spec 02):

1. **Shared Packaging & Dependency Locks:**
   - `pyproject.toml`: Modern PEP 621 metadata, dependencies (`httpx>=0.27.0`, `psycopg[binary]>=3.1.18`, `pydantic>=2.7.0`), development dependencies (`pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `ruff>=0.4.0`, `pre-commit>=3.7.0`), ruff lint/format configurations, and pytest configuration.
   - `requirements.lock`: Hash-less pinned runtime dependencies matching teammate environments (Python 3.12, HTTPX 0.28.1, Psycopg 3.3.9, Pydantic 2.14.4).
   - `requirements-dev.lock`: Pinned development and test dependencies including Ruff 0.17.6 and Pytest 9.2.0.
   - Package stub: `src/nyc311_pipeline/__init__.py` exporting `__version__ = "0.1.0"`.

2. **Multi-Stage Non-Root Docker Image:**
   - `Dockerfile`:
     - Stage 1 (`builder`): Builds virtual environment `/opt/venv` and installs locked dependencies from `requirements.lock`.
     - Stage 2 (`runtime`): Creates dedicated non-root user `appuser` with UID `10001` and GID `10001` (`groupadd --gid 10001 appgroup && useradd --uid 10001 --gid appgroup`).
     - Copies `/opt/venv` and application code with non-root ownership.
     - Declares `USER appuser`. Default `CMD` tests package import and runtime UID.

3. **PostgreSQL 16 Compose with Healthcheck and Named Volume:**
   - `compose.yaml`:
     - Service `db`: Uses official `postgres:16-alpine`.
     - Healthcheck: `pg_isready -U ${POSTGRES_USER:-nyc311} -d ${POSTGRES_DB:-nyc311}` (interval: 5s, timeout: 5s, retries: 5).
     - Named Volume: Mounts persistent named volume `postgres_data` (`nyc311_postgres_data`) to `/var/lib/postgresql/data` ensuring data survives container restarts/recreations.
     - Service `app`: Isolated under profile `app` with `depends_on: db: condition: service_healthy` to demonstrate readiness coordination without exposing an artificial always-healthy endpoint.

4. **GitHub Actions CI Workflow:**
   - `.github/workflows/ci.yml`:
     - Job `lint`: Runs on `ubuntu-latest`, verifies `ruff format --check .` and `ruff check .`.
     - Job `unit`: Runs deterministic unit smoke tests and verifies Docker multi-stage build, non-root runtime UID (`10001`), and package import.
     - Job `integration`: Uses a `postgres:16-alpine` service container with `pg_isready` healthcheck and runs PostgreSQL 16 connectivity and isolation tests via `TEST_DATABASE_URL`.

5. **Pre-commit Hooks:**
   - `.pre-commit-config.yaml`: Configured with `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`, `check-added-large-files`, `ruff`, and `ruff-format`.

---

## 2. Actual Verification Evidence (2026-11-23)

### A. Environment and Package Installation
```bash
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-dev.lock
.\.venv\Scripts\pip install --no-deps -e .
.\.venv\Scripts\python -c "import nyc311_pipeline; print(nyc311_pipeline.__version__)"
# Output: 0.1.0
```

### B. Linting and Formatting (Ruff)
```bash
.\.venv\Scripts\ruff check .
# Output: All checks passed!

.\.venv\Scripts\ruff format --check .
# Output: 66 files already formatted
```

### C. Pre-commit Hooks
```bash
.\.venv\Scripts\pre-commit run --files pyproject.toml compose.yaml Dockerfile .env.example .github/workflows/ci.yml .pre-commit-config.yaml requirements.lock requirements-dev.lock src/nyc311_pipeline/__init__.py tests/conftest.py tests/integration/test_db_connectivity.py tests/unit/test_smoke.py tests/unit/test_container_config.py
# Output:
# trim trailing whitespace.................................................Passed
# fix end of files.........................................................Passed
# check yaml...............................................................Passed
# check toml...............................................................Passed
# check for added large files..............................................Passed
# ruff.....................................................................Passed
# ruff-format..............................................................Passed
```

### D. Deterministic Pytest Execution
```bash
.\.venv\Scripts\pytest -v
# Output:
# ============================= test session starts =============================
# platform win32 -- Python 3.12.4, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\OnOff-09092023\Desktop\MagProj1\nyc-311-data-pipeline\.venv\Scripts\python.exe
# configfile: pyproject.toml
# testpaths: tests
# plugins: anyio-4.16.0, platformdirs-4.14.8, asyncio-1.5.0
# asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
# collected 8 items
# 
# tests/integration/test_db_connectivity.py::test_postgres_version_16 SKIPPED [ 12%]
# tests/integration/test_db_connectivity.py::test_isolated_database_crud SKIPPED [ 25%]
# tests/unit/test_container_config.py::test_dockerfile_multi_stage_and_non_root PASSED [ 37%]
# tests/unit/test_container_config.py::test_compose_postgres_service_and_named_volume PASSED [ 50%]
# tests/unit/test_container_config.py::test_unavailable_database_connection_failure PASSED [ 62%]
# tests/unit/test_smoke.py::test_package_import PASSED                     [ 75%]
# tests/unit/test_smoke.py::test_core_dependencies_importable PASSED       [ 87%]
# tests/unit/test_smoke.py::test_deterministic_smoke PASSED                [100%]
# 
# ======================== 6 passed, 2 skipped in 2.42s =========================
```

### E. Negative / Controlled Failure Checks
- Unavailable Database Connection:
  Connecting to an unreachable port (`postgresql://nyc311:wrong@127.0.0.1:54329/nonexistent`) deterministically raises `psycopg.OperationalError` (verified in `test_unavailable_database_connection_failure`).
- Controlled Lint Failure:
  Introducing an unformatted line or unused import causes `ruff check` / `ruff format --check` to exit with status code 1.
- Database Integration Skipping:
  When `TEST_DATABASE_URL` is omitted, integration tests safely skip without failing or touching external infrastructure.

---

## 3. Disclosed Limitations & Environment Caveats

1. **Local Host Tooling:**
   The development host is Windows 11 without a running local Docker daemon or GitHub CLI (`gh`). Therefore, Docker image build and runtime UID verification are tested via AST/configuration assertions in `tests/unit/test_container_config.py` locally and executed directly via Docker CLI in the GitHub Actions `unit` CI job.
2. **Remote CI Link:**
   Remote CI results will be triggered upon branch push to GitHub and recorded in the PR review thread.
3. **Foundation-Only Boundary:**
   No application run/health CLI, ingestion, scheduler, run history, or domain tables are included in this PR. Application wiring remains gated on accepted Spec 01 and Nijat's integration runner.
