---
name: integration-safe-development
description: "Use when starting or modifying a feature branch, preparing a pull request, syncing with main, resolving merge conflicts, integrating another developer's changes, or assessing whether repository work is safe to merge."
---

# Integration-Safe Development

Keep feature work bounded to its intended delta and prove it is based on the latest
`origin/main`. This skill does not authorize branch creation, commits, pushes, merges,
rebases, resets, cleanup, or pull-request completion when the task has not authorized
those actions.

Follow the mandatory context-loading order in `AGENTS.md`, then read the assigned
planner/task and `docs/development/BRANCH_MERGE_PROTOCOL.md`.
`docs/PROJECT_CONTEXT.md` is additional context only when the task needs it. Before PR
readiness, also read `references/PRE_PR_CHECKLIST.md`.

## Stage 0 — Inspect repository

Run:

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin
git rev-parse origin/main
git log --oneline --decorate -10
```

Record existing staged, tracked, and untracked work. Never destroy or move existing work.
If a command would exceed the user's Git authorization, stop and report the required
action.

## Stage 1 — Establish baseline

Record `BASE_SHA`, `FEATURE_BRANCH`, and `HEAD_SHA`. Confirm the branch began at current
`origin/main`. If implementation has not begun and the branch is stale, update or
recreate it only with explicit authorization. If implementation exists, preserve it;
do not reset, rebase, or recreate the branch to hide drift.

## Stage 2 — Scope map

Before editing, identify exact expected files, shared interfaces, hotspot files, tests
protecting existing behavior, and likely overlap with main. Create the smallest plan.
Treat `App.tsx`, `api.ts`, `types.ts`, backend `main.py`/`composition.py`, CI, README, and
dependency lockfiles as hotspots. Change one only when the delta cannot be isolated
cleanly elsewhere.

## Stage 3 — Implementation

Implement only the assigned scope. Prefer small modules/components and existing
provider/service boundaries. Do not add a duplicate implementation merely to avoid
understanding the current owner. Preserve current main behavior unless the assigned
requirement explicitly supersedes it.

## Stage 4 — Local verification

Run focused tests first, then applicable repository-defined backend tests, frontend
tests, typecheck, lint, contract validation, security checks, and build. Read the
current-main CI definition plus package/tool configuration for exact commands. Never
invent a command or report an unexecuted check.

Run whitespace/hygiene checks across tracked changes and every task-owned new file.
Plain `git diff --check` does not inspect untracked Markdown. Derive test inventory from
the current owned suites and record counts only as revision-specific evidence.

## Stage 5 — Main-drift check

Run:

```powershell
git fetch origin
git rev-parse origin/main
git merge-base HEAD origin/main
git log --oneline HEAD..origin/main
```

If the final command lists commits, integration is not finished.

## Stage 6 — Integrate latest main

When authorized, merge `origin/main` into the feature branch with
`git merge origin/main`. Do not rebase a shared/pushed branch or auto-resolve conflicts.

For each conflict, establish main intent and feature intent, preserve newer main
security/API/business/regression behavior, and reapply the smallest feature delta.
Preserve tests from both sides unless proven obsolete. If intent is unclear, stop with
the conflict unresolved.

After resolution, inspect:

```powershell
git status
git diff --check
git diff --cached
git diff origin/main...HEAD
```

Follow the protocol's special guidance for frontend, API/type, composition, lockfile,
CI, and documentation conflicts. Never select a lockfile side before establishing
whether dependency manifests intentionally changed.

## Stage 7 — Regression verification

Run focused conflict-area tests first, then every applicable broad repository check.
Verify that merged main behavior and tests did not disappear.

## Stage 8 — Pre-PR audit

Confirm all intended and supporting feature work is committed. Run
`git status --short`; if it reports staged, unstaged, or untracked files, stop and
classify them before continuing. Do not run the checker expecting dirty work to receive
PASS. Once the working tree and index are clean, run `python scripts/pre_pr_check.py`,
then complete `references/PRE_PR_CHECKLIST.md`. Review:

```powershell
git status --short
git diff --stat origin/main...HEAD
git diff --name-status origin/main...HEAD
git log --oneline origin/main..HEAD
```

Classify every file `INTENDED`, `SUPPORTING`, or `UNEXPECTED`. If an unexpected change
belongs to this task and can be safely reversed, remove it; otherwise preserve it and
stop for owner guidance. A checker PASS proves only its listed deterministic checks; it
does not prove semantic merge safety. Do not claim `MERGE SAFE` while any required
check failed, was skipped, or origin/main remains ahead.

## Stage 9 — Publication after exact independent PASS

Publication requires both exact independent `PASS` on frozen content and explicit
task/owner authorization for the external actions. `PASS WITH MINOR FIXES` requires
remediation and an independent recheck to `PASS` before publication. Use a separate
publication role when available.

1. Compare the current implementation/instruction paths and diff/tree identity with the
   reviewer's frozen-content record. If reviewed content changed, return it to review.
2. Stage only specific reviewed task-owned paths plus the assigned independent report.
   Inspect `git diff --cached`, staged whitespace and file classification before
   committing.
3. Create the authorized descriptive commit, fetch `origin`, and assess latest-main
   drift. Integrate only understood, explicitly authorized changes; never rebase shared
   history or guess through a conflict. If integration changes reviewed content, obtain
   a fresh independent recheck before publication continues.
4. Rerun affected checks after any integration and reach a clean-tree
   `scripts/pre_pr_check.py` result before push.
5. Push the authorized branch, verify local/remote SHA identity, and create or update the
   PR against `main`. Never bypass an approval prompt and never merge the PR.
6. Observe applicable push and `pull_request` workflow runs. Record repository/PR,
   head/base, event, actual checkout SHA/tree when available, run/attempt and relevant job
   conclusions. A PR-only query is not proof of push CI, and one passing run does not
   excuse another failing applicable run. Report pending CI as in progress and do not
   promise unattended monitoring.

## Stage 10 — Handoff

Report feature branch, `BASE_SHA`, latest `origin/main` SHA, `HEAD_SHA`, whether main was
merged after development, files and hotspots changed, API/schema/config changes, exact
tests and results, limitations, conflict resolutions, remaining integration risks, and
a recommended PR title.

When publication occurred, also report the commit, remote branch/SHA identity, PR, each
applicable CI event/run/attempt and its current conclusion.

Distinguish `OBSERVED`, `INFERRED`, and `ASSUMED`. No normal feature-development agent
merges the PR.

## Stop conditions

Stop rather than guess when conflict intent is ambiguous, an unexpected worktree could
be overwritten, a contract change lacks authority, required main integration is not
authorized, or a required check cannot be run. Do not work around these states with a
force push, shared-branch rebase, `git clean`, `git reset --hard`, broad checkout, or an
unrequested backup branch.
