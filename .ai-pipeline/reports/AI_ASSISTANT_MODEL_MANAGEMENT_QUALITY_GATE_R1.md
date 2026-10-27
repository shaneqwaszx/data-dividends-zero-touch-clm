# AI Assistant Model Management (D-093) - Independent Quality Gate, Re-gate R1

Stage 3 independent re-check. The reviewer did not author or remediate the reviewed content
and did not author the previous gate. Only this report was written; no fix, stage, commit,
stash, reset or push was made.

## 1. Outcome

**PASS.**

- Both required fixes from the previous gate are fixed and verified: F-1 (refused callers
  could evict the audit history) and F-2 (blank line at the end of a file).
- The optional fixes F-3, F-4, F-5, F-6 and F-8 are also fixed and verified, as is the extra
  fix (a refusal code with no fixed message no longer raises `KeyError`, which used to give
  HTTP 500).
- F-7 (a qualification process can outlive the service) is still **open**. It is bounded
  and fails closed, so I accept it as a Low residual (section 4).
- Two new Low findings and three informational notes are reported. None is required for
  this gate.

This verdict covers only the frozen content in section 2.

## 2. Reviewed identity

| Item | Value |
| --- | --- |
| Worktree | `C:/Users/shane/Desktop/claude-worktrees/assistant-model-management-20261027` |
| Branch | `feat/assistant-model-management-20261027` |
| Reviewed HEAD | `ffeeddfcab0e18073cbc0bb25bba1a02540a268a` |
| Reviewed tree | `6fac2b5647a85deefa148e1cb822868e4b354197` |
| Base = `origin/main` | `23c45a7a4ca18cc3da751416d30365beaba2114f` (unchanged; the candidate is on latest main) |
| Previous gate | `5341dcf` (tree `de53c2c`), FAIL; report committed at `.ai-pipeline/reports/AI_ASSISTANT_MODEL_MANAGEMENT_QUALITY_GATE.md` |
| Primary scope | `git diff 5341dcf ffeeddf`: 9 files, +460/-47. These are `model_admin.py`, `model_admin_store.py`, `model_qualification.py`, `test_model_management.py`, `test_model_config_capability.py`, `PROJECT_STATE.md`, `DECISION_LOG.md`, `AI_MODEL_CONFIGURATION.md` and the committed previous gate report |
| Full candidate | `git diff 23c45a7 ffeeddf`: 34 files, +5330/-44 |
| Worktree state | Clean (no tracked or untracked changes) at the start of the review. HEAD, tree and `origin/main` checked again, unchanged, before this report was written |

## 3. Status of prior findings

| Finding | Status | Evidence |
| --- | --- | --- |
| **F-1** Medium: refused callers evict the audit history | **Fixed** | See details below the table |
| **F-2** Low: blank line at EOF | **Fixed** | See details below the table |
| **F-3** Low: stale threshold shorter than one legal call | **Fixed** | See details below the table |
| **F-4** Low: failed-activation undo went to the baseline, audited only as a refusal | **Fixed** | See details below the table |
| **F-5** Low: supervisor had no exception handling | **Fixed** | See details below the table |
| **F-6** Low: some 404 refusals by an administrator not audited | **Fixed** | See details below the table |
| **F-7** Low: the qualification process can outlive the service | **Open, accepted as a bounded Low residual** | See section 4 |
| **F-8** Low: qualification basis omitted files that shape the prompt | **Fixed** | See details below the table |
| Extra fix: refusal codes with no fixed message returned 500 | **Fixed** | See details below the table |

**F-1 (fixed).**

- **What changed:** retention is now per class (`model_admin_store.py:255-273`).
  - Rows with outcome `applied` or `reverted` (model changes) are never pruned.
  - `ACCESS_REFUSED` rows keep their newest `MAX_REFUSED_EVENTS = 1000`.
  - All other rows keep their newest `MAX_EVENTS = 5000`.
  - Each class is trimmed only within itself.
- **Who can write each class:**
  - Every refusal of a caller without the capability goes through `admin()` (`model_admin.py:383-388`) and is written as `ACCESS_REFUSED`. Every route depends on `Admin`.
  - Only `recheck()` writes other refused rows, and only after the caller had already passed `admin()`.
  - `applied` and `reverted` are written only at `model_admin.py:243`, `:317` and `:810` (system revert, undo, HR change).
- **Store-level test:** `test_refused_access_cannot_push_model_changes_out_of_the_audit`.
- **My route-level probe (P1):**
  - With the limits at 5/3, HR activates a model. Then RM, CO and Director send 90 refused HTTP calls, and HR sends 10 refused `QUALIFICATION_VIEW` calls.
  - Result: `ACTIVATED/applied` survives, exactly 3 `ACCESS_REFUSED` rows remain, and every non-`ACCESS_REFUSED` refused row has role HR.
