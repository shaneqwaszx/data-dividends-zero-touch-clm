# IDP classification extraction verification

Status: extraction, complete browser/current shards and all required local regressions PASS;
independent exact-content acceptance pending.

Baseline HEAD/BASE_SHA/main: e799d74063678bb0eccbea445d5ab3c8628dd2c0.
Candidate: feat/blocker-resolution-idp-ux-optimization, intentionally uncommitted.

## Actual owner PDF

Owner-supplied directory contained orion-synthetic-technologies-classified.pdf (without
(1)). Read-only bytes have SHA256
76e5c9922abbd2ba7b71c51bd8139ede37ba91c599168e2550f2c7e7e5d50d48.
Before repair: one NATIVE_PDF_TEXT page, eleven CRLF separators, four identity fields,
zero classification observations. After repair on the same bytes: two observations,
Company - Private and Corporate, PAGE_1_LINE_10/11, page1, deterministic score0.97.
No owner PDF was modified. Safe before/after evidence is retained separately in
BLOCKER_REVIEW_BROWSER_EVIDENCE/owner-orion-baseline-verification.json and
BLOCKER_REVIEW_BROWSER_EVIDENCE/owner-orion-verification.json. Baseline extraction was
replayed from the exact e799d74 source archive against the same read-only bytes.

## Repair and extraction limits

LocalPdfTextIdpProvider normalizes CRLF and standalone CR to LF once, before existing
identity/ownership/classification parsers. Page identity, line order, original values,
method and evidence scores remain. Empty labels are absent observations; unknown values
remain untrusted observations and cannot bind. Conflicting/repeated labels retain their
own source references. Unsupported wrapped values are not inferred. No filename exception,
LLM, cloud API, new classifier, new vocabulary or source precedence was introduced.

Tests cover LF/CRLF/CR logical TXT/DOCX, actual native PDF, actual media-router DOCX/TXT,
supported bounded OCR, missing/wrapped/repeated/conflicting/unknown labels. Existing
classification tests enforce trusted currentness, confidence, vocabulary, compatibility,
partial candidates and stale/conflict review. Final evidence:21 parser/media tests,
36 real OCR checks, the complete2617-test backend lane plus136 zero-skip physical tests,
and104 browser tests. A new ignored runtime's native-worker import prerequisite was
also corrected and its21 media tests rerun. Exact revision binding is in the final receipt.

## Four repository-owned documents

The project-owned generator adds two labels to each PDF while leaving company seed data,
canonical identity fields and ownership graphs unchanged. Native worker evidence finds
four identity fields plus two classification observations, page1 lines7/8, NATIVE_PDF_TEXT.
The four rendered page images were visually inspected: all labels/identities legible,
no clipping, no ownership quantities. Exact PDF hashes are in the UAT README and final manifest.

| Company | UEN | KYC / segment | Source |
|---|---|---|---|
| Orion | 202400014N | Company - Private / Corporate | DOCUMENT |
| Pacific | 202400015O | Company - Private / Corporate | DOCUMENT |
| Straits | 202400016P | Company - Private / Corporate | DOCUMENT |
| Meridian | 202400017Q | Company - Private / Corporate | DOCUMENT |

Actual api_marketplace_mock and physical Mongo tests verify CACHE_HIT,
LOCAL_SYNTHETIC_UAT_V1 and zero Marketplace token/entity/officer/shareholder requests.
Tests now require both DOCUMENT selections without a manual classification PUT. Final
Review & Send remains explicit. Gamma Partnership and separate Government coverage retain
existing rules; Government classification does not establish supported UBO/control evidence.
The final unfiltered browser run passed 81 isolated selectors / 104 tests, including the
four-company api_marketplace_mock/Mongo loop with actual native PDF upload, both DOCUMENT
classifications, no classification PUT, exact ownership results, explicit final Mock send,
readback and reload without target replay. The separate Gamma/Government offline protocol
browser lifecycles also passed. No real provider request was used as acceptance evidence.

## Supported target-input inventory

Current owners: app/mappers/goldtier.py and goldtier_xpi.py, OnboardingService,
DocumentProcessingService, ReconciliationService, target policy/snapshot/ledger owners.
Mock and XPI Sandbox dialects retain their distinct contracts; no external mapping changes.

| Input | Authoritative source / extraction disposition |
|---|---|
| legalName | Document observation compared/reconciled against canonical registry; existing guarded legal-name source choice |
| registrationNumber / UEN | Canonical verified identity; document comparison; existing same-case UEN correction authority |
| countryOfIncorporation / registration.countryIso2 | Canonical explicit Singapore/jurisdiction validation; document comparison |
| address street1/street2/countryIso2/zip | Structured canonical registry address; document comparison, no new free-text address parsing/mapping |
| kycCustomerType | Fresh trusted explicit document, closed auto values Company - Private, Partnership - Unregulated, Government; compatible legal form; guarded USER fallback |
| clientSegment | Fresh trusted explicit supported vocabulary; never inferred from KYC/entity name; valid partial evidence preserved |
| customerExternalSystem, registrationType, policy, bookingEntity | Existing approved frozen configuration, no document inference |
| customerExternalSystemKey | Existing system derivation from canonical identity, never fabricated IDP output |
| goldTierId / goldTierID | Actual Search/Shell/verified readback and existing ledger binding |
| accountEntityType / productType | Existing optional explicit sponsor/sandbox-authority policy only; no automatic extraction |
| ANZSIC / groupCompanyName (optional XPI model fields) | Current XPI builder leaves these absent and therefore skips optional Amend for the identity-only package; no mapped input or IDP extraction is introduced |
| ownership/UBO | Existing registry/reviewed source and deterministic Decimal engine; not PDF classification inference or target hierarchy creation |
| Mock party role/type, source context | Existing provisional system constants, unchanged |

SSIC, controller identities, risk/KYC approvals, full historical dictionary fields and
unsupported hierarchies are not populated. All provider classifications remain Local,
Mock or offline test protocol; no Live/sponsor/compliance approval claim follows.
