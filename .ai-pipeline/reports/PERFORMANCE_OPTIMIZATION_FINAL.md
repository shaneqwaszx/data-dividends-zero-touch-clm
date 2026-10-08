# Final cumulative performance evidence

The final comparable run observed physical Mongo onboarding median **3595.463 -> 2869.739 ms (-20.18%)** and p95 **3958.299 -> 2973.436 ms (-24.88%)**. These are separate time-window observations. Exact-source alternating pairs independently establish the retained codec/read improvements; unchanged controls also improved, so the entire end-to-end change is not attributed to the optimizations.

The fresh independent verdict belongs solely to `PERFORMANCE_OPTIMIZATION_QUALITY_GATE.md` on the frozen final manifest. This coordinator report records implementation and verification evidence, not independent acceptance. All seven gates belong to one authorized local session. No push, PR, merge or cleanup.

## Tested and reviewed identity

- BASE, latest fetched origin/main and merge-base: `198341b059ebf500252ce93d72eb099d2585c60b`.
- Source HEAD measured and tested: `412e50250dfdd9064579c99ee8e3ab987df1ff2a`; branch `feat/performance-computational-throughput-optimization`, seven accepted local checkpoints ahead and zero behind before the final evidence commit.
- Reviewed working content also includes `.github/workflows/ci.yml` and `tests/test_run_e2e.py` inventory corrections, plus the Garden browser synchronization fix and opt-in safe milestones in `apps/frontend/e2e/s3-sandbox-submission.e2e.ts`, after measurement. Their exact hashes and fresh affected checks are bound separately; product/method bytes stayed unchanged.
- Worktree: `C:/Users/shane/.codex-clean2/worktrees/performance-computational-optimization/data-dividends-zero-touch-clm`.
- Backend app tree: `5bba6582542f0d186cd64562d9af8739801709df`. Frontend src tree: `8a654eaca8eea927a73271f5533ad7a7d4a8dd69`.
- Unchanged Gate 1 harness raw SHA256: `2bd95660eccc445a886991c58ba97d5211b401443c96e7366e57d2cb50c87222`.
- Prior 38-file cumulative content manifest raw SHA256: `9a8d2fb9db515569c555e981cb82e2a65ac6f4baeb5b248c7c20d867521723cd`. The final review manifest adds these two reports; the sole QG and post-checkpoint receipt bind the reviewed and committed content. The final evidence commit includes these reports plus the three late CI/test corrections below; product bytes stay unchanged; its resulting HEAD is returned in the owner handoff without rewriting accepted evidence.
- Stable ignored Gate 7 artifact manifest raw SHA256: `9f2dd4a690cf1da39cf50368ade048eb6c9e6965316241e69106e66c105d5f4a`. It preserves all 200 primary samples, ten profiles, the original serial aggregate and complete check receipts/logs. Gates 1-6 retain their manifests and rejected evidence separately.

Companion JSON includes bounded metric distributions, absolute/percentage deltas, exact operation signatures, source hashes, prior paired/browser/load evidence and complete command receipts. Raw case/document/provider bodies and private configuration are excluded.

## Environment and method

Windows 11 build 26200 / AMD64, 32 logical CPUs, 31.75 GiB RAM; Python 3.12.10, Node 22.23.3 / npm 10.9.9. Installed FastAPI 0.141.1, Starlette 1.6.0, AnyIO 4.14.2, Pydantic 2.13.5, PyMongo 4.15.1, Yappi 1.7.6, psutil 7.0.0, pytest 8.4.2, Ruff 0.16.2 and mypy 1.20.2. Correct worktree imports and task-local native dependencies were used. Tesseract was added only to controlled OCR/browser child PATHs; no OCR performance claim.

