# GoldTier Contract Closure + Demo Provider Readiness

Date: 2026-10-01. Local continuation on `fix/demo-happy-path-stabilization`.

## Executive Summary

The located originals close the current direct XPI request/authentication investigation.
The newer guideline and collection are byte-identical to the hashes in the existing
XPI mapping matrix. Direct Sandbox uses backend `user_id` with request-level `noauth`;
the historical Bearer collection targets a different ANZ APIMesh route. Neither
historical EDS OAuth2 nor EDS idempotency is inherited by direct XPI.

The guideline confirms that Create Customer Policy initiates GoldTier KYC activity.
No PEP, sanctions, adverse-media, risk-rating, source-of-wealth or source-of-funds
input occurs in the current four customer-operation contract. This establishes input
absence, not proof that each downstream screening service is configured or executed.

External lifecycle acceptance remains BLOCKED: no active authorized durable acceptance
ledger has been established; Policy/Amend business-state readback is not defined; the
historical Singapore Amend validation failure remains unexplained. No external call,
write, ACRA session, Docker test, Atlas access, commit, push or PR occurs in this run.

## Private Artefacts Reviewed

Inspection is read-only, with Postman values excluded at the read boundary. Original
files remain private and are not copied into tracked paths. No historical credential
or token is reused. One independent PDF-filter output exposed an example `user_id`
header value; this was reported, not repeated or saved into evidence, and inspection
was corrected to names-only projection. No token/client-secret/customer payload was
reported. This incident prevents an unqualified claim of zero private-value exposure.

Primary directory: `private/sponsor-artifacts-v2`:

- `GoldTier APIs_Guideline.pdf`: pages 1-4, operation/minimum/authentication structure.
- `GoldTier APIs.postman_collection.json`: all six request structures, no sample values.
- `JSON_COLLECTION_ENTITY_INFORMATION_QUERY.zip`: bounded member inventory only;
  accepted ACRA evidence is retained; no new ACRA request authority was supplied.

Companion directory: `private/sponsor-artifacts`:

- `GoldTier-XPI-Connection-Guide.pdf`: JWT, scope and configuration structure.
- `GT_API_PingFed_Auth.postman_collection.json`: token/request/header/scope structure.
- `EDS-GoldTier_Integration_API_Specification.docx`: EDS paths/auth/minimum/idempotency.
- `GoldTier_EDS_Data_Dictionary.xlsx`: read-only eight-sheet metadata inspection.
- `gt_eds_api_specs_json.zip`: EDS operation/reusable structure and existing validation.
- `gt_eds_openapi_yaml_final.zip`: corrected standalone EDS schema authority.

Both exact directories were inventoried. No `GT_DataMapping_ANZ.xlsx`, original static
data workbook or separate corrected mapping workbook is retained in either directory.
Other private files were inventoried but not consumed for unrelated questions.
Collection/guideline artifact titles contain no explicit contract version. Guideline
PDF creation metadata is 2026-09-21; prior supplied-date record is 2026-09-24.

## Contract Authority Matrix

| Family/source | Jurisdiction/environment/host | Dialect/auth/operations | Retry and authority |
|---|---|---|---|
| Newer XPI guide + collection | Current Singapore POC; collection Host/Env placeholders, configured direct Delta Capita Sandbox corroborated by accepted observations | `/{Env}/gt-xpi/v1`; four customer and two RP operations; each request `noauth`, `user_id` | AUTHORITATIVE_CURRENT_SANDBOX request/minimum reference under current owner priority; no upstream idempotency/retry guarantee |
| Older XPI connection guide | ANZ token-generator/JWT preference context; exact current direct-host enforcement not specified | JWT issuer/JWKS, action scopes and enablement preferences | OLDER_REFERENCE; cannot prove direct Sandbox needs Bearer; production applicability UNKNOWN |
| Older PingFed collection | ANZ gateway route `/insto/oacb/gt-...`; alternate environment, exact deployment currency unproved | client credentials token operation; Bearer, gateway header names, six XPI operations | OLDER_REFERENCE alternate APIMesh route; not proven CURRENT_ALTERNATIVE_ROUTE or SUPERSEDED |
| EDS specification + corrected standalone OpenAPI 1.0.0 | EDS-facing historical contract; ANZ examples are not SG mapping authority | `/v1/eds`, OAuth2/`eds:*`, sourceContext, seven operations | OLDER_REFERENCE for direct Sandbox; canonical EDS/Mock authority remains; EDS Idempotency-Key belongs only to EDS |
| Dictionary | ANZ UI/database universe; Claude-assisted BA generation 2026-07-14 | Inferred API joins/value lists | Supporting HISTORICAL_EDS_MAPPING or DATA_DICTIONARY_ONLY; confidence is not requiredness |

