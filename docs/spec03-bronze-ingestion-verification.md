# Spec 03 durable Bronze ingestion — review evidence

Implemented bounded slice, **not merged/peer-approved/full Spec 03**. PR #7 is merged into main
at `78de720ae8f5edea82592dc5e90444da1a1cd647`. Authorization and exact contract:
`context/contracts/bronze-v1.md`. Original transport client/retry/query modules,
Nizami's migration runner/0001, Firuz's locks/tooling/Docker/CI remain unchanged.
No peer decisions or source guarantees are assumed. ADR-001 remains PROPOSED.

## Implemented behavior

`ingestion.service.ingest` depends on the public `BronzeStore` protocol, not concrete
storage imports. It creates/explicitly resumes the canonical run on a dedicated
locked session, reads per-segment durable truth, fetches through the existing async
client, then commits each accepted page. Only empty pages exhaust segments. Record
caps apply to new rows per invocation, reduce request limits and pause without
advancing successful publication watermarks. Resume retains config/bounds/page size;
cap may change. Separate creation/update scopes and cursor kinds are supported.

`IngestResult.outcome` is completed/paused **extraction**, always `published=false`.
Completed ingestion remains a paused canonical pipeline run, ready for future
validation. Source/storage failures raise sanitized boundary errors; available DB
sessions record failed ingestion. If failure recording is impossible, running state
remains resumable rather than pretending a durable failed status exists. Retained
run_events preserve previous failures/resumes. No second history manager was added.

A retryable ambiguous commit error triggers checkpoint reload and one retry of the
**same retained Page**, not another fetch. The receipt resolves committed success.
A dead connection cannot retain the session lock: propagate, reconnect and explicitly
resume. Callers should allocate/retain their run UUID before starting (especially
for interruption recovery); the optional generated ID is returned on success.

Inputs are explicit source-wall-time intervals. America/New_York remains provisional;
no UTC-window splitting/DST conversion, quarantine or complete source CDC is claimed.
There is no production pipeline CLI, scheduler or Silver/Gold publication.

## Actual automated verification

Python 3.12.11, pytest 9.2.0, Ruff 0.17.6, shared development lock; PostgreSQL **16.14**
using isolated Compose DB on loopback port 55439. Synthetic HTTPX transports only.

```sh
TEST_DATABASE_URL=<isolated-PG16-DSN> pytest tests -q -ra
# 227 passed, zero failed, zero skipped (184 unit + 43 PostgreSQL integration)
ruff check .
ruff format --check .
PRE_COMMIT_HOME=<temporary-cache> pre-commit run --all-files
bash scripts/validate-context.sh
git diff --check
```

Lint/format, seven hooks, context and whitespace checks passed. Integration cases:
fresh load/equal timestamps, exact cap/new-connection resume, before/after-commit
interruption, lost acknowledgement without refetch, lost-session recovery, explicit
stale/malformed/transport failures, generation-invalidated resume/new run, immutable
scope rejection, final-write rollback, independent segments and typed update mode.
Parent Spec 05 tests prove receipt/CAS/concurrency/raw dedupe and batched statements.
No fixture mutation is presented as genuine source/SCD2 evidence.

An intermediate full run had **1 failed, 223 passed**: the previous client-only
phase test prohibited service.py entirely. A first fix removed direct storage imports
via a public protocol; the remaining obsolete no-service assertion still failed.
It was replaced by an explicit assertion that the original client imports neither
service nor persistence contracts. The original forbidden DB/CLI import scan remains.
Final 227-test result above is after that scope-appropriate correction and added cases.

## Actual Docker/PostgreSQL recreation check

Unchanged Dockerfile built successfully:

```sh
docker build -t nyc311-bronze-verify:local .
docker run --rm nyc311-bronze-verify:local id -u
# 10001
```

Final image config ID:
`sha256:7b6a8a033c770646c08780567c4322201933160442a9b9b317d7fb66c41a3b9a`.
Runtime imports both modules and discovers 0001 and 0002 at `/app/db/migrations`.
The existing migration CLI inside the non-root image successfully applied both:

```sh
python -m nyc311_pipeline.storage.migrations --migrations-dir /app/db/migrations upgrade
# applied: 0001_create_namespaces, 0002_bronze_ingestion
```

Verification used a temporary isolated Compose copy: project `nyc311-pr6-verify`,
volume `nyc311_pr6_verify_data`, synthetic credential and database `nyc311_bronze_demo`.
No ordinary project volume or real credentials were touched. Source Compose health
settings and mounts were retained. `compose config --quiet` and DB readiness passed.
A temporary stdin script used the real client with synthetic HTTP and the real repo:

- Run `a2674322-91cd-47b9-9a61-71809d452690`, non-root container: cap 3,
  outcome paused, new/total rows 3/3, unpublished. Raw/association/receipt counts
  **(3,3,2)**.
