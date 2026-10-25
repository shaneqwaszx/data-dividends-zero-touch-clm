# AI Assistant feedback, enhancement requests and single-reviewer mode: independent Quality Gate

Procedure: `fyp-quality-gate`, adapted from its report template for a bounded feature. The
`persistence-schema-change` and `integration-security-review` skills were applied for the
SQLite v4 migration and the auth/redaction surface. Change classes: BACKEND_API,
BACKEND_DOMAIN, FRONTEND_UI, AUTH_RBAC_SECURITY, PERSISTENCE (SQLite in `apps/assistant`, not
Mongo). `scripts/dev_context.py --change-class <CLASS>` was run once for each class (all exit 0).
I did not write this change. During the review I changed nothing except this report. `.env`
was not read.

## 1. Outcome

**Verdict: FAIL.**

Most of the work is sound. The single-reviewer decision path, the in-transaction rechecks,
team scope and 404s, redaction, the v4 migration, the panel and the confirm step all hold up,
and every check I ran passes except one test that also fails on `origin/main`.

The gate still fails on one Medium defect (F1). An enhancement request is linked to an entry
**id**, not to the version that holds its fix. When a request's fix is a guidance change, any
other pending version of the same guidance entry can change the request's status. Approving an
unrelated version marks the request `resolved` while its own fix is still pending. A request
whose fix is later rejected then stays `resolved` and never returns to the queue. That is a
false-success state, and it breaks acceptance criterion 4 for guidance fixes. The skill does
not allow PASS WITH MINOR FIXES for a false-success correction.

The fix is bounded. F2 to F5 are Low. This verdict does not authorize commit, push, PR or merge.
D-076 also still needs the owner's (Shane's) explicit acceptance before merge, whatever the
verdict.

## 2. Reviewed identity (frozen)

- Repository: `/Users/tasha/Documents/GitHub/data-dividends-zero-touch-clm`, branch
  `feat/ai-assistant-feedback-requests`.
- HEAD `81a59c211eb3a0855a469db89a8950703fdfcb63`, tree `69136d14dda3104b3e16311dba8b06ee262f7eb4`.
- Base and `origin/main`: `5d9fd145bb7b77f03f2398fd09e728912f3c071c`. Ahead 2 (`6d090a7`,
  `81a59c2`), behind 0.
- `git status --short` was clean at the start and at the end, apart from this report.
- Reviewed diff: `git diff 5d9fd14...81a59c2`. **It touches 23 files, not the 20 the brief
  states.** 20 is the file count of `81a59c2` alone; `6d090a7` touches 17. All 23 were
  reviewed:
  - Assistant source: `.env.example`, `README.md`, `config.py`, `knowledge/drafting.py`,
    `knowledge/service.py`, `knowledge/store.py`, `knowledge_api.py` and `main.py`.
  - Assistant tests: `test_knowledge_redaction.py`, `test_knowledge_review.py`, `_recheck.py`,
    `_safety.py` and `_scope.py`, plus the new `test_knowledge_single_reviewer.py`.
  - Frontend: `aiAssistant.ts`, `AiAssistantPanel.{css,tsx,test.tsx}` and
    `KnowledgeReview.{tsx,test.tsx}`.
  - Docs: `docs/ARCHITECTURE.md`, `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md` and
    `docs/decisions/DECISION_LOG.md`.
- I used only scratch files under the session scratchpad: probes, a temporary SQLite store and
  an `origin/main` frontend extract. None of them is in the repository.

## 3. Checks (exact results, this session, this HEAD)

