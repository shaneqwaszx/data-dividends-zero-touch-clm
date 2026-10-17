# Document/Reconciliation Wave 3 — final independent release re-gate

## 1. Independent result, identity and authority

**PASS — the exact frozen 18-path candidate satisfies the local release Quality Gate. No required correction remains. Publication authorization is pending.**

Reviewer: Codex `/root`, fresh independent Principal Technical Quality Gate and Release Evidence Reviewer in this chat. This reviewer did not implement the candidate, perform either preceding Quality Gate/corrective cycle, or conduct the HTTP 500 investigation. No subagent supplied this verdict. Owner authority permits one read-only re-gate, this new report and task-owned ignored audit files; it permits no remediation or publication.

Review began **15 October 2026 23:53:01 SGT** (15:53:01 UTC); ninety-minute stop **16 October 2026 01:23:01 SGT**. Original development deadline remains **16 October 2026 05:47:44 SGT**. Corrective budget remains **1/1 exhausted**. Issue time: 16 October 2026 00:06:31 SGT.

This PASS supersedes the old FAIL **only for acceptance of this exact frozen candidate with the newly audited evidence**. Historical failed executions retain their failures and classifications. Ownership/summary HTTP 500 causes remain **UNKNOWN / OPEN**. No repair, harmlessness, inheritance or common cause is claimed. This is bounded local POC acceptance, not hosted-CI success/exception, production reliability certification, Live integration approval or AM18 closure.

## 2. Repository, main and exact frozen source

- Repository: `shaneqwaszx/data-dividends-zero-touch-clm`.
- Worktree: `C:/Users/shane/.codex-clean2/worktrees/am-document-reconciliation-20261015-2147/data-dividends-zero-touch-clm`.
- Branch: `feat/am-document-reconciliation-disclosure-20261015-2147`.
- BASE_SHA / HEAD / merge base / inspected local `origin/main`: **`74da1b139d649c825d127385b3a8651cd9ce6b27`**; base/HEAD tree **`6acb4d5642683f2ebd4f2ea51f494ed248dd1d27`**. No ahead/behind commit delta.
- Read-only GitHub branches/main observation also returned that exact SHA. No fetch, integration or ref mutation occurred; publication must assess main again.
- Separate primary checkout remains on local `main` at `a497793be2615306bc7cfbd3104fd4352dead96d`, with its pre-existing untracked directories preserved. That older local branch is not substituted for `origin/main`.
- Candidate is deliberately **uncommitted HEAD plus all 18 paths below**. HEAD alone identifies neither tested nor reviewed content.
- Frozen manifest SHA256: `8bfb1a0e30a177f72c8b6722502fb434e24f714c9dc82d349b3e2716e5a60dab`.
- Independently recomputed aggregate: **`e6d7aac9230daa80bd8da03c85cab3508e1b980cae0fece25a41d3021874580f`**.

Independently recomputed raw SHA256, CRLF-to-LF SHA256 and native `git hash-object --path=<path> <path>` without `-w` for every record. All 54 individual identity fields match. Aggregate algorithm: SHA256 of UTF-8 compact JSON of ordered records, sorted object keys, separators `(',', ':')`. Native blobs are content predictions, not index/object/commit storage evidence. No source line-ending conversion occurred.

### Complete changed-file inventory and identities

All 18 paths are approved. Seventeen tracked changes comprise **five runtime presentation/style owners, four unit-test owners and eight browser-test owners**; the eighteenth is the untracked integration document. Runtime files/document are **INTENDED**; tests **SUPPORTING**; no unexpected candidate path exists. The pre-existing untracked independent FAIL report is separate evidence. This review adds one report.

