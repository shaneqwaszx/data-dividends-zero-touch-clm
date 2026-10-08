# Performance optimization baseline — corrected Gate 1 control group

Gate status: IMPLEMENTER EVIDENCE COMPLETE; independent recheck pending.
Claim: DEVELOPMENT_MEASUREMENT / LOCAL_MEASURED only. No product optimization yet.

## Source and environment

BASE_SHA, source HEAD, fetched origin/main and merge-base: 198341b059ebf500252ce93d72eb099d2585c60b.
Branch: feat/performance-computational-throughput-optimization.
Worktree: C:/Users/shane/.codex-clean2/worktrees/performance-computational-optimization/data-dividends-zero-touch-clm.
Clean isolated start; index empty; initial ahead/behind0/0. Primary checkout's unrelated
1037 untracked evaluation/output paths were preserved. All existing worktrees preserved.
Product tree: 130b3471bccfd8780db2f05069f859b4ae4c5876; uncommitted product diff digest: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 (empty diff).
Harness SHA256: 2bd95660eccc445a886991c58ba97d5211b401443c96e7366e57d2cb50c87222.

Machine: Windows-11-10.0.26200-SP0; Python3.12.10;32 logical/24 physical CPU cores,
34,086,969,344bytes RAM. Versions: {"Pillow": "12.3.0", "fastapi": "0.141.1", "psutil": "7.0.0", "pydantic": "2.13.5", "pymongo": "4.15.1", "pypdfium2": "5.13.0", "pytest": "8.4.2", "yappi": "1.7.6"}.
Node22.23.3/npm10.9.9; Docker29.8.1. Task-local ignored Python environment supplies
pinned native dependencies and optional dev measurement requirements. No product
manifest/lockfile dependency change. Task-owned mongo:7 image digest was inspected,
container limited to cpus2/memory1GiB, no host data volume, loopback port27861.

## Method and evidence lanes

Exact reproduction: `.venv/Scripts/python.exe scripts/performance_optimization.py --label baseline --count 20 --warmup 2`.
Each workload has two excluded warmups and20 measured repetitions. High-resolution
monotonic `perf_counter_ns`; median p50 and nearest-rank empirical p95. JSON contains
min/max/mean/sample standard deviation, request/response sizes where measured, repository,
provider and DB counts. No p99, SLA, confidence interval or production capacity claim.
Primary elapsed/process CPU has no resource sampler or profiler. Setup/login and
teardown are excluded. Fresh application/database state per mutating sample; read-only
fixtures reused within their bounded workload. Repository/HTTP counters remain identical
measurement instrumentation throughout later comparisons.

