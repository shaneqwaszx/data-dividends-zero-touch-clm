# Integration D-113 + Prompt-10 UI + D-114: Quality Gate R1 (re-gate of the remediation)

Reviewer: the same independent quality-gate subagent as R0. It authored and fixed nothing in the reviewed content.
Date: 2026-11-02. R0 report: `INTEGRATION_D113_D114_PARTNER_SHARES_QUALITY_GATE.md` (verdict PASS WITH MINOR FIXES on `0416f99`).

## 1. Executive Result

**PASS**

- F1 is resolved: D-114 now states its scope.
- F2 is resolved: the code is fixed, and a regression test fails on the pre-fix code.
- The E2E and accessibility changes do not weaken any assertion; they make the checks stricter.
- There is no line-ending churn and no scope creep.
- F3 and F4 remain disclosure items for the PR body, as agreed. They are not code fixes.

## Frozen identity

| Item | Value |
| --- | --- |
| Worktree | `<workspace>/dd-clm-qg-review`, detached at `6350f9b652f1091a7e8f3782c13a38434c61b157`, clean before and after the review |
| Base | `origin/main` = `ae5946b` |
| Previous gate | R0 on `0416f99` |
| Delta reviewed | `git log 0416f99..6350f9b`: 18fb658, f8a4531, 47bf1e7, plus merges 877a5ad, d06f825, 6350f9b. 7 files, +56/−8 |
| Unchanged since R0 | All other files. R0 evidence for them is reused. |

## 2. Remediation checklist

| R0 item | Result | Evidence |
| --- | --- | --- |
| F1 (P3): the D-114 E1 wording claimed more than the code does | **Resolved** | `docs/decisions/DECISION_LOG.md:2109-2114` now says E1 to E3 govern the case's own identity. Subsidiary discovery keeps its existing read-only, fail-closed lookups, and routing those by UEN is listed as a follow-up for Shane. The wording now matches the code (`onboarding.py` subsidiary readers, unchanged). |
| F2 (P3): `uen_route` could describe the previous UEN after a same-type correction | **Resolved** | `apps/backend/app/services/onboarding.py:959-961` now sets `requested.uen_route = corrected_route` on every correction. `UEN_ROUTE_CHANGED` is still emitted only when the route type changes (`:962-981`). The regression test is at `tests/test_government_no_acra.py:248-275`. **I confirmed independently** that it fails on the pre-fix code: the 6350f9b tree with the 0416f99 `onboarding.py` swapped in fails at `assert corrected["case"]["uen_route"]["uen"] == "T99GB0198G"`. It passes on 6350f9b. |
| F3 (P3): editable agreement date | Disclose in the PR (agreed) | Unchanged by design. |
| F4 (P3): the e2e coverage reference | Disclose in the PR (agreed) | Unchanged. |

### F2 side effects checked

- **Unroutable UEN:** if the corrected UEN has no Singapore shape, `uen_route` becomes `None`. That is correct: it records no route rather than a stale one.
- **Recheck without an identity change:** the route is recomputed for the same UEN, so the value is the same. An older schema-17 case gains the field only on an authorised mutation, never on a read. Persistence semantics are unchanged.
- **No new ACRA path:** the change only sets a field.

## 3. New-content review

### `apps/frontend/e2e/database-classification.e2e.ts:44-56`

The partnership journey now drives the new form. Its assertions are equal or stricter:
- **Kept:** none of the 6 rows is pre-ticked, and the RM ticks each one explicitly. The POST to `/manual-ownership-evidence` must return under 300. The basis must read "RM-confirmed" afterwards.
- **Added:** the form heading is visible; the total shows "Adds up to 100%"; the confirmed summary heading is visible.
- **Changed:** the old step *typed* the date `2026-01-05`. The new step asserts that the date field is *pre-filled* with `2026-01-05`. This is consistent with the F3 behaviour (pre-filled, editable) and does not weaken the check.
- **Narrower selector:** the checkbox selector now excludes the "select all" header row. This keeps the count of 6 meaningful.

### `ConfirmPartnerShares.tsx:108-111`, `styles.css:3301`, `ConfirmPartnerShares.test.tsx:114-116`

