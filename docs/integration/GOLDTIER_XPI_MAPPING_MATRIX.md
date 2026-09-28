# GoldTier XPI Sandbox Mapping Matrix

## Status and evidence boundary

This matrix reconciles the existing provider-neutral case/target owners with the
read-only sponsor files supplied on 24 September 2026:

- `GoldTier APIs_Guideline.pdf`, SHA-256
  `b4fedf629019d17a33c05d74a248fcf4973aef740c491e91dc63ce7d6c06ef55`;
- `GoldTier APIs.postman_collection.json`, SHA-256
  `e0c20335213e15cf566ea45b262e4e3f2c3cd27d326330c2e7c1b73c1a71a708`.

The files define a six-operation **XPI sandbox dialect**. They do not replace the
historical EDS-shaped Mock contract, establish production authentication, resolve
Q-001/Q-006/Q-007/Q-009/Q-010/Q-011/Q-018, or authorize a Live claim. Example values
are supporting `SPONSOR_SUPPLIED` sandbox inputs only; they are not copied into this
matrix or treated as production business policy.

Status vocabulary: `ACRA_PROVIDER_EVIDENCE`, `SPONSOR_EXAMPLE`,
`USER_AUTHORIZED_POC`, `PROJECT_DEFINED_POC`, `PROVIDER_OBSERVED`, `DIRECT`,
`DERIVED`, `SPONSOR_SUPPLIED`, `SANDBOX_OBSERVED`, `TARGET_POLICY`,
`MANUAL_ENRICHMENT`, `PROJECT_DEFINED_PROVISIONAL`,
`INDUSTRY_PRACTICE`, `TBD_SPONSOR`, `UNSUPPORTED`, `CONFLICT`.

## Contract differences from the historical Mock dialect

| Concern | Historical EDS-shaped Mock owner | Supplied XPI sandbox evidence | Reconciliation |
|---|---|---|---|
| Operation family | `searchParty`, shell, policy, amend under `/v1/eds/...` | Six `/gt-xpi/v1/...` customer/related-party operations | Keep separate adapter DTOs; do not rename or weaken the Mock DTOs. |
| Search identity | Registration number | Any one of `goldTierID`, `legalName`, `groupCompanyName`, `countryOfIncorporation` | XPI search has its own strict query DTO. Registration number is `UNSUPPORTED` until observed or confirmed. |
| Request headers | Correlation/source/idempotency headers in provisional Mock contract | `Content-Type` and `user_id`; each collection request is `noauth` | Treat only as `SPONSOR_SUPPLIED` sandbox behavior; do not infer production no-auth. Correlation remains an internal safe ledger identifier. |
| Shell body | Nested `party` and `sourceContext` | Flat customer fields plus nested address/registration/contact/system reference | XPI mapper consumes canonical target input and an immutable target-enrichment snapshot. |
| Policy body | Nested `policyDetails` and `sourceContext` | Flat customer/policy/account/product fields | Separate XPI DTO; no Mock behavior change. |
| Amend body | Path identifier plus EDS amendment object | Flat `goldTierId`, `policy`, optional `anzsic`/group-company data | Separate XPI DTO; ANZSIC is never inferred from ACRA. |
| Related party | Historical first-level EDS contract | Policy/amend calls require an existing `childId`/related-party identity | Local transformation is permitted; external execution is blocked until the child-ID lifecycle is proved. |
| Response schema | Strict project Mock response models | No response examples in the collection; the guide provides only general 200/400/500 guidance | Strict XPI decoders must be based on sanitized sandbox observations and fail closed on unknown/malformed shapes. |

## Field matrix

`Required?` distinguishes guide-stated minimums from fields that merely occur in the
collection example. `Source authority` names the authority for the mapping, not the
authority of an example value. `Default/policy` never contains a sponsor value.

The detailed rows preserve the implementation status recorded at the initial contract
reconciliation. The 24 September closure overlay is authoritative for current code:

- Customer Search DTO/transport supports the four supplied aliases; the case mapper
  deliberately dispatches legal name plus country only. Registration-number search is
  unsupported and group-company search has no current case-field owner.
- Customer Shell, Policy, and Amend strict DTOs, canonical/target-policy mapper,
  response projection, explicit composition, request preview, and existing-ledger
  execution are implemented and covered locally.
- Legal name, registration identity, incorporation country, represented registered-
  address components, and a case-bound synthetic external key are mapped directly or
  system-derived. Contact, group-company, address type, and ANZSIC are omitted.
