# Independent Quality Gate: combined D-085/D-086 candidate plus `:1248` race fix

**Verdict: PASS**

There are no P0, P1 or P2 findings. Two P3 notes follow in section 5; neither changes the reviewed tree.

This review was fresh, independent and read-only. I did not implement, remediate or review any earlier part of this candidate. I changed no checkout file, real index, ref or worktree. I did not open `.env`. I made no external provider or GoldTier call. My only writes were scratch files in this folder (`qg-combined\`).

## 1. Identity

| Item | Value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\generalized-poc-acceptance-int-20261025` |
| Branch | `feat/generalized-poc-acceptance-multilayer-20261025-int` |
| HEAD | `5de7f24c2dbf678bbb9de02ad627be777bc2f28c` |
| origin/main | `5de7f24c2dbf678bbb9de02ad627be777bc2f28c`. I ran `git fetch origin` at the start and again at the end; main had not moved. |
| Reviewed tree | **`205b2d4ec1791237655db24fb471e1ecb99506d1`**, which matches the claim. Method: I copied `git rev-parse --git-path index` to `qg-combined\index.copy`, ran `GIT_INDEX_FILE=<copy> git add --pathspec-from-file=candidate_paths_comb.txt` (49 paths), then `git write-tree`. I repeated this at the end (`index.copy2`) and got the same tree, so the content did not change during the gate. |
| Real index | 0 staged paths, before and after. |
| `git status --short` | 53 entries, before and after. These are the 49 tree paths plus 4 untracked report-only files: `GENERALIZED_POC_ACCEPTANCE_D085_D086_REPORT.md`, `GENERALIZED_POC_D085_D086_RE_QUALITY_GATE_2.md`, `E2E_DOCUMENTS_RACE_1248_QG_ADDENDUM.md` and `E2E_DOCUMENTS_RACE_FIX_QUALITY_GATE.md`. `comm` against the path list leaves exactly those 4 and no others. `.ai-pipeline/reports/ACRA_MULTI_LAYER_ENTITY_DISCOVERY_REPORT.md` is one of the 49. |
| Path lists | `candidate_paths_comb.txt` = `candidate_paths_int5.txt` (the 48 paths of `1b4b382`) + `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`. Nothing else differs. |

## 2. Confirmation points

### 2.1 The race fix equals the reviewed patch: CONFIRMED

- **Raw bytes:** `cmp` of the candidate file against `e2e-documents-race-20261025/apps/frontend/e2e/authenticated-zero-touch.e2e.ts` reports them identical.
- **`git hash-object --no-filters`:** `72caa412e44ab750e86867531487aeab35e824e1` in both worktrees.
- **Tree entries:** `git ls-tree` gives `72caa41` in both `205b2d4` and the reviewed race-fix tree `1e54662`. The file is `0f1f024` in both `5de7f24` and `1b4b382`.
- **Fix worktree:** HEAD is `5de7f24`, branch `fix/e2e-documents-response-race-20261025`, and only this file is modified.
- **`git diff 5de7f24 -- <file>`:** exactly 3 insertions in both worktrees, in hunk `@@ -1263,6 +1263,9 @@`. `cat -A` shows `^M$` (CRLF) on each of the three added lines, matching the surrounding CRLF context:
  - two comment lines;
  - `await page.goto("about:blank");`, placed immediately before the `documentsResponse = page.waitForResponse(...)` registration.
- **The fix is correct.** It makes the later `page.goto('/cases/<id>')` the only source of the awaited `/documents` GET. The stale in-flight fetch from the earlier page can no longer satisfy the wait and lose its body. All later assertions are unchanged.
- **Prior review:** `E2E_DOCUMENTS_RACE_FIX_QUALITY_GATE.md` reviewed blob `ed09aac…` (autocrlf `hash-object`), which corresponds to index blob `72caa41`. That matches the blob in this tree.

### 2.2 No E2E assertion removed or weakened; no retry, timeout or delay inflation: CONFIRMED

- **Scope of the E2E delta:** `git diff --stat 5de7f24 205b2d4 -- apps/frontend/playwright.config.ts scripts/run_e2e.py apps/frontend/e2e/` lists only two files:
  - `authenticated-zero-touch.e2e.ts`: +3/−0;
  - `five-layer-hybrid.e2e.ts`: +7/−1.
- **Unchanged:** `playwright.config.ts` and `run_e2e.py`.
- **No weakening tokens:** a scan of the `-U0` delta finds no `retries`, `timeout`, `waitForTimeout`, `setTimeout`, `test.skip`, `fixme`, `fail` or `slow` changes.
- **`authenticated-zero-touch`:** the change is additive only, as described in 2.1.
- **`five-layer-hybrid:78`, the one removed line:** it was the `toBeVisible()` expectation for "Partial or disputed ownership evidence — review required." Six lines replace it:
  - `ownership.simulation_calculated === true` and `ownership.poc_basis_accepted === false` (API);
  - the banner title "Multi-layer ownership simulation calculated" is visible;
  - the owner-copy paragraph regex is visible;
  - the old generic warning has `toHaveCount(0)`.
- **The replacement is faithful, and stronger.** In `OwnershipStructure.tsx:133-156` the banners are a single ternary chain (`poc_basis_accepted` → `calculatedForVerification` → `simulation_calculated` → generic warning). The old and new banners are therefore mutually exclusive, and D-086 specifies that the five-layer case now shows the simulation banner.
- **No review-state assertion was removed.** The test still asserts all of these:
  - API `state === "REVIEW_REQUIRED"`;
  - `goldtier_result` is null;
  - "Provisional UBOs" = 0;
  - the assumed-basis region labelled "…review required";
  - the selected holder shows `REVIEW_REQUIRED` and `→ INDETERMINATE`;
  - no "Confirm and send to Mock GoldTier" button (count 0).
- **Inherited from `1b4b382`:** the five-layer change was already part of that tree, which re-QG2 passed.

### 2.3 D-085/D-086 ownership functionality unchanged outside its approved scope: CONFIRMED

- `git diff --stat 1b4b382 205b2d4` shows exactly one file: `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`, +3.
- So the 48 ownership paths have the same blob ids as the reviewed `1b4b382`, which means identical index content.
- The worktree bytes are what the tree was written from, and the tree was unchanged at the end.

### 2.4 No unrelated AI Assistant changes: CONFIRMED

- **Path scan:** a `grep -i 'assistant|adr|knowledge|review'` over the 49 paths matches only `apps/backend/tests/test_classification_conflict_review.py`. That is an ownership classification test with a +1/−1 envelope-version bump, not assistant code.
- **DECISION_LOG:** `git diff --numstat 5de7f24 205b2d4 -- docs/decisions/DECISION_LOG.md` gives `169 0`, so 0 lines were deleted. The single hunk `@@ -781,3 +781,172 @@` only appends.
- **D-083/D-084 intact:** main's D-083 and D-084 sections (lines 711-783) have the same md5 in main and in the candidate (`46c3cba3…`). Headings D-080 to D-084 are at the same line numbers.
- **New decisions:** D-085 (line 785) and D-086 (line 855) are new. The ADR-012 mention count is the same as main's (10).

### 2.5 Latest main incorporated correctly: CONFIRMED

- **Base:** HEAD = origin/main = `5de7f24`, and the candidate is an uncommitted delta on top of it. `git log` shows `5de7f24` (#110) → `80301fd` (#108) → `7cd2bd9` (#109).
- **Overlap with PR #108 and #110:** PR #108 touched 28 files and PR #110 touched 6. Only two of those are in the candidate: `docs/ARCHITECTURE.md` (#108) and `docs/decisions/DECISION_LOG.md` (both).
  - `ARCHITECTURE.md`: +5/−1. The one removed line is the old D-082 ownership sentence, reflowed with D-085/D-086 text appended. PR #108's single-reviewer and assistant paragraph is still present (1 match).
  - `DECISION_LOG.md`: 0 deletions, as shown in 2.4.
- **No reverts:** no other PR #108/#110 file is in the candidate, so nothing from those PRs can be reverted.

### 2.6 Reports preserved: CONFIRMED

| Repo copy (`.ai-pipeline/reports/`) | Scratchpad original | `cmp` |
|---|---|---|
| `GENERALIZED_POC_D085_D086_RE_QUALITY_GATE_2.md` | `reqg2-entity\REQG2_ENTITY_REPORT.md` (4492 B) | identical (sha256 prefix `7a3306b3e6182665`) |
| `E2E_DOCUMENTS_RACE_1248_QG_ADDENDUM.md` | `qg-e2e-1248\QG_E2E_1248_ADDENDUM.md` (16198 B) | identical (`3be80650785c5cc7`) |
| `E2E_DOCUMENTS_RACE_FIX_QUALITY_GATE.md` | `qg-race-fix\QG_RACE_FIX_REPORT.md` (15760 B) | identical (`a1acf97fb0bff5d0`) |

The earlier gate chain for the ownership candidate also exists in the scratchpad. Each report has a matching recomputed tree:

| Report | Tree |
|---|---|
| `qg-int\QG_INT_REPORT.md` | `731beec` |
| `reqg-int\REQG_INT_REPORT.md` | `ca8e03d` |
| `qg-entity\QG_ENTITY_REPORT.md` | `b32a156` |
| `reqg-entity\REQG_ENTITY_REPORT.md` | `2dba784` |
| `reqg2-entity\REQG2_ENTITY_REPORT.md` | `1b4b382`, PASS |

### 2.7 Changed-file inventory: accurate (see section 3)

- `git diff --name-status 5de7f24 205b2d4` lists 49 files: 3 added and 46 modified, +2934/−545.
- `--ignore-cr-at-eol` gives the same stat, so there is no EOL churn.
- All 49 are INTENDED or SUPPORTING. None is UNEXPECTED.

### 2.8 Integration evidence: verified from the logs, and partly reproduced

**Selector `:1248`, from the implementer's logs (`comb-e2e\sel.log` and `sel_results.json`)**
- `discovered=115; selected=1`, `1 passed (3.6s)`, `E2E SUITE PASS: 1 configured selectors…`.
- JSON: `status PASS`, `complete true`, `counts {PASS:1}`, `exit_code 0`, started `2026-10-25T09:27:47Z`.

**Full suite, from the implementer's logs (`comb-e2e\full.log` and `full_results.json`)**
- The log ends with `E2E SUITE PASS: 115 configured selectors passed in isolated lifecycles.`
- JSON: `status PASS`, `complete true`, `mode full`, `discovered_count 115`, `selected_count 115`, `counts {PASS:115}`. There are 115 lifecycles with unique selectors, all `result PASS` and `exit_code 0`. It started `2026-10-25T09:27:57Z` and took 1569.3 s.

**Content binding of those runs**
- **Line shift.** The JSON lists `authenticated-zero-touch.e2e.ts` selectors 230, 242, 658, 700, 791, 864, 956, 1044, 1248, **1297, 1445, 1573, 1685**.
  - The top-level `test(` lines in candidate blob `72caa41` match exactly.
  - Main's blob has 1294, 1442, 1570, 1682 for the last four.
  - So the full run executed the combined file.
- **Timing.** The newest mtime among the 49 paths is the E2E file at 16:42:28 local (08:42:28Z). That is before both runs started (09:27Z). The three report copies were written at 17:28:16 local, but they are outside the tree.
- **No content identity in the JSON.** Its `identity.tree` (`56c6a705…`) is `HEAD^{tree}` with `dirty: true` (`run_e2e.py:851`), not the candidate content. See P3-2.

**My own reproduction, bound by blob hash**
- The E2E blob hashes `72caa41` and `33b3d58` were recorded before my runs and re-checked unchanged after them.
- I used task-owned Mongo `gpoc-comb-e2e-mongo` on `127.0.0.1:27133` (already running; I left it running) and ran one lifecycle run at a time with `--timeout-seconds 60`.
  - `qg_run1`: `:1248`, `:1297` and `five-layer-hybrid:78`. **3/3 PASS.**
  - `qg_run2` to `qg_run6`: `:1248` alone, five times in a row. **5/5 PASS.**
- Combined with the implementer's runs, `:1248` has 7/7 passes on this tree. The addendum's baseline failure rate before the fix was 5/16 on main and 6/16 on `1b4b382`.

**Checkers, rerun by me on the combined worktree with the repo venv**
| Checker | Result | Exit |
|---|---|---|
| `check_project_state` | `PROJECT STATE CHECK: PASS` | 0 |
| `check_architecture` | `ARCHITECTURE CHECK: PASS` | 0 |
| `check_secrets` | `Secret scan passed` | 0 |

**Focused backend run, by me (memory mode, `PHASE12_MONGO_URI` unset, `-p no:cacheprovider`, no bytecode)**
- Files: `test_opq_garden_sim_lim_scenario.py`, `test_simulation_calculation_status.py` and `test_poc_ownership_acceptance.py`.
- Result: **110 tests, 0 failures, 0 errors, 0 skipped** (`qg-combined\focused.xml`).

**Is reusing the earlier evidence valid?** I judge that it is, under `DEVELOPMENT_WORKFLOW.md` "Evidence reuse and invalidation". That rule says a change invalidates only the evidence it can reach. The only path not in `1b4b382` is an `.e2e.ts` file, and nothing else can reach it:
- **tsc:** `tsconfig.app.json` includes `src` only, and `tsconfig.node.json` includes `vite.config.ts` only.
- **vite build:** it bundles from `src`.
- **vitest:** `vite.config.ts` `test: {environment: "node"}` has no include override. The default `*.{test,spec}.*` pattern does not match `*.e2e.ts`.
- **pytest:** the only Python reference to this file is `test_slice_c_blocker_catalogue.py:181`, a path-string and existence check that its content cannot affect. No tracked config or doc cites the shifted line numbers; `git grep` finds none.

The affected Playwright lane was rerun in full on the combined content (115/115). So the reused backend evidence (3290 tests, 0 failures, with physical Mongo) and frontend evidence (vitest 1081, tsc, build), both bound to `1b4b382`'s product code, still apply to `205b2d4`.

### 2.9 Whitespace: CLEAN

- `git diff --check` (worktree) and `git diff --check 5de7f24 205b2d4` (tree) both exit 0.
- The only output is autocrlf "LF will be replaced by CRLF" notices, which are not whitespace errors.
- All 7 untracked files have 0 lines with trailing whitespace (`grep -P '[ \t]+\r?$'`) and 0 CRLF lines: the 5 report Markdown files, `test_opq_garden_sim_lim_scenario.py` and `test_simulation_calculation_status.py`.

### 2.10 Governance: CONFORMANT

I read `AGENTS.md`, `docs/DEVELOPMENT_WORKFLOW.md` (stages and evidence reuse) and `.agents/skills/fyp-quality-gate/SKILL.md`, and applied them as follows:
- **Independence:** this is a fresh reviewer, the review was read-only, and only scratch files were written.
- **Frozen identity:** the tree was recomputed at the start and at the end.
- **Authority labels:** D-085 and D-086 are both labelled `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`. Each explicitly disclaims verified ownership, a legal UBO determination (Q-004), Marketplace semantics (Q-012), person identity (Q-019) and Live evidence. Neither is presented as sponsor-approved. PROJECT_STATE records them as candidates.

**Scenario B fails closed; checked in code**
- `ownership_analysis.py:404` `_intermediate_ownership_like_roles` returns true when any retained `official_officer_roles` entry on a discovery record has a role in `{OWNER, PARTNER, MEMBER, SHAREHOLDER}`.
- It blocks eligibility in `eligible_poc_acceptance` (`:492`).
- It also forces `simulation_calculated` to false (`:652`).

**Scenario B fails closed; checked in tests (`test_opq_garden_sim_lim_scenario.py`)**
- **`:359`, the observed Garden Owner roles:** `REVIEW_REQUIRED`, `poc_acceptance is None` and `poc_basis_accepted` false.
- **`:402`, parametrised by role:** SHAREHOLDER and PARTNER block; DIRECTOR does not.
- **`:449`, end to end:** `OWNERSHIP_REVIEW_REQUIRED` is in the readiness blockers, the case stays `WAITING_FOR_REVIEW` at `OWNERSHIP`, and there is no target-confirmation exception. Also `goldtier_result` is None, `submission` is None and target executions are `()`, so nothing is sent to GoldTier.
- **`:491`, the counterfactual eligible chain:** it still needs explicit confirmation before a Mock send, and the snapshot carries status `REVIEW_REQUIRED` with 0 provisional UBOs.
- I ran these myself and they pass (part of the 110 above).

**Other hygiene**
- **`.env.example`:** removes the D-082 officer-role key and allowlist placeholders and adds the `ACRA_MARKETPLACE_OPQ_SCENARIO` selector with its default. It contains no secret values.
- **Discovery report:** no credentials, URLs or tokens.

**UI and shared types.** The Ownership & UBO UI (`OwnershipStructure.tsx`, `OwnershipPathExplorer.tsx`, `UboSummary.tsx`) and `types.ts` change in this candidate. D-086 records them as owner-directed, owner's copy included, and they were part of `1b4b382`, which the earlier gate chain reviewed. They are not new in this combined delta.

## 3. Inventory (49 paths, `git diff --name-status 5de7f24 205b2d4`)

| St | +/− | Path | Class |
|---|---|---|---|
| A | +285/−0 | `.ai-pipeline/reports/ACRA_MULTI_LAYER_ENTITY_DISCOVERY_REPORT.md` | SUPPORTING (D-085 Workstream B probe evidence, sanitized) |
| M | +9/−10 | `.env.example` | SUPPORTING (D-085 key removal, D-086 selector) |
| M | +64/−4 | `apps/backend/app/api_models.py` | INTENDED |
| M | +12/−14 | `apps/backend/app/composition.py` | INTENDED |
| M | +14/−7 | `apps/backend/app/config.py` | INTENDED |
| M | +171/−20 | `apps/backend/app/connectors/hybrid_ownership_overlay.py` | INTENDED |
| M | +105/−15 | `apps/backend/app/domain/ownership.py` | INTENDED |
| M | +8/−2 | `apps/backend/app/main.py` | INTENDED |
| M | +62/−2 | `apps/backend/app/persistence/models.py` | INTENDED (envelope 15) |
| M | +10/−2 | `apps/backend/app/persistence/mongo_case_store.py` | INTENDED (envelope 15) |
| M | +358/−175 | `apps/backend/app/services/ownership_analysis.py` | INTENDED |
| M | +19/−0 | `apps/backend/app/services/ownership_discovery.py` | INTENDED |
| M | +2/−2 | `apps/backend/app/services/zero_touch_orchestration.py` | INTENDED |
| M | +1/−1 | `apps/backend/tests/test_classification_conflict_real_mongo.py` | SUPPORTING (envelope bump) |
| M | +1/−1 | `apps/backend/tests/test_classification_conflict_review.py` | SUPPORTING (envelope bump) |
| M | +2/−2 | `apps/backend/tests/test_hybrid_five_layer_overlay.py` | SUPPORTING |
| M | +1/−1 | `apps/backend/tests/test_manual_ownership_evidence.py` | SUPPORTING |
| M | +4/−4 | `apps/backend/tests/test_official_shareholder_evidence.py` | SUPPORTING |
| A | +547/−0 | `apps/backend/tests/test_opq_garden_sim_lim_scenario.py` | INTENDED (Scenario B tests) |
| M | +6/−0 | `apps/backend/tests/test_ownership_api.py` | SUPPORTING |
| M | +3/−3 | `apps/backend/tests/test_ownership_discovery_policy.py` | SUPPORTING |
| M | +6/−6 | `apps/backend/tests/test_phase12_persistence.py` | SUPPORTING (envelope bump) |
| M | +1/−1 | `apps/backend/tests/test_phase12_real_mongo.py` | SUPPORTING (envelope bump) |
| M | +4/−4 | `apps/backend/tests/test_phase13_priority.py` | SUPPORTING (envelope bump) |
| M | +3/−3 | `apps/backend/tests/test_phase13_real_mongo.py` | SUPPORTING (envelope bump) |
| M | +1/−1 | `apps/backend/tests/test_phase14_5_real_mongo.py` | SUPPORTING (envelope bump) |
| M | +1/−1 | `apps/backend/tests/test_phase24c_real_mongo.py` | SUPPORTING (envelope bump) |
| M | +321/−212 | `apps/backend/tests/test_poc_ownership_acceptance.py` | INTENDED (D-085 eligibility) |
| M | +11/−9 | `apps/backend/tests/test_recursive_ownership_real_mongo.py` | SUPPORTING |
| M | +2/−2 | `apps/backend/tests/test_s2_intelligence_real_mongo.py` | SUPPORTING (envelope bump) |
| M | +2/−2 | `apps/backend/tests/test_s2_persistence_security.py` | SUPPORTING (envelope bump) |
| A | +390/−0 | `apps/backend/tests/test_simulation_calculation_status.py` | INTENDED (D-086 simulation flag and entity interests) |
| M | +4/−4 | `apps/backend/tests/test_slice_a_legacy_compatibility.py` | SUPPORTING (envelope bump) |
| M | +1/−1 | `apps/backend/tests/test_slice_c_real_mongo.py` | SUPPORTING (envelope bump) |
| M | +1/−1 | `apps/backend/tests/test_target_classification_continuation.py` | SUPPORTING (envelope bump) |
| M | +1/−1 | `apps/backend/tests/test_zero_touch_orchestration.py` | SUPPORTING (envelope bump) |
| M | +3/−0 | `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` | INTENDED (owner-approved race fix, byte-identical to the reviewed patch) |
| M | +7/−1 | `apps/frontend/e2e/five-layer-hybrid.e2e.ts` | INTENDED (D-086 banner expectation) |
| M | +2/−2 | `apps/frontend/src/pages/OwnershipPathExplorer.tsx` | INTENDED (D-086 owner-directed copy) |
| M | +95/−4 | `apps/frontend/src/pages/OwnershipStructure.test.tsx` | SUPPORTING |
| M | +49/−10 | `apps/frontend/src/pages/OwnershipStructure.tsx` | INTENDED (D-086 banner, entity interests, type label) |
| M | +3/−1 | `apps/frontend/src/pages/UboSummary.tsx` | INTENDED (D-086 copy) |
| M | +35/−0 | `apps/frontend/src/pages/ownershipAssumedBasisFixture.ts` | SUPPORTING (test fixture) |
| M | +26/−1 | `apps/frontend/src/types.ts` | INTENDED (new response fields) |
| M | +5/−1 | `docs/ARCHITECTURE.md` | SUPPORTING (durable docs) |
| M | +13/−1 | `docs/PROJECT_STATE.md` | SUPPORTING (envelope 15, D-085/D-086 rows) |
| M | +51/−0 | `docs/contracts/OWNERSHIP_UBO_PROFILE.md` | SUPPORTING (contract docs) |
| M | +169/−0 | `docs/decisions/DECISION_LOG.md` | SUPPORTING (D-085, D-086; 0 deletions) |
| M | +43/−11 | `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md` | SUPPORTING (demo docs) |

**Totals:** 49 files, +2934/−545. UNEXPECTED: 0.

**Excluded, untracked, report-only (4):** `GENERALIZED_POC_ACCEPTANCE_D085_D086_REPORT.md`, `GENERALIZED_POC_D085_D086_RE_QUALITY_GATE_2.md`, `E2E_DOCUMENTS_RACE_1248_QG_ADDENDUM.md` and `E2E_DOCUMENTS_RACE_FIX_QUALITY_GATE.md`.

## 4. Not executed by this gate

- **Full backend suite and physical-Mongo backend tests.** I reused the earlier `1b4b382` evidence (3290 tests, 0 failures) under the invalidation rule in 2.8. I ran only the 110 focused memory-mode tests.
- **Frontend vitest, tsc and `vite build`.** Reused from `1b4b382`, because the e2e file is not reachable by those tools.
- **Full 115-selector Playwright run.** I verified it from the logs (content bound by the line shift and mtimes) and did not rerun it. My own runs were 3 + 5 selector lifecycles.
- **`pre_pr_check.py`.** That is a publication gate on a committed state; the candidate is intentionally uncommitted.
- **Hosted CI.** Not observed.
- **Live, sponsor or Sandbox evidence.** None. Everything here is Mock or Local.

## 5. Verdict

**PASS** for tree `205b2d4ec1791237655db24fb471e1ecb99506d1` on `origin/main` `5de7f24`.

| ID | Grade | Finding |
|---|---|---|
| P3-1 | P3 (outside the tree, before publication) | The untracked handoff `GENERALIZED_POC_ACCEPTANCE_D085_D086_REPORT.md` (mtime 16:30) is stale for the combined candidate. It names `1b4b382` as the "Final candidate tree", reports Browser E2E as 114/115, and states that "a single run with all 115 green has not been achieved". It does not record `205b2d4`, the folded race fix, the owner decision or the 115/115 combined run. Refresh it, or the PR text, before publication. This is a handoff/report edit, so under the workflow it invalidates no behavioural evidence and needs no re-review of the tree. |
| P3-2 | P3 (informational) | The `run_e2e.py` results JSON records `identity.tree = HEAD^{tree}` with `dirty: true`, so it cannot bind uncommitted content by itself. Here the binding rests on the selector line shift, the mtimes and this gate's blob-checked reruns. No action is required for this candidate. |

**Scope of this verdict.** It covers only the exact 49-path content above. Any change to those paths needs a fresh independent review. Publication still needs explicit owner authorization, `pre_pr_check.py` on the committed state, and the PR checklist. A repository-owner human merges.

**Classifications.** D-085/D-086 remain project-defined POC candidates, not sponsor-approved policy. Scenario B remains REVIEW_REQUIRED, with readiness blocked at OWNERSHIP and no GoldTier submission.
