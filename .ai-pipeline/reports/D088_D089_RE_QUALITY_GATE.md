# Re-QG D-087 + D-088 + D-089: independent re-review of the remediated candidate

Reviewer: fresh, independent and read-only. I did not write the change and did not do the
previous review. I made no worktree edits, staging, commits, stashes, resets or cleans. The
real index is untouched: `git diff --cached` is empty before and after. Scratch files are in
`scratchpad\reqg-d088\`. I did not access `.env`, print a Mongo URI or call any provider.

## 1. Identity

| Item | Value | Evidence |
|---|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\generalized-poc-acceptance-int-20261025` | verified |
| Branch | `feat/generalized-poc-acceptance-multilayer-20261025-int` | `git branch --show-current` |
| HEAD | `8451e2a70030f74c50d68194b060bf106aebe7b4` (PR #111 head) | verified |
| Merge-base with origin/main | `5de7f24c2dbf678bbb9de02ad627be777bc2f28c` | verified |
| origin/main | `a6e86fc041d7745271d6349c4200a1b3a779852f`. `git diff --name-only 5de7f24 origin/main` = `README.md` only, which is not among the 27 candidate paths, so there is **no overlap** | verified |
| Inventory | `git status --short` = exactly the 27 paths in `d088r_paths.txt` (25 modified, 2 untracked tests) | verified |
| Candidate tree | Copied index, `GIT_INDEX_FILE=<copy> git add --pathspec-from-file`, then `write-tree` = **`a9b5c07a571cefc7ec397c071529872d002e3668`**. This matches the claim, and I recomputed it at the end of the review with an identical result | verified |
| Delta from the reviewed tree `b23d03a` | 6 files, +86/−13, identical with `--ignore-cr-at-eol` (no EOL churn). The files are exactly the 6 claimed | verified |
| HEAD → candidate EOL | `git diff --stat` equals `--ignore-cr-at-eol` (27 files, +3283/−131). All delta files are pure LF | verified |

**Delta content.** I read all 86 added lines. Nothing changed outside the findings:
- **`acra_api_marketplace_mock.py`:**
  - `_exact_count` and `_exact_amount` now reject `(bool, str)`;
  - two `whole_count` after-validators were added, on `_BusinessProfileShareholder` and
    `_BusinessProfileCapital`.
- **`registry.py`:** docstring only (`business_profile_holder_id`); no code change.
- **`test_business_profile_evidence.py`:** five added malformed cases.
- **`test_opq_garden_abc_scenario.py`:** two added tests (mixed-class rows; model invariant).
- **`ACRA_MOCK_API_PROFILE.md` and `DECISION_LOG.md`:** wording for string counts, the
  pseudonymous digest and `dateOfTransferOfRegistration`.

## 2. Findings

### P2-1: the decoder accepted JSON string counts. **RESOLVED**

- **Code.** `_exact_count` and `_exact_amount` raise on `bool` and `str` before pydantic's
  lax Decimal coercion. Each new `whole_count` validator raises when
  `value != value.to_integral_value()`. The capital variant is None-safe.
- **My probe** (`reqg-d088\probe_p2_1.py` → `probe_p2_1.out`, run against the worktree code
  with `app.__file__` checked). All string inputs are **refused**:
  - holder `"1000"`, `"1000.5"`, `"1e3"` and `" 1000 "`;
  - issued `"12.5"`;
  - amount `"1000"`.

  The other bad inputs are also **refused**: `1000.5`, `True`, `None`, `1e400` via
  `json.loads` (that is, inf), and non-JSON `Decimal("1000.5")` / `Decimal("12.5")`. The
  `whole_count` validators refuse `Decimal("2.5")` directly on both models.
- **The observed numeric shape still decodes.** These are **accepted**:
  - holder `1000` and `1000.0` → exact `1000`;
  - amount `1000` → `1000`, and `1000.0` → `1000.0`;
  - the fixture as-is, and after a `json.dumps`/`json.loads` round-trip (the production
    transport parses with plain `json.loads`).
- **Tests isolate the cause.** The two capital cases in `test_malformed_profiles_are_refused`
  have numeric controls that **decode**: issued `12` with no amount, and amount `1000`. So the
  `"12.5"` and `"1000"`-amount cases fail on the string rule and on nothing else. All 5 new
  cases are present (13 parametrized cases in total).
- **Mutants.** M14 (count accepts str) and M15 (amount accepts str) are KILLED. M17 (str
  accepted and the whole_count validators removed) is KILLED.
- **String amounts.** The open question ("decide and document whether string amounts are
  allowed") is decided in code and test: they are refused.

### P3-1: no mixed-class multi-row test (M02 survived). **RESOLVED**

`test_mixed_class_rows_that_total_the_issued_count_are_never_assumed_current` uses rows of
500 ORDINARY + 500 PREFERENCE over 1000 issued ORDINARY. It asserts:
- the result is RETAINED;
- both rows have `assumed_current=False`;
- there is no POC acceptance.

M02 is now **KILLED**, by exactly this test.

### P3-2: no direct model test (M10 survived). **RESOLVED**

`test_a_returned_status_can_never_be_recorded_as_assumed_current` checks three cases:
- assumed with no status → valid;
- a returned status with `assumed_current=False` → valid;
- a returned status with `assumed_current=True` → `ValidationError` matching "never replaced".

M10 is now **KILLED**, by exactly this test.

### P3-3: the `BP-` digest is pseudonymous, not irreversible. **RESOLVED (documented disposition accepted)**

- **Where it is documented.** Three places now state that the digest is unkeyed,
  pseudonymous, Mock-only, and that a keyed digest under a server-held secret is required
  before any non-Mock use:
  - the `business_profile_holder_id` docstring;
  - the D-088 decision entry;
  - the decoder bullet in `ACRA_MOCK_API_PROFILE.md`.
- **Mock-only is enforced in code, not only in prose.**
  - `supports_business_profile_evidence` delegates to the Marketplace-Mock-only
    `supports_shareholder_evidence`.
  - `RegistrySnapshotEntry` refuses non-`MOCK` environments for the profile contract.

  So no non-Mock provider can reach the digest.
- **Judgement.** For a Mock-only POC this disposition meets the owner constraint "do not
  retain personal identifiers":
  - the source identifier itself is never stored or projected;
  - the data source is the ACRA Marketplace Mock (test identities);
  - the repo fixture is synthetic;
  - the residual enumeration risk is now stated truthfully, and an explicit precondition
    blocks any non-Mock use.

  A keyed digest is preferable, but under a Mock-only scope it is not required.
- **Residual wording (observation, not a finding).** Two places still say "opaque":
  - `ARCHITECTURE.md` line 1104: "opaque holder digest";
  - the `MarketplaceBusinessProfileDecoder` class docstring: "the adapter's opaque digest".

  "Opaque" (meaning carries no visible meaning) does not claim irreversibility, so neither is
  false. Aligning them to "pseudonymous" in a later edit would be tidier.

### P3-4: `dateOfTransferOfRegistration` missing from the observed-shape list. **RESOLVED**

The observed-shape list now includes it. I compared the list against all 59 `field_paths` in
`acra-discovery\abc_bp_live.json`:
- **Entity keys:** all 12 top-level entity keys are covered (`uen`, `entityName`,
  `companyType`, `statusOfCompany`, `statusDate`, `dateOfTransferOfRegistration`,
  `businessActivities`, `officer`, `registeredOfficeAddress`, `shareholder`,
  `issuedShareCapital`, `paidUpCapital`).
- **Shareholder rows:** all 8 keys match.
- **Capital rows:** all 4 keys match.

## 3. Regressions

- **Related files (my run).** `PYTHONPATH=<worktree>/apps/backend` with `PHASE12_MONGO_URI`
  unset, `-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1`. I ran all 8 named files:
  - `test_business_profile_evidence`, `test_opq_garden_abc_scenario`,
    `test_opq_garden_sim_lim_scenario` and `test_poc_ownership_acceptance`;
  - `test_acra_api_marketplace_mock_connector`, `test_official_shareholder_evidence`,
    `test_hybrid_five_layer_overlay` and `test_simulation_calculation_status`.

  Result: **274 passed, 1 skipped** in 33.6 s. The skip is the physical-Mongo BP cache test
  (no URI configured). The JUnit file is `reqg-d088\related.xml`.
- **ruff 0.16.2 (check).**
  - From the repo root, on all changed or new `.py` files: all checks passed.
  - From `apps/backend` (`app tests`, matching the CI `ruff check .`): all checks passed.
- **ruff format (not a CI gate).** `acra_api_marketplace_mock.py` would be reformatted. This
  is pre-existing: the HEAD and `b23d03a` blobs have the same status, and the hunks fall
  outside the delta. The two new test files are format-clean.
- **mypy 1.20.2 (strict + pydantic plugin).** The cache directory was in scratch.
  - The 11 changed `app` modules: no issues.
  - `mypy app` (the CI gate): **no issues in 129 source files**.
- **`git diff --check`:** clean.
- **Untracked files.** Both tests are pure LF, with 0 trailing-whitespace lines, and end
  with LF. No untracked Markdown.
- **Doc and secret checkers (my runs):** `check_secrets`, `check_policy_authority`,
  `check_project_state` and `check_architecture` all PASS.

## 4. Evidence

- **Full backend (implementer): `full_backend_d088r.xml` / `.log`.**
  - **Freshness.** The latest candidate-file mtime is 2026-10-25 23:35:36 (+08), on
    `registry.py`, `acra_api_marketplace_mock.py` and the two docs. The tests were edited at
    23:35:10. The suite timestamp is **23:37:35**, so the run postdates every edit. The XML
    was written at 00:01:24. The tree recomputed now is still `a9b5c07`.
  - **Result.** 3350 tests, 0 failures, 0 errors, 6 skipped (all "Local Tesseract
    unavailable"). The log reads 3344 passed / 6 skipped. 3350 = 3343 (previous run) + 7 new
    test IDs, which matches.
  - **Contents.** The XML contains both new tests and 13 `test_malformed_profiles_are_refused`
    cases. `test_profile_cache_entries_survive_a_physical_mongo_store_and_coordinator_restart`
    ran and passed (physical Mongo).
  - **Verdict:** valid and current.
- **Multi-holder smoke C (implementer): `smoke_d088\d088_smoke_C.json`.**
  - **Result.** 16/16 PASS. The JSON was written at 23:36:25, and `backend_C2.log`
    (SETTINGS_OK for `garden_abc_multi_holder`) at 23:36:04. Both are after the 23:35:36
    edit.
  - **Vite.** `vite_C2.log` shows the new Vite failed with "Port 5799 already in use", so the
    22:47 Vite served the frontend. Vite serves the live worktree source, and the remediation
    delta has no frontend files. So the served frontend content is identical to the candidate
    either way.
  - **Backend.** The API results contain `OPQ_GARDEN_ABC_V1`, `LOCAL_POC_ISSUED_CAPITAL_BASIS`
    and a `GT-MOCK-` completion. This proves the proxied backend runs D-088 worktree code. It
    is not the unrelated main-repo dev server on :8000, which predates D-088.
  - **Limit.** I cannot independently prove that the serving backend process was the
    post-fix one rather than a surviving 22:47 instance. That would require the launcher's
    stderr or credentials, which I did not inspect. **It does not matter for validity.** The
    remediation changes only string and non-integral handling. The smoke fixture uses
    numeric counts, so pre-fix and post-fix backends produce byte-identical results on this
    path.
  - **Verdict:** valid as happy-path non-regression evidence for the candidate. It does not
    discriminate the delta, by design; the backend unit tests and mutants above cover the
    delta.
  - Currently nothing listens on 5799 or 8799, so the orphan is gone.
- **Full E2E: `d088-e2e\full_results.json`.**
  - 115/115 PASS, `mode full`, complete. It started 2026-10-25T14:48:05Z (22:48 +08) on
    `b23d03a` content.
  - **Not invalidated.** Under `DEVELOPMENT_WORKFLOW.md` "Evidence reuse and invalidation", a
    change invalidates only "the evidence it can reach". Here:
    - the only runtime change is inside the `businessProfile` decoder models;
    - `_exact_count` and `_exact_amount` have no other users;
    - the `registry.py` change is a docstring;
    - neither `apps/frontend/e2e` nor `scripts/run_e2e.py` references `businessProfile`,
      `business_profile`, `OPQ_GARDEN_ABC` or issued capital;
    - no shared owner, hotspot, composition, dependency or CI file changed.

    The E2E evidence carries forward.

## 5. Mutation table

The harness is `reqg-d088\mutate.py`, adapted from the previous QG. It ran on scratch copies
`reqg-d088\mut\<mutant>\apps\backend` with `PYTHONPATH=<copy>;<worktree>`, and `app.__file__`
was asserted to be inside each copy. The targets were `test_business_profile_evidence.py` and
`test_opq_garden_abc_scenario.py`, run with `-x`. Raw results are in
`reqg-d088\mutation_results.json` and `mutation_run.log`.

| # | Mutant | Result | Killing test (first failure) |
|---|---|---|---|
| M00 | control, unmutated copy | 49 passed / 1 skipped (previously 42+1; +5 cases, +2 tests) | — |
| M01 | drop the sum-equality check (spot-check) | KILLED | `test_incompatible_profiles_are_retained_but_never_accepted[rows short of issued capital]` |
| **M02** | drop the rows' common class/currency check | **KILLED** (survived before) | `test_mixed_class_rows_that_total_the_issued_count_are_never_assumed_current` |
| M05 | drop the returned-status check (spot-check) | KILLED | `test_incompatible_profiles_…[a returned status is never assumed away]` |
| **M10** | drop the `assumption_never_overrides_a_returned_status` validator | **KILLED** (survived before) | `test_a_returned_status_can_never_be_recorded_as_assumed_current` |
| M13 | decoder accepts fractional floats (spot-check) | KILLED | `test_malformed_profiles_are_refused[body0]` |
| M14 | `_exact_count` accepts `str` (P2-1 revert) | KILLED | `test_malformed_profiles_are_refused[body4]` |
| M15 | `_exact_amount` accepts `str` (P2-1 revert) | KILLED | `test_malformed_profiles_are_refused[body8]` |
| M16 | remove both `whole_count` validators | SURVIVED (**equivalent** for the production transport) | — |
| M17 | `str` counts accepted **and** `whole_count` removed | KILLED | `test_malformed_profiles_are_refused[body4]` |

**Why M16 is equivalent.** The decoder input comes only from `json.loads`, which yields only
`int`, `float`, `str`, `bool` and `None`. The before-hooks already refuse non-integral floats
and all strings, so a non-integral `Decimal` can never reach the after-validators. They are
defence in depth: they work when exercised directly (my probe), but no committed test drives
them. This is not a finding.

## 6. Not executed (no claim made)

- **Physical Mongo:** not run by me. No URI is configured in my environment, and `.env` was
  not accessed. I rely on the implementer's verified, post-edit XML.
- **Full backend:** not rerun (about 24 min). I verified the implementer's run from its XML
  and mtime.
- **Full E2E and the smoke:** not rerun. I verified them from artefacts and judged them still
  valid, as in §4.
- **Frontend:** vitest, `tsc` and the vite build were not rerun. The remediation delta has no
  frontend files.
- **Other checkers:** `check_external_provider_readiness` and `check_tooling_config` were not
  rerun. No connector config or tooling changed in the delta.
- **Not run at all:** live provider calls, hosted CI, `pre_pr_check.py` (the candidate is
  uncommitted and publication was not requested) and integration onto `a6e86fc` (not
  authorized).
- **Stray temp file:** one checker-output temp file was written to `/tmp/null_out` (Git Bash
  temp). It is outside the repo, holds only checker summary lines, and could not be removed
  (permission denied).

## 7. Verdict: **PASS**

All five previous findings are resolved correctly and without regressions:
- **P2-1:** strings are refused for counts and amounts, non-integral values are refused, and
  the observed numeric shape decodes.
- **P3-1 and P3-2:** the M02 and M10 mutants are now killed by the new tests.
- **P3-3:** the pseudonymous, Mock-only disposition is documented and backed by Mock-only
  enforcement in code.
- **P3-4:** the field list matches the live field paths.

The delta is confined to the findings. Related tests, ruff, `mypy app`, `git diff --check`,
whitespace and the doc and secret checkers pass. The full-backend evidence postdates the last
edit, and the smoke and E2E evidence remain valid.

**Graded findings:** P0 none, P1 none, P2 none, P3 none.

**Non-blocking observations** (no fix required for this gate):
1. `ARCHITECTURE.md` line 1104 and the decoder class docstring still say "opaque" digest. It
   is not false, but "pseudonymous" would be consistent with D-088.
2. The docs state that string *counts* are refused but do not mention string *amounts*,
   which code and tests also refuse. The docs are not wrong, because behaviour is stricter
   than the text.
3. The `whole_count` validators are untested defence in depth (M16 is an equivalent
   survivor).
4. The `ruff format` drift on `acra_api_marketplace_mock.py` is pre-existing and not a CI
   gate.

The next authorized action is the owner's decision. Integration onto `a6e86fc` (README-only
drift, no overlap), commit, push and publication all require explicit owner authorization.
