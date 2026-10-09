# Synthetic company pack - independent Quality Gate

Date: 2026-10-09 (Asia/Singapore). Assignment: four complete synthetic happy-path companies.

## Executive result

**PASS. P0/P1/P2 findings: 0/0/0. No required fix remains.**

The frozen candidate satisfies the assigned local SYNTHETIC MOCK company, document,
owner-based database warm, cache reuse, explicit confirmation, and no-replay criteria.
This is the sole independent verdict. It applies only to the identity and evidence below.
Stop for owner publication review; no commit, push, PR, merge or next phase is authorized.

## Reviewed identity and boundary

- Branch: `feat/synthetic-happy-path-company-pack`.
- Worktree: `C:/Users/shane/.codex-clean2/worktrees/synthetic-happy-path-company-pack/data-dividends-zero-touch-clm`.
- BASE_SHA / HEAD / fetched origin/main: `21124498cb1b8fd47b1406534d6fd9c24af0e2ea`.
- Frozen payload: **20 paths**; raw aggregate SHA256 `71349034c050402494ef6d5937aebc5cfbfb21d745094356820718254aa13d02`.
- Formula: SHA256 of each sorted UTF-8 path, NUL, raw-file SHA256, NUL.
- Every raw hash and the aggregate were independently recomputed before and after execution.
- Current source is uncommitted; HEAD names its base rather than the modified source.
  Behavioral evidence belongs to the frozen working-tree payload, not an invented commit.
- Excluded derivative evidence: implementation report, manifest and this report only.
  The finalized implementation report was independently read, including final backend
  results and exact-byte frontend/typecheck/build evidence supplied by the coordinator.
- Review scope: BACKEND_DOMAIN, PERSISTENCE (existing-owner warm), CI_TOOLING, FRONTEND_UI.
- Reviewer writes only this report. No reviewed source, tests, configuration, assets,
  acceptance criteria or Git state were changed by the reviewer.

The full tracked diff and all task-owned new files were inspected. Complete reviewed set:

| Path |
|---|
| apps/backend/app/connectors/mock_acra.py |
| apps/backend/app/connectors/synthetic_company_pack.py |
| apps/backend/tests/fixtures/uat/README.md |
| apps/backend/tests/fixtures/uat/meridian-synthetic-infrastructure-client.pdf |
| apps/backend/tests/fixtures/uat/orion-synthetic-technologies-client.pdf |
| apps/backend/tests/fixtures/uat/pacific-synthetic-ledger-client.pdf |
| apps/backend/tests/fixtures/uat/straits-synthetic-holdings-client.pdf |
| apps/backend/tests/test_slice_f_document_pack.py |
| apps/backend/tests/test_synthetic_company_pack.py |
| apps/backend/tests/test_synthetic_company_pack_real_mongo.py |
| apps/frontend/e2e/slice-b-registry-demo.e2e.ts |
| apps/frontend/e2e/synthetic-company-pack.e2e.ts |
| apps/frontend/src/App.tsx |
| docs/ARCHITECTURE.md |
| docs/PROJECT_STATE.md |
| docs/demo/SYNTHETIC_COMPANY_PACK.md |
| scripts/generate_synthetic_company_pack.py |
| scripts/run_physical_mongo_tests.py |
| scripts/warm_synthetic_company_pack.py |
| tests/test_phase_07_delivery_assets.py |

## Prerequisite and acceptance checklist

Authoritative read-only `gh run view 37918635850` established Project CI / push /
head `21124498cb1b8fd47b1406534d6fd9c24af0e2ea`: backend, frontend, local-ocr,
phase12-mongo, security, demo-lifecycle-windows and e2e are all COMPLETED / SUCCESS.
E2E completed at 2026-10-09 18:54:56 +08:00. Branch reflog records creation at
19:03:19 +08:00, after that gate. Coordinator records that origin was fetched and
checked before branch/worktree/files; independent review confirms the exact retained
origin/main and authoritative seven-job result. No pre-gate implementation is indicated.

