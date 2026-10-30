# D-104 Independent Re-Quality Gate 2 (M1/L1/L2 remediation and whole candidate)

Date: 2026-10-30. Reviewer: a fresh, independent Quality Gate agent. It did not author or
remediate the reviewed content. Read-only review; this file is the only file written. Nothing
was committed, staged, stashed, reset or pushed, and no branch changed. No `.env` file was
read. No network or paid call was made. The primary checkout's `apps/assistant/data` was not
touched, and the `apps/frontend/node_modules` junction was left in place. Probes and caches
were kept in the session scratchpad.

## Frozen identity

| Item | Value |
| --- | --- |
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\assistant-data-access-policy-20261030` |
| Branch | `feat/assistant-data-access-policy` |
| HEAD = base = `origin/main` | `0c6a6325e8ad9bdc650c72824124a4d0f2fc863f` (all changes uncommitted) |
| Reviewed paths | 17. This is the sorted union of `git diff --name-only` and `git ls-files --others --exclude-standard`, excluding `D104_QUALITY_GATE.md`, `D104_REQG.md` and this report. It is 14 tracked files plus 3 new files: `data_access.py`, `test_data_access_policy.py` and `D104_DATA_ACCESS_POLICY.md` |
| Content-id at start | `1b8c84b20bf417f48ef4fb314af631c097dbd79d7cd65c90a57a6bcc9e421e92` (matches the assignment) |
| Content-id at end | `1b8c84b20bf417f48ef4fb314af631c097dbd79d7cd65c90a57a6bcc9e421e92` (unchanged) |

The content-id is sha256 over `path + b'\0' + content(CRLF->LF) + b'\0'` for each path.

## Checks run (this session, on the frozen content)

| Check | Result |
| --- | --- |
| Focused pytest, from `apps/assistant` with `PYTHONPATH=$PWD`, `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1` and `timeout`. Files: `test_data_access_policy`, `test_synthetic_eligibility`, `test_remote_test`, `test_claude_runtime`, `test_claude_console`, `test_claude_hr_spending`, `test_claude_multi_turn`, `test_model_management`, `test_spending_controls`, `test_d098_recovery`, `test_guardrails*`, `test_warm_up_security`, `test_ai_assistant`, `test_knowledge_review_safety` | 865 tests: 0 failures, 0 errors, 0 skipped (junitxml in the scratchpad). That is 863 at the prior gate plus the 2 new tests |
| Full assistant suite, and the four Errno-24 files run alone | Not run. They are not needed for the changed delta, and no claim is made from them |
| `scripts/build_synthetic_boundary.py --check` (from `apps/assistant`) | `synthetic boundary is current`, exit 0 |
| `qualification_basis()`, candidate | `598cfe14753d028898a7b727741291b282259dc694f897bedf5fdc0b41f6f3ce`. Matches the stated basis and the docs (Q1, §14, PROJECT_STATE) |
| `qualification_basis()`, `origin/main` | `65f22e46c509…`. Reused from D104_REQG, because main is unchanged at `0c6a632` |
| `ruff check --no-cache` and `ruff format --check --no-cache` (`ai_assistant` plus the new test) | All checks passed; 58 files already formatted |
| `mypy ai_assistant` (cache in the scratchpad) | Success: no issues in 46 source files |
| Frontend `npx tsc -b --pretty false` | Exit 0 |
| Frontend `npx vitest run src/pages/AiModelManagement.test.tsx` | 98 passed |
| `git diff --check`; trailing whitespace in the 3 untracked files; `--stat` against `--ignore-cr-at-eol` | Clean; clean; identical (no EOL churn) |
| Test deletion or weakening against `origin/main` | No tracked backend test file changed. The frontend test diff removes one line only, an import line that was widened. No test was removed or weakened |
| Adversarial probes (scratchpad `probe/test_reqg2_probe.py`, using the suite's autouse network guard and credential fixtures) | 9 passed. Details follow |

### Adversarial probes

All probes run without model management (no profiles file), with an RM asking about a
non-synthetic (`LIVE`) case.

| Probe | Result |
| --- | --- |
| Base URL `http://10.0.0.5:8080/v1`, `http://localhost:8080/v1`, `https://api.example.invalid/v1` or `http://127.0.0.1.nip.io:8080/v1` | View: `active_restricted=true`, IT row restricted. Chat: not answered by the model, IT eligibility notice shown, baseline called 0 times |
| Base URL `http://127.0.0.1:8080/v1` or `http://[::1]:8080/v1` | Unrestricted, as before (D-093 default); baseline called once |
| `llm_enabled=false` with a non-loopback URL | `restrict_remote` is true. View: `not_managed`, `active_class=None`, `active_restricted=false`, IT row `{restricted:true, locked:true}`. No model call |
| Injected `chat_model` (the eval-harness path) | `restrict_remote` is false, by design. The admin router is not mounted (`main.py:909`, `if chat_model is None`), so `GET /data-access` returns 404 and no view can misreport |
| Mutation: force `restrict_remote=False` after construction | The new test `test_without_model_management_a_non_loopback_model_is_still_restricted` fails, so the test is not vacuous |

