---
name: worktree-task
description: "Use when concurrent repository tasks need separate Git checkouts, unrelated work blocks safe branch switching, or a task explicitly requires worktree isolation."
---

# Worktree Task

Use a worktree only when concurrent histories need separate checkouts. Keep the primary
checkout as the stable `main` reference where practical; strictly sequential work does
not need another worktree.

## Before mutation

1. Inspect `git status --short`, the current branch and `HEAD`, active Git operations,
   and `git worktree list --porcelain`.
2. Identify the task owner, intended base, branch, path, and cleanup trigger. Preserve
   every existing checkout whose ownership or state is unclear.
3. Prefer current updated `origin/main` as the base unless the assigned workflow names a
   different reviewed base. Follow `AGENTS.md` and
   `docs/development/BRANCH_MERGE_PROTOCOL.md` for baseline and branch rules.

## Isolation decision

- Reuse the current task checkout when work is sequential and its state is compatible.
- Create one task-scoped worktree for a concurrent development stream.
- Use a distinct worktree pinned to the frozen commit (detached is acceptable) when an
  independent review must run concurrently with implementation. Uncommitted content is
  not a stable concurrent-review boundary; review it sequentially after writes stop, or
  wait for an authorized frozen revision.
- Use descriptive task-scoped worktree and branch names. A branch decision and a
  worktree decision are separate.

## Create or reuse safely

Use an explicitly exposed host-managed worktree lifecycle when available. Otherwise, after
verifying the exact target path and ownership, use ordinary `git worktree add` without
force flags. Read back the worktree list, root, branch/HEAD, and status before writing.

Never switch a checkout used by another worker; reset, clean, stash, or check out over
unrelated changes; reuse/delete an ownership-unknown branch; or force-remove a dirty,
locked, active, unreviewed, or ownership-unknown worktree. Stop when safe ownership or
the intended base cannot be established.

## Handoff and cleanup

Report the worktree path, branch/ref, base SHA, owner, status, and expected cleanup
event. Explain cleanup only after merge or task completion. Before removal, prove the
worktree has no unreviewed or unpreserved changes; never use force removal as routine
hygiene.
