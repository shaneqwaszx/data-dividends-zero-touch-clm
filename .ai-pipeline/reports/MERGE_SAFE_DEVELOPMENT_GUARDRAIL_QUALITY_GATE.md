# Merge-Safe Development Guardrail — Independent Quality Gate

## 1. Executive summary

**Result: FAIL.** The documentation and read-only design are directionally strong, but
the checker is not safe enough to be the repository-wide PR-readiness signal for weaker
agents. It returns `SUMMARY: PASS` for staged and unstaged tracked feature work that is
absent from `HEAD`, and it omits deletions from the committed delta and all advisory
classifiers. A committed branch that deletes every required hotspot, the CI workflow,
and `package-lock.json` therefore passes with zero warnings and is reported as having no
committed delta.

There are **0 Critical, 2 High, 3 Medium, and 0 Low** findings. The two High findings
independently violate the gate's zero-High/zero-Medium PASS threshold and can produce a
false PR-ready interpretation in common workflows. No implementation fix was made.

## 2. Baseline

| Item | Observed result |
|---|---|
| Worktree | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm` |
| Branch | `chore/merge-safe-development-guardrail` — expected branch confirmed |
| `HEAD` | `7568624e84b06dee05dac59158a8165a4a2e88cd` |
| Local `origin/main` | `7568624e84b06dee05dac59158a8165a4a2e88cd` |
| Expected baseline | Confirmed |
| Branch relationship at review start | `HEAD == origin/main`; implementation is entirely uncommitted |
| Report pre-existence | Absent; no historical report was overwritten |

No fetch, branch switch, commit, push, merge, rebase, reset, clean, staging operation,
or ref mutation was performed. The local `origin/main` ref was used as instructed; it
was not network-refreshed because this is a review-only gate and a fetch would mutate a
Git ref.

## 3. Scope audit

The declared implementation contains nine files:

| Classification | Files |
|---|---|
| INTENDED | `AGENTS.md`; `docs/development/BRANCH_MERGE_PROTOCOL.md`; `.agents/skills/integration-safe-development/SKILL.md`; `.agents/skills/integration-safe-development/references/PRE_PR_CHECKLIST.md`; `scripts/pre_pr_check.py` |
| SUPPORTING | `.agents/skills/README.md`; `.github/workflows/ci.yml`; `.github/pull_request_template.md`; `tests/test_pre_pr_check.py` |
| UNEXPECTED tracked change | None |

`git diff --name-status` showed only the three declared modified tracked files because
the other six files are untracked. `git status --short` accounted for all six declared
new paths. The separately identified pre-existing untracked filename beginning
`e workspace and multi-document intake` was not opened, read, staged, renamed, deleted,
or classified as a gate defect. Existing `pytest-cache-files-*` artifacts were not
removed or opened.

There are no dependency, application API, persistence, UI, sponsor mapping, business
rule, authentication, or runtime behavior changes in the reviewed delta. The sole
hotspot change is the intended one-line CI addition.

## 4. AGENTS.md review

**PASS.** The new section is concise enough for repository-wide use and points to the
detailed skill, protocol, and checklist instead of reproducing the full workflow. It is
compatible with the existing project rules and explicitly states that:

- `origin/main` is canonical and feature branches start from its current state;
- development must not happen directly on `main`;
- latest `origin/main` must be integrated before PR readiness;
- shared branches are not rebased by default;
- force-push, `git reset --hard`, and `git clean` are prohibited;
- conflicts cannot be resolved by blindly choosing ours/theirs or current/incoming;
- newer-main API, UI, security, mock, configuration, business, and documentation
  behavior must not be replaced by stale branch behavior.

## 5. Skill review

**PASS.** `.agents/skills/integration-safe-development/SKILL.md` has explicit Stages
0–9 for repository inspection, baseline establishment, scope mapping, bounded
implementation, local verification, drift detection, latest-main integration,
regression verification, pre-PR audit, and handoff. The stages provide concrete Git and
verification commands plus explicit authorization and stop conditions.

Conflict guidance requires preservation of newer-main security fixes, API contracts,
business behavior, regression behavior, and tests from both sides while reapplying the
smallest feature delta. Ambiguous intent requires STOP rather than a guessed resolution.
The skill accurately says deterministic checks do not prove semantic merge safety. The
checker defects in Findings H-01 and H-02 prevent the Stage 8 automation from enforcing
the otherwise sound written workflow.

## 6. Human protocol review

**PASS.** `docs/development/BRANCH_MERGE_PROTOCOL.md` teaches the requested sequence:
fresh main, feature branch, bounded work, specific staging/commit/push, current-main
fetch, merge main into the feature branch, intent-based conflict resolution, regression
checks, pre-PR audit, PR, CI, and repository-owner squash merge. It explains that the
feature owner resolves conflicts before final integration and that merging main into the
feature branch preserves shared history without requiring a force push. Rebase is not
the default. The shown Git commands work in PowerShell and CMD after replacing the
clearly marked placeholders.

## 7. `pre_pr_check.py` safety review

**PASS for non-mutation and command execution safety.** Line-by-line inspection found
only these Git operations: `rev-parse`, `branch --show-current`, `merge-base
--is-ancestor`, `rev-list`, `diff`, `show`, `ls-files`, and `status`. All subprocesses
use an argument vector with the default `shell=False`; no repository-controlled string
is interpreted by a command shell. There is no commit, merge, rebase, reset, clean,
checkout/switch, push, pull, branch deletion, file write, or remote mutation path.

An independent fixture captured `HEAD`, all refs, porcelain status, the index hash, the
tracked-file hash, and the untracked-file hash before and after the checker. All values
were identical. Git inspection failures handled through `_required_paths` fail closed;
missing/non-commit `origin/main`, invalid relationship output, status failure, and
unresolvable `HEAD` also fail. `merge-base --is-ancestor` nonzero results conservatively
fail, including command errors.

## 8. `pre_pr_check.py` functional review

Verified behavior:

- rejects `main` and detached/non-feature states;
- fails when `origin/main` is missing or is not contained in `HEAD`;
- reports ahead/behind counts;
- fails on unresolved conflicts, conflict markers, and tracked diff whitespace errors;
- inventories additions/modifications and untracked files;
- warns for the seven named hotspots, dependency files, CI workflows, and the two exact
  frontend API/type files;
- fails for tracked `.env*` files and supported key/certificate suffixes;
- ends with deterministic PASS/FAIL and explicitly disclaims semantic merge safety.

It does not fully meet changed-file inventory, deletion, dirty-tree completeness,
credential-like filename, and repository API/shared-type reporting requirements. See
H-01, H-02, M-02, and M-03.

## 9. Dirty-working-tree / PR-completeness review

**FAIL — H-01.** Independent isolated cases produced:

| State while `HEAD == origin/main` | Exit/result |
|---|---|
| One unstaged tracked feature modification | Exit 0; `SUMMARY: PASS (0 unsafe conditions, 0 warning(s))` |
| The same feature modification staged | Exit 0; `SUMMARY: PASS (0 unsafe conditions, 0 warning(s))` |
| One untracked feature file | Exit 0; `SUMMARY: PASS (0 unsafe conditions, 1 warning(s))` |

The checker prints tracked dirty state only as `INFO` inventory and never changes the
summary. Untracked state receives a warning, but the headline remains PASS. A weak agent
can therefore claim PR readiness even though its current feature work is not represented
in `HEAD` and will not be part of the branch delta used by a PR.

For a pre-PR checker intended for weak/free models, staged or unstaged tracked changes
should fail. Untracked files should also fail unless a deterministic, explicit mechanism
proves they are intentionally excluded; at minimum the output must not end in an
unqualified PASS while PR completeness is unresolved.

## 10. Stale-main verification

**PASS.** In an isolated Git repository, advancing `origin/main` after creating the
feature branch caused exit 1 with `Current branch does not contain the latest
origin/main commit` and relationship `ahead 0, behind 1`. A feature branch containing
the current `origin/main` commit returned exit 0 and `ahead 0, behind 0`.

These results prove the ancestry check itself. They do not prove that a local
`origin/main` ref was freshly fetched, nor does the checker claim that they prove
semantic merge safety.

## 11. Conflict-marker verification

**Partial; M-01.** A changed source file containing the normal five-line
`<<<<<<<` / `=======` / `>>>>>>>` structure failed, and a staged marker fixture was
detected in both staged and working-tree content. A line containing ten equals signs
passed. However, a legitimate changed text file containing only the exact line
`=======` failed as a conflict marker. The regex treats any isolated seven-equals line
as conclusive without requiring the surrounding start/end markers. This is an obvious
false positive for valid text/Markdown separator content and requires remediation.

## 12. Hotspot verification

**Partial; H-02 applies to deletions.** Modifications to all required hotspots generated
one advisory warning listing:

- `apps/frontend/src/App.tsx`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/types.ts`
- `apps/backend/app/main.py`
- `apps/backend/app/composition.py`
- `.github/workflows/ci.yml`