Evidence abbreviations: API = independently executed new company tests; PACK = actual
17-file extraction regression; PHYSICAL = independently executed new/cache Mongo tests;
BROWSER = independently executed parameterized real-browser journeys; CLI = independent
actual utility invocation on a newly generated allowlisted disposable database.

| Assigned requirement | Result and direct evidence |
|---|---|
| Latest clean merged baseline, exact SHA, fetch and 7/7 prerequisite | PASS; exact base/HEAD/origin/main, authoritative CI and post-E2E branch chronology above |
| Exact requested branch/worktree; never develop on main | PASS; branch/worktree/status observed independently |
| All four exact legal names/UENs/addresses/country | PASS; fixture data inspected against assignment, deterministic PDF tests and API identity comparisons |
| Private company entity type / LIVE entity status | PASS; strict Mock DTO construction inspected; LIVE remains fictional entity status, environment MOCK |
| Orion 70/30 graph | PASS; exact natural-person Decimal direct/aggregate values and candidates |
| Pacific 40/35/25 graph; 25 qualifies inclusively | PASS; Ellis 25 is PROVISIONAL_UBO_CANDIDATE under the existing engine |
| Straits nested graph and 48/40/12 results | PASS; actual edges root60/40 and holding80/20; exact Decimal results and Fiona/Jordan candidates |
| Meridian nested graph and 30/20/30/20 results | PASS; actual edges root50/30/20 and holding60/40; exact Decimal results and Hannah/Iris candidates |
| One stable fictional director per company; distinct officer IDs | PASS; four bounded IDs/fields inspected; API proves directors absent from ownership candidates |
| Extend existing Mock registry owner | PASS; connector dataset extension only; no second registry engine |
| ENTITY_PROFILE/OFFICERS/OWNERSHIP_PARTIES/RELATIONSHIPS COMPLETE | PASS; API and BROWSER verify four COMPLETE results for each company |
| Fresh miss four operations exactly once | PASS; API and BROWSER record 1+1+1+1 per exact UEN |
| Strict DTO, source provenance, UTC, mapping, coordinator | PASS; ordinary adapter/coordinator/mapping chain inspected; PHYSICAL preserves original UTC microseconds |
| No orchestrator shortcut or direct completion fixture | PASS; orchestrator unchanged; ordinary intake, documents, ownership, readiness and ledger exercised |
| Four matching deterministic native-text PDFs; project generator | PASS; byte equality to existing text_pdf helper; one page each; actual parsing and rendered visual review |
| Legal Name/UEN/Registered Address/Country exact match | PASS; API proves all four MATCH/ACCEPTED and AUTO_CONFIRMED per company |
| HIGH accepted extraction evidence under current policy | PASS; all four fields HIGH and deterministic score 0.97; no calibrated-probability claim |
| PDF ownership bypass prohibited | PASS; no percentages or party names in PDF text; no target classification labels; registry graph remains the quantitative source |
| Bounded asset index and exact inventory truthful | PASS; 17 PDFs, named generator, four raw hashes, PACK and four independent asset tests |
| Full synthetic bundles persisted through existing owner | PASS; warm calls adapter/coordinator/repository, no direct BSON; PHYSICAL and actual CLI prove persisted complete bundles |
| MOCK_ACRA_SYNTHETIC_V1 distinct from Marketplace namespace | PASS; exact identity inspected; memory/physical tests prove adjacent official namespace miss |
| COMPLETE only; exact UEN/provider/environment/contract/dataset key | PASS; complete-only warm guard before write; current coordinator and store validators retained |
| Original retrieval provenance retained | PASS; repeat warm leaves snapshots identical; original UTC microseconds survive physical restart |
| No document/case/analysis/target state cached as registry evidence | PASS; existing normalized snapshot schema/owner inspected; distinct cases independently recompute their own evidence |
| Dedicated safe database; no shared clm_poc automation | PASS; protected name refused before client construction; every physical/CLI database generated and allowlisted with cleanup absence |
| Manual explicit operator command; no startup seed | PASS; documented safe command; no composition/startup hook changed |
| Singapore route and exact synthetic UEN accepted | PASS; separate independent API probe asserts SG resolution / ACRA route for all four |
| Initial Mock Search uses existing rules | PASS; NO_MATCH retained, initial target call search only; no constructor/customer seed |
| Ownership ANALYZED with exact expected candidates; no ownership blocker | PASS; API/PHYSICAL check all exact Decimal direct/indirect/aggregate values and classifications |
| No reconciliation blocker/manual discrepancy resolution | PASS; current blockers reduce to TARGET_CONFIRMATION_REQUIRED after ordinary matching document work |
| Target classification stays explicit user selection | PASS; API helper and BROWSER save Company - Private / Corporate through current versioned endpoint |
| Review & Send mandatory; zero target mutations beforehand | PASS; initial target calls contain search only; BROWSER has no target-confirmation POST before explicit send |
| Explicit Mock confirmation reaches COMPLETED / SUBMISSION_CONFIRMED | PASS; all four API, PHYSICAL and BROWSER journeys |
| Existing operation order and exact readback retained | PASS; search/recheck/shell/policy/amend/readback recordings; VERIFIED readback ID equals returned target ID |
| Reload/reopen/restart never replays mutations | PASS; API repeated GETs, PHYSICAL application restart and BROWSER reload preserve ledger/outcomes with unchanged calls |
| Owner-warmed distinct same-UEN case CACHE_HIT; no provider calls | PASS; four API owner-warm cases and PHYSICAL cases use zero calls; separate-case hit also tested before either target submission |
| SYNTHETIC MOCK UI/docs; official Marketplace/Garden truth unchanged | PASS; explicit local banner/docs/PDF labels; inherited Garden partial/official boundary regression executed |
| Required focused, physical, assets, frontend/browser and broad checks | PASS with explicit conditional skip accounting below |
| Fresh independent gate and publication stop | PASS; this review is independent of implementation; no publication action performed |

