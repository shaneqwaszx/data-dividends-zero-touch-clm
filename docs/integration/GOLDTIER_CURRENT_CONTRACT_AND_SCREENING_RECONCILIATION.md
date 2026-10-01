# GoldTier current contract and screening reconciliation

## Superseding original-artifact reconciliation — 2026-10-01

The subsequent original-artifact investigation found both current XPI originals in
`private/sponsor-artifacts-v2`; their hashes match the existing XPI mapping matrix.
The older ANZ authentication collection was structurally inspected under the owner's
new explicit authorization, without reusing embedded credentials. Newer request-level
`noauth` plus backend `user_id` is current direct Sandbox evidence; historical ANZ
Bearer and EDS OAuth2 are distinct routes. The newer guideline explicitly says Policy
creates a policy/account and initiates GoldTier KYC activities. Screening inputs are
absent from the current XPI customer contract; individual screening execution is unproved.

See [GoldTier Contract Closure + Demo Provider Readiness](../development/GOLDTIER_CONTRACT_CLOSURE_AND_DEMO_PROVIDER_READINESS.md)
for the current field/authority and ten-prerequisite matrices. It supersedes the
unavailable-original and unopened-collection statements below for this later session.
Absence of upstream XPI idempotency alone is no longer a fatal prerequisite: the owner
permits durable one-intent/one-dispatch, uncertainty-stop, no-replay and read-only
recovery controls. Unexpected mutation HTTP statuses now preserve uncertainty instead
of resolving a definitive failure. The active durable runtime, meaningful business
readback and conditional Singapore Amend requirements still block mutation acceptance.
No provider call or mutation occurred in this continuation. The following earlier
investigation is preserved as dated history, not the current readiness verdict.

Date: 2026-10-01. Read-only structural reconciliation for the Garden stabilization
continuation. D-062 records the current owner clarification. This document authorizes
no provider mutation, replay, production activation or duplicate screening.

## Authority and inspected sources

Current synchronized source and decisions select the XPI adapter for Singapore
`SANDBOX_PARTIAL`. The EDS contract remains a separate historical/reference and Mock
dialect. No current evidence justifies migrating Sandbox runtime to `/v1/eds`.

| Source | Version/date | Jurisdiction and dialect | Authentication and operations | Authority and disposition |
|---|---|---|---|---|
| Current XPI source, D-048/D-055-D-060 and `GOLDTIER_XPI_MAPPING_MATRIX.md` | 2026-09-24 onward | Singapore POC, XPI Sandbox | Backend-only `user_id`; customer Search, Create, Policy, Amend; RP blocked | Current synchronized implementation and recorded reconciliation; not Live |
| `GoldTier APIs_Guideline.pdf` and `GoldTier APIs.postman_collection.json` | Supplied 2026-09-24; hashes recorded in existing mapping matrix | XPI Sandbox | Six customer/RP operations; collection `noauth` plus `user_id` | Current Sandbox source authority as previously reconciled; original files unavailable in the inspected explicit directory this session |
| `private/sponsor-artifacts/gt_eds_openapi_yaml_final.zip` | Corrected standalone OpenAPI 1.0.0 | EDS, broader historical contract | OAuth2 client credentials; seven `/v1/eds` operations | Standalone machine authority for EDS/reference and selected vocabularies; not proof of current Sandbox transport |
| `private/sponsor-artifacts/EDS-GoldTier_Integration_API_Specification.docx` | Draft; metadata 2026-07-14/17 | EDS | Mandatory-field overlay, audit and idempotency | Historical EDS authority within recorded precedence; do not transplant into XPI |
| `private/sponsor-artifacts/GoldTier_EDS_Data_Dictionary.xlsx` | Cover A5: 2026-07-14 | ANZ UI/EDS mapping | Derived mappings and value-list references | Workbook supporting evidence; Cover A4 identifies a Claude-assisted BA session, not an approved API-requiredness contract |
| `private/sponsor-artifacts/GoldTier-XPI-Connection-Guide.pdf` | Historical inventory available by 2026-08-10 | Historical connection reference | Production/security reference in existing baseline | Cannot override the later Sandbox dialect reconciliation; not re-extracted for current operation authority |
| `private/sponsor-artifacts/gt_eds_api_specs_json.zip` | Historical supplied examples | EDS | Minimum/full examples and reusable objects | Supporting examples only; contradictory examples remain INVALID / QUARANTINED |

The dictionary references original `GT_DataMapping_ANZ.xlsx` at Cover A8. That original
workbook was not present in the explicitly inspected sponsor directory or either
inspected archive. No broader parent/sibling/private scan was performed. The
credential-bearing authentication collection was not opened. No raw sponsor payload,
credential, customer record or value-list contents are reproduced here.

## Screening and field ownership