- `docker compose ... up -d --force-recreate --wait db` replaced DB container
  `09c8f34bc752` with `3860b6a32ca9`, retaining the named volume; became healthy.
- A **new** application container explicitly resumed the same run: completed
  extraction, new/total rows 1/4, unpublished. Counts **(4,4,4)**, no duplicated rows.
- `pg_isready -h 127.0.0.1 -p 1` inside DB exited **2**, proving negative readiness.

This is capped extraction + container/DB recreation evidence, not a killed-container
or scheduled-production recovery demonstration (Spec 09 remains outstanding).

## Bounded live evidence

After the one-row projection/header preflight documented in `docs/source-smoke-test.md`,
a distinct adapter-to-database smoke test used the existing client, one-record cap,
same one-day source interval, and a disposable DB. Outer live-page deadline 15 seconds,
no token/body logging and no large download. Actual result: one HTTP attempt, HTTP 200,
**one raw version, one association, one receipt**, paused, `ingest_complete=false`,
`published=false`, generation `2026-11-23T02:37:55+00:00`. Run ID:
`c89fd217-fb32-496e-9cbc-32b90b5f2c16`. The ephemeral live DB was removed afterward.
No source row was committed to Git. This establishes one accepted durable page only;
repeatable fresh snapshots, complete updates and genuine SCD2 changes remain open.

## Initial handoff Git/CI evidence (historical)

Two implementation branches preserve separate Spec 05/03 reviews. Review/merge the
Spec 05 parent first, then normally merge updated main into Spec 03 and retarget its
stacked PR to main. No rebase, force push or automatic PR merge.

GitHub connector PR creation returned HTTP **403**, resource not accessible by
integration; `gh auth status` reports no signed-in host. Browser form automation
could read the comparison but mutations repeatedly stopped on user-change protection;
no PR was submitted there. Therefore draft PR creation and **remote CI for these new
heads are unverified**, not passed. The existing workflow targets PRs to main only;
a stacked Spec 03 PR targeting the parent branch will not trigger CI until retargeted.
Local execution used its same all-unit/all-integration paths and locked toolchain.
Prepared PR descriptions: `docs/review/spec05-bronze-pr.md` and
`docs/review/spec03-bronze-pr.md`. Do not merge until actual required checks and human
Nizami/Firuz review are recorded.

Still outstanding: source/schema/missing-key preflight, UTC/DST eligibility and
quarantine, complete incremental/reconciliation behavior, validation/quality,
atomic Silver/Gold publication, scheduler/full lifecycle, source SCD2 evidence,
million-row throughput and real kill/startup failure drills. These are not waived.

## PR #8 final integration verification — 2026-11-24

Fetched origin and normally merged `origin/main` at
`78de720ae8f5edea82592dc5e90444da1a1cd647` into the existing Spec 03 branch.
Merge commit `62f3b63675e2372d66f9f6052a429396c2af780c` retains the old Spec 03
head `7f028f3` and merged main as parents. No conflict, rebase, force push or
migration rewrite occurred. The merge required no application-code change.

The diff against main is limited to the intended Spec 03 service/public protocol,
its tests and relevant contracts/spec/evidence/runbook documents. `db/migrations`,
`storage/`, dependency locks, pyproject, Docker, Compose and CI match main exactly.
ADR-001 remains PROPOSED. Completed extraction still means `published=false`, not
successful downstream publication or successful-publication watermark advancement.

Actual re-verification on the merged branch:

| Command/check | Result |
| --- | --- |
| `pytest tests/unit -q` | **184 passed** |
| `TEST_DATABASE_URL=<isolated-PG16-DSN> pytest tests/integration -q -ra` | **43 passed** |
| Total | **227 passed, zero failed/skipped** |
| `ruff check .` | Passed |
| `ruff format --check .` | Passed; 92 files formatted |
| `PRE_COMMIT_HOME=<temporary-cache> pre-commit run --all-files` | All seven hooks passed |
| `bash scripts/validate-context.sh` | Passed |
| `git diff --check origin/main...HEAD` | Passed |

PostgreSQL `SHOW server_version` returned **16.14**. Tests used the isolated
Compose database/temporary per-test DBs and synthetic HTTP fixtures; no live
source experiments were repeated. No skips are presented as passes.

At initial inspection PR #8 still targeted `feat/05-bronze-domain-foundation-nijat`.
A connector request to change its base to `main` returned HTTP **403**, resource
not accessible by integration. `gh auth status` confirms no authenticated host.
That base must be corrected in GitHub: this repository's existing workflow only
triggers for PRs targeting main. Remote CI must be observed on the final pushed
head; local passes do not substitute for GitHub Actions evidence. No PR approval
or merge is performed by the agent.
