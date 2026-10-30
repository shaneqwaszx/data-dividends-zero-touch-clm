# D-104 Independent Re-Quality Gate (provider-neutral D-095 eligibility and data access policy)

Date: 2026-10-30. Reviewer: a fresh, independent Quality Gate agent. It did not author or
remediate the reviewed content. Read-only review. This file is the only file written.
Nothing was committed, staged, stashed, reset or pushed, and no branch changed. No `.env`
file was read. No network or paid call was made. The primary checkout's
`apps/assistant/data` was not touched.

## Frozen identity

| Item | Value |
| --- | --- |
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\assistant-data-access-policy-20261030` |
| Branch | `feat/assistant-data-access-policy` |
| HEAD = base = `origin/main` | `0c6a6325e8ad9bdc650c72824124a4d0f2fc863f` (all changes uncommitted) |
| Reviewed paths | 16. This is the sorted union of `git diff --name-only` and `git ls-files --others --exclude-standard`, excluding `D104_QUALITY_GATE.md` and this report. It is 13 tracked files plus 3 new: `data_access.py`, `test_data_access_policy.py` and `D104_DATA_ACCESS_POLICY.md` |
| Content-id at start | `68848ab26a648d14ad9c2a1fc8c2861c2280053e64a00fb9d2cd246715895942` (matches the assignment) |
| Content-id at end | `68848ab26a648d14ad9c2a1fc8c2861c2280053e64a00fb9d2cd246715895942` (unchanged) |

## Checks run (this session, on the frozen content)

| Check | Result |
| --- | --- |
| Focused pytest: `test_data_access_policy`, `test_synthetic_eligibility`, `test_remote_test`, `test_claude_runtime`, `test_claude_console`, `test_claude_hr_spending`, `test_claude_multi_turn`, `test_model_management`, `test_spending_controls`, `test_d098_recovery`, `test_guardrails`, `test_guardrails_dropped`, `test_warm_up_security`, `test_ai_assistant`, `test_knowledge_review_safety` | 863 tests, 0 failures, 0 errors, 0 skipped (junitxml in the scratchpad). `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1` |
| Full assistant suite | Not run by this gate. I reused the implementer's full-run evidence only as context (2893 passed, 14 `Errno 24` environmental failures). This gate did not verify it |
| `scripts/build_synthetic_boundary.py --check` (from `apps/assistant`) | `synthetic boundary is current`, exit 0. The new string constants add no D-094 vocabulary |
| `qualification_basis()`, candidate | `0d90e3e148f4dd1404af0ad93b4aa89752779399cfab9844dc9ed7dcb61ad277`. Matches the implementer's claim |
| `qualification_basis()`, `origin/main` (exported with `git archive` to the scratchpad) | `65f22e46c509b2f4e0540f8412e9940e5c1d9c49c85e6eb28c94f0e0b1479328` |
| `ruff check --no-cache`, `ruff format --check --no-cache` (ai_assistant and the new test) | All checks passed; 58 files already formatted |
| `mypy ai_assistant` (cache in the scratchpad) | No issues in 46 source files |
| Frontend `npx tsc -b --pretty false` | Exit 0 |
| Frontend `npx vitest run src/pages/AiModelManagement.test.tsx` | 98 passed |
| `git diff --check`; trailing whitespace in the untracked files; `--stat` against `--ignore-cr-at-eol` | Clean; clean; identical (no EOL churn) |
| Test deletion or weakening against `origin/main` | No tracked backend test changed. The frontend test diff removes only one import line, which was widened. No `it(`/`test(`/`def test_` was removed |
| Probe P1 (scratchpad): Claude catalogue scope with Claude ready and no OpenRouter configuration | `shared_mode` true, GPT-OSS `mode` false, Claude entries `scope = APPROVED_SYNTHETIC_CASE`; `data_access.verification_mode(...,"anthropic") = D-095` (see L1) |
| Probe P2 (scratchpad): no model management, `LLM_BASE_URL=http://10.0.0.5:8080/v1`, non-synthetic (`LIVE`) case | View: `status=not_managed`, `active_class=it_configured`, `active_restricted=false`, IT row `{restricted:false, locked:true}`. The RM chat returned `answered_by=model` and the baseline was called once (see M1) |

## Review against the owner's scope

### Part 1, A1

- **`shared_mode` is a strict subset of `remote_test.readiness`.** `shared_mode` is the
  D-095 flag plus readiness's first four checks, as the same expressions: the D-094
  decision, `llm_enabled`, D-091/D-092, the loopback backend and local origins.
  `mode = shared_mode and readiness is None`, so GPT-OSS's effective mode is unchanged.
  `remote_test.py` itself is untouched. Verified.
- **Claude.** `development_mode = shared_mode`, with no OpenRouter condition. It is used by
  `remote_gate` (main.py:711-712), by `_ready` (anthropic_runtime.py:686) and by the
  adapter-level re-check (anthropic_runtime.py:656). If Claude's own readiness fails while
  `shared_mode` is true:
  - the constructor refuses to build (`ProfileConfigError`, tested);
  - at call time, `_ready` re-checks `readiness`, the key, the ledger, the call limit and
    the preflight under its lock (anthropic_runtime.py:704-740) before anything is sent.
  The eligibility check and its single-use ticket (`admitted` pops) are still required, and
  absent a ticket the D-094 `check_messages` applies. Verified by inspection and tests.
- **No path sends without a ticket or the D-094 text check.**
  - Every chat path uses `selector.current()` (main.py:916-996), which wraps the model.
  - `SyntheticOnlyModel._admit` runs on `complete` and on first `stream` iteration.
  - `warm` is a no-op.
  - `/brief` warm-up only reaches the wrapper (tested).
  - `model_admin` makes no direct `complete` or `stream` call.
- **D-094 still refuses `v1`.** Tested. D-095 admits the genuine live Garden prompt for both
  providers, and the same tampered prompt is refused for both (tested).
- **Decision log.** Only the D-095 V1 and D-099 C7 amendment paragraphs were added. D-104
  is new.

### Part 2, policy

- **Classification** (`data_access.model_class`):
  - RemoteTestModel is `openrouter` and ClaudeTestModel is `anthropic`, checked by type
    before the URL.
  - BoundedPromptModel and the baseline are classified by `base_url` through
    `is_local_model_url`, which accepts literal loopback only. A non-loopback URL, a DNS
    `localhost` or `base_url=None` gives `it_configured`, which fails closed.
  - A `None` model is not wrapped, and the chat falls back.
- **Fail-closed paths.** With managed mode on:
  - an unreadable or invalid row becomes `None`, which restricts the model and refuses
    `PUT` (409);
  - a store exception in `_current` keeps the old model, which is still wrapped by
    `current()`.
- **Changes.**
  - Origin is required, and the requester has an admin dependency.
  - `recheck` runs inside `change_lock`.
  - CAS runs in the route and again in the store inside `BEGIN IMMEDIATE`.
  - `restrict_external:false` is refused (409) and audited.
  - Widening without `confirm_widen` is refused (400). The request is strict JSON
    (`extra="forbid"`, `StrictBool`).
  - The policy persists across restarts (tested).
- **L4 atomicity.** The policy and the `applied` audit row are written in one
  `BEGIN IMMEDIATE` transaction. If the audit write fails, the change rolls back (tested).
- **Audit retention.** `applied` rows are written directly. `record()` never prunes
  `CHANGE_OUTCOMES`, so applied rows are retained. Refused rows keep the existing bounded
  pruning.
- **L5.** There are tests for Claude active with local restricted, `/brief` under
  restriction, unmanaged local, and a four-thread store-level CAS race.
- **`data_access.py` in `BASIS_FILES`.** It is appropriate: it gates the prompts a
  restricted model receives, so any change to it should invalidate qualifications. The
  basis moves from `65f22e46c509…` to `0d90e3e148f4…`. Every earlier qualification,
  including Claude Balanced, therefore becomes out of date through the existing mechanism,
  and no history is modified. Verified by inspection and computation.

### Part 3

- **L1.** `_REMOTE_REFUSALS` includes the four policy notices (tested).
- **L2.** Claude tiles depend only on `budget.claude.configured`.
- **L3.** There is a separate count and `DATA_ACCESS_RATE_LIMITED` (tested).
- **L4 and L5.** As above.

## Findings

### Critical / High

None.

### Medium

**M1. An IT-configured remote endpoint is unrestricted without model management, while the
API, page and docs say it is locked to synthetic cases.**

Locations:
- `apps/assistant/ai_assistant/model_admin.py:431` (`if self.store is None ... return active`)
- `apps/assistant/ai_assistant/data_access.py:183,188` (`"restricted": managed`, `"locked": True`)
- `apps/frontend/src/pages/AiModelManagement.tsx:1321` (unconditional banner: "A model IT
  configured on another machine is treated the same way")
- `docs/decisions/DECISION_LOG.md:1634` (Z2: restricted "whatever the stored policy says";
  it "is never treated as local")
- `docs/integration/AI_MODEL_CONFIGURATION.md:499` ("Checked, locked | Treated like the
  external models")

Failure scenario (reproduced, probe P2):
1. IT runs the service without a profiles file (the D-093 fixed model) and sets
   `AI_ASSISTANT_LLM_BASE_URL=http://10.0.0.5:8080/v1`, which is not on this machine.
2. An RM asks about a real (non-synthetic) authorised case. The full case facts go to the
   remote endpoint (`answered_by=model`).
3. Meanwhile `GET /data-access` reports that class as `locked: true` with `restricted:
   false`, and HR's page banner says that the model is treated like the external models.

The owner's criterion was: "Only actual trusted local (literal loopback) endpoints count as
internal; an arbitrary remote IT-configured endpoint must not be local". In this
configuration, the remote endpoint gets exactly the local default treatment. Z4 and §14
contain a contradicting "Without model management nothing changes" sentence. No test covers
unmanaged mode with a non-loopback URL; `test_without_model_management_nothing_changes`
uses the loopback default.

Pre-existing main behaviour is the same, but this candidate newly asserts a lock that does
not hold. This is a security-relevant, untruthful status about a data-egress control, so it
cannot be treated as a minor fix.

Bounded remediation: the owner chooses one of two options.
- (a) Wrap `it_configured` regardless of the store, and add a test for unmanaged mode with
  a non-loopback URL. Local stays unchanged.
- (b) Explicitly accept unmanaged behaviour as out of scope. The API must then not report
  `locked` for it. The banner, Z2 and the §14 row must state the unmanaged exception
  truthfully, and a test must pin it.

### Low

**L1. The Claude catalogue scope is still coupled to OpenRouter readiness.**

Location: `apps/assistant/ai_assistant/model_catalog.py:364` (unchanged file:
`elif synthetic_eligibility.mode(settings)`).

With Claude ready and D-095 on but no OpenRouter attestations or endpoint (probe P1), the
Claude profiles show `scope = APPROVED_SYNTHETIC_CASE`, which is D-094 wording. The runtime
admits D-095 cases, and the new Data Access section on the same page says "Verification in
force: D-095". The display is conservative (it understates scope), but it contradicts A1's
"Claude's D-095 mode must not depend on OpenRouter" on a user-visible surface.

Fix: use `synthetic_eligibility.shared_mode` for the Claude entries' scope, and add a test.
`model_catalog.py` is in the basis, so the basis would move again.

**L2. IT notice and label wording claims location.**

Location: `apps/assistant/ai_assistant/data_access.py:56-72`;
`AiModelManagement.tsx` `CLASS_LABEL.it_configured`.

Any non-literal-loopback URL is `it_configured`, including `http://localhost:…` or this
machine's own LAN address. The RM-facing notice "The model IT configured is not on this
machine" can therefore be false. The classification itself is correct and fails closed;
only the wording is wrong.

Suggested fix: "not on a literal loopback address".

## Verdict

**FAIL.**

Part 1 (A1), Part 3 (L1 to L5) and Part 4 (offline proof) are verified. Most of Part 2 is
verified. No Critical or High defect was found. However, M1 is a security-relevant
untruthful status: real case data goes to a remote IT endpoint while the server reports it
locked to synthetic cases, against an explicit owner criterion. The skill does not allow
that under "PASS WITH MINOR FIXES".

Remediation is bounded to M1, with L1 and L2 recommended in the same pass. A recheck should
review the corrected delta, recompute `qualification_basis()` and re-run
`test_data_access_policy`, `test_model_management`, `test_claude_console`,
`build_synthetic_boundary.py --check` and the page vitest. Other valid evidence from this
gate can be reused.

## Readiness

- The candidate is not ready for commit or publication. It needs M1 remediation (or an
  explicit owner decision under option (b)) and a fresh independent recheck of the changed
  content.
- After that, publication still requires owner commit authorisation, `pre_pr_check.py` on
  the committed state, and owner merge. Hosted CI is not evidenced here.
- No Live, Sandbox or provider-status claim is made.
- Claude Balanced's existing qualification is out of date under the candidate basis
  `0d90e3e1…`. A new, separately approved paid qualification would be required, and none
  was performed.
