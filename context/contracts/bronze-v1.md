# Bronze v1 — lead-authorized engineering slice

Authorization: Nijat's explicit durable Bronze implementation task, 2026-11-24.
**Nizami/Firuz approvals: not recorded.** Changes require human cross-owner review.
ADR-001 stays PROPOSED and source evidence remains partial. This bounded interface
supersedes conflicting proposed persistence/lifecycle details, not downstream gates.

## Frozen configuration and time

`bronze_contracts.IngestScope` is immutable: dataset `erm2-nwe9`, extraction kind,
ordered disjoint source-wall-time `[start,end)` intervals, page size 1..5000,
explicit UTC update bounds for update mode, contract/client/timezone policy versions.
Zero-based string segment IDs follow interval order. Separate creation/update
scopes never share checkpoints. SHA-256 canonical UTF-8 JSON freezes this config;
record caps and run IDs are invocation controls, excluded from config identity.

This slice accepts **explicit source-wall-time intervals**, not UTC user windows.
America/New_York is provisional; it does not localize ambiguous/nonexistent event
times or imply publisher confirmation. UTC-window/DST conversion and quarantine
remain future validation work. Cursor values preserve source text; source keys
remain opaque text (C-collated DB identity). Complete provider collation/CDC is unproven.

## Public boundaries and ownership review

- `BronzeRepository(connection)`: caller supplies a dedicated idle, autocommit
  psycopg 3 connection. Repository owns short transactions, never commits a
  caller transaction, never reconnects. Migration framework/ledger stays unchanged.
- `dataset_lock(dataset_id)`: context holds SHA-256-derived session advisory lock
  `nyc311:run:<dataset_id>` on the **same connection** used for all mutations.
  A contender fails `RunConflict`; a lost connection requires a new session, lock
  and explicit resume. Do not externally manipulate this dedicated connection.
- `begin_run(run_id, scope, resume=False)`: minimal pre-Spec07 storage adapter to
  **ops.pipeline_runs**, not a second history manager. New run UUID is caller-owned;
  unknown/duplicate UUID or another unfinished extraction conflicts. Resume checks
  exact config and permits interrupted running/paused/retryable failed extraction.
  Terminal failure is not resumable. Previously completed ingestion returns its
  durable summary. Resume appends an audit event, retaining previous failures.
- `load_run`, `load_checkpoint(run_id, segment_id)`: persisted truth. Checkpoint
  carries run/segment/page number, typed cursor, pinned generation and exhaustion.
- `commit_page(run_id, expected_checkpoint, Page) -> CommitResult`: run row then
  checkpoint row locked; compare the complete expected checkpoint. Validate record
  order/bounds/cursor/exhaustion and sanitized freshness metadata. First accepted
  commit pins run generation; every segment must match it. One transaction inserts
  raw versions, receipt, associations, checkpoint and ingest counters. No API page
  advances durable progress on validation/transaction failure.
- `finish_ingestion(... outcome=completed|paused|failed, category, retryable)`:
  adapter changes ingestion state/audit only under the dataset lock. Completed
  extraction requires every segment durably exhausted; canonical run status stays
  **paused**, `ingest_complete=true`, `published_at=NULL`. Result outcome may say
  `completed` only for extraction. No `succeeded` or successful update watermark.
  Firuz's later RunTracker must reuse this table/lock and supersede or wrap this
  narrow adapter; it must not create another run-history truth.

Nizami reviews DDL, batching/CAS/receipts and transaction ownership. Firuz reviews
this explicitly temporary adapter, audit events and lock/recovery boundary. These
are reviewable new interfaces; their earlier implementation is not silently changed.

## Physical schema and replay

Migration 0002 adds `bronze.raw_service_requests`, `ops.pipeline_runs`,
`ops.ingest_checkpoints`, `ops.ingest_page_receipts`, `ops.run_records`,
`ops.run_events`. Existing 0001 and migration ledger/lock are untouched. A trigger
protects immutable run config/identity and an already pinned generation. FK/unique
constraints protect raw identity, association ordinals and receipt identity.

Raw uniqueness: `(dataset_id, unique_key, SHA256(canonical complete projected JSON))`.
Source metadata participates; observation/run metadata does not. Ordered page hash
covers raw hashes plus checkpoint-before/after (including generation/exhaustion).
It excludes received time and request ID. Identity is `(run, segment, page_no)`.
Same receipt/hash returns its original result with `replayed=true`, even when the
checkpoint has moved further. Different content or stale CAS fails visibly.
`received_count` counts committed response rows; `raw_inserted_count` counts new
versions. New runs may associate existing versions without inserting raw payloads.
No evaluated/quality denominator is inferred from either count.

Raw and association writes use set-based JSONB recordsets: statement count is
bounded per page, not per record. Page limit bounds memory. No million-row benchmark
is claimed. Checkpoints and successful-publication watermarks remain distinct;
no code in this slice can advance the latter. No Silver/Gold objects are written.

A completed **extraction** releases the unfinished-ingestion restriction, allowing
an explicitly new reconciliation/replay run. This is a narrow pre-publication
exception to the proposed full lifecycle's unfinished-run rule; future publication
still requires the dataset lock and reviewed staged-run selection. Unfinished
paused/retryable extraction must be explicitly resumed, never silently replaced.

## Ingestion orchestration and errors

Spec 03 `ingestion.service.ingest(client, repository, scope, run_id=None,
resume_run_id=None, max_records=None)` holds the dataset lock, creates/resumes the
canonical run, loads each segment checkpoint, calls existing `ApiClient.fetch_page`,
and commits accepted pages. A short nonempty response is not terminal; only an
accepted empty response durably exhausts a segment. Cap limits newly received rows
per invocation and pauses without fetching beyond it; resuming may change the cap.
Page size/config stays frozen. No scheduler or production pipeline CLI is added.

Existing four-attempt/180-second strict client policy is unchanged. Generation
change is terminal for that run; re-extraction uses a new explicit run ID and the
same frozen bounds. Freshness unknown/malformed/order failures never commit a page.
Storage errors are sanitized (`storage`, retryable only for connection/transient
operational errors); conflicts are `run_conflict`. No raw payload/DSN/token is logged.

On ambiguous commit acknowledgement, retain the exact fetched Page. If the locked
connection remains usable, reload the checkpoint and retry that same commit once;
the receipt resolves success without double counting or re-fetching. If the session
is lost, propagate storage failure; reconnect/reacquire/explicitly resume from
persisted truth. Do not assert failure status was persisted when DB access failed.
Uncatchable process death leaves running metadata; lock release permits explicit
resume, with a recovery audit event. No automatic live-lock stealing.

No complete incremental capture, fresh source snapshot, missing-key preflight,
quarantine, publication, genuine SCD2 change or assessment-scale data claim follows
from synthetic fixture tests. Reconciliation/export fallback remains ADR-001's
reviewed future work; there is no permissive freshness fallback.