The newer guide uses the general term APIMesh for exposed APIs. That word does not
override the newer concrete direct URL template and noauth request structure. We do
not declare every APIMesh deployment Bearer-free. No source proves future Production
authentication, supersession of every older deployment, or inherited EDS semantics.

## Current Singapore Sandbox Contract

Current priority: newer direct collection/guideline, D-048/D-055-D-062 and corrected
selected vocabulary decisions, accepted actual observations, non-conflicting older
references. Search is `GET /customers/search`; Shell is `POST /customers/create`;
Policy is `POST /customers/createPolicy`; Amend is `POST /customers/amendCustomer`,
under the direct XPI root. RP Policy/Amend are documented but dispatch remains blocked.

The guideline hash is
`b4fedf629019d17a33c05d74a248fcf4973aef740c491e91dc63ce7d6c06ef55`;
collection hash is
`e0c20335213e15cf566ea45b262e4e3f2c3cd27d326330c2e7c1b73c1a71a708`.
Both match the existing `GOLDTIER_XPI_MAPPING_MATRIX.md` originals.

## Authentication Model

DIRECT_SANDBOX_AUTH_MODEL: request-level `noauth`, backend-injected `user_id`;
the current connector is retained. Accepted actual composed Search evidence supports
`portal.gt.deltacapita.net` / `anz-nutmeg`. Placeholder values in the collection alone
do not establish that concrete host/environment. No Bearer value is used or added.

APIMESH_AUTH_MODEL: historical client-credentials token request with Bearer and ANZ
gateway headers. Safe scope names: `AU.GTSEARCHAPI.WRITE`, `AU.GTSEARCHAPI.READ`,
`AU.GTAPI.CUSTOMER.UPDATE`, `AU.GTAPI.CUSTOMERKYC.CREATE`, `AU.GTAPI.RP.UPDATE`,
`AU.GTAPI.RPKYC.CREATE`. JWT preferences permit action-specific enforcement;
the guide does not establish the current direct host's effective preferences.

PRODUCTION_AUTH_MODEL: UNRESOLVED. Historical JWT/PingFed and EDS references do not
establish a provisioned approved Production runtime.

## GoldTier Field Matrix

Evidence: G1 = newer guideline page 1; G2 = page 2; C = newer request structure;
D = current bounded decisions. R = explicit minimum; O = example/optional; Cnd =
conditional; absent = not in that operation. Example presence alone is not mandatory.