Lane A uses Mock/local providers. Lane B uses generated allowlisted databases on the task Mongo 7 container at loopback port 27861, capped at two CPUs / 1 GiB and without a host volume. A separate owned Mongo 7 container at port 27185 with the same limits was created after final timing for browser classification fixtures. Lane C remains the owner's manual normal-configuration functional smoke; it contributes no performance or capacity number. Regression also includes explicitly sandbox-shaped offline fake protocols; these are not real Sandbox requests. No `.env`, original/shared `clm_poc` or real-provider automated access.

Every serial workload has 20 primary repetitions and two excluded warmups. Setup/login/teardown, sampling and Yappi profiling are excluded from primary elapsed/parent-CPU windows. Mutable cases use fresh runtimes; read controls reuse setup exactly as Gate 1. p95 uses nearest rank (19th of 20); no p99, confidence interval or statistical significance claim. CPU excludes native children and Mongo server and can quantize to zero for short Windows samples. RSS is one separate sampled parent/live-child observation including setup and accumulated runtime state, not a repeated primary peak or memory-saving proof.

## Complete comparable serial result

Times are milliseconds; delta is final minus baseline. Every row has n=20 per arm and deterministic correctness PASS. The intentional three authorization reads are the sole operation-signature change, described below.

| Workload | Baseline p50 | Final p50 | Delta ms | Delta % | Baseline p95 | Final p95 | Delta ms | Delta % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| memory_onboarding | 1216.9796 | 1118.2995 | -98.6800 | -8.11% | 1293.2226 | 1186.5989 | -106.6237 | -8.24% |
| mongo_onboarding | 3595.4627 | 2869.7391 | -725.7236 | -20.18% | 3958.2987 | 2973.4358 | -984.8629 | -24.88% |
| blocker_correction_resume | 112.9822 | 92.1700 | -20.8122 | -18.42% | 211.6555 | 96.7625 | -114.8930 | -54.28% |
| mock_target_success | 78.2413 | 64.3715 | -13.8698 | -17.73% | 204.1857 | 161.5462 | -42.6395 | -20.88% |
| uncertain_policy_recovery | 58.5896 | 50.1436 | -8.4460 | -14.42% | 81.4603 | 56.4041 | -25.0562 | -30.76% |
| case_detail | 17.8627 | 12.9416 | -4.9210 | -27.55% | 19.8540 | 15.6738 | -4.1802 | -21.05% |
| portfolio_memory | 47.5512 | 40.4881 | -7.0632 | -14.85% | 55.6241 | 44.2473 | -11.3768 | -20.45% |
| portfolio_mongo | 18.7118 | 17.7309 | -0.9808 | -5.24% | 21.3656 | 19.0583 | -2.3073 | -10.80% |
| ownership_graph | 0.4345 | 0.3823 | -0.0522 | -12.00% | 0.7847 | 0.4224 | -0.3623 | -46.17% |
| native_document | 508.8135 | 480.7079 | -28.1056 | -5.52% | 537.1365 | 502.6767 | -34.4598 | -6.42% |

Memory case detail and both 100-case portfolio queries are API controls. Native extraction has one page and four fields; the exact Decimal graph has four parties, four edges, three paths and an unchanged digest. These unchanged paths also improved across windows. Mock target-success p95 rose from 67.068 ms at Gate 4 to 161.5462 ms at final, while staying below the baseline 204.186 ms. Earlier blocker, portfolio and graph tails also varied; their original samples remain preserved. No blanket latency guarantee.

