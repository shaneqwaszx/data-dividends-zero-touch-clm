# AI Assistant Model Management (D-093) - Independent Quality Gate

Stage 3 independent review. The reviewer did not author or remediate the reviewed content.
Only this report was written; no fix, stage, commit, stash, reset or push was made.

## 1. Outcome

**FAIL** (narrow, bounded remediation).

Almost all acceptance criteria are met and verified. Two fixes are required:

- **F-1 (Medium, security / audit integrity):** any signed-in user without
  `MODEL_CONFIG_MANAGE` (RM, Client Onboarder, Director) can erase the whole model-management
  audit history, including `ACTIVATED`, `ROLLED_BACK` and `STARTUP_REVERTED`, just by sending
  refused requests. Every refusal adds one audit row, and all rows share one global limit of
  5,000 newest events. I reproduced this.
- **F-2 (Low, hygiene):** `git diff --check` fails because of a blank line at the end of a new
  file. `scripts/pre_pr_check.py` would reject it.

F-1 is a security correction, so the skill does not allow `PASS WITH MINOR FIXES`. This
verdict covers only the frozen content below.

## 2. Reviewed identity

| Item | Value |
| --- | --- |
| Worktree | `C:/Users/shane/Desktop/claude-worktrees/assistant-model-management-20261027` |
| Branch | `feat/assistant-model-management-20261027` |
| Reviewed HEAD | `5341dcf70987711d367e5228a218f7e99194fe6f` |
| Reviewed tree | `de53c2ca30c5e1377eae083b255b2dfb324486a0` |
| Base = `origin/main` | `23c45a7a4ca18cc3da751416d30365beaba2114f` (unchanged at start and end of review) |
| Diff reviewed | `git diff 23c45a7 5341dcf`: 33 files, +4917/-44 (12 new files included) |
| Worktree state | clean (no tracked/untracked changes) before this report; HEAD/tree re-verified unchanged before writing |

## 3. Acceptance criteria

