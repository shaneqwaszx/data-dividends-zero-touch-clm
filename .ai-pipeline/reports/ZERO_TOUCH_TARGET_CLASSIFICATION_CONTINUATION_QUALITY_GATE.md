# Target-classification continuation — independent Quality Gate, R0

Date: 2026-10-06. Reviewer-only fresh gate under fyp-quality-gate. This report is the reviewer's sole write. The previous accepted gate supplies baseline context only; its verdict is not reused.

## Executive result and findings

**FAIL — P0/P1/P2 = 0/3/1.** Two current product P1 defects and one product P2 projection defect were independently reproduced. A separate P1 safety acceptance blocker remains because requirement T's whole-session owner-dotenv/protected-database non-access cannot be certified. Product-only finding counts are 0/2/1. A passing broad suite cannot override the independently reproduced failures.

The frozen candidate is **not eligible for the second local commit**. No PR, push, merge, Live, production, sponsor approval or next-phase readiness is asserted. At most two owner-authorized remediation rounds are available; any behavioral change requires a new manifest/freeze and fresh independent gate. Remediation cannot erase the historical safety event.

### TC-QG-001 — P1: early manual selections silently override later safe current labels

Evidence: apps/backend/app/services/onboarding.py:1178–1180 unconditionally preserves a prior USER selection during document sync; apps/backend/app/services/clm_orchestration.py:1341 checks only DOCUMENT receipts.

Independent authenticated API reproduction, using memory repositories and a recording fake XPI transport:

1. Create fresh Alpha with no document.
2. PUT target-classification with Partnership - Unregulated / DI - Government and fresh automation/case versions: HTTP200, USER source.
3. Upload Alpha's exact identity and explicit Company - Private / Corporate target profile; complete intake.
4. Both contradictory USER selections remain. Current document labels are safe, but readiness.blockers is empty and TARGET_CONFIRMATION_REQUIRED is the sole active exception. Provider history remains one GET Search and the target ledger remains empty.

This violates F's safe automatic binding/manual fallback boundary and G's reviewed fallback intent. It does not establish a universal legal-form/segment mapping or give documents silent source precedence over an explicit user decision. The safe remedy is to require review when retained selection and safely assessable current evidence disagree, through existing owners, and provide explicit compatible resolution. Add the actual pre-intake USER -> later trusted document -> blocked/no Send -> explicit resolution regression, including partial and matching prior choices.

### TC-QG-002 — P1: confirmation bypasses classification currentness before freeze

Evidence: apps/backend/app/services/clm_orchestration.py:822–853 (_start_submission) calls _evaluate_readiness without classification_current; its default is True at line1487. The normal _evaluate_current path supplies the document-currentness predicate at line1335. confirm_target_dispatch enters _start_submission directly at line521.

Independent controlled retained-evidence falsification:

1. Prepare auto-bound Alpha normally.
2. In its disposable memory repository, retain the original reviewed current document observation and add a valid contradictory same-document KYC observation, Partnership - Unregulated, with its own safe reference. This is a failure-injection probe, not a claim of ordinary UI reachability or protected-storage mutation.
3. GET summary correctly reports GOLDTIER_CLASSIFICATION_REQUIRED.
4. POST target-confirmation with the fresh summary versions returns HTTP200, COMPLETED / SUBMISSION_CONFIRMED. Recorded fake methods are GET, GET, POST, POST, GET: confirmation Search, Shell, Policy and readback execute after the stale classification blocker. Four ledger operation markers include reads; two are business mutations.

The existing stale/superseded test misses this distinction: superseding the only document also fails the ordinary document prerequisite. Classification-only contradiction leaves identity reviewed, so the omitted currentness argument is consequential. Reuse the same authoritative currentness predicate during snapshot creation and relevant dispatch validation; test both ZeroTouch and direct CLM confirmation paths, and assert zero Shell/Policy/Amend/readback on rejection. Preserve the permitted separate read-only confirmation Search and no-replay.

### TC-QG-003 — P2: stale confirmation exception projects a prepared package despite a current blocker

Evidence: apps/backend/app/api_models.py:2308 makes package_prepared true from the retained TARGET_CONFIRMATION_REQUIRED exception; line2424 then projects COMPLETE independently of current readiness.

On TC-QG-002's pre-confirmation GET:
- READINESS = REVIEW_REQUIRED; blocker GOLDTIER_CLASSIFICATION_REQUIRED.
- GOLDTIER_TARGET = COMPLETE; same blocker; safe_result Prepared target plan retained.
- FINAL_REVIEW_SEND = REVIEW_REQUIRED; blocker TARGET_CONFIRMATION_REQUIRED.
- Authoritative target state = NOT_SUBMITTED.