| Workload | Parent CPU p50 baseline/final ms | Delta ms | Delta % | Separate sampled RSS baseline/final bytes | RSS delta bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| memory_onboarding | 218.7500 / 179.6875 | -39.0625 | -17.86% | 214089728 / 214474752 | +385024 |
| mongo_onboarding | 1992.1875 / 1468.7500 | -523.4375 | -26.27% | 238067712 / 239063040 | +995328 |
| blocker_correction_resume | 109.3750 / 93.7500 | -15.6250 | -14.29% | 256720896 / 256786432 | +65536 |
| mock_target_success | 78.1250 / 62.5000 | -15.6250 | -20.00% | 254664704 / 252993536 | -1671168 |
| uncertain_policy_recovery | 62.5000 / 46.8750 | -15.6250 | -25.00% | 221134848 / 220860416 | -274432 |
| case_detail | 15.6250 / 15.6250 | +0.0000 | +0.00% | 263593984 / 264183808 | +589824 |
| portfolio_memory | 46.8750 / 39.0625 | -7.8125 | -16.67% | 229445632 / 229408768 | -36864 |
| portfolio_mongo | 0.0000 / 0.0000 | +0.0000 | unavailable: baseline zero | 246390784 / 246505472 | +114688 |
| ownership_graph | 0.0000 / 0.0000 | +0.0000 | unavailable: baseline zero | 230268928 / 230555648 | +286720 |
| native_document | 0.0000 / 0.0000 | +0.0000 | unavailable: baseline zero | 287485952 / 287043584 | -442368 |

JSON retains p95, mean, min/max, standard deviations and response-byte distributions. Zero CPU is measurement quantization. Neither RSS differences nor unrelated control timing changes establish a causal saving.

## Measured hotspots and retained changes

Baseline diagnostic profiles identified recursive copying and strict full-envelope traversal in Mongo. `_reject_unknown_model_fields` had 642,078 calls, 2343.75 ms self / 3750 ms cumulative CPU; `_persistence_value` had 194,774 calls, 1125 / 2062.5 ms. Recursive deepcopy had 1,089,551 visits. Yappi overhead means those times are not wall-time fractions and cannot be compared with observer-free 1992.188 ms parent CPU. Native child latency was about 509 ms; child CPU attribution is unavailable.

| Retained optimization | Exact causal evidence | Safety and files |
| --- | --- | --- |
| Skip proven scalar no-op traversal; reuse model field key views | 20 alternating exact-source pairs, 1000 calls/batch: median 0.4296468 -> 0.36186285 ms (-15.78%); p95 0.4628455 -> 0.4037409 (-12.77%); CPU 0.421875 -> 0.359375 (-14.81%). All 20 pairs improved. Full traversal calls 642,078 -> 108,878 (-83.04%). | `mongo_case_store.py`; strict unknown-field/container shape rejection and existing Pydantic scalar validation retained. No schema/cache/owner change. |
| Remove 11 redundant read-section deep copies after fresh strict decode | 20 alternating physical pairs, 200 reads/batch: case median 3.50411225 -> 3.10381075 ms (-11.42%); CPU 2.65625 -> 2.3046875 (-13.24%). Documents median 3.32785025 -> 2.9958545 (-9.9763%, below 10%). All 20 pairs improved for both reads. Copy visits 950 -> 12/case and 639 -> 12/documents. Full Mongo copy visits 1,089,551 -> 836,272 (-23.25%). | `repositories.py`, store ownership docstring; no model cache, write/candidate/CAS/query/index change. Unmeasured verified-search copy retained. Fourteen ownership and two new physical tests cover caller mutation, restart, deletion and conflicts. |
| Schedule blocking native intake on the existing framework worker pool | 20 shared-ASGI cohorts per level/arm: five-case median makespan 4790.6146 -> 1159.45105 ms (-75.80%); 62.66 -> 254.48 intakes/min (4.06x); health p95 4393.6318 -> 5.9458 ms. One-case median 960.8742 -> 955.73855 ms. All 120 primary intakes per arm correct; zero errors/timeouts or target/registry calls during intake. | `main.py`, `zero_touch_orchestration.py`; existing 40 active workers, existing case RLock, first-in-lock fresh authorization, per-call subprocess/temp directory. No target parallelism/new owner. Five-case sampled RSS 206,176,256 -> 430,751,744 bytes; native peak concurrency 1 -> 5. |

