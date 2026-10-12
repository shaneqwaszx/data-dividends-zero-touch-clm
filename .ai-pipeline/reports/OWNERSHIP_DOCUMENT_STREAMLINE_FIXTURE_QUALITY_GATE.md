# PR83 fixture reconciliation — fresh independent Quality Gate

## Outcome

**FAIL. Required findings: P0=0, P1=0, P2=1.** ODS-P1QG-04's fifteen backend
arrangements are reconciled without weakening their assertions. The fresh canonical
browser shard fails in a separate initial-intake arrangement, and the remaining
required browser coverage is not executed. Focused passing evidence cannot provide
exact PASS or publication readiness.

Review date: 2026-10-12, Asia/Singapore. This is an implementation-independent review
of the failed Stage C candidate, not an acceptance gate following a completed Stage C.
The reviewer changed only this assigned durable report. Ignored runtime logs are
verification outputs. No reviewed source, tests, contracts, planner, configuration or
historical report was edited; no Git or GitHub mutation was performed.

## Reviewed identity and authority

- Worktree: `C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.ownership-hotfix`.
- Branch: `feat/ownership-ubo-doc-review-streamline`.
- Published/task HEAD: `169a5db0348c0ae6384289215410ed4d69fb23ad`.
- BASE_SHA and inspected `origin/main`: `a6c80d2f20048ce64b3f6184df34c098f8fff4ab`.
  This reviewer did not fetch; latest-main publication assessment remains conditional.
- Frozen manifest: `tmp/pr83-fixture-evidence/candidate-manifest.json`, **39 paths**.
- Aggregate identity: `c77e0f3d622247a2d6c8b622bbed76adee757fc36afa618798a9ee70bfbd505e`.
- Full tracked base diff SHA256:
  `9c69fa75ba8b0f55e29556e1cdea71c8b7cfa86f39f7026795818991625a5aa4`.
- Tracked HEAD delta SHA256:
  `53ddbafe4af78ae52a722f115ca4f5754c29aacfabf2cc862198b102740cd518`.
- Prior 35-path identity:
  `687430e24c88770993b0863033f905234d885510c7b40685f40511d5f1447cdf`.
- Immutable preceding P1 FAIL report SHA256:
  `39d281066dc9497db1b5d25966dce62acf06e4dc4084239f8b05f0fd98084d6f`.

Every raw file hash, canonical JSON aggregate and both diff hashes matched before and
after review. The verification manifest's entries and aggregate equal the candidate
manifest. All 35 prior raw hashes also match; the two newly reconciled backend suites
were added to the expanded review identity. This report is excluded from its own
reviewed identity. Aggregate algorithm: SHA256 of UTF-8 JSON manifest entries with
`sort_keys=True, separators=(',', ':')`, retaining path, raw SHA256 and classification.

Authority: owner brief `fe7c11fb` read directly from its attachment; root/backend/
frontend AGENTS, `fyp-quality-gate` and report template, reviewer/security roles,
development/context/branch workflow, current fixture planner and original ownership/
document plan, preceding P1 FAIL, canonical owner map/provider matrix, intake profile,
ownership/UBO profile, ADR-011 and relevant D-062/sponsor boundaries. Context selector
ran with CI_TOOLING, BACKEND_DOMAIN, BACKEND_API and FRONTEND_UI. Security and POC
regression checklists supplement the combined review. Current source and contract
override historical automatic initial-retry assumptions.

The owner authorization covers exactly fifteen backend initial setups in two files.
No product, assertion, timeout, skip-policy or browser-fixture edit is authorized by
this slice. Conditional fixture refinement: **0 used / 1 remaining**; its scope remains
the exact fifteen backend arrangements. This gate grants no expanded authority.

## Required finding

### ODS-FIXQG-05 [P2, REQUIRED] — canonical browser initial retry lacks count completion

Location: `apps/frontend/e2e/blocker-simulation.e2e.ts:221`, assertion `:267`.
Owning distinction: `apps/backend/app/services/zero_touch_orchestration.py:700` and
initial-start guard `:903`; current intake profile requires explicit intended count.

