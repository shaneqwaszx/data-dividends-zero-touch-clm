# Pre-Phase 22 integrated capability expansion - Intent

## TaskIntentDraft

- Requested outcome: Implement, independently review, publish, and open a PR for the authorized pre-Phase 22 capability expansion without activating Phase 22 or unproved Live integrations.
- Goal: Deliver explainable entity resolution, ML-assisted UBO advice, mock advisory risk, bounded audit/workbench improvements, and an SME demo while preserving deterministic and provider safety owners.
- Success evidence:
- Focused RED/GREEN evidence, required verification matrix, exact independent quality-gate PASS, clean publication commit, pushed branch, open PR, and CI results.
- Stop condition: Stop dependent GoldTier work when source artefacts or sandbox evidence are absent; stop assignment mutation when role/capability authority is unresolved; stop publication unless an exact fresh independent PASS covers the reviewed revision.
- Non-goals:
- Live GoldTier/PingFed activation, autonomous approval, production OCR, Camunda, production SSO, non-Singapore registries.
- Scope: Single orchestrated session on feature/pre-phase22-capability-expansion; root is sole writer and Git owner; specialists and quality gate are read-only except their owned reports.
- Change kinds:
- EXTERNAL_PROVIDER,BACKEND_DOMAIN,BACKEND_API,AUTH_RBAC_SECURITY,PERSISTENCE,FRONTEND_STATE_CACHE,FRONTEND_UI,ARCHITECTURE_REFACTOR
- Risk hints:
- high

## BaselineReadSetHint

- origin/main@3ca232b58c3842f413c4552dbd3b85aabea4591c

## BaselineUsageDraft

- Required baseline refs:
- origin/main@3ca232b58c3842f413c4552dbd3b85aabea4591c
- Acknowledged before plan:
- none
- Cited in plan:
- none
- Missing refs:
- origin/main@3ca232b58c3842f413c4552dbd3b85aabea4591c
- Advisory decision: needs-baseline-readback

## ImpactStatementDraft

- Compatibility boundary: Legacy case snapshots and persisted events remain readable; Mock/default provider behavior remains unchanged; Phase 22 remains on hold.
- Affected layers:
- domain,service,API,persistence,frontend,contracts,reports
- Owners:
- Root implementation/Git coordinator; existing policy, zero-touch, activity, target-ledger, and ownership owners retained.
- Invariants:
- Deterministic Decimal ownership remains authoritative; advisory ML/risk never creates legal/compliance truth; no target-ledger bypass; no inaccessible-case disclosure.
- Non-goals:
- Live GoldTier/PingFed activation, autonomous approval, production OCR, Camunda, production SSO, non-Singapore registries.

These records are Method Pack drafts / hints, not authoritative runtime decisions.
