# PR81 V4 controller diagnostic independent safety review

Verdict: **FAIL - BLOCKED FOR MANUAL V4 CAPTURE** for frozen bundle b8cb37b9dba0f62759341f4a2c4b6a690378425002a79de611561adf0c8b891c and manifest content1dd7ba1172763ada4fe6da399337016b2153cbc3930a2031748eb7192845829e. Two required watchdog getter-error paths permit synthetic export eligibility with UNKNOWN liveness. Previous V3 preparation PASS is not inherited. **Do not arm V4 or run the fixture. PR81 remains NOT READY FOR HUMAN MERGE.**

## Scope, independence and preservation

The owner attachment2d31071c-a460-42ea-8fe9-b370354a7483 authorizes numeric diagnostic-only V4 enhancement, synthetic tests and fresh review, forbids elevated capture/fixture/product changes/publication, requires preserved capture decisions and simultaneously requires fail-closed getter-error/no-false-export evidence. Review followed fyp-quality-gate and integration-security-review, repository AGENTS and scoped CI_TOOLING context. The reviewer did not implement V4 and wrote only this assigned NEW report.

Worktree C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm; branch feat/blocker-resolution-idp-ux-optimization; HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached origin/main/merge-base e799d74063678bb0eccbea445d5ab3c8628dd2c0. Local identity/staging/whitespace reads ran; staging empty. No fetch or Git mutation.

Independently recomputed manifest content identity by sorted compact JSON excluding content_identity: exact match. All frozen file hashes and bundle member hashes match. All1124 explicit prior preservation hashes remain unchanged; no protected raw ETL was included/read. Source25 recomputes ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490. V4 runner and sanitizer are byte-identical to V3. Earlier profile/gates/helpers/FAIL records remain unchanged.

## P1 current blocker: UNKNOWN watchdog liveness passes the guard

ControllerDiagnostics.ps1 lines55-72 evaluates property HasExited, records whether the result is Boolean, but assigns WatchdogGuard=!exited regardless of that result's knownness. In the measured PowerShell7.6.5 adapter paths a throwing getter can produce null without reaching the surrounding catch. Negating null passes the guard, so enable/result assignment and synthetic export eligibility proceed without known watchdog liveness. Numeric UNKNOWN recording does not make the authorization fail closed.

Independent exact Test-ControllerDiagnostics.ps1 execution without OutputPath reports30 cases,2 failed, exit1. Exact Invoke -Mode Validate independently passes19 unchanged sanitizer checks then fails on the same30-case/2-failure diagnostic criteria, exit1. Fresh in-memory result inspection, with no receipt write, verifies:

| Case | Liveness known/alive | Guard | Export eligible | HRESULT | Simulated stop/query |
|---|---|---|---|---|---|
|10 ScriptProperty getter error|false/null|true|true|-2147467259|one/one|
|30 CLR getter error|false/null|true|true|null UNKNOWN|one/one|

Case10 fails NO_FALSE_EXPORT and WATCHDOG_PROPERTY; case30 fails NO_FALSE_EXPORT and CLR_GETTER_UNKNOWN_FAIL_CLOSED. Aborted=false in both; cleanup remains attempted exactly once with the bound Guid/handle and absence once. No actual sanitized export or capture was performed.

A separate independent probe used only an unassociated System.Diagnostics.Process object, never Start, and disposed it afterward. Property evaluation produced null/non-Boolean, no caught HRESULT and original negation=true. Explicit get_HasExited invocation produced no Boolean and caught deepest HRESULT-2146233079. This confirms a real Process getter boundary rather than only the two stand-ins. [Microsoft HasExited documentation](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.process.hasexited) documents InvalidOperationException for an unassociated process. This probe does not prove the historical watchdog object was unassociated or that this mechanism caused its abort.

The defect is inherited by the preserved V3-style guard, newly demonstrated by current required adverse evidence. It blocks fresh V4 acceptance even though diagnostic-only preservation is otherwise faithful. The earlier V3 report remains a historical static preparation verdict, not renewed runtime or safety acceptance for this new evidence.

## Scope and smallest proposed correction

Preserving the demonstrated exception-path decision and requiring no export after unknown getter liveness cannot both be satisfied by numeric-only instrumentation. Making UNKNOWN reject changes that exception-path behavior; it is a bounded owning-controller safety correction, not solely observability.