RSS/host CPU are one separate untimed sampled resource observation per workload,
including its setup. RSS combines parent and live document children at10ms cadence;
short peaks can be missed and it is not a precise per-case allocation metric. Parent
process CPU excludes native document-child CPU, Mongo server CPU and external-provider
latency. Windows process CPU can quantize short samples to zero; zero does not prove
zero computational work. Yappi1.7.6 CPU profiling is a separate run outside primary timing across native parent threads, with self/cumulative invariant checks. Its aggregate
function CPU figures include profiling overhead and are diagnostic ranking clues, never
wall-latency percentages. Native child parsing CPU remains unobserved. See the
[profiler API](https://github.com/sumerc/yappi/blob/master/doc/api.md).

Lane A: deterministic Mock/local, no real external HTTP. Complete memory onboarding
uses normal services with synthetic ACRA four operations, native PDF evidence and ordered
Mock target success. Mock target success times confirmation/send only after readiness.
Blocker correction/resume times one current demo/test discrepancy resolution through
ConfirmingTestZeroTouchOrchestrator with Mock IDP/ownership; it is a supported synthetic
recovery fixture, not a normal human interaction measurement. Uncertain Policy recovery
uses an injected offline synthetic XPI transport with an invalid endpoint; its timing
covers recovery+explicit resume, excluding the initial uncertain writes and login.
Source/provider labels remain Partial/Mock as configured; this proves no Sandbox access.
Detail uses a representative prepared case. Portfolio reads50 rows from100 retained
supported cases in one authorized team. Ownership graph has4 parties,4 edges and3 paths,
including convergent paths; all20 exact Decimal candidate digests agree. Native document
is one supported native-text PDF, one local extraction call/four fields. OCR was not a
performance workload and no OCR speed claim follows.

Lane B: separate complete onboarding and portfolio with fresh generated allowlisted
clm_p12 databases on the dedicated task container. Naming is validated before connection;
cleanup is verified through the existing helper and failure aborts acceptance. Mongo
never falls back to memory. No shared/original clm_poc or private .env was read/copied.
The network guard permits only task Mongo plus Windows' internal socket pairs. Inherited
application configuration is discarded before current ordinary-test isolation is loaded.

Lane C: owner's prior normal-environment observation is FUNCTIONAL SMOKE only. It is
not included in any latency, CPU, throughput or provider improvement figure.

## Fresh control group

| Workload / lane | n | p50 ms | p95 ms | parent CPU p50 ms | DB commands | Correctness |
|---|---:|---:|---:|---:|---:|---|
| memory_onboarding / A_LOCAL_DETERMINISTIC | 20 | 1216.980 | 1293.223 | 218.750 | 0 | PASS |
| mongo_onboarding / B_PHYSICAL_MONGO | 20 | 3595.463 | 3958.299 | 1992.188 | 542 | PASS |
| blocker_correction_resume / A_LOCAL_DETERMINISTIC | 20 | 112.982 | 211.655 | 109.375 | 0 | PASS |
| mock_target_success / A_LOCAL_DETERMINISTIC | 20 | 78.241 | 204.186 | 78.125 | 0 | PASS |
| uncertain_policy_recovery / A_LOCAL_DETERMINISTIC | 20 | 58.590 | 81.460 | 62.500 | 0 | PASS |
| case_detail / A_LOCAL_DETERMINISTIC | 20 | 17.863 | 19.854 | 15.625 | 0 | PASS |
| portfolio_memory / A_LOCAL_DETERMINISTIC | 20 | 47.551 | 55.624 | 46.875 | 0 | PASS |
| portfolio_mongo / B_PHYSICAL_MONGO | 20 | 18.712 | 21.366 | 0.000 | 4 | PASS |
| ownership_graph / A_LOCAL_DETERMINISTIC | 20 | 0.434 | 0.785 | 0.000 | 0 | PASS |
| native_document / A_LOCAL_DETERMINISTIC | 20 | 508.814 | 537.136 | 0.000 | 0 | PASS |

All20 mutating outcomes/operation counts per workload agree. Complete memory and Mongo
both perform registry1/1/1/1, target Search3/Shell1/Policy1/Amend1. Uncertain Policy fixture
retains Shell1/Policy1 total attempts, recovery mutations0, and one subsequent readback;
Search never proves Policy success and no generic write retry is introduced.
Complete Mongo onboarding: find481,insert1,update60. Portfolio Mongo: find3 for current
authentication/team context plus one aggregation; no detail fan-out. Memory onboarding
has183 onboarding repository gets. Prepared detail has14 onboarding gets and6 document
list calls. These are measured repeated-work candidates; no optimization is yet accepted.

## Ranked diagnostic hotspots

| Parent CPU profile clue | calls | self CPU ms, profiled |
|---|---:|---:|
| copy.py:118 deepcopy | 1089551 | 3765.625 |
| mongo_case_store.py:933 _reject_unknown_model_fields | 642078 | 2343.750 |
| builtins:0 isinstance | 3222312 | 1468.750 |
| mongo_case_store.py:903 _persistence_value | 194774 | 1125.000 |
| builtins:0 <method 'get' of 'dict' objects> | 2293191 | 1093.750 |
| builtins:0 id | 1465750 | 703.125 |

The largest parent-process repeated-work clues are defensive copying, recursive strict
unknown-field walking, serialization and Pydantic validation. These profiler times are
perturbed diagnostics. Clean timings and exact operation counts above supply the control
group; every proposed retained change needs a bounded causal experiment and identical
post-change measurement. Native process boundaries remain security controls and cannot
be removed solely because elapsed native extraction dominates part of memory onboarding.

## Verification, remediation and freeze

Initial frozen methodology received independent FAIL for P2 G1-01 concurrent Windows
sampler contamination and P2 G1-02 impossible merged cProfile attribution. Its original
report remains PERFORMANCE_OPTIMIZATION_GATE_1_QUALITY_GATE.md. Rejected aggregates,
all200 samples and profiles are preserved under ignored
.runtime/performance-optimization/rejected-method1 and are excluded from this table.
One bounded methodology remediation removed concurrent sampling and replaced the
profiler. Corrected all200 samples and warmups then completed with unchanged product
source. Raw current evidence stays ignored in .runtime/performance-optimization.

Focused harness statistics tests4 PASS; CLI requires full/all-workload>=20 baseline.
Affected current regression89 tests collected;89 passed, zero skips (double-quiet output
was independently reconciled with collection; exit0). Logs: gate1-collection.txt and
gate1-regression.txt. Ruff on task Python files PASS. Project-state, architecture,
tooling configuration, policy authority, provider readiness and tracked/nonignored secret
checks PASS. Fresh recheck independently verifies raw aggregates, guards, profiles and
frozen bytes; self-review supplies no independent PASS.

API/types, schema, connector, runtime configuration, business rule, mapping, auth/security,
architecture owners, provider status and product runtime behavior: NO CHANGE.
Only development measurement tooling/tests/plan/reports changed. No commit, push, PR or
merge yet. Next authorized action: independent Gate1 recheck; checkpoint only on exact
PASS, then Gate2. Complete cumulative/physical/E2E/Windows regression belongs to later
retained changes/final gate and is not claimed here.