The current package and final-send projection must reflect current prerequisite blockers rather than a stale confirmation exception. This fails H/M and Q15/Q26. A frozen historical package after a real attempted submission remains legitimate history; that distinction must survive the repair.

### TC-QG-004 — P1 safety acceptance blocker: historical protected non-access unverified

The coordinator's candid incident record establishes that an early focused invocation encountered ambient dotenv/Garden configuration and an early standalone contract invocation selected ambient Mongo configuration and failed startup with PersistenceDataInvalidError. The reviewer did not access owner dotenv or the owner database to investigate.

Independent source inspection corroborates the consequence: persistence/composition.py:180 invokes store.initialize; mongo_case_store.py:96–120 creates indexes before decoding and can recover/replace preceding valid records before failing on a later invalid record. Therefore startup failure does not prove absence of database reads, index changes or recovery writes. The exact namespace/effects remain unknown; protected-database access or damage is neither certified absent nor asserted as a proven event.

No disclosed URI, secret, raw payload or external provider operation is established by this startup. Current guards are meaningful: ordinary pytest disables dotenv before composition; test-mode get_settings passes _env_file=None; standalone contracts reset persistence/provider settings, and the hostile-environment regression forbids MongoClient. Those controls do not retrospectively satisfy T. This is a current run-acceptance blocker, distinct from a remaining code bug, later sponsor dependency or accepted technical debt. No further protected investigation is authorized. Only the owner can decide the treatment of this disclosed historical uncertainty; this reviewer does not waive T or convert present containment into historical proof.

## Reviewed, tested and Git identity

- Worktree: C:/Users/shane/.codex-clean2/worktrees/zero-touch-registry-reuse-happy-path/data-dividends-zero-touch-clm.
- Branch: fix/zero-touch-registry-reuse-happy-path.
- Previous accepted/current HEAD: ccff7471fd23e64e87bf94a087a5540762276900.
- BASE_SHA / inspected origin/main / merge-base: 771a9696e1e31e3865da4fbbb3f9b33b5959cb6a. HEAD is one commit ahead; no remote freshness claim.
- Exactly72 reviewed paths: the appended list and ZERO_TOUCH_TARGET_CLASSIFICATION_CONTINUATION_REVIEW_MANIFEST.json.
- Raw aggregate SHA256: 995fd8affb09f9ad4f2f5bfdace68c4f697a66213121c0c403861c706c9fe4d0.
- Algorithm: lexical path order; UTF-8 concatenation of path + NUL + raw SHA256 + NUL; SHA256 of the concatenation. Raw path hashes/sizes, canonical CRLF->LF text hashes (PDFs unchanged), complete tracked/untracked set and aggregate independently match at start and end.
- Current/tested/reviewed source is HEAD plus this exact uncommitted payload. Derivative manifest, implementation report and this assigned report are excluded, not authority to alter acceptance.
- No staged path.65 tracked changed paths and7 task-owned new reviewed paths; derivative report/manifest files are additional untracked evidence. Reviewer made no implementation, test, config, ordinary-doc or Git mutation.
- git diff --check and explicit UTF-8 task-owned Markdown whitespace checks pass. An initial Markdown probe used Windows default decoding and was corrected to UTF-8; no source was changed.

## A–W acceptance

