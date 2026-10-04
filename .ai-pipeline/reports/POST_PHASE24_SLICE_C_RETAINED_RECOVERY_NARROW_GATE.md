# Slice C retained-finalization remediation — independent narrow gate

## Findings and verdict

**PASS for this narrow retained-finalization remediation only. No P0/P1/P2 finding remains in the reviewed delta.** The correct owner is the existing retained-recovery Playwright scenario. The browser expectation assumed that a completed target stage stays expanded; the unchanged disclosure owner intentionally collapses when the stage ceases to be active. The patch explicitly reveals that stage through its existing helper, preserving the original exact visibility and no-replay assertions.

This does not certify final Slice C acceptance, publication, the historical address incident's cause, or real provider interoperability. Interrupted rows12–15, canonical22, the final regression/physical/governance floor, and a NEW independent final Slice C gate remain pending.

## Authority, independence and exact identity

Independent reviewer dispatch: GPT-6.1 Sol / Extra High, as explicitly requested. Actual speed and separate runtime model introspection are unavailable. This reviewer did not implement, diagnose, or remediate the candidate before this assigned gate. The old address narrow gate supplies no independence for this review.

Controlling authority: the full latest owner continuation at attachment d4be5fef-1588-4fe9-84d3-884865f626a7/Pasted text.txt; original Slice C assignment at attachment 635a9f46-f35d-4474-b440-61446aad9b72/Pasted text.txt; AGENTS.md; fyp-quality-gate and its report template; code-reviewer.md; current workflow/planner; ZERO_TOUCH_AUTOMATION_POLICY, PERSISTENCE_RECOVERY_PROFILE, ADR-006/007; current StageDisclosure source/test and recovery owners. CI_TOOLING is the narrow test-only change class. dev_context.py was executed for that class and the emitted current sections were read.

Worktree: C:/Users/shane/.codex-clean2/worktrees/post-phase24-stability-provider-hardening/data-dividends-zero-touch-clm.
Branch: feat/post-phase24-stability-provider-hardening.
BASE_SHA = HEAD = observed local origin/main: 707765b1d51172c64b851c9e46e68b3c23006789.
No fetch or remote-main freshness claim. Index empty. Original main checkout clean.

| Identity | SHA256 |
|---|---|
| Frozen manifest, POST_PHASE24_SLICE_C_RETAINED_RECOVERY_CANDIDATE.json | 8865ee892be116a0271548b2e464bf5269159f2585aed7c8bdd463c7acd9caae |
| Complete 74-file aggregate | 46bdd65d01ec5e7908f1782beac97b74e0e74c86ade888fada402d8f80403579 |
| Previous 66-file runtime set | 16bcc9893db74a949331de8f569560d5cb7dfc1123d74dffe499717addd4b8cf |
| Current exact same 66-path runtime set | 6fc47699779da085ae01709e6624ea70697b14acc3da65f78823e38e41f5a638 |
| Current retained browser file | 4ba5ddab4a434c5dd64086d8514fd612a3ab28757468061312395c5ecbb4865b |
| Original retained browser file | 7d4c223ff69465a4b01755db0d6759758b9fc47d634b86f934392cf8e10c1b19 |

The manifest supplies the complete reviewed path inventory. Raw-byte SHA256 for every frozen path and all ten declared safe evidence paths matched at entry and after fresh execution. The aggregate uses sorted path/hash entries, JSON sort_keys=True and comma/colon separators. Exactly one original runtime path changed: apps/frontend/e2e/slice-c-recovery.e2e.ts. Replacing its new seven-line block with the original one-line HTTP-status assertion **in memory only** reconstructed the exact original file hash. No product, fixture, harness, configuration, or A/B source byte changed in this continuation.

Accepted anchors remain exact: A manifest ba6cf6882bdefd4afbd2a5d4cb60b73645f5e5aa3f4238fb1f922af2b9b2b15a; A gate 2ea5249f59c5641f6331f938b1967ff19276fcdd74b2b78cfa674c18d10c558a; B manifest 8570160b59d45ceb2a6a6439fdc393c1df4d8713179a8e290231dfcd2a035a14; B gate 3f9d05d8a7174747a0d52c5e961b187d2bd2f2b8c4c5e5d628ee0d4a57c49262.

## Failure, causal challenge and repair

