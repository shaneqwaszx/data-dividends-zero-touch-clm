# Phase 15A — Sponsor Rebaseline and Behaviour Alignment: Independent Targeted CI Re-Quality-Gate

## Reviewer Role and Scope

Independent Targeted CI Re-Quality-Gate Reviewer. This review did not implement the
remediation. It reviewed only the uncommitted CI-fixture correction following the
security-job failure in which five synthetic project-state tests rejected a hard-coded
verification date that had become stale relative to their execution-time Git baseline.

## Baseline and Git State

- Branch: `codex/phase15a-sponsor-rebaseline`
- HEAD: `caac4b49e840a8104f348cb541165799c6f5df4a`
- `origin/codex/phase15a-sponsor-rebaseline`:
  `caac4b49e840a8104f348cb541165799c6f5df4a`
- `origin/main`: `1893f74e744bb1f6da32e2be9b27b68deed5ad6a`
- Merge base: `1893f74e744bb1f6da32e2be9b27b68deed5ad6a`

`git fetch origin` completed and the required refs match the supplied baseline.
No Git-writing operation was performed.

## Remediation Diff and Determinism

The sole tracked remediation diff is `tests/test_check_project_state.py` (four
insertions and one deletion). After committing the synthetic source baseline, the
fixture obtains its SHA and runs `git show -s --format=%cs <sha>`; it assigns that
result to `metadata["verified_date"]`. Thus `verified_main_sha` and `verified_date`
derive from the same synthetic baseline commit.

No `date.today`, `datetime.now`, `datetime.utcnow`, `time.time`, system local/UTC date,
or replacement fixed calendar date occurs in the remediation. The existing fixed values
remain only in negative/format test cases, including the stale-date failure assertion.

No diff exists in:

- `scripts/check_project_state.py`
- `docs/PROJECT_STATE.md`
- `.github/workflows/ci.yml`

The checker still requires a valid existing baseline reachable from `origin/main`, a
valid ISO `verified_date`, and rejects dates more than one day before the baseline
commit date. The one-day tolerance, feature-HEAD independence, and an advancing
`origin/main` remain explicitly tested. No test was deleted, skipped, or weakened, and
the read-only/no-`.env`/no-untracked-read safety test passes.

## Reproduced Checks

The host-global Python installation cannot import the repository's `tests` package;
the repository virtual environment was therefore used, matching the remediation
evidence. An initial sandbox run could not create the test-owned temporary Git
repositories; the identical commands passed with the needed local Git-file access.

| Check | Result |
| --- | --- |
| `python -m unittest tests.test_check_project_state -v` | PASS — 16 tests |
| `python -m unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture -v` | PASS — 37 tests |
| `python -m unittest discover -s tests -p "test_check_secrets.py"` | PASS — 8 tests |
| `python -m unittest discover -s tests -p "test_pre_pr_check.py"` | PASS — 26 tests |
| `python scripts/check_project_state.py` | PASS |
| `python scripts/check_architecture.py` | PASS |
| `python scripts/dev_context.py` | PASS |
| `git diff --check` | PASS — no whitespace error |

`python scripts/check_secrets.py`, physical Mongo checks, and provider calls were not
run, as directed.

## Findings

- `P15A-CIRQG-001 | MEDIUM | repository root (untracked entries) | Three unexpected
  untracked filenames are present in addition to the expected remediation report:
  `e workspace and multi-document intake\uf0e2`, `tatus --short`, and `tatus --short
  --untracked-files=no`. Their contents were not opened or inspected. | The required
  remediation inventory is not clean, so an owner could accidentally include unrelated
  material in the remediation commit and this gate cannot attest that the complete
  untracked state is limited to the approved supporting artifact. | The owner must
  identify and remove or separately preserve those artifacts outside this remediation,
  then rerun `git status --short` and this targeted inventory check before staging.`

There are no findings in the test fixture, checker semantics, runtime/business behavior,
real project metadata, CI workflow, or safety contract.

- HIGH: 0
- MEDIUM: 1
- LOW: 0

## Verdict and Readiness

**VERDICT: FAIL.** The code remediation itself correctly resolves the time-sensitive
fixture defect and all required execution evidence passes, but the unexpected untracked
files violate the required clean, isolated remediation inventory. This is a readiness
failure, not a request to change the checker or fixture further.

- Ready for remediation commit: **NO**, pending owner disposition of the three
  unexpected untracked entries and a fresh inventory review.
- Ready for push and CI rerun after commit: **NO**, contingent on the same clean
  inventory and the owner committing only the approved fixture change and report.
- Runtime/business change: **NO**.

## Git and Data Safety

No stage, commit, push, merge, rebase, reset, stash, clean, amend, or branch switch
was performed. No `.env`, secret, Mongo URI, private key/certificate, `clm_poc`, or
protected unrelated artifact was accessed; the unexpected files above were identified
by filename only and not opened.
