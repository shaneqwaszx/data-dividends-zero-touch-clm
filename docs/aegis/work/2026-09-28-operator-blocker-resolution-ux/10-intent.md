# Operator blocker resolution UX - Intent

## TaskIntentDraft

- Requested outcome: Correct Director case control and team selection, continue safe case evidence after unresolved GoldTier Search, project truthful pipeline state, and add accessible stage-to-resolution navigation.
- Goal: Correct Director case control and team selection, continue safe case evidence after unresolved GoldTier Search, project truthful pipeline state, and add accessible stage-to-resolution navigation.
- Success evidence:
- none
- Stop condition: Stop when success evidence is satisfied or a blocker/risk requires pause.
- Non-goals:
- No external ACRA/GoldTier call; no Amend retry; no related-party childId; no schema/repository change unless proven necessary; no commit/push/PR/merge.
- Scope: Bounded local implementation on feat/operator-blocker-resolution-ux; no external provider calls, no target mutation retry, no childId invention, no publication.
- Change kinds:
- feature
- Risk hints:
- Cross-backend/frontend workflow semantics, provider failure truth, authorization, cache deletion, and no-replay safety.

## BaselineReadSetHint

- AGENTS.md; docs/DEVELOPMENT_WORKFLOW.md; docs/PROJECT_STATE.md; docs/ARCHITECTURE.md; ADR-005; ADR-006; PR #61 accepted behavior

## BaselineUsageDraft

- Required baseline refs:
- AGENTS.md; docs/DEVELOPMENT_WORKFLOW.md; docs/PROJECT_STATE.md; docs/ARCHITECTURE.md; ADR-005; ADR-006; PR #61 accepted behavior
- Acknowledged before plan:
- none
- Cited in plan:
- none
- Missing refs:
- AGENTS.md; docs/DEVELOPMENT_WORKFLOW.md; docs/PROJECT_STATE.md; docs/ARCHITECTURE.md; ADR-005; ADR-006; PR #61 accepted behavior
- Advisory decision: needs-baseline-readback

## ImpactStatementDraft

- Compatibility boundary: Reuse existing DELETE endpoint/dialog, team authorization, provider ports, target ledger, and HumanInterventionPanel action ownership.
- Affected layers:
- frontend UI/cache; backend domain/API; auth/RBAC; external-provider projection
- Owners:
- existing onboarding, CLM, zero-touch, API projection, React Query, and frontend view owners
- Invariants:
- Backend authority, safe 404, explicit Director team, target-ledger no-replay, Search failure != no-match, and no target mutation while identity unresolved.
- Non-goals:
- No external ACRA/GoldTier call; no Amend retry; no related-party childId; no schema/repository change unless proven necessary; no commit/push/PR/merge.

These records are Method Pack drafts / hints, not authoritative runtime decisions.
