# Ownership intelligence and document review lifecycle — independent quality gate

## Executive result

**FAIL. P0=0, P1=1, P2=0 required code findings.** The new pending-document replacement path can terminalize an unrelated failed current document and remove its authorized targeted retry. This fails B11 and the planner's failed-sibling preservation requirement. No publication or completion claim follows. The full affected backend regression was still running at report time; that lane is not reported as passing.

Review date: 2026-10-12, Asia/Singapore. This was a fresh independent review of the bounded superseding principal-engineering assignment and both implementation slices. The reviewer changed no implementation, test, contract, configuration, or Git state. The only durable write is this report. Ignored task-owned evidence probes and normal check output are verification artefacts.

### ODS-QG-01 [P1, OPEN] — successful pending replacement disables failed-sibling recovery

Affected owner: `apps/backend/app/services/zero_touch_orchestration.py`, pending eligibility at lines956–961 and unconditional replacement advancement at lines1066–1067; the existing DOCUMENT progression branch terminalizes a retained failed current document.

Independent reproduction uses real service owners with offline in-memory synthetic documents:

1. Create a pending review document, then intake a separate document whose controlled IDP processor fails.
2. Both records remain current; automation is `PENDING_INPUTS / DOCUMENT`.
3. Replace the review document with sufficient clean evidence through the newly permitted pending replacement path.
4. Automation becomes `TECHNICAL_FAILURE / DOCUMENT` because the unrelated current failed sibling is encountered by `_advance_locked`.
5. Targeted retry of that sibling rejects with `ZERO_TOUCH_INTAKE_NOT_OPEN`. The failed current record still exists, but the owning retry action is unavailable.

Observed target calls remain `['search']`; there is no false completion or target mutation. The defect is loss of recoverability after an otherwise valid active-slot replacement. It violates B11's truthful failed/partial processing behavior, the Slice B requirement to present the next legitimate blocker/action, and the planner's explicit failed-sibling preservation risk.

Evidence: `tmp/qg-failed-sibling-probe.py` and `tmp/qg-failed-sibling-probe.log`. Safe observed sequence is `IDP_PROCESSING_FAILED -> PENDING_INPUTS/DOCUMENT -> TECHNICAL_FAILURE/DOCUMENT -> ZERO_TOUCH_INTAKE_NOT_OPEN`. The probe imports the current test environment and runs the current ownership hotfix services; it does not use an external provider or alter source.

Required fix: after a successful replacement, preserve the failed-sibling targeted-intake checkpoint under the existing owning lock/CAS and document owners instead of advancing across current failed siblings. Add a regression for a pending review document plus an independent failed current sibling, successful replacement, still-available sibling retry, and continuation only after every failed sibling is replaced. Preserve lineage, receipts, final target confirmation, and no-replay behavior. Remediation belongs to a separate authorized implementation run and requires a new content identity and independent gate.

## Reviewed identity and authority

- Worktree: `C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.ownership-hotfix`.
- Branch: `feat/ownership-ubo-doc-review-streamline`.
- BASE_SHA, HEAD, and inspected fetched `origin/main`: `a6c80d2f20048ce64b3f6184df34c098f8fff4ab`.
- Reviewed scope: all staged/unstaged tracked changes and all seven declared task-owned new paths; 19 frozen paths total. No staged changes.
- Frozen aggregate: `cdb3da8207b016f6546114b50c7c8ccc490ef6530bc7d58bd47114936c5dc727`.
- Algorithm: SHA256 of UTF-8 `json.dumps(entries, sort_keys=True, separators=(',', ':'))`, with entries sorted by path and each entry containing `path` and its file SHA256. Every file hash and the aggregate matched before review and after checks. The gate report and ignored verification artefacts are outside that implementation identity.

Authority inspected: root/backend/frontend AGENTS, repository skill routing and quality-gate template, development and coordination workflows, the active ownership/document planner, current architecture/state, ownership/UBO, multi-document, reconciliation, zero-touch and persistence contracts, D-062, ADR-011, relevant open sponsor questions, owning services/API/view/cache behavior, changed tests, and the relevant preceding sponsor-demo gate. The Aegis code-reviewer checklist supplements review; the repository quality gate owns this verdict. Historical results were not transferred to this candidate.

