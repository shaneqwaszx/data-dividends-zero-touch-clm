# Phase 24B post-gate remediation round 1/2 fresh independent mini gate

## Executive Result

**FAIL — one remaining P2. STOP.** The original eight interrupted-refresh regressions now pass, but an independently reproduced, supported authenticated route sequence prunes the exact old ownership analysis from bounded history. Recovery then leaves its generation-0 ownership blocker OPEN against sufficient generation-5 evidence. This occurs even when the blocker retains its explicit numeric generation=0. It also survives canonical durable serialization and service reconstruction, and a further ordinary correction does not repair it.

Reviewed content ID: `2c92c076f4ea6c84c51e603d234d36bc196413b3f27a0e1d86f3483c365c74f8`. Exact reviewed 15-path set and SHA256 values are in `PHASE_24B_REMEDIATION_ROUND_1_MANIFEST.json`. Branch `feat/phase24-registry-identity-ownership-ubo`; BASE_SHA, HEAD and inspected origin/main `039101b69772c4c9ae4ca7b4a7ca3e4c19b03f4c`. Entry/final frozen path hashes, compact sorted JSON identity over only path/sha256, all 67 entry records and five exact entry backups were verified. The previous FAIL report remains unchanged. This report is excluded from the reviewed identity.

This is a fresh independent review under the assigned worktree fyp-quality-gate skill and report template, with the attached owner authorization controlling scope and STOP criteria. No implementation, test, configuration or ordinary-document fix was made.

## Phase Acceptance Checklist

| Owner-required criterion | Fresh independent result | Evidence |
|---|---|---|
| Reproduce original OLD stale-blocker defect | PASS as reproduction | Exact verified entry service modules loaded through a subprocess import finder: 6 failed / 2 passed / 11 deselected, failures at original blocker OPEN versus expected CANCELLED. Candidate was not replaced. |
| Original interrupted same-UEN resume/correction retry | PASS in authored bounds | All original 8 cases pass within current 24-test execution, including both CLM/reconciliation interruptions and numeric/legacy blocker binding. |
| Registry generation determines blocker currentness after supersession | **FAIL** | F1: authenticated repeated interrupted rechecks plus normal ownership load/analyze prune old analysis; numeric generation-0 blocker remains OPEN against generation 5. |
| Restart/reload does not revalidate old blocker | **FAIL in adverse sequence** | Canonical durable serialization and reconstructed services retain the stranded blocker; resume returns 200/OPEN for both numeric and legacy variants. Authored two reload cases pass. |
| A-to-B-to-A non-resurrection | PASS in authored bounds only | Current authored regression passes; no separate independent A-to-B-to-A probe was executed before STOP. |
| Current/unrelated blockers preserved; no blanket clear | PASS in authored bounds only | Current insufficient/unknown-binding and four unrelated-blocker cases pass. Production diff performs selected retirement; no blanket clearing found. |
| Lock/CAS and reauthorization | PASS in authored bounds only | Current adversarial CAS and denial-inside-lock tests pass; source retains case lock and existing owners. |
| P2-1 graph/scalar contradiction preserved | PASS in executed regression bounds | Two independently executed authored cases in test_phase24b_p2_regressions.py verify REVIEW_REQUIRED, explicit contradiction and indeterminate candidates, with compatible control ANALYZED. |
| P2-3 real component final next action | UNEXECUTED by this fresh reviewer | Source/test hashes remain frozen. Implementer reports 24 component tests; that claim is not fresh independent evidence. No independent component/browser probe executed before STOP. |
| Guarded physical Mongo full approved 9-suite lane, zero skips | UNEXECUTED by this fresh reviewer | Implementer reports 47/47, zero skips; cannot supply independence. STOP occurred before reviewer physical execution. |
| Full affected static/contracts/security lanes | UNEXECUTED except diff whitespace | No fresh broad PASS claim. STOP occurred after reproduced P2. |

All three original P2 findings cannot be declared closed. The remaining P2 alone requires FAIL, independently of unexecuted lanes.

## Contract and Integration Findings

