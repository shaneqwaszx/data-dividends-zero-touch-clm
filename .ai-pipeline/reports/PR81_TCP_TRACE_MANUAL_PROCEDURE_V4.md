# PR81 controlled native TCP capture: manual operator procedure

Status: BLOCKED. This V4 diagnostic candidate has two synthetic fail-closed criterion failures. Do not arm or execute this procedure. The commands below document the inherited operator procedure for review only. A new owner decision, corrected version and fresh exact independent PASS are required before any execution. This document does not authorize running the Codex application as administrator.

## Scope and preserved candidate

Use this Windows host only: installed build 10.0.26200.0, PowerShell 7 x64 and the existing worktree C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm. Branch feat/blocker-resolution-idp-ux-optimization, HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599, source25 identity ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490. No source edits, publication or release acceptance.

The V1 and V2 helper reviews remain FAIL; V3 remains preserved. V4 copies the exact V3 runner and sanitizer without changing bytes and reuses the same V2 capture profile and event schema. The only implementation delta is numeric controller/enable observation and shared synthetic test seams. The original V3 watchdog negation is preserved, including its newly demonstrated PowerShell getter-error ambiguity; V4 has not repaired it.

The controller uses one Microsoft-Windows-TCPIP manifest provider, an INCLUDE filter for 20 reviewed event IDs and 35 installed event versions. All 319 selected payload fields are numeric/boolean, opaque pointer identifiers or typed SocketAddress metadata. There are no selected HTTP body, credential, arbitrary packet-buffer or packet-header-snapshot fields. This is schema exclusion, not packet truncation. Raw ETL headers can retain host/user/path information and the selected host-wide metadata can include unrelated connections. Raw ETL must remain private; never upload it or send it to Codex.

A per-connection acquisition filter is not established for this kernel provider. The sanitizer exports only one fresh localhost tuple with both sides bound to the fresh fixture PID and unique TCBs; it omits addresses, pointers, other connections and rendered messages. Unknown fields/versions, ambiguous bindings, event loss or possible circular overwrite prevent export. For each endpoint, all1017/1033 start completions combined must contain exactly one event with the expected side role; an opposite-role start fails validation. Export also requires exactly one successful accept/connect completion, close request and disconnect completion, matching tuple/PID/nonzero ProcessStartKey, consistent process keys, ordered boundaries and no chosen-TCB row outside that interval. Duplicate same-tuple starts/ends, key conflicts or missing server send coverage prevent export. Even legitimate handshake/state events before completion can trigger this conservative rejection. Coverage cannot be promised; noexport means UNKNOWN and does not permit another run automatically. Native FIN delivery/state events are not proof of a wire FIN; incomplete delivery coverage stays UNKNOWN.

## V4 diagnostic output and blocking boundary

The V4 bundle SHA256 is b8cb37b9dba0f62759341f4a2c4b6a690378425002a79de611561adf0c8b891c. The safe diagnostic record schema is pr81-tcp-capture-v4/DIAGNOSTIC_OUTPUT_SCHEMA.json; additional fields are forbidden and every value is numeric, Boolean or null. null means UNKNOWN. Stages/categories and comparison-mask bits are fixed in DIAGNOSTIC_STAGES.json.

At the existing limits/watchdog/enable boundaries, V4 attempts fresh diagnostic-limits.json, diagnostic-watchdog.json and diagnostic-enabled.json in the task-owned control directory. On a managed abort it attempts diagnostic-abort.json. After stop/absence it attempts diagnostic-stopped.json. Maximum five files, each at most 16 KiB; FileMode.CreateNew rejects overwrites/reuse. No append, exception text, stack, HTTP body, native buffer, pointer, credential, host identity, machine name, process path or raw ETL is serialized. Existing stopped.json additionally contains only diagnostic_write_failed and nullable numeric diagnostic_write_hresult. A failed write is best-effort and cannot change the original guard outcome or bypass cleanup; a later available record carries the write failure. No available record is UNKNOWN, never evidence of success.