## Exact ownership outcomes

All results are Decimal values from the existing engine. Values below omit the common
fictional surname Synthetic only for table readability.

| Company / UEN | Direct / indirect / aggregate natural-person results (%) | >=25% provisional candidates |
|---|---|---|
| Orion / 202400014N | Avery 70/0/70; Blair 30/0/30 | Avery70; Blair30 |
| Pacific / 202400015O | Casey40/0/40; Dana35/0/35; Ellis25/0/25 | Casey40; Dana35; Ellis25 |
| Straits / 202400016P | Fiona0/48/48; Jordan40/0/40; Gabriel0/12/12 | Fiona48; Jordan40 |
| Meridian / 202400017Q | Hannah0/30/30; Ian0/20/20; Iris30/0/30; Julian20/0/20 | Hannah30; Iris30 |

Straits: 60 x80 /100 =48; 60 x20 /100 =12.
Meridian: 50 x60 /100 =30; 50 x40 /100 =20.
No second production calculator or threshold comparison was introduced.

## Contract, code, architecture and security findings

No current material finding. The active source/contracts/decisions, assigned user text,
AGENTS.md and emitted dev_context references governed this review. D-062 confirms the
bounded inclusive threshold only. Broader legal/control/source-policy and real target
approval questions remain unresolved and are not needed for these fictional fixtures.

The data module is a bounded frozen-input definition used by the existing Mock connector
and PDF generator. Strict adapter normalization, canonical mapping, reconciliation,
document owner, single Decimal engine, case authorization and target ledger remain the
owners. The warm-only adapter subclass adds a completeness guard; it neither replaces
runtime composition nor calculates ownership. The current cache store retains exact
key/digest validation, insert-only create, update-only CAS and lossless timestamp encoding.
No schema/index/repository semantic, dependency, source-precedence or ADR change occurs.