| Candidate path | Raw SHA256 | LF SHA256 | Native predicted Git blob |
|---|---|---|---|
| `apps/frontend/e2e/am-wave1.e2e.ts` | `e950374b225cc12206fb7b50dc8ccd09175d7bc1062a437b7e9c0ffdc636920f` | `6f0fa83ab7011ab40915a09c470fad1d4f5099bd610fd2c01dc9c4ae1b587a01` | `a5f00746aee4f4b0ca57a893dc637e4658d627df` |
| `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` | `30d2b318cdb263473f31fd6a09d9b490cde1404dc62b1812f2c12c5979eb3f6f` | `cc8889f7611e6524b80b42ff6508ea4ac30a348d7d30cf8c1a6bb73bd238f362` | `137ddd1552562be553ad7436b06adf3faf894b85` |
| `apps/frontend/e2e/blocker-review-performance.e2e.ts` | `09d7f4e1bd4589ac0ccf1abc2441789a610ece94ab5550b5353f5a152de0d780` | `0e697ecfe639fafb158c32776f5f2c9c889968ff2736d9250b2c3a1bf7cb7c37` | `3e447fdd3999bae877ca9c0a52f25cdfa0274bec` |
| `apps/frontend/e2e/garden-happy-path.e2e.ts` | `71711eb62c720d3694f9491d5206c53f8f9fc41e961d40aa9178c29fb07cc4c5` | `7a3b925f0ecaab4be40b921ca9d0bacadb3dc0df9ebedad21c478382ce9b365d` | `d1cc912914b643e8193e8e3da7f9c021977bba39` |
| `apps/frontend/e2e/ownership-document-streamline.e2e.ts` | `c61e8475babcbaa0158f181ba1a57b399d16e17aabf267c509638a1377d826b3` | `2a8acd24ea3bed9758591da816b8189462224dd1834e12c237f9524fec95c5fa` | `4707df5135e2645041b59a7187deeffa59f24d53` |
| `apps/frontend/e2e/phase24-identity.e2e.ts` | `67750bc6479e21eb8820200d915372773edf19be68bf72748541af8cde0fc611` | `1a78a879f6c01689cd852b88d732f452fa43e010d4207fded7e5c2c6ee473106` | `c539f38b3ffc23b2bd2ab20e42990c5d116b2c8c` |
| `apps/frontend/e2e/responsive-layout.e2e.ts` | `6aecae85882d09fbb3bdfe80572bf4f14975514dbf2d2f3f5516c0cde57d41d1` | `a7b429c5b956cbf34dbb74db18e3670c214ac88b3f765e2fdc58264d21e7fde7` | `b3f50e69c310610462dee8a06983210599ec3657` |
| `apps/frontend/e2e/s2-ownership.e2e.ts` | `6c9b02846704398a3385d2b772a35b5a0b7bacdae6d8d5084040b50acd2572c9` | `fa148e630c1e5a73ed09b8be54b15ed5e26a9b2a4139fc9762043b7cc6f84b00` | `5fc275ed0e12b8a785cf6c7f12a1af8922d66780` |
| `apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx` | `53ef52ae5055e9bdb82bcec885a188b46493bf7ee205a4562927b07d704b7a2a` | `5725a9ade02c4c6354dd00473ab9a1b00d8e13ce909556a104b69cc22f67a8d6` | `763a206101473f5acce6a46cbe589b9b8d818977` |
| `apps/frontend/src/pages/BlockerDecisionReview.test.tsx` | `d59e022eee13001ae4b05ca567dc26a587a77fca596c62c00a3a483932dbbf34` | `29b55eb694c63e59ba5885515edc2087d6374b2a1a3a90a8d5c2b5471bf178b9` | `49e8d8c2ce8702da53f8b751544dfb267c7eb9d6` |
| `apps/frontend/src/pages/BlockerDecisionReview.tsx` | `2c5679f458601d9931cdbad1b7730c20a627ff5a0b632a2e2e60afd78cc29629` | `e1bdf376977d7fce5ff5c80bcd00bf7cbdb7f737a947340bb7fc6bf74c66764e` | `0167f9f3b39b424ce96c9b6d80b4949a9c9f965f` |
| `apps/frontend/src/pages/CaseDetail.tsx` | `6466fdd77b6bd99666b3a3fa1bec86e47fb5d5c96df9af9cd714c90b6b73a63d` | `132b4c0265509efe6774b1ec1d0ca566debe53572e31c96839fad1cee431cc5b` | `e0ecf20ec1216ade9e3ae694ef9b6a5d9d1f0a8f` |
| `apps/frontend/src/pages/CaseStatePanels.test.tsx` | `956f6fcf3f54c5dd8e1d291b19bde54076a1408b256a0865a66a9f5555bf6233` | `fd4bc5f4ed881d007e9949512183fd1af734784705ee6a8477244b3f3bafee5d` | `ed2cfaa88a1107b78f3daa8cd716eec0d65f619c` |
| `apps/frontend/src/pages/CaseStatePanels.tsx` | `79287c603422f8710b9e13217482c39a447f2f040b336718c07fab88136aab34` | `a1d8b960bae33a644753e31998792aebfbf2c8d2b3b1a7d2c65fb1b8693683aa` | `7653805a35bdd5bae845fb8a99b6a5df128d0d15` |
| `apps/frontend/src/pages/DocumentEvidencePanel.test.tsx` | `61916655fb4715b81b7db3bc58a7b9d939ac68ca631d10895e12e9d1b8aca0b2` | `a369b3619007d423325f5362b1a1aace8b0981f26dc20ffcfea66250b6611eee` | `fd89d1ebaa801d8e3efd8168573961ec3ebe625a` |
| `apps/frontend/src/pages/DocumentEvidencePanel.tsx` | `ce745936586451888e3c22a625a39228779b66ba0cdfc0c35a2adb1ee2b8a161` | `44a3a715eea0378c0352bb8d7b899e7baf816b0068cd949d9294e6a1680658cf` | `1c40a8dadcc000f77edd43a7760de37dff8748ce` |
| `apps/frontend/src/styles.css` | `88eb8fe21866a48b96f8a67085125360c21ed31a49b4c0579472d75181edff37` | `ccff0ad89754113685d92aa11c234c3b592598d7836908f70050468acc3a30c9` | `96107fbba249c13222a8f1dc9c72527eff5fd101` |
| `docs/integration/AM_DOCUMENT_RECONCILIATION_DISCLOSURE.md` | `ce59acfb6d8d28eb7283a04d9fcc4684a7e04c4ee31535e01e08fd74d242bc65` | `42cfd0524b8faec38ada6b039118dd6022f3a2f1f8999a88aec8477de2711a1b` | `91b2bdfd555b5420586b92ad2751b93aa4363515` |

CaseDetail owns composition/navigation; DocumentEvidencePanel compatible full/Main/More/Technical rendering; CaseStatePanels reconciliation projection; BlockerDecisionReview remains the local batch-draft owner. CSS extends existing containment to passive partitions. All four unit and eight browser deltas were inspected completely: batch binding assertions strengthen, responsive/no-text cases extend, and authorized disclosure consumers adapt without substantive weakening. The integration document accurately records owners, scope, limits and synthetic manual QA.

## 3. Authority read-set and session capability

Read full root/frontend AGENTS, development workflow, branch/merge protocol, skill routing, `fyp-quality-gate`/template, relevant `integration-security-review` checklist, emitted Tier 1 architecture/state sections, PLAN/REMEDIATION/FINAL_HANDOFF, freeze manifests, original/subsequent FAIL report, full forensic handoff, failed/passing native logs, discovery/inventories, instrumentation and cleanup receipts. Read PR88 `PROGRESSIVE_DISCLOSURE_FOUNDATION.md`, PR90 `AM_SEARCH_REGISTRY_DISCLOSURE.md` and accepted release re-gate for preservation duties, not transferred acceptance. Reviewed IDP review/field, intake/reconciliation contracts, ADR-011/D-071 and Q-003/Q-013/Q-014/Q-015 limits.

Ran `python scripts/dev_context.py --change-class FRONTEND_UI --change-class CI_TOOLING`. FRONTEND_UI describes maintained candidate; CI_TOOLING was conservatively included for runner/observation scrutiny. No maintained runner/config/tooling change or new shared-cache/backend/persistence/provider change class is introduced.

Actually exercised PowerShell/Git, Python 3.12.10, Node 22.23.3, installed Vitest 3.2.4, configured Playwright JSON discovery and read-only Windows/Docker/GitHub queries. Preserved real Chromium/HTTP execution was audited, not rerun. Initial sandboxed Git status was unavailable; narrow approved worktree access resolved it. No `.env`, confidential sponsor artefact, raw customer document, protected Mongo DB or credential was accessed. No database connection or application/browser service was started here.

## 4. F-01 / F-02 / F-03 dispositions

