# PR81 V6.1 manual administrator capture procedure

Use only with exact independent PASS in PR81_TCP_TRACE_HELPER_V61_SAFETY_REVIEW.md and PR81_TCP_TRACE_MANUAL_V61_SAFETY_REVIEW.md. This is a reviewed preparation handoff, not permission for Codex to execute capture or the fixture now. The owner must explicitly authorize and initiate a fresh coordinated run. Do not execute the capture sections in this preparation assignment. PR81 remains NOT READY FOR HUMAN MERGE.

## Exact reviewed package

Worktree: C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm.
Branch feat/blocker-resolution-idp-ux-optimization; HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached main/base e799d74063678bb0eccbea445d5ab3c8628dd2c0.
Preserved source25: ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490.
V6.1 bundle SHA256: 53b6657eae510f4a022ea6d164bc1344b66f2f72563eb762709a792fed69422f.
Code-gate SHA256: fc070130760ecd1754acf5cac026e1df989f4b3863f313f5edf8cdd3af3707eb.

All V2-V6 bundles, previous PASS/FAIL reports and failed attempts remain immutable. V6's final verdict is BLOCKED due to the stale V2 export-profile identity; its initial PASS does not authorize execution. Use only the separately corrected V6.1 bundle after both fresh independent gates PASS. This preparation authorization does not authorize execution; obtain a new coordinated single-capture authorization first.

V6 adds only explicit EVENT_TRACE_STOP_ON_HYBRID_SHUTDOWN to the requested/strictly validated logging mode: CIRCULAR 0x2 | NO_PER_PROCESSOR_BUFFERING 0x10000000 | STOP 0x00400000 = 0x10400002 (272629762). Returned mode must equal exactly 0x10400002; missing STOP, PERSIST substitution, STOP+PERSIST and every extra bit reject. V5 requested 0x10000002 and observed 0x10400002. Microsoft documents default STOP/PERSIST selection based on caller session when neither is requested: https://learn.microsoft.com/en-us/windows/win32/etw/logging-mode-constants . Installed SDK 10.0.19041.0 confirms the constants. Explicit STOP preserves the observed stop-on-hybrid-shutdown behavior; it does not enable persistent capture or change selected content.

V6.1 corrects the sanitizer-owned production provenance/envelope flow. It independently hashes the actual unchanged V6 profile bytes and requires the supported identity, bundle/member hash and request/armed/active/done/receipt/stopped/capture-provenance records to agree. Missing, modified, stale V2, unsupported or conflicting identities fail closed before raw event reading and before export. The runner changes only four safe metadata dictionary fields; fixture/transport/assertions remain unchanged. The parent writes a bounded numeric capture-provenance record only after the original cleanup/export gate passes, retaining owned RunId, returned bounds/loss counts, statuses and deadlines. No raw field or exception text is added.

Original Select-Connection/lifetime/event-field filtering and V6 Native/controller/watchdog/cleanup logic remain unchanged after namespace versioning. The typed watchdog binds the exact Process object/PID/creation tick; only associated exact identity and known Boolean HasExited=false allow continuation. Unknown/null/dead/getter error fails closed. Diagnostic format remains version5; the new CAPTURE_PROVENANCE_SCHEMA.json and SANITIZED_EXPORT_SCHEMA.json formalize the exact safe metadata and retained ten-field export envelope. Actual export tests exercise the production reader/writer, not only selection.

Old export profile identity was74cea52445fe6f504e8859299f73a18f0976f00e53107daedaeabbe76f8760d1. Corrected export is independently recomputable from the V6 profile bytes: ce6dbe33f22388f215ccf18a7509a08538a386a905d1dc357b9eabdd904fb96f. There is no V2 fallback or alternative meaning for profile_sha256.

## 1. Open a separate PowerShell 7 administrator window

On the SAME Windows computer as the actual failing fixture (installed build10.0.26200.0), open the already installed PowerShell 7 x64 from Start, choose Run as administrator yourself and complete the Windows prompt. Keep Codex and the later fixture ordinary. Do not run the entire Codex application as administrator.