The scenario creates a new case, uploads a valid native PDF whose extraction exceeds
the unchanged text bound (503), retries the affected document with the same failing
PDF (503), then supplies a valid replacement (201). It never explicitly completes
initial intake. At line 267 it expects WAITING_FOR_REVIEW/READINESS immediately after
that successful initial retry. Actual state is PENDING_INPUTS.

**Classification: stale browser fixture/contract arrangement, outside the authorized
fifteen backend setups; no production defect demonstrated.** The existing authoritative
`started_at` is absent until legitimate initial completion. A successful targeted
initial retry preserves evidence/history and remains pending; a reupload event does
not prove intake completion. Genuine previously started recovery is separately proved
to continue. Making production auto-start this case would reopen the original P1.

Coordinator canonical shard 1/2 exited 1 at selection **11/48**, with its first ten
selections / **22 expanded cases passing**. The other 37 selections in shard 1 and all
48 selections in shard 2 are **NOT EXECUTED** after the sequential first failure.
Shard 2 receipt is absent. The aggregate is FAILED/incomplete, never PASS.
Log `tmp-pr83-fixture-shard-1.log` SHA256:
`2cde68d1e4facfbb3e47def891b5062b350b801a718779618bac8d3bfcefcb8f`.

Independent actual-browser reproduction on ports 8887/4287, with canonical tagged
composition, exited 1 with **1 failed** at the exact same line and state:

```text
python scripts/run_e2e.py --timeout-seconds 60 --backend-port 8887
  --frontend-port 4287
  --grep 'Blocker simulation actual native PDF intake failure targets retry and one continuation'
  --recovery-demo document-refresh
```

Log `tmp-pr83-fixture-reviewer-browser-recovery.log` SHA256:
`d26d780035f78b28596dbfa9517dee8ec4f7c66eded0516103f556d62805af63`.
No response interception, provider call, source fix, deadline extension or direct
state manufacture was used. The tagged composition is what the unfiltered canonical
runner selects automatically. The reviewer preserved two earlier diagnostic attempts:
default sandbox backend readiness failure (no Playwright assertion); then a normal
focused launch missing `--recovery-demo`, which failed the synthetic banner at line
233. Neither is production-failure evidence or a passing reproduction.

The failed assertion prevents this selector's later replacement-refresh/reload/recovery
and target-stopping assertions from being reached. Their source presence does not prove
their execution in this run.

**Smallest next owner authorization:** separately authorize reconciliation of this exact
browser selector with count-bound initial intake. Preserve both native 503 failures,
the 201 retry, pending-state/history assertions, keyboard/network checks and all later
started replacement-refresh/recovery/no-target-write assertions. Assert pending after
the initial retry, then explicitly complete its authored one-document intended set
through the supported visible count form before requiring readiness and exercising
started recovery. Do not infer a count from received-file success, replace readiness
with a weaker final assertion, add product exemptions or alter the runner policy.
Freeze the corrected candidate, run both canonical shards and applicable affected
checks, then obtain a fresh independent combined gate. This is guidance, not a fix or
authorization. The existing remaining backend-fixture allowance cannot cover this path.

## Fifteen-setup reconciliation

The matrix below is independently checked against the actual scenarios. An independent
AST comparison removes only each targeted first `zero.start` call's explicit constant
`expected_document_count` keyword and obtains exact equality with HEAD in both entire
files. Result: **12 call sites / 15 expanded cases**, all other statements/decorators/
assertions/control flow unchanged. The counts express authored intended files, not
successful-upload inference. `reconciliation-proof.json` agrees with that verification.

