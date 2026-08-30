# Pre-Phase 12 CLM Workspace and Multi-Document Boundary

## Scope

This bounded refinement preserves the accepted Phase 09–11 orchestration and adds:

- a Start-onboarding landing workspace with accessible progress and early case identity;
- a backend-authored process-local case portfolio and `WAITING_FOR_REVIEW` queue;
- bounded intake-only PDF/DOCX/TXT uploads followed by explicit intake completion; and
- complete-current-document reconciliation with per-document provenance.

It does not implement Phase 12, MongoDB, durable restart recovery, production assignment,
RBAC, notifications, live ACRA/GoldTier, OCR, or source-authority policy.

## Read-only workspace projection

```text
InMemoryZeroTouchAutomationRepository.list_records()
                    |
                    v
GET /api/clm/zero-touch/cases[?status=enum]
                    |
          +---------+---------+
          |                   |
     Dashboard history    Review queue
```

The repository returns deep defensive copies ordered by `updated_at` descending with a
stable case-ID tie-break. The API exposes only case ID, requested UEN, optional legal
name, status, stage, updated time, active-exception count, intervention count, and final
outcome. Listing does not invoke or resume any provider or workflow stage.

All records are process-local. Restart clears cases and the browser must describe the
portfolio as local POC history, not durable case management.

## Intake and processing sequence

```text
Create case (Registry once)
       |
       v
POST .../intake/documents  -- one browser File, repeated up to the bound
       |                        PDF -> validated transient bytes
       |                        DOCX -> bounded safe OOXML text extraction
       |                        TXT -> bounded UTF-8 text extraction
       v
One DocumentProcessingRecord per file (bytes/body not retained)
       |
       v
POST .../intake/complete { expected_document_count }
       |
       v
Reconcile every current document -> Ownership -> Readiness -> Mock GoldTier
```

The compatibility `POST .../documents` route retains its accepted single-document,
auto-start semantics. The new browser uses intake-only routes so an upload failure keeps
the created case and successful documents without starting against an incomplete set.
An explicit failed-document retry route supersedes the failed record and stays on the
same case.

## Media trust boundary

`DocumentMediaRouter` owns extension/MIME agreement and content validation. It accepts
only PDF, DOCX, and UTF-8 TXT. PDF input crosses the existing strict `pypdf` parser before
IDP, so marker-only, truncated, corrupt, encrypted, or zero-page input is rejected as a
document request error. DOCX extraction uses Python's bounded ZIP/XML readers; rejects
rooted, UNC-like, drive-qualified, traversal, backslash, NUL, encryption, macro, ActiveX,
and embedded-object entries; caps entry count and expanded bytes; and reads only
`word/document.xml`. TXT rejects invalid UTF-8 and binary or unsupported control content.
No parser executes macros, objects, scripts, or archives.

Default technical limits are 20 current files per case, 5 MiB per file, and 25 MiB total.
They are configurable POC safety controls, not sponsor policy. Browser folder selection
uses only files the browser supplies and never sends a filesystem path or ZIP. The Start
workspace totals only accepted, deduplicated selected files and displays that value
against the advisory 25 MiB limit; the backend remains authoritative.

## Multi-document reconciliation

Every observation retains its source document ID/display name, provider/environment,
observation time, confidence, validity, and normalized value. For each field:

- no usable document value produces `MISSING_IN_SOURCE`;
- one or more equal valid document values are consistent even if another document omits
  the field;
- distinct valid values remain a `CONFLICT` with every observation visible;
- any relevant invalid or unverifiable observation remains `INVALID` or `UNVERIFIABLE`;
- Registry, confidence, recency, first file, and last file never become automatic winners;
- `USE_DOCUMENT_VALUE` is advertised only for exactly one normalized valid legal-name
  candidate, even if more than one document supplies that same candidate.

Replacing document B leaves document A current, retains B as superseded, processes B2
once, rebuilds reconciliation from all current documents, and invalidates stale decision
context. Registry evidence is not reacquired.

## Security and persistence

Uploaded bytes, extracted PDF/DOCX/TXT bodies, raw Registry payloads, credentials,
private exceptions, and internal authority digests are absent from the portfolio, queue,
normal logs, and browser history. Current reviewer assignment remains an unauthenticated
session-only UI aid pending Q-015. Q-012, Q-003, Q-013, Q-014, and Q-015 remain open.