| Field | Search | Shell | Policy | Amend | Requiredness/evidence |
|---|---|---|---|---|---|
| legalName | criterion | R | absent | absent | G1 any-one Search; G2 Shell minimum |
| kycCustomerType | absent | R | absent | absent | G2; D-057 explicit case selection |
| clientSegment | absent | R | absent | absent | G2; D-057 explicit case selection |
| globalRelationshipManagerEmail | absent | O | absent | absent | C only; omitted by mapper |
| customerExternalSystem | absent | R nested systemReference | Cnd | absent | G2 Shell external details; Policy optional depending on scenario |
| customerExternalSystemKey | absent | R nested systemReference | Cnd | absent | G2; same reviewed case binding; local Policy sends both |
| legalRegisteredAddress.type/street1/street2/street3/city/countryIso2/state/zip | absent | O | absent | absent | C only; local canonical minimum requires represented street1/country/zip, distinct from sponsor minimum |
| registration.registrationType | absent | registration details | absent | absent | G2 aggregate minimum; C subfield; bounded D-056 ACRA |
| registration.countryIso2 | absent | registration details | absent | absent | G2/C; D-056 SG |
| registration.registrationNumber | absent | registration details | absent | absent | G2/C; D-056 unchanged UEN |
| contact.name/type/phone/email | absent | O | absent | absent | C only; not invented |
| countryOfIncorporation | criterion | R | absent | absent | G1 any-one; G2 Shell |
| groupCompanyName | criterion | O | absent | Cnd | G1/C; G2 GCN updates as required |
| goldTierID / goldTierId | query criterion goldTierID | response ID | R goldTierId | R goldTierId | G1/G2/C; exact retained target identity |
| policy | absent | absent | R | R | G2; bounded D-056 Singapore |
| bookingEntity | absent | absent | R | absent | G2; bounded D-056 |
| accountEntityType | absent | absent | O | absent | C empty example + D-055; no invented vocabulary |
| productType | absent | absent | O | absent | C empty example + D-055 |
| anzsic | absent | absent | absent | Cnd | G2 as required; no SG conversion/default |
| SSIC | absent | absent | absent | absent | Not a current XPI field; workbook value list is insufficient |
| PEP / sanctions / adverse media | absent | absent | absent | absent | G1/G2/C contain no input fields |
| risk rating | absent | absent | absent | absent | No required calculated score established |
| sourceOfFundsWealth / source of wealth / source of funds | absent | absent | absent | absent | Historical dictionary/EDS do not extend XPI |

Minimum request shapes are established. Conditional Singapore Amend behavior is still
UNRESOLVED: the earlier exact `goldTierId` + `policy` attempt failed provider validation
without field-level reason. That observation does not prove ANZSIC/GCN mandatory.
The current local required address and Policy references are conservative existing
mapping choices, not newly inferred sponsor requirements or proved local defects.

Workbook audit: eight sheets, 112 relevant metadata-row matches, captured with sheet,
row and exact A:M coordinates in ignored task evidence
`tmp/GOLDTIER_CLOSURE_WORKBOOK_MAPPING.json`. All relevant sheets and value-list
labels were searched; original workbook was not modified. Cover A4/A5/A8/A18 establish
assisted provenance/date/original source/automated joins. Key current XPI joins are
Overview A5/B5/H5/I5/J5/K5/L5 (KYC), A33/B33/H33/I33/J33/K33/L33 (segment),
A48/B48/H48/I48/J48/K48/L48 (Policy). Their current requiredness comes from G2.
Historical sourceOfFundsWealth: Individual A25/B25/H25/I25/J25/K25 and
Non-Individual A72/B72/H72/I72/J72/K72. Sanction-location metadata: Individual
rows 33-34, Non-Individual 96-97; high-risk/ECDD: Non-Individual 14,71,76-77;
ANZSIC: Individual 9 and Non-Individual 57, H/I/J/K/L/M columns. These are inferred
HISTORICAL_EDS_MAPPING, not screening-result or current-XPI-required fields. Risk/KYC
database names alone produce incidental matches and no mandatory score. PEP/adverse
labels have no direct object-sheet matches. Value-list presence supplies no API input.

## PEP / Sanctions / Adverse Media

| Subject | Exactly one current-input classification |
|---|---|
| PEP | NOT_IN_CURRENT_XPI_CONTRACT |
| Sanctions | NOT_IN_CURRENT_XPI_CONTRACT |
| Adverse media | NOT_IN_CURRENT_XPI_CONTRACT |
| Risk rating | NOT_IN_CURRENT_XPI_CONTRACT |
| Source of wealth | NOT_IN_CURRENT_XPI_CONTRACT |
| Source of funds | NOT_IN_CURRENT_XPI_CONTRACT |

GoldTier KYC initiation is documented. Specific screening ownership, execution/results
and Production obligations remain unproved. No duplicate local screening, EDD, risk
score or omitted mandatory screening field is inferred from the dictionary.

## KYC Ownership

Guideline page 1 explicitly assigns Policy the creation of a policy/account and
initiation of customer KYC activities. Intended target flow:

`prepare/reconcile -> RM Review & Send -> Shell -> Policy -> GoldTier KYC activity
initiated -> Amend/enrichment -> readback`.

