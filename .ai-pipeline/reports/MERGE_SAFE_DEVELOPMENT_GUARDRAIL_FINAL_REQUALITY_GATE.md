# Merge-Safe Development Guardrail — Final Targeted Independent Re-Quality Gate

## 1. Executive summary

**Result: PASS.** The final targeted review independently confirms that C-01 and M-04
are **CLOSED**, and that the five earlier findings H-01, H-02, M-01, M-02, and M-03
remain **CLOSED**. The checker preserves raw `.git/index` bytes in the required clean
mtime-only adversarial case while returning PASS, every Git subprocess uses the
centralized read-only helper, and Git-supported 32-character conflict markers fail in
committed, staged, and unstaged states. Matching coherent marker widths 7, 8, 32, and
128 are detected while standalone equals separators remain benign.

The required checker suites passed 37/37 under both pytest and unittest. Ruff,
compilation, the supporting secret-scanner tests, and GoldTier example validation tests
also passed. No Critical, High, Medium, or Low finding remains. No implementation,
test, workflow, configuration, or ordinary documentation file was changed by this
review.

## 2. Baseline

| Item | Observed result |
|---|---|
| Worktree | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm` |
| Expected branch | `chore/merge-safe-development-guardrail` |
| Observed branch | `chore/merge-safe-development-guardrail` |
| `HEAD` | `7568624e84b06dee05dac59158a8165a4a2e88cd` |
| Local `origin/main` | `7568624e84b06dee05dac59158a8165a4a2e88cd` |
| Expected baseline | Confirmed |
| Branch relationship | `HEAD == origin/main`; implementation remains uncommitted |
| Staged changes | None |

No fetch, branch switch, stage, commit, push, merge, rebase, reset, clean, restore, or
project-repository ref mutation was performed. The supplied task fixed the expected
local `origin/main` SHA, so the review verified that ref without network mutation.

## 3. Scope audit

The reviewed guardrail delta remains limited to nine implementation/supporting files:

| Classification | Files |
|---|---|
| INTENDED | `AGENTS.md`; `.agents/skills/integration-safe-development/SKILL.md`; `.agents/skills/integration-safe-development/references/PRE_PR_CHECKLIST.md`; `docs/development/BRANCH_MERGE_PROTOCOL.md`; `scripts/pre_pr_check.py` |
| SUPPORTING | `.agents/skills/README.md`; `.github/pull_request_template.md`; `.github/workflows/ci.yml`; `tests/test_pre_pr_check.py` |
| HISTORICAL EVIDENCE | `.ai-pipeline/reports/MERGE_SAFE_DEVELOPMENT_GUARDRAIL_QUALITY_GATE.md`; `.ai-pipeline/reports/MERGE_SAFE_DEVELOPMENT_GUARDRAIL_REQUALITY_GATE.md` |
| UNEXPECTED tracked implementation change | None |

The tracked diff remains 35 insertions across `AGENTS.md`,
`.agents/skills/README.md`, and `.github/workflows/ci.yml`. The remaining intended
files are untracked because the full implementation is deliberately uncommitted. There
are no application source, dependency manifest/lockfile, runtime API, persistence, UI,
connector, sponsor mapping, business-rule, authentication, or runtime-security changes.

The protected unrelated untracked filename beginning `e workspace and multi-document
intake` was not opened, read, staged, deleted, renamed, or cleaned. Existing
`pytest-cache-files-*` artifacts were left untouched. Git status emitted permission
warnings while attempting to enumerate those cache directories; they do not alter the
reviewed delta.

Historical reports were not overwritten. Their pre-report SHA-256 hashes were:

- original gate: `95AE609712AFA6CDE2A54896722C7520D8883854CF40B3382510DC8E0508F876`;
- first re-gate: `E8497A0A98A6A0D079AAE935EDB987AF9779DA7D35487F3206CB339B527FFE5C`.

## 4. Finding closure matrix

| Finding | Status | Fresh evidence |
|---|---|---|
| H-01 — dirty feature work could receive PASS | **CLOSED** | Clean committed feature is PASS-eligible; unstaged, staged, untracked, and mixed dirty states fail in the 37-test suite; implementation adds an explicit failure for each dirty category. |
| H-02 — deletions omitted from delta inspection | **CLOSED** | Independent fixture exposed committed, staged, and unstaged deletions; hotspot, CI, and dependency deletion warnings; a rename; and a real Git-reported type change. |
| M-01 — isolated `=======` false positive | **CLOSED** | Standard coherent markers and partial start/end markers fail; standalone equals separators remain structurally benign. |
| M-02 — common credential filenames missed | **CLOSED** | Required sensitive names classify as unsafe, allowlisted `.env.example` remains permitted, and ordinary config is benign; test fixtures verify no secret value is printed. |
| M-03 — actual API/shared contract files missed | **CLOSED** | All six named backend/frontend owners classify as advisory; ordinary service source does not. |
| C-01 — Git inspection mutated raw index metadata | **CLOSED** | Clean mtime-only CLI fixture returned PASS with byte-identical raw index SHA-256 and identical refs, staged representation, content hashes, and status. |
| M-04 — non-default conflict marker sizes evaded detection | **CLOSED** | Real `conflict-marker-size=32` fixtures fail when committed, staged, and unstaged; generic matching widths 7/8/32/128 are detected. |

## 5. C-01 implementation review

Static search and Python AST inspection found exactly one `subprocess.run` call, inside
`_git`. Every Git invocation in `scripts/pre_pr_check.py` routes through `_git`; there
is no `Popen`, `check_output`, `os.system`, alternate Git wrapper, or direct subprocess
path.

The helper:

- copies `os.environ` rather than replacing it;
- forces `environment["GIT_OPTIONAL_LOCKS"] = "0"` for every Git child;
- passes Git and arguments as a list;
- supplies the copied environment through `env=environment`;
- does not use `shell=True` or interpolate repository-controlled text into a shell.

The inspected Git verbs are read-only inspection operations: `rev-parse`, `branch
--show-current`, `merge-base --is-ancestor`, `rev-list`, `diff`, `diff-files`, `show`,
`ls-files`, and `status`. No `fetch`, `pull`, `commit`, `merge`, `rebase`, `reset`,
`clean`, `checkout`, `switch`, `add`, `restore`, `push`, or branch-deletion path exists.

## 6. C-01 raw-index evidence

An isolated temporary repository was created with a committed tracked file, local
`origin/main`, a clean feature branch, and ignored local/checker files. The current
checker source was copied into the isolated repository so that a real CLI invocation
used the fixture as its repository root.

Before execution, the snapshot contained `HEAD`, all refs, raw `.git/index` bytes and
SHA-256, `git ls-files --stage`, tracked and ignored-file hashes, and porcelain status.
Only the tracked file's filesystem mtime was advanced by three seconds. The index hash
immediately after that touch was still unchanged.

The checker then returned exit 0 with:

```text
INFO: Working-tree inventory: clean
SUMMARY: PASS (0 unsafe conditions, 0 warning(s))
```

Raw index SHA-256 before and after was identical:

`8A15547E866F16F7A7DB6AB617F40E5CAD094B3D112F97E4D35B0028A8B0EC8D`

The after snapshot was byte/value-identical for `HEAD`, refs, raw index, staged tree
representation, tracked content hash, ignored/untracked content hash, and status. This
directly closes the strict raw-index preservation condition.

One preliminary fixture was discarded because the copied checker itself was untracked,
so the checker correctly returned FAIL. After adding only that temporary path to the
fixture's `.git/info/exclude`, the clean PASS evidence above was obtained. The target
repository was not involved in either fixture.

## 7. C-01 environment/read-only evidence

The implementation's copied environment preserves harmless caller variables and
overrides only the child copy's `GIT_OPTIONAL_LOCKS` value. The authored environment
test patches a caller sentinel plus `GIT_OPTIONAL_LOCKS=1`, captures the actual
`subprocess.run` call, and proves the child receives the sentinel and
`GIT_OPTIONAL_LOCKS=0`; it also proves that no `shell` argument is supplied. That test
passed in both required 37-test runs.

The mtime fixture intentionally launched the checker while its parent environment held
`GIT_OPTIONAL_LOCKS=1`; strict raw-index preservation still held. Source inspection
confirms `_git` never assigns to `os.environ`, so the parent/global environment is not
permanently mutated. No Git mutation command or file-write mechanism was introduced.

## 8. M-04 implementation review

Conflict-marker scanning now uses generic regular expressions that capture the run
width for start (`<`), middle (`=`), and end (`>`) marker families. Partial start/end
markers of width at least seven fail safe. A coherent structure is detected only when
start, middle, and end markers share the same width and occur in order; this preserves
coverage for configured non-default widths without making standalone equals lines
conclusive.

`_non_marker_diff_check_output` discards a Git `leftover conflict marker` diagnostic
only when the referenced source line is an equals-only line and the independent
structural scanner has determined that exact line is benign. Diagnostics remain when
the line is part of a coherent structure, when source text cannot be safely read, or
when the diagnostic cannot be matched to the referenced source line. This avoids both
the previous isolated-equals false positive and the M-04 false negative.

The implementation is not hardcoded to 32. A corrected direct probe returned marker
lines `[1, 3, 5]` for coherent widths 7, 8, 32, and 128, while standalone equals lines
of each corresponding width returned no marker lines. Seven-character partial start
and end markers each remained suspicious. An earlier escaped-string probe was discarded
because it supplied literal escape text rather than physical lines.

## 9. M-04 Git-supported fixture evidence

Three independent isolated repositories each committed:

```text
*.txt conflict-marker-size=32
```

`git check-attr` confirmed `notes.txt: conflict-marker-size: 32` in every fixture. A
coherent 32-character start/middle/end structure was then tested as:

| State | Raw Git check | Checker result |
|---|---|---|
| Committed | exit 2; Git reported `leftover conflict marker` | exit 1; structural failure; `SUMMARY: FAIL` |
| Staged | exit 2; Git reported `leftover conflict marker` | exit 1; staged structural failure; `SUMMARY: FAIL` |
| Unstaged | exit 2; Git reported `leftover conflict marker` | exit 1; unstaged structural failure; `SUMMARY: FAIL` |

The checker did not filter the genuine Git diagnostics into a false PASS. Together
with the width 7/8/32/128 structural probe and benign standalone-equals probe, this
closes M-04 within the requested bounded marker-size scope.

## 10. H-01 through M-03 regression evidence

### H-01

The executed suite verifies a clean non-main feature branch containing `origin/main`
returns PASS eligibility. Unstaged tracked work, staged tracked work, untracked work,
staged-plus-unstaged work, and tracked-plus-untracked work all return FAIL with their
applicable reasons. The explicit failures in `audit_repository` match those outcomes.

### H-02

An independent combined fixture produced this real Git inventory:

- committed: rename of `apps/backend/app/composition.py`, deletion of
  `apps/frontend/src/App.tsx`, deletion of `notes.txt`, and `T\ttyped.txt`;
- staged: deletion of `.github/workflows/ci.yml`;
- unstaged: deletion of `apps/frontend/package-lock.json`.

The checker retained all three deletion states, the rename, and the type change; emitted
hotspot, CI, and dependency warnings; and failed because staged/unstaged work remained.
The implementation deliberately skips content reads only for deletions while keeping
their paths available to classification.

### M-01

The standard seven-character coherent start/middle/end structure fails. Partial
seven-character start and end markers fail safe. Standalone `=======`, standalone
longer equals separators, and legitimate Markdown/text separators do not fail solely
as conflict structures. Git whitespace diagnostics remain fail-closed after the narrow
benign-equals filter.

### M-02

Fresh classifier evidence was:

| Path | Classification |
|---|---|
| `credentials.json` | unsafe |
| `service-account-key.json` | unsafe |
| `.env` | unsafe |
| `private.pem` | unsafe |
| `.env.example` | permitted |
| `ordinary-config.json` | ordinary/permitted |

The 37-test suite also creates tracked sensitive-name repositories, requires checker
FAIL, and asserts that the sentinel secret content is absent from output.

### M-03

Fresh classifier evidence marked all required advisory owners:

- `apps/backend/app/api_models.py`
- `apps/backend/app/config.py`
- `apps/backend/app/main.py`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/types.ts`
- `apps/frontend/src/shared.ts`

