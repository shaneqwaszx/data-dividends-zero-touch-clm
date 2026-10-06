# Target-classification continuation — independent R1 Quality Gate

Date: 2026-10-06. Fresh reviewer-only run under `fyp-quality-gate`, including contract, architecture, testing, security and adversarial assessment. Only this assigned report was written; reviewed source, tests, configuration, ordinary documentation and Git were not changed.

## Executive result

**FAIL — P0/P1/P2 = 0/2/0.** R1 repairs the three R0 product counterexamples in the Sandbox lane, but the shared readiness predicate still ignores retained-selection currentness in Mock mode. Independent DOCUMENT and USER examples show false readiness, confirmation/snapshot creation and a frozen pre-send technical failure. The later NOT_STARTED guard prevents mutation; it does not repair the false readiness or prevent the invalid freeze.

A separate P1 acceptance blocker remains: requirement T's whole-session owner-dotenv/protected-database non-access cannot be certified after the disclosed earlier ambient configuration/Mongo startup incident. Current isolation guards are meaningful and independently pass, but cannot establish historical non-access. This report does not waive the owner's requirement or assert that the protected database was definitely accessed.

The conditional second local commit is **not eligible**. No push, PR, merge, previous-commit amendment, Live claim or next phase is authorized. R1 is the first behavioral remediation round; a further behavioral change requires a new freeze and independent review within the owner's maximum of two rounds.