| Finding | Independent disposition | Evidence |
|---|---|---|
| F-01: dangling field heading ID | **CLOSED** | Shared headingId supplies aria-labelledby and corresponding full/Main/More heading across current/history. Preserved RED: 1 failure/19 passes; GREEN 20 passes. Fresh143-test owner run includes all labelled-field checks. |
| F-02: obsolete whole-stage assumptions | **CLOSED** | Garden preserves three arrival/inspection checkpoints with visible Main/closed support. Phase 24 retains >=4.5 default/hover/focus contrast and native Enter/Space on both summaries. Performance replaces only obsolete pre-measurement collapse; exact pipeline/focus/unobscured/timing guards remain. All authorized consumers run in current complete campaign. |
| F-03: missing complete successful browser and cleanup evidence | **CLOSED for this candidate** | Current discovery equals complete disjoint 54/53;77+59=136 actual PASS, both native 0, no assertion/safety weakening. Creation-aware/database/port cleanup adequate. Historical campaigns remain FAIL. |

F-03 was a complete-verification blocker, not an established frontend root-cause finding. Its evidence closure does not close historical incidents. No new mandatory source/contract/security/safety defect was found.

## 5. Complete canonical browser audit

Fresh discovery used installed Node and `@playwright/test/cli.js test --config playwright.config.ts --list --reporter=json` with canonical sanitized base environment/configuration. Native0; no application/browser launch. Derived **107 unique selectors /136 expected passing Chromium records**. File/line/column/title/project/tags and all fixture maps equal corrected/forensic discovery, including each shard's internal discovery. Ordered-stride partitions are complete and disjoint.

For every selector, matched actual per-selector native log to discovery by file/line/column/full title including tags. Checked record ordinal/total sequences, declared Running count, passing summaries, native exit, sequential ports, fixture arguments,60-second limit, stopped processes, guarded lifecycle PASS and whole-suite PASS. Full shard logs reconcile to the same records. **Zero failures, skipped/flaky/retried records, duplicate/extra records or undispatched selectors.** This is execution evidence, not coordinator arithmetic.

| Shard | Selectors passed/discovered | Actual records PASS | Native exit | Total seconds | Slowest lifecycle seconds | Physical cleanup markers |
|---|---|---|---|---|---|---|
| 1/2 | 54/54 | 77 | 0 | 756.062 | 56.297 | 7 |
| 2/2 | 53/53 | 59 | 0 | 656.172 | 53.515 | 6 |

S1 completed 15 October 2026 23:15:29 SGT; S2 at 23:30:32 SGT. Calls: original `run_isolated_suite(backend_port=9800,frontend_port=4800,timeout_seconds=60,headed=False,diagnostics=False,shard=(1,2))`, then `(9900,4900,...,shard=(2,2))`, once each through ignored observational entry point. Attempt-start guards prevent automatic reuse/retries. No new full frontend/browser campaign occurred here.

| Shard | Complete log SHA256 | Per-selector receipt SHA256 | Native terminal receipt SHA256 |
|---|---|---|---|
| 1/2 | `e325de07731a23927a9578d72c054807e2ecf3f76f547832de99abaddb873dc5` | `1bbe51c4199372e10d2edabcfad7ac2e8b52f989709af2581b93cd9096b6dc59` | `2a7f4fc788a4a1b856fdea08dfdddf5fd66cf3b338f08414bdd519c031644c5f` |
| 2/2 | `afba77f15fc20d9e9bcb4e5115e124c2d8b4d59952f90a3b60f0fc0311fb1945` | `85c957a91f3b27b07b702aa516d571ffe95a99d63a283f43d2764a6529a339c0` | `ce684020df26c46ac7d4c8f29da166ace5a5160c83884982f75aebe290fb7900` |

Raw checks around each of 107 lifecycles and preserved freeze/source snapshots bind both runs to the same candidate. Independently rehashed **335 execution-source files**, **89 historical files**, six explicit UAT PDF fixtures and 17 static backend/runner/proxy/config owners. All match; static owners LF-equivalent to base. No campaign test body, fixture, assertion or safety change. These operational receipts do not provide a retroactive filesystem lock or proof against hypothetical unrecorded edits/reversions.

Expanded136 actual identities, fixture maps, every per-selector hash and arguments are in ignored `tmp/am-document-reconciliation-disclosure/release-regate/browser-reconciliation.json`; section 14 lists all 107 selectors/counts.

## 6. Observational instrumentation equivalence

Reviewed actual four primary observers and canonical runner/server/config, not just summaries. Final observer and supplemental-tool hashes match; initial adaptation provenance hashes are distinct and not substituted.

| Observer | Current preserved executed SHA256 |
|---|---|
| `backend-observer.py` | `b8d8c379ed8f0f78440b3513dbe92f31ad3c768a10ef3afc005203043694ddb8` |
| `proxy-observer.cjs` | `7aaabe92a917f979ba5598299c98f89577ff62ddaceda5d90c6c53cc6c6b5f5b` |
| `client-observer.cjs` | `44316818b9142fa10a24bb3a27a863e44769f5e17505ba2940933b97af04e7d2` |
| `run-campaign.py` | `edea0fb2ad6fdc2d90bc1d21c565a498b0551d0e2b06b8be169c2eb9f7f3efbb` |
| `process-tree-observer-v2.py` | `57b7c69db77d84b6bfc1a243ef0cd4943ae52d7a5899c46ad5c0c58aa06d4454` |

Wrapper calls original run_isolated_suite/run, preserves returned result and canonical exception/finally cleanup. OutputCapture adds metadata persistence with the original bounded drain. Backend runs original server and delegates uvicorn/ASGI/endpoint/projection, awaits original send, rethrows original exceptions. Proxy delegates original HTTP request/event functions and returns the original request. Client calls original Playwright methods, returning original response/rethrowing errors. No body/status/result substitution, response rewriting, correlation header, fault injection, target operation, retry, application sleep, timeout inflation or synthetic success was found.

Equivalence concerns source/assertion/fixture/authority/deadline semantics. Observation adds synchronous output, wrappers, a promise continuation and sampling overhead: **identical scheduling and non-interference with an intermittent race are not proved**. That limit remains material to historical causation.

Unchanged: one headless Chromium worker, retries 0, original test/expect polling subordinate to **60-second whole lifecycle**, discovery deadline and derived **9780/9600-second** outer budgets, per-selector processes, strict loopback ports, original guarded networking/known-font neutralization, blocked service workers/downloads, disabled automatic trace/video/screenshots, ephemeral auth and fail-closed cleanup. Memory/Mock/LOCAL, Garden, registry/recovery and offline synthetic Sandbox/database/sponsor fixture maps match discovery. Task-only Mongo port/Tesseract PATH/UTF8 and observational preloads are disclosed environment differences. Synthetic Sandbox tests do not prove external provider writes.

