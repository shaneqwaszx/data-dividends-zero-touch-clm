# Agent Pipeline

## Start here

Before selecting a pipeline role, read `AGENTS.md`, classify the change, and run
`python scripts/dev_context.py --change-class <CLASS>` once per class. Read every
emitted current section plus the assigned planner and relevant authority, skill,
source/tests. Unknown/ambiguous work uses `--full`; historical reports stay on demand.

This folder contains role instructions and phase handoffs for Codex.

Recommended order follows the five-stage lifecycle in `docs/DEVELOPMENT_WORKFLOW.md`:

`001_planner` + `003_builder` -> integration + `004_tester` acceptance once -> fresh
independent gate -> `007_publisher` -> owner merge

Insert `002_contract_analyst`, `005_reviewer`, `006_security_reviewer`, or another
narrow read-only specialist when the current change and risk require it. Not every task
needs every role. Security review is mandatory when secrets/auth/PII/external
connectivity are touched. `007_publisher` runs only after
exact independent `PASS` and explicit publication authorization; `PASS WITH MINOR FIXES`
requires remediation and recheck first. The publisher never merges.

Default to one implementation writer. Multiple writers require explicit non-overlapping
ownership and a named integration owner. Agents may share a checkout, so one coordinator
owns Git mutations and no branch switch occurs while another worker uses the worktree.
Serialize shared ports and conflicting browser/database/lifecycle runs.

The active phase scope is defined by an explicitly assigned planner handoff file under
`001_planner/`. Reports preserve evidence/history and do not override current source,
contracts, decisions, configuration or composition.