D-062 establishes the bounded inclusive numeric comparator separately from unresolved legal/control UBO policy. The user requested provisional candidate presentation; no legal finality is inferred. ADR-011 retains existing section checkpoints and the reconciliation UoW, rather than a new cross-document/case transaction. The hotfix documents this limitation truthfully.

### Complete frozen path/hash set

| Reviewed path | SHA256 |
|---|---|
| `.ai-pipeline/001_planner/OWNERSHIP_DOCUMENT_STREAMLINE_PLAN.md` | `ddc44a6c829cabb37be055883d2a1843b26bac46e3877726eb1ce59d708b77bc` |
| `apps/backend/app/services/zero_touch_orchestration.py` | `66237a7e7f4603cb6f7d79c4bbaea5da04f7d85215953c1fd6895821cce26fcc` |
| `apps/backend/tests/test_batch_review_real_mongo.py` | `e4a6aab97658b5e3a186383d7af2cba35c490a3f3ea16e6f3ff84f1dd5df433e` |
| `apps/backend/tests/test_ownership_document_streamline.py` | `d16ae8a1862f69b0315963d3526d71e49dd17c7e39d6781eb7eb1459c185af8c` |
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
| `docs/PROJECT_STATE.md` | `8c9f7308ce866d2b16915748c49a92cb9b9b4618ab9972565bf02b190dc114a5` |
| `docs/contracts/MULTI_DOCUMENT_INTAKE_PROFILE.md` | `278f941a9c1246d9689fe80469839372db2c2e167549f696d406f8daa89f4853` |

## Acceptance checklist

PASS rows below identify verified bounded behavior; they do not override the overall FAIL or the pending full backend lane.

| Criterion | Result | Current-content evidence |
|---|---|---|
| A01 Garden three levels | PASS | Actual Garden browser and inspected desktop/mobile screenshots show root, SIM LIM, natural persons; expandable holders. |
| A02 Direct/effective accuracy | PASS | Retained Decimal strings and path calculations only; ABCD123 direct 81.818182% in SIM LIM/effective 51.13636375000000%; LIM 37.500000%; unknown intermediate effective values explicitly Not retained. |
| A03 Explicit qualifying summary in both stages | PASS | Same `UboSummary` owner; actual Garden browser verifies Ownership/Final Review agreement for one analysis. |
| A04 No below-threshold/entity promotion | PASS | Backend MET plus provisional classification and natural-person filtering; focused component tests and Garden screenshot exclude TAN/EFGH and intermediate SIM LIM from qualifying list. |
| A05 Multiple paths/incomplete/unsupported truth | PASS | Repeated occurrences retained by relationship sequence; cycle traversal stops, unlinked/limited labels, review banner; technical retained diagnostics/relationships remain available. Focused cycle/multipath tests executed. |
| A06 Selection, keyboard/mobile/text resizing | PASS | Chips and native collapse selection in actual browser; 360px/desktop screenshots. Independent actual200% computed-text enlargement with long synthetic root name wraps and retains keyboard control. |
| A07 Provenance/precision after reload | PASS | Actual Garden browser reload and shared summary preserve exact strings, MOCK analysis and LOCAL_SYNTHETIC_SUPPLEMENT/LOCAL percentage sources. |
| B01 Four decisions grouped | PASS | Current batch suites plus physical four-field reject/replace and two-field-document failure checks; prevalidation before section writes. |
| B02 Sufficient decisions automatically continue | PASS for no failed sibling | Independent browser/HTTP tests reach next real source blocker/readiness without a resume POST. Failed sibling edge is ODS-QG-01's related continuation risk. |
| B03 Reject required fields truthfully | PASS | Four-field browser rejection stays DOCUMENT, replacement action available, target result/confirmation absent. |
| B04 Current replacement/history | PASS | Browser history and physical Mongo retain original decisions/IDs and exactly one active lineage. |
| B05 Extraction and eligible continuation | PASS for no failed sibling | Focused owner tests and browser reach READINESS; controlled replacement extraction counted once. ODS-QG-01 blocks safe generalization to failed siblings. |
| B06 New low/conflicting evidence | PASS | Executed controlled replacement tests extract once, remain DOCUMENT review and retain current replacement. |
| B07 Currentness/concurrency/auth/freeze | PASS for tested paths | Independent batch tests reject stale/tampered/concurrent groups and denied actors; existing Final Review/freeze/source-owner checks inspected; frontend action identity and centralized refresh reused. |
| B08 Mongo restart | PASS | Independent guarded physical7/7 includes new pending rejection/replacement restart; supplied affected physical11/11 adds Garden and Final Review persistence. |
| B09 Explicit final target confirmation | PASS | Browser/owner receipts retain null confirmation/result; only search before approval; current ledger/lock freeze paths unchanged. |
| B10 Garden PARTIAL/distinct COMPLETE fixture | PASS for focused evidence | Supplied focused affected suites and physical Garden preserve PARTIAL; actual distinct synthetic COMPLETE source browser retains Avery60.0/Blair40.0. This is source completeness, not implicit final approval. |
| B11 Truthful failed/partial processing and action | **FAIL** | ODS-QG-01 removes targeted retry after clean replacement beside a failed sibling. Ordinary failed-replacement checkpoint remains truthful in other executed tests. |
| B12 No UI/stale-cache false completion | PASS for tested paths | Confirm/replacement stay WAITING/READINESS or genuine DOCUMENT blockers, no target confirmation/result; source uses authoritative summary/current-case settlement. Full backend is pending. |

