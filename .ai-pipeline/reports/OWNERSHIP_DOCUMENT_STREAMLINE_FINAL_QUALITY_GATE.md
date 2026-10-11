# Ownership/document streamline â€” final independent quality gate

## Executive result

**FAIL. Required findings: P0=0, P1=0, P2=1.** The final retry API correction closes
ODS-RQG-02, and failed-sibling recovery remains repaired. A new independent adverse
review reproduces ODS-FQG-03: a contract-valid ownership relationship ID of `root`
collides with the explorer's client-row key. Selecting the qualifying holder displays
the client details. This fails A05/A06. The original acceptance criteria are unchanged.
No further fix, integration, commit, push, PR, merge or next phase is authorized.

Review date: 2026-10-12, Asia/Singapore. This reviewer inspected the complete tracked
diff and all task-owned new content, challenged the implementation independently, and
changed no reviewed source, test, configuration, contract or ordinary documentation.
The only durable write is this assigned report. Ignored controlled diagnostic harnesses,
synthetic API evidence and normal check outputs are outside the reviewed content.

## Reviewed identity and authority

- Worktree: `C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.ownership-hotfix`.
- Branch: `feat/ownership-ubo-doc-review-streamline`.
- BASE_SHA, HEAD and inspected `origin/main` reference:
  `a6c80d2f20048ce64b3f6184df34c098f8fff4ab`.
- Frozen scope: 24 paths, including the current planner and both retained FAIL reports.
  Manifest: `tmp/ownership-hotfix-evidence/final-remediation-manifest.json`.
- Aggregate SHA256: `874ac717f8c20f37720729110bbc16d4a4922167dad49e82221a48d6fd2ba0e2`.
- Identity algorithm: SHA256 of UTF-8 `json.dumps(entries, sort_keys=True,
  separators=(',', ':'))`, entries sorted by path and containing path/file SHA256.
  All 24 hashes and the aggregate matched before review, during review, after the full
  backend completion, and at report closeout. The report itself is excluded.

Authority read: root/backend/frontend AGENTS, repository skill routing, fyp-quality-gate
and report template, original request and superseding principal-engineering brief,
current planner including the final owner-authorized correction, both preceding FAIL
reports, development/coordination/branch workflows, architecture and project/provider
state, ownership/UBO, document intake, reconciliation and zero-touch contracts, D-062,
ADR-011 and relevant open sponsor questions. The context selector ran for FRONTEND_UI,
BACKEND_DOMAIN, BACKEND_API and conservatively FRONTEND_STATE_CACHE. Security and POC
regression checklists supplemented the combined gate.

Current capabilities used: task-bound Python 3.12.10/pytest 8.4.2, installed Node/npm,
Vitest/React, Ruff/mypy, and the configured guarded Playwright lifecycle. Python imports
were explicitly bound to this worktree, avoiding the primary checkout's editable app.
Browser runs used owned loopback ports 8886/4286 and offline controlled connectors. No
external provider mutation, dotenv inspection, protected database or credential access
was performed. Physical evidence attribution is stated below; no database was started
or touched by this final reviewer.

## Required finding

### ODS-FQG-03 [P2, OPEN] â€” valid relationship identity selects the client instead of its holder

Owner: `apps/frontend/src/pages/OwnershipStructure.tsx:18`, key construction; line51,
selected-row lookup; lines49â€“50 and56, shared selection/collapse identity.

The root row receives literal key `root`; every other occurrence receives its joined
relationship-ID path without a separate namespace. A direct relationship whose ID is
`root` therefore has the same key as the client. `SafeRelationshipId` in
`apps/backend/app/domain/ownership.py` permits this value and reserves no root sentinel.
`rows.find(row => row.key === selectedKey)` resolves the first, client row. React also
reports duplicate child keys. The resulting selected-holder panel names the company
and shows its unavailable direct/path values after the RM selects the natural person.
This is a current presentation/selection bug, not sponsor ambiguity or accepted debt.

Independent reproduction used a valid controlled provider source, rather than only the
original presentation fixture:

1. Extend the existing offline Mock provider in a reviewer-only probe and change only
   the first relationship ID to `root`.
2. Reconstruct through `OwnershipSourceResult.model_validate`, load through the existing
   ownership owner, and run the unchanged Decimal engine. Result: ANALYZED.
