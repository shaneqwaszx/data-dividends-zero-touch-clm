# AI Assistant feedback, enhancement requests and single-reviewer mode: independent Quality Gate R4 (latest-main integration recheck)

This is a focused Stage 3 recheck under `fyp-quality-gate`. It reviews the integration of
latest `origin/main` (`7cd2bd9`, PR #109, ownership D-080..D-082) into the branch and the
renumbering of the branch's proposed decision from D-080 to D-083, and reruns the evidence
that integration invalidated. Review of unchanged feature content is reused from the first
gate, R1, R2 and R3.

- **Change class of the reviewed delta:** integration merge (main's Sim Lim ownership work,
  76 files, none under `apps/assistant` and none of the branch's frontend files) plus a
  documentation/comment-only decision ID rename in branch-owned files. No branch behaviour,
  API, schema or test assertion changed.
- **Independence:** I did not write, integrate or remediate this change. I wrote only this
  report and did not read `.env`. Probes, build output, the mypy cache and E2E results are only
  in the session scratchpad (`.../scratchpad/r4/`).

## 1. Executive result

**Verdict: PASS.**

- The merge is clean apart from the hand resolution of `docs/decisions/DECISION_LOG.md`.
  Compared with git's own automatic merge of `0b2c8dd` and `7cd2bd9`, every hand edit is a
  `D-080` -> `D-083` substitution, plus the decision-log entry appended after main's D-082.
- The D-083 decision-log entry is byte-identical to the branch's former D-080 entry apart from
  the ID. Main's D-080..D-082 entries and every other main D-080 reference are unchanged.
- D-083 is the number main itself reserved for this PR:
  `.ai-pipeline/reports/SIM_LIM_D080_D082_PUBLICATION_READINESS.md:52` ("D-083 is reserved
  for AI Assistant PR #108's currently proposed 'D-080'"), and that report says the
  allocation does not approve the relaxation.
- The branch's total delta against main is exactly R3's reviewed delta with D-080 -> D-083
  (checked file by file). `guardrails.py`, `briefing.py`, `context.py`, `clm_client.py`,
  `guide.py` and `knowledge/redaction.py` are identical to main.
- #109 changes nothing the assistant reads in a way that matters. A probe of a D-082
  POC-accepted case summary finds no new party-name path outside the redaction walker
  (section 3).
- No required finding. One new informational note (I11).
- This verdict does not authorize commit, push, PR update or merge. **The proposed decision,
  now D-083, still needs Shane's explicit acceptance before merge.**

## 2. Reviewed identity (frozen)

- **Repository:** `/Users/tasha/Documents/GitHub/data-dividends-zero-touch-clm`, branch
  `feat/ai-assistant-feedback-requests`.
- **Reviewed candidate:** HEAD `cb45d0cf8b1b47e6025e9ee4af15cf524106bd00`, tree
  `66a33d13a1eec337ff9ad482e33d4e2384f7a430`. Working tree clean at the start and after all
  checks (no staged, modified or untracked files before this report).
- **Integrated `origin/main`:** `7cd2bd9318bce6b4f8850c7f080a7015e5f2878b` (PR #109).
  `git merge-base HEAD origin/main` equals it; 0 behind, 12 ahead. Local ref used; I did not
  fetch.
- **Merge parents:** `0b2c8dd` (R3 report commit on top of R3's PASS tree `2861400`) and
  `7cd2bd9`.
- **Remote branch:** `origin/feat/ai-assistant-feedback-requests` is at `0b2c8dd`; `cb45d0c`
  is not pushed. (`gh` is not installed here, so I did not observe PR #108's body.)
- **Automatic-merge reference:** `git merge-tree --write-tree 0b2c8dd 7cd2bd9` gives tree
  `e8d0da0` with one conflict (`DECISION_LOG.md`) and one auto-merge (`ARCHITECTURE.md`).
  `git diff e8d0da0 cb45d0c` touches 14 files: the 13 rename files below plus the decision log.
- **Branch delta vs main:** `git diff --stat 7cd2bd9 cb45d0c`, 27 files (four historical gate
  reports, 14 assistant files, 7 frontend files, `ARCHITECTURE.md`, ADR-012, decision log),
  3474 insertions, 384 deletions. No `apps/backend` file.

## 3. Integration verification

**Hand edits are ID-only.** For each file in `git diff --name-only e8d0da0 cb45d0c` other than
the decision log, I compared `sed 's/D-080/D-083/g'` of the automatic-merge blob with the
committed blob (`git hash-object`):

| File | Result |
|---|---|
| `apps/assistant/.env.example`, `README.md` | ID-only |
| `apps/assistant/ai_assistant/config.py`, `knowledge/drafting.py`, `knowledge/store.py`, `knowledge_api.py` | ID-only (docstrings/comments) |
| `apps/assistant/tests/test_knowledge_redaction.py`, `test_knowledge_review.py`, `test_knowledge_single_reviewer.py` | ID-only (docstrings/comments) |
| `apps/frontend/src/aiAssistant.ts`, `pages/KnowledgeReview.tsx` | ID-only (comments) |
| `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md` | ID-only |
| `docs/ARCHITECTURE.md` | `git diff -U0 e8d0da0 cb45d0c` changes only lines 975 and 979 (both D-080 -> D-083, branch paragraph). The blanket `sed` differs only because it would also rewrite main's ownership D-080 text (e.g. `:1007`, `:1014`), which was correctly left alone. |

**Decision log.** `git diff 7cd2bd9 cb45d0c -- docs/decisions/DECISION_LOG.md` is a pure
43-line insertion at `:710` (no deleted line), after D-082. The new `## D-083` entry
(`:711`), compared with the branch's former `## D-080` entry from `0b2c8dd` after
`s/D-080/D-083/`, is identical (42 lines each). Headings D-080 (`:480`), D-081 (`:526`) and
D-082 (`:599`) are main's.

**No stale feedback D-080; main's D-080 untouched.** Per-file `git grep -c D-080` at
`cb45d0c` equals that at `7cd2bd9` for every file, apart from the historical R3 report (14
occurrences, deliberately unedited). No `D-080` appears in `apps/assistant`, `aiAssistant.ts`,
`KnowledgeReview.tsx` or ADR-012. D-083 now appears in the 14 branch-owned live files listed
above plus main's readiness report reservation.

**Delta equals R3's reviewed delta.** For all 21 branch files outside the reports and the two
shared docs, `sed 's/D-080/D-083/g'` of the blob at `2861400` (R3 PASS) equals the blob at
`cb45d0c`. For `ARCHITECTURE.md` and `DECISION_LOG.md`, the `+/-` lines of
`git diff ceefe1e 2861400` after the same substitution equal those of
`git diff 7cd2bd9 cb45d0c`. Main changed none of the branch's assistant or frontend files
between `ceefe1e` and `7cd2bd9`.

**No assertion change vs R3 or main.** Every branch test file is the R3 blob with comment ID
substitution only. #109 changed no `apps/assistant` file, so no main-side assistant test moved
either. The branch's test delta vs main is therefore exactly what R1/R2 reviewed (including
the 15 superseded tests the PR must list).

**#109 interaction with the assistant.**

- Frontend overlap: #109 changed `types.ts`, `ReviewAndSend.tsx`, `UboSummary.tsx`,
  `CaseDetail.tsx`, `OwnershipStructure.tsx` and others; none is a branch file and none
  references the assistant panel or Knowledge Review (grep). `npm run typecheck`, vitest and
  build pass on the merged tree.
- Backend: the assistant reads `/api/auth/me`, `/api/clm/zero-touch/cases/{id}` and
  `/api/onboarding/cases/{id}/documents` (`clm_client.py:85-97`). #109 adds
  `poc_acceptance`/`poc_basis_accepted` to `OwnershipAnalysisResponse` (served on
  `/api/onboarding/cases/{id}/ownership`, which the assistant does not read), share
  class/currency on entity-less shareholder evidence (registry cache), and a new automation
  event code `OWNERSHIP_POC_BASIS_ACCEPTED` with fixed message text. No new business exception
  type.
- **Redaction probe** (`scratchpad/r4/probe_poc.py`): ran main's `accepted_case()` from
  `test_poc_ownership_acceptance.py` (opt-in D-082 Garden case) and fetched the zero-touch
  summary. It contains the new event code but no `poc_acceptance` or `share_type`. Of 31
  name/share-type/currency-like strings, every party name is in `redaction.case_parties`; the 11
  not covered are field names (`legal_name`, `registered_address`...), a policy weight
  (`0.25`) and the document file name, all pre-existing shapes. No new redaction gap.

## 4. Critical contracts after the merge

| Contract | Evidence |
|---|---|
| Exact-line catalog | `guardrails.py` (and `briefing.py`, `context.py`, `guide.py`) identical to main; catalog/guardrail subset passes |
| Maker-checker / D-074 with single-reviewer off | `store.py`, `knowledge_api.py` = R3 blobs + comment IDs; `test_with_the_setting_off_the_two_person_rule_is_unchanged`, `test_an_rm_can_never_approve_and_the_author_never_decides`, `test_a_director_edit_is_a_new_version_another_director_must_approve` pass |
| Retirement takes two reviewers | `test_retiring_still_takes_two_reviewers_in_single_reviewer_mode` passes |
| Permission recheck inside the SQLite transaction | `test_authorize_runs_first_inside_the_write_lock_and_its_error_rolls_back` (7 cases), `test_a_caller_revoked_during_the_request_changes_nothing` (32 cases) pass |
| Director-only fix writing, HR refused | `test_only_a_director_handles_enhancement_requests` and the HR 403 in `test_knowledge_review_scope.py:229-232` pass (in the full and focused runs) |

## 5. Checks

**Rerun by me on tree `66a33d1`** (repo `.venv`, Python 3.12, macOS; `PYTHONDONTWRITEBYTECODE=1`).

| Check | Result |
|---|---|
| `cd apps/assistant && ../../.venv/bin/python -m pytest -p no:cacheprovider` | **1190 passed** in 30.05s (= R3) |
| Focused: `test_required_p2.py`, `test_knowledge_single_reviewer.py`, `test_knowledge_review.py`, `_recheck`, `_safety`, `_scope`, `test_knowledge_redaction.py` | 218 passed |
| Contract subset `-k "hr or recheck or revoked or lost or two_person or setting_off or maker or self or retir or allowed or guardrail or catalog"` | 734 passed, 456 deselected |
| Named contract tests (section 4), `-rA` | 44 passed (7 test functions incl. parametrized cases) |
| `ruff check ai_assistant tests --no-cache` | All checks passed! |
| `ruff format --check ai_assistant tests --no-cache` | 60 files already formatted |
| `mypy ai_assistant --cache-dir <scratchpad>` | Success: no issues found in 26 source files |
| `cd apps/frontend && npm run typecheck` | exit 0 |
| `npx vitest run` | 64 files, **1076 tests: 1075 passed, 1 failed** = `ViteHistoryFallback.test.ts` ("/src/styles.css: expected 'text/css' to contain 'text/javascript'"). The test, `vite.config.ts` and `styles.css` are unchanged since `ceefe1e`, where R3 showed it fails identically on main: macOS baseline, not the branch. |
| `npx tsc -b` then `npx vite build --outDir <scratchpad>/dist` | exit 0, built (chunk-size warning only) |
| `scripts/run_e2e.py --selectors-file <scratchpad>/r4/selectors.txt` (`e2e/assistant-streaming.e2e.ts:10`) `--results-json <scratchpad>/r4/e2e-r4-results.json` | 1/1 passed, `E2E SUITE PASS`, exit 0. Still the only E2E file referencing the assistant. |
| D-082 case-summary redaction probe | see section 3 |
| `python scripts/pre_pr_check.py` on clean HEAD `cb45d0c` (before this report existed) | **SUMMARY: PASS (0 unsafe conditions, 1 warning(s))**; the warning is the expected `apps/assistant/ai_assistant/config.py` |
| `check_project_state.py` / `check_architecture.py` / `check_secrets.py` | PASS / PASS / "Secret scan passed" |
| `git diff --check` for `7cd2bd9..cb45d0c`, `e8d0da0..cb45d0c`, `0b2c8dd..cb45d0c` | clean |
| `git status --short` after all checks | empty (before this report) |

The implementer's Stage 2 numbers (1190 pytest, ruff, 60 formatted, 26 mypy files,
1075/1076 vitest, typecheck and build 0, 1 E2E passed, checkers PASS) match my reruns on the
same tree.

**Not rerun by me:** the full backend pytest. The implementer's run on `7cd2bd9` was still in
progress (about 62%, no failure so far) when I finished; I did not start a second one. The
branch changes no `apps/backend` file, so no branch claim depends on it; it is main's evidence.
The full E2E suite stays a known gap (no local MongoDB), as stated in the PR.

**Reused:** R1/R2/R3 review of authorization, redaction, single-reviewer control, CAS,
migration and acceptance criteria, because none of that code changed.

CI is billing-blocked and has no `apps/assistant` job. All of the above is local evidence
and is not hosted CI.

## 6. Findings

**Required findings: none.**

**Informational notes I1-I10 (R1-R3):** unchanged; none became required. I9 (chronology after
renumbering) now applies to D-083 at `DECISION_LOG.md:711-713` (dated 2026-10-21, after
D-082). I10 (historical reports keep old IDs) now covers R3 as well: in the first gate report,
R1 and R2 the feedback decision is "D-076", in R3 it is "D-080"; both mean today's D-083.

**New informational note (no fix required):**

- **I11: PR #108 body still uses the old ID.** The local PR body draft
  (`scratchpad/pr-body-feedback.md`) says D-080 for the feedback decision, and the remote
  branch is still at `0b2c8dd`. When `cb45d0c` is pushed, the PR body should say D-083
  (renumbered from D-076, then D-080, per main's reservation at
  `SIM_LIM_D080_D082_PUBLICATION_READINESS.md:52`). I could not read the live PR (`gh` not
  installed).

## 7. Remaining preconditions for publication

1. **D-083 owner acceptance:** Shane must explicitly accept D-083 (single-reviewer mode, on by
   default, relaxing D-074's two-person control) before merge, whatever this verdict says.
   Main's D-083 reservation is not that acceptance.
2. **Unchanged content:** the reviewed content must stay tree `66a33d1` plus this report only.
   Any further change to code, tests or docs needs a fresh independent recheck.
3. **Explicit owner authorization** for committing this report, the push and the PR update; a
   repository-owner human merges.
4. **Pre-PR state:** rerun `pre_pr_check.py` on the final committed state including this
   report's commit; fetch latest `main` and reassess if it has moved (I did not fetch).
5. **PR body:** flag D-083 (renumbered) for Shane, list the 15 superseded tests, state that
   evidence is local, not hosted CI, and record the backend-pytest and full-E2E gaps.
6. **Residual risks carried from R1-R3:** no browser E2E for the feedback note, Review window
   or confirm step; redaction limited to case-supplied values and patterns; POLICY_APPROVE
   stays PROJECT_DEFINED_PROVISIONAL and Q-014 stays UNKNOWN_BLOCKED; the macOS-only
   `ViteHistoryFallback.test.ts` baseline failure.

## 8. What changed and Git status

- **Changed by the reviewed delta:** integration of main `7cd2bd9`; decision ID D-080 -> D-083
  in branch-owned docs, comments and docstrings; decision-log conflict resolved by appending.
- **Not changed:** branch behaviour, API and types, configuration surface (names and
  defaults), SQLite schema, business rules, auth and security, test assertions, provider
  status.
- **Git:** branch `feat/ai-assistant-feedback-requests` at HEAD `cb45d0c`. Nothing staged, no
  tracked modifications. The only untracked file is this report.
- **No other changes:** I made no implementation fix, commit, push, stash, reset, rebase,
  checkout, PR or merge, and started no other phase.

**Verdict: PASS**
