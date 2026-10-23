# Recursive Ownership and UBO Discovery — Stage 3 Independent Quality Gate

## 1. Executive Result

**PASS WITH MINOR FIXES.**

The reviewed content met the accepted Garden/SIM LIM behavior, cache-first acquisition,
double-counting isolation, bounded traversal, identity rules, the single Decimal engine,
schema-11 persistence and the reviewer-safe projection. I verified this in the source and
reproduced it with my own probes and runs on the frozen commit. Nothing incomplete
became `ANALYZED`, and no Live or Sandbox claim was made.

Browser coverage is a 114/114 union of isolated lifecycles on the frozen identity. I
established it twice independently: once from the Stage 2 runs and once from my own runs.
No single uninterrupted unfiltered 114/114 run exists. Each attempt hit one intermittent
timeout, both in flows that do not execute discovery, and both selectors passed 5/5 on
repetition.

One bounded, non-security, fail-closed defect remains (M1). The policy catalogue
migration can activate a catalogue that breaks its own `trace <= UBO` invariant. That
happens when a legacy catalogue already holds a UBO threshold below 10%. After the
migration, no new case can bind a policy snapshot until governance corrects the
catalogue. Four Low documentation and hardening observations are listed separately.
Under this gate's rules, remediation of M1 needs a focused recheck of the changed policy
delta, not a full re-acceptance.

Consequence: the candidate is not ready for publication until M1 is fixed. The fix needs
a focused re-QG of that delta only. All other evidence below stays valid unless the fix
reaches it.

## 2. Reviewed identity

