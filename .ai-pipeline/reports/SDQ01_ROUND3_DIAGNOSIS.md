# SDQ-01: owner-authorized additional round

Status: required current validation PASS; independent review pending.
Root cause classification **F — unresolved**; SDQ-01 remains OPEN.
The historical 60-second failure has not reproduced in this round. No source correction
has been attempted. A current PASS cannot establish why the earlier execution stalled.
The owner's explicit stop condition remains: unproven root cause means SDQ-01 OPEN.

## Authority and frozen baseline

The owner attachment135583a9 authorizes exactly one additional diagnostic/remediation
round for `authenticated-zero-touch.e2e.ts:670`, preserving its original assertions,
120-second Playwright test configuration and configured60-second runner lifecycle.
Publication, a fourth remediation round and unrelated changes remain unauthorized.

Worktree: `C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm`.
Branch: `feat/blocker-resolution-idp-ux-optimization`. BASE_SHA, HEAD and fetched
origin/main: `e799d74063678bb0eccbea445d5ab3c8628dd2c0`. Zero staged files.

Historical269-file content identity:
`24f30d1411e2ad018b56d410c2eecde7c1012903aeb6848891c8272842844acf`.
Historical source identity:
`5de89b19dda6964828d87ecf744d7b30df4ea3ee8c872a5a4dd2ffabb9df38df`.
The historical independent FAIL report has SHA256
`2c7764f80565a0c2b1f3e7508ce96fb5b8ee633568acb92f10bcdfce0edce83c`.
Earlier FAILs, their manifests, logs and accepted implementation are preserved.
An explicit owned-path ZIP snapshot was taken before temporary tracing.

## Historical failure and prior attempts

The original second shard failed at selection2/44, the progress selector, after its
preceding ordinary-RM selector passed. The harness reported
`INDIVIDUAL_SELECTION_TIMEOUT`; lifecycle time66.390s includes process stopping after
the unchanged60-second boundary. Its captured output names the running test but has
no last-await trace. The observed outer failing operation is the runner's
`_wait_for_test(tests, deadline)`; the first internal blocked await/request/render or
teardown operation remains unknown. A frontend `/intelligence` socket-hang-up message during shutdown
does not establish that request as the first stalled operation.

Both unsuccessful fixture changes were recovered from the exact retained tool diffs
and read together with their failure logs. The first waited for real WAITING_FOR_REVIEW
and reloaded; the second controlled intake completion and held the document projection
until its assertion, then released after ownership. Both still timed out and were
reverted. Neither is repeated. The earlier extra API version diagnostic passed, so its
synthetic/real version difference alone did not prove a failure cause.

## Current diagnostic observations

| Execution | Observed result | Scope |
|---|---|---|
| Timestamped isolated original assertions | PASS8.5s | Temporary payload-free tracing; original delay/deadline preserved |
| Timestamped original second shard | Progress PASS7.5s after preceding selector PASS16.2s | Interrupted after those two; not a complete-shard PASS |
| Exact restored source, isolated | PASS8.0s | Original file restored byte-for-byte before execution |
| Exact restored source, complete original second shard | PASS44/44;537.594s | Progress PASS7.5s; lifecycle11.688s; preceding selector PASS16.7s |
| Exact restored source, earlier invocation environment | PASS7.6s; lifecycle11.859s | Tesseract PATH prefix and earlier root/backend PYTHONPATH reproduced |
| Exact restored source, complete original first shard with installed OCR prerequisite | PASS45/45;544.187s | All65 tests; runner invocation544.313s |

In the isolated successful trace, document projection is fulfilled at1858ms; its
assertion ends2870ms; ownership projection is fulfilled2903ms and asserted2919ms.
The3,500ms intake delay ends4329ms. Real document POST returns201 at5512ms and
intake-complete POST returns200 at5625ms. The Open full case click spans2920..6019ms;
this is an observed wait in a passing run, not proof of the earlier stall. Confirmation becomes
enabled6145ms; explicit target confirmation returns200 at6271ms; completed UI is
visible6386ms. Recorded screenshots take38..45ms. Canceled supporting queries are
followed by fresh successful reads after navigation. These are observations from a
PASS, not a reconstructed trace of the historical failure.

