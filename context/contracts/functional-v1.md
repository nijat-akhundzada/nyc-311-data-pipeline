# Functional pipeline engineering authorization — 2026-11-24

Nijat explicitly authorizes one integration branch implementing Specs 04/06 and
minimum 07/10 in this task, superseding their old dependency/one-spec-PR gates for
this iteration only. Ownership and human peer review remain; no Nizami/Firuz approval
is invented. ADR-001 stays PROPOSED for missing publisher/source evidence.

Reuse Bronze scope, API policy, receipts and checkpoints. The runner holds the
existing same-session dataset lock through ingestion, validation and publication.
The ingestion service gains only an optional external-lock argument; repository
mutation checks still enforce an actual lock. No competing run manager is added.

Validation uses pinned packaged tzdata and provisional America/New_York. Fold/gap
values are invalid, never guessed. UTC CLI windows query a conservative wall-time
superset (two-hour padding), followed by exact UTC eligibility; outside-scope valid
rows are audited/excluded from the denominator. Scope bounds/quality threshold,
fixture hash and timezone version are immutable in ops.run_settings. This settings
row is installed before any fetch; missing settings on resume fail safely.

Per-run reduction uses greatest source update per ID; conflicting equal-update
normalized content aborts. Invalid percentage counts distinct latest candidates;
exactly 5% passes, zero fails. All invalid candidates are quarantined with raw refs
and sorted reasons. Older-than-published updates/equal-update content conflicts
abort rather than overwrite. Malformed API envelopes/sort keys remain fail-fast
source errors under the existing client; they are not fabricated validation counts.

One transaction publishes Silver, Gold, run success and incremental watermark.
Observed-time SCD2 tracks normalized status/agency/complaint only; no source history
is reconstructed. The fact grain is one current request. Dates in the star are UTC
calendar dates; null categories use one unknown dimension member. A database
exclusion constraint prevents overlapping SCD2 intervals; no artificial microsecond
boundaries are invented. Identical replay creates no version. Changed state with
non-increasing observed time fails for review.

Incremental upper = run start minus 5 minutes; lower = successfully published
cohort watermark minus 48 hours. First incremental needs explicit initial lower;
backfill does not fabricate a successful update watermark. Watermarks never regress.
Capped/incomplete extraction never publishes. A retryable publish failure resumes
from staged/retained Bronze; a quality failure requires corrected data/new run.
The scheduler is a host-cron wrapper invoking the non-root Compose pipeline service;
installing a user's actual crontab is a deployment step, not silently performed.

Remaining source risks: freshness markers are proxies, not snapshot isolation;
complete incremental/deletion/replace coverage, publisher timezone, source preflight
and genuine SCD2 changes remain unverified. Synthetic tests prove mechanics only.