`apps/backend/app/services/onboarding.py` remained unclassified as an ordinary source
file. Modification and deletion coverage in the suite confirms the advisory is not
lost when current content is absent.

## 11. Test evidence

| Command/check | Result |
|---|---|
| `python -m pytest tests/test_pre_pr_check.py -p no:cacheprovider` | **37 passed in 37.01s** |
| `python -m unittest discover -s tests -p "test_pre_pr_check.py"` | **37 passed in 36.406s** |
| `python -m ruff check scripts/pre_pr_check.py tests/test_pre_pr_check.py` | **Passed** (`All checks passed!`) |
| `python -m py_compile scripts/pre_pr_check.py` | **Passed** with `PYTHONPYCACHEPREFIX` redirected to a validated temporary directory |

The first sandboxed pytest/unittest attempt could not create `.git` directories under
Windows `%TEMP%` and therefore produced environment setup failures, not product test
results. Both commands were rerun with narrowly scoped permission for temporary Git
repositories and passed as reported above.

The C-01 regression hashes raw `.git/index` bytes, changes only a tracked file's mtime,
asserts the raw index is unchanged before invoking the checker, and compares actual
repository state afterward. Its snapshot helper uses `GIT_OPTIONAL_LOCKS=0`; crucially,
the after snapshot reads raw index bytes before its later status call, so the meaningful
raw-index assertion cannot be invalidated by an accidental optional refresh.

