# Provider-verified Policy recovery remediation

Task authority: the owner's 2026-10-06 remediation assignment. Base/HEAD at start:
`529efea3966fb561027973e6d932cecb0e8f6bb8`; branch
`fix/goldtier-policy-provider-recovery`. Main remains unchanged.

## Scope and owners

- OnboardingService accepts both definitive Shell and provider-recovered Shell before
  one unresolved Policy. Preserve original completed operations, Shell status, frozen
  input and single intent; retain a separate Requested Policy recovery without calls.
- ZeroTouchOrchestrator records a bounded recovery transition from the matching
  uncertainty technical failure, without executing target operations. Explicit resume
  then uses existing CLM/ledger ordering and original final confirmation.
- Existing target-recovery API delegates to the owning orchestrator under locked
  TARGET_RECOVERY reauthorization. No route-owned persistence or new permission.
- Inspect safe uncertainty observability using existing event codes, avoiding a new
  persistence schema, private error retention or altered replay semantics.
- Existing backend API remains the recovery interface; a browser evidence form is
  outside this bounded fix. Requested only; no Active, new Policy ID, timeout change,
  external calls, real UAT access, publication or merge.

## Acceptance and evidence

Both predecessor shapes, repeat/conflicting evidence, strict identity and frozen-policy
binding, invalid/terminal prefixes, locked authorization, one intent and zero replay.
Fake transport tests cover no-Amend and required-Amend continuation, unchanged final
confirmation, historical failure retention and no calls during recovery. Generated
allowlisted disposable Mongo proves restart, repeated reads without rewrite and cleanup.
Run affected backend/regression, Ruff, strict mypy, contracts, secrets/governance and
hostile-environment isolation. No frontend behavior changes are planned.

## Architecture and change necessity

Existing case, ledger and orchestration owners can handle the requirement. Extend them
without a new owner/dependency/framework/schema. The old Shell-recovery-only predicate
is replaced with the two authorized predecessor shapes; historical behavior remains.
No separate ADR is needed for this owner-local behavior extension; update current
recovery contract and architecture/state delta. Decision: code-change, limited to these
owners and focused tests/docs. No source edits are justified outside this scope.

## Checkpoint

1. Baseline/context and physical-runtime preflight: complete.
2. Focused recovery and automation changes/tests: complete; round 1 rerun passes 178 checks.
3. Safe diagnostics decision/tests and durable docs: complete; Ruff/mypy/contracts/governance pass.
4. Complete diff review and physical restart: complete. Broad backend run had 14
   sandbox temp setup errors; both affected suites plus recovery rerun pass (57 tests).
   The independent gate will run the complete current 2,637-test inventory.
5. Initial independent gate FAIL with one P2 manual CLM compatibility regression.
   Remediation round 1 preserves that existing API without synthesizing automation;
   both manual predecessor tests and current recovery suite pass (33 tests).
   Freeze remedied content and obtain fresh independent gate (max two rounds).
6. Only after independent PASS, commit locally; no push/PR/merge. Stop for owner review.

Capabilities: PowerShell, primary repository Python virtualenv, managed worktree,
collaboration reviewer available. Task-owned loopback Mongo container is available;
the physical fixture generates and cleans its own allowlisted disposable database.
