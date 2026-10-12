# PR83 initial-intake P1 remediation - fresh independent combined quality gate

## Outcome

**FAIL. Required findings: P0=0, P1=0, P2=1.** The focused correction prevents the
initial-intake bypass and preserves exercised started recovery, but the mandatory
current full backend suite fails in 15 canonical regression cases. Their initial
fixtures still invoke count-free start against newly unstarted cases. Required broad
acceptance evidence is incomplete; exact PASS and publication are not available.

Review date: 2026-10-12, Asia/Singapore. This reviewer did not implement the candidate.
The sole durable reviewer write is this assigned report. No source, test, contract,
configuration, planner, historical report or Git state was changed. Normal generated
browser/check output is ignored verification evidence. The owner-authorized remaining
source cycle is exhausted (cycle 2/2); this report authorizes no corrective round.

## Reviewed content and authority

- Worktree: `C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.ownership-hotfix`.
- Branch: `feat/ownership-ubo-doc-review-streamline`.
- Published/task HEAD: `169a5db0348c0ae6384289215410ed4d69fb23ad`.
- HEAD tree: `e409b42f26f1ee5ef04745e7487aef53050b7609`.
- BASE_SHA and inspected latest `origin/main`:
  `a6c80d2f20048ce64b3f6184df34c098f8fff4ab`.
- Frozen full candidate: **35 paths**, including five unchanged historical reports;
  P1 remediation delta: **13 paths**, including the untracked initial-intake test.
- Manifest: `tmp/pr83-p1-evidence/candidate-manifest.json`.
- Aggregate: `687430e24c88770993b0863033f905234d885510c7b40685f40511d5f1447cdf`.
- Identity algorithm: SHA256 of UTF-8 canonical JSON of sorted manifest entries,
  `sort_keys=True, separators=(',', ':')`; each entry contains path, raw file SHA256
  and INTENDED/SUPPORTING classification. Every raw hash is separately verified.
- Full tracked base diff SHA256:
  `0ea62ade210be28072298d6c960eae8c4ea56a305a618f0ec4bb15318d085485`.
- Tracked HEAD-remediation diff SHA256:
  `ef7eeab0147748d77fecc5c646f73ef627152d35525064557a4a260c13177500`.
  These diff digests do not substitute for the raw hash of the untracked test.

All 35 raw hashes and the aggregate matched before review, during execution and at
closeout. The report is excluded from its own reviewed identity. The complete base
diff, remediation delta, declared new files and historical finding reports were
inspected. An initial path/hash-only aggregate calculation was clarified against the
actual generator; it was a different algorithm, not a content mismatch.

Authority includes root/backend/frontend AGENTS, repository quality-gate skill and
template, reviewer/security roles, workflow/context/branch guidance, active planner,
actual principal brief 5a1c60c4, overnight brief ce3841f8 and latest P1 brief 506865eb,
all five historical gates, current architecture/provider state, intake, ownership/UBO,
reconciliation, persistence and zero-touch contracts, ADR-011, D-062 and relevant open
sponsor questions. Context selection ran with BACKEND_DOMAIN, BACKEND_API, FRONTEND_UI
and CI_TOOLING. Security and POC regression skill checklists supplement the combined
review. Historical PASS is not transferred to changed candidate content.

Current capabilities used: PowerShell, task-bound Python/pytest with explicit AnyIO,
installed npm/Vitest and the guarded Playwright lifecycle. PYTHONPATH points at this
worktree, avoiding the primary checkout's shared editable environment. Browser ports
8887/4287 were exclusive and used the existing 60-second deadline. Tesseract was exposed
only in the child PATH. Runtime checks began only after the coordinator released its
heavy lane. No dotenv, credentials, protected database, external provider mutation,
package installation or Windows administrator change occurred. Reviewer touched no
Mongo database; attributed physical evidence is identified below.

## Required finding

### ODS-P1QG-04 [P2, REQUIRED] - canonical initial-start fixtures are not reconciled

Changed guard: `apps/backend/app/services/zero_touch_orchestration.py:903-907`.
Representative consumers:
`apps/backend/tests/test_zero_touch_exception_remediation.py:34` and
`apps/backend/tests/test_zero_touch_orchestration.py:1655`, `:1926`, `:2963`,
`:2988`, `:3011`, `:3051`, `:3086`, `:3122`.

