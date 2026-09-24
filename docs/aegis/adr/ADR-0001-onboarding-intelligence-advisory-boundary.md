# ADR-0001 - Source-neutral onboarding intelligence is advisory and case-bound

Status: `superseded-by-project-adr`
Date: `2026-09-23`

## Source Evidence

- User-authorized pre-Phase 22 requirements and implementation plan; current architecture and policy/persistence contracts.
## Context

The POC needs explainable entity-resolution, ML-assisted UBO, and mock advisory-risk outputs. Existing connector, reconciliation, deterministic ownership, policy, and ledger owners do not own cross-source advisory scoring, and advisory recomputation must not reinterpret persisted cases after policy/model changes.

## Decision

Create one source-neutral onboarding-intelligence domain/service owner. It consumes canonical evidence and the existing deterministic Decimal ownership result; emits versioned explainable advice with immutable non-authority labels; binds thresholds/model identifiers in the existing case policy snapshot; and cannot mutate canonical evidence, legal UBO outputs, approval, or target ledger decisions. It reports a case-bound risk review flag to the existing readiness owner; only that owner may create a typed review stop, and the flag defaults false.

## Alternatives Considered

- Put similarity in a GoldTier connector; extend the deterministic ownership engine into ML; store a second mutable intelligence record; or compute from current global policy on every read.
- Defer all advisory capability until sponsor regulatory policy is supplied.
## Consequences

- Focused domain/service/API/UI modules and backward-compatible snapshot persistence are required. Project-defined mock risk can demonstrate workflow behavior while Q-017 remains open, but cannot claim regulatory or compliance authority.
## Compatibility Boundary

Existing Mock/EDS GoldTier behavior, Decimal UBO truth, legacy case reads, authorization, query scoping, and ledger replay semantics remain unchanged; advisory risk does not block readiness by default. Legacy schema-v4 cases retain `intelligence = null` rather than being reinterpreted with current policy.

## Retirement Impact

No fallback or parallel authority is added. The advisory owner is replaced only by an explicitly reviewed successor; model versions remain auditable, and blocked XPI/assignment paths are not scaffolded.

## Baseline Sync

- Needed: needed
- Target: docs/ARCHITECTURE.md, docs/PROJECT_STATE.md, policy/persistence/ownership contracts, decision/open-question logs
- Action: update baseline
- Reason: The new owner and advisory boundary affect the canonical owner map and durable case interpretation.

## Evidence References

- docs/aegis/plans/2026-09-23-pre-phase22-capability-expansion.md
## Boundary

This ADR is an advisory Aegis Method Pack record. It does not grant completion authority or replace project-authoritative architecture sources.

The accepted canonical decision is
`docs/decisions/ADR-003_ONBOARDING_INTELLIGENCE.md`.
