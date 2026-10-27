# AI Assistant Model Management - Post-Integration Quality Gate R3

Gate: Stage 3 independent quality gate on the integrated candidate (PR #121 after merging
main `176e09b`, PR #122). Reviewer: fresh independent reviewer. I did not author, remediate
or integrate this content. I made no change other than writing this report.

## 1. Outcome

**PASS.**

The merge commit `04a7fc5` contains exactly what PR #122 brought and nothing else. Its tree
is identical to an independent `git merge-tree` of the two parents. No feature content from
either side was lost or altered. D-092 P11 to P14, D-093, ADR-012 Amendment 2 and ADR-012
Amendment 4 are preserved byte for byte. The only difference is one blank separator line
before the section that now follows. Model management composes correctly with #122's
answer path. The qualification basis changes as designed. Permissions, remote-profile
refusal and the D-092 PROPOSED status are unchanged. The `fe29593` PROJECT_STATE text matches
the evidence. One wording gap is new (R3-1, Low, non-blocking). No finding blocks the
owner's merge.

## 2. Reviewed identity

| Item | Value |
| --- | --- |
| Worktree | `C:/Users/shane/Desktop/claude-worktrees/assistant-model-management-20261027` |
| Branch | `feat/assistant-model-management-20261027` (PR #121) |
| Reviewed HEAD | `fe2959306b8cbc298df608d704bf743e385d49d4` |
| Reviewed tree | `90f1f8c2466851f498ba886904409f0511b85150` |
| Merge commit | `04a7fc5` (parents `49623b2` and `176e09b`), tree `bbea96dad19b609b009e6d37be3ef78b7d3bd871` |
| Integrated main | `176e09ba0f3027ba4dec85aa5fde9eeb9ace1542` (PR #122) |
| Merge base | `23c45a7` |
| Remote state (`git ls-remote`, no fetch) | `refs/heads/main` = `176e09b`. The branch and `refs/pull/121/head` are both `fe29593`. |
| Working tree | Clean. HEAD and tree were unchanged from the start of the review to the end. |
| Content since R2 | `04a7fc5`, the merge, and `fe29593`, a docs change to `docs/PROJECT_STATE.md` only (+13/-4) |

## 3. Integration fidelity

| Check | Result |
| --- | --- |
| `git merge-tree --write-tree 49623b2 176e09b` | `bbea96da…` = `04a7fc5^{tree}`. The merge is a pure automatic merge with no manual edits. |
| Files changed by the merge (`49623b2..04a7fc5`) vs files #122 changed (`23c45a7..176e09b`) | The same 11 paths |
| Files the PR changes vs main (`176e09b..04a7fc5`) vs the pre-merge PR (`23c45a7..49623b2`) | The same 36 paths |
| 9 paths only #122 changed (context.py, guardrails.py, guide.py, prompts.py, snapshots.json, gold.json, test_phase_b_quality.py, test_source_and_owner_topics.py, the Phase B quality report) | The blob in `04a7fc5` is identical to `176e09b` in every case |
| 34 paths only this PR changed | The blob in `04a7fc5` is identical to `49623b2` in every case (frontend included) |
| 2 overlapping paths (DECISION_LOG.md, ADR-012) | The added and removed lines on #122's side are identical to the merge's lines on that side. The same holds for this PR's side. |
| `fe29593` | Changes only `docs/PROJECT_STATE.md`. No changes under `docs/decisions` or code. |
| Raw patch bytes `a.diff`/`b.diff` | They differ only in hunk offsets and context in the two overlapping docs, as expected after a merge. The per-blob and per-hunk checks above are authoritative. |

Frontend: `git diff --name-only 49623b2 fe29593 -- apps/frontend` is empty. I reuse R2's
frontend evidence (65 files, 1,121 passed on content identical to the frontend at HEAD).

## 4. Preservation of decisions

| Section | Compared | Result |
| --- | --- | --- |
| DECISION_LOG `## D-092` (with P11 to P14) | `176e09b` vs `fe29593` | Identical except one trailing blank separator line (D-092 was the last section on main; D-093 now follows) |
| DECISION_LOG `## D-093` | `49623b2` vs `fe29593` | Identical |
| ADR-012 `## Amendment 2` | `176e09b` vs `fe29593` | Identical |
| ADR-012 `## Amendment 4` | `49623b2` vs `fe29593` | Identical |
| ADR-012 `## Amendment 3` | `176e09b` vs `fe29593` | Identical except one trailing blank separator line (Amendment 4 now follows) |

D-092 is still titled `(PROPOSED)` and still states that recording P11 to P14 does not
accept D-092. D-093 still states that D-091 and D-092 are unchanged.

## 5. Combined behaviour and permissions

- **main.py and #122's answer path:** #122 did not touch `main.py`, `llm.py`,
  `model_*.py` or `config.py`. #122's additions to context.py, guardrails.py, guide.py
  and prompts.py are new functions and constants only. The one existing symbol it changed,
  `TOPIC_ONLY_LINES`, keeps its frozenset type. Nothing the PR calls changed signature. The
  per-request snapshot still applies to every model use:
  - `selector.current()` is taken once in `/chat`, `/chat/stream` and `/brief`.
  - That snapshot goes into `_Outcome(model=...)` and `stream_answer(..., model)`.
  - `answer_with_model` reads `outcome.model`.
  - Metrics and records also read `outcome.model`.

  So #122's lines and guards run against the active model, which is wrapped in
  `BoundedPromptModel` with the qualified prompt limit when a managed model is active.
- **Qualification basis:** all six #122 runtime and fixture inputs are in `BASIS_FILES` or
  `BASIS_FIXTURES`: context.py, guardrails.py, guide.py, prompts.py, snapshots.json and
  gold.json. I computed the basis independently:
  - pre-merge content (`git archive 49623b2`): `704fd705…`
  - HEAD: `59a3bcd4…`

  The basis changes as designed, and the HEAD value matches the implementer's figure.
  `_build_stored` returns `QUALIFICATION_OUT_OF_DATE` when the stored qualification's
  basis differs, and the service then falls back to the baseline. A model activated before
  this merge therefore fails closed after deployment, as PROJECT_STATE's "Open" item says.
- **Runtime never imports `assistant_eval`:** `grep` finds no match under `ai_assistant/`.
  The guard test `test_the_runtime_package_never_imports_the_harness` passed.
- **HR has no case access:**
  - `ROLE_CAPABILITIES[HR]` = POLICY_VIEW, POLICY_MUTATE, IDENTITY_ADMIN, TEAM_ADMIN,
    PROVIDER_SANDBOX_TEST and MODEL_CONFIG_MANAGE. It has no CASE_ACCESS or CASE_GLOBAL.
  - The merge did not change `access.py`.
  - `test_hr_sees_the_overview_without_any_case_or_credential` passed.
  - The backend tests `test_only_hr_may_manage_the_ai_model` and
    `test_model_management_leaves_every_other_capability_unchanged` passed.
- **RM/CO/Director cannot manage models:**
  - `test_only_hr_may_use_any_management_endpoint_and_refusals_are_audited`, parametrised
    over rm, co and director, passed.
  - All 6 endpoints return 403 `MODEL_CONFIG_FORBIDDEN`, no model call is made, and each
    refusal is audited.
- **Remote profile unusable:**
  - `test_the_remote_profile_is_refused_for_every_action_before_any_network_call` passed:
    the result is 409 `REMOTE_NOT_AUTHORISED` with zero requests.
  - The catalogue still lists it as `pending_authorisation`.
  - `test_phase_b_live.py` passed in isolation, so the L1 to L4 locks are intact.
- **Guardrail lists:** `tests/test_guardrail_negation.py` is byte-identical from `23c45a7`
  to HEAD. At import, `UNSAFE` = 154 and `KNOWLEDGE_FILTER_LIMITS` = 46. They are
  unchanged, not even extended.
- **No scope creep from the merge:** the merge changed no backend, frontend, configuration
  or model-management code.

## 6. PROJECT_STATE (`fe29593`) truthfulness

| Claim | Verified by |
| --- | --- |
| Integrated with main `176e09b` by merge, without conflicts | The merge-tree reproduction (section 3) |
| Basis `59a3bcd4…` | My computation at HEAD |
| The earlier qualification showed as out of date and activation was refused (`NOT_QUALIFIED`) | Read-only inspection of the implementer's LOCAL store (`scratchpad/smoke/admin.sqlite3`): the old row is `passed` on basis `704fd705…`. Audit seq 13 is `ACTIVATED refused NOT_QUALIFIED` at 13:00:23Z. |
| A fresh qualification passed every gate: 84/84, 0 unsafe, line validity 0.808, G-5 0.214, capacity verified, 0 drifted | New row `f4dc654b…`: basis `59a3bcd4…`, `passed`, 84/84, `unsafe_display` 0, `line_validity_rate` 0.8084, `fallback_rate` 0.2143 (G-5 non-gating), capacity `verified` (probed 16,354 of 16,384, prompt limit 15,449), `drifted_turns` 0. G-1 to G-7 all passed. |
| Activation with the acknowledgement, then rollback | Audit seq 16 `refused ACKNOWLEDGEMENT_REQUIRED`, seq 17 `applied QUALITY_NOT_SCORED_ACKNOWLEDGED`, seq 18 `ROLLED_BACK applied` (to `env_default`) |
| Not Live, no remote or paid call | The profile is loopback Ollama (`llama3.1:8b`) and the remote profile is refused by code |
| Open items | Accurate. Hosted CI is billing-blocked (not executed), so I make no CI claim. |

This store corroborates the implementer's LOCAL run; I did not repeat it. I started no
model server.

**R3-1 (Low, documentation precision, non-blocking).** The new sentence says a "developer
browser smoke test … passed on `aea87b9`". It names the revision correctly and claims only
RM/Director refusal and the HR end-to-end flow. It does not say that the same smoke test
raised the three UI findings S-1 to S-3. Those were fixed in `555deb1`, with unit-test
evidence only (R2) and no browser re-smoke. No claim is false, because the scope and
revision are stated, but a reader could take it as a clean browser pass. Suggested later
wording: "…passed on `aea87b9`; its UI findings S-1 to S-3 were fixed in `555deb1`
(unit-tested, not re-run in a browser)". This does not need a fix before the merge.

## 7. Commands and counts (this session, on HEAD `fe29593` content)

| Command | Result |
| --- | --- |
| `pytest tests/test_model_management.py test_phase_b_quality.py test_guardrail_negation.py test_eval_harness.py test_source_and_owner_topics.py test_guardrails.py test_model_factory.py` (apps/assistant, `PYTHONPATH=.`, project venv) | 1,006 tests, 0 failures, 0 errors (JUnit) |
| `pytest tests/test_ai_assistant.py test_knowledge_review_scope.py test_answer_records.py` | 68 tests, 0 failures |
| `pytest tests/test_phase_b_live.py test_required_p2.py test_streaming_resources.py` (the files holding the 14 Errno-24 baseline failures, run in isolation) | 227 tests, 0 failures |
| `pytest apps/backend/tests/test_model_config_capability.py` | 2 tests, 0 failures |
| `ruff check --no-cache .` / `ruff format --check --no-cache .` (apps/assistant) | All checks passed / 106 files already formatted |
| `mypy ai_assistant assistant_eval scripts` (strict, cache in scratchpad) | No issues in 54 source files |
| `python scripts/check_secrets.py` | Passed |
| `git diff --check 176e09b fe29593` and `git diff --check 49623b2 fe29593` | Exit 0 |
| `python scripts/pre_pr_check.py` (read-only) | PASS: 0 unsafe conditions, 2 expected warnings (hotspot `App.tsx`/`types.ts`; API/config `config.py`/`types.ts`); working tree clean |

**Reused, not rerun:**
- The implementer's full assistant suite on `04a7fc5` content: 2,375 tests, 14 failures,
  all `OSError: [Errno 24] Too many open files`. The JUnit file confirms 14 failures and
  that every failure message is Errno 24. `int_failed.txt` has no entry outside
  `base_failed.txt` (16 baseline entries). All 14 pass in isolation (above), so they are
  environmental.
- The backend RBAC set (79 passed).
- R2's frontend evidence (1,121 passed). This is valid because the frontend blobs are
  identical.

## 8. Limitations

- I did not repeat the LOCAL Ollama requalification (no model server may be started). I
  corroborated it only from the persisted synthetic store.
- I did not run a browser or Playwright check. The page's frontend is unchanged since R2.
- I did not rerun the full assistant suite or the full backend suite. I reused the
  implementer's full-suite JUnit and checked its failure set as described in section 7.
- Hosted CI is billing-blocked and not executed. I make no CI claim.
- `D-092` remains PROPOSED. Nothing here is Live evidence or sponsor approval.

## 9. Findings

| ID | Severity | Status | Blocks merge |
| --- | --- | --- | --- |
| F-7 | Low | Open, carried from R1 (an orphan qualification process can outlive the service) | No |
| N-1 | Low | Open, carried from R1 (a refusal flood can hide model changes in the HR audit view) | No |
| N-2 | Low | Open, carried from R1 (a stranded `running` row blocks qualification for up to 35 minutes) | No |
| O-1 | Low | Open, carried from R2 (the 15 s audit interval keeps polling in the error state) | No |
| R3-1 | Low | New: PROJECT_STATE smoke-test sentence omits S-1 to S-3 (section 6) | No |

No integration defect, lost content, permission regression, remote-path exposure or
false-success claim was found.

## 10. Readiness

The integrated candidate `fe29593` (tree `90f1f8c2…`) is ready for the repository owner's
merge of PR #121, provided remote main is still `176e09b` at merge time. If main moves, a
fresh integration and gate are needed. This verdict covers only the frozen content above. I
did not commit, push or merge anything, and none of that is authorised by this gate.
