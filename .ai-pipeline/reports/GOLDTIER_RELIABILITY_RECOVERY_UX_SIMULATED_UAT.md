# GoldTier reliability/recovery UX — simulated owner UAT

Started 2026-10-07 12:46 UTC / 20:46 Singapore. Final human journeys completed
2026-10-07 14:41 UTC / 22:41 Singapore. Status: REMEDIATED AND VERIFIED;
FRESH INDEPENDENT QUALITY GATE REQUIRED.

Accepted starting source identity:
`f628a31fbc3cee3ac035ff7b0ddcd0527ec3d10fbe58dfbdafcdd50f8ed22dae`.
All 23 per-path hashes and cumulative hash matched before any test/write.
Branch: `codex/goldtier-submission-reliability-recovery-ux`.
BASE_SHA, HEAD and inspected origin/main:
`5c54c9af896585764d1e4ed809056d1deb576629`. Staged diff empty.
Existing 17 tracked implementation deltas and 10 task-owned new paths were preserved.
Original evaluation and camunda worktrees/resources/artifacts were preserved.
Evaluation chat: completed/idle revision 8, rechecked this turn.

Mechanism: interactive Chrome, then visible Codex in-app browser via cua_repl control,
with actual UI navigation,
fresh accessibility/DOM observations and documented browser APIs. No /simulate
capability is exposed in this session. The application uses the existing
e2e_backend_server.py and Vite manual runbook, loopback ports 8865/4273, ephemeral
in-memory synthetic credential, memory persistence and injected offline ACRA/GoldTier
fixtures. No real provider login/request/write or protected database access.

## Scope and checkpoint

- Parent assignment: owner acceptance attachment, 2026-10-07.
- Intended report-only writes until a reproduced in-scope defect requires repair.
- Executed scope: baseline and repaired Shell/Policy human journeys, visible
  aborted/truncated/held response scenarios and affected automated verification.
- Original historical screenshot case is not accessed; its cause remains UNKNOWN.
- If reviewed content changes, old PASS cannot apply to the changed candidate;
  re-freeze and stop for independent re-gate after affected verification.
- No commit, push, PR, merge, unsupported provider/role/Amend or architecture change.

## Observations

Preflight PASS: source identity unchanged, expected branch/base and empty staging.
Chrome login as Ethan Tan / RM reached the empty normal dashboard and New onboarding.
Chrome screenshot timed out and its hidden-input file-picker attempt reset the tool
session before a case was created. In-app browser fallback successfully selected the
synthetic file, but the picker tool took roughly 20 minutes. Screenshot capture and
subsequent UI operations work in the fallback. These are tool limitations, not product
defects. Native ArrowUp/ArrowDown date entry committed the date after tool fill alone
left the React form's required-date validation unresolved; no source fix was inferred.

Shell case: `29da7afc-682a-422e-960f-ec88134a4e0b`, created by Ethan/RM through
New onboarding, synthetic document picker, normal classification and current ownership
decision. Confirm was activated once. True Shell uncertainty appeared; panel opened,
RM recovery controls absent, Director escalation explicit, technical details collapsed.
Automatic read-only check returned exact matching customer and preserved uncertainty.
Explicit keyboard Enter on Check GoldTier status also returned the same safe result.
At 1280x1000 the actual panel copy/facts/actions wrap coherently with no visible overlap.

UAT-01 actual first-level observation: after confirmation settles, viewport remains at
the bottom of the long frozen review. Recovery heading is 3,372 pixels above viewport;
the visible footer says confirmation retained but contains no next-action link. The
new actionable panel is open in the document but not presented at the user's current
position. Screenshot and DOM rectangle independently establish this discoverability
defect; automated DOM visibility alone had not covered viewport/focus handoff.

