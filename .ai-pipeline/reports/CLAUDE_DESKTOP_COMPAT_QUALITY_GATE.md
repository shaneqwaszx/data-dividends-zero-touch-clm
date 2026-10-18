# Claude Desktop Compatibility Layer: Independent Quality Gate

**Verdict: FAIL**

Scope: a bounded governance/tooling change (change classes `CI_TOOLING` and `DOCS_ONLY`).
This verdict covers only the frozen, uncommitted content identified below. It says nothing
about product-phase readiness, ACRA/GoldTier readiness or any Live-integration claim.

## Reviewer independence and boundary

- The reviewer is a separate Claude Code session started by the coordinating session. It
  did not implement or edit any reviewed file. The implementer's self-checks were treated
  as input, not as proof.
- The canonical workflow was read from the reviewed checkout:
  `.agents/skills/fyp-quality-gate/SKILL.md`.
- This report is the only file written in the reviewed checkout. Probes and mutation
  copies ran in the session scratchpad outside the repository and were deleted
  afterwards. Python ran with `-B` and `PYTHONDONTWRITEBYTECODE=1`, and Ruff ran with
  `--no-cache`.
- No commit, push, PR, merge, branch or worktree mutation happened. `.env`, `private/`
  and sponsor material were not accessed. No push, merge or destructive command was run
  to test the deny rules.

## Frozen reviewed-content identity

| Item | Value |
|---|---|
| Checkout | `C:\Users\shane\Desktop\claude-worktrees\fyp-claude-desktop-compat` |
| Branch | `chore/claude-desktop-compat-20261018` (no upstream) |
| BASE_SHA = HEAD = origin/main | `cc10a2b626ef92d2dd44600d488c1f15cc4f04f8` |
| Content state | Uncommitted: 4 modified tracked files and 6 untracked files |
| MANIFEST_SHA256 | `c58ec36c80fe0c6c23812ff0f00a01469cb87275425927897af95364687ba682` |

The manifest was recomputed at the start of the gate and again after every check. Both
times it matched the assigned value, and `git status` showed exactly the 10 frozen
paths. Per-path SHA-256 values of the raw working-tree bytes:

```
4397357c27c6706a0fa3fcabd7e370bc5f550bd39a18e47ee0faac2a2bc9f7dc  .agents/skills/README.md
59b6591cf27d6c647350de77066d089fe374bca6a820a4e77a570d3622b3b82a  .claude/settings.json
94cd528f46e6000c73db780e8bdb8dbc90bc803215839e62a5da7f116237b1ed  .claude/skills/fyp-phase-execution/SKILL.md
008fde2df3dd71701d9e0575b7bc5008a4d08e4e1f6a4ef91da8616811127f18  .claude/skills/fyp-quality-gate/SKILL.md
25392024877fd96018fcf01fea0c7ac9b3e025b15256cd8dde6ddeb9d9bb56f2  .claude/skills/integration-safe-development/SKILL.md
524fef9d1da760fa154931127938daeed004681986e3f1530357b1dc9c78a891  .claude/skills/worktree-task/SKILL.md
3a289de46deee7af1fae6d0d141c2ac7daef7a14c4266333448b89fb3fbeb7f0  .github/workflows/ci.yml
48b59f1d01f89be87bbd4c66d0f0e63dd46a02a930a5c0d1f0dc90be0fbfdbed  .gitignore
a75ec6344b9960f615b355f9e7fa82b8c87729d9bb02bad1babb5f8a21c57d38  docs/development/TOOLING_AND_MCP.md
dbdff6d39c606884948570670eb2c2a5e2d16925da44f58a9f75322b6284ca87  tests/test_claude_skill_pointers.py
```

## Session capabilities

- Interpreter: the primary checkout's `.venv\Scripts\python.exe`, Python 3.12.10, run
  with `-B`. The worktree has no `.venv` of its own.
- Claude Code CLI 2.1.292 was available locally and was used for one bounded probe of
  instruction loading (see F1).
- Current Anthropic documentation was fetched from code.claude.com: `memory`,
  `permissions`, `skills` and `sandboxing`.
- Hosted GitHub CI is unavailable to this gate and has not run. The GitHub MCP server
  failed to connect in this session.

