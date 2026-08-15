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

## Phase 04 implementation status

The ownership foundation attaches a separate process-local analysis record to an
existing case and consumes a replaceable `OwnershipProvider`. The default Mock provider
is credential-free/network-free and supplies seven explicit fictional scenarios.
Generic provider, source, graph, service, domain, and API contracts contain no Mock
scenario.

Direct and indirect ownership paths use bounded iterative traversal and Decimal
arithmetic; unique paths aggregate once and retain deterministic edge/calculation
evidence. The configurable default `25%` inclusive threshold, graph limits, and
cycle/incomplete handling are project-defined and provisional pending Q-004. Cyclic,
incomplete, or calculation-limit data routes to review without a definitive candidate;
malformed/unsafe data terminalizes to retrievable sanitized `FAILED`.

The ownership sub-workflow never mutates the canonical ACRA entity, onboarding state, or
Phase 03 document records and makes no ACRA/GoldTier call. Q-002/Q-004/Q-006/Q-007 still
block live hierarchy binding, sponsor-approved UBO policy, related-party writes, and
final Singapore mappings.

Phase 04 quality-gate remediation additionally rejects natural-person owned-parent
edges, reconstructs all provider output into fresh nested trusted models, retains only
opaque server-side source references, minimizes browser provenance, protects terminal
records with atomic expected-version writes, uses bounded digest path IDs, validates the
shared six-decimal threshold contract at configuration time, and renders exact Decimal
strings without JavaScript numeric rounding. These are technical controls and do not
change the provisional sponsor-policy boundary above.

## Phase 05 implementation status

The first integrated CLM workflow adds a staged registry path that stops at validated
canonical evidence, while preserving the original Phase 01 onboarding API as the same
staged intake plus the existing Mock GoldTier sequence. Existing document and ownership
APIs remain the source of truth for their records.

A source-neutral orchestration aggregate evaluates current registry, document,
ownership, and Mock GoldTier readiness with typed blockers and separate real-integration
warnings. It requires a fully reviewed registry-compatible document and terminal
`ANALYZED` ownership result under the project-defined provisional Phase 05 policy.
Document corrections/rejections that conflict with ACRA do not overwrite canonical
data and route to `SOURCE_CONFLICT_REQUIRES_POLICY` pending Q-005/Q-014.

Submission revalidates current evidence server-side, creates a minimized immutable
snapshot, and serializes the accepted Mock search/conditional-shell/policy/amend path.
Duplicate/concurrent requests do not duplicate business operations. Related-party
preparation is reported as pending Q-006/Q-007 and performs no write.

Phase 05 quality-gate remediation now reuses one canonical minimum validator during
onboarding, readiness, and final pre-submit evaluation; compares reviewed document
evidence with the current canonical entity; makes the frozen snapshot the exact target
mapper input; and records a minimal safe process-local target outcome before fallible
rich receipt/result/error mapping so post-target finalization can be retried without
duplicate Mock operations. The frontend immediately
invalidates stale readiness after document/ownership mutation and refetches the backend
summary. These are technical integrity controls and do not change the provisional
sponsor-policy boundary.

The integrated success status is `MOCK_GOLDTIER_SUBMITTED`. It is not legal/compliance
approval, production GoldTier acceptance, or Ready-for-Approval. Live ACRA remains
blocked by Q-012; live hierarchy by Q-002; sponsor IDP/UBO policies remain unconfirmed;
and real GoldTier/PingFed remains not ready.

## Phase 06 implementation status

The sponsor-facing path now accepts a UEN and one PDF, then drives registry validation,
provisional document auto-confirmation, deterministic ownership analysis, Phase 05
readiness, and the hardened Mock GoldTier sequence from a server-owned state machine.
The React UI is a read-only progress/exception client after start; legacy manual flows
are available only behind environment-gated Demo/Test Controls.

Automatic document confirmation is restricted to complete, current-canonical matches
at or above the configured threshold. Phase 03 manual review behavior remains intact.
Typed exceptions retain bounded evidence and all blockers. `KEEP_REGISTRY_VALUE` is
advertised only for a source conflict and is bound to both versions and a server-only
fingerprint recomputed from current authoritative case/document evidence. It cannot
clear independent low-confidence or missing evidence. Ownership indeterminacy and existing/partial
target outcomes have no click-through action. Technical failures are separate and
cannot become review or completion.

Per-case serialization, expected-version writes, bounded transitions, idempotent
start/resume, and stale/cross-case resolution checks prevent duplicate local progress.
Unexpected progression failures converge to one sanitized terminal record. Phase 05
remains the target replay/recovery authority; only its typed finalization-retry signal is
re-entered without target replay. All guarantees remain
process-local and Mock-only. D-025 records the provisional policy; all sponsor blockers
listed in Q-001–Q-014 remain open as applicable.

## Phase 07 implementation status

The accepted Mock POC is packaged for sponsor UAT and integration handoff without
changing its business policy. A safe public execution-profile read keeps the normal
browser environment banner truthful. Demo-gated integrated presets now include multiple
document blockers, preferred low-confidence/ownership-cycle labels, multiple ownership
paths, partial amend, and deterministic replay-free finalization recovery. A whitelisted
JSON UAT export reports synthetic case/status/stage/blocker/metric/timing/operation/
warning/timeline evidence without PDF bytes, raw payloads, endpoints, credentials,
private fingerprints, or exception internals.

The sponsor UI adds a concise case summary and explicit recovery action; Windows scripts
provide checked Mock startup, exact launcher-owned process-tree stop, and verified
process-restart reset. Git-ignored runtime metadata binds role/PID/creation/executable/
project command/listener/port identity, and stale or mismatched ownership fails safe.
The final
handoff includes a 12-case UAT catalogue, synthetic document pack, demo script/runbook,
provider replacement and adapter conformance guides, API/configuration/failure/security
references, final architecture, sponsor dependency matrix, and deliverable index.

No new sponsor artefact was supplied and no open question was closed. Document/readiness
and UBO policy remain provisional; live ACRA/hierarchy/GoldTier and Ready-for-Approval
remain blocked or unconfirmed. Phase 07 adds no live adapter, credential handling,
related-party write, autonomous approval, production RBAC, durable orchestration, or
later-phase scope.
