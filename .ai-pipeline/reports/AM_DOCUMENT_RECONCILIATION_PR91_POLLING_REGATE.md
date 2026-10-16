# PR91 final polling exception - independent Quality Gate

## Executive result

**FAIL - REQUIRED CANONICAL BROWSER VERIFICATION FAILED; DO NOT PUBLISH OR MERGE.**

The polling correction closes the reproduced document-read authority mechanism in the inspected source and focused mounted regressions. The first query-projection P2 also remains closed in those checks. However, the mandatory complete canonical browser union failed on the frozen full candidate: shard2 stopped at selector50/53 after a case-summary GET returned HTTP500 following a successful explicit document replacement. Four expected Chromium records were not dispatched. These failures and missing records cannot be converted into PASS by the focused or full frontend successes.

This reviewer is `/root/pr91_polling_fresh_gate`, independent of implementation and all prior PR91 corrective work. No implementation, test, configuration, historical-report or acceptance-criteria change was made. The only reviewer-authored tracked deliverable is this report; independent execution/audit receipts are ignored current-task evidence. No Git mutation, publication, thread reply/resolution, resource termination or next phase occurred in this gate.

The original Wave3 cycle remains1/1 consumed; the first PR91 exception remains1/1 consumed; the final polling exception is1/1 used. No further correction or rerun is authorized. The failed campaign is preserved. Cleanup is verified separately and does not change the FAIL verdict.

## Reviewed identity and scope

- Repository: `shaneqwaszx/data-dividends-zero-touch-clm`.
- Worktree: `C:/Users/shane/.codex-clean2/worktrees/am-document-reconciliation-20261015-2147/data-dividends-zero-touch-clm`.
- Branch: `feat/am-document-reconciliation-disclosure-20261015-2147`.
- Current/published HEAD: `ebfc738e82b73a739a8e96654225f00235b0f36d`; HEAD tree `5f7056c65fb70a7f0cab247db7a62b6fde510b65`.
- BASE_SHA, merge base and inspected local `origin/main`: `74da1b139d649c825d127385b3a8651cd9ce6b27`; base tree `6acb4d5642683f2ebd4f2ea51f494ed248dd1d27`.
- Reviewed and tested content is HEAD plus the two uncommitted authorized paths, together with the complete frozen18-path candidate below. HEAD alone is not the tested content.
- Complete corrected18 aggregate: `3e02a16b757e2eff9ca8f4776b8f590b0524f619d361e88cf496ba527b5fbfce`.
- Previous corrected18 aggregate: `f7b92ab5c6e8f14df28809764e9219ae2a79730f8b24627b509e6d0f52f00010`; original aggregate `e6d7aac9230daa80bd8da03c85cab3508e1b980cae0fece25a41d3021874580f`.
- Exact current two-path binary diff SHA256: `02d51ff92ef6c8b5dbdfda15aa2cce2c97b9732b4a1d43556a92a26f4ca217b2`.
- Complete18-path binary diff against main SHA256: `70708c6c4f6934c9cafae7465ecd0cf5edeb400aaf2ca56c0764303516fa494f`.

Independently recomputed every raw SHA256, CRLF-to-LF SHA256 and native Git blob prediction before and after review. The aggregate is SHA256 of UTF-8 compact ordered-record JSON with sorted object keys and separators `(',', ':')`. All identities match the freeze. Native predictions do not claim future index/commit storage. All16 files outside CaseDetail.tsx and EvidenceWorkbenchIsolation.test.tsx remain identical to the preceding accepted corrected candidate. All589 protected historical files,9 unchanged owner/package files,3 installed Query source files and29 browser inputs remain byte-preserved.

