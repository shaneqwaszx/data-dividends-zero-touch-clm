# PR79 measurement review remediation

Outcome: both P2 findings adjudicated **VALID** and corrected in benchmark tooling only. Independent acceptance belongs exclusively to `PR79_MEASUREMENT_REVIEW_QUALITY_GATE.md` on the new frozen manifest; this report is implementer evidence.

## Task and identity

- Assigned bounded publication/evidence remediation of the two unresolved PR79 review threads; no new optimization phase.
- Existing worktree: `C:/Users/shane/.codex-clean2/worktrees/performance-computational-optimization/data-dividends-zero-touch-clm`.
- Branch: `feat/performance-computational-throughput-optimization`; start/source/test HEAD `b4ee8e92025eefc5946216befb417af15e6de356`.
- BASE, fetched origin/main and merge-base: `198341b059ebf500252ce93d72eb099d2585c60b`. Tracked/index state was clean at start. The unrelated main checkout and other worktrees are preserved.
- Change classes: CI_TOOLING + supporting DOCS_ONLY; emitted Tier1 owners, full AGENTS, workflow, selected architecture/state, original accepted gates and explicit task were read. No architecture/contract/provider/persistence change is necessary.
- Current-session preflight: PowerShell/exec, Git/GitHub CLI and independent subagent tools available. Worktree access explicitly escalated; Python3.12.10 from the exact worktree `.venv`, psutil7.0.0, local native dependencies and in-process TestClient available. No browser/process port or physical database is needed by this delta. No private `.env`, shared `clm_poc`, real provider or external network is used by automated measurement; existing initialize network guard remains. No installs/dependency changes.
- One coordinator owns implementation/Git; a fresh read-only reviewer owns the assigned new quality-gate report. Publication/threads only after exact independent PASS.

## Finding 1: resource sampler first observation