The same fixture also warned for `package-lock.json`, CI, and frontend API/shared types.
The result remained PASS, which is correct for advisory-only hotspot detection. A
committed deletion of those same files was invisible because deletions are excluded by
the path filters; that unsafe false-negative is H-02.

## 13. Sensitive-file verification

**Partial; M-02.** Synthetic staged `.env` and `.pem` files each caused FAIL without
printing file contents. A synthetic staged `credentials.json` file produced
`SUMMARY: PASS (0 unsafe conditions, 0 warning(s))`. The filename classifier recognizes
only `.env*` and certificate/keystore suffixes, not common credential-like names.

The existing secret-scanner unit suite passed 5/5, and a safe targeted scan of the nine
reviewed implementation files found zero supported secret patterns. The repository-wide
`python scripts/check_secrets.py` command was deliberately not run because it enumerates
and reads non-ignored untracked files, which would violate the explicit instruction not
to open/read the exempt untracked artifact. No sponsor/private credential source was
read or exposed.

## 14. Checker test evidence

| Command/check | Result |
|---|---|
| `python -m pytest tests/test_pre_pr_check.py` with pytest cache disabled | 9 passed in 6.89s after rerun with permission for Windows temp repositories |
| Initial sandboxed pytest attempt | 9 setup failures because `git init` could not write `.git` under `%TEMP%`; environment restriction, not a product result |
| `python -m unittest discover -s tests -p "test_pre_pr_check.py"` | 9 passed in 6.607s |
| `python -m ruff check scripts/pre_pr_check.py tests/test_pre_pr_check.py` | Passed |
| `python -m py_compile scripts/pre_pr_check.py` with bytecode redirected outside the repository | Passed |
| Independent adversarial fixture scenarios | 13 executed; exposed H-01, H-02, M-01, and M-02 while confirming stale-main, normal marker, hotspot, `.env`, and `.pem` behavior |
| Independent read-only state snapshot | Passed; refs, `HEAD`, index, tracked content, untracked content, and status were unchanged |
| `python -m unittest discover -s tests -p "test_check_secrets.py"` | 5 passed |
| Targeted supported-pattern scan of all nine reviewed implementation files | 0 findings |

