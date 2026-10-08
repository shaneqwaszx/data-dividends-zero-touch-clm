# Gate 6 independent quality gate

## 1. Executive Result

**PASS - Gate 6 only, on the frozen methodology and results below.** Both load runs
use the same unchanged product and method. All 520 primary cases in 70 closed cohorts,
294 statistical aggregate cells, operation counts and 46 raw artifact hashes
reconcile. Recovery/currentness/concurrency adverse checks passed independently.
No required product, safety, method or reporting correction remains.

The evidence identifies a local closed-cohort throughput plateau: memory around
concurrency 10, physical Mongo around 5-10. Mongo concurrency 20 is explicitly
resource-probe-only in both arms because its sampled completion time exceeds the
45-second escalation margin. It supplies no primary throughput, latency or error
rate. The before/repeat timing differences are descriptive repeatability, not a new
optimization gain. This verdict does not accept Gate 7 or publication readiness.

### Source, tested and reviewed identity

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/performance-computational-optimization/data-dividends-zero-touch-clm`.
- Branch: `feat/performance-computational-throughput-optimization`.
- Parent/current HEAD: `5a84f112ecb82e4da2051e9cac867fdc8d7e2295`.
- BASE, merge base and observed origin/main: `198341b059ebf500252ce93d72eb099d2585c60b`.
- Six local checkpoints ahead, zero behind. This internal gate does not fetch or run
  the clean committed pre-PR publication gate.
- Frozen review manifest: `.runtime/performance-optimization/gate6-review-manifest.json`;
  raw SHA256 `b299f67174fd1717465762929fffbff017659d461661ab769c5fcc1f35097a32`.
- Deterministic three-path reviewed-content identity: exact manifest map, preserving
  slash spelling, sorted compact JSON in UTF-8 without EOF, SHA256
  `6de538fd04c2844ef7317bde5904bd4898206382e6b266f85275af0993bae3ed`.

| Frozen candidate path | Raw SHA256 |
| --- | --- |
| `scripts/performance_load.py` | `484a3856b212508c2e5320810506ccf0e7e9d8323e5f71322b3c6f47b3cc0058` |
| `.ai-pipeline/reports/PERFORMANCE_OPTIMIZATION_GATE_6.md` | `ac530291ff9811e6551ba02c433b4f8585593bb405b620a561ab34e0d29b31eb` |
| `.ai-pipeline/reports/PERFORMANCE_OPTIMIZATION_GATE_6.json` | `f16eb4b29a4444303e0ea10a9585d1d4df0c87b498ee712178af3fea6e29c8c4` |

Both measured run wrappers bind the current method hash, HEAD and BASE above. The
companion JSON's embedded before/after reports exactly equal their stable raw files.
Current tracked product working-tree and staged diffs are empty. Product tree IDs
independently verified against parent HEAD: backend app
`5bba6582542f0d186cd64562d9af8739801709df`, frontend src
`8a654eaca8eea927a73271f5533ad7a7d4a8dd69`. Product source was not edited during
this gate. The independent focused checks below test those exact current product
bytes; coordinator load/physical/broader receipts are separately classified.

Stable raw directory `.runtime/performance-optimization/gate6` contains 46 artifacts.
Its manifest raw SHA256 is
`e6fdd20bce3626b6b943b9289b4b029ff43b2aaedff4a43ef2b7b545112730cc`;
all listed hashes were independently verified. Pilots are preserved and excluded from
primary statistics. The unchanged Gate 1 helper used for initialization, resource
sampling and summaries has SHA256
`2bd95660eccc445a886991c58ba97d5211b401443c96e7366e57d2cb50c87222`.

Current-session runtime observation: Windows AMD64, Python 3.12.10, FastAPI 0.141.1,
Starlette 1.6.0, AnyIO 4.14.2, PyMongo 4.15.1, Pydantic 2.13.5, psutil 7.0.0,
pytest 8.4.2 and Ruff 0.16.2. Physical evidence uses the existing task-owned local
Mongo lane, not owner/manual Lane C. No current-source evidence is borrowed from a
remote session or historical product revision.

## 2. Gate Acceptance Checklist

| Requirement | Result | Direct evidence |
| --- | --- | --- |
| Local deterministic load only; separated memory/physical Mongo lanes | PASS | Explicit Mock/local/test settings, generated allowlisted databases and guarded sockets |
| Representative complete flow at concurrency 1/5/10 | PASS | Both arms: five primary cohorts per level per mode, successful five-call flow and explicit target confirmation |
| Attempt 20 only when safe/useful; stop unsuitable escalation | PASS | Stable preceding probes; memory 20 measured; Mongo 20 refused primary acceptance on elapsed margin |
| CPU/memory/latency/throughput/DB/errors/provider/target counts | PASS | Source-bound raw records; separate resource cohort; all 294 aggregate cells and throughput recomputed |
| Shared application rather than isolated per-case runtimes | PASS | One bundle/app/client/target across all cohorts at each mode/level; fresh runtime only between levels |
| Exact domain/currentness/ordered mutation/no replay invariants | PASS | Live collection assertions, every primary outcome/count and post-read verification; independent recovery/adverse tests |
| Post-load correctness and physical verification | PASS | After each arm: 44 focused and physical 127/19 suites with zero skips; independent 44 focused checks |
| Truthful saturation/confidence/claim limits | PASS | Closed-burst scope, five-cohort correlation, resource-only Mongo 20 and no causal gain claim disclosed |
| Independent review and final hygiene | PASS | This report-only review with exact manifest/source/test identities and final receipt |

## 3. Contract and Integration Findings

No current contract defect or unexplained business assumption was found. Each case
uses the regular create, target-classification, native document intake, intake-complete
and explicit target-confirmation API operations. The current confirmation helper
passes authoritative expected automation/CLM/event versions; completion is the POC's
submission-confirmed state, not autonomous final approval or production compliance.

Fixtures are prepared outside timing. Distinct valid-format synthetic UENs prevent
accidental target reuse within a shared runtime; company DTOs clone and validate the
accepted Merlion Mock company fixture. Current Mock officers/ownership/relationships
remain the canonical direct 60/40 graph. No confidential or quarantined sponsor
example is introduced. Source acquisition and GoldTier mapping/ledger owners retain
their existing authority.

The target observation binds `metadata.source_case_id` to the case's authoritative
source-case identifier; ownership binds case UUID. The rejected pilot incorrectly
joined those distinct identities and is disclosed; accepted source corrected the
measurement join before collection. Every accepted run binds the final method hash.
Rejected draft style/pilot data is not mixed into primary results.

API/type, durable schema, connector, configuration, business-rule, mapping,
auth/security, architecture, provider classification and product runtime behavior
are unchanged. Tooling and evidence were added. No index, query, CAS, worker-limit,
resource, retry or timeout setting was changed to manufacture a result. Singapore
registry and target stay Mock; native processing Local. Live ACRA/real GoldTier and
sponsor-dependent approval/readiness remain outside this gate.

## 4. Tester and Adversarial Findings

### Independent executions

All Python commands used the task `.venv/Scripts/python.exe` with `-B`. Focused pytest
ran from `apps/backend`; others from repository root. No load benchmark was repeated.

| Check/command | Actual independent result |
| --- | --- |
| `-m pytest tests/test_clm_orchestration.py tests/test_zero_touch_orchestration.py tests/test_zero_touch_exception_remediation.py tests/test_slice_d_mock_goldtier.py tests/test_performance_intake_concurrency.py -k 'recover or recovery or uncertain or concurrent or stale or malformed' -o addopts= -p no:cacheprovider -q --tb=short` | Exit 0; 44 passed, 197 deselected in 25.48s |
| `-m ruff check --no-cache --config apps/backend/pyproject.toml scripts/performance_load.py` | Exit 0; all checks passed |
| `-m unittest tests.test_performance_optimization` | Exit 0; four tests OK |
| `-m unittest tests.test_run_physical_mongo_tests` | Exit 0; 19 tests OK in 1.769s; no physical DB connection |
| `-m unittest discover -s tests/contract -p 'test_*.py'` | Exit 0; 44 tests OK in 1.323s |
| `scripts/check_project_state.py` and `scripts/check_architecture.py` | Each exit 0/PASS |
| Fake-socket and fake-cleanup-client guard probe | PASS; external/wrong-port/hostname alias rejected before socket; protected/malformed DB names rejected before cleanup; no real network or DB access |
| Three-file UTF-8/BOM/EOF/trailing-whitespace + raw/statistics/identity audit | PASS; 46 raw artifacts, 520 cases, 70 cohorts, 294 aggregate cells |

The initial sandbox execution of physical-runner units had five temporary-fixture
permission errors before those cases could run; fourteen other tests passed. The
unchanged command reran outside that sandbox and all 19 passed. This was a tempfile
infrastructure limitation, not a product assertion failure or test/source change.
No assertion, timeout, test inventory or safety rule was weakened.

The bounded guard probe substituted a fake original socket connect and fake cleanup
client. Only exact loopback task-port access reached that fake function; external,
wrong Mongo port and alias addresses were rejected first. Protected and malformed
names caused zero fake cleanup operations. No private configuration value was read,
no external packet sent and no database accessed by that probe.

### Inspected coordinator receipts

Both full load logs finish all required levels, with Mongo 20 resource-only. After
before-load collection: 44 recovery/currentness/race/adverse tests passed, 197
deselected, 25.59s pytest duration. After repeat collection: the same current-source
selection passed 44, 197 deselected, 25.16s. Receipt command walls are 28.64s/28.23s,
both exit 0. These are bounded selected suites rather than full backend executions.

Canonical physical verification ran after each arm: 19 suites, 127 collected and
passed, zero failed/errors/skips; receipts exit 0, 187.42s/188.41s. This is actual
driver/server evidence. It was not rerun independently for this new tooling-only
method. Additional current coordinator checks: focused traversal/read ownership/
strict persistence/legacy compatibility 176 passed in 39.30s; backend Ruff PASS;
strict mypy 126 source files PASS; contracts 44 OK; unchanged harness four OK. Six
state/architecture/tooling/policy/provider/secrets logs and their receipts are PASS.
Full backend/frontend/browser/OCR/Windows lifecycle and final cumulative measurement
are not new Gate 6 executions and remain mandatory Gate 7 work.

### Raw arithmetic, counters and finite sample limits

Fourteen measured mode/level/arm workloads each have exactly five primary cohorts.
Per arm: memory 5/25/50/100 case latencies at 1/5/10/20; physical Mongo 5/25/50 at
1/5/10. Total 260 cases per arm, 520 overall, 70 cohorts. Case identifiers are unique
within each arm and every source-case ID binds its synthetic UEN. Each case is
COMPLETED/SUBMISSION_CONFIRMED, finite/nonnegative, within the fixed completion
acceptance limit, and no longer than its encompassing cohort makespan.

Recomputed count, median, nearest-rank p95, min/max, mean and sample standard deviation
for latency/makespan/parent CPU agree with every aggregate. Cases/minute equals total
primary cases times 60000 divided by the sum of primary cohort makespans, rather than
averaging per-case reciprocals or including warmup/setup/read-verification time.

| Mode/concurrency | Cases per arm | Before/repeat cases/min | Before p50/p95 ms | Repeat p50/p95 ms | CPU allocation p50 before/repeat ms |
| --- | --- | --- | --- | --- | --- |
| memory 1 | 5 | 54.1858/54.7261 | 1113.9487/1115.6940 | 1095.5128/1123.8078 | 156.25/171.875 |
| memory 5 | 25 | 161.3206/158.4921 | 1794.7662/1892.0742 | 1848.0475/1943.9770 | 175/175 |
| memory 10 | 50 | 202.9121/201.6878 | 2864.9693/3036.6986 | 2813.3294/3091.6776 | 189.0625/193.75 |
| memory 20 | 100 | 202.1217/204.5398 | 5547.2459/6126.6378 | 5491.3765/5925.6069 | 228.125/235.9375 |
| Mongo 1 | 5 | 20.3943/20.3997 | 2987.1544/3012.3198 | 2970.3484/3008.8047 | 1546.875/1546.875 |
| Mongo 5 | 25 | 32.2038/32.0231 | 9076.7601/9370.1630 | 9139.0958/9483.6246 | 1640.625/1675 |
| Mongo 10 | 50 | 33.6226/33.5213 | 17277.8707/18014.8513 | 17310.0305/18060.1449 | 1723.4375/1731.25 |
| Mongo 20 | 0 primary | unmeasured | unmeasured | unmeasured | unmeasured |

Only five independent makespan/CPU observations exist per workload. Case latencies
inside a cohort share resources and are correlated; larger within-cohort case counts
do not create that many independent load replications. Level 1 p95 is the maximum of
five. The explicit bounded sample choice is adequate for this exploratory saturation
check and supplies no confidence/SLA, p99 or open-arrival capacity estimate.

For every primary physical case: 484 finds, one insert, 60 updates, total 545 driver
command attempts. Every saved physical cohort scales those actual counters exactly
by its concurrency; all memory cohorts have empty driver counts. This includes the
accepted three additional authorization reads from Gate 4. HTTP request counts derive
from the five directly issued successful flow requests, not an independent network
monitor. One post-window HTTP GET per case and direct document/ownership reads occur
after the timed DB snapshot and are excluded from those primary driver totals.

Per case: four observed registry operations, one observed native processing call,
one observed ownership load, and target Search three/Shell one/Policy one/Amend one.
Live collection assertions verify the exact source-bound sequence
Search/Search/Shell/Policy/Amend/Search and verify the same journal after post-read.
Saved summaries are assertion-backed counts; no separately persisted per-call target
trace is claimed. Post-window checks verify one native page/four fields, direct
Decimal 60/40 candidates, one path per candidate and zero indirect ownership. No target
operation is added by observation. Error/timeout fields are zero for all accepted
primary cohorts; the complete raw set and successful assertions support that claim.

## 5. Code and Architecture Review

The method creates one app, persistence bundle, authenticated TestClient portal and
Mock target per mode/level. ThreadPoolExecutor drives distinct cases against that
shared runtime across all warmup/resource/primary cohorts. Runtime is replaced
between levels; each cohort waits for all submitted cases before counter reset.
Existing framework worker limiter remains 40. This tests closed shared-ASGI bursts,
not isolated per-case application instances or real TCP request concurrency.

Registry/native/ownership/target observations use one short-held threading lock;
actual driver counters use a separate lock including increment/reset/snapshot.
Observer locks are released before calling owners, so they do not serialize complete
provider work or invert case/store locks. Target wrapper captures each original
bound method separately, uses metadata.source_case_id and preserves ordered calls.
The existing Mock target owns its mutable customer facts under its RLock; unique UENs
avoid cross-case target-match reuse. Shared authenticated client login is completed
before workers; measured requests do not mutate its authentication state.

Existing case-lock/reauthorization, strict envelope decode, CAS/revision, immutable
intent/currentness and target execution ledger remain product owners. Native PDF
processing retains per-call subprocess/tempdir isolation and existing bounds. No
within-case Shell/Policy/Amend parallelism or generic uncertain-write retry is added.
Post-load tests cover stale/currentness/uncertain recovery, call stopping and races;
no distributed exactly-once guarantee follows.

One warmup cohort and one sampled resource cohort precede five observer-free primary
cohorts. Native PDF fixtures/setup/login are excluded. Parent process CPU includes
all parent threads, client/check overhead and orchestration; dividing by cohort cases
is an allocation, excluding native children and Mongo server CPU. Quantized Windows
CPU observations are not precise hotspot attribution. Resource scopes include
post-window verification and retained warmup state; they are not the full primary-run
peak, Mongo-container RSS or directly comparable setup-inclusive Gate 1 observation.
Cases accumulate within each bounded runtime, so this is a finite retained-case burst
experiment rather than steady-state infinite traffic.

The memory plateau around 10/20 (~202-205 cases/min) and doubled approximate tail at
20 demonstrate diminishing utility under this method. Physical Mongo's ~32-34 cases/
min at 5/10 with increasing latency supports a plateau in that region. No exact
saturation threshold, new causal load-cost decomposition or production bottleneck
attribution is established from these five cohorts. The same product/method in both
arms precludes a new causal optimization-gain claim.

## 6. Security, Resources and Adverse Boundaries

Initialization discards inherited application settings before canonical ordinary-test
composition, disables dotenv access, supplies ephemeral test credentials and permits
only task Mongo loopback sockets plus internal socketpair creation. The method
supplies explicit test Mock/local modes, memory or fail-closed Mongo, disabled registry
cache and no silent fallback. It creates a new allowlisted disposable database,
registers only that name for command counting, closes the bundle and performs
allowlisted drop-and-verify cleanup. Neither clm_poc nor any real provider is a target.
No URI, credential, document body or raw provider response is logged/saved by the
measurement; persisted raw case IDs/UENs are generated synthetic identifiers.

Escalation to 20 requires the preceding resource probe to meet declared limits;
level 20 itself probes before any primary acceptance. Limits are sampled parent/live-
child RSS below 2GiB, available host memory above 4GiB, sampled mean host CPU below
80%, resource-cohort completion below 45 seconds against a fixed 60-second acceptance
deadline. Every accepted resource probe satisfies these conditions. Host availability
snapshots exceed 10GB, sampled host CPU stays low, memory 20 sampled RSS is about
1.19GB before and 1.18GB on repeat. This is sampled evidence, not a guarantee of every
instant's memory or primary-run high-water mark.

Mongo 20 resource cohorts are 49724.1581/50224.2272ms. RSS observations are
900583424/895635456 bytes; sampled mean host CPU 12.99395/13.81053 percent. Both fail
the elapsed margin while remaining below resource thresholds. This is conservative
elapsed-margin refusal, not observed OOM/workstation instability. Warm/resource
assertions complete, but per-case resource records are not saved. Both primary Mongo
20 files are exactly empty arrays; aggregate results contain only status/resources.
No Mongo 20 throughput/latency/error distribution is synthesized from this probe.

The 60-second wait detects completion failure; ThreadPoolExecutor context shutdown
waits for started work, so it is not hard process termination. Native/driver limits
remain separate existing bounds. All primary accepted cohorts finish within that
limit. No timeout was increased to make failing work pass. Only level-20 escalation
is gated by prior stability in source; in these actual runs every 1/5/10 resource
probe is also suitable, so no claim relies on continued unsafe lower-level escalation.
The script is not certified as a general unattended load supervisor.

No external-load, private .env, shared database or owner-config access occurred.
No current security defect or required fix was found in the bounded reviewed lane.
Final report/source hygiene and canonical secret checks follow this sole report write.

## 7. Required Fixes

None for this frozen Gate 6. Limits above remain explicit: five independent cohorts,
correlated cases, closed ASGI bursts, sampled resource scope, parent-only CPU,
non-terminating completion deadline and resource-only Mongo 20. They constrain claims
rather than authorize unsafe extrapolation. Broad cumulative regression remains the
separately assigned Gate 7 requirement.

## 8. Readiness

Exact independent PASS permits the coordinator's authorized local checkpoint and
continuation to Gate 7 under the existing user program. Gate 7 requires the complete
comparable benchmark/regression and a fresh independent final reviewer. This review
does not execute/accept that gate or establish owner publication readiness, Live ACRA,
real GoldTier, production capacity, final approval or SLA compliance.

## 9. Git Status and Reviewer Boundary

At start, tracked worktree and index were clean; only the three candidate paths above
were untracked. This reviewer wrote only
`.ai-pipeline/reports/PERFORMANCE_OPTIMIZATION_GATE_6_QUALITY_GATE.md`.
No source/test/configuration/ordinary report or Git mutation was made. No benchmark,
physical load rerun, commit, push, PR, merge or next gate occurred. Final receipt
confirms frozen three-file hashes, unchanged HEAD/main/index/product diff, report
UTF-8/single EOF/trailing-whitespace, actual git diff-check exit and secret scan.
