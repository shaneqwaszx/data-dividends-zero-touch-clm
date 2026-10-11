# PR81 V6.1 FIELD_COUNT independent STOP review

Verdict: STOP / incomplete native TCP evidence. PR81 remains NOT READY FOR HUMAN MERGE. This is an independent read-only diagnostic assessment of RunId ce2590f5-11d3-414a-9cee-b7ca50b980be, not a new helper approval or authorization to capture, replay or publish.

## Frozen scope and authority

Canonical worktree: C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm. Branch feat/blocker-resolution-idp-ux-optimization; HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached main/base e799d74063678bb0eccbea445d5ab3c8628dd2c0; staging empty. AGENTS.md, fyp-quality-gate and integration-security-review were read. Sole new output is this report. No application/API/schema/provider/configuration/Selector/socket/runtime behavior changes were made.

Reviewed bundle SHA256 53b6657eae510f4a022ea6d164bc1344b66f2f72563eb762709a792fed69422f and exact authoritative profile SHA256 ce6dbe33f22388f215ccf18a7509a08538a386a905d1dc357b9eabdd904fb96f verified. Reviewed Get-ExportInputs independently rehashed all bound members and source paths; Assert-ExportInputs passed profile/source/run/receipt/host/deadline/status/bounds/loss and strict capture schema bindings. All 25 source hashes, 1,175 historical hashes and 1,204 complete preservation hashes independently rehashed with zero mismatch. Source identity remains ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490. Previous review and failure artifacts remain unchanged.

## Original fixture and cleanup facts

| Fact | Independently checked result |
|---|---|
| Receipt original_pytest_exit / exit_code / fixture-done exit_code | 0 / 0 / 0 |
| Original fixture | The reviewed runner invoked only test_http_seeder_runs_twice_against_one_live_memory_backend; original pytest PASS |
| First and second seeds | Original assertions require created10/reused0, then created0/reused10, prioritised10 each |
| Confirmation results | Ten diagnostic traces: HTTP200, client RETURN, complete matching server/client body counts and fingerprints; original ConfirmingHttpSeedApi requires COMPLETED and MOCK_GOLDTIER_SUBMITTED |
| Selected r01 connection | Server52346/client52360; 64,208 body bytes accepted and received/returned |
| r02 | Complete 65,786 body bytes accepted and received/returned; historical 506-byte deficit not reproduced |
| Deadlines and no replay | Receipt15-second HTTP /10-second cleanup; no_replay true; original worker join10 and stopped-worker assertion retained |
| Start / limits / enable / snapshot | 0 / 0 / 0 / 0 |
| Disable / stop / absence query | 0 / 0 / 4201 |
| Capture failed / cleanup failed / absent | false / false / true |
| Loss counters | EventsLost0 / LogBuffersLost0 / RealTimeBuffersLost0 |
| Returned limits | BufferSize64KiB; Min4/Max16/Number4; MaxFile8MiB; mode0x10400002; EnableFlags0; BuffersWritten16; reviewed Bounds and Complete passed |
| Export | sanitized.json absent; operator reports no sanitized-export success message |

These are fresh safe-record checks, not historical-main CI. The receipt fingerprint matches fixture-done and all seven record identities match this RunId. Original target confirmations executed against fresh synthetic memory/Mock cases; MOCK_GOLDTIER_SUBMITTED is a Mock result, not real GoldTier interoperability. Recorded exact-owned stop and same-run post-stop query4201 establish successful session removal at that query. Operator additionally confirms the controller returned to its prompt with no retry. No later live trace query was performed or claimed by this reviewer. Native provider enable was reached successfully. The failure is subsequent sanitization, not provider enable or session cleanup. Capture_failed false describes pre-export native capture/cleanup, not complete successful evidence delivery.

## Proven abort and collection-shape defect

Owner-supplied safe final status: ErrorId FIELD_COUNT, HResult -2146233087, Sanitize-TcpTrace.ps1:20, condition `$row.Values.Count -ne $defs.Count`. Exact safe operator status record: .ai-pipeline/reports/PR81_TCP_V61_ce2590f5_OPERATOR_FINAL_STATUS.json (owner evidence, not independently rerun administrator exception).

