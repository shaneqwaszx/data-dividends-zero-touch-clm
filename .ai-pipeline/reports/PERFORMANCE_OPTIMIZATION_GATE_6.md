# Gate 6 - shared local full-case throughput and saturation

Frozen methodology/results pending independent review. Product source unchanged; this gate validates retained optimizations rather than adding concurrency or persistence policy.

Base/origin main `198341b059ebf500252ce93d72eb099d2585c60b`; parent `5a84f112ecb82e4da2051e9cac867fdc8d7e2295`; branch `feat/performance-computational-throughput-optimization`.
Method `scripts/performance_load.py` SHA256 `484a3856b212508c2e5320810506ccf0e7e9d8323e5f71322b3c6f47b3cc0058` identical in both runs. Raw samples/method/check receipts preserved under ignored `.runtime/performance-optimization/gate6/manifest.json`.

## Protocol and lane separation

One shared application/bundle/client/Mock target across all cohorts at a mode/level; fresh runtime between levels. Memory Lane A and physical generated allowlisted local Mongo Lane B remain separate. Explicit test Mock/local settings, disabled registry cache and network guard; no .env/shared clm_poc/external provider load. Generated distinct valid-format synthetic UENs avoid accidental target reuse. Company DTOs clone/validate accepted Merlion Mock data; current Mock ownership is exact60/40. Native1-page/four-field fixture prepared outside timing.

Five closed primary cohorts each at1/5/10 and memory20, one excluded warmup and one separate sampled resource cohort per level. Five independent makespan/CPU observations per workload; case samples5/25/50/100 share cohorts and are correlated. Five cohorts bound interactive-workstation load; original/final serial control still uses20. Level1 p95 is the maximum of5, descriptive exploratory tail with no confidence/SLA or p99 claim. This is in-process ASGI full-case load, not network/production capacity or open-arrival traffic.

Case latency spans five regular API calls: create, explicit classification, native intake, intake complete, explicit Mock target confirmation. Parent CPU/cohort divided bycases is an allocation including caller/check overhead, excluding native child/Mongo CPU. No sampler/profiler in primary windows. Resource observation is separate, includes post-window verification and retained warmup state; not directly comparable with original setup-inclusive resource scopes. Actual default framework limiter40 unchanged. HTTP counts derive from the five successful issued flow calls, plus one post-window GET percase.

Counters for actual driver commands/native/ownership/registry/target metadata are synchronized; no unsynchronized canonical performance-wrapper counters are used. Case journal binds authoritative source_case_id, not case UUID. Assertions require ordered target6calls, one owned native/ownership call, registry4, native fields/page, exact Decimal60+40 and no target call on post-read. All520 primary cases completed with exact counts/outcomes and zero errors/timeouts.

|Mode/concurrency|Cases per run|Before/after cases/min|Before p50/p95 ms|Repeat p50/p95 ms|Before/repeat parent CPU allocation p50 ms|
|---|---:|---:|---:|---:|---:|
|memory_1|5|54.19/54.73|1113.95/1115.69|1095.51/1123.81|156.25/171.88|
|memory_5|25|161.32/158.49|1794.77/1892.07|1848.05/1943.98|175.00/175.00|
|memory_10|50|202.91/201.69|2864.97/3036.70|2813.33/3091.68|189.06/193.75|
|memory_20|100|202.12/204.54|5547.25/6126.64|5491.38/5925.61|228.12/235.94|
|mongo_1|5|20.39/20.40|2987.15/3012.32|2970.35/3008.80|1546.88/1546.88|
|mongo_5|25|32.20/32.02|9076.76/9370.16|9139.10/9483.62|1640.62/1675.00|
|mongo_10|50|33.62/33.52|17277.87/18014.85|17310.03/18060.14|1723.44/1731.25|
|mongo_20|0 primary|resource probe only|unmeasured|unmeasured|unmeasured|

Memory throughput plateaus around10: ~202-205cases/min at10/20;20 doubles p95 without material throughput gain. Physical Mongo plateaus around5-10: ~32-34cases/min with increased latency. Existing strict full-envelope decode/CAS/checkpoint work, parent Python execution and shared store transaction ownership remain material limits; prior profiles support these owners, but no new causal decomposition of load cost is claimed. Mongo and memory figures are not interchangeable.

Each physical complete case retains484find/1insert/60updates (545commands), including three new authorization reads from Gate4. Counts scale exactly with level; no index/query/call-stopping change. Target3Search/Shell1/Policy1/Amend1, exact Search/Search/Shell/Policy/Amend/Search per source-case; no mutation parallelized within a case and no replay after post-read. Provider/target equality is proven in raw primary data and source acceptance assertions.

## Escalation and resource limits

Escalation to20 requires the preceding probe meet declared limits; level20 also probes before primary acceptance. Thresholds: sampled parent/live-child RSS below2GiB, host available above4GiB, mean host CPU below80%, sampled cohort below45s against fixed60s completion deadline. All accepted measured resource probes at1/5/10 and memory20 satisfy them. Memory20 sampled RSS ~1.2GB. Host available remained above10GB and sampled host CPU remained low; no workstation exhaustion or deliberate crash.

Mongo20 executed warm/resource cohorts only. Resource elapsed49,724.16/50,224.23ms exceeds45s margin in both arms; sampled RSS900,583,424/895,635,456 bytes and mean host CPU12.99/13.81% are safe. This is a conservative elapsed-margin refusal, not observed OOM/host instability. Resource timings include sampler overhead and supply no20throughput, p50/p95 or primary error-rate claim. Per-case resource-probe details were not saved; assertions completed but only summary observations persist. Primary20 sample files are empty by design. Do not infer capacity from the observed resource cohort.

The60s wait is an acceptance completion deadline, not a guaranteed hard termination: ThreadPoolExecutor exit waits started workers, while existing native/driver bounds still apply. No timeout was increased to make load green, no worker-limit configuration or global queued-body cap added. Actual higher-workstation/external/open-loop limits remain unknown.

## Post-load correctness and affected verification

After first load:44 recovery/currentness/race/adverse tests PASS; canonical physical19suites127PASS/0skip. After repeated load:44same focused tests PASS and canonical physical19suites127PASS/0skip again. Focused strict traversal/readownership/legacy/persistence176PASS; backend RuffPASS; new method RuffPASS; strict mypy126PASS; contracts44PASS; unchanged harness4PASS; six state/architecture/tooling/policy/provider/secrets checksPASS. Product bytes equal accepted Gate4/Gate5; full backend is not rerun for this tooling-only gate, and cumulative full regression remains Gate7.

Initial draft style and pilot source-id join were rejected before accepted collection. Current request metadata source_case_id is CASE-<syntheticUEN>-<suffix>; corrected join uses that authoritative field, while ownership binds case UUID. Exact assertions and fixed deadline remain. No product fix, rule, validator, dependency, mapping or provider-status change.

## Change flags and next action

API/type/schema/connector/configuration/business-rule/mapping/auth/security/architecture/provider classifications/product runtime unchanged. Added bounded load measurement/evidence only. Higher local concurrency does not prove distributed exactly-once, Live/provider interoperability, approval, production capacity or SLA. Next: independent exact PASS, authorized local checkpoint, then complete comparable benchmark/regression and a fresh independent final reviewer.
