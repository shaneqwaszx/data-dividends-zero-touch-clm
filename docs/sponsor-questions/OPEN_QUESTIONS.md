# Open Sponsor Questions

Remove or mark a question resolved only after an explicit sponsor answer. These
questions do not block credential-free Phase 01 mock development unless stated.

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

What configurable rule should demonstrate the sponsor's “20–25% UBO” requirement:
`>= 25%`, `> 20%`, jurisdiction/policy-dependent, or another rule?

The Phase 04 development default is `aggregated ownership >= 25%`. Both the value and
inclusive comparator are explicitly project-defined/provisional and must not be treated
as the sponsor's final threshold or complete legal controller test.

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
