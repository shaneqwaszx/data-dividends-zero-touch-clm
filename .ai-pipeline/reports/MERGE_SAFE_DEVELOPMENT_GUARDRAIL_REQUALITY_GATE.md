# Merge-Safe Development Guardrail — Fresh Independent Re-Quality Gate

## 1. Executive summary

**Result: FAIL.** All five findings from the first independent gate are independently
confirmed **CLOSED**. Dirty staged, unstaged, untracked, and mixed states now fail;
deletions and type changes are inventoried and classified; isolated equals separators
are benign while standard and partial conflict markers fail; the required sensitive
filenames are blocked without printing content; and the real backend/frontend contract
owners receive advisory classification.

The re-gate nevertheless found two new blocking defects. First, the checker is not
strictly read-only: in a clean isolated repository with an mtime-only tracked-file
change, it emitted `SUMMARY: PASS` while changing the actual `.git/index` bytes through
optional Git index refreshes. The supplied rule states that any mutation is Critical.
Second, a coherent Git-supported 32-character conflict-marker structure was reported by
`git diff --check` but removed by the checker's output filter and missed by its
exactly-seven-character regexes, resulting in PASS.

Final findings are **1 Critical, 0 High, 1 Medium, 0 Low**. No implementation,
test, configuration, workflow, or ordinary documentation fix was made.

## 2. Baseline

