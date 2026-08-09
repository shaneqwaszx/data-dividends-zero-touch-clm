# Agent Pipeline

This folder contains role instructions and phase handoffs for Codex.

Recommended order:

`001_planner` -> `002_contract_analyst` -> `003_builder` -> `004_tester` -> `005_reviewer` -> `006_security_reviewer`

Not every task needs every role. Security review is mandatory when secrets/auth/PII/external connectivity are touched.

The active phase scope is defined by a planner handoff file under `001_planner/`.
