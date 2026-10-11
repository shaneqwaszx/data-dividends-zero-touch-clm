# PR81 V2 exact-helper independent safety review

Verdict: **FAIL - BLOCKED FOR CONTROLLED CAPTURE**. This separate verdict applies to the exact V2 bundle/manual bytes below. V1 profile PASS, V1 helper FAIL and V2 profile design-only PASS remain immutable. Neither Arm/Watchdog nor the fixture path is approved. PR81 remains **NOT READY FOR HUMAN MERGE**.

## Authority and preservation

The owner authorizes narrow preparation and independent review, with a stop before manual elevated capture, no source changes or publication. The reviewer did not implement this bundle, followed fyp-quality-gate read-only independence, and wrote only this assigned NEW report.

Worktree C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm; branch feat/blocker-resolution-idp-ux-optimization; retained HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached main e799d74063678bb0eccbea445d5ab3c8628dd2c0. No remote observation or Git mutation occurred in this gate.

Independently rehashed all1081 snapshot preservation paths and all25 maintained source paths: zero mismatches. Source identity ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490 remains unchanged. V1 helpers/SOP, previous gate reports and V2 profile/schema are frozen and explicitly bound. V2 bundle member hashes verify.

## Current blocking finding

**P1 - opposite-role native start events evade duplicate-start rejection.** In Sanitize-TcpTrace.ps1, the lifetime loop chooses beginId1017 for a server TCB or1033 for a client TCB and counts only that side-expected ID. An additional event using the other designated native start ID on the same TCB/tuple/PID/key is accepted if its timestamp is inside the approved interval. Thus a lifetime with both accept and connect start-completions is exported despite the V2 profile's rejection of duplicate same-tuple starts and ambiguous/reused lifetimes. This is a concrete conservative-attribution contract violation; no actual captured private record or transport defect is alleged.

Independent pure synthetic reproductions after dot-sourcing exact sanitizer -Validate:

- Its valid7-event selected connection plus Row1033/version1/TCB1 (server's already accepted TCB), local30101/remote30102, fixturePID30103, ProcessStartKey30104, UTC2026-01-01T00:00:02Z: Select-Connection accepts and exports8. The same TCB already has its required1017 at00:00:01Z.
- Its valid selected connection plus Row1017/version1/TCB2 (client's already connected TCB), local30102/remote30101, samePID/key, UTC00:00:02Z: accepts and exports8. The same TCB already has required1033 at00:00:01Z.

No guessed TCP state semantics are needed: both1017 and1033 are the profile's designated native beginning observations. The exact gate must account for all designated starts on each chosen TCB, require exactly one total and require that one's side-expected ID. A fresh revision and independent exact review are required; this reviewer made no fix.

## Earlier findings addressed in V2

V2 now rejects the old pre-lifetime1637 and two-close-only cases, requires successful native accept/connect plus exactly one close request/disconnect per chosen TCB, matching nonzero ProcessStartKey across endpoint observations, ordered timestamp intervals and no outside rows. Unknown/keyless/mismatched/conflicting or missing boundaries fail closed. A server send observation is required. These materially correct the prior retroactive attribution/missing-boundary behavior but do not override the current remaining contradiction.

The runner labels Python protocol metadata requested and obtains actual native family/type/protocol through read-only SO_PROTOCOL_INFOW0x2005. The ctypes definition matches the Microsoft SDK WSAPROTOCOL_INFOW/WSAPROTOCOLCHAIN field ordering, UTF16 fixed array256 and628-byte size, with offsets family76/type88/protocol92. Only three numeric fields are persisted; provider/name buffer stays transient. Getter OSError or bad length returns UNKNOWN with numeric error only, preserving subsequent original write. Independent exact --validate verifies these offsets, one synthetic valid buffer with private-name bytes excluded, three invalid sizes and getter-error UNKNOWN. No live socket read was performed. [Microsoft WSAPROTOCOL_INFOW](https://learn.microsoft.com/en-us/windows/win32/api/winsock2/ns-winsock2-wsaprotocol_infow) and [Microsoft SDK option/layout](https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/um/WinSock2.h) support this static ABI/option review.

Native Result now retains DisableAttempted/DisableCode. Controller records start, limit-query, enable, snapshot-query, disable, stop and absence-query numeric statuses; uncalled operations remain null. Failed disable prevents export even if stop succeeds. This addresses prior discarded primary statuses without private exception projection.

## Full procedure safety inspection

All four V2 helpers, bundle and complete SOP were read. The namespace is separate PR81TcpV2, avoiding V1 native-type collisions. Native x64 layout/filter compilation validates Stats120/Enable48. Setup uses only reviewed TCPIP provider, INCLUDE20 IDs, keyword0x0000409700000486, level5, properties/control flags0, version2/single descriptor,1000ms enable/disable, no system/all-provider/packet/WPR capture. Installed35 versions/319 fields remain the independently reviewed V2 schema; exact Validate again checks templates and levels. Runtime filter enforcement remains unexecuted.

Data exclusion follows selected typed schema, not packet truncation. Export omits pointer/address/ProcessStartKey/rawbinary/messages/XML; selected numeric/bool delivery fields remain. ETL control/header host/user/path metadata and host-wide other-connection metadata remain operator-local/protected. A per-TCB acquisition filter is unproven; correct conservative export attribution is therefore required before any controlled-capture READY verdict.

Manual SOP requires separate same-host PowerShell7 x64 administrator window, leaves Codex/fixture ordinary, and forbids policy bypass/UAC automation/group changes. Existing PowerShell7 RemoteSigned is supported; PS5.1 Restricted stays blocked. Controller validates host fingerprint, executable hash/PID/process creation time and source hashes. No driver/service/firewall/security/machine configuration change exists. [Microsoft controller permissions](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/nf-evntrace-controltracew) support the documented privilege boundary; actual elevated access was not acquired.

Fresh fixed-drive local raw directory/reparse ancestor checks and verified inheritance-disabled operator/SYSTEM/Administrators-only ACL precede StartTrace. ETL stays outside the repository/control directory. Circular8MiB/64KiB buffers4..16/NO_PER_PROCESSOR_BUFFERING/1s flush remain; returned limits checked before enable, zero losses and conservative overwrite guards required; export bounds<=4096 events/1MiB.

Arm waits<=300s without session/provider. Hidden inherited-token watchdog must report ready within5s before StartTrace; deadline45s assigned before child launch. Parent finally and independent watchdog use exact session name/fresh GUID, then original or queried session handle and rechecked handle-GUID, disable/stop by handle and require absence. Existing/foreign session aborts; no global stopping or process killing exists. Numeric failure records/noexport and exact original-RunId emergency instructions are present. Actual elevated ACL, parent interruption/session ownership races, watchdog/native blocking and termination remain untested; OS failure or both processes killed cannot guarantee cleanup.

Future runner remains one fresh canonical memory/Mock real-loopback seeder fixture under unchanged Selector/original assertions/request15s/cleanup10s, starting only after active marker checks. It does not replay historical uncertain confirmation or set socket options. It wraps ASGI/transport/socket accounting transiently; scheduling perturbation remains a limitation. No fixture execution occurred here.

The exact profile intentionally may reject legitimate handshake/state observations before completion or after disconnect. Noexport/UNKNOWN must remain final evidence rather than justification for arbitrary reruns or loosened attribution. Complete boundaries alone do not prove full TCP sequence/ACK coverage; native FIN delivery/injection is not wire FIN proof. Actual packet transmission/ACK/retransmission/FIN/RST/outstanding-close and root cause remain UNKNOWN.

## Independent validation evidence

- Exact V2 Invoke-Pr81TcpCapture.ps1 -Mode Validate: PASS exit0, schema/compile/source/layout/ownership/bounds/loss plus17 baseline sanitizer checks. Authorized nonprivileged read/compile only, no Windows token elevation/native trace control.
- Exact V2 Run-FreshFixture.py --validate: PASS exit0, parse/preservation/host/member hashes and synthetic protocol checks only.
- Additional selected-row cases: opposite start on server ACCEPTED8 and opposite start on client ACCEPTED8 (the blocking results above); keyless1017/version0 REJECTED PROCESS_KEY_MISSING; complete baseline with genuinely reversed input enumeration ACCEPTED7.
- An initial reversal command accidentally selected only the last and first rows using PowerShell range -1..0 and correctly failed CONNECTION_AMBIGUOUS_OR_UNBOUND. The corrected full-array reversal above passed. This command mistake provides no defect or runtime evidence.
- All preservation/binding hashes unchanged; assigned report whitespace checked explicitly.

The implementer's V2 validation receipt/log are separately bound and do not substitute for independent review. No raw ETL read, trace session, Arm/Watchdog, Start/Enable/Query/Control/Stop, fixture, real provider/database, settings change, Git/remote write or source correction occurred.

## Stop boundary

Do not manually execute this exact V2 bundle. A separate minimal preparation revision may correct the total-start ambiguity and receive a NEW exact independent review, using the unchanged V2 profile. Earlier failed reports and bytes must remain preserved. No maintained API/type, schema, connector, configuration, business rule, mapping, auth/security, architecture, provider status or runtime behavior changed. Historical506-byte deficit/causeUNKNOWN and earlier release FAIL remain; no capture/root-cause/release PASS is inherited.

## Exact reviewed binding

Review identity is SHA256 of sorted compact UTF-8 JSON below without newline; raw report hash is external.

Review identity: 4a1cbdecd0791b8737e7d56fe5278251c4aecea2c395ba75732e1dbf5498e7cc

```json
{
  "branch": "feat/blocker-resolution-idp-ux-optimization",
  "cached_main": "e799d74063678bb0eccbea445d5ab3c8628dd2c0",
  "head": "dd8c36c8a911f4b5f3b80e7441d049f1aa976599",
  "reviewed_paths": {
    ".ai-pipeline/001_planner/PR81_TCP_TRACE_PREPARATION_PLAN.md": "32116b527adcd3fc8ce43e71a9dedb64b9f8c924e356bdb0fc54a186ffb4fe67",
    ".ai-pipeline/reports/PR81_TCP_TRACE_CAPTURE_PROFILE.json": "e74975cef2a55384a2af3857a5dd162cda8292fba6b8a5eb6f7976c95d7f80cc",
    ".ai-pipeline/reports/PR81_TCP_TRACE_CAPTURE_PROFILE_V2.json": "74cea52445fe6f504e8859299f73a18f0976f00e53107daedaeabbe76f8760d1",
    ".ai-pipeline/reports/PR81_TCP_TRACE_EVENT_SCHEMA.json": "a67a8b36c9c46683af7700fc795ab172d5970fae420f6fceef10aae33f49f067",
    ".ai-pipeline/reports/PR81_TCP_TRACE_EVENT_SCHEMA_V2.json": "79c27947d2e0188a8e6f0c2cdc90329844f7e2f189d6966b2424cdf13dcc8e01",
    ".ai-pipeline/reports/PR81_TCP_TRACE_HELPER_SAFETY_REVIEW.md": "bae7923a82859e94e29e10e172d72740185dd4cd0b7572fd96dfbb70276accc5",
    ".ai-pipeline/reports/PR81_TCP_TRACE_MANUAL_PROCEDURE.md": "338ffd09afef8e0b9e3a6c5109bdd3391351cd8aa36c0138cdb3ec3f887e98ef",
    ".ai-pipeline/reports/PR81_TCP_TRACE_MANUAL_PROCEDURE_V2.md": "4faed58ca17b0684d6591a10e6dd73a3d494d117eb2631101c58ddb373417363",
    ".ai-pipeline/reports/PR81_TCP_TRACE_PROFILE_SAFETY_REVIEW.md": "850ba2d0cdba70c5c5ba4c7b38767d9b3c76f3c913792e38c78153cfbaa59c21",
    ".ai-pipeline/reports/PR81_TCP_TRACE_PROFILE_V2_SAFETY_REVIEW.md": "049ea47371f21df9e820a979ae248b7aeeaf25a32abf91cb487d656c35d16d39",
    ".ai-pipeline/reports/pr81-tcp-capture-v2/Invoke-Pr81TcpCapture.ps1": "bd1f3edf16bff3aa32774706cd0ad559f14aed873594189051d8764449c9c3b3",
    ".ai-pipeline/reports/pr81-tcp-capture-v2/NativeTcp.cs": "76dbce27bee9036437f982bc1fdaf58008f20d8750f2b0125c25732c0bf73e16",
    ".ai-pipeline/reports/pr81-tcp-capture-v2/Run-FreshFixture.py": "431466a2e139578928ba4de98cdb61ac682c06d6995242e07d0c75950c3c3776",
    ".ai-pipeline/reports/pr81-tcp-capture-v2/Sanitize-TcpTrace.ps1": "69b61440e79a2e72964b5e2cc644bf79a1df0ee1c8c7f61884ebc575f1e4c0aa",
    ".ai-pipeline/reports/pr81-tcp-capture-v2/bundle.json": "1d9d9aae9acd17d4cd69257beb496fa82d39ed76c229633cb6498c18fa4b0689",
    ".ai-pipeline/reports/pr81-tcp-capture/Invoke-Pr81TcpCapture.ps1": "f3c64712e584c0a49d5b4a1216c918554a664329ff1686a0babff207f0a19899",
    ".ai-pipeline/reports/pr81-tcp-capture/NativeTcp.cs": "d2dd7d13ff42b5d5a6c7c6ebc704240bc077b2e37160af68b22309f7d7053519",
    ".ai-pipeline/reports/pr81-tcp-capture/Run-FreshFixture.py": "0f5e3307a0f518639e0dcf4cb72cc13245cf486041f5eede5bf76ab6aca27cd2",
    ".ai-pipeline/reports/pr81-tcp-capture/Sanitize-TcpTrace.ps1": "6356841bca49305138359165449b44d5fd3bf1b0f8fdc66981680f9914f63c68",
    ".ai-pipeline/reports/pr81-tcp-capture/bundle.json": "4090ca46d93c9d9c79e863c2dc96f86bb423b6727d5e3ac73399d206a48ca402",
    "tmp/pr81-tcp-trace-preparation-start.json": "6944c98d5e59bfb3283c5fcdd1537b3e272d5f62730c46d9ca93cab0ba350690",
    "tmp/pr81-tcp-trace-preparation-validation-v2.json": "edf0548d7ec29e4cacdc3f72259a5882f385071118a16199c930e22e62a0946f",
    "tmp/pr81-tcp-trace-preparation-validation-v2.log": "5c960eff020e6647c8abd4f880eae9886dffb159b57337753521e0708868e504",
    "tmp/pr81_http_delivery_observe.py": "a6844511bf8512583366a860a8748d39865847ae882dbba275d7c79eee0496c7"
  },
  "scope": "Exact V2 helpers and manual procedure safety; no native runtime or release verdict",
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
