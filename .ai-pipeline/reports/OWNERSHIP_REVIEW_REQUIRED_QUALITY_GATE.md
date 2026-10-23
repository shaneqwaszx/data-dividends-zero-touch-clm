# Ownership & UBO REVIEW_REQUIRED investigation — independent Stage 3 Quality Gate

Independent reviewer, 2026-10-24. I did not write or remediate the reviewed content. This
verdict applies only to frozen content tree `114df971868f26fcd058ea9d5e03a00bcc7a1324`.

## 1. Executive Result

**PASS WITH MINOR FIXES.**

The code, test and contract content is correct:

- Application code, scripts and `apps/frontend` are byte-identical to BASE.
- Every Garden and OPQ REVIEW_REQUIRED cause reproduces exactly as an expected safeguard
  or a provider limitation. I found no arithmetic, classification, cache, provenance,
  graph or readiness defect.
- The two new tests are meaningful. Each fails under a targeted mutation.
- The D1 contract sentence matches the code.
- The A1 and G3 classifications are correct.

Two factual statements in the implementer report must be corrected before publication
(F1 and F2, both Low, documentation-only). Two more report details are advisory (F3 and
F4). Changing the report changes reviewed content, so a bounded recheck of the corrected
report delta is required. The verified code, test and contract evidence can be reused.

## Reviewed identity

