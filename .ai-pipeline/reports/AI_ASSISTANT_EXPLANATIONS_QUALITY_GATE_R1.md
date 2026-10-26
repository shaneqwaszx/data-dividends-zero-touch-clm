# AI Assistant explanations (D-090, ADR-012 Amendment 2) - independent quality gate, recheck R1

Reviewer: fresh independent QG subagent. It did not author or remediate the reviewed content
and did not run the first gate. Date: 2026-10-26. Skill: `.agents/skills/fyp-quality-gate/SKILL.md`
and `references/report-template.md`, read in full. AGENTS.md and the evidence-reuse and
change-class sections of `docs/DEVELOPMENT_WORKFLOW.md` were read.

## Reviewed content identity

| Item | Value |
| --- | --- |
| Checkout | `/Users/tasha/Documents/GitHub/dd-clm-qg-explanations`, detached, clean (`git status --porcelain` empty before and after every check) |
| HEAD | `33dc3ad353060116c67c7d59e34241019d6fc3e8` |
| Tree | `9ab9bed0cdfe5cb0d326ba3a914ff9ed65af3484` |
| Base / origin/main | `1d039865bf5197a76add7f733128829bb05019ac` (#111) |
| Branch commits | `e14fc25` (feature), `a49db57` (merge of `1d03986`, D-085 -> D-090 renumbering), `33dc3ad` (remediation of the first gate) |
| Whole-branch diff | `git diff 1d03986...33dc3ad`: 19 files, +1926/-69 (7 assistant source files, 8 assistant test files incl. new `test_explanations.py`, `AiAssistantPanel.test.tsx`, ADR-012, DECISION_LOG, first gate report) |
| Remediation delta | `git diff a49db57 33dc3ad`: `briefing.py`, `guardrails.py`, `guide.py`, `test_explanations.py` (additions only), ADR-012, DECISION_LOG, first gate report. No frontend, backend, E2E, script or config path. |

Change classes: assistant service behaviour (BACKEND_DOMAIN-like), the assistant output policy
as a trust boundary (AUTH_RBAC_SECURITY-adjacent), FRONTEND_UI (one test file only), DOCS.

## 1. Executive result

**PASS.** The four findings of the first gate are closed and I could not break the fixes; the
remediation introduced no regression. My own adversarial checks of G6 on the whole branch
(randomised batch and streamed answers, required-line insertion, template filters) found no
line shown outside the catalog. The remaining items are notes to carry into the PR text, not
required fixes. Merge still depends on owner decisions that this gate cannot give (section 8).

## 2. Acceptance checklist

| Claim | Result | Evidence |
| --- | --- | --- |
| F1 closed: a document value or blocker title cannot close the template's quotes | VERIFIED | `guardrails.py:108-117` refuses `"`, U+201C, U+201D. `_UNSUPPORTED_CHARACTER` (`guardrails.py:250`) refuses every other quote-like character (U+201E, U+201F, U+00AB/U+00BB, U+FF02, U+2033 probed: refused). The first gate's breakout values are now refused (`qg-r1/probe_r1.py`); new parametrised cases at `test_explanations.py:389-392` and `:576`. |
| F2 closed: "Approving the case is not offered to you on this case." is never offered on a ready case | VERIFIED | `approval_not_offered = not_ready and not approval_offered` (`guardrails.py:98-103`), used by `allowed_guidance` (`:219`) and the no-model answer (`briefing.py:312`); `topic_plan` filters to allowed lines, so it is not required either. Probe: line offered and required for the Merlion case, the no-action viewer and HR; not offered, not required, not in the fallback, and dropped when the model writes it, on ready and completed facts. Truth when offered: the backend refuses confirmation while readiness has blockers (`clm_orchestration.py:603-607`, `:922-935`), the frontend gates the Send button on zero readiness blockers (`ReviewAndSend.tsx:246-248`), and the Review & Send step (`TARGET_CONFIRMATION_REQUIRED`) is never projected as an intervention (`api_models.py:972-974`), so a case at final review has no blockers and the line is not offered. New test `test_the_approval_line_is_never_offered_on_a_ready_case` (`test_explanations.py:551`). |
| F3 closed: the document review sentence no longer states a sufficient condition | VERIFIED, note N6 | `guide.py:221`: "The document review needs a review decision for every field read from the document." Matches the human-review completion rule (`document_processing.py:731-740`). Residual imprecision recorded as N6. |
| N2 closed: the template comment does not claim approval-like values are refused | VERIFIED | `guardrails.py:136-140` now says the checks catch only their listed phrasings; ADR-012 Amendment 2 and D-090 E2 say the same. |
| G6 on the whole branch: only allowed lines, in the catalog's words | VERIFIED | `_Catalog` (`guardrails.py:653-701`) keys only whole allowed lines, bare offered labels and untagged knowledge sentences; no sub-sentence of an allowed line is a key, so a model cannot pull "The case is ready for GoldTier." out of a template line (probed). `qg-r1/probe_g6.py`: 2000 random answers over 5 fact shapes (incl. hostile document values) mixing allowed lines, junk, joined lines, upper-casing, curly quotes and list markers; every shown line is in `allowed_guidance`; `StreamingGuard` fed in random 1-15 character chunks emits only allowed lines and ends equal to `validate_answer` (text and `left_out`); `with_required_lines` for 8 questions adds only allowed lines and keeps the 6-line cap. |
| Templates filled only from the backend projection | VERIFIED | Difference values from `active_exceptions` evidence via `context._evidence_for`; titles from interventions with owners limited to `guide.OWNER`; offered labels from `authorized_actions` only. |
| New catalog sentences are true for this app | VERIFIED, note N6 | Approval line: see F2. Not-ready line: `not_ready` follows readiness blockers and excludes completed cases. Ownership sentences: checked by the first gate against `manual_ownership_evidence.py`; unchanged since. Difference sentences: "can" wording, general reasons, no case finding. |
| D-090 / ADR-012 Amendment 2 updated with the fixes; DECISION_LOG append-only against main | VERIFIED | `git diff 1d03986...33dc3ad -- docs/decisions/DECISION_LOG.md` has no removed lines; ADR table rows and D-090 E2/E3 describe the new filter and condition. Both remain PROPOSED with owner acceptance required. |
| Changed existing tests are complete and approved | VERIFIED | Removed/changed lines in `git diff 1d03986...33dc3ad -- apps/assistant/tests apps/frontend` match `scratchpad/changed-tests.md` exactly; the remediation only adds tests. None weakens G6 (the first gate's assessment stands; N5 below). |
| Browser acceptance | NOT GREEN, pre-existing; not required by the change-class matrix for this delta | See section 4. |

## 3. Contract and integration findings

- No backend, API, schema, connector, configuration, E2E or production frontend change on the
  branch. The assistant stays GET-only towards the CLM backend.
- No live ACRA, GoldTier or sponsor claim is made or affected.
- D-090 (incl. E2, which relaxes ADR-012 section C) and D-084, which it builds on, are PROPOSED.
  The filter E2 describes now matches the code (F1 closed), so the owner is accepting what the
  code does.
- Blocking: none. Minor: none.

## 4. Tester and adversarial findings

Commands run by this reviewer on HEAD `33dc3ad` / tree `9ab9bed` (local macOS, Python 3.12.14
venv; caches redirected or disabled, no repository files written):

| Check | Result |
| --- | --- |
| `cd apps/assistant && python -m pytest -q -o addopts="" -p no:cacheprovider` | **1372 passed** in 32 s (first gate on `a49db57`: 1368; +4 = new parametrised and approval tests) |
| `ruff check --no-cache .`; `ruff format --check --no-cache .` | All checks passed; 65 files already formatted |
| `mypy --cache-dir <scratch> ai_assistant` | Success: no issues in 26 source files |
| `git diff --check 1d03986...33dc3ad` | clean |
| `python scripts/check_architecture.py`; `check_project_state.py`; `check_secrets.py` | PASS; PASS; no supported secret patterns |
| `qg-r1/probe_r1.py` (F1 quote set, F2 seven fact shapes) | as in section 2 |
| `qg-r1/probe_g6.py` (randomised G6, streaming equivalence, required lines) | 2000/2000 cases held |

Reused, not rerun (identity checked):

- Frontend: no frontend path changed between `a49db57` and `33dc3ad`. The first gate's
  `AiAssistantPanel.test.tsx` 15/15 and the developer's `tsc -b` OK, `vitest` 1084/1085 (known
  macOS-only `ViteHistoryFallback.test.ts`) and `npm run build` OK on `a49db57` carry forward.
- Browser: the E2E suite never starts the Python assistant service; the only assistant spec,
  `e2e/assistant-streaming.e2e.ts`, renders the panel against a synthetic in-test HTTP server.
  The remediation delta (assistant Python and docs only) therefore cannot reach any browser
  result, and reusing the `a49db57` browser evidence is valid under the workflow's
  evidence-reuse rule. Identity in the JSON files: official full run `a49db57`/`0c70214`,
  `complete: false`, FAIL at `e2e/database-classification.e2e.ts:191` (30 PASS, 1 failure,
  84 not run); diagnostic `--keep-going` run `a49db57`/`0c70214` 106 PASS / 9 ASSERTION_FAILURE;
  the same 9 selectors fail at the same assertion lines on clean `1d03986`/`f031626`
  (`failing-on-main-1d03986.json`); `assistant-streaming.e2e.ts:10` PASS on `33dc3ad`/`9ab9bed`
  (`assistant-e2e-33dc3ad.json`, clean, origin/main `1d03986`).
- The keep-going result is diagnostic only, not an acceptance PASS. The official full browser
  run on this candidate is **not green**; the failures are pre-existing on `origin/main` and not
  caused by this branch. Full E2E is not an R/A row for these change classes in the
  `DEVELOPMENT_WORKFLOW.md` matrix and no browser surface is affected, so it does not block this
  verdict; it does need an explicit owner decision before merge (section 8).
- `pre_pr_check.py` was not run (publication step). CI has no `apps/assistant` job and is
  billing-blocked; all evidence above is local and is not hosted CI.

## 5. Code and architecture review

- The remediation is small and bounded to the findings. `approval_not_offered` is a single
  shared predicate for the catalog and the no-model answer, so the two cannot drift.
- `approval_offered` still looks for an approve-type label the backend never emits; it is now
  only a further restriction inside `approval_not_offered`, so it cannot make a false line
  appear. Harmless.
- No new coupling beyond the first gate's notes; scope matches D-090 E1-E6.

Notes (not required fixes; carry into the PR text):

- **N1** (first gate, still acceptable): `_EMPHASIS` strips unpaired `*`/`_`; output is catalog
  text. Not yet in committed docs; mention in the PR.
- **N3** (first gate, partly disclosed): ADR-012 Risks (`ADR-012...md:599`) says the cap can drop
  a model line; it does not say a line already streamed to the RM can disappear from the final
  answer and is not counted in `left_out`. Mention in the PR.
- **N4** (first gate, still acceptable): topic routing changes some no-model answers (e.g. "What
  is the registered address?" gets the difference explanation, losing the ACRA provenance
  line). Not in committed docs; mention in the PR.
- **N5** (first gate, approved): prompt budget `< 8000` -> `< 9000` plus `< 1000` for the topic
  message; recorded in `changed-tests.md`; list in the PR as a performance-budget change.
- **N6** (new): "The document review needs a review decision for every field read from the
  document." is the human-review rule. The backend can also finish a document without a human
  decision on each field: automated confirmation marks matching fields accepted
  (`document_processing.py:960-990`), a "Keep registry value" exception resolution can move a
  document to REVIEWED when no blocker remains (`document_processing.py:1075-1083`), and a
  cleared reconciliation skips the document-review blockers (`clm_orchestration.py:1584`). In
  each of these the field gets a decision of some kind, or the case decision replaces the
  review, so the sentence does not mislead the RM about what they must do; a later wording
  such as "...needs every field read from the document to be decided" would be exact.
- **N7** (new): straight and typographic single quotes, backticks and `**` are allowed inside a
  template value (`qg-r1/probe_r1.py`). They cannot close the template's double quotes and the
  panel renders plain text (no Markdown or HTML), so containment holds.
- The commit message of `e14fc25` still says D-085 (history only; code and docs say D-090).

## 6. Security review

- F1 containment of untrusted document text is now complete for the template's own quote
  character set. The no-model case-data answer still prints document values unfiltered, as it
  did on main before this branch (`briefing._difference_lines`); unchanged risk, disclosed in
  ADR-012 Risks.
- No secrets, `.env`, tokens or PII newly tracked (tests use the synthetic Merlion/Garden
  fixture; secret scan passed). No logging change. Allowed lines stay viewer-specific; backend
  authorization untouched.
- Findings: none blocking, none minor.

## 7. Required fixes

None. Notes N1, N3-N7 go into the PR description; they are not gate conditions.

## 8. Readiness

- Branch quality gate: **PASS** on `33dc3ad` / `9ab9bed`. Any change to this content needs a
  fresh review of the changed scope.
- Before merge, outside this gate:
  - Shane's explicit acceptance of D-090 (incl. E2's relaxation of ADR-012 section C) and of
    D-084;
  - an owner decision on browser acceptance: the official full E2E on this candidate is not
    green because of 9 selectors that fail identically on `origin/main` `1d03986`;
  - Shane's approval of the manual-CI exception (no `apps/assistant` CI job, CI billing-blocked);
  - `python scripts/pre_pr_check.py` on the clean committed tree at publication.
- No live ACRA verification or real GoldTier integration readiness is claimed or affected.

## 9. Git status

- Checkout `/Users/tasha/Documents/GitHub/dd-clm-qg-explanations`, detached at
  `33dc3ad353060116c67c7d59e34241019d6fc3e8`, tree `9ab9bed0cdfe5cb0d326ba3a914ff9ed65af3484`.
- No staged or tracked modification; the only new file is this untracked report.
- No implementation, test or doc fix, commit, push, merge, rebase, reset or stash was made.
  Reviewer probes are in the session scratchpad (`scratchpad/qg-r1/`).

Reviewed HEAD: 33dc3ad353060116c67c7d59e34241019d6fc3e8
Reviewed tree: 9ab9bed0cdfe5cb0d326ba3a914ff9ed65af3484

PASS
