# Ownership/document streamline remediation — independent quality gate

## Executive result

**FAIL. Required findings: P0=0, P1=0, P2=1.** Original ODS-QG-01 is repaired: grouped
confirmation, replacement and dependent-refresh recovery preserve independent failed
current documents and their targeted retry checkpoint. A fresh adverse HTTP probe finds
a separate required error-path defect in the newly automatic final intake retry.
Its continuation can raise ZeroTouchInfrastructureError without the retry route's safe
503 projection, returning generic 500 and bypassing the browser's coherent evidence
reload. This fails B11. The owner requested PASS/FAIL and only one remediation round;
no further implementation is authorized by this gate.

Review date: 2026-10-12, Asia/Singapore. This is a fresh independent review of the entire
remediated frozen candidate, not a transferred verdict from the original FAIL. The full
backend suite was still running at report time (last observed 66%); it is **PENDING, not
PASS**. Its eventual result cannot waive the reproduced current defect.

## Reviewed identity and boundary

- Worktree: `C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.ownership-hotfix`.
- Branch: `feat/ownership-ubo-doc-review-streamline`.
- BASE_SHA, HEAD and inspected fetched `origin/main`:
  `a6c80d2f20048ce64b3f6184df34c098f8fff4ab`.
- Frozen content: 21 paths, 20 implementation/test/planner/contract paths plus the
  retained original FAIL report. No staged changes.
- Aggregate SHA256: `5b917fbf31fb4566df770f282e7125c80c8d058580815670c93d11a654ff7418`.
- Algorithm: SHA256 of UTF-8 `json.dumps(entries, sort_keys=True, separators=(',', ':'))`,
  entries sorted by path, each containing `path` and its byte SHA256. The reviewed path
  list and per-file hashes are in `tmp/ownership-hotfix-evidence/remediation-manifest.json`;
  they were independently recalculated during this review and again at closeout.
- This fresh report and ignored verification output are excluded from that identity.
  The original `cdb3da...` FAIL is retained unchanged and supplies no PASS evidence.

The full tracked diff and every declared new file were inspected. Authority includes
root/backend/frontend AGENTS, the superseding principal-engineering brief, current
planner/remediation section, fyp-quality-gate and its report template, persistence skill,
development/coordination/Git workflow, architecture/provider matrix, ownership/UBO,
IDP review, multi-document intake, reconciliation, zero-touch and persistence profiles,
D-062, ADR-011, and relevant open sponsor questions. Context selectors were executed for
FRONTEND_UI, BACKEND_DOMAIN, BACKEND_API and PERSISTENCE. Existing owning API, document,
continuation, error projection and browser mutation-settlement paths were inspected.

The reviewer used the current shell/Python3.12, installed Node/npm/Vitest/TypeScript/Vite,
guarded Playwright lifecycle and task-owned Mongo7 service. Independent Python imports
were bound to this worktree rather than the reused environment's primary editable app.
Browser ports 8878/4278 and generated allowlisted `clm_p16_*` databases were used.
No `.env`, protected database, provider credentials or external provider operation was
accessed. There were no implementation, test, ordinary documentation, configuration or
Git mutations by this reviewer. Only this assigned report is a durable write.

## Findings and remediation assessment

### ODS-QG-01 [P1, CLOSED on this candidate]

Independent current-byte tests verify confirmation and replacement stop at
PENDING_INPUTS/DOCUMENT while an independent current FAILED document remains. The failed
record is unchanged; the accepted replacement retains one current lineage and original
history. Version-bound refresh recovery follows `_continue_replacement_locked`, performs
the existing dependent refresh and returns to the same reupload checkpoint. After the
last targeted retry, the case reaches WAITING_FOR_REVIEW/READINESS without target writes.

The domain exception is narrow: RESUMING is admitted only from DOCUMENT to
PENDING_INPUTS/DOCUMENT with the exact existing completed prefix and a final
DOCUMENT_REUPLOAD_REQUIRED event. Wrong stage, missing event and wrong prefix reject.
The general status table, enum, schema, repository and ledger are unchanged. Physical
restart retains the failed sibling, reviewed receipts, current replacement and targeted
retry. This closes the original defect on these bytes only.

