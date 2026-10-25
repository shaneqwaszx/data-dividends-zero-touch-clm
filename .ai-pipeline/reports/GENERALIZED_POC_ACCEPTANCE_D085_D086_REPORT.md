# Generalized POC acceptance (D-085) and dual multi-layer demonstrations (D-086) — handoff

Owner assignments, 2026-10-25: generalized acceptance; scope adjustment for dual
demonstrations; latest-main integration; entity effective ownership display; owner-approved
fold-in of the `:1248` E2E race fix; Stage 4 publication.

**Status:** combined candidate `205b2d4` passed a fresh independent QG. Stage 4
publication is authorized; the outcome is in §10.

## 1. Identity

| Item | Value |
|---|---|
| Latest `origin/main` (integrated) | `5de7f24c2dbf678bbb9de02ad627be777bc2f28c` (PR #110 on PR #108 `80301fd` on our base `7cd2bd9`) |
| Integration worktree / branch | `C:\Users\shane\Desktop\claude-worktrees\generalized-poc-acceptance-int-20261025`, `feat/generalized-poc-acceptance-multilayer-20261025-int`; HEAD = `5de7f24`; nothing staged |
| Ownership candidate tree | `1b4b382ea294cf828d323818c8924bb78e0dd7bb`: 48 paths, temporary-index `write-tree` |
| **Final combined tree** | **`205b2d4ec1791237655db24fb471e1ecb99506d1`**: 49 paths = `1b4b382` + the reviewed `:1248` race fix (raw blob `72caa412e44a…`); reports excluded |
| Pre-integration backup (untouched) | `...\generalized-poc-acceptance-20261025`, branch `feat/generalized-poc-acceptance-multilayer-20261025`, HEAD `7cd2bd9`, candidate tree `07f6176753fd4d386c7645a539395658fe5ce9a7`. Also kept as a git tree object and a binary patch in the session scratchpad |

## 2. How the work was preserved and integrated

The owner selected this plan. It used no commit, stash, reset or rebase.

1. **Recorded state and fetched.** The new main descends from the base. Only
   `docs/decisions/DECISION_LOG.md` and `docs/ARCHITECTURE.md` overlap our delta.
2. **Backed up the candidate.** Kept as a tree object, a binary patch, and copies of the
   untracked files.
3. **Created a new integration worktree and branch** at `5de7f24`.
4. **Byte-copied the 44 non-overlapping paths.**
5. **Ran a 3-way `git merge-file` on the 2 overlapping files.**
   - ARCHITECTURE: clean. Main's D-083 text is retained.
   - DECISION_LOG: one append/append conflict. Main's D-083/D-084 entries are kept
     verbatim; ours are appended after them, so the file is additions-only versus main.
6. **Checked that PR #108/#110 are retained.**
   - 0 of 48 paths are assistant, ADR-012, knowledge-review or single-reviewer code.
   - The DECISION_LOG diff versus main has 0 deleted lines.

## 3. Decision renumbering (old → new)

| Draft | Final | Content |
|---|---|---|
| D-084 | **D-085** | Reusable scenario-declared POC ownership acceptance |
| D-085 | **D-086** | Dual demonstrations: simulation status, OPQ → Garden → SIM LIM, entity interests |
| `D084_SCENARIO_DECLARED_POC_BASIS_V1` | `D085_SCENARIO_DECLARED_POC_BASIS_V1` | Policy literal |

- The policy literal was never released, so no stored record carries the old one.
- The D-082 literal is still readable.
- The D-085 entry has a numbering note.
- Historical QG reports in the scratchpad keep the old numbers.
- Main's assistant D-083/D-084 are untouched.

## 4. Behavior delivered

**D-085: generalized POC acceptance.**
- Officer-role HMAC allowlist settings are removed.
- A trusted catalogue scenario declares its assumptions, and eligibility evaluates the
  actual review causes.
- Default-off opt-in; Marketplace Mock hybrid lane only.
- Case/version/content/identity/document binding. Target confirmation and D-081 Option B
  are unchanged.
- Case envelope 15.

**Scenario A: five-layer simulation (unchanged fixture).**
- Results: BEATRICE 30, DIANA 25, ALEX 20, EDWARD 15, CHARLES 10.
- The UI shows the neutral **Multi-layer ownership simulation calculated** banner. Its
  source is the backend's presentation-only `simulation_calculated`, which is false
  whenever any genuine or masked defect remains.
- REVIEW_REQUIRED and the readiness block are unchanged and explained separately.
- No POC acceptance.

**Scenario B: OPQ → GARDEN BUSINESS → SIM LIM.**
- Selected only by the operator setting `ACRA_MARKETPLACE_OPQ_SCENARIO=garden_sim_lim_chain`;
  the default stays the five-layer simulation.
- Identities:
  - OPQ: official root.
  - Garden: official BUSINESS_PARTNERSHIP, shown as "Business partnership".
  - SIM LIM: official shareholder rows, operation-scoped name.
- OPQ → Garden is an **owner-declared 100%**: `LOCAL_SYNTHETIC_RELATIONSHIP`, no units,
  browser flag `owner_declared_percentage`, labelled "owner-declared percentage".
- Results (unchanged engine): ABCD123 51.13636375, LIM CHOON HUAT 37.5, TAN WEI LING and
  EFGH2345 5.681818125.
- **Fail closed (owner decision on QG P1-1).** Garden's 4 official Owner roles are retained
  beside the graph on its discovery record (role and status only). They block POC
  readiness: Scenario B calculates, stays REVIEW_REQUIRED, is blocked at OWNERSHIP and
  sends nothing.

**Entity effective ownership (owner request).**
- Intermediate entities show engine path values instead of "Not calculated":
  - Five-layer: L2 80, L3 50, L4A 30, L4B 20, L5 40 (30 + 10 across the diamond).
  - Scenario B: Garden 100, SIM LIM 62.5.
- The engine records entity paths only on an opt-in flag, so analysis runs main's exact
  code path.
- Withheld on a path/depth limit, a cycle or a total above 100.
- Presentation only.

**Garden scenario.** Unchanged and still D-085 accepted.

## 5. Changed-file inventory relative to `5de7f24` (48 paths)

- **Backend product:**
  - `app/api_models.py`, `app/composition.py`, `app/config.py`, `app/main.py`
  - `app/connectors/hybrid_ownership_overlay.py`
  - `app/domain/ownership.py`
  - `app/persistence/models.py`, `app/persistence/mongo_case_store.py`
  - `app/services/ownership_analysis.py`, `app/services/ownership_discovery.py`,
    `app/services/zero_touch_orchestration.py`
- **Backend tests:**
  - New: `test_opq_garden_sim_lim_scenario.py`, `test_simulation_calculation_status.py`.
  - Updated: `test_poc_ownership_acceptance.py`, `test_recursive_ownership_real_mongo.py`,
    `test_ownership_api.py`.
  - Current-envelope 14→15 expectation bumps in 18 files.
- **Frontend:**
  - `src/types.ts`
  - `src/pages/OwnershipStructure.tsx` (+ test), `OwnershipPathExplorer.tsx`,
    `UboSummary.tsx`, `ownershipAssumedBasisFixture.ts`
  - `e2e/five-layer-hybrid.e2e.ts`
- **Docs and config:**
  - `DECISION_LOG.md` (D-085, D-086), `ARCHITECTURE.md`, `PROJECT_STATE.md`
  - `OWNERSHIP_UBO_PROFILE.md`, `FIVE_LAYER_ACRA_HYBRID_DEMO.md`
  - `.env.example`
  - `.ai-pipeline/reports/ACRA_MULTI_LAYER_ENTITY_DISCOVERY_REPORT.md`

**Change statement:**
- **API/type:** new response fields `simulation_calculated`, `entity_effective_interests`,
  `provenance.owner_declared_percentage` and `poc_acceptance.accepted_assumptions`.
- **Schema:** envelope 15, plus the optional `official_officer_roles` field.
- **Connector:** none. One owner-authorized OPQ read was made for research.
- **Configuration:** two settings removed, one added.
- **Business rule:** POC eligibility (D-085) and fail-closed intermediate roles (D-086).
- **Mapping:** none.
- **Auth/security:** none.
- **Architecture:** none. There is still a single engine; entity paths are an opt-in
  additive output.
- **Provider status:** unchanged (Mock).

## 6. Evidence

| Lane | Pre-integration (historical) | Post-integration, final product code |
|---|---|---|
| ruff, mypy | clean | clean |
| Full backend + physical Mongo (disposable `mongo:7`) | 3278/0 fail (tree `07f6176`) | **3290 tests, 0 failures, 6 skipped** (product code identical to `1b4b382`; the later test-only delta reran 26/26) |
| Frontend vitest / tsc / build | 1074 / clean / OK | **1081 / clean / OK** |
| `check_project_state` / `check_architecture` / `check_secrets` | PASS | **PASS** |
| Browser E2E (115 selectors) | 6 failures under heavy concurrent load (superseded) | `1b4b382`: 114/115 (§7). **Combined `205b2d4`: 115/115 PASS, plus selector `:1248` PASS** (§10) |
| Visual smoke: offline allowlisted protocol transport, Mock GoldTier, nothing sent | — | **A: all PASS. B + Garden: all PASS** (see §8) |
| Live Marketplace Mock calls (owner-authorized) | research 1 token + 18 GETs; D-084 Garden smoke 1 token + ~4 GETs | OPQ single read 1 token + 1 GET |

**Independent QG history.** No earlier verdict was reused for a changed tree.

| Tree | Verdict | Resolution |
|---|---|---|
| `07f6176` (pre-integration) | FAIL | P1-1 → fail closed; P1-2 → integration and renumbering |
| `731beec` | FAIL | P1-A contract test → fixed |
| `ca8e03d` | PASS_WITH_NOTES | — |
| `b32a156` (entity interests) | PASS_WITH_NOTES | P2-A opt-in engine output; P2-B over-100/cycle withholding → fixed |
| `2dba784` | PASS_WITH_NOTES | Test-oracle P2 → fixed |
| `1b4b382` (ownership final) | PASS | Mutation-proven tests |
| `:1248` addendum (`1b4b382` vs `5de7f24`) | BLOCKED | Pre-existing test race; no waiver → owner chose a fix |
| `1e54662` (race fix only) | PASS | 28/28 isolated runs |
| **`205b2d4` (combined)** | **PASS** | P3-1: refresh this report (done); P3-2: informational |

## 7. Browser E2E (post-integration)

Quiet-machine `run_e2e.py --keep-going` on the final worktree (tree `1b4b382`): **114/115
passed**. The only failure is `authenticated-zero-touch.e2e.ts:1248`, with the
pre-existing `Network.getResponseBody: No resource with given identifier` race in the
documents fetch. This was superseded by the fix and the combined 115/115 run (§10). Earlier in this session the same selector also failed 5 of 7 runs on the
untouched **old** main `7cd2bd9`, interleaved with the pre-integration candidate, which
passed 1 of 9. That historical baseline predates PR #108/#110 and is not evidence for the
`5de7f24`/`1b4b382` pair. The independent addendum for that exact pair is in §7a. The five-layer spec passes with
the new simulation banner. A single run with all 115 green was not achieved on `1b4b382` itself.

## 7a. Independent E2E addendum for `:1248` (verdict: **BLOCKED**)

A fresh read-only reviewer ran the single selector in isolation, interleaved, on the
unchanged candidate tree `1b4b382` and on untouched main `5de7f24` (32 runs, one at a time,
task-owned Mongo).

| Revision | Passed |
|---|---|
| Candidate `1b4b382` | 6 / 16 |
| Main `5de7f24` | 5 / 16 |

- **Same error in all 21 failures** (line 1273): `Network.getResponseBody: No resource
  with given identifier`.
- **Not caused by the candidate** (Fisher p ≈ 1.0). The race is in the test:
  `waitForResponse` on the documents GET is armed before `page.goto`, so it often matches
  the outgoing page's fetch, whose body is discarded on navigation. The D-085/D-086 delta
  does not touch that path.
- **Why BLOCKED:** `DEVELOPMENT_WORKFLOW.md` requires the full browser suite, says a
  failure cannot pass it, and gives the gate no waiver. Risk exceptions belong to the owner.
- **Addendum:** session scratchpad `qg-e2e-1248/QG_E2E_1248_ADDENDUM.md`.

Publication was paused, and the owner then chose a bounded test fix (§10).

## 8. Visual smoke (sanitized; offline protocol transport)

- **Scenario A:** neutral simulation banner; five layers with `LOCAL_SYNTHETIC_RELATIONSHIP`
  sources; entity values 80/50/30/20/30+10; L5 detail "40% (calculated interest; not a UBO
  classification)"; readiness blocked at OWNERSHIP.
