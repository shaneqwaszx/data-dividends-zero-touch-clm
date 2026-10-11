# PR81 privileged TCP trace preparation handoff

**READY FOR CONTROLLED CAPTURE PROCEDURE — independent V3 safety PASS, subject to the owner's manual administrator action. STOP before elevated capture.**

## Scope and exact candidate

This completes only the owner's requested preparation and independent safety validation. Elevated capture and the subsequent fresh fixture remain unexecuted pending the owner's separate manual action. No product correction or release acceptance is inferred.

Worktree: C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm.
Branch: feat/blocker-resolution-idp-ux-optimization.
HEAD: dd8c36c8a911f4b5f3b80e7441d049f1aa976599.
Cached origin/main and merge-base: e799d74063678bb0eccbea445d5ab3c8628dd2c0. No fetch/integration was performed in this preparation.
Source25 raw identity: ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490.
All1081 prior named source/evidence paths match the task-start snapshot. Existing23 tracked modifications and2 source additions remain unchanged; staging is empty. The original checkout and unrelated worktrees were not modified.

## Independently reviewed design and helpers

V1 design/schema PASS permitted initial helper generation; its independent exact-helper review then returned FAIL. Proven synthetic examples accepted an earlier TCB-only event retroactively and accepted only two close bindings without a lifetime. The review also identified Python requested protocol metadata and discarded native operation statuses. The V1 profile/helpers/SOP/FAIL report are retained unchanged. The separate V2 helper review found an opposite-side native start accepted on the same TCB; both directions reproduced it. Its helper/SOP/FAIL report also remain unchanged. V3 corrects that one proven ambiguity by counting all designated starts together and rejecting a different side role, under the unchanged accepted V2 profile.

V2 design/schema independently passed before its separate helpers were generated. It adds only TcpAcceptListenerComplete1017 and TcpConnectTcbComplete1033. There are20 selected IDs,35 installed event versions and319 payload fields. All are numeric, boolean, opaque pointers or length-limited typed SocketAddress metadata; no selected HTTP body, arbitrary packet buffer, credential or packet-header-snapshot field exists. Pointer/address fields are not exported. This exclusion is based on the actual installed manifest, not truncation.

V2 profile SHA256: 74cea52445fe6f504e8859299f73a18f0976f00e53107daedaeabbe76f8760d1.
V2 schema SHA256: 79c27947d2e0188a8e6f0c2cdc90329844f7e2f189d6966b2424cdf13dcc8e01.
Exact final V3 helper bundle SHA256: aa6450f6fd60623bd2dc616d2e2706489eba0101b503e475ea95bc668f1cf78b.
Final V3 independent review identity: ccba87f97f2e263d730144ddd99e1adad82ecb6e1a83ba3d0709cb893029d2b9.
Final V3 review raw SHA256: f70d45808740ea1cffb9375fd459ec791b3f1342adb10cf4f82017a01de96daf.

The standalone native controller uses only Microsoft-Windows-TCPIP, INCLUDE event filtering, level5, positive named keyword mask0x0000409700000486, properties0 and no kernel/WPR/PktMon/all-provider configuration. The current host is Windows10.0.26200.0. Native APIs and these installed schemas are available statically; actual privileged API behavior and event coverage are unexecuted.

## Confidentiality and connection scoping

Native per-TCB acquisition filtering is not established. A PID filter may suppress the kernel provider, so this procedure collects selected host-wide TCP metadata during its short interval. Raw ETL/container headers may retain host/user/path/session identity metadata and unrelated endpoint metadata. It is not connection-only acquisition and the whole ETL is not claimed free of identifying metadata. Raw files remain in the operator's protected local directory and never enter Codex.

Export requires one fresh localhost tuple/PID, exactly one successful server accept/client connect, one close request/disconnect completion per side, consistent nonzero ProcessStartKey, unique TCB bindings, ordered temporal intervals and server send coverage. Duplicate starts/ends, different keys, reused pointers, rows outside the interval, missing boundaries, unknown schemas, loss or possible overwrite yield no export. Raw pointers, addresses, process-start keys, event messages and protocol/provider name buffers are omitted.

The checks intentionally can reject legitimate handshake/state events preceding connect/accept completion. A controlled run may therefore produce no export and UNKNOWN. Complete identity boundaries alone do not establish full TCP ACK coverage, literal wire FIN or outstanding-byte totals.

## Manual privileges, bounds and termination

Use only PR81_TCP_TRACE_MANUAL_PROCEDURE_V3.md and pr81-tcp-capture-v3. The owner opens a separately elevated PowerShell7 x64 on the same Windows host and verifies the exact reviewed bundle. Codex/the fresh memory/Mock fixture retain the existing ordinary token. No helper invokes RunAs/UAC, changes account groups or execution policy, installs a driver/service or modifies firewall/security/network configuration.

Installed PowerShell7.6.5 Core has existing LocalMachine RemoteSigned and permits local validation. WindowsPowerShell5.1 is Restricted and blocked the initial script before execution. No policy was bypassed or changed.

ARMED waits at most300 seconds without creating/enabling a session. A fresh ordinary-token runner request binds same-host fingerprint, PID, process start ticks, Python hash and source identity. The hidden inherited-token watchdog acknowledges readiness before StartTrace. A shared monotonic deadline requests stop within45 seconds from preparation, with earlier parent finally/fixture completion stop. Requested8MiB circular ETL,64KiB buffers,4 minimum/16 maximum and one-second flush are queried before enable. Bounds adjustment causes abort.