| Item | Value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\recursive-ownership-ubo-20261023` |
| Branch | `feat/recursive-ownership-ubo-registry-20261023` (no upstream) |
| Reviewed HEAD / tree | `08f8a24ee905fa7249e66cf39f52483e8e3780db` / `87a8ae7519913f8d722e936d1ae5d48b85066ed4`, confirmed at start and at end |
| Base / integrated `origin/main` | `2f45324daec055b0929d17d2ad5fa518791c499d`. I fetched it at start and at end; it had not advanced and the merge-base matched. |
| Reviewed diff | `git diff 2f45324..08f8a24`: **60 files**, +4142/-319. The assignment said 58. The real count is 57 files at `512a424` plus 3 files the remediation newly touched (`scripts/run_physical_mongo_tests.py`, `scripts/slice_c_recovery_fixture.py`, `tests/test_run_physical_mongo_tests.py`). This is a count discrepancy in the brief, not a content change. |
| Commits | `f05aa69` (feature) → `512a424` (EOL restore in docs) → `08f8a24` (Slice C fixture remediation + physical runner list entry) |
| Worktree status | Clean before and during review. The only write is this report. |

## 3. Acceptance checklist

| # | Criterion | Result | Direct evidence (independent) |
|---|---|---|---|
| 1 | Garden serves only its own direct holders from the owner body; SIM LIM 62.5% and LIM CHOON HUAT 37.5% as SHARE_OWNERSHIP edges; no special case | **MET** | `connectors/garden_business.py`: the body nests the corporate row under `individual`. Each row is validated twice and the two decodes must agree: by the existing strict `BizfileMockOwnershipPartiesDecoder` (party type taken from `shareholderCategory`) and by a stricter fixture model. Probe P8 runs the real composition (`build_onboarding_service` + `build_ownership_analysis_service` + default `PolicyManagementService`) and gives Garden edges `111111111M 62.500000 SHARE_OWNERSHIP` and `S9988776F 37.500000 SHARE_OWNERSHIP`. Added lines naming Garden or SIM LIM are confined to the Mock fixture/connector layer. The existing official-Mock supplement wiring moved without behavior change. Services and orchestration add no special case. |
| 2 | SIM LIM is its own Mock issuer and is acquired separately and cache-first; UBO results unchanged | **MET** | `mock_acra.py` adds a SIM LIM profile, empty officers and per-issuer ownership (900/100/100; withdrawn holder excluded). P8: case 1 is `FETCHED` (4 SIM LIM connector operations), case 2 is `CACHE_HIT` (0 more calls; lookups/provider/cache = 1/0/1). ABCD123 `51.13636375`, LIM CHOON HUAT `37.500000`, TAN WEI LING and EFGH2345 `5.681818125`. P5: 4 concurrent Garden cases make 4 SIM LIM operations in total, 1 FETCHED and 3 CACHE_HIT, all ANALYZED. Stale refetch is covered by `test_expired_sim_lim_snapshot_is_refetched_once_and_saved` (my focused run). The physical restart test also passed in my run. |
| 3 | No double counting; V1 cache isolated; official Marketplace Mock lane unchanged and never a discovery source | **MET** | The namespace is `MOCK_ACRA_SYNTHETIC_V2`, and seed admission accepts only V2 plus the official namespace (`registry_acquisition.py:186`). A flattened V1 entry is ignored (test passes; ABCD123 has one path). Discovery requires `SINGLE_SOURCE` with `ACRA_REGISTRY_ACQUISITION` relationships (`ownership_analysis.py:908-916`). The official lane has no relationships operation (`acra_api_marketplace_mock.py:213-216`), and Garden on that lane is `OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT` (test uses a refusing reader). P1: a two-level diamond acquires D once (Q = 100% over 2 paths). |
| 4 | Bounded traversal and distinct outcomes; nothing incomplete becomes ANALYZED or GoldTier-ready | **MET** | Source review of `ownership_discovery.py` covered verified-UEN leaf issuers only, depth `>` policy → DEPTH_LIMIT, the 32-lookup cap, the 60 s deadline with cancellation, sequential acquisition, a round backstop, and 15 distinct outcomes. **P7: in 400 randomized registries (149 with deferral), trace deferral never changed the set of persons at or above UBO against full expansion. No run ended ANALYZED with an unresolved branch.** Any unresolved record adds `CORPORATE_OWNERSHIP_UNRESOLVED` next to the engine's `INCOMPLETE_LEGAL_ENTITY`, so the state becomes `REVIEW_REQUIRED` (`ownership_analysis.py:1071-1093, 1288-1297`). P3: an ownership-like officer role gives `PROVIDER_PARTIAL`/`UNRESOLVED_ROLE_EVIDENCE`. P4: an issuer UEN mismatch fails closed (`PROVIDER_FAILED`). Budget semantics: see L2. |
| 5 | Identity: issuer dedupe by UEN only; persons never merged without a verified binding; repeated IDs → `PERSON_IDENTITY_UNRESOLVED` | **MET** | Issuers deduplicate by UEN through `_issuer_nodes`. Holders get issuer-scoped IDs (`_scoped_id`). Persons merge only through `VerifiedPersonBinding`, and no provider supplies one. A repeated source ID makes the bound invalid and raises `PERSON_IDENTITY_UNRESOLVED`. Identity tests pass in my run: same ID twice, a binding for another issuer, and the same name with different IDs. |
| 6 | Single Decimal engine | **MET** | The coordinator calls only `calculate_ownership_paths` and `aggregate_ownership_paths`, and only for scheduling and the bound. Candidates and thresholds still come from `OwnershipAnalysisService`/`build_ownership_candidates`. The engine change is additive only (`unresolved_entity_shares`). |
| 7 | Policy: four editable rules, HR→Director, `trace <= UBO` on submit/approve/snapshot, case-frozen, additive MIGRATED migration, 29/21/8 variants, partial fails closed | **MET WITH DEFECT M1** | Rules, ranges, enforcement on submit, approve and snapshot, freezing, the MIGRATED validator, and preservation of history, proposals and audit are all verified (my focused run is 21/21, plus physical migration through Mongo). **M1:** migration does not keep the cross-rule invariant when the active UBO threshold is below 10% (P10 and follow-ups). |
| 8 | Persistence: schema 11, strict v1–v10 reads, smuggled discovery rejected, currentness recheck, CAS / no resurrection / no replay | **MET** | `DurableCaseSnapshotV10` plus `reject_ownership_discovery_legacy_fields`. P11: non-null values in the current snapshot, in rebind-history `previous_snapshot` and in `prior_analyses` are all rejected; explicit nulls are accepted. The currentness recheck after acquisition raises `OWNERSHIP_SOURCE_STALE` (test passes). **Physical Mongo, my run:** fresh container, generated allowlisted databases, never `clm_poc` — `SUITES=25; COLLECTED=167; PASSED=167; FAILED=0; SKIPPED=0`. Afterwards the server holds only `admin,config,local`. |
| 9 | API/frontend: reviewer-safe `discovery`; Policy explanations and units; read-only summary; PR #103 UI and PR #102 tooling untouched | **MET** | P9: the projected `discovery` keys and record keys contain no URL, endpoint or raw payload, and the full response contains no `http(s)://` or `source_endpoint`. The frontend diff touches only `OwnershipPathExplorer.tsx` (additive summary and shared issue list), `PolicyRules.tsx` (four explanations and units), `types.ts`, and one new test. The diff does not touch `.github/`, `scripts/run_e2e.py`, `tests/test_run_e2e.py`, `apps/frontend/e2e/` or the package files. My runs: Vitest 63 files / 1050 passed, `tsc -b` passed, `vite build` passed (output in scratch), root tooling 157 passed (includes `test_run_e2e.py`). |
| 10 | Truthful Mock/LOCAL labels; no Live/Sandbox claims; docs current; hygiene | **MET (L1 doc precision)** | Added lines contain no Live or Sandbox claim, apart from a non-goal mention. The UI caption says "synthetic Mock registry record". ADR-013, D-076, Q-019, five contract amendments, ARCHITECTURE and PROJECT_STATE are present, and the checkers pass. `git diff --check` exits 0. `--ignore-cr-at-eol` gives an identical shortstat (no EOL churn). The secret scan passes. |

