# PR81 native TCP independent assessment

**BLOCKED: the required native tracing access is unavailable in the observed host context. The owner-directed stop before experiments is supported. Specific cause remains UNKNOWN; no correction or release PASS is justified.**

## Assignment and independence

Reviewer pr81_overnight_independent_review did not implement source changes, capability tooling or experiments. The current owner request was a direct message, with its requirements supplied to this reviewer by the coordinator. It explicitly directs stopping when required privileged trace access is unavailable. The assigned plan and actual sanitized capability receipt/log were inspected; the reviewer made no privilege attempt, native trace session, fixture execution, configuration change, source fix, Git mutation or remote write. Only this assigned new report was written.

The task permits at most two controlled experiments after capability preflight and only an evidence-justified smallest correction. ExperimentA requires native observation of the original direct connection. ExperimentB requires a discriminating mechanism fromA. Neither prerequisite is met. No relay repeat or generic rerun can substitute for missing native sequence/acknowledgement/termination evidence.

Worktree: C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm. Actual branch feat/blocker-resolution-idp-ux-optimization, HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599 and cached origin/main e799d74063678bb0eccbea445d5ab3c8628dd2c0 were independently read. Retained source25 raw identity ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490 remains unchanged. All1075 explicit preservation hashes and all25 source hashes were independently verified before this report. Previous forensic independent assessment remains raw SHA2566ed1a50cba0302bf81842ce5db0b49c4992309129845d525855527b09cbb7e8b.

## Actual capability evidence

The retained capability commands are read-only status/help/provider queries. No capture-start command was executed; pktmon start help requested documentation only.

| Observation | Actual retained result | Evidentiary limit |
|---|---|---|
| Effective host roles |ElevatedAdministrator=false; PerformanceLogUsers=false; PerformanceMonitorUsers=false|No checked privileged role available|
| pktmon status |Exit5: failed communication with PktMon driver; Access is denied|Direct observed denial for PktMon access|
| pktmon start help |Exit0; capture option help available|Help does not grant driver/capture access|
| wpr -status |Exit0; WPR is not recording|No active recording; does not establish capture permission|
| logman query providers Microsoft-Windows-TCPIP |Exit0; provider GUID/keywords registered|Metadata only; no runtime connection data or capture-right proof|
| netsh trace show status |Exit1; no trace session currently in progress|No active trace; no successful capture capability demonstrated|

