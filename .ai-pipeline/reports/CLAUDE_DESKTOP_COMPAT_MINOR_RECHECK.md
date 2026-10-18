# Claude Desktop Compatibility Layer: Independent Minor-Fix Re-Gate

**Verdict: PASS**

Scope: the bounded governance/tooling change (change classes `CI_TOOLING` and
`DOCS_ONLY`) after the authorized remediation of M1 and M2 from
`CLAUDE_DESKTOP_COMPAT_RE_QUALITY_GATE.md`. This verdict covers only the frozen,
uncommitted content identified below. It states governance/publication readiness only.
It makes no claim about product-phase readiness, ACRA/GoldTier readiness or any Live
integration.

## Reviewer independence and boundary

- This reviewer is a fresh Claude Code session. It did not implement or remediate any
  reviewed file and did not write either prior gate report. Implementer and remediation
  claims were treated as input, not proof.
- The canonical workflow was read from the reviewed checkout:
  `.agents/skills/fyp-quality-gate/SKILL.md`.
- This report is the only file this session wrote. Both prior gate reports were read and
  not edited. Python ran with `-B` and `PYTHONDONTWRITEBYTECODE=1`. Ruff ran with
  `--no-cache`.
- No commit, push, PR, merge, branch or worktree mutation happened. Only `git fetch
  origin` touched the network. `.env`, `private/` and sponsor material were not
  accessed. Other worktrees were not touched.

## Frozen reviewed-content identity

| Item | Value |
|---|---|
| Checkout | `C:\Users\shane\Desktop\claude-worktrees\fyp-claude-desktop-compat` |
| Branch | `chore/claude-desktop-compat-20261018` (no upstream) |
| BASE_SHA = HEAD = origin/main | `cc10a2b626ef92d2dd44600d488c1f15cc4f04f8` (confirmed after `git fetch origin`) |
| Content state | Uncommitted: 4 modified tracked files and 6 untracked candidate files. Nothing staged. |
| MANIFEST_SHA256 | `f3319ba16f4d5bb419d81c85287dc347a24ef16003e58d0ed8104ee145303d30` |

The manifest was recomputed before review and again after all checks. Both times it
matched the assigned value. `git status` showed exactly 12 entries: the 10 candidate
paths and the two reviewer-owned prior gate reports. Per-path SHA-256 of raw
working-tree bytes:

```
ee619784f1b74fe2b7363c675ce3b6ee6f55b7a0b02667ec77c79dbf2e7dfb62  .agents/skills/README.md
94c99a0bd9bfed47806723696e8c8a304668e9e9f56a16b7abd3284b1068d16a  .claude/settings.json
94cd528f46e6000c73db780e8bdb8dbc90bc803215839e62a5da7f116237b1ed  .claude/skills/fyp-phase-execution/SKILL.md
008fde2df3dd71701d9e0575b7bc5008a4d08e4e1f6a4ef91da8616811127f18  .claude/skills/fyp-quality-gate/SKILL.md
25392024877fd96018fcf01fea0c7ac9b3e025b15256cd8dde6ddeb9d9bb56f2  .claude/skills/integration-safe-development/SKILL.md
524fef9d1da760fa154931127938daeed004681986e3f1530357b1dc9c78a891  .claude/skills/worktree-task/SKILL.md
3a289de46deee7af1fae6d0d141c2ac7daef7a14c4266333448b89fb3fbeb7f0  .github/workflows/ci.yml
48b59f1d01f89be87bbd4c66d0f0e63dd46a02a930a5c0d1f0dc90be0fbfdbed  .gitignore
d497d6466da0600e4458f4482ef8624092560b7522968f38da181a14be17e9d9  docs/development/TOOLING_AND_MCP.md
a6c9b6dea32c0c20c7e5dbc26145f82a6452f0b85b3190bdfa0629b7d8fecd52  tests/test_claude_skill_pointers.py
```

Compared with the re-gate manifest (`7a8502b1…`), exactly two per-path hashes changed:
`docs/development/TOOLING_AND_MCP.md` and `tests/test_claude_skill_pointers.py`. The
other eight paths match the per-path hashes in the re-gate report byte for byte, so the
re-gate's findings for them carry over unchanged.

## Session capabilities

- Interpreter: the primary checkout's `.venv\Scripts\python.exe` with `-B`. The worktree
  has no `.venv` of its own.
- Hosted GitHub CI is unavailable to this gate and has not run. The GitHub MCP server
  failed to connect in this session.
- No Claude Code instruction-loading probe was re-run. The settings file it covered is
  byte-identical to the re-gated content, and neither changed file affects loading.

## Remediated findings

### M1: resolved

- **Now:** `TOOLING_AND_MCP.md:81-82`: "a stale `AGENTS.md` copy inside an untracked
  `output/` or ignored `tmp/` snapshot loads when Claude reads a file there". This is
  the exact wording the re-gate required.
- **Evidence:** `git check-ignore -v --no-index` reports `tmp/x/AGENTS.md` ignored by
  `.gitignore:50:tmp/`. `output/x/AGENTS.md` and `outputs/x/AGENTS.md` are not ignored.
  `git ls-files output outputs tmp` is empty, so nothing there is tracked. The primary
  checkout's status lists `output/` as untracked. "Untracked `output/`" and "ignored
  `tmp/`" are therefore both accurate.
- **No new defect:** the diff against HEAD changes only that sentence plus line
  wrapping. Added lines are at most 90 columns. The longer lines in the file (lines
  7-11, up to 138 columns) are base content outside the diff. No other statement in the
  section changed meaning.

### M2: resolved

