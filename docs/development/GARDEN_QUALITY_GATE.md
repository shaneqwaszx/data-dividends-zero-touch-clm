# Garden Happy Path & Operator Experience — Independent Quality Gate

## Executive result

**FAIL** — frozen candidate reviewed independently on 2026-10-01. The offline clean
and discrepancy journeys execute successfully, but the operator still sees a stale
registry-review blocker after ownership recovery, document evidence is visually
unreadable, 200% content zoom overflows, and the additive processing status is not
fully represented in the frontend contract. Required physical persistence evidence
also remains unavailable. This is not an exact PASS or publication readiness.

The reviewer had no implementation role and made no candidate fixes. Only this report
was written. Remediation changes require a fresh frozen identity and independent gate.

## Reviewed identity and boundary

| Item | Value |
|---|---|
| Branch | fix/demo-happy-path-stabilization |
| Base, HEAD, local origin/main | efc31f450f0103766fa812bc0aa80754f801dbe9 |
| Frozen manifest | tmp/GARDEN_REVIEW_MANIFEST.json; 42 paths |
| Candidate SHA-256 | 5efb38952c96d941ae814d22f145daa9454a060fdb52b1444d377bfad00011d2 |
| Hash verification | All 42 path hashes matched before review and after execution |
| Reporting exclusions | GARDEN_IMPLEMENTATION_REPORT.md and this report |
| Tree/index | Task-owned modified/new files; uncommitted, unstaged |
| Authorized writes | Exactly docs/development/GARDEN_QUALITY_GATE.md |

The reviewed scope includes the complete tracked diff and task-owned new source,
tests, synthetic PDFs, plan, guide, contracts and ADR amendment listed in the manifest.
Implementation-report evidence was inspected and distinguished from independent runs.
No fetch, switch, worktree, reset, stash, clean, commit, push, PR or merge was performed.

## Acceptance assessment

| Requirement | Result | Evidence / limitation |
|---|---|---|
| Garden clean ordinary UI journey | Local execution PASS | Login, intake, PDF extraction, structured manual review, classification, explicit confirmation, Mock completion, Cases and Onboarded |
| Conflicting document/human intervention | Local execution PASS | Four field acceptances and four explicit retained registry decisions; readiness reached without target submission |
| Current official ACRA observations | NOT VERIFIED | Synthetic injected transport exercises production decoder; no new official network observation |
| Unsupported versus empty | Partial FAIL | Backend has truthful UNSUPPORTED/no call/no provenance; detailed frontend status label is missing |
| GoldTier child identity boundary | PASS in inspected/focused scope | Name-only identity is not exact; related-party dispatch remains blocked |
| Console guides and dry-run | Focused PASS | Collapsed native details, focus checks, eight-step guide, unchanged dry-run tests |
| Cases / Onboarded overlap | PASS | UI journey and backend separate-case projection regression |
| Ordinary blocker progression/no stale UI | FAIL | Registry review persists visually after reviewed supplementary ownership |
| Explicit confirmation/no target replay | Focused PASS | No completion before confirmation; ordinary POST completes Mock ledger; adverse suite passes |
| Performance evidence | Credible bounded evidence | Duplicate intelligence refresh regression; small local timing samples do not prove provider latency improvements |
| Responsive five widths | FAIL visual usability | No body overflow at normal widths, but evidence values collapse into character columns |
| 200% content magnification | FAIL | 1440 viewport produces 2015-pixel-wide full-page screenshot; descendant overflow missed by body-only assertion |
| Keyboard/focus | Focused PASS; limited | Native summary focus and registry focus exercised; no claim of exhaustive keyboard-only journey |
| Upload text/instructions | Inspected PASS | Deterministic typed extraction; no agent/tool instruction execution route introduced |
| Physical Mongo/restart | REQUIRED / PENDING | No authorized disposable local Mongo; normal Atlas/application database prohibited |
| Broad configured evidence | Implementer-reported | 1491 backend, 375 frontend, 22 canonical browser, 193 governance; not reclassified as independently executed |

## Required local fixes

### GQ-01 — P1: retained acquisition absence remains a current registry blocker

