# PR81 V6 independent helper-code safety review

## Outcome and exact reviewed scope

**PASS for the frozen V6 helper code/profile/test preparation only.** No required correction remains in this bounded logging-mode change. This is an independent review by the separate PR81 V6 code-safety reviewer, read-only except this assigned report. The manual administrator SOP does not yet exist in this reviewed set and requires its own fresh exact-bound review. No manual READY, elevated capture success, TCP causality, publication or human-merge readiness follows from this verdict.

Worktree C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm; branch feat/blocker-resolution-idp-ux-optimization; HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached origin/main and merge base e799d74063678bb0eccbea445d5ab3c8628dd2c0. No fetch or Git mutation. Existing 23 tracked changes remain; staged set empty. Product source25 identity ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490 verified independently before and after the checks. All 1175 explicitly snapshotted historical paths remain exact, including V3/V4/V5 and the V5 failure receipts.

Reviewed manifest content identity14a0e1e9e969244719042245920f786e1aeede6ae485ec3484f3b00fda4d66f3; all20 reviewed path hashes match; bundle SHA256 b072fb20d5002a9d94f7baef38204c4b5547ba2de64eece1e31c6446ab8150a7 and all13 bound members match. The full exact binding is below. Current source, independently exercised helper content and independently reviewed content are the same frozen set.

Read AGENTS.md, fyp-quality-gate, integration-security-review/checklist, scoped CI_TOOLING dev_context, selected current workflow/architecture/state authority, V6 plan/handoff/diff/receipts, prior V5 code gate, safe V5 stop report, actual helpers/tests/profile/schema and installed SDK. Applicable scope is local capture-helper configuration/testing/log-safety, with no changed application owner or external contract.

## Documented mismatch and smallest authoritative correction

The safe V5 ce820f5f failure record proves requested0x10000002, returned0x10400002, sole comparison-mask64 and query0; ownership/other limits/readiness passed. Provider enable and HTTP fixture were not reached; cleanup stopped0 and queried absence4201. No raw ETL or protected operator marker was read for this review.