The owner explicitly requires initial intake to remain count-bound and original
regressions to remain satisfied. The new guard correctly rejects unstarted
PENDING_INPUTS with no expected_document_count. Two unchanged canonical test files
still create fresh unstarted cases/documents and call `zero.start(case_id=...)`
without completing initial intake. Consequently their substantive threshold,
required-field, conflict, concurrency and historical ordering assertions are not
reached. This is a required fixture/contract reconciliation and verification defect;
it is not proof that a correctly count-bound production path is broken.

Coordinator full execution completed exit1 with **15 failed, 2678 passed, 151 skipped,
4 warnings**, 965.39s. Dynamic inventory: 2844 cases. All 15 failures end with the same
ZeroTouchRequestError at guard 904: complete intended intake before starting onboarding.
The complete log and every failure chain were inspected. Log
`tmp-pr83-p1-backend-full.log` has raw SHA256
`54c30b70b7acbc293b9988d52d926c79e3fa4bce480ee4adba6fdf5c413b967c`;
the coordinator result receipt is `tmp/pr83-p1-evidence/backend-results.json`.

Independent reproduction used the existing failing canonical test plus the unchanged
current initial-intake and owning continuation suites. Result: **1 failed, 19 passed,
1 existing warning**, 28.18s, exit1 (tool session 8359). The failure is exactly
`test_matching_document_auto_confirms_even_after_readiness_created_reconciliation`,
test line 34/guard 904. The 19 successful bodies do not turn that command into PASS.

Affected failures are:

- Six cases in `test_zero_touch_exception_remediation.py`: matching-document
  confirmation after reconciliation; both inclusive confidence boundaries; both
  partial low/missing-confidence cases; changed canonical/operator rejection.
- Nine cases in `test_zero_touch_orchestration.py`: legacy required address;
  duplicate/concurrent start; earlier and later reviewed conflicts; one current
  discrepancy retaining both documents;100-run equal-time insertion order;
  former-flaky100-run wrapper; conflict resolution preserving originals;
  reviewed low confidence remaining blocked.

Required future correction, only under a new owner authorization: establish initial
completion through the existing explicit count-bound owner in these canonical fixtures,
preserve every substantive assertion, and rerun focused plus required broad evidence.
Do not loosen the new guard, add an inferred/hardcoded product completion count, delete
assertions, exclude tests or relabel this failed suite. No fix was made here.

## Correction and prior finding assessment

The shared `_initial_intake_pending` predicate uses existing status and started_at.
Grouped decisions retain current receipts without starting initial automation;
initial replacement and failed-upload retry retain current supersession/eligible
machine confirmations without advancing. Count-free initial resume fails 409. Correct
explicit completion starts once; repeated completion is idempotent. Existing started
reupload recovery retains its start time and automatically continues when sufficient.
A reupload event alone cannot make initial intake eligible. Single-document compatibility
still uses its existing attach/start path.

The UI uses the existing authoritative nullable timing projection for presentation.
Initial completion requires a blank user-entered intended count and calls the existing
count-bound completion API. It does not infer a count from received documents. Mutation
settlement and actor/case/query lifetime owners are reused; no automatic resume or
target confirmation is introduced. Fresh real browser evidence verifies wrong count 409,
remaining intake, reload/second upload, correct completion, one start event and absent
target mutation. The mobile screenshot was visually inspected.

**ODS-QG-01 remains CLOSED on exercised current paths:** owning tests preserve the
failed current sibling, receipts, lineage and retryability after confirmation,
replacement and version-bound dependent-refresh recovery. Final retry alone continues.
The narrow RESUMING/DOCUMENT transition still requires its completed prefix and
DOCUMENT_REUPLOAD_REQUIRED event; wrong stage/event/prefix reject.

**ODS-RQG-02 remains CLOSED on exercised current paths:** the shared retry handler
projects ZeroTouchInfrastructureError through its existing sanitized 503 helper.
Accepted replacement/current terminal checkpoint and original event prefix survive;
replay rejects. Frontend tests verify one POST/four GET settlement, retained accepted
history, terminal error, no obsolete retry control and no extra resume.