### ODS-RQG-02 [P2, REQUIRED] — final retry continuation failure skips safe projection and reload

Affected changed call: `apps/backend/app/services/zero_touch_orchestration.py:688`,
the new `self.start` call after final failed-intake replacement. Its existing route helper
at `apps/backend/app/main.py:1711` catches DocumentProcessingInfrastructureError and
ZeroTouchRequestError, but omits ZeroTouchInfrastructureError (catch chain 1743–1758).
Other start/replace/resume routes project that class through
`_zero_touch_infrastructure_http_error` as sanitized 503.

Independent reproduction uses real current services, generated test authentication and
controlled offline documents:

1. Create a pending review document and an independent failed current document.
2. Replace the review document successfully; the remediated case stays PENDING_INPUTS.
3. Retry the failed sibling successfully, injecting OwnershipInfrastructureError only
   at the existing ownership load boundary reached by automatic continuation.
4. Replacement is accepted and the owning pipeline safely retains
   TECHNICAL_FAILURE/OWNERSHIP with OWNERSHIP_PERSISTENCE_UNAVAILABLE.
5. The typed ZeroTouchInfrastructureError escapes the retry route. Default TestClient
   reports that unhandled class; with server-exception propagation disabled the actual
   public response is HTTP 500, text/plain, fixed `Internal Server Error`.

The browser retry uses `settleEvidenceMutation` (`CaseDetail.tsx:701–706`). Its refresh
predicate (`CaseDetail.tsx:128–129`, used at 630) covers 409/503 and transport failure, but
not 500. Consequently this response skips the current summary/document/ownership reload
after accepted supersession and changed terminal stage. The browser can continue showing
last-confirmed PENDING_INPUTS and the historical retry action with a generic error.
This violates B11's truthful failed/partial processing and the current architecture's
stable sanitized API-error boundary. A later manual refresh or rejected stale retry can
recover the view; that does not satisfy automatic settlement of this authorized action.

Evidence: `tmp/qg-remediation-retry-failure-probe.py`,
`tmp/qg-remediation-retry-failure-probe.log` and
`tmp/qg-remediation-retry-failure-probe-http.log`. The probe patches ownership load,
not the orchestrator or API, and suppresses private response contents. Observed target
calls remain `['search']`. No false completion, blind target replay, data corruption,
authorization bypass or private-error disclosure is asserted. Severity is P2 because
backend safe stopping remains intact; the required correction is the newly reachable
typed failure's established API projection plus adverse HTTP/browser-settlement coverage.
This is a current defect, not accepted debt, infrastructure absence or sponsor ambiguity.

No fix was made. The one authorized remediation round has already been consumed;
only the owner can authorize any additional bounded correction and fresh independent gate.

## Acceptance checklist

PASS rows record bounded verified behavior; they do not override the overall FAIL or
the unfinished full-backend regression lane.