Safe read-only workbook inventory: Cover & Methodology; Customer Overview; Customer
Individual; Customer Non-Individual; RP Overview; RP Individual; RP Non-Individual;
Value Lists. Object-sheet headers A:M identify label, system ID, domain, table/column,
schema, request notes, API field/path, endpoints, mapping confidence and value lists.
There is no independent current-XPI requiredness column. Mapping confidence is not
authority or requiredness. Embedded value lists do not override corrected OpenAPI.

| Subject | Exact dictionary cells | Historical standalone EDS result | Current XPI classification and conclusion |
|---|---|---|---|
| Source of funds/wealth | Customer Individual A25, G25, H25, J25, K25; Customer Non-Individual A72, G72, H72, J72, K72 | `Party.individualProfile` and `nonIndividualProfile` source-of-funds/wealth properties are optional in inspected Shell/Amend schemas | NOT_IN_CURRENT_CONTRACT. Historical optional enrichment; not a required current XPI input |
| Sanction location particulars | Customer Individual A33:H34; Customer Non-Individual A96:H97 | `Party.riskProfile.sanctionedLocations` optional; location particulars are not a screening result | NOT_IN_CURRENT_CONTRACT. Current screening ownership requires sponsor confirmation |
| Risk particulars | Customer Non-Individual A14/H14; A76:H77; A71/H71 | High-risk attributes and ECDD applicability optional in inspected EDS structures; no mandatory score established | NOT_IN_CURRENT_CONTRACT. Do not infer risk scoring or build EDD |
| PEP | No direct PEP/politically-exposed field-label match in six object sheets | No PEP property found in inspected Shell/Policy/Amend schemas | NOT_IN_CURRENT_CONTRACT; internal/downstream ownership unproved |
| Adverse media | No direct field-label match in six object sheets | No adverse-media property found in inspected schemas | NOT_IN_CURRENT_CONTRACT; internal/downstream ownership unproved |
| Risk rating/score | No direct rating/score input established by inspected object labels or current DTOs | Risk particulars do not establish a required calculated score | NOT_IN_CURRENT_CONTRACT; do not invent a mapping |
| ANZSIC | Customer Non-Individual A57/H57/L57/M57 | Historical optional particulars | OPTIONAL_BY_CURRENT_API for XPI Amend `anzsic`; Singapore SSIC-to-ANZSIC conversion is not established |
| KYC customer type | Customer Overview A5/G5/H5/J5 | Workbook V3 note; historical mapping | REQUIRED_BY_CURRENT_API guide minimum, corrected 17-value vocabulary; explicit case selection |
| Client segment | Customer Overview A33/H33/J33/L33 | Historical mapping | REQUIRED_BY_CURRENT_API guide minimum, corrected 23-value vocabulary; explicit case selection |
| Policy | Customer Overview A48/H48/J48/L48 | Historical mapping | REQUIRED_BY_CURRENT_API for current Policy/Amend minimum |

For PEP, sanctions, adverse media, risk rating, wealth and funds, conclusion D applies:
absent from the current documented XPI input contract. Conclusion E also applies to
ownership: current evidence does not establish whether GoldTier owns downstream
screening, whether another contract requires EDS input, or whether optional enrichment
is accepted. Absence of an input is not proof of internal screening. No duplicate
screening or guessed field follows. Q-007/Q-017 remain open for those questions.

The inspected EDS draft contains no screening/wealth/funds or Ready-for-Approval
requirement. Its optional schema fields and workbook rows do not establish a current
XPI requirement. KYC remains POC evidence preparation; final RM/onboarder confirmation
is submission confirmation. No second local approval or EDD workflow is required.

## Fresh synthetic customer plan — prepared, not dispatched

Use a new uniquely allowlisted synthetic identity, never Garden or a real customer.
The exact identity and classification choices must be bound to one reviewed case;
the document does not preselect a business value. Backend metadata and credentials
remain private. Every operation is owned by the existing target ledger.

| Operation | Fields and value source | Authority/requiredness | Expected local response boundary | Retry and uncertain outcome |
|---|---|---|---|---|
| Search | Unique synthetic `legalName`, canonical `countryOfIncorporation=SG`; optional exact `goldTierID` for readback only | Guide/collection; one criterion minimum; no registration-number query invented | Bounded HTTP 200 list; zero candidates proves NO_MATCH for supplied criteria | Read-only bounded budget; no automatic provider retries or enumeration |
| Shell | Canonical reviewed legal name, UEN, SG and represented address; `registrationType=ACRA`; case external key; `customerExternalSystem=DSD`; explicitly selected KYC type and segment | Canonical reviewed evidence plus D-056/D-057; six policy prerequisites; guide minimum and local canonical/address controls | HTTP 200 with safe provider-issued ID retained durably; missing/ambiguous ID is uncertain | One authorized attempt only; no replay after uncertain response; stop all later mutations |
| Policy | Exact retained Shell ID, same external key, `DSD`, `Singapore`, `ANZBGL (Singapore Branch)`; account/product empty unless explicitly supported | D-055/D-056 immutable case policy; account/product compatibility-optional | Current decoder accepts HTTP 200 and optional policy ID; upstream business completion contract remains incomplete | One attempt only; uncertain outcome stops; 200 alone is not approval or policy activation |
| Amend | Exact retained provider ID and `policy=Singapore`; omit ANZSIC/group data without explicit authority | Guide minimum, D-056; conditional Singapore requirements remain Q-007 | Current local decoder recognizes HTTP 200; provider business validation/readback semantics remain incomplete | One attempt only; no replay of uncertain/failed history without authoritative no-application/retry evidence |
| Readback | Search with exact durably retained `goldTierID` | D-057, existing ledger owner | One candidate with exact same ID; other outcomes fail closed | Read-only budget; no mutation replay. Identity existence alone does not prove Policy/Amend business fields |