**ODS-FQG-03 remains CLOSED:** disjoint structured JSON occurrence keys preserve
client, path and unlinked identity. Ordered relationship arrays distinguish direct A.B
from composed A,B. Current keys drive selection/collapse and prune obsolete occurrences.
Fresh validated source/Decimal/API probes retain root/Avery60 and two paths/Avery 40,
Search-only calls, and exact canonical fixture equality. Focused UI arbitrary-ID and
refresh tests pass; a fresh real authenticated root-ID browser verifies keyboard,
360 px/reload, correct holder and no duplicate key warnings.

## Acceptance assessment

These rows state assessed evidence and its boundaries. They do not grant whole-candidate
acceptance despite the mandatory broad regression failure.

| Criterion | Assessment and direct evidence |
|---|---|
| A01 Garden hierarchy | Source and current focused presentation tests retain legal root, intermediate holder and people; prior exact unchanged presentation evidence is historical support. No new Garden browser execution in this stopped gate. |
| A02 Authoritative direct/effective values | Current focused precision tests and fresh Decimal/API probes pass; no frontend calculator or rounding-based classification. Garden retained strings remain 51.13636375000000 and 37.500000. |
| A03 Qualifying summary in both views | Shared UboSummary with current ReviewAndSend/S2 tests; natural-person/MET/provisional filter and exact values. |
| A04 No entity/below-threshold promotion | Current focused filtering tests pass; entities and below-threshold persons remain outside qualifying list. |
| A05 Graph/path/cycle/unsupported truth | Current repeated/unlinked/cycle tests and fresh composed-path engine/API challenge pass; limits remain explicit. |
| A06 Selection/keyboard/mobile | Current arbitrary-ID/refresh tests and fresh authenticated root-ID browser pass at desktop/360 px/reload; historical text-scaling remains attributed to original presentation bytes. |
| A07 Provenance/precision/reload | Fresh canonical API fixture equality and root-ID browser reload pass; provider/local supplement labels remain separate. |
| B01 Grouped decisions | Current owning tests prevalidate complete groups before receipt writes; exact retained initial receipts remain idempotent. |
| B02 One sufficient authorized continuation | Current P1/owning tests verify correct explicit initial completion once and automatic genuinely started confirmation/recovery; initial partial confirmation does not start. |
| B03 Rejected required evidence blocked | Current owning REJECTED path stays genuine DOCUMENT review; replacement action remains. |
| B04 Active replacement/history | Current owning and attributed physical 14-case evidence retain current slot, prior IDs/receipts and restart history. |
| B05 Eligible extraction/continuation once | Current extraction-count/recovery tests pass; initial replacement/retry remain pending, started recovery continues. |
| B06 Low/conflicting replacement | Current owning tests extract once and retain DOCUMENT review. |
| B07 Auth/currentness/concurrency/freeze | Existing locked creator/team/freeze/CAS owners retained; current focused adverse coverage passes. Required canonical concurrent-start regression is blocked by its initial fixture: ODS-P1QG-04. |
| B08 Mongo restart/lineage | Coordinator current guarded 14 PASS/0 skip, inspected physical tests and log; reviewer did not rerun Mongo. Initial review/retry, count refusal and genuine recovery persist across restart. |
| B09 Final explicit confirmation/no replay | Current owner/API/browser evidence retains Search-only target activity or no restart calls and null confirmation/result; ledger owner unchanged. |
| B10 Garden PARTIAL/distinct COMPLETE | Current source/fixture and fresh validated COMPLETE source assessed; required full canonical confidence/conflict/order evidence does not pass: ODS-P1QG-04. |
| B11 Truthful technical/partial errors | Current failed-sibling/typed503 tests and frontend authoritative reload pass; failures are not successful continuation. |
| B12 No false completion | Current initial browser and owner tests remain PENDING until explicit completion, then WAITING/READINESS without dispatch confirmation or target result. |
| P1 A partial initial decisions | Independent current regression and actual browser PASS; no start/ownership advancement. |
| P1 B wrong intended count | Independent current tests/browser PASS 409 without advancement. |
| P1 C correct count | Independent current tests/browser PASS one continuation/start and idempotent repeat. |
| P1 D single document | Independent current compatibility test PASS. |
| P1 E interrupted/failed sibling/replacement/final retry | Independent current owning tests PASS; initial reupload-event-only eligibility rejects; genuine started recovery preserved. |
| P1 F restart/currentness/auth/frozen/no replay | Current physical evidence attributed; currentness/history/creator/freeze owners reviewed; broad canonical concurrency evidence is not accepted while ODS-P1QG-04 remains. |
| P1 G all originals/three findings closed | Earlier three findings remain closed on exercised paths, but original full regression requirement FAILS. Overall G and whole candidate are not accepted. |

