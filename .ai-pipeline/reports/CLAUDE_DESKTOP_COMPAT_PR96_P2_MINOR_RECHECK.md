# Claude Desktop Compatibility Layer: PR #96 P2 Minor-Fix Independent Recheck

**Verdict: PASS**

Scope: the uncommitted correction on top of PR #96 head `0698f4c` after the MF1/MF2
remediation required by `CLAUDE_DESKTOP_COMPAT_PR96_P2_REGATE.md` (PASS WITH MINOR
FIXES, manifest `859146f1…`). Change classes: `CI_TOOLING` + `DOCS_ONLY`. Date:
2026-10-18.

MF1 and MF2 are resolved accurately. The Codex P2
(<https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/96#discussion_r4303815319>)
stays resolved in both shells. No new defect was found.

## Reviewer independence and boundary

- Fresh independent Quality Gate run via `.agents/skills/fyp-quality-gate/SKILL.md`. This
  reviewer did not implement, remediate, or previously gate this content. The
  remediation summary was treated as input and checked against the files and external
  docs.
- Writes: this report only. No commit, push, PR comment/reply/resolve, merge, branch or
  worktree mutation, `.env`, `private/` or sponsor-material access. Permission behavior
  was evaluated without executing any Git mutation (synthetic strings only). The only
  `git branch` invocation was `git branch --show-current`, a read-only listing.

## Frozen reviewed-content identity

| Item | Value |
| --- | --- |
| Checkout | `C:\Users\shane\Desktop\claude-worktrees\fyp-claude-desktop-compat` |
| Branch | `chore/claude-desktop-compat-20261018` |
| HEAD (local) | `0698f4cf6343e31f62761b8de994a362ba22c60a` |
| Remote branch (`git ls-remote`, after fetch) | `0698f4cf6343e31f62761b8de994a362ba22c60a` (unchanged) |
| `origin/main` (fetched) / merge-base | `cc10a2b626ef92d2dd44600d488c1f15cc4f04f8` / same |
| Working-tree delta vs `0698f4c` | 3 modified, 0 staged: `.claude/settings.json`, `docs/development/TOOLING_AND_MCP.md`, `tests/test_claude_skill_pointers.py` (+89/-11). Untracked: the prior re-gate report (history, not reviewed content) |
| MANIFEST_SHA256 (10 paths, raw working-tree bytes, `<sha256>  <path>` LF lines, assigned order) | `e0c60348af01d2c67998f1da778a01f565710647fc2d5c918ec76d43dd2f176e` (matches the assigned value; recomputed at start and before verdict) |

Per-file hashes compared with the re-gate report:

| Path | Re-gate (`859146f1…`) | This recheck | Changed |
| --- | --- | --- | --- |
| `.claude/settings.json` | `f52f8de1…b8732` | `ea50ac5e…1d760d5` | yes |
| `docs/development/TOOLING_AND_MCP.md` | `d5526e3d…24133` | `d0418396…caef49` | yes |
| `tests/test_claude_skill_pointers.py` | `f5254364…d06` | `c024d30b…aab35` | yes |
| Other 7 manifest paths | no diff vs `0698f4c` | no diff vs `0698f4c` (`git diff --quiet HEAD`; EOL-normalized blobs equal `HEAD`; `ci.yml` raw bytes equal its blob) | no |

Only the three expected paths differ.

## Remediation delta verified

- `ask` grew from 64 to 66 entries: `Bash(git filter-branch*)` and
  `PowerShell(git filter-branch*)`. The full `ask` delta vs `0698f4c` (+24/−6) is the
  re-gate's reviewed set plus these two. `deny` (29) and `allow` (12) are byte-identical
  to `0698f4c`.
- `BRANCH_AND_WORKTREE_ASK` gains `"git filter-branch*"` (20 patterns).
- The doc sentence now reads that the settings ask "before every `git branch` command,
  including bare listing and read-only flags such as `--show-current` (use
  `git rev-parse` for read-only branch lookups)", and names `git filter-branch` among the
  covered commands. The re-gate's "with arguments" wording is gone (`git grep`).

## External authority consulted (fetched 2026-10-18)

- `code.claude.com/docs/en/permissions`: rules are evaluated deny, then ask, then allow,
  and the first match decides. A trailing `*` with a space before it "also matches the
  bare command" when it is the only wildcard. PowerShell rules use the same shape and
  match case-insensitively. Deny/ask rules are not a security boundary
  (`git -C . push` is not matched by `Bash(git push *)`).
- `git-scm.com/docs/git-branch`: bare `git branch`, `--list`, `-a/-r`,
  `--show-current` and the filter/format flags only list. Every form that changes refs
  or config takes arguments.
- `git-scm.com/docs/git-filter-branch`: titled "Rewrite branches". It rewrites the
  positive refs named on the command line and stores the originals under
  `refs/original/`. No read-only mode is documented, so asking on every invocation is
  correct.

## Non-executing permission evaluation

A scratch evaluator outside the repository implements the documented rules above
(deny→ask→allow, `*` as any text, the trailing-` *` bare-command rule, case-insensitive
PowerShell). It classified 32 synthetic commands against the frozen settings and the
`0698f4c` settings for `Bash(...)`, `PowerShell(...)` and upper-cased PowerShell input.

| Command | `0698f4c` | Frozen | Note |
| --- | --- | --- | --- |
| `git branch` (bare), `git branch --show-current`, `-a`, `--list feat*` | unlisted | ASK (all 3 variants) | MF1: matches the new doc text |
| `git rev-parse --abbrev-ref HEAD` | unlisted | unlisted | MF1: the documented read-only alternative does not prompt |
| `git filter-branch --tree-filter true -- --all`, `git filter-branch -f --msg-filter cat HEAD` | unlisted | ASK | MF2 resolved |
| P2 examples `git branch feature`, `git branch -m old new`, `git worktree move a b`; also `lock`, `repair`, `update-ref`, `symbolic-ref`, `pull` | unlisted | ASK | P2 still resolved |
| `git branch -D x`, `git branch --delete-merged x`, `commit`, `push origin x`, `reset --soft` | ASK | ASK | unchanged |
| `push --force`, `push origin +x`, `reset --hard`, `stash`, `clean -fd`, `add -A`, `gh pr merge 96`, `gh api …/pulls/96/merge` | DENY | DENY | deny precedence and owner-only merge preserved |
| `git fetch origin main:main`, `git -C . branch -D x` | unlisted | unlisted | disclosed as not covered |
| `git status`, `git worktree list` | Bash unlisted / PowerShell ALLOW | same | pre-existing PowerShell-only allows, unchanged |

Apart from the two pre-existing PowerShell-only allows, Bash and PowerShell results are
identical for every command.

## Acceptance criteria

| Criterion | Result |
| --- | --- |
| MF1 resolved accurately | MET. The doc says every `git branch` command prompts, including bare listing and `--show-current`, and points to `git rev-parse` for read-only lookups. This matches the documented trailing-` *` rule and the evaluation. |
| MF2 resolved (owner option (a)) | MET. `git filter-branch*` is in `ask` for both shells and in `BRANCH_AND_WORKTREE_ASK`; the doc names it as covered. `git filter-branch*` cannot collide with any other built-in git command. |
| P2 still resolved in both shells | MET. Every mutating `git branch` form and worktree add/move/remove/prune/lock/unlock/repair ask in Bash and PowerShell. |
| Deny precedence preserved | MET. Deny list byte-identical to `0698f4c`; deny is evaluated first, so the broader ask rules do not weaken hard reset, force push, `+refspec`, stash, clean or broad staging. |
| Owner-only merge denial preserved | MET. `gh pr merge*`, `gh api *merge*` (both shells) and `mcp__plugin_github_github__merge_pull_request` remain in deny. |
| Best-effort vs security-boundary wording intact | MET. The "other spellings … not covered" list (including `git -C`, `sh -c`, `git fetch` local refspecs), "best-effort guardrails, not a security boundary", the sandbox-on-Windows note, the deferred PreToolUse hook, and "do not replace `AGENTS.md`, independent review, or owner-only merge" are all retained. |
| Tests meaningful | MET. With `PowerShell(git filter-branch*)` or `Bash(git filter-branch*)` removed from a scratch copy of the settings, both `test_branch_and_worktree_mutations_ask_in_both_shells` and `test_deny_and_ask_rules_have_shell_parity` fail. The tests check that patterns are present, not how they match, which is acceptable for a config-shape guard. |
| No new defect / nothing else changed | MET. Only the three expected paths changed; no staged paths; remote branch unchanged; no other tracked doc claims branch/worktree ask coverage. |

## Findings

None. No critical, high, minor, security, contract or false-success defect.

Observations (non-blocking, carried forward, no action required for this content):

- PR #96 body line 12 still summarizes ask rules loosely. The PR body is outside the
  frozen content and belongs to an owner-authorized publication run.
- `git bisect` and `git config branch.<name>.*` remain uncovered and are not claimed as
  covered. The doc's `checkout … am` list of "commands that move a branch or discard
  work" is now accompanied by explicit naming of the other covered commands, so it no
  longer implies coverage it lacks.
- In `TOOLING_AND_MCP.md:100-103` the lines wrap unevenly ("They are best-effort" ends
  a short line). This is cosmetic only.

## Checks run by this gate (current session, frozen content)

Interpreter `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm\.venv\Scripts\python.exe -B`,
`PYTHONDONTWRITEBYTECODE=1`, run from the reviewed checkout root.

| Check | Result |
| --- | --- |
| `unittest discover -s tests -p test_claude_skill_pointers.py -v` | PASS (7 tests) |
| `unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture` | PASS (55 tests) |
| `unittest tests.test_check_secrets tests.test_check_tooling_config tests.test_check_policy_authority tests.test_check_external_provider_readiness` | PASS (52 tests) |
| `scripts/check_project_state.py` | PASS (exit 0) |
| `scripts/check_architecture.py` | PASS (exit 0) |
| `scripts/check_tooling_config.py` | PASS (exit 0) |
| `scripts/check_policy_authority.py` | PASS (exit 0) |
| `scripts/check_external_provider_readiness.py` | PASS (exit 0) |
| `scripts/check_secrets.py` | PASS (exit 0) |
| `ruff check --no-cache` / `ruff format --check --no-cache` on the test | PASS / PASS |
| `mypy` on the test (cache in scratch, outside the repository) | PASS |
| `git diff --check` and `git diff --check 0698f4c` | PASS (exit 0) |
| Test mutation check (filter-branch removed per shell, scratch settings copy) | Run; tests fail as expected |
| Non-executing permission evaluation (32 synthetic commands × 3 shell variants, old vs new) | Run; results above |
| `scripts/pre_pr_check.py` | NOT_EXECUTED: requires a clean committed state; the correction is intentionally uncommitted |
| Hosted CI for `0698f4c` | NOT_EXECUTED: both runs had zero steps (billing refusal); never a PASS. No CI exists for the correction. |

## Change declaration

Changed: shared Claude Code permission configuration (`ask` rules in both shells),
tooling documentation, and one tooling test. Not changed: API/type, schema, connector,
configuration names, business rule, mapping, auth/security boundary (rules remain
best-effort, not a security boundary), architecture, provider status, application
runtime behavior, deny and allow lists, CI workflow.

## Git status at verdict

Branch `chore/claude-desktop-compat-20261018`, HEAD = remote = `0698f4c`, base
`origin/main` `cc10a2b`. Working tree: the 3 reviewed modifications, the prior re-gate
report (untracked) and this report (new, untracked). Nothing staged, committed or pushed
by this gate. The P2 thread was not replied to or resolved.

## Readiness

Governance readiness only; no product-phase claim. The frozen content (manifest
`e0c60348…`) passes and is ready for an owner-authorized publication run. That run
still needs a committed state, `scripts/pre_pr_check.py` on the clean tree, explicit
owner authorization for commit and push, and owner-run hosted CI once billing is
restored. Any change to the reviewed content requires a fresh review. Agents do not
merge.
