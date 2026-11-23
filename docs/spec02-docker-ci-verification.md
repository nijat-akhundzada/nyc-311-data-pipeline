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

---

## 4. PR #6 integration reconciliation (supersedes the local-only caveats above)

This is foundation integration evidence, not full Spec 02 acceptance. ADR-001 remains
PROPOSED; no source-dependent gate, application runner or domain behavior is added.
The historical Windows results above are retained as Firuz's original evidence.

### History and conflict resolution

Merged `origin/main` at `01e19e77e0e8359359e61f59726ecd83624d3af1` normally into
`feat/02-docker-ci-foundation-firuz`; merge commit `adcf34a` retains both parents.
Firuz's original commits `d3c192c`, `8e7f416`, `e376741`, `c344be8`, and `e891e1d`
remain ancestors, along with the merged API-client and migration work. No rebase,
squash, force push, main edit or migration rewrite was performed.

The sole textual conflict was add/add `tests/conftest.py`. Both versions provided
the same maintenance-DSN and isolated-database fixtures. The combined version uses
one neutral `nyc311_test_` database prefix and retains per-test creation, connection
termination and cleanup. A missing DSN still skips local DB tests; CI supplies a DSN.
A configured unreachable DSN fails, rather than skipping.

Compatibility changes:

- Align pre-commit Ruff with locked Ruff 0.17.6; declare the already locked PyYAML
  test dependency and pin build setuptools to the existing development-lock version.
  Both requirements locks remain unchanged: runtime versions are identical in the
  development lock, and all declared dependencies are covered. Locked installation,
  editable installation without dependency resolution/build isolation, and
  `uv pip check` succeeded (34 compatible installed packages).
- Apply the shared 100-column formatter to the merged Python files. Compare parsed
  ASTs against `origin/main`: API modules, migration implementation and their owner
  tests are identical. `git diff origin/main -- db/migrations` is empty.
- Include existing SQL assets in the non-root image at `/app/db/migrations`.
  Container callers must supply this existing explicit migrations-directory option;
  no migration API or default-path semantics changed.
- Replace the Compose print-only readiness claim with an actual Psycopg connection
  and `SELECT 1`, followed by the UID assertion. This is a one-shot foundation probe,
  not a pipeline health endpoint or production runner.
- Add `.dockerignore` to exclude credentials/local environments and Git metadata
  from build context. CI jobs are named `lint`, `unit`, `integration`; they install
  the locked toolchain, collect all existing unit/integration directories, import
  both owner modules in the image and verify packaged migration assets. The PG
  healthcheck names the configured role/database explicitly.
- Add two deterministic infrastructure regression tests for lock compatibility,
  hook version alignment and complete CI test-directory/runtime-import wiring.

### Actual local verification

Python 3.12.11, pytest 9.2.0, Ruff 0.17.6, Docker 28.5.1, Compose
2.40.3-desktop.1. Dependencies were installed from `requirements-dev.lock` into
`/tmp/nyc311-pr6-venv`; no repository virtual environment or real credentials were used.

| Command/check | Actual result |
| --- | --- |
| `ruff check .` | Passed |
| `ruff format --check .` | Passed; 80 files already formatted |
| `pytest tests/unit -q` | 159 passed |
| `TEST_DATABASE_URL=<isolated-PG16-DSN> pytest tests -q -ra` | 169 passed, zero skipped (159 unit + 10 integration) |
| `PRE_COMMIT_HOME=<temporary-cache> pre-commit run --all-files` | All seven hooks passed |
| `bash scripts/validate-context.sh` | Context validation passed |
| `git diff --check` | Passed |
| `docker build -t nyc311-pr6-verify:local .` | Passed |
| `docker run --rm nyc311-pr6-verify:local id -u` | `10001` |
| Container imports `ApiClient`, migration module and `discover_migrations('/app/db/migrations')` | Passed; version 0.1.0, one migration discovered |

The integration total includes Nizami's eight migration tests and Firuz's two
connectivity/isolation tests. No live NYC 311 requests were made. The combined
fixture cleans up its disposable databases.

### Docker, PostgreSQL and named-volume evidence

To avoid touching a teammate's running containers/data, verification used a temporary
copy of `compose.yaml`: only the project/container/volume names, host port (55439),
absolute build context and built image tag were isolated. Original service commands,
healthcheck, health dependency and volume mount were retained. A temporary env file
held a synthetic test-only credential; the repository `.env` was not read or changed.
Project: `nyc311-pr6-verify`; volume: `nyc311_pr6_verify_data`.

- `docker compose ... up -d --wait db` succeeded; inspection reported `healthy`.
  `SHOW server_version` returned **16.14**.
- `docker compose ... run --rm app` succeeded with
  `nyc311_pipeline v0.1.0 database_ready=true uid=10001` after a real `SELECT 1`.
- Image config ID:
  `sha256:4c173b34cc2f8332dd3bdec623842121e299c906f5551274b1cab80c86910189`.
- Inserted `pr6_named_volume_survives` into a synthetic probe table, then ran
  `docker compose ... up -d --force-recreate --wait db` without deleting its volume.
  Container changed from `a91c45b5556f` to `8d41d99dee37`; a subsequent SQL query
  returned the same marker. No production named volume was used.

Controlled negative checks (expected failures, not passing production operations):

- A temporary unused import made Ruff exit **1**; a temporary `assert False` test
  made pytest exit **1**. These demonstrate local failure propagation, not an
  intentionally failing remote CI run.
- An explicitly configured unreachable PostgreSQL DSN made the connectivity test
  fail with `OperationalError`, exit **1**, and no skip.
- `pg_isready -h 127.0.0.1 -p 1` inside the DB container returned **2**, no response.
- After stopping the isolated DB, `docker compose ... run --rm --no-deps app`
  exited **1** with `OperationalError` (unresolvable stopped-service hostname),
  without claiming readiness. The isolated DB was subsequently restarted healthy.
- One initial verification invocation used unsupported `compose run --no-build`;
  Compose rejected the flag before running the probe. Retried with supported
  `compose run --rm app`; the real readiness result above is from that successful run.

### Remaining review boundaries

Pre-commit reports an upstream deprecated stage-name warning for the existing
pre-commit-hooks v4.6.0 configuration; all hooks execute successfully. This is
nonblocking and does not require expanding the toolchain upgrade scope.

Remote Actions results must be checked for the pushed head and reported separately;
local success alone does not establish CI success. No approval, merge, source-contract
acceptance or full Spec 02 completion is recorded here.
