# AI Assistant D-094 in-app OpenRouter test mode - Independent Quality Gate R5 (fifth check)

Date: 2026-10-28. Reviewer: a fresh, independent QG. This reviewer did not author or remediate
the candidate and did not run R1 to R4.
Scope: the delta since R4 (`AI_ASSISTANT_D094_IN_APP_OPENROUTER_QUALITY_GATE_R4.md`, FAIL on
CONTENT ID `66a1c3d2…` with one finding, R4-1, and advisories R4-A1 to R4-A3), and the
evidence that delta invalidated.

## Verdict

**PASS**

R4-1 is closed, by both of the fixes R4 offered:

- **A failed document list now refuses remote use.** `CaseSnapshot.documents_loaded` is False
  after a non-authentication error or a non-list reply. `check` then returns
  `SYNTHETIC_DOCUMENTS_UNAVAILABLE` before anything else about documents is checked.
- **Document names in the case summary are now checked directly.** Every non-empty
  `reconciliation.discrepancies[].observations[].document_display_name` must be an approved
  fixture name, whether or not the list loaded. Otherwise `check` returns
  `SYNTHETIC_DOCUMENT_NOT_APPROVED`.

R4 reproduced the leak with a failed document list and a summary observation named
`Tan Wei Lee.pdf`. That case now sends nothing to the mock OpenRouter, on both `/chat` and
`/chat/stream`.

The local (non-remote) path is unchanged:
- `documents_loaded` is a trailing field that defaults to True, and only
  `synthetic_boundary.check` reads it.
- `context.py`, `prompts.py`, `guardrails.py` and all of `apps/backend` match `c36b8af`.

No new finding. Two optional advisories are recorded below.

## Frozen content identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\assistant-openrouter-local-test-20261027`,
  branch `feat/assistant-openrouter-local-test-20261027`. HEAD, base and the local
  `origin/main` ref are all `c36b8aff5213037d9ed0710e69f8b9afc7c8c614`. The review made no
  fetch, because no non-loopback host may be contacted.
- Uncommitted, nothing staged:
  - 19 modified tracked files, including `apps/assistant/ai_assistant/clm_client.py`, which is
    new since R4.
  - 6 new product files.
  - The untracked R1 to R4 reports, which are not product.
- Tracked diff sha256 `fcd4fd5542ac9492e623776e444a49ba4864181f615b8c73a37bb174617d4499`.
  `diff --stat` and `--ignore-cr-at-eol` agree: 19 files, +748/−478.
- Per-file hashes:
  - Unchanged since R4: `remote_checks.py` `f874bab4…`, `remote_test.py` `fc57406e…`,
    `synthetic_boundary.json` `fe638667…` and `build_synthetic_boundary.py` `b7dfd34d…`.
  - Changed: `synthetic_boundary.py` `7519a783…` and `test_remote_test.py` `7f0b3027…`.
- Files changed after the R4 report, by file time:
  - `clm_client.py`, `synthetic_boundary.py` and `test_remote_test.py`;
  - the docs `apps/assistant/README.md`, `docs/decisions/DECISION_LOG.md` and
    `docs/integration/AI_MODEL_CONFIGURATION.md`.

  Every other file predates R4, so R3 and R4 evidence for those files is reused. That covers
  the frontend files, `qualification.py`, `main.py` and the rest of the runtime.
- **CONTENT ID at START: `15dce753ec7062237a3bca50ac5b46758565c33c238664b58bde9fcb27ed1a45`**
  (matches the brief). It was re-computed after all checks and before writing this report,
  with the same value.

## Findings

