# GoldTier Provisional Development Contract — Phase 00

## Status and permitted use

**Status: implementation-ready for credential-free Phase 01 mock development only.**

This is a project development contract, not a Delta Capita-confirmed correction of
the sponsor artefacts. Conflicts and sponsor confirmation needs are preserved in
`GOLDTIER_CONTRACT_DISCREPANCIES.md` and `OPEN_QUESTIONS.md`. It must not be used to
claim real GoldTier interoperability, enable sandbox authentication, or promote
quarantined sponsor examples into canonical fixtures.

The evidence boundary covers the latest sponsor clarifications, standalone operation
OpenAPI, combined OpenAPI, JSON examples, EDS-GoldTier Integration API Specification,
GoldTier EDS Data Dictionary, and XPI connection guide available on 10 August 2026.
The supplied authentication Postman collection is credential-bearing quarantined
material and was not used to derive this contract.

## Provisional authority policy

1. Latest direct Delta Capita sponsor clarification is highest authority.
2. Corrected standalone operation OpenAPI governs paths, schema shapes, property
   names, enums, and machine validation.
3. A sponsor direction to a specific artefact governs that specific question. The
   sponsor directed the team to the API specification for per-endpoint mandatory
   fields, so those explicitly listed fields form a provisional mandatory-field
   overlay. Differences from the standalone schema remain documented conflicts.
4. JSON examples are reference examples only when they validate against the resulting
   contract. Invalid examples are quarantined and are not fixture or enum sources.
5. The combined OpenAPI is lower-confidence where it conflicts with corrected
   standalone files or direct decisions.

This ordering is a project decision pending sponsor/API-owner confirmation. The local
validator currently classifies the sponsor JSON suite as **19 VALID, 19 INVALID /
QUARANTINED, and 48 NOT VALIDATED**. The last group consists of shared/reusable or
future-operation objects without a deterministic binding to one of the seven operation
schemas. See `README.md` for the repeatable local command.

## Shared contract

### Transport and authentication

- Real sponsor connectivity requires TLS 1.3 and OAuth2 bearer authentication with
  the operation scopes declared by standalone OpenAPI.
- Expected scopes are `eds:party:read` for party reads, `eds:party:write` for party
  writes, `eds:policy:read` for `getPolicy`, and `eds:policy:write` for `createPolicy`.
- Token/base URLs, client authentication details, grants, certificates, and gateway
  requirements are not approved runtime contract values.
- Supplied credential/token material must not be tested or reused. Real GoldTier
  authentication is blocked until the sponsor confirms rotation/revocation and
  provides fresh credentials through an approved secret-delivery mechanism. A
  sanitised collection may be used later as non-secret reference evidence.
- This containment does not block credential-free Phase 01 mocks.

### Mandatory headers

| Header | Applies to | Rule |
|---|---|---|
| Authorization: Bearer redacted | All operations in real mode | Required OAuth2 bearer token with the relevant operation scope. Never log it. |
| `X-Correlation-Id` | All operations | Required UUID and propagated as the safe tracing identifier. |
| `X-Source-Case-Id` | All operations | Required source case identifier. For POST requests it matches `sourceContext.sourceCaseId`. |
| `Content-Type: application/json` | POST operations | Required. |
| `Idempotency-Key` | POST operations | Required UUID v4. |

`Accept: application/json` is a compatibility default for GETs, not a standalone
mandatory parameter. Older create-shell examples use `X-DSD-Case-Id` and/or
`sourceContext.dsdCaseId`; both are stale. Canonical development requests use
`X-Source-Case-Id` and matching `sourceContext.sourceCaseId`. No canonical fixture may
use the DSD-specific forms.

### `sourceContext`

Every POST body requires the standalone fields:

- `sourceSystem`
- `sourceCaseId`, equal to `X-Source-Case-Id`
- `acceptedBy`
- `acceptedAt`, as UTC ISO-8601

Optional standalone fields include `sourceRequestId`, `sourceChannel`, `submittedBy`,
and `submittedAt`. When supplied, `sourceChannel` must use the standalone enum:
`EDS_API`, `API`, `PORTAL`, `BATCH`, `EVENT`, or `MANUAL`. The JSON examples' conflicting
value is quarantined pending sponsor correction.

### Idempotency, errors, partial success, and audit

- All four POST operations are idempotent by `Idempotency-Key`.
- Replaying an identical canonical payload with the same key returns the original
  outcome; reusing the key for a different body returns `409`.