| Criterion | Result | Evidence / consequence |
|---|---|---|
| A Readiness meaning/label | PASS | Existing readiness owner retained; Submission readiness and explanatory copy; approval remains separate. |
| B Submission settings UX | PASS | Four groups, fixed DSD/ACRA/Singapore/ANZBGL, technical details retained. |
| C Existing document owner and profile | PASS | Two labelled observations, four identity keys unchanged, no second service. |
| D Bounded safe/current automatic types | FAIL | Initial bounded vocabulary/threshold works; TC-QG-002 bypasses currentness before freeze. |
| E Source/audit | PASS, bounded | DOCUMENT/USER and document/version/page/method/quality/score/value/time/policy/vocabulary retained; no automatic USER label. |
| F Auto-bind before blocker; partial safe fields | FAIL | Normal and partial paths pass; TC-QG-001 ignores later safe labels behind early USER values. |
| G Safe manual fallback | FAIL | Deterministic Alpha/Government rejected, but TC-QG-001's later mismatch gets no review. |
| H Readiness/final-review separation | FAIL | Normal ready path passes; TC-QG-003 stale package/final action contradicts current blocker. |
| I Package rename/12 nodes | PASS | GoldTier submission package;12 nodes unchanged. |
| J Classification performs no target writes | PASS | Independent manual/automatic counters and empty ledger; local refresh replaces generic advance. |
| K Uncertainty diagnosis | PASS within available evidence | Empty-intent false projection independently reproduced/fixed; actual earlier Shell/Policy uncertainty distinguished. Original owner history remains unknown. |
| L Attempt freeze | PASS | Retained ledger/snapshot confirmation guards; classification409, no replay. |
| M Authoritative uncertain/status consistency | FAIL | Real uncertain/no-send projection passes; stale pre-send package contradiction TC-QG-003 remains. |
| N Complex fixtures/Government limitation | PASS | Alpha two; Beta/Gamma six; same Decimal engine; Government no invented shares/control. |
| O Visible scan profile/fixed constants | PASS | Five fictional image-only scans; fixed values system-owned. |
| P UAT guide/Atlas name/bootstrap | PASS | Auto expectation, fallback,32-byte guarded format, refusal and separately provisioned auth prerequisites. |
| Q Q1–38 | FAIL | Per-criterion table below. |
| R Browser UAT | PASS for executed scenarios | Coordinator fresh Alpha/Partnership/Government and uncertain-Policy runs; actual OCR/HTTP/Mongo, guarded network, cleanup. Does not cover reproduced adversarial defects. |
| S Terminology | PASS | Primary RM copy changed; authority retained in details. |
| T Safety | FAIL | TC-QG-004; current isolation/zero-external evidence cannot prove whole-session protected non-access. |
| U Verification | PASS execution, defects remain | Final broad and physical evidence below; passing tests do not discharge independent counterexamples. |
| V Fresh freeze/independent gate | FAIL acceptance | Fresh review completed; required0/0/0 is unmet. No behavioral remediation during R0. |
| W Second local commit | BLOCKED | Conditional PASS authorization has not been satisfied; previous commit untouched. |

## Q1–38 checklist

Evidence: I33 = independent continuation plus hostile-isolation pytest33; I29 = independent database-first/OCR fixture pytest29; S = inspected source/contracts/decisions; B = coordinator frozen backend/frontend/physical/browser evidence; A1/A2/A3 = independent probes in findings001/002/003.

| Q | Result and direct evidence |
|---|---|
| 1 Alpha scan extracts private/Corporate | PASS — I29 actual installed OCR; profile exact. |
| 2 Zero-click auto binding | PASS normal path — I33 four fixtures, B Alpha browser classificationPUT0. |
| 3 Partnership binding | PASS — I33/I29 Gamma and B Partnership actual scan. |
| 4 Government binding where applicable | PASS — I33 actual OCR; B classification-only browser stops at unsupported ownership. |
| 5 Missing classification review | PASS — I33 missing/partial labelled fields. |
| 6 Low confidence review | PASS initial assessment — I33 low-score/identity cases; later currentness coverage insufficient under A2. |
| 7 Conflicting documents review | FAIL overall currentness — I33 initial cross-document conflict passes; A2 current contradictory retained observation still dispatches. |
| 8 Out-of-scope types not auto-bound | PASS — I33 Trust/Individual/invalid. |
| 9 Constants not document-overridden | PASS — I33 hostile fixed profile text. |
| 10 Document/version/page audit | PASS — I33 source receipts and schema validation; S bounded projection. |
| 11 Classification-ready readiness complete | FAIL overall — normal I33 passes, A1 falsely treats contradictory retained choices as current-ready. |
| 12 Confirmation alone not readiness failure | PASS — I33 normal12-node projection. |
| 13 Package prepared/complete | FAIL currentness projection — normal I33 passes; A3 Complete beside current prerequisite blocker. |
| 14 Final-review alone expected action | FAIL after stale evidence — A3 leaves confirmation action despite current classification blocker. |
| 15 No contradictory cards/pipeline | FAIL — A3 exact backend projection. |
| 16 Manual save provider0 | PASS — I33, A1 one prior Search unchanged by PUT. |
| 17 Automatic binding provider0 | PASS — I33 existing Search-only history and empty ledger. |
| 18 No mutation/readback before confirmation | PASS — I33/B; A2 defect executes only after explicit confirmation. |
| 19 No attempted pre-confirm mutation | PASS — I33/A1 empty ledger and B counts. |
| 20 Classification frozen after attempts | PASS — I33 Shell/Policy uncertainty409 and unchanged counters. |
| 21 Fresh pre-send no uncertainty | PASS — I33 normal fresh and empty NOT_STARTED intent. |
| 22 Actual Shell uncertainty operation | PASS — I33 ReadTimeout fake transport, operation-specific message. |
| 23 Actual Policy uncertainty operation | PASS — I33 fake failure, B uncertain-Policy browser. |
| 24 Uncertainty no replay | PASS — I33 repeated confirmation/classification refusal and retained counters. |
| 25 Save does not create/relabel uncertainty | PASS — I33 freeze/error chronology and empty intent. |
| 26 No stale Prepared/Blocked contradiction | FAIL — A3 same authoritative summary. |
| 27 Alpha two60/40 | PASS — I29 existing engine; S fixture. |
| 28 Beta >5 valid direct/indirect paths | PASS — I29 six outputs30/25/17/14/8.5/5.5, every parent100 Decimal. |
| 29 Gamma >5 exact100 | PASS — I29 six synthetic interests30/25/20/10/10/5. |
| 30 Inclusive>=25 and below-threshold | PASS — I29 existing candidate assertions; no comparator change. |
| 31 No second calculator | PASS — S unchanged ownership engine; fixture only supplies edges/expected outcomes. |
| 32 Government no fabricated shares | PASS — S empty graph; I33/B stops outside complete-ownership claim. |
| 33 PDFs image-only | PASS — I29 four zero-native-text scans; fifth actual Government OCR and S image generator. |
| 34 Actual Tesseract identity/classification | PASS — I29 four scans; I33 Government; B actual browser. |
| 35 Seed identity matches documents | PASS — I29 all four exact profiles and bundles. |
| 36 Fresh seeded ACRA0 | PASS — I29 NoAcra guards; B physical Alpha/Partnership counters. |
| 37 No real PII | PASS — S explicitly fictional DEMO identities/no NRIC or person registration IDs; no confidential new path. |
| 38 Seed idempotence | PASS — I29 existing-repository rerun/guards, B physical lane. |

