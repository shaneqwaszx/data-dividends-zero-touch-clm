# D-099 (proposed) Claude Sonnet 5.5 Balanced/Fast: final independent Quality Gate (PR #130)

Date: 2026-10-29. Reviewer: a fresh independent QG agent. I did not write, fix or review this
content before. This report is the only file I created, and it is uncommitted. I edited no
other file. I made no provider, inference or network call apart from read-only `gh` and
`git ls-remote` queries. I set no API key, ran no paid command, and made no commit, push, PR
comment or PR change.

## Verdict: PASS

The whole PR diff against `origin/main` meets every review criterion. No Critical, High or
Medium finding remains, and no fix is required for this candidate. The findings below are Low
or Info: documentation staleness, plus the two dormant-adapter items already recorded as
enablement prerequisites.

## Reviewed identity (checked at start and recomputed at end, unchanged)

- Worktree `C:\Users\shane\Desktop\claude-worktrees\assistant-claude-sonnet-console-20261029`,
  branch `feat/assistant-claude-sonnet-console`, clean before this report was written.
- HEAD = PR #130 head = remote branch = `541b10f08961777e54447d995a1e90e66e93a269`, tree
  `35dadafe267e0474ea7cec8bf49f45ddb2b1a32a`.
- Base `origin/main` = remote `main` = `8c7ea99cfb134a6edf2313f907fb913c4c21a1d6` (the PR #129
  squash). It is also the merge-base.
- `git diff origin/main...541b10f | sha256sum` =
  `bc0f0209b3f9c8dc46ba376799c43e8f0a579d5b9fda718d5886cd14a250deaf`. 16 files, +1779/-8.
- PR #130: OPEN, draft, MERGEABLE, `headRefOid` = `541b10f`.

## History verification

| Claim | Result |
| --- | --- |
| `1c515e8` is the content the earlier gate reviewed | VERIFIED. Its tree is `750cac42…` and its parent is `c2630cd`. `git diff c2630cd 1c515e8` over the 11 tracked files hashes to `c5b20254…50d`, which is the earlier gate's frozen hash. The three new code/test files and the integration report at `1c515e8` match the earlier gate's untracked sha256 values exactly (`5817cf7d…`, `ad4b518b…`, `37e6a59f…`, `0ce57552…`). The only other file is the earlier gate report itself. |
| `5d70ceb` merges `origin/main` with tree equal to `750cac42` | VERIFIED. Its parents are `1c515e8` and `8c7ea99`, its tree is `750cac42…`, and `git diff 1c515e8 5d70ceb` is empty. `8c7ea99`'s tree equals `c2630cd`'s (`fd17aa2c…`), so keeping our side in all three conflicts is lossless. `c2630cd` is not an ancestor of `8c7ea99`, which explains the conflicts. |
| `541b10f` changes the docs only | VERIFIED. `git diff --stat 5d70ceb 541b10f` shows one file, `.ai-pipeline/reports/D099_CLAUDE_SONNET_CONSOLE_INTEGRATION.md` (+34/-11). Its accuracy is assessed in the staleness section. |

## Criteria

