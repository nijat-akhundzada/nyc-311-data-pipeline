# Actual host cron execution

On 24 November 2026 an actual host crontab entry invoked a byte-identical copy of
`scripts/scheduled-run.sh` from `/tmp/nyc311-final/scripts/` against the isolated
drill Compose project. This temporary path avoids relying on cron access to a
Desktop checkout. An atomic one-shot directory guard prevented repeated execution.
Production wrapper default remains the same incremental CLI; `SCHEDULE_FIXTURE`
is explicit opt-in for a synthetic demonstration only.

Cron log: **2026-11-24T04:31:03Z**. Canonical run
`8e82e869-325a-40e1-8101-07bcc0a22829` started 04:31:16.447001Z, succeeded/published
04:31:16.594008Z. Received/evaluated/valid 20; inserted 0 on replay; no extra facts.
The initialized incremental watermark advanced atomically. This proves a real
scheduler trigger and run history with a **synthetic source**, not a scheduled
live source success. [Invocation, result and cleanup evidence](evidence/final/cron.json).

The temporary tagged entry was removed immediately after observation. Existing
crontab entries were preserved; no recurring test schedule remains installed.

## Install, inspect and disable

Install only after an initial successful incremental for the same cohort. Use the
actual host timezone, Docker executable PATH, credentials in a protected `.env`,
absolute checkout path and writable log directory. Real production scheduling must
omit `SCHEDULE_FIXTURE`. Resume unfinished work explicitly before future triggers.

1. `crontab -l` inspects current jobs (it may report no crontab).
2. `crontab -e` preserves existing jobs while adding the adapted line from
   `docker/scheduler.crontab.example`; add `# nyc311-incremental` for identification.
3. Inspect the log's JSON run ID, then `pipeline report --run-id UUID`; exit 0 alone
   is insufficient because a capped run is not published.
4. Disable with `crontab -e`, removing only the tagged NYC 311 line; verify with
   `crontab -l`. Never use `crontab -r` on a shared user account.

No extra scheduler service/framework is introduced. PostgreSQL's same-session
advisory lock protects the entire run. Source failures and zero-candidate quality
failures remain explicit; cron does not retry endlessly or advance a failed watermark.