| # | Criterion | Result | Evidence |
| --- | --- | --- | --- |
| 1a | `MODEL_CONFIG_MANAGE` exists and is HR only. RM, CO and Director lack it. Director `POLICY_APPROVE` and HR `POLICY_MUTATE` are unchanged. HR has no `CASE_ACCESS` | Met | `apps/backend/app/domain/access.py:53-55,79`. `/api/auth/me` derives capabilities from `ROLE_CAPABILITIES` (`api_auth.py:103`). `test_model_config_capability.py` plus `test_phase13_auth_rbac.py`: 73 passed |
| 1b | Every operation is enforced server-side, and activation/rollback are re-checked inside the lock | Met | Every route depends on `admin()` (`model_admin.py:369-376`), which checks origin, calls `/api/auth/me` with the caller's cookie, then checks the capability. `change()` calls `recheck()` inside `selector.change_lock` (`model_admin.py:712-713`). Test `test_only_hr_may_use_any_management_endpoint...` covers 3 roles x 6 endpoints → 403, with no model call |
| 1c | Successful and denied operations are audited, without secrets | Partly met. See F-1 and F-6 | Refusals of signed-in callers are recorded as `ACCESS_REFUSED` or as action-specific `refused` rows. Rows hold no URL or key: the test asserts `SECRET` and `127.0.0.1:1234` are absent from the SQLite bytes. However, refused callers can evict the history (F-1), and some 404 refusals are not audited (F-6) |
| 2 | Env baseline plus an IT JSON file. No literal credentials. Key variable names come only from the allowlist, never `OPENROUTER_API_KEY`. The browser sends only a profile id | Met | Strict schema with `extra="forbid"` and `strict=True` (`model_catalog.py:67-118`). My probes: a literal `api_key` field, `credential_env` set to `OPENROUTER_API_KEY`, `AI_ASSISTANT_LLM_API_KEY` or `AI_ASSISTANT_MODEL_KEY_OTHER`, a string-typed number, reserved ids, path-like ids and control characters are all refused. Errors name the field, never the value. The request body is `ChangeRequest` with `extra="forbid"` (revision and acknowledgement only). Paths carry only a profile or qualification id |
| 3 | Only literal-loopback models are selectable. The loopback and proxy rules are kept. Remote models cannot be activated. D-091 and D-092 are unchanged, and D-092 is still PROPOSED | Met | `_file_entry` uses `is_local_model_url`. Probes: `localhost`, `0.0.0.0`, `nip.io`, userinfo and remote hosts → `unavailable/NOT_LOOPBACK`. `build_profile_model` always calls `require_direct_loopback`, which checks env and system proxies. The remote profile is `pending_authorisation` and refused with no network call (tested: `server.requests == []`). The decision log diff has 0 removed lines. D-092 header is still `(PROPOSED)` |
| 4a | G-4 ≤5%, G-6 ≥0.70 with a zero denominator never passing, G-7 capacity. Zero unsafe lines is mandatory. G-5 is reported only | Met | `model_qualification.gates()` (`:368-446`). Overall pass uses gating gates only (`assistant_eval/qualification.py:208`). Threshold and zero-denominator tests pass |
| 4b | Context compliance uses verified or conservatively bounded capacity | Met | `verify_capacity` uses only server-reported `prompt_tokens`. It refuses on missing usage, a non-linear count (truncation) or a rejecting server, and caps the probe at 32,768. Bound = `probed - base - max_answer - 256`. At runtime the activated model is wrapped in `BoundedPromptModel` (UTF-8 bytes + role + 16 per message). The tokens ≤ bytes assumption is checked on the largest real prompt, and `TOKENIZER_BOUND_NOT_CONFIRMED` is raised otherwise |
| 4c | Quality shows `NOT_SCORED` while gold is empty. Technical qualification is never shown as proof of quality. An unscored model needs an explicit acknowledgement | Met | `quality_state()` and harness `gold_state()` return NOT_SCORED with the current stub gold. The server requires `acknowledge_quality_unscored` unless the run itself recorded a verified `SCORED` (`model_admin.py:741-743`). The audit code is `QUALITY_NOT_SCORED_ACKNOWLEDGED`. UI and docs say "technical qualification only / not proof of answer quality" |
| 5 | At startup, revert to the baseline with an audited reason. Runtime failures use the deterministic fallback. Only an administrator switches or rolls back. An unavailable baseline fails safely | Met | `_restore`/`_build_stored` (`model_admin.py:215-284`). Parametrised restart tests cover CREDENTIAL_MISSING, QUALIFICATION_OUT_OF_DATE, PROFILE_MISSING, MODEL_DISABLED_BY_ENVIRONMENT and PROFILE_CHANGED → `STARTUP_REVERTED` by `system`. No automatic switch exists on the answer path. With `llm_enabled=false`, management is off and answers use case data |
| + | The nine guardrail categories are kept. The 154 UNSAFE and 46 KNOWLEDGE_FILTER_LIMITS sentences are kept | Met | No guardrail, prompt, catalog or routing file changed. Counts measured: UNSAFE=154, KFL=46. `test_guardrail_negation.py`: 640 passed |
| + | Activation is atomic, concurrent requests are consistent, and the state survives a restart | Met | CAS on `revision` under `BEGIN IMMEDIATE` (8-thread test: one applied, 7 `RevisionConflict`). Each request takes one snapshot (`selector.current()` at chat/stream start, passed to `stream_answer`/warm-up). A two-selector test shows two processes agree |
| + | Qualification concurrency, resources and failures are bounded | Met, with Low notes F-3, F-5 and F-7 | One `running` row, process deadline plus a 60 s supervisor kill, a 15 s grace after cancel, a cooperative stop before each turn and capacity probe, and the run is always closed (`finally`) |
| + | Existing remote inference permissions are unchanged | Met | `model_factory.py` only adds `require_direct_loopback` (moved from the harness, same rules). `build_chat_model` and the D-091 locks are untouched. `test_model_factory.py` (61) and `test_phase_b_live.py` (80) pass in isolation |
| + | No overlap with Session 2 (prompts, instructions, response catalog, topic routing) | Met | See section 6 |
| + | No existing test was deleted or weakened | Met | Test-file diff: only additions (5 files, +1378/-0). The only one-line change in an existing test adds the `aiModels` route prop to `Phase15CNavigation.test.tsx` |

