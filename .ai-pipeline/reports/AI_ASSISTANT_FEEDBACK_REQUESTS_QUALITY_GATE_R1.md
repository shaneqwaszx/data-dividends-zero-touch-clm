# AI Assistant feedback, enhancement requests and single-reviewer mode: independent Quality Gate R1

This report follows the `fyp-quality-gate` procedure and adapts its report template for a
bounded feature. I also applied the `persistence-schema-change` skill (to the SQLite v4
migration) and the `integration-security-review` skill (to authorization and redaction).

- **Change classes:** BACKEND_API, BACKEND_DOMAIN, FRONTEND_UI, AUTH_RBAC_SECURITY and
  PERSISTENCE. Persistence here means SQLite in `apps/assistant`, not Mongo.
- **Context:** I ran `python3 scripts/dev_context.py --change-class <CLASS>` once for each
  class, and all five runs exited 0.
- **Independence:** I did not write or remediate this change. During the review I wrote only
  this report, and I did not read `.env`.

## 1. Executive result

**Verdict: PASS WITH MINOR FIXES.**

- **Remediation of the first gate:** all five findings from the gate on `81a59c2` (F1–F5) are
  fixed, and I verified each one independently.
  - I ran the new F1 and F3 tests against the code at `81a59c2` and they fail there. One F1
    test fails on a behavioural assertion. The other fails on a missing key, and once I removed
    the link assertion it reproduces the original false `resolved` state. All of them pass at
    the reviewed candidate.
- **Fresh review:** I reviewed the whole delta again and found no defect in authorization,
  in-transaction rechecks, redaction, the single-reviewer control, false-success paths or the
  v3→v4 migration.
- **One required minor fix (R1-F1, Low, persistence robustness):**
  - The branch stamped schema "4" on three different shapes, at `6d090a7`, `81a59c2` and
    `f9d5e06`. A store opened by either of the first two commits never gains the later columns.
    The test meant to cover this case lowers the stamped version to 3, so it hides the problem.
  - The ignored local development store in this checkout is in the `6d090a7` shape (I checked
    only its schema, read-only). With the candidate code, the Review window's entry list and
    every decision would fail with `no such column`.
  - This is bounded and not a security, contract or false-success issue, because no such
    shape ever reached `main`. It still needs fixing before the owner runs the demo on that
    store.
- **Not an authorization:** this verdict does not authorize commit, push, PR or merge. D-076
  still needs the owner's (Shane's) explicit acceptance before merge, whatever the verdict.

## 2. Reviewed identity (frozen)

- **Repository:** `/Users/tasha/Documents/GitHub/data-dividends-zero-touch-clm`, branch
  `feat/ai-assistant-feedback-requests`.
- **Reviewed candidate:** `0ed9055a9efb80d8011f64248a24cd959b2cc7f7`, tree
  `014d674fa3bfd8c5b7c81e99de6b2678a83da462`.
