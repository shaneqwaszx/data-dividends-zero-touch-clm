# GoldTier Contract Discrepancy Catalogue

## Purpose and interpretation

This catalogue records material disagreements in the Phase 00 sponsor evidence. It
does not assert that Delta Capita has corrected any source artefact. The provisional
development authority is the policy in `AGENTS.md`: direct sponsor clarification
first; standalone OpenAPI for machine structure; and the sponsor-directed API
specification for explicitly stated per-operation mandatory fields.

`Safe to use in Phase 01?` means safe for **credential-free mock development under
the provisional contract**, not safe for real GoldTier integration. A `NO` means the
conflicting source item is quarantined and must not drive fixtures, DTO enums, or
contract assertions.

Artefact abbreviations:

- **Standalone:** corrected operation YAML in `gt_eds_openapi_yaml_final.zip`
- **Combined:** `gt-eds-openapi-bundle.yaml` in that ZIP
- **JSON:** file in `gt_eds_api_specs_json.zip`
- **Specification:** EDS-GoldTier Integration API Specification

## Paths, headers, and shared context

| Operation | Artefact/file | Field/path/value | Conflicting value | Provisional development authority | Reason | Sponsor confirmation required? | Safe to use in Phase 01? |
|---|---|---|---|---|---|---|---|
| `amendParty` | Combined | Route | `/v1/eds/parties/{goldTierId}:amend` | Direct clarification + standalone: `POST /v1/eds/parties/{partyId}/amend` | Latest direct clarification is conclusive; combined bundle is stale. | NO | NO |
| `retrieveParty` | Combined | Path-parameter name | `{goldTierId}` | Standalone: `{partyId}` | Standalone controls corrected path/property names. | YES | NO |
| `getPolicy` | Combined | Path-parameter name | `{goldTierId}` | Standalone: `{partyId}` | Standalone controls corrected path/property names. | YES | NO |
| `amendParty` | Combined vs standalone response schemas | `200` and `207` target identifier | Combined uses top-level `goldTierId`; standalone uses top-level `partyId` | Standalone response schemas: `partyId` | Standalone controls response property names for canonical mocks. | YES | NO for the combined form |
| `amendParty` | Combined vs standalone request schemas | Optional `party` object identifier | Combined defines optional `party.goldTierId`; standalone defines optional `party.partyId`; the remaining optional party shape is otherwise aligned for this identified difference | Standalone request schema: `party.partyId` | Standalone controls machine property names. | YES | NO for the combined form |
| `amendParty` | Combined vs standalone embedded examples | Full request and `200`/`207` response identifier | Combined full request uses `party.goldTierId` and response examples use `goldTierId`; standalone uses `party.partyId` and `partyId`. The minimum request examples have no corresponding identifier difference | Standalone request/response schemas | Embedded examples follow their conflicting schemas and cannot override standalone machine authority. | YES | NO for the combined examples |
| `retrieveParty` | Combined vs standalone response schemas and embedded success example | Top-level and nested party identifier | Combined uses `goldTierId` and `party.goldTierId`; standalone uses `partyId` and `party.partyId` | Standalone response schema: `partyId` at both levels | Standalone controls canonical mock response property names. | YES | NO for the combined form |
| `getPolicy` | Combined vs standalone response schema and embedded success example | Top-level party identifier | Combined uses `goldTierId`; standalone uses `partyId` | Standalone response schema: `partyId` | Standalone controls canonical mock response property names. | YES | NO for the combined form |
| `createShellCustomer` | JSON `full_request.json` | Header | `X-DSD-Case-Id` | Standalone/specification: `X-Source-Case-Id` | DSD-specific form is stale and conflicts with the generic EDS contract. | YES | NO |
| `createShellCustomer` | JSON `full_request.json`, `request_body.json` | `sourceContext.dsdCaseId` | Uses stale property and omits `sourceCaseId` | Standalone: `sourceContext.sourceCaseId`, matching `X-Source-Case-Id` | Standalone property is required and rejects the stale additional property. | YES | NO |
| All POST operations | JSON minimum examples plus related-party, policy, and amend full/body examples | `sourceContext.sourceChannel` | Example value is outside the standalone enum | Standalone enum: `EDS_API`, `API`, `PORTAL`, `BATCH`, `EVENT`, `MANUAL` | Standalone controls enums; contradictory examples are quarantined. | YES | NO |

