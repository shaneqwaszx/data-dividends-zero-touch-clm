# D-104 AI Assistant data access policy and provider-neutral synthetic eligibility

Date: 2026-10-30. Stage 1 (bounded implementation) of the owner's assignments "Provider-Independent
Data Access & Synthetic Mode" and "D-104 - Owner Direction: Complete Provider-Neutral Synthetic
Eligibility" (A1 authorised). Implementer evidence only; not an independent Quality Gate. The first
QG (`D104_QUALITY_GATE.md`, PASS) covers only the earlier candidate `b6440a5f…`.

## Work boundary

| Item | Value |
| --- | --- |
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\assistant-data-access-policy-20261030` |
| Branch | `feat/assistant-data-access-policy` (no upstream; nothing committed or pushed) |
| `BASE_SHA` / `origin/main` | `0c6a6325e8ad9bdc650c72824124a4d0f2fc863f` (re-fetched 2026-10-30, unchanged) |
| Change classes | BACKEND_API, AUTH_RBAC_SECURITY, PERSISTENCE, EXTERNAL_PROVIDER, FRONTEND_UI, DOCS_ONLY |
| Running service, Claude activation, key, ledgers, model-admin database | Not touched (tests use temporary directories) |
| Evidence class | Mock / Local offline only. No network, no paid call, no Live claim |

## 1. Architecture

```
case retrieval (RM session) → shared prompt → data access policy → shared D-095 eligibility
  (or D-094 fixed fixture) + single-use ticket → selected model (provider's own readiness,
  ledger, preflight, per-call re-admission) → shared exact-line output guard → RM chat
