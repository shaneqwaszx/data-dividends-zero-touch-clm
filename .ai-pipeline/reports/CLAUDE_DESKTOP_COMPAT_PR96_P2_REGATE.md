# Claude Desktop Compatibility Layer: PR #96 P2 Remediation Independent Re-Gate

**Verdict: PASS WITH MINOR FIXES**

Scope: the uncommitted post-publication correction on top of PR #96 head `0698f4c` that
remediates the unresolved Codex P2 "Prompt for every branch and worktree mutation"
(<https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/96#discussion_r4303815319>,
`.claude/settings.json:50`). Change classes: `CI_TOOLING` + `DOCS_ONLY`. Date: 2026-10-18.

The P2 is resolved in both shells for every mutating form of the `git branch` and
`git worktree` command sets it cites. Two bounded documentation-accuracy corrections
remain (MF1, MF2); neither weakens a deny rule, owner-only merge, or the best-effort
disclosure.

## Reviewer independence and boundary

- Fresh independent Quality Gate run via `.agents/skills/fyp-quality-gate/SKILL.md`. This
  reviewer did not implement, remediate, or previously gate this content. Implementer
  rationale was treated as input and checked independently; one claim in it is wrong
  (see MF1).
- Writes: this report only. No commit, push, PR comment/reply/resolve, merge, branch or
  worktree mutation, `.env`, `private/` or sponsor-material access. Permission behavior
  was evaluated without executing any Git mutation (synthetic strings only).

## Frozen reviewed-content identity

| Item | Value |
| --- | --- |
| Checkout | `C:\Users\shane\Desktop\claude-worktrees\fyp-claude-desktop-compat` |
| Branch | `chore/claude-desktop-compat-20261018` |
| HEAD (local) | `0698f4cf6343e31f62761b8de994a362ba22c60a` |
| Remote branch (`git ls-remote`, after fetch) | `0698f4cf6343e31f62761b8de994a362ba22c60a` (unchanged) |
| `origin/main` (fetched) / merge-base | `cc10a2b626ef92d2dd44600d488c1f15cc4f04f8` / same |
| Working-tree delta vs `0698f4c` | 3 modified, 0 staged, 0 untracked: `.claude/settings.json`, `docs/development/TOOLING_AND_MCP.md`, `tests/test_claude_skill_pointers.py` (+85/-11) |
| MANIFEST_SHA256 (10 paths, raw working-tree bytes, `<sha256>  <path>` LF lines, assigned order) | `859146f1627f17922f9f9348f8a8a127a9c3ac14316bf911d8beebea807c9eb2` (matches assigned value; recomputed at start and before verdict) |

Per-file hashes of the three changed paths: `.claude/settings.json`
`f52f8de1…b8732`, `docs/development/TOOLING_AND_MCP.md` `d5526e3d…24133`,
`tests/test_claude_skill_pointers.py` `f5254364…d06`. The other seven manifest paths
have no diff against `0698f4c`.

PR #96 state (GitHub API, read-only): open, not merged, head `0698f4c`, base `main`.
The P2 thread is a single unreplied comment by `chatgpt-codex-connector[bot]` on
commit `0698f4c`.

## Session capabilities

`git`/`gh` (read-only API), repository `.venv` Python with `-B`, ruff, mypy, WebFetch for
official docs. No Claude Code permission engine was exercised against real commands;
matching was evaluated against the documented semantics (below). Hosted CI not
re-run.

## External authority consulted (fetched 2026-10-18)

- `code.claude.com/docs/en/permissions`:
  - Order is deny, then ask, then allow; first match wins; specificity does not reorder.
  - A trailing `*` preceded by a space, when it is the only wildcard, "also matches the
    bare command" (`Bash(ls *)` matches `ls`). The space is part of the rule
    (`Bash(ls*)` also matches `lsof`).
  - Deny/ask rules apply when any subcommand of a compound command matches, including
    in auto mode; listed wrappers (`timeout`, `nice`, …) are stripped first.
  - Rules match command text and are explicitly not a security boundary
    (`git -C . push`, `git -c … push`, `sh -c` are not stopped by `Bash(git push *)`).
  - PowerShell rules use the same shape; matching is case-insensitive; the AST is
    split on `|`, `;`, `&&`, `||`.
- `git-scm.com/docs/git-branch`: every mutating form (create, `-f`, `--track`,
  `-m/-M`, `-c/-C`, `-d/-D`, `-u`/`--set-upstream-to`, `--unset-upstream`,
  `--edit-description`, `--delete-merged`) takes arguments; bare `git branch` only lists.