| Check | Result |
|---|---|
| `apps/assistant`: `../../.venv/bin/python -m pytest -q -p no:cacheprovider` | **1184 passed** in 20.71s |
| `ruff check ai_assistant tests` | All checks passed! |
| `ruff format --check ai_assistant tests` | 60 files already formatted |
| `mypy ai_assistant` | Success: no issues found in 26 source files |
| `apps/frontend`: `npx vitest run src/pages/KnowledgeReview.test.tsx src/pages/AiAssistantPanel.test.tsx` | 2 files, **28 passed** (14 + 14) |
| `npm test` | 60 files: 59 passed, 1 failed. 1013 tests: **1012 passed, 1 failed**. The failure is `ViteHistoryFallback.test.ts`: "/src/styles.css: expected 'text/css' to contain 'text/javascript'" |
| Same test on unmodified `origin/main` (`git archive origin/main apps/frontend` into the scratchpad, with `node_modules` symlinked) | **Fails identically** (1 failed, same assertion). It predates the branch and is unrelated to the diff, which touches no Vite configuration. I classify it as a pre-existing baseline failure, not a defect of this change. |
| `npm run typecheck` (`tsc -b`) | exit 0 |
| `npm run build` | built in 1.30s (only the usual chunk-size warning). `dist` is ignored and status stayed clean. |
| `python3 scripts/run_e2e.py --backend-port 18765 --frontend-port 14173 --grep "PR89 streaming"` | 1 passed. "E2E PASS: guarded authenticated local Mock browser suite completed." rc 0 |
| `python3 scripts/pre_pr_check.py` | **SUMMARY: PASS (0 unsafe conditions, 1 warning(s))**. The warning is that `config.py` changed. |
| `git diff --check 5d9fd14 81a59c2` | clean (rc 0) |
| Reviewer probes: store-level scripts against a temporary SQLite file | These reproduce F1. They also confirm that code from before v4 opens a v4 store, resets `schema_version` to 3, and that v4 code reopens it cleanly. |

**E2E gap.** The streaming E2E does not exercise feedback; `assistant-streaming.e2e.ts` has no
feedback or review steps. No E2E opens the Knowledge review window. The panel and review
behaviour is covered by vitest (DOM, request bodies, disabled states, focus trap) and by the
backend API tests over a real ASGI app. Directors can now publish entries alone, so a browser
run of RM note → Director fix → confirm → publish would be valuable. It is a residual risk, not
a blocker, because each layer has direct evidence.

## 4. Findings

### F1 — Medium (false success; acceptance criterion 4): a request's status follows any version of its linked entry id

- **Where:**
  - `apps/assistant/ai_assistant/knowledge/store.py:882` links the request by `entry_id` only.
  - `store.py:593-597` (reject reopens) and `store.py:610-614` (approve resolves) match
    `WHERE entry_id = ? AND status = 'drafted'`, whatever version is being decided.
  - Fixes reach this path through `knowledge_api.py:566-648`, the guidance branch of `draft`.
- **Scenario A (two requests fixed by one guidance entry, reachable through the API):**
  1. Two RMs report the same gap.
  2. Olivia picks the same "Guidance to change" for both, which creates `guidance.x` v2 for R1
     and v3 for R2.
  3. Approving v2 marks **R1 and R2** `resolved`, while R2's fix (v3) is still pending.
  4. Rejecting v3 changes nothing, because R2 is no longer `drafted`. R2 stays `resolved` with
     a rejected fix and never reappears under Enhancement requests.

  Reviewer probe output:
  `after rejecting R2's fix: [(1,'resolved'),(2,'resolved')] v2: rejected`.
- **Scenario B (an HR proposal on the same guidance):**
  - Approving HR's unrelated pending version resolves the request; the probe prints
    `[(1,'resolved'),(2,'resolved')]` while the Director's fix is still `pending_review`.
  - Rejecting HR's version reopens a request whose fix is still pending, so a second fix can
    be drafted for it. The probe printed `second draft accepted: 4`.
- **Why it matters:** criterion 4 says approving *the linked entry* resolves the request and
  rejecting *it* reopens it. Here the status follows unrelated decisions, so the user-visible
  status is false. Past-resolution fixes are not affected, because each gets a fresh random id.
- **Required fix:**
  - Link a request to the exact version holding its fix, for example by storing the version or
    key next to `entry_id`.
  - On a reviewer edit (`revise_pending`), carry the link forward along the `revises` chain.
  - Resolve or reopen only the request(s) whose linked version is the one being decided.
  - Alternatively, refuse to draft a fix onto an entry that already has a pending version, but
    the link still has to be version-exact.
  - Add tests for both scenarios: two requests on one guidance, and an HR pending version.

