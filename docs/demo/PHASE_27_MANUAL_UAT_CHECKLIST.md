# Phase27 grouped agent UI UAT checklist

Baseline: merged PR #70, `4ee8819d7404d6442e064fd60dcee03ccc84cf11`.
Branch: `feat/phase27-final-delivery-closeout`. This is the agent UI checkpoint before
Barrier A. Automated browser success is recorded separately in the
[implementation record](../../.ai-pipeline/reports/PHASE_27_IMPLEMENTATION.md).
This is the planned execution matrix; current outcomes are in the linked results. An
automated assertion or historical gate never counts as an agent UI PASS.

Use one grouped session across the fixture modes below. Record an actual observation,
PASS/FAIL/NOT_RUN, and a defect ID/notes for each U27 row. Record the completed rows in the linked agent results file; an example is: `U27-01 PASS: observed ...; U27-02 FAIL: steps/expected/actual ...`.
For optional cases deliberately skipped, give `NOT_RUN: reason`. Do not include
passwords, confidential document content, provider bodies or private customer data.

## Authorized agent UI environment

The owner authorization of2026-10-05 supersedes personal execution and the earlier
8875/4273 isolated-harness instructions. Classification: **AGENT_EXECUTED_UAT**;
each recorded row uses **EXECUTION_MODE=AGENT_EXECUTED_UI**. Never label these
results HUMAN_UAT. Historical automated results do not establish a UI PASS.

Use the real frontend at `http://127.0.0.1:5173`, started with
`scripts/start_demo_windows.bat`. The owned launcher runs the unchanged PR70
application from the main checkout, whose product source matches the Phase27
worktree. Process settings explicitly select `CLM_PERSISTENCE_MODE=memory`,
`REGISTRY_CACHE_MODE=mock`, `REGISTRY_CACHE_FRESHNESS_SECONDS=7776000`, and
`GOLDTIER_SANDBOX_ALLOW_WRITES=false`; providers are Mock ACRA, Mock GoldTier,
local PDF/text IDP and Mock ownership. No original database or external provider
is part of this session. Application-managed local account configuration is used;
Codex does not read `.env`, retrieve hashes, print or persist passwords.

Reuse the healthy owned environment. The first launch failed settings validation
because inherited Mock-cache freshness differed from7776000 seconds. The second
launch used the explicit valid setting and both health checks passed. This was a
CONFIGURATION issue before UI execution, with no product change.

All three authorized existing roles authenticated normally. The grouped results and
bounded retests are recorded in [agent results](PHASE_27_AGENT_UAT_RESULTS.md).
No personal human execution is claimed. Missing prerequisites remain explicit NOT_RUN.
The repaired worktree was started with the same normal launcher for retest; main
product source was not edited. The initial main session and worktree retest source
identities remain distinct.

The S/G/T/F/U labels below describe the intended checklist fixtures. The normal
launcher is not evidence that all isolated test-only fixture modes are exposed
through product UI. Verify actual availability and record any blocked row. Use
only existing synthetic PDFs under `apps/backend/tests/fixtures/uat` and ignored
synthetic Phase27 scratch inputs, with normal uploads and product controls.
Capture visible expected/actual observations and safely reproduce each failure
once. Classify PRODUCT, TEST/UAT SCRIPT, ENVIRONMENT, CONFIGURATION or EXPECTATION
ERROR. Continue unrelated rows; only confirmed product defects trigger bounded
remediation after grouped execution.

## Execution matrix

For all rows: use synthetic data, the current case creator for ownership mutation,
and allowed backend controls. Existing frozen/completed cases cannot be edited.
Review & Send is final local approval; KYC/RFA remains outside this application.

