# PR81 V2 TCP capture profile independent safety review

Verdict: **PASS - V2 PROFILE/SCHEMA DESIGN ONLY**. This permits adapting new task-owned helpers for separate exact review. It does **not** make the procedure READY FOR CONTROLLED CAPTURE: exact helpers/SOP remain V1 and their independent FAIL remains binding. No capture or fixture execution is approved by this report.

## Scope and frozen state

This separate review addresses the owner's Privileged TCP Trace Preparation and Controlled Continuation request and the coordinator's explicit V2 design-only assignment. It follows fyp-quality-gate read-only independence. Only this new report is written; no source, helper, profile, earlier report, Git or host setting is changed.

Worktree C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm; branch feat/blocker-resolution-idp-ux-optimization; HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached main e799d74063678bb0eccbea445d5ab3c8628dd2c0. These are retained local identities, not a new remote observation.

Independently rehashed 1081 prior paths and source25: all unchanged. Source identity remains ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490. The old profile PASS and helper FAIL hashes remain unchanged; existing V1 helper files and SOP are explicitly bound below.

## Schema and acquisition findings

V2 adds only IDs1017 TcpAcceptListenerComplete and1033 TcpConnectTcbComplete, versions0/1. All original31 event definitions remain exactly equal to V1. The combined selection is20 IDs,35 installed versions,319 payload fields. Both new templates have numeric Status/ProcessId/Compartment, opaque Tcb, length-delimited Local/Remote SocketAddress; version1 adds numeric ProcessStartKey. No string, packet-buffer, body, raw TCP-header, credential or arbitrary binary field is added.

Independent read-only installed Get-WinEvent provider comparison on this same host confirmed all35 ID/version templates, task names and levels exactly match frozen V2 definitions, provider GUID2f07e2ee-15db-40f1-90ef-9d7ba282188a, and positive named-keyword OR0x0000409700000486. Allowed field types are UInt32/UInt64/Boolean/Pointer/Binary(SocketAddress only);319 counted. The initial comparison mistakenly compared numeric Task.Value to frozen task names; inspection of the installed metadata shape corrected it to Task.Name. The corrected comparison reports zero mismatches. No trace-control API or session was used.

