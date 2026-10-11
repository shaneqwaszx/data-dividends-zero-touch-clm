# PR81 V5 single controlled attempt — STOP / incomplete capture
## Outcome and exact attempt
RunId ce820f5f-a85c-478e-b56c-adb23ccab76e. The ordinary-token reviewed runner was invoked exactly once and exited1: No active capture: fixture NOT EXECUTED. No fixture import/execution, synthetic case, target confirmation or TCP confirmation connection occurred. No retry or product/helper correction followed.
Bundle a6a1891b717dced37bc991363df1193526367a6f03532b9f6b2d108b72043e3d; source25 ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490. Same feature branch/HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached main/base e799d74063678bb0eccbea445d5ab3c8628dd2c0. Staging remains empty.
The later owner-provided RunId53967fe8-453f-4efd-a0f8-085a18b83cd1 was not invoked by this task. The one-attempt authorization is consumed and explicitly requires stopping after any control failure/incomplete capture. No second fixture-request was sent by this task.
## Proven initiating control failure
PROVEN for this V5 run: successful limits query returned LogFileMode272629762 / 0x10400002, but the exact reviewed profile/Native.Bounds predicate requires268435458 / 0x10000002. XOR difference0x00400000. No interpretation of the additional flag's origin/meaning or safe acceptance is asserted.
All other queried comparisons and ownership passed. FailedComparisons64 is bit6, the sole LogFileMode comparison. FailureLastCompleted5 (query/observations), FailureAttempt6 (original aggregate guard), FailureCategory1 (managed guard), HRESULT-2146233087 and native query status0 distinguish the managed guard failure from a failed native query.
Source location: pr81-tcp-capture-v5/ControllerDiagnostics.ps1 line69, QUERIED_LIMIT_MISMATCH, immediately after observing the query and before pre-enable watchdog/enable. The unchanged Native.Bounds exact LogFileMode check owns the failed predicate. No safeguard is weakened.
| Value | Required | Observed |
|---|---|---|
| Query code | 0 | 0 |
| Ownership GUID match | true | true |
| BufferSize | 64 | 64 |
| MinimumBuffers | 4 | 4 |
| MaximumBuffers | 16 | 16 |
| MaximumFileSize | 8 | 8 |
| NumberOfBuffers | <=16 | 4 |
| LogFileMode | 0x10000002 / 268435458 | 0x10400002 / 272629762 |
| EnableFlags | 0 | 0 |
WrapperEntered=false, NativeAttempted=false, NativeReturned=false and ControllerAssigned=false establish that the provider ENABLE wrapper/path was not reached in this attempt. Cleanup later invokes the same underlying EnableTraceEx2 API with DISABLE control; that does not mean the provider ENABLE operation ran.
## Watchdog/deadline contribution and cleanup
Readiness site24 recorded associated=true, exact identity=true, known Boolean=true, alive=true, guard=true, no property HRESULT/error. The pre-enable site7 was never reached because limits guard6 aborted first. These are the last readiness observations, not an assertion that an unmeasured later getter was evaluated.
Deadline353386218; finished tick353342343, remaining43875ms. Normal45s deadline expiration cannot explain the observed early guard failure. The capture deadline was assigned at353341218; the parent finish was1125ms later.
| Native status | Observed |
|---|---|
| StartTrace | 0 |
| Limits query | 0 |
| Provider enable | null / not reached |
| Snapshot query | null / not reached |
| Disable during cleanup | 1168 |
| Stop | 0 |
| Absence query | 4201 |
| capture_failed / cleanup_failed | true / false |
| absent | true |
Disable1168 occurred after the recorded guard abort, in exact-owned cleanup. It is a secondary cleanup disable result; it is not the initiating failure. Parent stop0/final query4201/absent=true prove the named session was removed at that final query. No new native session query or protected watchdog marker/ETL read was performed by Codex. The independent child retains only its reviewed deadline stop path; its later protected completion record was not accessed.
DiagnosticWriteFailed=false; all three diagnostic records passed exact schema validation and stopped.json passed a strict fixed numeric/status key/type check before analysis.
## Delivery evidence and unresolved scope
No active.json, fixture-done.json or sanitized.json exists for this attempt. No native TCP provider ENABLE occurred and no fixture ran, so server bytes accepted, TCP transmitted/acknowledged ranges, client bytes received, FIN/RST/outstanding bytes and confirmation EOF are unmeasured, not zero-valued success claims.
Underlying HTTP response-delivery cause remains UNKNOWN. Historical V3 guard/506-byte missing-response cause remains UNKNOWN; this V5 result does not retroactively prove historical values. No product correction is justified from this result.
Minimum next investigation, only under new owner authority: identify from supported Windows documentation why the additional0x00400000 mode bit was returned and assess its safety semantics against the fixed profile before proposing any separately versioned helper/profile correction. No mask, bound, provider, timeout, socket option, Selector or validation change is made now. Any changed helper requires focused adverse tests and fresh independent exact review; no rerun/fixture replay is implied.
## Safe evidence and preservation
Only these fixed task-owned records were accessed: armed.json, fixture-request.json, diagnostic-limits.json, diagnostic-abort.json, diagnostic-stopped.json, stopped.json. Diagnostic numeric/Boolean/null schema SHAaa66f7883a1ac49e5853f40a126187a0ad774f9dd57ad73fec6e361ed14d312c; source/RunId/profile bindings match.
Safe receipt: tmp/pr81-tcp-v5-controlled-stop-ce820f5f-a85c-478e-b56c-adb23ccab76e.json (validated record copies/hashes/presence). Single-invocation claim: tmp/pr81-tcp-v5-once-ce820f5f-a85c-478e-b56c-adb23ccab76e.json. Raw ETL and protected operator files were not read or exported.
All1142 historical preservation hashes, complete V5 reviewed bindings and source25 remain exact. No maintained source/report/helper edit, commit/push/PR update/merge, external provider or database action occurred. Only new task-owned single-attempt evidence/report files were created.
STOP. PR81 remains NOT READY FOR HUMAN MERGE.