Read the final owner assignment, root/frontend AGENTS, fyp-quality-gate/template, frontend-state-cache-change, relevant integration-security guidance, actual FRONTEND_UI/FRONTEND_STATE_CACHE dev-context and selected workflow/architecture/project-state sections, current intake/reconciliation contracts, ADR-011, PLAN_AND_READ_PATHS, both P2 thread bodies, prior gate/handoff boundaries, current owning source/tests and the complete cumulative18-path diff. Current source/tests govern. No sponsor/provider authority changes.

The only current product delta is CaseDetail.tsx. The only current test delta is EvidenceWorkbenchIsolation.test.tsx. Shared caseQueries/automationPolling/queryClient/auth/API/types, presentation component, dependencies/lockfile, all eight browser owners, fixtures, maintained runner, network policy and configuration remain unchanged in this final exception.

### Complete frozen candidate

| Path | Raw SHA256 | LF SHA256 | Native blob prediction |
|---|---|---|---|
| `apps/frontend/e2e/am-wave1.e2e.ts` | `e950374b225cc12206fb7b50dc8ccd09175d7bc1062a437b7e9c0ffdc636920f` | `6f0fa83ab7011ab40915a09c470fad1d4f5099bd610fd2c01dc9c4ae1b587a01` | `a5f00746aee4f4b0ca57a893dc637e4658d627df` |
| `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` | `30d2b318cdb263473f31fd6a09d9b490cde1404dc62b1812f2c12c5979eb3f6f` | `cc8889f7611e6524b80b42ff6508ea4ac30a348d7d30cf8c1a6bb73bd238f362` | `137ddd1552562be553ad7436b06adf3faf894b85` |
| `apps/frontend/e2e/blocker-review-performance.e2e.ts` | `09d7f4e1bd4589ac0ccf1abc2441789a610ece94ab5550b5353f5a152de0d780` | `0e697ecfe639fafb158c32776f5f2c9c889968ff2736d9250b2c3a1bf7cb7c37` | `3e447fdd3999bae877ca9c0a52f25cdfa0274bec` |
| `apps/frontend/e2e/garden-happy-path.e2e.ts` | `71711eb62c720d3694f9491d5206c53f8f9fc41e961d40aa9178c29fb07cc4c5` | `7a3b925f0ecaab4be40b921ca9d0bacadb3dc0df9ebedad21c478382ce9b365d` | `d1cc912914b643e8193e8e3da7f9c021977bba39` |
| `apps/frontend/e2e/ownership-document-streamline.e2e.ts` | `c61e8475babcbaa0158f181ba1a57b399d16e17aabf267c509638a1377d826b3` | `2a8acd24ea3bed9758591da816b8189462224dd1834e12c237f9524fec95c5fa` | `4707df5135e2645041b59a7187deeffa59f24d53` |
| `apps/frontend/e2e/phase24-identity.e2e.ts` | `67750bc6479e21eb8820200d915372773edf19be68bf72748541af8cde0fc611` | `1a78a879f6c01689cd852b88d732f452fa43e010d4207fded7e5c2c6ee473106` | `c539f38b3ffc23b2bd2ab20e42990c5d116b2c8c` |
| `apps/frontend/e2e/responsive-layout.e2e.ts` | `6aecae85882d09fbb3bdfe80572bf4f14975514dbf2d2f3f5516c0cde57d41d1` | `a7b429c5b956cbf34dbb74db18e3670c214ac88b3f765e2fdc58264d21e7fde7` | `b3f50e69c310610462dee8a06983210599ec3657` |
| `apps/frontend/e2e/s2-ownership.e2e.ts` | `6c9b02846704398a3385d2b772a35b5a0b7bacdae6d8d5084040b50acd2572c9` | `fa148e630c1e5a73ed09b8be54b15ed5e26a9b2a4139fc9762043b7cc6f84b00` | `5fc275ed0e12b8a785cf6c7f12a1af8922d66780` |
| `apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx` | `b6a2c39a67b91bf1ffa27255155f6eec7f182eb7b83a2058411ad29b0f6c4799` | `e8bc8d5a7c1ffb6af9f40179a16b91985080dca2a092c19c0f85d4ac5e0aace6` | `b0d1c8b9282fc36f75d547b3e1b57da1aa502ccb` |
| `apps/frontend/src/pages/BlockerDecisionReview.test.tsx` | `d59e022eee13001ae4b05ca567dc26a587a77fca596c62c00a3a483932dbbf34` | `29b55eb694c63e59ba5885515edc2087d6374b2a1a3a90a8d5c2b5471bf178b9` | `49e8d8c2ce8702da53f8b751544dfb267c7eb9d6` |
| `apps/frontend/src/pages/BlockerDecisionReview.tsx` | `2c5679f458601d9931cdbad1b7730c20a627ff5a0b632a2e2e60afd78cc29629` | `e1bdf376977d7fce5ff5c80bcd00bf7cbdb7f737a947340bb7fc6bf74c66764e` | `0167f9f3b39b424ce96c9b6d80b4949a9c9f965f` |
| `apps/frontend/src/pages/CaseDetail.tsx` | `a3362517ffa54a6dd5ec77952f64e9032f2d3ac905f3d2cd0686f8a2bdc4b718` | `ce1833e7fe16f1b6e1a83cf406cb2a499c8e8256f10dd9a1c3f15e4b26a9207b` | `57750fcac37fecd4171ce14ff5d361f988fcaa66` |
| `apps/frontend/src/pages/CaseStatePanels.test.tsx` | `956f6fcf3f54c5dd8e1d291b19bde54076a1408b256a0865a66a9f5555bf6233` | `fd4bc5f4ed881d007e9949512183fd1af734784705ee6a8477244b3f3bafee5d` | `ed2cfaa88a1107b78f3daa8cd716eec0d65f619c` |
| `apps/frontend/src/pages/CaseStatePanels.tsx` | `79287c603422f8710b9e13217482c39a447f2f040b336718c07fab88136aab34` | `a1d8b960bae33a644753e31998792aebfbf2c8d2b3b1a7d2c65fb1b8693683aa` | `7653805a35bdd5bae845fb8a99b6a5df128d0d15` |
| `apps/frontend/src/pages/DocumentEvidencePanel.test.tsx` | `2864fff3fb5a0a9e1918e047e0fc8298dd16424b5fdbb0e0774f9bfdc1b2b621` | `b57ab40d835922ecd4b4ba9207968964a651bf669f08df5873e78f611baf7bfb` | `2b36c17d4437bbbfb0dd16d0e302f01be21f893b` |
| `apps/frontend/src/pages/DocumentEvidencePanel.tsx` | `22d5ddaf5736e210d67ae97fc848c043a9c6328df0ec469d33d6e8c9cb2ae26a` | `5feccd3c29c89f33a20e86737d333121a7f67d59382399659139544c8a432c96` | `5a35180748b2de3589d290f67d1cd32af6945b28` |
| `apps/frontend/src/styles.css` | `88eb8fe21866a48b96f8a67085125360c21ed31a49b4c0579472d75181edff37` | `ccff0ad89754113685d92aa11c234c3b592598d7836908f70050468acc3a30c9` | `96107fbba249c13222a8f1dc9c72527eff5fd101` |
| `docs/integration/AM_DOCUMENT_RECONCILIATION_DISCLOSURE.md` | `ce59acfb6d8d28eb7283a04d9fcc4684a7e04c4ee31535e01e08fd74d242bc65` | `42cfd0524b8faec38ada6b039118dd6022f3a2f1f8999a88aec8477de2711a1b` | `91b2bdfd555b5420586b92ad2751b93aa4363515` |


