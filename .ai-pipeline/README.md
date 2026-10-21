# Agent Pipeline

## Start here

Before selecting a pipeline role, read `AGENTS.md`, classify the change, and run
`python scripts/dev_context.py --change-class <CLASS>` once per class. Read every
emitted current section plus the assigned planner and relevant authority, skill,
source/tests. Unknown/ambiguous work uses `--full`; historical reports stay on demand.

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

## Folder layout

| Path | Contents | Status |
|---|---|---|
| `002_*/` … `007_*/ROLE.md` | Instructions for each pipeline role | Current |
| `001_planner/` | Phase and task planner handoffs | The assigned planner is current; the rest are history |
| `reports/*.md`, `reports/*.json` | Implementation reports, Quality Gates, regression runs, manifests and receipts, named by phase, slice or PR | Historical archive |
| `reports/*_EVIDENCE/`, `reports/*_SCREENSHOTS/` | Browser screenshots, logs and diagnostics captured as evidence | Historical archive |
| `reports/pr81-tcp-capture*/` | PR 81 TCP capture helpers | Historical archive; hash-pinned |

The archive is kept as an audit trail. Read a report only when current source, contracts,
decisions, architecture and state cannot answer a question.

Some archived files are still read by code, so do not move or rename them without
updating the code:

- `scripts/pre_pr_check.py` pins about 30 `reports/` files by hash.
- `tests/contract/` reads several `001_planner/PHASE_0*` files.
- `scripts/run_s3_sandbox_acceptance.py` reads the `ONBOARDING_INTELLIGENCE_S*` gate
  files.
- `.gitattributes` has byte-preservation rules for `reports/SDQ01_ROUND3_EVIDENCE/logs/`.

`reports/RECOVERABLE_ONBOARDING_OPERATOR_ROUTE_SCREENSHOTS/` used to be
`apps/frontend/test-artifacts/operator-route/`. Older reports still cite that path.