Shell journey completed on accepted source: RM reload and Cases -> Open retained the
uncertainty; logout removed case content; Director returned through Cases -> Open with
fresh eligible controls. At 320px, Space attested the exact candidate, Tab moved to
Resolve, two immediate Return activations retained recovery once. Reload preserved
RECOVERY_PENDING and Complete safe recovery. Keyboard Enter continued to COMPLETED /
SUBMISSION_CONFIRMED with the same submission `691c6c71-6f49-408f-83d8-0fbfedd51b11`.
Actual fixture totals: SEARCH2, SHELL1, POLICY1, AMEND0, READBACK9, external_calls0.
Additional reads are explicit checks, reload/role checks, fresh recovery validation and
final readback; the original Shell remains outside the definitive prefix and inside
lifecycle-resolved evidence. Original confirmation is retained; no second send control.

Interactive responsive evidence: 1280/720/320 widths, actual status/technical-details
and Director candidate controls used. No visible desktop overflow; measured content
widths705/305 fit the 720/320 viewports. No clipped recovery buttons or overlapping
panel text observed.
Native summary/checkbox focus visible. Tab after checking reaches Technical details;
native sequential tab order remains logical despite disabled-button focus reporting BODY.
No separate manual-check focus defect was inferred.

Counter-observation interference: the first supplementary API login reused Ethan and
invalidated his browser session under the existing one-session-per-user policy. The
browser cleared case data on401 as intended. Reauthenticated through normal UI; later
counter reads use Maya, a separate synthetic observer, preserving Director/RM sessions.
This is a test-method correction, not a product defect or a role/cache failure.

After recovery is retained, the primary package reverts to Status: Blocked / retained
target ledger / safe finalization wording. The enabled continuation works safely,
but this first-level explanation assumes architecture knowledge rather than explaining
that verified work is preserved and the same submission can continue. This is UAT-02.

## Defects

| ID | Journey | Severity | Observation | Expected | Reproducible | Fix |
| --- | --- | --- | --- | --- | --- | --- |
| UAT-01 | Shell after Confirm | P2 | Viewport stays at frozen review footer; recovery heading top=-3372 at 1280x1000; no next action in that viewport | Bring the actionable verification panel into view/focus when confirmation yields uncertainty | Yes, actual UI and DOM rectangle | Fixed: guarded same-case heading handoff and pre-paint disclosure settlement; final manual heading top=489, focused |
| UAT-02 | Retained Shell recovery | P3 | Primary continuation explanation leads with Blocked, ledger and safe finalization | Plain-language same-submission continuation; technical ledger explanation secondary | Yes, actual retained/reloaded UI | Fixed: Verified work is saved / Continue the same submission; old explanation remains in Technical details |
| UAT-03 | Policy identity check | P3 | Matching-customer result advertises Shell recovery on an uncertain Policy | Explain that matching identity leaves Policy unverified and requires independent evidence | Yes, actual RM/Director UI and failing component assertion | Fixed: operation-specific copy in existing TargetRecoveryPanel |
| UAT-04 | Confirmation response loss | P2 | Browser can wait indefinitely for a response that never settles, before GET observation starts | Bound browser response waiting, observe retained state without another POST | Yes: headed held-success regression failed at 15s, verifying heading absent | Fixed: eight-second existing UI ceiling on this confirmation request only |

## Policy baseline and failure investigation

Policy case `37bb88dd-d7f7-4049-b436-704b8679d6bd`, original submission
`1c22956c-4bce-412a-be05-b9850b3eaaf8`. Ethan/RM followed the same normal intake,
classification/current ownership and one confirmation. The backend retained true Policy
uncertainty, SEARCH2/SHELL1/POLICY1/AMEND0/READBACK0, while the browser remained on
"Confirming reviewed target dispatch…" for minutes. Console had no JavaScript errors.
The task-owned Vite proxy recorded connection resets. A fresh browser document initially
read retained uncertainty successfully; the check preserved uncertainty and no RM
recovery control appeared. Its result incorrectly described Shell recovery (UAT-03).