| Item | Observed result |
|---|---|
| Worktree | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm` |
| Expected branch | `chore/merge-safe-development-guardrail` |
| Observed branch | `chore/merge-safe-development-guardrail` — confirmed |
| `HEAD` | `7568624e84b06dee05dac59158a8165a4a2e88cd` |
| Local `origin/main` | `7568624e84b06dee05dac59158a8165a4a2e88cd` |
| Expected baseline | Confirmed |
| Branch relationship | `HEAD == origin/main`; implementation/remediation is uncommitted |
| Staged changes | None |
| Historical gate SHA-256 before report | `95AE609712AFA6CDE2A54896722C7520D8883854CF40B3382510DC8E0508F876` |

No fetch was performed: this review was instructed not to mutate refs, and the supplied
baseline identifies the expected local `origin/main` value. No branch switch, commit,
stage, push, merge, rebase, reset, clean, restore, or branch operation was performed in
the project repository.

## 3. Scope audit

The nine intended guardrail implementation files are:

| Classification | Files |
|---|---|
| INTENDED | `AGENTS.md`; `.agents/skills/integration-safe-development/SKILL.md`; `.agents/skills/integration-safe-development/references/PRE_PR_CHECKLIST.md`; `docs/development/BRANCH_MERGE_PROTOCOL.md`; `scripts/pre_pr_check.py` |
| SUPPORTING | `.agents/skills/README.md`; `.github/pull_request_template.md`; `.github/workflows/ci.yml`; `tests/test_pre_pr_check.py` |
| HISTORICAL EVIDENCE | `.ai-pipeline/reports/MERGE_SAFE_DEVELOPMENT_GUARDRAIL_QUALITY_GATE.md` |
| UNEXPECTED tracked implementation change | None |

`git diff --name-status` contains only the three tracked modifications to `AGENTS.md`,
`.agents/skills/README.md`, and `.github/workflows/ci.yml`. The other six implementation
files and the historical report are untracked as declared. The tracked diff is 35
insertions in three files. The sole CI delta is one checker-test command in the existing
security job.

No application source, dependency manifest/lockfile, API runtime, persistence, UI,
connector, sponsor mapping, business rule, authentication, or application-security
behavior changed. The protected unrelated untracked filename beginning
`e workspace and multi-document intake` was not opened, read, staged, renamed, deleted,
or cleaned. Existing `pytest-cache-files-*` artifacts were left untouched; permission
warnings while Git enumerated status are environmental and are not gate defects.

## 4. Previous-finding closure matrix

| Previous finding | Status | Independent result |
|---|---|---|
| H-01 — dirty feature work received unqualified PASS | **CLOSED** | Unstaged, staged, untracked, staged+unstaged, and tracked+untracked states all returned FAIL; clean and committed-feature fixtures remained PASS-eligible. |
| H-02 — deletions omitted from inventory/classifiers | **CLOSED** | Committed/staged/unstaged deletions were visible; hotspot, CI, dependency, backend-contract, and frontend-shared deletions warned; rename/type statuses were visible; deleted content was not scanned. |
| M-01 — isolated `=======` treated as conflict | **CLOSED** | Standard coherent and partial markers failed; isolated `=======`, `==========`, and Markdown separator text passed. A separate non-default-marker defect is reported as M-04. |
| M-02 — credential-like filenames missed | **CLOSED** | All fourteen required sensitive names failed without content disclosure; `.env.example`, `ordinary-config.json`, and `credentials-help.md` passed. |
| M-03 — real contract owners missed | **CLOSED** | All six required owners warned on modification, backend and frontend owners warned on deletion, and ordinary service source was not overclassified. |

## 5. H-01 independent evidence

Isolated temporary Git repositories produced:

| State | Exit/result |
|---|---|
| Clean non-main feature branch containing `origin/main` | Exit 0; PASS; clean inventory |
| Unstaged tracked modification | Exit 1; explicit uncommitted tracked-change failure |
| Staged tracked modification | Exit 1; explicit staged-change failure |
| Untracked feature file | Exit 1; explicit commit/ignore/remove failure |
| Staged + unstaged state | Exit 1; both failure reasons present |
| Tracked + untracked state | Exit 1; both failure reasons present |
| Clean branch with committed feature addition | Exit 0; committed delta visible |

The rendered clean result includes `Working-tree inventory: clean`, `SUMMARY: PASS`,
and `NOTE: PASS does not prove semantic merge safety.` The dirty results never emit an
unqualified PASS. The skill, protocol, and checklist additionally state that the
checker is run only after the index/worktree is clean and all intended work is committed.

**H-01 — CLOSED.**

## 6. H-02 independent evidence

`CHANGE_FILTER = "ACMRDT"`; NUL-delimited parsing retains status and both paths for a
rename/copy. Independent evidence confirmed:

1. committed ordinary deletion: `D\tnotes.txt`, not `Committed branch delta: none`;
2. staged ordinary deletion: visible and dirty-tree FAIL;
3. unstaged ordinary deletion: visible and dirty-tree FAIL;
4. committed `apps/frontend/src/App.tsx` deletion: hotspot warning;
5. staged `.github/workflows/ci.yml` deletion: CI warning;
6. unstaged `apps/frontend/package-lock.json` deletion: dependency warning;
7. committed `apps/backend/app/api_models.py` deletion: contract-owner warning;
8. committed `apps/frontend/src/shared.ts` deletion: contract-owner warning;
9. a rename from `App.tsx` to a path containing a space retained both paths and
   classified the old hotspot safely;
10. a committed regular-file-to-symlink type change rendered `T\ttyped.txt` and PASSed
    from a clean worktree;
11. a synthetic Git `C100` NUL record with spaces in both paths was parsed correctly;
12. a branch deleting all seven named source/CI/dependency examples retained every
    path and emitted hotspot, CI, dependency, and contract-owner warnings.

Instrumented content readers were not called for committed, staged, or unstaged deleted
paths. Advisory categories remained warnings for clean committed deltas; dirty state,
not advisory classification alone, caused staged/unstaged failures.

**H-02 — CLOSED.**

## 7. M-01 independent evidence

| Fixture | Result |
|---|---|
| Standard `<<<<<<<` / `=======` / `>>>>>>>` structure | FAIL |
| Actual unresolved Git index conflict | FAIL with `Unresolved Git conflicts` plus marker/dirty evidence |
| Isolated `=======` | PASS; no marker failure |
| Isolated `==========` | PASS; no marker failure |
| Legitimate Markdown/text separator | PASS; no marker failure |
| Partial start marker only | FAIL intentionally |
| Partial end marker only | FAIL intentionally |

The standard false positive from the previous gate is removed without weakening
standard seven-character or partial-marker detection. See M-04 for a distinct
Git-supported non-default marker-size bypass found during new-defect review.

**M-01 — CLOSED.**

## 8. M-02 independent evidence

The following tracked synthetic filenames each returned FAIL:

`.env`, `.env.local`, `credentials.json`, `credential.json`, `secrets.json`,
`secret.json`, `service-account.json`, `service_account.json`,
`service-account-key.json`, `service_account_key.json`, `private.pem`, `private.key`,
`certificate.p12`, and `certificate.pfx`.

Each fixture used a sentinel secret value; the sentinel never appeared in checker
output. `.env.example`, `ordinary-config.json`, and `credentials-help.md` did not match
the sensitive-name failure. Matching is case-normalized and bounded to explicit
environment names, structured credential stems/extensions, or key/certificate suffixes.

**M-02 — CLOSED.**

## 9. M-03 independent evidence

A clean committed modification fixture produced one advisory containing all required
owners:

- `apps/backend/app/api_models.py`
- `apps/backend/app/config.py`
- `apps/backend/app/main.py`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/types.ts`
- `apps/frontend/src/shared.ts`