The next narrow authorization must explicitly permit exception-observing watchdog evaluation and rejection unless the object/result is valid and liveness is a known Boolean confirming alive, while preserving healthy/dead outcomes, source hashes, provider/filter/options/bounds/deadlines and exact-owned cleanup. Review all capture-critical HasExited read sites, including readiness/enable/wait, rather than creating another speculative owner or accepting an error-swallowed null. Keep numeric HRESULT when available and UNKNOWN otherwise. Require synthetic script/CLR/actual-unassociated-Process failures, healthy/dead/null paths, diagnostic-write failure and unchanged sanitizer tests, followed by a NEW independent exact gate.

The owner's generic bounded-remediation provision does not justify silently treating a behavior change as diagnostic-only against its explicit preservation requirement. Resolve this narrow authority conflict before dependent edits; this review implements no remedy and approves no capture. No product TCP/socket option/event-loop change or broadened release test is proposed.

## Complete semantic delta and diagnostic usefulness

Complete V3-to-V4 controller/native diff was inspected. Only new versioned helper observability, typed Diagnostic state, best-effort numeric recording and shared synthetic injection seams were added. Native Start/Query/Owned/Bounds/Complete/Disable/Stop, provider/filter arguments and allocation/finally ordering remain unchanged aside namespace. Runtime EnableOnly has no injection switch; TestEnable shares marshaling with a fake return and never invokes ETW. The inherited second-allocation-before-finally cleanup limitation is preserved, not fixed or attributed to the historical failure.

New limits output observes query status, all seven returned values, ownership Boolean, individual comparisons and mask. Code nonzero with comparison-mask0 is distinguishable from a property mismatch. Watchdog output separately records object/value-known/alive/original-guard, tick/remaining deadline and observed numeric error. Enable stages8..16 distinguish entry, data/descriptor allocation, marshaling, managed native-attempt boundary, native return, wrapper code, finally/free and controller assignment. NativeAttempted is a managed call-attempt marker, not proof of physical native entry; missing controller code does not establish the native API was never attempted. The first abort snapshot retains initiating completed/attempted/category/HRESULT across later cleanup; stop/disable/absence are separate.

These additive fields would narrow a future pre-enable abort if safe records are available. They cannot reconstruct historical returned values or replace missing historic evidence. All successful synthetic comparisons, query-status cases, enable boundary failures, assignment failures, stop/absence errors and diagnostic-write cases pass except the two named getter paths.

## Confidentiality, bounds and cleanup assessment

Reviewed every new Diagnostic field and exact output schema/stage table. Values are fixed-schema integer/Boolean/null only, with additionalProperties=false; no unrestricted messages/stacks/native buffers/pointers/HTTP/credential/host identity are serialized. HRESULT extraction unwraps numeric codes only; absent code is null UNKNOWN. The schema defines fixed stages0..22/categories0..9 and comparison bits0..7.

Writer uses at most five fixed fresh filenames, UTF8<=16KiB each, FileMode.CreateNew/FileShare.None, no append/overwrite. Write failures record Boolean/numeric status best-effort and are not capture authorization inputs. Independent in-memory test results confirm bounded writer/no-overwrite/schema checks pass; original abort plus logging failure retains failure/cleanup/noexport, and healthy logging failure preserves original eligibility. Temporary writer test uses its own random file outside the repository and removes only that file; no frozen receipt was written.

Raw ETL, operator ACL/local-path protections, shared safe control directory, host-wide selected metadata disclosure and strict per-connection sanitizer remain unchanged. Profile uses only reviewed TCPIP20 IDs/35versions/319 typed metadata fields, INCLUDE mask0x0000409700000486, parametersVersion2, property/control flags0 and timeout1000ms; no packet/all-provider/System/WPR recording. Actual installed template checks execute read-only in Validate; no native trace call occurs.

Arming300s, absolute capture deadline45s, raw8MiB, buffer64KiB/min4/max16/NO_PER_PROCESSOR_BUFFERING, queried limits, zero losses/overwrite rejection and sanitized4096events/1MiB remain. Same-host manual administrator PowerShell7 is separate from ordinary Codex/fixture; no automatic elevation, execution-policy bypass, account/driver/firewall/security changes. Exact session-name/freshGUID/handle-owned stop/finally and absence checks remain. Actual privileged behavior and watchdog/session cleanup are unexecuted in this review; the demonstrated UNKNOWN guard prevents current approval.

Copied runner preserves original Selector, request15/cleanup10, assertions/idempotence/no-replay and read-only native protocol/TCP_NODELAY/SO_LINGER observations. No option or event-loop changes. Copied sanitizer retains conservative start/close/end/key/lifetime/ambiguity guards and no wireFIN/ACK-total inference.

## Independent evidence and remaining limitations

