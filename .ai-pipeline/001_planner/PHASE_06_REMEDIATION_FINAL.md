# Phase 06 Final Remediation Handoff

## Boundary

Close only the three HIGH findings left partially closed by the latest independent
Phase 06 quality gate:

- P06-QG-005-R1: reviewed document lifecycle state bypasses current semantic conflict
  and confidence checks.
- P06-QG-006-R1: repeated typed Phase 05 finalization recovery is incorrectly converted
  into permanent `AUTOMATION_LOOP_GUARD`.
- P06-QG-009-R1: the generic registry boundary trusts mutable/preconstructed ACRA DTOs,
  does not bind returned UEN to the request, and retains unsafe provenance.

Preserve all nine independently closed Phase 06 findings and every accepted Phase
01-05 behavior. Do not redesign Phase 06 or begin another phase.

## Acceptance criteria

1. Every case-owned document is semantically re-evaluated against current canonical
   authority regardless of lifecycle state or insertion order. `REVIEWED` alone is
   never sufficient. Reviewed mismatch and low-confidence evidence remain business
   blockers unless a specific `KEEP_REGISTRY_VALUE` resolution clears only the current
   source conflict without rewriting historical extraction/review evidence.
2. `CLM_FINALIZATION_RETRY_REQUIRED` receives a small bounded attempt budget per
   invocation. Exhaustion persists a recoverable nonterminal target-finalization state,
   not a loop-guard failure. A later Phase 06 start/resume delegates to the same Phase 05
   recovery authority and reconciles the actual SUCCESS, MATCH_FOUND, POLICY_FAILURE,
   or PARTIAL_AMEND result without replay or identity change. The real no-progress loop
   guard remains effective.
3. Every ACRA result is dumped to primitives and freshly reconstructed under the strict
   provider schema before canonical mapping. Returned and requested UENs must normalize
   identically. Malformed/bypass-constructed results, unsafe or non-HTTPS provenance,
   and identity substitution become fixed sanitized technical provider failures with no
   downstream work. Safe Mock/SANDBOX results and not-found behavior remain accepted.
4. Permanent tests cover the named P06-QG-005-R1, P06-QG-006-R1, and P06-QG-009-R1
   adversarial matrices plus all prior Phase 06 regressions.
5. Architecture/contracts, the canonical regression catalogue, and supporting Phase 06
   remediation/security/regression reports record the final evidence while preserving
   the historical independent FAIL and all sponsor questions, especially Q-005 and
   Q-012.

## Security and sponsor constraints

- Provider-returned typed objects remain untrusted.
- Do not retain or project query-bearing/token-shaped registry endpoints, raw payloads,
  validation internals, private exception text, credentials, or uploaded bytes.
- `KEEP_REGISTRY_VALUE` is a provisional journey-specific conflict disposition, not a
  sponsor-confirmed master-data rule.
- Do not implement live ACRA, PingFed/GoldTier, hierarchy/related-party writes, final
  document/UBO policy, RBAC, durable orchestration, or Ready-for-Approval.
- Q-001/Q-002/Q-003/Q-004/Q-005/Q-006/Q-007/Q-008/Q-012/Q-013/Q-014 and
  D-018/D-023/D-024/D-025 remain applicable.

## Required verification

Run the full backend suite; focused Phase 01-06 and all three final-remediation groups;
contract and repository unittest discovery; Ruff; strict mypy; `pip check`; frontend
typecheck/tests/build; `npm ls --all`; secret scanner/tests; GoldTier validator tests and
classification; tracked, cached, and explicit untracked whitespace checks. Regenerate
the requested supporting security and regression reviews only after all behavior is
stable.

## Non-goals and completion

Do not stage, commit, push, merge, change branches, or start Phase 07. The next human
action after successful validation is a final independent Phase 06 re-gate.
