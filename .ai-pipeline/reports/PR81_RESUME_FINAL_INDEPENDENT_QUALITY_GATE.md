# PR81 Resume — Final Independent Quality Gate (initial freeze)

## Verdict and boundary

**FAIL — NOT READY FOR PUBLICATION / NOT READY FOR HUMAN MERGE.**

The reviewed application's local acceptance, security and current prospective stability requirements are satisfied within the stated Mock/offline scope. The full candidate gate nevertheless fails because two immutable archival unified-diff files introduce three unapproved whitespace diagnostics into the staged/committed publication checker. This is the sole mandatory local defect established by this review. No product defect or failing acceptance assertion was found.

This report is the initial, immutable FAIL. A bounded governance correction requires a separately versioned manifest and fresh independent R1 review. Do not overwrite this report or treat its product conclusions as an overall PASS. Publication, clean committed-state checks, actual candidate push/PR CI, thread resolution and human merge readiness remain subsequent gates.

## Authority, independence and exact candidate

Reviewer: independent agent pr81_http_completion_independent_gate; implementation and Git coordinator: parent agent. The reviewer made no implementation, Git, database, target, fixture, ETW or publication mutation. Its only output is this assigned report. Repository AGENTS.md, canonical fyp-quality-gate and integration-security-review skills/checklists, the current workflow/context and current contract/decision owners governed this review.

Latest owner assignment: attachment 536d4c1f-74a3-441d-963e-71add3d4ab10/Pasted text.txt, SHA256 12e77d08988f294d5c9fad2b0f07f709abf506962e147516c30b5eef1ea1828d. The owner permits at most two bounded, evidence-justified remediation/re-review cycles, says not to stop merely for ordinary in-scope remediation, prohibits weakening requirements, and requires preserving historical evidence. It requires fresh complete browser acceptance and eight actual journeys while avoiding unnecessary repetition of already valid expensive suites.

| Binding | Exact value |
| --- | --- |
| Worktree | C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm |
| Branch | feat/blocker-resolution-idp-ux-optimization |
| HEAD | dd8c36c8a911f4b5f3b80e7441d049f1aa976599 |
| Published HEAD tree | 2bbef607d571b4fb7a734582cb9112debed1a305 |
| Cached origin/main and merge-base | e799d74063678bb0eccbea445d5ab3c8628dd2c0 |
| Frozen source36 | f6607f766b36ec1e2b6fc251b93b22c4940985fac394d28160b1878e802cfbae |
| Prior source27 executed by earlier broad suites | 916d57b043be8a5d29e85992b9df9cb2dbdab855fa909e776208391ad934dcab |
| Historical original source25 identity | ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490 |
| Frozen publication manifest SHA256 | 702121db2777150430133625518cb01f286b54814e161facc4468085acdadc32 |
| Publication268 raw map identity | 0f29bd3024a2a3a0bfe4429d085ed07baed9f2deea74bdcc1f716cea054c95a3 |
| Complete674 branch-candidate raw map identity | aa767f47b296500ea025f9b83aae33aaecc8f017d8a19c9a7f8ab590138b96dd |

Map identities are SHA256 of UTF-8 JSON with sorted keys and separators comma/colon, without an added newline. The reviewer independently read and recomputed all36 source hashes, all268 proposed publication hashes and all674 complete branch-candidate hashes. All matched. The 268 paths comprise31 tracked modifications,226 nonignored untracked additions and11 individually identified ignored logs. The manifest and this report are separately additive-bound to avoid recursive hashing. No new fetch, staging or committed candidate was represented as completed.

## Mandatory finding F1: immutable archive-context whitespace

**Severity: publication-blocking governance defect.**

Direct read-only Git verification reproduced:

- .ai-pipeline/reports/PR81_TCP_V61_DIFF.txt:425: trailing whitespace.
- .ai-pipeline/reports/PR81_TCP_V61_DIFF.txt:464: trailing whitespace.
- .ai-pipeline/reports/PR81_TCP_V6_HELPER_DIFF.txt:196: trailing whitespace.

