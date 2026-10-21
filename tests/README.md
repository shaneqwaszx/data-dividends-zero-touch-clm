# Repository-level Tests

This folder tests repository tooling and governance: the scripts in `scripts/`,
delivery documents, and cross-cutting contracts. Application tests live with each app:

| Suite | Location | Runner |
|---|---|---|
| Backend unit and API tests | `apps/backend/tests/` | `python -m pytest`, run from `apps/backend` |
| Frontend unit tests | `apps/frontend/src/**/*.test.ts(x)` | `npm test` (Vitest) |
| Browser end-to-end tests | `apps/frontend/e2e/*.e2e.ts` | `npm run e2e` (Playwright via `scripts/run_e2e.py`) |
| AI assistant tests | `apps/assistant/tests/` | `python -m pytest`, run from `apps/assistant` |

## Run in CI

| Tests | CI job |
|---|---|
| `contract/test_phase_0*_contract.py` | `backend` |
| `test_phase_07_delivery_assets.py` | `backend` |
| `test_demo_lifecycle_windows.py` | `demo-lifecycle-windows` |
| `test_check_secrets.py`, `test_pre_pr_check.py`, `test_dev_context.py`, `test_check_project_state.py`, `test_check_architecture.py`, `test_check_policy_authority.py`, `test_check_external_provider_readiness.py`, `test_claude_skill_pointers.py`, `test_validate_external_provider_evidence.py`, `test_validate_goldtier_examples.py` | `security` |

## Not run in CI

No CI job runs these tests. Run them by hand when you change the script they cover.

| Test | Covers | Style |
|---|---|---|
| `test_check_tooling_config.py` | `scripts/check_tooling_config.py` | unittest |
| `test_github_pr_ci.py` | `scripts/github_pr_ci.py` | unittest |
| `test_run_e2e.py` | `scripts/run_e2e.py` | unittest |
| `test_run_physical_mongo_tests.py` | `scripts/run_physical_mongo_tests.py` | unittest |
| `test_contract_test_isolation.py` | Contract-test imports ignore local `.env`, Mongo and provider settings | unittest |
| `test_performance_optimization.py` | `scripts/performance_optimization.py` | unittest |
| `test_validate_acra_marketplace_mock_evidence.py` | `scripts/validate_acra_marketplace_mock_evidence.py` | unittest |
| `test_dev_preflight.py` | `scripts/dev_preflight.py` | pytest |
| `test_slice_b_e2e_fixture_routing.py` | `scripts/slice_b_registry_fixture.py` routing | pytest |
| `test_slice_c_e2e_fixture_routing.py` | `scripts/slice_c_recovery_fixture.py` routing | pytest |
| `test_slice_f_fixture_routing.py` | `scripts/slice_f_target_fixture.py` routing | pytest |

## Running tests

From the repository root, with the backend installed (`pip install -e "apps/backend[dev]"`):

```bash
python -m unittest discover -s tests -p "test_dev_context.py"   # one unittest file
python -m unittest discover -s tests/contract -p "test_*.py"     # contract tests
python -m pytest tests/test_dev_preflight.py                     # one pytest file
```

`contract/phase13_contract_credentials.py` is a shared helper for the contract tests,
not a test.