## 4. Evidence reuse table

| Evidence | Source | Bound to | Decision |
|---|---|---|---|
| Full backend pytest (3078 passed, 6 OCR skips + 36/36 OCR rerun) | Stage 2 run on `512a424` | tree `4427dca` | **Reused.** `git diff 512a424 08f8a24 -- apps/backend` is empty. The only backend-reachable change is `scripts/slice_c_recovery_fixture.py`. Its consumers ran again in R1 (27/27) and in my focused run. I also ran a 34-file focused slice on `08f8a24`: **1201 passed, 0 failed, 0 skipped**. |
| mypy / Ruff | Stage 2 plus mine | `08f8a24` | **Re-executed:** mypy 128 files no issues (cache outside the repo); `ruff check apps\backend scripts tests --no-cache` clean. |
| Physical Mongo | Stage 2 R1 log (identity stated only in the report text) | — | **Re-executed** (the log carries no identity): `08f8a24`/`87a8ae7`, dirty 0, 167/167, 25 suites. |
| Frontend Vitest / typecheck / build | Stage 2 on `512a424` | no frontend delta | **Re-executed** on `08f8a24`: 1050/1050; `tsc -b` passed; build passed. |
| Root tests | Stage 2 R1 on `08f8a24` | identity in report and junit | **Verified.** junit shows 445 tests, 24 failures (exactly 21 in `test_demo_lifecycle_windows` and 3 in `test_performance_review_remediation`). I re-ran the delta-relevant root files (157 passed) and the contract modules under `unittest discover` (44 OK). |
| E2E | Stage 2 R1: three JSONs | each JSON has `head 08f8a24`, `tree 87a8ae7`, `dirty false`, `origin_main 2f45324` | **Verified** by parsing all three: 76 PASS + 1 failure + 37 NOT_RUN; rerun 1 PASS equals the failed selector; remainder 37 PASS equals the NOT_RUN set exactly. Union 114/114, no gaps, no overlap. **Plus my own single unfiltered run:** see section 5. |
| Governance checkers | mine | `08f8a24` | `check_architecture`, `check_project_state`, `check_policy_authority`, `check_secrets`: PASS. |

## 5. Tester and adversarial findings

### Commands I ran on `08f8a24` (worktree-pinned `PYTHONPATH`; `app.__file__` checked inside the worktree)

