---
name: integration-safe-development
description: "Use when synchronizing a completed feature with main, resolving merge conflicts, preparing a pull request, assessing merge readiness, or publishing independently accepted work."
disable-model-invocation: true
---

# Integration-Safe Development: Claude Code pointer

This file only makes the canonical repository skill discoverable in Claude Code.
It adds no instructions, scope or authority.

1. Find the root of the current checkout with `git rev-parse --show-toplevel`. In a
   worktree, that is the worktree itself, never the primary checkout.
2. From that root, read `.agents/skills/integration-safe-development/SKILL.md` in full and follow it
   exactly. Resolve its relative references against `.agents/skills/integration-safe-development/`.
3. `AGENTS.md` and the canonical skill control any disagreement with this pointer.

`disable-model-invocation: true` stops Claude from loading this workflow on its
own; only an explicit `/integration-safe-development` invocation loads it. This is invocation
control only. It does not authorize integration, commit, push, pull-request creation or
merge; those remain governed by `AGENTS.md` and the canonical skill.