3. Read the real ownership API: HTTP200, `root` retained, Avery Tan 60% and Blair Lim 40%.
   Only the permitted early target Search occurs.
4. Feed that exact safe API projection into the actual `OwnershipPathExplorer` and click
   Avery Tan's existing person control.
5. The panel displays MERLION CIRCULAR LABS PTE. LTD. instead of Avery Tan. An isolated
   Vitest assertion fails and duplicate-key warnings are observed.

Evidence: `tmp/qg-final-valid-root-record.py` and `.log`; safe API projection
`apps/frontend/tmp/qg-final-valid-root-record.json`; ignored
`apps/frontend/tmp/qg-final-key-collision.probe.tsx`, `qg-final-probe.config.ts`;
`tmp/qg-final-key-collision-valid.log`. The preserved source probe independently passes
source validation/engine/API; the UI probe independently reports **1 failed**. Its
`.probe.tsx` name and explicit config keep it outside the standard test inventory.

Reproduce from the worktree with the existing Python environment:
`../.venv/Scripts/python.exe tmp/qg-final-valid-root-record.py`; then from apps/frontend:
`npm test -- --config tmp/qg-final-probe.config.ts --run`.

Recommended owning correction, for a separately authorized task only: give client,
relationship-path and unlinked occurrences disjoint stable identities, and use those
same identities for selection and collapse. Preserve backend relationship IDs. Add a
valid `root` relationship regression and challenge other sentinel-like IDs. No fix was
made or authorized during this gate. Severity is P2: retained ownership calculations,
authorization, target confirmation and no-replay remain intact, but a required RM
inspection action presents the wrong holder.

## Prior findings and final correction

- **ODS-QG-01: CLOSED on this candidate.** The current owning continuation stops at
  PENDING_INPUTS/DOCUMENT when independent FAILED current evidence remains. Confirmation
  retains receipts; replacement and version-bound dependent refresh retain retryability.
  Final sibling retry reaches the next genuine state without target writes. The narrow
  RESUMING/DOCUMENT recovery still requires the existing completed prefix and
  DOCUMENT_REUPLOAD_REQUIRED event; wrong stage/event/prefix reject.
- **ODS-RQG-02: CLOSED on this candidate.** The only main.py delta adds the existing
  ZeroTouchInfrastructureError-to-safe 503 helper in the shared retry request handler.
  The inspected failing-first HTTP log records 500 before the correction. Current tests
  verify 503, terminal TECHNICAL_FAILURE/OWNERSHIP, accepted replacement/immutable prior
  event prefix, matching safe IDs, target call stopping and rejected replay. Existing
  frontend settlement reloads four evidence resources once after 503, displays accepted
  history/current failure, removes obsolete retry input, and sends no resume/second POST.
  No frontend runtime policy was changed.
- An independent unexpected-ownership-exception probe additionally verifies sanitized
  ZERO_TOUCH_UNEXPECTED_FAILURE 503, retrievable terminal checkpoint, private exception
  text absent, accepted current lineage, subsequent retry 409 and Search-only target calls.

## Original acceptance checklist

PASS rows are bounded observations and do not override the overall FAIL.

