# Multi-Tenant SaaS Profile

Merge these rules when tenant-owned data exists.

- Derive tenant identity from trusted authentication context.
- Scope every tenant-owned read and write.
- Validate that referenced resources belong to the same tenant.
- Never authorize solely from a client-supplied tenant identifier.
- Include tenant keys in relevant unique constraints and indexes.
- Test cross-tenant identifier swapping for every protected resource family.
- Define platform-admin access separately from tenant roles.
- Ensure logs, caches, jobs, files, exports, and analytics preserve isolation.
