# Phase 24B post-gate remediation round 2/2 fresh independent MINI gate

## Executive Result

**FAIL — one independently reproduced P2. STOP ENTIRE SESSION.** Generation-first retirement fixes the original five-refresh history-pruning defect, but recovery fails when the remaining valid blockers have chronological order different from stage order. A retained independent target confirmation followed by a genuine current ownership blocker makes resume select READINESS even though OWNERSHIP is the earliest open stage. The repository rejects the recovery candidate with an uncaught ValueError. The old blocker stays OPEN and the workflow cannot resume.

This is the last authorized Phase 24B remediation round. No Phase 24C development, remediation, publication or new worktree may follow this FAIL. Prior failed gates remain immutable.

Fresh independent reviewer: separate reviewer agent, GPT-6.1 Sol / High, applying the assigned worktree fyp-quality-gate skill and report template. Review writes only this report; no implementation/test/configuration/documentation repair occurred.

## Reviewed Identity and Scope

Worktree: C:/Users/shane/.codex-clean2/worktrees/phase24-registry-identity-ownership-ubo/data-dividends-zero-touch-clm.

Branch: feat/phase24-registry-identity-ownership-ubo. BASE_SHA, HEAD and inspected origin/main: 039101b69772c4c9ae4ca7b4a7ca3e4c19b03f4c. Uncommitted, unstaged candidate; empty index. No fetch or remote-main freshness claim.

Frozen content ID: 3e520a839d6eb0e257b3b14c7ceacf989999e0dbf216f196eb1a463fa4c02e4a. Complete 82-path set and exact SHA256 values are in PHASE_24B_REMEDIATION_ROUND_2_MANIFEST.json. Manifest SHA256: c494f3ffc5b593ffceb2625af8be8a3e1a3edfaa6f9476497094afb1f7487055. All 82 candidate hashes, deterministic compact sorted path/sha256 identity, 74 preserved round-entry hashes and the manifest itself matched at entry and final pre-report verification. Exact entry service backup hashes matched entry.json before OLD import-hook execution. No candidate source swapping occurred.

Authority: latest owner attachment80cd96ac, root/backend/frontend AGENTS, Phase 24B planner, round-two scope/handoff/delta/manifest, preceding failed MINI gate, current workflow/architecture/state and relevant ownership/persistence/security authority. Scope is the bounded generation-currentness remediation plus mandatory preservation checks, not acceptance of deferred Phase 24C.

## Phase Acceptance Checklist

| Mandatory MINI criterion | Independent result | Direct evidence |
|---|---|---|
| 1. OLD exact history-pruning sequence | PASS as reproduction | Exact entry ownership_analysis and zero_touch_orchestration modules loaded through subprocess import finder; normal authenticated interrupted correction plus ownership/load and ownership/analyze leaves numeric generation-0 blocker OPEN at 5 and 11 replacements. Four-replacement control cancels. |
| 2. Five-refresh prune boundary | PASS in isolation | Fresh route probe on current candidate: history remains four, generation-zero analysis is absent, current generation=5 ownership ANALYZED; resume cancels original blocker. |
| 3. More than five refreshes | PASS in isolation | Fresh 11-replacement route probe cancels the original numeric blocker and retains current analysis; authored 10/12 cases also executed. |
| 4. Serialized reload | PASS in isolation | Canonical _persistence_value(DurableCaseSnapshot), model validation and reconstructed services, restarting at generation3 before pruning and generation5 after pruning. Known generation0 cancels; pruned unproven null remains OPEN. |
| 5. Retry after reload | PASS in isolation | Resume after reconstructed state and repeated idempotent resume preserve current analysis and make no target call. |
| 6. Further same-UEN correction | PASS in isolation | Following recovered 4/5/11 and restart variants, ordinary authenticated ENTERED correction advances the generation, retains cancellation, recomputes ownership and makes only one Search. |
| 7. A-to-B-to-A | PASS | Independent five-refresh sequence followed by two interrupted changes A->B->A without intermediate ownership rebuild; current generation7 receives a new analysis, old A blocker cancels, eight Search calls and no target mutation. |
| 8. Unrelated blocker preservation and currentness composition | **FAIL** | F1: canonical owned state retains independent READINESS target confirmation plus newer insufficient OWNERSHIP generation6; recovery uses chronological first instead of earliest remaining stage and throws before saving retirement. Individual authored preservation cases pass. |
| 9. Greater/equal/less generation | PASS in isolation | Independent pruned generation5 variants: binding0 cancels, binding5 and6 remain OPEN/WAITING_FOR_REVIEW. Pruned null remains review; retained legacy controls executed in authored suite. Six independent new type/stage combinations bind generation0 even from current null-generation registry analysis and survive canonical serialization. |
| 10. CAS/concurrency/authorization | PASS in executed bounds | Independent older automation and ownership candidates reject CAS after generation7; reauthorize callback observes owning case lock and denial leaves canonical snapshot unchanged. Independent physical lane exercises stale-writer boundaries; no last-writer-wins change found. |
| 11. P2-1 contradiction behavior | PASS | Fresh 40% graph vs compatible class/unit denominator100 and scalar20/80 gives REVIEW_REQUIRED, explicit CONTRADICTORY_OWNERSHIP_EVIDENCE, all retained candidates INDETERMINATE/REVIEW_REQUIRED. Compatible scalar40 control is ANALYZED; all calls remain Search only. |
| 12. P2-3 next-action behavior | PARTIAL before STOP | Independent HTTP flow pauses for final RM confirmation, three resumes do not auto-submit, explicit confirmation alone executes Mock target sequence, terminal resume does not replay. Source has explicit final/terminal next action; fresh frontend rendered/component execution was not completed before reproduced P2 STOP. Implementer 24-component-test claim remains inherited evidence. |