| Check | Result |
|---|---|
|V4 synthetic test, no OutputPath|FAIL exit1;28/30 pass, getter cases10/30 fail|
|V4 exact Validate|FAIL exit1;19 sanitizer checks PASS, then diagnostic failures|
|Fresh in-memory results/writer inspection|writer PASS; both getter paths export_eligible=true confirmed|
|Actual unassociated Process probe|null property/true negation versus caught explicit-getter HRESULT; no process started|
|Project state / architecture|PASS / PASS|
|Canonical secret-scanner tests|8 passed|
|Canonical scan on explicit V4 reviewed files plus source25|0 findings; bounded scanner limitations remain|
|Ruff no-cache V3/V4 runners|FAIL: two identical inherited I001 findings per file, lines2/67; no new V4 lint regression|
|Tracked diff / explicit task-owned whitespace|PASS / zero findings|
|Frozen hashes/source25/1124 preservation|PASS|

Ruff failures are existing byte-identical import formatting issues, not fixed under the required copy preservation. No full business/backend/frontend/lifecycle/Mongo/pre-PR gate was appropriate: those owners are unchanged and fixture execution/publication are forbidden. Neither unexecuted evidence nor historical main CI supplies current PASS.

Historical RunId2dee5743-13fd-48f3-9fdd-c61388d64fdb remains Start0/query0/enable null/disable1168/stop0/absence4201, fixture never imported/executed and no confirmation sent. Its exact rejected condition remains UNKNOWN. The safe prior stop report confirms absence; no protected raw records were read or needed. Current getter evidence does not identify that historical cause, TCP transmission/ACK/FIN/RST or the prior506-byte missing-response cause.

## Final stop

**BLOCKED; no manual action or new RunId now.** Preserve this FAIL and candidate. Obtain the explicit narrow watchdog-guard correction authorization/authority resolution, make only that separately versioned bounded remedy, rerun focused adverse evidence and obtain fresh independent review. No source/product repair, capture, fixture replay, commit/push/PR update or merge follows.

No maintained API/type, persistence schema, connector, configuration, business rule, mapping, product auth/security, architecture, provider classification or runtime behavior changed. New local diagnostic schema/observability is the reviewed task scope only. PR81 remains NOT READY FOR HUMAN MERGE.

## Exact reviewed binding

Review identity is SHA256 of the sorted compact UTF-8 JSON below without newline. Raw report hash is external to avoid self-reference.

Review identity: 939987f1114fe40dc096ae3e5adcc7d309fdaf003bf980288ad87f7748308af4

