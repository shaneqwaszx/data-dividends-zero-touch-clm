# Phase 07 Integration Security Review — Final Lifecycle Remediation

**Review date:** 2026-08-15

**Result:** PASS WITH ACCEPTED POC LIMITATIONS

**Scope:** implementation-side rerun after the independent Phase 07 Quality Gate
**FAIL**. This report does not replace that gate or claim an independent PASS.

## Findings

No current Critical or High implementation-side security finding remains after the
bounded P07-QG-001 remediation.

### P07-QG-001 — implementation-side remediated; independent re-gate required

The trust boundary is the fixed Git-ignored `.runtime/demo-processes.json`. It contains
only schema/session/status, role, launcher/listener PID and UTC creation time,
executable, fixed project command/working-directory markers, and local port. It contains
no credential, token, KYC/PII, PDF, provider payload, case, target payload, or business
evidence. Runtime/state/temp paths remain fixed normal non-reparse paths beneath the
repository.

State structure is now validated before any destructive Stop action. `RUNNING` requires
exactly one backend and one frontend record. Missing, duplicate, differently cased, or
unknown roles return `DEMO_RUNTIME_STATE_INCOMPLETE`, retain the metadata, and terminate
nothing. A port listener is never used to guess the missing owner. `STARTING` has its own
narrow partial schema (backend only or backend plus frontend) and cannot be interpreted
as `RUNNING`.

Only after structural completeness does Stop validate both process identities: PID,
creation time, executable, code-owned role command markers, descendant listener, and
port. All checks complete before any tree is selected. Termination remains
`taskkill /PID <validated-root> /T /F`; no window title, executable-name kill, or broad
port-owner kill is used. Both required ports must be free before complete-session state
deletion and success. Ownership mismatch or unexpected remaining port fails nonzero and
retains recovery evidence.

Reset propagates Stop failure. Missing frontend and missing backend Reset tests each
returned nonzero, retained the same session, left both healthy processes untouched, and
did not launch a replacement. Exact manual missing-role reproductions returned exit `1`
with both endpoints still `200`; restoring the original metadata permitted verified
exact-tree cleanup.

### Preserved boundaries

P07-QG-002 blocker presentation and P07-QG-003 `APP_NAME` consistency remain closed;
launcher dependency/version preflight remains active. No ACRA, IDP, ownership,
GoldTier, PingFed, evidence-export, UAT, or browser data boundary changed. UAT export
remains demo-gated/case-bound and excludes PDF bytes, raw payloads, endpoints,
authorization material, credentials, private fingerprints, and exception details.
Mock/SANDBOX/live and Mock-submission claim boundaries are unchanged. The quarantined
authentication collection was not opened, copied, tested, or sanitized.

## Verification

- Windows lifecycle: 13 passed; repository discovery: 71 passed.
- Exact missing frontend/backend Stop: nonzero, metadata/session retained, both services
  untouched, no session-wide success; exact metadata cleanup passed.
- Missing frontend/backend Reset: nonzero, same state, no replacement start.
- Normal Start/Stop/Reset, case `200 -> 404`, unrelated Python/Node/cmd survival,
  occupied-port survival, ownership mismatch, stale PIDs, and repeated lifecycle passed.
- Backend 494; focused Phase 01–07: 28 / 81 / 59 / 77 / 61 / 179 / 16.
- Contracts 44; explicit UAT smoke 4; frontend typecheck/35 tests/build/npm tree passed.
- Ruff, strict mypy, `pip check`, secret tests/scanner, tracked-private check, GoldTier
  validator/classification, PowerShell parse, whitespace, and final runtime audit passed.

## Accepted limitations and sponsor dependencies

Accepted POC limitations remain: process-local state, no production RBAC/durable audit/
queue/distributed locking, no production supervisor/service installation, no production
CORS/monitoring, and no live ACRA/hierarchy/GoldTier/PingFed/IDP/ownership connector.
Q-001–Q-014 and D-018/D-023–D-026 remain open/applicable. This implementation-side PASS
WITH ACCEPTED POC LIMITATIONS is ready for, but does not replace, the final independent
Phase 07 closure gate.
