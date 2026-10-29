# Independent Quality Gate: synthetic boundary `onboarded` hotfix

Date: 2026-10-30. Reviewer: independent QG (did not author the change). Read-only on all tracked checkouts.

## Verdict: PASS

## Identity and fingerprint

| Item | Start | End |
|---|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\synthetic-boundary-onboarded-20261030` | same |
| Branch | `fix/synthetic-boundary-onboarded` | same |
| HEAD = origin/main | `2911b54fb78b2503e80511c0cc3fc54eae37e37f` (#133) | same |
| Status | ` M apps/assistant/ai_assistant/synthetic_boundary.json` only | same |
| sha256 `git diff HEAD --binary` | `9fc36de347ed769d19c27e90686a295a409a3b8dd8577f31ec011e4d20f6bb42` | same |
| sha256 working file | `8acef57e594b92ed4c8743843df5641e3f3ca6673bb195972c1e23c028bb177f` | same |

Fingerprint correction: the original brief gave `bb34dc6b...` / `4e4dee1d...`; the coordinator
later corrected these to `9fc36de3...` / `8acef57e...`. My own measurements at start and end
match the corrected values, not the original ones. Reviewed content did not change during the gate.

## Exact diff

```
--- a/apps/assistant/ai_assistant/synthetic_boundary.json
+++ b/apps/assistant/ai_assistant/synthetic_boundary.json
@@ -2654,6 +2654,7 @@
   "omit",
   "omits",
   "omitted",
+  "onboarded",
   "onboardingcase",