- The hint moved out of the `<label>`, so the accessible name is now exactly "Agreement date (as-of date)".
- `aria-describedby` is kept. The unit test pins both the label text and the `aria-describedby` link.
- The CSS change adds one scoped rule.
- The request the form sends is unchanged.

### `DECISION_LOG.md`

The change only adds the scope paragraph. No other decision text changed.

### Hygiene

- **Weakened assertions:** none.
- **Scope creep:** none.
- **Line endings:** `git diff --numstat` and `git diff --ignore-cr-at-eol --numstat` for `0416f99..6350f9b` are identical (md5 `8d53c473…`), so there is no CRLF/LF churn.
- **Whitespace:** `git diff --check 0416f99 6350f9b` is clean.

## 4. Checks run (this gate)

| Check | Result |
| --- | --- |
| Backend, 13 affected files: `test_government_no_acra`, `test_uen_route`, `test_uen_route_persistence`, `test_zero_touch_entity_types`, `test_marketplace_mock_partnerships`, and every suite that drives identity correction or recheck (`test_garden_uen_partial_resume`, `test_phase13_auth_rbac`, `test_phase24_identity`, `test_phase24b_stage_recovery_round1`, `test_slice_a_legacy_compatibility`, `test_slice_g_target_reuse`, `test_target_reliability_recovery_ux`, `test_zero_touch_orchestration`) | 520 passed, 0 failed |
| Regression check for F2 (pre-fix `onboarding.py` swapped into a scratch export of 6350f9b) | Fails as expected on `uen_route.uen` |
| `ruff check --no-cache app tests` | All checks passed |
| `mypy app` | No issues in 132 files |
| Frontend vitest (`dd-clm-integration` checkout, HEAD = `6350f9b`, clean): `ConfirmPartnerShares`, `PartnershipAgreementDisplay`, `UenRoute` | 3 files, 34 passed |
| `tsc --noEmit` | Clean |

### Evidence reported by the author, not re-run here

- Full backend run on the integration head: 3407 passed, 181 skipped, 6 failed. All 6 are `test_s2_local_ocr.py::test_real_local_ocr_acceptance`, the known macOS font failures that also fail on main.
- Combined E2E on `0416f99`: 115/119. The failures were main's 3 known macOS failures plus the partnership journey that f8a4531 and 47bf1e7 fixed.
- Affected-selector E2E on `6350f9b`: 7/7.

I did not run E2E, as instructed, so no browser claim is made by this gate. The R0 physical Mongo evidence (133 passed) still applies: the delta touches no persistence code. This is all local evidence, not a hosted-CI PASS.

## 5. Security

No new security surface:
- The F2 change sets a field the system computes; it is never taken from a request (`extra="forbid"` still applies).
- The frontend changes affect labels and E2E only.
- Safety controls are untouched: the D-101 checks, RM confirmation, maker-checker, permission rechecks and the assistant's exact-line catalog.

## 6. Required Fixes

None.

For the PR body, as agreed:
- F3: the editable, pre-filled agreement date.
- F4: the government_identity scenario lists `database-classification.e2e.ts`, but that spec covers only the happy path.
- The changed `PartnershipAgreementDisplay.test.tsx` test 1 and the updated `database-classification.e2e.ts` partnership steps, for explicit review.

Owner decisions that remain:
- The D-113 and D-114 candidate status.
- Manifest commit `a90b6ea`.
- The D-114 subsidiary-routing follow-up.
- The synthetic-boundary drift, which was already on main.

## 7. Readiness

The candidate at `6350f9b` is ready for the pre-PR check on a clean committed tree and for the merge-readiness steps. Only Shane merges.

No Live ACRA or real GoldTier readiness is claimed.

## 8. Git Status

- **Reviewed worktree:** `dd-clm-qg-review`, detached at `6350f9b`, with no tracked, staged or untracked changes.
- **Integration checkout:** `dd-clm-integration` was used read-only.
- **Files written:** only this report, plus scratchpad temporary files (an export at `scratchpad/r1_export`, and the mypy cache).
- **Not done:** no implementation fix, commit, push or merge.