The original fresh failure lasted24.516s and its assertion was NOT retained. This gate does not invent that lost assertion, response telemetry, or an exact stack frame. The authorized unchanged-source diagnostic reproduced the current blocker at original slice-c-recovery.e2e.ts:172: expect(page.getByText("Completed POC workflow", { exact: true })).toBeVisible(); expected visible, element not found,23.297s. Its safe receipt identifies the assertion through the original exact source bytes; missing diagnostic telemetry fields remain missing.

The first attempted regression edit failed its LF byte-pattern check and did not change source. The subsequent7.922s PASS in regression_red.json is NOT RED evidence; its manually populated owning-stage field is not an observed browser fact.

The applied regression first checks the POST result is COMPLETED and the target disclosure has aria-expanded=false, then retains the original visibility assertion. regression_red_applied.json records failure at pre-repair line177, expected visible / received hidden,24.328s. The preceding stronger assertions necessarily passed to reach that line. This RED is meaningful causal evidence for the test's disclosure assumption: it deterministically waits for the accepted transition before exercising the same invalid automatic-visibility expectation. It does not prove a product defect or force product state.

Current authority establishes the correct behavior:
- StageDisclosure.tsx:21 follows active changes with setOpen(active); its existing owner test verifies true→false collapse and explicit reveal.
- CaseDetail.tsx:641 excludes COMPLETED from active stages.
- CaseDetail.tsx:859–864 places CompletedOverview within the target disclosure.
- CaseStatePanels.tsx:962 renders that receipt only for COMPLETED.
- Current browser test:173–178 checks COMPLETED, waits for the collapsed disclosure, calls existing openStage, then checks the unchanged exact receipt visibility.

Classification accepted: **INVALID_TEST_EXPECTATION**, with timing-sensitive synchronization in the test owner. The transient original PASS and diagnostic failure are consistent with the response/render/effect ordering; the strengthened RED pins the accepted collapsed state. The24.516s run's lost assertion remains a provenance limit, rather than retroactively recovered evidence.

The repair is one existing openStage invocation. It adds no timeout, sleep, test retry, skip, generic fetch retry, error suppression, page refresh, or weakened assertion. openStage already contains bounded navigation synchronization; its implementation and bounds are unchanged. The new invocation does not change the retry policy or retry a failed lifecycle.

Backend/API and stale-publication hypotheses were challenged. Fresh real HTTP/browser execution observes completion; an independent API trace observes the authoritative finalized ledger; unchanged centralized supporting-mutation cancellation/publication and adverse stale-response tests pass. No product relaxation is justified. No Design Defect, Implementation Drift, duplicate owner, new fallback, or unresolved retirement change was found within this remediation.

## Fourteen required criteria

| # | Criterion | Disposition and evidence |
|---|---|---|
| 1 | Original fresh failure understood | PASS with explicit provenance limit: original24.516s assertion lost; same exact pre-repair test reproduces current visibility failure, and deterministic RED proves the disclosure mechanism. |
| 2 | Precise assertion captured | PASS: diagnostic original line172; applied RED line177 expected visible/received hidden. Current repaired visibility is line178. |
| 3 | Evidence-backed cause | PASS: COMPLETED response and collapsed-stage assertions precede RED; unchanged source/owner test define collapse; independent repaired browser execution passes. |
| 4 | Correct owner | PASS: sole changed runtime path is the retained Playwright scenario; product disclosure remains intact. |
| 5 | Legal fixture | PASS: ordinary create/document/classify/confirmation owners generate state; inert bounded finalization fault; strict full schema8 before/after codec round-trips independently pass. |
| 6 | Ledger/no replay preserved | PASS: TARGET_OUTCOME_RECORDED→FINALIZED, retained outcome→receipt, attempts2→3, operations unchanged SEARCH/SEARCH/SHELL/POLICY/READBACK. |
| 7 | No direct state forcing | PASS: fixture uses existing composition/fault seams and normal authenticated routes. Repair performs only browser disclosure navigation. |
| 8 | No forbidden workaround | PASS: original exact visibility/no-replay assertions preserved; no timeout/retry/sleep/skip/refresh/validation weakening added. |
| 9 | Repeated recovery PASS | PASS: frozen coordinator receipts10/10 isolated successful lifecycles; distinct process audits10/10; additional independent exact lifecycle1/1 PASS. |
| 10 | Neighbors PASS | PASS: eight recorded neighbors PASS; supplemental independent normal Golden STP directly confirms final Review & Send/completion/receipt/progress. |
| 11 | C-QG-001/002/003 remain closed | PASS within narrow impact: owners byte-unchanged; independent backend owner tests cover C001/002 and current render tests cover C003; mixed-sibling and failed-Search neighbors PASS. |
| 12 | A+B floor preserved | PASS within narrow impact: immutable anchors and prior runtime delta verified; recorded B synthetic-company neighbor PASS; independent normal happy-path/final confirmation PASS. Wider A+B final floor remains pending. |
| 13 | External calls0 | PASS: inert allowlisted transport cannot construct external HTTP; browser guard/afterEach rejects external traffic; inspected routing/composition and all scoped execution show0. |
| 14 | No P0/P1/P2 | PASS: no such finding remains in this narrow delta; historical and broader pending evidence are stated separately. |