Normal RM logout and Olivia Koh/Director login through Cases -> Open returned the same
case and exposed only server-authorized Policy recovery. Customer ID and Policy name
were read-only, labels associated, status options blank/Requested only, and Requested
explicitly did not mean approval/completed KYC. Without attestation the submit control
was disabled; attempted Enter was blocked by browser control, with no mutation or
provider writes. Before valid recovery: SEARCH2/SHELL1/POLICY1/AMEND0/READBACK3.
At 320px: selected Requested, Space attested, Tab reached Resolve, two immediate
Return activations retained recovery once. No provider call occurred in Policy recovery.

Reload then hit another proxy connection reset and stayed Loading case. Direct backend
GET was 200 in 31ms, 67,083 synthetic bytes, RECOVERY_PENDING/FINALIZATION_PENDING.
A fresh browser document also stalled; restarting ONLY the owned Vite process allowed
normal reload to read retained continuation. Keyboard Enter completed the same original
submission, COMPLETED/SUBMISSION_CONFIRMED, confirmation retained, final counts
SEARCH2/SHELL1/POLICY1/AMEND0/READBACK4/external0. The reload interruption is retained
as a local proxy limitation, not fabricated as an uninterrupted PASS. Its exact network
origin is UNKNOWN; no global transport/configuration repair was inferred.

Source-change necessity: scrolling/refreshing does not guarantee observation when a
confirmation response never settles. The existing confirmation API and CaseDetail view
own the repair; no new owner, provider contract, permission, schema or retry is needed.
Classification: FRONTEND_UI + FRONTEND_STATE_CACHE (request response deadline).
Pre-change regressions: focused component copy/focus assertions failed (2 failed,
40 deselected); headed held-response test failed because verification never appeared.
The accepted f628 identity and its old PASS are historical evidence only from the first
reviewed test edit onward. No new independent PASS is claimed.

Causal account: missing browser response bound is the confirmed proximate liveness
mechanism. Upstream connection-reset origin remains unknown. The deterministic
counterfactual holds a successful server response: unchanged source waits forever;
bounded confirmation response enters existing GET-only observation. Header/body wait,
network rejection, decoding failure and slow in-flight backend work are distinguished;
stopping browser waiting does not imply failure or cancel server work. This closes the
held-response UI class, not the unknown proxy/historical incident cause.

## Exact repaired human journeys

Source/test edits were finished before these final journeys; no source was changed
during them. Mechanism remained manual browser control in the visible in-app browser,
with native Enter/Space/Tab interactions and actual synthetic file selection.

| Scenario / role / viewport | Actions actually performed | Observed / expected result | Outcome |
| --- | --- | --- | --- |
| Fresh uncertain Shell; Ethan/RM; 1280x1000 | Normal intake, classification, current ownership, Confirm once; explicit Check by Enter | Verification heading focused at top=489/bottom=511.39; clear preserved-work/duplicate prevention; no RM recovery mutation; check retained uncertainty | PASS |
| Same Shell; RM; 720x1000 | Technical details by Enter; reload; Cases -> Open | Technical code secondary and disclosure keyboard operable; same retained uncertainty, no stale success/re-enabled Send | PASS |
| Same Shell; Olivia/Director; 320x1000 | Normal logout/login, Cases -> Open; Space exact attestation, Tab to Resolve, two immediate Return activations | Exact identity prefilled; recovery retained once; continuation focused at top=488.91; body width305 fits320; safe plain copy | PASS |
| Same Shell; Director; 320x1000 | Reload, Enter Complete safe recovery | Same submission confirmed; result focused at top=489.05; no uncertainty panel or another Send/Shell | PASS |
| Fresh uncertain Policy; Ethan/RM; 1280x1000 | Same normal preparation and one Confirm; Check by Enter | Heading focused at top=489; result explicitly says matching customer does not verify Policy; no RM recovery control | PASS |
| Same Policy; RM; 720x1000 | Technical details by Enter; reload; normal logout | Retained state and corrected wording survive; no stale RM case content on sign-in | PASS |
| Same Policy; Olivia/Director; 320x1000 | Cases -> Open; Requested selected, Enter in read-only Policy-name input without attestation | Resolve stays disabled, uncertainty retained; SEARCH2/SHELL1/POLICY1/AMEND0/READBACK4/external0; no recovery/write | PASS |
| Same Policy; Director; 320x1000 | Space explicit attestation, Tab to Resolve, two immediate Return activations | Recovery retained once; plain continuation and focused heading at top=488.91; body width305 fits320 | PASS |
| Same Policy; Director; 320x1000 | Reload; Enter Complete safe recovery | Original submission confirmed, result focused at top=489.05; no new Send/Policy | PASS |