## Acceptance criteria

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | `AGENTS.md` and `.agents/skills/` stay canonical; the diff is limited to the 10 paths; `.codex` is unchanged; `check_tooling_config` passes | **Met** | `git diff --quiet HEAD -- AGENTS.md .codex` succeeded. No file under `.agents/skills/` other than `README.md` changed. Exactly 10 paths are dirty. `TOOLING_CONFIG=PASS`. |
| 2 | Four pointers: `name`/`description` lines byte-identical to canonical; read the canonical skill from `git rev-parse --show-toplevel`; add no authority; only QG and integration set `disable-model-invocation: true`, documented as invocation control | **Met** (but see F2 on how far the test proves "no authority") | Frontmatter matched canonical byte-for-byte (drift test plus mutations). Bodies are 15–22 lines, defer to `AGENTS.md` and the canonical skill, and do not use the primary checkout. The QG and integration pointers state that the flag does not confer independence or publication authority. The skills docs confirm the flag removes the description from context and allows only `/name` invocation. |
| 3 | `settings.json` uses current syntax; Bash/PowerShell parity for deny and ask; `.env` denied; `private/` asks; owner-only/destructive Git and PR merge denied; commit/push/branch/worktree/PR mutations ask; no broad interpreter allow; limitations stated honestly | **Partially met: blocked by F1** | Permission rules are valid under the current docs (`PowerShell(...)` uses the same rule shape as Bash; precedence is deny, then ask, then allow; MCP rule is `mcp__<server>__<tool>`; `/path` anchors at the primary working directory). Deny and ask lists have 14:14 and 25:25 Bash/PowerShell parity. Allow rules are limited to `dev_context.py`, `.venv` pytest/ruff/mypy and read-only `git status`/`diff`/`log`/`worktree list`. The stated limitations match the docs: text matching, `git -C`/`sh -c` not covered, no native-Windows sandbox, PreToolUse hook deferred. However, `claudeMdExcludes` uses current syntax but its semantics are unsafe (F1). |
| 4 | `.gitignore` ignores `.claude/settings.local.json`, `.claude/worktrees/` and `.playwright-mcp/`, but not `.claude/settings.json` or `.claude/skills/` | **Met** | `git check-ignore -v --no-index` confirmed all five cases. |
| 5 | The drift test is meaningful and wired into the CI security job with a one-line `ci.yml` change | **Met** (see F2) | `numstat` for `ci.yml` is `1 0`. The base file has mixed line endings (174 CRLF of 191 lines; index `i/mixed`), and the inserted line is LF like its neighbours in the `security` job (`ubuntu-latest`). The mutation results are below. |
| 6 | Docs are accurate against current Anthropic docs and FYP governance | **Not met: F1** | Most statements check out (see "Documentation accuracy" below). The `claudeMdExcludes` sentence is materially incomplete because it omits the over-match proven in F1. Owner-only merge is preserved. Hosted CI is not claimed. |
| 7 | No Camunda, plugins, product code or unrelated changes | **Met** | Diff is exactly the 10 paths. The only plugin reference is a **deny** rule for the GitHub plugin's merge tool. Camunda appears only in docs prose saying it stays Codex-only. |

## Findings

### F1: `claudeMdExcludes` silently suppresses the canonical `AGENTS.md` for checkouts under any `tmp` or `output` directory (blocking)

- **Where:** `.claude/settings.json` (`"**/output/**/AGENTS.md"`, `"**/tmp/**/AGENTS.md"`)
  and the matching sentence in `docs/development/TOOLING_AND_MCP.md`.
- **Defect:** The current memory docs say `claudeMdExcludes` patterns are "matched against
  absolute file paths using glob syntax" and that they apply to `AGENTS.md`. These
  patterns therefore match more than the repository's stale `output/` and `tmp/`
  snapshots. They also match the root `AGENTS.md`, and every nested one, of any checkout
  whose absolute path contains a directory named `tmp` or `output`. Examples are a
  `/tmp/<clone>` review clone on Linux or macOS, or a worktree created under the repo's
  own `tmp/` (where this project keeps evidence and `main-*` baseline snapshots). In
  those sessions Claude Code starts without the controlling governance instructions, and
  nothing indicates it. That is a fail-open loss of the primary instruction control.
