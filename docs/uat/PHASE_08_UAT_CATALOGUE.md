# Phase 08 Input-Driven UAT Catalogue

All documents and UENs below are fictional synthetic test data. Normal start uses only
UEN and actual PDF bytes through `LOCAL_PDF_TEXT`; Developer/Test controls are not used.

| UAT | Inputs | Expected safe result |
|---|---|---|
| ID-01 | `202400001A` + `clean-company-profile.pdf` | `COMPLETED / MOCK_GOLDTIER_SUBMITTED`; 0 post-start interventions; search/shell/policy/amend once |
| ID-02 | `202400001A` + `address-mismatch.pdf` | `WAITING_FOR_REVIEW / DOCUMENT_SOURCE_CONFLICT`; no ownership or target call before resolution |
| ID-03 | ID-02 then corrected replacement | Prior document retained/superseded; new current document completes and auto-resumes |
| ID-04 | `202400001A` + `missing-field.pdf` | `WAITING_FOR_REVIEW / DOCUMENT_REQUIRED_FIELD_MISSING`; no fabricated value or target call |
| ID-05 | `202400001A` + `low-confidence.pdf` | `WAITING_FOR_REVIEW / DOCUMENT_LOW_CONFIDENCE`; no click-through action |
| ID-06 | `202400001A` + `no-text.pdf` | `WAITING_FOR_REVIEW / DOCUMENT_TEXT_UNAVAILABLE`; no OCR claim or target call |
| ID-07 | `202400006F` + `cycle-uen-clean.pdf` | Document pass then `WAITING_FOR_REVIEW / OWNERSHIP_CYCLE`; no target call |
| ID-08 | `202400005E` + `second-case-isolation.pdf` | Document/ownership pass then existing-party review; `SEARCH / MATCH_FOUND` only; Shell/Policy/Amend not attempted |

The UAT export remains a strict safe whitelist. It must not contain PDF bytes, full raw
text, server paths, parser objects, credentials, raw payloads, or authority digests.
This is an input-driven bounded synthetic POC, not live onboarding, production IDP, AI
validation, or Ready-for-Approval.