| Failed case (test prefix omitted) | Old initial arrangement | New count | Preserved purpose |
|---|---|---:|---|
| matching_document_auto_confirms_even_after_readiness_created_reconciliation | One clean intake, reconciliation, count-free start | 1 | AUTO_CONFIRMED, no pending field/intervention/document blocker, Search only |
| frozen_threshold_is_inclusive[0.85-True] | One exact-boundary document, count-free start | 1 | Inclusive confidence and original field statuses |
| frozen_threshold_is_inclusive[0.849999-False] | One below-boundary document, count-free start | 1 | Below threshold remains pending |
| partial_machine_confirmation_does_not_clear_missing_or_low_confidence[LOW_CONFIDENCE] | One low-confidence file, count-free start | 1 | REVIEW_REQUIRED, one pending field, genuine document blocker |
| partial_machine_confirmation_does_not_clear_missing_or_low_confidence[MISSING_FIELD] | One required-missing file, count-free start | 1 | Missing value/confidence retained and blocked |
| changed_canonical_value_and_operator_rejection_do_not_auto_clear | One file with explicit rejection, count-free start | 1 | Changed-canonical ineligibility and rejection/history |
| legacy_document_profile_still_requires_registered_address | One legacy-profile file, count-free start | 1 | Original profile seed and required-address discrepancy |
| duplicate_and_concurrent_start_do_not_repeat_completed_work | One file, two barrier-synchronized starts | 1 in each worker | Both workers race through completion; duplicate/resume versions and exact target calls unchanged |
| P06_QG_005_REVIEWED_CONFLICT_EARLIER_DOCUMENT | Reviewed conflict then clean file, count-free start | 2 | Earlier reviewed reference and Search-only conflict |
| P06_QG_005_REVIEWED_CONFLICT_LATER_DOCUMENT | Clean then reviewed conflict, count-free start | 2 | Later reviewed reference and Search-only conflict |
| P11_ONE_CURRENT_FIELD_DISCREPANCY_RETAINS_BOTH_CONFLICT_DOCUMENTS | Two reviewed conflicts, count-free start | 2 | One discrepancy, both observations in insertion order |
| P06_QG_013_EQUAL_TIMESTAMPS_PRESERVE_INSERTION_ORDER_100_RUNS | Two equal-time files in each iteration | 2 | Original 100 iterations, equal times, insertion order and 100 Searches |
| P06_QG_013_FORMER_FLAKY_TEST_IS_STABLE_100_RUNS | Calls two-conflict scenario 100 times | 2 via reconciled callee | Wrapper unchanged; all original assertions repeated 100 times |
| P06_QG_005_REVIEWED_CONFLICT_RESOLVED_BY_KEEP_REGISTRY | One reviewed conflict, count-free initial start | 1 | Completion, original/reviewed values, decision and exact target calls |
| P06_QG_005_REVIEWED_LOW_CONFIDENCE_REMAINS_BLOCKED | One reviewed low-confidence file | 1 | Genuine WAITING blocker, no action, Search only |

The legacy-profile setup tests address requiredness; it does not use the compatible
single-document attach route. Its original repository seed is unchanged. The separate
compatibility-route regression still proves that supported route auto-starts. The race
retains its barrier and two workers, with no artificial pre-race start. Completed
duplicate and resume calls remain count-free. Neither 100-run loop was shortened.

## Verification and acceptance evidence

All coordinator result receipts were read and every referenced log SHA256 independently
matched raw bytes. Current results below belong to the corrected frozen candidate;
they are attributed executions, not falsely described as reviewer-run full suites.

| Lane | Exact current evidence | Result |
|---|---|---|
| Original fifteen RED | `red-results.json`, original diagnostic log | 15 failed; retained failure proof |
| Intermediate partial correction | `green-results.json` | 9 failed / 6 passed; retained, not PASS |
| Complete fifteen selection | `green2-results.json` | 15 passed / 0 skips / 1 warning, 232.50s; both 100-run bodies intact |
| P1 owners | `p1-results.json` | 19 passed / 1 warning |
| Affected backend/API/ownership/document | `regression-results.json` | 140 passed / 1 warning |
| Full backend | `backend-results.json` | 2693 passed / 151 skipped / 4 warnings, pytest 1179.19s, exit 0 |
| Full frontend | `frontend-results.json` | 597 passed / 51 files; typecheck and build exit 0 |
| Contracts/governance/static | `static-results.json` | 44 contracts, 93 governance; Ruff, mypy 127-source, state/architecture/secrets/tooling/authority/readiness/dependencies/inventory exit 0 |
| Fresh affected physical Mongo | `physical-results.json` | 14 passed / 0 skips / 1 warning, 71.63s |
| Focused actual browser | `browser-results.json` | Initial/root 2, confirmation/replacement 2, offline Garden 1: 5 passed |
| Full canonical browser | `shard-1-result.json` | FAILED at 11/48; 22 expanded passes precede one failure; shard 2 NOT EXECUTED |
| Independent backend selection | `tmp-pr83-fixture-reviewer-backend.log` | 23 passed / 0 skips / 1 warning, 37.31s, exit 0 |
| Independent canonical-composition browser | `tmp-pr83-fixture-reviewer-browser-recovery.log` | Exact assertion/state failure reproduced; exit 1 |