## Refresh-path inventory and owner review

| Entry point | Success/failure authority | Scope, currentness and disposition |
|---|---|---|
| Initial document useQuery | Existing documentQueryOptions; pending/fetching/error/success observed by all3 presentations | User/case key, consumed AbortSignal and retainNewestDocuments unchanged. Empty support claims require a confirmed successful read. |
| Automation onUpdate | Case summary publication remains separate; document and ownership fetchQuery executions settle independently | Existing polling generation guard precedes callback. staleTime0 forces the scheduled GET; retry:false preserves single-attempt supporting reads. allSettled handles every detached rejection; query state exposes failure. |
| Explicit read-only refresh | refreshEvidence cancels the4 existing exact keys, checks current action and executes the document factory via fetchQuery | Document failure is observable on the same query as initial/polling reads. No new mutation is introduced. Existing case/ownership/intelligence successful publications remain individually guarded. |
| Evidence mutation followup | settleEvidenceMutation uses refreshEvidence | Existing pending lock, actor/case/generation checks, mutationBlocked and safe unavailable handling remain. A failed refresh does not clear the block. |
| Replacement, review, retry, intake, resume and recovery | Existing handlers enter settleEvidenceMutation and the same refresh | Original fingerprints, event/version checks, frozen-target and backend authorization are preserved. No automatic document retry or Send. |
| Priority/general mutation uncertainty | Existing refreshEvidence callers and error handling | Even the existing general refresh catch cannot hide the document query's failure state. This change does not grant new mutation permission. |
| Supporting invalidation and identity rebind | Existing caseSupportingMutationEffect owns cancel/invalidate/reset | Identity-dependent evidence is retired before rebound summary publication; canonical retention and deletion protections remain read-only. |
| Refetch, case/actor transition, logout/session replacement/401 and unmount | Existing QueryClient/auth lifecycle and consumed signal | Query cancellation/deduplication supersedes the old detached page GET publication. Late responses cannot overwrite the current scope; session clearing removes incompatible data. |