Run these commands in that separate window. They inspect current policy and bindings; no policy is changed. Windows PowerShell5.1 is currently Restricted and unsuitable. If Core/7/x64/admin or local-script policy checks fail, STOP. Do not bypass/change execution policy, unblock files, change groups or install anything.

```powershell
$PSVersionTable.PSEdition
$PSVersionTable.PSVersion
[Environment]::Is64BitProcess
Get-ExecutionPolicy -List
if ($PSVersionTable.PSEdition -ne 'Core' -or $PSVersionTable.PSVersion.Major -lt 7 -or ![Environment]::Is64BitProcess) { throw 'PowerShell 7 x64 required: STOP' }
if (!([Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Separate manual administrator window required: STOP' }
Set-Location -LiteralPath 'C:\Users\shane\.codex-clean2\worktrees\blocker-resolution-idp-ux\data-dividends-zero-touch-clm'
$reviewedBundleSha = '53b6657eae510f4a022ea6d164bc1344b66f2f72563eb762709a792fed69422f'
$reviewedCodeGateSha = 'fc070130760ecd1754acf5cac026e1df989f4b3863f313f5edf8cdd3af3707eb'
$reviewedHelperDirectory = '.ai-pipeline/reports/pr81-tcp-capture-v6-1'
$reviewedIssuedSha = '73352bf12c61f7f0f2cb83056cbcf9ef89f6a7410f4a3f29d641127b48b76781'
if ((Get-FileHash -LiteralPath '.ai-pipeline/reports/PR81_TCP_V61_ISSUED_BINDING_MANIFEST.json').Hash.ToLower() -ne $reviewedIssuedSha) { throw 'Issued binding changed: STOP' }
$reviewedIssued = Get-Content -LiteralPath '.ai-pipeline/reports/PR81_TCP_V61_ISSUED_BINDING_MANIFEST.json' -Raw | ConvertFrom-Json
foreach ($boundPath in $reviewedIssued.reviewed_paths.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath $boundPath.Name).Hash.ToLower() -ne $boundPath.Value) { throw 'Reviewed path changed: STOP' }
}
if ((Get-FileHash -LiteralPath "$reviewedHelperDirectory/bundle.json").Hash.ToLower() -ne $reviewedBundleSha) { throw 'Reviewed bundle changed: STOP' }
if ((Get-FileHash -LiteralPath '.ai-pipeline/reports/PR81_TCP_TRACE_HELPER_V61_SAFETY_REVIEW.md').Hash.ToLower() -ne $reviewedCodeGateSha) { throw 'Code review changed: STOP' }
$reviewedPackage = Get-Content -LiteralPath "$reviewedHelperDirectory/bundle.json" -Raw | ConvertFrom-Json
foreach ($member in $reviewedPackage.files.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $reviewedHelperDirectory $member.Name)).Hash.ToLower() -ne $member.Value) { throw 'Reviewed member changed: STOP' }
}
$helperValidationOk = $false
try {
    & '.ai-pipeline/reports/pr81-tcp-capture-v6-1/Invoke-Pr81TcpCapture.ps1' -Mode Validate
    $helperValidationOk = $?
} catch { throw 'Helper validation failed: STOP' }
if (!$helperValidationOk) { throw 'Helper validation failed: STOP' }
& 'tmp/pr81-final-windows-checkout/.venv/Scripts/python.exe' -B '.ai-pipeline/reports/pr81-tcp-capture-v6-1/Run-FreshFixture.py' --validate
if ($LASTEXITCODE -ne 0) { throw 'Runner validation failed: STOP' }
```

Expected policy remains LocalMachine RemoteSigned with higher scopes Undefined. Validate must PASS: 30/30 controller cases,39/39 watchdog site/adverse cases,six actual Process checks,50/50 V6 mode/bounds/ownership cases,19/19 sanitizer selection regressions and51/51 actual export-envelope cases (3 positive/48 negative). It compiles/checks hashes, installed event schema, native layout and guards, without live trace-control, a child watchdog or fixture. The envelope tests create/delete only fresh synthetic safe JSON records and temporary exports; they do not read ETL or start a seeder. Runner --validate similarly checks only bindings/protocol layout. Neither command imports/runs the seeder fixture. Stop on any error; do not suppress a failed check.