| # | Severity | Location | Finding |
| --- | --- | --- | --- |
| R4-1 | **Closed** | `apps/assistant/ai_assistant/clm_client.py:34-36,99-105,116`; `apps/assistant/ai_assistant/synthetic_boundary.py:282-298` | The fix is as the brief describes. The flag is computed as `loaded and isinstance(documents, list)`, and authentication errors still propagate. The summary check is independent of the list, so a list that loaded but is empty or incomplete, with a summary that names an unlisted document, is also refused. |
| R5-A1 | Advisory (docs precision) | `synthetic_boundary.py:10-11,282-283`; `tests/test_remote_test.py:398-399`; `DECISION_LOG.md:1276`; `AI_MODEL_CONFIGURATION.md:167-168`; `README.md:530-531` | The docs say "every document the case summary names" has an approved name, and the code comment and test docstring give "the timeline" as an example. The explicit check covers reconciliation observations only, which is the only place `context.py` takes a document name from the summary (`context.py:205`). Other summary text reaches the prompt only as system text: timeline messages, blocker texts and the technical-failure message. That text is covered in two ways. First, by list completeness: the list is read after the summary, from an append-only repository with no pagination, superseded documents included (`backend/app/main.py:3292-3308`, `services/document_processing.py list_documents`). Second, by the system word screen. I found no backend code that writes a document's display name into timeline or intervention text (no f-string uses `display_name` under `apps/backend/app`). The claim therefore holds in effect. Optionally, reword it as "and the case summary's document observations". |
| R5-A2 | Advisory (carried) | R4-A1 `synthetic_boundary.py:59-64,144-146`; R4-A3 `assistant_eval/qualification.py:313-316` | Both are unchanged and both fail safe. **R4-A1:** a date of birth can be hidden behind a fake time, but only in an assistant turn written by hand, a class R3 accepted. User turns are still refused (re-confirmed in R4). **R4-A3:** a run that crosses the deadline or is cancelled after its last turn is recorded `error`/`cancelled`, never a false pass, and every call is still verified by `remote_test.py`. Neither is needed for PASS. The R2-5 note on EOL also stands: `clm_client.py` stays CRLF like its base blob, with 117 CRLF and 0 LF lines, and the diff equals `--ignore-cr-at-eol`. |

## Delta verification

| Item | Result | Evidence |
| --- | --- | --- |
| `clm_client` semantics | **Verified** | Client probes through `httpx.MockTransport`. `documents_loaded` is False for a documents 404, 403 or 503, a dict reply, a `null` reply and a transport `ConnectError`. It is True for `[]`, for a valid list, and for a list with a junk item (the item is dropped and never reaches the prompt). A 401 still raises `AUTHENTICATION_REQUIRED`. |
| Boundary: failed list | **Verified** | With `documents_loaded=False`, `Tan Wei Lee.pdf`, `garden-business-tan-wei-lee.pdf` and `client-passport.pdf` (the R4 residual set) are each refused `SYNTHETIC_DOCUMENTS_UNAVAILABLE`. An otherwise approved summary with a failed list is also refused. |
| Boundary: summary names | **Verified** | The same three names in an observation, with the list loaded (empty, or with approved documents only), are each refused `SYNTHETIC_DOCUMENT_NOT_APPROVED`. An approved name with a trailing space, a whitespace-only name, an int and a list are refused. An approved name and `""` pass. Malformed reconciliation shapes (list, string, dict, string observation) raise no exception. |
| No over-blocking | **Verified** | The R4 live-like discrepancy (form, ACRA MOCK and the conflicting fixture document) and the plain fixture snapshot are still inside. A positional 3-argument `CaseSnapshot` is still inside, with `documents_loaded` True by default. |
| End to end (Journey, mock OpenRouter) | **Verified** | (a) R4's reproduction (documents 500 plus `Tan Wei Lee.pdf` in an observation): `case_data` with `Reason: SYNTHETIC_DOCUMENTS_UNAVAILABLE.` on `/chat` and `/chat/stream`, **0** requests, and the name is absent from every mock request. (b) The unapproved summary name with the list loaded: `SYNTHETIC_DOCUMENT_NOT_APPROVED`, 0 requests. (c) The approved conflicting fixture name: `answered_by: model`, 1 request. (d) **Local mode unchanged:** with no remote activation and documents 500, both endpoints are answered by the local baseline model, with no `SYNTHETIC` notice and 0 OpenRouter requests. |
| Other `CaseSnapshot` users | **Verified** | Callers that build it positionally or by keyword: `build_synthetic_boundary.py:268`, `scripts/speed_test.py:51` and 15 test modules. `documents_loaded` is read only at `synthetic_boundary.py:284`. Its callers: `main.remote_gate` (`main.py:674`, only for the remote test model) and tests. `knowledge_api.py` loads cases but makes no model call. The boundary file is current (`--check`). |
| New tests | **Verified** | `test_an_unreadable_document_list_or_an_unapproved_name_in_the_summary_is_refused` and `test_the_client_marks_a_document_list_it_could_not_read` cover the unit and client cases. `test_a_document_list_that_fails_to_load_sends_nothing` covers end to end. The Journey now looks up `self.backend.handler` per request, a harness change only. The tests assert the right reason codes and zero requests. |
| Docs | **Verified** (R5-A1 optional) | The D-094 T4 row, `AI_MODEL_CONFIGURATION.md` section 9, the README and the module docstring all state that an unreadable list refuses and that summary-named documents are checked. `PROJECT_STATE.md` is unchanged since R4 and its summary wording ("fixture documents") stays accurate. |

