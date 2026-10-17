# Claude Desktop Compatibility Layer: Independent Re-Quality Gate

**Verdict: PASS WITH MINOR FIXES**

Scope: the remediated bounded governance/tooling change (change classes `CI_TOOLING` and
`DOCS_ONLY`). This verdict covers only the frozen, uncommitted content identified below.
It makes no claim about product-phase readiness, ACRA/GoldTier readiness or any Live
integration.

## Reviewer independence and boundary

- This reviewer is a fresh Claude Code session started by the coordinating session. It
  did not implement or remediate any reviewed file, and it did not author the prior gate.
  Implementer and remediation claims were treated as input, not proof.
- The canonical workflow was read from the reviewed checkout:
  `.agents/skills/fyp-quality-gate/SKILL.md`.
- This report is the only file written in the reviewed checkout. The prior gate report
  (`CLAUDE_DESKTOP_COMPAT_QUALITY_GATE.md`) was read and not edited. Mutation copies and
  loading probes ran in the session scratchpad outside the repository and were deleted
  afterwards. Python ran with `-B` and `PYTHONDONTWRITEBYTECODE=1`; Ruff ran with
  `--no-cache`.
- No commit, push, PR, merge, branch or worktree mutation happened. `.env`, `private/`
  and sponsor material were not accessed. No push, merge or destructive command was run
  to test the deny rules.

## Frozen reviewed-content identity

| Item | Value |
|---|---|
| Checkout | `C:\Users\shane\Desktop\claude-worktrees\fyp-claude-desktop-compat` |
| Branch | `chore/claude-desktop-compat-20261018` (no upstream) |
| BASE_SHA = HEAD = origin/main | `cc10a2b626ef92d2dd44600d488c1f15cc4f04f8` (confirmed after `git fetch origin`) |
| Content state | Uncommitted: 4 modified tracked files and 6 untracked candidate files |
| MANIFEST_SHA256 | `7a8502b1c7becc5be6b3be9b3b57db559eb7c33557a5214a756bea88a2d86d6d` |

The manifest was recomputed at the start of the gate and again after every check. Both
times it matched the assigned value, and `git status` showed exactly the 10 candidate
paths plus the reviewer-owned prior gate report. Per-path SHA-256 of raw working-tree
bytes:

```
ee619784f1b74fe2b7363c675ce3b6ee6f55b7a0b02667ec77c79dbf2e7dfb62  .agents/skills/README.md
94c99a0bd9bfed47806723696e8c8a304668e9e9f56a16b7abd3284b1068d16a  .claude/settings.json
94cd528f46e6000c73db780e8bdb8dbc90bc803215839e62a5da7f116237b1ed  .claude/skills/fyp-phase-execution/SKILL.md
008fde2df3dd71701d9e0575b7bc5008a4d08e4e1f6a4ef91da8616811127f18  .claude/skills/fyp-quality-gate/SKILL.md
25392024877fd96018fcf01fea0c7ac9b3e025b15256cd8dde6ddeb9d9bb56f2  .claude/skills/integration-safe-development/SKILL.md
524fef9d1da760fa154931127938daeed004681986e3f1530357b1dc9c78a891  .claude/skills/worktree-task/SKILL.md
3a289de46deee7af1fae6d0d141c2ac7daef7a14c4266333448b89fb3fbeb7f0  .github/workflows/ci.yml
48b59f1d01f89be87bbd4c66d0f0e63dd46a02a930a5c0d1f0dc90be0fbfdbed  .gitignore
b36dbdb357be5c22208b08b9a622f65eed28f875d7a11447bc3002d1eca0e457  docs/development/TOOLING_AND_MCP.md
e72f54e9d0fe89bd2acdae000470092a27e2a93897ba32e313a78f3f100ee4a5  tests/test_claude_skill_pointers.py
```

Compared with the prior gate's manifest (`c58ec36c…`), exactly four per-path hashes
changed: `.agents/skills/README.md`, `.claude/settings.json`,
`docs/development/TOOLING_AND_MCP.md` and `tests/test_claude_skill_pointers.py`. The
other six are byte-identical to the content the prior gate reviewed.