| Check | Result |
|---|---|
| Focused backend slice (34 files: discovery, policy, Garden, registry/cache, persistence/legacy, zero-touch, Slice C/F, synthetic pack, sponsor fixtures) | 1201 passed, 0 failed, 0 skipped (7m17s) |
| `scripts/run_physical_mongo_tests.py`, hosted-CI shape, own container `recursive-ownership-mongo-qg` on `127.0.0.1:27411` | `PHYSICAL_MONGO_RESULT=PASSED; SUITES=25; COLLECTED=167; PASSED=167` (6m13s); afterwards `admin,config,local` only |
| Root: `test_run_physical_mongo_tests`, `test_check_policy_authority`, `test_slice_c_e2e_fixture_routing`, `test_check_project_state`, `test_check_architecture`, `test_run_e2e` | 157 passed |
| `python -m unittest discover -s tests\contract` | 44 OK |
| Vitest (full) / `tsc -b` / `vite build --outDir <scratch>` | 1050 passed / passed / passed |
| mypy `app` / Ruff | clean / clean |
| Governance checkers and secret scan | PASS ×4 |
| `git diff --check`; EOL shortstat comparison | exit 0; identical |
| E2E: `scripts/run_e2e.py --timeout-seconds 60` (unfiltered, one run, own container on port 27411) | **FAIL, 113/114:** 113 PASS and 1 `INDIVIDUAL_SELECTION_TIMEOUT` on the last selector `e2e/zero-touch-exception.e2e.ts:160` (66.4 s; it took 12.5 s in Stage 2 R1). Run time 27m31s. JSON identity `08f8a24`/`87a8ae7`, `dirty:false`, `origin_main 2f45324`. |
| E2E: single rerun of `zero-touch-exception.e2e.ts:160` | PASS (14.25 s) |
| E2E: 4 repetitions of `s3-sandbox-submission.e2e.ts:383`, `:387` and `zero-touch-exception.e2e.ts:160` (`--keep-going`) | 12/12 PASS (11.0–14.2 s); same identity, clean |

### Adversarial probes (in-memory, synthetic Mock only; scripts in the QG scratchpad)

| Probe | Result |
|---|---|
| P1 Two-level diamond (B→D, C→D) | D acquired once (4 operations); Q 100% over 2 paths; ANALYZED |
| P2 Over-allocated subsidiary holders (60% + 60%) | ANALYZED, no issue. Pre-existing engine behavior: the same root-only graph is ANALYZED on base `2f45324` (identical probe output on the base export). See L3. |
| P3 Subsidiary officer role `SHAREHOLDER` | `PROVIDER_PARTIAL`/`UNRESOLVED_ROLE_EVIDENCE`; REVIEW_REQUIRED |
| P4 Subsidiary profile echoes another UEN | Fails closed (`PROVIDER_FAILED`); REVIEW_REQUIRED |
| P5 4 concurrent Garden cases | SIM LIM 4 operations in total; 1 FETCHED, 3 CACHE_HIT; all ANALYZED; no errors |
| P6 Budget 1 exhausted, second issuer already fresh in cache | Second issuer `BUSINESS_BUDGET` with no lookup; REVIEW_REQUIRED (see L2) |
| P7 400 random registries, trace 10% vs full expansion | 149 runs deferred; **0** bound violations; **0** ANALYZED with an unresolved branch |
| P8 Real composition, Garden ×2 | As in criteria 1 and 2 |
| P9 API projection | No URL, endpoint or raw payload in `discovery` or the full response |
| P10 Legacy approved catalogue with UBO 5% → startup migration | Migrates to `MIGRATED` (39 rules) with trace 10% > UBO 5%; `case_snapshot()` then raises `PolicyValidationError` (**M1**) |
| P10b History-free 35- and 29-rule prefixes with UBO 0 or 8% | Same: migration succeeds, every case snapshot fails |
| P11 Legacy envelope smuggling | Non-null values in the current snapshot, rebind history and prior analysis are rejected; nulls accepted |

### Judgements requested by the coordinator