The authored tests exercise meaningful behavior rather than merely executing happy
paths, including main rejection, stale-main rejection, current-main acceptance,
unresolved conflicts, markers, sensitive environment files, hotspot reporting, and
non-mutation. They do not cover dirty tracked/staged PR completeness, untracked
completeness semantics, deletions, isolated benign `=======`, common credential-like
filenames, or actual repository API/shared-type filenames. Those omissions allowed all
five gate findings to remain green in CI.

## 15. CI review

**PASS for the workflow change.** The diff adds exactly one command to the existing
read-only `security` job:
`python -m unittest discover -s tests -p "test_pre_pr_check.py"`. All existing backend,
frontend, Mongo, Windows lifecycle, secret, and contract-validation jobs/checks remain
present. No permission was added or widened (`contents: read` remains). CI executes the
checker tests rather than the checker against the CI checkout, so a push to `main` does
not fail merely because the checked-out branch is `main`. The test fixtures are local,
synthetic, network-free, and deterministic on the configured Ubuntu runner.

CI cannot compensate for missing assertions in the new test file; it will currently
accept the false-PASS behaviors in H-01 and H-02.

## 16. PR-template review

**PASS.** The template captures scope/non-goals, feature branch, initial `BASE_SHA`,
latest-main integration and SHA, changed backend/frontend/API/persistence/config/CI
areas, shared/hotspot files and rationale, exact tests and omissions, checker result,
conflict resolutions, sponsor/business assumptions, limitations, and reviewer focus.
It is compact enough for routine use.

## 17. Compatibility with existing skills

**PASS.** The new skill complements rather than overrides:

- `fyp-phase-execution`: supplies branch/baseline/integration mechanics while phase
  scope and acceptance remain with the planner and phase skill;
- `fyp-quality-gate`: leaves independent review and sole-report boundaries intact;
- `ci-failure-triage`: does not diagnose or weaken failing CI and requires exact checks;
- `integration-security-review`: preserves the specialist security boundary and calls
  out security/auth changes for disclosure;
- `poc-regression-check`: requires applicable regression checks without redefining the
  canonical scenario catalogue;
- `sponsor-contract-reconciliation`: preserves authoritative contract/business intent
  and stops when conflict intent is ambiguous.

`AGENTS.md` remains authoritative, and `.agents/skills/README.md` explicitly states
that skills cannot broaden planner scope, override repository rules, or authorize
commit/push/merge.

## 18. Diff audit

At the pre-report audit, `git diff --check` passed. `git diff --stat` reported the three
tracked modifications as 35 insertions across `AGENTS.md`, `.agents/skills/README.md`,
and `.github/workflows/ci.yml`; the six expected new files remained untracked and were
verified directly. Line-ending notices stated that Git may convert LF to CRLF when it
next touches the three modified tracked files; they were warnings, not whitespace
errors.

Every tracked implementation change is INTENDED or SUPPORTING. There is no unexplained
UNEXPECTED tracked change, dependency change, application change, or generated/lockfile
change. This report is the only quality-gate-created repository file.