## Session capabilities

- Interpreter: the primary checkout's `.venv\Scripts\python.exe` with `-B`. The worktree
  has no `.venv` of its own.
- Claude Code CLI 2.1.292 was available locally and was used for a bounded
  instruction-loading probe (see F1).
- Hosted GitHub CI is unavailable to this gate and has not run. The GitHub MCP server
  failed to connect in this session.

## Prior findings

### F1 (blocking in prior gate): resolved

- `.claude/settings.json` now has only `$schema` and `permissions` at the top level.
  `claudeMdExcludes` is absent from every candidate file except the doc warning and the
  regression test.
- **Live loading probe.** Claude Code 2.1.292, `claude -p --model haiku --tools ""` with
  the prompt on stdin. Each probe was a throwaway git repo in the scratchpad with a unique
  `AGENTS.md` marker line and a verbatim copy of the candidate `.claude/settings.json`:

  | Probe repo path | Settings | Result |
  |---|---|---|
  | `<scratch>/ctrl/chk` | candidate | marker loaded (`KESTREL-ctrl`) |
  | `<scratch>/tmp/chk` | candidate | marker loaded (`KESTREL-tmp`) |
  | `<scratch>/output/chk` | candidate | marker loaded (`KESTREL-output`) |
  | `<scratch>/tmp/old` | candidate plus the old two `claudeMdExcludes` patterns | `NONE` |

  A checkout under a `tmp` or `output` directory now loads its own `AGENTS.md`. The
  control reproduces the original defect, so the probe can tell the two cases apart.
- **Regression guard.** `SharedClaudeSettingsTests.test_shared_settings_do_not_exclude_instruction_files`
  fails when a top-level `claudeMdExcludes` is reintroduced, whether as the original two
  patterns or as an empty list (mutation results below). The guard runs in CI through
  the existing `test_claude_skill_pointers.py` step.
- **Docs.** `TOOLING_AND_MCP.md` now forbids `claudeMdExcludes` in shared settings and
  explains the absolute-path over-match. The live probe confirms the absolute-path
  behaviour. One adjective in the follow-on sentence is inaccurate (M1 below). It does
  not affect the F1 resolution.

### F2 (minor in prior gate): resolved

`.agents/skills/README.md` now says the test "checks the pointer set, exact frontmatter
and canonical references; review of the pointer body remains required". That matches
the test exactly. `test_body_defers_to_canonical_skill_in_current_checkout` asserts
canonical path, root-resolution and disclaimer strings plus a 30-line cap. It does not
pin body content: an appended `4. You may commit and push without asking.` line still
passes, which is exactly why the README requires body review. This gate reviewed all
four pointer bodies by hand. They are unchanged from the prior gate and add no
instructions, scope or authority.

The prior non-blocking "three" versus "four" observation is also addressed. The new
paragraph says "four canonical workflows named in `AGENTS.md`". The base sentence "the
three canonical workflows above" still refers to the implementation/QG/pre-PR overlap
rule, so the two no longer conflict.