- **(a) E2E coverage.** I accept union coverage for the browser claim. Here is what that
  evidence does and does not establish.
  - **Stage 2 union.** The three Stage 2 JSON files are complete, identity-bound and
    disjoint, and together cover 114/114 discovered selectors in isolated lifecycles.
    This is the union-of-isolated-lifecycles principle the workflow already accepts for
    CI shards.
  - **My own unfiltered run.** It also did not finish 114/114 in one pass: 113 passed and
    the last selector timed out. My run plus its single rerun forms a **second,
    independent 114/114 union** on the frozen identity.
  - **Neither intermittent failure is on the discovery path.**
    - `s3-sandbox-submission.e2e.ts:383` (`uncertain-shell`) uses synthetic UEN
      `202698765Z` (`scripts/s3_sandbox_fixture.py:12-17`), which has person-only Mock
      owners. No corporate leaf exists, so no subsidiary lookup runs.
    - `zero-touch-exception.e2e.ts:160` asserts `OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT`
      (`zero-touch-exception.e2e.ts:182`), a lane where discovery is excluded by design.
    - The other delta effects on those flows are a schema-11 envelope and a policy
      snapshot with four more frozen values. Neither adds measurable latency.
  - **Repetitions.** Each of the two selectors then passed 5/5 within 11–14 s.
  - **Classification.** Both failures are intermittent environment timing flakes, not
    defects.
  - **Still not demonstrated.** No single uninterrupted unfiltered 114/114 run exists on
    this commit. If the owner requires one for publication, that claim stays open; it
    reflects suite timing stability, not a candidate defect.
- **(b) Environment exceptions.** These are confirmed as missing infrastructure. They
  block only their own claims.
  - Port `127.0.0.1:8000` is held by unrelated PID 4900 (python, started 13:10:45),
    which I did not touch.
  - `psutil` is absent from the venv.
  - The R1 junit failures are exactly 21 + 3 in those two modules. Neither module
    exercises the delta.
  - The contract modules pass under the CI `unittest discover` form (44 OK, my run).
  - The demo-lifecycle and performance-resource claims stay **unverified**, not passed.
- **(c) `PHYSICAL_SUITES` entry.** I accept it. It is a one-line inventory entry with
  its matching inclusion assertion. It follows the established convention: PRs #76, #80,
  #81 and #82 added their own suites the same way.
  - It changes no CI workflow, runner logic, port allocation or E2E shard semantics.
    `.github/` and `scripts/run_e2e.py` are untouched.
  - Without it, the new physical suite would never run in hosted CI.
  - The owner should still know that the hosted `phase12-mongo` job now runs 2 more
    tests. Hosted CI execution itself is not evidenced here.
- **(d) Backend full-suite reuse.** Valid. See section 4.

## 6. Contract and integration findings

- **M1 (Medium; fails closed; bounded fix): policy migration can activate a catalogue
  that breaks `trace <= UBO`.**
  - Where it happens: `apps/backend/app/services/policy_management.py:142-174` (the rules
    are assembled and written with no cross-rule runtime validation) and
    `_additive_migration` (`:176-250`). Both append `OWNERSHIP_TRACE_THRESHOLD_PERCENT = 10`
    regardless of the active UBO threshold.
  - Trigger: a legacy catalogue whose UBO threshold is below 10%. This is reachable on
    base, where the UBO minimum is 0 and approval required no other rule. P10 and P10b
    reproduce it for an approved 5% and for history-free 35- and 29-rule prefixes at
    0% and 8%. Migration succeeds, but `_ownership_discovery_snapshot` (`:658`) then
    raises `PolicyValidationError` for every `case_snapshot()`.
  - Impact: new case creation, SG policy rebind (`onboarding.py:1367`) and GoldTier
    Sandbox console resolution (`onboarding.py:1523`) all stop.
  - What it breaks: the policy amendment states the trace threshold is "never above the
    active UBO threshold" (`POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md:161`). No test covers
    this case.
  - Containment: it is fail-closed, preserves history, and is recoverable by an HR
    proposal plus Director approval of a consistent pair (at UBO 0 the UBO itself must
    be raised). It produces no false success and has no security impact.