### F2 — Low (scope/hygiene; criterion 6): `docs/ARCHITECTURE.md` line endings rewritten across the whole file

- **Where:** `docs/ARCHITECTURE.md`, the whole file. The diff shows 987 added and 978 removed
  lines. With `--ignore-cr-at-eol` it is +10/−1 at around line 974.
- **Cause:** the base file had mixed CRLF/LF endings, and the branch converted all of it to LF.
- **Scenario:** the actual change is lost in a 1,965-line diff. Any concurrent ARCHITECTURE
  edit will conflict. This breaks "ARCHITECTURE.md … updated only where they describe this
  flow" and AGENTS.md's ban on unrelated formatting churn.
- **Required fix:** restore the base bytes and re-apply only the 10-line paragraph.

### F3 — Low (guidance-fix scope and visibility read the latest version, not the current one)

- **Where:** `knowledge_api.py:587` (`existing = kb.store.get(target)`, used for `found` scope)
  and `knowledge_api.py:617` (`current = kb.store.get(target)`, used for inherited visibility).
  `KnowledgeStore.get` with no version returns the highest version
  (`ORDER BY version DESC LIMIT 1`), whether it is pending, rejected or retired.
- **Scenario:** HR's rejected v3 of `guidance.x` narrowed or widened its visibility. A Director's
  fix then inherits v3's visibility instead of the approved version's, and scope is checked
  against v3. ADR-012 and D-076 say "keeps the current version's visibility".
- **Required fix:** use `kb.store.current(target)`, falling back to the latest version only when
  nothing is approved. Alternatively, make the docs say "latest version". Add a test.

### F4 — Low (truthful UI and docs): the Review window lists only currently approved single-reviewer entries, and the confirm text ignores the mode

- **Where:** `apps/frontend/src/pages/KnowledgeReview.tsx:476-497` and `:351`. The docs claim
  "every such decision is … listed in the Review window": `DECISION_LOG.md:382`,
  `ADR-012…md:74` and `apps/assistant/README.md:110`.
- **Scenario:**
  - A self-approved entry that is later replaced or retired drops out of "Published by a single
    reviewer".
  - A self-*reject*, recorded with `single_reviewer=1` by `store.py:588`, is never shown.
  - The history is still stored and returned by `GET /entries/{id}`, so the record is complete,
    but the Review window does not show "each" decision.
  - The confirm box always says "If you wrote or edited it, publishing is recorded as a
    single-reviewer decision", even when `single_reviewer` is false and the author would get
    `MAKER_CHECKER`.
- **Required fix:** either list single-reviewer decisions from the review history, or narrow
  the docs to "approved entries currently published by a single reviewer". Show the
  single-reviewer sentence only when `/knowledge/me` reports `single_reviewer: true`.

### F5 — Low: a past-resolution fix silently ignores `fields` and `stages`

- **Where:** `knowledge_api.py:138-141`. The validator rejects `entry_id`, `source_ref`,
  `visibility` and `blocker_codes` for `kind="resolution"`, but not `fields` or `stages`, which
  `resolution_from_request` then discards.
- **Scenario:** an API caller sends `fields` with a resolution, gets 200, and the values are
  dropped. The UI never sends them.
- **Required fix:** add `self.fields is not None or self.stages is not None` to the resolution
  refusal, and test it.

### Informational (no fix required)

- **I1:** "Yes, helpful" rows are stored with `status='open'` (`store.py:844`, since `entry_id`
  is now always `None`). Every reader filters on `helpful=0` (queue, `_open_request`,
  `open_gaps`), so nothing misbehaves today. A future caller of `feedback(status="open")`
  without `helpful=False` would see ratings as open.
- **I2:** for `kind=guidance`, the `INVALID_ENTRY_ID` 422 (`knowledge_api.py:575-584`) is
  computed before `require(profile, APPROVE)`. An RM or HR caller can therefore get 422 instead
  of 403 for a title that slugs badly. Nothing exists to leak, so there is no existence leak,
  but the order differs from the other routes.