## 7. Document/Reconciliation behavioral acceptance

| Acceptance area | Independent disposition and support |
|---|---|
| Persistent Main; all required work | **PASS.** Existing persistent composition holds upload, intended count/intake completion, current readiness/status, review, source comparisons, batch Confirm, checkpoint repair, replacement/retry/recovery outside optional support. Predicates, IDs, callbacks, disabled/error/frozen/denied states retained. No required correction needs More/Technical. |
| Required warnings and ambiguous values | **PASS.** Main retains six reconciliation outcome counts/comparisons, no-default-source/replacement/no-action warnings. Pending candidate values are plain Main sections. Missing, low-score, unavailable and conflict stay distinct. Actual no-text record/component checks retain retry/replacement and prohibit fabricated acceptance. |
| More details | **PASS.** Supporting observations/completed reviews/notes and clearly labelled superseded history are passive. Current support cards avoid actionable-card selectors; historical cards have no mutation controls. Authenticated history/replacement and S2 proposal consumers pass with explicit support opening. |
| Technical details | **PASS.** Safe method/quality/score/formula, page/source references, versions/events, lineage/original UTC timestamps and reconciliation provenance projected explicitly, including after checkpoint. No nested Technical or business inputs. No raw document/provider body/private exception. |
| Exact choices/current requests | **PASS.** No default source/decision; only backend-allowed source actions. Confirm reads current automation/case-event/reconciliation versions, document fingerprint/event count and discrepancy fingerprint. Current AM-wave1:163 strengthens exact request assertions and passes. |
| Bulk draft and explicit confirmation | **PASS.** Eligible undecided document fields only; choices/corrections/notes/explicit source choices preserved. Missing suggestions cannot be accepted; low/missing originals retain replacement warnings. Change/save/clear/bulk call no confirmation. Complete explicit authorized Confirm uses existing one-family batch API; no auto-acceptance or Send. |
| Refresh retention/evidence replacement | **PASS.** Stage identity is actor/case/role/team, never summary.version/poll time. Unchanged GET/toggles retain draft/optional state. Existing stricter parent batch key still resets on version/events/fingerprints/authority changes. Standalone bindings retire changed/removed document/source choices before render/confirm; source binding includes reconciliation identity/version, fingerprint and allowed actions. |
| Current/history and actor/session/case separation | **PASS.** Superseded evidence excluded from current decisions; source choices require current document IDs/event counts. AuthProvider session-generation remount, actor/case/role/team keys and guarded actions retained. Existing isolation/currentness/late-response/deletion/session records run. No cache owner or browser storage added. |
| Names, keyboard, contrast and focus | **PASS.** F-01 names resolve; independent native summaries preserve Enter/Space/Tab/visible focus. Phase 24 retains >=4.5 contrast default/hover/focus. Attention/pipeline/PR87 deliberate-focus guards and anchors unchanged; Garden arrival and pipeline corrective-focus records pass. |
| Responsive layout | **PASS within configured evidence.** Current selector checks Main/support at 1440/1280/900/360 px, containment, draft retention/zero writes. Original Garden 320/360/768/1280/1440/1920 and 200% CSS zoom/width assertions pass unchanged. Garden does not separately establish every Technical state at 200%; no broader claim. |
| No inspection mutation or target replay | **PASS.** Optional partitions lack business inputs/handlers; disclosure/focus/navigation/print retain existing presentation owners. Current browser assertions preserve zero unsafe-method writes, separate deliberate target confirmation and original ordering/stopping/recovery/no-replay. |
| Compatibility/authority | **PASS.** Legacy full defaults retained. No source precedence, extraction algorithm, backend/API contract, provider classification or approval change. Mock/Local and provisional labels retained; no Live/compliance/final approval claim. |

Direct current records: authenticated-zero-touch:244/:1269; am-wave1:163; responsive-layout:440/:740; garden-happy-path:217/:366; phase24-identity:83; blocker-review-performance:140; all original ownership/S2/history/recovery/target-safety consumers. Section 14/expanded audit map each to actual execution. Complete production/test delta inspected; every additional authorized consumer preserves substantive assertions.

## 8. Other verification, governance and security

| Lane | Preserved audit / fresh execution |
|---|---|
| Corrected full frontend | **Preserved PASS 54 files/737 tests, native 0.** Every per-file result independently counted, including root-level ViteHistoryFallback.test.ts; sums exactly 737. Actual remediation-unit-all.log and native receipt inspected. Current corrected manifest/source/history identities match; old 736/15-path evidence not substituted. Not rerun. |
| Typecheck/build | **Preserved native 0 each.** Actual remediation-typecheck/build logs/native receipt inspected on corrected candidate. Existing >500 kB advisory retained, no suppression/error. Not rerun. |
| Existing tooling/governance | **Preserved 122-test OK log.** Bare log lacks exact module arguments; not presented as newly reconstructed inventory. Bytes match historical snapshot and tooling sources unchanged. |
| Fresh identified tooling modules | **137 tests PASS, native 0**, 28.793 s: `python -B -m unittest tests.test_run_e2e tests.test_check_project_state tests.test_check_architecture tests.test_check_tooling_config tests.test_check_policy_authority tests.test_check_external_provider_readiness tests.test_check_secrets`. Current partition/deadline/cleanup/scanner/governance tests pass. Mocked suite-failure line is intentional negative-path output, not a real campaign failure. |
| Fresh frontend owner tests | **143 tests/5 files PASS, native 0**, 5.07 s: installed Vitest run DocumentEvidencePanel, BlockerDecisionReview, CaseStatePanels, EvidenceWorkbenchIsolation and StageDisclosure with `--cache=false`. Existing React act warnings retained. |
| Configured governance/secrets | Fresh check_project_state/check_architecture/check_tooling_config/check_policy_authority/check_external_provider_readiness/check_secrets: **six native 0**; complete outputs retained. |
| Hygiene/identity | Fresh git diff --check passes; integration/new-report Markdown explicitly checked separately. All 18 identities, original evidence and empty index rechecked at closeout. Own ignored evidence supported-pattern scan recorded. |
| Focused authenticated journeys | Preserved review/replacement/history, exact batch, approved proposals, unavailable/available OCR/no-text, responsive, Garden zoom and 3 amended journeys inspected. Relevant scenarios also execute in new complete campaign. Original failures remain failed. |