- **Now:** `tests/test_claude_skill_pointers.py:1`: "Claude Code pointers must mirror
  canonical skills; shared settings must not exclude instructions."
- **Evidence:** the docstring now claims exactly what the tests check. Four tests cover
  the pointer set, exact frontmatter, manual-only flags and canonical-reference
  strings. One test asserts that shared `.claude/settings.json` has no top-level
  `claudeMdExcludes`. The docstring no longer claims to guard `AGENTS.md` loading as a
  whole, so it no longer implies coverage of tracked `CLAUDE.md` variants.
- **No new defect:** the test logic matches the re-gate's description (5 tests, the same
  classes and assertions, 96 lines). Ruff check and format pass, so the 103-column
  docstring is within the configured limits. All 5 tests pass.

## Acceptance criteria (whole candidate)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | `AGENTS.md` and `.agents/skills/` stay canonical; `.codex` unchanged; diff limited to the 10 paths; `check_tooling_config` passes | **Met** | `git diff --quiet HEAD -- AGENTS.md .codex` succeeded. Numstat lists only README (+7), `ci.yml` (+1), `.gitignore` (+5) and the TOOLING doc (+34). The other 6 candidates are untracked. `TOOLING_CONFIG=PASS`. |
| 2 | Four pointers mirror canonical metadata, read from the current checkout and add no authority | **Met** | The pointer files are byte-identical to the re-gated content. The drift test passes. |
| 3 | Settings syntax, deny/ask/allow posture and Bash/PowerShell parity | **Met** | `.claude/settings.json` is byte-identical to the re-gated content (`94c99a0b…`). |
| 4 | `.gitignore` covers local Claude state but not shared settings or skills | **Met** | `.gitignore` is byte-identical (`48b59f1d…`). |
| 5 | Drift test is meaningful and wired into CI with a one-line `ci.yml` change | **Met** | `ci.yml` is byte-identical and its numstat is `1 0`. The test passes, and its logic is unchanged from the mutation-tested re-gate version. |
| 6 | Docs are accurate against Claude Code behaviour and FYP governance | **Met** | M1 and M2 are resolved as described above. The README is byte-identical to the re-gated content, which the re-gate found accurate after F2. |
| 7 | No Camunda, plugins, product code or unrelated changes | **Met** | No paths outside the 10 candidates are modified. |

## Findings

No new findings. Nothing remains to fix. The re-gate's non-blocking observations still
apply, because the content they cover is unchanged: only the top-level key is guarded,
working-tree files are CRLF by repository convention, `/private/**` is anchored at the
start directory, Read-deny coverage is limited, the GitHub merge tool name was not
verified live, the pytest allow can run repository test code, and `git stash*` is
denied outright.

## Checks run by this gate (current session, frozen content)

| Check | Result |
|---|---|
| `unittest discover -s tests -p test_claude_skill_pointers.py -v` | PASS (5 tests) |
| `unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture` | PASS (55 tests) |
| `tests.test_check_secrets` / `test_check_tooling_config` / `test_check_policy_authority` / `test_check_external_provider_readiness` | PASS (8 / 11 / 14 / 19 tests) |
| `scripts/check_project_state.py` | PASS (exit 0) |
| `scripts/check_architecture.py` | PASS (exit 0) |
| `scripts/check_tooling_config.py` | PASS (exit 0) |
| `scripts/check_policy_authority.py` | PASS (exit 0) |
| `scripts/check_external_provider_readiness.py` | PASS (exit 0) |
| `scripts/check_secrets.py` | PASS (exit 0) |
| `ruff check --no-cache` / `ruff format --check --no-cache` on the test | PASS / PASS |
| `git diff --check` (tracked) | PASS |
| Whitespace on the 6 untracked candidates (`git diff --no-index --check /dev/null <file>`) | PASS (no warnings) |
| Byte scan of the 9 non-`ci.yml` candidates (BOM, final newline, blank EOF, trailing whitespace, tabs) | PASS. Line endings are consistently CRLF (for example 128/128 in the TOOLING doc and 96/96 in the test). |
| `git check-ignore -v --no-index` for `output/`, `outputs/`, `tmp/` | `tmp/` ignored; `output/` and `outputs/` not ignored |
| `scripts/pre_pr_check.py` | **NOT_EXECUTED**: the content is uncommitted, and this check requires a clean committed state |
| Hosted GitHub CI | **NOT_EXECUTED**: it has not run, and no result is claimed |

## Change declaration

- **Documentation:** `docs/development/TOOLING_AND_MCP.md` (one adjective corrected)
  and the test module docstring. Nothing else changed since the re-gate.
- **Whole candidate:** Claude Code client-side configuration (`.claude/settings.json`,
  `.gitignore`), one CI unittest step, governance docs (`.agents/skills/README.md`, the
  TOOLING doc), four discovery pointers and one test module (5 tests).
- **Unchanged:** API/type, schema, connector, business rule, mapping, application
  auth/security, architecture, provider status and runtime behaviour.

## Git status at verdict

The branch is `chore/claude-desktop-compat-20261018` at `cc10a2b`, with no upstream and
nothing staged or committed. The working tree holds the 10 frozen candidate paths, the
two prior gate reports and this report. Nothing was published.

## Readiness

- **Governance:** all seven acceptance criteria are met for manifest `f3319ba1…`. No
  fixes remain.
- **Before publication:** the owner must authorize a commit. Then
  `scripts/pre_pr_check.py` must pass on the clean committed state, and hosted CI must
  actually run. Any content change after this manifest needs a fresh independent review.
- **Authorization:** commit, push, PR and merge remain unauthorized. Only the repository
  owner merges.
- **Product readiness:** no product-phase or ACRA/GoldTier readiness is stated or
  implied.
