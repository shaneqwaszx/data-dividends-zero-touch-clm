# Post-integration Quality Gate: PR #111 merge tree 88a014e

Reviewer: a fresh, independent, read-only Quality Gate. I did not write this change.
Date: 2026-10-26.

Scope: the owner-authorized local integration of `origin/main` `a6e86fc` (README-only
#112) into the reviewed D-087/D-088/D-089 candidate.

I made no edits, staging, commits, stashes, resets, cleans, pushes or merges. I did not
access `.env`, print a Mongo URI or call any provider. My scratch files are in this
folder only.

## 1. Identity

| Item | Observed | Result |
|---|---|---|
| Worktree / branch | `C:\Users\shane\Desktop\claude-worktrees\generalized-poc-acceptance-int-20261025`, `feat/generalized-poc-acceptance-multilayer-20261025-int` | as stated |
| `HEAD` | `5b2e4cd8c70d3ad20ec2bab4a725498e8698e27d` | as stated |
| `7047d46^{tree}` | `a9b5c07a571cefc7ec397c071529872d002e3668` | equals the reviewed tree |
| `7047d46^` | `8451e2a70030f74c50d68194b060bf106aebe7b4` | as stated |
| `5b2e4cd^1`, `5b2e4cd^2` | `7047d46ffd5e…`, `a6e86fc041d7745271d6349c4200a1b3a779852f` | as stated |
| `5b2e4cd^{tree}` | `88a014e25229448f123ae00dd6dd03fa00a35a80` | as stated |
| `origin/main`, after `git fetch origin` and confirmed by `git ls-remote` | `a6e86fc` ("Update README.md (#112)") | has not moved |
| Remote PR branch (`ls-remote`) | `8451e2a` | nothing has been pushed |
| `git status --porcelain` | 0 lines (ahead 3: `7047d46`, `a6e86fc`, `5b2e4cd`) | clean |
| Merge base of `8451e2a` and `origin/main` | `5de7f24` | old base confirmed |

## 2. Integration-only delta

- `git diff --name-status 7047d46 5b2e4cd` shows only `M README.md`.
- That diff is byte-identical to `git diff 5de7f24 a6e86fc -- README.md`, checked with `cmp`.
  Main's change was applied verbatim.
- `5de7f24..a6e86fc` is the single commit `a6e86fc`, and it touches only `README.md`.
- `git diff a6e86fc 5b2e4cd -- README.md` is empty. The `README.md` blob is `d47d9ce` on both
  `a6e86fc` and `5b2e4cd`. On `7047d46` and `5de7f24` it is `c3f1798`, so the candidate never
  touched `README.md`.
- The patch IDs match. `git diff 5de7f24 7047d46 | git patch-id --stable` and
  `git diff origin/main 5b2e4cd | git patch-id --stable` both give `3a3c5727e03347d03b759e8d3f1736ff9e0c2800`.
- The stronger raw check also matches: `git diff --binary 5de7f24 7047d46` is byte-identical
  to `git diff --binary a6e86fc 5b2e4cd`.
- `git diff --stat a9b5c07 88a014e` shows `README.md | 94 (+88/−6)` and nothing else.

## 3. Nothing reverted or lost

- PR #111 changes 54 paths (`5de7f24..8451e2a`). The candidate changes 27 paths
  (`8451e2a..7047d46`).
- 17 of the PR #111 paths differ between `8451e2a` and the merge tree. All 17 are inside the
  27-path candidate set. Running `comm -23` against the candidate set returns an empty list.
- The complete set of `8451e2a..5b2e4cd` paths outside the candidate set is `README.md` only.
  That is main's change.
- Each of the 27 candidate paths has a blob on `5b2e4cd` identical to its blob on `a9b5c07`.
  This was a per-path `rev-parse` loop with zero differences.
- The E2E race-fix file `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` has blob
  `72caa412e44ab750e86867531487aeab35e824e1` on `8451e2a`, `7047d46` and `5b2e4cd`.
  It is unchanged.
- No AI Assistant paths are touched: `git diff --name-only 5de7f24 5b2e4cd | grep -i assist`
  returns nothing.
- The OPQ 50/50 allocation, the strict `businessProfile` decoder and the acceptance code
  are byte-identical to the reviewed tree. The merge tree differs from `a9b5c07` only in
  `README.md`, which covers `acra_api_marketplace_mock.py`, `hybrid_ownership_overlay.py`,
  `ownership_discovery.py`, `ownership_analysis.py`, `onboarding.py`,
  `scripts/five_layer_hybrid_fixture.py` and every other candidate file.

## 4. README impact on tests and tooling

I ran `git grep` on the merge tree for `README` across code and config:

- file types: `*.py`, `*.ts(x)`, `*.js`, `*.json`, `*.toml`, `*.yml`, `*.cfg`, `*.ini`,
  `*.ps1`, `*.bat`, `*.sh`;
- `.github/`;
- `pyproject.toml`, `package.json`, `vite`/`playwright` configs.

Historical `.ai-pipeline/reports` were excluded.

No test, script, workflow, packaging, build or E2E file reads the root `README.md` content.

| Reference | What it does | Affected by the README change? |
|---|---|---|
| `scripts/pre_pr_check.py:168` `HOTSPOTS` | Warns at publication when a hotspot path changed. Merge-conflict signal only; it does not read content | No. It will emit a hotspot warning at Stage 4, which is expected |
| `scripts/dev_context.py:27-28,476` | Reads only `.agents/skills/README.md` and `.ai-pipeline/README.md` | No |
| `tests/test_pre_pr_check.py` | Writes `README.md` inside temporary synthetic repos | No (it does not touch the real file) |
| `tests/test_dev_context.py:322` | `.ai-pipeline/README.md` | No |
| `tests/test_phase_07_delivery_assets.py:59` | `apps/backend/tests/fixtures/uat/README.md` | No |
| `apps/assistant/ai_assistant/main.py:10` | Prose comment | No |
| `.github/workflows/ci.yml` | No README reference | No |
| `apps/backend/tests/test_active_text_encoding.py` | Scope is `apps/backend/app`, `apps/frontend/src` and one contract doc | No |
| `check_secrets.py` / `check_architecture.py` / `check_project_state.py` | Scan tracked files in general (`git ls-files`) | Re-run on the merge commit: PASS (see section 6) |

**Judgment.** The README integration is prose-only (`DOCS_ONLY`). It cannot affect any
backend or frontend test, the E2E runner, any script's behavior, configuration, packaging or
a generated input. The only tooling that sees it treats it as tracked text: the secret scan,
the whitespace checks and the pre-PR hotspot warning. I re-checked all of these.

## 5. Evidence-reuse decision

The rule text is in `docs/DEVELOPMENT_WORKFLOW.md`, "Evidence reuse and invalidation"
(lines 254–272):

> "A change to implementation, tests, configuration, dependencies/lockfiles, CI, scripts
> or integrated main invalidates the evidence it can reach: rerun focused checks plus
> the affected change-class rows. Rerun the complete applicable set when it touches a
> shared owner, hotspot, composition, dependency or CI orchestration, or its impact
> cannot be safely bounded."

The "Integration and PR readiness" section (lines 356–360) adds: "earlier evidence is then
pre-integration and is revalidated by effect after integration."

**Analysis.**

- The integrated-main delta is one `DOCS_ONLY` file. Its reach is bounded by section 4:
  nothing executable consumes it.
- `README.md` is a pre-PR "hotspot", but that label exists for merge-conflict risk. There
  was no conflict, and the branch carries main's blob exactly. So the "complete applicable
  set" for this delta is the `DOCS_ONLY` column of the change-class matrix (lines 157–174):
  - focused check (R): done, see sections 2–4;
  - Ruff (A): not affected, because no Python changed;
  - contract tests (A): not affected, because none reads the root README;
  - secret scanner (A): re-run, PASS;
  - `check_project_state`/`check_architecture` (R): re-run, PASS;
  - `pre_pr_check.py` (R): the Stage 4 publication gate, not run here.
- The product delta is byte-identical before and after integration (raw diff and patch ID).
  The reviewed tree's files are unchanged.

**Decision: all four prior evidence sets remain valid for merge tree `88a014e`. No full
rerun is required.**

| Evidence | Identity | Decision |
|---|---|---|
| Full backend: 3350 tests, 0 failures, 0 errors, 6 skipped (physical Mongo), `full_backend_d088r.xml` (re-read: `tests="3350" failures="0" errors="0" skipped="6"`) | `a9b5c07` | **Valid**. The README is not reachable by any backend test |
| Frontend: 1084 tests, `tsc`, build | `a9b5c07` | **Valid**. No frontend file changed, and no config reads the README |
| E2E 115/115, `d088-e2e\full_results.json` (re-read: `status PASS`, `complete true`, `mode full`, 115/115) | `b23d03a`, carried to `a9b5c07` by the re-QG | **Valid**. The E2E specs and `run_e2e.py` do not read the README |
| Smoke C 16/16, `smoke_d088\d088_smoke_C.json` | candidate | **Valid**. The fixture/runtime path is unchanged |

I also ran a supplementary confirmation on the merge tree itself:

- tests: `test_opq_garden_abc_scenario.py`, `test_business_profile_evidence.py` and
  `test_opq_garden_sim_lim_scenario.py`;
- environment: `PYTHONPATH=<worktree>/apps/backend`, `PHASE12_MONGO_URI` unset,
  `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`;
- result: **76 tests, 0 failures, 0 errors, 1 skipped**, exit 0 (`postint-qg\smoke.xml`).
  The worktree stayed clean afterwards.

## 6. Repository checks on `5b2e4cd`

All checks ran with the main checkout's `.venv` Python from the integration worktree. I
captured each exit code directly; outputs are in `postint-qg\*.out`.

| Check | Result |
|---|---|
| `scripts/check_project_state.py` | `PROJECT STATE CHECK: PASS`, exit 0 |
| `scripts/check_architecture.py` | `ARCHITECTURE CHECK: PASS`, exit 0 |
| `scripts/check_secrets.py` | `Secret scan passed`, exit 0 |
| `scripts/check_policy_authority.py` | `POLICY AUTHORITY CHECK: PASS`, exit 0 |
| `scripts/check_external_provider_readiness.py` | `EXTERNAL PROVIDER READINESS CHECK: PASS`, exit 0 |
| `scripts/check_tooling_config.py` | `TOOLING_CONFIG=PASS`, exit 0 |
| `git diff --check origin/main HEAD` | No output, exit 0. Also clean against `5de7f24` |
| `README.md` hygiene | No trailing spaces, no CR characters, ends with a newline |

## 7. Decision numbers

- The `DECISION_LOG.md` headings for D-085, D-086, D-087, D-088 and D-089 each appear
  exactly once on the merge tree, and zero times on `origin/main`.
- The only duplicate heading ID is **D-069**, at lines 3 and 199. The same duplicate exists
  on `origin/main`, so it is pre-existing and not introduced by this branch.
- D-083 and D-084 are main's AI Assistant proposals. There is no collision with them.

## 8. Not executed

- I did not rerun the full backend suite, physical Mongo, the full frontend suite, `tsc`,
  the frontend build, the full E2E or smoke C. I reused them under section 5.
- I did not run `scripts/pre_pr_check.py`. It is the Stage 4 publication gate, and it will
  emit an expected `README.md` hotspot warning.
- I did not run Ruff or mypy. No Python changed in the integration delta.
- Hosted CI has not run, because nothing has been pushed. Earlier PRs recorded hosted CI as
  billing-blocked; that is not evidence either way.
- I did not re-review the candidate's product logic. The prior QG and re-QG covered it on
  `a9b5c07`, and that tree is byte-identical here.

## 9. Verdict

**PASS** for the integrated merge tree `88a014e25229448f123ae00dd6dd03fa00a35a80` (commit
`5b2e4cd`).

Findings:

- **P0 / P1 / P2:** none.
- **P3 (informational).** At publication, `pre_pr_check.py` will report `README.md` as a
  changed integration hotspot relative to the PR's previous head. This is expected, because
  it is main's #112 content carried verbatim. It is not a defect.
- **P3 (informational).** The duplicate D-069 heading in `DECISION_LOG.md` is pre-existing
  on main. It is out of scope for this branch.

Next authorized action: Stage 4 publication, if the owner authorizes it. That means a
clean-tree `scripts/pre_pr_check.py` on `5b2e4cd`, then a push of the unchanged content to
the PR #111 branch. Owner merge stays with the human repository owner.