The current early read-only Search remains before ACRA under D-058/D-061. The target
sequence above starts after evidence preparation. Initiation is not KYC completion,
screening acceptance, account activation, approval or Ready-for-Approval. No new local
KYC analyst, compliance approver or four-eyes workflow is added.

## Local Code Remediation

The original connector treated every non-200 mutation, including 500/503/redirect,
as a definitive validation failure. Nine failing-first Shell/Policy/Amend regressions
proved that it resolved the ledger instead of preserving uncertainty. Minimal guard
now treats statuses outside the existing 200/400 boundary as uncertain, stops later
operations and prevents replay. HTTP 400 remains a controlled validation rejection;
this does not assert upstream rollback and provides no automatic retry permission.

Fresh strict mypy exposed legacy reconstruction of an initial identity from a nullable
canonical legal name. A narrow null guard now preserves the existing identity-edit
eligibility check without constructing an invalid identity. No schema/CAS/persistence
owner is changed. Source/testing identities are recorded in the closure manifest.

## GoldTier Connection

Existing config/composition, XPI DTO/decoder, mapper/preview, HR console and target
ledger were inspected. Sandbox selection has no Mock fallback. HTTPS certificate
verification, TLS 1.3, redirects disabled, timeout default 10s bounded at 30s, response
default 128 KiB bounded at 1 MiB, backend-only headers and write opt-in remain intact.
The two prior HTTP 200 synthetic NO_MATCH Searches are accepted unchanged. This run
uses zero new Search/read/write calls. Policy 200 allows an absent policy ID and Amend
200 supplies no proven business-state envelope. Same-ID Search readback proves target
identity existence, not Policy/account/KYC/Amend persistence.

## Mutation Prerequisite Matrix

| # | Prerequisite | Result | Reason |
|---|---|---|---|
| 1 | Current XPI dialect | PASS | Originals match recorded hashes and current request paths |
| 2 | Current auth | PASS | Direct request metadata + accepted two actual Searches; separate ANZ Bearer route |
| 3 | Shell minimum | PASS | G2/C/D-056/D-057; case inputs must still be reviewed/frozen |
| 4 | Policy fields | PASS | G2 minimum plus D-055/D-056; no EDS fields imported |
| 5 | Amend fields | UNRESOLVED | Minimum proven; historical SG validation failure has no reason or conditional rule |
| 6 | PEP/screening ownership sufficiently settled | UNRESOLVED | Current-input absence is proven and KYC initiation explicit; specific downstream screening ownership/execution remains unproved |
| 7 | Mutation uncertainty / duplicate controls | PASS for supported local design | Intent/attempt markers before dispatch, lock/CAS, uncertain stop, no replay, read-only recovery; new unexpected-status guard; not upstream exactly-once |
| 8 | Active durable ledger | FAIL | No authorized durable acceptance runtime established; memory insufficient; Atlas untouched |
| 9 | Meaningful resulting-state readback | UNRESOLVED | Current same-ID Search cannot prove Policy/Amend business state |
| 10 | Fresh synthetic identity | UNRESOLVED | Prior untouched synthetic identity has accepted NO_MATCH; exact newly reviewed durable case/allowlist not yet established; no new Search budget inferred |

No upstream XPI idempotency guarantee is required by assumption. Its absence alone
is not fatal under the latest user instruction. Durable one-intent/one-dispatch/
uncertainty-stop/no-blind-replay/read-only-recovery controls are required instead.
Historical EDS replay guarantees are never claimed for XPI. This matrix remains
insufficient for a pre-mutation PASS; no write is dispatched.

## Pre-Mutation Independent Verdict

NOT RUN as an authorizing gate because required prerequisites are not all PASS.
The independent reviewer is asked to validate the safety design and blockers, not
to waive them. Prior conditional write authorization remains bounded and unused;
Garden/RP/Production writes remain zero. No external deletion or cleanup is proposed.

## ACRA Exact Network Acceptance

BLOCKED_AUTHORIZATION. No fresh session authority accompanies this prompt. Prior
transport/auth evidence is accepted; prior exact-case completion remains unproved.
The checkpointing harness is retained. Captured replay is not network acceptance.