Full backend log SHA256:
`9b76d4ae955f132948fa8fb61749b0bcaeb93a2bf7a8e33194f83975a9dbd528`.
The 151 skips are guarded physical-Mongo tests lacking their explicit configured test
connection in the ordinary full run; they are unexecuted physical evidence, not passes.
The separate fresh 14-case physical run covers affected batch/current intake, Final
Review and Garden restart/lineage. It does not certify every skipped physical suite.
Warnings are the existing Starlette/httpx deprecation and three deliberately malformed
Pydantic conformance-fixture serializer warnings. No skips or timeout policies changed.
Inventory remains 119 expanded tests / 21 files / 96 selectors, partitioned 48+48;
inventory success does not prove shard execution.

Independent backend command used task Python, explicit AnyIO plugin, `-o addopts=`,
`-p no:cacheprovider -q -ra`, the entire `test_initial_intake_continuation.py` and
`test_ownership_document_streamline.py`, plus the reconciled matching-document test,
both confidence-boundary cases and two-worker concurrent-start case. Its log SHA256:
`cdebc9e31ff839ba787bc16e5409f9e311b7866cd927b9e95018b9a56d05ad4e`.

| Original acceptance | Assessment on frozen content |
|---|---|
| A01 Garden hierarchy | Bounded behavior supported by inspected retained-row source, fresh Garden browser and full frontend evidence. |
| A02 Exact direct/effective values | Existing Decimal engine/API strings remain authoritative; hierarchy displays retained values and labels unknown intermediates. |
| A03 Qualifying people in both views | Shared UboSummary plus fresh Garden comparison to the same backend candidates. |
| A04 No false entity/below-threshold promotion | Natural-person/MET/provisional filter and executed frontend/engine regressions preserved. |
| A05 Paths/cycles/unsupported evidence | Disjoint occurrence IDs, bounded traversal, explicit cycle/unlinked/limited states; existing engine adverse coverage preserved. |
| A06 Keyboard/mobile/drill-down | Fresh root/Garden browser assertions cover selection, collapse, 360px layout and reload; full frontend tests pass. |
| A07 Precision/provenance/reload | Backend strings, retained sources, LOCAL supplement labels and reload assertions preserved. |
| B01 Whole grouped decisions | Prevalidation precedes writes; partial groups reject; independent owner suite passes. |
| B02 Authorized sufficient continuation | Initial group cannot complete intake; legitimately started review continues once. Independent proof passes. |
| B03 Reject/replace | Genuine rejected/missing evidence stays blocked; actual four-field browser path passes. |
| B04 Current slot/history | Independent replacement lineage and failed-sibling tests pass; fresh physical restart evidence matches. |
| B05 Eligible replacement/retry | Started sufficient recovery advances, initial replacement/retry stays pending; independent proof passes. |
| B06 Low/conflicting replacement | One extraction and truthful document checkpoint are independently exercised. |
| B07 Auth/currentness/race/freeze | Existing lock/CAS and reauthorization inspected; affected suite and independent concurrent-start pass; required complete browser lane remains incomplete. |
| B08 Mongo restart | Fresh affected 14-case physical evidence supports retained started/initial distinction, receipts and lineage. |
| B09 Separate target confirmation | Independent adverse suites retain Search-only, null confirmation/result; no ledger bypass found. |
| B10 Garden PARTIAL/distinct COMPLETE | Existing source classification and explicit synthetic declaration remain distinct; fresh root/Garden selectors pass. |
| B11 Truthful failures | Independent native browser stops correctly pending, safe503/history/no replay tests pass; its later recovery segment is not reached. |
| B12 No false UI completion/replay | Inspected settlement/scoped action owners and focused evidence preserved; complete canonical acceptance remains blocked by ODS-FIXQG-05. |

