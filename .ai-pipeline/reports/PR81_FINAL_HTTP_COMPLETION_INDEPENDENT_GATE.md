# PR81 independent HTTP completion correction gate

**Focused correction: PASS. One prospective original-seeder window: APPROVED under the exact protocol below. PR81: NOT READY FOR HUMAN MERGE.** Approval is provisional acceptance eligibility, not proof of historical repair, stability closure, residual-risk acceptance for publication, or a full-candidate Quality Gate.

## Independent scope and frozen identity

Reviewer pr81_http_completion_independent_gate did not implement the candidate. Latest owner assignment ce355c4a-ca47-4817-a8a1-f1bc7f6676aa was read, including sections6,9,10 and13. Root/backend AGENTS, fyp-quality-gate and integration-security-review/checklist, canonical CI_TOOLING sections, original stability plan, preceding independent FAIL/disposition, current handoff/diff/tests and bound receipts were inspected. This reviewer ran only the supplementary completion suite, scoped Ruff and read-only context/hash/Git/runtime checks. Sole written artifact is this report. No original seeder fixture, broad suite, target mutation, database, ETW/raw ETL, Git or remote operation was performed.

Canonical worktree C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm; branch feat/blocker-resolution-idp-ux-optimization; HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached main/merge-base e799d74063678bb0eccbea445d5ab3c8628dd2c0. Cached main is not a fresh remote observation. Staging empty;24 tracked modifications comprise preserved23 plus this seeder correction. Prior source additions and historical task artifacts remain. Full diff inventory was inspected for scope; semantic acceptance here covers the two new owning paths and their relevant unchanged consumers, not every prior PR81 correction.

Frozen source27 e876200d203fc5869373b88274d83b878c892c56a448dd08bdf5bb7cccb5d1f7 independently recomputed from actual raw bytes. All27 match; all25 checkpoint paths still match ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490. All1,175 historical and all1,204 preservation hashes match before/after focused execution. Bound evidence8/8 matches. Full preservation-map identities: historical caa2bf3e7066903094f41be17179f7620170962ad4cbc164de70b8cb03f9a4f6; complete40948034f5c890f157d772adc45c7c95ecdbedaff5317c74848e03d291087fb6. Frozen original fixture hash435d3feba400b00e23a946a6785b193c3bb7b355b39b7f05d6abb0060b73fbb6 unchanged.

| Owning path | Raw identity | Delta |
|---|---|---|
| scripts/seed_phase13_demo.py | old33cbd0c589d3ecc84ec5fc5bd2dd65b146f336f2c64a4934db63929f07df181d; newb2c225009ae050a003f14ff4309c949a442edb0705b7e92b1faff69c4b599223 | Four added lines at181-184,194-195; post-read remaining-length guard |
| apps/backend/tests/test_http_seed_response_completion.py | f375810e1da5135c16fe1f009c24388a8d116744be68b511b6434b435db0bc7a | Ten supplementary cases; real HTTPResponse parser plus real complete-body loopback control |

The seeder HEAD blob has normalized LF bytes, unlike the raw pre-remediation checkpoint. Independently normalizing current bytes proves exactly the prescribed four additions versus HEAD; no additional seeder change is hidden by raw hash differences.

## Mechanism and correction review