| Criterion | Result | Current-content evidence |
|---|---|---|
| A01 Three-level Garden display | PASS | Independent guarded Garden browser; root, SIM LIM and natural persons; inspected mobile screenshot. |
| A02 Direct/effective accuracy | PASS | Backend Decimal strings retained; direct 81.818182 in SIM LIM/effective 51.13636375000000 for ABCD123; LIM 37.500000; intermediate effective values say Not retained. |
| A03 Qualifying summary in both views | PASS | Shared UboSummary; independent Garden journey compares both stages to the same retained analysis. |
| A04 No false below-threshold/entity qualifiers | PASS | Explicit natural-person/MET/provisional filter; executed component tests; TAN/EFGH excluded and SIM LIM remains intermediate. |
| A05 Multiple paths/incomplete/unsupported truth | PASS | Full presentation review; repeated relationship paths, bounded cycle stop, unlinked/limit labels, incomplete banner and retained technical evidence; executed component tests. |
| A06 Selection, keyboard/mobile/text scaling | PASS | Independent Garden chip/collapse keyboard checks ; 360px/desktop; actual computed fonts doubled with long synthetic root name, overflow/focus asserted. |
| A07 Provenance/precision after reload | PASS | Independent browser reload; exact retained strings and LOCAL_SYNTHETIC_SUPPLEMENT/LOCAL remain distinct from official-Mock identity evidence. |
| B01 Four decisions grouped | PASS | Independent batch/physical suites; whole-group prevalidation and one affected document retention; four-field native history preserved. |
| B02 Sufficient confirmation auto-continues | PASS | Independent owner/browser checks; no extra resume POST; failed sibling now returns PENDING with retained receipts. |
| B03 Required rejection means replacement | PASS | Four rejected fields stay genuine DOCUMENT blocker; explicit replacement action and no target confirmation/result. |
| B04 Current replacement and history | PASS | Independent owner/browser/physical restart; original IDs/receipts and exactly one current lineage retained. |
| B05 Extraction/eligible continuation | PASS for successful prerequisite paths | Controlled extraction once; normal and recovered continuation stop on FAILED siblings; final retry reaches READINESS. Downstream failure projection is ODS-RQG-02. |
| B06 Conflicting/low-confidence replacement | PASS | Independently executed controlled scenarios extract once and remain genuine DOCUMENT review. |
| B07 Currentness, double click, auth, switch/freeze/concurrency | PASS for reviewed paths | Independent batch and recovery/final-review suites plus unchanged centralized session/case-action/cache owners; stale/currentness/auth/freeze reject before unsafe writes. |
| B08 Mongo restart | PASS | Independent physical 8/8, no skips; failed-sibling parameter preserves stage, lineage, receipts, target absence and targeted retry across restart. |
| B09 No target mutations before final confirmation | PASS | Independent owner/browser/physical observations; only search before approval; target confirmation/result absent. Existing ledger/freeze owner unchanged. |
| B10 Garden PARTIAL and distinct COMPLETE fixture | PASS for bounded regression evidence | Current affected120-test evidence plus independent Garden; unchanged synthetic source fixture and retained Avery 60.0/Blair 40.0 receipts; full backend remains pending. |
| B11 Truthful failed/partial processing and errors | FAIL | ODS-RQG-02: accepted final retry can return unprojected500 and skip browser evidence reload after terminal downstream failure. |
| B12 No UI/stale-cache false completion | PASS for reviewed paths | Target confirmation remains explicit; checkpoints stay PENDING/WAITING or genuine failure; no COMPLETED through confirmation/replacement; source-backed mutation identity remains unchanged. |

## Verification and evidence

Reviewer-executed against this frozen candidate:

- Focused backend: `PYTHONPATH=apps/backend`, plugin autoload disabled,
  `python -m pytest apps/backend/tests/test_ownership_document_streamline.py
  apps/backend/tests/test_batch_review_decisions.py -o addopts= -q -p no:cacheprovider`:
  **34 passed**, 41.46s. Log `tmp/qg-remediation-focused.log`.
- Adverse owners: current document-refresh recovery, Final Review editing and the
  multiple-interrupted-document retry test: **22 passed**, 30.83s. Log
  `tmp/qg-remediation-adverse.log`; covers stale/missing versions, concurrent recovery,
  auth/freeze/deletion, repeated refresh failure, target absence and final retry.
- Physical Mongo: current batch review file through `_child_environment` and existing
  generated-database cleanup fixture: **8 passed, 0 failed/errors/skipped**. Log
  `tmp/qg-remediation-mongo.log`. Cleanup verifies each generated database is absent;
  no URI printed or protected database accessed.
- Browser: owned offline lifecycle `scripts/run_e2e.py`, ports 8878/4278, discovered
  confirmation/replacement titles: **2 passed**, 9.1s, zero extra resume POSTs. Log
  `tmp/qg-remediation-browser.log`. An initial incorrect grep selected no tests and
  failed; that diagnostic is not passing evidence.
- Garden and actual text scaling: inspected evidence helper uses the same configured
  guarded lifecycle and network policy: **1 passed**, 4.7s. Log
  `tmp/qg-remediation-garden-textscale.log`. Computed font sizes are doubled and checked
  at least 1.99x; long synthetic root name, 360px overflow and native collapse focus pass.
  Mobile and actual 200% screenshots were visually inspected. No universal browser/OS
  accessibility claim follows.