One fixed descriptive session name has a fresh RunId GUID. Existing sessions cause abort; GUID checks and native handle binding protect exact owned stop. Parent and watchdog record numeric statuses; failure/absence uncertainty forbids export. An already stopped session can conservatively prevent export. OS/API blocking or loss of both processes is not guaranteed automatically recoverable; exact GUID-guarded emergency instructions are supplied. There is no global stop or automatic file deletion.

Raw: operator LOCALAPPDATA/PR81TcpTrace/<RunId>, fixed local non-reparse path, inheritance disabled, exact operator SID/System/Administrators permissions verified before trace. Sanitized: worktree tmp/pr81-tcp-capture-control/<RunId>/sanitized.json, at most1MiB/4096 events after all guards. Raw ETL/XML/messages must never be supplied to Codex.

## Focused validation and limits

Root's final V3 Mode Validate and runner --validate both returned0. Nineteen sanitizer synthetic checks exercised complete matching lifetime export, unrelated metadata exclusion, unknown ID/version, string/binary rejection, PID/key conflicts, missing beginning/end/send, duplicate same-side/opposite-side starts and end boundaries, before/after-lifetime events and TCB reuse. Native ABI/layout, GUID ownership, loss/overwrite and bounds checks passed. The628-byte WSAPROTOCOL_INFOW layout was checked at offsets76/88/92, with3 invalid-size cases and getter-error UNKNOWN behavior.

Future actual protocol observation uses read-only SO_PROTOCOL_INFOW and exports only family/type/protocol, marking failures UNKNOWN without changing the original write. Python socket.proto remains labeled requested metadata. TCP_NODELAY/SO_LINGER are read without setting options.

No trace-control call, raw ETL read, capture, elevated ACL creation/watchdog termination test, native socket option read, original fixture run or publication check was performed here. These validations establish preparation guards; they do not prove actual TCP delivery or cleanup on a live privileged session. The independent V3 reviewer separately ran both validation modes and the prior adverse cases, including reverse enumeration. All passed or rejected as required. Its verdict is PASS for these exact preparation bytes only.

## Historical forensic accounting, not a new capture

| Observation | Prior reproduced D1 failure | Current preparation |
|---|---:|---|
| Server native body bytes accepted |65786|No new run|
| TCP bytes transmitted |UNKNOWN|Unmeasured|
| TCP bytes acknowledged |UNKNOWN|Unmeasured|
| Client body bytes received |65280|No new run|
| Body deficit |506|Not a kernel outstanding count|
| FIN/RST |No client EOF; native packet evidence unavailable|Unmeasured|
| Outstanding bytes at timeout/close |UNKNOWN|Unmeasured|
| Root cause |UNKNOWN|UNKNOWN|
| Correction |None justified|No product change|

The prior D1 HTTP200 Content-Length65786 timed out under the original15-second deadline. Earlier relay/control PASS observations do not prove a transport cause and are not repeated. Historical SDQ-01 root cause remains unresolved, with its previous exact-candidate residual-risk record unchanged.

## Maintained behavior and next action

API/type, durable schema, connectors, business rules, mappings, auth/security ownership, architecture, provider classifications and maintained runtime configuration/behavior did not change. Selector, fixture assertions,15-second request timeout and10-second cleanup bound remain unchanged. The only additions are local diagnostic preparation tools/reports and their validation evidence.

The owner may follow the exact V3 manual procedure in a separately elevated PowerShell7 x64 on this host, verify the reviewed bundle, generate one fresh RunId and arm the controller. ARMED does not start tracing. Return only that RunId while the300-second arm window is active; only then may the subsequent ordinary-token fresh runner coordinate capture. No elevated/controller/fixture action has been performed in this preparation. Do not execute V1/V2 FAIL procedures.

A subsequent authorized runner uses fresh synthetic memory/Mock cases and one original first/second-seed idempotence fixture. It does not resend an uncertain confirmation. TCP acknowledged ranges must come from native ACK evidence, never send acceptance or empty user-space buffers. Missing coverage stays UNKNOWN. A causal correction requires authoritative evidence and separate focused adverse tests/fresh independent gate; no product implementation is approved by this handoff.

No commit, push, PR update or merge was performed. Earlier FAILs remain unchanged. PR81 is **NOT READY FOR HUMAN MERGE**. Full CI/acceptance/release blockers remain open; historical main CI is not candidate evidence.

## Evidence binding

PR81_TCP_TRACE_PREPARATION_MANIFEST.json binds all preparation paths, source25 hashes and the start snapshot's1081 prior hashes. Its content identity is SHA256 of compact sorted UTF-8 JSON without the content_identity property; the manifest excludes its own file hash. Independent verdicts bind their own exact path/source sets and do not inherit earlier PASS results.

Primary references: [ETW control and privilege](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/nf-evntrace-controltracew), [native session handle/GUID](https://learn.microsoft.com/en-us/windows/win32/etw/wnode-header), [event filter semantics](https://learn.microsoft.com/en-us/windows/win32/api/evntprov/ns-evntprov-event_filter_descriptor), [WSAPROTOCOL_INFOW](https://learn.microsoft.com/en-us/windows/win32/api/winsock2/ns-winsock2-wsaprotocol_infow).