Seven concurrency tests prove worker lock/fresh authorization, health progress, same-case serialization, revoked-session 401/cross-team 404, started cancellation completion, queued cancellation before worker entry and missing-case safe 404. Started cancellation proves the actual AnyIO portal shielding behavior; queued observation is at the earlier synchronous dependency. It does not prove every transport/process-shutdown scenario. The limiter bounds active workers; globally queued upload-body memory is not capped. Intake-only scheduling gains remain separate from full-case throughput.

## Persistence, operation counts and no replay

Full physical onboarding: **find 481 -> 484; insert 1 -> 1; update 60 -> 60**. The three extra reads are onboarding/profile/team reauthorization inside the lock after worker queueing. Memory driver counts remain empty. Portfolio remains three finds and one bounded aggregate. CAS cycles/checkpoint writes, current schema 10 and strict legacy 1-9, create/update distinctions and no resurrection remain unchanged.

Existing query plans were suitable: IDHACK and document/submission indexes each examine one key/document; the authorized team index examines 101 fixture documents, with 51 bounded rows feeding the 50-row page. The corruption-rejecting facet remains. No measured index/query issue justified a change.

Full flow per case retains four registry operations, five HTTP calls, target Search three / Shell one / Policy one / Amend one, with exact sequence **Search, Search, Shell, Policy, Amend, Search**. Partial timed target/blocker confirmation has two searches because setup lookup lies outside timing; its baseline/final counts match. Supported uncertain-policy recovery retains setup Shell one / Policy attempt one and **zero timed recovery mutations**. Detail/portfolio queries issue no provider/target calls. Ledger-owned currentness, immutable intent, explicit confirmation, ordered mutations and no generic uncertain-write retry remain intact. Load post-read leaves the target journal unchanged.

Response sizes are effectively unchanged: detail median 51,922 bytes; full-flow decoded API response totals across five calls are memory 199,798 and Mongo 199,816 -> 199,815 bytes. These are serialized/decoded body sizes, not wire bytes. Small differences follow synthetic IDs/timestamps/order. Unknown sizes remain null. No payload-size or external-provider-speed optimization claim.

## POC scenario regression

Current source assertions in the passing full backend/physical/browser suites take precedence over historical catalogue counts. D2 new Mock success requires ledger readback after Amend; no catalogue rule or provider status was changed.

| Scenario / invariant | Asserted current result and call stopping | Evidence |
| --- | --- | --- |
| Canonical happy path | COMPLETED after supported Search/Shell/Policy/Amend/readback; stable events/IDs | `test_onboarding`, D2 ledger tests |
| Missing address | REVIEW_REQUIRED; no target stages | `test_onboarding` |
| Policy failure | FAILED / GT_POLICY_VALIDATION_FAILED; no Amend or completion | `test_onboarding`, orchestration/D2 tests |
| Partial Amend | REVIEW_REQUIRED / partial enrichment; no readback-success or completion | `test_onboarding`, D2 tests |
| Unknown eligible synthetic UEN | REVIEW_REQUIRED / ACRA_ENTITY_NOT_FOUND; no mapping/target mutation | `test_onboarding`, registry/routing tests |
| Document all-match / mismatch / low-confidence / missing | Historical manual review remains; four matching candidates, explicit mismatch, confidence0.54, nullable missing source; no implicit canonical overwrite | `test_document_processing` |
| Document processor failure | Retrievable FAILED / safe processing code; no later field/later-provider result | document resilience/API tests |
| Direct / indirect / multiple ownership paths | ANALYZED; exact Decimal60/40,30/10,20direct+20indirect=40; paths counted once | `test_ownership_analysis` |
| Below threshold | ANALYZED; inclusive configured comparison; no false candidate | ownership threshold tests |
| Incomplete chain / cycle / bounds | REVIEW_REQUIRED with typed diagnostic, no definitive candidate | ownership adverse tests |
| Ownership provider failure | Safe retrievable FAILED; no stranded loading/analysis or partial result | ownership resilience tests |
| Zero-touch discrepancy / low-confidence / multiple blockers | WAITING_FOR_REVIEW until specific current backend-authorized resolution; unrelated blocker remains; no downstream target write | zero-touch/reconciliation tests |
| Unsupported/conflicting jurisdiction and invalid SG identifier | Registry-stage review; no ineligible ACRA or downstream calls; no invented route | routing/acquisition tests |
| Stale/duplicate/concurrent resolution or submission | Current version/policy/intent enforced; one accepted execution and stable finality | orchestration/ledger/currentness tests |
| Uncertain target and retained-outcome recovery | No generic mutation replay; same intent/finalization authority; readback cannot infer Policy success | recovery/D2/physical restart tests |
| Persistence restart/corruption/CAS/deletion | Strict current10/legacy1-9; safe corruption failure, detached reads, update-only/CAS and no resurrection; read-only restore adds no provider calls | physical127 and strict/read-ownership tests |
| Auth/team/cache isolation | Backend RBAC/safe404, fresh in-lock authorization, session-scoped cache cancellation/clearing; no cross-case stale response | backend concurrency/access, frontend and browser tests |
| Browser/demo process lifecycle | Exact owned processes, bounded stop/reset, occupied/unrelated/PID-reuse protection, truthful provider/stage labels | Windows lifecycle and full browser receipts |
| Real ACRA/GoldTier or official remote Mock retrieval | Not automated in this program; no runtime/provider promotion or interoperability claim | Outside authorized local evidence lanes |

