# Agent Pipeline

## Start here

Before selecting a pipeline role, read `AGENTS.md`, `docs/PROJECT_STATE.md`,
`docs/ARCHITECTURE.md`, and `docs/DEVELOPMENT_WORKFLOW.md`, then run
`python scripts/dev_context.py`. Load the assigned planner and relevant specialist
skill/source/tests; do not read every historical report by default.

This folder contains role instructions and phase handoffs for Codex.

Recommended order:

`001_planner` -> `003_builder` -> fresh independent gate -> `007_publisher`

Insert `002_contract_analyst`, `004_tester`, `005_reviewer`,
`006_security_reviewer`, or another narrow read-only specialist when the current change
and risk require it. Not every task needs every role. Security review is mandatory when
secrets/auth/PII/external connectivity are touched. `007_publisher` runs only after
exact independent `PASS` and explicit publication authorization; `PASS WITH MINOR FIXES`
requires remediation and recheck first. The publisher never merges.

Default to one implementation writer. Multiple writers require explicit non-overlapping
ownership and a named integration owner. Agents may share a checkout, so one coordinator
owns Git mutations and no branch switch occurs while another worker uses the worktree.
Serialize shared ports and conflicting browser/database/lifecycle runs.

The active phase scope is defined by an explicitly assigned planner handoff file under
`001_planner/`. Reports preserve evidence/history and do not override current source,
contracts, decisions, configuration or composition.