- **Residual:** a refusal flood can still hide the history from the API/UI view, but not from the store. See N-1.

**F-2 (fixed).** `git diff --check 23c45a7 ffeeddf` exits 0. The test change removes one blank line and no assertion.

**F-3 (fixed).**

- The supervisor now refreshes the heartbeat once per poll while the child is alive (`model_admin.py:621`, new `store.touch`).
- `STALE_SECONDS` is now 2100, which is more than 3 × 600 s plus a margin.
- **My probe (P5):** `STALE_SECONDS` was set to 1 and the child never sends a heartbeat itself. A second start 3 s later is still refused with `QUALIFICATION_BUSY`, so the supervisor heartbeat alone keeps the run alive.
- Side effect: a stranded run now blocks for longer. See N-2.

**F-4 (fixed).**

- **What changed:** `apply()` (`model_admin.py:291-324`) now restores the *previous* choice together with the previous last-good model (`_last_good(before)`). It records `ACTIVATION_UNDONE/reverted`, then calls `_restore()`. If the previous model is no longer usable, `_restore()` reverts to the baseline with an audited `STARTUP_REVERTED`.
- **When `before` is valid:** `before` is read under the lock before the CAS, so it equals the state at `expected` whenever the CAS succeeds.
- **Implementer test:** previous X is restored and last-good stays `BASELINE`.
- **My probes:**
  - P3: X and Y both become unbuildable. Result: the baseline, rows `ACTIVATION_UNDONE`, `STARTUP_REVERTED` and `ACTIVATED/refused`, no `ACTIVATED/applied`, HTTP 409 `CREDENTIAL_MISSING` with the fixed generic message.
  - P3b: undo when the previous model was the baseline. The baseline and its last-good pair are unchanged.
- **Narrow race:** see I-R1.

**F-5 (fixed).**

- **What changed:** inside the supervisor loop, store errors are caught and supervision continues. Any other error ends with `SUPERVISOR_FAILED`. A `finally` kills a live child and waits for it. Recording the outcome is guarded.
- **Implementer test:** `poll()` raises, which ends in kill and `error/SUPERVISOR_FAILED` plus a `QUALIFICATION_FINISHED` row.
- **My probe (P6):** `touch` always raises (`database is locked`), the child is hung, and the deadline is shortened. Result: the child is killed and the run closes as `error/DEADLINE`.

**F-6 (fixed).** An unknown or malformed id on GET and cancel is now audited as `QUALIFICATION_VIEW`/`QUALIFICATION_CANCEL_REQUESTED` `refused QUALIFICATION_UNKNOWN`. Only the code is stored, not the path value, so nothing can be injected into the audit. Test: `test_unknown_qualification_ids_are_audited`.

**F-8 (fixed).**

- **What changed:** `instructions.py`, `answer_records.py`, `knowledge/retrieval.py` and `knowledge/redaction.py` were added to `BASIS_FILES`. Each file's path relative to `apps/assistant` is now hashed, instead of the bare file name, so files with the same name in different folders are told apart. `PACKAGE_DIR` and `ASSISTANT_DIR` are both resolved, so `relative_to` is safe.
- **My probe (P8):** run on a copied tree. Changing each of the 4 new files gives a distinct new basis, and restoring the file gives the original basis back.

**Extra fix (fixed).**

- `_refusal` now uses `MESSAGES.get(code, MESSAGES["BUILD_FAILED"])`. A configuration code such as `CREDENTIAL_MISSING` returns HTTP 409, the code, and a fixed message instead of a 500.
- The fallback message is in the frontend allowlist (`apps/frontend/src/aiAssistant.ts:131`), so the browser shows it. The frontend did not change.
- `adapter_for` already used the same fallback.

## 4. F-7 assessment (orphan qualification process after a service restart)

**Still open, and bounded.**

- **What is bounded:**
  - The child checks its own deadline (`model_qualification_max_seconds`, ≤ 14,400) and the cancel flag before each turn and each capacity count (`assistant_eval/qualification.py:96-100`).
  - Each model call is limited by the profile timeout (≤ 600 s).
  - A cancel sent from a new service instance is honoured cooperatively.
  - The orphan cannot activate anything, because activation is a separate audited HR action.
- **What remains:**
  - A child hung outside a model call is never killed.
  - An orphan that finishes writes its result, but no `QUALIFICATION_FINISHED` audit row is written, because there is no supervisor.
  - A run left `running` by a crashed service and child now blocks every new qualification for up to 35 minutes (see N-2).
- **Verdict:** this is fail-closed and limited to an administrator feature, so I accept it as a Low residual for this POC. It is not a blocker.