Final Shell case `101b46e1-3c78-4599-91be-26e938e8c121`, original submission
`711ba3a7-97d6-4a37-a4dd-e6e12cdd4d57`: COMPLETED/SUBMISSION_CONFIRMED,
confirmation retained; SEARCH2/SHELL1/POLICY1/AMEND0/READBACK6/external0.
Final Policy case `e908e557-c757-4b78-ac01-2252944587e5`, original submission
`3bb4356e-aeec-471e-a670-d3aea003ba80`: COMPLETED/SUBMISSION_CONFIRMED,
confirmation retained; SEARCH2/SHELL1/POLICY1/AMEND0/READBACK5/external0.
Extra readbacks are read-only explicit/automatic checks and final verification.
Manual browser transport was not independently instrumented to count confirmation
POSTs; each had one actual UI activation and retained original confirmation. Headed
response-loss tests instrumented and asserted exactly one confirmation POST, and both
headed recovery tests asserted exactly one recovery request despite repeated Enter.

Intermediate handoff repair evidence is retained: focus-only microtask and first-frame
attempts failed real viewport assertions. A safe diagnostic traced Submission readiness
height1301.56 ->76.30 after scrolling, shifting the focused heading upward1225px.
The existing StageDisclosure owner now settles active changes in its layout effect
before paint; CaseDetail reveals/focuses/scrolls the transitioned same-case heading in
the next frame. Temporary diagnostics were removed. The incomplete intermediate Shell
case `b3ce1649-e260-4aee-a518-a617d237f4f4` was task-owned memory fixture data; it
was replaced by restarting only our owned fixture for the final fresh-case test.
No failed intermediate result is counted as final PASS.

Console: baseline settled pages had no JavaScript issues. During source hot refresh,
the long-lived test tab recorded React removeChild/createRoot errors at14:13–14:24 UTC;
Vite recorded incompatible export Fast Refresh invalidations. Fresh reloaded final
journeys from14:28 UTC onward had zero console errors/warnings. These development
hot-refresh observations were preserved; no speculative auth/DOM refactor was made.
The proxy reset interruption described above was absent from the final journeys.

## Visible response-loss and affected verification

Measurement coordination was cleared before broad verification: Build FYP evidence
workbook latest turn completed, notLoaded/idle revision9. No measurement process,
evaluation branch/worktree/output or container was changed.

All browser runs used the existing owned-process harness, --headed, unused loopback
ports8965/4373, fresh offline composition per selector, timeout180s, one worker/no retries,
trace/video off and the existing external-network guard. For response loss, the actual
successful server response was aborted, truncated, or held; a test-only GET gate kept
the observation panel on screen long enough for viewport/focus inspection and a sanitized
screenshot. Releasing that gate produced authoritative confirmation, no decoder error
or false-failure alert, disabled Send while observing and no Send after confirmation.
The controlled hold changes response delivery only; it is not a real provider scenario.
Each loss variant: confirmation POST1, SEARCH2/SHELL1/POLICY1/AMEND0/READBACK1/external0.

