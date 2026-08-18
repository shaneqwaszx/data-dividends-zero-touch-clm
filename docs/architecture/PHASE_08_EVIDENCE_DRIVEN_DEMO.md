# Phase 08 — Evidence-Driven Demo Architecture

The sponsor journey is an **input-driven bounded synthetic POC**. It has no integrated
scenario selector: the UEN selects provider-local fictional registry, ownership, and
Mock GoldTier records, while the uploaded PDF itself supplies the document evidence.

```text
UEN -> Mock Registry Store -> Canonical Entity
                                  ^
PDF -> pypdf text extraction -> deterministic labelled-field parser
                                  |
                        semantic comparison / POC confidence
                                  |
                         pass or human review/replacement
                                  |
                         UEN-keyed Mock Ownership Store
                                  |
                           Decimal UBO/readiness analysis
                                  |
                           UEN-keyed Mock GoldTier Store
                                  |
                                  outcome
```

`LocalPdfTextIdpProvider` supports only text-based PDFs. It reads up to ten pages and
64,000 extracted characters,
rejects malformed/encrypted input through the existing sanitized processor failure
boundary, and reports `DOCUMENT_TEXT_UNAVAILABLE` for an otherwise-valid PDF without
extractable text. It neither performs nor claims OCR.

The parser reads the four existing provisional fields: Legal Name, UEN, Registered
Address, and Country. Confidence is **PROJECT-DEFINED / POC EXTRACTION CONFIDENCE**:
unique primary labelled value `0.97`, supported alternate label `0.90`, ambiguous
distinct candidates `0.40`, missing `0.00`. This deterministic parser evidence is not
an ML probability or sponsor-approved policy; Q-003, Q-005, Q-014 remain open.

Replacement evidence is explicit. A fresh document is created, then only the active
same-case replaceable document receives a supersession link. Historical extraction is
retained, superseded records no longer block readiness, unrelated current documents
continue to block, stale/cross-case/terminal requests fail safely, and a clean current
replacement automatically re-enters the established Phase 06 resume flow.

Developer/Test Controls remain separate, default-collapsed, environment-gated fault
injection. Their scenario bindings are never attached to the normal sponsor start path
and cannot alter an existing sponsor case.

Runtime stack: React/TypeScript/Vite; Python/FastAPI/Pydantic; pypdf plus deterministic
parser behind `IdpProvider`; Mock/SANDBOX-shaped ACRA connector; Decimal ownership
analysis; Mock GoldTier connector; process-local bounded repositories; pytest, Vitest,
contract tests and quality gates; existing Windows lifecycle controller.