`apps/backend/app/services/onboarding.py` was modified in the same fixture and was not
included in that advisory. Separate deletion fixtures confirmed both a backend API owner
and a frontend shared owner remain classified after deletion.

**M-03 — CLOSED.**

## 10. Read-only safety review

Line-by-line review found only argument-array subprocess calls (`shell=False` by
default) to `rev-parse`, `branch --show-current`, `merge-base`, `rev-list`, `diff`,
`show`, `ls-files`, and `status`. No repository-controlled text is executed through a
shell. The Python source contains no explicit fetch, pull, commit, merge, rebase, reset,
clean, checkout, switch, add, restore, push, branch deletion, or file-write operation.
Command failures are converted to failures for repository detection, branch identity,
origin/HEAD resolution, ancestry, relationship, unresolved paths, whitespace checks,
change inventories, content reads, tracked paths, and status as applicable.

However, the subprocess environment does not set `GIT_OPTIONAL_LOCKS=0`, nor does it
invoke Git with `--no-optional-locks`. In a clean fixture, changing only a tracked
file's mtime produced:

- index SHA-256 before touch/checker:
  `337a04d952d1adbd9b11ff75a507c5d3d01d54e0c9472999334821c1282312e2`;
- index SHA-256 immediately after the mtime-only touch: unchanged;
- checker result: `SUMMARY: PASS` and `Working-tree inventory: clean`;
- index SHA-256 after checker:
  `5ca0d08300b1ef2bedc1fa1366de5afec0ccf270e66d1fefc7b27dfc1f7f1b87`.

Fresh one-command fixtures isolated index writes to the checker's worktree inspection
forms of `git diff --name-only --diff-filter=U -z`, `git diff --check HEAD`,
`git diff --name-status ...` without a tree argument, and `git status --short`.
Revision-only diff, ref, branch, merge-base, rev-list, `ls-files`, and staged-diff
probes did not alter the index in the same test. A separate dirty-state snapshot proved
HEAD, refs, tree content, tracked bytes, untracked bytes, status, and actual index bytes
stable in that particular dirty fixture; it does not cure the clean mtime case.

This violates the explicit strict read-only invariant. See C-01.

## 11. Main-drift/branch review

Independent repositories confirmed:

- `main` returns FAIL;
- detached HEAD returns FAIL;
- a feature branch behind local `origin/main` returns FAIL and reports it does not
  contain the latest `origin/main` commit;
- a feature branch containing local `origin/main` satisfies the ancestry condition;
- missing `origin/main` returns FAIL.

The checker reports the local `origin/main` SHA and branch relationship. It does not
claim that it fetched a remote. `AGENTS.md`, the integration skill, the checklist, and
the human protocol require `git fetch origin` before the final drift/checker workflow.

## 12. Workflow/documentation consistency

The written lifecycle is consistent across the five reviewed documents:

fresh main -> feature branch -> bounded implementation -> tests -> commit feature work
-> fetch origin -> merge `origin/main` when required/authorized -> deliberate conflict
resolution -> retest -> commit integration resolution -> clean index/worktree ->
pre-PR checker -> authorized push/PR -> CI -> repository-owner squash merge.

