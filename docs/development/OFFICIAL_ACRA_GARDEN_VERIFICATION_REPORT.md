# Official ACRA Marketplace Mock Garden Verification — Final Report

## 1. Executive Summary

STATUS: PARTIAL. Current official networked Marketplace Mock acquisition is VERIFIED.
The production OAuth client and connector obtained four HTTP 200 responses within the
authorized budget. Strict decoding bound UEN 11111999A to GARDEN BUSINESS, decoded four
officers, and retained EMPTY shareholders with UNSUPPORTED/no-call Relationships.

The original network-backed browser case did not complete: its temporary verification
harness skipped asynchronously loaded document review controls. Captured normalized
company/empty-ownership evidence subsequently completed through the normal local UI,
reviewed synthetic client document, manual declaration, explicit confirmation and local
Mock GoldTier. That replay omitted unretained officer personal records and is not a
second network observation or proof of the exact original case completing.

No application source compatibility defect was established. Required physical Mongo
and exact original network-backed end-to-end completion remain unverified. No publication.

## 2. Repository / Candidate

| Item | Value |
| --- | --- |
| Branch | fix/demo-happy-path-stabilization |
| Base / HEAD / local origin/main | efc31f450f0103766fa812bc0aa80754f801dbe9 |
| Starting candidate | 3cc6d9bd753b825450e9618a4e9f7b44604cc0bc12debf1ea6079a2bfed17a5b |
| Final source candidate | Same; all 46 path hashes unchanged |
| Working tree | Existing Garden modifications/new files plus reporting-only continuation; index empty |
| Evidence bundle | a23a331a8133c2a99c6c4c90c8e8b8166021ce1acdfc0113c2da0881cd86f41e |
| Evidence manifest | tmp/OFFICIAL_GARDEN_EVIDENCE_MANIFEST.json; seven local receipt/harness paths |

Mandatory preflight verified branch/base, frozen identity, empty index, no unexpected
paths and whitespace. No switch, branch/worktree creation, fetch, reset or Git metadata
mutation occurred. Report-only content is outside the source candidate.

## 3. Authorized External Budget

| Operation | Authorized max | Actual network requests |
| --- | ---: | ---: |
| Token | 1 | 1 |
| entityBasicInformation | 2 | 2 |
| coShareholdersDetails | 1 | 1 |
| LLP Highlights | 0 | 0 |
| Capital Details | 0 | 0 |
| Relationships | 0 | 0 |
| GoldTier external reads | 0 | 0 |
| External provider writes | 0 | 0 |
| Other external-provider requests | 0 | 0 |

The application uses entity/basic once for the profile and once for officers. Those
requests consume the entire entity budget; no extra HR Entity Profile lookup or external
remediation/retest was dispatched. No refresh or provider retry occurred.

## 4. ACRA Authentication

Existing ignored configuration supplied client ID and secret key; only presence was
reported. Credentials were not changed or saved. Fixed host: api-sandbox.bizfile.gov.sg.
Production OAuth2 Client Credentials used HTTP Basic authentication at the fixed Mock
token endpoint, then the raw `token` header downstream. No Bearer substitution.
Token request returned HTTP 200 and passed the strict production token decoder.

TLS verification, bounded time/body size, disabled redirects and trust_env=False were
preserved. Token state remained in process memory. Runtime overrides selected memory,
local_pdf_text and local Mock GoldTier with external writes disabled. Mongo configuration
was discarded before application composition; a task guard prohibited MongoClient use.
The normal ignored configuration was not modified.

Chronology matters: automatic approval review first rejected the launch because it did
not recognize the attachment's explicit human authorization. Re-presenting that exact
authorization for the same command was accepted; no rejected command executed. A local
bootstrap stop and a temporary pre-auth header assertion also preceded actual dispatch.
The initial guard ran before HTTPX injected Basic auth; independent inert-transport
reproduction proved zero underlying dispatches. Its preserved V1 counter is a reservation,
not an extra token request. The guard was moved after auth injection and before transport.

## 5. Garden Entity Profile

Observed in the successful session at 02:32 on 2026-10-01 Asia/Singapore
(receipt timestamps retain UTC). Both entity/basic responses were HTTP 200. The production
decoder requires one entity and checks returned UEN against requested UEN.