```
1 file changed, 1 insertion. `git diff --check` clean. Index and working copy are LF (`i/lf w/lf`);
the CRLF warning is only the local autocrlf advisory.

## Reproduction and determinism (throwaway detached worktree of 2911b54, now removed)

- Baseline `build_synthetic_boundary.py --check` -> "synthetic boundary is not current", rc=1.
- Baseline `pytest tests/test_remote_test.py::test_the_boundary_file_is_current` -> FAILED (AssertionError at line 271).
- Generator run in the throwaway -> output sha256 `8acef57e...`, `cmp` byte-identical to the candidate; a re-`--check` passes.
  This shows the candidate is pure generator output (no manual edit) and the generator is deterministic.
- `ai_assistant`/`assistant_eval` confirmed imported from the throwaway tree (not main's editable install).

## Cause

- Structural compare (baseline vs candidate JSON): key order equal; `schema, note, company, documents (5),
  viewers (6), values (19), knowledge (12), conversation_vocabulary (806), prompt_vocabulary (64)` unchanged;
  `code_vocabulary` 2,877 -> 2,878, added `["onboarded"]`, removed `[]`.
- AST scan of `apps/backend/app` + `apps/assistant/ai_assistant` string constants containing "onboarded" at 2911b54:
  `case_management.py:288` (the `progress` Literal), `case_management.py:397`, `main.py:1984`,
  `mongo_case_store.py:1549`, `case_query.py:120`; all added by #133. At `d90ab6a` (pre-#133), `onboarded`
  appears only in identifiers (`weekly_onboarded`), not string literals. Cause confirmed.

## Security semantics (key)

`synthetic_boundary.boundary()` builds `conversation = conversation_vocabulary`,
`assistant = conversation | prompt`, `system = conversation | prompt | code_vocabulary`.
`check_messages` consults `approved.system` only for `role == "system"`; assistant history uses
`approved.assistant`; user turns use `approved.conversation`. `code_vocabulary` is therefore system-only.
The generator also states and enforces that (`code_only = code_words - conversation - prompt_words`).
Other callers (`remote_test.py`, `anthropic_runtime.py`, `anthropic_chat.py`, `main.py` via `check`)
all go through `check_messages`; `synthetic_eligibility.py` imports only helpers, not the vocabularies.

Probe (`probe.py`, uncached loader, hotfix worktree as import root), output in `probe_output.txt`:

| Message | Baseline | Candidate |
|---|---|---|
| user "Which cases are onboarded?" | SYNTHETIC_TEXT_NOT_APPROVED | SYNTHETIC_TEXT_NOT_APPROVED |
| user "onboarded" | SYNTHETIC_TEXT_NOT_APPROVED | SYNTHETIC_TEXT_NOT_APPROVED |
| assistant history "The case is onboarded." (+ normal user q) | SYNTHETIC_TEXT_NOT_APPROVED | SYNTHETIC_TEXT_NOT_APPROVED |
| system "The case is onboarded." | SYNTHETIC_TEXT_NOT_APPROVED | None (allowed) |
| control user "What should I do next?" | None | None |

Set sizes: conversation 806/806 and assistant 870/870 identical; system 3,747 -> 3,748, diff exactly `{onboarded}`.
Conclusion: the hotfix does not broaden what a user question or assistant history may transmit; it only
lets the service's own system text use one backend status word.

## No other changes

Only the JSON changed: no change to the generator, `synthetic_boundary.py`, tests, remote-inference
authorisation (`remote_test.py`, `anthropic_runtime.py`, config), or spending safeguards (`budget.py`, D-098/D-100 code).

## Test and check evidence (hotfix worktree, cwd `apps/assistant`, PYTHONPATH = that dir, main `.venv` python)

| Command | Result |
|---|---|
| `python scripts/build_synthetic_boundary.py --check` | "synthetic boundary is current", rc=0 |
| `pytest -p no:cacheprovider tests/test_remote_test.py::test_the_boundary_file_is_current` | 1 passed, 0 failed (junit) |
| `pytest -p no:cacheprovider -o faulthandler_timeout=300 tests/test_remote_test.py tests/test_synthetic_eligibility.py tests/test_claude_runtime.py tests/test_claude_console.py tests/test_phase_b_live.py tests/test_model_management.py tests/test_d098_recovery.py` | 462 tests, 0 failures, 0 errors, 0 skipped, 143 s (junit), rc=0 |
| `python scripts/check_secrets.py` (repo root) | "Secret scan passed", rc=0 |
| `python scripts/check_project_state.py` | PASS, rc=0 |
| `python scripts/check_architecture.py` | PASS, rc=0 |
| `python scripts/check_policy_authority.py` | PASS, rc=0 |

No network calls, no paid calls, no qualifications or activations. `.env` was not read.

## Qualification basis

`model_qualification.qualification_basis()` (includes `synthetic_boundary.json`):
- baseline 2911b54 (pristine file): `33f602653de73f372a787a9d4403daedcd589140aae02b86a4796cd994e87513`
- candidate: `9c9131ecdd40c8934d2de65597daead2c068845dfa29754769e715ab4c52b22f`

## Downstream consequences (informational)

1. The basis change invalidates every earlier GPT-OSS / Claude qualification recorded against `33f60265...`;
   requalification needs separate owner authorisation (not done here).
2. D-102 integration (`731afe4`, based directly on 2911b54) does not touch the boundary file, so it carries the
   same stale boundary; its own basis is `4c54e4dd9dbd...`. Verified in a separate throwaway detached worktree
   of 731afe4 (D-102 worktrees untouched; throwaway removed): with the candidate JSON applied, the generator
   `--check` passes (D-102 adds no new code vocabulary words) and the basis becomes
   `65f22e46c509b2f4e0540f8412e9940e5c1d9c49c85e6eb28c94f0e0b1479328`, matching the prior QG's figure.

## Findings

- Blocking / Major / Minor: none.
- Info: the CRLF warning is the local autocrlf advisory; the blob stays LF, as the generator writes it.
- Info: the underlying fragility (any new backend string literal makes the boundary stale and moves the
  qualification basis) is existing design, outside this hotfix's scope.

## Next authorised action

Commit, push, PR and merge need explicit owner authorisation. This gate did none of them.