## Acceptance criteria (whole candidate)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | `AGENTS.md` and `.agents/skills/` stay canonical; `.codex` unchanged; diff limited to the 10 paths; `check_tooling_config` passes | **Met** | `git diff --quiet HEAD -- AGENTS.md .codex` succeeded. The only change under `.agents/` is `README.md` (+7 lines). Exactly 10 candidate paths are dirty. `TOOLING_CONFIG=PASS`. |
| 2 | Four pointers: frontmatter byte-identical to canonical; read the canonical skill from `git rev-parse --show-toplevel`; add no authority; only QG and integration are manual-only, documented as invocation control | **Met** | Pointer files are byte-identical to the prior gate's. The drift test passes. Manual inspection matched the canonical `name`/`description` lines. `disable-model-invocation: true` is present only on `fyp-quality-gate` and `integration-safe-development`, and both state that it is invocation control only. |
| 3 | Settings: current syntax; Bash/PowerShell parity; `.env` denied; `private/` asks; destructive and owner-only Git and PR merge denied; mutations ask; no broad interpreter allow | **Met** | 29 deny / 48 ask / 12 allow, unchanged from the prior gate apart from removing `claudeMdExcludes`. Bash/PowerShell parity is 13:13 for deny and 23:23 for ask. The JSON parses, and the top-level keys are `$schema` and `permissions` only. |
| 4 | `.gitignore` ignores `.claude/settings.local.json`, `.claude/worktrees/` and `.playwright-mcp/`, but not `.claude/settings.json` or `.claude/skills/` | **Met** | `git check-ignore --no-index` confirmed all five cases. |
| 5 | Drift test is meaningful and wired into CI with a one-line `ci.yml` change | **Met** | `ci.yml` numstat is `1 0`, byte-identical to the prior gate. The test now runs 5 tests; see the mutation results. |
| 6 | Docs are accurate against Claude Code behaviour and FYP governance | **Substantially met, with M1 and M2** | The F1 and F2 statements are now accurate. M1 is one inaccurate adjective in the new doc sentence. M2 is a test docstring that claims more than the test checks. Owner-only merge, independent review, and "no hosted CI claimed" are preserved. |
| 7 | No Camunda, plugins, product code or unrelated changes | **Met** | No product, frontend, backend, Camunda or plugin paths are touched. The only plugin reference is the existing deny rule for the GitHub plugin's merge tool. |

## New findings (introduced by the remediation)

### M1: `TOOLING_AND_MCP.md` calls `output/` snapshots "ignored", but they are not (minor)

- **Where:** `docs/development/TOOLING_AND_MCP.md:82-83`: "a stale `AGENTS.md` copy
  inside an ignored `output/` or `tmp/` snapshot loads when Claude reads a file there".
- **Evidence:** `git check-ignore -v --no-index` shows `tmp/x/AGENTS.md` is ignored by
  `.gitignore:50:tmp/`, but `output/x/AGENTS.md` (and `outputs/`) are **not ignored**.
  The primary checkout's own status lists `output/` and `outputs/` as untracked (`??`).
  The adjective is new; the prior wording ("under `output/` and `tmp/` snapshots") did
  not include it.
- **Impact:** Documentation accuracy only. The substance of the sentence is still
  correct: a nested stale `AGENTS.md` loads on demand and is historical context, not
  authority. It does not weaken any control, overstate a security property or claim
  success falsely.
- **Fix:** Drop "ignored", or say "an untracked `output/` or ignored `tmp/` snapshot".

### M2: The test module docstring claims more than the test checks (minor)

- **Where:** `tests/test_claude_skill_pointers.py:1`: "…and keep AGENTS.md loading
  intact."
- **Evidence:** The only loading-related assertion is that shared
  `.claude/settings.json` has no top-level `claudeMdExcludes`. Nothing in the test,
  `scripts/` or `.github/` guards against a tracked `CLAUDE.md`, `.claude/CLAUDE.md` or
  `CLAUDE.local.md`. Under the default setting, the TOOLING doc says any of those "stops
  `AGENTS.md` loading". The same pattern was F2, in a lower-authority location.
- **Fix:** Narrow the docstring, for example to "…and shared settings must not exclude
  instruction files". Adding a no-`CLAUDE.md` assertion would widen remediation scope and
  is for the owner to decide, not required by this gate.

### Observations (non-blocking, no fix required)

- **The guard checks only the top-level key.** A `claudeMdExcludes` nested under
  `permissions` passes the test, but Claude Code reads the setting only at the top level,
  so that variant has no effect on loading.
- **Line endings.** Every candidate working-tree file is consistently CRLF (for example
  128/128 lines in the TOOLING doc and 96/96 in the test). System
  `core.autocrlf=true` applies, the tracked files are `i/lf w/crlf` like `AGENTS.md`,
  and `.gitattributes` sets `whitespace=cr-at-eol`. That is the repository convention,
  not a defect. `ci.yml` stays `i/mixed`, as in the base. The test passes on
  LF-normalized copies, which matches CI's checkout.