The M-04 regression tests use a real committed `.gitattributes` marker-size fixture,
confirm Git's attribute, and exercise committed, staged, and unstaged 32-character
structures. The tests also directly exercise generic marker widths and benign
separators.

## 12. Supporting security/contract checks

| Command | Result |
|---|---|
| `python -m unittest discover -s tests -p "test_check_secrets.py"` | **5 passed** |
| `python -m unittest discover -s tests -p "test_validate_goldtier_examples.py"` | **5 passed** |

No repository-wide tool that would read the protected unrelated untracked file was
run. No secret content or sponsor/private artifact was opened or printed. There is no
application contract or sponsor-mapping change in this guardrail delta.

## 13. CI/documentation review

The CI diff adds only
`python -m unittest discover -s tests -p "test_pre_pr_check.py"` to the existing
read-only `security` job. The backend, frontend, phase12 Mongo, Windows lifecycle, and
security jobs remain present. Existing lint, type, test, build, secret, and GoldTier
validation commands remain. CI does not invoke the feature-branch checker directly
against a `main` checkout. Repository permissions remain `contents: read`; no
permission was widened and no check was weakened.

`AGENTS.md`, the integration skill, the checklist, the branch protocol, and the PR
template consistently teach:

implement -> test -> commit feature work -> fetch -> merge latest `origin/main` when
needed and authorized -> retest -> commit integration resolution -> clean tree ->
`pre_pr_check` -> authorized push/PR -> CI -> repository-owner squash merge.