At the happy-path screenshot checkpoint, backend active exceptions contain only
TARGET_CONFIRMATION_REQUIRED, ownership is ANALYZED, and Review and Send is enabled.
Nevertheless the progress header selects **ACRA registry — Review required** and the
registry panel displays **Registry data incomplete**, REGISTRY_EXPECTED_DATA_MISSING,
and **Action: Review required**. The successful operator correction therefore leaves
stale blocker UI and obscures the actual next step.

`apps/backend/app/api_models.py` in project_processing_pipeline unconditionally maps
acquisition PARTIAL to REVIEW_REQUIRED despite registry stage completion.
`apps/frontend/src/pages/CaseStatePanels.tsx` in registryPresentation prioritizes the
retained acquisition issue and sets attention true independently of current blockers.
Preserve historical empty/unsupported evidence, but distinguish it from current identity
and ownership workflow obligations. Add readiness and completed-state regressions.

### GQ-02 — P2: document evidence layout is unreadable and magnification overflows

All six independently inspected screenshot attachments show reviewed field values and
provenance compressed into one/two-character columns, including desktop widths. For
example the 1920 screenshot is 17,881 pixels tall and the 1440 screenshot 20,391 pixels
tall; identifiers and ACRA_LOCAL_PDF_TEXT provenance read vertically. The 200% CSS
content-zoom capture at a 1440 viewport is **2015 x 57336**, establishing horizontal
overflow. The browser test only checks the body's bounding width at zoom and misses
overflowing descendants. Make affected evidence cards readable at required widths and
magnification, then test actual document scroll extent and useful field reflow.

### GQ-03 — P2: shared processing-node contract omits UNSUPPORTED

The backend ProcessingNodeStatus and relationship projection add UNSUPPORTED, but
frontend `ProcessingNodeStatus` in `apps/frontend/src/types.ts` omits it, as do
PROGRESS_STATUS_LABELS and PROGRESS_STATUS_SYMBOLS in CaseStatePanels.tsx. The distinct
registry-operation status union was updated, which does not cover this second contract.
Detailed processing renders blank status/symbol for the server value. Align the shared
contract and maps and assert a truthful visible Unsupported state.

### GQ-04 — required persistence coverage gap: new stored enum not exercised physically

The new physical restart test uses MISSING_OWNERSHIP_UEN and the existing Mock connector,
whose missing ownership operations are EMPTY. It does not persist/reload UNSUPPORTED.
The JSON bundle reconstruction test is useful but is not driver/server restart evidence.
Add an explicit guarded physical UNSUPPORTED roundtrip/restart scenario while retaining
legacy read compatibility and confirmation/no-replay assertions. Execute it only with
the authorized disposable service. An unexecuted authored test cannot satisfy this lane.

## Independently executed evidence

| Check | Result |
|---|---|
| Frozen path hashes before/after | PASS: 42 unchanged |
| Focused backend connector/protocol/acquisition/cache/orchestration | PASS: 187 collected/executed; Starlette deprecation warning |
| Four focused frontend files | PASS: 27 tests; existing SSR useLayoutEffect warnings |
| Guarded Garden browser, standard reporter | PASS: 2 tests, 14.4 seconds |
| Garden browser visual-capture rerun | PASS execution: 2 tests, 16.0 seconds; visual defects above |
| Contract discovery with ordinary-test guard applied before imports | PASS: 44 tests |
| Architecture checker | PASS |
| Supported-pattern secret scanner | PASS; not a universal secret-proof claim |
| Local performance profiler, 2 iterations per side | PASS execution; memory/Mock representative actions, zero provider requests |
| Project-state checker | FAIL: verified_main_sha unreachable from origin/main; pre-existing accepted-base conflict |
| Tracked diff whitespace | PASS |
| Physical Mongo | NOT RUN: missing authorized disposable infrastructure |
| Windows lifecycle | Not rerun; implementer reports occupied unrelated port 8000, 20 runtime tests blocked |
| Publication pre_pr gate | NOT RUN: intentionally uncommitted handoff |

The first scoped frontend/browser attempts encountered Vite/esbuild sandbox ancestor-read
errors. Scoped offline escalated reruns succeeded; no candidate mutation or dependency
installation was required. Visual capture used an in-memory harness reporter override
and OS-temp HTML output, leaving frozen source bytes unchanged. Original configured
passing-run attachments are discarded by preserveOutput=never and the line reporter.

