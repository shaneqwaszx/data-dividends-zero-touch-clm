# PR81 cache performance forensic investigation

Status: STOPPED / NOT READY FOR HUMAN MERGE after a new mandatory backend failure. No independent acceptance or publication occurred. Owner b51148d6-23b6-40c2-bfc1-8f7a326c4233 authorizes this bounded continuation. Preserve the existing uncommitted25-path candidate ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490, publishedHEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599 and every prior FAIL record.

## Causal result and correction decision

Classification D: mixed or unresolved diagnosis. Current-versus-published sequential diagnostics do not establish a product/UI regression: current was faster in this controlled pair, both completed identical workloads and all assertions passed. Timing variability exists on unchanged source. Its external/resource cause is NOT proven. Starting the exact task Mongo container did not reproduce failure; it is not established as the cause. No runaway query, query error, extra request or target mutation was observed. No root-cause closure or harmless-transient claim is made.

The earlier timeout's deepest observed mechanism remains cumulative navigation work plus the fixed22.5 seconds of waits exhausting the original60-second startup+test guard. The original failure's earliest excessive operation cannot be identified from its bounded legacy capture; do not invent it. Fresh diagnostics capture every iteration, phase, request timing, query numeric activity and CDP task/layout/script/heap metric, but their passing runs cannot retroactively explain the failing host state. GC was NOT directly measured. A single paired comparison is not proof of equivalence under every load.

Change necessity decision: no new source change justified by current causal evidence. No test restructuring, runtime/performance repair, cache-policy change or measurement-method change was made. A lifecycle split would require proving browser/session/compile/GC/warmup conditioning comparability; merely resetting the browser or changing interleaving to evade the guard is not accepted. The original case/table/query owners and complete protocol remain unchanged. Failed correction count0; diagnostics and acceptance runs are separately labeled. Fresh independent QG must assess this explicit unresolved diagnosis and exact current mandatory evidence; neither the implementer nor an earlier gate grants acceptance.

## Observed timing comparison

| Revision / setting | Playwright seconds | Total runner/subprocess seconds | Result |
|---|---:|---:|---|
| Main e799 verified GitHub run37954652603/job113901971040 |48.1|51.788|Historical PASS; original main inventory73, not candidate acceptance|
| Published PR dd8c GitHub canonical log |46.1|49.167|Historical PASS, log114234488421|
| Previous candidate full shard1 |Not completed|66.484 failing lifecycle|Original60-second guard FAIL|
| Previous candidate partial timing probe |Not completed|66.610|FAIL; index20 warm render at56.085s from test-body start|
| Fresh paired candidate diagnostic |48.4|56.844|PASS,44 diagnostic navigations|
| Fresh paired published diagnostic |52.4|63.360|PASS,44 diagnostic navigations|
| Exact unchanged width360 |49.7|58.547|PASS,40 measured +4 warmup navigations|
| Exact unchanged width1440 |49.1|57.625|PASS,40 measured +4 warmup navigations|
| Exact unchanged width360 with owned Mongo running |47.9|56.344|PASS,40 measured +4 warmup navigations|

Total time includes owned Windows cleanup outside the original startup/test guard and parent subprocess overhead. The published diagnostic total63.360 does NOT extend or bypass the60-second guard: the unchanged canonical run(timeout_seconds=60) completed Playwright before its deadline, then performed its original separately bounded owned cleanup. Original Playwright120-second test/15-second expect settings and retries0 remain unchanged.

The main timing is now directly OBSERVED in the sanitized primary job log, tmp/pr81-perf-main-ci-baseline.log, with run/head/attempt/window and raw log SHA256 in its matching JSON. Historical main ran73 lifecycle selectors; its PASS is never attributed to the candidate91/112 inventory or nine-job release requirement.

Complete raw Git blob identity for performance-browser.e2e.ts is43adafb43c8c4b122e41031cc87f912e0e0f3a26 at both publishedHEAD and main. Current working CRLF bytes and scratch LF bytes are line-normalized equivalent; diagnostics restore exact prior scratch bytes and never alter root bytes. Exact acceptance copies root raw bytes; original40-sample artifacts bind their method_sha256 to those exact raw bytes. Instrumented artifacts have a distinct diagnostic hash and do not substitute for acceptance.

## Phase and resource observations

The unchanged protocol has22 iterations per viewport, each cold then warm,2 warmups and20 measured per type,50-case table assertions,query-cache reset on cold page reload,realistic Cases->same-case warm navigation,HTTP cache disabled by routing,mandatory500ms accounting tail on all44 navigations plus initial500ms settling,all network/layout/data-quality assertions andzero target confirmations.

