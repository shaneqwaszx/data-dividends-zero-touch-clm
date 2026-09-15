# Agent Pipeline

## Start here

Before selecting a pipeline role, read `AGENTS.md`, `docs/PROJECT_STATE.md`,
`docs/ARCHITECTURE.md`, and `docs/DEVELOPMENT_WORKFLOW.md`, then run
`python scripts/dev_context.py`. Load the assigned planner and relevant specialist
skill/source/tests; do not read every historical report by default.

This folder contains role instructions and phase handoffs for Codex.

Recommended order:

`001_planner` -> `002_contract_analyst` -> `003_builder` -> `004_tester` -> `005_reviewer` -> `006_security_reviewer`

Not every task needs every role. Security review is mandatory when secrets/auth/PII/external connectivity are touched.

The active phase scope is defined by an explicitly assigned planner handoff file under
`001_planner/`. Reports preserve evidence/history and do not override current source,
contracts, decisions, configuration or composition.
