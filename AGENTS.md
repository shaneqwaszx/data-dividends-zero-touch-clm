# Data Dividends — Codex Project Rules

## Project goal

Build the FYP Proof of Concept for:

**Zero-Touch Onboarding - Client Lifecycle Management (CLM)**

Primary project flow:

**ACRA Singapore -> EDS/orchestration layer -> GoldTier -> Ready-for-Approval / human review gate**

The implementation must remain extensible to additional corporate registries later, but the live POC registry scope is Singapore ACRA.

## How Codex should work

- Work only on the task/phase explicitly assigned.
- Read this file before making changes.
- Read `docs/PROJECT_CONTEXT.md` for current project scope and sponsor decisions.
- Read the active phase prompt under `.ai-pipeline/`.
- Do not silently invent missing business rules.
- If a material requirement is ambiguous or contradictory, record it and stop that part of the implementation rather than guessing.
- Prefer small, testable changes over large rewrites.
- Do not merge to `main`.
- Do not push unless explicitly instructed.
- Do not modify unrelated files.

## Source-of-truth priority

When supplied project artefacts disagree, use this priority:

1. Latest direct Delta Capita sponsor clarification recorded in `docs/decisions/DECISION_LOG.md`
2. Corrected/canonical standalone API artefacts and agreed JSON examples
3. EDS-GoldTier Integration API Specification
4. GoldTier EDS Data Dictionary
5. GoldTier connection guide / Postman examples
6. Approved FYP proposal

Never resolve a material conflict silently. Record it in:
`docs/decisions/DECISION_LOG.md` or `docs/sponsor-questions/OPEN_QUESTIONS.md`.

## Current implementation scope

### Implement
- Singapore NTB onboarding POC
- ACRA as the sole live external corporate registry source
- Registry data ingestion
- Canonical internal entity model
- ACRA -> internal model -> GoldTier mapping
- IDP for agreed PDF/document inputs
- Confidence scoring and human review for low-confidence/exception cases
- Related-party processing
- Deterministic ownership/UBO percentage calculation
- UBO tagging using configurable business rules
- GoldTier EDS/XPI integration
- Basic workflow/status UI
- Audit-safe technical logging
- Mock connectors so development is not blocked by sandbox availability

### Do not implement unless explicitly assigned
- ASIC live integration
- Malaysia or Hong Kong live registry integrations
- `createRelationship`
- creation of multi-level corporate hierarchies through GoldTier
- full compliance/risk assessment engine
- autonomous AI approval decisions
- ML-based final UBO decisions
- full analytics/MIS dashboard
- full Exception Workbench

## GoldTier contract decisions already confirmed

- Canonical amend endpoint:
  `POST /v1/eds/parties/{partyId}/amend`
- `createRelatedParty` supports direct, first-level related parties.
- Multi-level hierarchy creation is not supported through the current API.
- Complex hierarchy demo data will be seeded in GoldTier and should be retrieved/displayed when the relevant API is available.
- ACRA is the only external registry source for the POC.
- GoldTier authentication target is PingFed-based token retrieval when sandbox details are supplied.
- TLS 1.3 is required for the sponsor sandbox connection.
- ACRA registry proof should reference ACRA and the corresponding API endpoint.
- UTC ISO-8601 is acceptable/recommended for sourcing timestamps.

## Security rules

Never commit:
- `.env`
- passwords
- client secrets
- access tokens
- bearer tokens
- private keys/certificates
- sponsor credentials
- raw confidential sponsor artefacts in `private/`

Do not copy secrets from Postman collections into source code, documentation, tests, examples, or commits.

KYC/PII must not be written to normal application logs. Logs should contain safe identifiers, statuses, correlation IDs, and masked/sanitised summaries.

## Architecture rules

- External systems must be accessed through connector/service interfaces.
- Business logic must not depend directly on ACRA or GoldTier HTTP payloads.
- Use the flow:
  `source payload -> canonical internal model -> target mapping`
- Mock and real connectors should be switchable without changing business logic.
- UBO percentage calculation must be deterministic and testable.
- Human review is permitted and expected for exceptions.

## Testing rules

Every meaningful feature must have tests.

Before reporting a task complete, run the relevant:
- backend tests
- frontend tests
- type/lint checks
- contract tests
- security/secret checks where configured

Do not claim success if checks were skipped or failed.

## Definition of done

A task is complete only when:

1. Assigned requirements are implemented.
2. Relevant tests pass.
3. No secrets or confidential raw artefacts are newly tracked.
4. Documentation impacted by the change is updated.
5. Assumptions and unresolved questions are explicitly recorded.
6. The final Codex report includes:
   - files changed
   - tests/checks run
   - results
   - decisions/assumptions
   - blockers/risks
   - recommended next step