The documents describe the checker as read-only and fail-closed, which is now supported
by the raw-index proof. They also state that checker PASS covers deterministic hazards
only and does not prove semantic merge safety.

## 14. New-defect review

No material defect was found in the C-01/M-04 remediation. Specifically:

- no alternate Git subprocess bypasses `GIT_OPTIONAL_LOCKS=0`;
- no unsafe file or Git mutation replaced the prior inspection logic;
- no shell-injection path was introduced;
- dirty-tree detection remains fail-closed;
- deletion, rename, and type-change inventory remains intact;
- isolated equals separators remain benign;
- genuine matching-width conflict structures and Git diagnostics remain failures.

The review intentionally stopped at the requested bounded marker widths and normal team
Git workflow after those safety properties were directly proven.

## 15. Final diff audit

After creating this report, the required commands showed:

- `git diff --check`: passed; only the existing LF-to-CRLF notices were emitted;
- `git diff --stat`: unchanged at three tracked files and 35 insertions;
- `git diff --name-status`: only the three expected tracked modifications;
- `git diff --cached --name-status`: empty;
- `git status --short`: the pre-existing implementation/historical/unrelated entries
  plus exactly this new final report; no unexpected application/runtime path appeared.

The two historical report hashes remained byte-identical to the pre-report values. A
review-created ignored `scripts/__pycache__/pre_pr_check.cpython-312.pyc` was identified
by its current timestamp and removed; the directory's older unrelated bytecode files
were preserved. Bytecode from the required compile check had already been redirected
outside the repository and removed from its validated temporary path. This report is
therefore the only repository file created and retained by the final gate.

## 16. Findings

No current finding.

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |

All seven historical findings are closed. There is no required remediation.

## 17. Final metrics

| Metric | Value |
|---|---:|
| Guardrail implementation/supporting files reviewed | 9 |
| Historical gate reports preserved | 2 |
| Historical findings closed | 7 / 7 |
| Checker pytest tests | 37 passed |
| Checker unittest tests | 37 passed |
| Secret-scanner tests | 5 passed |
| GoldTier example-validation tests | 5 passed |
| Required non-default marker states | 3 / 3 failed safe |
| Required generic marker widths | 4 / 4 detected |
| Raw-index preservation fixture | PASS; byte-identical SHA-256 |
| Unexpected tracked implementation files | 0 |
| Critical findings | 0 |
| High findings | 0 |
| Medium findings | 0 |
| Low findings | 0 |

## 18. Final verdict

The targeted blocking criteria are fully met. This verdict concerns the merge-safe
development guardrail only; it does not authorize commit, push, PR creation, merge, or
any application phase. The implementation remains uncommitted as required.

PASS — MERGE-SAFE DEVELOPMENT GUARDRAIL READY TO INTEGRATE