Each line contains exactly one ASCII space: an empty context-line marker in a saved unified diff. Both files use LF, so independently computed raw and UTF-8 text hashes are identical:

| Immutable file | SHA256 | Exact context lines |
| --- | --- | --- |
| PR81_TCP_V61_DIFF.txt | ee7603a84a59648b769e24124802f8b05458fa632a6a69a4eff4f838c9bf711e | 425,464 |
| PR81_TCP_V6_HELPER_DIFF.txt | 4a107bbf6e77d4d28a700ac112df17b36002c2f7b05a8c7960053d377251295f | 196 |

Verification command for each exact path was git -c core.autocrlf=false diff --no-index --check -- /dev/null PATH. The output contains the diagnostics above followed by "+ " context content. These files are proposed additions and lack an existing attribute/checker exception. Their staged/branch additions will therefore fail the current ordinary whitespace check. Existing general CR-at-EOL attributes do not excuse these spaces. The earlier five-log whitespace authorization does not authorize these new archives.

**Smallest defensible correction:** extend the existing canonical scripts/pre_pr_check.py HISTORICAL_PATCH_WHITESPACE registry at line31 with precisely these two path/raw-hash/exact-line-set tuples. Preserve the existing identity checks and diagnostic parser in _check_diff_whitespace (line400) and _historical_patch_diff_check_output (line378). Accept only the exact "+ " diagnostics at the listed lines after verifying the entire immutable file hash and each actual line equals " ". No arbitrary path, changed byte, added whitespace, wrong line, different diagnostic shape or normal source/Markdown whitespace may become acceptable.

This is narrower than adding per-file .gitattributes whitespace suppression, which would exempt future nonmatching whitespace throughout each file. The canonical checker already has three exact immutable Phase24 patch exceptions and adverse tests. The proposed extension preserves that fail-closed owner and all other requirements. This review interprets the latest explicit two-cycle authority as sufficient for one bounded, evidence-justified immutable-evidence governance remediation; it does not inherit or expand the obsolete five-log authorization.

Required R1 evidence: positive committed-disposable-repository coverage for both exact archives; adverse modified bytes, additional whitespace, unsupported path, wrong line/diagnostic and changed clean text; retain existing regressions; affected checker/tooling/security unit suites, scoped Ruff and applicable governance checks; independently preserved archive/source/history hashes; new additive exact publication manifest; fresh independent R1 gate. The current raw Git diff check remains a truthful FAIL; a subsequent narrowly authorized canonical exception must be described explicitly. No historical file may be trimmed or overwritten. No application, HTTP, browser stability, target or expensive acceptance rerun is justified by this governance-only correction.

## Complete candidate review

The reviewer examined the complete changed production diff against main and the current uncommitted delta against HEAD, including all task-owned owning source and relevant adverse tests, rather than only the final output-isolation patch. The complete674 raw map binds the branch candidate; relevant contracts, decisions, configuration, acceptance receipts and preserved forensic evidence were read for the named questions. Larger unrelated historical payloads and protected data were excluded.

Contract/integration: batch review DTOs bound one family, up to20 documents/four fields and80 sources; forbid extra/duplicate/stale decisions; validate the entire batch before a first write. Current group reconciliation uses the existing canonical unit of work, exact retained group identities and full idempotence receipts. Partial document-save/retry recovery rejects different values sharing an audit prefix and preserves provenance. No new sponsor-controlled mapping or authoritative business rule was introduced. Current D071/D072, ADR011, multi-document intake and persistence-recovery profiles remain explicit about provisional and sponsor-unconfirmed behavior.

Authorization and persistence: sensitive replacement/reconciliation/recovery paths reauthorize inside the existing lock/CAS owner. Actor/team scope, inaccessible-case404, revision/document/event identity and deleted-case protection remain enforced. Accepted document replacement preserves lineage and source evidence, cancels stale confirmation readiness and requires a fresh Final Review. Restart recovery binds the retained DOCUMENT_REPLACEMENT_ACCEPTED event and complete document versions; no stale resurrection, stale readiness or alternate persistence owner was found.