- **Scenario B:**
  - The scenario id is recorded. Garden appears as "Business partnership" with source
    "LOCAL_SYNTHETIC_RELATIONSHIP · LOCAL · owner-declared percentage".
  - Garden 100%, SIM LIM 62.5%, ABCD123 51.14%.
  - The 4 Owner roles are retained; not POC-accepted; blocked at OWNERSHIP; no target
    confirmation; nothing sent.
- **Garden:** D-085 accepted, unchanged values, root shown as "Business partnership".
- Mobile 390px shows no overflow.
- Screenshots are in the session scratchpad (`smoke_d085/screenshots_A`, `screenshots_B`)
  and are not tracked. GoldTier Sandbox was never called.

## 9. Unresolved decisions and risks

1. **Owner question (D-086):** extend `DESCRIPTIVE_OFFICER_ROLES` to a declared
   intermediate issuer's official ownership-like roles? Until then, Scenario B stays in
   review.
2. **OPQ legal form reads `OTHER`.** The decoder ignores `companyType`; it was left
   unchanged as instructed.
3. **Ownership-like role vocabulary is an exact-match set** (QG P3-C, the same as for
   roots). A missing officer record means no roles (P3-D).
4. **E2E `:1248` race:** fixed by the folded three-line correction (§10). Untouched main
   keeps the race until this PR merges.