| # | Criterion | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Claude entries are listed and never selectable. Every action is refused and audited before any network call, and only HR may act. | VERIFIED | `anthropic_profiles.availability` (anthropic_profiles.py:116-121) returns only `pending_authorisation` or `unavailable`. `model_admin.entry_for` (model_admin.py:1127-1150, unchanged) audits and refuses `REMOTE_NOT_AUTHORISED` or `PROFILE_NOT_SELECTABLE` before any adapter or probe. Test `test_every_action_is_refused_before_any_network_call_and_audited` passes for both settings: 6 audited refusals and `server.requests == []`. `test_only_hr_may_act_on_them` passes: RM, Client Onboarder and Director get 403 `MODEL_CONFIG_FORBIDDEN`. On the frontend, every action button is gated on `status === "selectable"` (AiModelManagement.tsx:774). The backend remains the authority. |
| 2 | Start-up never builds them. A stored Claude activation becomes "AI unavailable" with no automatic switching. | VERIFIED | `_build_stored` returns `PROFILE_UNAVAILABLE` at model_admin.py:620, before the `source == "code"` build at :640. `is_remote` (:549-555) is true for code entries, so `_restore` writes `UNAVAILABLE_ID`, not the baseline or GPT-OSS. Test `test_a_stored_claude_activation_is_never_served_and_switches_to_nothing` passes. No switching code was added. |
| 3 | The dormant adapter is safe. | VERIFIED | `require_offline_transport` accepts only `type(t) is httpx.MockTransport`. My offline probe confirmed that a real `AsyncHTTPTransport`, `None` and a MockTransport subclass are all refused (`TRANSPORT_NOT_ALLOWED`). `build()` refuses with either reason. Repo-wide grep: `anthropic_chat` is imported by no module other than its test; `anthropic_profiles` is imported only by `model_catalog` and `anthropic_chat`. `repr` shows only the profile id. Unapproved text is refused (`not_allowed`) with 0 requests sent. The key never appears in an error, repr or usage. `trust_env=False`, no redirects, and error bodies are bounded to 16 KiB. |
| 4 | No new key source, ledger or budget change, and no change to the GPT-OSS controls. | VERIFIED | `git diff --stat origin/main...541b10f` is empty for `budget.py`, `remote_test.py`, `remote_checks.py`, `key_sources.py`, `model_admin.py`, `guardrails.py`, `prompts.py`, `guide.py`, `context.py`, `openrouter.py`, `main.py`, `llm.py`, `synthetic_boundary.py`, `synthetic_eligibility.py`/`.json`, `model_qualification.py`, `telemetry.py`, `scripts/build_synthetic_boundary.py`, `assistant_eval/` and `apps/backend`. The GPT-OSS catalogue code (`_remote_entries`) is untouched. `_claude_entries` is appended after it. |
| 5 | The secret-scanner additions are correct and weaken nothing. | VERIFIED | Changes are additive only: rule `anthropic-key` `\bsk-ant-[a-z]+(?:\d{2})?-[A-Za-z0-9_-]{20,}`, and `AI_ASSISTANT_ANTHROPIC_API_KEY` and `ANTHROPIC_API_KEY` appended to the `ASSISTANT_CREDENTIALS` alternation. The alternation is used inside capturing groups with the existing `(?<![A-Za-z0-9_])` lookbehind. No existing rule, placeholder set or `CREDENTIAL_RULES` member changed. The new test builds its literals at run time and asserts that no value appears in the findings. |
| 6 | Qualification-basis impact | VERIFIED | Of the 21 `BASIS_FILES`, the only one in the diff is `synthetic_boundary.json`. I compared its keys one by one against a `git archive 8c7ea99` export in the scratchpad. All 10 keys are present on both sides. Only `code_vocabulary` differs: it adds exactly `adaptive, anthropic, claude, com, geo, sonnet, thinking`, removes nothing, and grows from 2867 to 2874 entries, still sorted with no duplicates. `company`, `conversation_vocabulary`, `documents`, `knowledge`, `note`, `prompt_vocabulary`, `schema`, `values` and `viewers` are identical. `build_synthetic_boundary.py --check` reports "synthetic boundary is current". The basis on the exported base is `b4049047884e9f2897a6ac3ebd232ccfe6482e6a6beb82aa50e6304ecb00fd22`. On the candidate it is `235030035ccc27e28320f35c4b887cdd04735f02692feb88ad0745666cfe1927`, as expected. No code pins, preserves or forces either value; the only occurrences are in docs and reports. D-099 C5 and AI_MODEL_CONFIGURATION section 13 both say that every earlier GPT-OSS qualification needs a paid requalification once this merges. |
| 7 | Synthetic boundary safety | VERIFIED | `test_remote_test` (67) and `test_synthetic_eligibility` (62) all pass. They cover user text, unapproved cases, viewers, values and documents, non-synthetic documents, invisible characters, and nothing being sent. The new test shows that the seven words are absent from the `conversation` and `assistant` vocabularies, and that a question or history using them returns `SYNTHETIC_TEXT_NOT_APPROVED`. |
| 8 | Existing tests were changed only for catalogue composition. | VERIFIED | `test_model_management` keeps its exact-equality status map, now with the two Claude rows added. The wrong-file test's source list grows from 2 to 4 entries. `test_reasoning_configurations` keeps the single-element unpacking (uniqueness still enforced) and now selects by `deployment == "openrouter"` or `OPENROUTER_PROFILE_ID`. No assertion was removed or loosened. The frontend test changes are additions only. |

## Findings (ranked)

No Critical, High or Medium finding.

### L1. LOW (carried, not reachable): a second `message_start` is not rejected (earlier QG F1)

- Location: `apps/assistant/ai_assistant/anthropic_chat.py:352-399`.
- Failure scenario: a later `message_start` naming another model is passed through, and the
  cost settles.
- Not reachable: the adapter is dormant, accepts only a mock transport and is never composed.
- Fix: before any enablement, reject a second `message_start` and drop the cost. This is
  already recorded in the integration report §4 prerequisites.

### L2. LOW (carried, not reachable): the D-095 ticket honours a constructor flag (earlier QG F2)

