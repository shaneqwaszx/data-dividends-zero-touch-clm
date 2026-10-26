# AI Assistant explanations (D-090, ADR-012 Amendment 2) - independent quality gate, recheck R3

Reviewer: fresh independent QG subagent. It did not author or remediate the reviewed content
and did not run the first gate, R1 or R2. Date: 2026-10-26. Skill:
`.agents/skills/fyp-quality-gate/SKILL.md` and `references/report-template.md`, read in full;
AGENTS.md sections on review, gates and the AI Assistant read. Earlier reports read: first gate
(FAIL on `a49db57`), R1 (PASS on `33dc3ad`), R2 (PASS on `30b3e7f`, with R2-B1 and notes N8, N9).

## Reviewed content identity

| Item | Value |
| --- | --- |
| Checkout | `/Users/tasha/Documents/GitHub/dd-clm-qg-explanations`, detached, clean before and after every check |
| HEAD | `70a97e28948d14f5f7be8ad81541cf9e0c1af281` (merge of `origin/main` `769c149`, #115) |
| Tree | `b4330f1dc2f31e656733a1fe0dbf859c963d09e5` |
| Base | `769c14939491de47ea5438923cf9ac5548e60bd6` (#115) |
| Recheck delta | `git diff 30b3e7f 70a97e2`: #115's files, plus the conflict resolution in `ai_assistant/main.py`, `assistant_eval/runner.py` (+11/-3), `tests/test_explanations.py` (+11, additions only), ADR-012 Amendment 2 Change 4 and DECISION_LOG D-090 E5 (N8/N9) |
| Whole-branch diff | `git diff 769c149...70a97e2`: 22 files, +2372/-74. No backend, E2E, script, config or production frontend path |

Change classes: assistant service output policy (trust boundary), an addition to the chat reply
contract (`added_lines`), a change to the owner's (#115) offline evaluation harness, DOCS.

## 1. Executive result

**PASS WITH MINOR FIXES.** The `main.py` conflict resolution keeps both sides' intent: #115's
telemetry is intact and content-free, `kept_lines` keeps #115's meaning, and `streamed` is
tracked and passed on both the finished and cut-short stream paths. The branch-owned
guardrail, catalog and prompt code is byte-for-byte the delta R2 reviewed, and G6 still holds on
the merged tree. Two bounded fixes remain, both in the #115 evaluation harness boundary, not in
what the RM sees: the harness's committed snapshots are now stale for every question (M1), and
the `_shown` change removes the added positions from the harness's own unsafe-display check (M2).

## 2. Acceptance checklist

| Claim | Result | Evidence |
| --- | --- | --- |
| #115 telemetry kept (`_Outcome`, `selected`, `answered`, `emit`, `retrieval_ms`, `delivered`/`cancelled`, first-piece/first-line timings) | VERIFIED | `main.py:183-204`, `377-431`, `496-561` match #115; `git diff 769c149 70a97e2` on `main.py` only adds the import, `added_lines`, `Prepared.plan`, `topic_plan(...)`, `streamed` and the `_model_reply` parameter. `telemetry.py`, `config.py`, all other `assistant_eval` modules, the scripts and #115's tests are unchanged against `769c149`. |
| `streamed` tracked and passed on finished AND cut-short paths | VERIFIED | `main.py:504`, `515`, `526-532`, `545-551`. Probe `qg-r3/probe_r3.py`: 366 model answers (`/chat` and `/chat/stream`, random 1-20 char chunks, 98 mid-stream `LlmUnavailableError`); every streamed line is in the final answer and every final line is an allowed line. |
| `kept_lines` keeps #115's meaning (model lines kept, not added) | VERIFIED, note N10 | `outcome.selected(validation)` runs before `_model_reply` adds lines (`main.py:443`, `519`, `539`). |
| `added_lines`: positions only, never text, exactly the lines the service added | VERIFIED | `main.py:140-142`, `239-241`. Probe: for every non-cut answer, `{answer[k] for k in added_lines}` equals the final lines not in the model's own validated selection; positions sorted, unique, in range; empty on case-data answers. New tests `test_explanations.py:830`, `:833`. |
| Runner skips added positions; Shane's tests unchanged and pass | VERIFIED, minor M2 | `runner.py:162-183`, `278-281`. `git diff 769c149 70a97e2 -- tests/test_eval_harness.py tests/test_telemetry.py` is empty; both pass in the full run. |
| Harness signal not hidden | **NOT FULLY** (M1, M2) | Section 4. |
| N8 / N9 doc corrections | VERIFIED | ADR-012 Amendment 2 Change 4 (`ADR-012...md:556-566`) now says limits apply only when lines are added, that such an answer can be longer than 8 but all lines are allowed, and that an added line can appear above lines already read; D-090 E5 names `added_lines`. Both match `guardrails.py:751-763`. |
| G6 on the whole branch (only allowed lines, in the catalog's words) | VERIFIED | `guardrails.py`, `guide.py`, `prompts.py`, `briefing.py`, `knowledge_answers.py`, `persona_and_rules.md`: the `769c149...70a97e2` delta is identical (+/- lines) to the R2-reviewed `1d03986...30b3e7f` delta. #115 adds no new output path: `/chat` and `/chat/stream` both go through `validate_answer`/`StreamingGuard` then `_model_reply` -> `with_required_lines`, which adds only `allowed_guidance(facts)` lines. Probe: 0 non-allowed final lines in 366 runs. |
| 6/8 limits and never-remove-streamed | VERIFIED | `with_required_lines` unchanged since R2 (R2's 12,000-case unit probe stands); merged stream path re-probed above. |
| Telemetry logs no answer or case text | VERIFIED | `AnswerMetrics` (`telemetry.py:145-196`) holds only codes, counts, hashes, scores, flags and timings, each validated; the merge adds no field. `added_lines` is in the reply only, not in metrics. |
| No existing test changed since R2 | VERIFIED | `git diff 30b3e7f 70a97e2 -- apps/assistant/tests`: `test_explanations.py` (+11, additions) plus files arriving from #115 unchanged against `769c149`. The whole-branch list in `scratchpad/changed-tests.md` is unaffected. |
| Browser acceptance | NOT GREEN, pre-existing; reuse valid | Section 4. |

## 3. Contract and integration findings

- `added_lines` is an additive field on the chat reply and `done` event. The panel's parser
  (`apps/frontend/src/aiAssistant.ts:229`) checks only known fields, so it is tolerated. It is
  disclosed in the PR draft.
- `runner.py` is #115 (Shane's) code; the change is listed for Shane in the PR draft. That is
  the right handling, and the approach (the service reports what it added, the harness scores
  the model's selection) is sound. The two minors below are about how it was applied.
- No backend, schema, connector or configuration change; the assistant stays GET-only. No live
  ACRA, GoldTier or sponsor claim.

## 4. Tester and adversarial findings

Run by this reviewer on HEAD `70a97e2` / tree `b4330f1`, local macOS, repository venv, caches
disabled or redirected to the scratchpad:

| Check | Result |
| --- | --- |
| `cd apps/assistant && python -m pytest -q -o addopts="" -p no:cacheprovider` | **1461 passed** in 52 s |
| `ruff check --no-cache .`; `ruff format --check --no-cache .` | All checks passed; 78 files already formatted |
| `mypy ai_assistant`; `mypy assistant_eval` (cache in scratchpad) | no issues in 27 files; no issues in 9 files |
| `git diff --check 769c149...70a97e2` | clean |
| `scripts/check_architecture.py`; `scripts/check_secrets.py` | PASS; no supported secret patterns |
| `qg-r3/probe_r3.py` (service + harness) | 366/366 model answers OK (268 with added lines, 233 with streamed text, 98 cut short); `_shown` unmapped 0 in every run |
| `scripts/evaluate_answers.py check` on `70a97e2` | **`snapshots drifted: 84 turns differ`** (all of them; `prompt_version` e5ae1c2dba716b54) |
| same, on a `git archive` copy of `769c149` | `snapshots are current (84 turns, sha256 9341411d512d3beb)` |
| `evaluate_answers.py run --model self-test-perfect` (on a `git archive` copy in the scratchpad, so no output in the repo) | label-free: unsafe_display 0, line_validity_rate 1.0; gold-based: **turns_excluded_for_drift 84, turns_scored 0**, every gold measure "-" |
| Hostile `_shown` input: a non-allowed line at an added position | `unmapped = 0`: the harness does not count it (M2) |

Reused, not rerun: frontend (no frontend/backend/E2E/script path changed since `a49db57`;
tsc OK, vitest 1084/1085 with the known macOS-only `ViteHistoryFallback.test.ts`, build OK);
browser: official full run on `a49db57` FAIL at 31/115, diagnostic `--keep-going` 106 PASS / 9
FAIL, the same 9 failing on clean `1d03986`; `e2e/assistant-streaming.e2e.ts:10` PASS on
`70a97e2` (`scratchpad/assistant-e2e-70a97e2.json`, complete, not keep-going). The E2E suite
never starts the Python assistant. Keep-going is diagnostic, not acceptance; the official run is
not green for pre-existing reasons and needs Shane's decision. No E2E was run in this recheck.
`pre_pr_check.py` not run (publication step). CI has no `apps/assistant` job and is
billing-blocked; all evidence is local, not hosted CI.

## 5. Code and architecture review

**M1 (minor, harness integration) - #115's frozen evaluation snapshots are stale for all 84
questions.** This branch changes the prompt and the catalog, so `tests/fixtures/eval/snapshots.json`
(committed by #115) no longer matches what the service offers. `evaluate_answers.py check`
fails on `70a97e2` and passes on `769c149`; any harness run on the merged tree excludes every
turn from gold scoring (`turns_excluded_for_drift 84`). No test catches this, and the PR draft
does not mention it. `gold.json` holds only 84 stubs (no owner labels), so nothing labelled is
lost. Fix: rebuild with `evaluate_answers.py snapshot --write-fixture` then `stubs` (the
documented path, `apps/assistant/README.md:345-352`) and list the fixture change for Shane, or,
if Shane wants to own the refresh, say so in the PR under the #115 integration section.

**M2 (minor, harness signal) - `_shown` drops added positions before the unsafe-display
check.** `runner.py:168-170` `continue`s on an added position before the `by_text` lookup, so a
line there is counted neither in `shown` nor in `unmapped` (`unsafe_display`, which the harness
says must be 0), nor in `must_not_violations`. Today the service adds only
`allowed_guidance(facts)` lines, the same function that builds the harness's `offered`
(`snapshot.py:133`), so nothing is hidden now (probe: 0 in 366 runs). But the harness's
independent unsafe-display check now trusts the service's own claim about which lines it added;
a future regression in `with_required_lines` would not show up there. Minimal fix: still look
the added line up and count it as `unmapped` when it is not offered, and leave it out of `shown`
only (one-line reorder in `_shown`, plus a harness test with a non-allowed line at an added
position).

Notes (no fix required; for the PR text):

- **N10:** `kept_lines` counts model lines that passed validation, before the service's trim. When
  required lines are added and the model gave many lines, unseen model lines can then be dropped
  (probe: 98 of 366 random answers), so `kept_lines` can exceed the model lines the RM saw, and
  the harness's "model's own selection" is the model's selection minus lines the service
  trimmed. `line_validity_rate` (a validation ratio) is unaffected. Worth one sentence next to
  the ADR's `kept_lines` remark.
- **N11:** a gold `must_not` line that is also a topic's required line would be added by the
  service and skipped by the harness. That conflict is between gold and D-090's policy, not the
  model; the gold labelling guidance could say required lines are out of scope.
- R1/R2 notes N1, N4, N5, N7 stand; N8 and N9 are now documented and closed.

## 6. Security review

No secrets, `.env`, tokens or PII newly tracked. Telemetry stays content-free (section 2);
`added_lines` carries integers only. No new input reaches the output path: `streamed` comes from
the guard's own accepted text and added lines from `allowed_guidance`. M2 weakens an offline
measurement, not a runtime control. Findings: none blocking.

## 7. Required fixes

1. M1: refresh (or explicitly hand to Shane) #115's eval snapshots and stubs; disclose in the PR.
2. M2: keep counting non-offered lines at added positions as `unmapped` in `runner.py::_shown`,
   with a test.

Both are bounded and low-risk; a recheck needs to review only that delta and rerun the
assistant suite, ruff, mypy and `evaluate_answers.py check`.

## 8. Readiness

- Branch quality gate: **PASS WITH MINOR FIXES** on `70a97e2` / `b4330f1` against `769c149`.
- Before a PR: M1 and M2 (with a recheck of that delta); Shane's acceptance of D-090 (incl. E2,
  which relaxes ADR-012 section C) and D-084; Shane's review of the `runner.py` change and of any
  eval-fixture refresh; an owner decision on the not-green full E2E (pre-existing failures on
  main); Shane's manual-CI exception; `python scripts/pre_pr_check.py` on the clean committed
  tree.
- No live ACRA verification or real GoldTier integration readiness is claimed or affected.

## 9. Git status

- Checkout detached at `70a97e28948d14f5f7be8ad81541cf9e0c1af281`, tree
  `b4330f1dc2f31e656733a1fe0dbf859c963d09e5`; no staged or tracked modification; the only new
  file is this untracked report.
- No implementation, test or doc fix, commit, push, merge, rebase, reset or stash was made.
  Probes and harness runs used the session scratchpad (`scratchpad/qg-r3/`).

Reviewed HEAD: 70a97e28948d14f5f7be8ad81541cf9e0c1af281
Reviewed tree: b4330f1dc2f31e656733a1fe0dbf859c963d09e5

PASS WITH MINOR FIXES