## Verification and adversarial evidence

Reviewer-executed against frozen content:

- Backend: `PYTHONPATH=apps/backend`, plugin autoload disabled, `python -m pytest apps/backend/tests/test_ownership_document_streamline.py apps/backend/tests/test_batch_review_decisions.py -o addopts= -q -p no:cacheprovider`: **31 passed**, one existing Starlette/httpx deprecation warning, 32.53s. `app.__file__` independently bound to this worktree, avoiding the reused editable environment's primary checkout.
- Frontend: three affected OwnershipStructure/ReviewAndSend/S2 suites: **41 passed in 3 files**.
- `scripts/run_e2e.py`, owned8878/4278: Garden focused journey **1 passed in 4.6s**; confirmation/replacement **2 passed in 8.6s**. Existing network policy permits owned loopback only, and no external mutation occurs.
- Actual text resizing: ignored `tmp/qg-textscale-probe.py`, config and copied browser evidence helper use the same owned runner/network policy. Every computed font size in hierarchy/detail/current UBO summary is doubled and asserted at least 1.99x; a long synthetic entity name is substituted; 360px overflow and native focus/collapse checked. **1 passed in 4.9s**. Screenshot copied to stable `tmp/ownership-hotfix-evidence/qg-actual-200-text.png`. This closes the earlier root-font-only evidence gap; it does not claim every OS/browser accessibility setting was tested.
- Physical: current `test_batch_review_real_mongo.py` through `_child_environment` and guarded generated databases on the task-owned Mongo7 container: **7 passed, 0 failed, 0 errors, 0 skipped**. No URI printed; no protected database used.
- Configured backend cwd: `ruff check app tests`: **PASS**; `mypy app --cache-dir ../../tmp/qg-mypy-cache`: **PASS, 127 sources**.
- Frontend `npm run typecheck` and `npm run build`: **PASS**, 138 modules; existing 605.80kB minified chunk warning.
- Architecture/project-state governance: **PASS**. Per-file UTF-8/whitespace/hash inspection and tracked `git diff --check`: **PASS**. Supported secret patterns on all 19 declared paths: **no findings**. Stable 22-file evidence manifest matched when inspected.
- Failed-sibling adversarial probe: **reproduced ODS-QG-01**, as described above. This is a current behavior defect, not missing infrastructure.

Supplied implementer evidence inspected for this candidate:

- Focused backend affected suites 117 passed; full frontend 587 passed / 51 files (`tmp-hotfix-frontend-final.log`); contracts 44 passed (`tmp-hotfix-contract-final.log`).
- Affected physical Mongo 11 passed / 0 skipped (`tmp-hotfix-mongo-final.log`); confirmation/replacement 2 passed and Garden 1 passed current-content logs; existing failed-intake/dependent-refresh 2 passed and Garden PARTIAL correction offline browser evidence.
- Final full backend `tmp-hotfix-backend-final.log` was still running, last observed 66%; no final collected/passed/skipped counts were available. **PENDING, not PASS.** This blocks full regression completion independently of the reproduced defect.
- Initial root-cwd Ruff/mypy logs are failed diagnostic invocations, not the final configured pass. A prior backend run had an obsolete PENDING assertion; the frozen test now requires automatic continuation and verifies explicit confirmation remains absent. Only executed fresh evidence is credited.

Default sandbox backend/browser attempts could not start normally and were cancelled; approved local process runs supplied actual evidence. Early ignored text-probe ESM packaging failures were corrected only in the evidence helper. These failures do not change the product verdict. Remote CI and clean-committed pre-PR checks were not executed; the candidate is intentionally uncommitted and publication remains reserved.

## Contract, code, architecture and security assessment

The full affected diff and all new files were inspected. The read-only hierarchy arranges retained relationships without frontend percentage arithmetic, inferred percentages, new source precedence, or legal UBO claims. It preserves repeated paths and bounds traversal. Summary filtering is shared between Ownership and Final Review. The current Garden receipt identifies ABCD123 51.13636375000000% and LIM CHOON HUAT 37.500000%, both MET at 25.000000; percentage sources remain LOCAL, distinct from official Marketplace Mock identity evidence.

Backend changes remain inside ZeroTouchOrchestrator and reuse document/reconciliation/CLM owners. Whole-group currentness and required-decision validation happen under the existing case lock before first receipt. Existing section checkpoint recovery, creator/team/CSRF/in-lock reauthorization, strict CAS, historical receipts/lineage, target-freeze and ledger ordering/no-replay are retained. The found defect is a missing failed-sibling stop in this newly admitted pending replacement route, rather than a new architecture owner.

No API DTO/type, durable schema, connector, runtime configuration, provider classification, target mapping, threshold/comparator, source-precedence rule or auth grant changes. API behavior changes: incomplete grouped decisions get safe `ZERO_TOUCH_REVIEW_INCOMPLETE`, and successful eligible document actions advance their returned stage. Architecture owner/dependency direction remains unchanged; presentation components are added. Runtime/UI changes are the hierarchy/shared summary and document continuation. No secret, raw provider body, uploaded bytes, or confidential sponsor artefact is newly introduced by the 19-path candidate. Scanner coverage is pattern-based; source inspection complements it.

No current contract/security defect besides ODS-QG-01 was found. Existing single-process lock/CAS/section durability limits remain explicit. Broader legal/control UBO policy, production reviewer/retention policy, Live ACRA, real GoldTier interoperability, related-party hierarchy/file transfer and production identity remain later sponsor dependencies; this task neither implements nor proves them.

## Required fixes and readiness

ODS-QG-01 requires bounded remediation and a fresh independent gate on changed content. The full affected backend regression must also finish with accurate failures/skips/counts before any final completion claim. No implementation fix was made by this reviewer.

This candidate is **not ready for acceptance or publication**. No next phase is authorized. Passing unrelated lanes does not waive failed-sibling recovery or the pending full backend lane. After remediation, freeze the new full path set, rerun affected verification and obtain exact independent PASS. Commit/push/PR still require separate owner authorization and the documented integration/pre-PR workflow. Human owners merge.

## Git and write-boundary statement

At review start/end, HEAD/base/inspected origin/main are the SHA above, with 12 tracked modifications and 7 task-owned new implementation/planner paths, no staged content. This report is the sole durable reviewer addition. Per-file 19 path hashes and aggregate were checked again at closeout; implementation bytes are unchanged. The reviewer did not stage, commit, push, create a PR, merge, switch/remove worktrees, edit implementation/tests/contracts, or begin another phase. Ignored tasktmp probes/logs, normal caches/build output and browser evidence are verification output only.
