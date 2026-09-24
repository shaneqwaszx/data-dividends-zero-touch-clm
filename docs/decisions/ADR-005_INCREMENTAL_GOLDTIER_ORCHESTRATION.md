# ADR-005 — Early GoldTier Search and incremental synchronization use one ledger

## Status

Proposed

## Date

2026-09-24

## Context

The accepted CLM path previously treated GoldTier as a terminal ordered submission.
The sponsor has clarified that customer Search must occur immediately after canonical
registry identity and that target synchronization is incremental. Existing customers
must continue local evidence, ownership, and risk work without duplicate Shell creation.
The repository already has one entity-resolution owner and one durable target ledger;
adding parallel owners would split identity and replay authority.

## Decision

The CLM aggregate retains one immutable, safe Search checkpoint bound to a fingerprint
of canonical registration number, legal name, and country. Search is read-only and runs
after Singapore registry identity but before document/reconciliation/ownership stages.
Bounded candidates go through the existing entity-resolution engine.

- `EXACT_MATCH` retains the GoldTier party ID and marks Shell skipped.
- `NO_MATCH` permits the new-customer path, but Shell waits for ordinary readiness.
- probable, ambiguous, multiple, conflicting, failed, or stale outcomes block mutation.

When readiness is met, the existing target ledger is seeded from the checkpoint and
advances at most one mutation checkpoint at a time: Shell when new, then Policy, then
Amend. Intent is persisted before each call and definitive completion after validation.
An attempted operation without a definitive result remains uncertain and cannot be
automatically replayed. A retained terminal outcome may be finalized without another
provider call. Related-party dispatch stays outside this decision until the required
child-ID lifecycle and relationship authority are proved.

## Alternatives considered

- Keep one terminal bulk sequence: rejected because it contradicts the sponsor-directed
  incremental workflow and hides intermediate recovery state.
- Add a second Search/resolution service or sandbox ledger: rejected because the current
  entity resolver and target ledger already own those decisions.
- Treat any single candidate as existing: rejected because hard identifiers and bounded
  scoring must still prove an exact authorized match.
- Replay a timed-out operation with the same idempotency key: rejected because current
  provider evidence does not prove end-to-end idempotency after uncertain acceptance.

## Consequences

- CLM and automation expose an explicit GoldTier Search stage and safe operation states.
- Existing schema-v5 records remain readable through an explicit automation stage-order
  version. Missing stage-order metadata means the pre-Search v1 order; new records use
  v2. A safe non-terminal v1 continuation is CAS-rebased to the earliest unproved v2
  stage, so Search is performed rather than inferred. Legacy terminal outcomes remain
  terminal, and legacy uncertain target attempts remain stopped without replay.
- The optional progress inspector renders backend-authored events only.
- Mock remains default; XPI remains `SANDBOX_PARTIAL`; no Live or approval claim changes.
- The HR sandbox console may call read-only Search and construct offline previews, but it
  cannot bypass the case-bound ledger for writes.

## Security and verification

Retain no raw provider body, credential, document content, or customer payload. Candidate
projection is bounded to safe identity fields. Verify early ordering, exact/no-match/
ambiguous paths, zero duplicate Shell, Policy/Amend prerequisites, identity-change
Search refresh, restart compatibility, uncertain no-replay, capability enforcement, and
safe API/UI projections. Independent quality-gate review is required before publication.

## Related authority

- D-048/D-049 and ADR-004 remain the provider/identity baseline.
- D-051 records the sponsor-directed workflow intent.
- Q-001, Q-006, Q-007, Q-009, Q-010, Q-011, Q-016, and Q-018 remain open.
- Phase 22 remains on hold.