Limits records include query status, all seven returned numeric properties, ownership-match Boolean and each comparison. FailedComparisons bit0 is ownership and bits1–7 follow the seven bounds; LimitsGuard retains the original Code==0 && Owned && Bounds predicate. QueryCode nonzero with mask0 distinguishes query failure from a bound mismatch.

Watchdog records include object existence, observed-value-known, nullable alive value, the original guard Boolean, evaluation tick/deadline remaining and numeric HRESULT when available. A throwing PowerShell ScriptProperty may add a safe numeric Error record; a throwing CLR property getter can be swallowed by the PowerShell adapter without an observable exception. UNKNOWN is recorded in that case. V3's negation can turn the resulting null into a passing guard. This is a synthetic safety finding, not proof of the failed historical run's cause. Preserving it fails the owner's requested no-false-export tests; changing it would change V3 guard behavior and is outside diagnostic-only authorization. Do not run this V4 candidate.

Enable stages8–16 distinguish wrapper entry, data allocation, descriptor allocation, marshaling, native invocation attempt, native function return, wrapper return-code observation, original finally frees, controller assignment and original return-status guard. NativeAttempted is a managed invocation-attempt marker, not proof of physical native entry or completion. NativeReturned and a numeric NativeReturnCode differ from ControllerAssigned/ControllerReturnCode. Exceptions retain the initiating FailureLastCompleted/FailureAttempt/FailureCategory/HRESULT across cleanup and separately record stop/disable/absence statuses. A missing controller return never proves the native API was uncalled.

Synthetic tests use the same pre-enable/cleanup/export guards and the native enable core with a fake native return. No live ETW Start/Enable/Stop/Query, privileged controller, watchdog child or fixture is invoked. Two getter-error paths are expected to FAIL the required fail-closed assertions. Other failures are distinguished and cleanup remains attempted once with the original Guid/handle. The 19 unchanged sanitizer tests read no ETL.

Manual action is currently NONE: no fresh RunId, elevated session or fixture should be supplied. Preserve this blocked candidate and all prior evidence. The smallest next proposed correction is to evaluate watchdog liveness through an exception-observing owning operation and require a known Boolean result; it would need narrowly scoped owner authorization because it changes the demonstrated V3 exception-path decision, a new version and a fresh independent review. Applying that correction is not part of this V4 implementation.

## Open the manual administrator controller (BLOCKED; review template only)

1. On the same Windows computer, open Start and find the already installed **PowerShell 7 (x64)**. Select **Run as administrator** yourself and complete the Windows prompt. Leave Codex and the fixture process under their current ordinary token. Do not use Windows PowerShell 5.1: its current Restricted execution policy blocks these files.
2. In that separate elevated PowerShell 7 window, run the following. These commands inspect existing policy; they do not change it. If the shell is not Core/7/x64, or a policy blocks local scripts, stop. Do not change execution policy, unblock files or pass ExecutionPolicy Bypass.

```powershell
$PSVersionTable.PSEdition
$PSVersionTable.PSVersion
[Environment]::Is64BitProcess
Get-ExecutionPolicy -List
Set-Location -LiteralPath 'C:\Users\shane\.codex-clean2\worktrees\blocker-resolution-idp-ux\data-dividends-zero-touch-clm'
$reviewedBundle = 'b8cb37b9dba0f62759341f4a2c4b6a690378425002a79de611561adf0c8b891c'
if ((Get-FileHash -LiteralPath '.ai-pipeline/reports/pr81-tcp-capture-v4/bundle.json').Hash.ToLower() -ne $reviewedBundle) { throw 'Reviewed bundle changed: STOP' }
& '.ai-pipeline/reports/pr81-tcp-capture-v4/Invoke-Pr81TcpCapture.ps1' -Mode Validate
```

The expected existing PowerShell 7 policy is LocalMachine RemoteSigned with higher scopes Undefined. Validation currently FAILS with V4_SYNTHETIC_CRITERIA_FAILED. STOP there. A future independently accepted version must PASS; it compiles/checks schema and guards and runs synthetic sanitizer checks, without calling native trace control or executing the fixture. The helper verifies every bundle member and all 25 source hashes again on arming.

