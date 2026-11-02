# Integration D-113 + Prompt-10 UI + D-114 — Independent Quality Gate

Reviewer: independent QG subagent. It did not author or fix any of the reviewed content.
Date: 2026-11-02. This is a bounded integration gate, not a numbered phase gate.

## 1. Executive Result

**PASS WITH MINOR FIXES**

All three changes do what their decision entries and the brief say:
- D-113: Marketplace Mock partnerships take registry partners from current partner officers.
- Prompt-10: the "Confirm partner shares" UI.
- D-114: the UEN picks the register, and Government cases never reach ACRA.

Every case-identity path for a GA/GB or unsupported UEN avoids the ACRA provider: creation, correction verification, Search recheck re-acquisition, and cache-off. The D-101 cross-checks, RM confirmation and permission paths are unchanged. Persistence is strict and does not rewrite stored data. No P1 or P2 defect was found.

Two bounded fixes remain:
- **F1:** a scope sentence for the D-114 decision text.
- **F2:** keep `uen_route` in step with the corrected UEN.

Two items should be disclosed in the PR (F3, F4). None of them is a security, false-success or safety-control problem.

## Frozen identity

| Item | Value |
| --- | --- |
| Worktree | `<workspace>/dd-clm-qg-review` (detached, clean, `git status --short` empty before and after the review) |
| HEAD | `0416f99b35c2a9b1f2834a6f49123aa6b35ff019` (`feat/integration-d113-d114-partner-shares`) |
| Tree | `23ba1bddae325693f6853ba4291dd73ba226d56d` |
| Base | `origin/main` = `ae5946b1c3d20fa1c1aaf9f51fbed852db3e1e24` (an ancestor of HEAD) |
| Diff identity | `git diff ae5946b 0416f99 \| shasum -a 256` = `25be981774f677b357d4682e31acf0a9c7efaf9b49fadbc209fcd350e91cf649` |
| Scope | 64 files, +2437/−115 (`git diff --stat`) |
| Commits | 64092ac, 4ae6904, cf03d81 (D-113); 5df9edf, 09c143c (UI); 87535ca, ed7e856, a90b6ea, 3617cd0 (D-114 and its manifest/doc commits); 0bb56d7, 417557f, 3fa2960, 333fe05, 0416f99 (merges) |
| Frontend test checkout | `<workspace>/dd-clm-integration` HEAD = `0416f99` (same commit, clean), used read-only for its `node_modules` |

## 2. Acceptance Checklist

| # | Requirement | Result | Evidence |
| --- | --- | --- | --- |
| A1 | D-113 M1: only the closed list of partner positions becomes `PARTNER`, in the Marketplace connector only; the shared role pattern and the BizFile decoder are unchanged | Met | `acra_api_marketplace_mock.py:51-55,73-112,453`. The mapping runs on a copy of the body. An unlisted position is left for the strict decoder, which fails the operation (tested, `test_marketplace_mock_partnerships.py:128-143`). |
| A2 | D-113 M2: a partner row that is not Active and has no withdrawal date fails closed | Met | `acra_api_marketplace_mock.py:101-105`. Parametrised over Withdrawn, Ceased, `""` and `3`. A `withdrawalDate` of `""` cannot become `None`: `_RealOfficer.withdrawal_date: date \| None` (`acra_bizfile_sandbox.py:203`) rejects it, so it also fails closed. |
| A3 | D-113 M3: officers are used only for `BUSINESS_PARTNERSHIP`, with no relationships, no listed seed partners, `OWNERSHIP_PARTIES` UNSUPPORTED and MOCK provenance | Met | `partnership_agreement.py:27-61`. UNSUPPORTED is set only by `_unsupported_ownership`, under `_company_shareholders_only` and a non-company legal form (`connectors/registry.py:400-411,536-541`). The Live environment is excluded by the MOCK provenance guard. |
| A4 | D-113 M4: the D-101 cross-checks are unchanged | Met | The only change in `partnership_agreement.py` is `registry_partner_names`. The tests for ALLIE / RAIN JORDON pass at service and API level. |
| A5 | UI sends the same API payload shape and does not compute UBO or registry decisions in the browser | Met, with F3 | `ManualOwnershipEvidenceForm.tsx` partnership mode reuses the same `submit()` (lines 213-254). The summary reads `partnership_state`, the receipt and the server's `candidates[].classification` (`ConfirmPartnerShares.tsx:21-45`). The browser computes only a display total, and the server re-checks everything. The as-of date behaviour changed: see F3. |
| A6 | D-114: no GA/GB or unsupported UEN reaches the ACRA provider on any case path | Met for case identity; F1 for subsidiary discovery | See the path table in §4. |
| A7 | D-114: rules BPD-GOVERNMENT-IDENTITY-1 and BPD-UEN-ENTITY-TYPE-1 send the case to the existing identity correction | Met | `blocker_decision_policy.py:175-215`. `api_models.py:1092-1124` adds the cards. Intake and orchestration lists are updated consistently (`zero_touch_orchestration.py:2434-2439,4602-4604`, `App.tsx:126-150`). |
| A8 | Persistence: schema 18, a strict schema-17 reader, no rewrite on read, stable fingerprints, CAS unchanged | Met | `persistence/models.py:829,848-888,1075-1083`; `mongo_case_store.py:93-95,609-626,708-711`. `uen_route` uses `exclude_if=None` (`domain/models.py:1091-1095`). The store still reads schemas 1 to 16. CAS, create and update code is untouched. Physical Mongo run passed (§4). |
| A9 | Demo Parks renumbered: fixture, PDF, README hash, docs | Met | The PDF SHA-256 `bbd0fd4d…8e96` matches the README and `synthetic_eligibility.json`. `T99FY0105G` appears only in history and decision text, and as the "unsupported" test row. |
| A10 | Assistant code unchanged apart from the regenerated manifest | Met | `git diff --stat ae5946b 0416f99 -- apps/assistant` touches only `synthetic_eligibility.json`, which is in its own commit `a90b6ea` for Shane to accept or drop. |