The official Marketplace connector, Garden supplementary data, orchestrator, mappings,
authentication/CSRF/team/currentness boundaries and frontend cache owners are unchanged.
Only the local Mock banner text changes. No RP/hierarchy write, external HTTP call,
new endpoint, customer seed, threshold exception or autonomous approval is added.

Security review confirms fictional data without fabricated natural-person identifiers,
no credentials/private sponsor artefacts/new protected bytes, redacted CLI failures,
no dotenv loading by the utility, protected-database rejection before client construction
and no public seed endpoint. Existing auth remains exercised by the real-browser lane.
Secret scanner independently passed on tracked and nonignored task-owned paths.
Mongo URIs were never printed or persisted in this report or other evidence. The
reviewer did not connect to shared/protected databases or external providers.

## Independent execution and adversarial evidence

Runtime: provisioned project .venv Python with this worktree's apps/backend PYTHONPATH;
import location was explicitly checked. System Python's absent PDFium was not used as
passing evidence. Ordinary tests used existing runtime-only auth provisioning. The
independent browser harness reserved 8825/4225, separate from implementation ports.
Mongo used the task-owned server and fresh clm_p16 helper-generated database names.

| Fresh independent check | Result |
|---|---|
| pytest test_synthetic_company_pack.py + test_slice_f_document_pack.py + test_slice_b_registry_demo.py, no cacheprovider | 42 PASS; zero skips |
| pytest test_synthetic_company_pack_real_mongo.py + test_phase16_registry_cache_real_mongo.py, guarded physical environment, no cacheprovider | 11 PASS; zero skips; generated DB cleanup absence asserted |
| Independent combined collection of those five suites | 53 collected; agrees with executed 42+11 inventory |
| run_e2e.py --backend-port 8825 --frontend-port 4225 --registry-demo synthetic-cache --grep 'Synthetic company pack' | 4 PASS / one worker / real HTTP and guarded browser network; owned lifecycle exited successfully |
| Actual warm_synthetic_company_pack.py CLI twice in one newly generated safe DB | Four PROVIDER_FETCH followed by four CACHE_HIT; four exact COMPLETE snapshots unchanged; database absent after guarded cleanup |
| Standalone authenticated SG/ACRA route assertions | All four PASS |
| unittest contract discovery | 44 PASS |
| unittest test_phase_07_delivery_assets.py | 4 PASS |
| check_project_state, check_architecture, check_policy_authority, check_external_provider_readiness, check_tooling_config | All PASS |
| check_secrets | PASS |
| Raw payload hashes/aggregate, tracked git diff --check, every new/touched text file whitespace | PASS |
| PDF native text plus independent PDFium render inspection | All four matching/legible/unclipped; no ownership quantities |

Adverse paths actually exercised include incomplete acquisition rejected before cache
write, namespace mismatch, ordinary expiry/reacquisition, exact microsecond expiry after
restart, one physical CAS winner, invalid enabled-cache startup, deletion preserving
shared registry evidence, official Garden PARTIAL retaining original unsupported quantity
truth, and target mutation/reload/restart no-replay. Separate same-UEN cases reuse only
registry evidence; no submitted target result or ownership analysis is transplanted.

Reviewer setup attempts with a missing PYTHONPATH during collection, a Windows default
text encoding during hash inspection, and missing ordinary test bootstrap during an
ad hoc API probe were corrected before evidence collection. They are not counted as
passes or product defects. The corrected 53-item collection, UTF-8 hash check and all
four authenticated route probes succeeded. Existing Starlette/httpx deprecation remains.

## Broader execution evidence inspected

The implementation coordinator's finalized receipt belongs to the same unchanged frozen
payload. These broad runs were performed by the coordinator, not claimed as independent
reruns of this reviewer:

- Full backend: 2710 items; 2572 PASS; 138 explicitly SKIPPED; four existing warnings;
  exit0; 993.38 seconds. Conditional physical/OCR opt-in skips are not passes.
