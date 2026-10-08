# Performance optimization Gate 1 independent quality gate

Outcome: **FAIL** for the frozen first measurement attempt, reviewed on 2026-10-08.

The workload executions and aggregate arithmetic passed the independent checks below, but the control group does not yet establish trustworthy application CPU/timing attribution. The resource sampler runs during primary measurement and contributes to process CPU without a measured observer-cost bound. The merged Mongo worker profile also contains materially inconsistent self/cumulative timing. No product optimization may begin from this attempt. The coordinator has assigned bounded harness remediation followed by a fresh independent recheck.

## Reviewed identity and boundary

- Worktree: C:/Users/shane/.codex-clean2/worktrees/performance-computational-optimization/data-dividends-zero-touch-clm.
- Branch: feat/performance-computational-throughput-optimization.
- BASE_SHA, source HEAD, origin/main, and merge-base: 198341b059ebf500252ce93d72eb099d2585c60b; ahead/behind 0/0.
- Product tree: 130b3471bccfd8780db2f05069f859b4ae4c5876. Tracked product diff is empty; its SHA-256 is e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.
- Source identity is unchanged main plus the uncommitted three-file harness/planner/test delta. The baseline executed that product tree with harness hash 30bfe17a below. The independent verdict reviews the exact manifest below; it is not a verdict on a later remedied harness or baseline.
- Reviewer write boundary: only this report. No implementation, test, configuration, ordinary documentation, or Git mutation was made by the reviewer.

| Reviewed path | SHA-256 |
|---|---|
| .ai-pipeline/001_planner/PERFORMANCE_OPTIMIZATION_PROGRAM.md | ec63e56b6b813338c4392bac83ac98a4b6dfabce6ced6984419c98b37d071c71 |
| .ai-pipeline/reports/PERFORMANCE_OPTIMIZATION_BASELINE.json | d99ba04c7fc5f55cca9bcbcffa6195242015d737dde4db11e8a9b31271fd6035 |
| scripts/performance_optimization.py | 30bfe17ab76bc651dccedf46b53748cff5256523691efebeb15d7573dd453f49 |
| tests/test_performance_optimization.py | 291673659c2582117ba26dde39735b7a814c731a4171b970d0e0d3787231d783 |

Reviewed manifest SHA-256: c5afb7c43f8c84423e524b993486fc859e73ecb4468f76669b71a160bcb29f99. Construction: sorted repository-relative paths, a tab, lowercase file SHA-256, and LF per row.

The 20 task-owned raw files (10 baseline sample JSON files and 10 profiles) under ignored .runtime/performance-optimization have manifest SHA-256 866751a0c47c9031f35d530e8d0e284e19591924812bdd08084ad896dccfe586, using the same construction. Their contents are first-attempt evidence only. The baseline Markdown report was not present at review freeze; no narrative baseline acceptance is inferred.

## Acceptance and execution evidence

| Requirement | Result | Direct evidence |
|---|---|---|
| Exact baseline before product edits | PASS | HEAD/base/origin/main and apps tree match; no tracked product delta |
| Required supported synthetic workloads | PASS for exercised behavior | All 10 workloads completed: memory/Mongo onboarding, blocker correction/resume, Mock target success, uncertain Policy recovery, detail, memory/Mongo portfolio, multiple-path graph, native PDF |
| At least 20 primary samples and separate warmups | PASS | Independently inspected 200 measured raw samples; 2 warmups per workload; CLI enforces complete baseline/final runs and count >=20 |
| Distribution arithmetic and bounded aggregates | PASS | Recomputed count, median, nearest-rank p95, min/max, mean, sample standard deviation, response bytes, outcome signatures and DB count sets directly from all raw samples; exact agreement |
| Operation/outcome stability | PASS within workload claims | All 20 samples per workload have the same non-payload outcome/counter signature; onboarding has four registry operations and one Shell/Policy/Amend each; recovery has zero timed target mutations |
| CPU, peak memory and elapsed integrity | FAIL / unverified attribution | Primary process CPU includes concurrent sampler; no sampler-free control or overhead bound |
| Ranked actual hotspot contribution | FAIL for precise timing attribution | Mongo profile select.select self 588.1611 ms exceeds cumulative 421.5752 ms; profile timings cannot be precise contributions |
| Private configuration and provider isolation | PASS for inspected/exercised boundaries | Settings isolation, injected offline transports, fixed task port, generated allowlisted databases and guarded cleanup; independent negative socket/config checks below |
| Applicable regression/hygiene | PARTIAL; no final passing claim | Four independent unit tests and untracked whitespace passed; coordinator affected-regression log was still reported running and contains progress only |

Independent execution in this session:

- python -B -m unittest discover -s tests -p test_performance_optimization.py -v: 4 tests passed.
- Four CLI negative probes: baseline count19, partial final workload, count101 and warmup6 each rejected with exit2 before application initialization.
- Initialization probe injected application configuration canaries, then verified they were discarded, dotenv was disabled, and ordinary settings resolved memory/Mock. External numeric address, shared Mongo port27017, and IPv6 endpoint were rejected before socket connection; internal socketpair remained usable.
- Independent raw-to-aggregate recomputation: 10 workloads / 200 measured samples passed, including stable outcomes, reported DB count sets, explicit A/B lanes, positive sampled RSS and bounded host CPU.
- Whitespace/newline inspection passed for all four reviewed untracked files. Tracked diff and index summaries were empty.
- Static inspection of all 10 saved profiles found the material Mongo select.select inconsistency below. Tiny additional differences in time.sleep and a native lock entry were not used as the material finding.