3. Generate a new RunId and arm the controller. Never reuse an old case, run directory, connection port or uncertain confirmation.

```powershell
$captureRunId = [Guid]::NewGuid()
& '.ai-pipeline/reports/pr81-tcp-capture-v4/Invoke-Pr81TcpCapture.ps1' -RunId $captureRunId
```

Expected message: ARMED followed by the fresh RunId. **No ETW session or provider is enabled at ARMED.** Send only that RunId to Codex while the helper is waiting. Arming expires after 300 seconds. An expiry performs no capture and no fixture run; report the expiry instead of starting a rerun without a new controlled authorization.

The operator window must remain open. Do not run a test manually, close Codex or terminate the fixture. Do not run the entire Codex application as administrator.

## Coordinated subsequent run

After the manually armed controller is actually available, Codex will invoke the reviewed Run-FreshFixture.py once under the current ordinary token, with the supplied fresh RunId. The helper verifies same-host fingerprint, PID, Windows process start time, approved Python executable hash and preserved source identity before starting trace. The runner waits for an active capture marker before it even imports/runs the fixture.

Only the original direct memory/Mock seeder fixture runs, once against its own fresh case set, retaining its first/second seed idempotence assertions, Selector setup, 15-second HTTP timeout and 10-second cleanup bound. Instrumentation reads actual accepted family/type/protocol through read-only SO_PROTOCOL_INFOW, exporting only the three numeric fields (not the provider/name buffer). Python socket.proto is labeled requested metadata. A getter/layout failure records numeric status and UNKNOWN and preserves the original write. It also reads local tuple, TCP_NODELAY and SO_LINGER; it does not set options or replay a failed confirmation. All response traces remain recorded as sanitized counts/fingerprints; selection for TCP export uses the first incomplete/failing response, or the first response if none fails. A successful rerun alone does not establish causality or a valid release candidate.

The runner command below is for Codex's subsequent ordinary-token run only; the operator must **not** execute it in the administrator window:

```powershell
& 'tmp/pr81-final-windows-checkout/.venv/Scripts/python.exe' '.ai-pipeline/reports/pr81-tcp-capture-v4/Run-FreshFixture.py' '<fresh RunId printed by ARMED>'
```

## Bounds, output and cleanup

The trace deadline is 45 seconds from controller/watchdog preparation, not 45 seconds after an arbitrarily delayed fixture. A separate hidden PowerShell 7 child inherits only the manually elevated controller token and acknowledges readiness within 5 seconds before StartTrace. It independently requests stop at that absolute deadline if the controller dies. Parent finally also stops early when fixture completion arrives. Neither helper requests elevation, installs a driver/service, changes groups, changes firewall/security settings or enables a system/WPR/PktMon/all-provider capture.

One session name PR81-Loopback-TCP-Metadata has the new RunId as Wnode.Guid. Any existing session causes an abort. Stop queries ownership, binds the returned native handle, checks that handle's GUID and stops by handle; it never globally stops or enumerates sessions. The fallback watchdog can obtain the handle from the queried owned session even if the parent dies before recording its handle.

The requested limits are 8 MiB circular ETL, 64 KiB buffers, 4 minimum/16 maximum buffers, no per-CPU reservation and one-second flush. Returned limits are checked before provider enable. Stop is requested no later than the monotonic deadline during normal scheduling. This is not a guarantee against a blocked native API, OS crash, or termination of both controller and watchdog; failures prohibit export and require the exact emergency check below. Start/query/enable/disable/stop/absence numeric statuses are recorded; uncalled operations remain null. A failed disable forbids export even if stop confirms absence. Stop/query statuses must prove absence, all loss counters must be zero and the conservative buffer-written bound must exclude possible overwrite.

Raw records stay under **the administrator operator's** LOCALAPPDATA/PR81TcpTrace/<RunId> on this same host. The fresh local directory rejects UNC/reparse ancestors and has inheritance disabled with only operator SID, LocalSystem and Builtin Administrators FullControl. Raw ETL never enters the repository/control directory.

