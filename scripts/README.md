# Scripts

Repository tooling, grouped by purpose. Run scripts from the repository root, for example
`python scripts/dev_context.py`. Some scripts import each other as the `scripts`
package, so backend tests and CI set `PYTHONPATH` to the repository root.

The "Run by" column says what calls each script. **CI** means a job in
`.github/workflows/ci.yml`. **Manual** means a person runs it by hand, following the doc
named.

## Repository checks and task context

| Script | Purpose | Run by |
|---|---|---|
| `dev_context.py` | Prints the docs and sections to read for a change class | Manual, at task start (see `AGENTS.md`) |
| `pre_pr_check.py` | Read-only pull-request readiness gate | Manual, before a PR |
| `check_architecture.py` | Architecture guards over tracked source | CI, `pre_pr_check.py` |
| `check_project_state.py` | Checks `docs/PROJECT_STATE.md` facts against source | CI, `pre_pr_check.py` |
| `check_secrets.py` | Fails on secret-shaped content in the tree | CI |
| `check_policy_authority.py` | Validates the sponsor-policy authority registry | CI, `pre_pr_check.py` |
| `check_external_provider_readiness.py` | Validates the external-provider readiness registry | CI, `pre_pr_check.py` |
| `check_tooling_config.py` | Validates `.codex/config.toml` | CI, `pre_pr_check.py` |
| `validate_goldtier_examples.py` | Classifies sponsor GoldTier JSON examples against schemas | CI |
| `validate_external_provider_evidence.py` | Validates sanitized external-provider evidence | CI (via its test) |
| `validate_acra_marketplace_mock_evidence.py` | Validates `docs/evidence/acra_api_marketplace_mock_*.json` | Manual |
| `requirements-contract-validation.txt` | Pinned dependencies for the validators | CI |

## Test runners and harnesses

| Script | Purpose | Run by |
|---|---|---|
| `run_e2e.py` | Runs the Playwright browser suite with owned local processes | CI, `npm run e2e` |
| `e2e_backend_server.py` | Starts the backend for E2E runs with explicit test fixtures | `run_e2e.py` |
| `run_physical_mongo_tests.py` | Runs the opt-in real-MongoDB suites | CI |
| `mongo_test_safety.py` | Disposable database naming and cleanup for real-Mongo tests | Backend tests |
| `ocr_validation.Dockerfile` (+ `.dockerignore`) | Network-free image for local OCR acceptance | CI |
| `check_mongodb.py` | Connectivity-only MongoDB ping | Manual (`docs/development/DEVELOPMENT_TOOLING_RUNBOOK.md`) |
| `dev_preflight.py` | Reports local runtime composition and prerequisites | Manual (`README.md`) |
| `github_pr_ci.py` | Reports pull-request checks for one head SHA | Manual (`docs/development/DEVELOPMENT_TOOLING_RUNBOOK.md`) |

## Windows demo lifecycle

| Script | Purpose | Run by |
|---|---|---|
| `start_demo_windows.bat` | Starts the backend and frontend demo | Manual (`README.md`) |
| `stop_demo_windows.bat` | Stops only the launcher-owned processes | Manual |
| `reset_demo_windows.bat` | Verified stop, then fresh start | Manual |
| `demo_lifecycle.ps1` | Shared implementation behind the three `.bat` files | The `.bat` files; tested in CI |

## Demo data and seeding

| Script | Purpose | Run by |
|---|---|---|
| `seed_phase13_demo.py` | Seeds team portfolios through the application API | Manual (`docs/demo/DEMO_RUNBOOK.md`) |
| `validate_phase13_mongo_dashboard.py` | Checks a seeded disposable Mongo dashboard | Manual (`docs/demo/DEMO_RUNBOOK.md`) |
| `generate_admin_bootstrap_password_hashes.py` | Generates environment-only demo login hashes | Manual (`docs/demo/DEMO_RUNBOOK.md`) |
| `seed_zero_touch_happy_path_companies.py` | Seeds the four database-backed happy-path companies | Manual; backend tests |

## Generators for committed files

Each generator rebuilds files that are committed to the repository. Run one only when
its source data changes.

| Script | Output | Run by |
|---|---|---|
| `generate_blocker_rectification_guide.py` | `docs/demo/BLOCKER_RECTIFICATION_GUIDE.md` (a backend test checks it is up to date) | Manual |
| `generate_phase08_synthetic_pdfs.py` | PDFs in `apps/backend/tests/fixtures/uat/` | Manual; backend tests |
| `generate_garden_demo_pdfs.py` | Garden demo PDFs in `apps/backend/tests/fixtures/uat/` | Manual |
| `generate_slice_b_demo_pdfs.py` | Slice B demo PDFs in `apps/backend/tests/fixtures/uat/` | Manual |
| `generate_synthetic_company_pack.py` | Synthetic company PDFs in `apps/backend/tests/fixtures/uat/zero-touch-database/` | Manual |
| `generate_zero_touch_happy_path_documents.py` | Image-only OCR PDFs in `apps/backend/tests/fixtures/uat/zero-touch-database/` | Manual; backend tests |

## Offline test fixtures

Synthetic, offline provider data and compositions. They are imported only by
`e2e_backend_server.py` and backend tests, never by normal application startup.

- **Registry data:**
  - `garden_protocol_fixture.py`
  - `slice_b_registry_fixture.py`
  - `synthetic_company_pack.py`
  - `synthetic_company_pack_test_transport.py`
  - `zero_touch_happy_path_fixtures.py`
- **Recovery and target scenarios:**
  - `slice_c_recovery_fixture.py`
  - `slice_f_target_fixture.py`
  - `s3_sandbox_fixture.py`
- **Browser scenarios:**
  - `sponsor_demo_browser_fixture.py`
  - `zero_touch_classification_browser_fixture.py`

## Provider smoke and acceptance (opt-in)

These may need provider credentials from the process environment. CI never runs them
against a provider. See
`docs/integration/CONFIGURATION_REFERENCE.md` before using them.

| Script | Purpose |
|---|---|
| `acra_sandbox_smoke.py` | Manual ACRA sandbox smoke check with credential-safe output |
| `acra_marketplace_mock_smoke.py` | Bounded smoke test of the official ACRA API Marketplace Mock |
| `run_s3_sandbox_acceptance.py` | One synthetic GoldTier XPI Sandbox acceptance run |

## Performance and evaluation

| Script | Purpose | Run by |
|---|---|---|
| `performance_optimization.py` | Offline performance measurement. Backend tests also import its `application` helper | Manual; backend tests |
| `requirements-performance-optimization.txt` | Optional `psutil` and `yappi` for `performance_optimization.py` | Manual |
| `profile_garden_local.py` | Profiles the Garden flow in memory, without servers | Manual (`docs/development/GARDEN_IMPLEMENTATION_REPORT.md`) |
| `evaluate_onboarding_intelligence.py` | Prints the synthetic evaluation for the advisory intelligence | Manual (`docs/models/*_MODEL_CARD.md`) |
| `recoverable_onboarding_smoke_report.py` | Serializes onboarding smoke outcomes | Backend tests |
