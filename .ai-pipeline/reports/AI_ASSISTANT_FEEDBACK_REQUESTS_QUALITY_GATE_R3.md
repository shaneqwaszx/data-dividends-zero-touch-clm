# AI Assistant feedback, enhancement requests and single-reviewer mode: independent Quality Gate R3 (latest-main integration recheck)

This is a focused Stage 3 recheck under `fyp-quality-gate`. It reviews the integration of
latest `origin/main` (`ceefe1e`, PRs #102-#107) into the branch and the renumbering of the
branch's proposed decision from D-076 to D-080, and reruns the evidence that integration
invalidated. Review of unchanged feature content is reused from the first gate, R1 and R2.

- **Change class of the reviewed delta:** integration merge (main's E2E runner, UI
  enhancement v1 and ownership/UBO D-076..D-079) plus a documentation/comment-only decision
  ID rename in branch-owned files. No branch behaviour, API, schema or test assertion changed.
- **Independence:** I did not write, integrate or remediate this change. I wrote only this
  report, and I did not read `.env`. Probes, a `ceefe1e` frontend snapshot, the build output,
  the mypy cache and E2E results are only in the session scratchpad.

## 1. Executive result

**Verdict: PASS.**

- The merge is clean apart from the hand resolution of `docs/decisions/DECISION_LOG.md`.
  Compared with git's own automatic merge of `cd01db4` and `ceefe1e`, every hand edit is a
  `D-076` -> `D-080` substitution, plus the decision-log entry appended after main's D-079.
- The D-080 decision-log entry is byte-identical to the branch's former D-076 entry apart from
  the ID. Main's ownership D-076..D-079 entries and every other main D-076 reference are
  unchanged (per-file D-076 counts in `a399f20` equal those in `ceefe1e`, apart from the
  three historical feedback gate reports).
- No branch-owned live file still calls the feedback decision D-076.
- Main's four assistant changes (`guide.py` section list, two guidance front-matter `stages`
  lines, `test_required_p2.py`) do not touch any file the branch changed and do not interact
  with the exact-line catalog, request drafting, redaction or the knowledge store in a way
  that breaks them. The case envelope v11+ `ownership_discovery` audit is not in the CLM
  summary the assistant reads (probe in section 3).
- Critical contracts are preserved: `guardrails.py` is identical to main; the store and API
  code differ from R2's reviewed content only in comments.
- No required finding. Two informational notes (I9, I10).
- This verdict does not authorize commit, push, PR or merge. **The proposed decision, now
  D-080, still needs Shane's explicit acceptance before merge.**

## 2. Reviewed identity (frozen)

- **Repository:** `/Users/tasha/Documents/GitHub/data-dividends-zero-touch-clm`, branch
  `feat/ai-assistant-feedback-requests`.
- **Reviewed candidate:** HEAD `28614002baa5562c0a2a44dc1eb8020aa556f4ed`, tree
  `a399f200afd3b6adb254590a1e47edf398b96089`. Working tree clean at the start (no staged,
  modified or untracked files).