## 5. Acceptance-criteria matrix

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | "Yes, helpful" records the rating with blocker codes, fields and stages; no draft, no queue entry, no retrieval or ranking change | PASS | `knowledge_api.py` feedback route: `entry_id=None`, no `propose`. Retrieval code is untouched by the diff. Covered by `test_yes_helpful_only_records_the_rating_with_its_case_context`. |
| 2 | "Not helpful" needs a note (422 on empty or whitespace); Send disabled; label without "(optional)"; exact hint; note redacted before it is stored | PASS | `FeedbackRequest` validator; `test_not_helpful_needs_a_note[empty/spaces/whitespace]`; the redaction test. In `AiAssistantPanel.tsx`, `required`, the button disabled until `note.trim()`, and the exact hint string; `AiAssistantPanel.test.tsx:429-449`. |
| 3 | Stats show confidence by topic; a row with no code counts only in the totals | PASS | `by_topic` deduplicates codes per row; `test_stats_show_confidence_by_topic`. UI list labelled "Confidence by topic". |
| 4 | Directors handle requests end to end; HR cannot; fix as past case or guidance; close with required reason (v4 nullable column, v3 migration test); in-transaction recheck for both; approve resolves and reject reopens; only open requests; past case visible to the request's team or NO_TEAM | **FAIL (F1)**; everything else PASS | Recheck: `draft_request` and `close_feedback` use `_write(authorize)`. `test_a_caller_revoked_during_the_request_changes_nothing[draft-from-gap]` and the team-move variants pass. The `STORE_CALLS` entry for `draft_request` proves `authorize` runs after BEGIN IMMEDIATE and before any read. Open-only: `_open_request` raises 409 CHANGED; the race test has exactly one winner. Team and NO_TEAM: `resolution_from_request`; `test_a_global_director_drafts_a_team_b_request_visible_to_team_b_only`; NO_TEAM redaction test. HR gets 403. **Resolve and reopen are wrong for guidance fixes (F1).** |
| 5 | `AI_ASSISTANT_KNOWLEDGE_SINGLE_REVIEWER` (default true); author approval only with confirm, recorded single-reviewer; off means the two-person rule is unchanged; both modes tested; sentence checks and redaction kept; final text plus confirm in the UI; recorded in history and shown; retirement still needs two people | PASS (with F4 Low) | `decide`: a non-author is never marked (`int(own)`); an author approval without `confirmed` raises `ConfirmationRequiredError` before any write; an author with the setting off gets MAKER_CHECKER even with `confirm=true`. `request_retirement` is unchanged. Tests are in `test_knowledge_single_reviewer.py`, both modes. Output catalog and sentence checks: the diff does not touch `grounding`, `output` or `context` modules. The UI confirm section shows title, body, follow-ups and audience before "Confirm and publish". |
| 6 | D-076 and ADR-012 state the relaxation, the reason, and the owner's acceptance before merge; ARCHITECTURE and PROJECT_STATE changed only where they describe this flow | PASS for content; **F2** for ARCHITECTURE line endings | D-076, ADR-012 and ARCHITECTURE all state "relaxes D-074… one Director… needs the owner's (Shane's) explicit acceptance before merge". PROJECT_STATE has no description of this flow and is rightly unchanged. |
| 7 | Full-flow test with maya-lim, olivia-koh and hr-admin (Director and HR without a team) | PASS | `test_the_full_flow_with_the_real_synthetic_roles`. HR gets 403, olivia drafts, publishing without confirm is refused, with confirm it is published, the request is resolved and the next chat cites the fix. `test_with_two_person_review_the_only_director_cannot_publish_her_own_fix`. The real profiles (`access.py:171-198`, `admin_repository.py:291-294`) have no team for the Director or HR, and the Director has `CASE_GLOBAL`, so the case load used for redaction is valid in reality. |

## 6. Interpretive choices assessed

| Choice | Assessment |
|---|---|
| Self-reject allowed in single-reviewer mode without confirmation, recorded as single-reviewer | **Justified.** With one Director, the author could not otherwise discard their own wrong fix. A reject publishes nothing, so the confirm step guards only going live. It is documented in D-076 and covered by `test_an_author_may_reject_their_own_fix_and_the_request_opens_again`. It falls under the owner acceptance D-076 already requires. |
| Fix redacted against the request's case, loaded with the Director's own session; failure stops the change; guidance from a request is also redacted | **Justified and fail-closed.** Directors hold `CASE_GLOBAL`. The load happens before the lock, but the in-lock recheck re-validates identity, capability and request scope. The recheck tests assert `locked == [False, True]`. Pattern redaction of guidance can mangle legitimate 6-digit numbers, but the Director sees the result before publishing. |
| Guidance change keeps the current version's visibility unless one is given | Reasonable, but **the implementation reads the latest version (F3)**. |
| Frontend sends `confirm_single_reviewer=true` on every approval after its confirm step; the server ignores it for non-authors | **Justified.** The confirm step precedes every approval in the UI. The server marks single-reviewer only when the approver is an author, and `test_a_second_reviewer_is_never_marked_single_reviewer` sends `confirm=True` from a non-author. |
| `turns` and `draft_entry_id` removed from the feedback API | **Justified.** The conversation is no longer used. `extra="forbid"` turns an old client's `turns` into a 422, which the test asserts. No other consumer in the repository references `draft_entry_id` (`git grep`). |

## 7. Security, authorization and persistence review

- **Authorization and scope.**
  - `draft` and `close` call `require(APPROVE)`, so RM and HR get 403.
  - `request_in_scope` returns 404 "No such enhancement request." for out-of-team, missing or
    helpful-rating ids alike, so there is no existence leak. Tests cover a team-B Director, id
    999 and a rating id.
  - A guidance target outside the caller's scope gets 404 through `found`.
  - Global Directors (role DIRECTOR, no team) see every team, and the scope tests cover them.
- **In-transaction recheck.**
  - Both new store methods take `authorize` and run it right after `BEGIN IMMEDIATE`.
  - `reach` re-reads the request scope and the guidance scope inside the lock.
  - `decide` keeps its existing recheck.
  - The only work outside the lock is the case load and the pre-check, and the recheck covers
    both.
- **CAS and races.**
  - `draft_request` and `close_feedback` both require `status='open'` under the write lock, and
    the race test proves exactly one winner either way.
  - `decide` still uses `_set_status`, which only acts while the version is pending.
  - Approve and reject happen in the same transaction as the request update. Only F1's link
    granularity is wrong.
- **Single-reviewer path.**
  - No path skips the confirmation for an author approval.
  - `own` comes from `_chain_authors` (the authors and editors of the revises chain), so an
    editor is covered too.
  - A non-author cannot set the mark.
  - The flag reaches `decide` only from server config (`main.py`), never from the request.
- **v4 migration.**
  - The `reviews` ALTER adds a column with `DEFAULT 0` and is committed on its own.
  - The `feedback` rebuild is one explicit `BEGIN…COMMIT` script. On error, the `with db`
    rollback in `_connect` undoes the rename.
  - Both steps are idempotent and guarded by column checks, so a crash between them, or
    between them and the `meta` write, recovers on reopen.
  - The v3 test checks row-for-row preservation, the ids continuing, the CHECK constraint after
    the rebuild and a second open.
  - The `_migrate_to_2` change to explicit column names is behaviour-neutral (both tables have
    seven columns at that step) and safer.
  - The rollback note in ADR-012 holds: my probe shows pre-v4 code opens a v4 store and resets
    the version to 3, and v4 code reopens it cleanly with `close_reason` intact.
  - The knowledge store was introduced in one PR (#99), so no other legacy feedback shape
    exists.
- **Redaction.**
  - RM notes are redacted against the case before they are stored.
  - Director title, body and follow-ups (resolution) and title and body (guidance) are redacted
    against the request's case and then by pattern.
  - `source_ref` is not redacted. It is a policy reference written by the Director, and the
    reviewer sees it.
- **Browser errors.** The three new fixed messages are added to `SAFE_ERROR_MESSAGES`, and
  everything else falls back to a generic message.
- **Secrets.** No secret, credential or PII is newly tracked. `.env.example` only gains the
  setting.

## 8. Superseded and changed tests

- **Legitimately superseded:**
  - Tests that asserted "Solved it" or helpful creates a draft:
    `test_solved_it_drafts_a_redacted_entry_pending_review`, the frontend "sends Yes, helpful
    with the conversation", `closes a gap`/"Mark as handled", the `draft_entry_id` assertions,
    and the redaction tests built on `draft_resolution`/`turns`.
  - Each has a replacement that keeps the safety property:
    - The redaction properties now apply to the Director's fix and the RM note.
    - The "forged assistant turns" protection becomes a 422 for any `turns`.
    - Pattern redaction gets its own test.
    - The known-address-part test is kept.
- **Changed helper `solved` → `drafted`:** the draft is now written by `director-drew` instead
  of RM maya-lim. Every maker-checker test that used it still asserts the author or editor
  gets 403 MAKER_CHECKER under the default test setting (`single_reviewer=False`).
- **`test_the_original_author_cannot_decide_a_revision_of_their_entry`:** it now uses
  drafter-session as the original author. The coverage is equivalent.
- **`test_an_rm_can_never_approve_and_the_author_never_decides`:** it gained an extra legacy
  RM-authored case, so it is stronger.
- **`test_the_author_can_see_their_own_draft` / `..._sees_only_the_versions_they_wrote`:** these
  now use `legacy_rm_draft`, since RMs no longer author drafts. The property is preserved for
  legacy stores.
- **`test_the_whole_loop…`:** it now drafts, edits in a follow-up and approves with a second
  Director. The follow-up learning is still asserted.
- **Recheck tests:** the suite pins `knowledge_single_reviewer=False`, so the two-person
  expectations are unchanged. A new `draft-from-gap` mutation was added to every revocation and
  team-move matrix. The adjusted `me_calls` and `locked` expectations are explained by the
  extra case load and still prove the refusal comes from inside the write.
- **Conclusion:** no test was weakened.
- **Gap:** no test covers F1's scenarios, two requests on one guidance entry or an HR pending
  version.

## 9. Required fixes

1. **F1 (Medium, blocking):** link each request to the exact fix version. Carry the link
   through reviewer edits. Resolve or reopen only that request. Add tests for both scenarios.
2. **F2 (Low):** restore the original line endings in `docs/ARCHITECTURE.md`, keeping only the
   10-line paragraph.
3. **F3 (Low):** use the current approved guidance version for scope and inherited visibility,
   or correct the docs. Add a test.
4. **F4 (Low):** make the Review-window claim in the docs match the UI, or list
   single-reviewer decisions from history. Gate the confirm box's single-reviewer sentence on
   the mode.
5. **F5 (Low):** refuse `fields` and `stages` on a past-resolution fix.

Not required: I1, I2 and the pre-existing `ViteHistoryFallback.test.ts` failure, which also
fails on `origin/main`. Because the reviewed content will change, a fresh independent gate is
required afterwards.

## 10. Residual risks and later dependencies

- Single-reviewer mode defaults to **on**. Until the owner accepts D-076, merging would ship a
  relaxed D-074 control by default. That is the owner's decision, not a defect.
- Redaction only knows case-supplied values and the listed patterns. A client name or address
  not in the case data is not removed, even though the panel hint, mandated by the
  assignment, says names, UENs and addresses are removed. The Director's final-text review
  remains the control.
- No browser E2E covers the feedback note, the Knowledge review window or the confirm step.
- POLICY_APPROVE stays PROJECT_DEFINED_PROVISIONAL and Q-014 review authority stays
  UNKNOWN_BLOCKED. No Live, sponsor or provider claim is made or affected.

## 11. Readiness and Git status

- **Readiness:** not ready for publication. F1 must be fixed and re-gated, and D-076 needs the
  owner's explicit acceptance.
- **No impact on ACRA or GoldTier:** the change touches no ACRA or GoldTier path, provider
  status or CLM backend write.
- **Git:** branch `feat/ai-assistant-feedback-requests`, HEAD `81a59c2`. Nothing is staged,
  there are no tracked modifications, and the only untracked file is this report.
- **No other changes:** no implementation fix, commit, push, stash, reset, PR or merge was
  made, and no other phase was started.

**Verdict: FAIL**