## 2. Fresh coordination before manual arming

First arrange the next single fresh ordinary-token V6.1 runner with Codex under explicit owner authorization. Codex must verify the exact package/source and be ready to receive the RunId. This preparation assignment alone does not launch that runner.

In the same manual administrator window, after both exact independent gates and validation PASS, generate a NEW RunId and arm:

```powershell
$captureRunId = [Guid]::NewGuid()
& '.ai-pipeline/reports/pr81-tcp-capture-v6-1/Invoke-Pr81TcpCapture.ps1' -RunId $captureRunId
```

Expected output: ARMED followed by the fresh RunId. No ETW session/provider is started at ARMED. Send that RunId to Codex within the 300-second arming window. Keep the operator window open and Codex ordinary. Never reuse any earlier RunId, including 2dee5743-13fd-48f3-9fdd-c61388d64fdb, ce820f5f-a85c-478e-b56c-adb23ccab76e or 53967fe8-453f-4efd-a0f8-085a18b83cd1, an old directory, case, port or uncertain confirmation.

A missed window expires without capture/fixture. Stop and report expiry rather than repeat automatically. Only after the fresh ARMED coordination is actually available may the reviewed runner execute ONCE under the ordinary token. This command is for Codex's future authorized coordination, never the administrator window:

```powershell
& 'tmp/pr81-final-windows-checkout/.venv/Scripts/python.exe' -B '.ai-pipeline/reports/pr81-tcp-capture-v6-1/Run-FreshFixture.py' '<fresh ARMED RunId>'
```

Runner verifies same-host fingerprint, source/preservation and bundle, then sends a fresh request with its own executable/PID/start-time binding. Controller independently checks it. Runner waits for active.json before fixture import/execution and refuses insufficient remaining time. If active is absent or any request is failed/uncertain, do not retry that confirmation.

Only the original direct memory/Mock seeder test runs against fresh synthetic cases, preserving first/second seed idempotence, Selector, request15seconds/cleanup10seconds and no target replay. Accepted native protocol, TCP_NODELAY and SO_LINGER are read-only; no buffers/options/topology/event loop change. A passing rerun alone does not prove the HTTP/TCP cause.

## 3. Data exclusion and scope

V6 profile PR81_TCP_TRACE_CAPTURE_PROFILE_V6.json SHAce6dbe33f22388f215ccf18a7509a08538a386a905d1dc357b9eabdd904fb96f and schema PR81_TCP_TRACE_EVENT_SCHEMA_V2.json SHA79c27947d2e0188a8e6f0c2cdc90329844f7e2f189d6966b2424cdf13dcc8e01 select one Microsoft-Windows-TCPIP manifest provider,20 IDs/35 installed versions/319 numeric/Boolean/opaque-pointer/typed SocketAddress fields. Only the logging-mode STOP bit/description/revision changed in the profile; the INCLUDE event filter/mask/level/API flags are unchanged. No selected HTTP bodies, credentials, confidential payloads, arbitrary packet buffers, packet-header snapshots, strings, SID/TSID or stacks. Payload exclusion is verified from event schemas, not packet truncation.

Acquisition contains selected TCP metadata across the host; no connection-only acquisition filter has been established. Raw ETL headers may contain host/user/path metadata. Never attach, copy to the repository or expose raw ETL, XML/rendered messages, native buffers/pointers or packet data to Codex.

Raw files stay under the administrator operator's LOCALAPPDATA/PR81TcpTrace/<fresh RunId> on the SAME host: fresh fixed local drive/no UNC/reparse, inheritance disabled and verified operator/SYSTEM/Administrators FullControl only. No driver, service, firewall, account, group, execution-policy or machine-wide network/security changes are made. Helpers never request UAC/RunAs.

