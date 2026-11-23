# Code and testing standards

- Python >=3.12 with typing, clear modules, small functions, `ruff check`, `ruff format --check`, pytest. `pyproject.toml` and lockfile created by first implementing contributor.
- Python services use structured logging with run_id, phase, page, count; redact passwords and source free text.
- UTC-aware datetime internally; source timezone parsing and DST documented. SQL parameterization everywhere.
- One migration per coherent schema change; migration forwards/backwards where safe, never edit applied versions.
- Real idempotent SQL upserts and stage/publish transactions; no row-by-row loops for million-row bulk path.
- Fixtures test pagination boundary, 429/503, malformed JSON and fields, resume, duplicate replay, SCD2 state change, late updates, rollback and scheduler locking.
- Integration tests run against temporary Postgres service in CI, deterministic seed fixtures, not public API.
- Pre-commit hooks for ruff and hygiene. Atomic conventional commits: `feat(ingestion): ...`, `test(gold): ...`, `docs: ...`.
- Test outcomes and benchmark numbers must be measured. Never commit API secrets, huge dumps, or personal data.