## 4. Commands and results

Python: `C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.venv/Scripts/python.exe` (`<py>`).

| Command (cwd) | Result |
| --- | --- |
| `PYTHONPATH=. <py> -m pytest -q -p no:cacheprovider -o faulthandler_timeout=400 --junitxml=...` (apps/assistant, full suite, under `timeout 1500`) | **2246 collected, 2231 passed, 15 failed**, 0 errors, 703 s |
| 15 failures: 14 match the implementer's 16-entry baseline list. The 15th is `test_knowledge_answers.py::test_a_paraphrase_part_or_retag...`: a `knowledge retrieval failed` log during an `EMFILE` storm, so case-data fallback was asserted against a model answer. The other 2 baseline entries passed in this run | All failing files pass in isolation (below). Root cause: `OSError: [Errno 24] Too many open files` on this Windows host. I did **not** rerun the full suite on `origin/main` myself, so the baseline list is the implementer's; my evidence is the isolation reruns |
| Isolation reruns (`-o addopts= -q`): `test_knowledge_answers.py` / `test_model_factory.py` / `test_phase_b_live.py` / `test_required_p2.py` / `test_streaming_resources.py` / `test_guardrail_negation.py` / `test_eval_harness.py` | 21 / 61 / 80 / 67 / 80 / 640 / 35 passed, 0 failed |
| `tests/test_model_management.py` | 46 passed (34 functions, some parametrised), including the real-subprocess test against a real loopback HTTP server |
| `<py> -m ruff check --no-cache .` / `ruff format --check --no-cache .` / `mypy ai_assistant` (apps/assistant) | All checks passed / 105 files already formatted / no issues in 37 source files |
| `PYTHONPATH=. <py> -m pytest -p no:cacheprovider tests/test_model_config_capability.py tests/test_phase13_auth_rbac.py` (apps/backend) | 73 passed |
| `<py> scripts/check_secrets.py` (root) | Secret scan passed |
| `<py> -m pytest -q tests/test_check_secrets.py -p no:cacheprovider` (root) | 32 passed |
| `npx tsc -b --pretty false` (apps/frontend) | exit 0 |
| `npx vitest run src/pages/AiModelManagement.test.tsx src/Phase15CNavigation.test.tsx` | 2 files, 53 passed |
| `npx vitest run` (apps/frontend, full) | **65 files, 1118 passed**, 0 failed. `AiAssistantPanel.test.tsx` and `ViteHistoryFallback.test.ts` both passed in this run |
| `git diff --check 23c45a7 5341dcf` | **exit 2**: `apps/backend/tests/test_model_config_capability.py:38: new blank line at EOF` (F-2) |
| Added-line trailing whitespace / CR in new files | none |
| Doc removed-line check (ADR-012, ARCHITECTURE, PROJECT_STATE, contract, README) | 0 removed lines each |
| Reviewer probes (scratchpad only): `adversarial.py` (profile-file and build hostility) and `test_qg_probes.py` (2 tests) | All probes behaved as described in section 3. Both probe tests passed, which **confirms F-1 and F-3** |

## 5. Findings

### F-1 Medium (security / audit integrity): refused callers can evict the administrative audit history

