# ACRA to Canonical Mapping - Phase 02

## Status and evidence boundary

This is a narrow Phase 02 project adapter contract, not an ACRA-published JSON schema
and not evidence of live sandbox interoperability.

Official ACRA public material confirms that the Business Profile API is part of the
Entity Information Query service and includes information such as UEN, entity name,
business activities, incorporation/registration date, and position holders, owners, or
partners. ACRA's open-data description separately confirms the availability of basic
entity information, status, type, and registered office address. See:

- https://www.acra.gov.sg/news-events/news-announcements/905/
- https://www.acra.gov.sg/resources/open-data-initiative/

Neither public page specifies the subscribed API operation path, JSON property names,
envelope, error schema, or authentication method. The exact source fields below are
therefore the sanitized project decoder shape used to prove the boundary. They must be
reconciled against authoritative subscriber documentation before a live smoke test.

## Field mapping

| Project ACRA adapter field | Canonical field | Transformation | Phase 02 required? | Confidence / decision source | Sponsor confirmation needed? |
|---|---|---|---|---|---|
| `company.uen` | `registration_number` | Trim, reject blank, uppercase, and require equality with the requested UEN | YES | HIGH for concept: official ACRA field; LOW for JSON name/envelope | YES |
| `company.entityName` | `legal_name` | Trim and reject blank; preserve the remaining source text | YES for successful onboarding | HIGH for concept: official ACRA field; LOW for JSON name | YES |
| `company.countryCode` | `country_of_incorporation` | Trim and reject blank; current workflow expects `SG` | YES for current workflow | MEDIUM: source-neutral canonical need; exact ACRA field unconfirmed | YES |
| `company.entityType` | `party_type` | Trim and reject blank; no GoldTier value-list translation in Phase 02 | YES for current workflow | HIGH for concept: official ACRA field; LOW for JSON name/value list | YES |
| `company.registrationDate` | `registration_date` | Parse ISO date to source-neutral date | NO | HIGH for concept: official ACRA field; LOW for JSON name/format | YES |
| `company.entityStatus` | `entity_status` | Trim surrounding whitespace and preserve the remaining source text; do not infer compliance/risk meaning | NO | HIGH for concept: official ACRA field; LOW for JSON name/value list | YES |
| `company.registeredAddress.block` + `streetName` | `registered_address.address_line_1` | Trim and reject blank components, then join with one space | YES when address is present | HIGH for address concept; LOW for component schema | YES |
| `company.registeredAddress.unit` + `buildingName` | `registered_address.address_line_2` | Trim each optional value, normalize empty-after-trim to `None`, and join only remaining values with comma and space; emit `None` when both are absent | NO | LOW: project display transformation | YES |
| `company.registeredAddress.postalCode` | `registered_address.postal_code` | Trim and reject blank; preserve text to retain leading zeroes | YES when address is present | MEDIUM: Singapore address convention; exact source name unconfirmed | YES |
| `company.registeredAddress.countryCode` | `registered_address.country_code` | Trim and reject blank; preserve source code | YES when address is present | LOW for exact source field | YES |
| Configured connector mode | `source.environment` | local `mock` -> `MOCK`; official `api_marketplace_mock` -> `MOCK`; generic `sandbox` -> `SANDBOX`. Provider-mode metadata must distinguish the two Mock lanes. | YES | HIGH: project provenance decisions D-019/D-050 | NO |
| Constant business source | `source.source_system` | Always `ACRA`; never `MOCK_ACRA` | YES | CONFIRMED: D-002/D-006 and Phase 01 boundary | NO |
| Actual query-free request endpoint | `source.registry_source_link` | Store the HTTPS ACRA endpoint/reference used for the UEN request; exclude authorization and headers | YES | CONFIRMED concept: D-006/D-012; exact endpoint pending Q-012 | YES |
| Backend UTC clock at accepted response decoding | `source.retrieved_at` | Timezone-aware UTC datetime serialized as ISO-8601 | YES | CONFIRMED: D-006/D-012 | NO |

The trim/nonblank rules are project-defined source-integrity controls for the current
mapping, not claims about the final subscribed ACRA schema. Structural or semantic
failure produces the fixed safe `ACRA_MALFORMED_RESPONSE` boundary. Source-neutral
canonical minimum checks independently prevent blank required business values from
reaching GoldTier. The internal canonical model retains `registry_source_link` for
future proof mapping, but the browser-facing case projection deliberately omits it.

## API Marketplace Mock observation boundary

The 2026-09-24 read-only no-auth diagnostic to
`https://api-sandbox.bizfile.gov.sg/api/acra/entityQuery/entityBasicInformation`
returned HTTP `401`. No successful provider payload was accepted, so the observation
adds no new field, enum, default, relationship, or ownership-percentage mapping. In
particular, historical sample-derived `SG` defaults, constitution-to-entity-type mapping,
shareholder categories, and empty relationship behavior remain provisional/supporting
evidence rather than newly proved official contract behavior. Q-012 remains open.

## Intentionally ignored in Phase 02

- business activities and SSIC classifications;
- position-holder, officer, shareholder, owner, partner, and member records;
- former names and audit-firm data;
- account/annual-return due dates;
- binary Business Profile documents and proof-category codes;
- source confidence scores;
- ownership percentages, related-party relationships, and UBO tags;
- raw response bodies, response headers, authorization data, and credentials.

These fields are either unnecessary for the current vertical slice, require later
sponsor rules, or belong to later phases. Their public availability does not make their
exact subscribed API schema or CLM mapping confirmed.

## Fixture policy

`apps/backend/tests/fixtures/acra/synthetic_company_success.json` is project-created,
sanitized test data. Its top-level notice states that it is not an ACRA response. No
captured sandbox response may replace or supplement it in tracked files without an
explicit privacy/security review and schema authority decision.
