# Phase 03 Integration Security Review

## Result

**PASS for the credential-free, synthetic, local Phase 03 POC boundary.** The Phase 03
remediation closes the active upload, provenance, and failure-terminalization findings
identified by the independent quality gate. No active in-scope security defect remains.
The accepted Q-013/Q-014 limitations below still prohibit real documents, real KYC/PII,
or production exposure.

## Reviewed boundary

This review traced the current working tree from browser upload through API validation,
bounded body reading, provider selection, provider input/output validation, canonical
comparison, process-local persistence, API/browser projection, field review, and safe
failure retrieval. It also rechecked the unchanged ACRA/GoldTier mock boundaries,
secret controls, mock/live labeling, and Phase 03 scope exclusions.

## Trust-boundary results

1. The generic document API accepts only the provider-neutral upload contract. Mock
   scenario selection exists only on the dedicated `/api/demo/.../documents` endpoint
   and in `MockIdpDemoControl`/`MockIdpProvider`; it is absent from generic input,
   provider, service, domain, and response contracts.
2. The display name is a bounded, display-only `.pdf` label. Path separators, traversal
   syntax, control characters, unsafe extensions, and overlong names are rejected before
   provider invocation. No filesystem path is derived from it and no temporary file is
   created.
3. Declared `Content-Length` and actual streamed bytes are independently bounded. Each
   ASGI chunk is compared with remaining capacity before `body.extend`, so an oversized
   chunk is not first copied into the application buffer. Missing or deceptive declared
   lengths cannot bypass the streamed limit.
4. The accepted body is used only for the synchronous provider call. It is marked
   `repr=False` at the provider boundary and never enters the repository, events, API
   response, browser model, or normal logs. Only synthetic PDF fixtures are authorized.
5. Provider metadata and source references use reusable provider-neutral types. Values
   are trimmed, nonempty after trimming, control-free, and length-bounded. Blank,
   newline, embedded-control, and overlong provenance is treated as malformed provider
   output and terminalizes through a fixed safe error.
6. Provider output remains untrusted until strict Pydantic validation proves the exact
   provisional four-field profile, unique field keys, bounded values, valid confidence,
   bounded page/reference provenance, and no unknown properties.
7. Known invalid canonical comparison values are checked before bounded retained field
   models are built. The reproduced 513-character legal-name input becomes a
   retrievable `FAILED / DOCUMENT_COMPARISON_INPUT_INVALID` document.
8. Every recoverable exception after upload acceptance is inside the trusted processing
   boundary: processing-start persistence, provider metadata/invocation/result,
   field/provenance/model construction, normalization/comparison, clock use, and
   updates through `REVIEW_REQUIRED`. Transactional copy-before-save updates preserve
   the last stored record for recovery. Failure records contain exactly one safe
   terminal event and no underlying exception text.
9. Document failure cannot change the parent onboarding case, reach `REVIEWED`, or call
   GoldTier. List/get/review operations enforce the route case as owner.
10. Review requests use the domain field/decision enums, forbid extra properties, and
    bound correction/note text. Validation errors use fixed document-safe messages and
    do not echo submitted document field values or notes.
11. Events contain generated IDs, state, outcome, fixed code/message, optional field
    key, and UTC timestamps. They exclude filename, PDF bytes/text, provider raw output,
    extracted/canonical/corrected values, review notes, credentials, headers, endpoints,
    and private exception text.

## Active findings

| Severity | Finding |
|---|---|
| CRITICAL | None |
| HIGH | None |
| MEDIUM | None |
| LOW | None |

## Quality-gate security remediations verified

| Finding | Security result |
|---|---|
| P03-QG-001 post-acceptance false nonterminal state | CLOSED: adversarial comparison, 513-character canonical input, clock, and recoverable update failures end as retrievable sanitized `FAILED` records with one terminal event. |
| P03-QG-002 Mock type leakage | CLOSED: Mock scenario control is segregated from provider-neutral business/domain/API contracts. |
| P03-QG-003 unsafe provider provenance | CLOSED: conservative reusable validation rejects blank, whitespace, control, newline, and overlong values. |
| P03-QG-004 append-before-limit-check | CLOSED: remaining capacity is enforced before buffer extension; provider non-invocation is tested. |
| P03-QG-005 loose review input | CLOSED: typed enums, bounded text, forbidden extras, and safe validation projection are tested. |

## Accepted Phase 03 security limitations

### HIGH if deployed: unauthenticated review mutation (Q-014)

The local API has no authentication, authorization, verified reviewer identity, or
maker-checker separation. `REVIEWED` means local document field review only and is not
customer, compliance, GoldTier, or Ready-for-Approval status. Q-014 must define roles,
permissions, separation of duties, and durable audit requirements.

### HIGH if real documents are accepted: narrow PDF controls (Q-013)

The boundary performs size, media type, name, signature, and terminal EOF checks. It is
not antivirus, sandboxed parsing, CDR, active-content removal, polyglot detection, or
decompression-bomb protection. Q-013 must define approved document types, threat model,
storage, malware controls, retention/deletion, access, encryption, jurisdiction, and
incident handling before real documents or customer data are accepted.

### MEDIUM if scaled: synchronous process-local design

The body is bounded but buffered synchronously. There is no gateway limit, rate limit,
concurrency budget, queue, retry worker, object storage, database, or durable audit
store. These remain explicitly outside Phase 03 and require a separately authorized
production design.

## Verification evidence

- Backend suite: **167 passed**.
- Focused Phase 03 remediation/provider/API contract suite: **67 passed**.
- Canonical onboarding plus document/adversarial scenario subset: **66 passed**.
- Contract suite: **23 passed**.
- Repository unittest discovery: **33 passed**.
- Ruff: PASS.
- strict mypy: PASS across 32 application source files.
- Frontend typecheck: PASS; frontend tests: **11 passed**; production build: PASS.
- Secret scanner: PASS; secret-scanner tests included in the 33-test repository suite.
- `pip check`: PASS; `npm ls --all`: exit 0 with platform/feature optional dependencies
  reported as optional only.
- GoldTier example validator: unchanged expected result, 19 valid, 19 invalid and
  quarantined, 48 not validated; validator regression tests PASS.
- `git diff --check`, cached diff check, and untracked whitespace check: PASS.

No PDF parser, OCR/cloud IDP SDK, VLM, credential, PingFed, real ACRA, real GoldTier,
UBO, hierarchy, worker, queue, or database capability was introduced.

## Remaining sponsor dependencies

- Q-003: final document types and exact IDP field profile.
- Q-005: validation ownership and sequencing in the wider onboarding workflow.
- Q-013: privacy, storage, retention/deletion, fixture policy, and production PDF
  security controls.
- Q-014: confidence policy, review roles, authentication/authorization,
  maker-checker separation, and audit retention.
- Q-012 still blocks live ACRA verification. GoldTier/PingFed contract and sandbox
  dependencies still block real GoldTier readiness.
