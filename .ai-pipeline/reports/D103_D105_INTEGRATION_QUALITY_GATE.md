# D-103 / D-105 integration quality gate (PR #138)

Independent Stage 3 review (`fyp-quality-gate`) of a feature change. This is not a
numbered phase gate. The reviewer did not write or remediate the reviewed content.

## 1. Executive result

**PASS WITH MINOR FIXES**

The Support role (D-103) and the conversation-feedback / Support review workflow (D-105)
are implemented as recorded. The parts that matter for security hold up under independent
inspection and adversarial execution:

- `SUPPORT` has exactly `POLICY_VIEW`, `KNOWLEDGE_REVIEW` and `KNOWLEDGE_CASE_READ`.
- `CASE_READ` admits only the two named GET routes. Every other case route answers 404,
  the same as an absent case.
- Knowledge review requires `KNOWLEDGE_REVIEW`, and Directors no longer have it.
- Conversations are never joined across users or cases, and an ended conversation is
  never joined again.
- An end is recorded only once.
- The caseless Support chat reads no case.
- Neither new model path calls a model that requires the synthetic boundary.
- Schema v6 migrates a real main (v5) store.
- The #139 integration lost nothing.

The remaining items are low-risk corrections to wording, documentation, an edge-case
legacy link and consistency (section 7). None of them blocks the verified behaviour.

Some required evidence is still unavailable. These are missing-infrastructure items, not
defects:

- physical Mongo (for the Mongo-mode `support-user` seed);
- the complete official E2E/lifecycle suite;
- hosted CI.

Each blocks only the claim named in section 4.4. Before publication, the owner must
decide what to do about them.

## 2. Frozen identity and scope