Safe records go to this worktree's tmp/pr81-tcp-capture-control/<RunId>: armed/request/active/done/stopped status markers and, only after successful checks, sanitized.json. The sanitized export is at most 1 MiB and 4096 events and contains only run/profile/schema identity, known localhost ports/PID/correlation, timestamps, side aliases and selected numeric delivery metadata. The separate ordinary-token receipt tmp/pr81-tcp-native-<RunId>.json retains safe ASGI/client byte accounting and socket options, never response bodies.

Expected completion prints that raw records remain local/protected and the sanitized.json path. Give Codex only this independently validated sanitized metadata and numeric cleanup status; never attach ETL, event XML/messages, raw packet data, credentials or body contents. No export after a guard/cleanup/loss failure. Existing source/reports and earlier FAIL results are unchanged.

The watchdog exits at its original 45-second deadline even if the parent stopped early; it does not keep a session alive. There is no automatic file deletion. Keep raw files protected pending the operator's retention decision. Do not delete a parent folder or use broad cleanup commands.

## Emergency exact-session check

If absence is not confirmed, the operator must keep or reopen a separately elevated PowerShell 7 window on the same host. Use the **original RunId** only. If reopening, first repeat the exact bundle-hash check above and then load only the reviewed native type:

```powershell
# Reopened window only: set the worktree and verify bundle as above first.
# Set $captureRunId to the exact original ARMED Guid; never generate a replacement here.
if (-not ('PR81TcpV4.Native' -as [type])) { Add-Type -Path '.ai-pipeline/reports/pr81-tcp-capture-v4/NativeTcp.cs' }
$ownedStatus = [PR81TcpV4.Native]::Query($captureRunId)
if ($ownedStatus.Code -eq 4201) {
    'Exact named session absent'
} elseif ($ownedStatus.Code -eq 0 -and [PR81TcpV4.Native]::Owned($ownedStatus.Stats, $captureRunId)) {
    $cleanup = [PR81TcpV4.Native]::Stop($captureRunId, [uint64]0)
    $afterCleanup = [PR81TcpV4.Native]::Query($captureRunId)
    [pscustomobject]@{stop_code=$cleanup.Code;absent=($afterCleanup.Code -eq 4201)}
} else {
    throw 'Session is unqueryable or belongs to another Guid: STOP; do not touch it'
}
```

An absent result is 4201 (ERROR_WMI_INSTANCE_NOT_FOUND). On another GUID or access/stop error, stop and report only numeric status; do not use netsh trace stop, wpr cancel, logman stop, process killing or global session cleanup. Do not retry the fixture after an uncertain confirmation.

## Review and interpretation boundary

Consult PR81_TCP_TRACE_PROFILE_V2_SAFETY_REVIEW.md for the exact design/schema PASS and PR81_TCP_TRACE_HELPER_V4_SAFETY_REVIEW.md for the separate exact-helper verdict. Administrator access is needed for this selected operator procedure; alternative ETW logging identities exist, but this task makes no group/service/account changes. Host provider/schema and APIs are installed; actual privileged enable/filter behavior, elevated raw ACL creation/watchdog termination, exact returned limits, native accepted-socket option reads and per-connection event coverage have not been exercised in this preparation.

Server send acceptance is not acknowledgement. Calculate TCP transmitted/ACK ranges only if the fresh sanitized events provide complete same-connection coverage; otherwise retain UNKNOWN. A trace may fail or a rerun may pass without identifying the defect. No speculative correction, full acceptance, commit/push/PR update or merge follows automatically. **PR81 remains NOT READY FOR HUMAN MERGE.**

References: [ETW permissions and control](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/nf-evntrace-controltracew), [session handle and GUID](https://learn.microsoft.com/en-us/windows/win32/etw/wnode-header), [event filters](https://learn.microsoft.com/en-us/windows/win32/api/evntprov/ns-evntprov-event_filter_descriptor), [execution policies](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies).


Native protocol reference: [WSAPROTOCOL_INFOW layout](https://learn.microsoft.com/en-us/windows/win32/api/winsock2/ns-winsock2-wsaprotocol_infow), [Microsoft SDK option constant](https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/um/WinSock2.h). The full option buffer is transient and never persisted.
