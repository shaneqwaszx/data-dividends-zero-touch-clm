# Backend Guidance

These instructions extend the repository root guidance for files under `apps/backend`.

## Boundaries and conventions

- Keep FastAPI routes thin. Validation and HTTP projection belong at the API boundary;
  domain behavior belongs in services/domain owners; durable access belongs behind
  repository interfaces and adapters.
- Map external input through strict provider DTOs into canonical evidence before domain
  or target use. Keep connectors responsible for transport and decoding, not business
  policy. Project stable sanitized error codes/messages across API boundaries; never
  expose raw provider bodies or exception details.
- Extend existing ports, services, repositories, mappers, and composition. Do not add
  Mongo access to route handlers, duplicate ownership or authorization logic, bypass the
  target ledger, or silently fall back between providers or persistence modes.
- Preserve Pydantic/schema strictness, identity binding, Decimal ownership math, UTC
  ISO-8601 sourcing timestamps, revision/CAS behavior, insert-only create, update-only
  mutation, call stopping, and no-replay/anti-resurrection semantics where affected.
- Keep secrets backend-only. External HTTP uses HTTPS, certificate verification,
  bounded timeouts, safe redirects/errors, and only contract-authorized retry.

Use `external-provider-integration`, `persistence-schema-change`,
`integration-security-review`, or `architecture-change-review` when their trigger
applies.

## Verification

Select required checks from the root change-class matrix. From the repository root, the
standard backend commands are:

```powershell
.\.venv\Scripts\python.exe -m pytest apps\backend\tests
.\.venv\Scripts\python.exe -m ruff check apps\backend scripts tests
.\.venv\Scripts\python.exe -m mypy apps\backend\app
```

Start with the focused owning test. Run contract, lifecycle, security, POC regression,
or guarded physical Mongo checks only when the change class or affected boundary calls
for them. Physical Mongo tests must use the repository safety harness and a fresh
allowlisted disposable database, never `clm_poc`.