## 4. Bounds and exact-session cleanup

Arming300seconds; readiness5seconds; absolute capture45seconds assigned BEFORE hidden watchdog launch; raw8MiB circular,64KiB buffers/min4/max16, no per-CPU reservation, flush1second. Returned limits must match before enable, including exact LogFileMode0x10400002; no normalization/mask/extra-bit allowance. Original HTTP15/cleanup10 bounds remain.

The parent pins the exact child returned by Start-Process. The independently running child inherits the operator token, verifies package/source/schema and fresh RunId/deadline, and acknowledges readiness in protected raw metadata. Unknown identity/liveness blocks readiness BEFORE StartTrace. Unknown liveness after StartTrace blocks enable or remaining wait/export and still runs original finally-owned stop and subsequent absence check. The independent child requests termination at the absolute deadline if parent dies; no unrelated process is killed.

Only descriptive session PR81-Loopback-TCP-Metadata with fresh Wnode.Guid/RunId is owned. Any existing session causes refusal, not takeover. Stop checks GUID, pins/requeries owned handle, disables this provider and stops by owned handle. Parent and watchdog both retain the original ownership checks. Query must prove absence4201; disable/stop errors prevent export even if absence later succeeds. This is not a guarantee against blocked native API, OS failure or loss of both parent/watchdog; use exact emergency check below if cleanup is unverified.

The child exits at its original deadline even if parent stopped early; it does not keep a session alive. No automatic raw deletion occurs. Retention belongs to the operator. Do not use broad parent-folder/process/session cleanup.

## 5. Safe output and interpretation

Task control folder: tmp/pr81-tcp-capture-control/<fresh RunId>. Existing armed/request/active/done/stopped markers remain. V6.1 retains the exact V5 diagnostic field/schema format version5; the stages map describes the V6 expected mode. Diagnostics use DIAGNOSTIC_OUTPUT_SCHEMA.json and DIAGNOSTIC_STAGES.json: integer/Boolean/null only; null means UNKNOWN; no unrestricted exception messages/stacks, HTTP, raw buffers/pointers, credential or host identity. Private watchdog object/PID/creation ticks never serialize.

Up to six fixed diagnostic filenames, each<=16KiB/CreateNew/no append/overwrite: diagnostic-arm-abort.json (prestart rejection), diagnostic-limits.json, diagnostic-watchdog.json, diagnostic-enabled.json, diagnostic-abort.json and diagnostic-stopped.json. Healthy readiness/wait probes are in-memory; failures/final status retain them. Write failures are best-effort Boolean/numeric and cannot bypass liveness, original failure or cleanup; missing/partial records are UNKNOWN.

After the original successful cleanup/export gate, one additional fixed capture-provenance.json contains numeric bounds/loss/status/deadline and safe RunId/source/profile/schema identities only. It is bounded by the exact CAPTURE_PROVENANCE_SCHEMA.json/16KiB reader limit. Any missing/incomplete record, failed native status/cleanup/absence, loss/overwrite or identity conflict rejects export. Parent cleanup remains completed before this record or sanitizer is invoked.

Limits stages5/6 report query code, seven actual returned properties, ownership Boolean and individual comparison-mask bits, preserving exact aggregate. Watchdog stages7/23/24/25 report association/identity/knownness/liveness/error/site/tick/remaining deadline. Enable stages8..16 distinguish entry, two allocations, marshaling, managed native-call attempt, native return, wrapper-code observation, original finally frees and controller assignment. Last/current failure stages/category/HRESULT survive stop/absence updates. Missing controller return does not prove native API was never entered. NativeAttempted is a managed attempt marker, not physical API-entry proof.

