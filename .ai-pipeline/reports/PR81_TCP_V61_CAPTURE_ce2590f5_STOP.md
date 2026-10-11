# PR81 V6.1 single controlled capture: incomplete evidence stop

RunId ce2590f5-11d3-414a-9cee-b7ca50b980be. Exactly one reviewed ordinary-token runner execution completed with exit0; original pytest selector passed. No retry. **STOP: sanitized TCP export is absent; PR81 remains NOT READY FOR HUMAN MERGE.**

| Validated observation | Result |
|---|---|
| First/second seed fixture and original assertions | PASS in this one instrumented run; original HTTP15s,cleanup10s,Selector/read bound retained |
| HTTP confirmation accounting | 10 complete response bodies; all client/server counts agree |
| Selected connection | d1-native-ce2590f5-11d3-414a-9cee-b7ca50b980be-r01; server52346/client52360; fixture PID42268 |
| Server body bytes accepted | 64,208 |
| Client body bytes received/returned | 64,208 |
| TCP bytes transmitted/acknowledged | UNKNOWN; no validated sanitized TCP event export |
| FIN/RST/outstanding bytes | UNKNOWN |
| Start/limits/enable/snapshot | 0/0/0/0 |
| Disable/stop/absence query | 0/0/4201 |
| CaptureFailed/CleanupFailed/Absent | false/false/true |
| Loss counters | EventsLost0,LogBuffersLost0,RealTimeBuffersLost0 |
| Returned logging mode | 0x10400002; all comparison guards PASS |
| Capture metadata/profile/source validation | PASS through reviewed Assert-ExportInputs and strict capture schema |
| Sanitized export/final sanitizer status | Export absent; final operator status not yet supplied |
| Exact export failure identifier/numeric code | UNKNOWN; no such failure recorded in the validated control records |
| Historical506-byte deficit/root cause | Not reproduced / UNKNOWN |

Recorded exact-session absence is confirmed by the same-run post-stop native query4201. No later live query is claimed; Codex did not execute native trace-control. The separate operator controller has performed cleanup. Provider enable was reached and returned0. Missing export does not change those proven statuses or establish a TCP defect. Its absence alone does not identify the sanitizer failure or prove the operator has returned.

Authoritative selected socket protocol measured family2/type1/protocol6,error0. TCP_NODELAY0; SO_LINGER disabled0/seconds0. Read-only observation only; no option change. r02 also received all65,786 bytes in this run; no current confirmation reproduced the previous missing506 condition. No wire delivery/ACK inference is made from send acceptance or fixture PASS.

Exact source25 ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490; all25 source paths and1,204 preservation hashes remain unchanged (includes1,175 historical hashes). Reviewed bundle53b6657eae510f4a022ea6d164bc1344b66f2f72563eb762709a792fed69422f unchanged. Four numeric diagnostic files passed the bound diagnostic schema; capture-provenance passed strict schema; all seven records/profile/source/host/receipt/deadline/status/bounds/loss bindings passed the reviewed pure validation functions. Raw ETL was not read. No source changes, elevated Codex/runner, retry, helper generation, commit,push,PR update or merge.

This consumes the one authorized controlled-capture attempt. Custom tracing must not expand or retry automatically. The last owner instruction requires stop on evidence failure/incompleteness. Minimum remaining operator information: whether the controller returned, its fixed error identifier and numeric exit/HResult if present, and whether it printed Sanitized metadata exported. Send only those safe fields; never raw ETL/XML/payloads or unrestricted exceptions. The asynchronous question has been issued; pending response remains UNKNOWN.

Existing capture/code/manual preparation gates PASS do not certify this incomplete attempt or the complete product candidate. Required release tests, full independent gate, final-main integration, publication and CI acceptance remain outstanding. Historical FAIL reports remain immutable. Further recovery requires bounded release-risk reassessment supported by actual evidence, with no arbitrary workaround or waived mandatory failure.

Safe original records remain in tmp/pr81-tcp-capture-control/ce2590f5-11d3-414a-9cee-b7ca50b980be and safe ordinary receipt tmp/pr81-tcp-native-ce2590f5-11d3-414a-9cee-b7ca50b980be.json. Exact hashes are recorded in PR81_TCP_V61_CAPTURE_ce2590f5_STOP.json; no raw data is copied. Record time UTC 2026-10-11T07:32:26.355652+00:00.
