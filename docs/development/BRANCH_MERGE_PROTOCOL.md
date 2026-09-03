# Branch and Merge Protocol

`main` is the shared integration branch. Feature owners integrate the latest
`origin/main` into their own branch before a pull request is declared ready. This puts
conflict resolution with the person who understands the feature, before final main
integration.

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

## Develop a bounded change

Keep the feature delta small. Prefer an existing extension point or a new focused
module/component over rewriting a central file. Do not opportunistically refactor,
rename, reformat, regenerate, or update dependencies.

Stage only reviewed paths:

```powershell
git status
git add <specific-files>
git commit -m "<type>: <description>"
git push -u origin feature/<short-name>
```

Never use `git add -A` when unrelated files are present. A development agent must not
merge a pull request, force-push, rebase a shared branch, modify `main`, delete another
developer's branch, or run `git clean` or `git reset --hard`.

## Integrate main before the PR

Immediately before PR readiness:

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

Do not perform the merge when the user or task has not authorized it. Report that the
branch is not PR-ready instead.

## Resolve conflicts by intent

For each conflicted file:

1. List unresolved paths with `git diff --name-only --diff-filter=U`.
2. Identify the current `origin/main` behavior and the feature's intended delta.
3. Preserve newer main security, API, business-rule, regression, and test behavior.
4. Reapply only the smallest feature delta.
5. Preserve tests from both sides unless an authoritative requirement makes one obsolete.
6. Inspect imports, types, interfaces, and contracts affected by the resolution.
7. Run focused conflict-area tests, then the applicable broad checks.

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

## Verify and open the PR

Use commands defined by the repository and CI; do not invent substitutes. Run focused
tests first, then the applicable backend, frontend, type, lint, contract, security, and
build checks. Commit the reviewed feature work using specific paths before the final
main-drift check. If `origin/main` must be merged, rerun the affected and broad checks,
then commit the reviewed conflict resolution. The pre-PR checker is a clean-branch gate:
staged, unstaged, or untracked files make it fail.

```powershell
git status --short
python scripts/pre_pr_check.py
git diff --stat origin/main...HEAD
git diff --name-status origin/main...HEAD
git log --oneline origin/main..HEAD
```

The first command must produce no entries. The complete lifecycle is: implement, test,
commit feature work, fetch `origin`, merge `origin/main` if required, rerun tests, commit
any reviewed integration resolution, ensure the tree is clean, then run the checker and
push/open the PR when authorized.

Classify every changed file as `INTENDED`, `SUPPORTING`, or `UNEXPECTED`. If an
unexpected change belongs to this task and can be safely reversed, remove it from the
feature delta; otherwise preserve it and stop for owner guidance. The checker is
read-only and fail-closed for deterministic hazards, but passing it does not prove
semantic merge safety.

When explicitly authorized, push normally, open a PR targeting `main`, complete the PR
template, and wait for GitHub CI. The repository owner performs the squash merge after
review; a normal feature-development agent does not merge the PR.

## Evidence language

Keep claims auditable:

- `OBSERVED`: directly shown by a command, diff, test, or authoritative file.
- `INFERRED`: a conclusion supported by stated observed evidence.
- `ASSUMED`: not verified; identify it as a risk or blocker.

Never report a command or test as run unless it was actually executed. If a dangerous
operation, contract intent, or conflict resolution is ambiguous, stop rather than guess.
