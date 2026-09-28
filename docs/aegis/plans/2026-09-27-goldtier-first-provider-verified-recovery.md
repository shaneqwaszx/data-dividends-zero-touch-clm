# GoldTier-first provider-verified recovery implementation plan

**Date:** 2026-09-27
**Branch:** `feat/goldtier-sandbox-pipeline-inspector`
**Baseline / current `origin/main`:** `463ecdcb4357bb44618cdd5b277671766543dbfc`
**Scope authority:** Garden Business POC only; the user-authorized values are `Partnership - Unregulated` and `Commercial SBB (Small Business Banking)` with authority `USER_AUTHORIZED_POC`. They are not defaults or ACRA-derived values.

## Goal and boundaries

Complete the bounded pre-Phase-22 real GoldTier acceptance sequence without replaying the uncertain Shell, fabricating provider facts, falling back to mock providers, or introducing a second persistence owner. Add the minimum durable recovery and GoldTier-first orchestration needed to prove:

1. the historical Garden Shell remains recorded as attempted once with its original response uncertain;
2. later exact provider evidence recovers GoldTier ID `143878` under explicit `PROVIDER_VERIFIED_RECOVERY` authority;
3. Policy, Amend, and same-ID read-back resume through the existing durable target ledger;
4. a second Garden onboarding finds the same target first, skips ACRA and Shell, hydrates target state with explicit provenance, then safely performs its authorized update;
5. ambiguous search results stop before ACRA or mutation, while no-match results proceed to ACRA;
6. the pipeline inspector truthfully presents stage, provenance, and call history.

No push, PR, merge, autonomous approval, unsupported UEN Search, name-only recovery, acceptance-only ledger, or global provider vocabulary default is in scope.

## Architecture decision

Proceed by evolving the existing owners:

- `OnboardingCase` remains the canonical case aggregate.
- `GoldTierExecutionLedgerEntry` remains the sole mutation-ordering/no-replay owner.
- `MongoCaseStore` / `MongoTargetExecutionRepository` remain the durable persistence and CAS owners.
- the current GoldTier provider interface remains the only provider call boundary.
- recovery is a durable fact attached to the existing ledger model; it is not a replacement ledger.
- prior verified target state is discovered from existing durable case snapshots and carries an explicit `EXISTING_TARGET_STATE` provenance; it does not masquerade as fresh ACRA evidence.

Create a superseding ADR and decision-log entry because GoldTier-first ordering, durable recovery semantics, and the snapshot schema version are material architecture changes. Preserve the full approved GoldTier vocabularies per case; represent the two Garden values only as explicit case-authorized input/evidence.

## TDD route

`TDD Mode: off` — no explicit strict TDD route was requested. Add focused adverse-path and restart tests alongside each implementation slice before advancing to the next slice.

## Implementation tasks

### 1. Freeze contracts and add focused failing tests

**Files:**

- `apps/backend/tests/test_onboarding.py`
- `apps/backend/tests/test_zero_touch_orchestration.py`
- `apps/backend/tests/test_phase12_persistence.py`
- `apps/backend/tests/test_phase12_real_mongo.py`
- `apps/backend/tests/test_phase13_auth_rbac.py`
- `apps/backend/tests/test_goldtier_xpi_sandbox.py`
- relevant frontend tests under `apps/frontend/src/`

Add tests for the exact chronology, idempotent recovery, all rejection cases, zero Shell calls during recovery, persisted-before-call / persisted-after-result behavior, restart recovery, exact/no-match/ambiguous GoldTier-first branches, prior-state provenance, per-case vocabulary authority, and browser/API validation.

### 2. Extend the domain and durable schema

**Files:**

- `apps/backend/app/domain/models.py`
- `apps/backend/app/domain/target_submission.py`
- `apps/backend/app/domain/zero_touch.py`
- `apps/backend/app/persistence/models.py`
- `apps/backend/app/persistence/mongo_case_store.py`

Add validated initial identity and target-state provenance models. Add a `ProviderVerifiedRecovery` fact that records the historical uncertain Shell, recovered target ID, exact identity evidence, actor/time/authority, and `replayed=false`. Separate definitively completed provider calls from lifecycle-resolved operations so recovered Shell can unblock later calls without rewriting history. Increment the durable snapshot schema and migrate earlier versions deterministically.

### 3. Add repository queries without a new owner

