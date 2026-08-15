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

## Common safe failures

- `422`: malformed UEN/request, PDF metadata/body, unsupported action, or field input.
- `404`: missing case/document/ownership record or disabled demo boundary.
- `409`: stale version/evidence, conflicting transition, or duplicate in-flight owner.
- `503`: sanitized provider/target/infrastructure failure with a retrievable case where
  accepted.

No API response should contain credentials, authorization headers, raw documents,
provider payloads, internal fingerprints, or stack traces.
