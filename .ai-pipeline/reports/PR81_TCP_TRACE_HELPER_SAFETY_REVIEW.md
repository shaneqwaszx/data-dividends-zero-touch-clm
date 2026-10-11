# PR81 exact TCP helper independent safety review

Verdict: **FAIL - BLOCKED FOR CONTROLLED CAPTURE** for the exact proposed bundle below. The separate profile/schema design PASS remains immutable. This review approves no capture, fixture execution, causal correction or release acceptance. PR81 remains **NOT READY FOR HUMAN MERGE**.

## Scope and preservation

The owner's current Privileged TCP Trace Preparation and Controlled Continuation request requires independent exact-helper review and stopping before manual elevated capture. Review followed the fyp-quality-gate read-only boundary. The reviewer did not implement the bundle and changed only this assigned new report.

Worktree: C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm. Branch feat/blocker-resolution-idp-ux-optimization; HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached origin/main e799d74063678bb0eccbea445d5ab3c8628dd2c0. No fetch or publication occurred.

Independent rehash: all 1081 preserved paths unchanged, all 25 source paths unchanged, identity ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490. Exact bundle/member hashes match. Read-only Git status confirms prior 23 tracked modifications, zero staged paths and retained two new source/test files; tracked diff whitespace check exits zero. Source remains intentionally uncommitted.

## Findings

1. **P1 - sanitized export does not enforce a fresh connection lifetime.** Sanitize-TcpTrace.ps1 lines 13, 44-58 maps ports/PID by raw TCB then exports every captured row with a selected TCB. It does not bound rows to a validated lifetime or check ProcessStartKey against the fresh process. Different-port reuse is rejected; same-binding reuse is not detected. Host-wide TCB-only metadata from an earlier lifetime can consequently be attributed to the task connection. No actual private record was captured: this defect is demonstrated with synthetic numeric metadata.

   Independent adverse case: dot-source the exact sanitizer -Validate; create Row 1637 version 0, TCB 1, UTC 2026-01-01T00:00:00Z, followed by its provided server/client Row 1038 version 1 bindings at 00:00:10Z and Row 1332 version 5 send at 00:00:11Z. Select-Connection accepts all four and exports the earlier TCB-only event. Result: exported=4, earlier_event_exported=true. This does not prove what that synthetic earlier event represents; it proves that the code cannot reject the unbounded attribution. A revised gate must reject reused, unknown or unvalidated lifetimes rather than retroactively assigning every identifier occurrence.

2. **P1 - missing boundary coverage is accepted contrary to the frozen profile.** The profile's sanitized_output_contract requires rejection of missing boundary coverage. Select-Connection requires only one PID-verified server TCB and one client TCB; it checks no begin/end/delivery coverage. Two provided Row 1038 close-request bindings alone return exported=2, without begin/send/ACK/termination evidence. Its existing positive fixture also has only close-request bindings plus send. The UNKNOWN observations text does not implement the required export gate. Conservative validated boundary criteria are required; unavailable coverage must remain BLOCKED/UNKNOWN and cannot support delivery totals.

3. **P2 - actual accepted Winsock protocol is not measured.** Run-FreshFixture.py line 56 records protocol=s.proto, the Python socket object's protocol metadata; zero may represent default construction. This is not a native read of the bound protocol. TCP_NODELAY/SO_LINGER are read-only getsockopt observations and no option mutation was found. Actual native protocol needs an explicitly validated SO_PROTOCOL_INFOW read-only ABI, or an UNKNOWN label with the unmet objective stated. No option-based correction is justified. References: [Python socket metadata](https://docs.python.org/3.12/library/socket.html#socket.socket.proto), [Windows bound protocol information](https://learn.microsoft.com/en-us/windows/win32/winsock/socket-options-and-ioctls-2).

4. **P2 - numeric failure accounting is incomplete.** NativeTcp.cs line 65 discards Disable's returned code. Invoke-Pr81TcpCapture.ps1 lines 102-110 turns start/query/enable failures into generic flags without persisting numeric native statuses. Stop code/final absence alone do not distinguish these failures. This violates the profile's numeric-status accounting contract; it is not evidence of failed termination. Preserve safe numeric operation statuses without private exception detail.

## Safeguards and limits reviewed

All four helpers, bundle and manual SOP were read completely. Native x64 declarations match WNODE_HEADER 48-byte, EVENT_TRACE_PROPERTIES 120-byte and ENABLE_TRACE_PARAMETERS 48-byte layouts. The INCLUDE event filter is 4+2*18 bytes with one descriptor. Setup selects only reviewed TCPIP IDs, keyword mask 0x0000409700000484, level 5, properties/control flags zero, timeout 1000ms and no packet/system/WPR/all-provider recording.