The reviewer initially ran contract discovery without the ordinary-test guard. Importing
app.main implicitly resolved normal settings, possibly including dotenv, and attempted
Mongo DNS resolution. It timed out before an established database client/server connection;
no database mutation occurred and no URI/secret was printed or inspected. This was a
verification error, not authorized physical evidence. Subsequent discovery explicitly
called enforce_ordinary_test_environment before app.main imports and passed. Do not
repeat ambient-config discovery or categorically claim no implicit dotenv access.

Synthetic visual evidence is in OS temp:
`C:/Users/shane/AppData/Local/Temp/garden-qg-visual-xh3evi1g/data/`.

| Width / magnification | PNG | Dimensions |
|---|---|---|
| 360 | 09b256db77493447844aa9fcc27092880524be22.png | 360 x 25822 |
| 768 | 292f1dd01bcb9df2288c1cbcf903d5feeb278d54.png | 768 x 22057 |
| 1280 | 2592b9f905728b43d757c035e2fef5814afcd438.png | 1280 x 21341 |
| 1440 | 61d29009ca8780ccb3a01d0cf0d01d15c9fb9543.png | 1440 x 20391 |
| 1920 | 10067e0344128f853947a357291b7b159de62fb7.png | 1920 x 17881 |
| CSS content zoom 200% at 1440 | 334e46b200b4f6977c812bb7a37020d01a0a87f9.png | 2015 x 57336 |

This proves CSS content magnification behavior; native browser-chrome zoom was not tested.
The browser paths use normal UI mutations; summary GETs are observation only, with no
direct database writes or hidden stage-skipping endpoint.

## Architecture, contracts, security and authority

Existing connector -> strict DTO -> canonical evidence -> mapper ownership remains.
No route-to-Mongo owner, alternate Decimal engine, target-ledger bypass, foreign registry,
child-party dispatch, source precedence rule, or Live provider promotion was introduced.
PARTIAL identity continuation is bounded by canonical validation; FAILED acquisitions
still stop dependent work. Structured declaration stays LOCAL / USER_SUPPLIED_DECLARATION
/ MANUAL_DECLARATION_POC and binds current reviewed document/version, actor and rationale.
The changed review path retains owning-lock reauthorization and preconfirmation checks.
Frontend cache keys/session clearing/cancellation owners remain; intelligence invalidation
is deduplicated without global mutation retry. No new security defect was established in
the inspected changed scope; broader production policies remain sponsor dependencies.

API/type changed additively; durable stored operation enum changed; connector no-call
semantics changed; explicit test-only launch composition changed. Bounded workflow recovery
and UI/runtime behavior changed. Target mapping, UBO threshold, auth owner and provider
Live classification did not change. Physical claims remain unverified.

Actual external ACRA reads: 0. Actual external GoldTier reads/writes: 0. Only local Mock
target completion occurred. The inadvertent ambient Mongo DNS attempt is separately
disclosed above. No application database cleanup, raw sponsor artefact access or unrelated
process termination was performed.

## Missing evidence and later dependencies

Required physical evidence is pending and cannot be waived. The user prohibits normal
Atlas/MONGO_URI cleanup and reports no disposable local Mongo. Existing GitHub mongo:7
CI can provide evidence only after a separately authorized publication route, or a newly
authorized disposable service can provide it. This gate does not authorize either step.

Current official Marketplace observations were not dispatched; synthetic input proves
adapter/local workflow behavior only. The proposed bounded external budget remains one
token, two entityBasicInformation, one coShareholdersDetails, zero Relationships and zero
GoldTier activity, subject to separate authorization. GoldTier childId lifecycle,
name-only customer identity, full subscriber ACRA semantics, final approval and Live
interoperability remain distinct sponsor/external dependencies.

## Readiness and next action

**Exact independent verdict: FAIL.** Local clean/discrepancy execution succeeds but full
Garden operator acceptance does not. Publication and next-phase readiness are not granted.
Remediate GQ-01 through GQ-04, run focused adverse/layout/contract checks and proportional
regression, freeze the new candidate, and obtain fresh independent re-QG. Required physical
execution must remain pending until safe infrastructure and authority are available.