The unchanged production row builder at Sanitize-TcpTrace.ps1:148 uses `Values=@($_.Properties|ForEach-Object {$_.Value})`. PowerShell enumerates returned byte arrays into scalar bytes. Select-Connection line19 builds one definition per template data field and line20 rejects the altered count, before any accepted export. Production property extraction differs from validation Row's List[object].Add/ToArray construction (lines90-103), which preserves each binary socket address as one value. The existing selection and new export-envelope regressions receive already-preserved rows, so they do not cover this production extraction defect.

Independent synthetic execution used actual saved 1017/version1 template with nine fields, two synthetic 16-byte IPv4 loopback address values and known dummy numeric fields. No ETL or actual events were read. The EXACT production Properties/ForEach-Object expression expanded nine property values to39 entries (seven scalar fields plus32 scalar address bytes). Passing that row to the unchanged Select-Connection threw FIELD_COUNT. A comparable seven-row complete-lifetime synthetic control using List[object].Add/ToArray preserved array values and passed, yielding seven selected safe events. This proves a reproducible collection-shape defect in the production builder without weakening any sanitizer check.

Installed Microsoft-Windows-TCPIP provider metadata was inspected via Get-WinEvent -ListProvider only. All35 allowed event/version templates exactly match saved authoritative schema templates and field counts;319 template fields total. No installed schema drift was found. This comparison does not prove every actual ETL event's Properties shape or exact offending event.

The captured offending event's ID/version, original property count and expanded Values count were not persisted in allowed safe records. Accordingly, the owning shape defect is PROVEN reproducible, but attribution of this exact capture's FIELD_COUNT to a particular event or exclusion of every alternate event-property decoding mismatch remains UNKNOWN. Do not label the native HTTP loss root cause proven: TCP transmitted/ACK ranges, FIN/RST and outstanding bytes remain UNKNOWN with no validated native export.

## Smallest defensible next action

Stop and preserve this consumed single attempt. No rearm, confirmation replay, raw ETL access, capture expansion, helper generation or code correction is authorized by this diagnostic request.

If the owner chooses another bounded helper-only remediation, the smallest evidenced correction is at the production row builder: preserve exactly one Value per EventProperty, including byte-array values, and add a regression exercising this real extraction expression rather than only prebuilt rows. Retain exact count equality, all type/socket-address/event/lifetime/loss/identity checks and export whitelist. A separately versioned candidate, independent review and fresh owner authorization would be required before any new elevated action. No application transport change is justified.

If exact failed-event attribution is required, the minimum additional safe guard diagnostic is numeric event_id, version, template_definition_count, EventProperties.Count and projected_Value_count at FIELD_COUNT (optionally binary-field count and expected fixed socket-address lengths). No values, addresses, pointers, event XML/messages, bodies or unrestricted exception dumps. These diagnostics are a proposal only; no instrumentation was added. Existing raw ETL is not inspected or reprocessed under this assignment.

Checks in this review: safe production provenance validation, all three preservation maps, installed provider-template comparison, isolated known-dummy production projection/control. Sanitizer -Validate was invoked twice while loading reviewed pure functions and passed existing19 checks each time; no full suite, controller, runner, trace-control or fixture was invoked. No accepted export was written during synthetics. Previous initial PASS does not cover this newly demonstrated extraction defect; native evidence readiness is blocked.

Safe evidence paths: tmp/pr81-tcp-capture-control/ce2590f5-11d3-414a-9cee-b7ca50b980be/{armed,fixture-request,active,fixture-done,stopped,capture-provenance}.json; bound receipt tmp/pr81-tcp-native-ce2590f5-11d3-414a-9cee-b7ca50b980be.json; historical immutable .ai-pipeline/reports/PR81_TCP_V61_CAPTURE_ce2590f5_STOP.{md,json}; frozen helper/schema/profile and PR81_TCP_V61_PRESERVATION_START.json. No protected raw ETL or operator-private record was accessed.
