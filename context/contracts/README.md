# Integration contracts — proposed version 1 for Spec 01 review

**Not frozen or approved.** Supersedes version 0 as the review proposal only. ADR-001 engineering acceptance and source-evidence completion are separate; both remain open. NYC 311 selection is lead-approved. The limited Spec 03 client-only exception activates only after review/approval/merge of its documentation amendment; this file alone grants no implementation permission. Nijat approves the source/client policy; Nizami reviews persistence/publish/SCD2; Firuz reviews lifecycle/locking/errors. Existing approved foundation scopes are unchanged. Physical DDL and implementation remain with their owners.

## Functional integration exception

The lead authorizes [functional v1](functional-v1.md) for the current single-branch
implementation. It supersedes conflicting proposed downstream details for this slice,
not missing source evidence or human review. ADR-001 remains PROPOSED.

## Bounded Bronze engineering authorization — 2026-11-24

The lead now authorizes the narrow engineering interface in [Bronze v1](bronze-v1.md)
for durable ingestion. That document supersedes conflicting **proposed** persistence
and pre-Spec07 adapter details only for this bounded slice. It does not freeze the
remaining version 1 contract, claim Nizami/Firuz approval, accept ADR-001 or complete
source verification. No downstream dependency gate is released.

## Client-only subset proposed for limited implementation

The current ADR risk amendment and Spec 03's client checklist govern this subset after explicit activation; the DB/lifecycle/publish proposals below remain unapproved. Cross-owner decisions are recorded at `docs/spec01-contract-review.md`, not inferred from branch existence or missing objections.

Transport-only types live under `ingestion/models.py`, without DB/runner imports:

- `CreationCursor` and `UpdateCursor` retain the kind/value/key structures below. Validate a nonempty opaque text key without changing it. Creation values are parsed naive source wall times, updates are offset-aware and serialized UTC `Z`; reject mismatched cursor kinds and malformed values.
- `ApiPageRequest`: kind (`creation`/`update`), creation_start_source and creation_end_source (naive ISO source-wall-time bounds for one interval), nullable matching cursor, limit (integer 1..5,000), nullable pinned_generation (parsed UTC truth-header time); update mode additionally requires aware update_lower_utc/update_upper_utc. Bounds must be strictly increasing. The fixed reviewed field projection is not an arbitrary identifier argument. A future runner, not this slice, constructs requests from multi-interval Scope and persisted state.
- `Page`: ordered raw records, candidate `next_cursor` (last record or unchanged for an empty response), exhausted (only true for empty response), received_at_utc, generation, request_id and sanitized HTTP metadata. No checkpoint/run ID, transaction, write callback or durable-progress acknowledgement is included. First acceptable page returns generation to its caller; a supplied generation must match.
- `ApiClient.fetch_page(request: ApiPageRequest) -> Page` performs only a single logical page fetch with the exact retry/freshness policy in ADR-001. It neither loops across pages nor persists anything. `build_query(request)` is pure and emits a parameter mapping; use single-quoted SoQL literals with embedded apostrophes doubled as documented by [Socrata text literals](https://dev.socrata.com/docs/datatypes/text). HTTP query values are passed as parameters, not concatenated into an unescaped URL. Fixture tests do not prove live server collation/coverage.

Freshness header names are case-insensitive; stripped flag values true/false are parsed case-insensitively and other values fail as unknown. Parse truth/secondary HTTP-date timestamps to aware UTC; require secondary >= truth. After rejecting explicitly stale/lagging responses within the existing retry budget, a pinned-generation change on an otherwise fresh response fails immediately (lead-approved amendment, 2026-11-24). Do not relax mandatory markers to obtain a passing client test; handle missing metadata explicitly. Business-event timezone conversion, quarantine persistence, run/segment orchestration and full shared contracts.py are excluded from this slice.

## Evidence and remaining decisions

`docs/source-smoke-test.md` separates observed HTTP behavior from design choices. Text identity, floating event dates, fixed UTC update metadata, bounded creation/update keyset syntax and tie predicates were observed. Freshness/identity inconsistencies, publisher timezone/DST rules, update completeness and genuine same-request changes remain unverified. Current DNS failures prevent new source observations. No snapshot-consistency or complete change-feed guarantee is asserted.

Defaults below are precise proposals to review, not claims about the source. Acceptance needs the gate table in ADR-001. Open review questions must be resolved in the Spec 01 PR before freeze; no owner should infer missing interfaces.

## Source projection and types

- Dataset ID `erm2-nwe9`; GET `https://data.cityofnewyork.us/resource/erm2-nwe9.json`, HTTPS only. Optional secret `SOCRATA_APP_TOKEN` via `X-App-Token`, never query/log output.
- Proposed ingestion `$select`: `unique_key,created_date,closed_date,agency,agency_name,complaint_type,descriptor,status,borough,incident_zip,resolution_action_updated_date,:updated_at`. This combined projection needs a successful fresh preflight before acceptance; individual/subset fields have evidence. Bronze preserves the received projection, not an unrequested full provider row.
- `unique_key`: opaque nonempty text, unchanged; server and client ordering use text, never numeric casts. Database tie comparison uses deterministic `C` collation. Live variable-width key ordering still requires verification; local text ordering tests cannot prove provider collation.
- `created_date`: required floating timestamp; `closed_date` and `resolution_action_updated_date`: nullable floating timestamps. `:updated_at`: required fixed UTC timestamp for update mode. Other selected values are nullable text; missing optional values normalize to null. Numeric IDs or incompatible field types are rejected, never silently coerced.
- Raw optional omissions are legal; a required field missing from the schema is a contract error. New categorical values are legal text, not a fixed enum. Preserve actual status labels; only normalized `Closed` is closed for metrics until reviewed vocabulary evidence supports others.
- Check selected field/type declarations at run start; tolerate unrelated additive metadata fields, record a drift event without payloads, fail on removal/incompatible change of required projected fields. Addresses, coordinates and resolution descriptions are not requested; descriptor remains bronze-only. No record bodies or free text in logs.

## Time and scope

Selected engineering interpretation for the risk proposal: `SOURCE_EVENT_TIMEZONE=America/New_York`, **not publisher-confirmed**. Never treat an offset-free event value as UTC. Keep its exact source text and parsed naive wall time for cursor ordering; store a derived UTC timestamp separately only under an approved interpretation. Fixed `:updated_at` values parse independently as offset-aware UTC; do not localize them again. This selection is an explicit provisional assumption, not completed timezone verification.

DST policy proposal: determine valid UTC candidates by round-trip through the IANA zone. One candidate is valid; zero candidates gives `nonexistent_local_time`; two distinct candidates gives `ambiguous_local_time`. Quarantine the entire affected record, retaining its raw fields/reason, rather than invent a fold. This applies to each nonnull event timestamp needed in silver. Missing optional closure is not a timezone failure. Record the zone/tzdata version in run config. These rules handle ambiguity safely but cannot verify publisher semantics.

CLI date-only bounds mean UTC midnight, start inclusive/end exclusive. Also accept ISO-8601 timestamps with explicit offset, normalized to UTC; reject naive datetime bounds. Convert requested UTC windows to one or more source-wall-time intervals split at timezone transitions, query a superset if necessary, then apply exact UTC eligibility after conversion. Ambiguous rows are quarantined, not silently filtered out. Never assume local time is monotonic through a fall-back transition; source cursor order remains wall time plus key. Candidate baseline is 2025 UTC `[2025-01-01T00:00:00Z,2026-01-01T00:00:00Z)`; the earlier local-calendar count is not a count of this exact window.

`Scope` is an immutable run configuration: contract_version, dataset_id, mode, creation_start_utc, creation_end_utc, source wall-time interval list, extraction kind (`creation` or `update`), selected field list, normalization/timezone policy, update_lower_utc/update_upper_utc when relevant. `scope_id` is SHA-256 of canonical JSON of these values; never mix checkpoints from different config/intervals. A creation cohort must be explicitly configured for incremental mode; do not default to all history.

## Typed cursors and frozen bounds

- `CreationCursor`: `{kind:"creation", created_date_source:<original timestamp text>, unique_key:<text>}`.
- `UpdateCursor`: `{kind:"update", updated_at_utc:<UTC ISO-8601 with Z>, unique_key:<text>}`.
- `Checkpoint`: run_id UUID, scope_id, segment_id integer, cursor (nullable before first page), next_page_no integer, exhausted boolean, committed counts, pinned_source_generation, contract_version. One row per `(run_id, segment_id)`; each interval/partition has its own segment. A `generation` is the parsed source truth-modification header, not a provider snapshot token.
- Creation requests apply interval `[wall_start,wall_end)`, `$order=created_date ASC,unique_key ASC` and strict lexicographic predicate `(created_date > d OR (created_date = d AND unique_key > k))` after a cursor. Never use offset pagination.
- Update requests apply the approved creation cohort **and** `:updated_at >= lower AND :updated_at < upper`, `$order=:updated_at ASC,unique_key ASC`, and `(:updated_at > u OR (:updated_at = u AND unique_key > k))`. Use the system timestamp, not `resolution_action_updated_date` or HTTP Last-Modified, for this cursor.
- Request values are encoded with HTTP-client parameters and a tested SoQL literal escaper; identifiers are hardcoded from the reviewed allowlist. Validate returned keys strictly increasing and greater than the supplied cursor, including across page boundaries. A duplicate or decreasing key aborts the run; never skip it to make progress.
- Default page size 1,000, configurable from 1 to 5,000; use the remaining invocation cap for the final request when capped. These are chosen limits, not a measured API quota. Continue until a fresh, validated empty page, even after a short nonempty page. Empty-page exhaustion is itself durably committed.
- Freeze every bound before page 1 and retain it on crash resume. For incrementals propose `upper = run_started_at_utc - 5 minutes`, `lower = previous_successful_upper - 48 hours`; first run requires an explicit configured lower bound. The lag/overlap are mitigation defaults, not proofs of completeness. Process newly created records via creation reconciliation and changed records via update extraction; late imports with old creation dates need reconciliation.
- Only a fully exhausted, quality-passed, published run advances the successful update upper bound. Failed quality/publication must not skip an update window. A page cursor advances independently after bronze durability; it is never the successful publication watermark.

## Freshness and bounded retries

Proposed strict publication policy: require `X-SODA2-Data-Out-Of-Date=false`, parseable truth and secondary modification headers, secondary not older than truth, and the same truth-generation value across every accepted page/empty page in a run. First acceptable page pins generation. Missing/invalid markers fail with `source_freshness_unknown`; explicit stale/mismatched secondary retries within budget. An otherwise fresh truth-generation change invalidates the run (`source_generation_changed`): leave bronze/quarantine auditable, publish nothing, do not advance successful watermarks. Start a new run rather than silently resetting its cursor.

On resume, stale/lagging responses are rejected under the same bounded retry budget; the first accepted fresh response must match the pinned generation; otherwise fail that run and re-extract its frozen scope under a new run ID. These markers are conservative evidence checks, **not a documented snapshot isolation guarantee**. Cache-Control: no-cache may be requested but never bypasses the checks. Compare approved projection/metadata at run preflight. A missing-sort-key preflight (`$where=unique_key IS NULL OR created_date IS NULL`, `$limit=1`) must be verified before acceptance; if found, quarantine that sample and fail explicitly. For update mode also check missing `:updated_at` within the cohort. Do not filter unpageable records away without evidence/reason.

Retry policy proposal: one in-flight request; default maximum four attempts including the first; connect timeout 5s, per-attempt total timeout 30s, overall per-page deadline 180s. Retry transport timeout/DNS/reset, HTTP 202/408/429/500/502/503/504 and explicitly stale responses. Other HTTP errors, malformed JSON/envelopes, breaking schema drift and order violations fail immediately. No certificate-error retry. Never retry a database commit by re-fetching and assuming it failed.

Between attempts use full jitter from zero to `min(30s, 2**(attempt-1) seconds)`. For valid Retry-After delta-seconds or HTTP-date, wait at least that duration (plus nonnegative jitter), never truncate it. If the required wait or another attempt cannot fit the 180s deadline, fail retryably instead of issuing early. Invalid/negative Retry-After is logged as invalid metadata and uses backoff. Persist categorized final failure/request ID only in future integration, not this no-DB client slice. Do not deliberately trigger rate limits in audit/CI; header handling must be fixture-tested during implementation and has not yet been implemented/tested. No claim of a known endpoint numeric quota or observed Retry-After behavior.

## Persistence and component interfaces

These are proposed exact interface responsibilities; shared types live in a Nijat-owned contracts module after approval. Implementations must not import another owner's private module. `tx` is one psycopg 3 transaction connection supplied by the runner; storage code must not commit a caller-owned transaction. Dependency/library selection is a review item, not permission to change Firuz's lockfile.

| Interface | Inputs → result | Owner / transaction rule |
|---|---|---|
| `ApiClient.fetch_page` | ApiPageRequest → Page | Nijat; transport-only client subset; future runner builds request from Scope/checkpoint; no DB writes |
| `BronzeRepository.load_checkpoint` | run_id, segment_id → Checkpoint | Nizami; persisted truth only |
| `BronzeRepository.commit_page` | run_id, expected_checkpoint, Page → CommitResult | Nizami; owns one short transaction for raw rows + run associations + checkpoint + ingest counters |
| `BronzeRepository.record_source_rejection` | run_id, raw_record, sorted reason_codes → rejection_id | Nizami persistence / Nijat reasons; quarantine without advancing cursor |
| `BronzeRepository.iter_run_candidates` | run_id, batch_size → iterator of reduced Candidate records | Nizami; stable source-ID order, bounded batches; original raw reference/update/observation time retained |
| `BronzeRepository.stage_validation` | run_id, batch of ValidRecord/Rejection → StageCounts | Nizami persistence / Nijat validation; one short transaction persists outcomes/quarantine, never publishes |
| `BronzeRepository.finalize_validation` | run_id → QualityCounts | Nizami; assert every reduced candidate has one durable outcome, then return evaluated/valid/invalid counts |
| `Validator.validate` | raw_record, approved time policy → ValidRecord or Rejection | Nijat; deterministic, no publication |
| `QualityGate.evaluate` | distinct evaluated_count, invalid_count, threshold → PASS/FAIL | Nijat; complete staged scope only |
| `SilverPublisher.publish` | run_id, tx → PublishCounts | Nijat; staged candidates only; never commits |
| `GoldPublisher.publish` | run_id, tx → PublishCounts | Nizami; same tx and scope as silver; never commits |
| `RunTracker.start` | immutable RunConfig → RunRecord | Firuz; creates lifecycle record; cursor truth stays in repository |
| `RunTracker.heartbeat` | run_id → none | Firuz; short audit write; cannot change cursors/count pages |
| `RunTracker.transition` | run_id, expected_status, new_status, phase, lifecycle_metadata, tx or null → RunRecord | Firuz; compare-and-swap lifecycle only; cannot advance checkpoints/watermarks |
| `RunTracker.finish` | run_id, status, category, retryable, tx or null → none | Firuz; success must use publish tx; failures use a separate short tx after rollback |
| `PipelineRunner.run` | RunConfig, resume_run_id or null → RunResult | Nijat integration, Firuz lifecycle coordination; lock/run boundary |

`Page` contains raw records in response order, derived next cursor (last record, or unchanged for empty page), exhausted boolean, received_at_utc, generation, request_id and sanitized HTTP metadata. `CommitResult` contains the resulting checkpoint, received_count, inserted_raw_versions and page_no. Before commit, the client verifies freshness/order/envelope; the storage layer compares expected checkpoint under row lock. A repeated acknowledged page is a no-op returning its prior result; an older/conflicting page with different hash is rejected. An ambiguous connection loss is resolved by reloading the checkpoint/page receipt before retry. No durable checkpoint is held only in process memory.

The first page commit pins generation in both run metadata and segment checkpoint atomically; subsequent segment commits must match the run's generation. Reload run metadata as well as the checkpoint after lost acknowledgement. Canonical page identity is `(run_id, segment_id, page_no)`; hash its ordered raw-record hashes, cursor-before/after and generation, excluding received_at/request ID so a byte-equivalent retry remains idempotent. Exhausted empty pages retain the prior cursor and advance only the page receipt/exhaustion state.

Lifecycle metadata is restricted to phase timestamps, categorized error/retry state and validated-stage counts; phase transitions cannot rewrite immutable config or ingest counters. `RunRecord` contains the persisted pipeline_runs fields listed below. `PublishCounts` contains inserted/updated/unchanged counts by layer and new state-version count; it is audit output, never a replacement quality denominator. Database failures raise typed storage errors rather than returning a pretend successful count. Exceptions cross module boundaries by category (`configuration`, `api_transport`, `api_http`, `source_freshness_unknown`, `source_stale`, `source_generation_changed`, `source_contract`, `source_order`, `quality`, `storage`, `run_conflict`), with sanitized message and retryable flag; CLI maps them using the exit-code section.

`Candidate` contains source ID, raw reference/object, source_updated_at, observed_at and run/segment provenance; reduction rules are in the Silver section. `ValidRecord` contains the proposed typed silver fields plus candidate reference and metric-eligibility flags; `Rejection` contains candidate reference, nullable source ID, raw object and sorted reason codes. `StageCounts` reports newly written/already present outcomes; `QualityCounts` contains evaluated/valid/invalid distinct-candidate counts. Retrying identical stage writes is a no-op; conflicting outcomes for the same candidate fail rather than overwriting evidence.

Canonical JSON for hashes: UTF-8, object keys sorted, no insignificant whitespace, original JSON value types retained. Raw SHA-256 covers the entire received projected object (including update metadata), never run/observation fields. Raw version uniqueness is `(dataset_id, unique_key, raw_hash)`. Full replacements may add raw versions; they must not add SCD2 versions solely due to metadata.

A run-to-record association is required even for already existing raw versions: proposed `ops.run_records` keys `(run_id, segment_id, page_no, row_ordinal)` with raw reference, source key, source_updated_at, observed_at, validation outcome/reasons and staged candidate reference. This preserves replay counts, A→B→A observations and complete run evaluation without duplicating raw payloads. Nizami chooses physical staging layout after review; use one durable association/staging truth, not competing per-owner copies. Page identity/receipt stores page hash and cursor transition for idempotent commit; it may share checkpoint-associated infrastructure rather than an extra public table.

## Canonical operations data and run lifecycle

- `ops.pipeline_runs` is canonical, **never a second ops.run_history table**. Required logical fields: run_id, contract_version, mode, scope/config hash + serialized immutable config, status (`pending`,`running`,`paused`,`succeeded`,`failed`), phase (`ingest`,`validate`,`publish`,`finished`), source generation, frozen bounds, started_at/heartbeat_at/finished_at/published_at, ingest_complete, retryable, error_category, resumed_from/run lineage if restarted, counts and successful update bound. Preserve error history in structured audit events; never erase failure evidence on resume.
- `ops.ingest_checkpoints` holds segment cursor/page receipts/exhaustion; `ops.quarantine` holds run ID, nullable source ID/raw reference, original rejected object, deterministic sorted reason codes and observation timestamp. Logical uniqueness for validation quarantine is run + raw reference + reason set; an unkeyed source-rejection sample uses its raw hash. Quarantine can remain after aborted publication.
- Counts: `received_count` counts committed response rows including overlap; `raw_inserted_count` counts newly stored versions. `evaluated_count`, `valid_count`, `invalid_count` count distinct candidate source IDs after deterministic per-run reduction, not HTTP attempts. Duplicate identical raw observations do not inflate gate counts. Source-level unpageable/schema failures abort before gate, not a fabricated invalid percentage.
- Runner holds one PostgreSQL session advisory lock for the dataset across ingest/validate/publish; the key is derived deterministically from dataset ID, not Python's randomized hash. This intentionally serializes all scopes/publications for the deadline. Concurrent triggers fail visibly with `run_conflict`; no overlapping publication. Heartbeat is diagnostic, not permission to steal a live lock.
- Proposed lock key: signed big-endian 64-bit integer from the first eight SHA-256 bytes of UTF-8 `nyc311:run:<dataset_id>`. Use the same session for the lock and repository/publication transactions; loss of that session prevents further writes until reacquisition and recovery validation. Migration locks use a different namespace. A heartbeat may use a separate short-lived connection but cannot publish or claim run ownership.
- A paused/retryable unfinished run must be resumed explicitly or administratively marked failed/abandoned before a new run for the dataset; no new public abandonment CLI is implied. Resume validates exact config/generation and retains checkpoints. A killed process releases the DB lock; the new holder may reclaim that interrupted run, recording a recovery event.

Allowed lifecycle transitions: pending→running; running→paused/failed/succeeded; paused→running; retryable failed→running after explicit resume validation. Succeeded and nonretryable failed are terminal. Reclaiming an interrupted running record creates a new attempt/recovery audit event while retaining its run ID/config/checkpoints. Only the publish transaction may transition to succeeded; each transition uses compare-and-swap under the dataset lock. Failure recording after rollback is separate from domain publication.

## Silver, Gold and quality/publication

Per-run reduction picks the greatest source_updated_at per source ID; equal timestamp + different normalized business content is `conflicting_source_versions` and aborts publication. Older-than-current source updates cannot overwrite a published row; record a stale-observation rejection and fail visibly for reconciliation review. Equal source timestamp + same content is replay; equal timestamp + different content is conflict, not invented history. Reconciliation without trustworthy source update metadata needs a separately approved full-cohort policy; do not silently drop this ordering safeguard.

A valid row fetched only because UTC-to-wall-time conversion needed a superset is durably marked `outside_scope` after exact UTC eligibility checking; it is neither published nor part of the quality denominator, and its selection reason remains auditable. Ambiguous/nonexistent wall times cannot be safely classified away at the boundary: quarantine/count them as invalid candidates rather than silently losing potentially selected records. Invalid required sort/update keys are source failures under the preflight/page rules, not a cursor that skips the row.

Silver logical row: source ID text PK; created/closed UTC and source wall-time values; nullable normalized agency/name, complaint type, status, borough, incident ZIP text; source_updated_at; raw_hash/reference; observed_at; published_run_id. Normalize text by trimming exterior whitespace, empty→null, agency uppercase, status case-insensitive comparison for tracked hashes; preserve display text. Keep borough/complaint values without inventing an enum. No descriptor/address/location/free text in silver/gold. Missing source identity/creation, invalid types, negative closure interval or ambiguous/nonexistent required event times quarantine the record; open requests may omit closure. Closed-without-closure retains the request for volume but is flagged metric-ineligible with a reason/count. Exact validation reasons are deterministic contract strings, not free-text exceptions.

Gold: one latest accumulating `fact_service_requests` per source ID; date (creation/closure roles), agency, complaint type, borough dimensions plus `dim_service_request_state`. Unknown dimension member for optional missing category. SCD2 natural key source ID; normalized tracked tuple `(status,agency,complaint_type)`, SHA-256 of canonical tuple JSON. Validity is accepted observation time, `[valid_from,valid_to)`, one current version, nonoverlapping ranges. Persist original observation time through crash resume. Ignore metadata-only/hash-untracked changes; a genuinely later A→B→A creates three observed versions. If observation time would not strictly exceed the current version boundary, reject the conflict rather than create zero/negative ranges. Never use source creation/closure or update time as fabricated state-validity boundaries. No states before first observation are claimed; no real transition evidence exists yet.

The fact points to the current observed state version. Historical state analysis uses explicit observation-time joins; current fact measures cannot reconstruct historical daily backlog. Duration metrics use eligible closed requests only, with denominators/missing counts, and measure recorded closure rather than verified fulfillment. Retain metric definitions in `context/project-discovery.md`.

Default quality threshold `0.05`: fail iff `invalid_count / evaluated_count > threshold`; exactly 5% passes; zero evaluated fails safely. Threshold must be in `[0,1]`; no infinity/NaN. Abort if ingestion is incomplete, source generation invalidated or any required segment failed. Bronze/quarantine survive; no silver/gold mutations before complete staged validation and gate PASS.

After PASS, acquire/reconfirm the dataset lock and execute silver publish → SCD2/dimensions/facts → successful watermark update → `ops.pipeline_runs` success in **one database transaction**. Rollback any failure and separately record failed status. Consumers use normal committed reads; a single SELECT sees no partial run, and multi-query reports use a repeatable-read transaction. Whole-run staging is durable and streamed; never hold a million rows in Python memory. A failure cannot advance successful watermarks or expose a partial silver/gold run.

## CLI and result semantics (targets only)

- `python -m nyc311_pipeline run --mode incremental [--max-records N] [--resume-run-id UUID]`
- `python -m nyc311_pipeline run --mode backfill --start <UTC-bound> --end <UTC-bound> [--max-records N] [--resume-run-id UUID]`
- Proposed explicit reconciliation target: `python -m nyc311_pipeline run --mode reconcile --start <UTC-bound> --end <UTC-bound> [--resume-run-id UUID]`; full cohort creation scan refreshes changed identities without deleting missing records.
- `python -m nyc311_pipeline health` checks DB connectivity/schema version, not public API availability.
- `python -m nyc311_pipeline report --run-id UUID` returns persisted status/phase/bounds/counts/checkpoint summaries/error category/published flag, without raw records.

Resume rejects changed config/mode/bounds. `max-records` is a positive per-invocation ingest cap; at the cap persist `paused` with category `record_cap`, no publish and no successful watermark advancement. Exhausting all segments permits validation/publication. Use a bounded date range for a complete small demo; capped extraction must not masquerade as a fully synchronized interval. Incremental's first lower bound/cohort and all tuning defaults come from validated environment config recorded in RunConfig. No implicit live API calls from health or tests.

`max-records` and resume ID are invocation controls excluded from the frozen scope hash; a later invocation may increase/remove the cap to finish the same scope. All source selection, normalization and generation policies remain frozen. `RunConfig` contains Scope, page_size, retry policy version/settings, quality threshold, timezone/tzdata version and contract version; `run_id`/wall-clock lifecycle fields are persisted separately. CLI output is one structured RunResult JSON object; diagnostics go to stderr with redacted categories.

Exit codes remain 0 successful invocation (including explicitly reported paused/capped state), 2 bad config/missing resume/run conflict, 3 API/transport/freshness/schema/order errors, 4 quality failure, 5 storage/migration/publication error. `RunResult` contains run_id, status, phase, ingest_complete, published, counts, retryable, category and checkpoint summaries; exit 0 alone does not assert published. Application metrics/logs must state `published` and `ingest_complete` explicitly.

## Reconciliation and known limitations

Propose daily update extraction and weekly full selected-cohort reconciliation in bounded creation-date partitions with separate checkpoints. Scheduler wiring remains Spec 07. Count comparisons alone cannot detect content changes or compensating additions/removals; compare identities/content during actual reconciliation. Do not infer deletion from one missing row or automatically tombstone gold. Record absence candidates only after complete sufficiently fresh repeated reconciliations and require reviewed source-deletion semantics before removal.

A full provider replace can invalidate generation mid-run and require a new run; overlap alone does not repair this. Retrying/reconciling improves eventual coverage but does not recover intermediate states missed between pulls. With no source snapshot token or verified immutable ordering guarantees, exact point-in-time extraction is not proven. If generation stability/freshness cannot support a bounded run, pause source implementation and review an official dated export for bounded backfill or another source-backed strategy; neither fixtures nor exports establish live CDC or genuine SCD2 transitions.

## Approval checklist and downstream handoff

- [ ] Nijat: timezone evidence/policy, scope/CLI, freshness fallback and acceptance of stated coverage limits.
- [ ] Nizami: raw/run association uniqueness, page receipts/CAS, ledger versus domain boundary, one publish transaction, state/fact relationship.
- [ ] Firuz: run lifecycle, dataset lock/recovery, paused/error handling and scheduler boundaries.
- [ ] Resolve Spec 05's old ops.run_history name in its future domain phase; approved foundation scope is unchanged.
- [ ] Evidence track: fresh preflight/repeatability and genuine same-request tracked changes remain open. Engineering acceptance must record actual human/cross-owner decisions separately; only the explicitly approved client exception may proceed before full Spec 01 completion.

Review-only Spec 03 handoff: `docs/spec03-ingestion-handoff.md`. This proposal intentionally exposes cross-owner decisions instead of freezing guessed interfaces.