The owner explicitly requires a registry-derived blocker to be valid only for the evidence generation that created it, including interrupted retries and reload. The handoff's documented unknown/pruned-reference limitation does not waive that invariant. F1 is a current implementation blocker, not a later sponsor dependency or missing infrastructure.

The round-one repair remains within existing ownership and zero-touch owners and does not add a provider, connector, mapping, threshold or external approval rule. The current contract paragraph documents matching only retained analysis/history, but a description of the mechanism cannot authorize retaining a proven stale generation-0 blocker. Mock/local classifications and unresolved sponsor approval/Live dependencies remain unchanged.

## Tester and Adversarial Findings

Every command used the assigned worktree. The Desktop Python executable was reused as runtime only for accepted evidence; PYTHONPATH explicitly selected worktree backend and tests. Python used -B and pytest used -o addopts= -q -p no:cacheprovider --tb=short. No .env, secret, provider payload, retained Mongo, Atlas or clm_poc was accessed.

| Independently executed lane | Result |
|---|---|
| Exact OLD service import-hook replay on test_interrupted_same_uen_recovers_exact_obsolete_blocker | 6 failed, 2 passed, 11 deselected, one existing Starlette warning, 3.00s; expected OLD failure. Three loaded service backup hashes matched manifest entry_sha256. |
| Current test_phase24b_interrupted_retry.py plus test_phase24b_p2_regressions.py | 24 passed, one existing Starlette warning, 7.43s. This includes current original 8 plus 11 new adverse cases and 5 previous P2 regressions. |
| Fresh stdin authenticated-route adverse probe | Fails desired cancellation assertion: generation 5 resume 200, original blocker OPEN, current ownership ANALYZED. History is 4 and matcher False. |
| Fresh confirmation probe, numeric and legacy variants | Both reproduce normal resume 200/OPEN, serialized/reconstructed resume 200/OPEN and further ordinary correction 200/OPEN. After correction to generation 6, current getter returns None. Target calls remain read-only Search; reconstruction makes no calls. |
| git diff --check | PASS; existing line-ending advisories only. Report whitespace separately checked after write. |
| Entry/final frozen hashes and identity | PASS; 15 frozen paths, 67 entry records and five baseline backups verified. |

One initial current pytest invocation omitted explicit PYTHONPATH and failed collection with ModuleNotFoundError for the worktree-only ownership_evidence module. It supplied no accepted candidate evidence. Corrected explicit worktree PYTHONPATH execution produced the 24 passing tests above.

Full backend, physical wrapper, frontend component, contract, Ruff, mypy, supported-pattern secret scan, browser/lifecycle, provider smoke and publication gates were not executed by this reviewer after the STOP finding. Implementer counts in the handoff remain implementer claims. No build, dependency install or container mutation occurred.

### F1 — P2: exact-history-only matching strands a known generation-0 blocker after supported history pruning

Source owners:

- `apps/backend/app/services/ownership_analysis.py:980` — registry_dependency_is_obsolete only recognizes an exact analysis_id/version in retained current/prior analyses.
- `apps/backend/app/services/ownership_analysis.py:657` — ordinary identity-bound load retains only previous.prior_analyses[-3:] plus the replaced record, so first analysis disappears after five replacements.
- `apps/backend/app/services/zero_touch_orchestration.py:2030` — matcher passes only evidence_version; existing BusinessException.registry_evidence_generation is ignored.
- `apps/backend/app/services/zero_touch_orchestration.py:2054` — recovery exits without repair when no exact retained match remains.
- `apps/backend/app/services/zero_touch_orchestration.py:659` and `:1490` — resume and ordinary correction depend on that same matcher.

Reproduction uses normal authenticated routes, an existing typed failure boundary and synthetic evidence. There is no arbitrary record/version corruption:

1. Create UEN A and upload the synthetic document normally with RegistryAcquisitionOwnershipProvider and temporarily incomplete registry evidence. The original ownership analysis is REVIEW_REQUIRED, parent generation=0, and OWNERSHIP_REQUIRED blocker B0 is OPEN with its normal exact ownership reference and numeric registry_evidence_generation=0.
2. Restore sufficient registry evidence.
3. Repeat five times, within the existing 16-correction limit: submit the normal same-UEN ENTERED registry-identity route using current automation/CLM/case versions, inject ClmRequestError only from refresh_initial_search_after_recheck, receive 409, and immediately restore the checkpoint method. Parent/Search persistence advances normally before the injected failure.
4. After each interruption, use normal authenticated POST /api/onboarding/cases/{case_id}/ownership/load (201) and /ownership/analyze (200). This creates sufficient ANALYZED ownership for that current generation through the existing owner. No direct ownership record mutation is used.
5. At generations 1–4, history lengths are 1–4 and the original blocker matcher is True. At generation 5, history remains bounded to 4, the original exact analysis disappears, and matcher becomes False. B0 still retains numeric generation=0.
6. POST /api/clm/zero-touch/cases/{case_id}/resume returns 200 with B0 still OPEN and current generation-5 ownership ANALYZED. Calls are six Search operations and no target mutation.
7. Canonically serialize the existing DurableCaseSnapshot, validate it and reconstruct normal services with DurableOwnershipProviderBindingResolver. Resume again returns 200/OPEN and makes no target call.
8. A further non-interrupted authenticated same-UEN correction returns 200, advances generation 6 and still leaves B0 OPEN; now current ownership getter is None because the generation-5 analysis has been superseded. The composed path remains stranded.

The confirmation probe also models the supported legacy optional generation=None blocker and reproduces the same result. The numeric variant needs no legacy mutation: provenance and generation were created by the normal workflow, and a known stale generation=0 is still stored. This is not an impossible malformed reference or an unknown original dependency. Repeated partial checkpoints and legitimate ownership rebuilds are reachable through existing routes.

## Code and Architecture Review

The repair reuses existing ownership currentness, locks and CAS; no second freshness owner was added. However, blocker validity now depends on retention of a separate bounded historical copy rather than remaining recoverable from the blocker's existing known generation. The original invariant outlives that four-entry history. This is an unresolved correctness defect, not accepted debt. No remediation was attempted.

Change classification of round-one implementation: API/type no public shape change; durable schema no new shape/version/migration; connector/configuration/mapping/business threshold unchanged; auth/security ownership unchanged; architecture owner/dependency unchanged; provider status unchanged; runtime pre-submission retry behavior changed. Contract documentation changed. The review report changes none of these behaviors.

## Security Review

The observed defect stops progression; no unauthorized dispatch, target replay or false completed submission was observed. Accepted execution used synthetic authenticated fixtures and sanitized generation/state summaries only. Existing lock/reauthorization and CAS tests passed in authored bounds. The full secret/static/security lanes were not independently completed before STOP, and no blanket assurance is claimed.

## Required Fixes

F1 remains a P2 under original P2-2. A separately authorized bounded remediation must retain enough existing durable generation/provenance information to retire a proven stale registry blocker even after legitimate bounded history pruning, while preserving current/independent/unrelated blockers and existing freeze, lock, reauthorization and CAS boundaries. Provide failing-first coverage through this supported route sequence, reload/retry proof and a fresh independent gate. This report does not authorize that fix or a new persistence/version owner.

## Readiness

**Round 1/2 independent mini gate: FAIL. Remaining P2s: 1. STOP.** No deferred registry-cache, policy, performance, visual or broader UX work, publication, next phase or full Phase 24B acceptance may proceed under this report. Real ACRA/GoldTier interoperability, Live readiness and final human approval remain unproven. Further remediation requires owner authorization.

## Git Status

Before the reviewer report: 77 dirty paths (47 tracked modifications, 30 untracked); index empty. The only reviewer-owned project write is this report, yielding 78 paths (47 tracked, 31 untracked). Branch/HEAD/base/inspected origin/main remain the recorded039101b. All frozen implementation and preserved entry paths were verified unchanged at entry and final review. Prior FAIL reports and manifests were preserved.

No implementation/test/configuration/ordinary-document fix, staging, commit, push, PR, merge, reset, stash, clean, rebase, branch/worktree creation, container stop/removal or deferred phase occurred.
