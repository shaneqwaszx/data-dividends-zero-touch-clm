# AI Assistant D-094 in-app OpenRouter test mode - Pre-PR checklist

Date: 2026-10-28. Stage 4 (publication) record for branch
`feat/assistant-openrouter-local-test-20261027`. All results below were observed in this
session unless marked otherwise.

## Baseline and branch

| Item | Observed |
| --- | --- |
| Feature branch | `feat/assistant-openrouter-local-test-20261027` (not `main`) |
| Initial `BASE_SHA` | `c36b8aff5213037d9ed0710e69f8b9afc7c8c614` |
| `git fetch origin main` before the drift check | run |
| Latest `origin/main` | `c36b8aff5213037d9ed0710e69f8b9afc7c8c614` (unchanged) |
| `git log HEAD..origin/main` | empty (ahead 1, behind 0); no merge needed |
| Implementation commit | `71e4654c34d2c3486e39938df4eab5dd01fd10ac`, tree `468a8dfe9d6b62b9e67bb24fb86e025c6d9a380f` |

## Reviewed identity

- Independent QG R5 verdict **PASS** (`AI_ASSISTANT_D094_IN_APP_OPENROUTER_QUALITY_GATE_R5.md`)
  on CONTENT ID `15dce753ec7062237a3bca50ac5b46758565c33c238664b58bde9fcb27ed1a45`
  (HEAD `c36b8af`, tracked diff sha256 `fcd4fd55…`, plus six new product files).
- The same script recomputed the same CONTENT ID on the working tree immediately before the
  implementation commit. The commit staged exactly those 25 paths by name. After the commit
  `git status --short` showed only the five untracked QG reports.
- This report and the five QG reports (R1 to R5) are added in a separate report-only commit
  under `.ai-pipeline/reports/`; no product file changes after `71e4654`.

## Conflict and delta audit

| Check | Result |
| --- | --- |
| `git status --short` at check time | empty (QG reports parked outside the tree for the run, then restored) |
| `git diff --name-only --diff-filter=U` | empty |
| `git diff --check origin/main...HEAD` | clean |
| Whitespace of the new Markdown reports (trailing spaces or tabs) | 0 lines in each file |
| Dependency or lockfile changes | none |
| CI workflow changes | none; existing jobs unchanged |
| `apps/backend` changes | none |

Every changed path is classified:

- INTENDED: `ai_assistant/{remote_test,remote_checks,synthetic_boundary}.py`,
  `synthetic_boundary.json`, `config.py`, `main.py`, `model_admin.py`, `model_catalog.py`,
  `model_qualification.py`, `telemetry.py`, `clm_client.py`, `assistant_eval/qualification.py`,
  `apps/frontend/src/pages/AiModelManagement.tsx`.
- SUPPORTING:
  - Moves into `remote_checks.py`: `assistant_eval/live.py` (re-export) and
    `scripts/evaluate_answers.py` (delegation).
  - Generator: `scripts/build_synthetic_boundary.py`.
  - Tests: `tests/test_remote_test.py`, plus allowlist updates in `test_phase_b_live.py`
    and `test_openrouter_adapter.py`, and `AiModelManagement.test.tsx`.
  - Documentation: `.env.example`, `apps/assistant/README.md`,
    `docs/integration/AI_MODEL_CONFIGURATION.md`, `docs/decisions/DECISION_LOG.md` and
    `docs/PROJECT_STATE.md` (CRLF line endings kept).
- UNEXPECTED: none.

## Contracts and behaviour (disclosed)

| Area | Changed? |
| --- | --- |
| API routes or models | No new route. Existing model-management and chat responses may carry new closed codes: the fallback reason `remote_boundary` and the D-094 reason codes. |
| Shared frontend types | No |
| Persistence schema | No |
| Connector interfaces | No; the OpenRouter adapter is unchanged |
| Configuration names | Yes: six new `AI_ASSISTANT_LOCAL_API_TEST_*` settings, all off or inert by default (pre-PR warning: `config.py` changed) |
| Business rules or mappings | No |
| Auth/security | Yes, additively. There is a new server-side synthetic boundary and readiness gate; HR/RM separation and case access are unchanged. |
| Provider status | No change: D-091 remains dormant by default, D-092 PROPOSED, D-093 accepted local-only. D-094 is recorded as an owner-directed local synthetic test mode. |
| Runtime behaviour | Unchanged unless `AI_ASSISTANT_LOCAL_API_TEST_DECISION=D-094` and every readiness condition holds |

## Verification

| Evidence | Content | Result |
| --- | --- | --- |
| Full assistant suite | R5 reviewer, CONTENT ID `15dce753…` | 2,442 tests, 14 failed, all `OSError: [Errno 24] Too many open files` |
| The 4 Errno 24 files in isolation | same | 288 passed |
| Errno 24 baseline on main `c36b8af` | detached checkout, this session | see "Errno 24 baseline" below |
| Focused remote + assistant + model-management tests | same | 133 passed (R5) |
| ruff, ruff format, mypy | same | clean (R5) |
| `build_synthetic_boundary.py --check` | same | current |
| Guardrail protections | same | 154 unsafe-sentence and 46 adversarial knowledge-filter cases unchanged; guardrails.py identical to main |
| Frontend vitest + tsc | frontend files unchanged since R3 | 65 files, 1,123 tests passed; tsc clean (implementer, reused by R4 and R5) |
| Real-stack browser E2E, mocked OpenRouter | implementer; R4-1 re-checked through the API afterwards | see the PR description |
| `python scripts/pre_pr_check.py` | `71e4654`, clean tree | **PASS** (0 unsafe conditions, 1 warning: `config.py` changed) |
| Six repository checkers (inside pre-PR) | `71e4654` | PASS |

### Errno 24 baseline

The full assistant suite was run on a detached checkout of `main` `c36b8af` in this session,
with the same interpreter and the same pytest options:

- `main`: 2,375 tests, 14 failed, all `OSError: [Errno 24] Too many open files`.
- Candidate (R5 run): 2,442 tests (67 new), 14 failed, all Errno 24.
- The two sets of failing test IDs are **identical**:
  - `test_model_factory::test_the_suite_guard_blocks_remote_connections`;
  - `test_phase_b_live::test_marker_is_not_an_offline_transport`;
  - 5 `test_required_p2::test_real_http_sse_framing` cases;
  - 7 `test_streaming_resources` loopback/chunked cases.
- None of the failing IDs is new, and no failure is something other than Errno 24.
  Those 4 files pass in isolation on the candidate (288 passed).

## Not run or not available

- **Hosted CI: NOT RUN / BILLING BLOCKED.** GitHub Actions is blocked by the account spending
  restriction until 1 November 2026. It is not reported as passing. The owner holds the
  manual-CI exception, and the local evidence above substitutes for it.
- **Paid OpenRouter smoke test: NOT RUN.** It needs new explicit owner authorisation (proposal
  in the PR description). No paid call was made for D-094.
- The backend suite was not rerun: `apps/backend` is unchanged from `c36b8af`.

## Handoff

The PR targets `main` as a Draft, because the paid validation and the owner's merge approval
are outstanding. The repository owner merges.