- Frontend affected Vitest suites: **41 passed / 3 files**. `npm run typecheck`: PASS.
  `npm run build`: PASS, 138 modules; existing 605.80kB chunk warning remains.
- Configured backend cwd: `ruff check .`: PASS; `mypy app` with tasktmp cache:
  PASS, 127 source files.
- `check_project_state.py`, `check_architecture.py`, tracked `git diff --check`: PASS.
  Explicit21-path UTF-8/whitespace/hash checks: PASS, including untracked Markdown.
  Supported secret patterns on those exact paths: no findings. All22 stable evidence
  file hashes match. Pattern scanning complements source inspection; it is not a
  claim to detect every possible confidential value.
- New downstream-failure probe: **reproduced ODS-RQG-02** with real HTTP 500 and retained
  safe technical checkpoint; no target writes. Initial standalone imports lacked test
  paths/auth setup; corrected task-owned test environment was used for actual evidence.

Supplied current-content implementation evidence inspected:

- Focused affected backend: **120 passed**, 83.73s,
  `tmp-hotfix-remediation-focused-final.log`.
- Affected physical: **12 passed**, 65.47s, no failure/error/skip,
  `tmp-hotfix-mongo-remediation-final.log`.
- Full frontend: **587 passed / 51 files**, `tmp-hotfix-frontend-final.log`. All11 frontend
  frozen paths independently match the earlier reviewed manifest; backend remediation
  did not change those bytes. This is attributed implementation execution, not a newly
  reviewer-executed full frontend suite.
- Contracts: **44 passed**, `tmp-hotfix-contract-final.log`; contract source is unchanged.
- Full current backend: `tmp-hotfix-backend-remediation-final.log` still running at
  last inspection 66%; no final passed/failed/skipped inventory. **PENDING, not PASS**.
  Earlier interrupted full runs and the earlier119-pass/1-test-setup-failure focused
  invocation are not credited as PASS.

Starlette/httpx deprecation warnings are recorded; they do not change the assertions.
Remote CI, external interoperability and clean-committed pre-PR checks were not run.
The intentionally uncommitted handoff is not a publication-gate candidate.

## Contract, architecture, security and impact assessment

D-062 confirms only the bounded inclusive numeric default/comparator; legal/control
UBO determination remains unresolved. Both displayed candidates remain provisional.
Independent Garden evidence shows ABCD123 51.13636375000000% and LIM CHOON
HUAT 37.500000%, MET at 25.000000. Percentage provenance is LOCAL_SYNTHETIC_SUPPLEMENT /
LOCAL; official Marketplace Mock identity evidence is separate. No Garden values are
hardcoded in product UI and no frontend ownership arithmetic or competing calculator is
added. Missing intermediate results remain unknown.

ADR-011's section checkpoints and reconciliation UoW remain the durable owners. Group
prevalidation occurs before first write; partial retention is recoverable and is not a
new cross-document/case transaction. Creator/team/session/CSRF and in-lock authorization,
currentness, strict CAS, update-only persistence, supersession history and target ledger
freeze/no-replay remain authoritative. The domain remediation extends a narrow guarded
reupload exception, not a general transition or new lifecycle owner. Remaining coupling
stays in the existing orchestrator; focused presentation components are read-only.

| Surface | Reviewed impact |
|---|---|
| API/type | DTO/type/route shapes unchanged; incomplete grouped decision error and automatically progressed responses changed. ODS-RQG-02 affects safe failure projection of final retry. |
| Durable schema/repository | Unchanged; existing section checkpoints/CAS/history used; restart behavior exercised physically. |
| Connector/configuration/provider status | Unchanged; controlled Mock/Local/offline evidence only. |
| Business rule | Ownership/threshold/source/approval rules unchanged; narrow document-reupload transition and authorized continuation behavior changed. |
| Target mapping/ledger | Unchanged; no bypass or replay observed. |
| Auth/security | No grant or owner changed. Safe generic 500 does not leak private details; it violates existing typed error projection and settlement behavior. |
| Architecture | Canonical owners/dependencies unchanged; hierarchy/shared summary presentation modules added. |
| Runtime | Hierarchy and qualifying summary added; complete document actions continue to genuine next checkpoint; failed siblings preserved. |