Full suites assert terminal/error/event/call-stopping behavior, not merely test names. Primary serial/load raw signatures provide additional direct count/result evidence. Every required-stage failure stops prohibited later calls; read-only observation cannot complete or replay a target operation. Historical catalogue entries remain unchanged.

## Frontend findings and remediation

No frontend product/query/cache/projection optimization was retained. The same-session desktop 1440 / narrow 360 measurements have 20 cold/warm primary pairs per width/arm, 160 interactions total. Cold navigation always has 14 attempts / nine completed / five cancelled requests, about 110,108 decoded ResourceTiming bytes. Warm client-query navigation has zero requests/bytes. Development StrictMode, cancellation and authenticated cache behavior explain the repeated attempts; current session/stale-result guards remain intact.

Desktop cold median 731.101 -> 716.757 ms; narrow 717.402 -> 710.158. Warm medians 278.884 -> 281.014 and 279.445 -> 279.656. These repeated-window differences establish no causal frontend gain.

Gate 5 initially failed independent review on cache metadata: Playwright routing disables HTTP cache, contradicting a warm-assets label. Exactly a reload comment and output metadata field were corrected. The original method/raw timings remain; bidirectional byte reconstruction proves execution, assertions and waits unchanged. Original method SHA256 `1310bf487ce69024a4080a04b1b59e7aea9bfaa86eead27e3291613cf1a9dcc8`; corrected candidate `e8f6fda4ff88b36fd41ac25b2d60b6a9fa523b17688dded43959ffdbba4cc19b`. Fresh recheck passed; final full E2E executes the corrected method.

HTTP cache stays disabled; only the client query cache is warm. Browser CPU/memory/rerender work and the actual Chromium build were not captured. Optional standalone E2E TypeScript checking with `--types node` failed TS2688 because Node ambient types are absent. Canonical app/node typechecks and runtime browser execution passed without dependency churn. No production, warm-assets or fresh-browser timing claim.

## Complete-case local load

Gate 6 added no product change. Before/repeat arms use the same method, one shared app/bundle/authenticated client/Mock target per mode/level, and unique synthetic cases. Each level has five primary closed cohorts, one excluded warmup and a separate resource probe. Total: **520 primary cases / 70 cohorts**. Cases within each cohort are correlated; there are only five independent makespan/CPU observations per level. This is shared in-process ASGI burst evidence, not open-arrival/TCP/production capacity. The table uses the repeat arm; JSON preserves both arms.