- **Where:** `apps/assistant/ai_assistant/model_admin.py:369-373` (every refused call writes `ACCESS_REFUSED`) together with `apps/assistant/ai_assistant/model_admin_store.py:26,252-255` (one global retention of the newest `MAX_EVENTS = 5000` rows, deleted on every insert).
- **Scenario:** an RM, Client Onboarder or Director with a normal CLM session scripts `GET /assistant/admin/models` (no `Origin` header is needed; `check_origin` allows a missing origin) 5,000 times. Each call is refused and audited. Every earlier `ACTIVATED`, `ROLLED_BACK`, `QUALIFICATION_*` and `STARTUP_REVERTED` row is deleted.
- **Reproduced:** `test_refused_callers_can_evict_activation_history` with `MAX_EVENTS=20`. After 20 refused RM calls, the remaining actions were only `['ACCESS_REFUSED']`.
- **Why it matters:** D-093 M1 requires model changes and refusals to be audited. The audit is the only record of who switched the application-wide model. A non-administrator can wipe it, so model changes become deniable.
- **Bounded fix options (the remediation owner chooses):** retain refusal events separately from administrative events, or never let `ACCESS_REFUSED` rows evict non-refusal rows; optionally collapse repeated refusals per actor.

### F-2 Low (hygiene; blocks publication): blank line at EOF in a new file

- **Where:** `apps/backend/tests/test_model_config_capability.py:38`.
- **Impact:** `git diff --check` exits 2, and `scripts/pre_pr_check.py:818-826` fails on it.

### F-3 Low: the stale-run threshold is shorter than one legal model call, so "one run at a time" can be broken

- **Where:** `apps/assistant/ai_assistant/model_admin_store.py:27,295-304` (`STALE_SECONDS = 300`), `model_catalog.py:84` (`timeout_seconds ≤ 600`). Heartbeats happen only before each turn and each capacity count (`assistant_eval/qualification.py:96-100`, `model_qualification.py:222-224`).
- **Scenario:** the profile has `timeout_seconds: 600`. A slow CPU model needs more than 300 s for one turn or for the 32k-token capacity probe. A second HR start then marks the live run `error/STALE` and launches a second process against the same local model. The first run's result is discarded.
- **Reproduced:** with a store-level probe (`test_a_live_run_with_a_slow_turn_is_marked_stale_and_a_second_run_starts`).
- **Why it matters:** the overlap is bounded (the stale run stops at its next heartbeat, and each process has its own deadline), but the documented "one run at a time" guarantee does not hold.
- **Fix:** make the stale threshold exceed the profile's timeout plus a margin, or have the supervisor heartbeat while the child is alive.

### F-4 Low: the failed-activation "undo" switches to the baseline and is audited only as a refusal

- **Where:** `apps/assistant/ai_assistant/model_admin.py:297-300` and `762-763`.
- **Scenario:** the active model is X and HR activates Y. IT edits or removes Y, or its key disappears, in the window between the pre-checks and `apply()`. `apply()` commits Y, cannot build it, then "undoes" to the **baseline**, not to X. That bumps the revision twice. The audit records only `ACTIVATED refused <code>` with the *old* revision.
- **Why it matters:** the application-wide model changed from X to the baseline with no audit row showing it. The window is small.

### F-5 Low: the qualification supervisor has no exception handling

- **Where:** `apps/assistant/ai_assistant/model_admin.py:585-621`.
- **Scenario:** a SQLite error, such as `database is locked` beyond the 10 s timeout, inside the polling loop ends the daemon thread silently. The child is then never killed at deadline or after a cancel grace, and no `QUALIFICATION_FINISHED` row is written.
- **Why it matters:** the child's own deadline check still bounds it (fail-closed), so this is Low.

### F-6 Low: some refusals of an authorised administrator are not audited

- **Where:** `apps/assistant/ai_assistant/model_admin.py:683-684` and `691-694`.
- **Scenario:** `QUALIFICATION_UNKNOWN` on get/cancel (unknown, malformed or already finished id) returns 404 without an audit row.
- **Why it matters:** this is minor next to criterion 1's "denied operations audited". Refusals while management is off cannot be audited (no store), which is acceptable.

### F-7 Low: the qualification process can outlive the service

