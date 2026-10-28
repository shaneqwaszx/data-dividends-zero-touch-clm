# API Handoff

All routes are local POC APIs. Errors use stable public codes/messages where modeled;
raw provider bodies and exception details are not returned. UUID case IDs are
server-created. The normal frontend uses the Vite same-origin proxy; cross-origin CORS
deployment is not configured.

## System/read APIs

| Method/path | Purpose | Key response / behavior |
|---|---|---|
| `GET /health` | Process health | `ok`, service, non-secret app environment |
| `GET /api/system/execution-profile` | Safe connector labels/policy defaults | ACRA `MOCK` or `SANDBOX`; IDP/Ownership/GoldTier `MOCK`; no endpoint or secret |
| `GET /api/clm/zero-touch/cases/{case_id}` | Authoritative sponsor summary/timeline | Idempotent read; safe 404 if absent |

## Product APIs — primary zero-touch flow

| Method/path | Purpose | Input | Idempotency / safe errors |
|---|---|---|---|
| `POST /api/clm/zero-touch/cases` | Create registry-backed journey | JSON `{ "uen": "202400001A" }` | Creates one process-local case; registry failure is retained safely |
| `POST /api/clm/zero-touch/cases/{case_id}/documents` | Attach required PDF | raw `application/pdf`; `X-Document-Name` | Rejects invalid name/type/size/structure before progression |
| `POST /api/clm/zero-touch/cases/{case_id}/start` | Start or re-enter safe work | none | Duplicate/terminal calls return current checkpoint; target work is not replayed |
| `POST /api/clm/zero-touch/cases/{case_id}/resume` | Explicitly resume/reconcile | none | Same authority as Start; used for `RECOVERY_PENDING` finalization only |

The React primary path creates and attaches in one Start interaction; the backend keeps
these two inputs separate so rejected PDFs do not create false running state.

Every accepted Start creates a new CLM case identity and preserves that case's own
document, reconciliation, and activity history. Customer identity is separate: an
exact GoldTier match may reuse the existing target ID and skip Shell/new-policy work,
while an ambiguous match blocks Shell, target binding, and Amend without discarding the
new case or preventing bounded document intake. A no-match case continues through ACRA
and the new-customer path.

For an exact reused target, reconciliation labels the retained canonical baseline as
`EXISTING_CASE`; it does not claim that ACRA was called again for the new case. The new
case owns its own document and reconciliation records even when the retained target ID
is shared with an earlier completed case.

The Onboarded view requests exactly the accessible `COMPLETED` cases and does not apply
a hidden frontend status filter. It is a completed-case POC projection, not a deduped
client master. A future customer-centric view may group cases by an authoritative
target customer ID, but that projection is deliberately not implemented here.

## Review API

`POST /api/clm/zero-touch/cases/{case_id}/exceptions/{exception_id}/resolve`

Request:

```json
{
  "action": "KEEP_REGISTRY_VALUE",
  "expected_automation_version": 7,
  "evidence_version": "bounded-server-value"
}
```

Only an action advertised by the current server exception is accepted. Case,
exception, automation version, evidence version, and a server-only current-authority
fingerprint are checked under the case lock. Stale/cross-case/forged requests return a
safe conflict and cannot increment interventions, resume, or call the target.

## Demo/Test APIs — non-production and fail closed

These require `DEMO_CONTROLS_ENABLED=true`; otherwise they return
`404 / DEMO_CONTROLS_DISABLED`.

| Method/path | Purpose |
|---|---|
| `POST /api/demo/clm/zero-touch/cases` | Create an integrated synthetic preset; body adds `scenario` |
| `POST /api/demo/clm/zero-touch/cases/{case_id}/documents` | Attach PDF using the preset's Mock IDP/ownership adapters |
| `GET /api/demo/clm/zero-touch/cases/{case_id}/uat-evidence` | Export a whitelisted synthetic UAT JSON summary |
| `GET /api/onboarding/mock-scenarios` | Historical Phase 01 scenario discovery/profile |
| `POST /api/demo/onboarding/cases/{case_id}/documents` | Historical manual IDP scenario |
| `POST /api/demo/onboarding/cases/{case_id}/ownership/load` | Historical manual ownership scenario |

The evidence export requires a case registered through the integrated demo boundary;
normal cases cannot be mislabeled as a preset.

## Historical/manual APIs

The `/api/onboarding/...` document/review/ownership routes and `/api/clm/cases/...`
staged readiness/submission routes remain for regression and development diagnostics.
They are not the sponsor's primary walkthrough. See generated `/docs` for their exact
schemas; keep them under **Legacy manual diagnostics** in the browser.

`GET /api/onboarding/cases/{case_id}/document-digests` (D-095, case-scoped like the document
list) returns `[{document_id, document_version, content_sha256}]`: the SHA-256 the backend
computed from each document's uploaded bytes at upload (stored on the document record, case
snapshot schema 16; `null` for records stored earlier). It exists only so the AI Assistant can
recognise approved synthetic fixtures before any external inference; the browser does not use
it, and the digest is not part of any other document response. No document content is
returned.

## Common safe failures

- `422`: malformed UEN/request, PDF metadata/body, unsupported action, or field input.
- `404`: missing case/document/ownership record or disabled demo boundary.
- `409`: stale version/evidence, conflicting transition, or duplicate in-flight owner.
- `503`: sanitized provider/target/infrastructure failure with a retrievable case where
  accepted.

No API response should contain credentials, authorization headers, raw documents,
provider payloads, internal fingerprints, or stack traces.