## Mandatory-field disagreements

| Operation | Artefact/file | Field/path/value | Conflicting value | Provisional development authority | Reason | Sponsor confirmation required? | Safe to use in Phase 01? |
|---|---|---|---|---|---|---|---|
| `createShellCustomer` | Specification vs standalone `createShellCustomer.yaml` | `party.nonIndividualProfile.countryOfIncorporation` | Specification lists it mandatory; standalone does not mark it required | Specification mandatory-field overlay | Sponsor explicitly directed the team to the specification's per-endpoint mandatory fields. This is not an independently confirmed Singapore rule; Singapore mapping/value-list validation remains open. | YES | YES, as provisional required input |
| `createPolicy` | Standalone `createPolicy.yaml` vs specification | `customerExternalSystem`, `customerExternalSystemKey` | Standalone marks both required; specification's business-minimum table omits both | Standalone machine-validation contract: both are provisionally required in canonical Phase 01 mock requests | Standalone required properties determine schema-valid mocks. Whether Delta Capita considers them part of the business minimum remains open and is not sponsor-confirmed policy. | YES | YES, provisionally required for canonical mocks |
| `amendParty` | Specification vs standalone `amendParty.yaml` | Mandatory `goldTierId` | Specification names it; standalone uses mandatory path `partyId` and has no body property | Canonical path `partyId` is the mandatory target identifier; do not invent a rejected duplicate body field | Direct route decision and standalone shape must coexist with the sponsor-directed minimum-input statement. | YES | YES only as mandatory canonical path identifier |
| `createRelatedParty` | Specification vs standalone `createRelatedParty.yaml` | `party.relationshipProfile.rpRole` | Specification lists `rpRole` mandatory; standalone defines it but does not mark it required | Specification mandatory-field overlay; standalone enum/shape | Sponsor explicitly directed use of specification mandatory fields. | YES | YES, using standalone enum/casing |
| `createRelatedParty` | JSON minimum/full/body vs specification/standalone | Relationship input set | Examples add nested parent/relationship details; older specification says operation does not auto-link; latest clarification supports direct/first-level relationships | Direct clarification for supported level; specification overlay for mandatory `rpRole`; standalone for shape | Atomic persistence and remaining conditional fields are not settled. | YES | YES only for a direct mock relationship, not atomic-link claims |

## Request schema and enum disagreements