Full frontend log SHA256 `ce385a2895afe8ecdd6cf1ec6b03b1ad81f3f1c115025d7af017b5f646a68278`; corrected native frontend receipt `b99c46ee5f99413e160262ca85621682d9270e4ec78f995e2114072a1311619a`; preserved 122-test log `f19db0f165dc3093f60253670b7fd2c57424ef510fda53a79c0f71bd72fe3d30`. Corrective records, subsequent independent source review and preserved current hashes bind them to corrected content. Audited preserved execution is distinguished from fresh execution.

Security review found no new trust bypass, unsafe HTML sink, raw body/private exception exposure, credential, permission grant, storage or mutation retry. Authorized API projections remain the boundary; evidence text/filenames use React escaping. Upload validation, backend RBAC/CSRF, in-lock authority, current fingerprints/versions, target freeze/ledger unchanged. Observers retain route/opaque IDs, fixed metadata/status/time and exception class/application frame locations without bodies, auth headers/cookies, exception messages or locals. No confidential/temporary diagnostic path newly tracked/staged. Pattern scanners are not comprehensive confidentiality proof; forensic 15 MB derived analysis.json exceeds 2 MiB limit and remains an explicit size skip. Underlying metadata captures/observer projection inspected.

Existing 6 npm advisories (1 moderate/3 high/2 critical) remain recorded dependency risk; no dependency/lockfile change/new finding is established. No configured frontend lint script; no lint PASS invented. Full backend/persistence suites, external Live checks and human manual QA **NOT_EXECUTED here**; no affected product change/local-gate criterion makes them newly required. Physical Mongo was only canonical fixture prerequisite. Open sponsor production document/source/reviewer/privacy questions remain separate from this authorized POC scope.

## 9. Historical HTTP 500 uncertainty and residual reliability

| Historical failure | Direct preserved sequence | Current classification |
|---|---|---|
| A — Garden ownership | corrected-shard-1.log,17/54 at garden-happy-path:217/helper142: classification200, ownership GET **500** expected200, before viewport/zoom/target confirmation; native 1 | Real frontend-origin historical read failure. Origin/cause **UNKNOWN/OPEN**. New same selector passes unchanged assertions. |
| B — AM18 reuse summary | corrected-shard-2.log,1/53 at am-wave1:124: target-confirmation200 then summary GET **500** polling COMPLETED before second case/manual correction; native 1 | Separately **UNKNOWN/OPEN**. New same selector passes state/target guards. POST200 never proves later GET succeeded. |
| Earlier AM14 ownership | shard-1-final-of-2.log,2/54: ownership POST200 then ownership GET **500** | Separate preserved historical failure. Focused/current complete passes supply no causal closure. |

Old corrected inventory remains **27 PASS/2 FAIL/107 NOT_EXECUTED of 136**. Failed corrected log hashes remain `e95af52c590198fd6a6f7551353012f32881760b01d7f3ab44592f07d87c7b0e` / `a54e33d178dacc539b50f491f36c8d6fd5e48519b2248165ecfc0702e09c139c`. Earlier Garden width failure remains historical, original assertion retained.

Historical capture lacks exact failed request/case correlation, completed-response metadata, contemporary backend/proxy arrival/exception/frame and process/resource state. Original runner prints ordinary assertion failure without persisting backend/frontend capture. Post-stop bounded-tail zero counters are not exoneration. No historical evidence was manufactured.

Independently aggregated all per-selector raw JSONL, including exact frontend-ID lifecycle checks:

| New campaign fact | Observed result | Limit/meaning |
|---|---|---|
| Summary GET |966 frontend arrivals/966 upstream starts;963 ASGI arrivals/ends;940 completed frontend responses:939 x200/1 x404;620 API responses all 200 |404 negative/deletion/access results preserved; unfinished response not called delivered200. |
| Ownership GET |548 frontend arrivals/548 upstream starts;543 ASGI arrivals/ends;480 completed frontend responses:315 x200/165 x404;58 API responses all 200 |No completed ownership GET500; browser-channel counts supplemental, not complete census. |
| ECONNRESET |234 overall; summary23/ownership68 |All 91 target resets match exact unfinished frontend close/no finish;9 summary/3 ownership reused sockets. Reset does not prove historical completed 500 cause. |
| Disconnected intake POST |One ASGI500 attempt and ClientDisconnect at responsive-layout:404 after frontend upload close unfinished; no completed frontend 500 |Distinct POST/body-read event, not GET reproduction. Teardown/cancellation consistent with chronology; initiator/general recurrence unproved. No repair/harmlessness conclusion. |
| Processes/resources |Actual backend-child samples107/107; no sampled unexpected pre-stop backend/frontend exit; memory load91%, minimum available3,057,074,176 bytes |One-second samples do not exclude transients or prove allocation failure/common cause. |
| Runtime difference |Current Pydantic 2.14.1 vs prior PR90 recorded2.13.5 |Earlier runtime equivalence not established; no causal attribution/dependency fix. Both current shards use disclosed current environment. |

No completed frontend case-route500 in new streams. The189 endpoint HTTPExceptions and separate upload ClientDisconnect remain recorded, not hidden by that narrower claim. No target-GET projection exception/backend 500 demonstrated. No common cause links historical errors, resets, upload disconnect, memory pressure or version difference. Source equality cannot prove candidate independence; one clean instrumented pair cannot prove eradication/low recurrence/production reliability.

**Release judgment:** historical read-availability uncertainty is meaningful residual risk and remains open. Current criteria require complete successful original canonical verification on exact candidate, all safety assertions, adequate cleanup and no demonstrated outstanding mandatory defect. F-03 requested that complete evidence while preserving unknown incidents; no causal-proof/repeated-pass/soak/uninstrumented replacement condition was imposed. Newly authorized complete campaign now supplies the missing evidence. Source review and original state/version/target assertions establish no outstanding serious candidate/security/data-integrity/no-replay violation; disconnected POST supplies no failed current required behavior or delivered error. Keeping unexplained historical cause alone as an indefinite mandatory blocker would add a criterion absent from scope. This PASS waives no required check and declares none of the incidents fixed, harmless, inherited or production-safe. Owner must retain separate uncertainties in later release decisions.

## 10. Resource cleanup and preservation