| Criterion | Result | Direct evidence |
|---|---|---|
| A01 Garden three-level display | PASS | Fresh guarded Garden browser and inspected mobile/desktop hierarchy retain root, SIM LIM and natural persons. |
| A02 Direct/effective values | PASS | Backend Decimal strings displayed unchanged; ABCD123 81.818182% in SIM LIM / 51.13636375000000% in root; LIM 37.500000%; intermediate unknowns explicitly Not retained. |
| A03 Qualifying summary in Ownership/Final Review | PASS | Shared UboSummary and fresh Garden browser compare both views with the same authoritative analysis. |
| A04 Below-threshold/entities not promoted | PASS | Explicit natural-person/MET/provisional filter;83 affected frontend tests and Garden screenshots exclude TAN/EFGH and intermediate company. |
| A05 Accurate retained graph/path representation | FAIL | Multiple-path/cycle/unlinked/limit behavior is verified, but a valid root relationship produces duplicate occurrence identity and wrong selected details: ODS-FQG-03. |
| A06 Person controls/path inspection/keyboard/mobile | FAIL | Garden keyboard, 360px, long-name and actual 200% text checks pass; valid root-ID person selection fails in actual explorer. |
| A07 Provenance/precision after reload | PASS | Fresh browser reload retains exact values and LOCAL_SYNTHETIC_SUPPLEMENT/LOCAL distinction from Mock acquisition. |
| B01 Four fields grouped | PASS | Executed current batch tests prevalidate all groups before writes; real browser four-field rejection confirms one group action. |
| B02 One sufficient authorized continuation | PASS | Fresh owner/browser tests reach genuine blockers/readiness without extra resume; failed siblings stay PENDING with receipts. |
| B03 Required rejection remains blocked/replacement available | PASS | Four rejected fields remain DOCUMENT; actual replacement control; no target confirmation/result. |
| B04 Current replacement/history | PASS | Fresh owner/browser evidence plus unchanged physical persistence surface retain original IDs/receipts and one current lineage per replaced slot. |
| B05 One extraction/eligible continuation | PASS | Current controlled extraction-count tests; normal and recovered replacement stop at failed siblings, final successful retry advances once. |
| B06 Conflicting/low-confidence replacements | PASS | Independently executed cases extract once and retain genuine DOCUMENT review. |
| B07 Currentness/double click/auth/switch/freeze/concurrency | PASS | 57 independent backend core and 83 frontend checks cover stale/tampered groups, in-lock auth, concurrent recovery, final freeze, case-action lifetime and denied mutation. |
| B08 Mongo restart | PASS for unchanged affected persistence surface | 12 affected guarded physical cases, zero skips, independently inspected; same service/domain/batch/persistence owning bytes and retained restart/lineage/retry evidence. Final API-only projection did not change durable behavior. |
| B09 Final explicit confirmation before target writes | PASS | Independent owner/browser/probes retain absent confirmation/result and Search-only calls; existing freeze/ledger guards inspected. |
| B10 Garden PARTIAL/distinct COMPLETE source behavior | PASS for bounded offline regression | Fresh 2680 backend run and Garden browser; retained exact unchanged Garden PARTIAL and separate COMPLETE synthetic fixture evidence, not legal or target completion. |
| B11 Truthful failed/partial processing | PASS | Both prior blockers repaired; independent typed and unexpected retry 503, current terminal evidence reload/history and no blind retry. |
| B12 No UI/stale-cache false completion | PASS | Current mutations use authoritative state and scoped settlement; genuine WAITING/PENDING/technical checkpoints, explicit target confirmation and no target replay. |

## Verification ledger

### Independently executed on the frozen candidate

- Backend core: `PYTHONPATH=apps/backend`, plugin autoload disabled,
  `pytest test_ownership_document_streamline.py test_batch_review_decisions.py
  test_document_refresh_recovery.py test_final_review_editing.py
  test_phase12_persistence.py::test_multiple_interrupted_documents_require_individual_targeted_retries
  -o addopts= -q -p no:cacheprovider`: **57 passed**, 69.56s.
  Log: `tmp/qg-final-backend-core.log`.
- Frontend: OwnershipStructure, ReviewAndSend, S2OwnershipReview and Phase15CNavigation:
  **83 passed / 4 files**. The adverse 503 branch and exact call counts passed.
- Guarded actual browser/HTTP: confirmation and replacement **2 passed**, 8.7s;
  fresh Garden plus actual computed 200% font enlargement **1 passed**, 4.4s.
  Owned 8886/4286; strict offline transports/network policy. Desktop/mobile/reload,
  keyboard collapse and selected-person controls exercised; actual text is asserted
  >=1.99x with a long synthetic root name and 360px overflow check. Screenshots visually
  inspected. Logs: `tmp/qg-final-browser-documents.log`, `tmp/qg-final-browser-textscale.log`.
- Unexpected-error retry probe: PASS safe 503, terminal OWNERSHIP, no private error,
  retained lineage, replay 409, target calls only Search.
  Log: `tmp/qg-final-unexpected-retry-probe.log`.
- Valid root-ID provider/engine/API probe: PASS. Actual explorer adverse UI probe:
  **1 failed**, directly reproduces ODS-FQG-03.
- Backend configured cwd: `ruff check . --no-cache`: PASS;
  `mypy app --cache-dir ../../tmp/qg-final-mypy-cache`: PASS, 127 sources.