| Mode/concurrency | Primary cases per arm | Repeat cases/min | p50 ms | p95 ms | Parent CPU p50 ms/case | Separate sampled RSS bytes | Errors/timeouts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| memory_1 | 5 | 54.73 | 1095.51 | 1123.81 | 171.8750 | 188903424 | 0 / 0 |
| memory_5 | 25 | 158.49 | 1848.05 | 1943.98 | 175.0000 | 422248448 | 0 / 0 |
| memory_10 | 50 | 201.69 | 2813.33 | 3091.68 | 193.7500 | 712929280 | 0 / 0 |
| memory_20 | 100 | 204.54 | 5491.38 | 5925.61 | 235.9375 | 1180069888 | 0 / 0 |
| mongo_1 | 5 | 20.40 | 2970.35 | 3008.80 | 1546.8750 | 282345472 | 0 / 0 |
| mongo_5 | 25 | 32.02 | 9139.10 | 9483.62 | 1675.0000 | 505298944 | 0 / 0 |
| mongo_10 | 50 | 33.52 | 17310.03 | 18060.14 | 1731.2500 | 705576960 | 0 / 0 |
| mongo_20 | 0 primary | resource only | unmeasured | unmeasured | unmeasured | 895635456 | unmeasured |

Memory plateaus near concurrency 10/20 at about 202-205 cases/min with roughly doubled latency at 20. Mongo plateaus around 5/10 at about 32-34 cases/min with longer latency at 10. Existing strict/copy/full-envelope/transaction costs remain; load does not newly isolate causal bottlenecks.

Mongo 20 resource probes completed in 49.724 / 50.224 seconds, exceeding the 45-second escalation margin against the unchanged 60-second acceptance deadline. Sampled RSS was about 900 / 896 MB, host CPU about 13% and available memory above 10 GB. Refusal reflects the elapsed margin, not observed OOM/host instability. Both primary arrays are empty: no Mongo 20 throughput, latency, CPU or error distribution. The 60-second wait detects noncompletion; ThreadPoolExecutor shutdown awaits started work, so it is not hard termination. No per-selector, cleanup, native, driver or load deadline was inflated; the CI aggregate envelope change below accounts only for added selectors.

Every primary case asserts COMPLETED/SUBMISSION_CONFIRMED, one native page/four fields, exact Decimal 60/40 candidates/paths and the unchanged target journal after post-read. Counts are four registry / one native / one ownership / five HTTP / six ordered target operations, physical 484 finds / one insert / 60 updates. Saved counts are backed by live assertions; no separately saved full call trace is claimed. Resource probes include post-window verification and retained warm cases, unlike serial setup-inclusive RSS. After each load arm, 44 recovery/adverse tests and physical 127 across 19 suites passed. Independent Gate 6 audited all 520 cases, 70 cohorts, 294 aggregate cells and 46 artifacts and reran 44 adverse tests.

## Rejected work and independent gate history

| Gate | Independent outcome | Rejected/corrected evidence |
| --- | --- | --- |
| 1 | Initial FAIL -> fresh PASS | Observer-contaminated primary CPU and invalid merged thread profile replaced before product edits; complete remeasurement. Rejected 200 samples retained. Later EOF-only report correction separately reviewed/checkpointed. |
| 2 | PASS | Preliminary separate-window microbenchmark is corroboration only; source-byte/style restoration and exact-source alternating pairs completed before acceptance. |
| 3 | PASS | Yappi total-recursive call interpretation corrected before accepted report. Original higher blocker tail and unchanged-source repeat both preserved. |
| 4 | PASS | Cookie/queue-observer test pilots corrected to canonical clients and actual dependency; no assertion/deadline weakening. |
| 5 | Initial FAIL M1 -> fresh PASS | Metadata corrected in exactly comment/output field; original execution/raw timings preserved. Request-entry/seed-row pilots corrected before measurements. |
| 6 | PASS | UUID versus authoritative source-case join pilot rejected/corrected before collection; no product change. |
| 7 | Initial root inventory failure -> affected recheck; sole fresh final QG | Added coverage required exact inventory / derived CI envelope maintenance; initial failure preserved. Coordinator evidence does not grant independent PASS. |