- Object order and whitespace do not change identity. A retryable `503` may be retried
  with the same key; `429` and `503` can carry `Retry-After`.
- The retention/replay duration is unspecified.
- Errors use the standalone `ProblemDetail` shape and must not expose stack traces,
  infrastructure internals, credentials, or KYC/PII.
- `207 Multi-Status` reports committed valid/core sections and failed optional
  sections. Omitted sections remain untouched; correctable failures can be resubmitted
  through `amendParty`.
- GoldTier audit behaviour is fail-closed as described by the specification. This
  application logs only safe identifiers, statuses, correlation IDs, and sanitised
  summaries—not KYC/PII or request/response payloads.

## Operation contract

### `searchParty`

- **Method/path:** `GET /v1/eds/parties/search`
- **Headers/scope:** shared GET headers; `eds:party:read`
- **Minimum input:** at least one of `legalName`, `registrationNumber`,
  `registrationNumberType`, `externalSystem`, `externalSystemKey`, `lei`, `firstName`,
  `middleName`, `lastName`, or `dateOfBirth`
- **Pagination:** optional `page >= 1`; optional `1 <= pageSize <= 250`
- **Idempotency:** not applicable
- **Success:** `200` with result count, pagination values, party summaries,
  `correlationId`, and timestamp
- **Relevant failures:** `400`, `401`, `403`, `404`, `422`, `429`, `500`, `503`.
  Standalone OpenAPI declares `404`, but the available evidence does not define the
  condition in which GoldTier returns it; mocks must not invent that behaviour
- **Unresolved:** pagination defaults, matching/case/fuzzy semantics, and guaranteed
  no-match behaviour

### `retrieveParty`

- **Method/path:** `GET /v1/eds/parties/{partyId}`
- **Headers/scope:** shared GET headers; `eds:party:read`
- **Minimum input:** non-empty `partyId`; optional `includePolicyDetails`,
  `includeDocumentMetadata`, and `includeFieldMetadata`
- **Idempotency:** not applicable
- **Success:** `200` with `partyId`, party data, requested optional content,
  `correlationId`, and timestamp, using the standalone response schema
- **Relevant failures:** `400`, `401`, `403`, `404`, `422`, `429`, `500`, `503`
- **Unresolved:** seeded hierarchy retrieval uses a separate, still-unconfirmed read
  contract; do not infer hierarchy content here

### `createShellCustomer`

- **Method/path:** `POST /v1/eds/customers/shell`
- **Headers/scope:** shared POST headers; `eds:party:write`
- **Minimum fields:** `party.partyRole`, `party.partyType`,
  `party.names.legalName`, `party.nonIndividualProfile.countryOfIncorporation`, and
  required `sourceContext`
- **Country qualification:** country of incorporation is **required in the provisional
  EDS API contract because the sponsor explicitly directed the team to use the API
  specification's per-endpoint mandatory fields; Singapore-specific mapping/value-list
  confirmation remains pending.** The standalone omission is an artefact discrepancy,
  not permission to remove the field and not an independently confirmed Singapore rule.
- **Idempotency:** shared POST rule
- **Success:** `201` with the new GoldTier identifier, shell/customer and overall
  statuses, `correlationId`, and timestamp; `207` may report optional-section failures
- **Relevant failures:** `400`, `401`, `403`, `404`, `409`, `422`, `429`, `500`, `503`
- **Unresolved:** Singapore entity-specific conditional fields and value-list mapping;
  conflicting JSON success/error/partial enum values remain quarantined

### `createPolicy`

- **Method/path:** `POST /v1/eds/policies`
- **Headers/scope:** shared POST headers; `eds:policy:write`
- **Minimum fields:** canonical Phase 01 mock requests provisionally require
  `goldTierId`, `customerExternalSystem`, `customerExternalSystemKey`,
  `policyDetails.policy`, and required `sourceContext`
- **Schema qualification:** `customerExternalSystem` and
  `customerExternalSystemKey` are required for canonical mocks because standalone
  OpenAPI governs machine validation. The sponsor-directed specification's business
  minimum table omits them, so whether Delta Capita considers them part of the business
  minimum remains an open sponsor/API-owner clarification. This is not a
  sponsor-confirmed business policy
