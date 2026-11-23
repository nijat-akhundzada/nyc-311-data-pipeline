# NYC 311 Data Engineering Pipeline

**Course:** Data Engineering, Fall 2026 · **Submission deadline:** 26 November 2026 · **Team:** Nijat Akhundzadeh (lead / member 1), Nizami (member 2), Firuz (member 3).

> **Status: specification-only scaffold.** No pipeline implementation, tests, data, migrations, or benchmark results are claimed complete. This repository is a human-reviewed plan for contributors and their AI coding agents.

## Objective
Build a reliable, dockerized Python + PostgreSQL pipeline consuming one public API, with resumable pagination, bronze/silver/gold, quarantine and quality gating, idempotent incremental and backfill modes, SCD2 in gold, ~1 million source records, scheduled runs, analytics and demonstrated recovery/performance.

**Proposed API:** NYC Open Data, 311 Service Requests 2020-present, Socrata dataset `erm2-nwe9` (https://dev.socrata.com/foundry/data.cityofnewyork.us/erm2-nwe9). Confirm endpoint, field names, pagination and quotas in Spec 01 before coding. Never fabricate or replicate records to meet the 1M requirement.

## Start here
Current discovery evidence: `docs/source-smoke-test.md`. Bounded parallel-work recommendations and remaining gates: `context/implementation-readiness.md`. ADR-001 remains proposed; these documents do not claim implementation readiness for the full pipeline.

1. Lead reviews `context/decisions/ADR-001-source-and-contracts.md` and accepts or changes it **before feature coding**.
2. Read `AGENTS.md`, `context/architecture.md`, `context/contracts/README.md`, and `context/specs/00-build-plan.md`.
3. Allocate issues using `context/team-workflow.md`; each member copies their prompt in `prompts/team/` into a coding agent **one approved spec at a time**.
4. Create feature branches; implement, run checks, commit atomically, push and open **draft PRs**; lead reviews and merges after CI passes. AI must not bypass review.
5. Read `docs/runbook.md` and `docs/submission-checklist.md` for the final demonstration and submission artifacts.

## Anticipated execution (after implementation)
Commands in `docs/runbook.md` are **target interface contracts**, not working commands yet. The codebase begins with directories and documentation, not functioning CLI or Compose services.

## Assignment mapping
See `context/requirements-traceability.md` and `docs/submission-checklist.md` for evidence requirements. Final README must be updated with **real** setup commands, data model, quality thresholds, idempotency, Git exercises, demonstrated results and the names of all members. Do not claim finished features based on specifications alone.

## Source and academic integrity
Assignment: `docs/source-assignment.pdf` (copy of teacher-provided instructions). Students must understand every committed line. No cross-team code sharing; no main force pushes. AI assistance is permitted for learning/debugging, with human-authored review and explanation.
