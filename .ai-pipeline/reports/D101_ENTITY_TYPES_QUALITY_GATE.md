# D-101 Partnership and Government entity types — independent Quality Gate

Date: 2026-10-30. A fresh, independent reviewer ran this under `fyp-quality-gate` (plus the
persistence-schema-change and integration-security-review concerns). Change classes:
BACKEND_DOMAIN, BACKEND_API, PERSISTENCE (schema v17), FRONTEND_UI, AUTH (new CASE_SCOPED route),
and the regenerated apps/assistant D-094 manifests. This file is the only file the reviewer wrote. The
reviewer did not edit, stage, commit, push, merge, reset or stash anything and did not read `.env`. Mongo
use was limited to the ephemeral 127.0.0.1:27188 instance, through `run_e2e.py`. The full E2E suite was
not rerun.

## Executive result

**FAIL: P0/P1/P2/P3 = 0/1/2/4.** The product behaviour is sound: the partnership checks fail closed,
Government status is never set automatically, the confirmation route is authenticated, case-scoped and
version-checked, and schema v17 is strict. One check that hosted CI requires now fails deterministically
because of this branch (P1-1). In addition, origin/main moved during the gate, so the candidate is no
longer integrated with the latest main (P2-1).

## Reviewed identity

- Worktree `/Users/tasha/Documents/GitHub/dd-clm-entity-types`, branch `feat/zero-touch-entity-types`.
- HEAD `20ee88d72ca41e1ea56316d6b059d9034221a17b`, tree `5a1e5b72507399c8e5374f2776133382ec62d590`. The
  working tree is clean with no untracked files.
- The merged base is origin/main `859b8f0ebc8faf8ee83097234ec408eba98a6273` (an ancestor of HEAD). It has 90
  files and +3125/-282 lines against that base.