```json
{
  "branch": "feat/blocker-resolution-idp-ux-optimization",
  "cached_main": "e799d74063678bb0eccbea445d5ab3c8628dd2c0",
  "frozen_manifest_content_identity": "1dd7ba1172763ada4fe6da399337016b2153cbc3930a2031748eb7192845829e",
  "head": "dd8c36c8a911f4b5f3b80e7441d049f1aa976599",
  "merge_base": "e799d74063678bb0eccbea445d5ab3c8628dd2c0",
  "owner_authority_sha256": "1312d8ddcbb50468c25dc991a949ee13bfb9488d09e879a6fbcef9f6cc3ed447",
  "reviewed_paths": {
    ".ai-pipeline/reports/PR81_TCP_CONTROLLED_CAPTURE_STOP_2DEE5743.md": "5961d24a09200963fcf6dae70252658fdf1e3641807da7f0c5ef2c434a164082",
    ".ai-pipeline/reports/PR81_TCP_TRACE_CAPTURE_PROFILE_V2.json": "74cea52445fe6f504e8859299f73a18f0976f00e53107daedaeabbe76f8760d1",
    ".ai-pipeline/reports/PR81_TCP_TRACE_EVENT_SCHEMA_V2.json": "79c27947d2e0188a8e6f0c2cdc90329844f7e2f189d6966b2424cdf13dcc8e01",
    ".ai-pipeline/reports/PR81_TCP_TRACE_HELPER_V3_SAFETY_REVIEW.md": "f70d45808740ea1cffb9375fd459ec791b3f1342adb10cf4f82017a01de96daf",
    ".ai-pipeline/reports/PR81_TCP_TRACE_MANUAL_PROCEDURE_V4.md": "1b02a69f8bf1d95571be50367b21a6d9e96fc5c363cd6905dee21ff03cb01fa9",
    ".ai-pipeline/reports/PR81_TCP_TRACE_PROFILE_V2_SAFETY_REVIEW.md": "049ea47371f21df9e820a979ae248b7aeeaf25a32abf91cb487d656c35d16d39",
    ".ai-pipeline/reports/PR81_TCP_V4_IMPLEMENTATION_PLAN.md": "5e237f495f252906c9cbeff3c494472d1f711e740b1cdadc9760359508789259",
    ".ai-pipeline/reports/PR81_TCP_V4_IMPLEMENTER_HANDOFF.md": "ad6a8f4414e5312338acb19b74cc55d09bbbc26c3e6eb1e6097de3e76eade3e2",
    ".ai-pipeline/reports/PR81_TCP_V4_IMPLEMENTER_VALIDATION.json": "29da41b305eb1a3058b4fea0b8bc0b5b0bebd8bb3901683730d433b7f5cf6d94",
    ".ai-pipeline/reports/PR81_TCP_V4_PRESERVATION_START.json": "ce781054e42e91b8c6c55743091c8d1d93bb2c3715e22e882e4c40e50dd6101e",
    ".ai-pipeline/reports/PR81_TCP_V4_REVIEW_MANIFEST.json": "e91193929961c41c18bfe235f2e5e6b575c75b13844729f17dbdd5790df7675c",
    ".ai-pipeline/reports/PR81_TCP_V4_SYNTHETIC_RESULTS.json": "b1f160aa60c3aca79f9089444b699f763903658f2d765d2e3bd1ce264bbf8d3e",
    ".ai-pipeline/reports/pr81-tcp-capture-v3/Invoke-Pr81TcpCapture.ps1": "e74c3d18745f7cace342cd5280f87b88a584993e74377f84d6093c11784aa618",
    ".ai-pipeline/reports/pr81-tcp-capture-v3/NativeTcp.cs": "d3e0a45ac6e8ca34ac6412418b7af6e67cdefcf1e188359260867a3f5281e1f1",
    ".ai-pipeline/reports/pr81-tcp-capture-v3/Run-FreshFixture.py": "431466a2e139578928ba4de98cdb61ac682c06d6995242e07d0c75950c3c3776",
    ".ai-pipeline/reports/pr81-tcp-capture-v3/Sanitize-TcpTrace.ps1": "f4b67b37fc9980a4731698559ff0dbfbcdfc72cc1d85868ba79d0aad74c1392c",
    ".ai-pipeline/reports/pr81-tcp-capture-v3/bundle.json": "aa6450f6fd60623bd2dc616d2e2706489eba0101b503e475ea95bc668f1cf78b",
    ".ai-pipeline/reports/pr81-tcp-capture-v4/ControllerDiagnostics.ps1": "87d66cf3bf924e7643ebc55e2aeb62bfce1a83f929efe32bd93c6ef53914164d",
    ".ai-pipeline/reports/pr81-tcp-capture-v4/DIAGNOSTIC_OUTPUT_SCHEMA.json": "4e74ec9b9f057a09003ac136c7b3873ab674fec10db4fb05a67ba8561143baf1",
    ".ai-pipeline/reports/pr81-tcp-capture-v4/DIAGNOSTIC_STAGES.json": "9d65686d674eea88bdaa7ad4ed98e884f7808b588696a64f5e34b9e235d4ee24",
    ".ai-pipeline/reports/pr81-tcp-capture-v4/Invoke-Pr81TcpCapture.ps1": "36d6ebf6ccef44f533a943a217dd10323f6373f2c088dc0b6871c9492efd12af",
    ".ai-pipeline/reports/pr81-tcp-capture-v4/NativeTcp.cs": "83ba9f83546002541b8a1a2a504faaf12eac7d7cd225c3401f9404593d0b9290",
    ".ai-pipeline/reports/pr81-tcp-capture-v4/Run-FreshFixture.py": "431466a2e139578928ba4de98cdb61ac682c06d6995242e07d0c75950c3c3776",
    ".ai-pipeline/reports/pr81-tcp-capture-v4/Sanitize-TcpTrace.ps1": "f4b67b37fc9980a4731698559ff0dbfbcdfc72cc1d85868ba79d0aad74c1392c",
    ".ai-pipeline/reports/pr81-tcp-capture-v4/Test-ControllerDiagnostics.ps1": "102ae771fc36dc7cb0388bdcb4fde1b632da1b4baf6c72442335aa85116085d7",
    ".ai-pipeline/reports/pr81-tcp-capture-v4/bundle.json": "b8cb37b9dba0f62759341f4a2c4b6a690378425002a79de611561adf0c8b891c"
  },
  "scope": "Fresh V4 exact diagnostic-only independent review; FAIL/BLOCKED; no capture",
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
