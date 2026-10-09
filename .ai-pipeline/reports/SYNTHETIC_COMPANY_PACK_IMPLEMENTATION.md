# Synthetic company pack - implementation candidate

Outcome: implementation and required scoped verification complete; the independent verdict belongs exclusively to SYNTHETIC_COMPANY_PACK_QUALITY_GATE.md.

## Task identity and boundary

- Assignment: four complete Orion/Pacific/Straits/Meridian SYNTHETIC MOCK companies.
- Branch: feat/synthetic-happy-path-company-pack.
- Worktree: C:/Users/shane/.codex-clean2/worktrees/synthetic-happy-path-company-pack/data-dividends-zero-touch-clm.
- BASE_SHA / HEAD / fetched origin/main: 21124498cb1b8fd47b1406534d6fd9c24af0e2ea.
- Prerequisite: Project CI37918635850, same head SHA, seven completed SUCCESS jobs, E2E completed2026-10-09T10:54:56Z. Fetch/gate preceded worktree, branch and all file edits.
- Primary checkout's unrelated untracked artifacts/evaluation/outputs preserved.
- Classes: BACKEND_DOMAIN, PERSISTENCE (warm evidence only), CI_TOOLING, FRONTEND_UI.
- Existing owners: MockAcraConnector -> strict DTO/ACRA adapter/mapper -> RegistryAcquisitionCoordinator -> snapshot repository; document parser; single Decimal engine; target ledger.
- No new owner/boundary/dependency/schema/threshold/mapping/authorization. No ADR required for fixture additions.
- Non-goals: official Marketplace/Garden changes, startup/target seed, new arithmetic, autonomous approval or external HTTP.

## Capability and resources

Current session: shell, managed-worktree lifecycle, collaboration independent-review tools.
Python3.12.10 / Node22.23.3 / npm10.9.9; Docker29.8.1. Exact frontend lockfile installed with npm ci.
System Python lacks PDFium: inherited PDF acceptance also failed there. Tests use the provisioned project .venv runtime with worktree-local imports; no product fix was needed.
Configured Playwright owned processes use task-reserved8795/4195 ports.
Task-owned Mongo7 container clm-synthetic-pack-20261009 uses isolated loopback port27149.
Physical tests generate allowlisted clm_p16 names and verify cleanup absence. No dotenv read or shared DB connection.
No commit/push/PR/merge authorized. Managed worktree is preserved for owner review.

## Delta and acceptance

Four fixture graphs extend Mock ACRA only. Intermediate legal entities use the existing fictional SYN-<party ID> convention to bind nested percentage evidence; these are synthetic identifiers, never asserted UENs. Natural people have no fabricated personal identifiers. Distinct fictional directors are separate from ownership facts.
Native-text PDF fields match registry identity exactly; no ownership quantities or target classification labels are in these PDFs.
Explicit warm utility uses the current adapter/coordinator/repository with MOCK_ACRA_SYNTHETIC_V1, complete-only acquisition guard, existing exact-key/CAS/freshness semantics. No startup hook or direct BSON exists.
User-selected Company - Private/Corporate is retained. Review & Send precedes all mutations; ledger-owned Mock Search/recheck/Shell/Policy/Amend/exact-ID readback and no replay remain.

## Verification

Focused new/registry/document tests:38 PASS (before extending the existing pack test list).
Focused physical cache/new tests:11 PASS, no skips, generated DB cleanup verified.
Frontend typecheck/build PASS;560 tests PASS. Existing React SSR/act and chunk-size warnings retained.
All four PDFs rendered and visually inspected: readable four identity fields, explicit synthetic label, no clipping.
Four new browser companies PASS together; two inherited browser scenarios PASS in their own isolated lifecycles (six passing tests total). Each retains guarded browser network policy and no reload mutations.
Full guarded physical runner:20 suites/132 collected/132 PASS/zero failures/errors/skips. Cleanup absence is asserted by the generated-database fixtures.
Full backend Ruff PASS; mypy127source files PASS; changed-script Ruff PASS; pip check PASS.
Contracts44PASS; exact asset/hash checks4PASS; physical-runner unit tests19PASS; security/governance unit tests96PASS.
check_project_state/check_architecture/check_tooling_config/check_policy_authority/check_external_provider_readiness/check_secrets all PASS.
Tracked git diff --check and explicit new-text whitespace PASS.
Full backend:2710items;2572PASS;138conditional skips;4existing warnings;993.38s;exit0. Ordinary opt-in skips are reported as skipped, never passing. Required physical cache coverage separately executed132tests with zero skips; new native-document acceptance has zero skips. The independent verdict is exclusively recorded in SYNTHETIC_COMPANY_PACK_QUALITY_GATE.md.

Initial validation failures were diagnosed, not counted as PASS: test connector injection/API-projection assertions were corrected; the two nested graphs needed existing SYN-* Mock legal-entity identifiers; the new browser counter needed its per-test operation delta. A combined inherited browser invocation violated those existing scenarios' required isolated lifecycles; final isolated executions passed. An anchored grep selected no tests; corrected actual selectors passed. A compact frontend log wrapper hit a Windows output-encoding error after typecheck/560tests/build had all returned success; the checks themselves passed. CR-at-EOL findings on newly touched lines were fixed without changing unrelated baseline bytes.