- **Where:** `apps/assistant/ai_assistant/model_admin.py:164-179,667-672`.
- **Scenario:** the child is a plain `Popen` (no Windows job object or process group) supervised by a daemon thread. If the service restarts or crashes during a run, the child keeps running unsupervised. It is still bounded by its own deadline check before each turn, and a cancel from the new instance is honoured cooperatively. A hung child is never killed; it only becomes `STALE` after 300 s.

### F-8 Low: the qualification basis does not cover every file that shapes the prompt

- **Where:** `apps/assistant/ai_assistant/model_qualification.py:57-68`. The hashed set omits `instructions.py` (the loader that strips comments from `instructions/*.md` and builds the system prompt) and `knowledge/retrieval.py` and `knowledge/redaction.py`.
- **Why it matters:** a change there alters what the model sees without invalidating qualification. D-093 says "a prompt, catalog or guardrail change requires qualifying again". Safety is unaffected, because guardrails are hashed and the runtime prompt bound is enforced regardless.

### Informational (no action required for this gate)

- **I-1:** the planner's 2.3 says the profiles file is "git-ignored", but no ignore rule exists. A `model_profiles.json` placed in `apps/assistant/` could be committed. Its content cannot hold credentials (strict schema), but it could hold internal hostnames.
- **I-2:** telemetry `profile` for an activated file profile records the environment profile id (`local`). The `model` field is correct. The planner's "telemetry profile-id pattern" item was not implemented, and the record is not wrong in boundary terms.
- **I-3:** some planner audit actions were not implemented as named: `QUALIFICATION_CANCELLED` (it is `QUALIFICATION_CANCEL_REQUESTED` plus `QUALIFICATION_FINISHED/cancelled`) and `CONFIG_CHANGED` (shown as a `config_changed` flag instead). `STARTUP_REVERTED` is also written when *any* process fails to build a newly activated model mid-run, not only at start. This is fail-safe, but the name is narrower than the behaviour.
- **I-4:** after IT edits the *active* profile at runtime, re-activating the same profile id returns `ALREADY_ACTIVE` until restart. The UI banner and the IT guide describe this.
- **I-5 (coordination):** once Session 2's prompt or instruction changes merge, every qualification becomes out of date by design. Any activated file profile then reverts to the baseline at the next restart (`QUALIFICATION_OUT_OF_DATE`). Both branches also edit `main.py`; expect a textual merge, not a semantic overlap.

## 6. Session 2 overlap check

- No diff in `ai_assistant/prompts.py`, `instructions/`, `instructions.py`, `guardrails.py`, `guide.py`, `knowledge_answers.py`, `briefing.py`, `small_talk.py`, `knowledge/` or `tests/fixtures/` (`git diff --name-only` on these paths: empty).
- `main.py` changes are limited to model selection:
  - the `selector` snapshot, `_Outcome.model` and warm-up using the active `base_url`;
  - health reading the current model;
  - mounting the admin router.
- Topic routing (`prompts.topic_plan`) and the exact-line guard are untouched.
- **No overlap found.** The only coupling is by design: the qualification basis hashes Session 2's files (I-5).

## 7. Security review

- **Credentials:** values are only in the process environment, through the 4-name allowlist, and are read when the adapter is built. They never appear in a response, the store or the audit (tested). The secret scanner covers the new variable names (tested: 3 assignment forms flagged without echoing the value).
- **Browser surface:**
  - Inputs are a path id (unknown → 404 with `profile_id=None` in the audit, so no injection into the audit) and `{expected_revision, acknowledge_quality_unscored}` with `extra="forbid"`.
  - Messages are fixed and also allowlisted in `aiAssistant.ts`.
  - Responses carry loopback `host:port` only, never a URL path or the key's variable name.