The coordinator's current affected-regression invocation names test_slice_b_registry_demo.py, test_policy_provider_recovery.py, test_zero_touch_database_happy_path.py, and test_phase18_case_portfolio.py. Its task-owned sanitized log is .runtime/performance-optimization/gate1-regression.txt. The reviewer saw progress through 100% but no terminal test summary/exit evidence at freeze, so it is not recorded as passing here. Ruff, governance/security checks and other lanes were not independently completed for this failed attempt. No historical/remote/main CI success substitutes for those checks. No heavy benchmark or physical suite was started by the reviewer during coordinator measurement/regression.

## Required findings and remediation

**G1-01 — P2: primary measurements include unbounded resource-observer work.** scripts/performance_optimization.py:104-134 and 531-540 start the Resources thread before setup and keep it active through every measured interval. Its 10 ms loop enumerates recursive children and samples each RSS plus host CPU. time.process_time_ns measures all parent threads, so parent_cpu_ms includes the sampler; process-tree enumeration on this Windows host is potentially material. Native extraction reports median parent CPU234.375 ms during median elapsed510.67945 ms, but that figure cannot separate application and observer work. The same observer may affect elapsed distributions through CPU/scheduling contention. No sampler-free measurement or bound was supplied. This is an unverified methodology requirement, not evidence that the application itself consumes that CPU.

Required closure: remove the sampler from primary elapsed/process-CPU runs; obtain resource metrics in a separately labelled untimed observation, or demonstrate an adequately bounded equivalent method; rerun the identical complete control group with >=20 samples and separate warmups. Preserve this rejected attempt only as rejected evidence. Do not carry these CPU/timing distributions into an accepted before/after claim.

**G1-02 — P2: merged worker profiling cannot support precise hotspot-time attribution.** scripts/performance_optimization.py:582-598 merges API worker profiles and ranks by reported self time. baseline-mongo_onboarding.prof contains select.select with 1,004 total/676 primitive calls, self588.1611 ms and cumulative421.5752 ms. The self/cumulative relationship is materially inconsistent for attribution. The profile is a separate instrumented run and its timings also include profiling overhead. Stable source call counts and clean end-to-end timings remain useful investigative evidence; they do not repair the invalid precise-time attribution.

Required closure: retain per-worker profiling identity, validate timing invariants, and suppress precise time/percentage contribution claims for profiles failing validation. Use clean direct workload/owner timing to confirm a proposed hotspot optimization. Rerank the accepted baseline using only evidence the repaired methodology supports. Native profiling covers the parent/provider and worker wait, not child parsing CPU.

## Contract, architecture, security and limits

The harness reuses current supported source/test fixtures and owners. It introduces no product owner, direct route-to-Mongo access, target ledger bypass, target mutation concurrency, generic uncertain-write retry, sponsor rule, schema or mapping. Offline Policy recovery starts from one synthetic uncertain Shell/Policy sequence, then times recovery plus resume only; the initial uncertain writes are excluded. The timed recovery sends no mutation, and resume adds only remaining readback. Customer Search is not treated as Policy success.

Blocker correction/resume uses the current legacy ConfirmingTestZeroTouchOrchestrator with Mock IDP/ownership; its internal explicit-confirmation fixture behavior must be labelled rather than represented as the normal operator interaction. Detail and portfolios use reusable pre-established authorized fixtures; portfolio has100 cases and limit50. The graph has four parties, four edges and three paths with stable candidate digest; it is the supported MULTIPLE_PATHS fixture, not production graph scale.

Lane A is Mock/local/offline transport; Lane B uses generated task-owned physical Mongo. Lane C owner-manual observation supplies no timing evidence. The reviewer did not read/copy .env, access clm_poc, issue real provider requests, or inspect protected artefacts. Raw report data consists of sanitized counts/digests/statistics rather than document/provider bodies or credentials. The negative socket probes test the direct guard and do not claim an exhaustive OS network firewall.

CPU is parent-only and excludes document children/Mongo server. First-attempt RSS/host CPU spans setup and warmups, so these are absolute process-observation values, not per-operation increments. Windows CPU quantization makes sub-millisecond graph CPU statistics unsuitable for small-delta claims; host CPU zero for that very short workload is not proof of zero CPU. Missing response-size measurement is represented as zero in the first-attempt recovery/graph/native summaries and must be treated as unavailable, not an actual zero-byte response. Small20-sample p95 supports only local development comparison; no p99, production/SLA, external-provider acceleration, or Live claim is accepted.

API/type, durable schema, connector implementation, owner configuration, business rules, mappings, auth/security behavior, architecture, provider classification and product runtime behavior: **unchanged**. The delta adds development harness/test/planner behavior only. Current sponsor dependencies remain later/external dependencies and do not authorize provider promotion.

## Readiness and final Git status

Gate 1 first attempt: **FAIL**. Gate 2/product optimization is blocked until bounded methodology remediation, full clean remeasurement, applicable verification and fresh independent exact PASS. This report grants no publication authority and no Live ACRA/GoldTier readiness.

Before this report, four task-owned paths were untracked, tracked worktree/index were clean, and HEAD stayed at the required base. This report is the reviewer's sole write. No commit, push, PR, merge, branch switch, cleanup, implementation fix or next gate was performed. The coordinator's next authorized action is harness remediation followed by a separately assigned fresh Gate 1 recheck.