- `check_architecture.py`, `check_project_state.py`, supported secret scanner:
  PASS. Explicit 24-path supported secret patterns: no findings. UTF-8 and trailing
  whitespace checked for every frozen file, including untracked Markdown; tracked
  `git diff --check`: PASS. Scanner coverage is bounded, not universal secret detection.

Diagnostic attempts are kept distinct: one initial backend command named a nonexistent
extra suite and executed zero tests; default sandbox backend/browser attempts were
stopped without evidence; an initial standalone probe lacked generated test auth and
was corrected through canonical conftest isolation. An optional 141-test extended run
was stopped prematurely after buffered 51% output and is **incomplete**, neither PASS nor
a reproduced defect. A narrow existing demo-route check separately passed 5 cases.
No test assertion, timeout, skip or reviewed source was changed to obtain passing results.

### Coordinator execution, independently inspected

- Full current backend, exit0: **2680 passed, 155 skipped, 4 warnings in 1203.70s**;
  dynamic inventory 2835. Complete log: `tmp-hotfix-backend-final-round.log`;
  SHA256 `a1474072866648982ee686183af52117637651f833a9877fbe0a2bbbb5b8ac34`.
  Every skip row and warning category was inspected. 149 skips are unconfigured guarded
  physical Mongo tests; 6 skips are unavailable local Tesseract tests. Those lanes are
  unexecuted in the broad ordinary run. Four warnings are existing Starlette/httpx
  deprecation and three malformed-fixture Pydantic serialization warnings. No
  failure/error rows. This is coordinator execution, not reviewer full-suite execution.
- Full frontend: **588 passed / 51 files**, `tmp-hotfix-frontend-final-round.log`.
- Frontend typecheck/build: PASS, 138 modules; existing 605.80kB chunk warning.
- Contract unittest: **44 passed**, `tmp-hotfix-contract-suites-final-round.log`;
  validator/isolation: **31 passed**, `tmp-hotfix-contract-final-round-verified.log`.
  The earlier sandbox temporary-file PermissionError is a failed diagnostic; approved
  normal execution supplied the final pass without a code/test workaround.
- Security/governance unit checks: **45 passed**, `tmp-hotfix-governance-final-round.log`.
- Affected physical Mongo: **12 passed, 0 skipped**, 65.47s,
  `tmp-hotfix-mongo-remediation-final.log`. This belongs to the earlier aggregate
  `5b917fbf31fb4566df770f282e7125c80c8d058580815670c93d11a654ff7418` and is credited
  only to the unchanged persistence/service/domain/test surface after hash comparison;
  it is not represented as a whole-final-candidate rerun or fresh reviewer physical run.
  Only main.py's two-line retry projection and non-persistence regressions subsequently
  changed executable content. The supplied cleanup receipt records zero non-system
  databases, no host mounts, two anonymous volumes and cleanup exit0 for the exact
  task-owned container. No URI or protected database access is claimed.

The broad backend PASS and unaffected physical evidence do not waive the separately
executed UI failure. Historical PASS verdicts were not transferred to these bytes.
Remote CI, real external smoke and clean-committed pre-PR checks were not run.

## Contract, architecture and security assessment

D-062 confirms only the bounded inclusive numeric default/comparator; both UBO summaries
remain provisional. Existing legal/control, privacy/reviewer/source-authority and real
provider dependencies remain open. They are later dependencies, separate from the
current required UI fix. Official Mock identity and local synthetic percentage sources
remain distinct. Product code contains no hardcoded Garden names/values, frontend
percentage calculator, new source winner or legal-finality claim.

The existing document, reconciliation UoW, zero-touch, lock/CAS and target ledger owners
remain authoritative. Whole-group validation precedes writes; durable sections remain
monotonic/resumable rather than a new cross-document/case transaction. Current creator,
team, session, CSRF, currentness, final freeze, strict revision/identity and no-resurrection
controls remain intact. The final retry helper projects through the existing sanitized
DTO/status owner and preserves the downstream technical failure. No swallowed failure,
false continuation, target replay, private-error disclosure or new auth grant was found
in the independently exercised paths. ODS-FQG-03 changes displayed selection identity,
not the retained engine result or target authorization.

