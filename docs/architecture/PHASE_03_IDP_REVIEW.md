# Phase 03 IDP Document Processing and Human Review

## Status and scope

Phase 03 adds a document sub-workflow to an existing onboarding case:

`bounded PDF -> DocumentProcessingService -> IdpProvider -> validated field candidates
-> canonical comparison -> field review -> reviewed document`

The profile and rules are project-defined and provisional because Q-003 is unresolved.
They are not Delta Capita-approved. The sub-workflow does not rewrite the canonical
entity, change the parent onboarding state, call ACRA or GoldTier, or establish
Ready-for-Approval.

## Components and boundaries

- `DocumentProcessingService` validates uploads and provider output, compares fields,
  applies field decisions, records safe events, and terminalizes failures.
- `IdpProvider` is the replaceable provider protocol. Business/review code has no AWS,
  Azure, OCR, VLM, or LLM dependency.
- `IdpDocumentInput`, provider metadata, extraction results, provenance, and
  `DocumentProcessingService` are provider-neutral. The generic contract has no Mock
  scenario. Provider metadata supplies a bounded provider label and one of the generic
  environments `MOCK`, `LOCAL`, `SANDBOX`, or `LIVE`.
- `MockIdpProvider` is the deterministic, credential-free, network-free CI default. Its
  values are synthetic and are not derived from PDF text. Scenario selection is
  confined to `MockIdpDemoControl` and the dedicated demo API boundary.
- `IdpSourceResult` is the strict untrusted-provider contract. It requires each of the
  four provisional fields exactly once with independent confidence and provenance.
- `DocumentProcessingRecord` retains safe metadata, field candidates, comparisons,
  review results, events, and timestamps in a process-local repository. It never
  retains PDF bytes, a filesystem path, raw text, or the raw provider payload.

No text-native parser was added. Scanned PDFs and OCR are unsupported.

## Upload trust boundary

`POST /api/onboarding/cases/{case_id}/documents` accepts an `application/pdf` body and
bounded `X-Document-Name` using the composed provider. The separate
`POST /api/demo/onboarding/cases/{case_id}/documents` endpoint additionally accepts a
fixed `X-Mock-IDP-Scenario` for deterministic local demonstrations. Before provider
invocation:

- the parent case must exist;
- media type must be exactly PDF;
- the display name must be bounded ASCII text ending in `.pdf`, with no control or
  path syntax;
- declared and streamed size must remain within the configured limit (5 MiB default,
  20 MiB configuration cap); each streamed chunk is checked against remaining capacity
  before it is appended to the in-memory buffer;
- content must be nonempty, start with `%PDF-`, and end with `%%EOF` after whitespace.

The name is retained only as a display label and never passed to filesystem APIs.
Bytes are kept only for the synchronous call and the provider input excludes them from
its representation. Normal logs/events contain no filename, PDF, extracted value,
corrected value, review note, or exception text.

These are narrow POC checks, not full PDF parsing, antivirus, CDR, polyglot detection,
decompression-bomb protection, or a production upload threat model. Only synthetic
documents are permitted.

## Field candidates and comparison

The profile contains registration number, legal entity name, registered address, and
country of incorporation. Each candidate retains the original suggestion, normalized
value, confidence in `[0, 1]`, provider/page/source provenance, canonical value,
comparison status, and separate review state/value/time/note.

Comparison uses deterministic trim, whitespace collapse, uppercase case
normalization, UEN-specific removal of all whitespace, and conservative address
joining. Results are
`MATCH`, `MISMATCH`, `MISSING_FROM_DOCUMENT`, `MISSING_FROM_REGISTRY`, or
`NOT_COMPARABLE`. No fuzzy or AI matching occurs and neither source overwrites the
other. The default `0.85` attention threshold is configurable and provisional; every
field still requires an explicit human decision.

## Human review lifecycle

Document states are:

`UPLOADED -> PROCESSING -> REVIEW_REQUIRED -> REVIEWED`

and processing failures terminalize as `FAILED`. A reviewer submits one field at a
time to `POST .../documents/{document_id}/reviews`:

- `ACCEPTED` retains the IDP suggestion as the reviewed value;
- `REJECTED` records no reviewed value; or
- `CORRECTED` requires and retains a separate bounded corrected value.

The original extraction is immutable. Accepting a missing suggestion is invalid.
Identical decision retries are idempotent and conflicting second decisions return a
safe conflict. Only completion of all four field decisions produces `REVIEWED`.
The API request model uses the domain field and decision enums directly, forbids extra
properties, and bounds corrected values and review notes.

The local POC has no authenticated reviewer identity, authorization, maker-checker
control, or durable audit store. `REVIEWED` means only that this document's provisional
fields were decided; it does not mean customer/compliance approval.

## API and frontend

- `POST /api/onboarding/cases/{case_id}/documents`
- `POST /api/demo/onboarding/cases/{case_id}/documents` (Mock scenario control only)
- `GET /api/onboarding/cases/{case_id}/documents`
- `GET /api/onboarding/cases/{case_id}/documents/{document_id}`
- `POST /api/onboarding/cases/{case_id}/documents/{document_id}/reviews`

The React UI can create or reopen a case, list/select documents, upload a PDF, choose a
synthetic Mock IDP scenario, inspect confidence/provenance/comparison, and accept,
reject, or correct each field. Low confidence and non-matches are visually highlighted.
Original suggestions and human-reviewed values remain separately visible.

## Failure and isolation invariants

- Invalid inputs stop before IDP processing.
- Every failure after the upload has been accepted and persisted, including provider
  invocation/result validation, comparison-input validation, field/provenance/model
  construction, clocks, and document updates, is contained by the trusted processing
  boundary. A recoverable persistence seam records one retrievable terminal `FAILED`
  document with one fixed sanitized failure event.
- Candidate state changes are saved transactionally from a copy. If an update fails,
  recovery starts from the last successfully persisted record rather than exposing a
  false `PROCESSING` mutation.
- Known invalid retained comparison input is rejected before bounded field models are
  constructed. Unexpected exception text is never projected into the API or events.
- Failure never changes or corrupts the parent case, never marks the document reviewed,
  and performs no downstream target operation.
- List/get/review operations enforce the route case as document owner.
- Events use generated identifiers, fixed codes/messages, statuses, outcomes, and UTC
  timestamps only.

## Limitations and sponsor dependencies

- Q-003: approve the actual document types and exact field profile.
- Q-005: confirm rule ownership and document sequencing in the wider workflow.
- Q-013: approve privacy, fixtures, retention/deletion, storage, access, and production
  PDF security controls.
- Q-014: approve confidence policy, review roles, authentication, separation of duties,
  and audit retention.
- Q-012 still blocks live ACRA verification; Q-008 and sandbox dependencies block real
  GoldTier integration.

There is no database, object storage, retry/worker, malware scanner, real IDP/OCR,
authenticated reviewer, real document fixture, or Phase 04 capability.