Every required criterion must be verified and no P0/P1/P2 may remain for PASS. F1 independently requires FAIL; the incomplete fresh rendered portion of criterion12 also prevents a full independent PASS claim.

## Contract and Integration Findings

Generation-first currentness uses the existing durable BusinessException.registry_evidence_generation and authoritative case identity-correction count. Less-than retires; equal/future stays review. Legacy null needs exact retained registry provenance and existing currentness; unknown/pruned null stays review under explicit owner acceptance. History is not enlarged and UEN equality is not the currentness owner.

The updated ownership contract describes these semantics without inventing a sponsor policy, new counter, mapping, target approval or provider classification. All NEW dependency types across OWNERSHIP/READINESS have a current-generation binding path. The stage/type/reference guard protects independent target/classification/document references. F1 is a current recovery correctness blocker rather than a later sponsor dependency. No real ACRA/GoldTier interoperability or Live readiness is asserted.

## Tester and Adversarial Findings

All shell commands set the assigned worktree explicitly. Desktop .venv was reused only as executable/dependency runtime; worktree backend/tests were selected by PYTHONPATH or script sys.path. Python used -B; ordinary pytest used -o addopts= -q -p no:cacheprovider --tb=short. Physical wrapper child bytecode was disabled by environment. Synthetic temporary probes were outside the repository. No .env, credential, private sponsor body, external provider, retained database, Atlas or clm_poc was accessed.

| Fresh independent execution | Result |
|---|---|
| Exact entry import-hook OLD probes | Eight completed variants. OLD numeric5/11, before/after-pruning reload remain OPEN; four boundary control cancels; null/equal/future controls remain OPEN. Expected OLD defect reproduced without modifying source. |
| Current focused backend eight suites | 303 passed, one existing Starlette warning, 68.01s. Includes generation suite19, interrupted-retry suite19 and prior P2 cases. |
| Independent current route/adversarial probes | 4/5/11, restart3/restart5, retry/further correction, numeric/null/equal/future, A-B-A, lock denial, stale CAS, six new registry dependency combinations passed in isolation. Mixed retained stages reproduce F1. |
| Full backend | 1665 passed, 51 guarded physical skips, four existing warnings, 159.68s. Already running before F1 was confirmed; no repeated broad execution after STOP. |
| Approved physical Mongo wrapper | 9 suites; 51 collected, 51 passed, 0 failed/errors/skipped. Fresh allowlisted fixture databases only, task-created mongo7 service on loopback port27024; URI constructed locally and never printed/persisted. Container unchanged by reviewer. |
| Ruff | PASS with --no-cache. Initial default cache attempt was blocked by filesystem permissions and is not passing evidence. |
| Configured strict mypy | PASS, 115 source files, --config-file apps/backend/pyproject.toml and temporary external cache. Initial invocation without that configuration produced two diagnostics; corrected configured execution passed. |
| Normal git diff --check | PASS, configured line-ending behavior preserved. |
| Final frozen identity | All82/preserved74/manifest hashes unchanged; index empty and branch/HEAD/origin-main unchanged. |

The implementer reports 361 focused, 44 contracts, 24 frontend component cases and governance/secret lanes; these are inherited handoff claims, not fresh executions by this reviewer. Fresh contract/governance/secret, full frontend/typecheck/build, browser/lifecycle, provider smoke and publication gates were not completed after STOP. No stale/unexecuted lane is called passing.

Some initial synthetic probe setups were rejected before accepted execution: returning to A incorrectly used ENTERED rather than OTHER; new exception injection collided with deduplication; cancellation left an inconsistent WAITING_FOR_REVIEW record. These were corrected only in the external temporary probe, not candidate source. F1's final reproduction instead uses valid canonical service-created blockers, passes domain validation and durable reconstruction before resume, and does not rely on those rejected setups.

### F1 — P2: recovery selects chronological first remaining blocker instead of earliest active stage