Only after successful complete cleanup/bounds/loss/fixture/lifetime/schema checks can sanitized.json export<=1MiB/4096 events for one unique fresh localhost tuple/PID/two TCBs. Same nonzero ProcessStartKey, exactly-one side-correct start/close/disconnect, ordered interval and no chosen-TCB rows outside it are mandatory. Missing/ambiguous/reused/keyless/unknown-schema/overwritten/lost coverage prevents export. Legitimate pre-start handshake rows may be conservatively rejected. Export excludes raw addresses/pointers/keys/strings/messages and unrelated connections. The ordinary receipt tmp/pr81-tcp-native-<RunId>.json contains safe ASGI/client counts/fingerprints/options only.

Give Codex only independently schema-validated numeric diagnostics/status and sanitized metadata. Validate sanitized.json against the exact reviewed SANITIZED_EXPORT_SCHEMA.json, recompute the authoritative V6 profile hash from its bytes and require it equals bundle/profile and all matching capture records; validate capture-provenance.json against CAPTURE_PROVENANCE_SCHEMA.json before sharing. Safe receipt remains bounded to1MiB; it now explicitly records the same profile identity. Do not share raw ETL or unrestricted receipt content.

Complete capture metadata may describe an original HTTP fixture failure; that does not claim HTTP success, override an owner stop boundary or authorize another confirmation. Fixture results and delivery causality remain separate from metadata provenance. No export or failed trace is not permission to retry. Server send acceptance is not ACK. Transmission/ACK ranges, retransmissions, FIN/RST/outstanding bytes remain UNKNOWN unless complete uniquely correlated evidence supports them; selected FIN-delivery/injection events are not proof of literal wire FIN. Historical V3 abort and underlying506-byte HTTP loss remain unresolved. The V5 mode-guard failure is now identified; actual V6.1 native returned mode is untested until a separately authorized capture.

## 6. Emergency exact-owned-session procedure

If cleanup/absence is unverified, use a separately elevated PowerShell7 window on this SAME host. In a reopened window, repeat section1's version/policy/known bundle AND all member checks before loading native code. Set captureRunId to the EXACT ORIGINAL ARMED Guid, never a newly generated one. Use only:

```powershell
# Reopened window: repeat section1 integrity checks first.
# Set $captureRunId to the exact original ARMED Guid; do not generate a replacement.
if (-not ('PR81TcpV61.Native' -as [type])) { Add-Type -Path '.ai-pipeline/reports/pr81-tcp-capture-v6-1/NativeTcp.cs' }
$ownedStatus = [PR81TcpV61.Native]::Query($captureRunId)
if ($ownedStatus.Code -eq 4201) {
    'Exact named session absent'
} elseif ($ownedStatus.Code -eq 0 -and [PR81TcpV61.Native]::Owned($ownedStatus.Stats, $captureRunId)) {
    $ownedCleanup = [PR81TcpV61.Native]::Stop($captureRunId, [uint64]0)
    $afterCleanup = [PR81TcpV61.Native]::Query($captureRunId)
    [pscustomobject]@{stop_code=$ownedCleanup.Code;disable_attempted=$ownedCleanup.DisableAttempted;disable_code=$(if($ownedCleanup.DisableAttempted){$ownedCleanup.DisableCode}else{$null});absence_code=$afterCleanup.Code;absent=($afterCleanup.Code -eq 4201)}
} else {
    throw 'Unqueryable or foreign Guid: STOP; do not touch it'
}
```

Report only numeric cleanup states. Do not globally stop/enumerate sessions, use netsh trace stop/wpr cancel/logman stop, kill unrelated processes or replay the fixture.

## Review and stop boundary

Independent helper-code gate PASS is limited to exact V6.1 bytes and tests. Final manual-procedure gate must separately PASS for this exact SOP/issued manifest; verify their raw hashes against the final owner handoff/manifest before manual action. Neither proves actual administrator ACLs, native filter/limits, child watchdog/termination, useful event coverage, TCP causality or release acceptance. The owner must perform manual action on the same host; Codex remains ordinary and stopped until fresh authorized coordination.

No maintained application changes, full PR acceptance, commit/push/PR update/merge or real ACRA/GoldTier writes follow. PR81 remains NOT READY FOR HUMAN MERGE.

