# Phase 03 Planner Handoff - IDP Document Processing and Human Review

## Goal

Build the first case-linked PDF, IDP-provider, field-comparison, and human-review
sub-workflow without changing the accepted onboarding workflow or beginning Phase 04:

`existing case -> bounded transient PDF -> IdpProvider -> provisional field candidates
-> deterministic canonical comparison -> field review -> reviewed document result`

The workflow must preserve both the original IDP suggestion and any human-reviewed
value. IDP output must never overwrite the canonical legal entity or impersonate human,
compliance, four-eye, or GoldTier approval.

## Authority and provisional boundary

- This handoff implements the detailed Phase 03 scope supplied on 2026-08-10.
- Q-003 remains unresolved. The document profile, four fields, comparison rules,
  confidence threshold, and mock scenarios are PROJECT-DEFINED / PROVISIONAL and must
  not be presented as Delta Capita-approved.
- Q-005, Q-013, and Q-014 remain unresolved for validation ownership, privacy/retention,
  production upload controls, confidence policy, and authenticated review.
- Real ACRA verification remains blocked by Q-012. GoldTier remains mock-only.

## Implementation scope

### Document domain

- Retain generated document/case/correlation IDs, a validated display name, PDF media
  type, provisional corporate profile, processing state, created/processed/reviewed UTC
  timestamps, field candidates, safe events, and sanitized errors.
- Use a document sub-workflow such as `UPLOADED -> PROCESSING -> REVIEW_REQUIRED ->
  REVIEWED`, with `FAILED` terminal on processing failure.
- Keep documents isolated by case and expose list/get operations.

### Provisional field profile

Use only:

- `registration_number`;
- `legal_name`;
- `registered_address`; and
- `country_of_incorporation`.

Each field retains the original extracted value, deterministic normalized value,
independent confidence `[0, 1]`, source/page provenance, canonical comparison status,
field review status, optional corrected/reviewed value, review timestamp, and a bounded
safe optional note.

Create `docs/contracts/IDP_FIELD_PROFILE.md` and explicitly label all profile fields,
thresholds, and rules provisional.

### IDP provider boundary

- Define `IdpProvider`; business and review logic must not depend on a cloud vendor,
  OCR library, VLM, or LLM.
- Implement deterministic, credential-free, network-free `MockIdpProvider` as default.
- Support exactly the synthetic scenarios required for Phase 03:
  `ALL_FIELDS_MATCH`, `FIELD_MISMATCH`, `LOW_CONFIDENCE`, `MISSING_FIELD`, and
  `PROCESSOR_FAILURE`.
- Validate untrusted provider output before comparison or persistence. Do not implement
  a real/local text parser unless it remains clearly optional; no OCR dependency is
  required for acceptance.

### Upload safety

- Accept only `application/pdf`, a bounded safe `.pdf` display name, nonempty content,
  configured size, `%PDF-` signature, and terminal `%%EOF` before provider processing.
- Check metadata before streaming and actual bytes while streaming. Never use the name
  as a filesystem path, log the PDF/raw text, retain binary content, or commit a real
  sponsor/customer document.
- Keep request bytes in memory only. The narrow structure checks are not malware/CDR or
  production PDF security and must be documented as such.

### Confidence and deterministic comparison

- Keep the configurable development threshold (default `0.85`) explicitly provisional.
- Low-confidence fields require review. High confidence never approves a customer.
- Compare each provisional document field with the existing canonical entity using
  conservative deterministic normalization only: trim/collapse whitespace, uppercase
  case-insensitive corporate text/country/UEN, and a stable canonical address join.
- Produce `MATCH`, `MISMATCH`, `MISSING_FROM_DOCUMENT`, `MISSING_FROM_REGISTRY`, or
  `NOT_COMPARABLE`. Never fuzzy-match or overwrite either source.

### Human review

- Review one field per typed request with `ACCEPTED`, `REJECTED`, or `CORRECTED`.
- `CORRECTED` requires a bounded nonblank corrected value; acceptance of a missing
  suggestion is invalid. Preserve original extraction and normalized value after every
  decision.