- **Idempotency:** shared POST rule
- **Success:** `201` with identifier, policy/status, `correlationId`, and timestamp
- **Relevant failures:** `400`, `401`, `403`, `404`, `409`, `422`, `429`, `500`, `503`
- **Unresolved:** sponsor/API-owner business-minimum treatment of the two external
  reference fields and Singapore policy/value-list configuration; conflicting JSON
  enum values are quarantined

### `amendParty`

- **Method/path:** `POST /v1/eds/parties/{partyId}/amend`
- **Headers/scope:** shared POST headers; `eds:party:write`
- **Minimum fields:** mandatory target GoldTier identifier, `partyType`, `policy`, and
  required `sourceContext`; send only amendment sections intended to change
- **Identifier qualification:** the specification calls the mandatory identifier
  `goldTierId`, while corrected standalone OpenAPI places `partyId` in the path and
  does not define a duplicate body field. For mock development the canonical path
  identifier is the mandatory target identifier; a duplicate body property must not
  be invented against an `additionalProperties: false` schema. Sponsor correction is
  still required
- **Idempotency:** shared POST rule
- **Success:** `200`; `207` may report optional-section failures
- **Relevant failures:** `400`, `401`, `403`, `404`, `409`, `422`, `429`, `500`, `503`
- **Unresolved:** identifier wording/body placement and Singapore conditional rules;
  conflicting JSON enum values are quarantined

Do not use the stale `/v1/eds/parties/{goldTierId}:amend` form.

### `createRelatedParty`

- **Method/path:** `POST /v1/eds/related-parties`
- **Headers/scope:** shared POST headers; `eds:party:write`
- **Minimum fields:** `parentGoldTierId`, `party.partyRole`, `party.partyType`,
  `party.names.legalName`, mandatory `party.relationshipProfile.rpRole`, and required
  `sourceContext`; individual first/last-name and relationship conditional rules remain
  subject to sponsor confirmation
- **Enum rule:** `rpRole`, when supplied, uses standalone casing/value options such as
  `Director`, `Owner`, `UBO`, `Authorised Signatory`, `Senior Management`, or `Other`.
  Conflicting uppercase/underscore JSON values are quarantined
- **Supported behaviour:** direct/first-level related parties only. Multi-level
  hierarchy creation is unsupported; seeded complex hierarchy data will be retrieved
  and displayed once its read contract is supplied
- **Idempotency:** shared POST rule
- **Success:** `201` using the standalone response shape; `207` may report optional
  section failures
- **Relevant failures:** `400`, `401`, `403`, `404`, `409`, `422`, `429`, `500`, `503`
- **Unresolved:** atomic relationship-link persistence, exact conditional relationship
  inputs, and response corrections

### `getPolicy`

- **Method/path:** `GET /v1/eds/policies/{partyId}`
- **Headers/scope:** shared GET headers; `eds:policy:read`
- **Minimum input:** non-empty `partyId`; optional `policy` and
  `includeStatusDetails`
- **Idempotency:** not applicable
- **Success:** `200` with `partyId`, policies, `correlationId`, and timestamp using the
  standalone schema
- **Relevant failures:** `400`, `401`, `403`, `404`, `422`, `429`, `500`, `503`
- **Unresolved:** exact unfiltered no-policy behaviour; conflicting JSON response
  values remain quarantined

## Registry proof metadata

The sponsor clarification permits registry-reference proof without a binary registry
document. Where proof completion is requested:

- `documentMetadata` carries `proofCategory`, `registrySourceLink`, and
  `sourcingDateTime`.
- For this POC, the source link identifies ACRA and the actual corresponding ACRA API
  endpoint; sourcing time is UTC ISO-8601.
- `fieldMetadata` includes path, registry name, and retrieval timestamp, with optional
  source/evidence/confidence metadata as supported by the standalone schema.
- Exact proof categories and ACRA endpoint values come from the source transaction and
  confirmed value lists, never copied from conflicting Australia/ANZ examples.

## Mapping-confidence boundary

- **Confirmed:** sponsor decisions in `DECISION_LOG.md`, seven operation catalogue,
  canonical amend route, ACRA scope, first-level-only relationship behaviour, TLS 1.3,
  and ACRA registry-reference provenance.
- **Candidate/inferred:** data-dictionary API-field joins, value-list joins, and any
  confidence label generated by name-similarity logic—even `HIGH`.
- **Requires validation:** Singapore ACRA-to-GoldTier mappings, conditional mandatory
  fields and value lists, policy identifiers, relationship details, and proof category
  codes.

No candidate mapping is a DTO assertion or sponsor-confirmed mapping until explicitly
validated.
