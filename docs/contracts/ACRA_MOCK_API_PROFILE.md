# ACRA Mock/API Profile — Current Phase 09 Capability

## Status

This is a sponsor-readable description of the project's current synthetic ACRA
boundary. It is not an ACRA-published API specification, a captured ACRA response, or
evidence of live sandbox interoperability. Q-012 still blocks binding the sandbox seam
to an authoritative subscribed endpoint, authentication scheme, response contract,
error contract, and service limits.

## Current operation

```text
registration identifier / UEN
  -> RegistryProviderRouter (Singapore only)
  -> accepted Singapore UEN eligibility check
  -> AcraRegistryProviderAdapter.retrieve_company(identifier)
  -> configured AcraConnector.fetch_company(uen)
  -> strict AcraCompanyPayload reconstruction
  -> requested/returned UEN equality check
  -> map_acra_company
  -> CanonicalLegalEntity
```

There is no dedicated browser ACRA endpoint. `/api/onboarding/cases`, `/api/clm/cases`,
and `/api/clm/zero-touch/cases` acquire the profile during case creation after the
gateway selects Singapore/ACRA.

The provider has no separate entity-identification, profile, officer, shareholder,
relationship, document, or ownership operation. The current call is therefore
classification **A: one monolithic operation**.

## Request

| Item | Current rule |
|---|---|
| Identifier | Normalized uppercase registration identifier; ACRA is called only after SG resolution **and** the identifier satisfies the current accepted Singapore UEN eligibility rule |
| Mock happy-path format | Nine digits followed by one uppercase letter |
| Binding | Returned payload UEN must equal the requested identifier after normalization |
| Routing | Backend closed table; no caller-provided endpoint, provider name, class, or module |

## Currently retrievable fields

| Source DTO field | Canonical field | Available? | Notes |
|---|---|---:|---|
| `uen` | `registration_number` | YES | Required and request-bound |
| `entity_name` | `legal_name` | YES | Required source text; canonical validation rejects missing value |
| `country_code` | `country_of_incorporation` | YES | Synthetic fixtures use `SG` |
| `entity_type` | `party_type` | YES | Synthetic value `PRIVATE_COMPANY_LIMITED_BY_SHARES` |
| `registration_date` | `registration_date` | YES | Synthetic fixtures use `2024-01-02` |
| `entity_status` | `entity_status` | YES | Synthetic fixtures use `LIVE` |
| address block + street | `registered_address.address_line_1` | YES when address exists | Joined with one space |
| address unit + building name | `registered_address.address_line_2` | YES when supplied | Nonblank values joined |
| address postal code | `registered_address.postal_code` | YES when address exists | String preserves leading zeroes |
| address country code | `registered_address.country_code` | YES when address exists | Synthetic fixtures use `SG` |

## Provenance retained

The canonical entity retains business source `ACRA`, environment `MOCK` or `SANDBOX`,
UTC `retrieved_at`, and an internal query-free HTTPS `registry_source_link`. Browser
responses omit the source link and never expose authorization headers, secrets, base
configuration, raw response bodies, or transport diagnostics.

Mockness is an environment label, not a different business source. Synthetic Mock data
must not be represented as live ACRA data.

## Synthetic scenarios

| UEN | Synthetic entity | Registry outcome |
|---|---|---|
| `202400001A` | Merlion Circular Labs | Complete profile |
| `202400002B` | Straits Test Trading | Address absent; canonical review required |
| `202400003C` | Orchid Validation Demo | Complete profile; later Mock GoldTier failure scenario |
| `202400004D` | Harbour Partial Demo | Complete profile; later partial Mock GoldTier scenario |
| `202400005E` | Lion City Existing Customer | Complete profile; later existing-party scenario |
| `202400006F` | Cyclic Harbour Holdings | Complete profile; later ownership-cycle scenario |
| Any other accepted SG UEN | None | `ACRA_ENTITY_NOT_FOUND`; no mapping or downstream call |

The downstream labels do not change the registry operation or payload shape. All values
are project-created and synthetic.

## Controlled errors and stopping behavior

| Code | Meaning | Current behavior |
|---|---|---|
| `REGISTRY_IDENTIFIER_NOT_ELIGIBLE` | Resolved SG request does not satisfy the accepted Singapore UEN rule | Controlled retrievable Registry blocker; zero ACRA or downstream calls |
| `ACRA_ENTITY_NOT_FOUND` | No provider result | Failed/retrievable case; no downstream call |
| `ACRA_CONFIGURATION_ERROR` | Sandbox config/authorization unavailable | Sanitized technical failure |
| `ACRA_AUTHENTICATION_ERROR` | Authorization rejected | Sanitized technical failure |
| `ACRA_TIMEOUT` | Request timeout | Sanitized technical failure |
| `ACRA_SERVICE_UNAVAILABLE` | Rate/service/network unavailability | Sanitized technical failure |
| `ACRA_MALFORMED_RESPONSE` | Sandbox response cannot be decoded | Sanitized technical failure |
| `ACRA_CONNECTOR_UNEXPECTED_FAILURE` | Unexpected connector failure | Sanitized technical failure |
| `ACRA_RESPONSE_INVALID` | Adapter strict DTO reconstruction failed | Sanitized technical failure |
| `ACRA_RESPONSE_IDENTITY_MISMATCH` | Returned UEN differs from request | Sanitized technical failure |
| `ACRA_SOURCE_MAPPING_FAILED` | Canonical mapping precondition failed | Sanitized technical failure |
| `ACRA_MAPPING_UNEXPECTED_FAILURE` | Unexpected mapper failure | Sanitized technical failure |

Provider/raw exception text is not projected to the browser. Technical failures do not
become human-approved business exceptions and cannot falsely complete.

## Explicitly unavailable information

The current operation does **not** retrieve or map:

- officers or directors;
- position holders, owners, partners, or members;
- shareholders;
- related parties;
- party-to-party relationships;
- direct or indirect ownership percentages;
- ownership graphs or multiple ownership paths;
- UBO candidates or legal/controller determinations;
- Business Profile PDF/binary documents;
- business activities or SSIC classifications;
- former names, audit firms, accounts, or annual-return information.

Current ownership/UBO data comes from a separate provider-neutral synthetic ownership
workflow after document acceptance. It must not be described as ACRA-retrieved.

## Future expanded acquisition mapping

An expanded registry workflow could add distinct provider operations for identification,
profile, officers, shareholders, relationships, and ownership only after authoritative
ACRA subscriber documentation and sponsor field requirements are supplied. Each source
DTO would still require strict reconstruction, request/entity binding, provenance, and
source-to-canonical mapping before business use.

No GoldTier field/value mapping is sponsor-confirmed by this profile. For every future
ACRA field-to-GoldTier value, enum, role, relationship, proof category, or mandatory
condition the status is **`TBD_SPONSOR`** until reconciled under the repository's
contract-authority policy.

## Deferred concepts

- Configurable mock/sandbox/live switching beyond the already existing mock/sandbox
  ACRA connector mode: deferred.
- Synthetic “ACRA+” provider: deferred pending sponsor confirmation.
- Foreign registry implementations: out of Singapore POC scope.
- Live ACRA verification: blocked by Q-012.