**Files:**

- `apps/backend/app/services/repository.py`
- `apps/backend/app/services/target_execution_repository.py`
- `apps/backend/app/persistence/repositories.py`

Add bounded repository reads for prior verified UEN/name/country-to-target bindings and the case-bound recovery target. Keep memory and Mongo behavior identical. Enforce exact identity and single-candidate semantics.

### 4. Implement recovery service and RBAC API

**Files:**

- `apps/backend/app/domain/access.py`
- `apps/backend/app/services/authorization.py`
- `apps/backend/app/services/onboarding.py`
- `apps/backend/app/main.py`
- corresponding API/service tests

Add a least-privilege `TARGET_RECOVERY` capability for the authorized case-management role. Reauthorize inside the owning lock/CAS boundary. Validate untrusted browser input against case identity and a fresh real provider ID lookup. Support both an existing uncertain ledger and an explicitly labelled replacement recovery record after historical local-ledger loss. Make identical retries idempotent, reject overwrite/conflict/definite-failure/name-only/wrong-UEN/wrong-ID/multiple-candidate cases, and make no Shell call.

### 5. Implement GoldTier-first orchestration

**Files:**

- `apps/backend/app/services/onboarding.py`
- `apps/backend/app/services/clm_orchestration.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/app/domain/zero_touch.py`
- `apps/backend/app/main.py`

Accept legal name, UEN, and country as initial identity. Search GoldTier by supported fields only. On one exact match, persist the Search checkpoint, hydrate from verified prior target state with provenance, and skip ACRA and Shell. On no match, acquire ACRA through the current route. On ambiguous or insufficient identity, stop with human review and zero ACRA/mutation calls. Preserve target-ledger ordering for all later calls.

### 6. Update UI and pipeline inspector

**Files:**

- `apps/frontend/src/api.ts`
- `apps/frontend/src/types.ts`
- `apps/frontend/src/App.tsx`
- relevant frontend components/tests and E2E specifications

Collect the full initial identity, display GoldTier-first outcomes and provenance, provide the guarded recovery action only to authorized users, and show truthful operation chronology. Never label the uncertain historical Shell as having returned `143878`.

### 7. Record durable architecture and contract state

**Files:**

- `docs/decisions/DECISION_LOG.md`
- `docs/adr/` or the repository's current ADR location
- `docs/ARCHITECTURE.md`
- `docs/PROJECT_STATE.md`
- `docs/contracts/GOLDTIER_CONTRACT_BASELINE.md`
- `docs/contracts/GOLDTIER_CONTRACT_DISCREPANCIES.md`
- `docs/sponsor-questions/OPEN_QUESTIONS.md`
- active Aegis work evidence

Record authority classifications precisely: user-authorized POC values, provider-verified recovery, project-defined least-privilege recovery control, and unresolved sponsor/global-default questions. Do not elevate any POC fact to sponsor-confirmed.

### 8. Verify locally and physically

Run focused backend/frontend tests first, then the change-class matrix: type/lint/build, backend full suite, frontend full suite, contract tests, persistence and real-Mongo tests, provider conformance, security review, POC regression, diff/whitespace/secret hygiene. Use only an allowlisted disposable Mongo database for physical tests and never print its URI.

### 9. Execute the real bounded Garden sequence

Use normal Mongo-backed composition and a newly generated allowlisted durable database. Recover `143878` through the new API/service, create Policy, amend the same ID, perform real same-ID Search/read-back, and verify in the portal where technically available. Restart between persisted intent/result checkpoints to prove no replay. Run the second Garden onboarding with a synthetic document update; prove the same ID, zero ACRA, zero Shell, and same-ID amend/read-back. Preserve safe evidence only.

### 10. Independent gate, remediation, and local commit

Freeze exact content and ask a separate reviewer to run `fyp-quality-gate`. Remediate task-scoped findings, rerun affected verification, and obtain a fresh independent gate until the verdict is exact `PASS`. Only then stage the exact reviewed task-owned paths, inspect the staged diff, and create local commit(s). Do not push, create a PR, or merge.

## Stop conditions

Stop dependent external mutation if exact identity cannot be proven, the durable ledger cannot be established before the call, the provider result is uncertain, Mongo durable composition is unavailable, a value would need to be invented, the real provider would need to fall back to mock, or the reviewed content changes after final PASS without a re-gate.
