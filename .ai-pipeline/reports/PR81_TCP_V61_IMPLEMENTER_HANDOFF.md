# PR81 V6.1 final sanitizer remediation implementer handoff

## Outcome and identity
Production export-profile correction implemented for fresh independent review. Self-verification PASS is not independent acceptance.
Branchfeat/blocker-resolution-idp-ux-optimization; HEADdd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached main/basee799d74063678bb0eccbea445d5ab3c8628dd2c0; staging empty; no fetch. Source25ba47966ed4cd5a4a9c084cc9450bc5250b46b61d85c8a3cc1185448ffa691490.
V6.1 bundle SHA256 53b6657eae510f4a022ea6d164bc1344b66f2f72563eb762709a792fed69422f. Failed V6 bundle b072fb20d5002a9d94f7baef38204c4b5547ba2de64eece1e31c6446ab8150a7 remains exact. Historical1175 and1204 total frozen paths retained. Product/runtime owners unchanged; no maintained API/type/schema/config/connector/business-rule/mapping/auth/architecture/provider-status/runtime changes.

## Exact old/new identity and authoritative flow
Old V6 actual exporter read the V2 profile and would label output74cea52445fe6f504e8859299f73a18f0976f00e53107daedaeabbe76f8760d1.
V6.1 recomputes SHA256 of exact unchanged authoritative V6 profile bytes: ce6dbe33f22388f215ccf18a7509a08538a386a905d1dc357b9eabdd904fb96f.
Only that reviewed profile is supported. Recomputed bytes must match supported identity, bundle.profile_sha256 and its exact V6 member. No hash fallback, normalization, dual identity or V2 substitution.
Get-ExportInputs validates all actual bundle members and source paths, reads fixed same-RunId task-owned records with bounded JSON/no reparse, and independently hashes authoritative profile/schema and safe receipt bytes. Checks run/profile/source/host/process identities across request/armed/active/done/receipt/stopped/capture provenance. Missing/conflicting/unsupported/incomplete rejects before raw ETL event reading; re-read before export protects the same boundary after decoding.
Controller retains original successful-capture/export gate and exact native cleanup, then projects numeric capture-provenance (owned RunId, deadlines, statuses, returned bounds/loss counts). Sanitizer validates its exact schema and uses original Native.Bounds/Complete, not a second bounds owner.
Runner adds profile_sha256 only to four safe request/receipt/done dictionaries; AST normalized for those fields is identical to V6. All fixture/transport/Selector/assertions/HTTP15s/cleanup10s/idempotence/no-replay code remains unchanged.
Actual writer calls New-SanitizedEnvelope, original Select-Connection and exact schema; retains the original ten envelope keys and safe event fields, <=4096events/1MiB. CreateNew refuses output reuse. Successful diagnostic export does not require fixture PASS: original failing HTTP remains eligible for honest forensic metadata if capture itself is complete; no replay.

## Affected files and preservation
New folder pr81-tcp-capture-v6-1 only: Sanitize-TcpTrace.ps1, ExportEnvelope.ps1, Test-ExportEnvelope.ps1, CAPTURE_PROVENANCE_SCHEMA.json, SANITIZED_EXPORT_SCHEMA.json, Invoke-Pr81TcpCapture.ps1, Run-FreshFixture.py, bundle.json.
Other copied Native/controller/test references only gain separately versioned PR81TcpV61 namespace. V6 Native/controller bodies unchanged after namespace normalization; typed watchdog and exact-owned cleanup unchanged. Select-Connection/address/lifetime and original19 validation body remain exact. Diagnostic schema format5 and event schemaV2 exact; capture-profileV6 bytes exact. New schemas formalize the existing export whitelist and safe capture metadata only.
Full V6-to-V6.1 diff in PR81_TCP_V61_DIFF.txt. Historical previous PASS/FAIL evidence is immutable; none inherited.

## Complete verification
Actual production envelope/writer suite51 cases:3 positive,48 negative. Positive exact V6, complete capture with original fixture failure, and actual safe-record IO through production reader/writer. Exact output hash recomputable; ten-key envelope/seven synthetic selected events/no sensitive fields.
Negative staleV2 and missing hash in all seven provenance records; changed/missing/unsupported profile bytes; bundle hash/member/version mismatch; missing/incomplete/failed capture; failed cleanup/unproven absence/unknown native result/type; wrong run/source/PID/receipt; schema mismatch; deadline mismatch; loss/overwrite; old logging mode; extra capture field; production reader missing record; existing output reuse. Every negative produces no new accepted export. Synthetic files individually removed inside verified task/temp paths; no old records reset.
Controller30/30, watchdog39/39 plus6 actual process probes, mode50/50, selection19/19, scanner8/8 PASS. Helper -Mode Validate, runner --validate, Ruff, state/architecture, scoped scanner and authored whitespace/Git diff --check PASS. Structured exact receipts in V61_*_RESULTS and IMPLEMENTER_VALIDATION.
New test initially expected eleven envelope fields; old actual fixed field set has ten. Test corrected before final PASS without changing output fields. No fixture, trace or raw ETL ran in the failed test.
Full backend/frontend/Mongo/browser/lifecycle/pre-PR/CI are unaffected/not authorized for this uncommitted helper preparation.

## Safety constraints and limits
Native45s/arming300s/readiness5s/raw8MiB/buffers64KiB4..16/flush1/event provider allowlists/filter/schema unchanged. Correct V6 explicit STOP mode0x10400002 and exact equality unchanged.
No packet/HTTP/credential/document content or arbitrary event strings/pointers/address/ProcessStartKey fields exported. Acquisition remains host-wide selected TCP metadata, never claimed connection-only. Protected operator raw ETL is not read by Codex. Only safe synthetic JSON exercised. Fixtures and transport untouched.
Actual elevated capture/ACL/filter/returned-mode/child termination/coverage remains unexecuted. Underlying missing506-byte HTTP cause and historical V3 abort UNKNOWN. No release or merge acceptance.

## Independent gate and stop
Freeze exact V61_REVIEW_MANIFEST; fresh code reviewer writes only PR81_TCP_TRACE_HELPER_V61_SAFETY_REVIEW.md, no fix. On exact PASS, issue separately hash-bound V6.1 administrator SOP and require fresh manual review before any readiness claim. Any unrelated finding stops for owner reassessment. No more open-ended helper cycle.
This task authorizes preparation only. No elevated capture, fixture, oldRunId reuse, product change, commit/push/PR update/merge. PR81 NOT READY FOR HUMAN MERGE.