No query/index/auth-cache/timeout or target-parallelization change was retained. No unsafe optimization was attempted. Prior gates' pending-review wording records their original frozen point; their separate exact PASS reports/checkpoints establish acceptance.

## Fresh cumulative verification

Receipts below bind to the source HEAD above. Full backend opt-ins are explicitly reconciled: 127 physical and six real OCR cases run separately with zero skips. Root-unit selection includes all current root test modules except separately executed Windows/harness modules. Unit tests of pre-PR logic do not run the actual publication gate.

| Check | Actual exit | Command wall seconds | Stable receipt/log |
| --- | ---: | ---: | --- |
| backend | 0 | 960.09 | gate7-backend.txt |
| ruff | 0 | 0.11 | gate7-ruff.txt |
| mypy | 0 | 1.36 | gate7-mypy.txt |
| method-ruff | 0 | 0.14 | gate7-method-ruff.txt |
| contracts | 0 | 3.42 | gate7-contracts.txt |
| harness | 0 | 0.12 | gate7-harness.txt |
| physical | 0 | 188.02 | gate7-physical.txt |
| real-ocr | 0 | 11.98 | gate7-real-ocr.txt |
| frontend-test | 0 | 7.86 | gate7-frontend-test.txt |
| frontend-typecheck | 0 | 5.70 | gate7-frontend-typecheck.txt |
| frontend-build | 0 | 7.11 | gate7-frontend-build.txt |
| windows | 0 | 376.91 | gate7-windows.txt |
| root-units | 0 | 118.56 | gate7-root-units.txt |
| check_project_state | 0 | 0.31 | gate7-check_project_state.txt |
| check_architecture | 0 | 0.42 | gate7-check_architecture.txt |
| check_tooling_config | 0 | 0.09 | gate7-check_tooling_config.txt |
| check_policy_authority | 0 | 0.09 | gate7-check_policy_authority.txt |
| check_external_provider_readiness | 0 | 0.08 | gate7-check_external_provider_readiness.txt |
| check_secrets | 0 | 2.34 | gate7-check_secrets.txt |
| e2e | 0 | 1072.95 | gate7-e2e.txt |

Accepted local checkpoints before final evidence commit:

- `abb7f14b090927d6680cd86d89d7dd500d9cfd6a`: perf: establish measured optimization baseline
- `c779cf3a2b68ad5acf626b05a313e70067af1228`: docs: correct reviewed baseline report EOF hygiene
- `8ad875e60883129221e06e588c1a650394283aba`: perf: reduce measured computational overhead
- `d0a4855d2564d6bcb0f42a895b45b0a9cdf6e1d5`: perf: optimize measured persistence hotspots
- `a3f4d17a920bc19fbf7f3807c1fe494453c692ee`: perf: introduce bounded safe concurrency
- `5a84f112ecb82e4da2051e9cac867fdc8d7e2295`: perf: measure browser request and cache behavior
- `412e50250dfdd9064579c99ee8e3ab987df1ff2a`: perf: validate local throughput

Late tooling remediation: root 278 initially had one failure because the inventory assertion expected 70 selectors; the added browser measurements make 72. Exact inventory and suite-budget assertions were corrected to 72 / 13,020 seconds, and the CI outer envelope to 231 minutes. Existing execution 60 seconds, cleanup 120 seconds, discovery 60 seconds and installation 14 minutes remain. This coverage-budget maintenance has no performance claim. The original failure receipt is retained, the focused inventory test passed, and all affected root/governance/full browser checks reran on the three exact current working-file hashes. Product source and original timing methodology remain unchanged.