## Checks run (this session, on CONTENT ID `15dce753…`)

| Check | Result |
| --- | --- |
| Content ID: start, and before the report after all checks | `15dce753…1a45` both times |
| `tests/test_remote_test.py` (`-p no:cacheprovider`, `-B`) | 67 passed |
| remote + `test_ai_assistant.py` + `test_model_management.py` | **133 passed** (matches the implementer) |
| CaseSnapshot-consumer regression: `test_eval_harness`, `test_document_selection`, `test_document_review_choices`, `test_guardrails`, `test_explanations`, `test_answer_records` | 287 passed |
| Full assistant suite (`faulthandler_timeout=300`, junitxml in scratch) | **2442 tests**: 2428 passed, 14 failed, 0 errors. All 14 are `OSError: [Errno 24] Too many open files` (junit-verified): `test_model_factory` 1, `test_phase_b_live` 1, `test_required_p2` 5 and `test_streaming_resources` 7. That is the same set as R1 to R4 and the implementer. Those 4 files in isolation: **288 passed** |
| ruff check / ruff format --check (`--no-cache`) | All checks passed; 111 files already formatted |
| mypy `ai_assistant assistant_eval scripts tests/test_remote_test.py` (cache in scratch) | Success: no issues in 59 source files |
| `scripts/build_synthetic_boundary.py --check` | synthetic boundary is current |
| `check_project_state`, `check_architecture`, `check_policy_authority`, `check_secrets`, `check_external_provider_readiness`, `check_tooling_config` | all PASS (exit 0) |
| `git diff --check c36b8af` | clean |
| `git diff --quiet c36b8af -- apps/backend guardrails.py context.py prompts.py` | unchanged (exit 0) |
| Byte-level trailing whitespace and final newline: 6 new files, `clm_client.py` and the 3 changed docs | clean (EOL as in R2-5) |
| Boundary and client probes (`qg094r5/probe_boundary5.py`) | 34 checks, 0 unexpected |
| End-to-end probes (`qg094r5/test_probe_journey5.py`) | 4 passed |
| Frontend `tsc` / vitest | Not re-run. The frontend files are unchanged since R3, so the R3 evidence and the implementer's (65 files / 1123 tests) are reused |
| Real-stack browser E2E | Implementer's evidence; not re-run by this reviewer. Ports 8791, 8192 and 5191 were not touched |

The probes are in
`C:\Users\shane\AppData\Local\Temp\claude\C--Users-shane--claude-spares-spare-6YcPey\583f9cb6-22ae-4b09-9725-20ab186f8738\scratchpad\qg094r5\`.

Safety limits kept:
- No real OpenRouter call; no non-loopback host contacted.
- No `.env` read; no real `OPENROUTER_API_KEY` set or read.
- No Mongo use.
- Nothing written to the repository except this report.

## Change classification (this delta)

| Area | Changed in this delta? |
| --- | --- |
| API/type | One internal assistant dataclass field (`CaseSnapshot.documents_loaded`, default True). No HTTP API change |
| Schema, connector, configuration, mapping | No |
| Auth/security | Yes: the D-094 synthetic boundary is tightened (fails closed). No auth change |
| Business rules, architecture, provider status | No |
| Runtime behaviour | Remote test mode only: a new refusal reason, `SYNTHETIC_DOCUMENTS_UNAVAILABLE`, plus stricter document-name refusal. The local path is unchanged |

## Readiness

This independent PASS applies only to CONTENT ID `15dce753…1a45` and the tracked diff sha256
`fcd4fd55…d4499` recorded above. Before publication:
- the owner authorises commit, push and PR;
- `pre_pr_check.py` passes on the committed state, which must carry exactly this content;
- any change to the reviewed content needs a fresh independent review.

R5-A1 and R5-A2 are optional and do not block. This reviewer made no commit, push or PR.

CONTENT ID at END: `15dce753ec7062237a3bca50ac5b46758565c33c238664b58bde9fcb27ed1a45` (unchanged; the verdict applies to this content).
