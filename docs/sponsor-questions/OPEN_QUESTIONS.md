# Open Sponsor Questions

Remove or mark a question resolved only after an explicit sponsor answer. These
questions do not block credential-free Phase 01 mock development unless stated.

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

### Q-002 — Seeded hierarchy retrieval

Which GoldTier endpoint/schema should the UI use to retrieve the seeded multi-level
corporate hierarchy, ownership links, and UBO-related data for the complex demo?

### Q-003 — IDP document target

Which document types must the final IDP demo process—for example, a trust deed,
partnership agreement, or ACRA/business-profile PDF—and which exact fields must be
extracted from each?

### Q-004 — UBO threshold rule

What configurable rule should demonstrate the sponsor's “20–25% UBO” requirement:
`>= 25%`, `> 20%`, jurisdiction/policy-dependent, or another rule?

### Q-005 — Validation responsibility split

Which validation/business rules belong in the EDS/orchestration layer and which should
be delegated to GoldTier's seeded policy/rule configuration?

### Q-007 — Singapore mapping sign-off

Which subset of candidate GoldTier EDS Data Dictionary field/value-list mappings is
approved for the Singapore ACRA NTB POC? The workbook states that its joins are
automatically inferred and not a confirmed data contract. Please confirm Singapore
entity-specific conditional fields, values, proof-category codes, and ACRA mappings
before they become implementation assertions.

## C. CONTRACT ARTEFACT CORRECTIONS

### Q-006 — `createRelatedParty` direct-link semantics

When `POST /v1/eds/related-parties` succeeds for a direct/first-level related party, is
the parent relationship persisted atomically? Please confirm the minimum relationship
inputs. The API specification lists `rpRole` as mandatory, standalone OpenAPI defines
relationship fields without marking them required, and older specification text says
the operation does not auto-link. This question does not propose `createRelationship`
or multi-level hierarchy creation.

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
