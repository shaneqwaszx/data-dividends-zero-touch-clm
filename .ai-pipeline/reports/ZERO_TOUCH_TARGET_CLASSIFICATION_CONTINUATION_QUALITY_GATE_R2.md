# Target-classification continuation — independent FINAL R2 Quality Gate

Date: 2026-10-06. Fresh independent reviewer run under `fyp-quality-gate`. R2 is the second and final owner-authorized remediation round. The reviewer inspected frozen source, contracts, tests, documentation, architecture, security and adverse behavior. Only this assigned report is writable; no implementation or acceptance criterion was changed.

## Executive result

**FAIL — P0/P1/P2 = 0/2/0.** R2 repairs the specific R1 Mock mode readiness/freeze counterexamples. A new ordinary-API counterexample exposes the remaining underlying conflict/currentness gap in both Mock and Sandbox: a USER choice retained before intake silently survives two later contradictory current trusted documents. Submission readiness and the package become Complete/Prepared without classification review. Explicit final Send then freezes and completes this unresolved profile.

The second P1 is the unchanged requirement-T historical safety acceptance blocker. Whole-session owner-dotenv/protected-database non-access cannot be certified after the disclosed earlier ambient configuration/Mongo startup incident. Later isolation controls cannot establish historical non-access. This report does not assert definite protected-database access or waive the owner's criterion.

No second commit is eligible. Two permitted remediation rounds are exhausted. Preserve this uncommitted worktree and stop for owner review. No further remediation, commit, amendment, push, PR, merge, protected-database investigation, worktree removal or next phase is authorized by this verdict.