- During the gate, origin/main advanced to `0c6a6325e8ad9bdc650c72824124a4d0f2fc863f` (#137, D-102). That
  commit is **not** merged into this branch, and `git merge-tree` reports content conflicts in
  `docs/PROJECT_STATE.md` and `docs/decisions/DECISION_LOG.md`.
- Delta e6b439f..20ee88d: only `apps/frontend/e2e/s3-sandbox-submission.e2e.ts` and
  `apps/frontend/e2e/slice-b-registry-demo.e2e.ts` (+3/-2). Backend, frontend source and assistant evidence
  produced on e6b439f is therefore valid for these paths.

## Assessment against the requirement (prompt 8) and D-101

### Partnership (Gamma)
- The registry seed lists P1..P6 by name with `source_category="PARTNER"` and has no relationships. It is
  a PARTIAL bundle with the issue "Partners are listed without shares" (`scripts/zero_touch_happy_path_fixtures.py`).
  Alpha, Beta and Delta are unchanged (`SHARE_COMPANIES`).
- Extraction is an exact-label regex (`connectors/local_pdf_idp.py` `_PARTNER_SHARE`) bound to the
  document's single labelled UEN. A conflicting `Agreement Date` produces no rows. Each row is an
  `OwnershipObservationValues` on the existing document-ownership path; no second path was added.
- Cross-checks (`services/partnership_agreement.py`) cover: missing agreement, low confidence or a
  non-HIGH score, wrong entity, duplicates, shares that are not positive, a Decimal total that is not
  exactly 100, a registry partner missing from the agreement, an extra partner, and a declaration that
  differs from the agreement (Counter equality). They run in two places:
  - at submission (`ZeroTouchOrchestrator._require_partnership_agreement_match`), which refuses even a
    user-supplied "corrected" split;
  - again at readiness (`clm_orchestration._partnership_agreement_issues`), bound to the receipt's exact
    document version.
- Nothing is auto-accepted. Before RM submission the ownership is REVIEW_REQUIRED with no relationships.
  The form preselects the agreement but leaves every row unticked, and E2E asserts `not.toBeChecked()`.
  The E2E also asserts the computed UBOs P1 30% and P2 25%.
- Labels read "from partnership agreement, awaiting RM confirmation / RM-confirmed" and never say ACRA or
  registry.
- Observation (P3-4): the readiness re-check runs only in the `ANALYZED` branch. A REVIEW_REQUIRED
  analysis carrying a D-082/D-085 POC acceptance would bypass it. `eligible_poc_acceptance` needs a
  scenario-declared basis that Gamma does not have, so this is not reachable today.

### Government
- `RegistryLegalForm.GOVERNMENT` covers only the exact value "GOVERNMENT". Other values ("GOVT",
  "STATUTORY BOARD", …) stay `OTHER`, and a test covers this.
- `government_profile_applies` requires KYC type Government **and** the exact legal form.
- The evidence (`services/government_status.py`) must be exactly one current REVIEWED document with:
  - no semantic blockers, so the legal name and UEN must match the case entity;
  - exactly one HIGH-confidence `Founding Instrument`;
  - exactly the two labels `KYC Customer Type: Government` and `Client Segment: DI - Government`.
  A label alone never qualifies.
- The confirmation route `POST /api/clm/zero-touch/cases/{case_id}/government-status-confirmation`:
  - is CASE_SCOPED in `ROUTE_POLICIES` and is covered by the generic cross-team/absent-case 404 test;
  - uses `build_case_reauthorizer(require_creator=True)` inside the case lock;
  - repeats the creator check in the service and requires an open GOVERNMENT_STATUS_REQUIRED hold,
    WAITING_FOR_REVIEW and no target execution;
  - is CAS-checked on automation version and case event count, plus an exact document id and event count;
  - binds the evidence by fingerprint.
  The confirmation is honoured only while it stays bound to the current evidence. Readiness, the
  snapshot check, `_government_gate` and the browser projection all recompute it.
- No ACRA verification is claimed. The registry issue says "Not ACRA-registered", the basis label says
  "not ACRA-registered; government status from reviewed document", and `registry_evidence_binding` is
  None (never a CACHE_HIT). `GOLDTIER_REGISTRATION_TYPE_POC_VALUE` staying "ACRA" is owner-approved.

### Compatibility table
- `bounded_classification_compatible` maps Company only to COMPANY, Partnership to
  BUSINESS_PARTNERSHIP/LLP/LP, Sole Trader to BUSINESS_PARTNERSHIP and Government to GOVERNMENT. A
  mismatch is UNSAFE and goes to manual review.
- OTHER or a missing form is UNSAFE for automatic (DOCUMENT) candidates and allowed for a manual pick
  (owner-approved).
- The existing private-company/Government message is kept.
- Every cell is tested in both automatic and manual mode.

### Persistence (schema v17)
- `CASE_SNAPSHOT_SCHEMA_VERSION = 17`. There is a strict `DurableCaseSnapshotV16` reader, and
  `reject_entity_type_legacy_fields` runs for schemas 1..16. Schema ≤16 rejects each of the following,
  even when null or empty: the confirmation, the observations, the GOVERNMENT legal form,
  PARTNERSHIP_AGREEMENT_SHARE discrepancies (including in prior analyses), the Government hold, and the
  Government readiness blocker.
- A v16 read upgrades without rewriting the stored envelope.
- `exclude_if` keeps the new fields out of `model_dump` while they are empty, so fingerprints of older
  cases are stable (`test_d101_fields_do_not_change_dumps_of_cases_without_them`).
- Physical Mongo round-trip and restart tests were added (`test_zero_touch_entity_types_real_mongo.py`,
  2 tests).

### Teammate test assertions changed (git diff origin/main...HEAD -- '*test*' '*e2e*')
All of these are judged **superseded**, not weakened:
- **Schema 16→17 bumps.** About 25 files assert `schema_version == 17`. Unknown-version probes move
  17→18. Legacy fixtures strip the D-101 keys via the new `without_d101_fields` / `omit_session2_fields`,
  and expected re-encodes add `government_status_confirmation: None` and
  `government_status_observations: []`. This is a mechanical consequence of v17, and the strictness
  tests are kept.
- **RBAC.** `test_phase13_auth_rbac.py:1160/1167` changes 86→87 routes and CASE_SCOPED 46→47 (the new
  route).
- **Blocker catalogue.** `test_slice_c_blocker_catalogue.py` changes 62→63 (+GOVERNMENT_STATUS_REQUIRED).
- **Seed counts.** 8→9 (Government seed) in `test_synthetic_company_pack*.py`,
  `test_zero_touch_database_*`, `test_sponsor_demo_real_mongo.py` (9→10 docs), plus a PARTIAL status
  for Gamma and Government.
- **Gamma removed from share-graph parametrisations (COMPANIES→SHARE_COMPANIES):**
  - `test_zero_touch_database_happy_path.py` (2 tests);
  - `test_zero_touch_database_real_mongo.py`;
  - `test_synthetic_company_pack.py`;
  - `test_target_classification_continuation.py`.
  This is a coverage move: the Gamma journey now lives in `test_zero_touch_entity_types.py` and the
  database-classification E2E.
- **Garden uses Partnership - Unregulated (option A, owner-approved):**
  - `test_post_uat_remediation.py:235`;
  - `test_slice_b_registry_demo.py:84`;
  - `s3-sandbox-submission.e2e.ts:529`;
  - `slice-b-registry-demo.e2e.ts:63`.
- **Company - Public replaces Partnership - Unregulated on a company (owner-approved):**
  - `test_classification_conflict_review.py:249`;
  - `test_target_classification_continuation.py:597,732`.
  The test intent (a different but compatible prior user value) is kept.
- **`database-classification.e2e.ts`:**
  - The Government special-case early return (ownership unsupported, no Send) was replaced by the full
    journey. The removed assertions (no Save button, zero PUTs, SEARCH 1 / SHELL 0, zero external calls)
    still run in the shared path for all three fixtures.
  - Partnership `CACHE_HIT` became `not CACHE_HIT`. This is superseded by the agreed narrowed PARTIAL
    seed, and Alpha still asserts CACHE_HIT.
- **`AttentionQueue.test.tsx`.** One enum value was added.

## Evidence

Reruns by this reviewer at 20ee88d:

| Check | Result |
|---|---|
| Backend `pytest apps/backend/tests` (serial) | 3334 passed, 181 skipped, 6 failed. All 6 are `test_s2_local_ocr.py::test_real_local_ocr_acceptance[*]` (macOS font OSError, known, environment-only). `test_phase13_auth_rbac.py` is now green. |
| CI `python -m unittest discover -s ../../tests -p test_phase_07_delivery_assets.py` | **FAIL** at branch HEAD (`test_synthetic_document_pack_is_explicit_and_bounded`). It is **OK 4/4 on an origin/main 859b8f0 archive**, so this is a branch regression (P1-1). |
| CI `unittest discover -s ../../tests/contract` | 1 failure (`test_phase_04_ownership_contract`). It fails identically on origin/main (pre-existing, not D-101). |
| `check_project_state.py` / `check_architecture.py` | PASS / PASS |
| `tests.test_check_project_state`, `tests.test_check_architecture` | OK |
| Assistant `build_synthetic_boundary.py --check` / `build_synthetic_eligibility.py --check` | current / current |
| PDF SHA256 against the README | both match (`e45feb3a…`, `ed3bb29e…`) |
| Line endings: `--numstat` against `--numstat --ignore-cr-at-eol` | identical |
| `git diff --check origin/main...HEAD` | clean |
| Vitest: GovernmentStatusPanel, PartnershipAgreementDisplay, AttentionQueue | 16/16 |
| Focused E2E, committed HEAD, clean tree: `scratchpad/qg-d101-e2e-focused-20ee88d.json` | 6/6 PASS: database-classification 197/202/207/212, s3-sandbox-submission:752, slice-b-registry-demo:132 |

Adversarial probes (scratch only: `scratchpad/qgprobe/test_qg_d101_probe.py`, 6 tests, all passed):
- **Government Send.** The frozen snapshot has `ownership_reference.status=GOVERNMENT_STATUS_CONFIRMED`
  and `provisional_ubo.candidate_count=0`. Target calls are only search/create/createPolicy, with no
  related-party write.
- **Non-creator.** `ryan-lee` was refused with `ZERO_TOUCH_GOVERNMENT_STATUS_CREATOR_REQUIRED`, and
  nothing was persisted.
- **Other-UEN letter.** It is not evidence (DOCUMENT_SOURCE_CONFLICT; state stays EVIDENCE_REQUIRED).
- **Second matching letter after confirmation.** The confirmation is revoked (readiness blocker
  GOVERNMENT_STATUS_REQUIRED), and Send is refused with 409 CLM_NOT_READY and no POST.
- **Partnership partial row selection.** Refused with 409.

Reused caller evidence:
- On e6b439f: ruff and mypy clean; physical Mongo 177/177 across 28 suites; assistant 2843 passed plus 1
  timing flake; full Vitest 1247/1248 (ViteHistoryFallback, macOS-only); tsc and build pass.
- Full E2E keep-going `d101-e2e-full-e6b439f.json`: 112/117 at a clean tree. The remaining failures are
  onboarding-recovery:6, s3-sandbox-submission:232 and slice-c-recovery:294, which are known on main,
  plus 752 and slice-b:132, both now re-proven at the committed HEAD above.
- The caller's `garden2.json` was run on a dirty tree. It is superseded by this reviewer's
  committed-HEAD rerun.
- All of this is local evidence only. It is not hosted CI, and hosted CI remains billing-blocked.

## Findings

- **P1-1: a CI-required test regresses.** `tests/test_phase_07_delivery_assets.py:58` builds the
  synthetic PDF pack set excluding only `demo-{alpha,beta,gamma,delta}-scanned.pdf` and
  `demo-government-scanned.pdf`.
  - The branch adds `zero-touch-database/demo-gamma-partnership-agreement.pdf` and
    `demo-parks-government-status.pdf`, which are in neither the exclusion set nor `expected`.
  - The README rows (`apps/backend/tests/fixtures/uat/zero-touch-database/README.md:52-53`) also do not
    use the backticked `| \`name.pdf\` | … | \`sha\` |` index format that the test parses.
  - `.github/workflows/ci.yml:31` runs this test, so the backend CI job would fail. It passes on
    origin/main.
  - Fix: either index the two PDFs in the test's `expected` set and the README in the parsed format, or
    exclude them alongside the other database scans. Either way the change touches a teammate test, so
    list it in the PR. Then rerun that test.
- **P2-1: the integration is stale.** origin/main is now `0c6a632` (#137, D-102). Merging it conflicts in
  `docs/PROJECT_STATE.md` and `docs/decisions/DECISION_LOG.md` (both append at the end; D-101/D-102
  numbering does not collide).
  - #137 changes `apps/assistant` code (`model_admin.py` and others), so `synthetic_boundary.json`
    `code_vocabulary` may need regenerating with `--check` after the merge.
  - The workflow requires merging the latest main and rerunning what the merge invalidates (assistant
    manifests check, assistant tests, Vitest for `AiModelManagement`) before pre-PR.
- **P2-2: a test assertion is vacuous.** `apps/backend/tests/test_zero_touch_entity_types.py:238-240`
  reads `final["clm"].get("submission_snapshot")`, but the API field is `clm.submission`, so the "0
  provisional UBO" assertion never runs. The behaviour is correct (this reviewer's probe confirmed it), but
  the Government no-UBO submission invariant is untested. Assert it on the domain record via
  `bundle.clm.get_for_case(...)`, as the probe does.
- **P3-1: docs overstate the signatory display.**
  - `docs/decisions/DECISION_LOG.md:1583` says signatories "are shown on the Government case for display
    only".
  - `docs/demo/ZERO_TOUCH_DATABASE_HAPPY_PATH_UAT.md:170-171` says the step "shows the reviewed founding
    instrument and signatories".
  - The UI (`GovernmentStatusPanel.tsx:32`) states that signatories "appear on the status document only"
    and are not extracted.
  - Align the docs with the UI. The prompt allows leaving them out if this is said explicitly.
- **P3-2: PROJECT_STATE is stale.** `docs/PROJECT_STATE.md:1385` still lists "database-classification E2E
  rewrites, integrated acceptance" as open. Refresh it when resolving the P2-1 merge.
- **P3-3: scenario coverage omits the browser test.** `blocker_decision_policy.py:1281` maps the
  `government_status` scenario only to the backend test, so the generated guide says "Unit-only coverage
  reference. No end-to-end browser demonstration". `database-classification.e2e.ts` now demonstrates
  this. Optionally add it.
- **P3-4: readiness re-check is ANALYZED-only (observation).** The partnership readiness re-check runs only
  when the analysis is `ANALYZED` (`clm_orchestration.py:1728`). A D-082 POC-accepted REVIEW_REQUIRED
  analysis on a partnership would skip it. This is unreachable for Gamma today, but consider applying the
  check before the D-082 branch. Separately, after the confirmation is revoked by a second matching
  letter, the automation shows only TARGET_CONFIRMATION_REQUIRED while readiness blocks. This is safe
  (Send is refused), but the RM sees no reopened Government hold.

No P0 issue was found. No safety control was weakened (maker-checker, permission rechecks, CAS and the
exact-line catalog are untouched). There is no secret exposure, no real ACRA or GoldTier call, and no ACRA
verification claim for Government.

## Readiness

The candidate is not ready for pre-PR. The bounded remediation is:
1. Fix P1-1.
2. Merge origin/main `0c6a632`, resolve the docs conflicts and rerun what the merge invalidates (P2-1).
3. Make the P2-2 assertion real.
4. Optionally fix P3-1 to P3-3.

A recheck should review that delta and reuse the unchanged evidence listed above. Real ACRA and GoldTier
readiness is unaffected and remains out of scope. D-101 and its defaults still need Shane's
confirmation, and any manual-CI exception needs Shane's approval.

VERDICT: FAIL
