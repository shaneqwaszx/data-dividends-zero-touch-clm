---
name: integration-safe-development
description: "Use when synchronizing a completed feature with main, resolving merge conflicts, preparing a pull request, assessing merge readiness, or publishing independently accepted work."
---

# Integration-Safe Development

Own lifecycle Stage 2 (latest-main integration plus the one integrated acceptance cycle)
and Stage 4 (publication) of the five-stage lifecycle in `docs/DEVELOPMENT_WORKFLOW.md`.
Stage 1 implementation belongs to `fyp-phase-execution`; Stage 3 independent acceptance
belongs to `fyp-quality-gate`; Stage 5 merge belongs to the human owner. This skill does
not authorize commits, pushes, merges, rebases, resets, cleanup, or pull-request
completion when the task has not authorized those actions.

Follow the mandatory context-loading order in `AGENTS.md`, then read the assigned
planner/task and `docs/development/BRANCH_MERGE_PROTOCOL.md`.
`docs/PROJECT_CONTEXT.md` is additional context only when the task needs it. Before
publication, also read `references/PRE_PR_CHECKLIST.md`.

## Lifecycle Stage 2 — Integration and one acceptance cycle

Start only from a stable Stage 1 candidate: known failures fixed, focused checks green,
and implementer self-review complete. INTEGRATION and TESTING may share this run; it
must not be the implementation run.

### Step 1 — Inspect repository

