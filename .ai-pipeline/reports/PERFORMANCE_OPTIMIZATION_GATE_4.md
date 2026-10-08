# Gate 4 - bounded worker scheduling for native intake

Frozen candidate pending exact independent concurrency/security review. Local deterministic Lane A and separate physical Mongo Lane B; no real provider access.

## Identity and measured cause

Base/origin main `198341b059ebf500252ce93d72eb099d2585c60b`; parent checkpoint `d0a4855d2564d6bcb0f42a895b45b0a9cdf6e1d5`.
Branch `feat/performance-computational-throughput-optimization`. Exact four product/test/method hashes are in companion JSON; unchanged Gate1 method `2bd95660eccc445a886991c58ba97d5211b401443c96e7366e57d2cb50c87222`.
Raw samples, profiles, dependency map and check receipts: ignored `.runtime/performance-optimization/gate4/manifest.json`.

The async intake handler executed a blocking native extraction child on the shared event loop. Five independent case intakes consequently ran sequentially and blocked health responses. The existing synchronous orchestration method now runs through FastAPI/Starlette/AnyIO's existing worker limiter (40 active workers). Existing per-case RLock still owns the full intake; fresh authentication, profile/team and case scope run first inside that lock. Shell/Policy/Amend ordering, write candidates, CAS and all target sequencing remain unchanged.

The body stays bounded before worker admission. No new pool, framework, owner or configuration. The limiter caps active workers, not globally queued upload bodies. Test load is bounded at five here; no global queued-memory or production capacity claim.

## Identical shared-ASGI before/after

20 measured cohorts per level, two warmups and one separate resource cohort. Native PDF/4 fields/AUTO_CONFIRMED; cases remain PENDING_INPUTS/NOT_SUBMITTED. Setup/login/seed excluded. Parent CPU includes health/client/assertion overhead and excludes native child CPU. Resource samples exclude initial case seeding. Primary windows contain no resource sampler/profiler. This is intake-only in-process ASGI, not full-case/network throughput.

|Concurrency|Before cohort p50 ms|After cohort p50 ms|Before intake/min|After intake/min|Before health p95 ms|After health p95 ms|
|---|---:|---:|---:|---:|---:|---:|
|1|960.874|955.739|62.48|62.89|494.068|3.182|
|5|4790.615|1159.451|62.66|254.48|4393.632|5.946|

All 120 primary intakes passed in each arm; zero errors/timeouts, registry operations or target mutations during intake. Five-cohort peak parent/live-child RSS increased 206,176,256 -> 430,751,744 bytes; peak actual provider concurrency increased 1 -> 5. Serial RSS stayed about185MB. Exact elapsed/CPU/resource distributions and request counts are in JSON. No statistical significance, p99, external latency, SLA or production gain claim.

## Complete unchanged serial control

All ten workloads:20 measured +2 warmups; original Gate1 method. Provider, target and HTTP counts match Gate3. Fresh in-lock authorization deliberately adds repository reads and physical finds for full onboarding; exact deltas below. Those are the measured cost of closing the queue authorization window, not eliminated operations.

|Workload|Gate3 p50 ms|Gate4 p50 ms|Gate3 p95 ms|Gate4 p95 ms|
|---|---:|---:|---:|---:|
|memory_onboarding|1140.760|1126.664|1175.189|1182.421|
|mongo_onboarding|2870.821|2866.961|3075.768|2980.796|
|blocker_correction_resume|97.804|91.624|195.848|197.040|
|mock_target_success|64.986|64.058|164.137|67.068|
|uncertain_policy_recovery|49.914|49.169|52.539|53.524|
|case_detail|12.869|12.951|15.213|13.674|
|portfolio_memory|38.663|39.133|39.990|46.925|
|portfolio_mongo|17.936|17.602|20.753|19.424|
|ownership_graph|0.333|0.422|0.468|0.686|
|native_document|471.334|480.213|482.245|498.410|

`memory_onboarding` repository delta: `{"onboarding.get": 1, "profiles.get": 1, "teams.get": 1}`; DB `[{}]` -> `[{}]`.

`mongo_onboarding` repository delta: `{"onboarding.get": 1, "profiles.get": 1, "teams.get": 1}`; DB `[{"find": 481, "insert": 1, "update": 60}]` -> `[{"find": 484, "insert": 1, "update": 60}]`.

The unchanged graph median rose0.333->0.422ms and p950.468->0.686ms versus Gate3; it remains below the original median0.435ms. The unchanged blocker p95 stayed high195.848->197.040ms and memory portfolio p95 rose39.990->46.925ms. These tails are retained, with no blanket improvement or future latency guarantee. Gate4 edits do not execute on these workload paths.

Whole-run differences are descriptive across time windows; unchanged memory/projection/native/graph paths are host controls. Retention rests on large source-explained five-case scheduling and health improvements, unchanged serial latency, exact deterministic results and adverse checks.

## Correctness and dependency ownership

New seven tests: worker owns existing case RLock with fresh auth; health progresses during blocked native work; same-case intake serializes; revoked session401 and cross-team404 reject before writes; started AnyIO cancellation completes exactly one owned document; queued cancellation before worker entry creates none; worker missing-case exception preserves safe404.

The queued-cancellation observation is at the earlier synchronous FastAPI dependency, using the actual shared limiter. Started cancellation proves the AnyIO portal scope with abandon_on_cancel=False; it does not prove every transport/process-shutdown scenario. Case lock -> existing nested document RLock -> repository/CAS ownership is unchanged. Native PDF extraction uses a child/temp directory per call. No shared parent PDFium state or target parallelization.

Initial test-helper attempts failed before provider entry due to cookie-adapter/queue-observer mistakes. Corrected tests use the canonical RawAsyncClient/cookie jar and actual earlier dependency queue; no product fix, assertion weakening or deadline increase. Final focused7PASS. Full backend2601PASS/133 opt-in skips/3 existing timestamp warnings; focused176PASS; RuffPASS; strict mypy126PASS; contracts44PASS; harness4PASS; six governance/security checksPASS. Canonical physical Mongo19suites127PASS, zero skips/failures/errors. Full backend covers the current POC catalogue, strict schema1..9/current10, Decimal, call stopping/currentness/ledger/no replay and recovery. Catalogue unchanged. Six realOCR opt-ins remain pending final cumulative verification.

Independent source/security review found no lock inversion and verified installed FastAPI0.141.1/Starlette1.6.0/AnyIO4.14.2 pool/shield semantics. Acceptance requires the separate exact independent Gate4 report. Frontend query/cache or public response shape is unchanged; full browser/frontend verification remains Gates5/7.

## Change flags

External API/type unchanged; internal intake signature adds an optional fresh-reauthorization callback. Schema/connector/configuration/business rule/mapping unchanged. Auth/security changes: fresh check inside the existing lock after queueing. Runtime changes: native intake runs in the existing bounded worker pool. Architecture owners/dependencies/provider classifications unchanged. No .env/shared clm_poc/external calls. Next: independent PASS, authorized local checkpoint, then actual desktop/narrow browser measurements.