| Operation | Artefact/file | Field/path/value | Conflicting value | Provisional development authority | Reason | Sponsor confirmation required? | Safe to use in Phase 01? |
|---|---|---|---|---|---|---|---|
| `createRelatedParty` | JSON minimum/full/body and `response_success.json` | `party.relationshipProfile.rpRole` / returned role | Uppercase/underscore values and casing differ from schema | Standalone enum (`Director`, `Owner`, `UBO`, `Authorised Signatory`, `Senior Management`, `Other`) | Machine enum authority is standalone. | YES | NO |
| `createRelatedParty` | JSON full/body | `documentMetadata[].proofCategory` | Value outside standalone enum/casing | Standalone enum | Example fails schema validation. | YES | NO |
| `createRelatedParty` | JSON full/body | `documentMetadata[].sourceSystem` | Combined DSD/EDS label outside standalone enum | Standalone enum | Example fails schema validation. | YES | NO |
| `createRelatedParty` | JSON full/body | `party.addresses[].usage` | Uppercase value differs from standalone label/casing | Standalone enum | Example fails schema validation. | YES | NO |
| `createRelatedParty` | JSON full/body | `party.commonProfile.clientSegment` | Example value outside standalone enum | Standalone enum | Example fails schema validation. | YES | NO |
| `createRelatedParty` | JSON full/body | `party.commonProfile.kycCustomerType` | Example value outside standalone enum | Standalone enum | Example fails schema validation. | YES | NO |
| `createRelatedParty` | JSON full/body | `party.individualProfile.gender` | Uppercase value conflicts with title-case standalone enum | Standalone enum | Example fails schema validation. | YES | NO |
| `createPolicy` | JSON full/body | `policyDetails.bookingEntity` | Short code conflicts with detailed standalone enum label | Standalone enum | Example fails schema validation. | YES | NO |
| `amendParty` | JSON full/body | `documentMetadata[].proofCategory` | Uppercase/underscore values differ from standalone labels | Standalone enum | Example fails schema validation. | YES | NO |
| `amendParty` | JSON full/body | `documentMetadata[].sourceSystem` | Combined DSD/EDS label outside standalone enum | Standalone enum | Example fails schema validation. | YES | NO |
| `amendParty` | JSON full/body | `party.addresses[].usage` | Uppercase/underscore values differ from standalone labels | Standalone enum | Example fails schema validation. | YES | NO |
| `amendParty` | JSON full/body | `party.aliases[].aliasType` | Uppercase/underscore values differ from standalone labels | Standalone enum | Example fails schema validation. | YES | NO |
| `amendParty` | JSON full/body | `party.commonProfile.clientSegment` | Example value outside standalone enum | Standalone enum | Example fails schema validation. | YES | NO |
| `amendParty` | JSON full/body | `party.commonProfile.kycCustomerType` | Example value outside standalone enum | Standalone enum | Example fails schema validation. | YES | NO |
| `amendParty` | JSON full/body | `policy.policyContext.bookingEntity` | Short code conflicts with detailed standalone enum label | Standalone enum | Example fails schema validation. | YES | NO |
| `searchParty` | JSON `full_request.json`, `request_parameters.json` | Optional person-name and birth-date query values | Explicit `null` values supplied where schemas are non-null strings/date | Standalone parameter schemas | Optional parameters must be omitted rather than supplied as null. | YES | NO |
| `createShellCustomer` | JSON full/body | `documentMetadata[].proofCategory` | Uppercase/underscore value differs from standalone label | Standalone enum | Example fails schema validation. | YES | NO |
| `createShellCustomer` | JSON full/body | `documentMetadata[].sourceSystem` | Combined DSD/EDS label outside standalone enum | Standalone enum | Example fails schema validation. | YES | NO |
| `createShellCustomer` | JSON full/body | `party.addresses[].usage` | Natural-language value differs from standalone enum label | Standalone enum | Example fails schema validation. | YES | NO |
| `createShellCustomer` | JSON full/body | `party.commonProfile.kycCustomerType` | Example value outside standalone enum | Standalone enum | Example fails schema validation. | YES | NO |
| `createShellCustomer` | JSON full/body | `party.workflowContext.status` | Natural-language value outside standalone status enum | Standalone enum | Example fails schema validation. | YES | NO |

## Response disagreements

| Operation | Artefact/file | Field/path/value | Conflicting value | Provisional development authority | Reason | Sponsor confirmation required? | Safe to use in Phase 01? |
|---|---|---|---|---|---|---|---|
| `createRelatedParty` | JSON `response_success.json` | Relationship role value/casing | Does not validate against standalone response enum | Standalone response schema | Correct shape/enum must be derived from standalone, not the example. | YES | NO |
| `retrieveParty` | JSON `response_success.json` | Proof/source/address/alias/client/KYC/policy/source-channel enum families | Multiple example values/casing fail standalone response schema | Standalone response schema | Response example cannot be a canonical fixture. | YES | NO |
| `getPolicy` | JSON `response_success_getpolicy.json` | `policies[].policyContext.bookingEntity` | Short code conflicts with detailed standalone enum label | Standalone response schema | Response example cannot be a canonical fixture. | YES | NO |
| `createShellCustomer` | JSON `response_error_problem_detail.json` | `errors[].code` | Generic example code outside standalone error-code enum | Standalone `ProblemDetail` response schema | Error example cannot be a contract assertion. | YES | NO |
| `createShellCustomer` | JSON `response_partial_207.json` | `sections[].errors[].code` | Example code outside standalone error-code enum | Standalone `207` response schema | Partial response example cannot be a contract assertion. | YES | NO |