```

- **Shared D-095 eligibility:** `synthetic_eligibility.check` / `approve` / `admitted`
  (unchanged), plus `synthetic_eligibility.shared_mode`. `shared_mode` is the D-095 flag, the
  D-094/D-091/D-092 decisions, the model switched on, a loopback CLM backend and local origins.
- **GPT-OSS:** `synthetic_eligibility.mode` = `shared_mode` + `remote_test.readiness` (endpoint,
  reasoning settings, OpenRouter attestations). Unchanged in effect; `remote_test.py` is untouched.
- **Claude:** `ClaudeTestModel.development_mode` = `shared_mode`. The chat uses it, and so does the
  adapter's per-call re-check. `anthropic_runtime.readiness` (D-099 decision, four attestations,
  workspace, limits, ledger path) is still checked before every call, followed by the preflight,
  ledger and in-band verification.
- **Chat:** `main.remote_gate` asks the active model for `development_mode` (a model without one
  keeps GPT-OSS's mode).

## 2. Root causes (before A1)

- **Coupling:** `synthetic_eligibility.mode` required `remote_test.readiness`, and Claude called it.
  With the OpenRouter attestations unset, Claude was limited to D-094.
- **`v1`:** the backend event "…policy catalogue v1." enters the CASE FACTS system message, and the
  D-094 word screen refuses `v1`. D-094 is deliberately unchanged and still refuses it (test). This
  was an admission refusal, not model reasoning; no model was called.

## 3. HR checkbox behaviour

| Class | Shown | Server |
| --- | --- | --- |
| OpenRouter, Anthropic | Checked, locked | Own code gate; policy not read; `restrict_external:false` → 409 `EXTERNAL_DATA_POLICY_LOCKED` |
| `it_configured` (any non-loopback endpoint, including `localhost`) | Checked, locked | Always wrapped (`SyntheticOnlyModel`, IT notices), with or without model management; only a model injected by tests or the evaluation harness is exempt |
| `local_internal` (literal loopback) | Unchecked by default | Restricted when HR checks it or the policy is unreadable; widening needs `confirm_widen` |
| No model management | Shown as `not_managed` | A loopback model behaves as before; a non-loopback one is still restricted; `PUT` → 409 `MODEL_MANAGEMENT_OFF` |

## 4. QG findings and resolutions

| Finding | Resolution |
| --- | --- |
| L1 generic refusal notice | `main._REMOTE_REFUSALS` includes `data_access.REFUSAL_NOTICES`; a restricted local or IT model refusal shows its own notice and reason (telemetry `remote_boundary`) |
| L2 Claude tiles need GPT-OSS view | Overview reads `overview.budget.claude` regardless of GPT-OSS `configured` |
| L3 "Too many spending changes" | Separate count and code `DATA_ACCESS_RATE_LIMITED` with its own message |
| L4 audit written separately | `ModelAdminStore.set_data_access_policy` writes the policy and the `applied` audit row in one `BEGIN IMMEDIATE` transaction; an audit failure rolls the change back (test) |
| L5 inspection-only paths | Tests: Claude active with local restricted; `/brief` warm-up never reaches a restricted model; no model management unchanged; a 4-thread CAS race applies once |

### Re-QG (`D104_REQG.md`, FAIL on `68848ab2…`) and remediation

| Finding | Resolution |
| --- | --- |
| M1: a non-loopback model was unrestricted without model management, while the page said it was locked | Option (a), as the owner's "only trusted local endpoints are internal" direction requires. `ModelSelector.restrict_remote` is true unless the model was injected; `open_selector` passes it. The view reports the enforced state. Test `test_without_model_management_a_non_loopback_model_is_still_restricted`; a mutation that turns the flag off makes it fail |
| L1: Claude's catalogue scope used the OpenRouter-coupled mode | `model_catalog.py` (not a basis file) uses `shared_mode`; test added |
| L2: "not on this machine" wording | Changed to "not on a literal loopback address" in notices, labels and docs |

## 5. Files (14 tracked + 3 new)

`apps/assistant/ai_assistant/`:
- `synthetic_eligibility.py`: `shared_mode`.
- `anthropic_runtime.py`: `development_mode`.
- `main.py`: per-model mode, refusal notices.
- `data_access.py` (new).
- `model_admin.py`: selector wrapping, routes, L3, L4.
- `model_admin_store.py`: table, atomic audit.
- `model_qualification.py`: `data_access.py` added to `BASIS_FILES`.
- `model_catalog.py`: Claude scope on `shared_mode` (re-QG L1).

Tests: `apps/assistant/tests/test_data_access_policy.py` (new, 49 tests).

Frontend:
- `apps/frontend/src/aiAssistant.ts`
- `pages/AiModelManagement.tsx`
- `pages/aiModels/ConsoleShell.tsx`
- `pages/AiModelManagement.test.tsx` (6 new tests)

Docs:
- `docs/decisions/DECISION_LOG.md` (D-095 and D-099 amendments, D-104)
- `docs/integration/AI_MODEL_CONFIGURATION.md` §14
- `docs/PROJECT_STATE.md`
- this report

Change statement:
- **API:** additive. Two routes and an overview field.
- **Schema:** additive. One SQLite table in the model state database.
- **Configuration:** no new settings.
- **Unchanged:** connectors, mappings and business rules.
- **Auth and security:** a new HR-only route; external restriction unchanged; non-loopback models
  now locked.
- **Provider status:** unchanged.
- **Runtime behaviour:**
  - Claude's D-095 mode no longer needs OpenRouter readiness.
  - Restricted and IT-configured models are gated.
  - The qualification basis changes (section 7).

## 6. Evidence

These checks ran on the final tree (Windows host, repo `.venv`, `PYTHONPATH` pinned to the worktree;
frontend through a `node_modules` junction to the primary checkout's install).

| Check | Result |
| --- | --- |
| `tests/test_data_access_policy.py` | 49 passed (after the re-QG remediation) |
| Full assistant suite (`tests/`, final tree) | 2895 passed, 14 failed (the same 4 files as on the pre-remediation tree, 2893 passed). All 14 are `OSError: [Errno 24] Too many open files`, the known Windows limitation recorded in D-102 and seen identically on main. Rerun alone (`test_model_factory`, `test_phase_b_live`, `test_required_p2`, `test_streaming_resources`): 289 passed. Not a clean PASS |
| Mutation checks | Claude's mode back on `mode` (the old coupling) → the A1 tests fail; `shared_mode` without its interlocks → the interlock tests fail; earlier mutants (no wrapping, no wrapper admission) also fail |
| `ruff check`, `ruff format --check`, `mypy ai_assistant` (46 files) | Pass |
| `scripts/build_synthetic_boundary.py --check` | Current (file unchanged) |
| Frontend `tsc -b`; `vitest run` (69 files) | Pass; 1249 tests (6 new) |
| `git diff --check`, untracked whitespace, EOL churn (`--stat` equals `--ignore-cr-at-eol`) | Clean |
| Not run | Backend suite (no backend change); E2E (needs disposable Mongo and Tesseract, outside this scope); `pre_pr_check.py` (needs an authorised commit); hosted CI |

Part 4 coverage, each offline with zero provider messages on every refusal:
1. Garden with `v1` passes D-095.
2. Claude admits it with no OpenRouter attestations or endpoint, in a unit test and through the RM
   chat journey.
3. GPT-OSS's mode is still off without each OpenRouter condition.
4. The same tampered prompt is refused for both providers.
5. Tampered documents, non-approved companies, unverified identifiers, ungrounded values and
   unauthorised users (401 or 404) are all refused.
6. Guardrails: the existing guardrail and adversarial suites pass in the full run.
7. Activation, ledger and spending tests pass.
8. Policy authentication, audit and bypass tests pass.

## 7. Qualification basis and activation consequences

`qualification_basis()` moves from `65f22e46c509b2f4e0540f8412e9940e5c1d9c49c85e6eb28c94f0e0b1479328`
(main `0c6a632`) to `598cfe14753d028898a7b727741291b282259dc694f897bedf5fdc0b41f6f3ce` (this tree).
The re-QG remediation changed `data_access.py` again, giving this final value. The changed basis files are `main.py`, `anthropic_runtime.py` and `synthetic_eligibility.py`, and
`data_access.py` was added. `synthetic_boundary.json` is unchanged and current.

What happens when this code runs:
- Every existing qualification is out of date, including Claude Balanced `c5c76fda…` on
  `65f22e46c509`.
- The stored Claude activation becomes *AI unavailable* at the service's next start (D-098 R6,
  D-099 P-6).
- Nothing is marked qualified, and no history is changed.
- A new, separately approved paid qualification and activation is needed.

The running service was not restarted or changed.

## 8. Readiness

The candidate is ready for a fresh independent QG. It is not ready for commit: the owner's
authorisation is required. `pre_pr_check.py` needs a clean committed state, so it has not been run
and is blocked on that authorisation. PR publication needs a commit, the pre-PR PASS and owner
authorisation.