## Evidence identities and fresh execution

All following paths are under tmp/slice_c_retained_recovery_20261003 and ignored. Hashes were independently checked before/after; no receipt was edited.

| Safe evidence | SHA256 |
|---|---|
| diagnostic_01.json | 3c39dcbdb8083b4c1d50faef58bf773515e5acdc7b1bb5180dc77b4fd4cff763 |
| regression_red.json (unchanged-source PASS, not RED) | 224f228e97eda7eaad6fe1f16d8e60c4baa23b59df739cf65b6840009544190a |
| regression_red_applied.json | f9162a633b9461be486d10e4457587cdab3eb43c8d7e1314e6059ea538798f61 |
| api_owner_trace.json | b96b495ef2b0bdcfc44e8ecfbb57cfef455f98e98404ed5a80c14364e6fa4d82 |
| api_owner_trace_schema8.json | 9c03d7ecee782d41b8ca13348616a544936e8f82bab0f043fac0e34cd5d11941 |
| retained_repeated.jsonl | 303331a8bfddfc09b14a4172abf8d78cc0e90db53585e8ddce0d6001bef1d45c |
| retained_repeated_audit.json | e41550b8b207e69ddb6e37a13fd12557f56e37df68f09829cbf0ab7ebb5932ce |
| remediation_neighbors.jsonl | 8de0999671f5f2d1fd11d36e9763303927bced53fa40d110c79e4d1d547393c2 |
| remediation_neighbors_audit.json | 647afc6d8c2f7050345c54d537d869bafd3a78a341664ce8f9578ab0d38391a3 |
| run_selected_lifecycles.py | e493fc72354b2e41025f9d5c9fb0acce395da2e879faaf8dc60bae0bff75eebf |

Recorded retained ten lifecycles each select one test, use60 seconds, show both processes healthy, ports free, no retry and0 external calls. Recorded neighbors: optional Amend/NO_MATCH; failed Search/recheck; stale policy rebind; legal-name discrepancy; address discrepancy; mixed sibling; Phase24 invalid identity; Slice B second synthetic company. The Phase24 row proves Review & Send placement/availability, not dispatch completion. It is supplemented below, so this gate does not misattribute that row.

Fresh independent commands exercised the frozen candidate with Python3.12.10, Node22.23.3 and installed project test dependencies:
- Exact python -B scripts/run_e2e.py --backend-port 8038 --frontend-port 5208 --timeout-seconds 60 --grep "Slice C retained finalization recovery" --recovery-demo retained-recovery: **1 PASS**,9.765s, one selected test, both processes alive, ports free, retries0, external calls0.
- Same unchanged harness/ports/bound, --grep "Zero-touch Golden STP", normal Mock mode: **1 PASS**,9.516s; final confirmation, completed receipt/progress and A happy path.
- pytest -p no:cacheprovider over tests/test_slice_c_e2e_fixture_routing.py, apps/backend/tests/test_slice_c_blocker_recovery.py, and the two named existing finalization/no-replay tests in test_zero_touch_orchestration.py: **27 selected /27 passed /0 failed /0 skipped /0 errors**,5.469s. An earlier identical focus exited0 but its quiet count was not retained; the counted execution supplies this evidence.
- npm test -- --no-cache src/pages/StageDisclosure.test.tsx src/pages/CaseStatePanels.test.tsx: **39 PASS /2 files**,3.563s.
- npm test -- --no-cache src/UiV2Integration.test.tsx src/ZeroTouchPublication.test.ts: **51 PASS /2 files**,2.860s; includes stale mutation/GET/evidence rejection.
- Independent new synthetic create→document→classify→confirm→resume API/codec probe: **PASS**,1.734s. Before: RECOVERY_PENDING/v14/MOCK_GOLDTIER, TARGET_OUTCOME_RECORDED, outcome present, receipt absent, attempts2. After: COMPLETED/v16/COMPLETE, FINALIZED, receipt present, attempts3. Both complete snapshots include the retained target entry and round-trip through the canonical schema8 serializer/decoder. Recovery history remains. Operations unchanged;0 external calls. No Mongo connection or physical claim.
- check_project_state.py and check_architecture.py: **PASS**.
- git diff --check: **PASS**; direct UTF-8/trailing-whitespace/NUL checks on all72 frozen text paths: **PASS**. Exactly75 pre-report changed paths are accounted for (74 manifest entries plus self manifest); index empty.
- Canonical check_secrets.scan_file rules over exactly the74 frozen paths: **0 findings**.

