# PR81 V6 implementer handoff

## Outcome and identity
Helper correction complete for independent review; no independent PASS claimed here. Branch feat/blocker-resolution-idp-ux-optimization; HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached main/base e799d74063678bb0eccbea445d5ab3c8628dd2c0. Source25 ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490. Bundle SHA256 b072fb20d5002a9d94f7baef38204c4b5547ba2de64eece1e31c6446ab8150a7.
Scope is only V6 helper/profile/test/documentation, intentionally uncommitted. Historical 1175 files exact. No product path changed; staged set empty.

## Documented causal explanation
Installed SDK 10.0.19041.0 shared/evntrace.h lines401,439,447,448 confirms CIRCULAR2, NO_PER_PROCESSOR_BUFFERING0x10000000, STOP0x00400000, PERSIST0x00800000. Microsoft documents session-dependent default selection when neither STOP nor PERSIST is provided: https://learn.microsoft.com/en-us/windows/win32/etw/logging-mode-constants .
V5 observed successful query0 and sole comparison-mask64, requested0x10000002 versus returned0x10400002. The extra flag is documented STOP; Windows default selection explains the observed normalized configuration. No direct new kernel-default measurement was performed. Explicitly requesting STOP preserves the observed hybrid-shutdown stop behavior and avoids relying on default normalization for strict equality.
The hybrid-shutdown flag is a session lifecycle choice, not an event-content/provider/filter/socket change. No added capture content, persistence across hybrid shutdown or weakening of exact equality.

## Exact delta
Separately versioned PR81TcpV6 namespace; Native.ApprovedLogFileMode is named SDK constants CIRCULAR|NO_PER_PROCESSOR_BUFFERING|STOP =0x10400002.
Native.Props Start properties, Native.Bounds, controller numeric comparison and validation/synthetic stats use approved constant. Profile V6 changes only log_file_mode, description and revision. New50-case test reflects actual Start properties without StartTrace; rejects missing STOP, PERSIST replacement, both STOP/PERSIST and every29 unexpected bits; six other bounds and exact/foreign/empty ownership enforced; every39 mode case checks enable gating and exact owned cleanup delegates.
All other Native runtime bodies, including typed watchdog/Query/Enable/Stop/Disable/Complete, proven identical to V5 after namespace normalization. Controller changes only namespace, mode expectation, validation suite hook and SOP filename. Stages map comparison6 records new exact value; diagnostic field format and schema version5 remain byte-identical. Runner/sanitizer bytes identical to V5.
No user API/type, product config, persistence schema, connector, business rule, mapping, authorization/security owner, architecture, provider classification, HTTP transport, Selector, socket option or response tests changed. Only task-owned helper logging-mode configuration/validation changes.

## Verification
Final current V6: mode50/50; controller30/30; watchdog39/39 plus6 actual process checks; sanitizer19/19; scanner tests8/8. Controller -Mode Validate and runner --validate PASS. Ruff, project-state/architecture, scoped secret scan and Git whitespace PASS. JSON receipts contain exact test results.
Initial new test harness used a nonexistent function name; corrected before PASS. Initial hygiene aggregation incorrectly treated unified-diff blank context prefixes as authored trailing whitespace; checker scope corrected. No capture or fixture was run in either failed validation.
New authored paths and patch added lines receive explicit whitespace scan. Full product/backend/frontend/Mongo/lifecycle/pre-PR checks are out of this helper-only surface; pre-PR certification is forbidden for this uncommitted preparation.

## Safeguards and residual limitations
45s absolute capture/300s arming/readiness5s/raw8MiB/buffers64KiB4..16/flush1/provider allowlists unchanged. V5 typed watchdog identity/liveness, fail-closed unknown state, original finally/watchdog exact-owned cleanup unchanged. Original HTTP15s/cleanup10s/idempotence/no replay untouched.
Event schema20 IDs/35 versions/319 typed fields remains exact and verified by installed provider Validate; no HTTP bodies/packet buffers/credentials/strings. Acquisition remains host-wide selected metadata; strict unique connection sanitization is unchanged and may reject native coverage. Operator raw ETL stays protected/local; never read by Codex.
Actual elevated capture properties, ACLs, filter/child-watchdog termination and useful delivery/ACK/FIN/RST evidence unexecuted. V5 pre-enable mode mismatch proven, historical V3 abort and underlying HTTP missing506 bytes remain UNKNOWN. No release or causal delivery claim.

## Independent review and stop
Freeze V6_REVIEW_MANIFEST before independent helper-code review. Reviewer writes only PR81_TCP_TRACE_HELPER_V6_SAFETY_REVIEW.md; no implementation changes. On PASS only, prepare hash-bound administrator SOP and obtain separately frozen manual safety review. Stop before elevated capture; new owner coordinated authorization and new RunId required. Final authorized helper correction cycle; no further speculative remediation. PR81 NOT READY FOR HUMAN MERGE.
