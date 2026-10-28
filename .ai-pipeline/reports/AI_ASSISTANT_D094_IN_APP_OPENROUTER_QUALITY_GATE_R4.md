# AI Assistant D-094 in-app OpenRouter test mode - Independent Quality Gate R4 (fourth check)

Date: 2026-10-28. Reviewer: a fresh, independent QG. This reviewer did not author or remediate
the candidate and did not run R1, R2 or R3.
Scope: the delta since R3 (`AI_ASSISTANT_D094_IN_APP_OPENROUTER_QUALITY_GATE_R3.md`, PASS WITH
MINOR FIXES on CONTENT ID `967024b4…`) and the evidence that delta invalidated. The delta has
six parts: fix 1 (the live-case `from` refusal), R3-1 docs, R3-A2 timestamps, R3-A3 words, the
qualification `done_turns` display, and the new tests.

## Verdict

**FAIL** (one bounded fix; everything else in the delta verified)

Fix 1 resolves the live-case over-blocking. A realistic live-like Garden snapshot is now inside
the boundary, and the model answers it end to end. Non-synthetic observation values are still
refused.

The brief asked whether every document name in a discrepancy's `from` is necessarily in
`snapshot.documents`. **It is not.**

- `ClmBackendClient.load_case` (`apps/assistant/ai_assistant/clm_client.py:96-101`, `:108-110`)
  replaces the document list with `[]` when that request fails with any non-authentication
  error, or when the reply is not a list.
- `check` then passes the document condition vacuously (`synthetic_boundary.py:281-285`).
- Fix 1 removed the only remaining check on those names, `from` compared as a value
  (`synthetic_boundary.py:236-239`).

So an unapproved document name now reaches the remote model when two things hold: the document
list fails, and every word of the name is in the system vocabulary. The system vocabulary holds
about 2,800 code words, including the name parts `tan`, `wei`, `lee` and `ng`. Reproduced end to
end: one request reached the mock OpenRouter and carried `Tan Wei Lee.pdf`. Under the R3 code
this name was refused (`SYNTHETIC_VALUE_NOT_APPROVED`).

How serious it is:
- **Likelihood is low.** It needs a backend error on the document list, plus a non-fixture
  document on the synthetic GARDEN BUSINESS case.
- **Impact is a file name only.** Observation values are still checked.
- **But it is a fail-open regression in the data boundary**, introduced by this delta, and it
  contradicts two documented claims: "Any doubt fails closed" (`synthetic_boundary.py:5-6`) and
  T4's "every document has an approved fixture file name".

The quality-gate skill reserves PASS WITH MINOR FIXES for non-security corrections, so this
gate cannot pass it as a minor fix. The fix is small (see R4-1).

## Frozen content identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\assistant-openrouter-local-test-20261027`,
  branch `feat/assistant-openrouter-local-test-20261027`. HEAD, base and origin/main are all
  `c36b8aff5213037d9ed0710e69f8b9afc7c8c614`.
- Uncommitted: 18 modified tracked files and 6 new product files. Untracked R1 to R3 reports
  are not product. Nothing is staged (27 status lines in total).
- Tracked diff sha256 `c6ce179685ffb7c750839f16d2cff0b60550f20f1854c86f023008956593e2d6`.
  `diff --stat`: 18 files, +740/−477, identical with `--ignore-cr-at-eol`.
- Per-file hashes: `remote_checks.py` `f874bab4…` and `remote_test.py` `fc57406e…` are
  unchanged from R3. `synthetic_boundary.py` is `2a27fd7d…`, `.json` `fe638667…`,
  `build_synthetic_boundary.py` `b7dfd34d…` and `test_remote_test.py` `e6d7d3c6…` (all changed).
- File times: every other modified runtime and frontend file predates the R3 report
  (01:33Z). The exceptions are `assistant_eval/qualification.py` (01:34Z) and
  `synthetic_boundary.py` (01:38Z), so R3's frontend and runtime evidence is reused for the
  others.