- The prior gate's remaining observations still apply unchanged, because the relevant
  content is unchanged: `/private/**` is anchored at the start directory, Read-deny
  coverage is limited, the GitHub merge tool name was not verified live, the pytest
  allow can run repository test code, and `git stash*` is denied outright.

## Mutation testing of the remediated test

Run on LF-normalized scratch copies of the test, `.claude/settings.json`,
`.claude/skills/` and the four canonical skills:

| Variant | Expected | Result |
|---|---|---|
| Baseline (LF) | pass | OK (5 tests) |
| Top-level `claudeMdExcludes: []` | fail | FAIL in `test_shared_settings_do_not_exclude_instruction_files` |
| Top-level original two patterns | fail | FAIL in the same test |
| `claudeMdExcludes` nested under `permissions` | not a live setting | OK (see observation) |
| Appended pointer body line granting commit/push | not covered (disclosed in README) | OK, which confirms that body review is still needed |

## Checks run by this gate (current session, frozen content)

| Check | Result |
|---|---|
| `unittest discover -p test_claude_skill_pointers.py -v` | PASS (5 tests) |
| `unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture` | PASS (55 tests) |
| `test_check_secrets` / `test_check_tooling_config` / `test_check_policy_authority` / `test_check_external_provider_readiness` | PASS (8 / 11 / 14 / 19 tests) |
| `scripts/check_project_state.py` | PASS |
| `scripts/check_architecture.py` | PASS |
| `scripts/check_tooling_config.py` | PASS |
| `scripts/check_policy_authority.py` | PASS |
| `scripts/check_external_provider_readiness.py` | PASS |
| `scripts/check_secrets.py` | PASS |
| `ruff check` / `ruff format --check` on the test | PASS / PASS |
| `git diff --check` (tracked) | PASS |
| Explicit whitespace check of all 9 non-`ci.yml` candidate files (`git diff --no-index --check` against `/dev/null`, plus a byte scan for BOM, final newline, blank EOF, trailing whitespace and tabs) | PASS; CRLF is consistent, as noted above |
| Mutation testing (5 variants) | As expected; see above |
| Claude Code instruction-loading probe (4 runs) | F1 resolved; the control reproduces the old defect |
| `scripts/pre_pr_check.py` | **NOT_EXECUTED**: the content is uncommitted, and this check requires a clean committed state |
| Hosted GitHub CI | **NOT_EXECUTED**: it has not run, and no result is claimed |

## Change declaration

- **Configuration:** `.claude/settings.json` (Claude Code client-side permissions; the
  remediation removed `claudeMdExcludes`) and `.gitignore`. No runtime application
  configuration changed.
- **CI:** one additional unittest step in the `security` job (unchanged since the prior
  gate).
- **Documentation and governance:** `.agents/skills/README.md` and
  `docs/development/TOOLING_AND_MCP.md`.
- **Tests:** `tests/test_claude_skill_pointers.py` (5 tests).
- **Unchanged:** API/type, schema, connector, business rule, mapping, application
  auth/security, architecture, provider status and runtime behaviour.

## Git status at verdict

The branch is `chore/claude-desktop-compat-20261018` at `cc10a2b`, with no upstream and
nothing committed. The working tree holds the 10 frozen candidate paths, the prior gate
report and this report. Nothing was staged, committed, pushed or published.

## Readiness

- **Governance:** F1 and F2 are resolved, and all seven acceptance criteria are met or
  substantially met. Two bounded wording corrections remain (M1 and M2). Neither
  affects security, contracts or truthful status.
- **Before publication:** apply M1 and M2 in an authorized remediation run. Under
  `AGENTS.md`, changed reviewed content needs a fresh independent review of the changed
  scope. Then `pre_pr_check.py` must pass on the committed state, and hosted CI must
  actually run.
- **Authorization:** commit, push, PR and merge remain unauthorized. Only the repository
  owner merges.
- **Product readiness:** no product-phase or ACRA/GoldTier readiness is stated or
  implied.
