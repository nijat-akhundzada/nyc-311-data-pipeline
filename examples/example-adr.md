# ADR 001 — Project ownership is single-account in V1

- Status: Accepted
- Date: 2026-01-01
- Related specs: Unit 04

## Context

The first release needs private projects. Collaboration is a possible later feature, but its invitation, role, and revocation rules are not approved.

## Decision

Every V1 project has exactly one owning account. Only that account may read or mutate it. Authorization derives the account from trusted authentication context.

## Consequences

- The initial data and authorization model remains simple and testable.
- Collaboration cannot be added as a flag; it requires a later approved membership model and migration.

## Rejected alternatives

- Adding speculative collaborators now: rejected because access semantics are undefined.
- Storing an owner identifier supplied by the client: rejected because it creates an authorization vulnerability.

## Migration and compatibility

The initial projects migration requires a non-null owner identifier and an owner-scoped index.
