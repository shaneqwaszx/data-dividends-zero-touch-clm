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
# Phase 12 durable-persistence boundary

Mongo mode persists only bounded structured case evidence and safe workflow/target
checkpoints. It excludes raw uploaded bytes, full extracted bodies, raw external
payloads, credentials, connection strings, provider objects, stack traces, and browser
state. Mongo unavailability, unknown schema versions, and malformed envelopes fail
closed without fallback or destructive repair. No TTL/purge is configured because
retention and deletion remain sponsor-dependent under Q-015. This is not production KYC
storage, a regulatory audit repository, or a distributed exactly-once system.

The Mongo document key is untrusted storage metadata: `_id` must be a canonical UUID
string equal to the envelope `case_id` on startup and every read path. A mismatch stops
before API/browser projection and is never normalized, rewritten, or deleted. Restart
classification of an interrupted current document retains no bytes, marks only that
record re-upload-required, and returns automation to bounded Document input. Unrelated
intake cannot bypass the targeted retry requirement, and completed evidence is not
reprocessed.

# Phase 13 authentication and authorization boundary

All `/api` operations except login now require a server-side process-local session.
Passwords are represented only by configured per-user scrypt hashes; plaintext is never
stored, logged, returned, written by the hash generator, or embedded in seed automation.
Unknown-user and wrong-password attempts execute the same verification path and return
the same bounded error. The opaque browser token exists only in a host-only HttpOnly
`SameSite=Strict` `/api` cookie; the server stores its SHA-256 digest, absolute expiry,
actor, and CSRF value. Login rotates the profile's old session and logout revokes it.

Unsafe requests require the session-bound CSRF header and same-origin browser metadata.
Central route classification authorizes every case route before its handler. Canonical
persisted `team_id`, never a caller header/query/browser filter, controls access; absent
and inaccessible cases return one fixed 404 to limit enumeration. Team ownership is
immutable in memory and Mongo. Browser auth state and CSRF remain memory-only and any
401 unmounts the sensitive workspace.

This POC does not provide rate limiting, lockout, MFA, password recovery, a distributed
session store, production CORS/reverse-proxy trust, enterprise IdP/SSO, separation of
duties, or production identity governance. Cookie Secure defaults on in production and
an explicit insecure production setting fails startup. Deployment behind a proxy needs
a separately reviewed same-origin/TLS design.