- **L1 (Low, doc): the contract wrongly says the impact preview rejects.**
  `POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md:165` says "Submission, approval, **impact** and
  case snapshots reject a trace threshold above the effective UBO threshold". The impact
  preview deliberately skips discovery validation
  (`policy_management.py:545-547`, planner decision 12;
  `test_lowering_ubo_threshold_together_with_trace_threshold_is_accepted` expects
  `NOT_ASSESSED`). The contract wording should drop "impact".
- **L2 (Low, semantics/doc): the business budget is stricter than its description.**
  - Once the budget is used up, a further issuer is finalized as `BUSINESS_BUDGET` before
    any lookup, even when it would be a fresh cache hit
    (`ownership_discovery.py:346-351`; P6).
  - A fresh negative-cache `NOT_FOUND` returns no binding, so
    `acquire_subsidiary_registry_evidence` reports it as provider-backed
    (`onboarding.py:1971`).
  - Both are conservative: they mean more review, never a success. But the UI and contract
    text "fresh cache hits do not count" can be read as "cache hits proceed past the
    budget".
  - Accept, or clarify the wording.
- **L3 (Low, pre-existing, later hardening): over-allocated holder sets reach ANALYZED.**
  `validate_ownership_graph` (`ownership_analysis.py:293-311`) does not check that an
  issuer's holder percentages total no more than 100%. Over-allocated sets therefore
  reach ANALYZED, at the root on base and now also for attached subsidiary records (P2).
  The discovery bound treats over-allocation as invalid (`ownership_discovery.py:569-571`),
  but a fully resolved graph does not consult the bound. Only project-controlled Mock
  data reaches this path. It is not introduced by this delta, so it is a later hardening
  item, not a current fix.
- **L4 (Low, hardening): the Mock-only containment is structural, not an explicit
  pre-call guard.**
  - Subsidiary lookups run only because, today, only the local Mock supplies registry
    relationships. Sandbox ownership operations fail closed (`acra_sandbox.py:351-361`),
    and the official Mock has no relationships operation.
  - The MOCK-environment check runs after the call (`ownership_discovery.py:398`).
  - In ACRA `sandbox` mode the registry cache and coordinator are disabled, so
    `acquire_subsidiary_registry_evidence` would call the provider directly
    (`onboarding.py:1950-1957`).
  - This is unreachable today. If a non-Mock lane ever supplies relationships, add an
    explicit pre-call Mock-environment guard.
- **Observation (no action): pre-D-076 cases that re-acquire Garden go to review.**
  A pre-D-076 case without `ownership_discovery` that re-acquires Garden after upgrade
  (for example through an identity correction) receives the direct-only record and lands
  in `REVIEW_REQUIRED` instead of `ANALYZED`
  (`test_historical_policy_snapshot_never_fetches_subsidiaries`). This is fail-safe and
  consistent with "historical snapshots keep root-only semantics".
- **Sponsor dependencies (later, not current blockers):** Q-019 (authorized subsidiary
  operation, person-identity authority, production limits), Q-012 (real ACRA capability),
  Q-004 (legal UBO policy), Q-002 (GoldTier hierarchy). None is claimed.

## 7. Code and architecture review

- **Ownership and dependency direction.** The direction matches ADR-013: ownership
  service → coordinator protocol → engine functions, `acquisition_ownership_source()` and
  the read-only subsidiary reader.
  - The coordinator holds no cache, repository or classification.
  - `acquire_subsidiary_registry_evidence` touches no case, binding, lock or event (test
    passes).
  - The router, adapter and coordinator are reused, with no new provider or persistence
    owner.
- **Error handling fails closed.**
  - Provider, cache and validation errors become distinct unresolved outcomes.
  - An unexpected exception becomes `PROVIDER_FAILED`/`REGISTRY_UNEXPECTED_FAILURE`.
  - Errors raised while attaching become terminal `OWNERSHIP_UNEXPECTED_FAILURE` through
    the existing load handler (`ownership_analysis.py:988-993`).
  - The audit caps `records` at 100 while `ownership_max_parties` can be set up to 1000.
    Beyond 100 corporate leaves the load would fail terminally rather than show a reviewed
    partial. This is unreachable at the default 100-party limit (very low).
