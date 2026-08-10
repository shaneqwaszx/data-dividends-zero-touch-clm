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

The supplied authentication collection is quarantined because it contains
credential/token material. Do not use, test, copy, or sanitise it in place. Real
GoldTier authentication is blocked until the sponsor confirms rotation/revocation,
provides a sanitised reference collection, and supplies fresh credentials through an
approved mechanism when real sandbox integration begins. This does not block
credential-free mock development.

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

## Phase 02 implementation status

The ACRA ingestion foundation supports deterministic Mock ACRA mode and a
production-shaped sandbox adapter behind the existing `AcraConnector` boundary.
Source DTOs, canonical mapping, authorization, HTTP transport, response decoding, and
safe connector errors are separate concerns. GoldTier remains mocked.

Exact live ACRA binding and sandbox verification remain blocked by Q-012 because the
approved project material does not contain the subscribed Business Profile API
operation schema, authentication contract, sandbox URL, or authorized credentials.
Tracked Phase 02 ACRA response fixtures are synthetic adapter-contract data and are not
represented as captured ACRA responses.

## Phase 03 implementation status

The document-processing foundation accepts bounded transient PDFs beneath an existing
onboarding case and passes them through a replaceable `IdpProvider`. The active Mock
IDP is credential-free, network-free, and produces deterministic synthetic candidates
for four project-defined provisional corporate fields. Uploaded bytes and raw provider
output are not retained; a validated display name is retained but never used as a path.
Mock scenarios are isolated to a dedicated demo control/endpoint. Generic provider
input, metadata, environment, extraction results, processing, domain, and review
contracts contain no Mock scenario requirement.

Candidates retain original value, independent confidence/provenance, deterministic
canonical comparison, and separate human accept/reject/correct results. The document
workflow is supplementary and does not alter the accepted onboarding terminal state or
call GoldTier. Its four fields, normalization/comparison, `0.85` confidence threshold,
completion rule, and upload limit are configurable project defaults, not sponsor-
approved policy. Q-003 and Q-005 still block final document types/fields, validation
ownership, and required workflow sequencing. Reviewer identity/authentication, real
OCR/IDP, production PDF security, and retention policy are not implemented.

The accepted-upload failure boundary covers all processing work through
`REVIEW_REQUIRED`. Recoverable provider, comparison, provenance/model, clock, and
repository-update failures persist one safe terminal failure without changing the
parent case or invoking downstream operations.
