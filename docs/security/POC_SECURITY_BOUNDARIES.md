# POC Security Boundaries

## Implemented controls

- External registry, IDP, ownership, and target outputs are untrusted and strictly
  reconstructed/validated before canonical/domain use.
- Returned/requested UEN identity and query-free HTTPS registry provenance are bound.
- Upload names/type/size/signature/EOF are bounded; PDF bytes are used synchronously and
  are not retained or returned.
- Ownership graphs/percentages/provenance/counts/depth/paths are bounded; unsafe shapes
  cannot create definitive candidates.
- Target responses are validated immediately; only `NO_MATCH` permits writes and each
  failure stops later calls.
- Typed business review, technical failure, completion, and target recovery are separate.
- Demo routes fail closed by backend configuration; frontend visibility is not authority.
- API/UI/UAT export use minimized safe fields and fixed error projections; private
  fingerprints, provider bindings, raw payloads, PDF bytes, endpoints, and stacks are
  omitted.
- Mock/SANDBOX labeling is explicit; completion remains Mock/provisional.
- `.env`, `private/`, keys/certificates/tokens, build output, and dependencies are
  ignored; a current-worktree secret scan is configured.
- The credential-bearing PingFed/Postman material is quarantined under D-018 and was not
  opened, tested, copied, or sanitized during Phase 07.
- Demo lifecycle control records only safe process metadata under the fixed Git-ignored
  `.runtime/` path. `RUNNING` requires exactly one backend and one frontend record before
  any destructive stop action. Missing, duplicate, unknown, PID-reused, or ownership-
  mismatched state fails nonzero and is retained; port occupation is never ownership
  proof. Stop then validates PID, creation time, executable, project command markers,
  descendant listener, role, and port before terminating the exact owned tree. Unrelated
  Python/Node/port processes are not selected. Reset deletes no case, repository,
  sponsor, or arbitrary filesystem data; process-local state disappears only through a
  verified backend restart.

## Not implemented / not claimed

- Production RBAC, authenticated reviewer identity, maker-checker authorization, or
  Ready-for-Approval.
- Antivirus, sandboxing, CDR, complete PDF validation, real OCR security assessment, or
  approved KYC retention/deletion.
- Durable encrypted database/audit storage, storage-jurisdiction policy, backup, or
  recovery.
- Distributed locks/queue/outbox, multi-process idempotency, or exactly-once delivery.
- Real PingFed/token handling, GoldTier TLS 1.3 connectivity, mTLS/private CA, or least-
  privilege scope verification.
- Verified live ACRA authentication/TLS/contract, live hierarchy, or live provider
  monitoring.
- Production CORS/deployment hardening, WAF/rate limiting, SIEM, alerting, or incident
  response.
- Mature repository-history/archive/entropy secret scanning.

## Data handling for UAT

Use only files under `apps/backend/tests/fixtures/uat/` or equally fictional data. The
normal local IDP reads bounded text from the uploaded PDF; its filename and developer
scenario controls do not determine the assessment. Mock IDP remains gated developer
fault-injection tooling. Safe evidence/export views contain only minimized derived
values, comparison, ownership paths, readiness, and server-authored operation status;
they exclude PDF bytes, full raw text, payloads, credentials, and endpoint detail.

## Live-integration security gate

Before any real adapter work, reconcile authoritative contracts; receive credentials
through an approved mechanism; confirm rotation/revocation of quarantined material;
verify HTTPS/certificates/TLS 1.3 and any mTLS/private CA; define retention/RBAC/logging;
run adapter conformance, secret scan, security review, and authorized sandbox smoke.
