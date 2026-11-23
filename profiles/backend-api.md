# Backend/API Profile

Merge relevant rules into the project context; do not keep unused placeholders.

- Define API versioning, request/response/error conventions, pagination, filtering, and idempotency.
- Keep transport handlers thin and business rules in the owning application/domain layer.
- Validate external input and provider callbacks.
- Define transaction boundaries and concurrency behavior.
- Require forward-only migrations and migration tests.
- Add unit, persistence/integration, API, and contract tests as relevant.
- Document authentication, scopes/roles, resource authorization, and audit requirements.
- Define health/readiness checks, structured logs, metrics, and secret handling.