- **Network boundary:** literal loopback only, with env and system proxy refusal via the shared `require_direct_loopback`. Redirects are not followed (existing adapter). The remote profile is refused before any network I/O.
- **Subprocess launch** (the requested design point):
  - argv is fixed, with no shell: `sys.executable`, the repository script, a uuid4 hex id the service generates and the child re-validates (`[0-9a-f]{32}`), and the service's own configured DB and profiles paths.
  - stdin, stdout and stderr go to DEVNULL, so no output is retained. `cwd=apps/assistant`.
  - There is **no browser-controlled argument, so no argument injection.**
  - The child re-reads the profile and refuses on a fingerprint or basis mismatch (`CONFIG_MISMATCH`). It re-applies the loopback and proxy rule with the real environment, always closes its run (`finally`), and checks its deadline and cancel before every turn.
  - It inherits the full environment, including any remote key, but has no code path that uses one. Scrubbing the environment is optional hardening.
  - Lifecycle gaps: F-3, F-5 and F-7, all Low and fail-closed.
- **Scope of the subprocess design:** it keeps the letter of `test_the_runtime_package_never_imports_the_harness`, which is a lexical check, and the spirit (the harness never loads into the service process). The trade-off is that the dev-only harness and `tests/fixtures/eval` become a deployment dependency of the service's qualification feature. D-093's implementation notes and the IT guide record this, and the planner's owner-condition block lists it. I judge it sound and within the approved scope, provided the owner accepts that deployment dependency.
- **RBAC:** a single capability, HR only, with no case or answer-record read in the admin API. `CapabilityRoute` and the nav entry are presentation only, and the server returns 403 independently.
- **Data:** qualification uses synthetic scenarios with a mock CLM. Stored summaries hold counts, rates, timings and codes only, with no answer text. The state DB sits under `apps/assistant/data/` (git-ignored, verified with `git check-ignore`).
- **Audit integrity:** see F-1 (Medium).

## 8. Required fixes (for the remediation run)

1. **F-1:** stop refused-caller events from evicting administrative audit events. Add a test that floods refusals and then asserts `ACTIVATED`/`ROLLED_BACK` rows survive.
2. **F-2:** remove the trailing blank line at `apps/backend/tests/test_model_config_capability.py:38`.

F-3 to F-8 are recommended but not required for this gate. If F-3 or F-4 are fixed in the same run, the recheck must cover them. A recheck reviews the corrected delta and reuses the unchanged evidence above (assistant suite, isolation reruns, frontend suite, backend RBAC and secret scanner) unless the change invalidates it.

## 9. Limitations

- No real local model server (Ollama, LM Studio or vLLM) was started, as instructed. No remote or paid inference was made. Qualification, capacity and connection behaviour were checked only against the fake transport and the in-test loopback HTTP server. This is `LOCAL`/mock technical evidence, not evidence about any real model or about answer quality.
- I did not run the full assistant suite on `origin/main`. I relied on the implementer's 16-entry baseline list plus my own isolation reruns of every failing file on the candidate (all pass).
- I did not exercise browser and HTTP behaviour with Playwright. Frontend evidence is vitest (jsdom) and `tsc`.
- Windows `EMFILE` limits the full-suite signal on this host. Another process may have been using CPU at the same time.
- Multi-process behaviour was checked with two in-process selectors on one SQLite file, not with two real service processes.

## 10. Readiness

The candidate is **not ready for integration or pre-PR**. It needs bounded remediation of F-1 and F-2, then an independent recheck of the corrected delta. This gate makes no product, Live, sponsor or answer-quality claim. D-093 remains an owner-accepted, project-defined POC decision; D-092 remains PROPOSED.

## 11. Git status at report time

- Branch `feat/assistant-model-management-20261027`, HEAD `5341dcf`, tree `de53c2c`, `origin/main` `23c45a7`.
- Before this report the worktree was clean (no tracked, untracked or staged changes).
- The only modification is this new, untracked report file.
- No implementation fix, commit, stash, reset, push, PR, merge or next phase was performed. Reviewer probe scripts live only in the session scratchpad, outside the repository.