- Location: `anthropic_chat.py:226,234,267`.
- Failure scenario: a future composer builds the model with `synthetic_dev=True`, and the D-095
  mode is later withdrawn.
- Fix: before any enablement, call `synthetic_eligibility.mode(settings)` on every call, as
  `remote_test.py` does. This is already recorded.

### L3. LOW (docs): no PROJECT_STATE entry for D-099

- Location: `docs/PROJECT_STATE.md`, which the PR does not change.
- Each earlier AI Assistant slice (D-093 to D-098) added a dated section there. D-099 adds
  user-visible catalogue entries and moves the qualification basis, but has no section.
- The same file still describes D-095, D-097 and D-098 as "(branch, not merged)", although
  PR #129 is merged. That staleness comes from `main` and is not introduced by this PR.
- `check_project_state.py` passes.
- Not required for this candidate: the decision log, `AI_MODEL_CONFIGURATION.md` §13 and the
  reports carry the facts, and merge-status syncs are done in separate docs PRs in this repo.
- Recommendation: include D-099, and the merged status of D-095, D-097 and D-098, in the next
  status-sync docs change. Do not edit this reviewed head without a fresh review.

### I1. INFO: the Claude entries reuse the GPT-OSS "code entry" branches in `model_admin.py`

- This is earlier QG F3.
- The branches are safe while `selectable` is never true for Claude.
- "Route model management by provider" stays a hard enablement prerequisite.

### I2. INFO: the shared "Fast" note is GPT-OSS-worded

- Location: `AiModelManagement.tsx:783`, an unchanged line. This is earlier QG F5.
- No action is needed.

## Staleness and accuracy list (no code impact)

**Integration report** (`.ai-pipeline/reports/D099_CLAUDE_SONNET_CONSOLE_INTEGRATION.md` at
`541b10f`):

1. The header says "base = PR #129 head `c2630cd` … PR #129 untouched". That was true when the
   work started. The PR's base is now `origin/main` `8c7ea99` (squash of #129, same tree). §5
   records the merge, but the header was not refreshed.
2. §4 is headed "Implemented (uncommitted)". The work has been committed since `1c515e8`.
3. §5 says "Three documentation conflicts". One of the three
   (`apps/frontend/src/pages/AiModelManagement.test.tsx`) is a frontend test, not a document.
   The substantive claims are verified: `main`'s files are identical to `c2630cd`'s, our side
   was kept, and the merged tree equals `750cac42…`.
4. §5 gives "108 boundary and eligibility tests". This gate counts 67 in `test_remote_test` and
   62 in `test_synthetic_eligibility` (129), so 108 is an unnamed subset. The full-suite
   figures (2,698 tests, 14 Errno 24 failures, "289 of 289" in four unnamed files) were not
   reproduced here. The earlier gate did not cover them either. They are unverified, not shown
   to be false.
5. The report does not mention hosted CI for PR #130. Both Project CI runs on `541b10f` (run
   `40808110377` and run `40808209983`) failed every job in about 2 s. Each job had 0 steps,
   and the annotation reads "The job was not started because recent account payments have
   failed…". Hosted CI is not executed, not passing. The report also does not record the
   pre-PR check.
6. Accurate as written:
   - the §5 earlier-QG summary: PASS, diff `c5b20254…`, F1 to F5 (verified above);
   - the §4 prerequisites list, which now includes F1 and F2;
   - the §6 advice to schedule catalogue changes before the GPT-OSS requalification.

**Decision log** (`docs/decisions/DECISION_LOG.md`, D-099 header):

7. It says "Stacked on PR #129 (D-098)". PR #129 is merged (`8c7ea99`), so D-099 is now
   proposed against `main`.

**Earlier QG report** (`D099_CLAUDE_SONNET_CONSOLE_QUALITY_GATE.md`):

8. It describes "All changes are uncommitted" on base `c2630cd`. That is accurate as a record
   of what that gate reviewed, which is identical to `1c515e8`. It is not a current-state
   claim.

**PROJECT_STATE.md:** see L3.

## Commands and results (this session)

Assistant checks ran from `apps/assistant` with `PYTHONPATH=.`,
`PYTHONDONTWRITEBYTECODE=1`, and
`C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm\.venv\Scripts\python.exe`.

**Identity**
- `git rev-parse` / `git diff origin/main...541b10f | sha256sum` / `git ls-remote` /
  `gh pr view 130`: as recorded in the identity section, at start and at end.