- **Integrated `origin/main`:** `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322` (PR #107).
  `git merge-base HEAD origin/main` equals it; the branch is 0 behind and 10 ahead. I used
  the local `origin/main` ref and did not fetch.
- **Previous candidate:** `d5dd81f` (R2: PASS). Branch-side content since then is only
  `cd01db4`, which adds the R2 report.
- **Merge parents:** `cd01db4` and `ceefe1e`; previous merge base `9e47b4f`.
- **Automatic-merge reference:** `git merge-tree --write-tree cd01db4 ceefe1e` gives tree
  `e16b2b2` with one conflict (`docs/decisions/DECISION_LOG.md`) and one auto-merge
  (`docs/ARCHITECTURE.md`). `git diff e16b2b2 a399f20` touches 14 files: the 13 rename files
  listed in section 3 plus the decision log.
- **Branch delta vs main:** `git diff --name-status ceefe1e 2861400`, 26 files: three
  historical gate reports, 13 assistant files, 6 frontend files, `ARCHITECTURE.md`, ADR-012
  and the decision log (3270 insertions, 384 deletions).

## 3. Integration verification

**Hand edits are ID-only.** For each file in `git diff --name-only e16b2b2 a399f20` other
than the decision log, I compared `sed 's/D-076/D-080/g'` of the automatic-merge version with
the committed version:

| File | Result |
|---|---|
| `apps/assistant/.env.example`, `README.md` | ID-only |
| `apps/assistant/ai_assistant/config.py`, `knowledge/drafting.py`, `knowledge/store.py`, `knowledge_api.py` | ID-only (docstrings/comments) |
| `apps/assistant/tests/test_knowledge_redaction.py`, `test_knowledge_review.py`, `test_knowledge_single_reviewer.py` | ID-only (docstrings/comments) |
| `apps/frontend/src/aiAssistant.ts`, `pages/KnowledgeReview.tsx` | ID-only (comments) |
| `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md` | ID-only |
| `docs/ARCHITECTURE.md` | Only lines 975 and 979 changed (both D-076 -> D-080, branch paragraph). The blanket `sed` differs only because it would also rewrite main's ownership D-076 at `:1045` and `:1065`, which were correctly left alone. |

**Decision log.** `git diff ceefe1e a399f20 -- docs/decisions/DECISION_LOG.md` is a pure
43-line append after D-079 (`:477`); main's text is untouched. The appended entry, compared
with the branch's former entry extracted from `cd01db4` after `s/D-076/D-080/`, is identical
(42 lines each). The log now has one `## D-080` heading and headings D-076..D-079 are main's.

**No stale feedback D-076.** `git grep -n D-076 a399f20`, excluding the three historical
feedback gate reports, lists only ownership references (ownership gate reports, backend
ownership tests, `ARCHITECTURE.md:1045/1065`, `PROJECT_STATE.md:143`, ownership contracts,
ADR-013, `DECISION_LOG.md:352/390`, `OPEN_QUESTIONS.md:152`). For every file containing
D-076 at `ceefe1e`, only `ARCHITECTURE.md` and `DECISION_LOG.md` differ at HEAD, and the
per-file D-076 counts are unchanged.

**No assertion change vs R2 or main.** Main changed no branch-owned file except the two
docs. `git diff cd01db4 2861400` on the branch's files, ignoring D-076/D-080 lines, shows
only main's added ownership sections in those two docs. Every branch test change since R2 is
a docstring/comment ID substitution. The branch's test delta vs main is therefore exactly the
one R1/R2 reviewed (including the 15 superseded tests the PR must list).

**Main's assistant changes** (`git diff 9e47b4f ceefe1e -- apps/assistant`, from PR #103):

- `guide.py`: `CASE_PAGE_SECTIONS` replaces "Submission readiness" and "GoldTier submission
  package" with "GoldTier Details & Status"; `GOLDTIER_CLASSIFICATION_REQUIRED` points there.
  These feed `guardrails.allowed_guidance` section lines and `context.py` section mapping;
  neither file is changed by the branch (`git diff ceefe1e 2861400 -- guardrails.py
  briefing.py context.py clm_client.py` is empty).
- `guidance/environments.md`, `guidance/review-and-send.md`: front-matter `stages` lines
  only. The branch changes neither file nor the guidance seeding (`service.py` +4 lines are
  unrelated). Request and fix `stages` are free strings from the case context and are not
  validated against `CASE_PAGE_SECTIONS`, so the renamed sections cannot reject a request.
- `tests/test_required_p2.py`: section count 7 -> 6, the stage-inventory test now resolves
  constants, and one new test `test_r1_every_blocker_location_is_a_case_page_section`. This
  is the +1 (1189 -> 1190). It is main's change, not a branch change.

**Case envelope v11+ and redaction (probe).** A Director's fix is redacted against the
request's case summary, read from `GET /api/clm/zero-touch/cases/{id}`. Main's
`OwnershipDiscoveryRecord` carries `display_name` without `party_type` inside a `records`
list, a shape `redaction.case_parties` would not treat as a party. I ran main's offline
five-layer hybrid journey (`test_five_layer_hybrid_journey.system()`/`start()`) in the
scratchpad and fetched that summary: it contains **no** discovery name path, and every
`name`/`display_name`/`legal_name` string in it is in `case_parties` except a numeric
policy weight. The discovery audit is only on `/api/onboarding/cases/{id}/ownership`, which
the assistant does not read. No new redaction gap. `redaction.py` is unchanged by the branch.

## 4. Critical contracts after the merge

| Contract | Evidence |
|---|---|
| Exact-line catalog | `guardrails.py` identical to main; guardrail/catalog tests pass (focused subset below) |
| Maker-checker / D-074 with single-reviewer off | `store.py` and `knowledge_api.py` differ from R2's content only in comments; `test_with_the_setting_off_the_two_person_rule_is_unchanged`, `test_an_rm_can_never_approve_and_the_author_never_decides`, `test_a_director_edit_is_a_new_version_another_director_must_approve` pass |
| Retirement takes two reviewers | `test_retiring_still_takes_two_reviewers_in_single_reviewer_mode` passes |
| Permission recheck inside the SQLite transaction | `test_authorize_runs_first_inside_the_write_lock_and_its_error_rolls_back`, `test_a_caller_revoked_during_the_request_changes_nothing` pass |
| Director-only fix writing, HR refused | `test_only_a_director_handles_enhancement_requests` and the HR case in `test_knowledge_review_scope.py:219-230` pass |

## 5. Checks

**Rerun by me on tree `a399f20`** (repo `.venv`, Python 3.12, macOS; `PYTHONDONTWRITEBYTECODE=1`).

| Check | Result |
|---|---|
| `cd apps/assistant && ../../.venv/bin/python -m pytest -p no:cacheprovider` | **1190 passed** in 30.44s (R2: 1189; +1 is main's new `test_r1_every_blocker_location_is_a_case_page_section`) |
| Focused: `pytest tests/test_required_p2.py tests/test_knowledge_single_reviewer.py tests/test_knowledge_review.py tests/test_knowledge_review_recheck.py tests/test_knowledge_review_safety.py tests/test_knowledge_review_scope.py tests/test_knowledge_redaction.py` | 218 passed |
| Contract subset: `pytest tests -k "hr or recheck or revoked or lost or two_person or setting_off or maker or self or retir or allowed or guardrail or catalog"` | 734 passed, 456 deselected |
| `ruff check ai_assistant tests --no-cache` | All checks passed! |
| `ruff format --check ai_assistant tests --no-cache` | 60 files already formatted |
| `mypy ai_assistant --cache-dir <scratchpad>` | Success: no issues found in 26 source files |
| `cd apps/frontend && npm run typecheck` | exit 0 |
| `npx vitest run` | 63 files, **1056 tests: 1055 passed, 1 failed** = `ViteHistoryFallback.test.ts` ("/src/styles.css: expected 'text/css' to contain 'text/javascript'") |
| Same test on a `git archive ceefe1e apps/frontend` snapshot (scratchpad, shared `node_modules`) | **fails identically on main**: pre-existing macOS baseline, not caused by the branch |
| `npx tsc -b` then `npx vite build --outDir <scratchpad>/dist` (the `npm run build` steps, output kept out of the repo) | exit 0, built (chunk-size warning only) |
| `python scripts/run_e2e.py --selectors-file <scratchpad>/selectors.txt` (`e2e/assistant-streaming.e2e.ts:10`) `--results-json <scratchpad>/e2e-r3-results.json` | 1 passed, `E2E SUITE PASS`, exit 0. It is the only E2E file that references the assistant. |
| Redaction-coverage probe on main's five-layer hybrid case summary | see section 3 |
| `python scripts/pre_pr_check.py` on clean HEAD `2861400` (before this report existed) | **SUMMARY: PASS (0 unsafe conditions, 1 warning(s))**; the warning is the expected `apps/assistant/ai_assistant/config.py` setting |
| `python scripts/check_project_state.py` | PROJECT STATE CHECK: PASS |
| `python scripts/check_architecture.py` | ARCHITECTURE CHECK: PASS |
| `git diff --check ceefe1e 2861400`, `cd01db4 2861400`, `e16b2b2 a399f20` | clean |
| `git status --short` after all checks | empty (before this report) |

The implementer's Stage 2 numbers (1190 pytest, 60 formatted, 26 mypy files, 1055/1056
vitest, build 0, 1 E2E passed, both checkers PASS) match my reruns on the same tree.

**Not rerun, reused:** R1/R2 review of authorization, redaction, single-reviewer control,
CAS, migration (R1-F1 fix) and acceptance criteria, because none of that code changed.

CI is billing-blocked and has no `apps/assistant` job. All of the above is local evidence
and is not hosted CI.

## 6. Findings

**Required findings: none.**

**R1/R2 informational notes I1-I8:** unchanged; none became required.

**New informational notes (no fix required):**

- **I9: decision chronology after the renumber.** `docs/decisions/DECISION_LOG.md:477-479`:
  D-080 is dated 2026-10-21 but follows D-079 (2026-10-24), because its number was reassigned
  at integration. Cosmetic; the PR body should say the decision was renumbered from D-076.
- **I10: historical reports use the old ID.** The first gate report, `_R1.md` and `_R2.md`
  call the feedback decision D-076, which on main now names ownership discovery. Leaving them
  unedited as records is correct; this report and the PR body record the mapping
  (feedback D-076 in those reports = D-080).

## 7. Remaining preconditions for publication

1. **D-080 owner acceptance:** Shane must explicitly accept D-080 (single-reviewer mode, on by
   default, relaxing D-074's two-person control) before merge, whatever this verdict says.
2. **Unchanged content:** the reviewed content must stay tree `a399f20` plus this report only.
   Any further change to code, tests or docs needs a fresh independent recheck.
3. **Explicit owner authorization** for committing this report, push and PR creation; a
   repository-owner human merges.
4. **Pre-PR state:** rerun `pre_pr_check.py` on the final committed state including this
   report's commit; fetch latest `main` and reassess if it has moved (I did not fetch).
5. **PR body:** flag D-080 (renumbered from D-076) for Shane, list the 15 superseded tests,
   and state that evidence is local, not hosted CI.
6. **Residual risks carried from R1/R2:** no browser E2E for the feedback note, Review window
   or confirm step; redaction limited to case-supplied values and patterns; POLICY_APPROVE
   stays PROJECT_DEFINED_PROVISIONAL and Q-014 stays UNKNOWN_BLOCKED; the macOS-only
   `ViteHistoryFallback.test.ts` baseline failure.

## 8. What changed and Git status

- **Changed by the reviewed delta:** integration of main `ceefe1e`; decision ID D-076 -> D-080
  in branch-owned docs, comments and docstrings; decision-log conflict resolved by appending.
- **Not changed:** branch behaviour, API and types, configuration surface (names and defaults),
  SQLite schema, business rules, auth and security, test assertions, provider status.
- **Git:** branch `feat/ai-assistant-feedback-requests` at HEAD `2861400`. Nothing staged, no
  tracked modifications. The only untracked file is this report.
- **No other changes:** I made no implementation fix, commit, push, stash, reset, rebase,
  checkout, PR or merge, and started no other phase.

**Verdict: PASS**