Source: apps/backend/app/services/zero_touch_orchestration.py:2098-2104, especially current_stage=remaining[0].stage. Repository validation: apps/backend/app/domain/zero_touch.py:546 requires earliest open stage. Canonical insertion already handles this correctly at apps/backend/app/services/zero_touch_orchestration.py:3216-3229 using min(..., key=stage_order.index).

Independent reproduction:

1. Create synthetic UEN A and document using normal authenticated routes, registry initially insufficient. Workflow creates generation0 OWNERSHIP_INCOMPLETE blocker B0 through the normal owner.
2. Perform five ordinary same-UEN corrections interrupted only at the typed CLM projection checkpoint. Between each, POST ownership/load and ownership/analyze normally. Generation5 ownership is ANALYZED and the generation0 analysis is legitimately pruned from four-entry history; B0 remains OPEN pending recovery.
3. Under the owning case lock, use the canonical _add_exception service seam to retain an independent TARGET_CONFIRMATION_REQUIRED at READINESS, with non-ownership reference and null registry generation. This is an explicit adversarial unrelated-safety input, not a claim that the normal route automatically reached target readiness while B0 remained open.
4. Perform a sixth supported interrupted same-UEN correction with synthetic registry evidence insufficient again; normal ownership/load/analyze returns REVIEW_REQUIRED with current generation6.
5. Under the case lock call the existing _raise_ownership_exception for that genuine analysis. It creates the current generation6 OWNERSHIP_INCOMPLETE blocker. No arbitrary record/version swap is used for this blocker.
6. The chronological OPEN sequence is OWNERSHIP(B0,gen0), READINESS(independent target,null), OWNERSHIP(current,gen6). Current stage is correctly OWNERSHIP. validate_automation_record passes. Canonical DurableCaseSnapshot serialization, validation and service reconstruction also pass, proving this is accepted durable owned state.
7. POST resume finds only B0 obsolete. The candidate retains both unrelated/current blockers but sets current_stage=READINESS from remaining[0]. The repository raises ValueError: current review stage must be the earliest open blocker. The error escapes start/HTTP processing. The case remains with B0 OPEN; current generation6 stays insufficient and no target call occurs.

This violates mandatory criterion8 and safe recovery composition with genuine current ownership/independent target control. Individual singleton preservation tests cannot establish this multi-stage condition. Remediation guidance, if separately authorized in a future task: select the earliest remaining active stage using the same existing stage-order authority as canonical insertion, preserve both blockers/decisions, and cover durable reload plus mixed chronological/stage order. This gate performs no fix and grants no remediation authorization.

## Code and Architecture Review

The original pruning root cause is addressed: known durable blocker generation remains usable after analysis history pruning. Existing ownership/zero-touch owners, bounded histories, CAS, reauthorization and target freeze are preserved. No second generation owner was added. The remaining stage-selection defect is in the composed recovery path, despite the generation comparator itself passing.

Round-two API/type and durable schema shape: unchanged. Connector/configuration/provider status: unchanged, non-Live. Mapping/business threshold: unchanged. Auth/security ownership: unchanged, recovery category guard tightened. Architecture owner/dependency: unchanged. Runtime behavior: generation-first obsolete-dependency retirement and new dependency binding changed; mixed remaining-stage recovery remains defective. Contract documentation updated. This report changes no runtime behavior.

## Security Review

No unauthorized target dispatch/replay, stale overwrite, credential disclosure or false completed state was observed. Independent owning-lock denial and stale CAS passed; the physical suite passed with no skips. F1 stops progression through an uncaught internal invariant error. Broad security/secret assurance is not substituted from inherited tests. Unresolved final approval and sponsor/Live integration remain separate later dependencies.

## Required Fixes

One P2 remains: F1. No post-gate fix is authorized within exhausted Round2. Full fresh frontend preservation evidence also remains incomplete because STOP took precedence. Do not rewrite any prior failed report or label the candidate accepted.

## Readiness

**MINI GATE: FAIL. Round2/2 exhausted. STOP ENTIRE SESSION.** Phase24C was not started and must not start. No commit, push, PR, merge, publication or new worktree occurred. Real ACRA/GoldTier and final human approval readiness are not established. Only a new explicit owner task can authorize further work.

## Git Status

Final pre-report status: 83 dirty paths, 47 tracked modifications and36 untracked, empty index. The manifest itself is outside its82-entry content identity; the reviewer report is also excluded. Adding only this assigned report yields84 paths, 47 tracked and37 untracked. Branch/HEAD/base/inspected origin-main remain039101b69772c4c9ae4ca7b4a7ca3e4c19b03f4c. Frozen implementation and all preserved old reports/manifests remain unchanged.

The sole reviewer-owned repository write is PHASE_24B_MINI_QUALITY_GATE_ROUND_2.md, UTF8/LF. No implementation/test/configuration/ordinary-document edit, staging, Git mutation, dependency install, source swap, container mutation or continuation occurred.
