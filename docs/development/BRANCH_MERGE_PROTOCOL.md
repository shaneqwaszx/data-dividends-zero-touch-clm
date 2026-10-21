# Branch and Merge Protocol

`main` is the shared integration branch. Feature owners integrate the latest
`origin/main` into their own branch before final acceptance. This puts conflict
resolution with the person who understands the feature, and lets one acceptance cycle
test the integrated candidate.

This protocol supplies the Git procedure for the five-stage lifecycle in
`docs/DEVELOPMENT_WORKFLOW.md`: (1) stable implementation, (2) latest-main integration
and one integrated acceptance cycle, (3) independent QG `PASS`, (4) publication, and
(5) owner squash merge.

## Start from the canonical baseline

Do not start meaningful work from a stale local `main`:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/<short-name>
git rev-parse origin/main
```

Record the final command's output as `BASE_SHA`. Use a new, task-specific branch. Do not
develop on `main`.

Before changing files, record `git status --short`, map the intended files and shared
interfaces, and identify integration hotspots. Preserve existing work. If the tree is
not clean or the assigned branch is unexpected, stop before moving or deleting anything.
Also record current-session tool permissions, required runtimes and any browser,
database, lifecycle or shared-port prerequisite relevant to the task. Configuration or
availability in another session is not current capability evidence.

## Develop a bounded change

Keep the feature delta small. Prefer an existing extension point or a new focused
module/component over rewriting a central file. Do not opportunistically refactor,
rename, reformat, regenerate, or update dependencies.

Stage only reviewed paths, and only when commit/push is authorized (normally by the
Stage 4 publisher):

```powershell
git status
git add <specific-files>
git commit -m "<type>: <description>"
git push -u origin feature/<short-name>
```

Never use `git add -A` when unrelated files are present. A development agent must not
merge a pull request, force-push, rebase a shared branch, modify `main`, delete another
developer's branch, or run `git clean` or `git reset --hard`.

Before independent review, check whitespace in tracked files and every task-owned new
file explicitly; `git diff --check` omits untracked Markdown. Freeze and record the
reviewed implementation/instruction path set and diff/tree identity. The reviewer may
write its report but must not fix reviewed content. A later content change invalidates
the old verdict for that changed scope.

## Integrate main before final acceptance

At Stage 2, before the integrated acceptance cycle, and again as the Stage 4 drift check:

```powershell
git fetch origin
git rev-parse origin/main
git merge-base HEAD origin/main
git log --oneline HEAD..origin/main
git merge origin/main
```

If `git log HEAD..origin/main` shows commits, integration is not finished. Merge
`origin/main` into the feature branch. Rebase is not the default because branches may
be shared and a rewritten branch commonly requires a force push. A merge commit on the
feature branch remains compatible with squash-merging the pull request.

Do not perform the merge, or any commit it requires, when the user or task has not
authorized it. Report the branch `NOT INTEGRATED` and not PR-ready instead; acceptance
evidence on the unintegrated candidate must be revalidated by effect after integration.

## Resolve conflicts by intent

For each conflicted file:

1. List unresolved paths with `git diff --name-only --diff-filter=U`.
2. Identify the current `origin/main` behavior and the feature's intended delta.
3. Preserve newer main security, API, business-rule, regression, and test behavior.
4. Reapply only the smallest feature delta.
5. Preserve tests from both sides unless an authoritative requirement makes one obsolete.
6. Inspect imports, types, interfaces, and contracts affected by the resolution.
7. Run focused conflict-area tests, then the Stage 2 acceptance set (or, at Stage 4, the
   evidence the resolution invalidates, followed by a fresh independent recheck).

Never resolve by blindly selecting `ours`, `theirs`, `accept current`, `accept incoming`,
or by deleting one side. If both intents cannot be established, stop with the file still
unresolved and report the ambiguity.

### Common conflict patterns

- **Large frontend component:** Preserve latest main behavior. Extract the feature into
  a smaller child component where practical; never replace all of `App.tsx` with an old
  branch copy.
- **API or shared type:** Inspect the backend API model and frontend type together. The
  frontend must not invent fields. Preserve compatibility unless an approved task
  explicitly authorizes a breaking change.
- **`composition.py` or `main.py`:** Preserve current provider composition and security
  defaults. Add dependencies through the existing boundary; do not restore stale
  connector wiring.
- **Lockfile:** First determine whether a dependency manifest intentionally changed.
  If it did, regenerate the lockfile with the repository package manager. If it did not,
  retain the lockfile matching the merged manifests. Never splice arbitrary lockfile
  conflict chunks or select a side before establishing dependency intent.
- **CI:** Preserve every current job and check. Add the minimum required check without
  replacing unrelated coverage.
- **Documentation:** Reconcile against the merged implementation. Newer implementation
  truth wins over stale phase claims.

## Verify and publish after exact independent PASS

Use commands defined by the repository and CI; do not invent substitutes. Stage 1 runs
focused tests. Stage 2 runs the applicable backend, frontend, type, lint, contract,
security, physical and build checks once on the frozen integrated candidate. Stage 4
reuses that evidence while content identity, environment and scope are unchanged. It
commits the reviewed feature work using specific paths before the final main-drift
check. If `origin/main` must be merged then, rerun the evidence the merge invalidates
(see the workflow's evidence-invalidation rules), and commit any reviewed conflict
resolution. The pre-PR checker is a clean-branch gate: staged, unstaged, or untracked
files make it fail.

```powershell
git status --short
python scripts/pre_pr_check.py
git diff --stat origin/main...HEAD
git diff --name-status origin/main...HEAD
git log --oneline origin/main..HEAD
```

The first command must produce no entries. The complete Git sequence is: implement with
focused tests; fetch and merge `origin/main` when authorized; run the integrated
acceptance once; obtain exact independent `PASS`; commit the reviewed work; fetch and
reassess drift, merging and revalidating by effect only if main advanced; ensure the
tree is clean; run the checker; push/open the PR when authorized; the owner merges.

Classify every changed file as `INTENDED`, `SUPPORTING`, or `UNEXPECTED`. If an
unexpected change belongs to this task and can be safely reversed, remove it from the
feature delta; otherwise preserve it and stop for owner guidance. The checker is
read-only and fail-closed for deterministic hazards, but passing it does not prove
semantic merge safety.

Only exact independent `PASS` on the frozen content permits the publication stage;
`PASS WITH MINOR FIXES` requires remediation and an independent recheck to `PASS`.
Explicit task/owner authorization is also required for external actions. A separate
publisher verifies the reviewed content is unchanged, stages only
reviewed task-owned paths plus the assigned independent report, inspects the staged
diff/whitespace, creates the authorized descriptive commit, fetches and assesses drift,
performs only understood authorized integration, reruns the evidence it invalidates, and
reaches a clean-tree pre-PR result. If integration changes the reviewed task delta,
obtain a fresh independent recheck before publication continues.

When authorized, push normally, verify local/remote branch SHA identity, open or update
a PR targeting `main`, complete the PR template, and observe applicable GitHub CI. Do
not bypass an approval prompt. For each relevant run record repository/PR, head/base,
workflow event, actual checkout SHA/tree when available, run/attempt and job conclusions.
Push and `pull_request` events may test different checkouts: a PR-only query does not
prove push checks passed, and a passing run never cancels a failing applicable run.
Report pending CI as `CI IN PROGRESS`, identify actual failing checks when present, and
treat skipped or cancelled jobs as not passed. Use
`HOSTED_CI_NOT_EXECUTED — BILLING/INFRASTRUCTURE BLOCKED` only when GitHub's
run/job/annotation evidence shows the jobs did not execute for billing or hosted-runner
infrastructure reasons; record the local evidence and leave any manual-CI exception to
the owner. Never report blocked CI as passed, waive a required check, or bypass branch
protection. Do not promise unattended monitoring.

Stage 5 belongs to the repository owner, who reviews the independent `PASS`, acceptance
and CI evidence, accepted limitations or CI exceptions, and branch/HEAD/main identity,
then performs the squash merge. The publisher does not merge the PR.

## Evidence language

Keep claims auditable:

- `OBSERVED`: directly shown by a command, diff, test, or authoritative file.
- `INFERRED`: a conclusion supported by stated observed evidence.
- `ASSUMED`: not verified; identify it as a risk or blocker.

Never report a command or test as run unless it was actually executed. If a dangerous
operation, contract intent, or conflict resolution is ambiguous, stop rather than guess.