Paired candidate: onboarding including initial settling2.858s; all44 measured UI phases21.375s; accounting phases22.300s (tails plus original accounting work); cold mean700.394ms,warm mean271.208ms across22 each. Published: onboarding3.034s,UI phases24.900s,accounting22.377s,cold823.130ms,warm308.670ms. These means include warmups and are diagnostic summaries, not replacement benchmark definitions.

Cold reloads were14 API attempts each; warm navigations0 each in both arms. Query activity settled with7 cached successful queries,0 fetches and0 errors at sample accounting. Same identity-scoped key/query/auth owners,AbortSignal,cancellation and clearing behavior remain. Cases table and case-detail phase durations are separately captured in every diagnostic row. Candidate backend GET mean44.725ms,max203ms; published mean64.759ms,max266ms,including dashboard/portfolio work. There is distributed timing variation; no single failing backend operation or currentness defect is established.

CDP task/script/layout/style durations and document/node/heap counts are recorded without page bodies or query keys. Candidate maximum JS heap85.247MiB,published92.292MiB. Candidate per-page long-task count0,published maximum1. These snapshots do not prove a leak, GC cause or host CPU contention. Startup/readiness candidate backend2.516s/frontend0.531s; published3.828s/1.234s. No unrelated process enumeration or resource mutation occurred.

## Evidence integrity and release boundary

Fresh diagnostic child capture sanitizes every emitted line with the original sanitizer and ephemeral sensitive values before writing. Original bounded in-memory capture,process ownership,deadlines,cleanup and assertions remain. Separate complete sanitized child-playwright/backend/frontend logs under tmp/pr81-perf-{arm}-child-*.log retain all iterations and route timings; wrapper logs/receipts bind their SHA256. Only scratch diagnostics were temporary; all33 overlaid scratch paths were restored exactly. Root candidate25 paths and868 historical records plus prior candidate/stop records remain exact. No .env,protected database,real provider write,Git staging/commit/push/PR mutation or merge.

Exact acceptance artifacts under tmp/pr81-perf-validate{360,1440,360mongo}-measurement.json contain40 measured samples each and original2 warmups per kind. Receipt field samples_accounted=0 means no added diagnostic sample rows in those unchanged tests; it does not mean missing benchmark samples. The successful original final40-sample assertion and bound artifacts prove all44 navigations completed.

Broader mandatory suites run sequentially using the existing guarded task harness,then complete browser shard1/shard2 and actual91/112 discovery/eight offline sponsor journeys/ledger/no replay. Any new mandatory failure stops this continuation. No current mandatory failure is waived by the old SDQ01 acceptance; SDQ01 historical cause remains unresolved and SDQ02 remains independently closed. Fresh exact independentPASS,latestmain review,exact-path scoped commit,clean committed pre-PR/checklistPASS,normal existingPR81 push,both nine-job CI PASS andlegitimate disposition of both P2 threads remain required. Current publication readiness isNOT READY.


## New mandatory failure and terminal checkpoint

Fresh full backend: 1 failed,2650 passed,145 physical-only deferrals,4 warnings in993.91s; wrapper996.047s. Test test_http_seeder_runs_twice_against_one_live_memory_backend failed during its first seed_demo call. ConfirmingHttpSeedApi.complete_case posted current versions to /api/clm/zero-touch/cases/{case}/target-confirmation. HttpSeedApi._request entered the returned response context, then response.read(1_048_577) reached socket.recv_into and raised TimeoutError under the existing15-second timeout. The second seeding/idempotence verification was not reached. Exact case/iteration,response status/body framing,eventual server/target state and cause are not captured. No transient-host,harmless-completion or current-source regression claim is established.

The owner's instruction applies: "If a new mandatory failure occurs, STOP and provide precise causal evidence rather than starting another unbounded rerun cycle." No rerun or repair was attempted and no timing limit was changed. The remaining queued physicalMongo/frontend/Windows/governance/static lanes and complete browser shards/eight journeys/fresh QG/pre-PR/publication were not dispatched. The earlier2651-pass result cannot overrule the new mandatoryFAIL. This test is real loopback HTTP with memory persistence and Mock providers, not Live external interoperability.

The fixture finally requests server exit,joins for10 seconds and closes its listener; the owning pytest process exited1. Prior897 records/candidate paths plus34 logs remain exact. The retained source25 identity remains unchanged. See PR81_PERFORMANCE_RELEASE_STOP_REPORT.md and STOP_EVIDENCE.json. Only the exact task Mongo container is stopped after identity verification; no database is removed or modified by cleanup.
