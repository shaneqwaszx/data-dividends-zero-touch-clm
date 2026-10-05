# Open Sponsor Questions

Remove or mark a question resolved only after an explicit sponsor answer. These
questions do not block credential-free Phase 01 mock development unless stated.

## Current closeout decision packet — 2026-10-05

Post-closeout bounded answers are recorded in
[the family/confirmation note](../integration/GOLDTIER_EXISTING_CUSTOMER_RESOLUTION.md).
Q-001 is partially answered for Maker versus downstream GoldTier four-eye/KYC ownership;
the exact RFA transition remains unproved. Q-005/Q-015 are partially answered for
existing-target precedence or explicit user choice, without a universal source policy.
Q-007/Q-010 are partially answered for accepted Singapore POC values, optional
ANZSIC/group-company fields and Requested/Active Policy Amend. Q-011 is partially
answered for synchronous ordered operations, known validation-failure no-application,
new corrected Amend intent and absence of upstream idempotency/retry; complete schemas
remain open. GTAPICONNECTUSER is confirmed for current XPI; Q-008/Q-018 Production/
PingFed authority remains open. Supplied EDS Search supports registration/external-key
criteria; no same-artifact resend is required and no XPI alias is invented.
Related-party child lifecycle, original-file upload and full legal/control UBO remain
open. Historical questions below retain their dated evidence, including failed Garden
Amend; sponsor clarification never authorizes replay or a new external attempt.

