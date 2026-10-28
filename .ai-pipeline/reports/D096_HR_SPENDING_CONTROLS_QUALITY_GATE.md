# D-096 HR spending controls — independent Quality Gate R1 to R3

Owner-authorised follow-up on PR #126 ("PR #126 — HR Budget Controls and Main Integration").
Each round was a fresh, independent, read-only reviewer agent; no network call to OpenRouter or
any external host; mocks only. Base: branch HEAD `c1d9069` (origin/main `7119905`), uncommitted
working tree.

| Round | Verdict | Required findings | Remediation |
| --- | --- | --- | --- |
| R1 | FAIL | F1, F2, F3 | below |
| R2 | PASS | none (one MINOR optional, fixed) | race fix, W1 wording |
| R3 | PASS | none | — |

## R1 — FAIL

- **F1 — MAJOR, REQUIRED.** The AI Models spending form seeded its inputs once but sent the
  latest `controls.revision`, so after a refetch a stale form could revert another
  administrator's change without a conflict (reproduced: daily limit US$0.05 at revision 4
  reverted to US$1.00). Fix: refill the inputs whenever the stored revision changes and send the
  revision they were filled from.
- **F2 — MAJOR, REQUIRED.** The lifetime-cap and provider-refresh routes did not require the
  model state store, so with no profiles file a cap raise succeeded with no audit record. Fix:
  `managed()` in both routes.
- **F3 — MINOR, REQUIRED.** The daily input rounded stored amounts to cents (US$0.005 shown as
  0.01), so saving only the call limit changed the daily limit. Fix: show amounts exactly.
- Verified: qualification basis unchanged (`2bd93aeb8886…` at HEAD and in the tree), synthetic
  boundary current, daily cap reaches `ledger.reserve` for chat and qualification, US$1.00
  ceiling, CHECK clauses, StrictInt, CAS, RBAC/Origin/rate limit, ledger history kept, no ledger
  created, only GETs to OpenRouter, fixed frontend messages, no change to model, prompts,
  eligibility, document verification or chat.

## Remediation after R1

F1: inputs refilled on a revision or cap change; the save sends the form's revision (test
`refills the form when another administrator changed the limits…`, fails without the fix).
F2: `managed()` first in both routes (test
`test_without_model_management_no_spending_change_is_made_unaudited`). F3: `amountText` exact
(test `shows stored amounts exactly…`). W1 wording on qualification timing.

## R2 — PASS

F1–F3 confirmed fixed, each test failing when its fix is undone. One **MINOR, OPTIONAL**
finding: `sync_controls` read the controls outside `_controls_lock`, so a request that read an
older revision could apply it after a newer one, briefly restoring a looser daily limit on the
active model (still within the ledger's US$1.00 daily ceiling). Also the W1 sentence about
running requests was inaccurate. Both fixed before publication (the read moved inside the lock;
test `test_a_late_reader_never_puts_an_older_limit_back`; W1 reworded). Advisories, left as is:
the lifetime cap has no CAS (a stale form can only lower, a stale raise fails closed); HR may
raise an environment-lowered daily cap up to US$1.00 (owner-requested, W1); in-flight requests
in another process use the limits last applied there; qualification reads the controls at run
start; refresh and raise run the full existing preflight (ledger recover and verification);
the raise check and `set_cap` are not atomic across processes (`set_cap` re-checks its own
confirmation); a cap equal to the opening usage blocks all calls (fails closed).

## R3 — PASS

The read is inside the lock that applies it; revisions only increase, so an older revision can
no longer overwrite a newer one. Lock order `_controls_lock` → `model._lock` only; no cycle
with `selector._lock`, `change_lock` or the store; sync routes run in the threadpool. The new
test passed 5 full-file and 20 isolated runs and failed 5/5 with the pre-fix ordering. W1
matches the code. Basis `2bd93aeb8886bdf431f8a910555c955e57318934ada8746f484c18746ec6295c`
unchanged; boundary current. Two INFO notes (cross-process "in force" means last applied in that
process; serialised store reads under the lock).

Reviewed content (R3): HEAD `c1d90698f5ac6fd4b6a9c00cd42672ea28a1b259` plus

```
858c1874a647a6fb8334777776c20fb74b8143fb02ae72ddd71b4f217fc803f4  apps/assistant/ai_assistant/config.py
42a818a04095c2a711520abf28848ddec91062f1b843782f299b51dae2deced3  apps/assistant/ai_assistant/model_admin.py
69aba1f0d8f83eae22263c04871c77de698e231969970e8af0a310fd77e0aa11  apps/assistant/ai_assistant/model_admin_store.py
759b92c68ab13093639b2fca89d891abdf725fe70b4cfbfc37c5340dc1acf8c9  apps/assistant/assistant_eval/qualification.py
f4bdef77dd7b55300095e7b159e053ab0a6df5ede2deb03a69df061f496f320e  apps/frontend/src/aiAssistant.ts
b79f249aa2cea4a2bb822ddcbd9a6490a35abc17c5e566e56dcbc9005fba9e92  apps/frontend/src/pages/AiModelManagement.test.tsx
c51fa16304c03c60b2d9903bde690a88b05fe29ce32af93cc47d9fb72318d598  apps/frontend/src/pages/AiModelManagement.tsx
024c5ea990c4dc97dfa27cd6e2182766331c65649f9111f26b815134be4856f7  docs/PROJECT_STATE.md
f32beb79b2ae2f8d5b9ffde390fbcc88485cd39c498c955faf4d8f5d79ef56ca  docs/decisions/DECISION_LOG.md
98b44d63e814ab9ccff97bacb41543c6639cef5066dabaf7f454596d03894411  docs/integration/AI_MODEL_CONFIGURATION.md
57c2180c2a2b2b553422eaad206a1429fc9f454e4ef22bf5a447bf461e78abbd  apps/assistant/tests/test_spending_controls.py
```

This report was added after R3 and changes no reviewed file. `QG VERDICT: PASS`.

## Evidence (author and reviewers)

| Check | Result |
| --- | --- |
| Assistant full suite | 2,566 passed, 1 failed (`test_a_read_only_ledger_fails_closed`: the sandbox runs as root; fails identically on main) |
| `tests/test_spending_controls.py` | 26 passed |
| Frontend full suite / `tsc -b` / build | 1,136 passed / exit 0 / built |
| ruff, ruff format, mypy (assistant) | clean |
| `build_synthetic_boundary.py --check`, `build_synthetic_eligibility.py --check` | current, current |
| `qualification_basis()` HEAD vs tree | identical |
| Secret scan, `check_project_state.py`, `git diff --check` | pass, PASS, clean |
| Hosted CI on `c1d9069` | `HOSTED_CI_NOT_EXECUTED — BILLING/INFRASTRUCTURE BLOCKED`: all 18 jobs in runs 40653175159 and 40653180429 completed within seconds with no runner assigned (`runner_id` 0, no steps, logs 404) |
| Physical MongoDB | NOT RUN (no MongoDB in the cloud session); deferred verification risk for PR #126 |