npm ci reported six inherited locked dependency advisories (one moderate, three high, two critical). No dependency/lockfile change is part of this task. Existing React SSR/act, Starlette/httpx deprecation and Vite bundle-size warnings remain. Conditional physical/OCR skips in the ordinary backend run will be stated separately from required physical/native-document evidence.

## Authority and limitations

LOCAL PROJECT SYNTHETIC MOCK, not official Marketplace ownership, customer data, Sandbox/Live ACRA or legal UBO determinations.
D-062 inclusive >=25% behavior and unresolved broader sponsor questions remain unchanged.
Database warm is manual into a dedicated allowlisted demo/test database. Application start never seeds.
No normal/owner database is populated in this run. Explicit operator command is in docs/demo/SYNTHETIC_COMPANY_PACK.md.
Next action: finish required verification, freeze content, fresh independent Quality Gate; stop for owner publication review.

## Frozen implementation receipt

Raw-content aggregate SHA256: `71349034c050402494ef6d5937aebc5cfbfb21d745094356820718254aa13d02`; 20 frozen implementation/instruction/asset paths. Formula and each raw hash are in SYNTHETIC_COMPANY_PACK_MANIFEST.json. Implementation/check evidence report, manifest and independent report are derivative exclusions; the reviewer checks the finalized evidence separately.

| Exact path | Classification |
|---|---|
| apps/backend/app/connectors/mock_acra.py | SUPPORTING |
| apps/backend/app/connectors/synthetic_company_pack.py | INTENDED |
| apps/backend/tests/fixtures/uat/README.md | SUPPORTING |
| apps/backend/tests/fixtures/uat/meridian-synthetic-infrastructure-client.pdf | INTENDED |
| apps/backend/tests/fixtures/uat/orion-synthetic-technologies-client.pdf | INTENDED |
| apps/backend/tests/fixtures/uat/pacific-synthetic-ledger-client.pdf | INTENDED |
| apps/backend/tests/fixtures/uat/straits-synthetic-holdings-client.pdf | INTENDED |
| apps/backend/tests/test_slice_f_document_pack.py | SUPPORTING |
| apps/backend/tests/test_synthetic_company_pack.py | INTENDED |
| apps/backend/tests/test_synthetic_company_pack_real_mongo.py | INTENDED |
| apps/frontend/e2e/slice-b-registry-demo.e2e.ts | SUPPORTING |
| apps/frontend/e2e/synthetic-company-pack.e2e.ts | INTENDED |
| apps/frontend/src/App.tsx | SUPPORTING |
| docs/ARCHITECTURE.md | SUPPORTING |
| docs/PROJECT_STATE.md | SUPPORTING |
| docs/demo/SYNTHETIC_COMPANY_PACK.md | INTENDED |
| scripts/generate_synthetic_company_pack.py | INTENDED |
| scripts/run_physical_mongo_tests.py | SUPPORTING |
| scripts/warm_synthetic_company_pack.py | INTENDED |
| tests/test_phase_07_delivery_assets.py | SUPPORTING |

Derivative files: .ai-pipeline/reports/SYNTHETIC_COMPANY_PACK_IMPLEMENTATION.md,
.ai-pipeline/reports/SYNTHETIC_COMPANY_PACK_MANIFEST.json,
.ai-pipeline/reports/SYNTHETIC_COMPANY_PACK_QUALITY_GATE.md (independent reviewer only).

Change-surface disclosure: API/public types unchanged; internal SyntheticCompany fixture descriptor added; schema unchanged; connector fixture data changed;
product configuration unchanged; business rule/threshold unchanged; source/target mapping unchanged;
auth/security boundaries unchanged; architecture/canonical owners unchanged; provider statuses unchanged;
runtime Mock data availability changed; manual operator warm tooling and UI synthetic label added.

## Independently executed evidence (verdict recorded separately)

Fresh reviewer execution:42focused API/document/inherited-registry tests PASS;
11physical new/cache tests PASS with cleanup;4new browser journeys PASS;
actual warm CLI4PROVIDER_FETCH then4CACHE_HIT, exact original snapshots retained and
generated database removed; explicit four-company SG/ACRA route assertions PASS;
44contract/4asset tests and secret/governance checks PASS;four PDF visual inspections PASS.
The reviewer independently observed the prerequisite seven-job CI receipt and rehashed
the unchanged frozen20-path payload. These facts are not an implementer-issued verdict.

Final repo state is intentionally uncommitted, with only assigned task files modified/new
in this worktree. HEAD and origin/main remain the starting SHA. No staging/commit/push/PR,
merge, protected/shared DB access, next phase or automatic startup seed occurred.
Closeout: task-created Mongo container was identity-verified and removed after independent tests/gate. Generated test databases had already been removed with absence verification.
The managed worktree and branch remain for owner review. Publication requires a separately
authorized run with unchanged exact-PASS content and the clean committed pre-PR workflow;
pre_pr_check.py was deliberately not run on this uncommitted implementation handoff.

Final exact-byte frontend check: typecheck PASS;47files/560tests PASS;build PASS after the newline-only hygiene correction.

Independent outcome: PASS, P0/P1/P2=0/0/0, as recorded only by the fresh reviewer in SYNTHETIC_COMPANY_PACK_QUALITY_GATE.md. Stop for owner publication review.