## Verification ledger

Independent current execution:

- Task PYTHONPATH; PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; explicit AnyIO, no pytest cache;
  `pytest test_initial_intake_continuation.py test_ownership_document_streamline.py`
  plus the representative old failing case: **1 failed / 19 passed / 0 skipped**, 28.18s.
- `npm test -- --run` OwnershipStructure, ReviewAndSend, S2OwnershipReview,
  Phase15CNavigation and DocumentEvidencePanel: **109 passed / 5 files / 0 skipped**.
- Two fresh read-only validated Mock source/Decimal/API challenges: **PASS**, root 60
  and composed-path40/two paths, canonical fixture equality and Search-only calls.
  Existing historical probe outputs were not overwritten.
- Guarded `run_e2e.py --backend-port 8887 --frontend-port 4287 --timeout-seconds 60
  --grep 'PR83 initial multi-file intake|Ownership hotfix valid root identity'`:
  **2 passed**, 8.7s; exit 0, owned lifecycle cleanup. No browser timeout/skip change.
- `check_architecture.py`, `check_project_state.py`, full tracked base diff whitespace,
  explicit 35-path UTF-8/trailing-whitespace/merge-marker/raw-hash checks: **PASS**.
- Exact 35-path supported secret scanner: **no findings**. Pattern coverage complements
  source inspection; it is not a universal secret/confidential-data detection claim.

Coordinator current evidence independently inspected:

- Full backend **15 FAIL / 2678 PASS / 151 SKIP / 4 warnings**, 965.39s, log/hash above.
  All 151 skips are unconfigured guarded physical checks in this ordinary broad lane;
  separate 14-pass physical evidence does not convert them to executed coverage.
  Four existing warnings are Starlette/httpx deprecation and three intentionally
  malformed-provider-fixture Pydantic serializer warnings.
- `tmp-pr83-p1-owner-final.log`: **19 passed**, 1 existing warning, 27.54s.
- `tmp-pr83-p1-physical-corrected.log`: **14 passed / 0 skip**, 74.35s. Guarded generated
  allowlisted databases only; root owns final container cleanup. No protected DB/URI
  appears in this report. Ten batch, two Final Review and two Garden partial cases.
- `tmp-pr83-p1-browser-initial.log`: **1 passed**, 4.9s, real authenticated initial flow.
  Independent fresh two-test browser execution is separately identified above.
- `tmp-pr83-p1-ui-green.log`: current **61 passed / 2 files** focused UI evidence.
  `tmp-pr83-p1-typecheck.log`: current typecheck PASS. Configured Ruff/mypy 127-source
  evidence was supplied by the coordinator; no new reviewer whole-type/lint run claimed.
- Current inventory receipt records 119 tests / 21 files / 96 selectors, strict 48+48 partition
  and 8700 budget. The runner/deadline/shard execution policy did not change. Inventory
  does not prove execution of either full canonical shard.

Diagnostic RED evidence remains FAILED: corrected initial API probe 3 status failures,
count-free resume 200 versus 409, UI 3 failures, and the earlier physical assertion expecting
409 for an exact retained initial group. Existing prepare_review_group/retain_review_group
explicitly permit exact unchanged receipt recovery without duplicate writes; corrected
physical assertions prove unchanged version/timeline/history. This correction does not
weaken stale-input validation. The first absent-DTO-field probe was harness-only.