Target safety: ledger-owned intent, attempt/result freeze and uncertain-submission recovery remain authoritative. Repeated/read-only recovery does not replay target confirmation. Final Review edits are denied once target submission is frozen or uncertain. Explicit confirmation uses current versions and readiness; no real ACRA or GoldTier Sandbox write was made. Mock, Local, Partial, Dormant and Live distinctions remain truthful.

Frontend: server-authoritative capabilities gate controls. Draft selections stay in memory and bind actor/auth/team/case/version/event/fingerprint context; identity or source change clears/hides stale drafts. Choosing sources does not issue mutation calls; confirmation sends one batch POST. Focus recovery uses the current enabled field and guarded identity/generation, preserving keyboard/focus behavior. Explicit recovery is protected against concurrent editing and stale context; uncertain target recovery remains read verification. No client-side authorization owner or credential-bearing projection was introduced.

Documents/ownership: newline normalization preserves parsed evidence/provenance and OCR scoring. Existing Decimal ownership evaluation, threshold and graph owner remain unchanged. Sponsor-native synthetic annexes distinguish informational registry ownership from client declarations. Review preserves conflicting source evidence and explicit source precedence decisions.

Runtime/tooling: the seeder adds a bounded incomplete-response framing guard, and the original15-second HTTP timeout,10-second fixture cleanup, Selector configuration and no-replay behavior remain intact. Browser sharding preserves the original91 lifecycle/112 test inventory, original assertions,60-second lifecycle contract and120-second overhead/cleanup allowance, serial1→2 dispatch and stop/no retry behavior. Physical Mongo use is explicit, task-owned, allowlisted and has no silent memory fallback or protected-database access.

Output isolation: nine owning config/artifact files move authored synthetic records from global/fixed historical destinations to a fresh UUID task-owned retained sibling of per-test transient output. Scope/containment rejects escape paths. Playwright preserveOutput remains never and automatic screenshots/trace/video remain off; no private error-context retention was enabled. Supplemental seven-test configuration is outside canonical E2E/Vitest discovery. Exact before copies and independent TypeScript AST review establish unchanged assertion/API/JSON payload/timeout/viewport/title contracts. The implementer1035-call projection agrees; the independent broader1820-call projection also matched. Historical report writers were removed without changing product behavior.

No new API target contract, database schema, registry route, provider status, ownership engine, credential flow or architecture owner was added. Recovery/batch/final-review application behavior and explicit capability projections are changed by the accepted branch; CI/fixture configuration, synthetic fixtures, evidence destinations and bounded seeder framing validation are also changed. These are not Live integration or autonomous final approval.

## Acceptance and evidence attribution

These decisions assess actual executed evidence and the source bytes that executed. They do not relabel earlier executions as source36 runs.

| Acceptance lane | Actual evidence and verdict |
| --- | --- |
| Exact source27 full backend | 2661 PASS,145 physical-only deferrals,4 warnings,943.52s; wrapper945.421s exit0. The physical lane separately covers all145 deferrals. |
| Physical Mongo | 23 suites,145/145 PASS,0 skip; allowlisted disposable task-owned database and unchanged owning source. |
| Frontend unit/type/build | 50 files,582 PASS; integrity/type/build PASS. |
| Root/fixture/contracts | Root374,fixture16,contracts44 PASS; applicable governance/security checks PASS. |
| Canonical lint/type | Backend-cwd full Ruff PASS; mypy127 files PASS. Prior lint failure and final import-only AST-identical correction remain separately recorded. |
| Original HTTP prospective window | Three fresh original uninstrumented process executions exactly once, exit0;9.0527661/8.5398164/8.4557539 seconds. Format continuity bridge preserves original-selector runtime bytes; no additional original window dispatched. |
| Original width360 window | Three exact predeclared fresh processes passed with three distinct40-sample sanitized numeric records. Original benchmark method/selector remains unchanged; no standalone rerun. |
| Affected output-isolation checks | Seven no-browser/no-server real Playwright path regressions PASS, independently rerun by this reviewer;48 runner/security tests PASS; frontend type/security/governance PASS. |
| Fresh complete browser source36 | Shard1:46 lifecycles/66 tests PASS,557.219s. Shard2:45 lifecycles/46 tests PASS,525.172s. Total91/112,0 skips,0 retries; exact selected sets disjoint and union equals inventory. |
| Fresh sponsor journeys | All8 actual journeys PASS, with16 retained authored screenshots and distinct synthetic receipts. |
| Fresh benchmark retention |30 batch observations and configured full-suite width360/1440 records with40 observations each. Numeric records are distinct and sanitized;0 target-confirmation requests in both navigation benchmarks. |