Original container `1d7b758a4fbd54bb477de25d86585fd0f82ade599b729fca6f264e602da6733b` and forensic container `a4f3a218359d76e90750a6407153cf5c50911bf8fb032f32bee6481b543f3dae` independently absent from current Docker inventory. Original receipt records exact identity/binding/no host mounts, zero non-system databases and both anonymous volumes removed. Original individual volume names are not retained there: historical removal is supported by that receipt and preceding independent gate, not a newly invented named-volume check.

Forensic cleanup retains exact ID/name/task label/loopback 27321/mount identities, system-only DBs before removal, native removal and **two exact anonymous volume names**, both independently absent now. All **13 physical-fixture cleanup markers** match the original generated allowlisted DB owner. No protected clm_poc test/connection/cleanup occurred. No database connected to or modified by this reviewer.

PID-only v1 observer misattributed later reused PIDs. Its attribution is explicitly invalidated; no unrelated process was terminated. V1 code/events/check failure preserved. Corrected v2 validates Windows creation times, ran before shard 2 and records empty between-shard/final tree. Independently rechecked **645 birth-identified instances**, including **219 headless_shell.exe descendants**, and **963 canonical root-event identities**: absent/exited or later unrelated PID reuse. One access-denied OpenProcess query resolved through independent Windows CIM snapshot showing PID absent; access denied alone was not absence evidence. No process terminated. Both observer streams end with explicit stop events.

Original Chromium display count 0 matched only chrome. cleanup-counter-audit.json correctly counts 219 headless_shell instances already covered by creation-aware assertions; no cleanup repeated. Sampling began during shard 1; transient unobserved descendants are not individually certified. Per-lifecycle process-group shutdown, complete root checks, creation-aware descendants, empty final tree and released ports together provide adequate cleanup with that limit.

Fresh **323 distinct original/forensic ports bind-free**: frontend 4800–4853/4900–4952; backend 9600–9653/9700–9752/9800–9853/9900–9952; Mongo 27210/27321. No preview/browser/database service started here.

Independent preservation covers **89 historical files**, **335 execution-source files**, six PDF fixtures, all 18 identities, primary/supplemental observer hashes, and pre-existing task evidence captured at review start. Prior report remains SHA256 **`bee573a0e615ac3122fcac3fc6d4db4411c43bec736d6ee27b9ecef9d3dd4d3c`**, including exact original FAIL suffix SHA256 **`6f5631597e4e4a50e098d6145170d14b9ba6b00c54bbcb0116a727e6dbd65a35`**. Forensic handoff remains **`b946b62e813edec5d696c51e3e75c3cf26c85175b42b4d23eea7f0b8238541ce`**. No historical report/manifest/log/receipt overwritten.

Own evidence is ignored `tmp/am-document-reconciliation-disclosure/release-regate/`; sole helper outside it is ignored task-owned release-regate-audit.py. Reviewer-only parser corrections used actual receipt field names (registry_demo/recovery_demo/sandbox_demo), included the root-level frontend test and corroborated the denied PID query with CIM. These audit stops are not product failures/retries; source/results untouched. Windows command-length rejection during report authoring was resolved by bounded write chunks; it did not execute or alter source/evidence.

## 11. Main, PR89 and final write boundary

Read-only [PR89 observations](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/89) show **OPEN**, unmerged, separate head feat/ai-assistant-phase1 at **`badf0c378f2991fc1f8e52e6902706588995a171`**, unchanged between this review's observations. No PR89 code/comment/review write, Git mutation or merge. Shared main/origin/main and primary checkout unchanged.

Index **empty**. Expected final visible state: 17 modified tracked candidate files plus 3 untracked paths (integration document, historical independent report, this new report). All reviewer helpers/evidence ignored. No tracked path added/removed/staged by reviewer. Candidate/worktree intentionally dirty and retained; task clean/repository clean **NO**. No branch/worktree creation/switch/removal/archive.

| Reviewed change surface | Disposition |
|---|---|
| API routes/shared DTO/type contract | **Unchanged**; compatible component-local presentation props/local draft binding type expand. |
| Durable schema/repository/persistence | **Unchanged**. |
| Connector/provider interface/composition | **Unchanged**. |
| Maintained configuration/dependencies/lockfiles | **Unchanged**; observational child-process settings disclosed separately. |
| Business rule/source precedence/IDP algorithm/threshold/mapping | **Unchanged**. |
| Backend auth/security authority/shared cache/session owner | **Unchanged**. |
| Architecture owners/provider status | **Unchanged**; Mock/Local/Partial/Dormant distinct from Live. |
| Runtime behavior | **Frontend presentation/bounded local stale-draft validation changed**, as reviewed; backend/target behavior unchanged. |
| This review's writes | **One assigned new report plus task-owned ignored audits only**; no production/test/remediation changes. |

## 12. Exact verdict and conditional publication

**PASS.** All 18 unchanged candidate paths independently approved; F-01/F-02 remain closed; complete F-03 browser/cleanup evidence satisfied. Behavioral/governance/security/resource checks adequate. No demonstrated outstanding mandatory release blocker. Historical read failures remain open and materially limit reliability confidence. Evidence grade **B** for bounded local acceptance; historical causal confidence **C/UNKNOWN**.

**Conditional publication may be considered by the owner/planner; it is not authorized by this report or assignment.** Missing next-stage authority is explicit owner authorization. Later publisher must verify unchanged accepted content, latest main, scoped committed/clean pre-PR evidence, applicable CI/current-head review and human merge boundary under repository workflow. No hosted-CI exception. No missing local-gate evidence requires another campaign here; further causal work/remediation needs separate assignment. Budget not reset. Ownership/UBO disclosure or any other phase not begun.

Readiness: frozen local candidate **ACCEPTED**; actual PR/publication **PENDING OWNER AUTHORIZATION AND ITS OWN GATES**; Live ACRA/GoldTier, production compliance/final approval **NOT ESTABLISHED**. No staging, commit, push, PR creation, merge or pre_pr_check. Stop and return report.

**DOCUMENT/RECONCILIATION RELEASE RE-GATE: PASS — FROZEN CANDIDATE ACCEPTED; PUBLICATION AUTHORIZATION PENDING.**

## 13. Review receipts and closeout

