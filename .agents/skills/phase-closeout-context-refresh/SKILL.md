---
name: phase-closeout-context-refresh
description: "Use when an accepted or merged feature needs current project state, architecture, provider classifications, sponsor questions, completed phases, evidence, and next-work context reconciled."
---

# Phase Closeout Context Refresh

## Trigger

Use after a feature has an independent accepting gate and is preparing final closeout,
or after it is merged. Do not use an implementation branch to publish unaccepted future
behavior as current main truth.

## Purpose

Keep task-start context current without inventing squash SHAs, sponsor authority,
provider readiness, or test evidence.

## Inputs

- planner/acceptance criteria and final independent gate;
- feature branch/base/head and PR/CI evidence;
- exact post-merge `origin/main` SHA when available;
- changed source/tests/contracts/decisions/questions and provider evidence.

## Mandatory context

Read `AGENTS.md`, `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`,
`docs/DEVELOPMENT_WORKFLOW.md`, the planner, final gate/re-gate, changed source/tests,
relevant decisions/contracts/open questions, and integration evidence.

## Preconditions

- The feature is independently accepted or merged; implementation completion alone is
  insufficient.
- The exact state (`accepted-pending-merge` or `merged-and-verified`) is known.
- Evidence is sanitized and no secret/provider payload is needed for context refresh.

## Analysis steps

1. Classify closeout state:
   - `accepted-pending-merge`: record branch/base/head, gate and CI evidence only in the
     planner-assigned implementation/closeout report under `.ai-pipeline/reports/` (or
     the active phase report explicitly named by the task). Do not create a competing
     generic report, change `PROJECT_STATE.verified_main_sha`, or describe feature
     behavior as current main.
   - `merged-and-verified`: fetch/read the resulting `origin/main`, inspect merged source
     and tests, and use that exact commit as `verified_main_sha`.
2. Reconcile `docs/PROJECT_STATE.md`: date/baseline, current pipeline, completed major
   phase, capabilities/non-capabilities, provider modes, persistence/auth truth, sponsor
   blockers, debt and next candidate work. Keep the structured metadata schema version,
   canonical case-envelope schema version, persistence modes and identity/session
   classification synchronized with the checker-owned source correlations.
3. Reconcile provider `mode` and evidence `classification` separately. A configured
   `sandbox` mode may remain `PARTIAL` or `SANDBOX`; never collapse the dimensions.
   Change either only with direct composed-source evidence plus required execution and
   security evidence. Live requires authorized live contract, composition and sanitized
   live execution proof.
4. Reconcile `docs/ARCHITECTURE.md` only when owners, boundaries, dependencies,
   invariants, persistence/concurrency, security or integration composition changed.
5. Reconcile decisions/contracts/open questions. Verbal discussion remains unconfirmed;
   do not close a question without durable authorized evidence.
6. Record checks/CI accurately. Gate acceptance is not sponsor acceptance.
7. Remove completed work from next candidates and add only bounded evidence-backed
   candidates. Do not automatically authorize the next phase.
8. Run both governance checkers and affected documentation/index checks.

## Allowed changes

- Update canonical current-state/architecture/index documents after evidence threshold.
- Record `accepted-pending-merge` only in a phase/implementation closeout report.
- Link an ADR/decision/question that was actually created or resolved.

## Forbidden changes

- Put a feature branch SHA in `verified_main_sha` as a substitute for a future squash SHA.
- Mark accepted-but-unmerged behavior as current main.
- Promote Mock/Local/Sandbox/Partial/Dormant to Live from CI, credentials or tool access.
- Close a sponsor question from conversation memory or verbal discussion alone.
- Rewrite historical reports to simulate current consistency.

## Stop conditions

Stop the affected update when merge/gate state is unknown, exact post-merge source is
unavailable, provider evidence is insufficient, sponsor authority is not durable, or
current source contradicts the proposed state. Preserve the question/debt instead.

## Required tests

- `python scripts/check_project_state.py`
- `python scripts/check_architecture.py`
- documentation/index checks for changed links/metadata;
- affected product/change-class checks when closeout edits accompany code integration;
- `python scripts/pre_pr_check.py` only on the clean committed PR state.

## Required evidence

- closeout state and exact branch/base/head/main identifiers;
- final gate/re-gate and CI references;
- source/tests inspected for every changed fact;
- provider classification evidence and sponsor-question authority;
- checker results and remaining drift/debt.

## Expected report

```text
CONTEXT REFRESH: UPDATED | PENDING MERGE | STOPPED
Closeout state:
Accepted evidence:
Main baseline:
PROJECT_STATE changes:
ARCHITECTURE changes:
Provider changes:
Sponsor question/decision changes:
Checks:
Deferred/blocked:
```

## Handoff format

For `PENDING MERGE`, hand the owner a report-only record and the exact post-merge refresh
steps. For `UPDATED`, hand QG/owner the changed canonical files, inspected main SHA,
evidence mapping, checker results, unresolved questions and next candidate work. Never
call either state sponsor approval or merge authority.
