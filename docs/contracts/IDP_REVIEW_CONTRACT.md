# Phase 03 IDP and Review API Contract

## Authority

This is a project-owned POC contract. It is not a sponsor-approved document schema,
IDP vendor contract, OCR accuracy claim, compliance rule, or GoldTier mapping. Q-003,
Q-013, and Q-014 remain open.

## Provider contract

`IdpProvider.process(IdpDocumentInput) -> object` isolates provider-specific behavior.
The provider exposes provider-neutral metadata separately and its returned object is
validated as `IdpSourceResult` before use. `IdpDocumentInput` contains only the profile
and transient bytes; it has no Mock scenario. Metadata contains a bounded provider name
and generic environment. The result must contain the `PROVISIONAL_CORPORATE` profile
and all four unique provisional fields. Each source field has a fixed field key,
nullable bounded value, confidence in `[0, 1]`, optional page number in `[1, 500]`, and
bounded source reference. Extra properties, missing/duplicate fields, invalid
confidence, blank values, control characters, and invalid provenance are malformed
output.

## Upload and retrieval

The generic upload request is a bounded raw PDF body with `Content-Type:
application/pdf` and a safe display-only `X-Document-Name`. The dedicated local demo
upload endpoint additionally accepts a fixed Mock scenario and selects a configured
Mock provider outside the business/domain contract. Bytes and raw output are transient.
The display name is returned but is never used as a path. Streamed chunks are rejected
when they exceed the remaining capacity before being appended to the application
buffer.

List and detail responses contain generated IDs, safe document metadata, profile,
provider-neutral environment, state, field candidates/reviews, safe events/errors, and timestamps.
They exclude PDF bytes, internal paths, raw provider payload, raw document text,
credentials, endpoint configuration, and exception details.

## Field review request

`POST /api/onboarding/cases/{case_id}/documents/{document_id}/reviews`

```json
{
  "field_key": "legal_name",
  "decision": "CORRECTED",
  "corrected_value": "HUMAN REVIEWED NAME",
  "note": "Optional safe operational note"
}
```

`field_key` is one provisional key and `decision` is `ACCEPTED`, `REJECTED`, or
`CORRECTED`. Both values are represented as domain enums in OpenAPI. Unknown properties
are forbidden. Corrected value (512 characters maximum) is required only for
correction; note is optional and limited to 240 characters. The response is the
complete updated document record. A missing suggestion
cannot be accepted; repeated identical decisions are idempotent; a different second
decision conflicts. Only the current evidence record is reviewable. A superseded
document returns `DOCUMENT_ALREADY_SUPERSEDED` before any review event or field change.

For a case already at document review, the document decision is the first durable
section of a monotonic sequence. A later reconciliation or automation checkpoint
rejection returns its typed safe error even though that accepted document event remains
durable. The request then stops with existing automation blockers intact and no
ownership/target work; an exact repeated decision is the idempotent repair entry point.

Original extracted values and provider provenance remain immutable. `ACCEPTED` retains
the original suggestion, `REJECTED` makes that field unusable, and `CORRECTED` records a
separate reviewed value. Under the current provisional rule, a correction can become
effective reconciliation evidence only when the original suggestion was present and met
the case-bound confidence threshold. Missing and low-confidence originals remain
replacement-required even when a correction is recorded.

## State and event contract

```text
UPLOADED -> PROCESSING -> REVIEW_REQUIRED -> REVIEWED
                     \-> FAILED
```

`DOCUMENT_UPLOADED`, `DOCUMENT_PROCESSING_STARTED`, `DOCUMENT_PROCESSED`,
`DOCUMENT_REVIEW_REQUIRED`, field accepted/rejected/corrected, review completed, and
processing failed events use safe fixed messages. `REVIEWED` requires all four fields
to have final decisions and is not Ready-for-Approval.

Once `DOCUMENT_UPLOADED` is persisted, the trusted processing failure boundary covers
every required step through `REVIEW_REQUIRED`. A recoverable exception results in one
terminal failure event and a retrievable `FAILED` document. It cannot leave
`PROCESSING`, reach `REVIEWED`, modify the parent case, or invoke GoldTier. Known
invalid canonical comparison inputs are validated before construction of bounded
retained field models.

## Safe error catalogue

Stable codes cover unknown case/document, unsupported media, unsafe name, invalid
length, empty/oversized/malformed PDF, invalid scenario, provider processing failure,
malformed output, unexpected processing failure, invalid field/decision/correction,
invalid canonical comparison input, missing suggestion acceptance, non-reviewable
document, superseded evidence, and decision conflict. Public
messages never append user input, PDF text, field values, notes, or private exceptions.
