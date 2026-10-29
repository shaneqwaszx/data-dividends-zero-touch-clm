# D-099 (proposed) Claude Sonnet 5.5 Balanced/Fast on AI Models: independent Quality Gate

Date: 2026-10-29. Reviewer: fresh independent QG agent. I did not write or fix the reviewed
content. This report is the only file I created. I made no source, test, config or doc edit,
no network or provider call, set no API key, ran no paid command, and made no commit, push or PR.

## Verdict: PASS

All eight claimed criteria were verified against the code and by running the checks myself.
The candidate keeps both Claude configurations listed and never usable. The adapter is dormant
and composed nowhere. The owner-approved boundary regeneration is exactly the seven
code-vocabulary words. No budget, ledger, key-source, model-admin, guardrail or GPT-OSS behaviour
changed. The findings below are LOW or INFO only. None blocks this candidate. Two (F1, F2) are
prerequisites to fix before any future decision to enable Claude.

## Reviewed content identity (frozen; recomputed at start and end, unchanged)

- Worktree `C:\Users\shane\Desktop\claude-worktrees\assistant-claude-sonnet-console-20261029`,
  branch `feat/assistant-claude-sonnet-console`, HEAD = base = `c2630cd13917ecf7f5f07c850313213d62049bad`
  (PR #129 head, D-098). All changes are uncommitted.
- `git diff c2630cd | sha256sum` = `c5b202544578c165b6f340f675acb362c24c7f0ec07c08eb31a6c96e3271e50d`
- Untracked files (sha256):
  - `apps/assistant/ai_assistant/anthropic_chat.py`: `5817cf7d501f236ba5a374fe113dd15202c16604b47c78f3bf5cf651fde2ded1`
  - `apps/assistant/ai_assistant/anthropic_profiles.py`: `ad4b518b95ae05029379660a87773ac2c92277d91099a8b79c34002152909cad`
  - `apps/assistant/tests/test_claude_console.py`: `37e6a59f1f04a715bbf1ed61ade24877ec928f066c6ffb03ce257d1cf58e3e91`
  - `.ai-pipeline/reports/D099_CLAUDE_SONNET_CONSOLE_INTEGRATION.md`: `0ce57552a699a295ccad839e899c30241bb3c76ce238b9d6922bb881d23c5cc6`
- Tracked changes: 11 files, +185/-8: `config.py`, `model_catalog.py`, `synthetic_boundary.json`,
  `test_model_management.py`, `test_reasoning_configurations.py`, `AiModelManagement.tsx`/`.test.tsx`,
  `DECISION_LOG.md`, `AI_MODEL_CONFIGURATION.md`, `scripts/check_secrets.py`, `tests/test_check_secrets.py`.

## Criteria

| # | Claim | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Listed, never selectable; every action refused and audited before any call; startup never builds; stored activation becomes AI unavailable; no automatic switching | VERIFIED | `anthropic_profiles.availability` (anthropic_profiles.py:116-121) returns only `pending_authorisation`/`ANTHROPIC_NOT_AUTHORISED` or `unavailable`/`ANTHROPIC_PROVIDER_CONTROLS_MISSING`. It matches exactly `D-099` (I probed `d-099` and ` D-099`: still not authorised). The env name is `AI_ASSISTANT_ANTHROPIC_DECISION` (env_prefix). `model_admin.entry_for` (model_admin.py:1127-1150, unchanged) refuses any non-selectable entry with an audit before any adapter or probe. The connection-test, qualification, activate and rollback routes all go through it. `_build_stored` returns `PROFILE_UNAVAILABLE` before the `source == "code"` build branch (model_admin.py:618-621). `_restore` uses `is_remote()` (`source == "code"`), so a stored Claude activation becomes `ai_unavailable`, never another model. Tests: `test_every_action_is_refused_before_any_network_call_and_audited` (6 audited refusals, `server.requests == []`) and `test_a_stored_claude_activation_is_never_served_and_switches_to_nothing`. No switching code was added. |
| 2 | Distinct fingerprints; qualifications never shared; IT files cannot take the ids | VERIFIED | `identity()` covers profile, provider, base URL, API version, all request fields, timeout and prices. `eligible_run` is keyed by profile id + fingerprint + basis, and cross-checks return `NOT_QUALIFIED` (test). `ProfilesFile` reserves `anthropic_profiles.PROFILE_IDS` (model_catalog.py:124). |
| 3 | Dormant adapter behaviour | VERIFIED (see F1, F2) | `require_offline_transport`: `type(t) is httpx.MockTransport` only. `build()` always raises `ProfileConfigError`. The only `apps/` importer of `anthropic_profiles` is `model_catalog`; nothing imports `anthropic_chat` (grep plus the test's rglob). Request: pinned URL, `anthropic-version: 2026-10-21`, body exactly model/max_tokens/thinking/output_config/system/messages/stream (test asserts equality). Send rule: ticket (when `synthetic_dev`) or `check_messages`, then the byte bound, then shape, all before any send. System mapping refuses a system message after history, a missing system message, a non-user end, or non-alternating turns. Model pinned at the first `message_start` before any text. Tier/geo/speed give `provider_mismatch`. Cache tokens, missing or malformed counts drop the cost. Refusal gives `content_filter`, `max_tokens` gives cut short, an unfinished stream or missing `message_delta` gives `upstream_midstream` with no cost. Spend-limit 400/429 gives `payment_key_limit`. Thinking and signature deltas are never yielded. My probes found no credential in any repr or error, including a 500 body and an `error` event carrying the key. |
| 4 | Provider/spending verdict; nothing else changed | VERIFIED | `git diff c2630cd --stat` over `budget.py`, `remote_test.py`, `remote_checks.py`, `key_sources.py`, `model_admin.py`, `guardrails.py`, `prompts.py`, `guide.py`, `context.py`, `openrouter.py`, `main.py`, `llm.py`, `synthetic_boundary.py`, `scripts/build_synthetic_boundary.py` and `assistant_eval/`: empty. `synthetic_eligibility.json` is unchanged. No ledger, key source or budget code was added. |
| 5 | Boundary regeneration: exactly seven code-vocabulary additions | VERIFIED | `PYTHONPATH=. python scripts/build_synthetic_boundary.py --check` printed "synthetic boundary is current" (exit 0). A JSON key-by-key comparison against `c2630cd` shows the same 10 keys. Only `code_vocabulary` differs: added `adaptive, anthropic, claude, com, geo, sonnet, thinking`, removed none, 2867 to 2874. Schema, note, company, documents, viewers, values, knowledge, conversation and prompt vocabularies are identical. The generator and `synthetic_boundary.py` are unchanged. The boundary refusal suites pass (test_remote_test, test_synthetic_eligibility: outside-case, viewers, unapproved names and documents, values, invisible characters, nothing sent). The new test proves the seven words are not in the conversation or assistant vocabularies, and that a question or history using them is refused. |
| 6 | Qualification basis | VERIFIED | Candidate: `235030035ccc27e28320f35c4b887cdd04735f02692feb88ad0745666cfe1927`. I recomputed the base from a `git archive c2630cd` export (scratchpad): `b4049047884e9f2897a6ac3ebd232ccfe6482e6a6beb82aa50e6304ecb00fd22`. The only basis file changed is `synthetic_boundary.json` (in `BASIS_FILES`). Nothing forces or preserves the old basis. D-099 C5 and AI_MODEL_CONFIGURATION section 13 state that GPT-OSS needs requalification after merge. |
| 7 | Existing tests changed only for composition | VERIFIED | `test_model_management` keeps the exact-equality status map, now with the two Claude rows. The wrong-file test lists the four fixed sources. `test_reasoning_configurations` still uses single-element unpacking (uniqueness kept), selecting by `deployment == "openrouter"` or `OPENROUTER_PROFILE_ID`. No assertion was removed or loosened. Frontend test changes are additions only. |
| 8 | Secret scanner | VERIFIED | Rule `anthropic-key` `\bsk-ant-[a-z]+(?:\d{2})?-[A-Za-z0-9_-]{20,}` matches api03, admin01, oat01 and sid01 shapes and ignores short tails. `AI_ASSISTANT_ANTHROPIC_API_KEY` and `ANTHROPIC_API_KEY` were added to `ASSISTANT_CREDENTIALS`. The test builds its literals at run time and asserts no value appears in the findings. The scan covers untracked files (`ls-files --others`). |

## Commands and results (this session)

Assistant commands ran from `apps/assistant` with `PYTHONPATH=.`, using
`C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm\.venv\Scripts\python.exe`.

- `python -m pytest tests/test_claude_console.py tests/test_remote_test.py tests/test_synthetic_eligibility.py tests/test_model_management.py tests/test_reasoning_configurations.py tests/test_d098_recovery.py -q -p no:cacheprovider -o faulthandler_timeout=300`: exit 0, 308 passed, 0 failed. The repository `addopts -q` plus `-q` hides the summary line, so I counted the progress dots.
- `python -m pytest tests/test_claude_console.py --junitxml=<scratchpad>`: tests=41, failures=0, errors=0, skipped=0.
- `python -m pytest tests/test_warm_up_security.py tests/test_model_factory.py tests/test_phase_b_live.py tests/test_budget_ledger.py tests/test_grounding.py tests/test_guardrail_negation.py -q`: exit 0, no failure or error marker. The summary was suppressed by the double `-q` and only the output tail was captured, so I did not record an exact count. It is about 1,000 tests by the progress percentages.
- `PYTHONPATH=. python scripts/build_synthetic_boundary.py --check`: "synthetic boundary is current", exit 0.
- `python -c "from ai_assistant.model_qualification import qualification_basis as q; print(q())"`: `235030035ccc…1927`.
- Repository root: `python -m pytest tests/test_check_secrets.py -q`: 33 passed. `python scripts/check_secrets.py`: "Secret scan passed", exit 0.
- `python -m ruff check --no-cache` and `ruff format --check --no-cache` on `anthropic_chat.py`, `anthropic_profiles.py`, `model_catalog.py`, `config.py`, `test_claude_console.py`, `test_model_management.py` and `test_reasoning_configurations.py`: "All checks passed!" and "7 files already formatted".
- `MYPYPATH=. python -m mypy --no-incremental` on `anthropic_chat.py`, `anthropic_profiles.py`, `model_catalog.py`, `config.py` and `test_claude_console.py`: no error in any of these files. It reports 6 errors in transitively imported `tests/test_model_management.py` (lines 77, 353, 373, 1194, 1201) and `tests/remote_fixtures.py:75`. All are in lines this change does not touch. The same `test_model_management` errors appear on the `c2630cd` export (lines 77, 353, 373, 1190, 1197), so they pre-exist.
- `apps/frontend`: `npx vitest run src/pages/AiModelManagement.test.tsx`: 41/41 passed. `npx tsc -b --pretty false`: exit 0, no output.
- `git diff --check c2630cd`: clean. The four untracked files have no trailing whitespace and no CR bytes. `git status` after tsc and vitest showed no new files.
- Ad-hoc offline adversarial probes of the adapter (a scratchpad script, MockTransport only) gave the results in claim 3 and F1.

## Findings (ranked)

### F1. LOW: a second `message_start` is silently ignored, so model pinning is first-event only

- `apps/assistant/ai_assistant/anthropic_chat.py:352-399`. Once `started` is true, a later
  `message_start` matches no branch and falls into the "event types added later carry no text"
  pass-through.
- Failure scenario: a stream sends `message_start(model=claude-sonnet-5-5)`, text, then
  `message_start(model=claude-opus-5-5)` and more text. My probe showed both texts yielded, the
  cost settled at Sonnet prices and `anomalies == ()`.
- Impact: nil today, because the adapter is dormant, mock-only and never composed. It is a
  fail-open gap in a defensive check that D-099 C4 describes as model pinning.
- Fix (before any enablement): treat a repeated `message_start` as `protocol` with
  `model_mismatch`/`usage_malformed`, or at least record an anomaly that drops the cost. Add a
  test.

### F2. LOW: the D-095 ticket is honoured from a constructor flag, not from the live D-095 mode

- `anthropic_chat.py:226,234,267`. `synthetic_dev` is fixed when the object is built. GPT-OSS
  (`remote_test.py:373-375`) honours a ticket only when `synthetic_eligibility.mode(settings)`
  holds at call time.
- Failure scenario: a future `build()` passes `synthetic_dev=True` and the D-095 decision or
  D-094 readiness is later withdrawn. The adapter would still accept ticketed messages.
- Not reachable now, because `build()` always refuses.
- Fix (before any enablement): evaluate `synthetic_eligibility.mode(settings)` per call, as
  `remote_test` does, or document that the composer must rebuild the model whenever the mode
  changes.

### F3. INFO: model admin's "code entry = GPT-OSS" branches now also see Claude entries

- `model_admin.py:549-555` (`is_remote`, documented as "A GPT-OSS configuration") and the
  `source == "code"` branches at :575, :640, :1335, :1418, :1467, :1479 and :1626.
- These are safe today: every branch is after `entry_for` or the `selectable` check, and the
  Claude entries are never selectable. `is_remote` returning true is what gives the correct
  D-098 R6 behaviour.
- If a Claude entry ever became selectable, `_build_stored` would build a GPT-OSS
  `RemoteTestModel` under a Claude id. The interrupted-run billing check would also consult the
  GPT-OSS ledger.
- The implementer's report (section 4, prerequisites) already records "route model management's
  code-entry branches by provider". Keep that as a hard prerequisite.

### F4. INFO: stale or minor inaccuracies in the implementer's report (a candidate file)

- `.ai-pipeline/reports/D099_CLAUDE_SONNET_CONSOLE_INTEGRATION.md`:
  - Section 5 still records "797 passed, 1 failed (the B2 boundary-currency test)" and
    "Independent QG: not run yet … after B2 is decided". B2 is now applied: `--check` passes and
    the focused suites pass.
  - Section 5 says `test_claude_console.py` has 40 tests. It collects 41.
  - Section 5 says the mypy errors are in modules "this work … does not change", but
    `test_model_management.py` is changed. Its errors are only in unchanged lines.
  - Section 6 advises bundling the catalogue fixes "with the B2 regeneration so requalification
    happens once". That advice is overtaken now that B2 has been applied alone.
- None of this changes the code verdict. Refresh it in the integration/publication record. This
  is not a reason to reopen this gate, which does not cover documentation-only edits to that
  report.

### F5. INFO: the AI Models page's Fast note is GPT-OSS-worded but also shows on Claude Fast

- `apps/frontend/src/pages/AiModelManagement.tsx:783` (unchanged line) renders
  "Fast is the same model, endpoint and limits with less reasoning …" for any
  `reasoning_effort === "low"` row, so Claude Fast gets it too.
- It is broadly accurate. Claude Fast also changes the thinking mode, which the row already
  shows as "Thinking: between tool calls only".
- No action is needed unless the owner wants provider-specific wording.

## Security and data handling

- No credential is read anywhere in the new code paths. `anthropic_profiles` reads none.
- The adapter holds a `SecretStr`, and its `__repr__` shows only the profile id.
- Provider error bodies are read to 16 KiB at most, only to classify. They are never kept or
  raised.
- `trust_env=False`, no redirects, and identity encoding only.
- The catalogue view shows the host and model id, with no path and no variable name.
- The secret scanner was extended. The repository scan, including untracked files, is clean.
- No KYC/PII, sponsor artefact or provider payload is added.
- Evidence class: Mock/offline only. Nothing is claimed Live.

## Change statement (verified)

- Changed:
  - API/type: the overview lists two more entries (new `details.thinking` key; the frontend
    type already accepts a string map);
  - configuration: one optional setting, `AI_ASSISTANT_ANTHROPIC_DECISION`;
  - frontend labels and reason text;
  - secret-scanner rules;
  - qualification basis: through the owner-approved boundary file.
- Unchanged:
  - schema, connector, business rules, mapping;
  - auth/RBAC (forbidden roles are still refused and audited);
  - budget and ledger;
  - GPT-OSS runtime, settings, prompts and catalogue;
  - architecture ownership;
  - provider status;
  - runtime answer behaviour (no Claude answer can be served).

## Readiness

- Governance and publication: the candidate passes this gate for the exact content identity
  above. Publication still needs an integrated acceptance and explicit owner authorisation, per
  `docs/DEVELOPMENT_WORKFLOW.md`.
- D-099 stays PROPOSED. Blocker B1 (Anthropic spending controls) remains an open owner decision.
- A merge makes every GPT-OSS qualification out of date (basis `235030035ccc…`). Requalifying
  needs its own paid-call approval.
- This gate does not cover the implementer's separate full-suite run.