No new secret, uploaded bytes, raw confidential sponsor artefact or raw provider body is
introduced. Production retention/reviewer policy, legal/control UBO tests, Live ACRA,
real GoldTier interoperability, related-party lifecycle and original-file transfer remain
later sponsor dependencies. They do not excuse the current API defect and are not proved
by this local gate. No other required current contract/security/architecture defect was
found in the reviewed scope.

## Required fixes, readiness and owner action

ODS-RQG-02 requires an additional explicitly authorized bounded correction and fresh
independent review; this gate does not implement or authorize it. The full current
backend regression must finish and its actual result be reported. The candidate is
**not accepted and not ready for publication**. No next phase is authorized. Real ACRA
or GoldTier readiness is unchanged and unverified by this task.

The original one remediation round is exhausted. Return this finding and exact evidence
to the owner for the next decision; do not automatically start another remediation,
commit, push, PR, integration or merge. If the owner later authorizes a correction,
changed bytes require a new freeze and independent gate. Publication additionally needs
exact PASS, separate owner approval and the documented clean-committed integration gate.

## Git and reviewer write statement

HEAD/base/inspected origin/main remain the SHA above, 13 tracked modifications and 8
original declared untracked paths, no staged changes. This fresh report adds one
untracked durable path. The frozen 21 paths were rehashed at closeout and remained
unchanged. The reviewer wrote only this assigned report and ignored tasktmp verification
artefacts/caches/build output. No implementation fix, staging, commit, push, PR, merge,
branch/worktree mutation or next phase occurred.

## Complete frozen path/hash set

| Path | SHA256 |
|---|---|
| `.ai-pipeline/001_planner/OWNERSHIP_DOCUMENT_STREAMLINE_PLAN.md` | `59e0dd0b55cae758a46e3e3d0899896e2bba9b4ca49cdcfec0d8a0a244c1f5f2` |
| `.ai-pipeline/reports/OWNERSHIP_DOCUMENT_STREAMLINE_QUALITY_GATE.md` | `cee0dbd346db3628cfd586534973221d7b3d992f2963042dfec7a0e53dd17d73` |
| `apps/backend/app/domain/zero_touch.py` | `05dad99a3c9567504a5786a8cc6929f94365898ae97a1014c222c202d15fe112` |
| `apps/backend/app/services/zero_touch_orchestration.py` | `ed701001f784d09fb05ef14ea664159d8ee03af843f6a838a649cc8312090b29` |
| `apps/backend/tests/test_batch_review_real_mongo.py` | `f470ddd21fd2c3b1d8020e2695126cb92b19a4b8c4786095fefcb3619e8c8020` |
| `apps/backend/tests/test_ownership_document_streamline.py` | `b9a425a245d20cf0a02dd0230a1082775d1d826d6262aac635424c6ec101490e` |
| `apps/backend/tests/test_phase12_persistence.py` | `e1cc2e76d8c27dd901ea481aedd7a604d12bbe7211a22a357f1da29a5d416840` |
| `apps/frontend/e2e/blocker-simulation.e2e.ts` | `fed2e207b553eca94152da439e3ed868abf9428f32d2d07fa9da0128d9e330aa` |
| `apps/frontend/e2e/ownership-document-streamline.e2e.ts` | `3127c2c9f33da9b49214c46fa7e75bd49ade16e87e1adbd077c00254b507693f` |
| `apps/frontend/src/design-system.css` | `8f8cd94b9422b75f0bfe052c32918e5eba8f50ff1702728bdc8c163120a1579a` |
| `apps/frontend/src/pages/OwnershipPathExplorer.tsx` | `e13501c39bb862a14f914255155aaf29f7ae397f8ce651010bdef468c33c57a4` |
| `apps/frontend/src/pages/OwnershipStructure.test.tsx` | `af73e9e04b2a2117a503563e41f0742b7473d6d7ee81d46cce942da33f63f3a9` |
| `apps/frontend/src/pages/OwnershipStructure.tsx` | `62deb388ef5f52b740b6ed62945fd97a8f303ea1e8842fbfd92096720d42f6aa` |
| `apps/frontend/src/pages/ReviewAndSend.test.tsx` | `aa3410712f16da80a6c5bfa4e2f7da32c87c52f8139fefaf7a0a349587d498c5` |
| `apps/frontend/src/pages/ReviewAndSend.tsx` | `f6529efa5ddb699d964cfa44221a456fa4f38b05ca2f476a266b10d4deeee6a0` |
| `apps/frontend/src/pages/S2OwnershipReview.test.tsx` | `0c3a4bbb254b3e246069934c5e417f638acfe7536a6941b1b800e96651814cbe` |
| `apps/frontend/src/pages/UboSummary.tsx` | `0329e8a59584786cc07496166c4400d5f53fd9e17abf14b7691fff4d95408e40` |
| `apps/frontend/src/pages/ownershipStructureFixture.ts` | `391e0508bba54661dd47e8d054f3174482218b642973a66f70769f83a6eed8b8` |
| `docs/ARCHITECTURE.md` | `21ddd4130a81d126ad3fcb3c4c1f9bcca6eeb7e44fd08af1eb88c44a5dfe0b15` |
| `docs/PROJECT_STATE.md` | `5490eb4f8247a14dbbb5d40e00174775a00651e13b235704029bc5eb1e8078d4` |
| `docs/contracts/MULTI_DOCUMENT_INTAKE_PROFILE.md` | `500a270c9a6e76abd5904f5755f4899ef5d4240f5b034fa4a63642caea786b12` |

