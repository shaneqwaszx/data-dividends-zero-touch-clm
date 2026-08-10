# Phase 03 POC Regression Check

## Result

**PASS.** The accepted Phase 01/02 onboarding catalogue and all five Phase 03 document
scenarios remain unchanged. The expanded suite also proves the independent quality
gate's adversarial failure cases, provider replacement, provenance, streaming, review
contract, and UEN normalization invariants. No active regression remains.

## Canonical onboarding scenarios and actual results

| Input | Actual terminal result | Actual ordered stages | Result |
|---|---|---|---|
| `202400001A` | `COMPLETED` | `REQUESTED -> REGISTRY_FETCHED -> VALIDATED -> GT_SEARCHED -> GT_SHELL_CREATED -> GT_POLICY_CREATED -> GT_ENRICHED -> COMPLETED` | PASS |
| `202400002B` | `REVIEW_REQUIRED / CANONICAL_DATA_INCOMPLETE` | `REQUESTED -> REGISTRY_FETCHED -> REVIEW_REQUIRED` | PASS |
| `202400003C` | `FAILED / GT_POLICY_VALIDATION_FAILED` | `REQUESTED -> REGISTRY_FETCHED -> VALIDATED -> GT_SEARCHED -> GT_SHELL_CREATED -> FAILED` | PASS |
| `202400004D` | `REVIEW_REQUIRED / GT_OPTIONAL_SECTION_REVIEW` | `REQUESTED -> REGISTRY_FETCHED -> VALIDATED -> GT_SEARCHED -> GT_SHELL_CREATED -> GT_POLICY_CREATED -> GT_ENRICHED -> REVIEW_REQUIRED` | PASS |
| `999999999Z` | `FAILED / ACRA_ENTITY_NOT_FOUND` | `REQUESTED -> FAILED` | PASS |

The focused onboarding tests also confirm that only `NO_MATCH` permits shell creation;
match/failure outcomes and injected required-stage exceptions stop every inappropriate
later call. No partial or failure path reaches `COMPLETED`.

## Phase 03 document scenarios and actual results

| Scenario | Actual result | Actual evidence | Result |
|---|---|---|---|
| `ALL_FIELDS_MATCH` | `REVIEW_REQUIRED`, then `REVIEWED` after four explicit accepts | Four `MATCH` candidates; original suggestions retained; final event is `DOCUMENT_REVIEW_COMPLETED` | PASS |
| `FIELD_MISMATCH` | `REVIEW_REQUIRED` | Legal name is `MISMATCH`; original and canonical values remain separate | PASS |
| `LOW_CONFIDENCE` | `REVIEW_REQUIRED` | Registered address confidence is `0.54`; confidence does not create a decision | PASS |
| `MISSING_FIELD` | `REVIEW_REQUIRED` | Address is `MISSING_FROM_DOCUMENT`; missing suggestion cannot be accepted | PASS |
| `PROCESSOR_FAILURE` | retrievable `FAILED / IDP_PROCESSING_FAILED` | Upload/start/failure only; no field result, review event, or downstream call | PASS |

Successful processing remains:
`DOCUMENT_UPLOADED -> DOCUMENT_PROCESSING_STARTED -> DOCUMENT_PROCESSED ->
DOCUMENT_REVIEW_REQUIRED`. The parent onboarding case remains unchanged for every
document scenario.

## Adversarial processing failures and actual results

| Injection | Actual terminal result | Required invariant | Result |
|---|---|---|---|
| Canonical legal name of 513 characters | retrievable `FAILED / DOCUMENT_COMPARISON_INPUT_INVALID` | upload/start/failure only; no stranded `PROCESSING`; parent unchanged | PASS |
| Comparison helper/model seam raises private exception | retrievable `FAILED / IDP_UNEXPECTED_FAILURE` | private sentinel absent; exactly one safe failure event | PASS |
| Clock fails after provider validation | retrievable `FAILED / IDP_UNEXPECTED_FAILURE` | no `REVIEWED`; private sentinel absent | PASS |
| One-shot repository update failure with recovery save available | retrievable `FAILED / IDP_UNEXPECTED_FAILURE` from last saved record | transactional update; one safe terminal event | PASS |
| Blank, whitespace, newline, embedded-control, or overlong provider name/reference | retrievable `FAILED / IDP_MALFORMED_OUTPUT` | unsafe provenance not retained or returned | PASS |