Installed Python3.12.10 HTTPResponse.read(amt) clips to remaining Content-Length, calls buffered read, subtracts returned bytes, and permits short EOF without IncompleteRead. Its source explicitly distinguishes bounded from strict unbounded reading. This agrees with [official CPython3.12.10 source](https://raw.githubusercontent.com/python/cpython/v3.12.10/Lib/http/client.py) and the [HTTPResponse API](https://docs.python.org/3.12/library/http.client.html#http.client.HTTPResponse.read). The new guard reads this authoritative remaining-length state after the existing bounded read. Positive remainder rejects valid-prefix JSON and missing-body empty success before JSON/empty acceptance. None preserves EOF-delimited/chunked behavior;0 preserves complete responses. The existing size-limit check retains precedence over incompleteness.

This is a proven general client-completion/false-success defect, owned by HttpSeedApi._request. The three-case real dummy probe showed complete65786 bytes return without peerEOF; short65280/65786 withEOF falsely accepted validJSON; short65280 withoutEOF times out15s. Deterministic real-parser red evidence produced three expected failures/seven passes, corrected ten passes. Synthetic POST is supplementary no-retry evidence; it does not replace ledger or real target-idempotence tests.

**Historical cause remains UNKNOWN.** Native acceptance65786 versus actual client65280, missing506/noEOF and15-second timeout are not explained or repaired by this guard. It runs only after read returns, cannot deliver withheld bytes, and cannot bypass the unchanged timeout. No TCP acknowledgement/FIN proof is available. The initial real dummy regression run6 PASS/4 FAIL includes two unexpected TimeoutErrors whose native delivery/EOF cause remainsUNKNOWN; its evidence is retained. Switching the supplementary early-EOF unit oracle to deterministic real HTTPResponse parsing exercises the proven parser defect; it does not convert the native failures into PASS or replace the original real integration test.

## Verification and safety

Independent command from repository root:

`tmp/pr81-final-windows-checkout/.venv/Scripts/python.exe -B -m pytest apps/backend/tests/test_http_seed_response_completion.py -q -p no:cacheprovider --tb=short`

Result10/10 PASS, exit0. Independently executed scoped Ruff with backend canonical config and --no-cache: PASS, exit0. Existing FastAPI/Starlette httpx deprecation warning retained; no dependency change made. Cases cover validJSON missing506, missing entire body, complete held-open realHTTP, zero-length, EOF-delimitedJSON, complete chunking, truncated chunk rejection, size-limit priority for complete/incomplete oversized responses, and one ambiguous dummyPOST without retry. Assertions verify timeout15 and one request in parser paths. Dummy owned worker cleanup is bounded10s.

Implementer frozen evidence: ten supplementaryPASS; ten affected existing seeder testsPASS with original selector reserved pending this approval; canonical mypy appPASS127files; six architecture/project-state/policy-authority/tooling/provider-readiness/secret checksPASS; final scopedRuff/Markdown hygienePASS. The original scoped receipt's earlier three authored-test lint findings remain truthful historicalFAIL; final hygiene and independent Ruff supersede lint only. git diff --check for owning tracked deltaPASS. Original fixture/assertions remain byte-identical and mandatory in subsequent acceptance.

Runtime independently verified Python3.12.10x64, Uvicorn0.52.1, FastAPI0.141.1, Starlette1.7.0, AnyIO4.15.1, httptools0.9.0, h11 0.16.0; ordinary Windows token administrator=False. Installed auto HTTP protocol remains HttpTools; original fixture explicitly returns asyncio.SelectorEventLoop. No options, loop, topology, delays, buffer settings, package pins or timeout changes. HTTPS/cookie/CSRF behavior, safe fixed errors, response limit1048576/read1048577 and no automatic retry remain. No raw bodies, credentials or KYC are newly persisted; test bytes are explicit dummy JSON. New incomplete error exposes no payload. Existing orchestration/ledger/currentness owners are unchanged; no target replay is added. API/type/schema/connector/configuration/business-rule/mapping/auth/architecture/provider status unchanged; only seeder runtime incomplete-body rejection and supplementary tests change.

No required focused fix remains. No acceptance claim is made for full backend/physical Mongo/frontend/browser/Windows/publication evidence yet.

## Prospective-route eligibility and exact authorization

**APPROVED once for this source27 and unchanged runtime**, as a separate prospective route under latest owner section10. This is not the proven-historical-repair branch. Existing stability-plan line9 permits a new fixed window after a justified changed candidate or materially new diagnostic evidence; the preceding independent disposition also recognizes conditional prospective acceptance. Here a real completion-contract defect has a narrowly justified correction, deterministic before/after falsification and new discriminating evidence. The historical failure is explicitly retained rather than reattributed. Latest section10 expressly permits historical cause to remain unknown if a separate route is documented and independently approved. No governance rule inspected requires known historical causality for that route. These facts meet eligibility to execute, not its final acceptance conditions.

The known early-EOF framing false-success defect is corrected; no known framing, target-ledger, auth or no-replay failure is waived as timing risk. The historical missing-byte failure remains an unresolved risk to be challenged by mandatory unchanged real tests. This reviewer does not accept its harmlessness, extend prior source68 SDQ01 risk acceptance, approve a sampling/reset strategy, or substitute diagnostic passes. Historical window ordinal1PASS/ordinal2FAIL/ordinal3undispatched remains permanentlyFAIL. Any failure of this new window blocks advancement.

Coordinator may dispatch exactly three fresh independent ordinary-token processes in ordinal order, working directory:

`C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm/apps/backend`

Each exact command:

`& 'C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm/tmp/pr81-final-windows-checkout/.venv/Scripts/python.exe' -B -m pytest tests/test_phase13_demo_scripts.py::test_http_seeder_runs_twice_against_one_live_memory_backend -q -p no:cacheprovider --tb=short`

Separate safe ordinary pytest output destinations: .ai-pipeline/reports/PR81_FINAL_HTTP_WINDOW_1.log, PR81_FINAL_HTTP_WINDOW_2.log, PR81_FINAL_HTTP_WINDOW_3.log. No full locals, credentials, HTTP bodies or extra tracing. Record ordinal, exact command/cwd/runtime, native exit, duration and source27 before/after. Each process creates fresh memory/Mock fixture and ephemeral listener. Preserve original request15, cleanup10, Selector, actual urllib/Uvicorn path, all ten COMPLETED/MOCK_GOLDTIER_SUBMITTED confirmations with version currentness, firstseed created10/reused0/prioritised10 and second created0/reused10/prioritised10, plus worker-not-alive assertion.

No wrapper, monkeypatch, plugin, relay, ETW, altered environment/configuration, socket option, enlarged buffer, added sleep/retry or altered assertion may affect this original selector. Do not execute any prior uncertain case. Check exact source/runtime binding before every process and after. Execute ordinal2 only if1 exit0 and binding/cleanup holds;3 only if2 meets the same conditions. First failure, source/runtime drift, cleanup failure or unexpected control error stops the window immediately. No failed-ordinal retry, additional window, sampled replacement or substitution of previous PASS. Subsequent ordinals stay NOT DISPATCHED. Any source correction requires new review and genuinely new authorized protocol; this report cannot be inherited.

Three PASS exits are **PROVISIONAL** stability evidence only. Final acceptance still requires canonical complete backend including the original selector, guarded physical Mongo, frontend/type/build/root/contracts/Windows/Ruff/mypy/security/governance, complete browser inventory/shards/eight journeys, direct independent final verification and explicit assessment of disclosed residual historical uncertainty, coherent full matrix, latest-main integration/committed pre-PR and both new push/PR mandatoryCI PASS. The separate historical width360 conditions remain applicable and are not closed by this HTTP-only protocol. This report grants no commit/push/PR-change authority or full releasePASS.

## Verdict and next action

Focused two-path correction PASS; exactly one defined prospective original-seeder window eligible and independently authorized under latest owner scope. Execute it once, stop first failure, and preserve all evidence. If it passes, proceed only through remaining mandatory acceptance and fresh full gate. Historical-cause uncertainty stays explicit. Current final decision: **NOT READY FOR HUMAN MERGE**.

## Exact independent read-set binding

Owner attachmentSHA256 368958d5d01d1ad8cb0cd6aa812d9bb4eb9d3ba1f293fb17c967e4bf5d77d7f1. Binding identity 34dda872a4bd0d0be7ad29a35d6bfd9642522007c3085b8c52f35fa152a066dc. Algorithm SHA256 of UTF8 sorted compact JSON, no trailing newline; source_hashes is frozen27 map from verified candidate binding, reviewed_read_set table below, owner_attachment_sha256 above and scope `Independent focused HTTP completion guard acceptance and one prospective original-seeder protocol eligibility; not full PR81 release gate`. Report excluded to avoid self-reference. Bound contents were rechecked after independent execution.

| Task-relative read-set path | Raw SHA256 |
|---|---|
| .agents/skills/fyp-quality-gate/SKILL.md | c2782d535ab2e8a8479a7742c7b471815c62a3769bc7f948851d9c1fb3b1a8d0 |
| .agents/skills/integration-security-review/SKILL.md | e5d8e06e643bf9d6c43845e837dfd3c020629913d0013047a65b404c7fd68b34 |
| .agents/skills/integration-security-review/references/review-checklist.md | 79c0b29f9c2a9e0ec55c3d1c4eec56bc9081c75748eaff9c2a5770e26235f78b |
| .ai-pipeline/001_planner/PR81_OVERNIGHT_STABILITY_PLAN.md | f3518b9608bfa9a6553161711a49100f90b31ce1bf6a30b1524986f8b69fafc2 |
| .ai-pipeline/reports/PR81_FINAL_HTTP_CANDIDATE_BINDING.json | 9c35dffc89545f2c38a4339802beb41abbd59ad0650718629502c41cd11bf0c8 |
| .ai-pipeline/reports/PR81_FINAL_HTTP_COMPLETION_PROBE.json | dad714d4c4a11a2d8a2f04d69d02f165e2d41dfa31a238d47aed684f5651ccc4 |
| .ai-pipeline/reports/PR81_FINAL_HTTP_CORRECTION_REVIEW_HANDOFF.md | 8d761295cdfc060f0ff20199eb7c127d03ab40b8f675e713d6866a53df51cdc4 |
| .ai-pipeline/reports/PR81_FINAL_HTTP_DETERMINISTIC_RED.log | 46866e62ce8ddf729aade56927b06941e4dab298ff73741a169af8aa8bedabd9 |
| .ai-pipeline/reports/PR81_FINAL_HTTP_EXECUTION_MAP_AND_PLAN.md | c02bb8c36e5d299eda051a7b3c29af71107cbfefb0ba22338aa6b2466239b987 |
| .ai-pipeline/reports/PR81_FINAL_HTTP_EXISTING_FOCUSED.log | 3b089233ed885d4e1f5be4749527cdb1a43bbf1a0bf6a6513ec33ec8a7d37ee1 |
| .ai-pipeline/reports/PR81_FINAL_HTTP_FIRST_RED_RECEIPT.json | cd539aea954e92197d88ad27b1956f816516ff05e6d5c12bb6b5159b05cdd0ff |
| .ai-pipeline/reports/PR81_FINAL_HTTP_FROZEN_FOCUSED.log | 3b089233ed885d4e1f5be4749527cdb1a43bbf1a0bf6a6513ec33ec8a7d37ee1 |
| .ai-pipeline/reports/PR81_FINAL_HTTP_FROZEN_HYGIENE.json | 537593f3ba66ebb92eb1589d41a37404706e8360d5cec5421701fc5179bb8b7e |
| .ai-pipeline/reports/PR81_FINAL_HTTP_MYPY.log | 43ae4572b2615ea845a8af9483b6f3c29d02aead3239ebc525ac7e906bc02fa1 |
| .ai-pipeline/reports/PR81_FINAL_HTTP_SCOPED_CHECKS.json | 47329d5a6b3e32c2491c3cd2e5aebf042e633c701eabdae856c7254d2f05fa97 |
| .ai-pipeline/reports/PR81_FINAL_RECOVERY_DEPENDENCY_DISPOSITION.md | 604957241c3c7119715ac26bd9728e748afd3ba353902d3de77bfcb6aa8b59a9 |
| .ai-pipeline/reports/PR81_OVERNIGHT_INDEPENDENT_QUALITY_GATE.md | 1d286d8e51e5f5471499ce51a0dcc51179be6f2e04e356889de833d7d3c7327f |
| AGENTS.md | 8e27887194365979c7e79b8a49294caefe519eb5d2faf106aab2a710a0c78fb0 |
| apps/backend/AGENTS.md | bdd5832ce3b341b867b56db41906af597eeee036066624a302bb298c41065e43 |
| apps/backend/tests/test_phase13_demo_scripts.py | 435d3feba400b00e23a946a6785b193c3bb7b355b39b7f05d6abb0060b73fbb6 |
| docs/ARCHITECTURE.md | 70e4634f80214332130848db478612972d59708a0f8b48d2f750d0db29cf6676 |
| docs/DEVELOPMENT_WORKFLOW.md | 8d7104d92dcae76c747eb1c5fe6955e045f047a1469a0453a9602bbd50667f9d |
| docs/PROJECT_STATE.md | d5b017dbb038351a2fdfaf8d904e6757656c807ba60d9136919bfc68189a10c4 |
