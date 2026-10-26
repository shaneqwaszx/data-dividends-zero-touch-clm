# AI Assistant explanations (D-090, ADR-012 Amendment 2) - independent quality gate, recheck R5 (merge of #113)

Reviewer: fresh independent QG subagent. It did not author or remediate the reviewed content
and did not run the first gate or R1-R4. Date: 2026-10-26. Skill:
`.agents/skills/fyp-quality-gate/SKILL.md` and `references/report-template.md`, read in full;
AGENTS.md scope, invariants, secrets, Git and verification sections read. Earlier reports
read: first gate (FAIL on `a49db57`), R1 (PASS), R2 (PASS on `30b3e7f`), R3 (PASS WITH MINOR
FIXES on `70a97e2`), R4 (PASS WITH MINOR FIXES on `445dd8f`, one finding R4-M1).

Scope agreed with the owner: the merge of origin/main `7d6a31a` (#113, D-084 answer records and
the enhancement request page) into the branch, plus the R4-M1 fix.

## Reviewed content identity

| Item | Value |
| --- | --- |
| Checkout | `/Users/tasha/Documents/GitHub/dd-clm-qg-explanations`, detached, clean at start |
| HEAD | `64e3f5741d86e073c7673d694636e0045f859802` (merge of `79644e2` and `7d6a31a`) |
| Tree | `75df3531b3681a18dbf815c1c2f8385334b620dc` |
| Base | origin/main `7d6a31a` (#113) |
| Recheck delta | `git diff 445dd8f 79644e2` (ADR N10/N11 wording, R4 report); `git show --remerge-diff 64e3f57` (conflict resolutions in `guardrails.py`, `main.py`; merge edits in `answer_records.py`, `test_answer_records.py`, `test_guardrails_dropped.py`, `AiAssistantPanel.test.tsx`) |
| Whole branch vs new main | `git diff 7d6a31a...64e3f57`: assistant only (21 files under `apps/assistant`), one frontend test file (+40/-0), ADR-012, DECISION_LOG and QG reports |

## 1. Executive result

**FAIL.** The merge itself is mechanically correct: `dropped` sits beside D-090's `_Catalog`
selection on both paths, is read-only, always agrees with `left_out`, never holds a selected
line, and streaming equals batch; G6, the 6/8 limits and never-remove-streamed still hold; the
R4-M1 fix is correct; all assistant checks and the two assistant E2E tests pass. But the merge
combines two proposals in a way neither document covers: D-090 E2 puts registry and document
values (`Registered address: ACRA says "...", the document says "..."`) into the catalog, and
D-084 stores catalog lines and model answers **unredacted** on the premise that they are fixed
wording. On the merged tree every answer record on a case with a difference stores the ACRA and
document addresses (or names / UENs) in clear, while the very same line inside a case-data
answer is stored as `[ADDRESS]`. That extends ADR-012 section A (D-084 D1 relaxes it only for
the question and a case-state snapshot), is not disclosed (Amendment 2 says it "amends section C
only"), and is protected KYC/document data under AGENTS.md. It is a data-protection and contract
issue, so it cannot be a minor fix; it needs either a code fix (redact) or Shane's explicit
acceptance of the wider relaxation.

## 2. Acceptance checklist

| Claim | Result | Evidence |
| --- | --- | --- |
| R4-M1 fixed (N10 sentence) | VERIFIED | `git diff 445dd8f 79644e2 -- docs/`: ADR-012 now says `kept_lines` counts before the 6/8 trim and the harness scores the final answer; N11 precision added. PR draft `scratchpad/pr-body.md:39-40` matches. |
| `Validation.dropped` kept on `validate_answer` and `StreamingGuard` with `_Catalog` selection | VERIFIED | `guardrails.py:713-732`, `:809-826`, `:862-868`; `dropped` is `compare=False, repr=False` (`:591-593`); appended only in the `selected is None` branch, stripped as #113 did. |
| `with_required_lines` carries `dropped` | VERIFIED | `guardrails.py:776-781`; also on the unchanged early return. |
| `dropped` and `left_out` cannot disagree; a selected line never in `dropped`; stream = batch | VERIFIED | Same branch increments both. Probe (section 4): 4,500 random answers on Merlion `FACTS`, `NO_ACTION`, `HR` with formatting noise and random 1-15 char streaming chunks: `StreamingGuard.validation() == validate_answer()` and equal `dropped`, `len(dropped) == left_out`, `dropped` disjoint from shown lines, `with_required_lines` keeps `left_out`/`dropped`. 0 failures. |
| `ChatResponse` keeps `added_lines` and `answer_id`/`small_talk` | VERIFIED | `main.py:156-167`; `answer_id` set by `record()` via `model_copy`. |
| Record built from final `response.answer`; `left_out`/`dropped` from `outcome.validation` | VERIFIED | `main.py:436-456`; probe: topic question with 3 service-added lines -> `chosen_lines == response.answer.splitlines()` (added lines included), `dropped_lines` length == `result.left_out` == 1, batch and stream identical. Consistent: required lines are allowed lines, so they never change `left_out`. |
| Record never holds unredacted case data beyond D-084 D1 | **NOT MET (R5-B1)** | Section 5. |
| `POLICY_LINES` tagging and the `skip` set | VERIFIED, with note N13 | Section 5. |
| `test_guardrails_dropped.py` still proves `dropped` is read-only | VERIFIED | Reference loop bodies equal `79644e2`'s `validate_answer`/`StreamingGuard._accept` minus `dropped` (compared line by line); `_Catalog` is shared, but the change under test is only the `dropped` append, so the invariance is not circular for that purpose. All #113 assertions kept. |
| `test_answer_records.py` neutral questions | VERIFIED as justified, with minor R5-M1 | Only `QUESTION` and one long question changed; assertions unchanged (`git show --remerge-diff`). They avoid D-090 topics rather than test the combination; no test pins the merged behaviour (R5-M1). |
| `AiAssistantPanel.test.tsx` additions only vs main | VERIFIED | `git diff 7d6a31a 64e3f57 --numstat -- apps/frontend/`: `40 0` for that file only; 0 removed lines. |
| G6 on merged tree | VERIFIED | Probe: every final line in `allowed_guidance(facts)`; catalog text shown, never model text. |
| 6/8 limits and never-remove-streamed | VERIFIED | Probe: every streamed line present in the final answer; when lines are added, final length <= max(8, streamed lines). (Unchanged design: with nothing missing the model answer is returned as is.) |
| Telemetry content-free | VERIFIED | `telemetry.py` unchanged by both sides (`git diff 7d6a31a 64e3f57` and `79644e2 64e3f57` empty); `AnswerMetrics` carries counts only; `outcome.validation` is "never part of the metrics" (`main.py:224-226`). |

## 3. Contract and integration findings

- **R5-B1 (blocking, data protection / contract): answer records store registry and document
  values unredacted.**
  - `guardrails.py:145-159,191` (D-090 E2) adds `<Field>: ACRA says "<value>", the document
    says "<value>".` to `allowed_guidance`.
  - `answer_records.py:63-75` stores every allowed line as text (tagged `case`), unredacted,
    on **every** record, including model-down and case-data answers.
  - `main.py:438-446` stores a model answer's lines (`chosen_lines`) and `shown_answer`
    unredacted, because "a model answer is its checked lines"; only a case-data answer is
    redacted.
  - `knowledge_api.py:259-278` returns all three to the Director and the asking RM, and
    `RequestPage.tsx:146-185` displays them.
  - Reproduced on the merged tree (scratchpad probe): the model answer's line
    `Registered address: ACRA says "18 OFFICIAL MOCK STREET, #01-01, 123456, SG", the document
    says "18 GARDEN WALK, #01-01, 018919, SG".` is stored verbatim in `allowed_lines`,
    `chosen_lines` and `shown_answer`; the model-down record of the same question stores the
    same line as `ACRA says "[ADDRESS]", the document says "[ADDRESS]"` in `shown_answer` but
    still raw in `allowed_lines`.
  - D-084 D1 / ADR-012 Amendment 1 relax section A only for the question and a case-state
    snapshot (`ADR-012:399-403`, `DECISION_LOG.md` D-084 D1). ADR-012 Amendment 2
    (`:515-516`) and D-090 (`DECISION_LOG.md:1114`) say D-090 amends section C only.
  - Neither PR alone did this: on main the catalog has no case values, and before the merge
    the branch had no records. It arises from the merge and is not listed in the merge commit
    or the PR draft.
  - Fix (bounded, but the choice is the owner's): either (a) redact record copies of
    case-sourced lines with the request's `Redactor`, i.e. `allowed_lines` entries tagged `case`,
    and model `chosen_lines`/`shown_answer`, keeping `fix_start_lines`' allowed/chosen
    comparison consistent; or (b) record the wider section A relaxation in D-084/D-090 and
    ADR-012 for Shane's explicit acceptance. Add a test either way.
- No backend, schema, connector or configuration change in the merge delta; no live ACRA,
  GoldTier or sponsor claim. D-084 and D-090 both remain PROPOSED.

## 4. Tester and adversarial findings

Run by this reviewer on HEAD `64e3f57` / tree `75df353`, local macOS, repository venv,
`PYTHONDONTWRITEBYTECODE=1`, caches off or in the scratchpad:

| Check | Result |
| --- | --- |
| `cd apps/assistant && python -m pytest -q -o addopts="" -p no:cacheprovider` | **1761 passed** in 77 s |
| `ruff check --no-cache .`; `ruff format --check --no-cache .` | All checks passed; 82 files already formatted |
| `mypy ai_assistant`; `mypy assistant_eval` (cache in scratchpad) | no issues in 28 files; no issues in 9 files |
| `python scripts/evaluate_answers.py check` | snapshots are current (84 turns, sha256 1421eedb7fd536ea) |
| `npx vitest run src/pages/AiAssistantPanel.test.tsx src/pages/KnowledgeReview.test.tsx` | 2 files, 55 passed |
| `npx tsc -b --noEmit` | exit 0 |
| `scripts/run_e2e.py --backend-port 49165 --frontend-port 45573 --selectors-file` (answer-records `:12`, streaming `:10`) | **PASS 2/2** (`scratchpad/qg-r5/e2e-r5.json`); no other `run_e2e` was running |
| `git diff --check 7d6a31a...64e3f57`; `check_architecture.py`; `check_secrets.py` | clean; PASS; no supported secret patterns |
| Record probe (`scratchpad/qg-r5/probe/test_r5_probe.py`, /chat and /chat/stream) | `chosen_lines == answer` incl. added lines; `dropped` redacted (`[ADDRESS]`); `left_out` == dropped count; **raw case values in `allowed_lines`/`chosen_lines`/`shown_answer` (R5-B1)** |
| Guard fuzz (`scratchpad/qg-r5/probe/fuzz.py`) | 4,500 answers, 0 failures (section 2) |

Reused, not rerun: full frontend vitest 1109/1110 (macOS-only `ViteHistoryFallback.test.ts`) and
`npm run build` OK (developer, on `64e3f57`); full E2E not green on earlier trees with the same 9
failures on clean main (earlier reports). Keep-going runs are diagnostic only. `pre_pr_check.py`
not run (publication step). CI has no `apps/assistant` job and is billing-blocked; all evidence
is local, not hosted CI. The reviewer's runs created the ignored `apps/assistant/data/`; it was
removed. Pre-existing ignored `__pycache__` folders were left as found.

## 5. Code and architecture review

- R5-B1: see section 3.
- **R5-M1 (minor, test gap):** the merge commit states "the answer record keeps
  response.answer, so 'Lines shown to the RM' includes added lines", but no test pins it.
  `test_answer_records.py:24-25,142-143` were switched to topic-free questions, which is
  justified (assertions unchanged) but sidesteps the combination. Add one record test with a
  topic question asserting `chosen_lines == reply["answer"].splitlines()`, the added positions,
  and `left_out`/`dropped_lines` unchanged.
- **R5-M2 (minor, user-visible wording):** `RequestPage.tsx:195` (#113) tells the Director "Not
  an allowed line: only exact allowed lines are shown." After D-090 E6 matching ignores
  formatting, so "exact" is now wrong (a line can be dropped for one disallowed sentence, or
  kept despite Markdown).
- **N13 (note) POLICY_LINES:** `POLICY_LINES = allowed_guidance({}) - {NO_CONTACT}` gives 13
  fixed, unconditional lines (6 disclaimers, 6 "Open the section" lines, `OUT_OF_SCOPE`); none
  can hold case values (built from empty facts), so the `skip` set in `fix_start_lines`
  (`answer_records.py:142`) can never let a case-filled line skip redaction, and a skipped
  policy line is fixed wording that needs none. Excluding `NO_CONTACT` is consistent with
  `NOT_READY` and `APPROVAL_NOT_OFFERED`, which are also conditional and already tagged `case`.
  Imprecision: E1 explanation sentences, `NOT_READY`, `APPROVAL_NOT_OFFERED` and `NO_CONTACT`
  hold no case values but are tagged `case`, which the docstring (`:66-67`) defines as "filled
  from this case". Optional: a third tag or a docstring change.
- **N14 (note):** the record has no `added_lines`, so the Director cannot tell service-added
  required lines from the model's choice. Allowed model lines trimmed by the 6/8 rule show
  neither under "Lines shown" nor under "Lines left out". `suggestedCause` is unaffected (a
  model answer always has shown lines).
- R1-R4 notes N1, N4, N5, N7, N11 and N12 stand.

## 6. Security review

- R5-B1 is the security finding: registry and document values (KYC/document evidence) are
  stored in clear in the assistant's local store for up to 7 or 30 days and shown on the
  Director's request page, beyond the documented D-084 relaxation and inconsistent with the
  redaction applied to the same text elsewhere. It is contained to the git-ignored local
  SQLite store, Director and own-RM access, logged views and D-084 retention. Nothing is newly
  tracked in git, and no secret, `.env` or token is involved.
- `dropped_lines` stay redacted and capped (`capped_dropped`). Telemetry stays content-free.

## 7. Required fixes

1. **R5-B1 (blocking):** redact the case-sourced lines that records store (`allowed_lines`
   tagged `case`, model `chosen_lines` and `shown_answer`), or obtain and document Shane's
   explicit acceptance of the wider section A relaxation in D-084/D-090 and ADR-012
   Amendments 1 and 2. Either way, list it in the PR and add a test.
2. **R5-M1 (minor):** add a record test for a topic question with added lines.
3. **R5-M2 (minor):** correct the "only exact allowed lines" wording on `RequestPage.tsx:195`,
   or list it for Shane as a #113 follow-up.

A recheck needs only the fix delta plus the evidence it invalidates (assistant pytest, and the
answer-records E2E if the record or page changes).

## 8. Readiness

- Branch quality gate: **FAIL** on `64e3f57` / `75df353` against `7d6a31a`, for R5-B1 only.
  All other merge claims are verified.
- Unchanged from R4: before a PR the branch still needs Shane's acceptance of D-090 (incl. E2)
  and D-084, his review of the #115 runner and fixture changes, an owner decision on the
  not-green full E2E (pre-existing failures on main), his manual-CI exception, and
  `python scripts/pre_pr_check.py` on the clean committed tree.
- No live ACRA verification or real GoldTier integration readiness is claimed or affected.

## 9. Git status

- Checkout detached at `64e3f5741d86e073c7673d694636e0045f859802`, tree
  `75df3531b3681a18dbf815c1c2f8385334b620dc`; nothing staged or modified. This report is the
  only new file (untracked).
- No implementation, test or doc fix, commit, push, merge, rebase, reset or stash was made.

Reviewed HEAD: 64e3f5741d86e073c7673d694636e0045f859802
Reviewed tree: 75df3531b3681a18dbf815c1c2f8385334b620dc

FAIL