- **Integrated `origin/main`:** `9e47b4fc000426d2609ba5310e0e9bb0b66fb5e4` (PR #101). The merge
  base equals `origin/main`; the branch is ahead 5 and behind 0. The original base was
  `5d9fd14`.
- **Branch history:**
  - `6d090a7` and `81a59c2`: the original implementation;
  - `f9d5e06`: remediation of the first gate;
  - `e8ec522`: merge of `origin/main`;
  - `0ed9055`: ARCHITECTURE.md fix, docs only.
- **Report-only commit during my review:** the coordinator committed the first gate's FAIL
  report on top, giving HEAD `51b7a2f91373d0c7a3f754458e67b4a5513d0094` (tree `819c9cf…`).
  - That commit is `0ed9055` plus exactly one file. `git diff 0ed9055 HEAD --name-only` lists
    only `.ai-pipeline/reports/AI_ASSISTANT_FEEDBACK_REQUESTS_QUALITY_GATE.md`.
  - That file is byte-identical to the scratchpad copy I was given (`cmp`).
  - The reviewed code, tests and docs did not change.
- **Reviewed delta:** `git diff origin/main...0ed9055`, which touches 23 files. I reviewed all
  of them:
  - **Assistant source:** `.env.example`, `README.md`, `config.py`, `knowledge/drafting.py`,
    `knowledge/service.py`, `knowledge/store.py`, `knowledge_api.py` and `main.py`.
  - **Assistant tests:** `test_knowledge_redaction.py`, `test_knowledge_review.py`,
    `test_knowledge_review_recheck.py`, `test_knowledge_review_safety.py`,
    `test_knowledge_review_scope.py` and the new `test_knowledge_single_reviewer.py`.
  - **Frontend:** `aiAssistant.ts`, `AiAssistantPanel.{css,tsx,test.tsx}` and
    `KnowledgeReview.{tsx,test.tsx}`.
  - **Docs:** `docs/ARCHITECTURE.md`, `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md`
    and `docs/decisions/DECISION_LOG.md`.
- **Working tree:** `git status --short` was clean at the start and at the end, apart from
  this report.
- **Scratch work:** probes, and extracts of `81a59c2`, `6d090a7` and `origin/main`, are only
  under the session scratchpad.

## 3. Prior gate history and remediation verification

The first gate ran on `81a59c2` and returned **FAIL**, with F1 (Medium) and F2–F5 (Low). Its
report is now committed at `.ai-pipeline/reports/AI_ASSISTANT_FEEDBACK_REQUESTS_QUALITY_GATE.md`.

| Prior finding | Remediation in `f9d5e06` | Verified | Evidence |
|---|---|---|---|
| F1: request linked by entry id only | `feedback.entry_version` | **Fixed** | See below. |
| F2: ARCHITECTURE.md CRLF rewritten | Original bytes restored; only the knowledge-loop paragraph changes | **Fixed** | See below. |
| F3: newest version used for scope and visibility | `current()` used | **Fixed** | See below. |
| F4: docs overstate the Review window; confirm text ignores the mode | Window loads `/knowledge/me`; sentence only in single-reviewer mode; docs narrowed | **Fixed** | See below. |
| F5: past-case fix accepts and drops `fields`/`stages` | Both refused | **Fixed** | See below. |

**F1 (request linked to its fix by entry id only)**

- **Code:**
  - `store.py:888-893`: `draft_request` sets `entry_id` and `entry_version` together.
  - `store.py:594-599` (reject) and `store.py:613-617` (approve): the status change matches
    `entry_id`, `entry_version`, `status='drafted'` and `helpful=0`.
  - `store.py:802-807`: `revise_pending` moves the link to the edited version in the same
    transaction.
- **Tests:**
  - `test_two_requests_fixed_in_the_same_guidance_are_resolved_by_their_own_versions` covers
    scenario A.
  - `test_a_decision_on_another_version_of_the_guidance_leaves_the_request_alone` covers
    scenario B: HR versions are approved and rejected, and the link is carried through an edit.
- **Against `81a59c2`:** I ran HEAD's test file against the old code in the scratchpad.
  - The first test fails on `KeyError: 'entry_version'`.
  - With the link assertion removed, it fails with
    `{1: 'resolved', 2: 'resolved'} != {1: 'resolved', 2: 'drafted'}`, the original defect.
  - The second test fails with `{1: 'open'} != {1: 'drafted'}`.
- **At HEAD:** both pass.

**F2 (ARCHITECTURE.md line endings)**

- `git diff --stat` reports +13/−3, all in one paragraph near line 971.
- Every changed line ends in CRLF.
- The CRLF line count went from 978 on `main` to 988 at HEAD, matching the 10 net added lines.

**F3 (scope and visibility from the newest version)**

- **Code:** `knowledge_api.py:594` uses `current(target) or get(target)` for scope, and `build`
  takes inherited visibility from `current(target)`.
- **Test:** `test_a_guidance_fix_takes_scope_and_visibility_from_the_current_approved_version`
  covers both a 404 for out-of-scope current guidance and the inherited TEAM_B visibility.
- **Against `81a59c2`:** it fails with `assert 200 == 404`.

**F4 (Review-window claims and confirm text)**

- **UI:**
  - `KnowledgeReview.tsx:357` shows the sentence only when `singleReviewer` is on.
  - `KnowledgeReview.tsx:481-501` lists "Published by a single reviewer" (currently published
    entries only) and says so in a comment.
- **Docs:** `DECISION_LOG.md` D-076, ADR-012 and `README.md` now say "lists the entries
  currently published that way". The ADR adds that "a replaced or retired one, or a rejection,
  is only in the entry's history".
- **Test:** the vitest "says nothing about single-reviewer decisions when the mode is off".

**F5 (`fields` and `stages` on a past-case fix)**

- **Code:** `knowledge_api.py` `FixRequest._fits_its_kind` includes `fields` and `stages` in
  the resolution refusal.
- **Test:** `test_a_fix_must_fit_its_kind` gained both cases (422).

**The other remediation claim: "a store rebuilt before the column existed gains it"**

This claim is **only partly true**; see R1-F1.

## 4. Checks (exact results)

I ran the backend and governance checks on the reviewed content, using the repo `.venv`
(Python 3.12) and the repo's Node `node_modules`, on macOS. HEAD was `0ed9055`, or `51b7a2f`
after the report-only commit; their code is identical.

**Rerun by me in this session**

| Check | Result |
|---|---|
| `apps/assistant`: `../../.venv/bin/python -m pytest -p no:cacheprovider` | **1188 passed** in 31.13s |
| `ruff check ai_assistant tests --no-cache` | All checks passed! |
| `ruff format --check ai_assistant tests --no-cache` | 60 files already formatted |
| `mypy ai_assistant` | Success: no issues found in 26 source files |
| `apps/frontend`: `npx vitest run src/pages/KnowledgeReview.test.tsx src/pages/AiAssistantPanel.test.tsx` | 2 files, **29 passed** |
| `npm run typecheck` (`tsc -b`) | exit 0; status stayed clean |
| `python3 scripts/check_architecture.py` | ARCHITECTURE CHECK: PASS |
| `python3 scripts/check_project_state.py` | PROJECT STATE CHECK: PASS |
| `python3 scripts/pre_pr_check.py` (at `51b7a2f`) | **SUMMARY: PASS (0 unsafe conditions, 1 warning(s))**. The warning is "API/config/shared type files changed: apps/assistant/ai_assistant/config.py" (the new setting; expected). |
| `git diff --check origin/main...0ed9055` | clean |
| Report whitespace (`grep -n ' $'` on this report) | none |

**Reviewer probes, all in the scratchpad**

| Probe | Result |
|---|---|
| HEAD's `test_knowledge_review.py` against `81a59c2` code | The 4 new tests fail as described in section 3. |
| `81a59c2`-shaped store opened by HEAD code | Stays at `schema_version` 4, and `feedback` has no `entry_version`. |
| `6d090a7`-shaped store opened by HEAD code | `reviews()` and `single_reviewer_approvals()` raise `OperationalError: no such column: single_reviewer`. |
| Local ignored store `apps/assistant/data/knowledge/knowledge.sqlite3` (opened read-only, schema and meta only, no rows read) | `schema_version` 4; `feedback` has `close_reason` but no `entry_version`; `reviews` has no `single_reviewer`. This is the `6d090a7` shape. |

**Reused from Stage 2, run on `e8ec522`**

I reused these because the only change between `e8ec522` and `0ed9055` is
`docs/ARCHITECTURE.md` (verified with `git diff e8ec522 0ed9055 --name-only`).

| Check | Result |
|---|---|
| `npm test` | 1013 tests: 1012 passed, 1 failed. The failure is `ViteHistoryFallback.test.ts` ("/src/styles.css: expected 'text/css' to contain 'text/javascript'"). |
| `npm run build` | ok |
| `python3 scripts/run_e2e.py --backend-port 18765 --frontend-port 14173 --grep "PR89 streaming"` | 1 passed |

- **Baseline frontend failure:** the first gate showed that the `ViteHistoryFallback.test.ts`
  failure also happens on an unmodified `origin/main` export. The diff touches no Vite
  configuration and no file in that test's path. I classify it as a pre-existing baseline
  failure, not a defect of this change.
- **E2E gap:** no E2E opens the Knowledge review window or the confirm step, and the streaming
  E2E does not exercise feedback.
  - Each layer has direct evidence: vitest covers the DOM, request bodies, the confirm step,
    mode gating and disabled states, and the backend API tests run over the real ASGI app with
    the real role profiles.
  - I judge the gap a residual risk, not a blocker. A browser run of RM note → Director fix →
    confirm → publish would still be worth adding, because single-reviewer publishing is the
    relaxed control.

## 5. Findings

### R1-F1 — Low (persistence robustness; required minor fix): earlier branch-only "v4" stores never gain the later v4 columns

- **Where:**
  - `apps/assistant/ai_assistant/knowledge/store.py:333` runs `_migrate_to_4` only when the
    stamped version is `< 4`.
  - The column-presence repairs in `_migrate_to_4` (`store.py:966-990`, including the
    `entry_version` add at `:983-987`) are therefore never reached for a store already stamped
    4.
  - The test `apps/assistant/tests/test_knowledge_review.py:943-957` forces `schema_version` to
    `'3'` (`:951`) before reopening. That models a crash mid-migration, not a store written by
    the earlier branch commits, which stamp `'4'`.
- **Scenario:** `6d090a7` stamped v4 with only `close_reason`, and `81a59c2` added
  `reviews.single_reviewer`. A developer who ran either commit, which this checkout's own
  ignored store shows happened, then runs the candidate.
  - **On the `6d090a7` shape:**
    - `GET /assistant/knowledge/entries` fails with `no such column: single_reviewer` (via
      `single_reviewer_approvals`, `store.py:470`). The Review window loads that endpoint in
      its `Promise.all`, so the whole window fails.
    - `GET /entries/{id}` and every decision fail the same way, as a 500.
  - **On the `81a59c2` shape:** writing a fix and every approve or reject fail on
    `entry_version`.
  - The remediation's statement "a store rebuilt before the column existed gains it" is
    therefore true only when the stamp is below 4.
- **Why only Low:** no such shape ever reached `main`. Upgrades from `main`'s v3 are clean and
  tested, the failure is loud (500) rather than a false success, and no data is lost.
- **Required fix (bounded):**
  - Make the idempotent column-presence steps run whenever the stamped version is `<= 4`, or
    on every open, so that:
    - `reviews.single_reviewer` is added if missing;
    - `feedback.entry_version` is added if `close_reason` exists without it.
  - Change the test to keep the stamp at `'4'` and also drop `reviews.single_reviewer`.
  - Alternative: the owner records that local stores from the unmerged branch commits must be
    deleted. A code fix is preferred, because the demo store is already in that shape.

### Informational (no fix required)

- **I1:** `docs/ARCHITECTURE.md:958-960` still heads the section "AI Assistant knowledge loop
  candidate — 2026-10-21 (proposed; …)" and opens with "PR #99 proposes …".
  - Line 983 now correctly says PR #99 is merged. The specific stale sentence the assignment
    named was fixed.
  - The surrounding wording reads as a proposal, which a later docs refresh could tidy.
- **I2 (carried from the first gate):** for `kind=guidance`, the `INVALID_ENTRY_ID` 422
  (`knowledge_api.py:579-587`) is computed before `require(profile, APPROVE)` (`:598`).
  - An RM or HR caller can therefore get 422 instead of 403 for a badly slugged title.
  - Nothing exists to leak, so there is no existence leak.
- **I3 (carried):** "Yes, helpful" rows are stored with `status='open'`. Every current reader
  of enhancement requests filters on `helpful=0`, and the store's own status changes filter on
  `helpful = 0`.
- **I4:** a guidance fix takes visibility from the current approved version, but not its
  `illustrative` flag or `replaces`. A new version of an illustrative entry would therefore be
  non-illustrative. Real guidance files are not illustrative, and the HR route behaves the same.
- **I5:** the Review window lists the **currently published** single-reviewer entries.
  - A self-approval later replaced or retired, and every self-rejection, is recorded
    (`reviews.single_reviewer`) and returned by `GET /entries/{id}`, but not rendered in the
    window.
  - The docs now say exactly this, so nothing is overstated.
  - A strict reading of criterion 5's "every self-approved decision … shown in the Review
    window" would want a history list. That is an owner choice, not a defect.

## 6. Acceptance-criteria matrix

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | "Yes, helpful": confidence only; stored with blocker codes, fields and stages; no draft, no queue, no retrieval or ranking change | PASS | The feedback route stores `entry_id=None` and no longer calls `propose`. `reviews` lists `gaps` with `helpful=False`. The diff does not touch retrieval or ranking modules. Test: `test_yes_helpful_only_records_the_rating_with_its_case_context`. |
| 2 | "Not helpful" needs a note: 422 on empty or whitespace; button disabled until text; label without "(optional)"; exact hint; note redacted before it is stored | PASS | `FeedbackRequest` validator; `test_not_helpful_needs_a_note[...]`. In `AiAssistantPanel.tsx`: `required`, `disabled={… \|\| !state.note.trim()}`, the label "What was missing?" and the exact hint "Your note goes to a Director. Client names, UENs and addresses are removed first." `Redactor(...).redact(body.note.strip())` runs before `add_feedback`. Redaction tests pass. |
| 3 | Stats: confidence by topic alongside totals; a row with no code counts only in the totals | PASS | `by_topic` deduplicates codes per row; `test_stats_show_confidence_by_topic`. The UI list is labelled "Confidence by topic". |
| 4 | Directors handle requests end to end; HR does not draft; fix as past case or guidance, published by the Director; close with a required reason (v4 nullable column, v3 migration test); in-transaction recheck for both; approve resolves, reject reopens; only open requests; past case visible to the request's team or NO_TEAM | **PASS** (with R1-F1 Low on branch-only stores) | The window heading is "Enhancement requests". `draft_request` and `close_feedback` use `_write(authorize)`, so `authorize` runs right after BEGIN IMMEDIATE (the `STORE_CALLS` recheck test and the revoked/team-move matrices include `draft-from-gap`). `_open_request` gives 409 when a request is not open, and the race test has one winner. Version-exact resolve and reopen hold (F1 verified). `resolution_from_request` uses `request.team or NO_TEAM`. HR gets 403. The v3 test `test_a_version_3_store_gains_request_statuses_and_close_reasons` checks rows kept, the new columns null and the CHECK constraint. |
| 5 | `AI_ASSISTANT_KNOWLEDGE_SINGLE_REVIEWER`, default true; author approval only when true; false keeps the two-person rule; both modes tested; checks and redaction stay; final text plus confirm; every self-decision recorded and shown; retirement still needs two people | PASS (I5 noted) | `config.py` defaults the setting to true, and `main.py` passes it from config only. In `decide`: `own and not single_reviewer` gives MAKER_CHECKER; `own and approve and not confirmed` gives `CONFIRM_SINGLE_REVIEWER` before any write; `single_reviewer=int(own)`. `request_retirement` is unchanged. `test_knowledge_single_reviewer.py` covers on and off, the editor case, a second reviewer never marked, self-reject and retirement. The confirm section shows title, body, follow-ups and audience. The diff does not touch the grounding, output or catalog modules. |
| 6 | D-076 and ADR-012 state the relaxation, why, and Shane's acceptance before merge; ARCHITECTURE and PROJECT_STATE changed only where they describe the flow; CRLF kept; stale PR #99 sentence fixed | PASS (I1 noted) | D-076, ADR-012 (status and section A) and ARCHITECTURE all state it. CRLF verified (section 3, F2). PROJECT_STATE is untouched and has no description of this flow; `check_project_state` passes. |
| 7 | Real roles: maya-lim "Not helpful"; olivia-koh writes and publishes; request resolved; hr-admin cannot draft | PASS | `test_knowledge_review_scope.py:216` uses `rm-session` (maya-lim, TEAM_A), `hr-global-session` (hr-admin, HR, no team) and `director-global-session` (olivia-koh, DIRECTOR, no team, CASE_GLOBAL). These match `access.py:171,195` and `admin_repository.py:291`. In the test HR gets 403, publishing without confirm is refused, with confirm it succeeds, the request is `resolved` by olivia-koh, and the next chat cites it. |
| R | Output catalog and every existing check untouched; no other safety control weakened; no invented business rules | PASS | No catalog, grounding or guardrail file is in the diff. Maker-checker, hash binding, team scope, retirement and redaction are unchanged or extended. The relaxation is behind the setting and recorded as PROPOSED with POLICY_APPROVE PROJECT_DEFINED_PROVISIONAL and Q-014 UNKNOWN_BLOCKED. |

## 7. Interpretive choices (re-judged independently)

| Choice | Assessment |
|---|---|
| Self-reject allowed in single-reviewer mode, recorded as single-reviewer, no confirmation | **Justified.** A reject publishes nothing, and without it the only Director could not discard their own wrong fix. It is recorded and documented, and it falls under D-076's owner acceptance. |
| The fix is redacted against the request's case, loaded with the Director's own session | **Justified and fail-closed.** The case load is outside the lock, but the in-lock recheck re-validates identity, capability and request scope (`locked == [False, True]`). A case the Director cannot load stops the change. |
| Guidance written from a request is redacted too | **Justified.** It is written from a client's case. The Director sees the redacted result before publishing. |
| A guidance change keeps the current approved version's visibility unless one is given | **Justified, now implemented as documented** (F3). With no approved version, the default is everyone. |
| Frontend sends `confirm_single_reviewer=true` after its confirm step | **Justified.** Every approval in the UI follows the confirm section, rejects send `false`, and the server ignores the flag for non-authors (tested). |
| `turns` and `draft_entry_id` removed from the feedback API | **Justified.** The conversation is no longer used. An old client's `turns` gets a 422 (tested), and no other consumer references `draft_entry_id`. |

## 8. Code, architecture and security review

- **Ownership:** the assistant's SQLite store remains the single persistence owner. No CLM
  backend write, route-to-Mongo access, frontend authorization or second authorization owner
  is added. The assistant stays GET-only towards the CLM backend.
- **Authorization:**
  - `draft` and `close` call `require(APPROVE)` and the scoped `reach` before work, then again
    in the write transaction.
  - An out-of-team, missing or helpful-rating id all get the same 404 "No such enhancement
    request.", so there is no existence leak.
  - Guidance targets are scope-checked against the current approved version.
- **Single-reviewer control:**
  - The flag reaches `decide` only from server config.
  - `own` covers authors and editors through `_chain_authors`.
  - No path approves an author's own entry without `confirmed`.
  - With the setting false, behaviour is byte-for-byte the old two-person rule.
- **CAS and terminal states:**
  - The request status moves only from `open` (draft or close) and from `drafted` on its exact
    version (approve or reject).
  - Entry status still moves only from `pending_review`, through `_set_status`.
  - The request update shares the entry decision's transaction.
- **Migration from `main`:** v3→v4 is one explicit transaction and idempotent by column
  checks. Rollback to v3 code is documented and matches the code (the `INSERT` column lists
  are explicit). The gap is R1-F1, which concerns branch-only shapes.
- **Redaction and browser errors:**
  - RM notes are redacted before storage.
  - A Director's fix is redacted against the case and the identifier patterns.
  - The three new fixed messages are in `SAFE_ERROR_MESSAGES`, and everything else falls back
    to a generic message.
- **Secrets:** nothing secret, credential or PII is newly tracked. `.env.example` only gains
  the setting.

## 9. Superseded and changed tests

- **Changes since the first gate:**
  - `f9d5e06` only adds tests: three in `test_knowledge_review.py` and two refusal cases in
    `test_a_fix_must_fit_its_kind`. It also extends the v3 migration assertion to the new
    `entry_version` column.
  - `e8ec522` and `0ed9055` change no tests.
- **Earlier changes (`6d090a7`, `81a59c2`), checked independently:**
  - Tests asserting "Solved it" or helpful creates a draft were replaced. This is legitimate,
    because the requirement supersedes them.
  - Their safety properties moved to the RM note and the Director's fix:
    - officer, party and address-part redaction;
    - the "forged assistant turns" protection, now a 422 for any `turns`;
    - a new pattern-redaction test.
  - The helper `solved` became `drafted`, written by a Director. The maker-checker tests that
    use it run with `knowledge_single_reviewer=False` (pinned explicitly in the recheck suite,
    and the default of the test client), so they still assert MAKER_CHECKER.
  - In the recheck matrices, `close-gap` now sends a reason and `draft-from-gap` was added.
    The changed `me_calls` and `locked` expectations are explained by the case load and still
    prove the refusal comes from inside the write.
- **Conclusion:** no test was weakened.

## 10. Required fixes

1. **R1-F1 (Low):** make the v4 column repairs apply to stores already stamped 4
   (`reviews.single_reviewer`, `feedback.entry_version`), and test that case with the stamp
   left at `'4'`. Alternatively, the owner records that branch-era local stores must be
   deleted.

These are not required: I1–I5 and the pre-existing `ViteHistoryFallback.test.ts` failure.
Because the reviewed content will change, the fix needs a focused independent recheck of the
changed delta. Evidence for unchanged paths can be reused.

## 11. Residual risks and later dependencies

- **D-076 is not accepted.** Single-reviewer mode defaults to **on** and relaxes D-074's
  two-person control. The owner (Shane) must explicitly accept D-076 before merge.
- **Redaction limits:** redaction knows only case-supplied values and the listed patterns. A
  client name or address that is not in the case data is not removed, although the hint the
  assignment mandated says names, UENs and addresses are removed. The Director's final-text
  confirmation is the remaining control.
- **No browser E2E** covers the feedback note, the Knowledge review window or the confirm step.
- **Review authority:** POLICY_APPROVE stays PROJECT_DEFINED_PROVISIONAL and Q-014 review
  authority stays UNKNOWN_BLOCKED. No Live, sponsor or provider claim is made or affected.

## 12. Readiness and Git status

- **Readiness:** not ready for publication until R1-F1 is fixed and rechecked, and the owner
  explicitly accepts D-076. This change does not touch any ACRA or GoldTier path, provider
  status or CLM backend write.
- **What changed (as AGENTS.md asks):**
  - API, types, schema (SQLite v4), business rules (D-076, proposed), auth and security
    (single-reviewer relaxation behind a setting), configuration (the new setting) and runtime
    behaviour of the assistant knowledge loop all changed.
  - Connectors, mappings, architecture ownership and provider status did not change.
- **Git:** branch `feat/ai-assistant-feedback-requests`, HEAD `51b7a2f`, which is `0ed9055`
  plus the first gate's report. Nothing is staged and there are no tracked modifications. The
  only untracked file is this report.
- **No other changes:** no implementation fix, commit, push, stash, reset, PR or merge was
  made, and no other phase was started.

**Verdict: PASS WITH MINOR FIXES**