These bounded assessments do not waive the failed required canonical aggregate. No
complete A01–A07/B01–B12 release acceptance is claimed on this candidate.

## Prior findings, architecture and security

- **ODS-QG-01 remains closed on exercised content:** confirmation/replacement and
  replacement-refresh recovery stop for a failed sibling, preserve receipts/history
  and permit its targeted retry; independent owner tests pass.
- **ODS-RQG-02 remains closed:** accepted final retry followed by owning continuation
  failure projects safe503, retains TECHNICAL_FAILURE/history and rejects replay;
  independently executed HTTP regression passes.
- **ODS-FQG-03 remains closed on current presentation evidence:** JSON tuple namespaces
  distinguish root/path/unlinked occurrences; valid sentinel/delimiter and repeated-path
  tests remain, and the fresh root browser selector passes. No new duplicate-key defect
  was demonstrated.
- **Original P1 bypass is corrected in local candidate evidence:** explicit count,
  wrong-count no advancement, one valid start, no pre-completion confirmation/retry/
  replacement auto-start, and supported compatibility route all independently pass.
  This does not claim the uncommitted correction is published or its GitHub thread
  resolved.
- **ODS-P1QG-04 is reconciled:** entire two-file AST proof, original 15 GREEN and full
  backend zero failures. Its historical FAIL report stays immutable; this gate still
  FAILS for the separate required browser blocker.

The fixture slice creates no owner/interface/schema/configuration or runtime change.
Retained production delta stays in ZeroTouchOrchestrator, document/reconciliation/CLM
and target-ledger owners. Existing started_at supplies the durable initial/recovery
distinction; no inferred received-file count or completion flag is stored. Whole-group
validation and section checkpoint recovery preserve ADR-011's limits; no cross-document
or cross-owner transaction is claimed. Backend auth/team/creator/currentness and
locked reauthorization remain authoritative. Read-only hierarchy/UBO components reuse
backend retained Decimal classifications and provenance, with bounded unknown states.
No second ownership engine, route-to-Mongo path, target replay or frontend authority
was introduced.

No new secret, confidential artefact, raw upload/provider body, private exception or
credential exposure was found in the reviewed delta. Secret/governance checks passed.
Reviewer used child-only PYTHONPATH and Tesseract PATH, generated synthetic local
providers, separate ports and the guarded lifecycle. No .env, protected database,
real ACRA or GoldTier Sandbox mutation, package install or host policy change occurred.
Reviewer did not connect to or clean Mongo; the coordinator supplied the fresh affected
physical evidence and subsequently reported task-owned cleanup after all reviewer
runners exited. The cleanup receipt is operational evidence, not product acceptance.

Later sponsor dependencies (legal/control UBO, production review/retention/identity,
Live providers, related-party/hierarchy/file-transfer and GoldTier-internal approval)
remain separate from this current browser blocker. D-062 confirms the bounded numeric
comparator only. No Mock/Local/Partial/Dormant evidence is relabelled Live.

| Surface | Current fixture slice / retained candidate impact |
|---|---|
| API/type | Fixture slice unchanged; retained P1 count-free initial resume 409 and safe503 behavior, no route/DTO shape change. |
| Schema/persistence | Unchanged schema/repository semantics; existing started_at, lineage, checkpoints/CAS reused. |
| Connector/configuration | Unchanged; child runtime setup only, synthetic local verification. |
| Business rule/mapping | Fixture slice unchanged; retained explicit initial completion safeguard and started continuation, ownership/source/threshold/target mapping unchanged. |
| Auth/security | No grant/policy/owner change; existing guards and safe projections retained. |
| Architecture/provider status | Owners/dependencies and Mock/Local/Partial/Dormant classifications unchanged. |
| Runtime/UI | Fixture slice no runtime edit; retained bounded hierarchy/shared summary, blank intended-count form, initial pending and genuine started continuation. |
| Tests/tooling | Twelve existing initial calls gain explicit authored count1/2; fifteen original cases, assertions/races/100-run loops retained. |

## Readiness, hygiene and next action