Run:

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin
git rev-parse origin/main
git log --oneline --decorate -10
```

Record existing staged, tracked, and untracked work. Never destroy or move existing work.
If a command would exceed the user's Git authorization, stop and report the required
action.

### Step 2 — Establish baseline

Record `BASE_SHA`, `FEATURE_BRANCH`, and `HEAD_SHA`. Confirm the branch began at current
`origin/main`. If implementation has not begun and the branch is stale, update or
recreate it only with explicit authorization. If implementation exists, preserve it;
do not reset, rebase, or recreate the branch to hide drift.

### Step 3 — Main-drift check

Run:

```powershell
git fetch origin
git rev-parse origin/main
git merge-base HEAD origin/main
git log --oneline HEAD..origin/main
```

If the final command is empty, record `origin/main` as the integrated main SHA and go to
Step 5. Otherwise integration is not finished.

### Step 4 — Integrate latest main

When authorized, merge `origin/main` into the feature branch with
`git merge origin/main`. A merge, and any commit of the candidate it requires, needs task
authorization. Without it, report `NOT INTEGRATED`; acceptance run on the unintegrated
candidate is pre-integration evidence and must be revalidated by effect afterwards. Do
not rebase a shared/pushed branch or auto-resolve conflicts.

For each conflict, establish main intent and feature intent, preserve newer main
security/API/business/regression behavior, and reapply the smallest feature delta.
Preserve tests from both sides unless proven obsolete. If intent is unclear, stop with
the conflict unresolved.

After resolution, inspect:

```powershell
git status
git diff --check
git diff --cached
git diff origin/main...HEAD
```

Follow the protocol's special guidance for frontend, API/type, composition, lockfile,
CI, and documentation conflicts. Never select a lockfile side before establishing
whether dependency manifests intentionally changed.

### Step 5 — Freeze the candidate and run acceptance once

1. Freeze the integrated candidate. Record its content identity (commit/tree, or `HEAD`
   plus path set and per-file hashes for uncommitted content), the integrated
   `origin/main` SHA, and the runtime environment.
2. Run focused conflict-area tests first, then the complete applicable change-class set
   from `docs/DEVELOPMENT_WORKFLOW.md` once on that identity, including any required
   browser, physical Mongo, OCR, lifecycle, contract and security evidence. Serialize or
   isolate suites that share a browser, database, port or lifecycle harness.
3. Verify that merged main behavior and tests did not disappear, and check whitespace for
   tracked changes and every task-owned new file.
4. The testing run edits nothing. A failure returns the candidate to Stage 1; after the
   fix, rerun the failed focus plus the evidence the fix invalidates, not unaffected
   valid evidence.
5. Hand Stage 3 a compact evidence table: command, content identity, environment,
   result, counts, meaningful skips/warnings. Name skipped, unavailable or failed checks
   and the claim each blocks; never report them as passing.

## Lifecycle Stage 4 — Publication after exact independent PASS

Publication requires both exact independent `PASS` on frozen content and explicit
task/owner authorization for the external actions. `PASS WITH MINOR FIXES` requires
remediation and an independent recheck to `PASS` before publication. Use a separate
publication role when available. Reuse the Stage 2 and Stage 3 evidence; do not rerun
complete suites whose content identity, environment and scope are unchanged.

### Step 6 — Verify content and commit

1. Compare the current implementation/instruction paths and diff/tree identity with the
   reviewer's frozen-content record. If reviewed content changed, return it to review.
2. Stage only specific reviewed task-owned paths plus the assigned independent report.
   Inspect `git diff --cached`, staged whitespace and file classification before
   committing.
3. Create the authorized descriptive commit. Committing exactly the reviewed tree plus
   the report does not invalidate evidence.

### Step 7 — Final drift check and pre-PR audit

1. Fetch `origin` and repeat Step 3. If main advanced, integrate only understood,
   explicitly authorized changes; never rebase shared history or guess through a
   conflict. Revalidate by effect using the workflow's evidence-invalidation rules.
   Confirm the reviewed task delta is unchanged by comparing `git patch-id --stable` of
   `git diff <integrated main SHA> <reviewed commit>` with that of
   `git diff origin/main HEAD`; a conflict resolution, unequal id or other change to
   reviewed content needs a fresh independent recheck.
2. Confirm all intended and supporting work is committed. Run `git status --short`; if
   it reports staged, unstaged, or untracked files, stop and classify them. Do not run
   the checker expecting dirty work to receive PASS.
3. Once the working tree and index are clean, run `python scripts/pre_pr_check.py`, then
   complete `references/PRE_PR_CHECKLIST.md`. Review:

```powershell
git status --short
git diff --stat origin/main...HEAD
git diff --name-status origin/main...HEAD
git log --oneline origin/main..HEAD
```

Classify every file `INTENDED`, `SUPPORTING`, or `UNEXPECTED`. If an unexpected change
belongs to this task and can be safely reversed, remove it; otherwise preserve it and
stop for owner guidance. A checker PASS proves only its listed deterministic checks; it
does not prove semantic merge safety. Do not claim `MERGE SAFE` while any required
check failed, was skipped, or origin/main remains ahead.

### Step 8 — Push, PR and CI

1. Push the authorized branch normally, verify local/remote SHA identity, and create or
   update the PR against `main`. Never bypass an approval prompt and never merge the PR.
2. Observe applicable push and `pull_request` workflow runs. Record repository/PR,
   head/base, event, actual checkout SHA/tree when available, run/attempt and relevant job
   conclusions. A PR-only query is not proof of push CI, and one passing run does not
   excuse another failing applicable run.
3. Classify each applicable run as passed, `CI IN PROGRESS`, failed (actual job and
   evidence), or skipped/cancelled (not a pass). Use
   `HOSTED_CI_NOT_EXECUTED — BILLING/INFRASTRUCTURE BLOCKED` only when GitHub's
   run/job/annotation evidence shows jobs did not execute for billing or hosted-runner
   infrastructure reasons; then record the local evidence and leave any manual-CI
   exception to the owner. Never report blocked CI as passed, waive a required check,
   or bypass branch protection. Do not promise unattended monitoring.

## Handoff

Give one compact report, not overlapping audits. Report feature branch, `BASE_SHA`,
integrated `origin/main` SHA, `HEAD_SHA`, whether main was merged after development,
files and hotspots changed, API/schema/config changes, the evidence table and its content
identity, limitations, conflict resolutions, remaining integration risks, and a
recommended PR title.

When publication occurred, also report the commit, remote branch/SHA identity, PR, each
applicable CI event/run/attempt with its classification, and the Stage 5 owner action.

Distinguish `OBSERVED`, `INFERRED`, and `ASSUMED`. No normal feature-development agent
merges the PR.

## Stop conditions

Stop rather than guess when conflict intent is ambiguous, an unexpected worktree could
be overwritten, a contract change lacks authority, required main integration is not
authorized, or a required check cannot be run. Do not work around these states with a
force push, shared-branch rebase, `git clean`, `git reset --hard`, broad checkout, or an
unrequested backup branch.