## Physical Mongo

Accepted 38/38 physical PASS retained. No persistence/schema/CAS/runner change is made
in this continuation; no Docker rerun or physical database access. Atlas is untouched.
That accepted physical evidence does not constitute an active durable target runtime.

## Demo Composition

ACRA: official networked API Marketplace Mock opt-in, authorized sessions only.
IDP: actual local PDF-text extraction. Ownership: one deterministic Decimal engine
with explicitly reviewed client evidence when registry evidence is incomplete.
GoldTier: actual direct XPI Sandbox read verified; full normal target lifecycle
blocked. Local Mock remains the truthful offline test/CI demonstration target pending
acceptance. Persistence: explicit memory/Mongo modes; no silent fallback; no active
acceptance Mongo runtime established in this task. Desired full provider composition
cannot yet truthfully be enabled as accepted normal sponsor-demo behavior.

## Test Evidence

Incoming accepted candidate: 61 paths, digest
`11fc4d703a845b7bc0412154aceb7f595091b2e428c490c9e398246debd244ff`, verified unchanged
before edits. Branch/HEAD/local origin/main/base are unchanged at
`efc31f450f0103766fa812bc0aa80754f801dbe9`; index empty. No remote-main freshness claim.

Nine new safety regressions failed before the guard; XPI suite 92 PASS afterwards.
Fresh contract suite 44 PASS; Ruff PASS; strict mypy with `--no-incremental` PASS for
112 files after the null guard. Final backend suite: 1,503 PASS, 38 opt-in physical
SKIP, zero failures/errors, 1,541 collected. Architecture, provider-readiness and
secret checks PASS. Project-state remains PREEXISTING_GOVERNANCE FAIL because its
documented verified-main SHA is not reachable from the accepted local origin/main.
Previously accepted frontend 381, Garden browser 5,
typecheck/build and physical 38 are retained because their source is unchanged.
Ordinary suites use dotenv-disabled memory/mock settings with Mongo construction
forbidden. No private original becomes a fixture. No upstream calls are made by checks.

## Final Independent Verdict

Independent local implementation verdict: PASS. Contract/auth/field technical
conclusions: PASS. Full contract/auth/field gate: FAIL because the review-process
read-boundary incident violated the names-only output requirement; it cannot be undone
or certified as zero exposure. Full requested external acceptance: FAIL / BLOCKED.
No remaining reproducible in-scope local defect was found. See
`GOLDTIER_CONTRACT_CLOSURE_QUALITY_GATE.md` for exact frozen candidate identity,
independent checks and remaining external blockers.
Independent report is outside the implementation freeze. No local acceptance claim
is promoted to a complete provider lifecycle claim.

Change impact: API/types unchanged; schema/persistence/CAS unchanged; connector error
classification changed; config/auth/header/mapping/business-rule unchanged; no new
architecture owner; documentation clarifies existing KYC boundary; runtime now
preserves mutation uncertainty for unexpected HTTP statuses; provider remains Partial.
Publication is not requested or authorized.

## Final Capability Matrix

| Capability | Result |
|---|---|
| ACRA OFFICIAL MARKETPLACE MOCK | Transport/auth VERIFIED; accepted prior observations |
| EXACT NETWORK GARDEN | BLOCKED; new session authorization absent |
| GOLDTIER SANDBOX READ | VERIFIED; accepted two actual Searches |
| GOLDTIER SANDBOX WRITE CONTRACT | BLOCKED for full acceptance; documented minima/auth established |
| GOLDTIER FULL LIFECYCLE | BLOCKED; durable runtime/readback/conditional Amend prerequisites |
| PEP / SANCTIONS / ADVERSE MEDIA | NOT_IN_CURRENT_XPI_CONTRACT; execution not verified |
| KYC | GoldTier Policy initiates activity; completion not verified |
| PHYSICAL MONGO | PASS; accepted 38/38 retained |
| NORMAL DEMO PROVIDERS | Desired full network composition remains blocked |
| PRODUCTION/LIVE | NOT CLAIMED |
| PUBLICATION | NOT REQUESTED |
