# Performance optimization Gate 1 independent recheck

Outcome: **PASS** for the frozen corrected Gate 1 methodology and control group, reviewed on 2026-10-08. Both first-attempt methodology findings are closed. No product optimization, Gate 2 result, production/SLA capacity, external-provider acceleration, or publication readiness is certified.

## Exact source, tested and reviewed identity

- Worktree: C:/Users/shane/.codex-clean2/worktrees/performance-computational-optimization/data-dividends-zero-touch-clm.
- Branch: feat/performance-computational-throughput-optimization.
- BASE_SHA, source HEAD, fetched origin/main and merge-base: 198341b059ebf500252ce93d72eb099d2585c60b; ahead/behind 0/0.
- Product tree: 130b3471bccfd8780db2f05069f859b4ae4c5876. Tracked/index diffs are empty. Empty product-diff SHA-256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.
- Current source is unchanged main plus the task-owned uncommitted measurement delta. The corrected baseline executed that product tree with harness SHA-256 2bd95660 below. Independently reviewed content is the exact seven-file manifest below; neither the first rejected measurement nor a future changed tree supplies this PASS.
- Reviewer remained independent of implementation/remediation. The sole write in this recheck is this report; the original FAIL report is unchanged.

| Reviewed path | SHA-256 |
|---|---|
| .ai-pipeline/001_planner/PERFORMANCE_OPTIMIZATION_PROGRAM.md | ec63e56b6b813338c4392bac83ac98a4b6dfabce6ced6984419c98b37d071c71 |
| .ai-pipeline/reports/PERFORMANCE_OPTIMIZATION_BASELINE.json | 102796f299b302373239b881daa0103be35e8dc85a059a57ca2db04d0a0a5c31 |
| .ai-pipeline/reports/PERFORMANCE_OPTIMIZATION_BASELINE.md | 12a899eb275b41504681aeec66aaaf5fc03082b21a3b96d531c74ef3f2f52dbd |
| .ai-pipeline/reports/PERFORMANCE_OPTIMIZATION_GATE_1_QUALITY_GATE.md | 2b4428331e66da1a450ee55bc6024f6355c6e120136da74de18f0d89b05ecb65 |
| scripts/performance_optimization.py | 2bd95660eccc445a886991c58ba97d5211b401443c96e7366e57d2cb50c87222 |
| scripts/requirements-performance-optimization.txt | 4a0ad47fcff49479412490285fed97370090758226dfc6cfa4c9fe0663ac11d2 |
| tests/test_performance_optimization.py | 291673659c2582117ba26dde39735b7a814c731a4171b970d0e0d3787231d783 |

Reviewed manifest SHA-256: 4904cb3d4f178c32f9cc53ca80107b80e74921f846c4fdd6f16ecca488e87842. Construction: sorted repository-relative paths, tab, lowercase file SHA-256 and LF per row. The 20 current ignored raw sample/profile files use the same construction and have manifest SHA-256 a3349c81d2fa840a9ed8ff0436c421cc76b83a23e2e1a73d4ecb7afaacb1ad63.

## Acceptance evidence

| Gate 1 requirement | Result | Current direct evidence |
|---|---|---|
| Exact main control before product edits | PASS | HEAD/origin/main/apps tree and empty product diff independently checked |
| Required bounded supported fixtures and separate A/B/C lanes | PASS | All 10 workload definitions inspected; normal complete memory/Mongo flow, blocker correction/resume, Mock target success, offline uncertainty/recovery, detail, memory/Mongo portfolio, convergent graph and native PDF exercised |
| >=20 samples, separate warmup/setup/profiling | PASS | 20 raw samples per workload, 200 total; 2 warmups; CLI rejects partial/under20 baseline/final runs |
| Monotonic elapsed and trustworthy primary process CPU | PASS within parent-only claim | perf_counter_ns/process_time_ns surround operation only; no Resources or profiler in primary window; AST and source inspection confirm separation |
| Distributions, counters and outcome reproducibility | PASS | Independent exact recalculation of count/p50/p95/min/max/mean/sample stddev, payload summaries/nullability, outcome signatures and DB command sets for all samples |
| CPU-profile integrity and measured hotspot clues | PASS within diagnostic claim | Separate Yappi1.7.6 native-thread CPU run; all 10,274 saved profile function entries satisfy nonnegative self and cumulative>=self; app/all-function counters remain bounded |
| Peak memory/host CPU | PASS within sampled-observation claim | One separate untimed resource observation per workload, setup included; positive recorded peak RSS and bounded host CPU |
| Offline/configuration/physical-Mongo containment | PASS for inspected/exercised boundaries | No dotenv, explicit Mock/offline transport, fixed task port, generated allowlisted databases and guarded cleanup; independent negative probes below |
| Focused/affected regression, governance, lint and hygiene | PASS | Unit4; current affected regression89; six governance/security checks; configured Ruff; tracked diff and all seven untracked files checked |

Current benchmark environment is Windows11 build26200, Python3.12.10, 32 logical cores; versions and container resource limits are recorded in the reviewed baseline. Yappi/psutil are pinned optional development tools. No product manifest/lockfile/runtime dependency was added.

## Independent verification and finding closure

After the coordinator released the measurement window, this reviewer independently ran:

- Task-local Python unit discovery for test_performance_optimization.py: **4 passed**.
- Four CLI negative probes: incomplete baseline count19, partial final workload, count101 and warmup6 each rejected with exit2 before application resources.
- Task-runtime profiler version check: Yappi1.7.6. Injected inherited application configuration was discarded; dotenv disabled; ordinary settings returned memory/Mock. Three disallowed numeric/shared-port/IPv6 sockets were rejected before connection; internal socketpair succeeded.
- Raw-to-aggregate arithmetic for **10 workloads / 200 samples** and all saved profile functions: **PASS**. Unknown recovery/native/graph payload sizes remain null instead of invented zero-byte measurements. The baseline Markdown's10 data rows, rounding and DB command totals exactly match JSON.
- Source/AST check: resource observation begins after primary iterations; no Resources call appears in their scope. Profiler starts/stops in a separate operation window, with setup/teardown outside it.
- Exact configured Ruff command: .venv/Scripts/python.exe -B -m ruff check --no-cache --config apps/backend/pyproject.toml scripts/performance_optimization.py tests/test_performance_optimization.py: **PASS**.
- check_project_state.py, check_architecture.py, check_tooling_config.py, check_policy_authority.py, check_external_provider_readiness.py and check_secrets.py: each independently rerun with **exit0/PASS**.
- git diff --check: **PASS**; tracked/index name-status outputs empty. Explicit UTF-8, newline and trailing-whitespace check for all seven untracked reviewed files: **PASS**.

The initial default Ruff invocation encountered host-policy RUF059/I001/FURB157 diagnostics. Repository authority resolves this: there is no root Ruff config; the configured backend pyproject selects E/F/I/UP/B/SIM with line-length100. The explicit repository-configured invocation passes. The ambient invocation is not represented as passing and did not authorize source edits.

Current coordinator affected regression covers test_slice_b_registry_demo.py, test_policy_provider_recovery.py, test_zero_touch_database_happy_path.py and test_phase18_case_portfolio.py. The reviewer read gate1-collection.txt (explicitly89 collected) and gate1-regression.txt (89 passing dots, no skip/failure/error markers), reconciling the double-quiet log with the coordinator's exit0 execution receipt. Collection, regression, governance and baseline-run logs are current task-owned evidence under ignored .runtime/performance-optimization, not historical evidence. The coordinator baseline completed exit0; the reviewer independently validated its complete raw data rather than rerunning a competing benchmark.

**G1-01 closed:** the concurrent 10ms resource sampler is absent from every primary elapsed/CPU sample. Resource observations are separate and explicitly include setup. Native parent CPU median now reads0 at Windows process-clock resolution; that is not a zero-computation or child-CPU claim.

**G1-02 closed:** invalid cross-worker cProfile merging is replaced by Yappi CPU profiling with timing validation before save. Yappi records native-thread contexts and aggregates function CPU statistics; this use matches the [official API](https://github.com/sumerc/yappi/blob/master/doc/api.md). Every saved current profile passed independent invariants. Profile values include profiling overhead and are diagnostic clues, not precise wall-latency percentages. Direct clean timing must establish any retained optimization.

No required current Gate 1 correction remains. Original rejected data stays under ignored rejected-method1 and the original FAIL remains attributable to its earlier hashes.

## Contract, architecture, security and adverse paths

Current supported fixtures and canonical owners are reused. The harness creates no product rule, target-ledger bypass, parallel Shell/Policy/Amend mutation, uncertain-write retry, schema owner, authorization owner or provider promotion. Complete memory and Mongo onboarding preserve four registry operations and Search3/Shell1/Policy1/Amend1. Mongo onboarding records find481/insert1/update60; Mongo portfolio records find3/aggregate1. Twenty outcome/counter signatures per workload agree.

Offline Policy recovery retains one Shell and one uncertain Policy attempt in setup, performs zero timed mutation calls, and resumes only remaining readback. Search is not Policy-success evidence. The blocker fixture's legacy confirming test orchestrator and Mock IDP/ownership are disclosed. Portfolio fixtures contain100 supported cases and page50; the graph is the supported four-party/four-edge/three-path convergent case with stable exact-Decimal digest. Native evidence is one supported PDF/four fields, with no OCR-performance claim.

The reviewer did not read/copy .env, access clm_poc, issue real ACRA/GoldTier requests, or inspect protected artefacts. Mongo is task-local and generated/allowlisted; the guard probes do not claim an exhaustive OS network firewall. Sanitized aggregates contain counts/digests/statistics, not document/provider bodies or credentials. Secret scans passed on tracked/nonignored worktree files.

API/type, durable schema, connector implementation, owner runtime configuration, business rules, mappings, auth/security behavior, architecture owners, provider status and product runtime behavior: **unchanged**. Development measurement tooling, optional development requirements, tests, planner and reports changed.

## Limits, readiness and Git status

This is DEVELOPMENT_MEASUREMENT / LOCAL_MEASURED only. Parent CPU excludes document-child and Mongo-server CPU. Separate10ms RSS sampling can miss short peaks and is not per-case allocation. Small20-sample empirical p95 and noisy blocker/target tails do not establish statistical significance or production capacity. Short CPU samples may quantize to zero. Lane C owner-manual smoke supplies no performance data. Later optimizations must retain identical instrumentation/workloads and prove improvement exceeds measurement noise.

Gate 1 corrected control group: **PASS**. The coordinator may freeze its authorized local checkpoint and proceed to the already assigned Gate 2 process. This verdict does not accept any optimization or later gate, grant push/PR/merge authority, or establish Live ACRA/GoldTier readiness. Full cumulative/E2E/lifecycle and retained-change physical regression belong to their later assigned gates.

At freeze, all seven manifest files were untracked, tracked/index diffs were empty, and HEAD remained the required base. This recheck report is the reviewer's only additional file. No implementation/configuration/test fix, commit, push, PR, merge, branch switch, worktree cleanup or next-gate implementation was performed by the reviewer.

