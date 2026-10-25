# Sim Lim D-081 POC equal-unit distribution: independent Quality Gate (Stage 3)

Reviewer: independent Stage 3 Quality Gate. I did not author or remediate this content.
Review only. This file is the only file written. Date: 2026-10-24.

## 1. Executive Result

**FAIL.**

The D-081 arithmetic, opt-in boundary, fail-closed refusals, identity rules and
persistence guards are correct. I verified each one independently.

One finding blocks acceptance. D-081 changes how an existing readiness path behaves, and
neither the documents nor the tests disclose it:
- Before D-081, the Garden hybrid case with SIM LIM's live-shape rows kept SIM LIM
  unresolved. A creator `CURRENT_EVIDENCE` decision (the D-078 path) was refused with
  `409 ZERO_TOUCH_MANUAL_OWNERSHIP_REVIEW_REQUIRED`, and readiness stayed blocked.
- After D-081, the same decision succeeds (`200`). The ownership record becomes
  `ANALYZED` / `MANUAL_DECLARATION_POC` with no issues, and the readiness blockers clear
  (`[]`). Only `TARGET_CONFIRMATION_REQUIRED` remains before a GoldTier target mutation.
- The adopted numbers are the POC-assumed, class-pooled percentages. They become
  `PROVISIONAL_UBO_CANDIDATE` classifications (51.13636375 MET and 37.5 MET).

This contradicts the owner constraint "keep review required with no readiness or GoldTier
effect" and the D-081 decision text "Readiness and GoldTier stay blocked"
(`docs/decisions/DECISION_LOG.md:553`). D-078 lets a creator replace a hybrid analysis
"with no new restriction", but it predates D-081 and names only
`LOCAL_SYNTHETIC_RELATIONSHIP` graphs. No owner decision records whether it extends to
links built on the POC assumption. Per AGENTS.md, this material ambiguity stops the
dependent work, which is publication.

Consequence: the candidate is not ready for Stage 4. Remediation is bounded: an owner
decision, then truthful documentation plus a pinned test, or an owner-authorized
restriction. A re-QG then reviews only that delta and the evidence it invalidates.

## 2. Reviewed identity and acceptance checklist

