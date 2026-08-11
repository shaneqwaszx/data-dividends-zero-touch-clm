# Phase 05 Quality-Gate Remediation

## Goal

Close `P05-QG-001` through `P05-QG-005` without redesigning the CLM product or
changing the accepted Phase 01–05 normal behavior:

`Registry -> Document Review -> Ownership / UBO -> Backend Readiness -> Immutable Submission Snapshot -> Mock GoldTier -> Unified CLM Result`

This is a bounded Phase 05 remediation. It does not authorize Phase 06.

## Required fixes

### P05-QG-001 — current canonical validation

- Extract/reuse one canonical minimum validator for original onboarding, every Phase 05
  readiness evaluation, and final pre-submit evaluation.
- Treat current invalid canonical data as blocked with a typed blocker and zero
  GoldTier operations; do not trust historical `VALIDATED` state alone.
- Compare human-reviewed document values with the current canonical entity while
  retaining original extraction and the canonical value captured during Phase 03.
- Preserve source conflict as review; never overwrite canonical or document evidence.

### P05-QG-002 — snapshot/payload binding

- Make the validated immutable snapshot the source of the target submission input.
- Reuse one provider-neutral Mock GoldTier sequence for legacy and Phase 05 flows.
- Retain stable case, snapshot, submission, correlation, readiness-policy, and
  per-operation idempotency linkage without secrets or raw payloads.
- Prove that later live canonical mutation cannot change the mapper/request data.

### P05-QG-003 — post-target recovery

- Retain a minimized process-local execution receipt before CLM terminal mapping.
- Distinguish target-not-executed from target-executed/finalization-incomplete.
- Resume finalization from the retained receipt after result mapping, clock, event,
  repository-save, or one-shot CAS/update failure.
- Reuse the same logical submission/correlation/idempotency identities and never repeat
  the accepted Mock business sequence during recovery.
- Preserve successful amend, match-found, policy-failure, and partial-amend outcomes.

### P05-QG-004 — frontend readiness invalidation

- Invalidate visible readiness immediately when document or ownership mutation starts.
- Refetch the authoritative CLM summary after every relevant success or failure.
- Refresh after `CLM_NOT_READY` or submission conflict; do not reproduce readiness
  business policy in React.
- Keep submission disabled while authoritative readiness is refreshing.

### P05-QG-005 — README

- Document the staged CLM routes, five-stage Mock demo, principal statuses, Mock-only
  claim boundary, and remaining sponsor/live dependencies concisely.

## Required adversarial regressions

- Current canonical invalidation for every accepted mandatory field.
- Historical document/canonical A versus current canonical B conflict.
- Snapshot-to-request binding across legal name, registration number, address, and
  country mutation.
- Recoverable post-target result mapping, clock, terminal event, terminal save, and
  one-shot CAS/update failures with no duplicate Mock calls.
- Recovery outcome preservation for success, match found, policy failure, and partial
  amend.
- Frontend ready-state invalidation after document and ownership mutations.
- Existing stale-readiness, duplicate/concurrent submit, call-stopping, and case
  isolation scenarios.

## Contract and security boundary

- D-023 remains a working project decision pending sponsor confirmation.
- Q-003/Q-005/Q-013/Q-014 keep document/readiness policy provisional; Q-004 keeps UBO
  policy provisional; Q-006/Q-007 prohibit related-party writes/mapping claims.
- Preserve the confirmed canonical amend endpoint and existing GoldTier evidence
  hierarchy/quarantine classification.
- Add no real GoldTier HTTP, PingFed/OAuth, credentials, related-party write, live
  hierarchy, live ACRA ownership, Ready-for-Approval action, RBAC, durable database,
  worker/queue, or sponsor approval logic.
- Execution receipts and browser summaries must contain no raw request/response,
  document/provider payload, private provenance, secret, auth material, or endpoint.

## Validation and handoff

Run the complete backend, frontend, phase-focused, contract, repository, static,
dependency, security/secret, GoldTier-validator, production-build, diff, cached-diff,
and untracked-whitespace matrix. Re-run the integration security review and POC
regression check, replacing their superseded pre-gate conclusions with explicit closure
evidence for all five findings.

Do not stage, commit, push, merge, change branch, or begin Phase 06. Hand the remediated
worktree to the final independent Phase 05 quality gate.