## 5. New findings (none required for this gate)

### N-1 Low (audit visibility): a refusal flood can hide model changes from the HR audit view

- **Where:**
  - `apps/assistant/ai_assistant/model_admin.py:577-581`: `GET /audit` returns the newest `limit` rows (default 100, at most 500) across all classes, with no class filter and no paging.
  - `model_admin_store.py:30` keeps up to 1,000 `ACCESS_REFUSED` rows.
- **Scenario:** a non-administrator sends 500 or more refused requests. The HR page and the API at its maximum limit then show only `ACCESS_REFUSED` rows. The `ACTIVATED`, `ROLLED_BACK` and `STARTUP_REVERTED` rows are still in SQLite but cannot be reached through the product.
  - Reproduced with probe P1b using the real limits: 1,050 refusals, the API view at 500 rows shows only refusals, and the database still holds the `ACTIVATED` row plus 1,000 refusals.
  - The flood also replaces older refusal evidence, which is inherent to bounded retention.
- **Why it is not blocking:** F-1's integrity defect (erasure) is fixed. The flood rows themselves name the actor and role, and IT can read the database. D-093 requires that operations be audited, and they are.
- **Suggested follow-up:** a class filter or separate change-history query on `/audit`, or collapsing repeated refusals per actor.

### N-2 Low (availability, side effect of the F-3 fix): a stranded `running` row blocks qualification for up to 35 minutes and cannot be cancelled

- **Where:**
  - `apps/assistant/ai_assistant/model_admin_store.py:33` (`STALE_SECONDS = 2100`).
  - `:310-327` (`begin_qualification` reclaims only stale rows).
  - `:359-366` (`request_cancel` only sets a flag).
  - No running row is reconciled at start-up.
- **Scenario:** the service and its child are both stopped mid-run, for example by a host restart. The new instance refuses every qualification with `QUALIFICATION_BUSY` until 2,100 s after the last heartbeat. HR's cancel succeeds but releases nothing, because no process closes the run. Probe P9 confirms both points.
  - Before the fix this window was 300 s.
  - The IT guide (`docs/integration/AI_MODEL_CONFIGURATION.md` §6-7) does not mention it.
- **Why it is not blocking:** it fails closed, it affects only an administrator feature, it ends by itself, and no unsafe activation is possible.
- **Suggested follow-up:** document the window. Or let cancel close a run whose heartbeat is older than a short threshold, or mark the run as interrupted when the service starts.

### Informational

- **I-R1:** in a multi-process race, another process can revert the just-committed unbuildable choice (`_restore`, `STARTUP_REVERTED`) before the undo CAS at `model_admin.py:310`.
  - The undo then raises `RevisionConflict`, and the caller gets `REVISION_CONFLICT`.
  - There is no `ACTIVATION_UNDONE` row, but the store and the audit (`STARTUP_REVERTED`) stay truthful, and the in-memory model resynchronises on the next request.
  - The end state is the baseline rather than X. The window is very narrow.
- **I-R2:** `test_a_run_is_not_called_stale_during_its_longest_silent_step` (`tests/test_model_management.py:1113-1118`) checks the bound on the env `llm_timeout_seconds`. The file profile's `timeout_seconds` bound (`model_catalog.py:84`) is the one used for file-profile qualification. Both are 600 today, but raising only the profile bound would not be caught.
- **I-R3:** the supervisor now writes once per second (`BEGIN IMMEDIATE`, rollback-journal SQLite) while a run is live.
  - This is negligible at POC scale.
  - Store errors on the answer path already keep the current model (`ModelSelector.current`).

## 6. Regression check of the full candidate

- **Session 2 overlap:**
  - `git diff --name-only 23c45a7 ffeeddf` on `prompts.py`, `instructions/`, `instructions.py`, `guardrails.py`, `guide.py`, `knowledge_answers.py`, `briefing.py`, `small_talk.py`, `knowledge/`, `tests/fixtures/` and `test_guardrail_negation.py` is empty.
  - F-8 only *reads* more Session 2 files into the basis hash. This widens the by-design coupling I-5: Session 2 edits make qualifications out of date.