| Item | Value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\sim-lim-acra-ownership-followthrough-20261024` |
| Branch | `feat/sim-lim-acra-ownership-followthrough-20261024` |
| BASE = HEAD = `origin/main` | `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322`; `git ls-remote origin refs/heads/main` returned the same SHA, so no drift |
| Reviewed content | 39 tracked modifications (`git diff --name-only`). The untracked `.ai-pipeline/reports/*` files are outside the product tree |
| Recomputed product tree | `1fa01fbc2d233f8f0dcc70a78fac1a1c0a64ae05`. I used a temporary `GIT_INDEX_FILE` under scratchpad `qg81` (`read-tree HEAD`, `add -u`, `write-tree`). It matches the brief at gate start and again at gate end. The real index has no staged paths |
| D-081 delta | `git diff 5dfa844..1fa01fb`: 13 files (5 app, 2 test, 6 docs), +608/-136, `apps/frontend` 0 files |

| Owner acceptance item | Result | Evidence |
|---|---|---|
| `holder active units / issuer total active units x 100`, six decimals, reuses `quantized_unit_share` | PASS | `hybrid_ownership_overlay.py:247-305` calls `quantized_unit_share` (`garden_business.py:374`, ROUND_HALF_UP to 6 dp). No new rounding. Decimal only |
| Garden values 81.818182 / 9.090909 / 9.090909, then 51.13636375 / 37.5 / 5.681818125 / 5.681818125 | PASS | I ran scratch `poc_check.py` myself. Values reproduced exactly; all `REVIEW_REQUIRED`/`INDETERMINATE` |
| Withdrawn excluded; per-issuer denominator; classes pooled only in links, rows keep their true class, currency and status | PASS | Code filters `current_interest` rows of the one issuer. The live-shape test and my probes show rows unchanged (withdrawn row retained as history) |
| Links labelled `LOCAL_POC_ASSUMED_EQUAL_UNITS` / `LOCAL` | PASS | Verified in `poc_check.py` output. Source reference is `POC_EQUAL_UNITS_<uen>.POC_<uen>_<n>` |
| Opt-in only | PASS | Probe `probe_guard.py`: coordinator with `overlay=None` retains D-079 rows with no POC links; `garden_legacy_supplement` has no POC label or reason; `_validate_source` refuses POC links unless `local_overlay=True` and environment `LOCAL` |
| Fail closed on bad rows | PASS | Probe `probe_d081.py`: 10 refusal cases match a forced-refusal baseline exactly (section 4) |
| Review stays required with no readiness or GoldTier effect | **NOT MET / UNRESOLVED** | Automated analysis: PASS. Existing creator path: readiness now clears (F1) |
| Preservation list | PASS (code) | Engine, comparator, cache schema, connector/auth, Garden fixture, five-layer math, reconciliation, manual service, CAS/RBAC/GoldTier and frontend are untouched by D-081. Edits to `OwnershipAnalysisService` (3 small hunks) and the coordinator (1 hook) are additive. The behavioral effect on manual authority/readiness is F1 |
| Persistence: v13 rejects POC links and records, v12 rejects the reason, v14 round trip | PASS | `persistence/models.py:838-875`. The store applies the <=13 guard to v12 too (`mongo_case_store.py:611-616`). Unit codec test plus my physical rerun |

## 3. Contract and Integration Findings

**F1: Major, current blocker (unresolved owner authority plus a documentation
truthfulness defect on a readiness claim).**

D-081 newly enables the D-078 `CURRENT_EVIDENCE` creator path to clear the ownership
readiness blocker for the Garden hybrid case.

- Reproduction is offline, using the fixture transport and memory persistence:
  - `qg81/probe_d078.py`: Garden journey with live-shape SIM LIM rows, then
    `keep_current_evidence`. Result: `CURRENT_EVIDENCE status: 200`, ownership `ANALYZED`
    / `MANUAL_DECLARATION_POC`, issues `[]`, readiness blockers `[]`, exceptions
    `['TARGET_CONFIRMATION_REQUIRED']`, `goldtier_result` None, 0 external calls.
    Candidates: 51.13636375 and 37.5 `PROVISIONAL_UBO_CANDIDATE`; 5.681818125 x2
    `BELOW_PROVISIONAL_THRESHOLD`.
  - `qg81/probe_d078_baseline.py`: identical, but with the POC builder refused, which is
    exactly the D-079/D-080 outcome. Result: `409 ZERO_TOUCH_MANUAL_OWNERSHIP_REVIEW_REQUIRED`,
    readiness blocker `OWNERSHIP_REVIEW_REQUIRED` remains.
- After replacement, the current graph's links read `MANUAL_DECLARATION_POC`. The
  `LOCAL_POC_ASSUMED_EQUAL_UNITS` label survives only in `prior_analyses`, which are
  retained for at most four further changes (D-078).
- No document or test discloses this:
  - D-081 says "Readiness and GoldTier stay blocked" (`DECISION_LOG.md:553`).
  - The implementer report states readiness and manual authority are "Unchanged".
  - The pinned Garden journey test (`test_five_layer_hybrid_journey.py:165-203`) runs
    without SIM LIM rows. It cannot observe the change.
  - D-078 (`DECISION_LOG.md:410-435`) covers creator retention of
    `LOCAL_SYNTHETIC_RELATIONSHIP` graphs. Whether it also covers class-pooled POC
    percentages, which the owner said must have no readiness effect, is not recorded.
- Classification: not a code defect against D-078's literal text. It is an unverified
  owner acceptance criterion, plus an untrue safety statement in a current decision record.

**Authority and claims (no finding).** D-081, the ownership contract, ADR-013,
ARCHITECTURE, PROJECT_STATE and demo §8 all label the result `USER_AUTHORIZED_POC` /
`PROJECT_DEFINED_PROVISIONAL`. None claims ACRA ownership, a verified denominator, Live
status, class-rights semantics (Q-012), legal UBO (Q-004) or sponsor approval. The
holder names in the docs (ABCD123, TAN WEI LING, EFGH2345, FGH SERVICES) already exist
in tracked content on `origin/main`, so no new PII is added. Test identifiers are
synthetic.

**Later sponsor dependencies (unchanged, not blockers here):** Q-004, Q-012, Q-019,
Q-002. Marketplace denominator and relationship semantics remain unconfirmed.

## 4. Tester and Adversarial Findings

Commands ran with the venv interpreter, `PYTHONDONTWRITEBYTECODE=1`,
`-p no:cacheprovider`, and `app.__file__` confirmed inside the worktree. No bytecode or
cache was written to the repository.

| Check (this gate) | Result |
|---|---|
| Focused pytest: 12 ownership/persistence files (official shareholder, hybrid five-layer, five-layer journey, recursive discovery, discovery policy, phase12 persistence, Garden fixture/protocol, manual evidence, ownership analysis, recursive real-Mongo, phase16 cache) | 340 collected, 336 passed, 4 skipped (physical without URI), 0 failed |
| Physical Mongo rerun of the changed suites (`test_recursive_ownership_real_mongo.py`, `test_phase16_registry_cache_real_mongo.py`) on the disposable `sim-lim-d081-mongo` (`mongo:7`, loopback); generated allowlisted DBs; URI never printed | 10 passed, 0 skipped |
| Ruff `ruff check . --no-cache`; mypy `app` (cache in scratchpad) | All checks passed; mypy no issues in 129 files |
| Contract lane (`tests/contract`) | 44 OK |
| `tests.test_dev_context`, `test_check_project_state`, `test_check_architecture` | 55 OK |
| `check_project_state`, `check_architecture`, `check_secrets`, `check_tooling_config`, `check_policy_authority`, `check_external_provider_readiness` | All PASS |
| `dev_context.py --benchmark` | Routine mean reduction 30.0% (35.6 / 21.0 / 33.5): passes, with almost no headroom |
| `git diff --check`; `--stat` vs `--ignore-cr-at-eol --stat` | Clean; identical (39 files, +1292/-150) |
| Untracked D-081 implementer report whitespace | No trailing whitespace, no tabs, final newline |

**Adversarial probes** (`qg81/probe_d081.py`). Each case is compared with the same input
under a forced POC refusal:

| Case | Outcome |
|---|---|
| Active row without units; zero plus positive units; all rows withdrawn | No links. D-079 `OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE` retained, bound 62.5, identical to refusal |
| Exact duplicate id (active+active, withdrawn+active) | Rejected upstream (`SHAREHOLDER_PROVIDER_FAILED`). POC never reached. Identical |
| Case-variant duplicate (`syn-a`/`SYN-A`); self id (upper, lower, withdrawn) | Refused by POC normalization. D-079 outcome identical |
| Cap exhaustion (`max_parties=4`) | Merge refused. D-079 outcome identical. `_merge` mutates only after all checks |
| Missing status | Decoder rejects (`REGISTRY_OPERATION_MALFORMED_RESPONSE`). Identical |
| Corporate holder whose id equals the root UEN | Attached as issuer-scoped `UNVERIFIED_UEN` (Marketplace decoder never supplies a registration identifier). No identifier inferred, no cycle, bound 5.681818125 |
| Hostile display name; 60-char id; 64 holders | Accepted as escaped text / hashed scoped id / 64 links; review required |
| Six equal holders | Links 16.666667 x6 sum to 100.000002, so the bound is invalidated (F3) |

**Review semantics.** Verified:
- `topology_complete` follows `discovery_topology_resolved`;
- `graph_complete`, `official_identity_complete` and `quantitative_evidence_complete`
  are false; certainty is `UNCERTAIN`;
- the bound is 31.25 with an unverified corporate holder and 0 with persons only;
- `SYNTHETIC_OWNERSHIP_EVIDENCE` always forces `REVIEW_REQUIRED`;
- the POC denominator message is 185 characters for the Garden case (at most 188 at the
  row cap), within the 200 limit;
- the non-POC message is byte-identical to D-080 in refused cases.

**Stage 2 evidence verification** (bound to tree `1fa01fb`). The latest tracked-file
mtime is 13:28:41, before every artifact; the full backend run started at about 13:31:47.

| Claimed | Verified against the artifact |
|---|---|
| Full backend, 4 chunks | JUnit: 732+994+653+786 = 3165 collected, 175 skipped, 0 failures/errors, so 2990 passed. The chunk runner globs all 146 `tests/test_*.py` files |
| Physical Mongo | `physical_d081.log`: PASSED, 25 suites, 169/169, 0 skipped |
| E2E run 1 FAIL at 67/115 | Confirmed: `getByLabel('User ID')` not found within 15 s after `page.goto("/")` on the unauthenticated login page, before any ownership request |
| Isolated rerun | PASS (7.4 s) |
| Run 2 | JSON `status=PASS`, `complete=true`, `keep_going=true`, `counts={PASS:115}`, started 06:13:55Z |

The frontend is byte-identical to BASE, so the "non-reproducing transient" classification
is truthful, and the failed run is disclosed. Browser E2E was not rerun by this gate.
CI unittest lanes other than those listed above are reused, not rerun; D-081 does not
reach them.

## 5. Code and Architecture Review

- **F2: Low (defense in depth).** `OwnershipDiscoveryRecord` accepts the reason
  `OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS` with a non-`PROVIDER_PARTIAL` outcome and no
  rows (`domain/ownership.py:451-455`). `discovery_topology_resolved` keys on the reason
  alone (`ownership.py:492-497`).
  - Probe `qg81/probe_validator.py`: `NOT_FOUND`, `PROVIDER_FAILED` and `UNVERIFIED_UEN`
    with the POC reason are ACCEPTED and counted topology-resolved.
  - The service cannot produce this. It matters only for a corrupted v14 read inside a
    hybrid audit, where review is still forced.
  - The test comment "The POC reason is valid only as a retained-rows partial outcome"
    (`test_official_shareholder_evidence.py:316`) overstates the enforcement.
- **F3: Low.** Quantized links can sum to more than 100 by up to n x 0.0000005. The
  unchanged bound treats any parent above 100 as over-allocated
  (`ownership_discovery.py:887`), so `unresolved_upper_bound_percent` becomes `None`.
  - This is conservative: no false success.
  - It is undocumented and untested.
  - The `Fraction` assertion at `test_official_shareholder_evidence.py:500` is a
    tautology (sum of u_i / sum u is always 1). The implementer report describes it as
    checking the links. The meaningful assertion for the Garden instance is line 512.
- **F4: Low (test depth).** Only all-zero units and a monkeypatched refusal are pinned
  (`:1042`). No test pins:
  - an active row without units, or partial zero units;
  - case-variant duplicates, or self identifiers;
  - merge or cap refusal.

  Removing those guards would pass the suite. The physical test round-trips a POC-bearing
  record but does not assert the POC reason or links. My probes confirm current behavior
  is correct.
- **F5: Low (wording).** `SYNTHETIC_OWNERSHIP_EVIDENCE` still reads "Ownership links are
  LOCAL_SYNTHETIC_RELATIONSHIP demonstration declarations" when POC links are present
  (`ownership_analysis.py:1232`). The denominator wording uses `poc = any(...)` across
  retained issuers (`:1187`). With two retained issuers, one refused, the text would
  overstate. Both stay truthful that nothing is ACRA-returned.
- Scope and coupling are good. There is one hook after D-079 retention, reuse of `_merge`
  (issuer-scoped ids, caps, atomic mutation) and the existing graph validation, and no new
  scheduler, cache, repository or provider.
- Rollback:
  - pre-D-080 code rejects v14 envelopes (as stated);
  - D-080-only code would also fail closed on D-081 records, because the POC reason with
    rows violates D-080's retained-rows validator.
- POC link `sourced_at` is the analysis time, not the rows' retrieval time. This is
  acceptable for a `LOCAL` derived label. Informational.

## 6. Security Review

No security finding:
- no secrets, credentials, `.env` access, network path or logging change was added;
- provider names and ids pass the existing safe-text models, and the React frontend
  renders them escaped;
- persistence fails closed on POC content in v12/v13;
- no frontend authorization was added, and RBAC and CAS are unchanged.

This gate made no ACRA or GoldTier calls. The only network call was a read-only
`git ls-remote` to the origin remote. No Mongo URI was printed or persisted.

## 7. Required Fixes

Current blocker:
1. **F1: owner decision, then remediation.** Obtain an explicit owner decision on whether
   the D-078 `CURRENT_EVIDENCE` path may adopt D-081 POC-assumed, class-pooled links and
   clear the ownership readiness blocker. Then do one of:
   - **(a) Owner accepts.** Update D-081 (decision log), `OWNERSHIP_UBO_PROFILE.md`,
     demo §8, `PROJECT_STATE.md` and the implementer report so they state this truthfully,
     instead of "Readiness and GoldTier stay blocked". Add a pinned test of the Garden
     live-shape `CURRENT_EVIDENCE` outcome.
   - **(b) Owner restricts.** Implement the owner-authorized restriction with tests.
     Manual authority and readiness are on the strict preservation list, so this needs
     explicit authorization.

Recommended in the same remediation (non-blocking, low risk):
- F2: require `PROVIDER_PARTIAL` for the POC reason in the record validator or the
  helper.
- F3: document the rounding-sum behavior, and replace the tautological assertion.
- F4: add direct refusal tests.
- F5: adjust the wording.

The context benchmark has about 0.03 percentage points of headroom. Keep any doc
additions to canonical files minimal.

## 8. Readiness

- Stage 4 publication: **NOT READY** (FAIL). Publication of this candidate stays on hold.
  The earlier D-080 PASS does not approve this content.
- Re-QG scope: the remediation delta, plus the evidence it invalidates. A docs-plus-test
  fix needs focused tests and the doc checkers. A code change in domain or manual paths
  needs the focused suites, full backend and physical Mongo per the change-class rows.
  Unchanged evidence can be reused.
- Live ACRA verification and real GoldTier integration: not established and not claimed.
  This is Mock plus a local POC assumption only.
- This verdict authorizes nothing further: no next phase, commit, push or PR.

## 9. Git Status

- Branch `feat/sim-lim-acra-ownership-followthrough-20261024`. HEAD = BASE = `origin/main`
  `ceefe1e`.
- 39 tracked modifications, unstaged; the real index has no staged paths.
- Untracked: six prior `.ai-pipeline/reports/*.md`, plus this report.
- Product tree `1fa01fbc2d233f8f0dcc70a78fac1a1c0a64ae05` was unchanged at gate start and
  gate end.
- The only repository write is this report. Probes, logs and temporary indexes are under
  the session scratchpad `qg81` folder.
- No implementation fix, stash, commit, push, PR, merge or next phase occurred.