- `git-scm.com/docs/git-worktree`: subcommands are add, list, lock, move, prune, remove,
  repair, unlock; only `list` (and `prune -n`) is read-only.

## Non-executing permission evaluation

A scratch evaluator (outside the repository) implemented the documented matching rules
above and classified 62 synthetic commands against both the frozen settings and the
`0698f4c` settings, for `Bash(...)`, `PowerShell(...)`, and upper-cased PowerShell input.

| Command group | `0698f4c` | Frozen correction | Shell parity |
| --- | --- | --- | --- |
| P2 examples `git branch feature`, `git branch -m old new`, `git worktree move old new` | unlisted | ASK | Bash = PowerShell |
| All 16 mutating `git branch` forms from the git synopsis | 3 of 16 ASK (deletes only) | 16 of 16 ASK | yes |
| `git worktree` add/move/remove/prune/lock/unlock/repair | 3 of 7 ASK | 7 of 7 ASK | yes |
| `git update-ref`, `git symbolic-ref`, `git pull`, `git cherry-pick`, `git revert`, `git am` | unlisted | ASK | yes |
| `checkout -b`, `switch -c`, `restore`, `merge`, `rebase`, `reset --soft`, `commit` | ASK | ASK | yes |
| `git reset --hard`, `push --force`, `push origin +x`, `stash`, `clean`, `add -A`, `gh pr merge`, `gh api …/merge` | DENY | DENY (deny precedes ask) | yes |
| `git push origin --delete x` (remote branch delete) | ASK | ASK | yes |
| Bare `git branch`, `git branch --show-current`, `git branch -a`, `git symbolic-ref --short HEAD`, `git worktree prune -n` | unlisted | ASK (fail-safe over-prompt) | yes |
| `git rev-parse --abbrev-ref HEAD` | unlisted | unlisted | yes |
| `git fetch origin main:main`, `git -C . branch -D x` | unlisted | unlisted (disclosed as not covered) | yes |
| `git filter-branch … -- --all` | unlisted | unlisted (not disclosed; MF2) | yes |

The only Bash/PowerShell differences are pre-existing, unchanged PowerShell-only allow
rules for read-only `git status/diff/log/worktree list`; deny and ask sets have exact
parity (also enforced by the new test).

## Acceptance criteria

| Criterion | Result |
| --- | --- |
| P2 resolved for both shells | MET. `Bash(git branch *)`/`PowerShell(git branch *)` cover every mutating `git branch` form, and worktree move/lock/unlock/repair are added beside add/remove/prune. |
| Deny precedence preserved | MET. Deny list byte-identical to `0698f4c` (29 entries); documented deny→ask→allow order keeps hard reset, force push, `+refspec`, stash, clean, broad staging denied though broader ask rules now also match some of them. |
| Owner-only merge denial preserved | MET. `gh pr merge*`, `gh api *merge*` (both shells) and `mcp__plugin_github_github__merge_pull_request` unchanged in deny. |
| Best-effort vs security-boundary distinction preserved | MET. The "other spellings … not covered", "best-effort guardrails, not a security boundary", sandbox-on-Windows and deferred-hook sentences are retained; `git fetch` local refspecs are added to the not-covered list. |
| Scope of additions justified | MET. `update-ref`/`symbolic-ref` write branch refs or HEAD directly; `pull`/`cherry-pick`/`revert`/`am` advance the current branch. All fall within the pre-existing documented promise ("asks before … branch/worktree mutation") the P2 holds the rules to. None loosens a rule; deny and allow are unchanged. Not scope creep. |
| No remaining gap the docs claim is covered | SUBSTANTIALLY MET. The enumerated commands are all covered in both shells. The phrase "the commands that move a branch or discard work (…)" reads as exhaustive but omits `git filter-branch` (MF2). |
| Docs accurate against current official docs | SUBSTANTIALLY MET. Wildcard/parity/best-effort statements match code.claude.com. "every `git branch` command with arguments" understates coverage because bare `git branch` also prompts (MF1). |
| Tests meaningful | MET. `test_branch_and_worktree_mutations_ask_in_both_shells` fails against the `0698f4c` settings (11 patterns missing per shell, verified by loading the test helpers against the old file). `test_deny_and_ask_rules_have_shell_parity` guards future one-shell edits. Limitation: tests assert pattern presence, not matching semantics; acceptable for a config-shape guard. |
| Nothing else changed | MET. Exactly 3 files differ from `0698f4c`; no untracked or staged paths; remote branch unchanged; no other doc claims ask-rule coverage (`git grep` for branch/worktree-mutation wording found only AGENTS.md process text and planner history). |