## Review of the remediation (focus questions)

- **M1 closed on every non-injected path.**
  - `open_selector` (`model_admin.py:1206-1214`) passes `restrict_remote=not injected` on
    the unmanaged branch. The unmanaged branch covers no profiles file, `llm_enabled`
    false, and injected.
  - `ModelSelector.__init__` (`model_admin.py:337`) forces it true whenever a store exists.
    Managed mode therefore always restricts `it_configured`, including a profile entry with
    a non-loopback `base_url` (`model_admin.py:848`).
  - `_with_data_access` (`model_admin.py:437-447`) wraps `IT_CLASS` whenever
    `restrict_remote` is true, independent of the store and the policy row.
  - A missing `base_url` classifies as `it_configured`, which fails closed.
  - The probes confirm this behaviour for every non-injected configuration.
- **`restrict_remote` defaults to False for direct construction. Production is not
  weakened.**
  - The only production construction is `main.py:448`
    (`open_selector(config, baseline, injected=chat_model is not None)`), and the module app
    at `main.py:1030` passes no `chat_model`.
  - `git grep` finds only one non-test `chat_model=` caller,
    `assistant_eval/runner.py:242`, the offline evaluation harness.
  - No other non-test `ModelSelector(` call exists.
  - Every chat, stream and warm-up path reads `selector.current()` (`main.py:916, 926, 941,
    974`), which applies `_with_data_access`. No caller uses the raw `_current()` result to
    send messages.
  - A default of True would be stronger defence in depth for future callers, but it is not
    required.
- **The view is honest in each mode.** `data_access.view` (`data_access.py:156-193`)
  reports the IT row as `restricted: remote_restricted`, and `active_restricted` uses the
  same predicate as the wrapper.
  - Managed mode: the local row equals `local_restricted(policy)`, the wrapper's own test.
    An unreadable policy gives `unavailable` with local restricted, which matches the
    wrapper's fail-closed behaviour.
  - Unmanaged mode: the local row is unrestricted and locked (it cannot be changed) under
    status `not_managed`, which is true.
  - Injected mode: no view exists (404).
  - The page banner ("treated the same way") is now true in every reachable mode.
  - Z2, §14 and the D104 report now say "with or without model management".
- **L1.** `model_catalog.py:364` uses `shared_mode`. The new test pins
  `VERIFIED_SYNTHETIC_CASES` for Claude with no OpenRouter configuration.
- **L2.** The RM-facing notices (`data_access.py:62-71`), the page labels, the
  confirmation text and the docs say "literal loopback". One non-user-facing TS doc comment
  still says "not on this machine" (see I1).
- **GPT-OSS mode has not regressed.** `mode = shared_mode and readiness is None`
  (`synthetic_eligibility.py:578-585`). `remote_test.readiness` (`remote_test.py:108-138`)
  checks every `shared_mode` condition except the D-095 decision ID, which `shared_mode`
  adds. GPT-OSS's mode is therefore unchanged. `RemoteTestModel` has no
  `development_mode`, so `main.py:711-712` falls back to `synthetic_dev_mode(config)` for
  it.