- **Reproduction:** Claude Code 2.1.292, `claude -p --model haiku --tools ""`, using
  throwaway git repos in the scratchpad. Each repo held only an `AGENTS.md` marker line
  and a `.claude/settings.json` with the same two patterns.
  - `<scratch>/ctrl/probe` with the excludes: the marker loaded (`ZEBRA-ctrl`).
  - `<scratch>/tmp/probe` with the excludes: `NONE`. The root `AGENTS.md` was **not**
    loaded.
  - `<scratch>/tmp/probe2` without the excludes: the marker loaded. This shows the exclude
    causes the loss; the path alone does not.
  - The Windows `...\AppData\Local\Temp\...` scratch path did not match, because `Temp`
    is not `tmp`. The usual owner layout (`C:\Users\...\Desktop\...`) is therefore
    unaffected today, but the configuration is shared and committed.
- **Docs impact:** `TOOLING_AND_MCP.md` says the setting "skips stale `AGENTS.md` copies
  under `output/` and `tmp/` snapshots". It does not disclose that it can also exclude
  the live checkout's own `AGENTS.md`, so criterion 6 is not met for this statement.
- **Why FAIL rather than a minor fix:** The canonical workflow allows minor fixes only
  for non-security, non-false-success corrections. This defect weakens the governance
  and security instruction channel in a fail-open way, and the accompanying doc
  statement overstates how safe the setting is.
- **Remediation direction (not applied):** Remove `claudeMdExcludes` from the shared
  settings and document the trade-off: a stale nested `AGENTS.md` loads only when Claude
  reads a file inside an ignored snapshot. Alternatively, move exact absolute-path
  excludes to the ignored `.claude/settings.local.json`. Any replacement must be shown not
  to match a checkout root. A probe like the one above, or a test, should cover a
  checkout path that contains `tmp` and `output`.

### F2: The README overstates what the drift test proves (minor)

- **Where:** `.agents/skills/README.md`, in the added paragraph: "…and adds no
  instructions or authority; `tests/test_claude_skill_pointers.py` checks this."
- **Evidence (mutation testing):** The test file and copies of `.agents/skills` and
  `.claude/skills` were run in the scratchpad. 12 variants ran: one baseline and 11
  mutations.
  - **The test caught 10 mutations:**
    - a reworded pointer description
    - a changed canonical description
    - `disable-model-invocation` removed from the QG pointer
    - `disable-model-invocation` added to the phase pointer
    - an added `allowed-tools` frontmatter line
    - a fifth pointer directory
    - an extra file in a pointer directory
    - a pointer switched to the primary checkout
    - a wrong canonical path
    - a pointer padded past 30 lines
  - **The test missed 1 mutation:** a short added body line, `4. You may commit and push without asking.`
  - **The baseline and an LF-only conversion passed as expected.** This shows the test
    works on CI's LF checkout.
- **Assessment:** The test is meaningful for metadata and structure drift, which is the
  main risk. Because the exact frontmatter equality blocks extra frontmatter keys such as
  `allowed-tools`, it already closes the most dangerous authority-adding route. It does
  not prove a body "adds no instructions or authority". Either narrow the README wording
  or pin each pointer body to an expected template.

### Observations (non-blocking, no fix required by this gate)

- **"three" versus "four" workflows.** `.agents/skills/README.md` already says
  "overlap the three canonical workflows above", meaning implementation, QG and pre-PR.
  The new paragraph says "four canonical workflows above". `AGENTS.md` names four,
  counting `worktree-task`. This is consistent with `AGENTS.md` but slightly inconsistent
  within the README.
- **`Read(/private/**)` and `Edit(/private/**)` anchor at the session's primary working
  directory.** This is documented behaviour. A session started in a subdirectory such as
  `apps/backend` would not cover the root `private/`. Sessions normally start at the
  root.
- **Read deny does not cover every process.** `Read(**/.env)` also applies to recognized
  Bash file commands such as `cat`, `head` and `tail`, and to redirection targets. It does
  not apply to arbitrary scripts or recursive `grep`. The doc's "scripts that open files
  themselves" wording covers this adequately.
- **The GitHub merge tool name was not verified live.**
  `mcp__plugin_github_github__merge_pull_request` follows the documented plugin-scoped
  form, `mcp__plugin_<plugin>_<server>__<tool>`. It could not be checked against a live
  tool list because the GitHub MCP server failed to connect in this session. The
  `gh pr merge*` and `gh api *merge*` deny rules still apply.
- **The pytest allow can run arbitrary repository test code.** The
  `.venv/Scripts/python.exe -m pytest *` allow rule is scoped to the project interpreter
  and module, so it is not a broad interpreter allow. It can still run any test code in
  the repository. This is accepted as a normal development allowance.