- Store a human-confirmed value only for `ACCEPTED`/`CORRECTED`; a rejected field has no
  reviewed value. Accept an optional bounded safe note without copying it into audit
  events.
- Make identical retries idempotent and reject conflicting second decisions.
- A document reaches `REVIEWED` only when every field has a final review status;
  otherwise it remains `REVIEW_REQUIRED`. This local control has no authenticated
  reviewer identity and is not Ready-for-Approval.

### API and frontend

- Provide create/list/get document endpoints below an existing onboarding case and a
  field-review endpoint at `/reviews` (or an equivalent typed design).
- Add frontend support to create or reopen a case, list its documents, upload PDF,
  select a visibly synthetic Mock IDP scenario, inspect field candidates/confidence/
  provenance/comparison, accept/reject/correct each field, and see completion state.
- Visually distinguish low confidence, mismatch/missing comparison, pending review,
  reviewed values, Mock IDP output, and unauthenticated local decisions.
- Do not redesign the overall UI or expose paths, configuration, credentials, raw PDF,
  raw provider output, or private errors.

### Safe events and failure handling

- Record fixed events for upload, processing start/success/failure, review required,
  field accepted/rejected/corrected, and review completion. Events contain IDs, state,
  timestamps, outcomes, codes, and fixed messages only.
- Any provider/output/unexpected processing failure must leave a retrievable terminal
  `FAILED` document with sanitized error, preserve the parent case, stop later document
  work, and never become `REVIEWED`.
- Do not implement retries, workers, or downstream target operations.

## Acceptance criteria

1. The existing onboarding create/get API and five accepted Phase 01/02 outcomes,
   connector call-stopping rules, terminal histories, environment labels, and truthful
   `COMPLETED` claim remain unchanged.
2. Existing cases accept isolated PDF documents; list/get enforce case ownership.
3. Upload validation covers PDF media type, safe name, empty/oversized content,
   signature/EOF structure, missing parent, and bounded streaming before provider use.
4. `IdpProvider` is replaceable; `MockIdpProvider` is deterministic, synthetic,
   credential-free, and network-free.
5. The four-field source result is strictly validated with independent confidence and
   bounded page/source provenance.
6. Comparison deterministically produces all five statuses without fuzzy matching or
   mutation of the canonical entity.
7. Low confidence and mismatch/missing fields are visibly reviewable; high confidence
   makes no approval claim.
8. Accept, reject, and correct preserve original extraction, produce distinct human
   review state/value, enforce validation/idempotency/conflict rules, and complete only
   after every field is reviewed.
9. Safe fixed audit events cover the required lifecycle without PDF text, extracted
   values, corrected values, notes, filenames, or exception detail.
10. Malformed/provider/unexpected failure is retrievable terminal `FAILED`, sanitized,
    isolated, and does not corrupt the parent case or call GoldTier.
11. Frontend supports existing-case opening, document list/upload, extracted fields,
    confidence, provenance, comparisons, field actions/correction, and reviewed state.
12. Only synthetic fixtures/scenarios are tracked; no real PDF, IDP secret, sponsor data,
    temporary file, or dependency for OCR/cloud/VLM is added.
13. Architecture, field profile, README demo, project decisions/questions, security
    review, and regression catalogue accurately describe implemented/provisional scope.
14. All backend, Ruff, strict mypy, repository/contract/Phase 01/02/03, secret,
    frontend, dependency-integrity, build, diff, and untracked whitespace checks pass.

## Explicit non-goals

UBO, ownership graph, related-party orchestration, hierarchy retrieval, real GoldTier,
PingFed, credentials, Ready-for-Approval, Camunda, queues/workers, durable persistence,
additional jurisdictions, autonomous AI approval, general-purpose OCR/VLM, real cloud
IDP, scanned-PDF support, retries, and every Phase 04 capability are excluded.

Do not stage, commit, push, merge, or begin Phase 04.