## Tester and adversarial evidence

Reviewer runtime: Windows PowerShell, Python3.12 primary venv, explicit worktree PYTHONPATH, installed Tesseract, shell tools. Every application probe used APP_ENV=test, memory, Mock ambient modes and Garden=false; the selected sandbox-shaped test settings supplied an injected fake transport and explicit _env_file=None. No dependency installation, browser or physical Mongo process was initiated by this reviewer.

Independently executed:
- python -B -m pytest -o addopts= -p no:cacheprovider apps/backend/tests/test_target_classification_continuation.py tests/test_contract_test_isolation.py -q: **33 passed**,0 skips,15.69s. Initial attempt lacked explicit worktree PYTHONPATH and failed collection on app.domain.registry_dataset; corrected environment rerun supplies the result, not the failed attempt.
- Same cache-free pytest for apps/backend/tests/test_zero_touch_database_happy_path.py: **29 passed**,0 skips,12.19s; actual Tesseract in PATH.
- Three independent inline Python probes using authenticated current application APIs and disposable memory fixtures: reproduced001/002/003 as above. No authored regression was added.
- Raw/canonical manifest hashes, exact path-set, Git identities/index, tracked whitespace and all task-owned Markdown whitespace independently checked. All pass.

Coordinator-executed final frozen evidence, attributed rather than claimed independently rerun:
- Full backend final exit0:2556 collected = **2434 passed /122 conditional physical-Mongo skips /4 warnings**,1290.43s. Actual legacy OCR6 executed with installed Tesseract in PATH. The mandatory physical lane separately executes122/122 with0 skips; ordinary skips are not reported as physical passing evidence.
- Frontend isolated exact-lockfile dependencies:42 files/520 tests pass; TypeScript pass; production build pass128 modules. Existing >500KB chunk warning,551.15KB. npm ls --all and pip check pass. Primary dependencies untouched.
- Physical Mongo7:17 suites/122 collected/122 passed,0 failed/errors/skipped, final source validators. Newly generated guarded disposable databases only on the owned loopback service; cleanup/absence verified.
- Fresh isolated-dependency Alpha/Partnership/Government Playwright journeys pass26.3s/15.3s/7.8s; actual OCR, authorized HTTP, Alpha/Partnership actual Mongo. Pre-send SEARCH1/SHELL0/POLICY0/AMEND0/READBACK0/attempts0/PUT0. Post-send SEARCH2/SHELL1/POLICY1/AMEND0/READBACK1. Government classification stops at ownership review. Uncertain-Policy/read-only/no-replay browser also passed. Zero external/network-policy violations. Parent cleanup VERIFIED each journey.
- Windows lifecycle31/31, reserved43210/43211; unrelated8000 untouched. Tooling+hostile isolation74/74.
- Backend Ruff pass; strict mypy126 sources pass. Contracts44 plus hostile-isolation1 pass; security/governance170 pass; direct project-state/architecture/policy/provider/secret checks pass.
- Browser discovery71 tests/14 files/64 isolated lifecycles; full64-lifecycle browser suite/remote CI not asserted executed here. Relevant guarded journeys executed. Five scans were visually verified by the coordinator.
- Earlier forced Windows child shutdown leaked8 owned isolated test databases, subsequently cleaned; current parent-owned exact-name cleanup covers startup/assertion failures and safe nonzero cleanup failure. This isolated cleanup history does not prove anything about the separate ambient Mongo incident.