Microsoft documents ETW session control as restricted to elevated administrators, Performance Log Users and privileged service contexts. This supports the relevance of the observed missing roles; it does not turn a provider listing into permission. [Controlling Event Tracing Sessions](https://learn.microsoft.com/en-us/windows/win32/etw/controlling-event-tracing-sessions)

The independent stop assessment is bounded to the actual denied capability and unavailable authorized tracing prerequisite. It does not claim an exhaustive proof that every conceivable native tool is unusable, nor that WPR/provider queries themselves were denied. No privilege bypass, group change, elevated helper, driver installation, security disabling or machine configuration change was attempted.

The installed PktMon help describes a default128-byte raw packet capture and flags that include raw packet logging. Arbitrary truncation is not demonstrated to be payload-free; no safe sequence/ACK/FIN/RST capture profile was independently exercised. Provider keyword availability likewise does not certify a confidential-data-safe schema. No raw packet/body/ETL capture is recorded.

## Measurement accounting: historical versus current

The previous forensic failure, d1-1-r02, is preserved historical evidence for this new assignment. It identified the actual client socket tuple (client loopback port51631 to server loopback port51614), but that ended connection cannot be traced retroactively. No new connection was created in this assignment.

| Requested field | Preserved prior observation | New native assignment |
|---|---|---|
| Server body emitted |65786 ASGI bytes|NOT MEASURED anew|
| Server body kernel accepted |65786 socket.send return bytes|NOT MEASURED anew|
| TCP bytes actually transmitted |UNKNOWN|UNKNOWN / no trace|
| TCP bytes acknowledged |UNKNOWN|UNKNOWN / no trace|
| Retransmissions/windows |UNKNOWN|UNKNOWN / no trace|
| Actual client body received |65280 SocketIO bytes|NOT MEASURED anew|
| Client deficit against declared body |506 bytes|Historical subtraction only|
| FIN/RST sent/received |UNKNOWN; no client EOF by old deadline|UNKNOWN / no trace|
| Outstanding TCP bytes at close/timeout |UNKNOWN|UNKNOWN;506 is not an observed outstanding-TCP count|
| Actual accepted socket protocol |NOT CAPTURED|NOT CAPTURED|
| Connection close/shutdown native error/state |User-space close callback only; no socket retained, no reported transport error|NOT MEASURED at kernel level|
| TCP_NODELAY/SO_LINGER |Separate relay topology observed NODELAY0/linger disabled|NOT CAPTURED for a new direct connection|

Previous server close/connection-lost at3.313s, client last chunk at3.328s and timeout at18.344s remain prior user-space observations. They do not reveal sequence/ACK ranges, FIN delivery or OS queue state. Empty native user buffer and successful send remain kernel acceptance, not delivery acknowledgement. Historical classificationB stays narrowed between accepted send and actual client socket receipt; the specific TCP/Winsock/termination cause remains UNKNOWN.

The earlier speculative Selector buffer-loss and omitted-protocol/NODELAY clues remain unproved incident causes. Accepted Selector configuration is unchanged. No fixture termination, shutdown, protocol, socket option or event-loop correction is warranted by missing native measurements.

## Executions, preservation and verdict

ExperimentA: NOT EXECUTED because required authorized trace access is unavailable.
ExperimentB: NOT EXECUTED becauseA produced no discriminating mechanism.
Native trace sessions started0; packet files0; new focused tests0; maintained source changes0. These are the recorded task actions, not passing tests or zero-error network measurements. The reviewer executed no additional tests or capability/privilege attempts.

Original15-second request timeout,10-second cleanup, read1048577, original HTTP assertions, first/second-seed idempotence and no-replay semantics remain preserved in source. They were not executed anew or certified by this native task. Earlier FAILs, passing diagnostic controls and all source corrections remain immutable. No new correction candidate or full release evidence exists.

The owner instruction applies: stop and report the unavailable privileged prerequisite. The independent assessment supports this safety/infrastructure stop, while preserving the unresolved product/fixture-delivery failure. This is not an approving Quality Gate on corrected content and does not accept or reset the previous failed stability window. No release matrix, commit, push, PR update, merge or auto-merge should proceed from this report.

The narrow next action is an explicitly authorized context with confirmed native capture access and a validated confidential-data-safe sequence/ACK/FIN/RST measurement profile. Then correlate one fresh original direct memory/Mock connection under the original deadlines; only a demonstrated mechanism can justify a single-variable experiment or owner-layer correction. Do not infer the cause from the existing506-byte arithmetic or substitute another passing relay/stability sample.

No owner.env, protected database, real provider or unrelated worktree was accessed by this reviewer. No API/type/schema/connector/configuration/business-rule/mapping/auth/security/architecture/provider-status/runtime behavior changed. SDQ01 remains historically unresolved and not fixed; SDQ02 remains closed. Existing release blockers and prior independent FAIL remain in force.

## Exact limited review binding

Limited reviewed-content/evidence identity: 957a15079618370cc6b1a228e7aec2e21413e63287fa1651f93e9074cbcc63f9. Algorithm: SHA256 of UTF-8 json.dumps(binding, sort_keys=True, separators=(",", ":")), with no trailing newline. Binding includes the full raw25-path source hash map, capability receipt/log, current plan, previous independent assessment and relevant prior forensic evidence. This new report is excluded to avoid circular hashing. It is not a Git tree or full semantic release review identity.

    {"evidence_hashes":{".ai-pipeline/001_planner/PR81_NATIVE_TCP_INVESTIGATION_PLAN.md":"fc013fca8499ca654fa9ffeea64775bde57fdb5c197d6dc9cdb1858d602c621b",".ai-pipeline/reports/PR81_HTTP_DELIVERY_FORENSIC_REPORT.md":"70ea25ae460a0fe1fc46af9cdc4c148bdfb08a207734da3b9f2fbbe75aa942b4",".ai-pipeline/reports/PR81_HTTP_DELIVERY_INDEPENDENT_ASSESSMENT.md":"6ed1a50cba0302bf81842ce5db0b49c4992309129845d525855527b09cbb7e8b","tmp/pr81-http-delivery-d1-1.json":"75318bc2fcd3b6bcb37d4cfd43c5165f4bdc2090a3f2b5a6f60560d8e0dd62bc","tmp/pr81-http-delivery-d1-1.log":"a43458c1bb8c0de4dd25b753f8b4825cdfa2d202655195202ca76d74ae749768","tmp/pr81-native-tcp-capability.json":"73e7ac22e3aa8b49ae67bcafee8197095c8536bb84a6c7272bb3b965afa3e22e","tmp/pr81-native-tcp-capability.log":"9b5a18ef58a4d1e7d2dcf39718d622d37952f7279cdb1a84e10f2f23a5d781db"},"scope":"Independent native TCP prerequisite stop assessment; no native connection experiment or correction/release acceptance","source_hashes":{".github/workflows/ci.yml":"09e1f4702f520d48e89e6bb91684d58ca8beba40900755164ace44801085a766","apps/backend/app/api_models.py":"15d6b9f08112eed9055e6f94aa863f129446221e263af74c99976d50950e0923","apps/backend/app/main.py":"a45be7fc76c667136a601812d0d02b9cd5793605f1a4f4e55250886b8b7a1a58","apps/backend/app/services/zero_touch_orchestration.py":"f97556ae259bf7aeabedb6d08ff96b8c21f2b91cec69bf707023328c994ee411","apps/backend/tests/test_document_refresh_recovery.py":"35171d0dcbad271e822c23562ffcbb21482ae5aff5938ae181a5f239a07b2578","apps/backend/tests/test_final_review_editing_real_mongo.py":"ac8106f4e387e790114787221306c16bae9eeb482be3398609a4be7182de266c","apps/frontend/e2e/blocker-review-performance.e2e.ts":"df4408f22eeeabec78338b14efdf44c5af732f762c274fe5533c2ed44b18377b","apps/frontend/e2e/blocker-simulation.e2e.ts":"59275b4de4ec1fb5d9ba2c764e597451e15622ce6da8caa53856a08a7513eb60","apps/frontend/src/App.tsx":"486631624f6e1ea8a6aa3bbb7c5bc4117b23957f11f5f24cfd8f0fd9f156bab3","apps/frontend/src/DemoPerformance.test.tsx":"6472cd41c6a5ba3f99b51184bd415e9ec4ac8c510eb3794bcc3ac3079258cedb","apps/frontend/src/ResumeDocumentRecovery.test.ts":"6c891c932ec6a06fcb363b37c1a5dec7d02e93ae383d8dc19d89469f9ff6a53d","apps/frontend/src/api.ts":"6fec47d7215fdd5b256052ac942e8419afdf92b37dc2e7076643c5cd10e957e5","apps/frontend/src/pages/CaseDetail.tsx":"259a28976f37beca416034b4af2efa82579e5d1c0222168fefee80edb1d1253c","apps/frontend/src/pages/DocumentEvidencePanel.test.tsx":"622f50223bd668622374d2917ef092d00cd09e241bbb18c0cd922aa01b42fbba","apps/frontend/src/pages/DocumentEvidencePanel.tsx":"474ede49c581c01b6b904b457356b5011ebee8573a51c2467ae4947553ea5941","apps/frontend/src/pages/OnboardingWorkspace.tsx":"f04b24ae131bb941209c38bd18d53285a46deb0f2cbdf7effb3c395ddb65a21f","apps/frontend/src/pages/S1PipelineWorkspace.test.tsx":"45db6bd50dd8f6c86aa777df22050d286e79bb35b1122fbddd8961700a720139","apps/frontend/src/types.ts":"b2141cfb5068dfecb30707f79aeec0635254ed6e10d925a3aaea2197ad61119e","docs/contracts/MULTI_DOCUMENT_INTAKE_PROFILE.md":"203ad8dfa7e4489c7a236d88f12119734810620be6e2499f97bc414331dd43c8","docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md":"3fbf91c9641ef3382c7141901be1d786590260933ff7926101410fd364000c07","scripts/e2e_backend_server.py":"2485c7f9f979f92b36c2cc789c0fec0f156cea71d9fbd5576dcecea0c272d981","scripts/run_e2e.py":"1ca9ee2fc8dfa82aaf2156b7ddc4c9d8b901e99043c31890218cfb732eb1ee70","scripts/slice_c_recovery_fixture.py":"e0dde54dd34c999f3309ae481e4b09e88d0532911af32d32af3727bec27984c9","tests/test_run_e2e.py":"baa4bcb320d762ca593a72c08377d61e2a7e1f2c59d203f8f63db92a1511b39f","tests/test_slice_c_e2e_fixture_routing.py":"219370b0a4547ce8881d4eef7bd9af5bcefa217d4ea4575cc3e2329b9cf390d9"}}
