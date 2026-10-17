---
name: fyp-phase-execution
description: "Use when implementing an explicitly assigned bounded Data Dividends FYP feature, phase, or remediation task."
---

# FYP Phase Execution: Claude Code pointer

This file only makes the canonical repository skill discoverable in Claude Code.
It adds no instructions, scope or authority.

1. Find the root of the current checkout with `git rev-parse --show-toplevel`. In a
   worktree, that is the worktree itself, never the primary checkout.
2. From that root, read `.agents/skills/fyp-phase-execution/SKILL.md` in full and follow it
   exactly. Resolve its relative references against `.agents/skills/fyp-phase-execution/`.
3. `AGENTS.md` and the canonical skill control any disagreement with this pointer.