| Item | Value |
|---|---|
| Branch | `assistant-edits` |
| HEAD | `79814364cff62d3222ee5a5b7035a1a4be07c52a`. This is a merge commit with parents `56c72ac` and `582ad66`. |
| Tree | `02b5dd09305c0b1bfece5c01c4f27310de1454b0`. Verified at the start and again before this report was written; it did not change. |
| Integrated base | `origin/main` `582ad666031c8f139bfc5ad254bcd03244c3d640` (includes #139) |
| Reviewed delta | `git diff 582ad66 7981436`: 53 files, +4151/−1250 |
| Working tree | Clean. The only file added is this report. |
| PR | #138 is OPEN. The PR head OID equals HEAD. GitHub reports it MERGEABLE. |

The scope covers the backend role, capabilities, route access, seed and configuration;
the assistant's knowledge API, conversations, store v6, the support chat and the `try`
endpoint; the frontend panel, Knowledge Review, End conversation, History and navigation;
the decision, ADR, contract, runbook and configuration documents; and the scripts and
test fixtures.

## 3. Acceptance checklist

| # | Criterion | Result | Direct evidence |
|---|---|---|---|
| D103-S1 | `SUPPORT` is team-less with exactly `POLICY_VIEW`, `KNOWLEDGE_REVIEW` and `KNOWLEDGE_CASE_READ`; no other role holds the latter two. | PASS | `apps/backend/app/domain/access.py:91-97`. The `UserProfile` and `UserAccountRecord` validators reject a team. `test_support_reviews_knowledge_and_views_policy_without_case_access` was re-run and passes. |
| D103-S2 | `support-user` is seeded from `PHASE13_SUPPORT_USER_PASSWORD_HASH`; a missing or malformed hash fails closed; an existing profile is never overwritten. | PASS (memory mode). Mongo mode is not physically verified. | `admin_repository.py:298-308` and `_insert_seed_profile` (unchanged fail-closed logic); `composition.py:233`. Both memory and Mongo modes call the same `bootstrap_administration`. Configuration, runbook and contract docs are updated. |
| D103-S3 | Every review endpoint and `can_review` require `KNOWLEDGE_REVIEW`; the global reviewer is a team-less `SUPPORT`; the recheck inside writes uses `REVIEW`. | PASS | `knowledge_api.py` replaces all 20+ `APPROVE` sites with `REVIEW`, including the `recheck(...)` calls inside writes. `test_a_director_with_policy_approval_cannot_review_knowledge` passes. In the QG adversarial test, Director, HR and RM all get 403 on every new Support endpoint. |
| D103-S4 | `CASE_READ` covers only the two GETs, for any case; every other case route answers 404 like an absent case; the portfolio returns 403; there is no mutation and no evidence-decision authority. | PASS | `authorization.py:124,237,288-307`; `api_auth.py:267-283`. `can_decide_evidence` still requires `can_access`, so Support gets `false`. `test_support_reads_only_the_knowledge_redaction_case_routes` iterates all 44 `CASE_SCOPED` policies; `test_every_current_application_route_is_deliberately_classified` (44 + 2). Both were re-run and pass. |
| D103-S5 | Knowledge Review is a tab gated on `KNOWLEDGE_REVIEW` and is Support's landing page; Policy is read-only. | PASS | `navigation.tsx` and the `Phase15CNavigation.test.tsx` D-103 test (re-run). |
| D105-C1 | A question joins a conversation only when it is that user's open conversation on that case. | PASS | `store.py` `_open_conversation`. The QG store-level and HTTP adversarial tests found no join to another user's conversation, another case's, an ended one, or a legacy record id. |
| D105-C2 | The form rules are enforced by the service (422); the comment is redacted; a conversation is rated once. | PASS | `EndConversationRequest`. The QG adversarial test checks: an offered/resolved mismatch gives 422; a blank improvement comment gives 422; extra keys give 422; a second end gives 404. `test_the_comment_is_redacted` passes. |
| D105-C3 | The priority mapping and the single feedback row are written in the same write; retention follows the request; a conversation is purged with its last record. | PASS, with finding L1 | `store.py:1234-1320` and `_purge_answers`. |
| D105-C4 | The review list holds rated conversations only, is filtered and paged 10 at a time, and is ordered high, medium, low, then none. | PASS | `test_support_lists_rated_conversations_by_priority_with_filters` and `test_the_list_pages_ten_at_a_time`. In the QG test, an unknown status or satisfaction gives 422 and a negative page is clamped. |
| D105-C5 | Drafts are redacted; they are cleared when a fix is saved or the request is closed; saving a draft is refused once the request is closed. | PASS, with finding L2 | `_drop_draft` in `draft_request` and `close_feedback`. In the QG test, closing clears the draft and a later PUT returns 409. |
| D105-C6 | History shows only the user's own conversations, with logged views. | PASS, with finding L4 (wording) | `test_history_lists_and_opens_only_the_users_own_chats`. The QG test confirms Support cannot open another user's chat through `/assistant/conversations/{id}`. |
| D105-C7 | The caseless Support chat requires `KNOWLEDGE_REVIEW`, reads no case data, uses the exact-line rule, and never calls the remote model. | PASS, with finding L3 (notice wording) | `support_chat.py`. In the QG test, a fake model with `requires_synthetic_boundary` made 0 calls, the transport recorded no `/cases/` request, and an injected non-allowed line was dropped. |
| D105-C10/C11 | `try` saves, publishes and records nothing and uses the local model only; Support's case chat keeps no record. | PASS | `main.py:961-1023`. In the QG test, `try` made 0 calls to the remote fake. `test_try_a_change_offers_its_sentences_and_saves_nothing`; `test_support_case_chat_on_a_review_page_keeps_no_record`. |
| D105-C12 | HR gets no AI Assistant panel. | PASS | `App.tsx` gate and the `Phase15CNavigation.test.tsx` test (re-run). HR gets 403 on the support chat, and its history is empty. |
| Store v6 | A real main (v5) store migrates in place. | PASS | QG script: a store was built with main `582ad66`'s `store.py` (v5), then opened with HEAD. It moved to version 6, gained `conversation_id` (NULL for the old record), and kept its feedback row. Conversations then worked. |
| #139 integration | No behaviour or test from main was lost; main's D-104 text is unchanged. | PASS | Of the 20 files #139 changed, only `main.py`, `aiAssistant.ts` and `DECISION_LOG.md` differ from main. Every line #139 added to the first two is present at HEAD. The DECISION_LOG diff against main contains only additions. |
| Manifests | The synthetic boundary and eligibility manifests are current. | PASS | Re-run of `build_synthetic_boundary.py --check` and `build_synthetic_eligibility.py --check`. |
| Qualification statement | The impact on the qualification basis is stated truthfully. | Partially, see L5 | The basis hash changes from `598cfe14…` (main) to `2c9d72cf…` (HEAD). Basis files changed: `main.py`, `answer_records.py`, `synthetic_boundary.json`. |

## 4. Tester and adversarial findings

### 4.1 Re-run in this session, on frozen HEAD `7981436`

| Check | Result |
|---|---|
| Backend focused: `test_phase13_auth_rbac.py`, `test_model_config_capability.py`, `test_phase13_demo_scripts.py`, `test_phase14_5_administration.py` | 107 passed |
| Assistant focused: `test_conversations.py`, `test_knowledge_review*.py` (3 files), `test_answer_records.py` | 178 passed |
| Assistant suite, per file (51 files) | 50 files pass. `test_d098_recovery.py` fails: `test_a_paid_run_waits_for_the_key_limit_check_and_an_unreconciled_ledger` raises `KeyError: 'detail'`. The same test fails on a clean extraction of main `582ad66`, so the failure is pre-existing and not caused by #138. |
| Assistant suite, single process | **Hung at about 83%** (process sleeping, 0% CPU) and was killed by the reviewer. I did not determine whether this also happens on main. It is not counted as a pass. The implementer also ran per file. |
| Frontend focused: `AiAssistantPanel.test.tsx`, `KnowledgeReview.test.tsx`, `Phase15CNavigation.test.tsx` | 113 passed |
| Frontend full vitest | 1256 of 1257 pass. `ViteHistoryFallback.test.ts` fails with `/src/styles.css` served as `text/css`. It fails the same way on the clean baseline 0c6a632 copy, and its inputs are untouched by both #139 and #138. |
| `tsc --noEmit` (frontend) | Pass |
| Ruff (`--no-cache`, all changed Python files) | Pass |
| mypy, assistant (47 files) and backend (129 files), with the cache in scratch | Pass |
| Synthetic boundary and eligibility `--check` | Both current |
| Root `tests/`: `test_slice_c_e2e_fixture_routing.py` (changed by this PR) | 4 failed, 12 passed. The same 4 fail on the baseline main copy (along with 4 `test_performance_review_remediation` failures and 1 `test_run_e2e` failure), so they are pre-existing. |
| `git diff --check 582ad66 7981436` | Clean |
| Tracked secret check | No new credential files. The only scrypt mention is runbook prose. |
| QG adversarial suite (scratch, outside the repo): 8 tests | 8 passed. Coverage: Director, HR and RM are refused on every Support endpoint; Support cannot see, try, end or open an open or foreign conversation; the form rules hold; joining rules hold over HTTP; the support chat reads no case, never calls the remote fake and drops an injected line; `try` never calls the remote fake; close clears the draft and a later draft PUT gets 409; filter validation. |
| QG store scripts | v5→v6 migration plus join and end-once rules: all OK. The legacy-feedback overlap reproduced finding L1. |

### 4.2 Reused implementer evidence, and why

| Evidence | Revision | Why it can be reused |
|---|---|---|
| Backend full pytest: all pass except 6 `test_s2_local_ocr` (local font) | `d265625` | `git diff d265625 7981436 -- apps/backend tests scripts` is empty, so the backend and its tests are byte-identical. The 6 font failures are environmental. |
| Contract tests: 43 of 44 (`test_decimal_api_contract_and_typed_classifications`) | `d265625` | Same reason. The failure is in the ownership contract, which this PR does not touch. |
| `assistant-answer-records` Playwright: 1 passed | `d265625` | Frontend changes since `d265625` are comment renumbering (D-104 to D-105) plus #139's AiModelManagement files. No behavioural change touches this journey. |
| `pre_pr_check.py` PASS (0 unsafe, 2 warnings) | `7981436` | Not re-run. It is a publication gate, and I relied on the implementer's run. |

### 4.3 Stale or partial evidence

- **Full official E2E.** Partial (keep-going on `d265625`/`179ca0d`): 20 pass and 11
  failures that the implementer says are identical on main. The remaining lifecycles did
  not complete because of `PORT_UNAVAILABLE`, intake hangs and sandbox cleanup. I did not
  re-run it, as the brief instructed.

### 4.4 Missing infrastructure and the claims it blocks

| Missing | Required by | Blocked claim |
|---|---|---|
| Physical Mongo server | PERSISTENCE (R) and AUTH (A) | Mongo-mode startup inserts `support-user` once, never overwrites it, and fails closed without the hash, all against a real driver and server. |
| Complete POC lifecycle / official E2E | AUTH_RBAC_SECURITY and PERSISTENCE (R) | That the new role and seed cause no regression in the other browser journeys under the official runner. |
| Hosted CI (GitHub billing block) | Publication | The remote CI status of PR #138. |

## 5. Code and architecture review

**L1 (Low, data integrity).** `apps/assistant/ai_assistant/knowledge/store.py:1288-1291`
(`end_conversation`).

- `end_conversation` overwrites `linked_request_id` on the conversation's last record
  without checking `rated_at`.
- The legacy `POST /assistant/cases/{id}/feedback` endpoint is kept "for compatibility"
  (C8) and still accepts "Not helpful" on a record that has a conversation.
- A user who rates a record through that endpoint and then ends the conversation leaves
  the first request without its record (reproduced: request 1 had `answer_id=None` and
  the record was linked to request 2). Retention then follows only the second request.
- Fix: skip or refuse a record that is already rated, or keep it through
  `answer_record_keeps`.
- This path is reachable only by the record's own user, through the API.

**L2 (Low, consistency).** `apps/assistant/ai_assistant/knowledge_api.py:780-787`
(`discard_draft`).

- `discard_draft` calls `save_conversation_draft(..., by=...)` without `authorize`. The
  module rule says "Every review or guidance change asks the backend again inside its
  write transaction", and `save_draft` does this with `still_reviewer`.
- No unauthorised action is reachable, because the actor is freshly loaded from the
  backend and checked for `REVIEW` and scope at the start of the same request.
- The change is still inconsistent with the stated rule and with AGENTS.md's in-boundary
  reauthorization invariant.
- Fix: pass the same recheck.

**L3 (Low, user-visible wording).** `apps/assistant/ai_assistant/support_chat.py:49-52,229-230`.

- `is_remote_test_model` is also true for a D-104 policy-restricted *local* model
  (`data_access.SyntheticOnlyModel`).
- In that state the Support chat correctly does not call the model, but it shows
  `REMOTE_NOTICE` ("uses the local model only (the external model is approved for
  synthetic case chats only)"). That text is inaccurate when the restricted model is the
  local one.
- The `try` endpoint (`main.py:1011`) falls back silently in the same case.
- Fix: choose the notice from the model's class, or use a neutral one.

**L6 (Low, comment accuracy).** `apps/assistant/scripts/build_synthetic_eligibility.py:118`.

- The comment says "the Support reviewer has no case access, so it never views a case in
  chat". Under D-105 C10, Support does chat about a case on the review page.
- Behaviour fails closed: the viewer name is not in the eligibility manifest, and
  document digests return 404 for Support.
- Only the comment is wrong.

**Observation (no fix required).** `support_chat.py` is a model-answering path with its
own prompt, but it is not in `model_qualification.BASIS_FILES`. A later change to it will
not invalidate a qualification. This is acceptable while C7 keeps the chat to models that
do not require the boundary; record it if another model is ever admitted.

Scope, coupling and architecture:

- No change to ACRA, GoldTier, ownership, the ledger or the D-104 data-access code.
- There is no direct route-to-Mongo access, no frontend authority (the UI gates are
  display-only and the backend and assistant enforce everything), and no second
  authorization owner.
- `CASE_READ` reuses the central middleware.

## 6. Security review

These were verified:

- Least-privilege capability set.
- `CASE_READ` is confined to the two GETs, and inaccessible cases answer 404 exactly like
  absent ones.
- Support's caseless chat performs no case read.
- No new model path reaches a boundary-requiring model.
- The comment, draft title, body and follow-ups, and the trial text are redacted against
  the case.
- The CSRF and origin checks (`check_origin` and the actor dependency) cover all new
  endpoints.
- Password hashes are handled only through `SecretStr` settings and the generator.
- `.env` was not opened.

Residual risks that are decided, not defects. Each needs sponsor confirmation (Q-013,
Q-014 remain open):

- **Global read for Support.** D-103 S4 deliberately lets `KNOWLEDGE_CASE_READ` read the
  summary and document list of *any* case, not only cases behind an open request.
  Support's case chat (C10) can put that case's facts in front of the local model.
- **Wider exposure of recorded questions.** Under D-105, Support sees the raw recorded
  question as the title of every rated conversation, including satisfied ones, and the
  full transcript, not only the D-084 "at most 2" earlier answers. The question is stored
  unredacted under the existing ADR-012 relaxation.
- **Bootstrap requirement.** Startup now requires the seventh hash. Existing operators
  must add it, as the runbook says.

## 7. Required fixes

All are minor and bounded.

1. **L1.** `store.py:1288` (`end_conversation`): do not overwrite an already-rated
   record's `linked_request_id`. Skip it or use a keep row. Add a test for the
   legacy-feedback-then-end case.
2. **L2.** `knowledge_api.py:784` (`discard_draft`): pass the `still_reviewer`-style
   recheck as `authorize`.
3. **L3.** `support_chat.py:49-52,229`: give an accurate notice when the active model is a
   D-104-restricted local or IT model.
4. **L4.** `docs/decisions/DECISION_LOG.md:1679` (C6) and `knowledge_api.py:568`
   (`transcript` docstring) say the transcript is "redacted". The answers are redacted,
   but the questions are stored and shown unredacted (ADR-012 relaxation). Correct the
   wording.
5. **L5.** `docs/decisions/DECISION_LOG.md:1687-1689` (D-105 qualification paragraph)
   names only `main.py` and `answer_records.py` and only GPT-OSS 120B. It should say:
   - `synthetic_boundary.json` also changed;
   - the basis hash changes, so *every* earlier qualification of any non-baseline profile
     (GPT-OSS, Claude, and console local or IT profiles) is out of date;
   - only the environment baseline model is unaffected.

   The PR description is closer to this but also says "the local model is unaffected".
6. **L6.** `build_synthetic_eligibility.py:118`: correct the comment. A manifest
   regeneration is not needed if only the comment changes.

## 8. Readiness

- **Feature content:** substantially accepted for the verified scope once the minor fixes
  above are made. Those fixes change reviewed content, so they need a bounded independent
  recheck of the changed delta. Unchanged valid evidence can be reused.
- **Publication:** additionally needs an owner decision on the missing-infrastructure
  lanes in section 4.4 (physical Mongo seed, complete E2E, hosted CI), plus explicit owner
  authorization.
- **Real ACRA / GoldTier readiness:** unaffected and not claimed. No connector changed.
- **Qualification:** re-qualifying every non-baseline model profile on the new basis is
  a separate, paid, owner-approved action.

## 9. Git status

- Branch `assistant-edits`, HEAD `7981436`, tree `02b5dd0`. Nothing was staged, and there
  were no tracked modifications during the review.
- The only file created in the repository is this report. Untracked, it is not
  covered by `git diff --check`, and its whitespace was checked separately.
- Scratch artefacts are under
  `/private/tmp/claude-501/-Users-despog-Documents-GitHub-data-dividends-zero-touch-clm/db1288e6-4e49-41f6-bb6d-1a3eb84a5b1f/scratchpad/qg/`.
- I made no implementation fix, commit, push, GitHub comment or merge, and did not touch
  any other branch or worktree. The dev servers on ports 8000, 5173 and 8100 were not
  touched.