| Item | Value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\ownership-review-investigation-20261024` |
| Branch | `fix/ownership-review-required-investigation-20261024` (uncommitted candidate) |
| HEAD = BASE = `origin/main` | `b867e2c7dc53a4fe29a40b4f80e176d8cd25e9e9` (base tree `24fe8a44aaa86d813e8ec04bed4b2d650d56dfeb`, PR #105 head tree, confirmed) |
| Reviewed paths (4) | `apps/backend/tests/test_hybrid_five_layer_overlay.py` (M), `apps/backend/tests/test_five_layer_hybrid_journey.py` (M), `docs/contracts/OWNERSHIP_UBO_PROFILE.md` (M), `.ai-pipeline/reports/OWNERSHIP_REVIEW_REQUIRED_INVESTIGATION.md` (new) |
| Frozen tree, start of gate | `114df971868f26fcd058ea9d5e03a00bcc7a1324` (temporary scratch index: `read-tree HEAD`, add of the 4 paths, `write-tree`) |
| Frozen tree, before verdict | `114df971868f26fcd058ea9d5e03a00bcc7a1324` (same method, recomputed) |
| BASE tree to frozen tree diff | Exactly the 4 paths: 396 insertions, 2 deletions. 0 files under `apps/backend/app`, `apps/frontend` or `scripts` |
| `apps/frontend` subtree | Identical listing hash `eb8685ca7ec3…` in both trees. `git diff --stat b867e2c -- apps/frontend` is empty, with no untracked frontend files |

## 2. Acceptance checklist (the 8 assigned verification items)

| # | Item | Result | Observed evidence (my runs) |
|---|---|---|---|
| 1 | UBO arithmetic | **MET** | See §4.1 for paths and totals. Every path sum equals the aggregate, every `path_id` is unique, natural persons total exactly `100`, and L5 has one record and one ENTITY_PROFILE GET in the diamond. |
| 2 | Provenance | **MET** | Root identity comes from the official profile (OPQ and Garden ENTITY_PROFILE GETs). All 11 OPQ edges and both Garden edges are `LOCAL_SYNTHETIC_RELATIONSHIP`/`LOCAL`. SIM LIM gets its own official lookup (1 ENTITY_PROFILE GET → `NOT_FOUND`). Garden has exactly 3 parties (no ABCD123/TAN WEI LING/EFGH2345). Root units only are in `supplemental_evidence` (2 items, entity `201511222D` / `11111999A`). |
| 3 | Expected review vs failure per code | **MET** | See §3. Every code traced to its source line and reproduced. G3 was confirmed by mutation. |
| 4 | Branch resolution and cache | **MET** | Garden run 1: lookups 1, provider-backed 1, cache 0. Run 2: provider-backed 0, cache 1, transport unchanged (1 token + 3 GETs in total). Officially found non-scenario SIM LIM gives `PROVIDER_UNSUPPORTED` across 6 profile variants (§4.3). |
| 5 | Backend authority and readiness | **MET** | `synthetic_basis_threshold_result` is written only in `ownership_analysis.py:1385-1397`. It is otherwise read only by the domain validator (`ownership.py:301`, which forces a REVIEW_REQUIRED/INDETERMINATE classification) and the persistence schema gate (`persistence/models.py:740`). No readiness, CLM or zero-touch reference exists. Both cases: readiness blockers `['OWNERSHIP_REVIEW_REQUIRED']`, `goldtier.status BLOCKED`, `submission None`, `goldtier_result None`. |
| 6 | No frontend change | **MET** | See identity table. |
| 7 | No synthetic-to-official promotion; A1/G3/D1 | **MET** | No link or identity gains ACRA/MOCK provenance. The A1 relabel goes to `MANUAL_DECLARATION_POC`/`LOCAL`, never official. See §3 for A1, G3 and D1. |
| 8 | Regression coverage | **MET** (advisories F5, F6) | Both new tests fail under targeted mutations (§4.2). Scenario coverage map in §4.4. |

## 3. Contract and Integration Findings

### Issue-code classification (independently reproduced, API and service level)

**Garden** `11111999A`: `REVIEW_REQUIRED`, source `OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY`,
legal form `BUSINESS_PARTNERSHIP`, active exception `OWNERSHIP_INCOMPLETE/UBO_REVIEW_REQUIRED`.

| Code | Source | My classification | Agrees with implementer |
|---|---|---|---|
| `INCOMPLETE_LEGAL_ENTITY` (affected `111111111M`) | Engine: SIM LIM is a reachable legal-entity leaf | Expected safeguard (provider limitation upstream) | Yes (G1) |
| `CORPORATE_OWNERSHIP_UNRESOLVED` (1 branch, up to 62.5%) | `ownership_analysis.py:1147-1169`; SIM LIM `NOT_FOUND` is outside `TOPOLOGY_RESOLVED_DISCOVERY_OUTCOMES` | Expected safeguard. The Marketplace Mock SIM LIM entity is empty (Stage 3.5 closeout: "Basic entity empty"), and D-077 never attaches SIM LIM holders locally | Yes (G1) |
| `SYNTHETIC_OWNERSHIP_EVIDENCE` | Always raised for the hybrid classification (`:1182-1202`, D-077) | Expected safeguard | Yes (G2) |
| `UBO_REVIEW_REQUIRED` ("Unquantified role/control evidence…") | 4 official `OFFICERS` `ROLE`=`OWNER` rows bound to no edge (`:1292-1350`). The officer-role exemption (`garden_fixture_graph`, `:1286-1291`) requires `OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT` | **Expected safeguard (G3 correct).** The contract limits the exemption to "that exact validated fixture graph" and adds "no general officer-to-owner rule changes" (`OWNERSHIP_UBO_PROFILE.md` lines 193-196). Extending it to the hybrid would be a new rule. It is also outcome-neutral: Garden stays REVIEW_REQUIRED on the other three codes. The issue carries no affected party IDs (coarse diagnostics, not a defect) | Yes |

**OPQ** `201511222D`: `REVIEW_REQUIRED`, legal form `OTHER`, active exception
`OWNERSHIP_INCOMPLETE/OWNERSHIP_METHOD_UNSUPPORTED`.

| Code | Source | My classification | Agrees |
|---|---|---|---|
| `SYNTHETIC_OWNERSHIP_EVIDENCE` (6 affected: root + 5 overlay issuer nodes) | D-077 | Expected safeguard | Yes (O2) |
| `OWNERSHIP_METHOD_UNSUPPORTED` | `record.legal_form == OTHER` (`:1327,1338-1340`). The offline root profile has no `entityConstnDetailsAndType`; `classify_registry_legal_form("")` returns `OTHER`. The closeout records the live constitution as absent | Provider limitation. Any other mapping needs Q-012 authority; inferring from "PTE. LTD." would invent a mapping | Yes (O1) |

No `INCOMPLETE_LEGAL_ENTITY` or `CORPORATE_OWNERSHIP_UNRESOLVED` is raised for OPQ
(topology complete, bound `0`).

### A1 — `CURRENT_EVIDENCE` retention of a synthetic hybrid graph: **authority/design gap (classification correct)**

Reproduced on BASE-identical application code via the API:

- **OPQ `CURRENT_EVIDENCE`** → 200. The case moves to `WAITING_FOR_REVIEW`/`READINESS`.
  - Ownership: `ANALYZED`, `SINGLE_SOURCE`, provider `MANUAL_DECLARATION_POC`, all links
    `MANUAL_DECLARATION_POC`, issues `[]`.
  - DIANA KOH (25, inclusive) and BEATRICE LIM (30) are `PROVISIONAL_UBO_CANDIDATE`/MET.
  - Readiness blockers `[]`. Active exception `TARGET_CONFIRMATION_REQUIRED`.
    `submission None`, `goldtier_result None`.
  - The prior hybrid analysis is retained in `prior_analyses`.
- **OPQ `USER_SUPPLIED_DECLARATION`** with the same numbers (every parent sums to 100)
  gives the identical outcome.

Why "authority gap" and not "actual defect":

- PR #69 (`OWNERSHIP_UBO_PROFILE.md` lines 150-156) authorizes CURRENT_EVIDENCE for "the
  exact current graph". It also states these choices "do not establish automatic source
  precedence or legal verification".
- D-077 (DECISION_LOG lines 396-401; contract lines 355-361) makes the *hybrid analysis*
  always REVIEW_REQUIRED. It bars only `synthetic_basis_threshold_result` from being a
  classification or readiness input. It is silent on a creator's manual retention.
- The replacement is a creator-attested, document-bound, receipted manual declaration. It
  is not official evidence, not the synthetic-basis field, and not a new or hidden
  approval power. It is pre-existing behavior that this candidate does not change.
- Blocking it would be a new business rule (AGENTS.md: do not invent one). Recording it as
  an owner decision is the required handling.
- Mitigations observed:
  - names keep their "(SYNTHETIC …)" markers;
  - the receipt records `CURRENT_EVIDENCE` and the replaced analysis;
  - `TARGET_CONFIRMATION_REQUIRED` remains a separate human gate before any GoldTier
    dispatch.

Points the owner should weigh, not stated or misstated in the implementer report (F1, F3):

1. The Garden `CURRENT_EVIDENCE` attempt is not "refused". It returns 409
   `ZERO_TOUCH_MANUAL_OWNERSHIP_REVIEW_REQUIRED`, but by design (AM18, "The graph and
   receipt are retained even for a safe 409", `zero_touch_orchestration.py:1549-1558`) the
   creator's replacement is persisted:
   - provider `MANUAL_DECLARATION_POC`, `SINGLE_SOURCE`, still REVIEW_REQUIRED;
   - only `INCOMPLETE_LEGAL_ENTITY` remains;
   - `SYNTHETIC_OWNERSHIP_EVIDENCE`, `CORPORATE_OWNERSHIP_UNRESOLVED` (with its 62.5% bound)
     and `UBO_REVIEW_REQUIRED` leave the current analysis;
   - the hybrid analysis moves to `prior_analyses`;
   - readiness stays blocked.

   So the A1 relabel also applies to incomplete synthetic graphs.
2. Because manual sources carry no `legal_form`, the OPQ replacement also drops
   `OWNERSHIP_METHOD_UNSUPPORTED`. This happens for any PR #69 manual declaration.
3. The proposed bounded option (reject only `CURRENT_EVIDENCE` when a link is
   `LOCAL_SYNTHETIC_RELATIONSHIP`) would stop a silent "keep current" conversion. It would
   not stop the same synthetic numbers reaching readiness via `USER_SUPPLIED_DECLARATION`.
   The decision is therefore best framed as "may any manual declaration resolve a D-077
   hybrid demo case?", with CURRENT_EVIDENCE as the narrower variant.

### G3 — expected safeguard: **correct** (reasoning above; mutation in §4.2).

### D1 — contract wording: **true to the code**

- `_apply_hybrid_root_overlay` (`ownership_analysis.py:1652-1693`) sets
  `record.supplemental_evidence = component.share_evidence` for the root issuer only, in
  both the merged and the retained-beside-official branches.
- `_attach_overlay` (`ownership_discovery.py:512-604`) builds the issuer
  `OwnershipSourceResult` from `component.parties`/`relationships` only, so
  `component.share_evidence` is discarded. `_merge` copies only `issuer.evidence`, which
  is empty.
- Observed: OPQ and Garden `supplemental_evidence` hold 2 items each, all for the root
  entity. Corporate issuers' declared units appear nowhere in the record.

The corrected sentence ("Corporate issuers' declared units are not retained separately;
only their derived direct percentages appear on the links, and the whitelisted catalogue
remains their source") is accurate. The previous sentence overstated retention.

### Other evidence-authority notes

- No contract, mapping, enum, DTO, provider status or sponsor-controlled behavior changed.
- Q-004, Q-012, Q-019 and Q-002 remain open, and the report states this correctly.
- Live facts cited in the implementer report (11 requests: 1 OAuth + 10 GETs, all 200;
  Garden partnership with role rows; OPQ constitution absent; SIM LIM and L2–L5 empty)
  match `.ai-pipeline/reports/ACRA_HYBRID_FIVE_LAYER_STAGE3_5_CLOSEOUT.md`.

## 4. Tester and Adversarial Findings

All runs used the shared venv. PYTHONPATH was pinned to the worktree, and `app.__file__`
resolved to the worktree's `apps\backend\app\__init__.py`. Everything ran offline
(`OfflineFiveLayerProtocolTransport`, `external_calls 0`) with memory persistence. There
were no credentials, no `.env`, no Mongo and no network. Scratch files stayed outside the
repository.

### 4.1 Arithmetic (service-level script, exact `Decimal`)

| Person | Paths (engine strings) | Aggregate | `>= 25` exact | Classification / threshold / synthetic basis |
|---|---|---|---|---|
| ALEX TAN | `20% = 20%` | `20.000000` | False | REVIEW_REQUIRED / INDETERMINATE / NOT_MET |
| BEATRICE LIM | `80% x 37.5% = 30%` | `30.000000000000` | True | REVIEW_REQUIRED / INDETERMINATE / MET |
| CHARLES ONG | `80% x 62.5% x 40% x 50% = 10%` | `10.0…0` | False | REVIEW_REQUIRED / INDETERMINATE / NOT_MET |
| DIANA KOH | `…x 60% x 100% x 62.5% = 18.75%` + `…x 40% x 50% x 62.5% = 6.25%` | `25.000…000` (exactly 25) | True (inclusive) | REVIEW_REQUIRED / INDETERMINATE / MET |
| EDWARD NG | `11.25%` + `3.75%` | `15.0…0` | False | REVIEW_REQUIRED / INDETERMINATE / NOT_MET |

Further checks:

- Natural persons total `100.0…0`.
- Discovery records: depths L2 1, L3 2, L4A 3, L4B 3, L5 4.
- L5 `max_effective_percent` 40 (30 + 10).
- Audit: `graph_complete False`, `topology_complete True`, `official_identity_complete False`,
  `quantitative_evidence_complete False`, `UNCERTAIN`, bound `0`.
- Lookups: 5 provider-backed, 0 cache hits.
- Transport: root ENTITY_PROFILE ×2, each issuer ×1, 1 token.
- Garden: LIM CHOON HUAT `37.500000` direct, INDETERMINATE / REVIEW_REQUIRED / synthetic MET.
- SIM LIM `max_effective_percent` = audit bound = `62.500000`.

### 4.2 Mutation testing (in-memory pytest plugin in scratch; no repository edit)

| Mutation | Target | Failing tests over 13 ownership modules (332) |
|---|---|---|
| `accept_partial`: non-COMPLETE, non-FAILED bundles accepted in `_DiscoveryRun._classify` | New test | 3 failed: new test `[False]` (outcome `FETCHED`), `[True]` (`PROVIDER_INVALID`), plus pre-existing `test_recursive_ownership_discovery::test_unsupported_or_failed_issuer_lookup_is_a_partial_reviewed_branch[issuer2-False-PROVIDER_PARTIAL]` |
| `partial_label`: `PROVIDER_UNSUPPORTED` relabelled `PROVIDER_PARTIAL` | New test | 2 failed: only the new test (both variants) |
| `unsupported_resolves`: unit rows of an unsupported bundle attached | New test | 1 failed: new test `[True]` |
| `garden_role_exemption_hybrid`: official ROLE evidence dropped for hybrid graphs (extends the G3 exemption) | New journey test | 1 failed of 124 (6 modules): only the new journey test |
| `manual_review_required_accepted`: REVIEW_REQUIRED manual replacement passes the zero-touch gate | New journey test | 4 failed of 124: new journey test plus 3 pre-existing AM18 tests |

Conclusions:

- The new tests are not tautological, and they would catch the regressions they claim.
- The `partial_label` and `garden_role_exemption_hybrid` mutations are caught **only** by
  the new tests.
- The implementer's mutation claim (both variants fail, `FETCHED` and `PROVIDER_INVALID`)
  is confirmed.
- One nit: `transport.metadata()["external_calls"] == 0` is a hard-coded constant of the
  offline transport, so that one assertion is documentary. The same line already exists in
  the pre-existing journey test.

### 4.3 P1 adversarial variants (officially found non-scenario SIM LIM)

The SIM LIM outcome is `PROVIDER_UNSUPPORTED` with identity/lookup `None`, bound 62.5,
3 parties and 4 Garden codes in all six variants:

| Variant | Shareholder reads |
|---|---|
| Company, no rows | 1 |
| Company, unit rows | 1 |
| No constitution | 0 |
| No constitution, with rows | 0 |
| Partnership | 0 |
| Public company with rows | 1 |

"Always PROVIDER_UNSUPPORTED" holds for **non-scenario** issuers. A *scenario* issuer
with an official empty profile attaches the overlay. That case is covered by
`test_an_official_issuer_profile_supplies_identity_while_links_stay_local`.

### 4.4 Required-scenario coverage map

| Scenario | Covered by |
|---|---|
| Garden, SIM LIM not found | `test_garden_hybrid_uses_direct_holders_only_and_looks_up_sim_lim_officially` (service) + **new** journey test (API) |
| Garden with a valid independently acquired corporate issuer | Hybrid lane: impossible on Marketplace (**new** P1 test). D-076 local lane: `test_garden_onboarding_discovers_sim_lim_from_its_own_record_once` |
| Eligible cached issuer vs cache miss | `test_repeat_onboarding_reuses_the_official_namespace_with_zero_http_gets`, `test_an_official_issuer_profile_supplies_identity_while_links_stay_local`, `test_issuer_lookups_use_only_the_official_namespace_and_refetch_after_negative_ttl`, journey `cache_hits == 5`, D-076 `test_second_garden_case_uses_fresh_sim_lim_snapshot_with_zero_calls`. **Gap F5:** the Garden hybrid rerun (non-scenario `NOT_FOUND` cache hit counters) is not pinned; I reproduced it manually |
| Garden legacy supplement vs hybrid | `test_default_official_lane_keeps_the_accepted_flattened_garden_supplement` vs Garden hybrid test (no 900/100/100 under hybrid) |
| Complete synthetic topology, incomplete evidence | `test_five_layer_case_attaches_five_corporate_levels_with_exact_paths_and_review` |
| Diamond and 25% aggregation | Same test (DIANA KOH 25 and both five-edge path strings; L5 ENTITY_PROFILE ×1) |
| Validated evidence vs local synthetic | `test_official_shareholder_rows_are_never_overridden_by_the_overlay`, `test_an_official_issuer_profile_supplies_identity_while_links_stay_local`, provider-failure/mismatch/cache/token tests |
| No GoldTier readiness from unresolved ownership | Both journey tests (incl. **new**), AM18 retained-409 tests |

**Gap F6 (advisory):** no test pins the A1 behavior either way. While A1 is undecided that
is appropriate, because pinning would entrench an unauthorised rule. Add the test with
the owner's decision.

### 4.5 Command results

| Check | Result |
|---|---|
| New/changed modules (`test_hybrid_five_layer_overlay.py`, `test_five_layer_hybrid_journey.py`) | 33 passed, 0 failed, 0 skipped (junit) |
| 13 ownership modules (overlay, journey, probe lane, recursive discovery, discovery policy, manual evidence, AM18, Slice B demo, ownership analysis/API, S2, Phase 24, document streamline) | 332 passed, 0 failed, 0 skipped. The implementer's 8-module subset = 15+3+4+30+26+26+40+10 = **154**, matching the report |
| Full backend pytest (unchanged app; run for completeness; watchdog + junit) | 3127 collected: **2952 passed, 174 skipped, 1 failed** (996.7 s), no stall. The failure was `test_phase13_demo_scripts.py::test_http_seeder_runs_twice_against_one_live_memory_backend`, a `TimeoutError` in a socket read against a live in-thread uvicorn memory backend. It also failed once in an isolated module rerun (24.9 s, also a timeout). It then passed 4 times on this worktree (2× single test, 2× module: 11/11) and 11/11 on a `git archive` export of BASE in scratch. Neither the test nor any of its imports is in the reviewed delta, and no module imports the changed test modules. Classification: **pre-existing environment-sensitive flake, unrelated to the candidate**. It is not counted as a pass for the full-suite run |
| Contract lane, CI-style from `apps/backend` (`unittest discover -s ../../tests/contract`) | Ran 44, OK |
| `tests.test_phase_07_delivery_assets` (unittest) | Ran 4, OK |
| `tests/test_dev_context.py`, `test_check_policy_authority.py`, `test_check_project_state.py` | 51 passed |
| `check_secrets` / `check_project_state` / `check_architecture` / `check_policy_authority` | PASS / PASS / PASS / PASS |
| Ruff check + format check (2 changed tests, `--no-cache`) | All checks passed; 2 files already formatted |
| `git diff --check`; `--stat` vs `--ignore-cr-at-eol --stat` | Clean; identical (165+/2-), no EOL churn |
| Untracked report hygiene | LF-only, 231 lines, 0 trailing-whitespace lines, 0 tabs, final newline |
| mypy backend (CI scope `mypy app`) | Not rerun: `apps/backend/app` is byte-identical to BASE, so PR #105 evidence is reused |
| Frontend, browser, physical Mongo | Not applicable: no frontend, persistence or runtime change (frontend subtree identical) |

## 5. Code and Architecture Review

- No application, connector, configuration, persistence or frontend change.
- Test changes are additive only; no existing assertion was modified or weakened.
- The new helpers (`sim_lim_unit_rows`, the `GARDEN_FIELDS` import) reuse existing fixtures.
- No direct route-to-Mongo access, no second calculator, no target-ledger bypass and no
  dormant-provider composition.
- The contract edit is one sentence, within the D-077 section.
- No scope creep. The UI ambiguities (U1–U4) are correctly left as frontend-out-of-scope
  observations, and I verified them against `OwnershipPathExplorer.tsx` lines 43-49 and
  195 and `types.ts` lines 861-872 (the issue-code union lacks `SYNTHETIC_OWNERSHIP_EVIDENCE`).

## 6. Security Review

- No secrets, tokens, URIs, raw provider payloads or PII were added. Synthetic names
  only. `check_secrets` PASS.
- Offline transport only. No credential use, no `.env` read, no Mongo connection.
- No authorization, capability or trust-boundary change. The manual-evidence path keeps
  its existing creator-scoped, lock/CAS-bound checks (unchanged).

## Findings

| ID | Severity | Finding | Required? |
|---|---|---|---|
| F1 | Low (report accuracy) | Report §6 says Garden `CURRENT_EVIDENCE` is "refused, 409…". Observed and by design (AM18), the creator's replacement is persisted on the 409. Ownership becomes `MANUAL_DECLARATION_POC`/REVIEW_REQUIRED with only `INCOMPLETE_LEGAL_ENTITY`; `SYNTHETIC_OWNERSHIP_EVIDENCE`, `CORPORATE_OWNERSHIP_UNRESOLVED` (62.5% bound) and `UBO_REVIEW_REQUIRED` leave the current analysis; the hybrid analysis goes to `prior_analyses`; readiness stays blocked. This bears directly on the A1 decision, because the synthetic relabel also occurs for incomplete graphs. | **Yes**: correct the wording and add it to the A1 scope |
| F2 | Low (report accuracy) | Report P1: "The fail-closed path had **no test anywhere**." The generic non-COMPLETE fail-closed branch of `_classify` was already covered for `PROVIDER_PARTIAL` (`test_recursive_ownership_discovery…[issuer2-False-PROVIDER_PARTIAL]`, which also kills my `accept_partial` mutation). What had no test was the `PROVIDER_UNSUPPORTED` outcome and the official-Marketplace non-scenario issuer path. | **Yes**: narrow the claim |
| F3 | Advisory | Report §6 omits that the OPQ manual replacement also drops `OWNERSHIP_METHOD_UNSUPPORTED` (manual sources carry no `legal_form`). It also omits that `USER_SUPPLIED_DECLARATION` alone reproduces the A1 outcome, so the proposed CURRENT_EVIDENCE-only exclusion is a labelling safeguard. | No (recommended with F1) |
| F4 | Advisory | Report §Identity says the offline Garden profile "mirrors" the live probe "4 OWNER roles". The closeout records 4 people with "OWNER/PARTNER/MEMBER roles"; the offline fixture uses 4 `OWNER`. The outcome is equivalent. | No |
| F5 | Advisory (coverage) | Garden hybrid rerun counters (non-scenario SIM LIM `NOT_FOUND` cache hit: provider-backed 0, cache 1, zero GETs) are reproduced but not pinned. The shared counter code is covered by the scenario-issuer negative-cache tests. | No |
| F6 | Advisory (coverage) | A1 behavior is unpinned pending the owner decision (appropriate). | No |
| F7 | Advisory (pre-existing, out of scope) | `test_phase13_demo_scripts.py::test_http_seeder_runs_twice_against_one_live_memory_backend` timed out 2 of 6 runs on this machine (live uvicorn socket read). It passed on the BASE export and on 4 worktree reruns. It is unrelated to the delta. Track it separately; this candidate need not fix it. | No |

No Critical, High or Medium finding. No security, contract, false-success or scope finding.

## 7. Required Fixes

1. **F1:** In `OWNERSHIP_REVIEW_REQUIRED_INVESTIGATION.md` §6, replace "refused" with the
   observed retained-409 behavior and include it in the A1 decision scope.
2. **F2:** In the P1 row (§5) and wherever else it is restated, limit "no test anywhere" to
   the `PROVIDER_UNSUPPORTED` / official non-scenario issuer path.

Both are documentation-only edits to the implementer report. They need a bounded recheck
of that delta only. Recommended in the same edit: F3. No code, test or contract fix is
required.

## 8. Readiness

- **Candidate:** code, test and contract content verified. After F1/F2 and a passing
  bounded recheck it is ready for Stage 4 publication, subject to explicit owner
  authorization.
- **Owner decision A1:** remains open. It does not block this candidate, because no A1
  behavior was implemented.
- **Not established by this gate:** live ACRA or Marketplace onboarding (NOT_RUN), real
  GoldTier integration and sponsor authority (Q-004/Q-012/Q-019/Q-002 open). No
  next-phase work is authorized by this gate.

## 9. Git Status

- Branch `fix/ownership-review-required-investigation-20261024`; HEAD = `origin/main` =
  `b867e2c7dc53a4fe29a40b4f80e176d8cd25e9e9`.
- Nothing is staged in the real index. Tracked modifications are the 3 reviewed files.
- Untracked files: the reviewed implementer report and this QG report (the only file I
  wrote in the worktree).
- Pre-existing ignored `.ruff_cache/` directories were not created by this gate (ruff ran
  with `--no-cache`).
- I used a temporary index only in my scratch directory. No implementation fix, commit,
  stash, reset, checkout, push, PR, merge or next phase occurred.

## Recheck (round 2) — report-only remediation of F1–F4

Same independent reviewer, 2026-10-24. This verdict applies only to tree
`c798dcfaf5422ff748c3b4c656f732c090685e3c`.

**Recheck result: PASS.**

### Identity

| Item | Value |
|---|---|
| Recomputed candidate tree | `c798dcfaf5422ff748c3b4c656f732c090685e3c`. I used a temporary scratch index: `read-tree HEAD`, add of the same 4 paths, `write-tree`. It matches the coordinator's tree |
| HEAD = `origin/main` | `b867e2c7dc53a4fe29a40b4f80e176d8cd25e9e9` (unchanged) |
| `git diff --name-status 114df971… c798dcfa…` | `M .ai-pipeline/reports/OWNERSHIP_REVIEW_REQUIRED_INVESTIGATION.md` only |
| Real index | Nothing staged. This QG report remains untracked and outside the candidate tree |

The tests, the contract sentence, application code and frontend are unchanged from the
round-1 reviewed tree `114df971…`. Every round-1 execution, mutation and reproduction
result therefore remains valid for `c798dcfa…`. As instructed, I reran no suite.

### Delta review (`git diff 114df971 c798dcfa -- <report>`)

| Item | Result | Basis |
|---|---|---|
| F1 (required) | **Resolved, accurate and complete** | §6 drops "refused". It now states the 409, readiness blocked, the replacement saved by AM18 design (`MANUAL_DECLARATION_POC`, still REVIEW_REQUIRED), only `INCOMPLETE_LEGAL_ENTITY` left, the three disappearing codes including the 62.5% bound, and the hybrid analysis moving to `prior_analyses`. Every element matches my round-1 API reproduction. The A1 row and §6 now place the incomplete-graph relabel inside A1 |
| F2 (required) | **Resolved, accurate** | The P1 row now credits the existing `PROVIDER_PARTIAL` coverage in `test_recursive_ownership_discovery`. It limits the untested scope to the `PROVIDER_UNSUPPORTED` outcome and the officially found non-scenario hybrid-lane issuer. This agrees with my mutations: `accept_partial` was also caught by the existing test, while `partial_label` was caught only by the new test |
| F3 (advisory) | **True to observation** | The OPQ replacement losing `OWNERSHIP_METHOD_UNSUPPORTED` matches what I observed (issues `[]`, `legal_form` null). The `USER_SUPPLIED_DECLARATION` equivalence matches my second OPQ reproduction |
| F4 (advisory) | **True** | The live record held 4 people with OWNER/PARTNER/MEMBER roles (Stage 3.5 closeout). All three values are in the ownership-like set `{OWNER, PARTNER, MEMBER, SHAREHOLDER}` at `ownership_analysis.py:1311`, so the `UBO_REVIEW_REQUIRED` outcome is the same |
| Reframed A1 (options 1–3) | **Faithful** | The question is now "may any manual declaration resolve a D-077 demonstration case?". The PR #69 citation ("the exact current graph"; exact-100 declarations) is correct. D-077 is correctly limited to the hybrid analysis and the synthetic-basis field. Option 1 lists the observed mitigations. Option 2 is correct: a `CURRENT_EVIDENCE` mismatch check runs before persistence and surfaces as HTTP 409 `OWNERSHIP_SELECTED_SOURCE_MISMATCH` with no stored change (existing `tests/test_p2_remediation.py` lines 130-137). Option 2 also correctly admits it does not stop `USER_SUPPLIED_DECLARATION`. Option 3 is correctly flagged as a stronger new rule needing defined scope and authority. Nothing is implemented, and no authority is claimed |
| §10 next action | **Accurate** | Round-1 verdict and tree are cited correctly. The "report only; no test, contract or code change" claim matches the name-status diff. Commit, push and PR are still reserved for the owner |
| Hygiene | **Clean** | LF only, 259 lines, 0 trailing-whitespace lines, 0 tabs, final newline. The working file equals the frozen blob |
| New inaccuracy or scope claim | None material | Two advisories follow, both on unchanged pre-existing text |

### Recheck advisories (non-blocking; no required fix)

- **R2-A.** §7 still describes the journey test as pinning "refusal of `CURRENT_EVIDENCE`
  for the incomplete graph". The test pins the 409 response and the continued block,
  which is true. Saying "the 409 for `CURRENT_EVIDENCE`" would match the corrected §6
  more precisely.
- **R2-B.** The P1 row's first cell still says "always `PROVIDER_UNSUPPORTED`" without
  "non-scenario". Its second cell now names the non-scenario case, and round-1 §4.3
  recorded the qualification. Optional wording polish.

### Recheck readiness and Git status

- No required fix remains for tree `c798dcfa…`. The candidate is ready for Stage 4
  publication only with explicit owner authorization.
- Owner decision A1 remains open and does not block this candidate.
- I made no repository edit other than appending this section to my QG report. There was
  no git mutation of the real index or branches, no network, no `.env` and no Mongo.

## Recheck (round 3) — owner decision A1 = option 1 (D-078) delta

Same independent reviewer, 2026-10-24. This verdict applies only to tree
`dd7f7e46e31d9dc75f21c3339ffaa8c6e0175aca`.

**Recheck result: PASS WITH MINOR FIXES.**

The decision is recorded faithfully to the owner's words. The pinning test is meaningful
and survives mutation. No runtime behavior changed.

Two factual statements in D-078 (one also in the contract bullet) overstate the
safeguards (R3-1, R3-2), and §9 of the investigation report is stale (R3-3). All three
are Low, documentation-only and bounded.

### Identity

| Item | Value |
|---|---|
| Recomputed tree | `dd7f7e46e31d9dc75f21c3339ffaa8c6e0175aca` over 5 paths (the previous 4 plus `docs/decisions/DECISION_LOG.md`). I used a temporary scratch index (`read-tree HEAD`, add the 5 paths, `write-tree`). It matches the coordinator's tree |
| HEAD = `origin/main` | `b867e2c7dc53a4fe29a40b4f80e176d8cd25e9e9` (unchanged) |
| `git diff --name-status c798dcfa… dd7f7e46…` | `M` investigation report, `M apps/backend/tests/test_five_layer_hybrid_journey.py`, `M docs/contracts/OWNERSHIP_UBO_PROFILE.md`, `M docs/decisions/DECISION_LOG.md`. Nothing else |
| BASE tree `24fe8a44…` to `dd7f7e46…` under `apps/backend/app`, `apps/frontend`, `scripts` | 0 files changed |
| Real index | Nothing staged. This QG report is untracked and outside the tree |

### Delta review

**`D-078` (DECISION_LOG) and the contract's "Manual replacement (D-078)" bullet**

What is faithful and true:

- Option 1 matches the owner's words: no restriction; accountability through the
  receipt, the prior analysis and target confirmation.
- "`MANUAL_DECLARATION_POC`/`LOCAL` … never ACRA, Mock or Live evidence, never a legal UBO
  determination" matches my reproductions.
- The receipt fields (actor, time, source selection, replaced analysis and version) match
  `ManualOwnershipReviewReceipt` and `replace_review_required_source`, lines 771-776.
- "Without `SYNTHETIC_OWNERSHIP_EVIDENCE`" is true.
- "An incomplete replacement still requires review" matches the Garden 409, where the
  replacement stays REVIEW_REQUIRED.
- "No runtime behavior changed" is true.
- The text is consistent with D-077 (which covers only the hybrid analysis) and with the
  PR #69 source decisions.
- No sponsor, legal or Live claim is made. `USER_AUTHORIZED_POC` with Q-014/Q-004/Q-012
  left open is appropriate.
- Nothing untrue is asserted about `OWNERSHIP_METHOD_UNSUPPORTED`; the decision does not
  mention it.

The two overstatements:

- **R3-1.** "Target-dispatch confirmation required before any GoldTier *operation*" is
  inaccurate. A GoldTier Search operation has already run before the ownership stage. On
  the OPQ case before replacement I observed `completed_stages = ['REGISTRY',
  'GOLDTIER_SEARCH', 'DOCUMENT']`, and AM18 asserts `target.calls == ["search"]`.
  Confirmation gates GoldTier *target mutation/dispatch*. The contract bullet's wording
  ("target-dispatch confirmation is still required") is accurate.
- **R3-2.** Prior-analysis retention is presented as durable: D-078 says "the retained
  prior hybrid analysis…", and the contract says it "stays in `prior_analyses`". The
  history is bounded:
  - `OwnershipAnalysisRecord.prior_analyses` has `max_length=4`;
  - replacement keeps `current.prior_analyses[-3:]` plus one snapshot.
  - Reproduced: after `CURRENT_EVIDENCE` and then 4 further accepted
    `USER_SUPPLIED_DECLARATION` revisions (ANALYZED stays editable before submission),
    the prior classifications went from `[OVERLAY, SINGLE…]` to four `SINGLE_SOURCE`.
  - The hybrid snapshot, its synthetic issue and links, and the first receipt (which
    lives inside the snapshots) were evicted from the ownership record.
  - The PR #69 section of the same contract says "bounded prior analyses", so the bound
    is documented. But D-078 cites retention as one of three accountability safeguards
    without the qualifier.
  - I did not raise this bound in rounds 1–2. The owner should be told the safeguard is
    bounded; whether option 1 still stands is the owner's call.

**Journey test**

- The `keep_current_evidence` helper builds the same payload as the old inline Garden
  call. The only difference is `root_registration_number`, now read from the case entity
  (still `11111999A` for Garden).
- The Garden test's 18 `assert` lines are byte-identical before and after.
- The new `test_a_creator_may_keep_the_synthetic_graph_only_through_the_accountable_path`
  passes. It asserts:
  - 200, `WAITING_FOR_REVIEW`, active exceptions exactly `[TARGET_CONFIRMATION_REQUIRED]`;
  - no GoldTier result and no submission;
  - ANALYZED/`MANUAL_DECLARATION_POC` links;
  - receipt `CURRENT_EVIDENCE`, `replaced_analysis_id` = the hybrid id, and an actor;
  - exactly one prior entry: the hybrid analysis id, its classification, its synthetic
    issue and `LOCAL_SYNTHETIC_RELATIONSHIP` links;
  - DIANA 25, and the provisional set {BEATRICE, DIANA}.

Mutation results (in-memory plugin `qg_mutations_r3.py` in scratch; journey module, 4
tests; baseline 4 passed):

| Mutation | Result |
|---|---|
| `skip_target_confirmation`: TARGET_CONFIRMATION_REQUIRED never added | New test fails (`'RUNNING' == 'WAITING_FOR_REVIEW'`): the pipeline would proceed |
| `unbind_receipt`: `replaced_analysis_id` cleared | New test fails (receipt binding) |
| `drop_receipt` | New test and Garden test fail |
| `drop_prior`: snapshot removed | New test fails (the existing persistence rejects it with a 409 first). The Garden test also fails |
| `scrub_prior`: snapshot classification/issues scrubbed | Only the new test fails |
| `keep_synthetic_issue_on_manual`: replacement keeps the hybrid classification | New test fails |

So the test is not tautological. It would catch loss of the receipt binding, loss or
scrubbing of prior-analysis retention, and a bypass of target confirmation.

**Investigation report**

- The P1 row now says "non-scenario" (R2-B addressed).
- §7 now says "the 409 for `CURRENT_EVIDENCE`" (R2-A addressed).
- The A1 row, the §6 owner-decision paragraph, the §7 additions and §10 are accurate.
- The §8 row "137 passed" matches my run.
- **R3-3:** §9 "Remaining provider and sponsor limitations" still lists "**Owner decision
  A1** above", which is now decided as D-078 (stale).
- The §6 paragraph inherits R3-2 ("the retained prior analysis").

### Evidence (only what the delta invalidates)

| Check | Result |
|---|---|
| Overlay, journey, manual evidence, AM18, P2 remediation, recursive discovery | **137 passed**, 0 failed, 0 skipped. Per module: 30/4/26/15/22/40. The new test and the refactored Garden test are among them |
| Contract lane (CI-style) | Ran 44, OK |
| `tests.test_phase_07_delivery_assets` | Ran 4, OK |
| `test_dev_context.py`, `test_check_policy_authority.py`, `test_check_project_state.py` | 51 passed |
| `check_secrets` / `check_project_state` / `check_architecture` / `check_policy_authority` | PASS ×4 |
| Ruff check + format (journey test, `--no-cache`) | Pass; already formatted |
| `git diff --check`; `--stat` vs `--ignore-cr-at-eol --stat` | Clean; identical (4 files, 250+/2-) |
| Investigation report hygiene | LF only, 283 lines, 0 trailing whitespace, 0 tabs, final newline. Working file equals the frozen blob |
| Unchanged lanes (overlay test module content, app, frontend, physical Mongo) | Not rerun. Round-1 evidence still valid (no app, frontend or scripts change) |

### Round-3 findings

| ID | Severity | Finding | Required? |
|---|---|---|---|
| R3-1 | Low | D-078 says target-dispatch confirmation is required "before any GoldTier operation". GoldTier Search has already run. Say "before any GoldTier target mutation (dispatch)". The new test's comment uses the same phrase (fix together) | **Yes** |
| R3-2 | Low | D-078 ("the retained prior hybrid analysis") and the contract bullet ("stays in `prior_analyses`") omit that history is bounded to the latest four prior analyses. Four further accepted revisions evict the hybrid snapshot and its receipt (reproduced). Add the qualifier, e.g. "retained in the bounded prior-analysis history (latest four)", in D-078, the contract bullet and report §6. Surface the bound to the owner | **Yes** |
| R3-3 | Low | Report §9 still lists owner decision A1 as remaining | **Yes** |
| R3-A | Advisory | D-078 lists `DOCUMENT_OBSERVATIONS`. That is true as a rule, but it still needs selected reviewed rows matching every edge, which the OPQ demo PDF does not provide. "Subject to their existing conditions" would be clearer | No |
| R3-B | Advisory | Neither D-078 nor the contract bullet notes that the replacement also drops `OWNERSHIP_METHOD_UNSUPPORTED` (recorded only in report §6) | No |
| R3-C | Advisory | The test name says "only through the accountable path". The test proves the path is accountable, not that it is the only one | No |

### Readiness and Git status

- After R3-1–R3-3 and a bounded recheck of that wording delta, the candidate is ready
  for Stage 4 publication only with explicit owner authorization.
- I recommend the coordinator confirm with the owner that D-078 stands, given the
  bounded-history fact in R3-2.
- I made no repository edit other than appending this section. There was no git mutation
  of the real index or branches, no network, no `.env` and no Mongo. Scratch scripts are
  only in my scratch directory.

## Recheck (round 4) — R3 wording fixes

Same independent reviewer, 2026-10-24. This verdict applies only to tree
`2ac3d7fbbb5a13d45ba978eb855fa58eef34f3a1`.

**Recheck result: PASS WITH MINOR FIXES.**

R3-1, R3-3, R3-A, R3-B and R3-C are resolved accurately. R3-2 is substantively
resolved: the bound is stated and correct for the contract bullet. One clause added to
D-078 and report §6 is inaccurate about receipts (R4-1). That clause came from my own
imprecise round-3 wording, which I correct below. Documentation only.

### Identity

| Item | Value |
|---|---|
| Recomputed tree | `2ac3d7fbbb5a13d45ba978eb855fa58eef34f3a1` over the same 5 paths (temporary scratch index). It matches the coordinator's tree |
| HEAD = `origin/main` | `b867e2c7dc53a4fe29a40b4f80e176d8cd25e9e9` |
| `git diff --name-status dd7f7e46… 2ac3d7fb…` | `M` investigation report, journey test, contract, `DECISION_LOG.md`. Nothing else |
| BASE tree to `2ac3d7fb…` under `apps/backend/app`, `apps/frontend`, `scripts` | 0 files changed |
| Real index | Nothing staged |

### Delta review

| Item | Result |
|---|---|
| R3-1 | **Resolved.** D-078 now says "before any GoldTier target mutation. GoldTier Search runs earlier and is read-only". The test comment says "target mutation". Report §6 says "Target confirmation gates GoldTier target mutations…". All three match the observed `completed_stages` (REGISTRY, GOLDTIER_SEARCH, DOCUMENT) before ownership |
| R3-2 | **Bound stated correctly; one clause inaccurate (R4-1).** "Latest four" matches `prior_analyses` `max_length=4` and the `[-3:]` plus snapshot logic (`ownership_analysis.py:809`, `:888`). The contract bullet ("stays in the bounded `prior_analyses` (latest four only)") is accurate. D-078 and §6 say the hybrid snapshot "and the receipts stored in it" leave after four further accepted revisions. I re-ran the reproduction with five revisions, and that is not what happens: see R4-1 |
| R3-3 | **Resolved.** §9 now reads "resolved as D-078", with the bounded-safeguard note |
| R3-A | **Resolved.** "Each subject to its existing conditions" is in D-078 |
| R3-B | **Resolved and true.** D-078 and the contract state that `OWNERSHIP_METHOD_UNSUPPORTED` is dropped because manual sources carry no registry legal form. This matches the observed replacement (`legal_form` null; issues `[]`) and the code: the replacement record carries no `legal_form`, and the method check is `record.legal_form == OTHER` |
| R3-C | **Resolved.** The test is renamed to `test_a_creator_may_keep_the_synthetic_graph_through_the_accountable_path`. The diff touches only the `def` line and one comment line, so the body and assertions are unchanged. It passes, and my round-3 mutation evidence still applies |
| Report §10 | Accurate (round-3 verdict and tree cited; wording and test name only) |

### R4-1 detail (five-revision reproduction, offline API)

After `CURRENT_EVIDENCE`, `prior_analyses` holds the hybrid snapshot with
`manual_review_receipt = None`. The hybrid analysis is a registry analysis and never
carries a receipt. The `CURRENT_EVIDENCE` receipt (`replaced_analysis_id` = hybrid) sits
on the current record, then in the *next* snapshot.

| Accepted `USER_SUPPLIED_DECLARATION` revision | `prior_analyses` (classification, receipt selection) |
|---|---|
| 1 | `[OVERLAY/None, SINGLE/CURRENT_EVIDENCE]` |
| 3 | `[OVERLAY/None, SINGLE/CURRENT_EVIDENCE, SINGLE/USD, SINGLE/USD]` |
| 4 | `[SINGLE/CURRENT_EVIDENCE, SINGLE/USD ×3]`: hybrid gone, the CURRENT_EVIDENCE receipt naming it still present |
| 5 | `[SINGLE/USD ×4]`: CURRENT_EVIDENCE receipt gone |

So "the hybrid snapshot and the receipts stored in it" is vacuous for the hybrid snapshot
and misleading about timing. My round-3 text ("the first receipt (which lives inside the
snapshots) were evicted" after four revisions) was imprecise in the same way, and I
correct it here.

Separately, `_load_locked` (document or identity reloads) also adds a snapshot under the
same bound (`:888`), so "accepted revisions" is not the only thing that consumes history
slots.

Suggested exact wording for D-078 and §6: "Retention is bounded to the latest four prior
analyses: after four further snapshot-creating changes (manual replacements or
document/identity reloads) the hybrid snapshot is no longer in the ownership record. The
`CURRENT_EVIDENCE` receipt that names it, held in the next snapshot, drops out one change
later. The hybrid analysis itself carries no receipt."

### Evidence (only what the delta touches)

| Check | Result |
|---|---|
| Journey module | **4 passed**, including the renamed test and the Garden test |
| Ruff check + format (journey test, `--no-cache`) | Pass; already formatted |
| Contract lane (CI-style) | Ran 44, OK |
| `check_secrets` / `check_project_state` / `check_architecture` / `check_policy_authority` | PASS ×4 |
| `test_dev_context.py`, `test_check_policy_authority.py`, `test_check_project_state.py` | 51 passed |
| `tests.test_phase_07_delivery_assets` | Ran 4, OK |
| `git diff --check`; `--stat` vs `--ignore-cr-at-eol --stat` | Clean; identical (4 files, 255+/2-) |
| Investigation report hygiene | LF only, 296 lines, 0 trailing whitespace, 0 tabs, final newline; equals the frozen blob |

### Round-4 findings

| ID | Severity | Finding | Required? |
|---|---|---|---|
| R4-1 | Low | D-078 and report §6 say that after four further accepted revisions "the hybrid snapshot and the receipts stored in it" leave the record. The hybrid snapshot holds no receipt. The `CURRENT_EVIDENCE` receipt naming it survives until the fifth change (reproduced). Reword, e.g. as suggested above. The contract bullet needs no change | **Yes** (wording only) |
| R4-A | Advisory | "Accepted revisions": document/identity reloads also consume the four-slot history (`_load_locked`, line 888). Covered if the suggested wording is used | No |

### Readiness and Git status

- After the R4-1 wording correction and a bounded recheck of that sentence, the candidate
  is ready for Stage 4 publication only with explicit owner authorization.
- The owner's reconfirmation of D-078 is outside this review, as instructed.
- I made no repository edit other than appending this section. There was no real-index
  or branch mutation, no network, no `.env` and no Mongo.

## Recheck (round 5) — R4-1 reworded

Same independent reviewer, 2026-10-24. This verdict applies only to tree
`415ee1755e7fea355f906f470330f076391f698a`.

**Recheck result: PASS.** No required fix remains.

### Identity

| Item | Value |
|---|---|
| Recomputed tree | `415ee1755e7fea355f906f470330f076391f698a` over the same 5 paths (temporary scratch index). It matches the coordinator's tree |
| HEAD = `origin/main` | `b867e2c7dc53a4fe29a40b4f80e176d8cd25e9e9` |
| `git diff --name-status 2ac3d7fb… 415ee175…` | `M` investigation report, `M docs/decisions/DECISION_LOG.md`. Nothing else |
| BASE tree to `415ee175…` under `apps/backend/app`, `apps/frontend`, `scripts` | 0 files changed |
| Real index | Nothing staged |

### Delta review

**D-078 retention sentence and report §6 bullet: true.**

Each claim checked against the code and my five-revision reproduction (round 4):

- "Bounded to the latest four prior analyses": `prior_analyses` holds at most 4, and both
  snapshot sites keep the last 3 plus one new snapshot (`ownership_analysis.py:809`,
  replacement; `:888`, load/reload).
- "After four further snapshot-creating changes (manual replacements or document/identity
  reloads), the hybrid snapshot … no longer in the ownership record": reproduced (the
  hybrid snapshot was present through revision 3 and gone at revision 4). The
  `_load_locked` path consumes slots the same way.
- "The hybrid analysis itself carries no receipt": observed `manual_review_receipt =
  None` on the hybrid snapshot.
- "The `CURRENT_EVIDENCE` receipt that names it is held by the next analysis and drops out
  one change later": the receipt sits on the replacing manual analysis, then in its
  snapshot (`_snapshot_prior_analysis` copies `manual_review_receipt`). It was still
  present at revision 4 and gone at revision 5, as observed.
- The old phrases ("receipts stored in it", "four further accepted revisions") no longer
  appear in either file.

**Report §10 round-4 line: accurate** (round-4 verdict and tree cited; R4-1 described
correctly).

No new inaccuracy, scope claim or authority claim. The contract bullet and the test are
unchanged from round 4.

### Evidence (only what the edit touches)

| Check | Result |
|---|---|
| `check_project_state` / `check_policy_authority` / `check_secrets` | PASS / PASS / PASS |
| `test_dev_context.py`, `test_check_policy_authority.py`, `test_check_project_state.py` | 51 passed |
| `git diff --check`; `--stat` vs `--ignore-cr-at-eol --stat` | Clean; identical (4 files, 257+/2-) |
| Investigation report hygiene | LF only, 301 lines, 0 trailing whitespace, 0 tabs, final newline; equals the frozen blob |
| Unchanged lanes (tests, contract, app, frontend) | Not rerun. Round 1–4 evidence remains valid for these paths |

### Readiness and Git status

- Candidate tree `415ee175…` has no required fix. It is ready for Stage 4 publication
  only with explicit owner authorization.
- The owner's reconfirmation of D-078 in light of the bounded history is outside this
  review.
- Hosted CI, commit, push, PR and merge have not occurred.
- I made no repository edit other than appending this section. There was no real-index
  or branch mutation, no network, no `.env` and no Mongo.