- **CONTENT ID at START: `66a1c3d299353800fd52d63f0f53e1745f676f0787d9ba879fe9231cfd646101`**
  (matches the brief). It was re-computed after all checks and before writing this report,
  with the same value. The END value is on the last line.

## Findings

| # | Severity | Location | Finding |
| --- | --- | --- | --- |
| R4-1 | **Low likelihood, security boundary (blocks PASS)** | `apps/assistant/ai_assistant/synthetic_boundary.py:233-239` with `:281-285`; `apps/assistant/ai_assistant/clm_client.py:96-101,108-110`; `apps/assistant/ai_assistant/context.py:205-211` | **An unapproved document name can reach the remote model when the document list fails.** **The code comment's premise does not hold.** It says "every document on the case must have an approved name, checked in `check`", but `check` checks only `snapshot.documents`, and `load_case` sets that to `[]` on a non-authentication error (for example a 500 or 404) or on a non-list reply. The reconciliation observations come from the separate case summary, so they still name the documents. `context._discrepancies` puts `document_display_name` into `from`. That name is backend data taken from the `X-Document-Name` upload header, which the user sets. Fix 1 stopped comparing `from` with approved values, and the system-message word screen is the only remaining check. Reproduced: with `documents=[]`, `Tan Wei Lee.pdf` and `garden-business-tan-wei-lee.pdf` pass `check()`, while `client-passport.pdf` and `Tan Ah Kow NRIC.pdf` are refused by the word screen. **End to end** (Journey, document list returning 500), the question was `answered_by: model`, 1 request reached the mock OpenRouter, and the name appeared in the prompt. With the document listed normally, every unapproved name is refused `SYNTHETIC_DOCUMENT_NOT_APPROVED` (3 probes). The backend never deletes documents and lists superseded ones, and the document route has the same `CASE_SCOPED` policy as the summary. So outside a failed load the premise holds. **Expected fix (not applied):** in `check`, refuse `SYNTHETIC_DOCUMENT_NOT_APPROVED` when any reconciliation observation's `document_display_name` in `snapshot.summary` is not in `approved.documents`. This is independent of the document list and keeps fix 1 for source labels. Alternatively, make a failed document load refuse in remote mode, which needs the snapshot to record that the load failed. Add a test: document list failed, plus an unapproved name in an observation, is refused. |
| R4-A1 | Advisory (within the accepted hand-built-history class) | `synthetic_boundary.py:60-63,143-145` | `_TIMESTAMP` accepts any `\d{2}:\d{2}` time and any year. A hand-built assistant turn can therefore hide a bare date of birth behind a fake time: `… "Keep registry value". 12 Mar 1985, 00:00` passes, and so does `1985-03-12T00:00`. Chained shapes such as `12 Jan 3456, 70:00 12 Jan 7890, 12:34 …` carry many digits. Bare dates are still refused (`12 Mar 1985`, `1985-03-12`), and user turns and user history do not strip timestamps (4 probes refused). This needs a deliberately crafted HTTP request. The panel sends only real answers, and R3 accepted that a hand-built assistant turn can already carry unlimited digits (R3-1 c), so this adds no new capability. Optional hardening: accept only a plausible service time (hour < 24, minute < 60, year at or after 2024). |
| R4-A2 | Advisory (docs completeness) | `docs/integration/AI_MODEL_CONFIGURATION.md:182-184`; `apps/assistant/README.md:539-541`; `docs/PROJECT_STATE.md:1150-1152` | R3-1 is closed. All five places now say the screen guards against accidental entry, not deliberate encoding, name spelled-out numbers and say the cap is per request. The "split numbers" overclaim is gone. The full list (punctuation or Morse codes, hand-built history) appears only in `DECISION_LOG.md:1290-1295` and the `synthetic_boundary.py:25-28` docstring; the other three use a shorter, non-exhaustive list. Optional. |
| R4-A3 | Advisory (fail-closed) | `assistant_eval/qualification.py:313-316` | `self._stop(len(turns))` runs before `verify_now()`. A remote qualification that finishes all turns but crosses the deadline, or is cancelled at that moment, is recorded as `error`/`cancelled` without the G-8 summary. Each call is still verified by the model itself (`remote_test.py`, unchanged), so the ledger stays correct. The display fix itself works: the journey test asserts `done_turns == 2`. |
| R2-5 | Advisory (carried) | new files | New files are LF and `remote_checks.py` is CRLF, as before. `PROJECT_STATE.md` is 680 CRLF / 474 LF against 655 / 474 in HEAD: the 25 added lines are CRLF and no LF line was added. |