The installed selected schema consists of 31 versions and 285 numeric/boolean, opaque-pointer or SocketAddress fields. Validate checks installed templates/levels. Export skips raw pointer/address/process-start-key/PID payload fields and never renders messages or exports XML. ETL/control headers may include local host/user/path identity metadata and remain operator-local. No payload-free claim depends on packet truncation. Runtime event-filter enforcement remains unexecuted.

Raw acquisition is explicitly host-wide selected metadata: supported per-TCB capture filtering is unproven and documented PID filtering is unsuitable for the kernel provider. The export lifetime defect prevents approving the promised unique-connection sharing scope.

Arm/Watchdog require manual administrator PowerShell 7 Core x64, inherit the operator token, and contain no UAC/RunAs, execution-policy bypass or group changes. Ordinary Codex/fixture remains separate. Same-host MachineGuid hash plus Python executable hash/PID/start-time validate the requesting process. Ordinary token lacks administrator access; actual capture remains manual. Windows PowerShell 5.1 Restricted is correctly blocked rather than bypassed. [Microsoft ETW controller permissions](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/nf-evntrace-controltracew) supports the documented roles; no role changes are proposed.

Fresh fixed-drive local raw paths reject reparse ancestors; ACL inheritance is disabled and operator/SYSTEM/Administrators FullControl-only identity/rules are verified before StartTrace. Raw ETL never enters the shared control folder. Elevated ACL creation has not run.

Circular capture is 8MiB, 64KiB buffers minimum4/maximum16 with NO_PER_PROCESSOR_BUFFERING and 1s flush; exact returned limits are checked before enable. Loss/overwrite checks reject incomplete capture; export bounds are 4096 events/1MiB and decode input is 8MiB/32768 selected events.

