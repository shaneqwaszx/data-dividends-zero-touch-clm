# Project Context

## Project

**Zero-Touch Onboarding - Client Lifecycle Management (CLM)**  
FYP team: Data Dividends  
Sponsor: Delta Capita

## Current sponsor-confirmed project flow

The main FYP flow is:

**ACRA Singapore -> EDS/orchestration layer -> GoldTier**

The project follows the **Singapore NTB** workflow. Australia examples in some earlier API material are illustrative and should not be treated as the live project registry scope.

The framework should remain extensible to other registries/jurisdictions later.

## Core POC outcome

Demonstrate onboarding of a Singapore corporate entity with data sourced from ACRA, processed through the team’s orchestration layer, and sent to the relevant GoldTier endpoints.

The UI should show the major NTB stages and the successfully created/retrieved customer.

The POC should also demonstrate:
- IDP for agreed PDF/document data
- confidence/review handling
- related-party processing
- UBO ownership unwrapping
- tagging around the sponsor-agreed UBO rule
- human-in-the-loop review/approval based on risk/exception conditions

## Important project constraints

- ACRA is the sole live external registry source for the FYP.
- GoldTier sandbox environment is being provisioned by Delta Capita.
- Development must continue against mocks while external environments are unavailable.
- `createRelatedParty` is limited to direct, first-level related parties.
- Multi-level hierarchy creation is not supported through the current API.
- Complex hierarchy demo data will be seeded by Delta Capita and should be retrieved/displayed.
- The project must never use AI as an autonomous approval authority.
- Human review is expected for missing, inconsistent, or low-confidence data.

## Canonical GoldTier path decision

Use:

`POST /v1/eds/parties/{partyId}/amend`

Do not generate clients/tests against the stale `{goldTierId}:amend` form.

## Authentication

Current sponsor direction is PingFed authentication. Exact sandbox connection details/token request will be supplied when Nutmeg is provisioned.

Never commit credentials or token material.

## Local sponsor artefacts

Store sponsor files only under:

`private/sponsor-artifacts/`

This directory is gitignored.

Expected artefact types include:
- approved FYP proposal
- sponsor Q&A documents
- EDS-GoldTier API specification
- GoldTier EDS data dictionary
- XPI connection guide
- Postman collection
- OpenAPI ZIP
- JSON sample ZIP

Do not copy credential values from sponsor artefacts into tracked files.

## Current unresolved items

See:
`docs/sponsor-questions/OPEN_QUESTIONS.md`