| Check after final source edits | Result |
| --- | --- |
| npm test -- --run src/pages/S3SubmissionStatus.test.tsx src/submissionObservation.test.ts src/pages/StageDisclosure.test.tsx | 52 passed across3 files; stalled-header/body request bounds, focus/rerender isolation, no-replay, Policy-copy and existing adverse paths |
| npm test | 560 passed across47 files |
| npm run typecheck; npm run build | Both exit0; build135 modules |
| Director recovers uncertain shell; Director recovers uncertain policy | 2 headed PASS, exact retained UUID/confirmation, recovery-request1, Shell1/Policy1/Amend0/external0, reload and viewport/focus assertions |
| Lost confirmation response.*held; .*aborted; .*truncated | 3 headed PASS after final disclosure edit; verifying/result focus and full viewport assertions, POST1/no replay |
| S3 normal Sandbox submission; S3 uncertain Policy checks; S3 definitive Policy failure; post-closeout existing-customer confirmation | 4 headed PASS, retained-state and no-replay regressions; ordinary failure distinct from uncertainty |
| responsive review case exposes; responsive cases and representative routes | 2 headed PASS, affected shared disclosure/view regression |
| check_project_state.py; check_architecture.py | Both PASS |
| Scoped check_secrets scanner over tracked/task-owned worktree paths | 1317 paths, zero findings before final receipts; final receipts rechecked below |
| git diff --check; explicit new Markdown hygiene / final freeze | Recorded in final identity receipt below |

Eleven final headed scenarios passed. Existing SSR-layout warnings in static React/router
test renders and the Vite >500kB bundle warning remain visible; neither was suppressed
or used to justify unrelated work. No dependency/lockfile churn. Backend, API projection,
provider, recovery/authorization/persistence source is unchanged from accepted identity
(all16 untouched accepted paths match). Full backend/physical Mongo/lifecycle suites
were not rerun for this frontend-only remediation. Historical backend evidence belongs
to f628, not a fresh broad-backend PASS on the new candidate. No publication pre-PR gate
was run for this intentionally uncommitted implementation handoff.

## Edges and evidence limits

The existing uncertain-shell/policy fixture always returns one exact matching customer.
It has no switch for a read-only CHECK_FAILED, retained no-match/ambiguity, unsupported
Amend or unrelated technical failure during recovery. Those three named read-only
edge journeys and the unrelated-failure recovery journey were NOT manually reproduced;
no browser PASS is fabricated. Existing focused component regressions executed safe
CHECK_FAILED/NO_MATCH/AMBIGUOUS/IDENTITY_UNVERIFIED copy, disabled unsafe Shell recovery
and visibility of unrelated failure with backend recovery unavailable. Headed tests
also executed a stale-submission check-result rejection and ordinary failed Policy.
No new fixture/provider behavior was invented. Historical screenshot cause stays UNKNOWN.
Policy attestation used synthetic fixture evidence only; no actual provider verification,
Live interoperability, approval, KYC completion or sponsor authority is claimed.

## Remediation scope and closeout

Nine source/test/doc paths changed relative to accepted content:

- apps/frontend/src/api.ts: confirmation response deadline using existing UI ceiling.
- apps/frontend/src/pages/CaseDetail.tsx: local guarded same-case focus/scroll handoff and plain retained continuation.
- apps/frontend/src/pages/StageDisclosure.tsx: active-state layout settles before paint.
- apps/frontend/src/pages/TargetRecoveryPanel.tsx: focusable heading and Policy-specific identity result copy.
- apps/frontend/src/pages/ReviewAndSend.tsx: focusable definitive outcome heading.
- apps/frontend/src/pages/S3SubmissionStatus.test.tsx: transition/rerender focus and Policy-copy regression.
- apps/frontend/src/submissionObservation.test.ts: stalled header/body deadline and one-request regression.
- apps/frontend/e2e/s3-sandbox-submission.e2e.ts: held-response scenario, visible/focused states and screenshots.
- docs/integration/GOLDTIER_RELIABILITY_RECOVERY_UX.md: current response bound and handoff behavior.