- **Claude's per-call safeguards have not regressed.** `ClaudeTestModel.development_mode`
  only replaces the mode predicate (`anthropic_runtime.py:656, 686`). The single-use ticket
  (`admitted`), the D-094 `check_messages` fallback, and `_ready`'s readiness, key, ledger,
  call-limit and preflight checks are unchanged and still run before every call. D-094
  still refuses the live `v1` token (tested).
- **The boundary vocabulary is unchanged.** `build_synthetic_boundary.py --check` reports
  it current.
- **No test was weakened or deleted** (see the checks above).

## Whole-candidate re-verification (prior gate's scope, on the changed content)

These checks were re-inspected on this content:

- **A1 split.** `shared_mode` is a strict subset of readiness; Claude does not depend on
  OpenRouter; there is one eligibility check and ticket; the adapter re-checks every call.
- **Policy routes** (`model_admin.py:2511-2560`):
  - admin dependency;
  - Origin and a dedicated rate limit (`DATA_ACCESS_RATE_LIMITED`);
  - `restrict_external:false` refused with 409 and audited;
  - `recheck` inside `change_lock`;
  - route CAS plus store CAS under `BEGIN IMMEDIATE`;
  - widening without `confirm_widen` refused with 400;
  - unreadable policy refused with 409;
  - strict JSON (`extra="forbid"`, `StrictBool`).
- **Store** (`model_admin_store.py:474-532`):
  - CHECK-constrained single row;
  - a type-strict read that raises on a malformed row, so the selector fails closed;
  - the policy and its audit row in one transaction;
  - the `applied` row is not pruned.
- **`SyntheticOnlyModel`.** It gates `complete` and the first `stream` iteration, and its
  `warm` is a no-op.
- **`data_access.py` in `BASIS_FILES`.** The basis moves to `598cfe14…`. Every earlier
  qualification, including Claude Balanced, becomes out of date through the existing
  mechanism, and no history is modified.
- **Offline proof.** The suite guard refuses non-local connections, and the refusal paths
  assert zero baseline, OpenRouter and Anthropic calls.

## Findings

### Critical / High / Medium

None.

### Low

None.

### Informational (non-blocking; no fix required for this gate)

- **I1.** `apps/frontend/src/aiAssistant.ts:714`: a TS doc comment still reads "an endpoint
  IT configured that is not on this machine". It is not user-visible, and it is the only
  remnant of the L2 wording. It can be aligned in any later touch.
- **I2.** `apps/assistant/ai_assistant/model_admin.py:331`: `restrict_remote` defaults to
  `False` for a directly constructed `ModelSelector` with no store. No production path
  reaches this today: the only production constructor is `open_selector`, called from
  `create_app`. A future direct caller would, however, silently get the exempt behaviour.
  A default of `True`, with tests opting out, would be stronger defence in depth.

## Status of prior findings

| Finding | Status |
| --- | --- |
| D104_REQG M1 (unmanaged non-loopback unrestricted while reported locked) | **Resolved**: option (a). Enforced on every non-injected path, the view reports the enforced state, and it is pinned by a test that a mutation breaks |
| D104_REQG L1 (Claude catalogue scope coupled to OpenRouter) | **Resolved** (`shared_mode`, tested) |
| D104_REQG L2 ("not on this machine") | **Resolved** for every user-facing string and doc; the one internal comment remnant is I1 |
| Original QG L1-L5 | Remain resolved (re-verified above) |

## Verdict

**PASS.**

This verdict applies only to content-id `1b8c84b2…e421e92` on base `0c6a632`, with the
evidence recorded above.

## Readiness

- The reviewed content is ready for the owner's commit decision. Nothing was committed here.
- Publication still needs:
  - explicit owner commit and push authorisation;
  - `python scripts/pre_pr_check.py` on the clean committed state, with no content change
    against this content-id;
  - an owner merge.
- Hosted CI is not evidenced here.
- The full assistant suite was not run by this gate.
- No Live, Sandbox or provider-status claim is made.
- Claude Balanced's existing qualification is out of date under basis `598cfe14…`. A new,
  separately approved paid qualification would be required; none was performed and nothing
  was spent.