- Eight target values are implemented as authority-labelled, immutable per-case policy
  fields. `registrationType=ACRA`, `customerExternalSystem=DSD`, `policy=Singapore`,
  and `bookingEntity=ANZBGL (Singapore Branch)` are fixed for this bounded POC. KYC
  Customer Type and Client Segment are write-once per-case selections from the exact
  corrected OpenAPI 1.0.0 vocabularies. The collection sends `accountEntityType` and
  `productType` as empty;
  unresolved placeholders for those two fields therefore serialize as explicit empty
  strings for this bounded sandbox dialect and do not become inferred vocabulary.
- Related-party strict DTOs are implemented locally. External RP dispatch remains
  blocked on `childId` lifecycle and relationship-value authority.

## Current Singapore POC value classification

| Resulting target field | Current value/source | Classification | Dispatch treatment |
|---|---|---|---|
| `legalName` | Canonical legal name from the official ACRA Marketplace Mock entity profile | `ACRA_PROVIDER_EVIDENCE` | Required; no sample substitution |
| `registration.registrationNumber` | Canonical Singapore UEN, unchanged | `ACRA_PROVIDER_EVIDENCE` | Required; never converted to ABN |
| `countryOfIncorporation`, `registration.countryIso2` | Canonical Singapore jurisdiction `SG` | `ACRA_PROVIDER_EVIDENCE` | Required |
| `registration.registrationType` | `ACRA` | `USER_AUTHORIZED_POC` | Required for this bounded POC; UEN remains the unchanged registration number and ABN is prohibited |
| `legalRegisteredAddress` | Canonical ACRA registered address when available | `ACRA_PROVIDER_EVIDENCE` | Required by the current local canonical minimum |
| `customerExternalSystem` | `DSD` | `SPONSOR_DOCUMENTED` | Fixed for this bounded sandbox POC; not ACRA evidence |
| `kycCustomerType` | One exact corrected OpenAPI 1.0.0 value selected per case | `USER_AUTHORIZED_POC` | Blocks Shell while unresolved; no global default |
| `clientSegment` | One exact corrected OpenAPI 1.0.0 value selected per case | `USER_AUTHORIZED_POC` | Blocks Shell while unresolved; no global default |
| `policy` | `Singapore` | `SPONSOR_DOCUMENTED` | Fixed for this bounded POC and Amend |
| `bookingEntity` | `ANZBGL (Singapore Branch)` | `USER_AUTHORIZED_POC` | Fixed bounded POC choice; not universal future policy |
| `accountEntityType`, `productType` | Explicit empty collection example | `SPONSOR_EXAMPLE` | Serialize empty for this sandbox dialect only |
| Search `NO_MATCH / 0` for the intended SG identity | Real `anz-nutmeg` XPI response | `PROVIDER_OBSERVED` | Permits the Shell branch only after all other prerequisites are satisfied |

### Corrected OpenAPI 1.0.0 machine vocabularies

The current Client Segment vocabulary has 23 values:

`Corporate`; `DI - Diversified Industrials`; `DI - Education and Defence`;
`DI - Food, Beverage, and Agribusiness`; `DI - Government`;
`DI - Telecom, Media, Entertainment, and Technology`; `DI - Transport and Logistics`;
`FIG - Banks`; `FIG - Diversified Financials`; `FIG - Funds`; `FIG - Insurance`;
`FIG - OSU`; `Global Subsidiary Group`; `Private Wealth`; `Property and Health`;
`Resource, Energy, and Infrastructure`; `Retail`;
`Commercial BB (Business Banking)`; `Commercial RBB (Regional Business Banking)`;
`Commercial SBB (Small Business Banking)`; `Corporate Finance`;
`Diversified & Specialist Industries`; `Personal`.

The current KYC Customer Type vocabulary has 17 values:

`Association - Incorporated`; `Association - Unincorporated`; `Co-Operative`;
`Company - Private`; `Company - Public`; `Government`; `Individual`; `Managed Fund`;
`Partnership - Regulated`; `Partnership - Unregulated`;
`Regulated Financial Institution`; `Regulated Fund Manager - ANZ Approved`;
`Regulated Fund Manager - Non-ANZ Approved`; `Sole Trader`; `Trust - Regulated`;
`Trust - Unregulated`; `Unregulated Fund Manager`.

The older DD18 list is historical and conflicting: its additional values are not merged
into either current list. Contradictory examples remain `INVALID / QUARANTINED`.