Current meaningful warnings: existing Starlette/httpx deprecation in independent Python suites, existing production bundle warning. Neither explains the reproduced failures. No external smoke, Production/PingFed or live interoperability test was authorized/executed.

## Contract, code, architecture and security assessment

The continuation extends LocalPdfTextIdpProvider -> DocumentProcessingService -> existing case classification binder -> CLM/ZeroTouch -> mapper/ledger. Pure selection types do not create a second service, repository, authority, calculator or raw provider-to-target path. Exact sponsor vocabulary and quarantined examples remain intact. Segment is explicit; fixture Corporate/DI - Government is not a universal mapping. Fixed values and unsupported product/account fields remain system-owned/unavailable.

Schema10 retains observations/selections inside the same case envelope. Strict schemas1..9 reject explicit later fields even null/empty, retain absent evidence as unknown and do not rewrite on read. Current validators bind source/value/score/policy and original observation/page/event evidence. Existing CAS, insert-only/update-only, immutable creator/team, no resurrection and ledger/no-replay owners remain. Old binaries cannot decode schema10; this documented compatibility boundary is not hidden fallback.

Backend actor/team capability and locked reauthorization remain authoritative. Frontend uses existing scoped session/query publication owners; no new key, retry or persistence owner. Selection provenance is safely bounded, React escapes values, original document bodies/full text/temporary paths remain transient. No target endpoints/TLS/auth family or provider classification changed. Current source isolation is strengthened, subject to historical004. No confirmed newly tracked credential, payload or real personal fixture is identified; whole-session secret/protected non-access is not certified.

Currentness is the material cross-owner flaw: a predicate is computed for ordinary reads but not all snapshot/confirmation paths, and USER receipts bypass comparison to later safe current labels. Stale exception-derived package status compounds it. These are current defects, not accepted technical debt. Large existing composition hot spots, process-local concurrency, non-calibrated OCR scores and unresolved sponsor production policies remain pre-existing bounded limitations.

Original owner UAT uncertainty cannot be assigned a definitive cause without its unavailable ledger. Controlled evidence supports the empty-intent projection defect and genuine prior Shell/Policy chronology; it does not establish classification-triggered external writes in that historical case. The current classification PUT independently makes zero provider calls/attempts.

## Required fixes and readiness

1. Remediate001's retained-user/current-document disagreement through existing review/currentness owners without inventing precedence or segment mapping.
2. Apply002's shared currentness check at confirmation/snapshot and all relevant dispatch paths; add classification-only stale/conflict adversarial regressions.
3. Correct003's current prerequisite/package/final-action projection; retain truthful frozen historical package and uncertainty/no-replay semantics.
4. Preserve004 and obtain owner treatment of the historical safety acceptance condition. Do not investigate owner dotenv/database or claim a code repair proves historical non-access.
5. Freeze the changed content, rerun affected/broad mandatory evidence and obtain a fresh independent verdict. Maximum2 behavioral remediation rounds; R0 is not an accepted baseline.

Next local second-commit readiness: **blocked**. Next phase, PR/publication, Live ACRA/GoldTier/PingFed, final legal UBO, GoldTier KYC/four-eye/Ready-for-Approval: **not established/unauthorized**. Later sponsor questions are separate from these present implementation and safety blockers.

API/types changed; durable schema9->10; local IDP connector observations changed; test/config/CI isolation changed; bounded classification/readiness behavior changed; mapping/target provider family unchanged; auth/security source validation and test containment strengthened without replacing RBAC; architecture owners unchanged; provider classifications unchanged; runtime local auto-binding/status/currentness changed with defects identified. No commit, push, PR, merge, prior-commit amendment or next phase occurred.