Prior broad suites executed at source27. The current source36 changes only browser evidence/configuration owners and supplementary tests/configuration. Independent raw-diff/AST/owner review establishes that the execution-relevant application, backend tests, physical suites, root logic, frontend unit/build sources and original HTTP selector bytes are unchanged. Affected browser/output ownership has actual focused revalidation and the fresh complete source36 browser run. This is a specific evidence-continuity bridge, not an inherited PASS or claim every prior suite ran at source36. The owner's prohibition on needless expensive repetition is respected.

The reviewer independently hash-verified127 retained authored artifacts, all8 actual JSON receipts,16 PNG signatures/hashes and both exact shard commands. Current receipts agree with summaries: COMPLETED/SUBMISSION_CONFIRMED, preview ready, unauthorized403, stale/frozen409, reopen mutations0; after-target counts equal before-search+1, shell1,policy1,amend0,readback1. All records classify AUTOMATED_OFFLINE_SIMULATION and real Sandbox UAT NOT_VERIFIED. Registry ownership classification/provenance remains explicit.

All8 completed screenshots were visually inspected. They show controlled synthetic completion/Final Review state, POC/provider limitations and no replay affordance. Thumbnail inspection does not prove every small glyph; actual full-resolution artifacts remain locally hash-bound. The viewer did not inspect automatic private error-context artifacts.

Independent numeric checks establish40 observations per navigation width (20 cold/20 warm),2 warmups per kind,500ms accounting tail, original method e8f6fda4ff88b36fd41ac25b2d60b6a9fa523b17688dded43959ffdbba4cc19b, finite nonnegative elapsed values and schema-limited GET /api/ request records. The configured full-suite performance lifecycles are part of the mandatory full suite and do not reset/repeat the separate standalone stability window.

## Causal limits and prospective-route decision

Historical missing506-byte/no-EOF TCP cause remains **UNKNOWN**. The reproduced historical record has65786 Content-Length/ASGI/native send acceptance,65280 client body bytes,15-second read timeout and no client EOF. Accepted native send does not establish TCP acknowledgement; no accepted ACK/FIN evidence resolves that historical cause.

The new seeder guard proves a different owning defect: a valid JSON prefix followed by early EOF could falsely pass without complete HTTP framing. Its deterministic adverse reproduction and focused regressions establish that false-acceptance correction. It cannot cause withheld bytes to arrive, repair missing EOF or prove a fix to the historical timeout. Do not describe it as a proven TCP transport correction.

The latest owner explicitly authorizes a separate prospective route when governance permits and mandates current local acceptance. The proven bounded framing correction, independently approved exact three-process route, unchanged original-selector contract and complete current acceptance support **PASS for the current prospective local HTTP stability prerequisite**. The fresh complete91/112 source36 run supplies the requested browser acceptance. This is an explicit present-candidate decision with residual historical uncertainty, not a borrowed earlier SDQ-01 risk waiver, arbitrary baseline reset or conversion of old FAIL evidence.

Old original-window ordinal2 FAIL/ordinal3 undispatched, prior forensic stops, historical root-causeUNKNOWN, frozen V2–V6.1 evidence, earlier lint failures and the interrupted browser run remain unchanged. The old interrupted browser shard1/ordinal18 and undispatched shard2 stay INCOMPLETE, with no assertion failure inferred from controlled termination. New complete runs are separately authorized and separately attributed.

## Preservation, security and cleanup

Independent rereading/recomputation establishes:

- Original25 map:23 current exact matches; two explicitly authorized E2E artifact-owner source deltas have exact archived original raw bytes.
- Historical1175 map:1173 current exact matches; same two source exceptions with exact preserved originals.
- Preserved1204 map:1202 current exact matches; same two source exceptions with exact preserved originals.
- All actual historical report/evidence hashes and frozen map bytes remain unchanged.
- All nine before-owner copies match their exact binding; the27 historical browser/harness paths have nine authorized output-owner changes and18 unchanged paths.
- The eight interrupted-run regression JSON records remain restored exactly; their historical FAIL/incomplete provenance was not erased.

The two exceptions are apps/frontend/e2e/blocker-review-performance.e2e.ts and apps/frontend/e2e/blocker-simulation.e2e.ts. Do not claim all1175 current paths remain byte-identical; they include these two authorized owning-source deltas. No raw ETL, .env, protected sponsor data, credentials or real provider body was read or exported.

An explicit safe-path audit preceded hashing all268/674 candidate paths. The reviewer independently ran the existing secret scanner only on268 manifest-listed paths:0 findings. The11 ignored logs are individually bounded sanitized check/fixture summaries. Fresh ignored browser artifacts, scratch runtimes, raw ETL and private automatic outputs are excluded from publication. Secret-pattern scanning alone is not asserted as proof of confidentiality; provenance/format/owner inspection supplies the additional evidence.

Command-scoped core.autocrlf=false preserves current raw source bytes without changing global configuration. Independent raw-OID vs path-filter OID checks matched all36 source paths; the manifest binds all268 corresponding OIDs. No text/eol/filter attribute affects these owning sources. Real staging must still compare each actual staged blob SHA256 to raw manifest bytes, and the complete committed tree must be independently checked. No stage occurred during review.

Cleanup receipt binds exited/nonrunning retained owned Mongo701abdade3ed2e4276d8092d8f1c142aa9d3fcba0f2a2610b3ea9157b87df4f2. An independent read-only ordinary-token check confirmed this exact container exited, no task-root Python/Node/Chrome processes and no listeners on18900/19400. No container/database deletion or unrelated process termination was performed.

Read-only validation helpers initially used assumptions about differing synthetic journey JSON shapes and Python module loading that were corrected without product or evidence mutation. Completed independent checks, rather than those interrupted helper attempts, support the conclusions above. No acceptance fixture or uncertain confirmation was repeated.

## Remaining release gates and allowed next action

Current overall gate is FAIL solely for F1. Execute only the bounded immutable-patch registry/test correction described above, retain this initial report and all frozen evidence, then obtain a fresh independently bound R1 full gate. Existing expensive product/browser acceptance may carry forward only through a specific unchanged-execution-byte bridge; governance checks affected by the correction must run afresh.

After a genuine independent full PASS, the coordinator must fetch and assess current main, stop for material conflict/new regression, stage exact accepted paths with raw-byte preservation, separately bind additive reports/manifests, verify complete committed tree and clean tracked worktree, run canonical committed-state pre-PR checks/checklist, and require PASS before normal push. Actual new push and PR workflows must meet all nine owner-required jobs on the exact remote candidate SHA; historical main CI is not candidate CI.

Remote observations remain preliminary: legacy branch-protection404 coexists with active Protect main ruleset23422674, strict five required contexts, required thread resolution, linear history, no bypass and0 required approval count. These observations do not waive the owner's all-nine-job/both-workflow requirements or unresolved review threads. No PR update, push or merge was authorized by this FAIL. Human owner performs any final merge.

**Next permitted action: bounded governance-only F1 correction and fresh independent R1 review. Full final publication eligibility: BLOCKED. Human merge verdict: NOT READY.**

## Recomputable reviewed read-set

The complete candidate is enumerated by the frozen manifest's674 raw hashes and268 exact proposed publication hashes. The exact source36 map and nine before-owner copies are bound by PR81_RESUME_EVIDENCE_ISOLATION_BINDING.json. Owning production diffs, relevant changed adverse tests, current contract/decision/governance owners, the historical stop/checkpoint and focused/format/stability gates were independently read. The following index binds the final acceptance/protocol/validator inputs; hashes were recomputed from local bytes before this report was written.