| ID / coverage | PRECONDITION | ROLE | STEPS | EXPECTED RESULT | ACTUAL RESULT | PASS / FAIL / NOT_RUN | NOTES / DEFECT ID |
|---|---|---|---|---|---|---|---|
| U27-01 clean intake / F-B | S; clean current PDF; fresh case | RM | Create SG Multiple Owner Demo202400008H; upload matching PDF; inspect stages | Retained case/document, supported evidence, real classification/confirmation blocker; no premature send | See agent results | Recorded separately | Record case-safe ID and observation |
| U27-02 wrong UEN / F-UEN | S; Merlion document; entered99999999Z | RM creator | Create; note document ID; Edit UEN202400001A; Verify UEN and resume | Same case/document and original extraction; dependent comparisons recompute; resumes to actual blocker | See agent results | Recorded separately | No replacement needed |
| U27-03 document/reconciliation / F-NAME | S; legal-name-mismatch.pdf then clean replacement if required | RM creator | Create Merlion; inspect field score/source agreement; use supported review/source action | Conflict never silently wins; accepted current decision/replacement advances; old history remains | See agent results | Recorded separately | Score, source agreement and verification stay separate |
| U27-04 scanned/image OCR | Actual local Tesseract runtime and bounded synthetic scan available | RM | Upload scan/image; inspect method/page/quality and extracted fields | Actual LOCAL OCR only if runtime exists; absent runtime safely reports unavailable | See agent results; actual OCR unavailable | NOT_RUN | Optional actual-OCR lane; automated absent-runtime test is not OCR PASS |
| U27-05 ownership discrepancy | S; fresh Multiple Owner Demo with comparable scratch discrepancy TXT at intake; OWNERSHIP/REVIEW_REQUIRED before supplementary upload | RM creator | Upload supplementary matching PDF during ownership review; inspect proposed60/40 vs registry50/30/20; select supported source explicitly with rationale | No automatic source winner; accepted current receipt preserves original observations/bindings and recomputes readiness | See agent results | Recorded separately | Use only current owner-authorized choices |
| U27-06 ownership edit | S; calculable current case; no target intent | RM creator | Open Edit ownership; revise valid percentages; enter rationale; save | Prior graph/receipt retained; single Decimal recomputation; stale readiness/confirmation invalidated; post-send edit absent | See agent results | Recorded separately | No legal determination |
| U27-07 tree/calculation | S; calculable graph | RM | Expand tree by keyboard; inspect direct/indirect/aggregate paths and threshold | Server Decimal strings/explanations; provisional candidates; no unsupported complete hierarchy claim | See agent results | Recorded separately | Multilevel exact arithmetic has separate automated S2 coverage |
| U27-08 Garden / F-A | G; fresh Garden11111999A; current partnership PDF | RM creator | Inspect offline official-shaped identity/officers; add reviewed fictional LOCAL60/40; inspect tree | PARTNERSHIP/partial source retained; LOCAL supplement separate; no official percentages/UBOs fabricated | See agent results | Recorded separately | Historical official Mock source authority; this session0 external calls |
| U27-09 second synthetic / F-B | S; fresh Multiple Owner Demo | RM | Create independently; inspect synthetic50/30/20 and document MATCH | Clearly labelled independent SYNTHETIC MOCK case, no Garden evidence carryover | See agent results | Recorded separately | Complete with U27-12/13 |
| U27-10 fresh cache / F-C | S; fresh backend; Merlion warm case kept unsubmitted | RM | Record local registry-counts; create distinct same-identity case; inspect reuse; compare counts through send | CACHE_HIT, preserved acquisition provenance and0 additional ACRA operations | See agent results | Recorded separately | `/api/__slice_b/registry-counts` is isolated safe test metadata; no target-reuse claim |
| U27-11 Policy proposal / F-POLICY | S; HR draft, current base; distinct Director | HR then Director | Propose .85->.92 with reason; inspect synthetic impact; submit; logout; Director decides | HR cannot activate; distinct Director approval creates ACTIVE; reject unchanged; old cases frozen; new cases bind ACTIVE | See agent results | Recorded separately | Record actual approve/reject action; no self-approval |
| U27-12 Review & Send / F-NEW | S/G; current evidence/classification ready | RM creator | Open Preparing GoldTier Submission then Final review & send; inspect destination/data; explicitly confirm | Confirmation last local approval; snapshot/currentness enforced; no extra unresolved local approval stage | See agent results | Recorded separately | Mock submission only |
| U27-13 confirmed target / F-NEW | S/G case submitted; optional T fresh fixture | RM | Inspect retained ID, required operations, same-ID readback; leave/reopen case | COMPLETED/confirmed only with retained operation and readback proof; stable after navigation | See agent results | Recorded separately | Memory restart loses data; historical Mongo restart evidence separate |
| U27-14 failed target | F; fresh S3 fixture identity/document; creator review/classification | RM | Confirm once; inspect failure; leave/reopen | Submission failed; retained ID/failure; no retry control, downstream success or false completion | See agent results | Recorded separately | Controlled offline XPI protocol, not external outage evidence |
| U27-15 uncertain target | U; fresh S3 fixture identity/document; creator review/classification | RM | Confirm once; inspect uncertain state/one identity check; leave/reopen | Outcome uncertain; Policy incomplete; identity existence does not confirm; no replay/automatic completion | See agent results | Recorded separately | Optional read-only check never resolves Policy |
| U27-16 logout/role/session | S; unsaved RM draft and visited case | RM -> Director -> HR | Logout/login roles; inspect normal landing/navigation; revisit old route | Draft/session/cache cleared; no stale prior-role data; backend inaccessible-case404; HR no case portfolio | See agent results | Recorded separately | Do not infer role from button visibility alone |
| U27-17 date filters | S; Cases and completed Onboarded records | RM, Director | Set valid/reversed/empty Created from/to on both pages | Inclusive Singapore days; server-filtered scope; reversed range controlled error; reset clears filters | See agent results | Recorded separately | Record actual day/range and resulting safe counts |
| U27-18 responsive/narrow | S; 320/720/1280px and keyboard | RM, Director, HR | Inspect navigation, tables, forms, tree, proposal/decision and target summary | Readable controls/focus; no page overflow or missing authorized action | See agent results | Recorded separately | Record widths and each role actually tested |
| U27-19 stage controls | S; active blocker and completed stages | RM | Use View details, Review, Resolve issue; inspect all12 stages | Each control reaches actual evidence/action owner; unsupported hard stops offer no invented resolution; final review last | See agent results | Recorded separately | No provider operation merely to inspect |
| U27-20 Director scope | S; Director creates unsubmitted synthetic cases in both available teams | Director | Inspect Cases; select explicit team filter; clear/filter another team | Backend-authored scope; no silent default selection; supported mutation authority retained | See agent results | Recorded separately | If only one team populated record untested alternate-team observation |
| U27-21 HR boundary | S; synthetic HR session | HR | Inspect users/teams/policy and diagnostics; try a case URL | Admin/proposal controls available; no case access; safe unavailable result | See agent results | Recorded separately | No external diagnostic lookup in this session |

## Session close and checkpoint

Stop only the owned launcher with `scripts/stop_demo_windows.bat` after the grouped
session. Do not stop another owner's process or delete any database.

Grouped outcome: PASS16, FAIL0, NOT_RUN5; AGENT_EXECUTED16 completed rows,
HUMAN_EXECUTED0. Two confirmed product presentation defects were fixed in one bounded
round and visibly retested. OCR, Garden, numeric cache counter and F/U fixture
prerequisites remain unavailable in this normal launcher; full reasons and partial
observations are in the results. No historical automated PASS substitutes for UAT.
Phase27A awaits fresh independent GPT-6.1 Sol / High BarrierA. Only exact PASS permits
27B. Maximum product remediation2 rounds; no commit before final Phase27 gate.
