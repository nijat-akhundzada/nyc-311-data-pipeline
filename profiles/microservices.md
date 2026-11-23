# Microservices Profile

Use only when multiple deployable services are justified.

- Give every domain and data set exactly one owning service.
- Never access another service's database directly.
- Use synchronous calls only when an immediate response is required.
- Use durable asynchronous messaging for side effects and eventual consistency.
- Define shared HTTP/event contracts before changing integrations.
- Use transactional outbox for business-event publication when atomicity matters.
- Make consumers idempotent and test duplicate delivery/replay.
- Define timeouts, retries, circuit behavior, dead letters, reconciliation, and observability.
- Preserve trace/correlation context across boundaries.
- Test contracts independently and critical journeys across deployed services.