| Normalized field | Value | Classification |
| --- | --- | --- |
| UEN | 11111999A | Returned; bound to request |
| Legal name | GARDEN BUSINESS | Returned |
| Entity type | PARTNERSHIP | Mapped from returned constitution |
| Registration date | 1974-09-28 | Returned date, normalized |
| Address block | 306C | Returned component |
| Street | XYZ LINK | Returned component |
| Unit | #03-21 | Derived formatting from returned level/unit |
| Building | ABC GARDEN | Returned component |
| Postal code | 333333 | Returned component |
| Address line 1 | 306C XYZ LINK | Derived joining of returned components |
| Address line 2 | #03-21, ABC GARDEN | Derived joining of returned components |
| Country / address country | SG | Existing Singapore-lane default; not directly returned evidence |
| Entity status | null | Omitted; no status invented |
| Source environment | MOCK | Fixed connector classification; no Production/Live claim |
| Officers | 4 decoded records | Actual outcome; personal names/details not retained |

The original offline fixture's company type and address differ from this current
provider evidence. Those fixture values were not promoted to official evidence.

## 6. Garden Shareholder Evidence

One coShareholdersDetails request returned HTTP 200. Production decoding retained
OWNERSHIP_PARTIES = EMPTY, zero records, with its actual Mock retrieval provenance.
No shareholder records or ownership percentages were manufactured.

EMPTY does not invalidate the registry identity, prove ownership completeness, or prove
that no beneficial owners exist. The existing registry ownership provider feeds the
incomplete graph to the Decimal engine; the local captured-data run retained
OWNERSHIP_INCOMPLETE and required supplementary reviewed evidence.

## 7. Unsupported Operations

Normal acquisition retained Relationships as UNSUPPORTED, record_count=0, provenance=null
and error=null. The production connector raises AcraOperationUnsupportedError before
authorization/transport dispatch. There is no invented endpoint or retrieval timestamp.
UNSUPPORTED is distinct from the actually observed EMPTY shareholder collection.

The HR console independently executed only local diagnostics for LLP_HIGHLIGHTS,
CAPITAL_DETAILS and RELATIONSHIPS against the real official connector composition.
Each receipt states UNSUPPORTED, provider_called=false and record_count=0. All external
sends were prohibited during that check. No unsupported endpoint was added or contacted.

## 8. Normal Garden Onboarding

The actual network-backed normal UI path proved:

1. Onboarder login, normal Create onboarding and local Mock GoldTier Search.
2. Actual Marketplace OAuth/profile/officers/shareholders transport and strict decoding.
3. Retained PARTIAL acquisition, valid canonical identity and truthful missing ownership.
4. Synthetic CLIENT PDF upload through local_pdf_text and a real registered-address conflict.
5. Audited Keep registry resolution preserving the actual canonical identity.
6. Operator target classification.

The harness then attempted manual evidence without a fully reviewed document because its
optional button-count checks preceded document rendering. This is an incomplete test
journey, not evidence that the production manual-evidence guard should be loosened. The
ephemeral memory case was closed with its owned verification process. No original-case
completion or external request replay is claimed.

A zero-network follow-up used only captured normalized company fields and the observed
empty ownership outcome; officer personal data was deliberately omitted. Its provider
label explicitly said LOCAL_NORMALIZED_REPLAY_OFFICERS_OMITTED / synthetic offline evidence.
Waiting for the document card resolved the harness race, with no application source fix.
All four document fields became ACCEPTED and the document REVIEWED. Reconciliation kept
the actual registry address. Structured 60/40 supplementary declaration then produced a
case/document-version-bound receipt with USER_SUPPLIED_DECLARATION, operator maya-lim,
LOCAL and MANUAL_DECLARATION_POC. It remained separate from ACRA evidence.

The replay reached READINESS with only TARGET_CONFIRMATION_REQUIRED, then an explicit
normal Confirm and send to Mock GoldTier action produced COMPLETED, no active exceptions,
registry aggregate COMPLETE and unchanged canonical entity. Source acquisition stayed
truthful. Its later HR harness navigation failure did not erase those completed steps;
HR was verified separately after opening the account disclosure correctly.

## 9. ACRA HR Console

Separate actual-composition, zero-external-call HR browser verification: PASS.

| Configuration | Observation |
| --- | --- |
| Provider | ACRA_API_MARKETPLACE_MOCK |
| Mode / classification | api_marketplace_mock / MOCK |
| Configured | Yes |
| Client ID / secret key present | Yes / Yes; values undisclosed |
| Safe host | api-sandbox.bizfile.gov.sg |
| Generic static-header auth | Not applicable for API Marketplace Mock |
| Unsupported diagnostic receipts | Safe IDs, classification, operation, UNSUPPORTED, provider_called=false, zero records |
| Extra Entity Profile diagnostic | Not executed; both entity requests already consumed by onboarding |

## 10. Source Changes

No application source, decoder, mapping, API/type, schema, configuration defaults,
business rules, authentication/security policy, architecture or provider classification
changed. No frozen candidate bytes changed. Production remains unclaimed.