Microsoft identifies0x00400000 as STOP_ON_HYBRID_SHUTDOWN and0x00800000 as PERSIST_ON_HYBRID_SHUTDOWN. It describes caller-session-dependent default choice when neither is explicit. The observed V5 added STOP bit is consistent with that documented default selection. The V5 record establishes the returned configuration; the documentation explains the mechanism without a new direct measurement of internal Windows normalization. The separate historical V3 guard and missing506-byte HTTP root cause remain UNKNOWN. Source: [Microsoft Logging Mode Constants](https://learn.microsoft.com/en-us/windows/win32/etw/logging-mode-constants).

Installed SDK10.0.19041.0 shared/evntrace.h independently read and hash-matched the frozen SDK receipt: lines401/439/447/448 define CIRCULAR2, NO_PER_PROCESSOR_BUFFERING0x10000000, STOP0x00400000, PERSIST0x00800000. Explicit STOP retains the observed session stop behavior on hybrid shutdown and avoids relying on the default choice. It introduces no PERSIST behavior, packet/provider change, socket operation or new event payload.

V6 Native.ApprovedLogFileMode is an immutable compile-time composition of the three named SDK constants,0x10400002. Native.Props, the actual properties constructor called by Start, requests it. Native.Bounds and the controller comparison both require exact equality to it; arbitrary extra flags are not masked or accepted. The new test reflects and marshals the actual private Props method without calling StartTrace, verifying the requested mode plus unchanged allocation/flush/clock/GUID/buffer/file constraints.

The only profile key changes against the immutable V2 profile used by V5 are log_file_mode, log_file_mode_description and revision. Native code after namespace normalization differs only by named mode constants and the two Props/Bounds substitutions. All remaining runtime bodies, including typed watchdog, native ownership/handle checks, Query, Enable/Disable, Stop and Complete, are unchanged. Controller changes are revision namespace, exact mode expectation, safe validation-suite hook and V6 manual filename. Stage comparison6 states the new exact value. Numeric diagnostic schema remains formatversion5, byte-identical; helper namespace/bundle helper_version6 distinguish the helper revision. Runner and sanitizer are byte-identical to V5. Existing test changes are namespace/mode positive-control updates only; separate logging-mode suite supplies new coverage.

## Independently executed evidence

All checks were run on the exact frozen content under the ordinary execution token. PowerShell Core safe Validate compiles C# and queries installed provider templates but invokes no live ETW trace-control API. Tests ran without OutputPath; the bounded synthetic writer creates and removes one uniquely named temporary numeric JSON file outside the repository. No watchdog child or fixture process was started or terminated. Python used -B; pytest cache disabled and Ruff no-cache.

| Independent check | Result |
|---|---|
| Invoke-Pr81TcpCapture.ps1 -Mode Validate | PASS: installed schema, layouts, source/bundle hashes, ownership/bounds/loss and all four suites |
| Test-LoggingModeSafety.ps1 through Validate | 50/50 PASS |
| Test-ControllerDiagnostics.ps1 through Validate | 30/30 PASS; bounded numeric writer and no overwrite PASS |
| Test-WatchdogSafety.ps1 through Validate | 39/39 site/adverse cases PASS; six actual Process checks PASS |
| Sanitize-TcpTrace.ps1 -Validate through Validate | 19/19 PASS; no ETL read |
| Run-FreshFixture.py --validate only | PASS; no fixture/socket confirmation/trace |
| Ruff check --no-cache V6 runner | PASS |
| pytest -p no:cacheprovider tests/test_check_secrets.py -q | 8 passed |
| Canonical scan_file on20 reviewed plus25 source paths | zero supported-pattern findings on45 explicit paths |
| scripts/check_project_state.py / scripts/check_architecture.py | PASS / PASS |
| git diff --check plus explicit new-path and diff-added-line whitespace | PASS / zero findings |
| Frozen manifest, bundle, source25, SDK and historical1175 hashes | PASS before and after verification |

The50 mode cases include exact approval, missingSTOP, extraREAL_TIME, PERSIST replacement, STOP+PERSIST, missingCIRCULAR/shared buffers, zero, circular-only, all bits and every29 absent bit individually. Every39 mode combination runs the actual controller pre-enable pipeline using fake native return, checks enabling allowed only for exact approval, original mode-mask64/stage6 on rejection, and exactly one correctly bound owned-stop/absence delegate. Six other individual bounds reject, three exact/foreign/empty ownership cases hold, and actual Start properties/profile constraints pass.

Existing30 controller cases independently cover all limits and foreign ownership, query native error/exception, watchdog missing/dead/getter error, shared EnableCore allocation/marshal/attempt/return/assignment stages, native enable failure, diagnostic-write failure, exact cleanup/absence exceptions, disable1168, missing completion and false-export prevention. TestEnable exercises shared marshaling with fake return and never calls native ETW. NativeAttempted remains a managed call-attempt marker, not proof of physical entry.

Watchdog39 cases exercise readiness24/pre-enable7/wait25 with healthy/dead/null/invalid primitive values, ScriptProperty/CLR errors, unassociated actual Process, missing association/identity, diagnostic failure and stale previous healthy state. Failure prevents start/enable as appropriate and export; owned cleanup stays exact. Six actual observations bind/observe the current process, reject a separate object for the same PID, null/unassociated binding and genuine getter failure. No child liveness/termination execution is implied; dead state is synthetic.

Sanitizer19 retains hostile type/unknown ID-version/address/PID/process-key/reuse/temporal/lifetime/missing-send rejection and exactly one matching complete pair. These checks establish strict export selection; they cannot prove future native delivery/ACK/FIN coverage.

The implementer receipts truthfully record an initial nonexistent test-function invocation and an initial whitespace-aggregation scope mistake, both before final passing results. Neither is silently counted as PASS or a capture; independent final execution passes current content. Full product/backend/frontend/Mongo/POC/lifecycle/pre-PR checks are not the changed surface, and fixture/publication are forbidden here. No historical main CI is used.

## Confidentiality, cleanup and adverse boundaries

Installed template/schema parity was checked by safe Validate. The same TCPIP provider,20 event IDs/35 versions/319 typed fields, INCLUDE filter0x80000200, keyword0x0000409700000486, level5, enableflags0, timeout1000ms and non-System session remain. Actual schema types are UInt32/UInt64/Boolean/Pointer and Binary only for length-delimited SocketAddress; no arbitrary string/body/packet buffer field. ETL control headers can contain local identity/path/session metadata and therefore remain protected operator-local. The mode correction does not change those records or justify reading raw ETL in Codex.

Acquisition remains selected host-wide TCP metadata, not a connection-only native filter. Sanitizer requires unique fresh localhost tuple/fixturePID/ProcessStartKey/two TCB lifetimes and excludes raw pointers, addresses, keys, XML/messages/binaries. Output bounds4096 events/1MiB, loss and conservative circular-overwrite rejection are unchanged. Selected FIN-delivery/injection events are not literal proof of wire FIN; missing transmission/ACK coverage stays UNKNOWN.

The45s absolute deadline assigned before hidden child launch,300s arming,5s readiness,8MiB file,64KiB buffers4..16, flush1, zero-loss/no-overwrite acceptance, same-host/runtime/source hashes, no-reparse/local disk, fresh directories and private operator/SYSTEM/Administrators ACL are unchanged. Native.Stop re-queries exact named session GUID then exact handle GUID before disabling/stopping; foreign/empty ownership is rejected. Parent finally and deadline watchdog remain separate. Unknown typed watchdog state fails closed; binding retains object-reference/PID/creation identity. No auto-elevation/RunAs, policy/group/firewall/driver/network changes, global session enumeration or unrelated process kills.

Numeric diagnostics are fixed integer/Boolean/null only, bounded fresh CreateNew files without overwrite; arbitrary exceptions/stack/content/object serialization are excluded. Initiating failure fields survive cleanup observations. The inherited optional diagnostic-write failure behavior is unchanged and does not turn UNKNOWN watchdog state into success. No cleanup is guaranteed against OS failure or simultaneous parent/watchdog termination; unverified exact cleanup blocks export and requires separately reviewed manual emergency action.

The original runner retains accepted Selector, request15s, cleanup10s, assertions, first/second seed idempotence/no replay and original fixture. Application API/types, durable schema, connectors/business rules/mapping, product authorization/security owners, architecture/provider classification and product runtime behavior are unchanged. Only task-owned ETW mode configuration/validation changes. No .env, protected database, sponsor artefact, raw ETL or unrelated worktree access, Git publication or PR update occurred.

## Findings, limitations and next authority

No current blocker in the frozen helper-code correction scope. Existing conservative export rejection and unexecuted elevated ACL/filter/real child/session/capture behavior are limits on future execution claims, not demonstrated regressions in this mode-only correction. No product correction or release acceptance is justified. PR81 remains NOT READY FOR HUMAN MERGE.

**PASS only for this exact code/profile/test set.** Next permitted preparation is issuance and fresh independent review of the exact hash-bound administrator V6 SOP. Stop before Arm/Watchdog/live Query/Start/Enable/Stop, fixture launch, RunId reuse or raw ETL access. Further actual capture requires new owner coordinated authorization and a fresh RunId. This review neither executes nor authorizes a retry.

## Exact review binding

Review identity is SHA256 of sorted compact UTF-8 JSON below with no newline; raw report hash is supplied externally to avoid self-reference.

Review identity: 74c4daf2484556cbdbb18241e743f5d8cdfeba0ff30db1476b0f1ba0a3e328af

```json
{
  "branch": "feat/blocker-resolution-idp-ux-optimization",
  "bundle_sha256": "b072fb20d5002a9d94f7baef38204c4b5547ba2de64eece1e31c6446ab8150a7",
  "cached_main": "e799d74063678bb0eccbea445d5ab3c8628dd2c0",
  "fixture_executed": false,
  "frozen_manifest_content_identity": "14a0e1e9e969244719042245920f786e1aeede6ae485ec3484f3b00fda4d66f3",
  "frozen_manifest_sha256": "8888ad82038cc147aa42eb345654947dd86dc03f44205e1b2f2fd7a45100acde",
  "head": "dd8c36c8a911f4b5f3b80e7441d049f1aa976599",
  "independent_test_counts": {
    "actual_process": 6,
    "controller": 30,
    "mode": 50,
    "sanitizer": 19,
    "scanner": 8,
    "watchdog": 39
  },
  "merge_base": "e799d74063678bb0eccbea445d5ab3c8628dd2c0",
  "native_trace_control_executed": false,
  "preserved_count": 1175,
  "reviewed_paths": {
    ".ai-pipeline/reports/PR81_TCP_TRACE_CAPTURE_PROFILE_V6.json": "ce6dbe33f22388f215ccf18a7509a08538a386a905d1dc357b9eabdd904fb96f",
    ".ai-pipeline/reports/PR81_TCP_V6_HELPER_DIFF.txt": "4a107bbf6e77d4d28a700ac112df17b36002c2f7b05a8c7960053d377251295f",
    ".ai-pipeline/reports/PR81_TCP_V6_IMPLEMENTATION_PLAN.md": "a47d4b7737398f915e9fc4f68b9a1b8c440cd2d072f89b9d6dca8f08c5f2d137",
    ".ai-pipeline/reports/PR81_TCP_V6_IMPLEMENTER_HANDOFF.md": "f767e097282b59ee8125012b54ae7a17ccf49716a27b57305614f3a86fd36a06",
    ".ai-pipeline/reports/PR81_TCP_V6_IMPLEMENTER_VALIDATION.json": "e16083a9abc8c006dd76574287f42d40ed91126998bfe426372f652b8839cdc0",
    ".ai-pipeline/reports/PR81_TCP_V6_MODE_RESULTS.json": "a28c72cfadf3c9d9bf91104e3bf903eac065d627b1a1d86fd2b8d26817eb0c22",
    ".ai-pipeline/reports/PR81_TCP_V6_PRESERVATION_START.json": "a91803069d5a99e148a1af4e268e716ba61bf75d903462fa73251480a25af024",
    ".ai-pipeline/reports/PR81_TCP_V6_SYNTHETIC_RESULTS.json": "570515d4bac29e474c740359704ac6b7067bd4d7dea48ade1c24ba65eccc0384",
    ".ai-pipeline/reports/PR81_TCP_V6_WATCHDOG_RESULTS.json": "094f436d47668d45ffb63de9a54ab4c93591d3490731dd326a50029051bdcf95",
    ".ai-pipeline/reports/pr81-tcp-capture-v6/ControllerDiagnostics.ps1": "c954e974190f97e039de67a04286a4b1106582348b5a9a42b865f66fc42cb296",
    ".ai-pipeline/reports/pr81-tcp-capture-v6/DIAGNOSTIC_OUTPUT_SCHEMA.json": "aa66f7883a1ac49e5853f40a126187a0ad774f9dd57ad73fec6e361ed14d312c",
    ".ai-pipeline/reports/pr81-tcp-capture-v6/DIAGNOSTIC_STAGES.json": "8d2f69ba13c865d46450a187fb27922d41a3b35c1a4910e9de6645f1146cb213",
    ".ai-pipeline/reports/pr81-tcp-capture-v6/Invoke-Pr81TcpCapture.ps1": "bd46e6cc617ab0b07573448e24c9454345259583e811f13900e0b2e769c760e1",
    ".ai-pipeline/reports/pr81-tcp-capture-v6/NativeTcp.cs": "69ba283326e743afddd3a2e1ed5afc7b1fe576ecd751f2ec9c4c21d3544c8bff",
    ".ai-pipeline/reports/pr81-tcp-capture-v6/Run-FreshFixture.py": "3cb70d06728c8a64eeb9f66d94c3d2a33e7b707d63fc181cfcb634f4ff2ec871",
    ".ai-pipeline/reports/pr81-tcp-capture-v6/Sanitize-TcpTrace.ps1": "f4b67b37fc9980a4731698559ff0dbfbcdfc72cc1d85868ba79d0aad74c1392c",
    ".ai-pipeline/reports/pr81-tcp-capture-v6/Test-ControllerDiagnostics.ps1": "7b533ac0b89f5880c8a7b65b4648aa9e8dfcb9712dde1a0d5f7de6abfc98a346",
    ".ai-pipeline/reports/pr81-tcp-capture-v6/Test-LoggingModeSafety.ps1": "d12675adf3a538b36044cb9f97e0e42ed973df19dcf6714d9a0e87c6abad61ec",
    ".ai-pipeline/reports/pr81-tcp-capture-v6/Test-WatchdogSafety.ps1": "fab013506224bd5ff10bd545919d8fee5770ce62a12e5e1cfe0002bd241d5cf0",
    ".ai-pipeline/reports/pr81-tcp-capture-v6/bundle.json": "b072fb20d5002a9d94f7baef38204c4b5547ba2de64eece1e31c6446ab8150a7"
  },
  "scope": "V6 helper code/profile/tests only; no manual SOP, elevated execution or release acceptance",
  "source25_identity": "ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490",
  "source_hashes": {
    ".github/workflows/ci.yml": "09e1f4702f520d48e89e6bb91684d58ca8beba40900755164ace44801085a766",
    "apps/backend/app/api_models.py": "15d6b9f08112eed9055e6f94aa863f129446221e263af74c99976d50950e0923",
    "apps/backend/app/main.py": "a45be7fc76c667136a601812d0d02b9cd5793605f1a4f4e55250886b8b7a1a58",
    "apps/backend/app/services/zero_touch_orchestration.py": "f97556ae259bf7aeabedb6d08ff96b8c21f2b91cec69bf707023328c994ee411",
    "apps/backend/tests/test_document_refresh_recovery.py": "35171d0dcbad271e822c23562ffcbb21482ae5aff5938ae181a5f239a07b2578",
    "apps/backend/tests/test_final_review_editing_real_mongo.py": "ac8106f4e387e790114787221306c16bae9eeb482be3398609a4be7182de266c",
    "apps/frontend/e2e/blocker-review-performance.e2e.ts": "df4408f22eeeabec78338b14efdf44c5af732f762c274fe5533c2ed44b18377b",
    "apps/frontend/e2e/blocker-simulation.e2e.ts": "59275b4de4ec1fb5d9ba2c764e597451e15622ce6da8caa53856a08a7513eb60",
    "apps/frontend/src/App.tsx": "486631624f6e1ea8a6aa3bbb7c5bc4117b23957f11f5f24cfd8f0fd9f156bab3",
    "apps/frontend/src/DemoPerformance.test.tsx": "6472cd41c6a5ba3f99b51184bd415e9ec4ac8c510eb3794bcc3ac3079258cedb",
    "apps/frontend/src/ResumeDocumentRecovery.test.ts": "6c891c932ec6a06fcb363b37c1a5dec7d02e93ae383d8dc19d89469f9ff6a53d",
    "apps/frontend/src/api.ts": "6fec47d7215fdd5b256052ac942e8419afdf92b37dc2e7076643c5cd10e957e5",
    "apps/frontend/src/pages/CaseDetail.tsx": "259a28976f37beca416034b4af2efa82579e5d1c0222168fefee80edb1d1253c",
    "apps/frontend/src/pages/DocumentEvidencePanel.test.tsx": "622f50223bd668622374d2917ef092d00cd09e241bbb18c0cd922aa01b42fbba",
    "apps/frontend/src/pages/DocumentEvidencePanel.tsx": "474ede49c581c01b6b904b457356b5011ebee8573a51c2467ae4947553ea5941",
    "apps/frontend/src/pages/OnboardingWorkspace.tsx": "f04b24ae131bb941209c38bd18d53285a46deb0f2cbdf7effb3c395ddb65a21f",
    "apps/frontend/src/pages/S1PipelineWorkspace.test.tsx": "45db6bd50dd8f6c86aa777df22050d286e79bb35b1122fbddd8961700a720139",
    "apps/frontend/src/types.ts": "b2141cfb5068dfecb30707f79aeec0635254ed6e10d925a3aaea2197ad61119e",
    "docs/contracts/MULTI_DOCUMENT_INTAKE_PROFILE.md": "203ad8dfa7e4489c7a236d88f12119734810620be6e2499f97bc414331dd43c8",
    "docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md": "3fbf91c9641ef3382c7141901be1d786590260933ff7926101410fd364000c07",
    "scripts/e2e_backend_server.py": "2485c7f9f979f92b36c2cc789c0fec0f156cea71d9fbd5576dcecea0c272d981",
    "scripts/run_e2e.py": "1ca9ee2fc8dfa82aaf2156b7ddc4c9d8b901e99043c31890218cfb732eb1ee70",
    "scripts/slice_c_recovery_fixture.py": "e0dde54dd34c999f3309ae481e4b09e88d0532911af32d32af3727bec27984c9",
    "tests/test_run_e2e.py": "baa4bcb320d762ca593a72c08377d61e2a7e1f2c59d203f8f63db92a1511b39f",
    "tests/test_slice_c_e2e_fixture_routing.py": "219370b0a4547ce8881d4eef7bd9af5bcefa217d4ea4575cc3e2329b9cf390d9"
  },
  "verdict": "PASS"
}
```