No document instructs users to interpret a checker result obtained with expected
uncommitted feature work as PR readiness. Rebase is explicitly not the default for a
shared branch. The documents correctly limit PASS to deterministic hazards rather than
semantic merge safety. Their claim that the checker is read-only is inconsistent with
the observed optional index refresh in C-01; this is a checker implementation defect,
not a second documentation finding.

## 13. Conflict-resolution policy review

Persistent instructions still require the resolver to inspect both current
`origin/main` intent and feature intent; preserve newer main security, API/contracts,
business behavior, regressions, and relevant tests; reapply the smallest feature delta;
and stop with the conflict unresolved when intent cannot be established. They prohibit
blind ours/theirs or current/incoming selection. The remediation did not weaken these
rules.

## 14. Hotspot/dependency/CI advisory review

Modifications to `App.tsx`, `api.ts`, `types.ts`, backend `main.py`/`composition.py`,
`.github/workflows/ci.yml`, and dependency manifests/lockfiles remain advisory warnings
on a clean committed branch. Required deletions reached the same classifiers. A rename
classified both its old and new paths, preventing an old hotspot from disappearing.
The API/config/shared-type category overlaps appropriately with hotspot reporting for
the named owners. No advisory category automatically fails a clean committed branch.

## 15. Test evidence

| Command/check | Result |
|---|---|
| `python -m pytest tests/test_pre_pr_check.py -p no:cacheprovider` | 30 passed in 25.35s after rerun with permission for Windows temporary Git repositories |
| `python -m unittest discover -s tests -p "test_pre_pr_check.py"` | 30 passed in 26.428s |
| `python -m ruff check scripts/pre_pr_check.py tests/test_pre_pr_check.py` | Passed |
| `python -m py_compile scripts/pre_pr_check.py` with bytecode redirected outside the repository | Passed |
| Independent synthetic top-level scenarios | 33: 31 met the safety expectation; 2 exposed C-01 and M-04. The sensitive-name scenario itself covered 14 required names. |

The first sandboxed checker-suite attempt produced setup failures because Git could not
create `.git` under the restricted Windows `%TEMP%`; the authorized reruns above are the
product evidence. One initial type-change probe used a malformed symlink fixture and
left a dirty representation; a corrected clean symlink fixture independently showed
`T\ttyped.txt` and PASS. Neither environmental/reviewer-fixture issue is counted as a
product defect.

The tests assert exit codes and meaningful output for branch, dirty-tree, conflict,
deletion, warning, sensitive-file, and contract-owner behavior. The authored read-only
test compares `git write-tree`, which proves staged tree content but not byte-for-byte
index preservation; its `git status` snapshots can also refresh the index before the
comparison. It therefore misses C-01. It also lacks the non-default-marker case in M-04.

## 16. Security/contract supporting checks

| Command | Result |
|---|---|
| `python -m unittest discover -s tests -p "test_check_secrets.py"` | 5 passed |
| `python -m unittest discover -s tests -p "test_validate_goldtier_examples.py"` | 5 passed |

The repository-wide secret scanner was not invoked because it would enumerate/read the
explicitly protected unrelated untracked file. Synthetic sensitive-name checks exposed
no secret contents. No sponsor/private artifact was opened. No application contract or
sponsor mapping changed.

## 17. CI review

The original backend, frontend, Mongo, Windows lifecycle, and security jobs remain.
Existing backend lint/type/test/contract/delivery checks, frontend dependency/type/test/
build checks, Mongo test, Windows lifecycle test, secret scan, and GoldTier contract
validation remain. The only CI change adds
`python -m unittest discover -s tests -p "test_pre_pr_check.py"` to the security job.
CI tests the checker but does not invoke the branch checker directly on `main`.
Permissions remain `contents: read`; no permission was widened. CI will not detect C-01
or M-04 until direct regression tests are added.

## 18. New-defect review

The review challenged rename parsing, spaces, status precedence, deletion scanning,
type/copy parsing, sensitive allowlisting/overmatching, real contract owners, stale
main, detached HEAD, missing refs, whitespace, exact index preservation, and
repository-controlled Git conflict-marker sizing.

