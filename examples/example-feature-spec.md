# Unit 04 — Owner-Scoped Projects API

- Status: Approved
- Owner: Backend

## Goal

Allow an authenticated account to create a project and retrieve only projects it owns through the versioned API.

## Current state

Authentication exists, but no project model, repository, use case, migration, or endpoints exist.

## Requirements

- Create a project with a required name and optional description.
- List the caller's projects newest first using cursor pagination.
- Retrieve one owned project by identifier.
- Return the shared not-found response for missing and non-owned identifiers.

## Boundaries and non-goals

- The Projects domain owns project records and rules.
- Routes authenticate, validate, call use cases, and map errors.
- Sharing, deletion, search, and UI are out of scope.

## Contracts and migrations

- Add request/response/error definitions to the public API contract.
- Add a forward migration with owner and creation-time indexes.
- Preserve the established identifier and timestamp conventions.

## Security and failure behavior

- Derive owner identity from the authenticated principal, never request input.
- Scope list and detail queries by owner.
- Do not reveal whether another account's identifier exists.

## Tests

- Creation and retrieval success.
- Invalid name rejection.
- Pagination order and cursor behavior.
- Anonymous rejection.
- Cross-account identifier swap returns not found.

## Dependencies

- Units 02 and 03.

## Verify when done

- [ ] Contract validation passes.
- [ ] Migration applies from the current head.
- [ ] Targeted and complete affected-package tests pass.
- [ ] No sharing or deletion behavior was introduced.
- [ ] Progress and documentation reflect the accepted implementation.