- release-regate/identities.json: all raw/LF/native records, complete paths, preserved source/fixture/observer hashes.
- current-discovery.json/browser-reconciliation.json: fresh discovery and 136 actual identities, original fixture modes, each native log hash/arguments.
- telemetry.json/resource-audit.json/process-snapshot.json: independent raw-stream and read-only creation-aware resource checks.
- focused-unit.log/receipt and tooling-unit.log/receipt: fresh 143 frontend/137 tooling tests, native 0.
- full-unit-count-audit.json/governance.json/supplemental-audit.json:737 row-count reconciliation, fresh configured checks/GitHub boundaries.
- start.json/final-preservation.json: before/after evidence/source preservation, explicit new Markdown hygiene, supported-pattern scan, index/status/report identity. Final receipt written after report verification.

Boundary held: existing owners and exact source/fixture/assertion semantics; no speculative HTTP fix or new acceptance criterion. Complexity control: no review-time product complexity added; legacy full rendering retained for existing consumers, retirement requiring separately scoped migration. Integration documentation is current for candidate; historical state/reports preserved rather than rewritten as merged truth. Next useful verification, if separately assigned, is correlated historical causation; it is not silently imposed as a new local-gate condition.

## 14. Complete 107-selector/136-record outcome inventory

Every row has actual canonical log/native receipt independently matched to current discovery. Expanded titles/line/column/tags and hashes retained in browser-reconciliation.json. Rows sum **54/77** and **53/59**, zero failures/skips/retries/undispatched records.