| Current owner | Current field | Input/source field | Canonical field | XPI operation | XPI field | Transformation | Required? | Source authority | Default/policy | Validation | Sandbox observation | Initial implementation status | Status | Remaining question / blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Target execution ledger | retained target result | prior Shell/Search result | target party identity | Customer Search | `goldTierID` | Strict trimmed identifier query | Any one search field | Sponsor guide + collection | None | Nonblank, bounded, query encoded | HTTP 200 empty array for a safe impossible ID | Adapter DTO required | `SANDBOX_OBSERVED` | Exact non-empty result envelope and ID type |
| Canonical entity | `legal_name` | reconciled Registry/Document evidence | `legal_name` | Customer Search | `legalName` | Preserve reconciled value; strict query encoding | Any one search field | Sponsor guide + collection; current canonical owner | None | Nonblank, bounded, control-free | HTTP 200 empty array alone and with `countryOfIncorporation=SG` | Adapter DTO/mapping required | `SANDBOX_OBSERVED` | Match/case/fuzzy semantics |
| Target enrichment | group-company value | explicit user/policy input only | None | Customer Search | `groupCompanyName` | Use only explicit enrichment | Any one search field | Sponsor guide + collection | No implicit default | Nonblank when present | HTTP 200 empty array for a unique synthetic value | Preparation field required | `SANDBOX_OBSERVED` | Owner and permitted vocabulary |
| Canonical entity | `country_of_incorporation` | reconciled Registry/Document evidence | `country_of_incorporation` | Customer Search | `countryOfIncorporation` | Canonical jurisdiction to ISO-2 text | Any one search field | Sponsor guide + collection; ACRA canonical mapping | None | Exactly two ASCII letters | HTTP 200 empty array in combination with synthetic `legalName` | Adapter DTO/mapping required | `SANDBOX_OBSERVED` | Other valid multi-field combinations |
| Canonical entity | `registration_number` | ACRA/reconciled registration identity | `registration_number` | Customer Search | No enabled collection parameter | No dispatch mapping | Not documented | Supplied collection | None | N/A | Not executed: ignored-parameter risk could expose broad data | Deliberately omitted | `UNSUPPORTED` | Does XPI support registration-number search? |
| Canonical entity | `legal_name` | reconciled Registry/Document evidence | `legal_name` | Shell Record | `legalName` | Preserve canonical value | Guide minimum | Sponsor guide + collection; current canonical owner | None | Nonblank, bounded, control-free | Pending | Mapper required | `DIRECT` | None once DTO bounds are confirmed locally |
| Existing policy/snapshot owner | target classification | authorized case selection | None | Shell Record | `kycCustomerType` | Copy the write-once case value | Guide minimum | Corrected OpenAPI 1.0.0 vocabulary | No global default | Exact 17-value membership; block unresolved/frozen changes | Pending external lifecycle | Case endpoint/snapshot implemented | `USER_AUTHORIZED_POC` | Production selection authority/automatic mapping |
| Existing policy/snapshot owner | target classification | authorized case selection | None | Shell Record | `clientSegment` | Copy the write-once case value | Guide minimum | Corrected OpenAPI 1.0.0 vocabulary | No global default | Exact 23-value membership; block unresolved/frozen changes | Pending external lifecycle | Case endpoint/snapshot implemented | `USER_AUTHORIZED_POC` | Production selection authority/automatic mapping |
| Existing policy owner | target enrichment rule | explicit target policy | None | Shell Record | `globalRelationshipManagerEmail` | Copy only explicit enrichment | Collection example only | Collection supporting evidence | No implicit default | Email syntax, bounded, control-free | Pending | Optional preparation field | `TBD_SPONSOR` | Requiredness and approved source |
| Target preparation | external-system name | case-bound target policy | None | Shell Record | `systemReference.customerExternalSystem` | Copy fixed target-system label | Guide minimum as part of external-system details | Sponsor material | Fixed `DSD` | Exact closed value | Sponsor documented | Snapshot/rule implemented | `SPONSOR_DOCUMENTED` | Production value/owner; never claim ACRA supplied it |
| Canonical entity | `registration_number` | ACRA/reconciled registration identity | `registration_number` | Shell Record | `systemReference.customerExternalSystemKey` | Use the case's canonical registration identifier or an explicit unique synthetic key for diagnostic execution | Guide minimum | Sponsor guide + collection + current identity owner | No generated business default | Nonblank, bounded, control-free; bind to case | Pending | Mapper required | `DERIVED` | Whether production requires a different external key |
| Canonical entity | registered address | reconciled canonical address | `registered_address` | Shell Record | `legalRegisteredAddress.street1/city/state/zip/countryIso2` | Map only represented canonical components; omit unsupported empty optional lines | Collection example only | Collection supporting evidence; current canonical owner | None | Country ISO-2; bounded control-free text | Pending | Mapper required | `DIRECT` | Requiredness and address-type vocabulary |
| Target enrichment | address usage/type | explicit target policy/manual value | None | Shell Record | `legalRegisteredAddress.type` | Copy only explicit value | Collection example only | Collection supporting evidence | No implicit default | Nonblank when present | Pending | Optional preparation field | `TBD_SPONSOR` | Approved vocabulary |
| Target enrichment | registration type | explicit bounded POC authority | None | Shell Record | `registration.registrationType` | For SG only, emit exact `ACRA`; never substitute ABN | Registration details are a guide minimum; this subfield's requiredness is not explicit | Corrected OpenAPI 1.0.0 + explicit POC authority | Fixed `ACRA` | Exact closed value | Awaiting provider mutation validation | Snapshot/rule implemented | `USER_AUTHORIZED_POC` | Production applicability remains open |
| Canonical entity | `country_of_incorporation` | reconciled Registry/Document evidence | `country_of_incorporation` | Shell Record | `registration.countryIso2` | Canonical jurisdiction to ISO-2 text | Registration details are a guide minimum | Sponsor guide + collection; ACRA canonical mapping | None | Exactly two ASCII letters | Pending | Mapper required | `DIRECT` | None for current SG route |
| Canonical entity | `registration_number` | ACRA/reconciled registration identity | `registration_number` | Shell Record | `registration.registrationNumber` | Preserve canonical identifier | Registration details are a guide minimum | Sponsor guide + collection; ACRA canonical mapping | None | Nonblank, bounded, control-free | Pending | Mapper required | `DIRECT` | None |
| Target enrichment | contact | explicit synthetic/manual contact | None | Shell Record | `contact.*` | Omit unless an authorized synthetic/manual value is supplied | Collection example only | Collection supporting evidence | No implicit default | Type-specific bounded fields; never real customer data in diagnostic | Pending | Optional DTO field | `MANUAL_ENRICHMENT` | Requiredness, privacy and approved source |
| Canonical entity | `country_of_incorporation` | reconciled Registry/Document evidence | `country_of_incorporation` | Shell Record | `countryOfIncorporation` | Canonical jurisdiction to ISO-2 text | Guide minimum | Sponsor guide + collection; ACRA canonical mapping | None | Exactly two ASCII letters | Pending | Mapper required | `DIRECT` | None for current SG route |
| Target enrichment | group-company value | explicit user/policy input only | None | Shell Record | `groupCompanyName` | Omit unless explicitly supplied | Collection example only | Collection supporting evidence | No implicit default | Nonblank when present | Pending | Optional DTO field | `MANUAL_ENRICHMENT` | Requiredness and source |
| Target ledger | Shell result | Shell response | target party identity | Create Customer Policy | `goldTierId` | Bind exact decoded Shell ID | Guide required | Sponsor guide + collection | None | Nonblank, bounded; bind to Shell result | Pending | Mapper/decoder required | `SANDBOX_OBSERVED` | Response envelope and ID field spelling/type |
| Target preparation | external-system name | case-bound target policy | None | Create Customer Policy | `customerExternalSystem` | Reuse the Shell source-system label | Guide: optional depending on scenario; present in collection | Sponsor material | Fixed `DSD` | Exact closed value | Sponsor documented | Snapshot/rule implemented | `SPONSOR_DOCUMENTED` | Production requiredness |
| Canonical entity | `registration_number` | ACRA/reconciled registration identity | `registration_number` | Create Customer Policy | `customerExternalSystemKey` | Bind to the same case external key used for Shell | Guide: optional depending on scenario; present in collection | Sponsor guide + collection | None | Nonblank, bounded, case-bound | Pending | Mapper required | `DERIVED` | Sandbox/production requiredness |
| Existing policy owner | target enrichment rule | explicit target policy | None | Create Customer Policy | `policy` | Copy fixed case snapshot value | Guide required | Sponsor material | Fixed `Singapore` | Exact closed value | Sponsor documented | Snapshot/rule implemented | `SPONSOR_DOCUMENTED` | Production applicability |
| Existing policy owner | target enrichment rule | explicit target policy | None | Create Customer Policy | `bookingEntity` | Copy fixed bounded POC value | Guide required | Sponsor allowed value + explicit POC authority | Fixed `ANZBGL (Singapore Branch)` | Exact closed value | Awaiting lifecycle acceptance | Snapshot/rule implemented | `USER_AUTHORIZED_POC` | Universal future Singapore policy |
| Existing policy owner | target enrichment rule | explicit target policy | None | Create Customer Policy | `accountEntityType` | Copy an explicit sponsor/observed value; otherwise serialize empty | Collection sends explicit empty string; guide does not list it as a minimum | Sponsor collection supporting evidence | Editable, versioned; default placeholder is never dispatched as vocabulary | Empty or bounded control-free text | Pending | Optional sandbox request field | `USER_AUTHORIZED_POC / COLLECTION_OBSERVED` | Production requiredness and sponsor-approved vocabulary |
| Existing policy owner | target enrichment rule | explicit target policy | None | Create Customer Policy | `productType` | Copy an explicit sponsor/observed value; otherwise serialize empty | Collection sends explicit empty string; guide does not list it as a minimum | Sponsor collection supporting evidence | Editable, versioned; default `TBD_SPONSOR` is never dispatched as vocabulary | Empty or bounded control-free text | Pending | Optional sandbox request field | `USER_AUTHORIZED_POC / COLLECTION_OBSERVED` | Production requiredness and approved vocabulary |
| Target ledger | Shell/Search result | decoded target result | target party identity | Amend Customer | `goldTierId` | Bind exact target ID | Guide required | Sponsor guide + collection | None | Nonblank, bounded, identity-bound | Sent once as `143878`; task audit ended `Valdiation Failed` without a failed-field reason | Mapper/decoder implemented | `SANDBOX_OBSERVED` | Provider validation cause and response envelope |
| Existing policy owner | target enrichment rule | fixed case snapshot | None | Amend Customer | `policy` | Reuse exact `Singapore` value | Guide required | Sponsor material | Fixed `Singapore` | Exact match to case snapshot | Sent once as `Singapore`; task audit does not identify Policy or `Requested` state as the cause | Snapshot/rule implemented | `SPONSOR_DOCUMENTED` | Production applicability and provider validation cause |
| No authoritative source | None | no current ACRA-to-ANZSIC mapping | None | Amend Customer | `anzsic` | Omit; require explicit manual/policy enrichment if sandbox proves mandatory | Optional/as required | Sponsor guide + collection | No default | Reject invented/blank value | Omitted in failed request; provider exposed no ANZSIC-specific reason | Omitted by default | `TBD_SPONSOR` | Authoritative SG SSIC/ANZSIC mapping, value and requiredness |
| Target enrichment | group-company value | explicit user/policy input only | None | Amend Customer | `groupCompanyName` | Omit unless explicitly supplied | Optional/as required | Sponsor guide + collection | No implicit default | Nonblank when present | Omitted in failed request; provider exposed no group-company-specific reason | Optional DTO field | `MANUAL_ENRICHMENT` | Requiredness and source |
| Target ledger | parent result | decoded customer identity | target parent identity | Create RP Policy | `goldTierId` | Bind exact parent GoldTier ID | Guide required | Sponsor guide + collection | None | Nonblank, bounded, identity-bound | Pending | Mapper required | `DIRECT` | None after customer response is proved |
| No current owner | None | unknown target child lifecycle | None | Create RP Policy | `childId` | No derivation | Guide required | Sponsor guide + collection | None | Must be a proved existing target child ID | Pending | External execution blocked | `TBD_SPONSOR` | How a new related party is created and obtains `childId` |
| Canonical related party | incorporation country | Registry/ownership evidence when applicable | related-party country | Create RP Policy | `countryOfIncorporation` | Map only when authoritative for that related party | Guide/collection field | Sponsor guide + collection; current evidence owner | None | ISO-2; identity-bound | Pending | Local transformation permitted | `DIRECT` | Requiredness for individual/corporate child types |
| Existing policy owner | target enrichment rule | explicit target policy | None | Create RP Policy | `policy` | Reuse case-bound policy value | Guide required | Sponsor guide + collection | Editable, versioned | Nonblank; block sentinel/missing | Pending | Local transformation permitted | `TARGET_POLICY` | Related-party policy vocabulary |
| Target relationship mapping | relationship type | explicit sponsor/policy relationship semantics | provider-neutral relationship | Create RP Policy | `relationships.relationshipAttribute.relationshipType` | No inference from ownership percentage | Guide required category | Sponsor guide + collection | No implicit default | Nonblank, approved vocabulary only | Pending | Local transformation blocked on authority | `TBD_SPONSOR` | Approved relationship-type mapping |
| Target relationship mapping | relationship titles | explicit sponsor/policy relationship semantics | None | Create RP Policy | `...relationshipTitles` | No inference from ownership percentage | Collection example only | Collection supporting evidence | No implicit default | Bounded list, approved vocabulary only | Pending | Local transformation requires explicit input | `TBD_SPONSOR` | Requiredness and vocabulary |
| Target relationship mapping | boolean relationship attributes | explicit sponsor/policy relationship semantics | None | Create RP Policy | `...receivableFinancing`, `...authorizedSignatory`, `...controller`, `...responsibleEntity` | No derivation from UBO/ownership | Collection example only | Collection supporting evidence | No implicit default | Strict booleans from explicit authority only | Pending | Local transformation requires explicit input | `TBD_SPONSOR` | Meaning, source and requiredness |
| Target relationship mapping | owner type | explicit sponsor/policy relationship semantics | None | Create RP Policy | `...ownerType` | No derivation from ownership percentage | Collection example only | Collection supporting evidence | No implicit default | Approved vocabulary only | Pending | Local transformation requires explicit input | `TBD_SPONSOR` | Meaning and vocabulary |
| Decimal ownership engine | aggregated percentage | authoritative Decimal path result | provisional ownership percentage | Create RP Policy | `...ownerPercent` | Serialize exact Decimal only when relationship semantics are explicitly compatible | Collection example only | Current ownership owner + collection field | None | Decimal 0..100, bounded precision; never legal UBO claim | Pending | Local transformation permitted only with semantic guard | `DERIVED` | Confirm field semantics and comparator |
| Target ledger | related-party identity | proved existing child identity | target child identity | Amend RP | `goldTierId` | Bind exact decoded child ID | Guide required | Sponsor guide + collection | None | Nonblank, bounded, identity-bound | Pending | External execution blocked with child lifecycle | `TBD_SPONSOR` | Whether this is the same identity as Create RP `childId` |
| Target preparation | external-system name | case-bound target policy | None | Amend RP | `customerExternalSystem` | Copy explicit target-system label | Guide says external-system details; collection present | Sponsor guide + collection | Editable, versioned | Nonblank | Pending | Local DTO/mapping permitted | `TARGET_POLICY` | Requiredness |
| Canonical related-party identity | external key | authoritative related-party identifier | None | Amend RP | `customerExternalSystemKey` | Map only from an explicit authoritative child external key | Guide says external-system details; collection present | Sponsor guide + collection | None | Nonblank, identity-bound | Pending | Local mapping blocked on child lifecycle | `TBD_SPONSOR` | Authoritative child external key |
| Existing policy owner | target enrichment rule | explicit target policy | None | Amend RP | `policy` | Reuse case-bound policy value | Guide required | Sponsor guide + collection | Editable, versioned | Nonblank | Pending | Local DTO/mapping permitted | `TARGET_POLICY` | Related-party policy vocabulary |
| Target enrichment | group-company value | explicit user/policy input only | None | Amend RP | `groupCompanyName` | Omit unless explicitly supplied | Collection example only | Collection supporting evidence | No implicit default | Nonblank when present | Pending | Optional DTO field | `MANUAL_ENRICHMENT` | Requiredness and source |

## Execution boundary

- Customer Search is the first permitted network action and is read-only.
- A Shell write is eligible only after an XPI no-match, exact local validation,
  legitimate case-bound target enrichments, a unique synthetic identity, active target
  ledger ownership, and any required managed external-mutation approval.
- Customer Policy and Amend may run only with the exact Shell result and the same
  immutable preparation snapshot. An uncertain write is never replayed.
- Sandbox Amend success must be followed by a ledger-owned Search using exact
  `goldTierID`. Only one returned candidate whose ID equals the retained Shell/Search
  identity completes the target path; no match, a different ID, or multiple candidates
  requires review and never causes mutation replay.
- Related-party request models may be validated locally. External RP execution remains
  `BLOCKED_CONTRACT / childId lifecycle` unless the supplied evidence plus safe sandbox
  observation conclusively establish the lifecycle and all relationship values have
  legitimate authority.
- Sandbox evidence can establish `SANDBOX_OBSERVED` or `SANDBOX / PARTIAL`; it cannot
  establish production authentication, PingFed, Ready-for-Approval, or Live status.