Historical backend 2680/155, frontend 595 and earlier E2E 118 evidence are not fresh
certification of changed bytes. After the acceptance-blocking full-backend failure,
remaining full frontend/build, publication contracts/security/governance, both canonical
shards, latest-main integration, committed pre-PR, push and remote verification were
not executed in this gate. Focused independent lanes do not waive those requirements.

## Contract, architecture and security

The correction stays in ZeroTouchOrchestrator and the existing document, lock/CAS,
reconciliation, CLM and target-ledger owners. Existing started_at is durable and its
nullable timing projection is already authoritative; no new completion flag/schema,
state owner or browser authorization is introduced. Initial document auto-confirmation
uses the same bounded semantic owner as ordinary intake and retains genuine mismatches,
low confidence, missing evidence and failures.

Whole-group validation precedes section writes. ADR-011's exact receipt repair and
section-level recoverability remain; no cross-document/case transaction is claimed.
Creator/team/session/CSRF and in-lock reauthorization, current fingerprints/versions,
strict envelope CAS, update-only persistence, no resurrection and target freeze remain
authoritative. Safe503 retains technical stopping rather than converting failure to
progression. No raw upload, private error, provider payload or secret was introduced.

Ownership continues to use one Decimal engine, exact retained percentages and provisional
classification. D-062 confirms only the bounded inclusive numeric comparator; broader
legal/control policy remains open. LOCAL synthetic percentages never become official
ACRA or Live evidence. Production identity/reviewer/retention, complete legal UBO,
real provider interoperability, related parties/hierarchy and original-file transfer
remain later sponsor dependencies, not excuses for the current verification defect.

| Surface | Impact |
|---|---|
| API/type | Routes/DTO/type shapes unchanged; initial count-free resume now incomplete-intake 409, document actions retain pending state; earlier safe 503 preserved. |
| Schema/persistence | No durable schema/repository change; existing started_at, lineage, section checkpoints and CAS reused. |
| Connector/configuration | Unchanged; controlled Mock/Local/offline evidence and child-only runtime setup. |
| Business rule | Ownership, threshold, source precedence and approval rules unchanged; explicit initial completion boundary and scoped continuation behavior corrected. |
| Mapping/target ledger | Unchanged; final confirmation/order/call stopping/no replay preserved. |
| Auth/security | No grant/policy/owner change; existing backend guards and safe error projection retained. |
| Architecture | Existing owner/dependency direction retained; original read-only presentation components remain. |
| Provider status | Mock/Local/Partial/Dormant unchanged; no Live claim. |
| Runtime/UI | Initial intake stays pending; explicit blank intended-count form; genuine recovery automatic continuation and original hierarchy/shared summary. |
| Tests/tooling | P1 regressions and 96-selector expectation added; canonical initial-start fixtures remain unreconciled, causing this FAIL. |

No additional current security or count-bound production-path defect was demonstrated.
Accepted existing limits remain bounded hierarchy/path presentation, unknown intermediate
values and single-process/section-level POC guarantees. They do not waive required tests.

## Required fixes, readiness and closeout

**Exact independent gate: FAIL. Not accepted; no commit/push/PR update/thread resolution
or merge is permitted on this candidate.** ODS-P1QG-04 is the required next issue.
The remaining source cycle has been used; a further fixture correction and fresh gate
require separate owner authorization. No next phase or real ACRA/GoldTier readiness
is asserted. The existing published PR83 HEAD remains unchanged by this reviewer.

At review start there were 12 tracked modifications, one task-owned untracked test and
no staged content. This assigned report adds one untracked durable path. Branch/HEAD/
base/inspected main remain as recorded. The primary checkout and other worktrees were
not edited. All 35 frozen raw hashes, classification aggregate and both diff digests
were rechecked at closeout; historical reports remain byte-identical. Runtime lane
was returned to the coordinator after owned browser cleanup; reviewer touched no Mongo.

The safe continuation point is the preserved frozen candidate, failure log/receipt and
this report. Preserve the failures and original assertions; do not manufacture PASS.
No source correction, staging, commit, fetch, integration, push, GitHub message, thread
resolution, PR modification, merge or another phase occurred in this review.