## Current, tested and reviewed identity

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/zero-touch-registry-reuse-happy-path/data-dividends-zero-touch-clm`.
- Branch: `fix/zero-touch-registry-reuse-happy-path`.
- HEAD / previous accepted commit: `ccff7471fd23e64e87bf94a087a5540762276900`.
- BASE_SHA / inspected local origin/main: `771a9696e1e31e3865da4fbbb3f9b33b5959cb6a`.
- Reviewed content: HEAD plus exactly72 paths in `ZERO_TOUCH_TARGET_CLASSIFICATION_CONTINUATION_REVIEW_MANIFEST_R2.json`.
- Raw aggregate SHA256: `2ac3a5b29e5501da9eb34bd69dd3324e9ce45a30fb25f5e675eb6642abbd501a`.
- Formula: lexically sorted UTF-8 `path + NUL + raw_sha256 + NUL`, then SHA256. All raw/canonical hashes, sizes and exact modified/new path inventory independently verified. Text canonicalization converts CRLF to LF; PDFs remain binary.
- Only six canonical paths change R1->R2: planner, CLM owner, continuation tests, CLM readiness policy, decision log and UAT guide. Cumulative72-path content is reviewed; R0/R1 reports/manifests remain immutable historical evidence.
- Derivative implementation report, gate reports and manifests are excluded from source identity. Their updates do not alter acceptance. Tests exercise uncommitted frozen content, not a future commit.
- Git index empty.65 modified tracked paths plus7 reviewed new paths; additional untracked derivative reports/manifests are named exclusions. No unexpected path, source mutation or Git action by this reviewer.
- No publication gate or latest-main fetch was run for this deliberately uncommitted review. Remote CI and PR readiness are unclaimed.

## Findings

### TC-R2-001 — P1: an earlier USER choice silently survives later contradictory current trusted documents

The existing assessor in `apps/backend/app/services/document_processing.py` rejects ambiguity by producing no candidate when current labelled values disagree. `ClmOrchestrationService._document_classification_current` (`clm_orchestration.py:1344`) checks USER disagreement only when a safe candidate exists. When contradictory documents remove that candidate, an earlier USER choice is treated as current. The binder preserves USER selections during automatic synchronization. R2's all-mode currentness predicate therefore still receives True for this unresolved conflict.

Independent reproduction used ordinary authenticated public APIs, fresh memory repositories, fictional seeded Alpha, explicit isolated test configuration and local/fake adapters. No source/evidence mutation was used:

1. Create Alpha before document intake.
2. PUT target-classification = Company - Private / Corporate. Both selections are USER.
3. Upload current Alpha identity text explicitly labelled Company - Private / Corporate.
4. Upload a second identical Alpha identity document explicitly labelled Partnership - Unregulated / Corporate.
5. Complete intake with expected_document_count=2. Both documents become current REVIEWED, all classification observations HIGH and score>=0.85, and both processed timestamps are after the USER selection.
6. GET returns readiness blockers [], only TARGET_CONFIRMATION_REQUIRED, Submission readiness COMPLETE, package COMPLETE/Prepared, final review REVIEW_REQUIRED. No classification review/conflict blocker is presented.
7. POST final target-confirmation returns200. Snapshot, confirmation and ledger are persisted. Both modes finish COMPLETED / SUBMISSION_CONFIRMED with ledger FINALIZED.

Executed twice per mode across independent exploration and confirmation runs. In Sandbox, fake target method chronology is GET, GET, POST, POST, GET: initial Search, post-confirmation Search, Shell, Policy, same-ID readback. No Amend is required for the existing identity-only plan. Mock uses its existing internal target owner and no injected HTTP transport calls. External ACRA and GoldTier calls remain0.

This is a false-ready/current-classification review defect. Classification PUT itself still dispatches0 provider calls and creates0 attempted mutations. Final confirmation was explicitly supplied; the finding does **not** establish a final-confirmation bypass, classification-triggered writes, or mutation replay. It establishes that contradictory current trusted evidence is silently accepted using a choice made before that evidence existed.

Violates owner F/G conflict/manual-review requirements, H/M current-input status consistency, and Q7/Q11/Q13–15/Q26. This is a residual form of the currentness/conflict design problem, not a sponsor dependency or accepted debt.

Required owner-authorized repair direction: preserve the reason/current observation set when automatic assessment yields no candidate. Distinguish a genuinely missing/unsafe field from contradictory current evidence and bind explicit manual review to that current evidence version/fingerprint. An older USER choice must not silently count as review of newly conflicting documents. A repeated explicit review of the same chosen value must be representable as a fresh decision; merely blocking every ambiguous field forever would break authorized manual fallback. Keep the existing document/case/CLM owners, no universal precedence or legal-form mapping, local-only save, final confirmation, freeze and no-replay. Add ordinary-API prior-choice/two-current-document regressions in both modes and obtain fresh independent review after any separately authorized repair. This reviewer implemented no fix.

### TC-R2-002 — P1 acceptance blocker: requirement-T whole-session safety remains unverified

The disclosed early focused invocation encountered ambient dotenv/Garden settings. A separate early standalone contract invocation selected ambient Mongo settings and failed application startup with PersistenceDataInvalidError. Source inspection confirms MongoCaseStore.initialize pings and creates indexes before decoding all records, and can recover/replace earlier valid records before a later invalid record fails. Failure therefore cannot prove no connection or no side effect.

Exact ambient namespace and effects remain unknown. This reviewer did not read owner dotenv, resolve an ambient URI, access an owner database or investigate/clean clm_poc. No URI, secret, raw provider body or private exception material is retained here. Available evidence does not establish ACRA/GoldTier execution from that startup, but cannot certify historical protected non-access or absence of database changes.

Current containment independently passes: ordinary pytest disables dotenv; APP_ENV=test settings bypass dotenv; standalone contracts establish memory/Mock before app import; hostile subprocess testing forbids MongoClient construction. These controls prevent recurrence in their tested paths. They do not undo historical uncertainty. Only the owner can decide acceptance disposition; further investigation requires separate explicit authority. Under unchanged requirements, this blocker independently requires FAIL.

### Earlier remediation status

R0's prior USER/safe-document disagreement and Sandbox snapshot-start/projection examples are repaired. R1's stale DOCUMENT/USER Mock examples and explicit partial/incompatible Mock profiles now require review before snapshot/confirmation. Independent R2 tests and16 additional all-mode adversarial cases prove those repairs, local compatible resolution and preserved no-input legacy Mock behavior. TC-R2-001 demonstrates the still-unhandled ambiguous-current-document branch; it does not invalidate the narrower repaired evidence.

## A–W acceptance checklist

I71 = independently executed71 focused tests; A16 = independently executed16 additional all-mode adverse/resolution cases; C2 = independently reproduced two valid public-API conflict cases; H1 = independently executed hostile subprocess; S = source/contracts/decisions/diff/hygiene review; B = coordinator execution on exact R2; U = explicitly unchanged earlier-surface evidence.

| Requirement | Result / evidence |
|---|---|
| A Submission readiness meaning/label | PASS S/I71/B; current conflict correctness is TC-R2-001. |
| B Submission settings/groups/constants | PASS S/U/B; authority/provenance retained in details. |
| C Existing document/IDP owner | PASS S/I71; two observations separate from four identity fields. |
| D Bounded automatic classification | PASS I71/A16/S; three exact types, explicit segment, score/current source audit. |
| E Separate source/audit | PASS I71/S; DOCUMENT/USER and original policy/version/page/method/score retained. |
| F Auto/partial binding and conflict review | FAIL C2; explicit ambiguity silently inherits older USER decision. Normal/partial I71/A16 pass. |
| G Safe manual fallback | FAIL C2 stale prior decision; compatible new fallback and deterministic Government/private refusal pass I71/A16. |
| H Readiness/package/final status | FAIL C2 false-ready/Prepared; normal and repaired cases pass I71/A16/B. |
| I Package label /12 nodes | PASS I71/B/S. |
| J Classification save calls/attempts0 | PASS I71/A16/C2/S; C2 dispatch follows explicit final confirmation. |
| K Controlled uncertainty diagnosis | PASS I71/S; empty intent defect isolated, genuine retained Shell/Policy chronology truthful. Original owner chronology unknown. |
| L Attempt freeze/no replay | PASS I71/B/S; genuine uncertain attempts reject edits and repeated confirmation. |
| M Authoritative current-state consistency | FAIL C2 conflict accepted as ready; genuine retained uncertainty passes I71/B. |
| N Fictional fixture graphs/profiles | PASS I71/S; Government separate without fabricated control rule. |
| O Image-only visible profiles | PASS independent five-PDF native-text check, I71 actual OCR, unchanged earlier visual inspection. |
| P Atlas-safe seed/UAT/bootstrap guide | PASS S/I71;32-byte allowlist/idempotence, no credentials. |
| Q Required38 checks | FAIL overall; detailed results below. |
| R Guarded browser journeys | PASS B four current R2 journeys; scope is actual performed scenarios. |
| S RM terminology/approval separation | PASS S/B/U. |
| T Safety/currentness | FAIL TC-R2-001 and TC-R2-002. Controlled external calls0 does not certify historical protected non-access. |
| U Required verification | PARTIAL — full run includes1 environmental failure; unchanged isolated/owning reruns pass. No clean full-run PASS claim; execution does not erase independently reproduced defects. |
| V Fresh gate0/0/0 | FAIL; fresh R2 is0/2/0. |
| W Conditional second commit | BLOCKED; exact PASS condition unmet. |

## Q1–38 evidence

| Q | Result |
|---|---|
| 1 Alpha extraction | PASS I71 actual OCR. |
| 2 Zero-click automatic binding | PASS I71/B; classification PUT0. |
| 3 Partnership binding | PASS I71/B actual Gamma scan. |
| 4 Government classification | PASS I71/B; ownership limitation explicit. |
| 5 Missing/partial review | PASS I71/A16; intentional legacy no-input Mock compatibility remains. |
| 6 Low-confidence review | PASS I71/A16 both modes with explicit input. |
| 7 Contradictory current documents review | FAIL C2 when prior USER choice exists. No-prior-choice I71 passes. |
| 8 Out-of-scope type not automatic | PASS I71/A16. |
| 9 Fixed system values protected | PASS I71/S. |
| 10 Document/version/page source audit | PASS I71/S. |
| 11 Only current prerequisites ready | FAIL C2 false-ready; normal/repaired I71/A16/B pass. |
| 12 Confirmation alone not readiness failure | PASS I71/B. |
| 13 Current Prepared package | FAIL C2; repaired stale-selection cases I71/A16 pass. |
| 14 Only valid final-review action remains | FAIL C2 unresolved classification hidden. |
| 15 No contradictory status | FAIL C2 unresolved current conflict presented Ready/Prepared. |
| 16 Manual save provider0 | PASS I71/A16/C2. |
| 17 Automatic binding provider0 | PASS I71/B; separate initial Search not classification. |
| 18 No pre-confirm writes/readback | PASS I71/B/C2; writes follow explicit confirmation. |
| 19 No pre-confirm attempted mutation ledger | PASS I71/B/C2. |
| 20 Freeze after genuine attempt | PASS I71/S. |
| 21 Fresh pre-send not falsely uncertain | PASS I71. |
| 22 Actual Shell uncertainty | PASS I71 controlled timeout. |
| 23 Actual Policy uncertainty | PASS I71/B. |
| 24 No uncertainty replay | PASS I71/B. |
| 25 Save cannot create/relabel uncertainty | PASS I71/S. |
| 26 Current-input/prepared consistency | FAIL C2 prior decision predates conflicting evidence. |
| 27 Alpha exactly two60/40 | PASS I71/S. |
| 28 Beta six direct/indirect people | PASS I71/S:30/25/17/14/8.5/5.5. |
| 29 Gamma six interests sum100 | PASS I71/S:30/25/20/10/10/5. |
| 30 Inclusive>=25 boundary | PASS I71; unchanged sole Decimal engine. |
| 31 No second ownership calculator | PASS S. |
| 32 Government no invented shares/control | PASS I71/B/S. |
| 33 Five PDFs image-only | PASS independently one page each/no native text. |
| 34 Actual Tesseract identity/classification | PASS I71/B. |
| 35 Seed/document identity match | PASS I71 allfour bundles. |
| 36 Fresh seeds ACRA0 | PASS I71/B physical browser. |
| 37 Fictional fixture data | PASS S/unchanged visual inspection; historical protected non-access separately unverified. |
| 38 Seed idempotence | PASS I71/B physical evidence. |

## Independent tester/adversarial evidence

- Primary Python3.12 venv, worktree backend/root/test PYTHONPATH; APP_ENV=test, memory, ambient ACRA/GoldTier Mock and Gardenfalse; PYTHONDONTWRITEBYTECODE=1. No dependency install, browser or physical database action by this reviewer.
- `python -m pytest -o addopts= -p no:cacheprovider apps/backend/tests/test_target_classification_continuation.py apps/backend/tests/test_zero_touch_database_happy_path.py -q`: **71 passed,0 skipped,31.94s,exit0**,42 continuation plus29 database/fixture tests. One existing Starlette/httpx TestClient deprecation warning. Existing five image-only scans use actual local Tesseract through the configured path.
- **16 independently authored inline assertion cases PASS**: both Mock and Sandbox retained DOCUMENT/prior USER conflicts, type-only/segment-only/out-of-scope/low-score/LOW-quality/UNKNOWN-method evidence, refusal before freeze and compatible explicit local resolution. Snapshot/confirmation/ledger remain absent in blocked cases; mutation0 and ACRA0; saves themselves preserve provider counts. No reviewed test was added.
- **Two valid ordinary-API C2 counterexamples reproduced**, in both modes, followed by a second verification run proving both current reviewed HIGH-score documents were processed after the prior USER choice. Successful process exit means reproduction succeeded; it is **not acceptance PASS**.
- `python -m unittest discover -s tests -p test_contract_test_isolation.py`: **1 passed,1.685s,exit0**. Hostile ambient configuration neutralized before app import; MongoClient forbidden.
- Five PDFs independently checked with installed pypdf: one page each, no native extracted text. Prior independent five-page visual inspection belongs to unchanged R1 PDF bytes; no new visual execution is claimed.
- Initial exploratory inline probes required repository test credential bootstrap; a string-only enum injection and over-specific stage/Search assertions were corrected. Those failed exploratory invocations are not passing evidence or product findings; the cited16-case run uses valid enums/public API expectations. They used isolated APP_ENV=test/memory and did not access owner dotenv/DB.
- Full raw/canonical identity, exact inventory, tracked whitespace, explicit untracked/new Markdown and all reviewed text UTF-8/trailing-whitespace checks independently pass. End-of-review identity is rechecked before issuing this verdict.

## Broader evidence attributed to coordinator

- Full backend collection:2566 items, exhaustive disjoint groups1242/1236/88. Group1 **1222 passed/19 conditional Mongo skips/1 failed**,pytest563.21s; group2 **1133 passed/103 skips**,242.69s; group3 **88 passed/0 skips**,343.24s, including both100-run stability cases. Aggregate **2443 passed/122 conditional skips/1 failure**, group1 exit1; other groups exit0. This is not a clean full-backend PASS.
- The failing parameter is `test_phase24b_stage_recovery_round1.py::test_unfinished_current_ownership_precedes_independent_readiness[False-False-False]`. Full causal log shows Windows **WinError10055 socket-buffer/queue exhaustion** in asyncio Proactor `socket.socketpair` while TestClient enters its request portal, before the application ownership/load request runs. A secondary unraisable missing `_ssock` warning follows partial event-loop initialization.
- Fresh independent quiet-host reruns on unchanged R2: the exact failed case **1 passed,0 skips,2.27s,exit0**; its whole owning recovery suite **19 passed,0 skips,23.53s,exit0**. This supports a recovered environment/resource failure rather than a new proved product regression. The full-run failure remains recorded; these reruns are not relabelled as a clean exhaustive run, and no source/harness change or extra remediation was performed.
- Fresh affected physical Mongo **10 passed/0 skips,37.73s**, only generated allowlisted disposable databases in owned loopback Mongo7; cleanup verifies absence.
- Full frontend **42 files/520 tests passed,10.15s**; TypeScript and build PASS,128 modules and551.15KB existing warning.
- Guarded real-HTTP browser **4/4 PASS**: Alpha9.8s, Partnership9.9s, Government6.6s, uncertain Policy6.0s.
- Backend Ruff PASS; strict mypy **126 source files PASS**.
- Contracts44 plus hostile isolation1 plus governance97: **142 passed,40.50s**. Initial collection failure from missing contract helper PYTHONPATH was corrected before the passing run; that failed collection is not PASS evidence.
- Direct project-state, architecture, policy-authority, provider-readiness and secret checkers PASS.

Fresh coordinator logs for the four browser journeys and full frontend result were independently inspected. Current R2 physical/browser tests use actual Mongo/Tesseract with local fake XPI, not Live providers. Parent exact-name database cleanup is VERIFIED after child shutdown and before each database E2E PASS. No external HTTP/network-policy violation occurred. Normal pre-Send Search1/Shell0/Policy0/Amend0/readback0/attempts0/classification PUT0; post-Send Search2/Shell1/Policy1/Amend0/readback1 with synthetic ID. Government stops at unsupported ownership review. Policy uncertainty is read-only/no-replay.

Explicit unchanged earlier-surface evidence remains attributed to its own revision: R0 physical17 suites122/122, Windows31 lifecycle tests, affected tooling73 plus hostile isolation1, dependency pip/npm checks and Playwright inventory71 tests/14 files/64 lifecycles. Persistence/schema/fixture/harness bytes are unchanged through R2 and fresh affected physical/browser lanes supplement them. No full64-lifecycle E2E or remote CI execution is claimed. Existing frontend act warnings, backend Starlette warning and >500KB build warning are visible; no new required dependency change was introduced. Actual pre_pr_check publication gate was not run on intentionally uncommitted content.

## Contract, architecture and security assessment

The sponsor vocabulary remains intact and classified by its current authority. Three automatic types and synthetic segment values are owner-authorized bounded POC behavior; no universal legal mapping follows. Quarantined examples were not promoted. Government control/legal UBO, related-party hierarchy, original-file transfer, Production/PingFed, provider KYC/four-eye and Ready-for-Approval remain unresolved/later scope, not excuses for TC-R2-001.

API/type and browser projection changed; durable case schema9->10 retains separate source evidence and strict read-only historical compatibility. Existing insert-only/update-only, CAS/no-resurrection, RBAC/team/session/locked reauthorization, source-neutral canonical boundary, sole Decimal engine and ledger call-stopping/no-replay owners remain. Local IDP observations/test isolation/configuration changed; GoldTier mappings, endpoints, family and provider status did not. No second owner/service/repository/dependency framework was added. Runtime local binding/preparation/status/test cleanup changed.

The current conflict assessment collapses distinct no-candidate reasons and lacks a USER decision binding to current conflicting evidence; that is the established product finding. No further P0/P1/P2 code/contract/security finding was established on this reviewed scope. Current safe error/source constraints and hostile isolation pass. No supported new secret/confidential-artifact pattern is found in reviewed task-owned content; this is a scoped content assessment, not a historical protected-non-access guarantee.

## Required fixes, readiness and final Git status

TC-R2-001 needs separately authorized design/remediation and fresh independent review. TC-R2-002 needs owner acceptance disposition; further protected investigation is not authorized. No third remediation is inferred.

Continuation acceptance and second-commit readiness: **FAIL / blocked**. Next phase: **not ready and not authorized**. Live ACRA/GoldTier/PingFed readiness: **not established**. Controlled Mock/Local/fake-Sandbox passing scenarios are not Live interoperability or KYC/approval.

Final exact72-path manifest/raw/canonical/size/inventory and whitespace checks independently PASS; index remains empty and branch/HEAD/base unchanged. All reviewer tests were read-only for reviewed content. Coordinator confirms the owned Mongo container was removed after disposable database count0, all reserved owned ports are free, and the primary checkout is clean; this reviewer required no remaining physical/browser resource. The retained worktree is intentionally dirty with65 tracked modifications and7 reviewed new paths plus excluded derivative evidence.

Only `.ai-pipeline/reports/ZERO_TOUCH_TARGET_CLASSIFICATION_CONTINUATION_QUALITY_GATE_R2.md` was written by this reviewer. No source/test/configuration/doc fix, staging, commit, amendment, push, PR, merge, next phase or worktree cleanup occurred. Preserve the worktree and stop for owner review.