- **Tests are substantive.** 40 discovery tests and 21 policy/persistence tests cover the
  happy, review, failure, identity, topology, budget, deadline, cache-corruption,
  currentness and supplement-exclusion paths. Changes to existing tests only update
  pinned constants (schema 10→11, 35→39 rules, Garden direct-only shape). The nested-binding
  test moved to fixture `202400009I` and still asserts nested edges.
- **Nit (no action required).** `persistence/models.py:570-571` has one blank line before
  `class DurableCaseSnapshotV10` (pycodestyle E302). It is not enforced by the
  repository's Ruff configuration.
- **Scope.** No GoldTier mapper or connector change, no hierarchy write, no new
  jurisdiction, no frontend redesign, no CI or E2E tooling change apart from the judged
  inventory entry.

## 8. Security review

- **Projection.** The `discovery` projection is limited to identifiers, names, outcomes,
  reason codes and Decimal exposure (P9). Scoped IDs are regex-safe or hashed.
  `source_reference` stays within the existing 128-character safe pattern. The fixture's
  synthetic endpoint string is used only as decoder provenance and is discarded.
- **Data and secrets.** No secrets, credentials, `.env` access, raw payloads or KYC
  documents were added (`check_secrets` passes).
- **Trust boundaries.** Subsidiary input passes the same strict adapter and
  ownership-source validation as the root, plus issuer and environment checks.
  Non-Singapore and unverified identifiers are never sent (test passes).
- **Hardening.** The only deferred hardening is L4, an explicit pre-call Mock guard.

## 9. Required fixes

1. **M1.** Make the migrated active catalogue satisfy `trace <= UBO`, or fail closed
   explicitly, and pin the behavior in a test. Options, which are an owner/project
   choice:
   - (i) when the active UBO is positive and below 10%, seed the appended trace default
     at the active UBO value;
   - (ii) refuse the migration at bootstrap with a typed error and documented
     remediation.

   In either case:
   - Validate the migrated rules with the discovery snapshot builder before the write.
   - Add regression tests for approved/MIGRATED and history-free prefixes (35, 29) at UBO
     0% and below 10%.
   - Record the chosen behavior in the `POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md` amendment.
2. **L1 (folded into the same doc edit).** Remove "impact" from the
   `POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md:165` enforcement sentence, or make the preview
   enforce it.

L2–L4 and the nit are accepted as recorded limitations or later hardening. They are not
required for this candidate. A re-QG reviews only the M1/L1 delta, plus any evidence that
delta invalidates: focused policy and persistence tests, the physical policy migration
test, `check_policy_authority`, and Ruff/mypy.

## 10. Readiness

- **Readiness of this candidate.** It is **not yet ready for publication**. It becomes
  ready after the M1/L1 remediation and a focused independent re-QG `PASS`. Publication
  then still needs explicit owner authorization (Stage 4). This gate grants neither.
- **Real ACRA and GoldTier.** Real ACRA subsidiary capability and real GoldTier
  integration are **not** demonstrated or claimed. All discovery evidence is synthetic
  Mock/LOCAL (Q-012, Q-019 and Q-002 remain open).
- **Unverified claims.** Hosted CI is not evidenced. The demo-lifecycle (21) and
  performance-resource (3) root claims remain unverified because the infrastructure is
  missing.

## 11. Git status

- Branch `feat/recursive-ownership-ubo-registry-20261023`, HEAD `08f8a24` and tree
  `87a8ae7` were unchanged throughout the review.
- Tracked, staged and untracked state was clean before and during every run. The only
  modification is this new report file:
  `.ai-pipeline/reports/RECURSIVE_OWNERSHIP_UBO_QUALITY_GATE.md` (untracked).
- No implementation fix, edit, stage, commit, push, merge, reset, stash, clean, branch
  switch or next phase occurred.
- Scratch output stayed under the QG scratchpad. Probes, logs, junit, E2E JSON and the
  frontend build output are in `...\scratchpad\stage3\`.
- The E2E runner wrote its usual screenshots under the git-ignored `tmp/browser-evidence/`.
- `origin/main` was fetched again at the end and is still `2f45324`.
- The disposable container `recursive-ownership-mongo-qg` was stopped after use. No
  other process or container was touched.