5. **Hosted CI** may be billing-blocked. Any manual-CI exception is the owner's decision.

## 10. E2E stability correction and combined candidate

1. **The fix.** Worktree `e2e-documents-race-20261025`, branch
   `fix/e2e-documents-response-race-20261025`, tree `1e54662`. Both are preserved for
   audit.
   - Change: two comments and `await page.goto("about:blank");` before the documents wait
     in `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`.
   - No assertion, delay, retry, timeout or selector changed.
   - The `case-portfolio` reload pattern near `:1212` was audited and left unchanged.
2. **Fix evidence (on main).**
   - Isolated runs: 20/20 by the implementer and 8/8 by the reviewer, against 5/16 on
     untouched main.
   - Full suite: 115/115.
   - Independent fix QG: **PASS**.
3. **Fold-in (owner decision, Option 1).**
   - The file was byte-copied into this worktree.
   - Its patch against `5de7f24` is identical to the reviewed patch.
   - Combined tree: `205b2d4`.
   - `git diff 1b4b382 205b2d4` shows only that file (+3).
4. **Combined evidence (first attempt; no failed attempts).**
   - Selector `:1248`: PASS.
   - Full `run_e2e.py`: **115/115 PASS** in 1569 s.
   - `check_project_state`, `check_architecture` and `check_secrets`: PASS.
   - Backend 3290/0 and frontend 1081/tsc/build are reused validly; the E2E file is outside
     their coverage.
5. **Fresh independent combined QG: PASS** (no P0–P2).
   - The patch is exact and nothing was weakened.
   - The 48 ownership blobs are unchanged.
   - There are no assistant changes, and main is retained.
6. **Reports committed separately** under `.ai-pipeline/reports/`:
   - this handoff;
   - `GENERALIZED_POC_D085_D086_RE_QUALITY_GATE_2.md`;
   - `E2E_DOCUMENTS_RACE_1248_QG_ADDENDUM.md`;
   - `E2E_DOCUMENTS_RACE_FIX_QUALITY_GATE.md`;
   - `GENERALIZED_POC_D085_D086_COMBINED_QUALITY_GATE.md`.

   The scratchpad originals are preserved.