The first restricted browser invocation failed frontend readiness before selecting Playwright tests (5.312s; ports released). Targeted worktree escalation then enabled the actual independent retained lifecycle. This is not an assertion retry. Local Vitest also required the targeted worktree access. No automatic approval-review rejection occurred.

An initial independent codec setup probe imported the conventional application before provisioning runtime-only test credentials; it terminated with a missing-authentication-setting error before fixture construction. The corrected probe disabled dotenv and provisioned ephemeral test credentials before import, then exercised the unchanged normal owners. No credential value, auth token, raw response, document body or URI was printed or retained. The coordinator's separate public model_dump probe rejection is also retained as a diagnostic limitation; canonical durable serialization, rather than weakened validation, supplies the passing proof.

## Contract, architecture, security and broader limits

RECOVERY_PENDING is expected until explicit finalization succeeds. A recorded target outcome permits receipt finalization only; an uncertain attempted outcome cannot be replayed. Completion follows the reconciled canonical target outcome, not final approval. Provider identity, case/submission identity, frozen confirmation, currentness, lock/CAS, backend RBAC and schema8 bindings remain unchanged. The fixture creates legal state through ordinary owners and an existing bounded fault seam, with a newly generated synthetic memory case. It does not inspect or reconstruct retained real GoldTier state.

Mock, Local, SYNTHETIC_OFFLINE, Sandbox/Partial and Live remain distinct. The fixture's inert XPI adapter seam proves local protocol/recovery behavior, not Sandbox or Live interoperability. No portal, real GoldTier recovery record, provider call, protected database, clm_poc, sponsor artefact, or .env inspection occurred. The reviewer wrote only this assigned report; generated ignored test output is not candidate content.

The full ~1900 backend suite is **not triggered by this remediation**: backend product source, schema, confirmation/ledger, auth and fixtures are unchanged; the only delta adds strong assertions plus navigation in one E2E scenario. Fresh27 owner tests,90 frontend owner/adverse tests, two actual browser lifecycles and the exact-order strict codec trace provide proportionate narrow impact evidence. This does not replace any broader final floor required by the owner. No physical Mongo run, full backend/frontend floor, typecheck/build, Ruff/mypy floor, canonical22 matrix, or final gate is claimed newly passing here.

C-QG-001/002/003 remain CLOSED on their unchanged owners and the stated focused evidence. Earlier address restored-runtime10/10 remains attributed unchanged evidence; the fresh address neighbor passes. Historical empty500 remains **NON_REPRODUCED / ROOT_CAUSE_UNCLASSIFIED residual risk**. No causal repair or impossibility-of-recurrence claim is made.

Changed in this continuation: browser test behavior only. API/type, schema, connector, configuration, business rule, mapping, auth/security, architecture, provider classification and product runtime behavior: **unchanged**. No compatibility alias or product fallback was added; only the test's automatic-expansion assumption is retired.

## Bounded consequence and Git status

**Independent narrow gate: PASS. Current retained-finalization blocker: CLOSED on the exact frozen candidate and recorded evidence above.** This report supplies acceptance only for the authorized narrow remediation.

Next authorized action for the coordinator: resume interrupted rows12–15, then canonical22/22, then the required fresh final regression/physical/governance floor; freeze unchanged cumulative content and dispatch a NEW independent final Slice C reviewer. A failure stops its dependent work under the owner assignment. This narrow reviewer does not begin those lanes.

Worktree remains intentionally uncommitted on the same branch/base/HEAD/local-main. Original main remains clean; index empty; reviewed content/evidence unchanged after all checks. No Git mutation, staging, commit, push, PR, merge, fetch, publication, Slice D, policy advisor, portal study or MockGoldTierConnector change occurred. Final Slice C gate and next-phase readiness remain pending.