## Current, tested and reviewed identity

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/zero-touch-registry-reuse-happy-path/data-dividends-zero-touch-clm`.
- Branch: `fix/zero-touch-registry-reuse-happy-path`.
- HEAD / previous accepted local commit: `ccff7471fd23e64e87bf94a087a5540762276900`.
- BASE_SHA / inspected local origin/main / merge base: `771a9696e1e31e3865da4fbbb3f9b33b5959cb6a`.
- Reviewed source: HEAD plus exactly the 72 paths in `ZERO_TOUCH_TARGET_CLASSIFICATION_CONTINUATION_REVIEW_MANIFEST_R1.json`.
- Raw aggregate SHA256: `ff5d98a940ffce87942d41f09b82c552c7f50cd641ce9dea7758b55422b5e9b2`.
- Formula: lexically sorted UTF-8 `path + NUL + raw_sha256 + NUL`, then SHA256. All 72 raw/canonical hashes and sizes were independently checked at start and completion. Canonical text converts CRLF to LF; PDFs remain raw binary. The exact modified/new inventory matches the manifest, with no unexpected path.
- Canonical R0-to-R1 changes are only the planner, api_models.py, clm_orchestration.py, continuation tests, CLM_READINESS_POLICY.md, DECISION_LOG.md and UAT guide. The cumulative 72-path continuation remains the scope of this review.
- Implementation handoff, R0/R1 reports and review manifests are excluded derivative evidence, not source. Evidence updates cannot alter acceptance. R0's verdict is historical evidence and is not reused as this verdict.
- Git index is empty. There are 65 tracked modified paths and seven new reviewed paths, plus excluded reports/manifests. Current behavior was exercised on this uncommitted frozen content, not on a future commit. No latest-main fetch or publication gate was required or performed for this deliberately uncommitted implementation review.

## Findings and remediation status

### TC-R1-001 — P1: retained classification currentness is ignored in Mock readiness and snapshot creation

Evidence: `apps/backend/app/services/clm_orchestration.py:1585` combines `not classification_current` with Sandbox-only `require_target_classification`. Both ordinary evaluation and snapshot start pass the currentness predicate, but Mock mode makes that predicate ineffective. `_start_submission` then builds and persists the snapshot at lines876–885. The later NOT_STARTED guard at lines604–616 checks `_submission_snapshot_is_current` in all modes and stops execution only after the invalid confirmation and snapshot exist.

Independent reproduction used the existing authenticated application, seeded fictional Alpha, disposable memory repositories, explicitly configured Mock mode and no external transport. Two cases were executed:

1. DOCUMENT: complete intake with current private/Corporate labels, retain the automatic receipts, then add a valid-shaped contradictory retained Government observation.
2. USER: choose Partnership - Unregulated / DI - Government before document intake, then upload and complete the trusted Alpha private/Corporate document. This case uses the ordinary public API sequence; no source/evidence mutation is needed.

In both cases GET returns readiness blockers `[]`, Submission readiness `COMPLETE / Ready for target submission`, package `COMPLETE / Prepared target plan retained`, and final review `REVIEW_REQUIRED`. POST target-confirmation returns200 and persists both submission_snapshot and target_dispatch_confirmation. The execution ledger stays empty. Subsequent classification save returns409/frozen. The DOCUMENT post-confirmation summary is `TECHNICAL_FAILURE / MOCK_GOLDTIER`, CLM `SUBMITTING`, target `NOT_SUBMITTED`, classification noneditable, readiness/package still Complete/Prepared, final review Failed. Thus the final dispatch guard contains writes but leaves false readiness, a frozen unsent package and no ordinary classification correction path.

Violates currentness before freezing, truthful pre-send readiness/status, conflict review, and requirements D/F/G/H/M/T plus Q7/Q11/Q13–15/Q26. This is an incomplete repair of the underlying R0 currentness problem, not accepted debt or a new sponsor dependency.

Additional independent Mock intake probes reproduce the same underlying provider-mode gate for partial explicit evidence: a private-type-only document retains that automatic value with segment unresolved, but readiness blockers remain empty; an Alpha document explicitly labelled Government/Corporate loses the incompatible automatic KYC value while retaining Corporate, yet is also ready with no blocker. Both have current observations and one retained selection. A no-label/no-selection legacy Mock control remains ready. These are F/G partial-safe/manual-review failures under the same finding, not separate severity counts.

Required repair: separate mandatory presence from currentness using the same CLM owner. Present retained selections must be current in all modes; explicit current classification observations or retained selections require complete safe classification inputs or manual review. Legacy Mock cases with neither observations nor selections may retain accepted optional-classification compatibility. This bounded distinction follows the human F/G criteria; it does not mandate classification for every legacy Mock case, infer a segment/legal rule or switch providers. Preserve legacy Mock cases without selection evidence. Add both DOCUMENT and USER Mock adverse regressions requiring review before confirmation, Send refusal, no snapshot/confirmation/ledger/mutation, and compatible explicit resolution where allowed. Do not weaken the NOT_STARTED/no-replay guard or invent document/user precedence.

### TC-R1-002 — P1 acceptance blocker: whole-session requirement-T safety remains unverified

The disclosed early focused invocation encountered ambient dotenv/Garden configuration; a separate early standalone contract invocation used ambient Mongo settings and failed startup with PersistenceDataInvalidError. Source inspection independently confirms `MongoCaseStore.initialize` at lines96–120 pings and creates indexes before decoding all records, and may recover/replace earlier valid records before a later invalid record fails. Startup failure therefore cannot prove no connection or no side effect.

The exact ambient namespace and effects remain unknown. The reviewer did not read owner dotenv, resolve ambient credentials/URI, connect to an owner database, or investigate/clean clm_poc. No URI, secret, raw provider body or private exception material is included here. Available evidence supports no ACRA/GoldTier execution from that startup; it cannot certify whole-session protected non-access or absence of database changes.

Current containment is verified: ordinary pytest disables dotenv, test-mode get_settings supplies `_env_file=None`, standalone contracts establish memory/Mock before app import, and the independently executed hostile subprocess forbids MongoClient construction. These controls prevent recurrence within their exercised paths. They cannot retroactively satisfy the historical requirement. Under unchanged acceptance this remains FAIL. Only the owner can decide how to treat the incident/acceptance consequence; no reviewer or source fix may silently waive it. Any investigation needs separate explicit authority and must not be inferred from this report.

### R0 product remediation verified within Sandbox

- Early USER disagreement with a safe later current document now produces GOLDTIER_CLASSIFICATION_REQUIRED; matching choices and compatible explicit resolution remain auditable/local.
- Contradictory retained DOCUMENT evidence now blocks Sandbox confirmation409 before snapshot, confirmation or ledger creation.
- The retained NOT_STARTED snapshot predicate becomes false when classification evidence changes.
- Current Sandbox blockers now prevent current Prepared copy and make final review Blocked; actual attempted/frozen packages remain historical and operation outcomes remain authoritative.

These are directly executed R1 results, not a blanket assertion that all modes are repaired. TC-R1-001 identifies the residual mode distinction. No other P0/P1/P2 product finding was established in this review.

## A–W acceptance checklist

Evidence labels: I66 = independent 66-test continuation/database-fixture run; A6 = independent six Sandbox adversarial assertions; M2 = independent two Mock retained-selection counterexamples; M3 = independent partial/incompatible explicit Mock evidence and legacy no-label control; H1 = independent hostile subprocess; S = source/contracts/decisions/diff review; B = coordinator execution on frozen R1; U = byte-unchanged surface evidence from the disclosed R0 runs.

| Requirement | Result and direct evidence |
|---|---|
| A Readiness meaning/label | PASS semantics/copy; S/I66. Mock currentness correctness remains TC-R1-001. |
| B Submission settings/groups/constants | PASS; S, U frontend and B browser. Technical authority is retained in details. |
| C Existing document owner/profile | PASS; S/I66. Two labelled observations; four identity fields unchanged. |
| D Three bounded automatic types/currentness | FAIL overall; initial safe assessment I66/A6 passes, M2 violates currentness before freeze. |
| E Separate source/audit | PASS; I66/S. DOCUMENT and USER evidence, original metadata and policy/vocabulary bindings retained. |
| F Automatic/partial binding; conflict review | FAIL overall; normal/partial Sandbox I66 passes, Mock prior USER conflict M2 does not require review. |
| G Safe manual fallback | FAIL overall; private/Government rejection I66 passes, Mock stale choices M2 falsely remain valid/freeze. |
| H Readiness/package/final-action consistency | FAIL overall; I66/A6 repaired Sandbox, M2 false-ready/frozen technical failure. |
| I Package label and12 nodes | PASS; I66/B. |
| J Classification writes/attempts0 | PASS; I66/A6/S. Classification refresh is local, never target dispatch. |
| K Uncertainty diagnosis | PASS within available evidence; I66 actual Shell/Policy and empty-intent cases. Original owner ledger chronology remains unknown. |
| L Retained attempt freeze/no replay | PASS; I66/S. Actual uncertainty edits/repeated confirmation refused. |
| M Authoritative target-state consistency | FAIL overall; real uncertainty I66/B passes, M2 stale prepared pre-send state fails. |
| N Alpha/Beta/Gamma/Delta/Government | PASS; I66/S. Government remains classification-only with no fabricated share/control rule. |
| O Image-only visible profile/constants | PASS; I66 and independent five-PDF native-text/visual inspection. |
| P UAT guide/Atlas/bootstrap | PASS; S/I66.32-byte guarded name; bootstrap prerequisites contain no credentials. |
| Q Q1–38 | FAIL overall; detailed table below. |
| R Guarded browser journeys | PASS for required executed scenarios; B four fresh R1 actual-HTTP journeys. |
| S Primary RM terminology | PASS; S/U/B. |
| T Safety/currentness | FAIL; TC-R1-001 currentness and TC-R1-002 historical non-access. No external call/Production/PingFed/provider-family change is claimed. |
| U Required verification | PASS execution; B exhaustive backend/affected physical/browser and other lanes below. Tests do not erase independent defects. |
| V Fresh exact independent gate0/0/0 | FAIL acceptance; this fresh R1 review yields0/2/0. |
| W Second local commit | BLOCKED; exact PASS condition unmet. |

## Q1–38 checklist

| Q | Result and evidence |
|---|---|
| 1 Alpha exact private/Corporate extraction | PASS I66 actual OCR. |
| 2 Zero-click binding | PASS I66/B; browser classification PUT0. |
| 3 Partnership binding | PASS I66/B actual Gamma scan. |
| 4 Government classification where applicable | PASS I66/B; unsupported ownership is explicit. |
| 5 Missing labels review | FAIL for partial explicit Mock evidence M3; Sandbox I66 partial/missing tests pass. Legacy no-label Mock compatibility remains distinct. |
| 6 Low score review | PASS Sandbox I66/A6; retained Mock currentness remains TC-R1-001. |
| 7 Conflicting evidence review | FAIL overall M2; Sandbox I66/A6 passes. |
| 8 Out-of-scope types not automatic | PASS I66 Trust/Individual/invalid. |
| 9 System constants protected | PASS I66 hostile document fixed values. |
| 10 Document/version/page audit | PASS I66/S and strict binding validators. |
| 11 Classification-ready readiness COMPLETE | FAIL overall M2 false-ready; normal I66/B passes. |
| 12 Confirmation alone not readiness failure | PASS I66/B. |
| 13 Prepared current package | FAIL overall M2 stale prepared state; Sandbox A6 repaired. |
| 14 Final review alone expected ready action | FAIL overall M2 invalid pre-send freeze; normal I66/B passes. |
| 15 No contradictory statuses | FAIL M2 ready/Prepared plus unsent technical failure. |
| 16 Manual save provider0 | PASS I66/A6; target histories unchanged by PUT. |
| 17 Automatic binding provider0 | PASS I66/B; existing independent initial Search only. |
| 18 No pre-confirm Shell/Policy/Amend/readback | PASS I66/B/M2; no mutation even in reproduced Mock failure. |
| 19 No pre-confirm attempted ledger operation | PASS I66/B/M2. |
| 20 Classification freeze after attempts | PASS I66 actual uncertain Shell/Policy409. |
| 21 Fresh pre-send no false uncertainty | PASS I66 empty NOT_STARTED/fresh cases. |
| 22 Actual Shell uncertainty chronology | PASS I66 injected timeout and operation-specific message. |
| 23 Actual Policy uncertainty chronology | PASS I66/B browser. |
| 24 No uncertainty replay | PASS I66/B unchanged counters/refusals. |
| 25 Save cannot create/relabel uncertainty | PASS I66/S. |
| 26 Stale package/current state consistency | FAIL overall M2; Sandbox A6 passes. |
| 27 Alpha two people60/40 | PASS I66/S. |
| 28 Beta >5 direct/indirect people | PASS I66/S:30/25/17/14/8.5/5.5, every parent100 Decimal. |
| 29 Gamma six interests100 total | PASS I66/S:30/25/20/10/10/5. |
| 30 >=25 boundary/below-threshold results | PASS I66; existing inclusive engine. |
| 31 No second ownership calculator | PASS S; fixture inputs only. |
| 32 Government no invented shares/control | PASS S/I66/B; separate empty graph. |
| 33 PDFs image-only | PASS independent allfive one-page/native-text-empty checks. |
| 34 Actual Tesseract identity/classification | PASS I66 five fixtures; B browser actual scans. |
| 35 Seed/document identity matches | PASS I66 allfour bundles/profiles. |
| 36 Fresh seed ACRA0 | PASS I66/B physical browser counters/NoAcra. |
| 37 No real fixture PII | PASS S/visual review; fictional DEMO names/no person identifiers. Historical protected non-access is separately unverified. |
| 38 Seed idempotence | PASS I66/B physical evidence. |

## Tester and adversarial evidence

### Independently executed on frozen R1

- Python3.12 primary venv; explicit APP_ENV=test, memory, Mock ambient modes, Gardenfalse, worktree PYTHONPATH and installed Tesseract PATH for all application probes. PYTHONDONTWRITEBYTECODE=1; pytest `-o addopts= -p no:cacheprovider`. No dependencies installed and no physical/browser resources occupied by this reviewer.
- `python -m pytest -o addopts= -p no:cacheprovider apps/backend/tests/test_target_classification_continuation.py apps/backend/tests/test_zero_touch_database_happy_path.py -q`: **66 passed,0 skipped, exit0,28.46s**.37 continuation and29 database-first cases. One existing Starlette/httpx TestClient deprecation warning.
- Six inline Sandbox assertions: independent fieldwise early USER type/segment conflict, compatible resolution, and retained low score/low quality/reference change/additional conflicting observation. All **PASS**: review/Send409, no snapshot, confirmation, ledger or mutation; ACRA0. These use current application APIs and safe memory fixtures; no test file was added.
- Two independent inline Mock retained-selection counterexamples reproduced TC-R1-001 for DOCUMENT and USER; three additional intake probes confirmed partial explicit and deterministic incompatible labels falsely remain ready, with a legacy no-label/no-selection compatibility control. Subsequent safe-state capture confirmed the false-ready/Prepared, unsent technical-failure projection. The first exploratory probe used a nonprojected response field and ended KeyError; corrected internal-accessor probes provide the cited evidence. That exploratory failure is not counted as passing evidence.
- `python -m unittest discover -s tests -p test_contract_test_isolation.py`: **1 passed, exit0,1.607s**. Hostile ambient configuration is neutralized before app import and MongoClient is forbidden.
- All five PDFs: one page each, zero native extracted text. Rendered with installed PDFium entirely in memory and visually inspected: fictional notice, identity/classification/system-profile lines and footer readable, no clipping. Actual OCR is separately executed in I66/B.
- Every raw/canonical hash/size, aggregate and exact path inventory checked independently at start and end. Tracked whitespace plus explicit UTF-8/trailing-whitespace checks across all reviewed text/new Markdown pass. Index remains empty.

### Coordinator evidence on frozen R1, attributed rather than claimed independently rerun

- Exhaustive full backend, three disjoint partitions covering all2561 collected items: group1 **1218 passed/19 Mongo skips**,607.39s; group2 **1133 passed/103 Mongo skips**,247.74s; group3 **88 passed/0 skips**,349.85s, including both100-run stability cases. Total **2439 passed/122 conditional Mongo skips**, all exit0. Ordinary conditional skips are not represented as physical passing evidence.
- Fresh affected physical Mongo: **10 passed/0 skips**,44.27s; normal case/snapshot/restart and generated allowlisted cleanup. Broader R0 physical17-suite122/122 result remains separately attributed below.
- Fresh guarded browser **4/4 pass**: Alpha8.7s, Partnership9.8s, Government6.7s, uncertainPolicy5.4s. Actual HTTP/OCR; Alpha/Partnership disposable physical Mongo. Exact-name parent cleanup VERIFIED each database journey, external calls0/network-policy violations0. Normal pre-Send SEARCH1/SHELL0/POLICY0/AMEND0/READBACK0/attempts0/classification PUT0; post-Send SEARCH2/SHELL1/POLICY1/AMEND0/READBACK1. Government stops at ownership review. Policy uncertainty remains read-only/no-replay.
- Current backend Ruff **PASS**; strict mypy **126 source files PASS**; contracts **44 PASS**; direct project-state/architecture/policy/provider/secret checkers **PASS**. Hashes independently rechecked unchanged by coordinator.

### Explicit byte-unchanged surface evidence from R0

Only seven canonical paths changed for R1. Frontend, fixture PDFs, configuration/test isolation, schema/repositories, Windows and browser harness source remain byte-identical to R0. Prior executed evidence on those surfaces: frontend **42 files/520 tests PASS**, TypeScript/build PASS (128 modules; existing551.15KB/>500KB advisory); exact-lockfile npm ls and pip dependency checks PASS; physical **17 suites/122 passed/0 skips**; Windows lifecycle **31 PASS**; tooling **73 PASS**, plus hostile isolation1; security/governance **170 PASS**; actual legacy OCR **6 PASS**. These results are preserved with their R0 execution identity and are supplemented by fresh R1 affected physical/browser/backend evidence; they are not claimed as newly rerun by this reviewer. No full64-lifecycle browser execution or remote CI result is asserted.

No external ACRA/GoldTier smoke, Production/PingFed or Live interoperability test was authorized/executed. Passing authored suites do not override M2 or establish historical protected non-access.

## Contract, architecture and security assessment

The flow remains existing LocalPdfTextIdpProvider -> strict observations -> DocumentProcessingService -> case binder -> CLM/ZeroTouch -> target mapper/ledger. The pure selection model is not a second IDP/classification/service/repository/calculator owner. Exact sponsor vocabularies and quarantined examples remain; segment is explicit text and fixture Corporate/DI - Government values do not become universal mapping rules. Fixed DSD/ACRA/Singapore/ANZBGL values remain system-owned; unsupported account/product values are not inferred. The active XPI family and EDS Mock distinction remain unchanged.

Schema10 extends the same envelope. Strict schemas1..9 reject explicit later fields even null/empty, preserve absent evidence as unknown, and read without rewriting/reclassification. Validators bind original document observation/page/method/quality/score/value/event evidence and case policy/source authority. Existing CAS, insert-only/update-only, creator/team identity, no resurrection, memory/Mongo separation and ledger no-replay owners remain. Old binaries cannot decode schema10 writes; this documented boundary is not hidden fallback.

Backend actor/session/team capability and reauthorization remain inside the owning lock/CAS. Browser changes consume the existing scoped query/mutation owners, escape retained labels and introduce no persisted sensitive cache, retry/authorization or raw-document owner. Raw upload/OCR bodies stay transient; logs/API errors remain minimized. Current test isolation is strengthened, subject to TC-R1-002's historical limit. No confirmed newly tracked credential, raw provider payload, real personal fixture or confidential sponsor artifact was found; scanner coverage is not universal detection and does not prove whole-session non-access.

Actual target uncertainty is projected from retained attempted operations, with safe Shell/Policy chronology, frozen inputs and no Send/replay. Empty intent is NOT_SUBMITTED rather than uncertainty. The original owner's real UAT cause cannot be conclusively assigned without its unavailable ledger: controlled evidence proves the empty-intent projection defect and legitimate earlier uncertainty examples, not classification-triggered external writes in that history.

Existing large composition hotspots, process-local concurrency, deterministic noncalibrated OCR scores and production/legal sponsor questions remain bounded pre-existing limitations. Government-control ownership, related parties/hierarchy/original-file transfer, Live/Production/PingFed, KYC/four-eye/Ready-for-Approval and broader Q-001–Q-018 authority remain later dependencies, distinct from these two current blockers.

## Required fixes and readiness

1. Remediate TC-R1-001 through the currentness owner for present receipts in all provider modes, preserving no-receipt Mock compatibility. Prove review/confirmation refusal before any freeze, compatible resolution and truthful current package/final-action projection.
2. Preserve TC-R1-002 and obtain explicit owner treatment of the historical safety acceptance condition. Do not access owner dotenv/database to investigate or claim a source repair establishes historical non-access.
3. Freeze any changed scope and run fresh affected/broad evidence plus independent review. This R1 FAIL cannot authorize the second local commit. Only one further behavioral remediation round remains under the original maximum2.

Next local second-commit readiness: **BLOCKED**. PR/publication/merge/next-phase and Live ACRA/GoldTier/PingFed readiness: **not established/unauthorized**. No pre-PR publication gate was run to certify this intentionally uncommitted handoff.

API/types changed; durable schema9->10; existing local IDP connector observations changed; test/configuration/CI isolation changed; bounded classification/readiness/runtime behavior changed. Auth/security source binding and test containment strengthened without replacing RBAC. Existing architecture owners, target provider family/endpoints/mappings, ownership threshold and provider status are unchanged. Currentness behavior remains defective in Mock as identified. Reviewer made no implementation correction, stage, commit, push, PR, merge, branch/worktree mutation or next-phase action.

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
- docs/PROJECT_STATE.md
- docs/contracts/CLM_READINESS_POLICY.md
- docs/contracts/IDP_FIELD_PROFILE.md
- docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md
- docs/decisions/DECISION_LOG.md
- docs/demo/ZERO_TOUCH_DATABASE_HAPPY_PATH_UAT.md
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
