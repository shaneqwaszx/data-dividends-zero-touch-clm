# Web Modeler Main-Branch Recovery

## Incident summary

- Previous accepted main: `62a7d80324b40308e8cb3feba806b73a24c9c6ac`
- Suspicious `origin/main`: `02ced1fd3de37f945081c01000ecf3315388edfb`
- Commit message: `Web Modeler - Git sync push - 1.0 (by Shane Tan)`
- Commit author: `camunda-sync-for-data-dividends[bot]`
- Commits ahead of the previous accepted main: `1`
- Classification: **C — entirely accidental Web Modeler synchronization**

The classification is based on repository evidence: the bot-generated commit added only
a minimal Camunda Web Modeler BPMN document while deleting unrelated governance,
documentation, frontend dependency/configuration, and backend test-fixture files. It
contained no application migration, runtime integration, tests, or other product change
that could plausibly justify those deletions as an intentional project phase.

## Exact suspicious diff

### Added

- `Zero-Touch Onboarding.bpmn`

### Modified

- None.

### Deleted

- `.agents/skills/README.md`
- `.ai-pipeline/README.md`
- `README.md`
- `apps/backend/tests/fixtures/acra/synthetic_company_success.json`
- `apps/backend/tests/fixtures/uat/README.md`
- `apps/frontend/package-lock.json`
- `apps/frontend/package.json`
- `apps/frontend/tsconfig.app.json`
- `apps/frontend/tsconfig.json`
- `apps/frontend/tsconfig.node.json`
- `docs/architecture/README.md`
- `docs/contracts/README.md`
- `docs/test-plan/README.md`

The suspicious commit changed 14 paths: 13 inserted BPMN lines and 3,455 deleted lines.
It removed application dependency/configuration inputs, repository governance and
documentation, and test fixtures. It contained nothing besides the BPMN addition and
those deletions.

## Recovery strategy and proof

Recovery was prepared in the isolated linked worktree
`C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-main-recovery` on branch
`hotfix/restore-web-modeler-sync`, created from `origin/main`. The protected primary
worktree on `codex/dev-governance-context` was not switched, staged, committed, stashed,
reset, cleaned, or otherwise modified.

The recovery uses the history-preserving command:

```text
git revert --no-commit 02ced1fd3de37f945081c01000ecf3315388edfb
```

Before this report was created, all of the following were observed:

- `git diff --check` returned exit code 0.
- `git diff --cached --check` returned exit code 0.
- `git diff --exit-code 62a7d80324b40308e8cb3feba806b73a24c9c6ac`
  returned exit code 0.
- All 13 deleted files listed above existed again.
- `Zero-Touch Onboarding.bpmn` no longer existed.

Therefore, before adding this report, the complete recovered working tree matched the
previous accepted main exactly. The report is the one intentional working-tree
difference added after that comparison.

## Authoritative staged-index equality proof

The recovery index was compared directly with the previous accepted main using:

```text
git diff --cached --exit-code 62a7d80324b40308e8cb3feba806b73a24c9c6ac
```

- Exit code: `0`
- Output: empty

This comparison is between the staged recovery index and the previous accepted main.
It proves that the staged recovery changes restore the tracked repository tree exactly;
it does not prove any external-system state. This recovery report is intentionally
untracked and unstaged, and is therefore excluded from the equality proof.

## BPMN disposition

The revert removes `Zero-Touch Onboarding.bpmn`. The recovery target is the exact
previously accepted tree, so the model must not be retained opportunistically. A BPMN
model may be proposed later as a separate, reviewed change after its repository
location, product intent, and Git-sync isolation strategy are agreed.

## Verification

- Suspicious commit metadata, author, message, stat, and exact name-status diff: PASS.
- Previous accepted commit object verification: PASS (`commit`).
- Primary worktree branch, HEAD, tracked status, and linked worktrees recorded: PASS.
- Recovery path and local/remote recovery branch absence checked before creation: PASS.
- No-commit revert: PASS.
- Staged and unstaged whitespace/conflict-marker checks: PASS.
- Exact recovered-tree comparison before this report: PASS.
- Critical restored-file existence checks, including both removed fixtures: PASS.
- Pre-PR checker unit tests: PASS, 37 tests. The first sandboxed attempt could not
  create its temporary Git repositories and reached no assertions; the bounded rerun
  with temporary-directory permission passed all tests.
- Secret-scanner unit tests: PASS, 8 tests.
- Tracked/non-ignored secret scan: PASS, with matched values suppressed by the scanner.
- Recovery-report trailing-whitespace check: PASS.
- Physical Mongo: not run; not relevant and explicitly prohibited for this recovery.
- Full product suites: not run; the product tree was proven identical to the previously
  accepted main before this report, so the task requests proportional structural checks.

## Safety

- No commit, push, pull request, reset, rebase, stash, clean, force operation, or direct
  modification of `main` was performed.
- No `.env`, secret value/hash, Mongo URI, private key, `clm_poc`, confidential sponsor
  material, or unrelated protected artifact was accessed.
- The recovery worktree contains the exact no-commit revert plus this report for an
  independent recovery quality gate.

## Web Modeler configuration assessment

Observed repository evidence shows a Camunda sync bot commit, a root-level BPMN file
exported by Camunda Web Modeler, and deletion of unrelated tracked files in the same
commit. This behavior is consistent with a model workspace being synchronized against
the repository root on `main` while its synchronized resource set was treated as
authoritative for the affected paths.

That configuration explanation is an inference, not a claim about exact Camunda account
settings: external Web Modeler configuration was not inspected or changed. The deepest
confirmed cause is the bot-authored destructive sync commit; the external configuration
mechanism remains owner-controlled and must be verified manually.

Before Git sync is enabled again, the repository owner should disable or redirect the
current root/`main` target and configure an isolated destination. Prefer a dedicated
model branch or, more strongly, a dedicated model repository. A dedicated subdirectory
is acceptable only after the owner verifies that Web Modeler scopes all updates and
deletions strictly to that directory. The BPMN can then enter the product repository
through an ordinary reviewed pull request if that is the chosen design.

## Current handoff state

- Application logic difference from previous accepted main: **No**.
- Dependency difference from previous accepted main: **No**.
- Ready for independent recovery quality gate: **Yes**.
- Ready for commit: **No**.
- Ready for push: **No**.
- Ready for pull request: **No**.