## Findings

No critical, high, security, contract or false-success defect.

### MF1 (minor, docs accuracy): bare `git branch` prompts but the doc implies it does not

`docs/development/TOOLING_AND_MCP.md:94-96` says the settings ask "before every
`git branch` command with arguments (read-only listing flags such as `--show-current`
also prompt; `git rev-parse` does not)". Per the official rule "A `*` at the end, with a
space before it, also matches the bare command", `Bash(git branch *)` and
`PowerShell(git branch *)` also match bare `git branch`. The implementer rationale ("bare
`git branch` … do not [prompt]") is incorrect. Over-prompting is fail-safe, but the text
misdescribes current behavior. Required fix: state that every `git branch` invocation
prompts, including bare listing (for example, "asks before every `git branch` command,
including bare listing and read-only flags such as `--show-current`; use `git rev-parse`
for read-only branch lookups").

### MF2 (minor, docs/rules consistency): `git filter-branch` rewrites branches without a prompt

The doc lists "the commands that move a branch or discard work (`checkout`, `switch`,
`restore`, `merge`, `rebase`, `reset`, `pull`, `cherry-pick`, `revert`, `am`)" as a
definite set. `git filter-branch` rewrites `refs/heads/*` and matches no rule in either
shell (`git branch *` does not match `git filter-branch …`). Required fix, either:
(a) add `Bash(git filter-branch*)` and `PowerShell(git filter-branch*)` to `ask` and to
`BRANCH_AND_WORKTREE_ASK`, or (b) make the doc say it lists the covered commands and
name `git filter-branch` (or "other ref-rewriting commands") among those not covered.
Either is bounded and does not affect deny or merge rules.

### Observations (non-blocking, no action required for this content)

- PR #96 body line 12 summarizes ask rules as "commit/push/merge/rebase/branch/worktree
  mutations". The PR body is outside the frozen content; any update belongs to an
  owner-authorized publication run.
- Other commands that touch HEAD or branch metadata without writing branch refs in the
  sense documented (`git bisect`, which detaches HEAD; `git config branch.<name>.*`) are
  not covered and not claimed covered. Leaving them out is a reasonable boundary.
- Pre-existing PowerShell-only allow rules for read-only Git are unchanged and outside
  this remediation.

## Checks run by this gate (current session, frozen content)

Interpreter `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm\.venv\Scripts\python.exe -B`,
`PYTHONDONTWRITEBYTECODE=1`, run from the checkout root.

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
| `mypy` on the test (cache in scratch, outside repo) | PASS |
| `git diff --check 0698f4c` and `git diff --check` | PASS (no untracked paths to check separately) |
| Non-executing permission evaluation (62 synthetic commands × 3 shell variants, old vs new) | Run; results above |
| `scripts/pre_pr_check.py` | NOT_EXECUTED: requires a clean committed state; the correction is intentionally uncommitted |
| Hosted CI for `0698f4c` | NOT_EXECUTED: both runs had zero steps (billing refusal); never a PASS. No CI exists for the correction. |

## Change declaration

Changed: shared Claude Code permission configuration (`ask` rules in both shells),
tooling documentation, and one tooling test. Not changed: API/type, schema, connector,
business rule, mapping, auth/security boundary (rules remain best-effort, not a security
boundary), architecture, provider status, application runtime behavior, deny and allow
lists, CI workflow.

## Git status at verdict

Branch `chore/claude-desktop-compat-20261018`, HEAD = remote = `0698f4c`, base
`origin/main` `cc10a2b`. Working tree: the 3 reviewed modifications plus this report
(new, untracked). Nothing staged, committed or pushed by this gate. The P2 thread was not
replied to or resolved.

## Readiness

Governance readiness only; no product-phase claim. The correction resolves the P2 for
both shells and is ready for publication after MF1 and MF2 are applied by a separately
assigned remediation run and a fresh independent recheck confirms the changed content.
Publication still requires a committed state, `scripts/pre_pr_check.py`, explicit owner
authorization for commit and push, and owner-run hosted CI once billing is restored.
Agents do not merge.