## Behavioural disagreements and limitations

| Operation | Artefact/file | Field/path/value | Conflicting value | Provisional development authority | Reason | Sponsor confirmation required? | Safe to use in Phase 01? |
|---|---|---|---|---|---|---|---|
| `createRelatedParty` | Older specification vs latest sponsor clarification | Relationship behaviour | Older text says the call does not auto-link; latest clarification says direct/first-level relationships are supported | Latest direct clarification | Direct support is settled; atomic link persistence is not. Multi-level creation remains unsupported. | YES, for atomicity only | YES for direct mock behaviour only |
| `createRelatedParty` | Future JSON `99_future_createRelationship/*` | Separate operation | Future examples could imply a current eighth operation | Confirmed seven-operation scope and decision D-014 | `createRelationship` is outside current scope and must not be implemented. | NO | NO |
| All operations | Combined vs corrected standalone | Schema/property/enum differences | Combined contains stale/lower-confidence structures where operation files differ | Corrected standalone operation OpenAPI | Corrected standalone controls machine validation. | YES | NO |
| All operations | JSON shared/reusable objects | Operation binding | Objects are not deterministically tied to a request/response schema | NOT VALIDATED | Treating them as valid would overstate automated coverage. | YES where promoted later | NO as canonical fixtures |

## Resolution state

The catalogue makes Phase 01 mock development safe by identifying the exact authority
and quarantining conflicting evidence. It does not make real integration safe. Contract
corrections, fresh authentication material, and environment details remain sponsor
actions.

## XPI sandbox dialect supplied 24 September 2026

The separately supplied `GoldTier APIs_Guideline.pdf` and
`GoldTier APIs.postman_collection.json` define a six-operation XPI sandbox dialect.
They are primary evidence for the bounded XPI continuation only and do not silently
replace the historical EDS-shaped Mock or production/PingFed contract.

| Concern | Historical provisional EDS contract | Supplied XPI sandbox evidence | Current disposition |
|---|---|---|---|
| Paths | `/v1/eds/...` seven-operation catalogue | `/gt-xpi/v1/customers/...` and `/gt-xpi/v1/relatedParties/...` six-operation catalogue | Separate XPI adapter/DTO dialect; preserve Mock behavior. |
| Search | Registration-number-oriented Mock request | `goldTierID`, `legalName`, `groupCompanyName`, `countryOfIncorporation`; registration number is not enabled in the collection | Do not rename the Mock DTO. Treat XPI registration-number search as unsupported pending confirmation/observation. |
| Request headers/auth shape | OAuth2/correlation/source/idempotency provisional EDS contract | Collection requests are `noauth` and carry `Content-Type` plus `user_id` | `SPONSOR_SUPPLIED` sandbox behavior only. Never infer that production GoldTier has no authentication. |
| Shell/policy/amend bodies | Nested EDS `party`, `policyDetails`, `sourceContext` shapes | Flat XPI customer bodies with different target enrichment fields | Strict XPI-specific DTOs and mapper; no direct ACRA-to-XPI payload mapping. |
| Related-party lifecycle | Historical direct first-level operation semantics | Create RP Policy requires both parent `goldTierId` and `childId`, but no operation creates or explains the child identity | Local request transformation may be implemented; external RP execution remains blocked on the child-ID lifecycle. |
| Responses | Project Mock response models | Collection contains no response examples; guide gives only general 200/400/500 descriptions | Decode only sanitized observed shapes; unknown/malformed responses fail closed. |

The complete field-level reconciliation and unresolved questions are recorded in
`docs/integration/GOLDTIER_XPI_MAPPING_MATRIX.md`. Example business values remain
supporting sponsor-supplied sandbox inputs and are not production policy or canonical
fixtures.