| Input | Raw SHA256 |
| --- | --- |
| .ai-pipeline/reports/PR81_RESUME_FINAL_PUBLICATION_MANIFEST.json | 702121db2777150430133625518cb01f286b54814e161facc4468085acdadc32 |
| .ai-pipeline/reports/PR81_RESUME_EVIDENCE_ISOLATION_BINDING.json | 398a3358ad2721d166ab20cbbf953be5a628838ea5d144cd55823071a8858c14 |
| .ai-pipeline/reports/PR81_RESUME_EVIDENCE_ISOLATION_INDEPENDENT_GATE.md | d90c300f4333b9d14853a21fe066594fea4545043df069d6c2803917d5444f19 |
| .ai-pipeline/reports/PR81_RESUME_EVIDENCE_ASSERTION_CONTINUITY.json | 83a86a62fdd5170ea6da7b227479c08ea9f853636024648bd2ba4c1342dabd7c |
| .ai-pipeline/reports/PR81_RESUME_EVIDENCE_ISOLATION_CHECKS.json | 10585654a53941559208ac6faf2f6d6869157bba4e10e1a954fd6859021eec69 |
| .ai-pipeline/reports/PR81_RESUME_EVIDENCE_ISOLATION_CHECKS_FINAL.json | eba261a1d3cf6f6a2d365e60725fb1e38bbfe02c5c9c68ad9e04ff5dc7607998 |
| .ai-pipeline/reports/PR81_RESUME_EVIDENCE_ISOLATION_RED.json | 3c9ae4f96c483415bf197d67bdfe2f7e82bbe03689a5a8cf65cc359bf81c3acc |
| .ai-pipeline/reports/PR81_RESUME_BROWSER_ACCEPTANCE_PROTOCOL.json | 81ccf8cd897cbacf1a5a722792b94753c6af9e47490f530461f839ca141e028c |
| .ai-pipeline/reports/PR81_RESUME_BROWSER_INVENTORY.json | 33ed5f68555e4a9cdd1a4cec942ea433fa028155491b02bd1ffec0ba4a74156f |
| .ai-pipeline/reports/PR81_RESUME_BROWSER_SHARD_1.json | 6334cc8fd495f6f9121a2fd50077922452c62d9e6c5a416f26df3ae02f8ca703 |
| .ai-pipeline/reports/PR81_RESUME_BROWSER_SHARD_2.json | 7f607404b8d31d4333638a8c6e43e92f44bb028c8f10e081abbb3d5c9a06f566 |
| .ai-pipeline/reports/PR81_RESUME_BROWSER_FINAL_EVIDENCE.json | 31f14fec5cdb85b89b51e6c1f7ff1ba16b316f864a5d49aef8c162b046754707 |
| .ai-pipeline/reports/PR81_RESUME_FULL_SUITE_MEASUREMENTS.json | cd04a7d1be9553599c7c707bede0c14ff7407904ed16e4c264a955e541e545b4 |
| .ai-pipeline/reports/PR81_RESUME_OWNED_CLEANUP.json | e4b11e1424b87750bc117c31f1fd13bcfa2cfcf82dc1b8ad9202869b351aa578 |
| .ai-pipeline/reports/PR81_RESUME_FINAL_REVIEW_HANDOFF.md | 673d7a19d9a3205439a6e6debab0d3dd2f0dfefe537f10a538359f76706bd69c |
| .ai-pipeline/reports/PR81_RESUME_PUBLICATION_PR_BODY.md | 0aba77103d7f624ed5c218392613436e7591c068bfceceabe99d4ea0b533c12f |
| .ai-pipeline/reports/PR81_TCP_V61_PRESERVATION_START.json | bb3a2d9f0293e5dc8bbf1c68c0504a1ce67be797cfe771e2e5464714d7494210 |
| .ai-pipeline/reports/PR81_FINAL_HTTP_FULL_BACKEND_FINAL.json | a5378894650b51bcfbec4c336d67547a149ddecd310aae875d4385d6ad01ecee |
| .ai-pipeline/reports/PR81_FINAL_HTTP_PHYSICAL_ACCEPTANCE.json | 733a8f0a8949215187cdc6d72bd803a835e9aab820f5a41deba6173eb6f6d330 |
| .ai-pipeline/reports/PR81_FINAL_HTTP_WINDOW_RECEIPT.json | 631dc54c4f38d5321f331ec774b69b0aff9d8e1fe044709a06bc87c72d94e05c |
| .ai-pipeline/reports/PR81_FINAL_HTTP_FORMAT_INDEPENDENT_GATE.md | de7e77617d7b3a891652c8d7ed8870de198c4967748bfd17ea0ea1fc6e970376 |
| .ai-pipeline/reports/PR81_FINAL_HTTP_STABILITY_INDEPENDENT_ASSESSMENT.md | 3d12d3c89e46b206ba79fba4332336dd73e58e6f016b805255f036318b2fad66 |
| .ai-pipeline/reports/PR81_TCP_V61_DIFF.txt | ee7603a84a59648b769e24124802f8b05458fa632a6a69a4eff4f838c9bf711e |
| .ai-pipeline/reports/PR81_TCP_V6_HELPER_DIFF.txt | 4a107bbf6e77d4d28a700ac112df17b36002c2f7b05a8c7960053d377251295f |
| tmp/pr81-resume-collect-browser-evidence.py | aa64486c8101c93530d5db847d9867ff003b670716b650d360a14fec00d8613d |
| tmp/pr81-resume-preserve-full-suite-measurements.py | ee7c6edb4c547d3993ee690bee2a2b2d442cf114bb1ea95930d8d7bf41b3a981 |
| tmp/pr81-resume-browser-acceptance.py | f0bdec9bf0ede0c6bce4b5abb14772823b3de9d8c9d3cfa23237c1dc1aff43f6 |
| scripts/pre_pr_check.py | 854c909e71942c0ce81ce72d57a381384327eea870ca5cf99fbee41e37db339f |
| tests/test_pre_pr_check.py | 45bbd0b32aa5592b87b7d4ba40101907759919af1c7240e0e3b64f08c40776a1 |
| .gitattributes | d05c12bd6b01f93474ff48c7e66f5e8faa054dd13ea973d5e1f1ff4ef2484564 |