- **Guardrail sentences:** UNSAFE = 154 and KNOWLEDGE_FILTER_LIMITS = 46 (measured), and `test_guardrail_negation.py` gives 640 passed.
- **Decisions:** `DECISION_LOG.md` vs base has 0 removed lines. D-092 is still `(PROPOSED)` (line 1179). The remediation's doc edits change only text this candidate added (retention wording).
- **Tests:** none deleted or weakened. Test diff vs base is +1517/-0 apart from the one blank line removed. Remediation tests are +140/-0.
- **Frontend:** `git diff 5341dcf ffeeddf -- apps/frontend` is empty, so the previous gate's evidence is reused (`tsc` exit 0; vitest 65 files, 1118 passed).
- **Remote and loopback paths:** `model_factory.py`, `main.py` and the catalogue rules did not change in the remediation, so the earlier remote and loopback evidence still applies.
- **Implementer LOCAL evidence:** `PROJECT_STATE.md` now records two implementer `LOCAL` runs against Ollama 0.40.10 `llama3.1:8b` with a 16k context. Declared 16,384 passed every gate. Declared 32,768 failed G-7 with `TRUNCATION_DETECTED`.
  - They are labelled implementer evidence and "Not Live evidence".
  - I did **not** reproduce them (no model server was allowed), so they remain implementer-reported.

## 7. Commands and results

Python `<py>` = `C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.venv/Scripts/python.exe`.

| Command (cwd) | Result |
| --- | --- |
| `PYTHONPATH=. <py> -m pytest -q -p no:cacheprovider -o addopts= tests/test_model_management.py tests/test_guardrail_negation.py tests/test_eval_harness.py` (apps/assistant, one process) | 727 passed, 89.5 s |
| Same three files run separately | 52 / 640 / 35 passed, 0 failed |
| `<py> -m ruff check --no-cache .` / `ruff format --check --no-cache .` / `mypy ai_assistant` (apps/assistant) | All checks passed / 105 files already formatted / no issues in 37 source files |
| `PYTHONPATH=. <py> -m pytest -p no:cacheprovider -o addopts= -q tests/test_model_config_capability.py tests/test_phase13_auth_rbac.py` (apps/backend) | 73 passed |
| `git diff --check 23c45a7 ffeeddf` (root) | exit 0 |
| Task-owned new files (14): trailing whitespace; index EOL (`git ls-files --eol`) | 0 trailing whitespace; all `i/lf`. The 6 `i/mixed` changed files (App.tsx, navigation.tsx, types.ts, Phase15CNavigation.test.tsx, ARCHITECTURE.md, PROJECT_STATE.md) were already mixed on base, and additions follow the surrounding EOL |
| `<py> scripts/check_secrets.py` (root) | Secret scan passed |
| Reviewer probes `scratchpad/qg_r1/test_qg_r1_probes.py` (outside the repo; run with `-p tests.conftest`, so the offline and no-dotenv guard applies) | 8 passed. The probes are P1, P1b, P3, P3b, P5, P6, P8 and P9, described in sections 3 to 5 |
| `git status --short` after all checks | empty (no cache or build output written to the repository) |

**Full assistant suite: not rerun. The reason:**

- The remediation changes only:
  - `ModelSelector.apply`, which runs only when there is a store;
  - the supervisor and the qualification endpoints;
  - store retention, heartbeat and basis files;
  - the `_refusal` message lookup, which differs only for codes that are missing from `MESSAGES`.
- These paths are used only by `test_model_management.py` and the eval harness / import-boundary tests in `test_eval_harness.py`. I reran both.
- `main.py`, the answer path, `model_factory.py`, prompts and guardrails did not change.
- So the previous gate's full-suite evidence on `5341dcf` still holds for every other file: 2246 collected, with 15 host `EMFILE` failures that all pass in isolation.

## 8. Limitations

- No local model server was started and no remote or paid inference was made. The real Ollama runs are implementer-reported `LOCAL` evidence that I did not reproduce. Everything else is fake-transport, in-test loopback or `LOCAL` mock evidence: it says nothing about any real model, and nothing about answer quality (`NOT_SCORED`).
- The full assistant suite and the frontend suite were not rerun (see section 7). The frontend evidence is reused from the previous gate, which ran on `5341dcf`; the frontend content is identical.
- Orphan-process behaviour (F-7) was checked by reading the code and a store-level probe. I did not kill a real service process.
- Multi-process races (I-R1) were analysed, not reproduced.
- No browser or Playwright checks were run.

## 9. Readiness

The candidate at `ffeeddf` (tree `6fac2b5`) is **ready to proceed to integration / pre-PR readiness**: the `integration-safe-development` checklist and `scripts/pre_pr_check.py` on the clean committed state, followed by publication only with explicit owner authorisation.

- N-1, N-2 and F-7 are recommended follow-ups, not conditions of this gate.
- Any change to the reviewed content needs a fresh independent review.
- This gate makes no product, Live, sponsor or answer-quality claim. D-093 remains an owner-accepted, project-defined POC decision, and D-092 remains PROPOSED.

## 10. Git status at report time

- Branch `feat/assistant-model-management-20261027`, HEAD `ffeeddf`, tree `6fac2b5`, `origin/main` `23c45a7`.
- The only modification is this new, untracked report file.
- No implementation fix, commit, stash, reset, push, PR, merge or next phase was performed.
