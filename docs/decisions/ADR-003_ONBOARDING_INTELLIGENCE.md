# ADR-003 — Source-neutral onboarding intelligence is advisory and case-bound

## Status

Accepted

## Date

2026-09-24

## Context

The owner-authorized pre-Phase 22 POC needs explainable entity-resolution evidence,
ML-assisted UBO advice, and project-defined mock advisory risk. Current connector,
reconciliation, deterministic ownership, policy, workflow, authorization, and target-
ledger owners do not own cross-source advisory scoring. Computing advice from current
global policy on every read would reinterpret older cases, while placing scoring in a
provider connector or the ownership engine would mix responsibilities and create
provider or legal-authority coupling.

The implementation must preserve the source DTO/canonical-evidence boundary, the sole
Decimal ownership engine, backend authorization and safe 404 behavior, explicit
memory/Mongo persistence with revision CAS, target call ordering/no replay, Mock/Local
provider truth, and the Phase 22 hold. Q-004 and Q-017 do not authorize production
identity, legal UBO, risk, compliance, or approval claims.

## Decision

Add one source-neutral `onboarding_intelligence` domain/service owner. It consumes only
canonical case evidence and the existing deterministic ownership result. It emits one
versioned, case-bound projection containing entity-resolution evidence, UBO advice, and
mock advisory risk with permanent non-authority labels.

The existing Policy Catalogue remains the sole editable threshold/weight owner. New
cases bind its intelligence policy immutably; the projection records the catalogue and
model versions. The existing case envelope remains the sole durable state owner through
schema v5. Exact schema-v1 through schema-v4 readers produce no intelligence projection
and do not rewrite on read.

Entity resolution uses loss-aware Unicode normalization, exact usable registration
identifier plus country before descriptive scoring, deterministic candidate ranking,
and fail-closed ambiguity/conflict behavior. Distinct identifiers or countries cannot
produce an automatic match. Generic legal-form agreement is not independent strong
corroboration. Persisted result models enforce outcome/candidate, evidence, threshold,
score/band, and UBO probability/ownership consistency.

Advisory intelligence never mutates canonical evidence, legal UBO results, approval, or
the target ledger. Mock risk is non-blocking by default. Only the existing zero-touch
workflow owner may create a typed human-review stop when the case-bound policy flag is
true. No resolution/bypass authority is introduced.

## Alternatives considered

- Extend the GoldTier connector with scoring: rejected because provider transport does
  not own source-neutral identity decisions and the XPI contract is absent.
- Extend the Decimal ownership engine: rejected because advice must consume, not
  recalculate or replace, legal ownership evidence.
- Add separate entity, UBO, risk, or audit stores: rejected because they would create
  duplicate persistence and lifecycle owners.
- Recompute from current policy on every read: rejected because it would reinterpret
  persisted cases after catalogue changes.
- Defer all ready slices: rejected because the local advisory POC is explicitly
  authorized and can remain truthfully fenced from blocked provider/sponsor lanes.

## Consequences

- Focused domain, service, repository-port, API, evaluation, and UI modules are added;
  existing hotspot edits remain composition or canonical workflow/schema integration.
- Case schema v5 and exact legacy readers must be maintained and tested in memory and
  physical Mongo.
- Synthetic evaluation can demonstrate deterministic named scenarios only; it cannot
  establish population accuracy, calibration, fairness, sponsor acceptance, or live
  interoperability.
- XPI candidate mapping remains unavailable until authoritative artefacts arrive, so
  only named synthetic demo scenarios currently supply candidate sets.
- Q-016 assignment/note/SLA mutations remain absent and cannot be inferred from this
  decision.

## Architecture invariants affected

- Added: one source-neutral advisory-intelligence owner and one optional projection in
  the existing case envelope.
- Added: persisted advisory types fail closed on contradictory semantic states.
- Added: projection reads reject catalogue, weight, threshold, readiness-flag, model,
  or outcome/evidence values that contradict the immutable case policy.
- Preserved: strict provider payload to DTO to canonical evidence direction.
- Preserved: one deterministic Decimal ownership/UBO engine.
- Preserved: one policy catalogue/snapshot owner, one case persistence owner, one
  authorization owner, one workflow/readiness owner, and one target ledger.
- Preserved: no silent persistence/provider fallback and no Live claim.
- Retired: none; no previous intelligence owner or fallback existed.

## Security and persistence implications

The browser/API projection contains bounded candidate IDs, contribution labels, safe
source references, probabilities, bands, reason codes, and model/policy metadata. It
excludes raw provider payloads, registration values, names, addresses, document bodies,
credentials, target responses, and private notes. Case access remains backend-owned and
inaccessible/absent cases share the same 404.

Schema v5 retains the projection inside the case envelope with strict case identity,
revision CAS, update-only mutation, whole-case deletion, restart recovery, and no stale
resurrection. Schema-v1 through schema-v4 compatibility is read-only. Mongo BSON
serialization is deterministic for set/frozenset values. Invalid nested outcome,
candidate, probability, score, band, signal, or threshold combinations are corruption
and fail closed. Risk limitations use a closed vocabulary.

## Migration and retirement implications

An exact known eight-rule Policy Catalogue may receive one audited, idempotent
intelligence-rule migration; unknown/custom partial shapes fail closed. There is no
bulk case migration and no version-only rewrite. Schema-v4 cases retain
`intelligence = null` and no intelligence policy.

The advisory owner may be replaced only by an explicitly reviewed successor with an
accepted migration/retirement decision. A future authorized XPI dialect may supply
candidate evidence but does not silently replace this owner or activate current Mock
behavior. Removing the feature requires retiring its policy rules, projection/API/UI,
and schema write path while preserving historical reads.

## Verification

- Focused RED/GREEN tests for Unicode/lossy normalization, identifier/country conflict,
  unequal usable identifiers with one-sided missing country, weak evidence, ambiguity,
  thresholds, deterministic evidence, UBO non-authority, and missing risk signals.
- Direct model and raw schema-v5 corruption tests for entity, UBO, risk, and immutable
  policy-binding invariants; memory/Mongo parity, CAS, legacy reads, restart, deletion,
  genuine-Mongo restart rejection, and physical Mongo BSON round trips.
- Backend full pytest, Ruff, strict mypy, contract/security/governance checks, synthetic
  evaluation, frontend tests/typecheck/build, lifecycle, browser E2E, and POC regression.
- Fresh independent exact-content re-quality gate after remediation.

## Revisit conditions

Revisit if authoritative GoldTier/XPI candidate fields arrive, a trained/statistical
model or executable artefact is proposed, production identity/compliance authority is
requested, policy must change existing cases, schema migration cannot remain strict,
multi-process/large-candidate scale invalidates bounded scoring, or the false-positive
boundary cannot be demonstrated on an appropriately governed evaluation set.

## Related contracts and sponsor questions

- [Architecture](../ARCHITECTURE.md)
- [Project state](../PROJECT_STATE.md)
- [Ownership/UBO profile](../contracts/OWNERSHIP_UBO_PROFILE.md)
- [Persistence recovery profile](../contracts/PERSISTENCE_RECOVERY_PROFILE.md)
- [Policy authority matrix](../contracts/POLICY_AUTHORITY_MATRIX.md)
- [Decision log](DECISION_LOG.md), D-047
- [Open sponsor questions](../sponsor-questions/OPEN_QUESTIONS.md), Q-004, Q-016, Q-017
- [Implementation plan](../aegis/plans/2026-09-23-pre-phase22-capability-expansion.md)
