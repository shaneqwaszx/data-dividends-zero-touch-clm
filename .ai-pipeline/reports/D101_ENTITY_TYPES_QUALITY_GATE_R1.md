# D-101 Partnership and Government entity types — independent Quality Gate recheck (R1)

**Date:** 2026-10-30.
**Reviewer:** the same independent reviewer as R0, running `fyp-quality-gate`.
**Scope:** only the delta since the R0 FAIL on `20ee88d`. Unchanged R0 evidence is reused.
**What the reviewer did not do:** edit, stage, commit, push, merge, reset or stash; read `.env`; rerun the full E2E.
**What the reviewer did:** wrote only this file, and used Mongo only on the ephemeral 127.0.0.1:27188 instance (through `run_e2e.py`).

## Executive result

**PASS.** P0/P1/P2 = 0/0/0. Three P3 notes remain, and none of them blocks.

All R0 blocking findings are closed:
- P1-1 (the phase_07 CI test) is fixed.
- P2-1 (stale integration) is fixed: the branch now contains the latest origin/main.
- P2-2 (a vacuous assertion) is fixed.

## Reviewed identity

- **HEAD:** `1a6fe8ce8084bc6229376949c6b5ebdcfd2ad204`, tree `af1d83c867987bcff66c88131d50222b75e09049`.
- **Working tree:** clean.
- **origin/main:** `7e5653d51cbaf3cde5a7eff35789ede7260cca55` (#140). This is an ancestor of HEAD.
- **Delta since R0:**
  - `899c64d` "fix: D-101 QG R0 follow-ups": 5 files, +15/-10.
  - Merge `1a6fe8c` of origin/main, which brings in D-102 to D-106 (#137 to #140).
- **Line endings:** `--numstat` equals `--ignore-cr-at-eol` against origin/main.
- **Whitespace:** `git diff --check origin/main...HEAD` is clean.
- **Conflict markers:** none in docs, apps, tests or scripts.

## Delta review

### Fix commit `899c64d`

**P1-1, closed.** `tests/test_phase_07_delivery_assets.py:58` now adds `demo-gamma-partnership-agreement.pdf` and `demo-parks-government-status.pdf` to the existing scanned-PDF exclusion set.
- These two files sit alongside the other image-only database scans. Their hashes are already indexed in the zero-touch-database README.
- The `expected` set and its README-index assertion are unchanged. That keeps the curated text-PDF pack bounded.
- This is a teammate test that was changed, but only by extending an existing exclusion list for the same class of asset. It is superseded, not weakened. **List it in the PR.**
- Rerun: `unittest discover -s ../../tests -p test_phase_07_delivery_assets.py` gives OK.

**P2-2, closed.** `test_government_happy_path_reaches_ready_for_approval_without_ownership_step` now reads `bundle.clm.get_for_case(...).submission_snapshot` and asserts:
- the snapshot is not None;
- `ownership_reference.status == "GOVERNMENT_STATUS_CONFIRMED"`;
- `provisional_ubo.candidate_count == 0`;
- `internal_party_ids == ()`.

The `if snapshot:` guard is gone, so the assertion is no longer vacuous. This matches the reviewer's R0 probe.

**P3-1, closed.** The signatory wording is corrected:
- `DECISION_LOG.md` D-101 now says "appear only on the status document ... The case page says so".
- UAT step 3 says the same.
- Both now agree with `GovernmentStatusPanel.tsx`.

**P3-2, closed.** The PROJECT_STATE "Open" items are refreshed.

**P3-3 and P3-4:** left as they were in R0. They remain non-blocking notes.

### Merge `1a6fe8c` of origin/main (D-102 to D-106)

Main's delta (92 files) is mostly assistant, Support role, AI console and admin-credential work. The backend parts of main's delta that touch this branch are `api_auth.py`, `authorization.py` (new `RouteAccess.CASE_READ`), `domain/access.py`, administration and composition.

**RBAC resolution is correct.** `test_phase13_auth_rbac.py` asserts 87 routes in total, with CASE_SCOPED 45 and CASE_READ 2. That is main's 44 CASE_SCOPED plus the one D-101 route.
- D-101's `government-status-confirmation` stays CASE_SCOPED.
- Main's generic test now iterates CASE_SCOPED and CASE_READ, so it covers the new route. A cross-team or absent case gets an identical 404.
- Main's Support test shows SUPPORT gets "absent" on every other case route. So SUPPORT cannot confirm Government status.

**Support visibility (observation).** SUPPORT (D-103) can GET the zero-touch case summary. That summary now includes `entity_type_basis`: the derived labels, the founding instrument of a fictional body, and the confirming actor id. This is the same class of case data the summary already exposes, and `ownership_edit_authorized` stays false for SUPPORT. No new sensitive field is introduced.

**Schema.** Main is still on schema 16, so D-101's v17 stands. No other schema bump collides.

**DECISION_LOG.md.** D-101 sits before D-102. D-103 and D-104 appear out of numeric order, but that order comes from main and is not from this branch.

**PROJECT_STATE.md.** Both sides are kept. `case_envelope_schema_version` is 17 and `check_project_state` passes.

**Assistant manifests.** Both `--check`s report current after the merge.

## Evidence

### Reruns by this reviewer at 1a6fe8c

| Check | Result |
|---|---|
| `pytest test_zero_touch_entity_types.py test_phase13_auth_rbac.py test_entity_types_persistence.py` | all passed (210 tests, no failures) |
| `unittest test_phase_07_delivery_assets.py` (CI command) | OK |
| `check_project_state.py` / `check_architecture.py` | PASS / PASS |
| assistant `build_synthetic_boundary.py --check` / `build_synthetic_eligibility.py --check` | current / current |
| Focused E2E on a clean committed tree, HEAD 1a6fe8c, origin_main 7e5653d (`scratchpad/qg-d101-r1-e2e-focused-1a6fe8c.json`) | 6/6 PASS. The tests are database-classification 197/202/207/212 (Alpha, Partnership, Government, conflict), s3-sandbox-submission:752 and slice-b-registry-demo:132 (Garden). |

### Caller evidence on 1a6fe8c, reused

The reviewer did not rerun these:
- ruff and mypy are clean.
- Backend: 3337 passed. The only failures are the 6 `test_s2_local_ocr` macOS font failures.
- Physical Mongo: 177/177.
- Assistant: 2954 passed, plus the 1 known timing flake `test_d098_recovery`.
- tsc and build pass.
- Vitest: 1277/1278. The one failure is ViteHistoryFallback, which fails on macOS only.

These counts are consistent with R0 plus main's added tests.

### Does the R0 full-E2E evidence still stand?

The R0 full keep-going run (`d101-e2e-full-e6b439f.json`, 112/117) is judged to still stand for the D-101 surface, with one condition: the residual risk is main's own surface, which is out of this gate's scope.
- The only D-101 changes since R0 are test and docs edits (`899c64d`).
- Main's delta touches assistant, Support, AI console, admin bootstrap and `e2e_backend_server.py`. It does not touch any D-101 page or flow.
- The 6 selectors that exercise D-101 (all three entity journeys plus the two Garden fixes) pass on the merged HEAD.
- The remaining R0 failures (onboarding-recovery:6, s3-sandbox-submission:232, slice-c-recovery:294) are the known main failures.

The full suite runs once, at final acceptance, if the change class requires it. All evidence here is local, not hosted CI. Hosted CI remains billing-blocked.

## Findings (non-blocking)

- **P3-1 (new, nit).** Two places still call the signatories "two display-only authorised signatories":
  - `docs/demo/ZERO_TOUCH_DATABASE_HAPPY_PATH_UAT.md:160`;
  - `apps/backend/tests/fixtures/uat/zero-touch-database/README.md:53`.

  Both describe the PDF's content, so the wording is accurate in context. They could say "on the document only" to match the corrected text elsewhere.
- **P3-3 (carried over).** `blocker_decision_policy.py` maps the `government_status` scenario only to the backend test. The browser journey now exists.
- **P3-4 (carried over).** Two observations:
  - The partnership readiness re-check runs only in the `ANALYZED` branch. It is unreachable for Gamma today.
  - After a second matching letter revokes the confirmation, no Government hold is reopened. This is safe: Send is refused.

## Readiness

The candidate is ready for `pre_pr_check.py` on this clean committed tree, and then for the push request to Tasha. The PR must:
- say "Needs Shane to confirm D-101 and the listed defaults";
- list every changed teammate test, including the R1 `tests/test_phase_07_delivery_assets.py` exclusion;
- note the manual-CI exception for Shane.

Real ACRA and GoldTier readiness is unaffected and out of scope.

VERDICT: PASS