## Final execution evidence addendum — 2026-10-12

This administrative addendum supersedes the earlier pending full-backend observation
and the outstanding full-regression requirement above. It does not change reviewed
source, the acceptance criteria, the **FAIL** verdict, ODS-RQG-02, or the exhausted
one-round remediation/owner authorization barrier. The original pending-at-review
statements remain as historical observations.

The coordinator's current frozen-content full backend run completed with exit0:
**2,679 passed, 155 skipped, 4 warnings in 1,185.56s (19m45s)**. The reviewer inspected
the complete final log, warnings and every skip-reason row in
`tmp-hotfix-backend-remediation-final.log`; its byte SHA256 is
`ebe71a578389a8e9bea4b983be098e974b255b6cb21d3f058a2cef09228237b3`.
The dynamic inventory is 2,834 executed-or-skipped cases, with zero failures/errors.
This is attributed coordinator execution on the unchanged candidate, independently
inspected by this reviewer; it is not a newly reviewer-executed full-suite run.

- **149 skips** are guarded physical Mongo checks because the broad ordinary run had
  no configured disposable Mongo service binding. They are unexecuted in that lane,
  never credited as passing physical coverage.
- **6 skips** are real local OCR checks because Tesseract was unavailable. Real OCR is
  not claimed. The task's controlled native extraction and unchanged OCR surface do
  not depend on those skipped real-Tesseract checks.
- The four warnings comprise the existing Starlette/httpx deprecation plus three
  malformed-provider-fixture Pydantic serialization warnings. Their original evidence
  values are not copied into the handoff.

The affected guarded physical run separately remains **12 passed, zero
failed/errors/skipped**, 65.47s; the reviewer re-read its final log. Independent
current-content batch physical verification remains **8 passed, zero
failed/errors/skipped**. Neither result converts all 149 skipped broad physical cases
into executed coverage.

The supplied task-owned cleanup receipt records zero remaining non-system databases,
no host mounts, two anonymous volumes and cleanup exit0 for the exact disposable
Mongo container. This is coordinator cleanup evidence, not a new reviewer database
operation. No protected database or URI is disclosed.

All 21 frozen file hashes and the aggregate were independently recalculated for this
addendum and still equal
`5b917fbf31fb4566df770f282e7125c80c8d058580815670c93d11a654ff7418`.
HEAD and inspected `origin/main` remain
`a6c80d2f20048ce64b3f6184df34c098f8fff4ab`; no staged or source changes occurred.
Only this assigned report was durably updated. The unapplied ignored proposal is not
implementation or reviewed accepted content. The candidate remains **not accepted and
not ready for publication** because ODS-RQG-02 still requires an owner-authorized
additional correction and fresh independent gate.