Exact source36 owners (all individually raw-hash checked against the manifest):

- .github/workflows/ci.yml — 09e1f4702f520d48e89e6bb91684d58ca8beba40900755164ace44801085a766
- apps/backend/app/api_models.py — 15d6b9f08112eed9055e6f94aa863f129446221e263af74c99976d50950e0923
- apps/backend/app/main.py — a45be7fc76c667136a601812d0d02b9cd5793605f1a4f4e55250886b8b7a1a58
- apps/backend/app/services/zero_touch_orchestration.py — f97556ae259bf7aeabedb6d08ff96b8c21f2b91cec69bf707023328c994ee411
- apps/backend/tests/test_document_refresh_recovery.py — 35171d0dcbad271e822c23562ffcbb21482ae5aff5938ae181a5f239a07b2578
- apps/backend/tests/test_final_review_editing_real_mongo.py — ac8106f4e387e790114787221306c16bae9eeb482be3398609a4be7182de266c
- apps/backend/tests/test_http_seed_response_completion.py — 44da4c56a85229be30f39b88e1fb0ca78fe7f51df61890a8cc6c0069dad0adbf
- apps/frontend/e2e/authenticated-zero-touch.e2e.ts — 45735ee4b86c6cd55718e5529a36d53ae8c46f7b5fda622e8ba32d1db22e7ff0
- apps/frontend/e2e/blocker-review-performance.e2e.ts — e978692927d25b67c30356921193efb8c9a9edfcc3ba69e21b0109c4976a0789
- apps/frontend/e2e/blocker-simulation.e2e.ts — c4ba5721051d0a140ec10c56598e6c56af7c3240fae27fe58e12545afcec0817
- apps/frontend/e2e/phase24c-policy.e2e.ts — 397677bd0e5206d497f3cbbfce380f8d08ba3628700115d8b208552740ce5bb3
- apps/frontend/e2e/s3-sandbox-submission.e2e.ts — cbf790d5df7207e3ec43014bdb03ab4da5b9cee7e873b26a6f149d49a89872a5
- apps/frontend/e2e/sponsor-demo-journeys.e2e.ts — 3a5b3dfc7e189fb7e2d8d2f111c3d82124ba7005d6dd83d433a256bf41a12c23
- apps/frontend/e2e/stage-disclosures.ts — fda8a2421bbe6f7c9140bea57353f6a6984c9b2990e7b6c06519b3e13df76b58
- apps/frontend/e2e/zero-touch-exception.e2e.ts — 256fa3844f119859e8d6558c9c721779de8f8b296f3a284d2024f07cf9f33ef7
- apps/frontend/evidence-tests/output-isolation.evidence.ts — 09191b4cf72e45631e2dd3bd97416c85cfa3bb5cabe01392697bd51cdd196de0
- apps/frontend/playwright.config.ts — 566653a56dc234f51016e278a738e0377eb29e1bd1ecf7faa7b14184e5e74a03
- apps/frontend/playwright.evidence.config.ts — efa9ba599696b942760984bd3b573adc1426a044faa8254f798b5f911e5ad088
- apps/frontend/src/App.tsx — 486631624f6e1ea8a6aa3bbb7c5bc4117b23957f11f5f24cfd8f0fd9f156bab3
- apps/frontend/src/DemoPerformance.test.tsx — 6472cd41c6a5ba3f99b51184bd415e9ec4ac8c510eb3794bcc3ac3079258cedb
- apps/frontend/src/ResumeDocumentRecovery.test.ts — 6c891c932ec6a06fcb363b37c1a5dec7d02e93ae383d8dc19d89469f9ff6a53d
- apps/frontend/src/api.ts — 6fec47d7215fdd5b256052ac942e8419afdf92b37dc2e7076643c5cd10e957e5
- apps/frontend/src/pages/CaseDetail.tsx — 259a28976f37beca416034b4af2efa82579e5d1c0222168fefee80edb1d1253c
- apps/frontend/src/pages/DocumentEvidencePanel.test.tsx — 622f50223bd668622374d2917ef092d00cd09e241bbb18c0cd922aa01b42fbba
- apps/frontend/src/pages/DocumentEvidencePanel.tsx — 474ede49c581c01b6b904b457356b5011ebee8573a51c2467ae4947553ea5941
- apps/frontend/src/pages/OnboardingWorkspace.tsx — f04b24ae131bb941209c38bd18d53285a46deb0f2cbdf7effb3c395ddb65a21f
- apps/frontend/src/pages/S1PipelineWorkspace.test.tsx — 45db6bd50dd8f6c86aa777df22050d286e79bb35b1122fbddd8961700a720139
- apps/frontend/src/types.ts — b2141cfb5068dfecb30707f79aeec0635254ed6e10d925a3aaea2197ad61119e
- docs/contracts/MULTI_DOCUMENT_INTAKE_PROFILE.md — 203ad8dfa7e4489c7a236d88f12119734810620be6e2499f97bc414331dd43c8
- docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md — 3fbf91c9641ef3382c7141901be1d786590260933ff7926101410fd364000c07
- scripts/e2e_backend_server.py — 2485c7f9f979f92b36c2cc789c0fec0f156cea71d9fbd5576dcecea0c272d981
- scripts/run_e2e.py — 1ca9ee2fc8dfa82aaf2156b7ddc4c9d8b901e99043c31890218cfb732eb1ee70
- scripts/seed_phase13_demo.py — b2c225009ae050a003f14ff4309c949a442edb0705b7e92b1faff69c4b599223
- scripts/slice_c_recovery_fixture.py — e0dde54dd34c999f3309ae481e4b09e88d0532911af32d32af3727bec27984c9
- tests/test_run_e2e.py — baa4bcb320d762ca593a72c08377d61e2a7e1f2c59d203f8f63db92a1511b39f
- tests/test_slice_c_e2e_fixture_routing.py — 219370b0a4547ce8881d4eef7bd9af5bcefa217d4ea4575cc3e2329b9cf390d9

Report created UTC: 2026-10-11T10:53:18.248021+00:00.