Contact, group-company, address type and industry data are not invented. The current
preview uses the canonical/target mapper, never direct ACRA-to-XPI conversion.
All required evidence, reconciliation, supplementary ownership, classification and
explicit reviewed confirmation must complete before a case can reach dispatch.

## Eight mandatory pre-mutation prerequisites

| Prerequisite | Evidence required before dispatch | Current limitation |
|---|---|---|
| Authoritative current Sandbox dialect | Current source plus sufficient upstream XPI authority | Recorded reconciliation supports XPI; current original guide/collection unavailable here |
| Required mapping | Exact reviewed fields, requiredness and immutable source authority | Conditional Singapore Amend requirements unresolved |
| Screening ownership | Required PEP/sanctions/adverse fields not omitted; sufficiently understood ownership | Mandatory inputs not established; internal/downstream ownership unproved |
| Synthetic Search NO_MATCH | Actual bounded Search of the new allowlisted identity | A dry-run or another identity's result is insufficient |
| Process-only write enablement | Explicit per-session opt-in after safety gate | Never persistently enable or infer from Search success |
| Durable target ledger | Active durable ledger owns every operation and restart/no-replay intent | Memory-only ledger is insufficient; physical-test Mongo permission does not authorize a mutation-acceptance database |
| Confirmed idempotency/no-replay semantics | Current XPI upstream duplicate/uncertain semantics plus durable local stopping | EDS Idempotency-Key semantics are not XPI authority; provider duplicate suppression remains unproved |
| Independent PRE-MUTATION safety PASS | Exact reviewed plan/content and prerequisites independently PASS | Not a general Quality Gate or retrospective approval; no dispatch while any prerequisite is missing |

Latest conditional budgets are Search <=2, Shell <=1, Policy <=1, Amend <=1, and
readback/Search <=2 for the new allowlisted customer. Related-party, Garden and
production writes remain zero. These conditional caps do not waive any prerequisite.
Separate base-prompt read-only Search verification remains independently authorized.

## Idempotency, response and Garden limits

EDS documents `Idempotency-Key`, identical-body replay and conflict handling. Current
XPI transport sends `user_id` and correlation metadata, not a provider idempotency key.
Local ledger no-replay stopping is not proof of upstream duplicate suppression. Never
combine the dialect guarantees. Query success cannot clear this prerequisite.

Current XPI non-200 mutations are locally projected as controlled failure; authoritative
atomic/no-application guarantees are not established. Policy permits optional policy ID
and Amend locally accepts HTTP 200. These decoder boundaries do not by themselves prove
the complete external business lifecycle. Sanitized provider evidence must remain
separate from local tests and current response-contract limitations.

Garden retains historical uncertain Shell, recovered Policy Requested evidence and
failed Amend. Search by retained ID may collect read-only evidence but name alone cannot
prove exact identity. Skip Shell only through authoritative existing-identity evidence
and the current resolver. D-059's Requested state proves a Policy request exists; it
does not prove approval, completion or activation. Neither a new fixture nor a new case
authorizes replaying Garden Shell/Policy/Amend history. No Garden write is permitted by
the overnight conditional authorization.


## 2026-10-01 bounded demo acceptance clarification

D-063 records the owner's revised acceptance: fresh customer Search/NO_MATCH,
Shell with durable provider ID, Policy operation success, optional supported reviewed
Amend, and exact-identity readback. No supported enrichment means `AMEND_NOT_REQUIRED`
and zero Amend dispatches. Historical validation failure remains disclosed above.
The fresh sanitized contract gate is
[FINAL_PROVIDER_SANITIZED_CONTRACT_GATE.md](../development/FINAL_PROVIDER_SANITIZED_CONTRACT_GATE.md).
It supersedes the historical gate only for the new sanitized review; it does not undo
the prior inspection incident. Search proves customer identity, while Policy result
supplies Policy-operation evidence. No downstream screening or KYC completion claim is
permitted. Production/Live, Ready-for-Approval and final compliance approval remain
outside this bounded acceptance.