Rename and Windows-space handling, deletion scanning, staged/unstaged precedence,
classification deduplication, allowlisting, dirty-tree truthfulness, and test-local Git
identity were acceptable. Two new defects remain:

- C-01: optional Git worktree inspection refreshes and writes `.git/index`;
- M-04: Git-supported non-default conflict markers are removed from diff-check output
  and missed by exact-seven regexes.

Because the implementation changes are entirely uncommitted, the actual project tree
was not used as a clean PASS fixture.

## 19. Final diff audit

Before writing this report:

- `git diff --check`: passed (LF-to-CRLF notices only);
- `git diff --stat`: three tracked files, 35 insertions;
- `git diff --name-status`: three expected `M` entries;
- staged diff: empty;
- branch/HEAD/origin baseline: unchanged.

All implementation changes are INTENDED or SUPPORTING. There is no unexpected tracked
application/runtime, dependency, API, persistence, UI, sponsor/business-rule, or auth
change. This re-quality-gate report is the only file created by this review. The prior
failed gate remains historical evidence.

## 20. Findings

### C-01 — Worktree inspection mutates the Git index while reporting PASS

**Severity: CRITICAL.** `scripts/pre_pr_check.py:116-125` runs Git without disabling
optional locks/index refresh. The worktree `diff` calls at lines 431-448 and 194-205,
plus `status --short` at lines 483-490, can update cached stat metadata in `.git/index`.
The mtime-only clean fixture changed the real index SHA-256 while the checker returned
PASS. Per this gate's supplied rule, any checker mutation is Critical, even though this
probe did not change HEAD, refs, staged tree content, or tracked/untracked file bytes.

**Required remediation:** execute every inspection Git subprocess with optional locks
disabled (for example a controlled `GIT_OPTIONAL_LOCKS=0` environment or Git's
`--no-optional-locks` global option), then independently prove unchanged HEAD, refs,
actual index bytes, staged tree, tracked/untracked hashes, and status. Add an mtime-only
clean regression that hashes `.git/index` directly; `git write-tree` alone is
insufficient.

### M-04 — Non-default Git conflict-marker sizes can receive PASS

**Severity: MEDIUM.** In a repository with
`*.txt conflict-marker-size=32`, a committed coherent 32-character start/middle/end
structure caused raw `git diff --check origin/main...HEAD` to return 2 with three
`leftover conflict marker` reports. `_non_marker_diff_check_output` at
`scripts/pre_pr_check.py:281-303` removed those reports, while `_marker_lines` at lines
243-266 recognized only exactly seven characters. The checker then emitted
`SUMMARY: PASS`.

**Required remediation:** retain fail-safe coverage for Git-recognized marker sizes
without restoring the isolated-seven-equals false positive. Do not discard Git's marker
diagnostics unless independent scanning provides equivalent coverage, including the
effective `conflict-marker-size` attribute. Add committed/staged/worktree regression
fixtures for a supported non-default size and retain benign separator tests.

## 21. Final metrics

| Metric | Value |
|---|---:|
| Previous findings closed | 5 / 5 |
| Checker pytest tests | 30 passed |
| Checker unittest tests | 30 passed |
| Secret-scanner tests | 5 passed |
| Contract-validation tests | 5 passed |
| Independent top-level scenarios | 33 |
| Critical findings | 1 |
| High findings | 0 |
| Medium findings | 1 |
| Low findings | 0 |
| Unexpected tracked implementation files | 0 |

## 22. Final verdict

The five original remediation targets are closed, and the written workflow remains a
strong foundation. The current checker is not safe enough for Codex, Luna-class,
GPT-5.5-class, weaker/free coding models, VS Code agents, or human teammates because it
violates the mandatory read-only invariant and has a remaining conflict-marker
false-negative. Integration readiness is blocked until C-01 and M-04 are remediated and
independently reverified. No commit, stage, push, merge, rebase, branch switch, or
implementation fix occurred.

FAIL — MERGE-SAFE DEVELOPMENT GUARDRAIL REQUIRES REMEDIATION
