# PR81 V6 final authorized helper cycle: BLOCKED

## Outcome
**BLOCKED. Do not arm or execute the V6 SOP.** The documented logging-mode mismatch is corrected and focused tests pass, but fresh independent manual review and supplemental code reassessment prove a capture-profile provenance defect. The initial code PASS is preserved historical scoped evidence and does not authorize this candidate. The final authorized correction cycle stops for owner reassessment.

## Microsoft-documented explanation and implemented delta
Microsoft identifies 0x00400000 as EVENT_TRACE_STOP_ON_HYBRID_SHUTDOWN and describes session-dependent default selection when neither STOP nor PERSIST is requested: https://learn.microsoft.com/en-us/windows/win32/etw/logging-mode-constants .
Installed SDK 10.0.19041.0 shared/evntrace.h lines401/439/447/448 confirms CIRCULAR0x2, NO_PER_PROCESSOR_BUFFERING0x10000000, STOP0x00400000 and PERSIST0x00800000.
V5 requested0x10000002 and successfully queried0x10400002 with sole failed comparison64. The returned flag is consistent with documented default selection. No new direct kernel-normalization observation is claimed.
V6 explicitly requests CIRCULAR|NO_PER_PROCESSOR_BUFFERING|STOP =0x10400002, using one Native.ApprovedLogFileMode in actual Start properties, exact Bounds equality and controller comparison/validation. Profile changes only mode, description and revision; namespaces are separately versioned. No flag mask, arbitrary-bit allowance or PERSIST substitution.
All other capture constraints remain unchanged:45s absolute/300s arming/readiness5s/8MiB/64KiB4..16/flush1/provider/schema/filter, typed watchdog, exact-owned cleanup, strict connection selection, protected raw, HTTP15s/fixturecleanup10s/Selector/assertions/no replay.

## Current independent finding
[Manual FAIL](C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm/.ai-pipeline/reports/PR81_TCP_TRACE_MANUAL_V6_SAFETY_REVIEW.md); review identity55821087e96a3ff4a979120814d82a30cf8ef1c6a68518f11c124bb1d3a9097f; rawSHA62a86228711a884630535b7e6ddf40570703834bd4b368c6eabe9d06fe87d314.
[Supplemental code FAIL](C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm/.ai-pipeline/reports/PR81_TCP_TRACE_HELPER_V6_PROVENANCE_REASSESSMENT.md); review identity1f37eb1bdcb36aab160dc1498fdce206a4abdf3d20a345f86e9a37a85b23891a; rawSHA39ac54010ca5605a388e9a1a1a810d93cccf7dc9b38cd90a9822c713f417c328.
Sanitize-TcpTrace.ps1 line148 would export oldV2 profile_sha25674cea52445fe6f504e8859299f73a18f0976f00e53107daedaeabbe76f8760d1, while V6 actual bundle/arm/active/stopped bindce6dbe33f22388f215ccf18a7509a08538a386a905d1dc357b9eabdd904fb96f.
V2 is outside V6 bundle members. The same profile_sha256 field cannot be relabeled into a different identity to accept this discrepancy. This is proven from the production expression and file hashes; no export/ETL was run.
Sanitizer -Validate returns at line133, before the envelope;19 selection regressions therefore miss the provenance error. Initial independent code review missed this dependency and its report remains immutable.
Smallest proposed contingent correction: change the V6 sanitizer's one literal capture-profile reference, add production-envelope positive/adverse identity checks against bundle/markers, regenerate bindings and obtain fresh code/manual reviews. No event selection or confidential data access is necessary. This is proposed only.

## Complete verification summary
| Current preparation check | Result |
|---|---|
| New logging-mode/bounds/ownership/actual-Props regression |50/50 PASS|
| Original controller diagnostics |30/30 PASS|
| Typed watchdog site/adverse tests |39/39 PASS|
| Actual process identity/getter probes |6/6 PASS|
| Connection sanitizer selection regressions |19/19 PASS; export provenance uncovered|
| Secret-scanner tests |8/8 PASS|
| Helper -Mode Validate / runner --validate |PASS; no ETW/fixture|
| Ruff / project-state / architecture |PASS|
| Scoped supported-pattern secret scan / explicit authored whitespace / Git diff --check |PASS; limited scanner coverage|
| Independent SOP PowerShell parse |4 blocks;0 errors; none executed|
| Current complete code acceptance / manual safety |FAIL / BLOCKED|
Initial new test harness function typo was corrected before final50 PASS. Initial hygiene aggregation treated unified-diff context prefixes as authored trailing whitespace; checker scope corrected. No capture/fixture in either failed validation. Full product suites, publication checks and CI were not run for this bounded uncommitted helper preparation.

## Exact identities and preservation
Reviewed V6 bundle SHA256 b072fb20d5002a9d94f7baef38204c4b5547ba2de64eece1e31c6446ab8150a7.
V6 profileSHAce6dbe33f22388f215ccf18a7509a08538a386a905d1dc357b9eabdd904fb96f.
[SOP retained for review, BLOCKED for execution](C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm/.ai-pipeline/reports/PR81_TCP_TRACE_MANUAL_PROCEDURE_V6.md) rawSHA239de2a9609a1411c8bf25cd0819e76ae00e7c8b5e5d01026f16236c38d686b0.
Initial code-gate rawSHA64e8e6759196a1c0c7f27cee5273fe13d81a49f0fa6c7ca09d7970c811cdf61b; its PASS does not override current FAIL.
Source25 ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490; HEADdd8c36c8a911f4b5f3b80e7441d049f1aa976599; branchfeat/blocker-resolution-idp-ux-optimization; cached main/basee799d74063678bb0eccbea445d5ab3c8628dd2c0; no fetch. All1175 historical hashes,20 frozen code paths,2 manual paths and13 bundle members remain exact. Existing23 tracked modifications retained; stage empty. Task remains uncommitted by owner instruction; repository is not clean because the preserved candidate is intentionally uncommitted.
Only new V6 helper/profile/test/SOP/evidence paths were created. No product API/type, persistence schema, connector, configuration, business rule, mapping, auth/security owner, architecture, provider classification or runtime changed. Only task-owned capture-helper mode configuration/validation changed. Original worktree and unrelated worktrees untouched.

## Stop boundary and remaining blockers
Owner instruction authorizes edits only to the affected capture profile, controller constants/validation, tests and supporting documentation. Correcting the sanitizer's production binding is outside that listed edit boundary; strict per-connection sanitization must remain unchanged. Final-cycle instruction requires owner reassessment.
No sanitizer correction, elevation/capture/Native Query/Start/Enable/Stop/child-watchdog/fixture/newRunId/replay/rawETL/commit/push/PR update/merge followed the finding. SOP is not approved for execution. Previous RunIds are not reused.
Underlying HTTP506-byte delivery cause and historical V3 abort remain UNKNOWN. Actual V6 native capture, transmission/ACK/FIN/RST correlation and release acceptance remain unverified. **PR81 NOT READY FOR HUMAN MERGE.**