FRONTEND STATE/CACHE: PROCEED for this bounded implementation; independent gate pending.
Case key/user/team scope, mutation effect owners, auth/logout/401 clearing and deletion
ordering are unchanged. Confirmation request now stops waiting after8s; timeout follows
the existing controller/generation-bound GET observation path, with no POST retry.
Current-case/actor generation rejects late work; new focus handoff is cancelled on
identity/state change. Full frontend regressions cover session/team/late response and
deletion protections. No durable browser cache or new state owner is introduced.

UAT delta: API/type contract NO; schema NO; connector NO; configuration/provider timeout
NO; business rule NO; mapping NO; auth/security/permissions NO; architecture/owners NO;
provider status NO; frontend runtime behavior YES (response bound, focus and copy).
The pre-existing accepted implementation delta remains separate and preserved.

Complexity control: existing API/view/disclosure owners only; the failed scheduling
attempt was replaced at the disclosure layout owner. No fallback, duplicate provider
logic or extra lifecycle/cache owner. Legacy missing-metadata behavior is preserved
because unsupported historical evidence is explicitly outside this remediation.
CaseDetail remains an existing oversized view (local-fix-without-new-responsibility);
decomposing the wider view is a separate task, not part of this bounded UAT repair.

Owned manual backend/frontend servers and agent-created tabs were stopped/closed;
temporary viewport override reset. Other worktrees/processes/artifacts remain preserved.
Staging is empty; no commit, push, PR or merge. New independent PASS is NOT issued.
Recommended next authorized action: independent reviewer evaluates the new frozen
manifest against this report and the accepted criteria; any further source edit
requires a new freeze/review. Owner/planner decides publication only after that gate.

## Frozen handoff identity and safe artifacts

New25-path normalized source identity:
`ffd55df6bacc51691dfc00b8d7d6e01860338e41863077ef61b87b28bdc2f5e7`.
Manifest: GOLDTIER_RELIABILITY_RECOVERY_UX_SIMULATED_UAT_MANIFEST.json.
All25 per-path hashes plus cumulative hash were recomputed after this receipt update;
no source drift. Original23-path manifest/QG remain historical and unchanged.
Old independent PASS valid for the repaired candidate: **NO**.
Fresh independent re-gate required: **YES**. This implementation run does not perform it.

Final Git identity: branch codex/goldtier-submission-reliability-recovery-ux;
BASE_SHA=HEAD=inspected origin/main=5c54c9af896585764d1e4ed809056d1deb576629.
Current integration ref was inspected locally; no integration/publication fetch or
pre-PR action was requested. All three existing worktrees remain in the final list,
with their original branch/HEAD; staged diff empty. Whitespace check and explicit
new Markdown hygiene pass; final source/report/manifest secret scan has zero findings.

Eight sanitized headed-browser screenshots, bound by artifact hashes in the manifest:
`GOLDTIER_RELIABILITY_RECOVERY_UX_UAT_SCREENSHOTS/retained-shell.png`,
`retained-policy.png`, `verifying-aborted.png`, `verifying-truncated.png`,
`verifying-held.png`, `confirmed-aborted.png`, `confirmed-truncated.png`,
`confirmed-held.png`. The saved continuation and held-response confirmed screenshots
were visually inspected: next action/result is readable, focus is visible and the
approved/KYC limitation remains explicit. Manual native captures in this chat provide
additional 1280/720/320 observations; no file reference is invented for those captures.

Evidence strength: direct human and affected regression evidence, bounded by offline
fixtures and the named unexecuted edge journeys. Scope is implemented and verified for
independent review, not accepted for publication. The next action is the fresh
independent quality gate on exactly this frozen content.