Changes are task-owned ignored verification harnesses and reporting-only evidence.
Harness repairs supplied ephemeral local login hashes, moved the header guard after
HTTPX authentication, waited for asynchronous documents and opened account disclosure
before Sign out. Replay and HR follow-ups prohibit all external sends.

## 11. Verification

| Check | Result / scope |
| --- | --- |
| Current official acquisition | PASS: OAuth1/entity2/shareholder1; all HTTP 200 |
| Original network-backed complete browser journey | NOT VERIFIED: stopped before manual declaration/confirmation |
| Captured normalized-data local completion | PASS through explicit local Mock completion; officer data omitted |
| Actual-composition HR configuration/unsupported UI | PASS; zero external calls |
| Focused backend | PASS: 233 tests; auth, connector, diagnostics/API, acquisition, orchestration, manual ownership |
| Focused frontend | PASS: 43 tests across four affected surfaces |
| Existing offline Garden clean/discrepancy browser | PASS: 2 tests, 12.2 seconds |
| Ruff | PASS: backend/scripts/tests |
| Strict configured mypy | PASS: 112 source files |
| Frontend typecheck/build | PASS: 124 production modules |
| Contracts | Unchanged API/types; prior frozen-candidate 44 PASS retained, not rerun in this continuation |
| Whitespace / secret-pattern scan | PASS; task-owned new reports checked explicitly |
| Physical Mongo | PENDING CI mongo:7; no normal Atlas use |

The first browser regression attempt found the verifier's own loopback ports occupied;
it did not terminate them. After that owned process ended, the isolated two-test run
passed. No unrelated process was stopped.

## 12. Independent Quality Gate

Fresh independent evidence-completion review is recorded in
[OFFICIAL_GARDEN_EVIDENCE_QUALITY_GATE.md](OFFICIAL_GARDEN_EVIDENCE_QUALITY_GATE.md).
Exact independent verdict: **FAIL**. Current official acquisition is VERIFIED; captured
normalized-data local completion is VERIFIED with officer omission. The original
network-backed complete journey and physical Mongo remain unverified. Independent
checks passed: 128 backend, 31 frontend and inert guard placement/reproduction checks.
All 46 source and seven evidence hashes matched before/after review. The reviewer made
no provider calls or implementation edits.

Under [fyp-quality-gate](../../.agents/skills/fyp-quality-gate/SKILL.md), FAIL applies when
an "unverified required criterion" remains. Current official acquisition can be upgraded
to VERIFIED, but it cannot substitute for unobserved original-case completion or required
physical execution.

## 13. Provider Safety

Actual ACRA data reads: 3, plus 1 OAuth token acquisition. Actual GoldTier external reads:
0. Actual GoldTier external writes: 0. External provider mutations: 0.
Production/Live ACRA: NOT USED. GoldTier external submission: NOT EXECUTED.
No tokens, credential values, auth headers, Mongo URI, raw provider bodies or officer/
shareholder personal details were printed or retained. Authorized configuration loading
occurred only in the bounded actual-composition runs; normal persistence was never used.
Token state ended with the owned process. No retry exceeded or extended the budget.

## 14. Remaining Acceptance

Physical Mongo: PENDING CI mongo:7 after separately authorized publication, or a newly
approved disposable service. Atlas is not authorized test infrastructure; acceptance is
not waived. Publication remains prohibited in this continuation.

The exact original network-backed case's full confirmation/completion was not observed.
The captured normalized-data completion is separate evidence with officer omission.
No remaining application source defect is established. Additional external acceptance
cannot be dispatched under the now exhausted budget.

## 15. Final Verdict

| Requested verdict | Result |
| --- | --- |
| GARDEN WITH ACTUAL OFFICIAL ACRA MARKETPLACE MOCK | Acquisition PASS; exact complete original journey FAIL / unverified |
| GARDEN CLEAN LOCAL COMPLETION | PASS, including captured normalized company-data replay |
| GARDEN HUMAN-REVIEW PATH | PASS, fresh existing offline browser regression |
| CURRENT OFFICIAL ACRA MOCK EVIDENCE | VERIFIED for acquisition |
| GOLDTIER SANDBOX | SANDBOX_PARTIAL; not composed here |
| EXTERNAL GOLDTIER SUBMISSION | NOT EXECUTED |
| PHYSICAL MONGO | PENDING |
| PUBLICATION | NOT YET REQUESTED |

Overall STATUS: PARTIAL. Preserve the candidate and minimized receipts. No commit, push,
PR, merge, provider retry or Atlas cleanup is authorized by this report.
