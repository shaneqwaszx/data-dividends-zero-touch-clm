---
name: fyp-quality-gate
description: "Run the independent combined quality gate for a completed Data Dividends FYP phase or bounded governance change. Use when Codex must review contract/integration behavior, tests, code or instructions and architecture, security, and adverse failure paths; write the assigned gate report; issue PASS, PASS WITH MINOR FIXES, or FAIL; and state readiness without implementing fixes."
disable-model-invocation: true
---

# FYP Quality Gate: Claude Code pointer

This file only makes the canonical repository skill discoverable in Claude Code.
It adds no instructions, scope or authority.

1. Find the root of the current checkout with `git rev-parse --show-toplevel`. In a
   worktree, that is the worktree itself, never the primary checkout.
2. From that root, read `.agents/skills/fyp-quality-gate/SKILL.md` in full and follow it
   exactly. Resolve its relative references against `.agents/skills/fyp-quality-gate/`.
3. `AGENTS.md` and the canonical skill control any disagreement with this pointer.

`disable-model-invocation: true` stops Claude from loading this workflow on its
own; only an explicit `/fyp-quality-gate` invocation loads it. This is invocation
control only. It does not make a review independent; independence, the frozen reviewed
content and the sole gate verdict remain governed by `AGENTS.md` and the
canonical skill.