Dynamic counts, warnings/skips and exact command arrays are in JSON and preserved logs. Full backend: 2601 passed / 133 opt-in skips / three existing invalid-timestamp serialization warnings. Strict mypy: 126 files; contracts: 44; harness: four; physical: 19 suites / 127 passed / zero skipped; real OCR: six passed. Frontend: 560 tests / 47 files; full E2E: 72 isolated selectors. Windows lifecycle: 31 passed; repository units: 278 passed. Their exact inventories are taken from fresh logs. Ruff, method lint, governance/scanner units and six governance/security scripts pass. Complete BASE diff, explicit new-file UTF-8/EOF/whitespace and secret checks precede freeze. No missing/stale/skipped evidence is called passing.

Initial full E2E stopped at selector 10/72 on the unchanged 60-second lifecycle deadline; first nine passed and the remaining 62 were not dispatched. The unchanged document-review selector passed a focused diagnostic run in 7.8 seconds, with upload 201, backend four reviewed fields, cache publication and four-field rendering complete. The initial stall was not localized. The first complete diagnostic repeat passed the original selector 10 and 52 selectors overall, then exposed a distinct Garden test race: it asserted one document before upload finished. Its GoldTier-search stage can be visible during responsive native processing. Registering the actual POST upload response before create and asserting 201 adds the missing dependency; all original document, ownership, target-count, external-call, state and readback assertions remain. The focused corrected Garden test passed. A full affected root/governance and 72-selector rerun followed at the same 60-second deadline. The next full run passed 51 selectors but the held-response selector 52 timed out, leaving 20 undispatched. Opt-in payload-free milestone strings were then added to the recovery/lost-response test helpers without changing any await, assertion, deadline or target operation. Focused held recovery passed in 12.7 seconds, including screenshot and confirmation; that earlier stall also remains unlocalized. Observed available memory was 10.21 GiB / host CPU 4.6%, so resource exhaustion is not asserted. All three failed full runs and their undispatched selectors remain recorded; the final complete result is separate. Diagnostic logging is not a claimed repair of either timeout. No product fix or per-selector timeout increase is claimed. The fresh reviewer must assess this residual observation against the complete repeat and source evidence.

## Change flags and remaining limits

- **api_type**: External request/response unchanged; internal intake adds optional Callable reauthorize keyword.
- **schema**: Unchanged current10/strict legacy1..9.
- **connector**: Unchanged.
- **configuration**: Product settings/defaults/runtime dependencies unchanged; task tooling requirements added; CI outer job envelope225->231 minutes solely for72 discovered selectors, preserving60 execution/120cleanup/60discovery seconds and14installation minutes.
- **business_rule**: Unchanged.
- **mapping**: Unchanged.
- **auth_security**: Fresh authentication/profile/team/case reauthorization first inside existing intake case lock after worker admission.
- **architecture**: Existing owners/dependency direction retained; no new pool/store/cache/provider owner.
- **provider_status**: Unchanged Mock/Local/Sandbox/Partial/Dormant/Live classifications; no Live promotion.
- **runtime**: Async native intake uses existing bounded worker pool; Mongo strict traversal/caller-owned read computational cost reduced.

Claims are LOCAL_MEASURED / POC_MEASURED / SYNTHETIC_LOCAL_LOAD / DEVELOPMENT_MEASUREMENT only. Existing provider labels, sponsor gaps and unresolved human/final approval gate remain. No production/SLA/Live claim or external-provider-load result. Existing frontend 574.42 kB chunk warning and npm audit six vulnerabilities (one moderate, three high, two critical) remain outside this bounded change; dependencies were not churned.

Eight canonical E2E-generated UAT PNGs are preserved under ignored task evidence and their tracked paths restored to exact pre-test HEAD blobs; no generated image churn enters this candidate. Worktree, containers and ignored raw evidence are retained. No push, PR, merge or actual pre-PR publication command. Exact fresh independent PASS permits only the already authorized local final checkpoint and owner publication review. Actual publication still needs separate owner authorization and latest-main/integration/clean-committed pre-PR checks. Final commit HEAD and exact QG hash are returned after acceptance.
