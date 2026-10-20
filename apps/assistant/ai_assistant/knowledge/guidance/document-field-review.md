---
id: guidance.document-field-review
title: Reviewing values read from a document
blocker_codes: DOCUMENT_SOURCE_CONFLICT, DOCUMENT_REVIEW_INCOMPLETE
fields: legal_name, registration_number, registered_address, country_of_incorporation
stages: Document verification
source: apps/backend/app/services/reconciliation.py, apps/backend/app/services/document_processing.py, apps/frontend/src/pages/BlockerDecisionReview.tsx
illustrative: false
---
The "Review extracted document fields" group answers one question: did the system read the document correctly? It is separate from "Compare registry and document values", which decides which value the case uses.

- "Accept document suggestion" confirms the value was read correctly. The value is then still compared with ACRA.
- "Reject document suggestion" says the value read should not be used, so the case has no document value for that field.
- "Record correction" lets the reviewer type what the document really shows; it replaces what the system read and is compared with ACRA again.

Accepting a value that differs from ACRA does not make it the company's value; the source decision is still needed.