| Shard/ordinal | Current selector | Actual records | Result/native exit |
|---|---|---|---|
| 1/1 | `e2e/am-wave1.e2e.ts:120` | 1 | PASS/0 |
| 1/2 | `e2e/am-wave1.e2e.ts:128` | 1 | PASS/0 |
| 1/3 | `e2e/authenticated-zero-touch.e2e.ts:232` | 1 | PASS/0 |
| 1/4 | `e2e/authenticated-zero-touch.e2e.ts:652` | 1 | PASS/0 |
| 1/5 | `e2e/authenticated-zero-touch.e2e.ts:785` | 1 | PASS/0 |
| 1/6 | `e2e/authenticated-zero-touch.e2e.ts:941` | 1 | PASS/0 |
| 1/7 | `e2e/authenticated-zero-touch.e2e.ts:1223` | 1 | PASS/0 |
| 1/8 | `e2e/authenticated-zero-touch.e2e.ts:1418` | 1 | PASS/0 |
| 1/9 | `e2e/authenticated-zero-touch.e2e.ts:1660` | 1 | PASS/0 |
| 1/10 | `e2e/blocker-review-performance.e2e.ts:144` | 1 | PASS/0 |
| 1/11 | `e2e/blocker-simulation.e2e.ts:25` | 10 | PASS/0 |
| 1/12 | `e2e/blocker-simulation.e2e.ts:133` | 3 | PASS/0 |
| 1/13 | `e2e/blocker-simulation.e2e.ts:233` | 1 | PASS/0 |
| 1/14 | `e2e/blocker-simulation.e2e.ts:414` | 1 | PASS/0 |
| 1/15 | `e2e/database-classification.e2e.ts:97` | 1 | PASS/0 |
| 1/16 | `e2e/database-classification.e2e.ts:101` | 1 | PASS/0 |
| 1/17 | `e2e/garden-happy-path.e2e.ts:217` | 1 | PASS/0 |
| 1/18 | `e2e/garden-happy-path.e2e.ts:315` | 1 | PASS/0 |
| 1/19 | `e2e/garden-uen-partial-resume.e2e.ts:21` | 2 | PASS/0 |
| 1/20 | `e2e/ownership-document-streamline.e2e.ts:14` | 1 | PASS/0 |
| 1/21 | `e2e/ownership-document-streamline.e2e.ts:156` | 2 | PASS/0 |
| 1/22 | `e2e/performance-browser.e2e.ts:97` | 1 | PASS/0 |
| 1/23 | `e2e/phase24-identity.e2e.ts:83` | 1 | PASS/0 |
| 1/24 | `e2e/phase24-identity.e2e.ts:165` | 2 | PASS/0 |
| 1/25 | `e2e/phase24c-policy.e2e.ts:79` | 1 | PASS/0 |
| 1/26 | `e2e/responsive-layout.e2e.ts:347` | 1 | PASS/0 |
| 1/27 | `e2e/responsive-layout.e2e.ts:440` | 1 | PASS/0 |
| 1/28 | `e2e/responsive-layout.e2e.ts:542` | 1 | PASS/0 |
| 1/29 | `e2e/responsive-layout.e2e.ts:575` | 1 | PASS/0 |
| 1/30 | `e2e/s1-workspace-session.e2e.ts:93` | 1 | PASS/0 |
| 1/31 | `e2e/s1-workspace-session.e2e.ts:186` | 1 | PASS/0 |
| 1/32 | `e2e/s2-ownership.e2e.ts:55` | 1 | PASS/0 |
| 1/33 | `e2e/s2-ownership.e2e.ts:254` | 6 | PASS/0 |
| 1/34 | `e2e/s3-sandbox-submission.e2e.ts:251` | 1 | PASS/0 |
| 1/35 | `e2e/s3-sandbox-submission.e2e.ts:257` | 1 | PASS/0 |
| 1/36 | `e2e/s3-sandbox-submission.e2e.ts:379` | 1 | PASS/0 |
| 1/37 | `e2e/s3-sandbox-submission.e2e.ts:452` | 1 | PASS/0 |
| 1/38 | `e2e/s3-sandbox-submission.e2e.ts:468` | 1 | PASS/0 |
| 1/39 | `e2e/slice-b-registry-demo.e2e.ts:120` | 1 | PASS/0 |
| 1/40 | `e2e/slice-b-registry-demo.e2e.ts:163` | 1 | PASS/0 |
| 1/41 | `e2e/slice-c-recovery.e2e.ts:122` | 1 | PASS/0 |
| 1/42 | `e2e/slice-c-recovery.e2e.ts:165` | 1 | PASS/0 |
| 1/43 | `e2e/slice-c-recovery.e2e.ts:270` | 1 | PASS/0 |
| 1/44 | `e2e/slice-c-recovery.e2e.ts:276` | 1 | PASS/0 |
| 1/45 | `e2e/slice-c-recovery.e2e.ts:303` | 1 | PASS/0 |
| 1/46 | `e2e/slice-e-policy.e2e.ts:64` | 1 | PASS/0 |
| 1/47 | `e2e/sponsor-demo-journeys.e2e.ts:317` | 1 | PASS/0 |
| 1/48 | `e2e/sponsor-demo-journeys.e2e.ts:319` | 1 | PASS/0 |
| 1/49 | `e2e/sponsor-demo-journeys.e2e.ts:321` | 1 | PASS/0 |
| 1/50 | `e2e/sponsor-demo-journeys.e2e.ts:323` | 1 | PASS/0 |
| 1/51 | `e2e/synthetic-company-pack.e2e.ts:22` | 4 | PASS/0 |
| 1/52 | `e2e/ux-refinement.e2e.ts:94` | 1 | PASS/0 |
| 1/53 | `e2e/ux-refinement.e2e.ts:188` | 1 | PASS/0 |
| 1/54 | `e2e/zero-touch-exception.e2e.ts:161` | 2 | PASS/0 |
| 2/1 | `e2e/am-wave1.e2e.ts:124` | 1 | PASS/0 |
| 2/2 | `e2e/am-wave1.e2e.ts:163` | 1 | PASS/0 |
| 2/3 | `e2e/authenticated-zero-touch.e2e.ts:244` | 1 | PASS/0 |
| 2/4 | `e2e/authenticated-zero-touch.e2e.ts:694` | 1 | PASS/0 |
| 2/5 | `e2e/authenticated-zero-touch.e2e.ts:851` | 1 | PASS/0 |
| 2/6 | `e2e/authenticated-zero-touch.e2e.ts:1029` | 1 | PASS/0 |
| 2/7 | `e2e/authenticated-zero-touch.e2e.ts:1269` | 1 | PASS/0 |
| 2/8 | `e2e/authenticated-zero-touch.e2e.ts:1548` | 1 | PASS/0 |
| 2/9 | `e2e/blocker-review-performance.e2e.ts:140` | 1 | PASS/0 |
| 2/10 | `e2e/blocker-review-performance.e2e.ts:148` | 1 | PASS/0 |
| 2/11 | `e2e/blocker-simulation.e2e.ts:85` | 1 | PASS/0 |
| 2/12 | `e2e/blocker-simulation.e2e.ts:178` | 1 | PASS/0 |
| 2/13 | `e2e/blocker-simulation.e2e.ts:382` | 1 | PASS/0 |
| 2/14 | `e2e/database-classification.e2e.ts:96` | 1 | PASS/0 |
| 2/15 | `e2e/database-classification.e2e.ts:98` | 1 | PASS/0 |
| 2/16 | `e2e/garden-happy-path.e2e.ts:157` | 1 | PASS/0 |
| 2/17 | `e2e/garden-happy-path.e2e.ts:301` | 1 | PASS/0 |
| 2/18 | `e2e/garden-happy-path.e2e.ts:366` | 1 | PASS/0 |
| 2/19 | `e2e/onboarding-recovery.e2e.ts:7` | 1 | PASS/0 |
| 2/20 | `e2e/ownership-document-streamline.e2e.ts:77` | 1 | PASS/0 |
| 2/21 | `e2e/ownership-document-streamline.e2e.ts:229` | 1 | PASS/0 |
| 2/22 | `e2e/performance-browser.e2e.ts:98` | 1 | PASS/0 |
| 2/23 | `e2e/phase24-identity.e2e.ts:146` | 1 | PASS/0 |
| 2/24 | `e2e/phase24c-policy.e2e.ts:34` | 6 | PASS/0 |
| 2/25 | `e2e/responsive-layout.e2e.ts:308` | 1 | PASS/0 |
| 2/26 | `e2e/responsive-layout.e2e.ts:404` | 1 | PASS/0 |
| 2/27 | `e2e/responsive-layout.e2e.ts:524` | 1 | PASS/0 |
| 2/28 | `e2e/responsive-layout.e2e.ts:550` | 1 | PASS/0 |
| 2/29 | `e2e/responsive-layout.e2e.ts:740` | 1 | PASS/0 |
| 2/30 | `e2e/s1-workspace-session.e2e.ts:123` | 1 | PASS/0 |
| 2/31 | `e2e/s1-workspace-session.e2e.ts:213` | 1 | PASS/0 |
| 2/32 | `e2e/s2-ownership.e2e.ts:188` | 1 | PASS/0 |
| 2/33 | `e2e/s3-sandbox-submission.e2e.ts:168` | 1 | PASS/0 |
| 2/34 | `e2e/s3-sandbox-submission.e2e.ts:254` | 1 | PASS/0 |
| 2/35 | `e2e/s3-sandbox-submission.e2e.ts:375` | 1 | PASS/0 |
| 2/36 | `e2e/s3-sandbox-submission.e2e.ts:444` | 1 | PASS/0 |
| 2/37 | `e2e/s3-sandbox-submission.e2e.ts:460` | 1 | PASS/0 |
| 2/38 | `e2e/slice-b-registry-demo.e2e.ts:92` | 1 | PASS/0 |
| 2/39 | `e2e/slice-b-registry-demo.e2e.ts:130` | 1 | PASS/0 |
| 2/40 | `e2e/slice-b-registry-demo.e2e.ts:186` | 1 | PASS/0 |
| 2/41 | `e2e/slice-c-recovery.e2e.ts:143` | 1 | PASS/0 |
| 2/42 | `e2e/slice-c-recovery.e2e.ts:198` | 1 | PASS/0 |
| 2/43 | `e2e/slice-c-recovery.e2e.ts:273` | 1 | PASS/0 |
| 2/44 | `e2e/slice-c-recovery.e2e.ts:300` | 1 | PASS/0 |
| 2/45 | `e2e/slice-c-recovery.e2e.ts:308` | 1 | PASS/0 |
| 2/46 | `e2e/slice-e-policy.e2e.ts:114` | 1 | PASS/0 |
| 2/47 | `e2e/sponsor-demo-journeys.e2e.ts:318` | 1 | PASS/0 |
| 2/48 | `e2e/sponsor-demo-journeys.e2e.ts:320` | 1 | PASS/0 |
| 2/49 | `e2e/sponsor-demo-journeys.e2e.ts:322` | 1 | PASS/0 |
| 2/50 | `e2e/sponsor-demo-journeys.e2e.ts:324` | 1 | PASS/0 |
| 2/51 | `e2e/ux-refinement.e2e.ts:44` | 1 | PASS/0 |
| 2/52 | `e2e/ux-refinement.e2e.ts:131` | 2 | PASS/0 |
| 2/53 | `e2e/zero-touch-exception.e2e.ts:126` | 1 | PASS/0 |