The current question/status/proved/unproved/minimum-input/action table is in
[Final POC limitations and next steps](../demo/FINAL_POC_LIMITATIONS_AND_NEXT_STEPS.md#sponsor-decision-packet).
Historical phase-specific questions below retain their original evidence and dates.
POC authentication/review, bounded D-056 values, D-062 >=25% and D-064 HR/Director
activation are implemented; production authority and broader contracts remain separate.
An answer requires a new explicit implementation assignment and never implicitly
authorizes external mutation. Phase25/26 closes no sponsor question and promotes no
provider classification. The earlier Phase14.5 direct-policy-edit description below
is historical and superseded for POC controls by D-064: HR proposal, distinct Director
approval, new ACTIVE version, and unchanged frozen existing cases.

## Phase27 current delivery classification

All eighteen questions retain their broader open scope. None blocks delivery of the
accepted bounded Mock/LOCAL POC. Production flags below identify a dependency when
that capability belongs to production scope; they do not declare every optional
feature mandatory. Optional means a later separately assigned expansion, never
permission to implement it. No new sponsor answer is supplied by Phase27.

| Question / remaining topic | BLOCKS CURRENT POC? | BLOCKS PRODUCTION ONLY? | OPTIONAL FUTURE ENHANCEMENT? | ANSWERED / PARTIALLY ANSWERED / OPEN |
|---|---|---|---|---|
| Q-001 RFA transition | NO | YES, for the relevant production contract/policy | NO | OPEN; POC prerequisite clarified |
| Q-002 External hierarchy retrieval | NO | YES, if hierarchy is in deployment scope | YES, if this feature is assigned | OPEN |
| Q-003 Document/field profile | NO | YES, for the relevant production contract/policy | YES, broader media/profile expansion | OPEN |
| Q-004 Full legal/control UBO policy | NO | YES, for the relevant production contract/policy | NO | PARTIALLY ANSWERED: bounded >=25% inclusive only |
| Q-005 Validation responsibility split | NO | YES, for the relevant production contract/policy | NO | OPEN |
| Q-006 Related-party child lifecycle | NO | YES, if related parties are in deployment scope | YES, if this feature is assigned | OPEN |
| Q-007 Complete SG mapping/screening ownership | NO | YES, for the relevant production contract/policy | NO | OPEN; bounded D-056 values retained |
| Q-008 PingFed containment/auth/TLS | NO | YES, for the relevant production contract/policy | NO | OPEN / production auth blocked |
| Q-009 Canonical production values | NO | YES, for the relevant production contract/policy | NO | OPEN; bounded current vocabulary retained |
| Q-010 Operation/conditional minima | NO | YES, for the relevant production contract/policy | NO | OPEN; current provisional overlay retained |
| Q-011 Complete success/error/partial schemas | NO | YES, for the relevant production contract/policy | NO | OPEN |
| Q-012 Subscriber ACRA/partnership/second sample | NO | YES, for the relevant production contract/policy | YES, second official demo only | PARTIALLY ANSWERED: official Marketplace Mock subset only |
| Q-013 Privacy/security/retention | NO | YES, for the relevant production contract/policy | NO | OPEN |
| Q-014 Production confidence/reviewer policy | NO | YES, for the relevant production contract/policy | NO | OPEN; POC review clarified |
| Q-015 Source precedence/restart/audit authority | NO | YES, for the relevant production contract/policy | NO | OPEN |
| Q-016 Production identity/admin/assignment | NO | YES, for the relevant production contract/policy | NO | OPEN; bounded D-064 governance retained |
| Q-017 Supplied risk/screening producer | NO | YES, for the relevant production contract/policy | NO | OPEN; current advisory only |
| Q-018 Deployment/handoff/continuation | NO | YES, for the relevant production contract/policy | NO | OPEN |

D-062 numeric authority does not answer complete legal/control policy. Q-012 official
Mock acceptance does not answer subscriber/Live/partnership percentages. Current
contracts/decisions and the linked decision packet retain exact minimum requested
inputs and next assigned action; no broader question is silently closed.

## Current clarification — 2026-10-01 / D-062

The owner relayed sponsor confirmation of aggregated ownership `>= 25%` with
`GREATER_THAN_OR_EQUAL_TO`. Q-004 remains open only for complete legal/control,
evidence and production policy; the bounded threshold itself is no longer provisional.
Existing catalogues and case snapshots keep their historical metadata.

For the current POC, KYC is onboarding/evidence preparation. RM/onboarder Review & Send
confirms the prepared target submission. No separate KYC analyst, compliance approver,
second final approver or mandatory four-eyes step is required. Q-014/Q-016 remain open
for production authority. Ready-for-Approval is not a local prerequisite unless the
actual target API technically requires it; inspected current XPI material does not
establish such a requirement. EDD remains out of scope. These clarifications do not
claim regulatory approval or resolve production workflow questions.

Local risk remains advisory: LOW continues, MEDIUM warns and continues, and HIGH may
request justified RM attention. Probability alone is not a hard blocker. The owner's
report of built-in GoldTier scoring is not verified API screening ownership. Q-017 and
Q-007 still require current XPI PEP/sanctions/adverse-media/risk/wealth/funds ownership,
requiredness, permitted source and optionality. Workbook presence is not an API minimum.

## POC IDENTITY, TEAM ACCESS, AND PRIORITY POLICY

### Q-016 - Production identity, role, assignment, and prioritisation policy

Should Client Onboarder and Relationship Manager have different mutation permissions,
and which roles may change priority? Are only priority values 1–3 permitted, and is 1
or 3 the highest/most urgent value? Who assigns or changes priority, and does it affect
routing, SLA, escalation, notification, due dates, risk, or any other downstream
behaviour? What downstream behaviour is authorized? Who may reassign a case, what
reason/history must be retained, and may one case be shared across teams or hold
multiple team memberships? Is Director globally read-only or permitted existing
mutations? What production IdP, SSO/session, RBAC, and identity-governance model is
expected?

Pending an explicit sponsor answer, Phase 13 uses project-defined POC behavior: roles
differ only in team/global visibility; any actor with case access may use existing
mutations and change priority; Director has global visibility and the same mutation
surface; there is no reassignment or sharing; priority affects ordering only; and local
scrypt credentials plus process-local sessions are demo-only. These rules do not resolve
the production policy requested here.

For current manual UAT, the UI uses project-defined provisional Low/Medium/High/Unset
labels. It preserves the nullable 1–10 API/Mongo field: Low writes 1, Medium writes 5,
High writes 10, and legacy reads map 1–3/4–7/8–10 to Low/Medium/High. This presentation
has no risk, SLA, routing, escalation, approval, or regulatory meaning and does not
resolve Q-016.

Phase 14.5 adds a synthetic HR administrator, persistent team/profile records,
capability-driven navigation, immediate local-session revocation after authority
changes, and Director-only server-side team filters. Relationship Manager and Director
may edit the two already-provisional runtime thresholds, which are snapshotted onto new
cases. These remain project POC decisions and do not answer the requested production
identity governance, separation of duties, policy ownership, or sponsor-approved
threshold questions.

### Q-017 - Supplied risk input and workflow authority

For a supplied LOW/MEDIUM/HIGH risk input, who is the authoritative producer, which
vocabulary and validation rules apply, and what evidence/provenance must accompany it?
Who may update it, what retention is required, and which workflow reactions are
permitted or required? Please define any EDD or human-approval authority and whether
risk may block readiness. The system must not invent a calculated risk score.

The pre-Phase 22 feature candidate adds a separately and permanently labelled
`MOCK_ADVISORY_RISK / NOT_COMPLIANCE_DECISION` projection using only available local POC
evidence. Its thresholds and optional readiness-review flag are project-defined,
case-bound, editable defaults; the flag defaults false. This does not answer who owns a
supplied risk input, authorize EDD/approval, or resolve Q-017.

### Q-018 - Production Zero-Touch / GoldTier deployment and handoff boundary

For production, should Zero-Touch remain an external service or operate inside or
alongside GoldTier? Where is the handoff point, which state and evidence transfer, who
owns the target-side continuation, and what production identity and audit implications
apply?

## ACRA SANDBOX BINDING AND ACCESS

### Q-012 - Authoritative ACRA Business Profile API contract and access

Please provide or identify the authoritative subscriber documentation for the ACRA
Business Profile / Entity Information Query API used by this POC, including the
sandbox base URL, company-by-UEN operation path, request/response schema, not-found and
error semantics, authentication/authorization mechanism, timeout/rate-limit guidance,
and any TLS/mTLS/private-CA requirements.

Please also confirm that the team has an authorized subscription/sandbox account and
deliver any required credential only through an approved secret mechanism. This blocks
exact subscriber-contract binding and live ACRA sandbox verification. It does not block
the Phase 02 connector/auth/decoder interfaces, synthetic contract tests, or Mock ACRA
mode.

Phase 06 now treats every adapter result as untrusted, reconstructs the source DTO,
requires returned/requested UEN identity, and retains only query-free HTTPS endpoint
provenance. This is a fail-closed POC boundary and does not identify or confirm the live
ACRA endpoint, authentication, or subscriber contract requested here.

Phase 10 adds separate entity-profile, officer, ownership-party, and relationship
operations only as project-owned Mock contracts with conservative bounds and synthetic
fixtures. Please additionally confirm whether these are separate subscribed operations,
their authoritative schemas/role and relationship vocabularies, pagination/limits, and
empty/partial semantics. The sandbox-shaped adapter fails closed for the new operations;
their Mock behavior is not evidence that these endpoints exist in ACRA.

Q-012 is now **PARTIALLY RESOLVED** for the official API Marketplace Mock only. The
supplied Postman exports and the explicitly authorized 2026-09-26 run confirm OAuth2
Client Credentials at the exact Mock token endpoint, HTTP Basic client authentication,
an empty JSON request body, and raw downstream header name `token` (not Bearer). The
observed successful token JSON has exactly `access_token` string, `expires_in` integer,
`scope` string, and `token_type` string fields.

The same bounded run observed successful strict Mock interoperability for
`entityBasicInformation` and `coShareholdersDetails` using approved Mock identities.
Garden entity identity matched. SIM LIM shareholder identity matched and supplied
share-count evidence. Garden shareholder retrieval returned an explicit empty entities
collection, so the local synthetic Garden chain is not provider evidence. A separate
capital sample exposed issued/paid-up capital, allotted-share, currency, and share-type
fields, but it did not establish a same-entity, compatible denominator for the observed
shareholders. The sanitized receipt retains no UEN values, raw payload, credentials,
token/header values, or provider error text.

Q-012 remains **OPEN** for authoritative not-found and provider-error schemas, token
failure schema, rate/timeout/retry guidance, mTLS/private-CA requirements if any,
pagination and collection limits, complete officer/address/constitution semantics,
same-entity capital/share-class denominator semantics, relationship/control semantics,
and all subscriber Sandbox, Production, and Live contracts. The canonical
`api_marketplace_mock` lane is opt-in `MOCK_INTEROPERABILITY_OBSERVED`; it is not
Sandbox or Live, and missing ownership relationships continue to fail closed.

Slice B rechecked the supplied seven-page Entity Information Query sample catalogue
as candidate discovery only. SECOND_OFFICIAL_COMPANY = BLOCKED_BY_SAMPLE_AUTHORITY.
The catalogue supplies no coherent same-UEN basic/profile pair; prior observed second
basic identities classify OTHER or BUSINESS_PARTNERSHIP without a retained full profile
contract suitable for deterministic onboarding. Shareholder/member/group and capital
sample identifiers with empty basic identities cannot be combined across UENs.

Please supply a coherent same-UEN basic/profile sample with legal name, legal form,
required address/country semantics and supported operation/empty/unsupported behavior.
Quantitative ownership is not a prerequisite when reviewed LOCAL supplementary ownership
is used. Garden remains PARTNERSHIP; officer roles are not percentage/control/UBO authority.
Partnership ownership, relationship/control schemas and same-entity denominator semantics
remain OPEN. Slice B made zero external calls and substitutes an explicitly labelled
existing SYNTHETIC MOCK second journey.

## JURISDICTION EVIDENCE AUTHORITY

### Q-015 - Jurisdiction source precedence, disagreement, and review authority

When jurisdiction observations are available from user input, an existing case/system,
uploaded documents/IDP, identifier format, or a future upstream provider, which sources
are authoritative and under what conditions? When two sources disagree, which
authenticated role may resolve the conflict, what evidence/correction must be retained,
and may the case resume or must it be restarted/re-submitted?

Phase 09 does not guess this policy. It retains active observations, resolves only
agreement, and stops conflicts with no browser resolution action. The omitted-country
Singapore UEN rule is explicitly recorded as `IDENTIFIER_FORMAT -> SG`, not treated as
a hidden source-precedence decision. Foreign jurisdictions are recognised only enough
to stop as provider not implemented; no foreign registry is selected or called.

Phase 11 extends the same no-precedence rule to legal name, registration identifier,
registered address, and country of incorporation. The POC retains Registry, Document,
and available request observations separately and requires an explicit bounded operator
decision for usable conflicts. `USE_DOCUMENT_VALUE` is limited to a safely validated
legal-name update; this is a project implementation boundary, not sponsor approval that
Document or Registry is authoritative. Please still confirm source authority by field,
authenticated reviewer role/separation of duties, permitted missing/invalid/confidence
decisions, retained audit evidence, and restart-versus-resume policy. Q-015 remains OPEN.

Phase 12 supplies only technical single-instance Mongo restart durability and
conservative target replay prevention. It does not answer who may decide, what must be
retained/deleted, whether this storage is an approved audit record, or the production
operational restart policy. Those parts of Q-015 remain OPEN.

## A. BLOCKING REAL GOLDTIER INTEGRATION

### Q-008 — Authentication containment and replacement

Please confirm that the credentials/tokens previously supplied in the PingFed/Postman
collection have been rotated or revoked, and provide a sanitised collection containing
no credential, token, client secret, certificate, or authentication value.

When real sandbox integration begins, please provide fresh credentials only through an
approved secret-delivery mechanism. Also confirm the sandbox EDS base URL, PingFed token
URL, granted scopes, client-authentication method, and any mTLS/private-CA requirement.

The supplied collection will not be used, tested, copied, or sanitised in place. This
blocks real GoldTier authentication but does not block Phase 01 mocks.

## B. NEEDED FOR LATER FUNCTIONAL PHASES

### Q-001 — Ready-for-Approval transition

What exact GoldTier action/state transition moves a successfully populated Singapore
NTB customer to the Ready-for-Approval / four-eye-check stage? Is it automatic after
the agreed EDS calls, or is another workflow API/action required?

Phase 05 therefore ends at `MOCK_GOLDTIER_SUBMITTED` after the Mock base operations and
does not claim or expose an achieved Ready-for-Approval transition.

### Q-002 — Seeded hierarchy retrieval

Which GoldTier endpoint/schema should the UI use to retrieve the seeded multi-level
corporate hierarchy, ownership links, and UBO-related data for the complex demo?

Phase 04 therefore uses only a credential-free provider-neutral Mock graph. No GoldTier
hierarchy route, schema, identifier, pagination, or provenance behavior is inferred.

### Q-003 — IDP document target

Which document types must the final IDP demo process—for example, a trust deed,
partnership agreement, or ACRA/business-profile PDF—and which exact fields must be
extracted from each?

### Q-004 — UBO threshold rule

The bounded default threshold/comparator is **RESOLVED** by D-062 on 2026-10-01:
aggregated ownership `>= 25%`, `GREATER_THAN_OR_EQUAL_TO`, sponsor-confirmed through
the owner's current clarification. What legal/control tests, evidence standards and
production jurisdiction/policy conditions complete the final UBO determination?

Historically, the Phase 04 development default was labelled project-defined/provisional.
That label is superseded for the bounded default threshold and comparator only. Existing
historical metadata remains readable; it must not be treated as a complete legal
controller test or production policy, or as negating the newly confirmed default.

### Q-005 — Validation responsibility split

Which validation/business rules belong in the EDS/orchestration layer and which should
be delegated to GoldTier's seeded policy/rule configuration?

Pending confirmation, Phase 05 uses a conservative project POC rule: canonical ACRA
data remains the base submission source, reviewed document evidence must agree for
automatic Mock submission, and any conflicting correction/rejection is blocked as
`SOURCE_CONFLICT_REQUIRES_POLICY` without overwriting either source.

Phase 06 likewise treats `REVIEWED` as lifecycle completion rather than authority. An
explicit `KEEP_REGISTRY_VALUE` decision clears only that journey's source-conflict
blocker and is recorded separately; extracted and reviewed evidence remains unchanged.
This does not answer which source should become master data.

### Q-013 — Document privacy, retention, and upload security

Please confirm the data classification and lawful test-data source for each Phase 03
document type, together with allowed environments, retention/deletion schedule,
encryption and storage-jurisdiction requirements, reviewer access controls, and whether
malware scanning/content-disarm or an approved PDF processing service is required.

The current foundation retains no uploaded bytes or raw provider output. It retains a
validated display name that is never used as a filesystem path. The local POC now combines
bounded size/type checks with strict PDF structure parsing and bounded in-memory DOCX
package/path validation before IDP. These controls remain neither antivirus/CDR nor
production document security and do not resolve the requested sponsor policy.

### Q-014 — Confidence and authenticated review policy

Please confirm the sponsor-approved extraction confidence policy, including whether the
threshold is overall, per field, document-type-specific, or tiered; which conflict or
missing-field conditions require review; permitted reviewer decisions; reviewer role
and authentication; separation-of-duties requirements; and audit-retention rules.

The Phase 03 default `0.85` threshold, four-field profile, deterministic comparison,
all-field completion rule, and unauthenticated local accept/reject/correct control are
project-only POC behavior and are not approval or Ready-for-Approval semantics.

Phase 08 replaces the normal synthetic path's scenario-selected values with actual
text-PDF extraction and project-defined parser confidence (unique primary label `0.97`,
alternate label `0.90`, ambiguity `0.40`, missing `0.00`). This deterministic POC
method does not resolve the approved field, confidence, reviewer, privacy, retention,
or source-authority policy requested above.

### Q-007 — Singapore mapping sign-off

Which subset of candidate GoldTier EDS Data Dictionary field/value-list mappings is
approved for the Singapore ACRA NTB POC? The workbook states that its joins are
automatically inferred and not a confirmed data contract. Please confirm Singapore
entity-specific conditional fields, values, proof-category codes, and ACRA mappings
before they become implementation assertions.

The 2026-09-28 XPI Garden Amend sent only the guideline minimum
`goldTierId=143878` and `policy=Singapore`; the provider task audit ended
`Valdiation Failed` without a failed-field reason. Please confirm whether XPI customer
Amend conditionally requires ANZSIC, group-company data, a later Policy state, or another
field; whether Singapore SSIC is supported when industry classification is required;
and the exact safe retry/idempotency and atomic no-application semantics after a
provider-verified validation failure. No ANZSIC/SSIC or group-company value will be
invented while this remains unanswered.

Phase 04 synthetic party/relationship fields and `SHARE_OWNERSHIP` basis are source-
neutral POC concepts only and do not resolve or pre-empt these GoldTier mappings.

## C. CONTRACT ARTEFACT CORRECTIONS

### Q-006 — `createRelatedParty` direct-link semantics

When `POST /v1/eds/related-parties` succeeds for a direct/first-level related party, is
the parent relationship persisted atomically? Please confirm the minimum relationship
inputs. The API specification lists `rpRole` as mandatory, standalone OpenAPI defines
relationship fields without marking them required, and older specification text says
the operation does not auto-link. This question does not propose `createRelationship`
or multi-level hierarchy creation.

Phase 04 performs no related-party write. Its ownership relationships are provider
results used only for local deterministic analysis and are not a model of this operation.

Phase 05 likewise performs no related-party write. It reports only a minimized internal
preparation summary with `PENDING_SPONSOR_CONFIRMATION` and
`RELATED_PARTY_WRITE_NOT_EXECUTED`.

Please also confirm the authoritative `childId` lifecycle before any related-party
dispatch:

1. What does `childId` represent in the GoldTier XPI related-party endpoints?
2. Is `childId` the GoldTier party ID of the related party?
3. How is `childId` created for a related party not already in GoldTier?
4. Is there a related-party Shell/create endpoint not included in the supplied collection?
5. If the related party already exists, how should it be searched or retrieved?
6. How is the relationship between the parent customer and child party created or identified?
7. What relationship-type/value vocabulary should be used?
8. Can one related party be associated with multiple customers?
9. What are the retry/idempotency semantics for related-party Policy and Amend?
10. What evidence is sufficient to reuse an existing `childId`?

Until all dependent authority is supplied, `BLOCKED_CHILD_ID_LIFECYCLE` remains a
contract blocker. The project performs zero related-party network calls and will not
substitute the parent ID or generate a local/random child ID.

### Q-009 — Authoritative values and casing

Where corrected standalone OpenAPI enums and JSON examples conflict, which values and
casing are authoritative? This affects at least `sourceContext.sourceChannel`,
`relationshipProfile.rpRole`, proof/source metadata, address usage, aliases,
client/KYC types, gender, booking entity, workflow status, and error codes.

The project provisionally uses standalone OpenAPI and quarantines contradictory JSON.
Please confirm that choice or supply corrected operation schemas and examples.

### Q-010 — Mandatory-field authority

Please explicitly confirm that the existing EDS-GoldTier Integration API Specification
should remain authoritative for per-endpoint minimum mandatory fields when corrected
standalone OpenAPI differs.

This currently affects:

- `createShellCustomer.countryOfIncorporation` (listed by the specification but not
  marked required in standalone OpenAPI)
- `createPolicy.customerExternalSystem` and `customerExternalSystemKey` (required by
  standalone OpenAPI but omitted from the specification's minimum list)
- the `amendParty` target identifier (`goldTierId` in the specification versus
  canonical path `partyId` and no duplicate body field in standalone OpenAPI)
- mandatory `createRelatedParty.rpRole` (listed in the specification but not marked
  required in standalone OpenAPI)

`countryOfIncorporation` is provisionally required because of the sponsor's direction
to use the specification. This is not an independently confirmed Singapore policy rule;
its Singapore mapping and allowed values remain part of Q-007.

### Q-011 — Corrected request/response artefacts

Please provide corrected JSON request and response examples that validate against the
confirmed operation schemas/rules, including corrections for:

- the stale create-shell `X-DSD-Case-Id` and `sourceContext.dsdCaseId` forms, replacing
  them with `X-Source-Case-Id` and matching `sourceContext.sourceCaseId`
- the stale combined amend route `/v1/eds/parties/{goldTierId}:amend`
- `createRelatedParty`, `createPolicy`, and `amendParty` request differences
- `retrieveParty`, `getPolicy`, and `createRelatedParty` success responses
- create-shell error and `207` partial responses

Please also confirm whether combined-bundle path-parameter names should be corrected to
the standalone `{partyId}` forms for `retrieveParty` and `getPolicy`.

### GoldTier XPI sandbox continuation — unresolved authority

The separately supplied six-operation XPI guide/collection and bounded no-match Search
observations establish a Partial sandbox dialect only. They do not close the existing
GoldTier questions. Please additionally confirm:

- the approved Singapore values and authority for `kycCustomerType`, `clientSegment`,
  `customerExternalSystem`, `registrationType`, `policy`, `bookingEntity`,
  `accountEntityType`, and `productType` (Q-006/Q-007/Q-009/Q-010);
- strict non-empty Search, create, policy, amend, 400, and 500 response schemas,
  including identifier type/casing and error bodies (Q-011);
- whether and how an authoritative related-party `childId` is created or retrieved,
  whether Amend RP's `goldTierId` is that child identity, and the approved relationship
  vocabularies/semantics (Q-006/Q-009/Q-010);
- the production PingFed/authentication and handoff contract. The collection's
  backend-only `user_id` and `noauth` metadata are sandbox observations, not production
  authority (Q-008/Q-018).

The 2026-09-27 bounded POC clarification and corrected OpenAPI resolve the implemented
Singapore request values to `ACRA`, unchanged UEN, `SG`, `DSD`, `Singapore`, and
`ANZBGL (Singapore Branch)`, plus exact current KYC/Client Segment vocabularies. KYC
and segment remain case decisions unless an approved deterministic mapping is later
provided. This does not establish production vocabulary, automatic SSIC mapping,
related-party lifecycle, or Live status; Q-006/Q-007/Q-009/Q-010 remain open at that
broader authority boundary.

## D. PHASE 06 ZERO-TOUCH CONFIRMATIONS

Phase 06 does not close any question above. For sponsor sign-off, please confirm:

- whether the provisional all-fields-match and per-field `0.85` rule may automatically
  confirm document evidence, and which authenticated role may resolve each exception
  (Q-003/Q-005/Q-013/Q-014);
- whether `KEEP_REGISTRY_VALUE` is an allowed conflict disposition and what corrected
  evidence, audit retention, separation of duties, and escalation actions are required;
- which action, if any, may resolve low-confidence-only or missing-field evidence; the
  remediated POC exposes no action rather than treating registry retention as confidence
  approval;
- how ownership cycle/incomplete evidence is replaced and which definitive UBO rule
  governs automatic continuation (Q-002/Q-004);
- the intended existing-party and partial-amend paths; Phase 06 currently stops before
  any further target write because sponsor semantics are absent (Q-001/Q-006/Q-007);
- the durable workflow, retry, idempotency, reviewer authorization, and audit platform
  required beyond this process-local POC.

Until confirmed, `COMPLETED` means only `MOCK_GOLDTIER_SUBMITTED`; it is never a legal,
compliance, live-system, or Ready-for-Approval claim.

## Post-merge S2 owner boundary — 2026-10-04 candidate

The current explicit owner program permits bounded local OCR, proposed document
ownership, creator-only evidence decisions, calculable pre-submission editing and the
distinct known Garden official-Mock/local supplement. D-062 confirms the >=25% inclusive
numeric POC candidate rule; Review & Send is final approval in this application.
These owner permissions do not close Q-003/Q-004/Q-005/Q-012/Q-013/Q-014/Q-015/Q-016
for production document policy, legal/control/denominator/source authority, retention,
calibrated accuracy, reviewer/maker-checker or Live/provider approval. Existing frozen
0.85 extraction score is a project parameter, not a probability. No new industry default
or external OCR disclosure is introduced. S2 gate and fresh bounded XPI execution are
separate evidence; prior Garden Amend failure remains failed and is never replayed.

## Post-merge S3 bounded observation — 2026-10-04 candidate

The separately authorized synthetic parent acceptance returned HTTP200 for Search2,
Shell1, Policy1 and exact-ID readback1; customer143887 and POLICY_CREATED are retained
under a successful finalized ledger. Application restart preserved confirmed state,
documents and reviewed ownership without new calls. An absent Policy ID remains absent;
Amend was not required. This closes the actual delivery question for this one bounded
synthetic parent package only. It does not establish KYC/approval/RFA, RP child lifecycle,
original-document transfer, production authentication or Live operation, and does not
close Q-006/Q-008/Q-009/Q-010/Q-011/Q-016/Q-018 at those broader authority boundaries.
The smallest future RP need remains a sponsor-confirmed child create/search/readback
lifecycle and relationship semantics; original-file transfer requires an authoritative
upload contract. Neither is inferred or dispatched by this program.