- **`git stash*` is denied outright, including the read-only `git stash list`.** This is
  conservative and consistent with `AGENTS.md`.

## Documentation accuracy

Each statement was checked against the code.claude.com page fetched on 2026-10-18.

- **Correct:**
  - Root `AGENTS.md` loads at session start, and a nested one loads when Claude reads a
    file in that subdirectory. This happens only when no `CLAUDE.md`,
    `.claude/CLAUDE.md` or `CLAUDE.local.md` exists at or above the working directory
    (memory docs, default "Project instructions" setting).
  - Any of those three files stops `AGENTS.md` from loading under the default setting.
  - Claude Code does not read `.agents/`. The skills docs list only `.claude/skills`, and
    the primary checkout, which has no `.claude/skills`, exposes no `fyp-*` skills in this
    session.
  - `disable-model-invocation` behaves as documented.
  - Rules match command text, and `git -C` and `sh -c` are not covered (permissions,
    "What a Bash rule doesn't match").
  - The sandbox does not run on native Windows (sandboxing docs).
  - A PreToolUse hook is the documented enforcement path, and it is stated as deferred.
- **Consistent but not explicitly documented:** "a session moved there later does not
  load the root file until it restarts". This follows from the documented "at session
  start" loading.
- **Incorrect or incomplete:** the `claudeMdExcludes` sentence (F1).
- **FYP governance:** The new docs keep owner-only merge and independent review, claim no
  hosted-CI result, and say they do not replace `AGENTS.md`.

## Checks run by this gate (current session, frozen content)

| Check | Result |
|---|---|
| `unittest discover -p test_claude_skill_pointers.py -v` | PASS (4 tests) |
| `unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture` | PASS (55 tests) |
| `test_check_secrets` / `test_check_tooling_config` / `test_check_policy_authority` / `test_check_external_provider_readiness` | PASS (8 / 11 / 14 / 19 tests) |
| `scripts/check_project_state.py` | PASS |
| `scripts/check_architecture.py` | PASS |
| `scripts/check_tooling_config.py` | PASS |
| `scripts/check_policy_authority.py` | PASS |
| `scripts/check_external_provider_readiness.py` | PASS |
| `scripts/check_secrets.py` (scans tracked and non-ignored untracked files) | PASS |
| `ruff check` / `ruff format --check` on the new test | PASS / PASS |
| `ruff check scripts` | 15 findings, all pre-existing (no file under `scripts/` changed) |
| `git diff --check` (tracked) | PASS |
| Explicit whitespace check of the 6 untracked files and 4 modified files (`git diff --no-index --check` plus a byte scan for trailing whitespace, tabs, final newline, blank EOF and BOM) | PASS |
| Drift-test mutation testing (12 variants: 1 baseline, 11 mutations) | 10 of 11 mutations caught; see F2 |
| Claude Code instruction-loading probe (3 runs) | F1 reproduced |
| `scripts/pre_pr_check.py` | **NOT_EXECUTED**: the content is uncommitted, and this check requires a clean committed state |
| Hosted GitHub CI | **NOT_EXECUTED**: it has not run, and no result is claimed |

## Change declaration

- **Configuration:** `.claude/settings.json` (Claude Code client-side permissions and
  `claudeMdExcludes`) and `.gitignore` changed. Neither affects runtime application
  configuration.
- **CI:** one additional unittest step in the `security` job.
- **Documentation and governance:** `.agents/skills/README.md` and
  `docs/development/TOOLING_AND_MCP.md`.
- **Unchanged:** API/type, schema, connector, business rule, mapping, application
  auth/security, architecture, provider status and runtime behaviour. The
  `claudeMdExcludes` defect affects agent instruction loading only, not the product.

## Git status at verdict

The branch is `chore/claude-desktop-compat-20261018` at `cc10a2b`, with no upstream and
nothing committed. The working tree holds the 10 frozen paths plus this report. Nothing
was staged, committed, pushed or published.

## Readiness

- **Governance and publication:** not ready. F1 must be remediated in a separate
  remediation run. That run should also address F2, or explicitly accept it. The changed
  content then needs a fresh independent Quality Gate.
- **Before publication:** `pre_pr_check.py` must pass on the committed state, and hosted
  CI must run.
- **Authorization:** commit, push, PR and merge remain unauthorized. Only the repository
  owner merges.
- **Product readiness:** no product-phase or ACRA/GoldTier readiness is stated or
  implied.
