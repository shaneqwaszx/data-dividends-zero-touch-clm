# ADR-011 - Grouped review through existing section checkpoints

## Status

Proposed; implemented under the 2026-10-10 owner assignment, pending independent review.

## Date

2026-10-10

## Context

Four individual decisions currently cause four mutations and refresh waves. The owner
requires local drafting and one confirmed group. Document, reconciliation and automation
sections already persist through separate owners; they cannot honestly claim a shared
transaction. Reconciliation alone has an existing canonical/reconciliation unit of work.

## Decision

Extend ZeroTouchOrchestrator, DocumentProcessingService and ReconciliationService.
Confirm exactly one decision family through the creator-authorized review-decisions API.
Reauthorize inside the case lock; validate the entire group, case/automation versions,
source fingerprints, current document chains and allowed decisions before writes.
Prepare document records without mutation, then retain one record per affected document.
Unchanged exact decisions may repair interrupted section retention without duplicate
receipts. Reconcile only after every document checkpoint is retained. Source decisions
commit through the existing reconciliation UoW. Retain automation next, then continue at
most once when no blocker remains. Target confirmation/ledger evidence freezes review.

Frontend drafts are current-tab memory, scoped to actor/case/current evidence. Save means
retaining that tab's draft only. Refresh or changed identity/evidence clears it; no browser
storage or durable draft schema is introduced. GoldTier Review & Send remains separate.

## Alternatives considered

- Hidden per-field requests: retain the measured latency and premature reevaluation.
- A new cross-owner transaction/repository: introduce a competing persistence owner.
- Durable drafts: require separate retention/schema decisions beyond this bounded need.
- Existing owners with resumable checkpoints: selected; preserves the current architecture.

## Consequences

Choices are immediate and a complete group has one mutation/refresh wave. Partial failure
can leave reviewed document receipts retained while automation stays blocked. The caller
receives a technical error and must refresh or retry unchanged input; no false success or
target mutation repairs a review checkpoint. This is not cross-document atomic persistence.

When the source UoW has committed but automation retention fails, use explicit Resume
against the retained receipts. Canonical changes invalidate the old request's case-event
version and may require a read-only Search recheck. They never authorize target replay.

## Architecture invariants affected

Existing case lock, strict envelope revision CAS, update-only sections, no resurrection,
one reconciliation owner/UoW, Decimal ownership and target ledger remain authoritative.
No new provider, source precedence, mapping or target-ordering owner is created.

## Security and persistence implications

Authenticated creator/team/capability and CSRF checks apply; sensitive reauthorization is
inside the owning lock. API input is bounded and rejects extra/duplicate fields. Source
observations and audit history remain retained; document bodies stay transient. Schema10
and strict historical reads are unchanged. No credentials or external writes are required.

## Migration and retirement implications

No migration. Standalone field-review remains for API compatibility and explicit checkpoint
repair; current Case Detail uses grouped review. Retirement needs a separately assigned
consumer audit. Rolling back the UI does not invalidate retained ordinary review receipts.

## Verification

Require HTTP group/tamper/auth/currentness tests, one UoW/continuation evidence, partial
save/restart through generated physical Mongo databases, browser zero-request selections,
focus and responsive evidence, full affected regressions, and fresh independent quality gate.

## Revisit conditions

Revisit for multi-process lock coordination, durable drafts, cross-owner atomicity, new
decision families, source-policy authority or changed persistence ownership.

## Related contracts and sponsor questions

[D-071](DECISION_LOG.md), [intake](../contracts/MULTI_DOCUMENT_INTAKE_PROFILE.md),
[reconciliation](../contracts/RECONCILIATION_PROFILE.md),
[persistence](../contracts/PERSISTENCE_RECOVERY_PROFILE.md).
Existing sponsor questions remain unresolved; no new sponsor decision is implied.