Installed TanStack Query5.102.8 source was inspected for fetchQuery defaulting, active-request deduplication, consumed-signal cancellation, error-state retention and cancellation/revert handling. The global initial-query retry1/45-second freshness policy is unchanged; the explicit supporting executions use retry:false/staleTime0. The actual production-default-client regression proves one failed polling attempt, while the slow-read test proves deduplication across the unchanged1-second polling cadence. The maintained polling error backoff and deadlines are unchanged.

Official [Query cancellation documentation](https://github.com/TanStack/query/blob/main/docs/framework/react/guides/query-cancellation.md) supports signal-driven cancellation/reversion; the exact installed source and local execution establish the version-specific behavior. A direct documentation-page fetch timed out; authoritative primary search and installed-source evidence were available. No speculative library behavior is used as proof.

## Acceptance and adversarial evidence

| Criterion | Local result and direct evidence |
|---|---|
| A cached document plus successful summary/failed supporting read | PASS in actual mounted CaseDetail: all3 projections display a visible failure/last-confirmed notice. |
| B no cached documents plus failed supporting read | PASS: optional support reports unavailable/unconfirmed availability; no authoritative empty claim or fabricated document. |
| C successful empty read | PASS: Main/More/Technical preserve the distinct truthful empty states without loading/error notices. |
| D current recovery | PASS: retained failure persists during the pending current recovery and clears after its success. |
| E older failure after newer success | PASS: real QueryClient refetch cancels the old consumed signal; its later503 cannot stale the newer successful evidence. |
| F case/actor/logout/unmount | PASS: four mounted adverse variants abort old support, reject late publication and prevent warnings/data leaking into the next identity. Existing Auth/session/401 regressions also pass. |
| G independent ownership | PASS: successful ownership evidence is published when the concurrent document read fails. |
| H rejection/write/retry/Send safety | PASS: actual process unhandledRejection listener remains empty; mocked HTTP asserts GET-only behavior; production-default client performs one attempt. No implicit business write, automatic retry or target submission is added. |
| I prior query/refetch/mutation-blocked and required review actions | PASS in focused source/execution: pending/error/refetch tests, explicit read-only refresh, blocked mutation recovery, grouped decisions, original version/source bindings and current action/focus regressions remain. |
| Full mandatory canonical browser union | **FAIL**: current summary500 at shard2 selector50/53; three selectors/four records undispatched. Local A-I successes do not waive this requirement. |
| Frozen full candidate and cleanup | Identity preserved; bounded task resource cleanup independently corroborated below. |

The new tests mount CaseDetail under a QueryClient and use real startAutomationPolling; they do not inject loadFailed into a presentation-only test. Deferred responses and fake timers exercise cancellation, out-of-order completion and actual callback failure without changing production deadlines. Existing first-P2 mounted loading/failed-empty/failed-retained and standalone optional-panel tests remain intact. The unhandled listener uses the actual Node process and removes only its own listener.

Before production changes, red.log had12 failures of70 tests; red-complete.log had13 failures/58passes of71 tests, including the directly related explicit-refresh route. Successful empty polling was already passing. Final focused GREEN was105/105. An initial typecheck failed only on the new test's node:process type import; that initial failure is preserved. The final test uses a minimal type for the actual global process without adding a dependency or changing the listener/assertions. The frozen candidate and final checks include that correction.

### Executed and audited checks

| Check | Actual result |
|---|---|
| Independent CaseDetail, document, reconciliation, state/cache and session focus | 242/242 tests across8 actual files, native0; independent-focused.log/json. The original command included a nonmatching .tsx filter for the publication test, which is not counted. |
| Independent exact ZeroTouchPublication.test.ts | 6/6, native0; independent-publication.log/json. Total independently executed focused tests248 across9 files. |
| Coordinator affected state/cache focus | 192/192 across7 files, native0; state-cache-focused.log. |
| Full frontend | 768/768 across54 files, native0; full-frontend.log/checks.json. |
| Typecheck / production build | Both native0 on frozen final content. |
| Project-state, architecture, tooling configuration, policy authority, external-provider readiness and secrets | All native0; actual log hashes match checks.json. |
| Governance unittest discovery / pre-PR checker unit tests | 89 +64 =153 current tests, native0; supplemental-checks.json. These are checker unit tests, not a clean committed publication gate. |
| npm ls --all / task venv pip check | Both native0. |
| Current delta whitespace and all18 full-file trailing whitespace | Clean. New report whitespace checked separately; plain git diff does not inspect an untracked report. |

Independent audit verified all passing log hashes and receipts rather than treating authored tests as proof. React act warnings and the Vite chunk-size advisory remain visible; native results are reported accurately. No configured frontend lint command exists. Full backend/domain/schema/provider/physical-persistence suites are not required solely by these frontend classes because those owners/contracts are unchanged. The canonical browser fixtures still use their existing guarded disposable Mongo route. No new POC regression catalogue entry or provider/approval claim is established.

## Required blocker F-01: failed canonical summary read and incomplete union

Fresh discovery collected107 selectors and136 Chromium records. The two stride partitions contain54 and53 selectors. Independently rebuilt expected file/line/column/full-title/tag multisets from discovery.json and matched every dispatched raw Chromium progress record and the ordered selector prefixes. Both canonical commands retained `--timeout-seconds 60`, zero Playwright retries, original fixture routing, network guards and assertions:

- `python -B scripts/run_e2e.py --backend-port 9800 --frontend-port 4800 --timeout-seconds 60 --shard 1/2`.
- `python -B scripts/run_e2e.py --backend-port 9900 --frontend-port 4900 --timeout-seconds 60 --shard 2/2`.

| Campaign | Expected selectors | Dispatched | Guarded successful lifecycles | Passed records | Failed records | Native exit |
|---|---:|---:|---:|---:|---:|---:|
| Shard1/2 |54|54|54|77|0|0|
| Shard2/2 |53|50|49|54|1|1|
| Actual combined |107|104|103|131|1|FAIL|

Three undispatched selectors account for four unexecuted records: `e2e/ux-refinement.e2e.ts:44` (1), `e2e/ux-refinement.e2e.ts:131` (2), and `e2e/zero-touch-exception.e2e.ts:126` (1). Thus132 of136 records executed, with131passed/1failed; four remain NOT_EXECUTED. No skipped, flaky or retried record is counted as passing.

The failed selector is `e2e/sponsor-demo-journeys.e2e.ts:324`, Sponsor blocker journey multilevel, tag `@s3-sandbox-sponsor-multilevel`. The explicit replacement POST's200 assertion at source256 succeeded. The subsequent expect.poll at257 calls summary(), whose source45-46 GET `/api/clm/zero-touch/cases/{safe_case_id}` required200 and observed500. The lifecycle failed after22.156seconds, within the unchanged60-second bound; this was an assertion/HTTP failure, not proof of deadline exhaustion. The generating layer, root cause, dependence on this candidate and relationship to any historical incident remain UNKNOWN. No backend-cause attribution, harmlessness/inheritance claim or repair is inferred from unchanged backend files or other passing runs.

Immutable current raw hashes: shard1 `d7c0f20f51e9225e469b36b778e54f9c1c2cab746718d7b62161263e259b3caa`; shard2 `c467a0095f3235f676ce30977456170f2441da971ee67f285752af36136b6ff6`. browser-receipts.json, independent-browser-reconciliation.json and browser-reconciliation.json preserve native exits, record counts, undispatched inventory and the failure. No rerun or corrective source edit followed the failure.

Historical Garden ownership500, AM18 summary500 and earlier AM14 ownership500 remain separate UNKNOWN/OPEN risks with their original raw evidence preserved. The current multilevel summary500 is an additional observation. A successful shard or earlier complete campaign neither explains nor closes any of them.

## Runtime resource cleanup

Canonical fixture cleanup markers are7 in shard1 and6 in shard2, including cleanup following the failed lifecycle. Only the fresh loopback task Mongo at27324 was used, with generated allowlisted fixture databases. No .env, clm_poc or external Live provider access occurred. The coordinator's helper executed its system-database-only subset assertion before exact Docker stop; it did not persist the exact final database-name list, so that list is not reconstructed or claimed here.

The exact task container `clm-pr91-polling-20261016-0201`, ID `a6e1d391e837755cb0c7f608fd8259761aab79ad1712e1813eb4028f9b8b9b5e`, was label/binding/volume-verified by the coordinator and stopped only by that coordinator. Independent read-only Docker checks found the daemon reachable and explicit no-such-object/no-such-volume responses for the exact container and both recorded anonymous volumes. All215 reserved task ports, including27324, were independently bound with SO_EXCLUSIVEADDRUSE after cleanup.

The observer sampled1751 owned descendants plus2 roots;451 executable instances were headless_shell.exe. Independent exact-PID/birth probes found0active matching births,1742 normal absent handles and11 different-birth PID reuses among1753 records. Valid Toolhelp and scoped CIM inventories included the audit's own live Python process and omitted both previously problematic PIDs58660/33120. No process was killed by the reviewer.

The first coordinator cleanup probe's3 access-denied handle records at those2 PIDs remain preserved as transient UNVERIFIED evidence. Fresh independent probing later had0access-denied/0unresolved handles. No kernel-object-destruction claim is made. The initial derived Chromium count0 was a classifier omission of headless_shell.exe; the old receipt remains preserved and the corrected451 is disclosed, without altering raw process/browser evidence. Sampling may miss short-lived processes; canonical containment, exact-birth probes, valid active-process inventories, Docker absence and exclusive port binding corroborate bounded cleanup. These limits do not erase the browser failure.

Direct independent receipts: independent-process-audit.json and independent-resource-audit.json; coordinator cleanup.json, cleanup-attempts.json and preserved first-probe/classification diagnostics. Cleanup is complete for observed task runtime; it is not a passing browser result.

## Combined findings, boundaries and readiness

Contract/integration: no new API shape, source choice, mapping, endpoint, sponsor rule or provider classification. The original document/reconciliation disclosure keeps required candidate values, comparison outcomes, warnings, replacement/recovery and complete explicit grouped review in Main; passive support/history/provenance retains safe existing fields. Current expected automation/case/document/reconciliation versions, fingerprints and target freeze remain authoritative. No new required action was found missing in inspected source/focused execution. Complete browser acceptance nevertheless remains unverified because F-01 stopped the mandatory union.

Code/architecture: correction reuses the existing document and ownership query factories rather than adding a second cache/error owner. retainNewestDocuments and retainNewestVersionedEvidence remain unchanged. Query keys, deletion effects, session owner, initial freshness policy and mutation retry policy remain unchanged. No architecture owner replacement or ADR is needed for this wiring change. Removed detached/manual document publication is replaced by canonical query lifecycle publication; no fallback, wrapper framework or parallel state engine is added.

Security/adversarial: backend capability/team/creator authorization, in-lock reauthorization, CSRF, safe inaccessible-case handling and target ledger are unchanged. React projects existing sanitized fields; fixed read notices expose no provider body/private exception. No sensitive browser persistence, new raw logging or confidential artefact is added. Cancellation/out-of-order/session isolation and call-count tests pass locally. Mock/Local/Partial/Dormant remain distinct from Live; no sponsor, production compliance, legal UBO, Ready-for-Approval or final approval claim follows.

Required fixes/current blockers: **F-01 remains blocking: the canonical browser execution failed and the complete successful union is absent.** The HTTP500 cause is not established. No further remediation, campaign loop or waiver is authorized by this task. Local A-I/source evidence supports the bounded mechanism correction only; it does not supply exact independent PASS or publication readiness.

Both existing PR91 P2 threads remain unresolved at the recorded remote checkpoint. This gate does not reply to or resolve either thread. The current published ebfc738 billing-refused hosted jobs remain NOT_EXECUTED, not product-test failures or hosted PASS. No correction commit exists, so correction-head review, stored-content publication proof, latest-main integration, clean committed pre-PR, push and new CI observation are NOT_EXECUTED and remain conditional stages blocked by this FAIL. No CI waiver or merge authority is granted. Only the human owner may adjudicate new scope/risk and any later merge; Wave4 and Live readiness are not established.

| Change surface | Final polling exception disposition |
|---|---|
| API/shared types | Unchanged. |
| Durable schema/repository/persistence | Unchanged. |
| Connectors/external providers | Unchanged. |
| Maintained configuration/dependencies/fixtures/runner/CI | Unchanged. |
| Business rule/source precedence/threshold/mapping/approval | Unchanged. |
| Backend auth/security authority | Unchanged. |
| Shared cache/session/architecture owners and provider status | Unchanged; page wiring uses existing owners and their cancellation/error states. |
| Frontend runtime | Document polling/manual refresh failure/currentness now query-owned; fetching status reaches all3 projections and successful ownership publishes independently. |
| Durable documentation | This new independent FAIL report; all preceding reports and integration documentation preserved. |

At report issue HEAD/origin-main remain the recorded identities, index is empty, the two authorized tracked paths are modified and this report is the sole new reviewer path. Ignored task receipts remain untracked. Assigned worktree is intentionally uncommitted/dirty; no clean-repository or publication-readiness claim is made. Primary checkout and unrelated worktrees/resources were not changed by this reviewer. No commit, push, PR write, merge or next-phase action occurred.

**PR91 POLLING RE-GATE: FAIL - REQUIRED BROWSER FAILURE/UNEXECUTED RECORDS REMAIN; DO NOT PUBLISH OR MERGE.**

Report issued UTC: 2026-10-15T18:31:15.687704+00:00.