## 3. Contract and Integration Findings

- **F1 (P3, decision wording vs implementation).** D-114 E1 says GA/GB UENs use "the government register only, never the ACRA provider". The implementation enforces that for the **case's own UEN** only.
  - `OnboardingService.acquire_subsidiary_registry_evidence` (`apps/backend/app/services/onboarding.py:2053-2104`) has no `route_uen` gate. Neither do `acquire_subsidiary_shareholder_evidence` (`:2106-2152`) or `acquire_subsidiary_business_profile_evidence` (`:2154-2200`).
  - Recursive ownership discovery (`ownership_discovery.py:433`) therefore looks up a GA/GB corporate shareholder UEN through the ACRA provider, or through `coordinator.acquire`.
  - Why it matters: government holders such as ministries and statutory boards are realistic shareholders. The decision text over-claims, or the gate is missing.
  - Impact: no wrong identity results, because the lookup is still read-only, fails closed and lands on the Mock lane.
  - Fix (owner's choice): add one sentence to D-114 that E1 governs the case identity and that corporate-holder discovery is unchanged; or gate the three subsidiary readers on `route_uen`.
- The D-113 boundaries hold. Officer partners cannot appear outside the Marketplace Mock lane or for non-partnerships (A3). The D-101 seed path (Gamma) has priority because `listed` comes first.
- Later sponsor dependencies (not current blockers): Q-012 (Live partner position wording), the provisional UEN PQ-code source, and Shane's decisions on the D-113 and D-114 candidates and on manifest commit `a90b6ea`.

## 4. Tester and Adversarial Findings

### ACRA call paths for GA/GB and unsupported UENs (reviewed by hand)

| Path | Code | Result |
| --- | --- | --- |
| Creation, coordinator present | `onboarding.py:2228-2264` | UNSUPPORTED stops first. GB reads the government register only, then `GOVERNMENT_IDENTITY_NOT_FOUND`, or uses the register bundle (`:2266-2267`). An ACRA-format UEN with a government record gets `ENTITY_CATEGORY_MISMATCH` before any ACRA call. |
| Creation, cache off / no coordinator | `_read_government_register` `:2202-2213` returns `None` | GB → `GOVERNMENT_IDENTITY_NOT_FOUND`. Never reaches `registry_provider.retrieve_acquisition` (`:2268-2274` is only for the ACRA route). |
| Correction verification | `_verify_registry_correction` `:1209-1272` | UNSUPPORTED raises before any read. GB uses the register or raises. The provider path runs only for the ACRA route, and only with no government record. |
| Search recheck re-acquisition | `:993`, `:1065` → `_acquire_registry_after_identity_recheck` → the same gate (`verified` is either the gated verification or the retained bundle) | Covered. |
| Subsidiary discovery | `:2053-2200` | Not gated (F1). |
| `UenRoute` vs `is_eligible_singapore_uen` | `uen_route.py:16-18` vs `jurisdiction.py:9-11` | The route accepts a superset of eligible UENs, so every eligible UEN gets a route (no `None` gap). |

### Commands and results

| Check | Result |
| --- | --- |
| Focused backend run: 24 files, D-113/D-114 and every changed teammate test that runs without Mongo, plus the happy-path and registry demo suites (`APP_ENV=test python -m pytest -p no:cacheprovider …`) | Exit 0. 1026 collected: 1023 passed, 3 skipped. |
| Physical Mongo: my own throwaway `mongod` on 127.0.0.1:27199 (stopped afterwards). `PHASE12_MONGO_URI=… pytest` on `test_zero_touch_entity_types_real_mongo`, `test_recursive_ownership_real_mongo`, `test_synthetic_company_pack_real_mongo`, `test_document_digests_real_mongo`, `test_phase12_real_mongo`, `test_classification_conflict_real_mongo` (+ `test_slice_a_legacy_compatibility`) | 133 passed, 0 skipped (42 of them physical, none skipped). |
| Frontend (read-only checkout at the same commit): `vitest run ConfirmPartnerShares.test.tsx PartnershipAgreementDisplay.test.tsx UenRoute.test.tsx` | 3 files, 34 passed. |
| Frontend typecheck: `tsc --noEmit -p .` | Clean. |
| `ruff check --no-cache app tests` | All checks passed. |
| `mypy app` (cache in scratchpad) | No issues in 132 files. |
| `build_synthetic_eligibility.py --check` (HEAD) | Current. |
| `build_synthetic_boundary.py --check` (HEAD) | Not current. Also not current on an export of `ae5946b`, where eligibility is also stale. This drift was already on main; the branch adds none. |
| Line endings: `git diff --numstat` vs `git diff --ignore-cr-at-eol --numstat` | Identical, so there is no CRLF/LF churn. |
| `git diff --check ae5946b 0416f99` | Clean. |

The author's full-suite, full physical Mongo (177/177), full frontend and `pre_pr_check.py` results were not re-run in full. My focused runs are consistent with them.

**Not run, by instruction:** E2E, which includes `database-classification.e2e.ts` with the renumbered UEN; it is being run separately. No browser-level claim is made here.

### Teammates' tests that were changed

Every change is a legitimate consequence of schema 18, the new catalogue entries or the UEN renumbering. None weakens an assertion:
- Schema pins move from 17 to 18, and the "unknown version" probes move from 18 to 19.
- Legacy-envelope builders drop `uen_route`, mirroring the existing D-101 pops.
- `expected["onboarding"]["uen_route"] = None` appears where an upgraded old envelope is re-encoded. The store writes every declared field, as it already does for D-101.
- Catalogue counts go from 63 to 66 (+3 codes).
- `T99FY0105G` → `T99GB0105G` in `test_synthetic_company_pack_real_mongo.py:76` and `database-classification.e2e.ts:11`.
- `test_recursive_ownership_real_mongo.py:378` also `$unset`s `onboarding.uen_route` for the schema-13 relabel.
- `test_zero_touch_entity_types_real_mongo.py` gains stronger assertions (route stored and kept across a restart).

`PartnershipAgreementDisplay.test.tsx` test 1 replaces the `source_selection` select assertion with the partnership heading and the "Partnership agreement" select. The default to DOCUMENT_OBSERVATIONS is still implied, because the heading renders only in that mode, and `ConfirmPartnerShares.test.tsx:180-195` asserts `source_selection: "DOCUMENT_OBSERVATIONS"` in the payload. I accept this, but list it for explicit review in the PR.

**Weakened assertions: none found.**

## 5. Code and Architecture Review

- **F2 (P3, audit accuracy).** `uen_route` is updated on a correction only when the route *category* changes (`apps/backend/app/services/onboarding.py:953-976`). Otherwise it is updated only when the registry is re-acquired (`:2230`).
  - The case: a correction that is not registry-verified, where the Search result is REVIEW_REQUIRED or FAILED, so `:1059` does not re-acquire, and the route category stays the same. Examples: GB → GB, or Format B → `…LL…`.
  - The result: the saved case keeps a `uen_route` whose `uen`, PQ code and description belong to the previous UEN, and the Registry section shows the old "Entity type from UEN" line.
  - D-114 E6 calls this field the audit record of how the case was routed, so it can disagree with `requested_uen`.
  - Fix: on every identity change, set `requested.uen_route = corrected_route`, or clear it to `None` until routed. Keep the `UEN_ROUTE_CHANGED` event only for category changes.
- **F4 (P3, test evidence mapping).** `_SCENARIO_TESTS["government_identity"]` (`apps/backend/app/services/blocker_decision_policy.py:1325-1328`) and the generated guide list `apps/frontend/e2e/database-classification.e2e.ts` as coverage. That spec only runs the Government happy path with the renumbered UEN; it does not exercise the three stops. The guide's "Unit-only coverage" limitation line mitigates this. Either drop the e2e reference or note that it covers the happy path only.
- Design is sound:
  - The code lists live in one module (`domain/uen_route.py`).
  - `read_government_register` takes no provider, so it cannot call ACRA by construction.
  - The routing decision is frozen with `extra="forbid"`, set only by the system, and rejected on requests (422, tested).
  - `ENTITY_CATEGORY_MISMATCH` is a sensible guard against misfiled register data.
  - Coupling grows modestly in `onboarding.py`; this is acceptable.
- Scope: the three changes stay within their briefs. The `styles.css` additions are scoped to `.partner-shares*`.

## 6. Security Review

- **Requests:** no new request-controlled authority. `uen_route` cannot be set from a request (`extra="forbid"`, 422 tested). `entity_category` is rejected.
- **Browser:** shows only the backend's description string. React escapes it, and the backend message includes only the code-list text or the 2-character PQ code (pattern `^[A-Z0-9]{2}$`).
- **Errors and secrets:** no PII, secrets or raw provider errors are added to messages. The connector raises `AcraMalformedResponseError` without echoing the row.
- **Safety controls not weakened:**
  - the D-101 cross-checks, RM confirmation and the version-checked Government status confirmation;
  - permission rechecks (the `ownership_edit_authorized` gating is unchanged in `CaseDetail.tsx`);
  - the assistant's exact-line catalog and code (only the manifest commit changes).
- **Maker-checker:** no code path touching it changed.
- **Data:** no `.env` file was read. No sponsor artefacts. The fixture PDF is fictional and re-hashed.

## 7. Required Fixes (bounded; re-check the delta only)

1. **F1:** state the D-114 E1 scope (case identity only; corporate-holder discovery unchanged), or add a `route_uen` gate to the three subsidiary readers. Owner's choice.
2. **F2:** keep `OnboardingCase.uen_route` consistent with the corrected UEN on every identity change, and add a test for a same-category correction without registry verification.

Disclose in the PR (no code change required):
- **F3 (P3):** in partnership mode the as-of date is pre-filled from the agreement and is **editable**. `ManualOwnershipEvidenceForm.tsx:158`, `ConfirmPartnerShares.tsx:108`, tested at `ConfirmPartnerShares.test.tsx:113-117,182-191`. Before, a single selected source date was read-only ("selected source dates stay historical", `ManualOwnershipEvidenceForm.tsx:310,314`). The payload shape is identical, but `as_of_date` can now differ from the agreement's recorded date, and the backend does not bind it (`manual_ownership_evidence.py:297` checks only for a future date).
- **F4:** the test reference clarification.
- The changed `PartnershipAgreementDisplay.test.tsx` test 1, for explicit review.

Owner decisions that remain and are not defects: D-113 and D-114 candidate status, manifest commit `a90b6ea`, and the boundary drift that was already on main.

## 8. Readiness

- After F1 and F2 are corrected and their delta is re-checked, the integration is ready for the pre-PR steps and the separately running full E2E.
- This gate gives no hosted-CI PASS (CI is billing-blocked, and there is no assistant CI job). The E2E result is outside this gate.
- Live ACRA and real GoldTier readiness are not affected and not claimed. Everything here is Mock or Local evidence.

## 9. Git Status

- Reviewed worktree `<workspace>/dd-clm-qg-review`: detached at `0416f99`; no tracked, staged or untracked changes before or after the review.
- `<workspace>/dd-clm-integration` was used read-only (vitest/tsc wrote nothing tracked).
- The main checkout was not touched.
- Files written: only this report and scratchpad temporary files (a `git archive` export of `ae5946b`, a mypy cache, and a throwaway mongod data directory, since stopped).
- No implementation fix, commit, push, merge or next phase happened.