- Required physical harness: 20 suites /132 collected /132 PASS /zero skips, with guarded
  generated database cleanup. The reviewer separately executed the affected physical lane.
- Exact final frontend rerun: 47 files /560 tests PASS; typecheck PASS; build PASS.
- Backend Ruff and changed-script Ruff PASS; mypy127 source files PASS; pip check PASS.
- Physical-runner unit tests19 PASS; security/governance unit tests96 PASS.
- Four new browser tests and two inherited browser scenarios PASS; the inherited
  scenarios used their separate required lifecycles. Reviewer repeated all four new tests.

The 138 ordinary opt-in skips do not leave an assigned acceptance criterion unverified:
required physical evidence ran separately without skips; all new native-document tests
and four normal browser journeys executed. This review does not promote skipped OCR,
external sandbox/live, or unrelated runtime claims to passing. Pre-PR check intentionally
was not run on this uncommitted handoff, in accordance with the repository workflow.

## Document byte identities

| PDF | SHA256 |
|---|---|
| orion-synthetic-technologies-client.pdf | 87420d3b16467f157fafe16c59d05940dbfb2f7566eb34b1976193420bb07f38 |
| pacific-synthetic-ledger-client.pdf | ab228e462648f022b5bf4c1a8262d919b7975d33e0114eb11da41c150f3eb30d |
| straits-synthetic-holdings-client.pdf | ed24243f5b7ad02d51222975b9348f61cb9091c17882ca8082d32f4eb3b09597 |
| meridian-synthetic-infrastructure-client.pdf | b34c6894129f41e898ce54b04cc0a5927ae1d8f56b83be9e602348f49f1ba88c |

## Required fixes, limitations and readiness

Required fixes: **none**. Current acceptance blockers: **none**.

All four companies end at COMPLETED / SUBMISSION_CONFIRMED only after explicit local
Review & Send and verified Mock readback. Ownership candidates remain provisional.
LOCAL PROJECT SYNTHETIC MOCK is not official ACRA ownership, customer data, Sandbox/Live
interoperability, legal UBO determination, GoldTier-internal KYC/approval or regulatory approval.
Manual warm remains bounded and complete-only; it is not a multi-key transaction.
Distributed exactly-once, production retention, real-provider policy and later sponsor
questions remain outside this task. No normal owner database was populated; its explicit
safe operator command is documented. Automated disposable databases were removed.
The coordinator retains responsibility for task-container resource cleanup.

Inherited six locked dependency advisories, React SSR/act warnings, Starlette/httpx
deprecation and Vite bundle-size warning are disclosed unchanged. This fixture task
neither changes dependencies nor certifies general production/security readiness.

The candidate is ready for owner publication review of these exact bytes. A later
source/instruction/asset change invalidates this verdict for that scope. Separately
authorized integration/publication still requires current-main assessment and the clean
committed pre-PR gate. No next phase has been started or independently accepted here.
Real ACRA/GoldTier readiness and provider classifications are unchanged.

Change-surface disclosure: API/types unchanged; schema unchanged; connector fixture data
changed; product configuration unchanged; business rule/threshold unchanged; source/target
mapping unchanged; auth/security boundaries unchanged; architecture/canonical owners
unchanged; provider statuses unchanged. Runtime local Mock data availability changes;
manual owner-based warm tooling and the explicit SYNTHETIC MOCK UI label are added.

## Git status and reviewer write statement

HEAD and retained origin/main remain the exact base above. Before this report, nine
tracked modifications and eleven new payload files form the frozen20-path candidate;
implementation report and manifest are excluded new derivative files. Nothing is staged.
This assigned report is the reviewer's sole durable repository write. Final raw hash and
Git hygiene checks are repeated after writing it. No implementation fix, Git mutation,
commit, push, PR, merge, shared-database operation or next phase occurred in this review.