The20-ID INCLUDE filter remains below the documented event-ID filter limit and uses the same manifest provider/one descriptor/version2 parameters. No unrestricted provider, packet capture or CaptureState request is introduced. [Microsoft event-ID filter documentation](https://learn.microsoft.com/en-us/windows/win32/api/evntprov/ns-evntprov-event_filter_event_id) supports that filter shape; actual provider enforcement remains unexecuted.

The same unavoidable limitation is explicit: acquisition contains selected metadata across the host, with no proven per-TCB capture filter. Kernel-provider PID filtering is not a substitute. Raw records, including ETL control/header identity/path metadata, remain local and protected. Sanitized scope must be implemented as an independently validated unique fresh connection filter; this profile alone cannot prove that implementation.

## Conservative lifetime contract

The new contract requires exactly one successful server accept1017 and client connect1033 for the fresh opposite loopback tuple, fixturePID, two unique TCBs and matching nonzero ProcessStartKey; one close request1038 and disconnect complete1043 per TCB; ordered boundaries. It rejects absent/keyless older versions, conflicting keys, duplicate starts/ends, same-tuple reuse and selected TCB rows outside the bounded interval. This directly responds to the prior proven retroactive attribution and missing-boundary defects. Successful Status must use the installed NTSTATUS field convention, not a guessed TCP state. An exact-zero STATUS_SUCCESS-only predicate can be a deliberate conservative gate, but must not claim that other NTSTATUS values are necessarily failures. [Microsoft NTSTATUS guidance](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/using-ntstatus-values) documents success and informational classes.

These are named event observations defining a conservative export interval. They do not prove actual TCB allocation/free times, packet delivery, acknowledgement or wire FIN. No OldState/NewState enum semantics are invented. Completion events may follow legitimate handshake/fast-path/state observations, so rejecting all selected-TCB rows before completion can make an otherwise fresh connection unexportable. Disconnect-complete may likewise precede other native events. Exactly-one requirements may also reject legitimate repeated native observations. Such rejection is an intentional conservative limitation: **no export/UNKNOWN**, not evidence of a transport defect or permission to loosen the filter.

Same PID/key and ordered boundaries improve attribution, but the future exact implementation must validate the fresh process/connection handshake, tuple direction, unique TCBs, timestamps/order and conflicting mappings together. No retrospective binding of outside rows, filtering away contradictory evidence, or numerical TCP total should be accepted. Missing runtime boundary coverage remains unavailable evidence. Complete connection boundaries alone do not guarantee complete sequence/ACK coverage; the retained contract correctly forbids totals before separate causal assessment.

## Unchanged safety controls and prerequisites

Static comparison confirms prior mechanism/provider, duration/size/buffer/permissions/protection/cleanup controls are unchanged. The selected procedure still requires a separately manually elevated PowerShell7 x64 on the failing Windows host, never administrator Codex, no automatic elevation/group/policy changes. Actual ordinary-token permissions remain insufficient; this review requests no privilege.

Protected fresh local raw directory with verified operator/SYSTEM/Administrators-only ACL, reparse/local-path checks and separate safe control folder remain required. Maximum circular output8MiB,64KiB buffers4..16 with NO_PER_PROCESSOR_BUFFERING, queried-limit guards,1s flush, zero loss and conservative no-overwrite checks remain. Export remains<=4096 events/1MiB and excludes raw pointers/addresses/ProcessStartKey/messages/XML.

Arming<=300s without provider/session, watchdog-ready<=5s before StartTrace, monotonic45s deadline, parent finally plus independent hidden watchdog, original-handle/GUID-owned stop and verified absence remain requirements. OS failure or killing both controllers cannot guarantee termination; owned-session emergency operator check remains necessary. [Microsoft ETW controller permissions](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/nf-evntrace-controltracew) supports the documented access roles, without implying this token can capture.

No Arm/Watchdog, Start/Enable/Query/Control/Stop, fixture, live provider/database, settings change, Git mutation or remote operation ran. Static installed schema and preservation checks alone cannot prove privileged filter/ACL/session/watchdog runtime behavior. No actual loopback event coverage or ACK/FIN/RST/outstanding-close evidence was measured.

## Remaining exact-helper gate

Before any manual READY verdict, adapt a new helper revision and independently review its exact bytes and SOP. Required checks include conservative lifetime/reuse/outside-boundary rejection, unknown/keyless/schema/length/PID/key rejection, numerical safe native-operation statuses, actual native accepted-protocol ABI validation, source preservation, watchdog/GUID/handle ownership and sanitized loss/size guards. Prior V1 helper FAIL cannot be inherited away through this design PASS.

Fresh diagnostic capture may still produce no usable export. FIN delivery/injection names do not establish literal wire FIN; absent native evidence stays UNKNOWN. Historical506-byte deficit and specific cause UNKNOWN remain unchanged. No maintained API/type, schema, connector, configuration, business rule, mapping, auth/security, architecture, provider status or runtime behavior changed. PR81 remains **NOT READY FOR HUMAN MERGE**; no release acceptance or publication is authorized.

## Exact reviewed binding

Review identity is SHA256 of sorted compact UTF-8 JSON below without newline. Report raw hash is external to avoid self-reference.

Review identity: e4a2bd35eb8a3a8c1319ffa68f160354ecbe5258ad4e52fae4a5622f78552240

```json
{
  "branch": "feat/blocker-resolution-idp-ux-optimization",
  "cached_main": "e799d74063678bb0eccbea445d5ab3c8628dd2c0",
  "head": "dd8c36c8a911f4b5f3b80e7441d049f1aa976599",
  "reviewed_paths": {
    ".ai-pipeline/001_planner/PR81_TCP_TRACE_PREPARATION_PLAN.md": "32116b527adcd3fc8ce43e71a9dedb64b9f8c924e356bdb0fc54a186ffb4fe67",
    ".ai-pipeline/reports/PR81_NATIVE_TCP_INDEPENDENT_ASSESSMENT.md": "77234eca5e806effb5db1fc44af8dc22c8d4442a0bd8d34275aff5cf4edc6055",
    ".ai-pipeline/reports/PR81_TCP_TRACE_CAPTURE_PROFILE.json": "e74975cef2a55384a2af3857a5dd162cda8292fba6b8a5eb6f7976c95d7f80cc",
    ".ai-pipeline/reports/PR81_TCP_TRACE_CAPTURE_PROFILE_V2.json": "74cea52445fe6f504e8859299f73a18f0976f00e53107daedaeabbe76f8760d1",
    ".ai-pipeline/reports/PR81_TCP_TRACE_EVENT_SCHEMA.json": "a67a8b36c9c46683af7700fc795ab172d5970fae420f6fceef10aae33f49f067",
    ".ai-pipeline/reports/PR81_TCP_TRACE_EVENT_SCHEMA_V2.json": "79c27947d2e0188a8e6f0c2cdc90329844f7e2f189d6966b2424cdf13dcc8e01",
    ".ai-pipeline/reports/PR81_TCP_TRACE_HELPER_SAFETY_REVIEW.md": "bae7923a82859e94e29e10e172d72740185dd4cd0b7572fd96dfbb70276accc5",
    ".ai-pipeline/reports/PR81_TCP_TRACE_MANUAL_PROCEDURE.md": "338ffd09afef8e0b9e3a6c5109bdd3391351cd8aa36c0138cdb3ec3f887e98ef",
    ".ai-pipeline/reports/PR81_TCP_TRACE_PROFILE_SAFETY_REVIEW.md": "850ba2d0cdba70c5c5ba4c7b38767d9b3c76f3c913792e38c78153cfbaa59c21",
    ".ai-pipeline/reports/pr81-tcp-capture/Invoke-Pr81TcpCapture.ps1": "f3c64712e584c0a49d5b4a1216c918554a664329ff1686a0babff207f0a19899",
    ".ai-pipeline/reports/pr81-tcp-capture/NativeTcp.cs": "d2dd7d13ff42b5d5a6c7c6ebc704240bc077b2e37160af68b22309f7d7053519",
    ".ai-pipeline/reports/pr81-tcp-capture/Run-FreshFixture.py": "0f5e3307a0f518639e0dcf4cb72cc13245cf486041f5eede5bf76ab6aca27cd2",
    ".ai-pipeline/reports/pr81-tcp-capture/Sanitize-TcpTrace.ps1": "6356841bca49305138359165449b44d5fd3bf1b0f8fdc66981680f9914f63c68",
    ".ai-pipeline/reports/pr81-tcp-capture/bundle.json": "4090ca46d93c9d9c79e863c2dc96f86bb423b6727d5e3ac73399d206a48ca402",
    "tmp/pr81-tcp-trace-preparation-start.json": "6944c98d5e59bfb3283c5fcdd1537b3e272d5f62730c46d9ca93cab0ba350690"
  },
  "scope": "V2 profile/schema design only; not exact helpers or capture",
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