## 19. Findings

### H-01 — Dirty feature work receives an unqualified PASS

**Severity: HIGH.** `scripts/pre_pr_check.py:264-316` inventories local changes but adds
no failure for staged or unstaged tracked work and only a warning for untracked files;
`scripts/pre_pr_check.py:329-333` still renders `SUMMARY: PASS`. Independent fixtures
confirmed PASS/zero warnings for both staged and unstaged tracked modifications while
`HEAD == origin/main`, and PASS/one warning for untracked work. A weaker agent can
therefore state that all current work is PR-ready even when the PR delta is empty.

**Required remediation:** fail when staged or unstaged tracked changes exist. Treat
untracked files as PR-completeness blocking unless an explicit deterministic exclusion
mechanism is designed; never emit an unqualified PASS while local feature content is
not represented in `HEAD`. Add tests for all three states and for mixed dirty states.

### H-02 — Deletions are excluded from delta inventory and every advisory classifier

**Severity: HIGH.** `_changed_paths` uses `--diff-filter=ACMR` for branch, worktree, and
staged paths (`scripts/pre_pr_check.py:101-130`), excluding `D` and type changes. The
result feeds committed-delta reporting, marker scanning, hotspots, dependencies, CI,
and API/shared-type warnings (`scripts/pre_pr_check.py:264-316`). An isolated committed
branch deleting all six required source/CI hotspots plus `package-lock.json` exited 0,
reported zero warnings, and printed `Committed branch delta: none`.

**Required remediation:** include deletions and relevant type changes in complete delta
inventory and advisory classification. Do not try to read deleted content, but report
the path and change status. Add committed, staged, and unstaged deletion tests covering
CI, dependencies, hotspots, and ordinary files.

### M-01 — Isolated seven-equals content is a false conflict marker

**Severity: MEDIUM.** `CONFLICT_MARKER` at `scripts/pre_pr_check.py:19` treats any exact
`=======` line as a conflict regardless of surrounding markers. A synthetic file whose
only content was that line failed; ten equals signs passed.

**Required remediation:** detect a coherent conflict-marker structure, or otherwise
avoid treating an isolated equals separator as conclusive. Add both true-marker and
benign Markdown/text cases.

### M-02 — Common credential-like filenames are not detected

**Severity: MEDIUM.** `_is_obvious_sensitive_file` at
`scripts/pre_pr_check.py:192-202` recognizes `.env*` and selected key/certificate
suffixes only. A staged `credentials.json` passed without warnings. Existing content
scanning in separate CI lowers but does not remove the pre-PR false-negative risk.

**Required remediation:** define and test a conservative set of common credential-like
filenames/patterns, with explicit allowlisted example/template variants where needed.
Keep reporting filename/type only and never matched secret values.

### M-03 — API/shared-type reporting misses real repository owners

**Severity: MEDIUM.** `_is_api_config_or_shared_type` at
`scripts/pre_pr_check.py:177-189` does not classify this repository's
`apps/backend/app/api_models.py` or `apps/frontend/src/shared.ts`. The path inventory
would still display modifications, and `main.py` has separate hotspot coverage, but the
required API/config/shared-type advisory is incomplete and can be missed by a weak
agent or reviewer.

**Required remediation:** align classifier rules with the repository's actual API model
and shared contract/type owners, then add direct tests for backend API models,
configuration, frontend API, frontend types/shared contracts, and non-contract control
files.

## 20. Final metrics

| Metric | Value |
|---|---:|
| Reviewed implementation files | 9 |
| Intended | 5 |
| Supporting | 4 |
| Unexpected tracked | 0 |
| Application/dependency/API/persistence/UI/business changes | 0 |
| Auth/security behavior changes | 0 |
| Checker pytest cases | 9 passed |
| Checker CI-equivalent unittest cases | 9 passed |
| Secret-scanner unittest cases | 5 passed |
| Independent adversarial scenarios | 13 |
| Critical findings | 0 |
| High findings | 2 |
| Medium findings | 3 |
| Low findings | 0 |

## 21. Final verdict

The written repository policy, staged integration workflow, human protocol, checklist,
CI insertion, and PR template are suitable foundations. The checker and its tests must
be remediated before this can become the team-wide standard for Codex, Luna-class,
GPT-5.5-class, weaker/free, IDE, and human workflows. Full backend/frontend suites were
not rerun because no application or dependency behavior changed; focused tooling,
security, lint, compile, CI-command, and adversarial evidence was proportionate to this
gate. No commit, push, merge, branch change, implementation fix, or next phase occurred.

FAIL — MERGE-SAFE DEVELOPMENT GUARDRAIL REQUIRES REMEDIATION