## Delta verification

| Delta item | Result | Evidence |
| --- | --- | --- |
| 1. Live-case `from` fix | **Over-blocking fixed; under-blocking residual R4-1** | I traced every way a value reaches `from` (`backend/app/services/reconciliation.py:518-613`). `ONBOARDING_REQUEST`/`USER_INPUT` with no environment; the registry provider and environment enums (`ACRA MOCK`); `EXISTING_VERIFIED_TARGET_CASE`; and `HUMAN_REVIEW`. The only free text is `document_display_name` (`source_display_name=document.display_name`, 5-99 characters, from the upload header). The domain validator allows display names only on `DOCUMENT_IDP` observations (`domain/reconciliation.py:252-253`). **Probes through `check()`, 16 cases:** a live-like UEN discrepancy (form, ACRA MOCK and the conflicting profile), plus HUMAN_REVIEW correction, rejected (MISSING) and existing-case variants, are all inside. A non-synthetic form value (`201511222D`) and document value (`S1234567D`) are refused `SYNTHETIC_VALUE_NOT_APPROVED`. Listed unapproved document names are refused (3). Failed-list cases: see R4-1. **End to end** (Journey with that live-like summary): `/chat` and `/chat/stream` were both answered by the model with the D-094 notice (2 requests). The non-synthetic value gave `case_data … SYNTHETIC_VALUE_NOT_APPROVED` with **0** requests. |
| 2. R3-1 docs | **Closed** (R4-A2 optional) | I re-read the five passages; the wording is correct and no overclaim remains. |
| 3. R3-A2 timestamps | **Verified; R4-A1 advisory** | The real fallback answer `… retrieved 28 Oct 2026, 01:21 UTC.` and an ISO timestamp pass as assistant history. A bare readable or ISO date is refused, and so is a date without the comma. The user question and user history with a date plus time are refused. A system message is unaffected. **End to end:** a refused turn's case-data answer (with a time), sent back as assistant history, was answered by the model on `/chat/stream`, and so was the following turn. |
| 4. R3-A3 words | **Verified** | All 11 words are in `conversation_vocabulary`; none is a name, place or identifier. `Who needs to fix it?`, `OK, thanks.`, `What is blocking this case?`, `How long will this take?`, `Okay, I will wait.` and `Is it fixed?` are all inside. The boundary file is current (`--check`). |
| 5. `done_turns` | **Verified** (R4-A3 note) | `qualification.py:313-314` was re-read. The journey test, which asserts `done_turns == 2`, passes. |
| 6. New tests | **Verified, with a gap** | The three new tests pass and assert what the brief says. None covers a failed document list (R4-1). |

## Regression re-confirmation

| Check | Result |
| --- | --- |
| R1/R2 probes (`check()`): CJK and full-width, NRIC question, tag characters, circled letters, ZWSP, `s 85 12 17`, 4 number groups | 7/7 refused `SYNTHETIC_TEXT_NOT_APPROVED` |
| Default-off, every-condition, without-decision, HR activation/rollback journey, call limit, wrong provider, failed call | Pass within `test_remote_test.py` (64/64) |
| Local D-093 flows and harness | `test_model_management.py` + `test_ai_assistant.py` + `test_remote_test.py`: 130/130. Full suite: see below |
| Guardrails | `guardrails.py`, `test_guardrail_negation.py` and all of `apps/backend` are unchanged against `c36b8af` (`git diff --quiet`, exit 0) |