**Assistant tests**
- `python -m pytest tests/test_claude_console.py tests/test_remote_test.py tests/test_synthetic_eligibility.py tests/test_model_management.py tests/test_reasoning_configurations.py tests/test_d098_recovery.py tests/test_spending_controls.py -q -p no:cacheprovider -o faulthandler_timeout=300 --junitxml=<scratchpad>/focused.xml`:
  - exit 0;
  - JUnit: tests=334, failures=0, errors=0, skipped=0, time 145 s;
  - per file: claude_console 41, remote_test 67, synthetic_eligibility 62,
    model_management 52, reasoning_configurations 7, d098_recovery 79, spending_controls 26.

**Boundary and basis**
- `python scripts/build_synthetic_boundary.py --check`: "synthetic boundary is current", exit 0.
- `qualification_basis()`: candidate `235030035ccc…1927`; base (from the `git archive 8c7ea99`
  export) `b4049047884e…fd22`.
- JSON key-by-key boundary comparison against the base export: as in criterion 6.

**Repository root**
- `python -m pytest tests/test_check_secrets.py -q --junitxml=…`: tests=33, failures=0,
  errors=0.
- `python scripts/check_secrets.py`: "Secret scan passed", exit 0.

**Lint and types**
- `ruff check --no-cache` and `ruff format --check --no-cache` on `anthropic_chat.py`,
  `anthropic_profiles.py`, `model_catalog.py`, `config.py`, `test_claude_console.py`,
  `test_model_management.py` and `test_reasoning_configurations.py`: "All checks passed!" and
  "7 files already formatted".
- `ruff check` on `scripts/check_secrets.py` and `tests/test_check_secrets.py`: passed.
- `ruff format --check` on the same two files reports reformatting under ruff defaults (there is
  no root ruff config). It reports the same on the base `8c7ea99` versions. The flagged lines
  are pre-existing, and none of the PR's added lines is flagged.
- `MYPYPATH=. mypy --no-incremental` on `anthropic_chat.py`, `anthropic_profiles.py`,
  `model_catalog.py`, `config.py` and `test_claude_console.py`: no error in those files.
  - 6 errors are reported in transitively imported, unchanged lines: `test_model_management.py`
    :77, :353, :373, :1194, :1201, and `remote_fixtures.py:75`.
  - The same `test_model_management.py` errors (:77, :353, :373, :1190, :1197) appear on the
    base export, so they pre-exist.

**Frontend**
- `npx vitest run src/pages/AiModelManagement.test.tsx`: 41/41 passed.
- `npx tsc -b --pretty false`: exit 0.
- `git status` afterwards: clean.

**Hygiene and probe**
- `git diff --check origin/main...541b10f`: clean, exit 0.
- Offline adapter probe (scratchpad script, MockTransport only): results as in criterion 3.

**Publication gate and CI**
- `python scripts/pre_pr_check.py`, read-only, on clean `541b10f`: `SUMMARY: PASS (0 unsafe
  conditions, 1 warning(s))`. The warning is the expected
  `API/config/shared type files changed: apps/assistant/ai_assistant/config.py`. All five
  sub-checks passed: project_state, architecture, tooling_config, policy_authority and
  external_provider_readiness.
- Does it need re-running? No. The head is unchanged since the earlier PASS on `541b10f`, and I
  reproduced the same result. Run it again only if the head changes. This report is untracked,
  so it would show in the working-tree inventory until it is committed or moved.
- `gh api …/actions/jobs/123232096014` and the job's annotations: 0 steps, billing block (see
  item 5 in the staleness list).

## Change statement (verified)

- **Changed:**
  - API/type: the overview lists two more entries, with a new `details.thinking` key;
  - configuration: one optional setting, `AI_ASSISTANT_ANTHROPIC_DECISION`;
  - frontend labels and reason texts;
  - secret-scanner rules (additive);
  - qualification basis: through the owner-approved boundary regeneration.
- **Unchanged:**
  - schema, connector, business rules and mapping;
  - auth/RBAC;
  - budget, ledger and key sources;
  - GPT-OSS settings, fingerprints, prompts, guardrails, catalogue and runtime;
  - architecture ownership;
  - provider status (Mock/offline only, no Live claim);
  - runtime answers (no Claude answer can be served).

## Readiness

- This PASS covers only the exact identity above: head `541b10f`, tree `35dadafe…`, diff
  `bc0f0209…`.
- Hosted CI has not executed (billing block). The owner must accept local evidence for it or
  re-run it.
- Publication from draft and merge need explicit owner authorisation. Repository-owner humans
  merge PRs.
- D-099 stays PROPOSED, and Blocker B1 (Anthropic spending controls) stays open.
- Merging makes every GPT-OSS qualification out of date. Requalifying needs its own paid-call
  approval.
