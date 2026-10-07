# GoldTier reliability and recovery UX correction

Owner assignment: pasted focused reliability/recovery request, 2026-10-07.
Base / HEAD / refreshed origin/main: `5c54c9af896585764d1e4ed809056d1deb576629`.
Worktree: `C:/Users/shane/.codex-clean2/worktrees/goldtier-reliability-recovery/data-dividends-zero-touch-clm`.
Branch: `codex/goldtier-submission-reliability-recovery-ux`. Coordinator: current chat.

## Scope and owners

Extend existing CLM pre-dispatch checks, onboarding recovery predicates, zero-touch
recovery coordination, API projections and session-scoped CaseDetail actions. Add a
prominent submission-package recovery component. Keep target ledger, immutable intent,
confirmation, capabilities, mapper, provider dialect and persistence schema owners.
Architecture review required: no new owner/dependency/schema; no ADR expected.
Change classes: frontend UI/state-cache, backend domain/API, auth/security, persistence
(existing recovery behavior), CI tooling (offline fixture/harness). No provider
transport/mapping or business-policy change.

## Execution and acceptance

1. Reproduce fresh success, uncertain Shell/Policy and preflight failure offline;
   record sanitized prefixes, dispatch counts and projection. The owner's original
   retained case is not inspected; classify only proved deterministic observations.
2. Reuse forced confirmation Search and currentness owners. Revalidate immediately
   before first mutation even for a retained empty intent. Failed read-only preflight
   creates no write marker; expose existing typed failure and safe recheck.
3. Observe lost confirmation responses through bounded authoritative GETs only;
   suppress second confirmation and stale/session results. Preserve one-shot uncertain
   status checks and successful/failed/finalization behavior.
4. Project current supported recovery eligibility and sanitized prefixes from the
   existing ledger owner. Bind recovery to expected immutable submission UUID under
   locked reauthorization; source identity from retained backend input. Shell uses
   fresh provider validation; Policy uses existing Requested attestation contract.
5. Expose direct status check, exact candidate confirmation, Director evidence form,
   secondary technical details and explicit same-intent continuation. RM can check
   status but cannot recover. Unsupported Amend stays safely blocked with escalation.
6. Focused adverse tests, affected full checks and guarded physical recovery tests,
   browser normal/recovery/timeout paths, static/governance/secret/whitespace checks.
7. Freeze exact uncommitted content for a fresh independent read-only quality gate;
   remediate real findings and obtain a fresh review of changed content. Hand off.

## Resources and stop conditions

Tools available: PowerShell/Python, managed worktrees, subagents for assigned independent
review; browser harness availability to be established. Original checkout and camunda
worktree belong to other work. Evaluation outputs and processes remain untouched.
No .env access or real ACRA/GoldTier calls. Measurement gate cleared by the evaluation
chat's completed/idle final turn, revision 8; heavy checks began only afterward.
No commit, push, PR, merge, other phase, fabricated identity/success or uncertain replay.
Use existing guarded generated disposable Mongo database harness only.

## Evidence identity

Source: base plus uncommitted task delta. Tested and independently reviewed identities
will be recorded separately in the implementation handoff using exact content hashes.
Initial independent gate failed with four bounded findings, now under remediation and
fresh verification. The next action is exact independent re-review and owner handoff.