All adversarial failures stop before review completion and do not alter the parent case
or invoke ACRA, GoldTier, or any other downstream business operation.

## Provider replaceability

- `MockIdpScenario` is absent from `IdpDocumentInput`, `IdpProvider`,
  `DocumentProcessingService`, source-neutral document models, and the generic upload
  API/OpenAPI contract: PASS.
- A non-Mock `LOCAL` stub provider processes the same four-field result through the
  unchanged service, produces identical comparisons, and completes the same explicit
  review flow without a scenario: PASS.
- Provider name/environment comes from validated provider metadata; generic environment
  values are `MOCK`, `LOCAL`, `SANDBOX`, and `LIVE`: PASS.
- Mock scenario selection remains available through the dedicated demo control/API and
  synthetic UI only: PASS.

## Upload, review, and normalization regressions

- Single oversized streamed chunk is rejected before append and before provider call:
  PASS.
- Multiple chunks crossing the limit are rejected before provider call: PASS.
- Structurally valid input exactly at the configured limit is accepted: PASS.
- Missing/deceptive `Content-Length` remains bounded and declared-length protection
  remains active: PASS.
- OpenAPI exposes `DocumentFieldKey` and `ReviewDecision` enums directly; invalid enums,
  unknown properties, overlong correction, and overlong note fail at API validation:
  PASS.
- Valid accept/reject/correct behavior and original-value preservation are unchanged:
  PASS.
- UEN comparison trims, removes internal whitespace, and normalizes case, so
  `2024 00001a` matches `202400001A`; a genuinely different UEN remains `MISMATCH`:
  PASS.
- Legal-name/address normalization was not changed to remove all whitespace: PASS.

## Cross-scenario invariants

- Original extraction remains immutable and distinct from accepted/corrected values:
  PASS.
- Rejection does not erase the extraction: PASS.
- Confidence never constitutes approval; all four fields need explicit final decisions:
  PASS.
- `REVIEWED` means local document review only, not customer/compliance approval,
  Ready-for-Approval, or GoldTier completion: PASS.
- Identical review retry is idempotent; conflicting second decisions are rejected:
  PASS.
- Invalid type/name/path/size/structure stops before provider invocation: PASS.
- Documents and cases remain isolated by parent case ID and generated identifiers:
  PASS.
- Uploaded bytes/raw text/raw output are absent from persistence, events, API/browser
  models, and logs: PASS.
- Mock, sandbox-shaped synthetic, and live claims remain distinct: PASS.
- No Phase 04, UBO, related-party, hierarchy, real ACRA, or real GoldTier behavior was
  added: PASS.

## Checks run

- Backend suite: **167 passed**.
- Focused Phase 03 remediation/provider/API contract suite: **67 passed**.
- Canonical onboarding plus document/adversarial scenario subset: **66 passed**.
- Contract suite: **23 passed**, including eight Phase 03 contract tests.
- Repository unittest discovery: **33 passed**.
- Frontend tests: **11 passed**; typecheck and production build: PASS.
- Ruff and strict mypy: PASS.
- Secret scanner/tests, `pip check`, `npm ls --all`, GoldTier validator regressions,
  `git diff --check`, cached diff check, and untracked whitespace check: PASS.
- GoldTier example classification remains the accepted 19 valid, 19 invalid and
  quarantined, 48 not validated; no contract artefact was normalized silently.

## Catalogue change

No sixth document product scenario was invented. The catalogue retains exactly the
five planner-defined Phase 03 scenarios and adds the explicitly authorized remediation
invariants for post-acceptance terminalization, provider replacement, provenance,
pre-append streaming bounds, typed review requests, and UEN normalization.

## Regressions found

One intermediate full-suite run detected that global request-validation sanitization
had changed the accepted Phase 01 blank-UEN error. The handler was narrowed to the
document-review boundary, and the final 167-test backend run is green. No active
regression remains.

## UI/API claim integrity

PASS. The UI uses the Mock-only demo endpoint and continues to label candidate data as
synthetic, provisional, and not OCR output from the file. The generic endpoint has no
Mock scenario contract. Neither UI nor API represents confidence, `REVIEWED`, mock ACRA,
or Mock GoldTier as sponsor approval or live interoperability.