The owning runner and backend contain their environment and choose local_pdf_text;
the added tests/contract PYTHONPATH is not forwarded as backend configuration.
The earlier environment variant also passes. No environmental or isolation cause is
proven. No smallest failing conditions were found, and no first failing await can be
truthfully named. No category A..E is selected.

Temporary source instrumentation was removed. The exact restored file SHA256 is
`552b5d8bcc78851608af892997254921fb2e8402bf3008973883c5840321074b`.
No sleep, retry, timeout, status, assertion, inventory, routing or product change is
retained from this round. SDQ-02's independently closed parent cleanup fix still
unconditionally passes `synthetic_seed_port` to the existing cleanup owner.

## Completed validation and pending independent review

Both complete original shards PASS on exact restored source:45+44=89 lifecycles and
65+47=112 browser tests, zero skips/exclusions/failures. Every selector remains in its
original shard/order and uses the configured60-second deadline. Assertions and retry
configuration are unchanged. All eight fresh sponsor journey receipts are PASS,
COMPLETED/SUBMISSION_CONFIRMED, with exact target-ID readback, stale409, frozen409 and
zero reopen mutations. Native Track B has zero intermediate human intervention and
ANALYZED ownership. The full browser run covers native IDP, batch review, retained
company-pack/negative scenarios, failure stopping and target no-replay paths.

Fresh affected evidence:48 harness tests,109 focused backend tests (one existing
Starlette deprecation warning),49 frontend files/576 tests, frontend typecheck and six
governance/security checks all PASS. Focused backend tests cover batch decisions,
Final Review editing, sponsor fixtures, native parser line endings, target reliability
and target classification continuation. The earlier broad backend2630/physical143 and
full-root373 results remain historical, bound to the recorded unchanged source; they
were not rerun or relabeled as fresh in this round. No new build claim is made.

All269 historical candidate files and68 source-manifest entries match their exact
prior hashes. All63 pre-existing browser write-target artifacts were restored after
copying53 fresh generated artifacts into the separate round-three evidence directory.
Fresh eight journey receipts and16 screenshots are also copied separately. The
historical FAIL reports, log hashes, metrics and candidate identity remain unchanged.
The new [verification](SDQ01_ROUND3_VERIFICATION.json),
[preservation](SDQ01_ROUND3_PRESERVATION.json) and
[resource inspection](SDQ01_ROUND3_RESOURCE_INSPECTION.json) provide exact attribution.

A new independent gate will review a separate frozen manifest/report. Earlier FAIL
verdicts will not be rewritten. The owner's historical-cause requirement remains
unverified despite successful current full coverage; no safe source correction is
justified. This round ends at SDQ-01 OPEN if that requirement remains unproven.

The first first-shard execution passed30 lifecycles and stopped at31/45,
`s3-sandbox-submission.e2e.ts:428`: scanned Garden upload returned503, expected201.
The parent validation environment lacked the installed Tesseract directory on PATH.
Direct `shutil.which("tesseract")` returned unavailable; the installed executable exists
and reports5.4.0. The existing OCR adapter uses that PATH lookup and fails closed with
OCR_RUNTIME_UNAVAILABLE. The failed execution/receipt are preserved separately as
`sdq01-r3-shard1-missing-ocr.log` and `sdq01-r3-validation-missing-ocr.json`.
The full first shard was repeated with its existing offline OCR prerequisite on
PATH and passed; the same scanned Garden lifecycle passed6.0s (9.407s total).
Source, assertions and deadlines remain unchanged. This separate prerequisite
failure is not evidence of SDQ-01's historical root cause.

Only offline synthetic providers and new allowlisted disposable databases are used.
The new task-owned Mongo container is `3147b9b2ddb91845c237d4c32a02a20492ad72c888dd2e837508f6b2decc89e5`,
on loopback27419 with two newly generated anonymous volumes. Post-suite driver/server
inspection found only admin/config/local databases and zero retained generated
namespaces. The exact container/volumes are retained temporarily for independent
review and will be removed after its report. Unowned resources,
protected databases and the original/company-pack checkouts are preserved.

Change classification for this additional round: API/types, durable schema, connector,
configuration, business rules, mapping, auth/security, architecture, provider status and
runtime behavior are unchanged. Additive diagnosis/evidence/review records are the
only intended durable changes. No commit, push, PR, merge or new phase is authorized.