## Checks run (this session, on CONTENT ID `66a1c3d2…`)

| Check | Result |
| --- | --- |
| Content ID start / before report / end | `66a1c3d2…646101` each time |
| `tests/test_remote_test.py` (`-p no:cacheprovider`, `-B`) | 64 passed |
| remote + model management + ai_assistant tests | 130 passed, 0 failed |
| Full assistant suite (`-p no:cacheprovider`, `-B`, `faulthandler_timeout=300`, junitxml in scratch) | **2439 tests**: 2425 passed, 14 failed. All 14 are `OSError: [Errno 24] Too many open files` (junit-verified), in test_model_factory 1, test_phase_b_live 1, test_required_p2 5 and test_streaming_resources 7. Those 4 files in isolation: **288 passed**. This matches the implementer's evidence and the R1 to R3 pattern |
| ruff check / ruff format --check (`--no-cache`) | All checks passed; 111 files already formatted |
| mypy `ai_assistant assistant_eval scripts tests/test_remote_test.py` (cache in scratch) | Success: no issues in 59 source files |
| `scripts/build_synthetic_boundary.py --check` | synthetic boundary is current |
| `check_project_state`, `check_architecture`, `check_policy_authority`, `check_secrets`, `check_external_provider_readiness`, `check_tooling_config` | all PASS |
| `git diff --check c36b8af` | clean |
| Byte-level trailing whitespace, final newline and EOL on the 6 new files plus the 4 docs and `qualification.py` | clean; EOL as in R2-5 |
| Boundary probes (`probe_boundary4.py`, `probe_a2.py`) | 51 checks: 0 unexpected, 7 informational (R4-1 and R4-A1 residuals) |
| End-to-end probes (`test_probe_journey4.py`, Journey and mock OpenRouter) | 4 passed. Live-like: 2/2 answered by the model. Non-synthetic value: 0 requests. Failed document list: 1 request carrying the unapproved name (R4-1). Timestamped history: answered by the model |
| Frontend `tsc` / vitest | Not re-run: the frontend files are unchanged since R3 (file times), so R3's evidence (exit 0; 31/31) is reused |

Probes are in
`C:\Users\shane\AppData\Local\Temp\claude\C--Users-shane--claude-spares-spare-6YcPey\583f9cb6-22ae-4b09-9725-20ab186f8738\scratchpad\qg094r4\`.
No real OpenRouter call was made and no non-loopback host was contacted. No `.env` was read,
Mongo was not used, and no real `OPENROUTER_API_KEY` was set or read. Ports 8791, 8192 and 5191
were not used or touched. The real-stack browser E2E is the implementer's evidence; I did not
re-run it. My live-like evidence is built from the backend's observation code instead.

## Required for PASS

1. R4-1: in `check`, refuse any reconciliation observation `document_display_name` in
   `snapshot.summary` that is not an approved document name. Alternatively, fail closed when
   the document list could not be loaded. Add the failed-list test.

The recheck may reuse all evidence above except: the `synthetic_boundary.py` probes,
`test_remote_test.py`, the boundary `--check`, and lint and type checks on the changed files.
R4-A1 to R4-A3 are optional.

## Readiness

Not ready to commit as PASS. After the R4-1 fix, a fresh independent recheck of that delta is
needed. No commit, push or PR was made by this reviewer. Publication also needs
`pre_pr_check.py` on a committed state and the owner's authorisation.

CONTENT ID at END: `66a1c3d299353800fd52d63f0f53e1745f676f0787d9ba879fe9231cfd646101` (unchanged; the verdict applies to this content).