[Existing review](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/79#discussion_r4225414759): thread startup could return before polling populated RSS/CPU; a fast region could stop the sampler and leave `host_cpu` empty, making `statistics.mean` fail. **VALID**.

Decision: code-change at the existing Resources owner. A documentation-only correction cannot eliminate the startup race. The sampler now signals `first_sample` only after positive RSS and finite CPU observations are populated. `__enter__` waits up to1s for readiness, stops/joins on failure and raises a safe benchmark error; cleanup joins up to2s and fails closed if the owned thread remains alive. No arbitrary sleep accepts startup. The existing10ms observation interval is retained.

Reproducing exact publication Resources with200 no-op sections produced **1 empty host_cpu list**. Corrected Resources passes200 no-op sections with first_sample/RSS/nonempty CPU before entry returns and the thread stopped after exit. Readiness timeout, invalid first sample and bounded join failure are tested.

Old serial raw harness SHA256 `2bd95660eccc445a886991c58ba97d5211b401443c96e7366e57d2cb50c87222`; corrected `b0e3d88014be68b2d5019affcae558efc87a01080330ad6503619e61ffe31f69`.

All176 recorded historical resource scalar cells across BASELINE/GATE2/GATE3/GATE4/GATE6/FINAL were audited (includes duplicated embeddings):93 positive RSS values;83 finite CPU means in0..100. Finite original `statistics.mean` outputs prove those CPU lists nonempty. Concurrency stores RSS only: its positive peaks prove nonempty RSS observations; raw CPU-list contents/counts were never persisted and are not claimed recovered. There is no accepted empty resource observation. Existing collected resource values remain historical valid observations; this correction hardens future/reproduction execution and does not retroactively relabel measured harness bytes.

## Finding 2: health timing during active provider work

[Existing review](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/79#discussion_r4225414765): provider-entry event could remain set after work completed, allowing an idle-app health timing to be labeled active intake responsiveness. **VALID**. The old health_ms claim is **SUPERSEDED / REQUIRES REMEASUREMENT**, with original numeric values retained as explicitly superseded history.

Decision: add a diagnostic probe in the existing concurrency harness, separately owned from primary cohorts. `measure_level` source is unchanged. Its elapsed/makespan/CPU/request behavior stays original; the primary run output now labels incidental health timing UNSYNCHRONIZED and directs reproduction to --health-probe. No primary workload is slowed.

`ActiveProviderProbe` counts invocations under a lock. Each wrapper executes the real local PDF provider then holds inside that same invocation, before return. The provider-entered event here establishes the hold. At /health TestClient transport entry, the dispatch hook under the same lock requires active>0, held>0 and an unreleased barrier, records counts/time and signals dispatch. Health completion records whether the hold persists and signals immediate release. An independent guard waits at most100ms after dispatch before releasing a blocked baseline; an independent20s operation/dispatch failsafe and finally/context cleanup prevent a stranded provider barrier. Executor teardown occurs after probe release. Intakes are drained and active/held/call counts and PENDING_INPUTS/NOT_SUBMITTED are asserted.

Transport entry is the in-process request-dispatch boundary, after request construction; it is not a claim that the blocked baseline event loop has begun its health handler. The baseline cannot handle health during its held synchronous invocation. Its five-intake queue also adds ordinary subsequent native work after release. Candidate health completes before release in every measured observation. The100ms control is a bounded diagnostic release budget, not a fabricated native workload or a latency-improvement percentage.

Old concurrency raw harness SHA256 `8afb25cbbe12fb3872649d2404365e42eeac82218ddd4717cc8020c0ce2fc9f8`; corrected published harness `317bc9f874b170971677b8e28a6c2993af64efa844d21d414dfa37ac193957a7`.

Baseline measured full method `b50c47884b9e183ef2f5c96a9bc99a19be9da1d965862020c190d33e8db1f089` and candidate measured method `317bc9f874b170971677b8e28a6c2993af64efa844d21d414dfa37ac193957a7` differ only by the primary-run `health_metric_status` metadata field, added while baseline collection was running; it is outside both timing paths. The exact baseline method snapshot is reconstructable by removing that one field and its SHA matches the recorded before identity. All three executed diagnostic class/function definitions are identical, normalized-definition SHA256 `f968f6ef2b89269abe07ef3076608fb9659b952c2a70e101a3a1c46312f80a24`. Both measured identities are retained; neither is falsely relabeled. The unchanged primary definition SHA256 is `67fdfb71bb17e1cb19c2f4fb4357adf3f3ca57ef7e852036a1f627c7c79ca16f`.

## Corrected bounded measurement

Exact baseline198341b source was imported read-only from the clean existing baseline-control checkout; candidate app source remains exactb4ee8e9. The corrected harness is in the performance worktree for both arms. Same machine, exact worktree Python/dependency environment, synthetic PDF digest, memory/Mock/local composition, clock and release budgets match. Two warmups per arm/level remain separately excluded; n20 measured per cell. Pilot n1 evidence is retained separately and excluded. Baseline collection overlapped bounded governance checks; there is no controlled host-idleness or statistical-significance claim.

| Arm | Concurrency | n | p50 ms | p95 ms | min ms | max ms | mean ms | stddev ms | Completed held |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Exact baseline | 1 | 20 | 115.24060 | 119.2050 | 109.2359 | 120.9048 | 115.24003 | 2.80941 | 0/20 |
| Exact baseline | 5 | 20 | 3968.36220 | 4067.0920 | 3893.4002 | 4120.2134 | 3979.12412 | 51.69685 | 0/20 |
| Candidate | 1 | 20 | 2.33160 | 2.6846 | 1.9798 | 2.9332 | 2.36279 | 0.23335 | 20/20 |
| Candidate | 5 | 20 | 2.51055 | 3.5114 | 2.1396 | 3.9070 | 2.70308 | 0.50494 | 20/20 |

All80 measured +8 excluded warmup dispatches have active_provider_count>0 and held_provider_count>0. Baseline dispatch minimums active/held1/1 at each level; candidate level1 minimums1/1 and level5 minimums5/1. All240 measured +24 warmup intakes complete REVIEWED/AUTO_CONFIRMED with4fields/1native page, all cases PENDING_INPUTS/NOT_SUBMITTED, active/held counts0. Zero target mutations, registry operations, external calls, errors or timeouts. Sample-level proof and all requested aggregates are in PR79_MEASUREMENT_REVIEW_EVIDENCE.json.

Old health p95 level1 before/after494.0678/3.1821ms and level5 4393.6318/5.9458ms are superseded and support no active-work claim. Corrected controlled-active measurements replace those claims without carrying over a percentage. The original makespan five-case4790.6146/1159.45105ms and62.66/254.48intakes/min remain historical throughput observations; this remediation does not remeasure or reattribute them.

## Evidence classification and preservation

| Evidence | Disposition | Reason |
| --- | --- | --- |
| Validator measurements | Unaffected historical | Product/validator measurement code unchanged |
| Mongo read measurements | Unaffected historical | Product/read timing and observations unchanged |
| Primary intake makespan/throughput | Unaffected historical | Exact primary function and app source unchanged; no inserted delay/changed timing |
| Original health_ms | SUPERSEDED | Entry signaling did not establish ongoing provider activity |
| Original RSS/resource observations | Retained historical valid observations | Positive RSS and finite original CPU mean audit; corrected startup is future robustness |

Historical reports/gates/raw artifacts are preserved. Only cumulative FINAL.md/JSON health statements and current correction provenance change; original FINAL bytes remain in Git at b4ee8e9 and ignored task snapshots with exact old hashes in companion evidence. Original source/tested/harness fields remain original; current candidate identity is separately recomputed. No earlier PASS/FAIL gate is rewritten. No old raw sample is presented as corrected collection. The earlier E2E synchronization PASS is not reopened.

## Verification and limitations

- Focused unittest: tests.test_performance_optimization + tests.test_performance_review_remediation:16 tests OK;200 corrected no-op regions; original race reproduced1/200. Failure, expiry, zero/stale activity rejection, provider exception, cleanup and exact primary-function preservation covered.
- Existing backend intake concurrency suite:7 passed, no skips; product source unchanged.
- Ruff on both changed scripts/new test:PASS.
- mypy check-untyped-defs on concurrency/new test:PASS2source files. Strict mypy on exact AST-extracted Resources class:PASS1file. Whole serial harness mypy still reports the same3 pre-existing diagnostics as exactb4ee8e9 (socket method assignment2 and nullable historical current indexing1); none is introduced in this delta and no full-script type PASS is claimed.
- Contracts:44 tests OK. Governance/security unit suites:107 tests OK.
- check_project_state/check_architecture/check_tooling_config/check_policy_authority/check_external_provider_readiness/check_secrets:PASS. Final tracked + explicit untracked whitespace/UTF8/hygiene and full diff checked before independent freeze; the independent report records its own final checks.
- Full product backend/frontend/OCR/physical/browser suites are not locally rerun for this harness-only change. Original accepted product evidence is preserved; publication still requires fresh seven-lane push and PR CI. No timeout/assertion relaxation, install, product or database mutation occurred.

API/types, schema, connectors, product configuration/dependencies, business rules, mapping, auth/security, architecture, provider classifications and product runtime behavior: **unchanged**. Benchmark runtime behavior and measurement evidence/provenance: **changed** as described. Independent QG does not promote any Mock/Local/Partial provider or establish Live/production capacity/SLA/full-case throughput. Existing sponsor blockers remain outside this task.

## Next authorized action

Freeze complete candidate hashes in PR79_MEASUREMENT_REVIEW_MANIFEST.json; obtain fresh independent exact PASS. Then coordinator separately enters publication role: reverify unchanged content, reply/resolve both existing threads, scoped commit, canonical clean committed pre-PR/checklist, fresh main drift assessment (STOP on drift), normal push to existing PR79, and wait for all7 lanes in both fresh runs. No new PR, force push, merge, auto-merge or next phase. Final commit/remote/thread/CI identity is returned in the owner handoff rather than backfilled into reviewed reports.
