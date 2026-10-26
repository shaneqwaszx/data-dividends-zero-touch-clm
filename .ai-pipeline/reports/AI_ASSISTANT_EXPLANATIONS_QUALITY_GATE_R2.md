# AI Assistant explanations (D-090, ADR-012 Amendment 2) - independent quality gate, recheck R2

Reviewer: fresh independent QG subagent. It did not author or remediate the reviewed content
and did not run the first gate or R1. Date: 2026-10-26. Skill: `.agents/skills/fyp-quality-gate/SKILL.md`
and `references/report-template.md`, read in full; AGENTS.md sections on invariants, secrets,
Git safety and verification read. Earlier reports read: the first gate (FAIL on `a49db57`) and
R1 (PASS on `33dc3ad`, notes N1, N3-N7).

## Reviewed content identity

| Item | Value |
| --- | --- |
| Checkout | `/Users/tasha/Documents/GitHub/dd-clm-qg-explanations`, detached, clean before and after every check |
| HEAD | `30b3e7f8f5d8ea9db9a513c6791f68cd45f65950` |
| Tree | `268d6dba94254972c12333f5749c6714406e85fe` |
| Assigned base | `1d039865bf5197a76add7f733128829bb05019ac` (#111) |
| Recheck delta | `git diff 33dc3ad 30b3e7f`: `guardrails.py`, `guide.py`, `main.py`, `test_explanations.py` (additions only, 0 removed lines), ADR-012, DECISION_LOG (1 row changed in the branch-added D-090 table), R1 report added |
| Whole-branch diff | `git diff 1d03986...30b3e7f`: 20 files, +2198/-72. No backend, E2E, script, config or production frontend path; `AiAssistantPanel.test.tsx` is the only frontend file |
| Newer main observed | the local `origin/main` ref is now `769c14939491de47ea5438923cf9ac5548e60bd6` (#115, AI Assistant Phase A1 metrics, committed 2026-10-26 12:15 +0800). See finding R2-B1 and section 8 |

Change classes: assistant service behaviour and its output policy (a trust boundary), DOCS.

## 1. Executive result

**PASS** for the frozen content `30b3e7f` / `268d6db` against base `1d03986`. N3 and N6 are
correctly done, N1/N3 are documented, and I could not break `with_required_lines` or the
`streamed` tracking in `stream_answer`, including the cut-short path and the last line that
only `guard.finish()` accepts. G6 still holds: only allowed lines are shown, in the catalog's
own words, and `left_out` is unchanged. Not publication-ready: `origin/main` has moved to
`769c149`, which conflicts in `apps/assistant/ai_assistant/main.py` (the streaming path this
commit changes); the re-integration needs a fresh independent review of the resolved scope
(section 8).

## 2. Acceptance checklist

| Claim | Result | Evidence |
| --- | --- | --- |
| N3: a line already streamed to the RM is never removed | VERIFIED | `guardrails.py:755-763`: pass 1 keeps `needed ∪ seen` down to 6, pass 2 keeps `seen` down to 8; a streamed line is in `keep` in both passes, so it is never in `droppable`. Probe `qg-r2/probe_r2.py`: 12,000 random (facts, topic, shown set, streamed prefix) cases; `streamed ⊆ result` always. |
| N3: required lines up to 8, unseen optional lines dropped first to 6 | VERIFIED | Same probe asserts: if any unseen optional line survives then `len ≤ 6`; if any unseen line survives then `len ≤ 8`; and no line is dropped while the answer is at or below the limit for its class (no over-dropping). New tests `test_required_lines_may_take_an_answer_up_to_eight_lines` (`test_explanations.py:766`) and `test_a_line_already_streamed_to_the_rm_is_never_removed` (`:775`). |
| Index handling while popping | VERIFIED | `droppable` is ascending; `droppable.pop()` takes the largest index, and removing a later element never shifts an earlier index. The list is recomputed for the second pass. Lines have no duplicates (`shown` comes from a dict-ordered validation; `missing` excludes `shown`). |
| `main.py` tracks what the RM was shown | VERIFIED | `StreamingGuard.feed` returns the cumulative `self.text` (`guardrails.py:829`), and `main.py:371` sets `streamed = shown` only when a `text` event is yielded, so `streamed` is exactly the last text sent. Accepted lines are only appended (dict order), so `streamed` lines are a subset of the final validation. The last line accepted only in `guard.finish()` (`main.py:379`) is not in `streamed` and may be dropped; that is correct because the RM never saw it. Cut-short path (`main.py:388-396`): `guard.validation()` excludes the unfinished line and `streamed` is passed; probe: 101 mid-stream `LlmUnavailableError` runs, all kept every streamed line. The frontend replaces the streamed text with the `done` answer (`apps/frontend/src/aiAssistant.ts:227`). |
| Streaming end-to-end | VERIFIED | New test `test_the_final_streamed_answer_keeps_every_line_the_rm_was_shown` (`test_explanations.py:792`). Probe: 300 `/chat/stream` runs with random 1-20 character chunks, allowed lines mixed with junk, random topic and optional mid-stream failure; in every run each streamed line is in the final answer and every final line is in `allowed_guidance` for the app's own facts. |
| Only allowed lines are added; `left_out` unchanged | VERIFIED | `missing` is filtered by `allowed_guidance(facts)`; the result is `Validation(text, left_out=validation.left_out, ...)`; probe asserts `result ⊆ shown ∪ needed ⊆ allowed` and equal `left_out`. |
| N6: document review sentence | VERIFIED | `guide.py:221` "When a person reviews a document, every field read from it needs a review decision." is exactly the human-review completion rule (`apps/backend/app/services/document_processing.py:732-743`, `HUMAN_REVIEWED` only when no field is `PENDING`). ADR-012 Amendment 2 table row names the automatic and reconciliation paths as out of the sentence's scope. |
| N1/N3 documented | VERIFIED, note N8 | ADR-012 Amendment 2 Change 4 and Change 5; D-090 E5. DECISION_LOG has no removed lines against `1d03986`; D-090 stays PROPOSED. |
| G6 on the whole branch | VERIFIED | R1's analysis of `_Catalog` stands (no change to the catalog or matching in this delta). This delta only selects among lines already validated or allowed. |
| New catalog sentences true against cited sources | VERIFIED | Only the N6 sentence changed (above). The others are unchanged since R1, which checked them. |
| Changed existing tests list complete | VERIFIED | The delta removes no test line; the whole-branch list in `scratchpad/changed-tests.md` is unaffected. Behaviour change for the non-streaming path (required lines now up to 8 instead of being cut at 6) is covered by new tests, not by changing old ones; `test_the_completed_answer_is_capped_dropping_optional_lines_first` still passes unchanged. |
| Browser acceptance | NOT GREEN, pre-existing; reuse valid | Section 4. |

## 3. Contract and integration findings

- No backend, API, schema, connector or configuration change. The assistant stays GET-only.
- No live ACRA, GoldTier or sponsor claim.
- **R2-B1 (integration, blocks publication, not this verdict):** `origin/main` moved to
  `769c149` (#115) after the assigned base. `git merge-tree --write-tree 30b3e7f 769c149`
  reports a content conflict in `apps/assistant/ai_assistant/main.py`, which #115 changed by
  +/-257 lines, including the streaming code where `streamed` is tracked. The resolution
  touches the N3 fix directly and is reviewed content that this gate has not seen.

## 4. Tester and adversarial findings

Run by this reviewer on HEAD `30b3e7f` / tree `268d6db`, local macOS, repository venv, caches
disabled or redirected to the scratchpad:

| Check | Result |
| --- | --- |
| `cd apps/assistant && python -m pytest -q -o addopts="" -p no:cacheprovider` | **1375 passed** in 35 s (R1: 1372; +3 new tests) |
| `ruff check --no-cache .`; `ruff format --check --no-cache .` | All checks passed; 65 files already formatted |
| `mypy --cache-dir <scratch> ai_assistant` | Success: no issues in 26 source files |
| `git diff --check 1d03986...30b3e7f` | clean; R1 report has no trailing whitespace |
| `scripts/check_architecture.py`; `check_project_state.py`; `check_secrets.py` | PASS; PASS; no supported secret patterns |
| `qg-r2/probe_r2.py` | unit 12,000/12,000; stream 300/300 (270 with streamed text, 101 cut short, 110 final answers over 6 lines) |

Reused, not rerun:

- Frontend: no frontend path changed since `a49db57` (`git diff a49db57 30b3e7f --name-only`).
  The developer's tsc OK, vitest 1084/1085 (known macOS-only `ViteHistoryFallback.test.ts`)
  and build OK carry forward.
- Browser: the E2E suite never starts the Python assistant; `assistant-streaming.e2e.ts`
  uses an in-test synthetic server. This delta is assistant Python and docs only, so reuse is
  valid. Official full run on `a49db57`: FAIL at 31/115 (`database-classification.e2e.ts:191`);
  diagnostic `--keep-going` 106 PASS / 9 FAIL, the same 9 failing identically on clean
  `1d03986`. `assistant-streaming.e2e.ts:10` PASS on `33dc3ad`. Keep-going is diagnostic, not
  acceptance; the official run is not green for pre-existing reasons and needs an owner
  decision. No targeted E2E was run in this recheck.
- `pre_pr_check.py` not run (publication step). CI has no `apps/assistant` job and is
  billing-blocked; all evidence is local and is not hosted CI.

## 5. Code and architecture review

The change is small and bounded to N3/N6. The two-pass loop is correct and readable; the
default `streamed=()` keeps the non-streaming call sites safe.

Notes (not required fixes; for the PR text):

- **N8 (docs precision):** ADR-012 Amendment 2 Change 4 says "a streamed answer can exceed 8
  lines only by lines the RM has already read". Trimming runs only when a required line was
  missing (`guardrails.py:751-752` returns early otherwise), so an answer with no missing
  required line is not capped at all: on `/chat`, or the final line accepted in
  `guard.finish()`, it can exceed 8 lines that were not streamed (probe: 9 of 300 final
  answers had more than 8 lines). All are allowed lines, so G6 is unaffected; the prompt asks
  for at most 6 lines. Same behaviour as R1's candidate.
- **N9 (UX):** when required lines are added, the final answer is reordered by the topic order,
  so a required line can appear above lines the RM already read while streaming (the new test
  asserts `final[:2] == [GARDEN_VALUES, ADDRESS_WHY]`). Nothing is removed; worth one line in
  the PR.
- R1 notes N4, N5 and N7 stand unchanged; N1 and N3 are now documented; N6 is closed.

## 6. Security review

No new input reaches the output path: `streamed` comes from the guard's own accepted text, not
from the model or the client. No secrets, `.env`, tokens or PII newly tracked; no logging
change. Findings: none blocking, none minor.

## 7. Required fixes

None for the frozen content. R2-B1 is an integration step before publication, not a defect in
the reviewed content.

## 8. Readiness

- Branch quality gate: **PASS** on `30b3e7f` / `268d6db` against `1d03986`.
- Not publication-ready. Before a PR:
  - merge `origin/main` `769c149` (#115) and resolve the `main.py` conflict so that the
    streaming path still passes `streamed` on both the finished and the cut-short paths and
    #115's telemetry does not record or count lines differently from what is returned; rerun
    the assistant suite, ruff, mypy and this probe; the resolved content then needs a fresh
    independent review of the changed scope (this PASS does not carry over);
  - Shane's acceptance of D-090 (incl. E2) and D-084; an owner decision on the not-green full
    E2E (pre-existing failures on main); Shane's approval of the manual-CI exception;
  - `python scripts/pre_pr_check.py` on the clean committed tree.
- No live ACRA verification or real GoldTier integration readiness is claimed or affected.

## 9. Git status

- Checkout detached at `30b3e7f8f5d8ea9db9a513c6791f68cd45f65950`, tree
  `268d6dba94254972c12333f5749c6714406e85fe`; no staged or tracked modification; the only new
  file is this untracked report.
- No implementation, test or doc fix, commit, push, merge, rebase, reset or stash was made.
  Probes are in the session scratchpad (`scratchpad/qg-r2/probe_r2.py`).

Reviewed HEAD: 30b3e7f8f5d8ea9db9a513c6791f68cd45f65950
Reviewed tree: 268d6dba94254972c12333f5749c6714406e85fe

PASS