| Impact | Assessment |
|---|---|
| API/types | Existing routes/DTOs preserved; incomplete review safe error and automatic workflow state; final typed retry infrastructure error now safe 503. |
| Schema/persistence | No durable schema/repository change; existing lineage/CAS/checkpoints retained. |
| Connector/configuration/provider status | Unchanged; verification offline Mock/Local/controlled protocol only. |
| Business rule/threshold/source precedence | Ownership/threshold/approval/source rules unchanged; narrow document continuation/reupload transition behavior changed under assigned scope. |
| Mapping/target ledger | Unchanged. |
| Auth/security | Grants/owners unchanged; existing guards retained; safe error projection corrected. |
| Architecture | Existing owners/dependency direction retained; focused read-only presentation components added. |
| Runtime | Hierarchy/shared candidates and authorized document continuation changed; valid-ID holder-selection defect remains. |

Accepted limitations: bounded 200-row/32-layer explorer and 20-path summary with explicit
limits, unavailable intermediate retained values, section-level persistence, local POC
identity, no production retention/security or distributed exactly-once guarantee.
None excuses ODS-FQG-03.

## Required fixes and readiness

**Current required fix: ODS-FQG-03 only.** Both prior findings are closed on this exact
candidate. Acceptance and integration/publication readiness remain **FAIL**. The final
owner-authorized round is exhausted; stop without another correction. A future owning
correction and fresh independent gate would require separate explicit authorization.

No next phase is started or authorized. Live ACRA verification, real GoldTier
interoperability, related-party/hierarchy writes and sponsor/legal approval remain
outside this gate and are not claimed. No pre-PR or publication readiness claim follows.

## Git status and closeout

Branch/base/HEAD/inspected main are as recorded above. The worktree remains intentionally
uncommitted: 15 modified tracked paths and 9 pre-existing task-owned untracked paths;
this final report adds one untracked report. No staged changes. The reviewer preserved
all 24 frozen paths and both historical FAIL reports, wrote only this assigned durable
report plus ignored review evidence, and performed no source/test/configuration fix,
Git mutation, commit, push, PR, merge, integration or next phase.

## Complete frozen path/hash set

| Reviewed path | SHA256 |
|---|---|
| `.ai-pipeline/001_planner/OWNERSHIP_DOCUMENT_STREAMLINE_PLAN.md` | `995f54a45922c1d09aee3aa267181c311494e04a70e2b5a72c7a44440e934e6b` |
| `.ai-pipeline/reports/OWNERSHIP_DOCUMENT_STREAMLINE_QUALITY_GATE.md` | `cee0dbd346db3628cfd586534973221d7b3d992f2963042dfec7a0e53dd17d73` |
| `.ai-pipeline/reports/OWNERSHIP_DOCUMENT_STREAMLINE_REMEDIATION_QUALITY_GATE.md` | `2850afcf2e3ea0901f60af7d188802a05d254e1be03a434abec0e7a209b68e69` |
| `apps/backend/app/domain/zero_touch.py` | `05dad99a3c9567504a5786a8cc6929f94365898ae97a1014c222c202d15fe112` |
| `apps/backend/app/main.py` | `322e429aecca1562f5b2437fc3582a61d1bed96b3f7e5fd59b307c5f1548dc6f` |
| `apps/backend/app/services/zero_touch_orchestration.py` | `ed701001f784d09fb05ef14ea664159d8ee03af843f6a838a649cc8312090b29` |
| `apps/backend/tests/test_batch_review_real_mongo.py` | `f470ddd21fd2c3b1d8020e2695126cb92b19a4b8c4786095fefcb3619e8c8020` |
| `apps/backend/tests/test_ownership_document_streamline.py` | `cb3dff3a4ead053a2f15162649b24d289aff6b26e3590030f8bfac280dc4e33c` |
| `apps/backend/tests/test_phase12_persistence.py` | `e1cc2e76d8c27dd901ea481aedd7a604d12bbe7211a22a357f1da29a5d416840` |
| `apps/frontend/e2e/blocker-simulation.e2e.ts` | `fed2e207b553eca94152da439e3ed868abf9428f32d2d07fa9da0128d9e330aa` |
| `apps/frontend/e2e/ownership-document-streamline.e2e.ts` | `3127c2c9f33da9b49214c46fa7e75bd49ade16e87e1adbd077c00254b507693f` |
| `apps/frontend/src/Phase15CNavigation.test.tsx` | `cfbc8b0545441c3ca491d676f915cbbfdfd758e8fc49a60bce89cf5cf8f31c53` |
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