## Exact reviewed path set

- .ai-pipeline/001_planner/ZERO_TOUCH_TARGET_CLASSIFICATION_CONTINUATION.md
- .github/workflows/ci.yml
- apps/backend/app/api_models.py
- apps/backend/app/config.py
- apps/backend/app/connectors/idp.py
- apps/backend/app/connectors/local_pdf_idp.py
- apps/backend/app/domain/documents.py
- apps/backend/app/domain/models.py
- apps/backend/app/domain/target_classification.py
- apps/backend/app/main.py
- apps/backend/app/persistence/models.py
- apps/backend/app/persistence/mongo_case_store.py
- apps/backend/app/services/clm_orchestration.py
- apps/backend/app/services/document_processing.py
- apps/backend/app/services/onboarding.py
- apps/backend/app/services/zero_touch_orchestration.py
- apps/backend/tests/fixtures/uat/zero-touch-database/demo-alpha-scanned.pdf
- apps/backend/tests/fixtures/uat/zero-touch-database/demo-beta-scanned.pdf
- apps/backend/tests/fixtures/uat/zero-touch-database/demo-delta-scanned.pdf
- apps/backend/tests/fixtures/uat/zero-touch-database/demo-gamma-scanned.pdf
- apps/backend/tests/fixtures/uat/zero-touch-database/demo-government-scanned.pdf
- apps/backend/tests/phase13_test_settings.py
- apps/backend/tests/s2_legacy_schema_fixtures.py
- apps/backend/tests/test_manual_ownership_evidence.py
- apps/backend/tests/test_phase12_persistence.py
- apps/backend/tests/test_phase12_real_mongo.py
- apps/backend/tests/test_phase13_priority.py
- apps/backend/tests/test_phase13_real_mongo.py
- apps/backend/tests/test_phase14_5_real_mongo.py
- apps/backend/tests/test_phase24c_real_mongo.py
- apps/backend/tests/test_s1_pipeline_projection.py
- apps/backend/tests/test_s2_intelligence_real_mongo.py
- apps/backend/tests/test_s2_persistence_security.py
- apps/backend/tests/test_slice_a_legacy_compatibility.py
- apps/backend/tests/test_slice_c_real_mongo.py
- apps/backend/tests/test_target_classification_continuation.py
- apps/backend/tests/test_zero_touch_database_happy_path.py
- apps/backend/tests/test_zero_touch_orchestration.py
- apps/frontend/e2e/authenticated-zero-touch.e2e.ts
- apps/frontend/e2e/database-classification.e2e.ts
- apps/frontend/e2e/garden-happy-path.e2e.ts
- apps/frontend/e2e/s1-workspace-session.e2e.ts
- apps/frontend/e2e/s2-ownership.e2e.ts
- apps/frontend/e2e/s3-sandbox-submission.e2e.ts
- apps/frontend/e2e/slice-b-registry-demo.e2e.ts
- apps/frontend/e2e/slice-c-recovery.e2e.ts
- apps/frontend/e2e/zero-touch-exception.e2e.ts
- apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx
- apps/frontend/src/pages/CaseDetail.tsx
- apps/frontend/src/pages/PolicyRebindPanel.test.tsx
- apps/frontend/src/pages/PolicyRebindPanel.tsx
- apps/frontend/src/pages/TargetClassificationPanel.test.tsx
- apps/frontend/src/pages/TargetClassificationPanel.tsx
- apps/frontend/src/types.ts
- docs/ARCHITECTURE.md
- docs/contracts/CLM_READINESS_POLICY.md
- docs/contracts/IDP_FIELD_PROFILE.md
- docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md
- docs/decisions/DECISION_LOG.md
- docs/demo/ZERO_TOUCH_DATABASE_HAPPY_PATH_UAT.md
- docs/PROJECT_STATE.md
- scripts/e2e_backend_server.py
- scripts/generate_zero_touch_happy_path_documents.py
- scripts/run_e2e.py
- scripts/s3_sandbox_fixture.py
- scripts/seed_zero_touch_happy_path_companies.py
- scripts/zero_touch_classification_browser_fixture.py
- scripts/zero_touch_happy_path_fixtures.py
- tests/contract/phase13_contract_credentials.py
- tests/test_contract_test_isolation.py
- tests/test_demo_lifecycle_windows.py
- tests/test_run_e2e.py