**Exact independent verdict: FAIL. No commit, push, PR83 update, review-thread reply/
resolution, integration/publication or merge follows this candidate.** Required full
browser acceptance remains failed/incomplete. Latest-main integration, clean committed
pre-PR and remote candidate CI have not executed; none is claimed PASS. Remote billing
restrictions remain a later separate release decision, not a reason to waive local
failure. No next phase or real ACRA/GoldTier readiness is asserted.

The smallest justified next action is the explicit separate browser-selector scope
authorization described in ODS-FIXQG-05, followed by complete canonical verification
and fresh independent review. No in-scope additional fixture issue was demonstrated;
the conditional remaining backend refinement allowance is unconsumed.

At start: 14 tracked modified paths, 3 task-owned untracked paths, no staged content.
This report adds one untracked durable path. `git diff --check` passed; whitespace was
explicitly checked in task-owned untracked planner/P1 report/initial-intake test.
All 39 frozen hashes and prior historical-report hashes matched at closeout. Primary
checkout and other worktrees were not edited. Independent runtime checks exited before
the coordinator reclaimed shared resources. No source fix, staging, commit, fetch,
integration, push, GitHub reply, thread resolution, PR mutation or next phase occurred.

## Complete frozen reviewed path set

The manifest records raw hashes/classification for this exact set:

```text
.ai-pipeline/001_planner/OWNERSHIP_DOCUMENT_STREAMLINE_PLAN.md
.ai-pipeline/001_planner/PR83_FIXTURE_RECONCILIATION.md
.ai-pipeline/reports/OWNERSHIP_DOCUMENT_STREAMLINE_FINAL_QUALITY_GATE.md
.ai-pipeline/reports/OWNERSHIP_DOCUMENT_STREAMLINE_OVERNIGHT_CYCLE_1_QUALITY_GATE.md
.ai-pipeline/reports/OWNERSHIP_DOCUMENT_STREAMLINE_OVERNIGHT_RECOVERY_QUALITY_GATE.md
.ai-pipeline/reports/OWNERSHIP_DOCUMENT_STREAMLINE_PR83_P1_QUALITY_GATE.md
.ai-pipeline/reports/OWNERSHIP_DOCUMENT_STREAMLINE_QUALITY_GATE.md
.ai-pipeline/reports/OWNERSHIP_DOCUMENT_STREAMLINE_REMEDIATION_QUALITY_GATE.md
apps/backend/app/domain/zero_touch.py
apps/backend/app/main.py
apps/backend/app/services/zero_touch_orchestration.py
apps/backend/tests/test_batch_review_real_mongo.py
apps/backend/tests/test_initial_intake_continuation.py
apps/backend/tests/test_ownership_document_streamline.py
apps/backend/tests/test_phase12_persistence.py
apps/backend/tests/test_zero_touch_exception_remediation.py
apps/backend/tests/test_zero_touch_orchestration.py
apps/frontend/e2e/authenticated-zero-touch.e2e.ts
apps/frontend/e2e/blocker-simulation.e2e.ts
apps/frontend/e2e/ownership-document-streamline.e2e.ts
apps/frontend/e2e/phase24-identity.e2e.ts
apps/frontend/src/Phase15CNavigation.test.tsx
apps/frontend/src/design-system.css
apps/frontend/src/pages/CaseDetail.tsx
apps/frontend/src/pages/DocumentEvidencePanel.test.tsx
apps/frontend/src/pages/DocumentEvidencePanel.tsx
apps/frontend/src/pages/OwnershipPathExplorer.tsx
apps/frontend/src/pages/OwnershipStructure.test.tsx
apps/frontend/src/pages/OwnershipStructure.tsx
apps/frontend/src/pages/ReviewAndSend.test.tsx
apps/frontend/src/pages/ReviewAndSend.tsx
apps/frontend/src/pages/S2OwnershipReview.test.tsx
apps/frontend/src/pages/UboSummary.tsx
apps/frontend/src/pages/ownershipStructureFixture.ts
apps/frontend/src/pages/ownershipValidIdentityFixture.json
docs/ARCHITECTURE.md
docs/PROJECT_STATE.md
docs/contracts/MULTI_DOCUMENT_INTAKE_PROFILE.md
tests/test_run_e2e.py
```