Arming lasts at most300s without a session/provider. Before StartTrace a hidden independent watchdog must be ready within5s; an absolute monotonic45s deadline is assigned before launching it. Parent finally and watchdog both use exact name/fresh GUID ownership. Native Stop checks name/GUID, chooses original handle or documented Wnode.HistoricalContext, rechecks handle/GUID then disables/stops by handle. It does not issue name-only stop after ownership switches. [WNODE_HEADER](https://learn.microsoft.com/en-us/windows/win32/etw/wnode-header) documents the output session handle. Parent interruption/concurrent ownership and actual session termination have not been exercised. OS failure or killing both controllers cannot guarantee cleanup; the SOP's manual emergency check preserves original RunId and rejects foreign ownership.

The future runner imports/runs only after active-marker checks. It invokes one fresh canonical memory/Mock fixture with unchanged Selector, assertions, 15s request/10s cleanup and adds transient observation; no replay of the historical uncertain confirmation was found. No fixture ran in this gate, so preserved real runtime behavior remains unverified under capture.

## Independent checks

- Exact Invoke-Pr81TcpCapture.ps1 -Mode Validate: PASS, exit0, compile/layout/schema/source/ownership/bounds/loss plus9 baseline sanitizer checks. Initial sandboxed schema enumeration was denied; the exact authorized nonprivileged mode succeeded outside that filesystem sandbox. The Windows token was not elevated and no native trace control was called.
- Exact Run-FreshFixture.py --validate: PASS, exit0, reads/parse only.
- Exact sanitizer -Validate: baseline9 checks PASS; additional2 pure in-memory adverse cases exposed findings1/2. Neither case read ETL or invoked native tracing.
- Independent source/member/preservation hash checks PASS; report whitespace checked explicitly.
- No Arm/Watchdog, Start/Enable/Query/Control/Stop, fixture, privileged capture, settings change or Git mutation occurred.

The implementer's validation receipt/log are separately bound evidence, not independent acceptance. Actual privileged filter enforcement/returned limits, raw ACL, watchdog termination, ETL decoding and loopback coverage remain unexecuted. Fresh TCP transmission/ACK/retransmission/FIN/RST/outstanding-close evidence is unavailable. FIN delivery/injection events are not literal wire FIN proof; missing evidence remains UNKNOWN.

Historical D1 remains server kernel acceptance65786 versus client body receipt65280, missing506, no observed EOF and original timeout. This proves neither TCP acknowledgement nor a specific cause. Earlier forensic/overnight FAIL reports remain immutable; cause UNKNOWN, no accepted correction, no release PASS inheritance.

## Stop and next action

This exact bundle is BLOCKED before manual capture. A separate bounded revision may correct only new preparation helpers/procedure and receive fresh independent review of new exact bytes. Do not execute this bundle's Arm/Watchdog or fixture path. No maintained API/type, schema, connector, configuration, business rule, mapping, product security, architecture, provider status or runtime behavior changed. No publication or merge readiness follows.

## Exact binding

Identity uses SHA256 of sorted compact UTF-8 JSON below without newline; raw report SHA is external to avoid self-reference.

Review identity: 37804417cafdde900d95d470f552c4ff23047f58553aa9bf15de81a1719f73e1

```json
{
  "branch": "feat/blocker-resolution-idp-ux-optimization",
  "cached_main": "e799d74063678bb0eccbea445d5ab3c8628dd2c0",
  "head": "dd8c36c8a911f4b5f3b80e7441d049f1aa976599",
  "reviewed_paths": {
    ".ai-pipeline/001_planner/PR81_TCP_TRACE_PREPARATION_PLAN.md": "32116b527adcd3fc8ce43e71a9dedb64b9f8c924e356bdb0fc54a186ffb4fe67",
    ".ai-pipeline/reports/PR81_HTTP_DELIVERY_INDEPENDENT_ASSESSMENT.md": "6ed1a50cba0302bf81842ce5db0b49c4992309129845d525855527b09cbb7e8b",
    ".ai-pipeline/reports/PR81_NATIVE_TCP_INDEPENDENT_ASSESSMENT.md": "77234eca5e806effb5db1fc44af8dc22c8d4442a0bd8d34275aff5cf4edc6055",
    ".ai-pipeline/reports/PR81_NATIVE_TCP_STOP_REPORT.md": "8a68a18c50f6113d9dc472b8950bef968df70e70e0946f39569895dfe99030be",
    ".ai-pipeline/reports/PR81_TCP_TRACE_CAPTURE_PROFILE.json": "e74975cef2a55384a2af3857a5dd162cda8292fba6b8a5eb6f7976c95d7f80cc",
    ".ai-pipeline/reports/PR81_TCP_TRACE_EVENT_SCHEMA.json": "a67a8b36c9c46683af7700fc795ab172d5970fae420f6fceef10aae33f49f067",
    ".ai-pipeline/reports/PR81_TCP_TRACE_MANUAL_PROCEDURE.md": "338ffd09afef8e0b9e3a6c5109bdd3391351cd8aa36c0138cdb3ec3f887e98ef",
    ".ai-pipeline/reports/PR81_TCP_TRACE_PROFILE_SAFETY_REVIEW.md": "850ba2d0cdba70c5c5ba4c7b38767d9b3c76f3c913792e38c78153cfbaa59c21",
    ".ai-pipeline/reports/pr81-tcp-capture/Invoke-Pr81TcpCapture.ps1": "f3c64712e584c0a49d5b4a1216c918554a664329ff1686a0babff207f0a19899",
    ".ai-pipeline/reports/pr81-tcp-capture/NativeTcp.cs": "d2dd7d13ff42b5d5a6c7c6ebc704240bc077b2e37160af68b22309f7d7053519",
    ".ai-pipeline/reports/pr81-tcp-capture/Run-FreshFixture.py": "0f5e3307a0f518639e0dcf4cb72cc13245cf486041f5eede5bf76ab6aca27cd2",
    ".ai-pipeline/reports/pr81-tcp-capture/Sanitize-TcpTrace.ps1": "6356841bca49305138359165449b44d5fd3bf1b0f8fdc66981680f9914f63c68",
    ".ai-pipeline/reports/pr81-tcp-capture/bundle.json": "4090ca46d93c9d9c79e863c2dc96f86bb423b6727d5e3ac73399d206a48ca402",
    "tmp/pr81-tcp-trace-preparation-start.json": "6944c98d5e59bfb3283c5fcdd1537b3e272d5f62730c46d9ca93cab0ba350690",
    "tmp/pr81-tcp-trace-preparation-validation.json": "774445dcba6930245233a03da0d4305243780225ab8ff8e55768bae3f5f42d95",
    "tmp/pr81-tcp-trace-preparation-validation.log": "8bc182a078f8800d2ba994ec71fb1321b38ad93fd4d84b8882cb99aeae51fbbc",
    "tmp/pr81_http_delivery_observe.py": "a6844511bf8512583366a860a8748d39865847ae882dbba275d7c79eee0496c7"
  },
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
  }
}
```
