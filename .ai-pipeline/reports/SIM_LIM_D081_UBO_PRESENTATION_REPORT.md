# D-081 UBO presentation correction — implementer report

Owner authorization 2026-10-24: U1–U4 approved, frontend presentation only. Nothing
committed, pushed or published.

## Identity

| Item | Value |
|---|---|
| Branch / BASE / HEAD / `origin/main` | `feat/sim-lim-acra-ownership-followthrough-20261024` / `ceefe1e` (all three) |
| Previously accepted tree (re-QG PASS) | `ff8f7ab5cbadb6349e3561a48fd030bd76567bfc` |
| New candidate tree | `f79e3192303bbec6759924e35317ecb0e3b312e6`. Temporary index over HEAD plus every tracked modification plus the two new task-owned files; untracked `.ai-pipeline/reports/*` excluded |
| Delta vs `ff8f7ab` | 12 files, +320 / −7. **0 files under `apps/backend`, `scripts` or `tests`** |
| Candidate vs BASE | 48 files, +2149 / −158 |

## What changed (presentation only)

| File | Change |
|---|---|
| `apps/frontend/src/types.ts` | Optional `synthetic_basis_threshold_result?: "MET" \| "NOT_MET" \| "INDETERMINATE" \| null` on `OwnershipCandidate` (already served by the API since D-077) |
| `apps/frontend/src/ownershipDisplay.ts` | `hasAssumedBasisComparison`, `assumedBasisMatches` and `assumedBasisLabel` (see below) |
| `apps/frontend/src/pages/UboSummary.tsx` | Separate section, "Meets the threshold on an assumed basis — review required" (details below). The formal list and its filter are unchanged |
| `apps/frontend/src/pages/OwnershipPathExplorer.tsx` | Stat "Assumed-basis matches", shown only when the API supplies the field. "Provisional UBOs" is unchanged |
| `apps/frontend/src/pages/OwnershipStructure.tsx` | Selected holder: row "Assumed-basis comparison … → MET/NOT_MET (not a classification)" between the formal threshold comparison and the classification, only when the field is present |
| Tests | New `UboSummary.test.tsx` (7) and `ownershipAssumedBasisFixture.ts`; one new Review & Send test; five-layer E2E UI assertions plus its stale comment |
| Docs | Demo guide (table row and §8), ownership profile (one sentence), D-081 presentation bullet |

**Helpers in `ownershipDisplay.ts`.**
- `hasAssumedBasisComparison`: whether any candidate carries the field.
- `assumedBasisMatches`: natural persons with the backend value `MET` and a formal
  REVIEW_REQUIRED/INDETERMINATE classification. There is no JavaScript comparator.
- `assumedBasisLabel`: built from the provenance of the links on the candidate's own
  retained paths, using the existing pattern in `UboSummary`'s "Ownership evidence sources":
  - a POC link gives "POC equal-unit assumption";
  - a local overlay link gives "Local synthetic overlay basis";
  - otherwise "Assumed POC basis".

**The new section in `UboSummary.tsx`.** It shows the owner's explanation text. Each
entry gives the name, the backend aggregate (existing rounding), the basis label, the
assumed-basis comparison and the formal classification. When it has entries and there is no
formal list, the empty text reads "No natural person is formally classified as a
provisional UBO; N meet the threshold only on an assumed basis (below)." Otherwise the text
is byte-identical. Review & Send renders it through the existing shared component.

**Not changed:**
- formal provisional counts and filters (explorer, hierarchy chip, row `is-ubo` highlight,
  `UboSummary` list);
- `viewModels.beneficial_owners` (client detail), `App.tsx`;
- readiness, Review & Send confirmation gating (backend blockers), Option B, GoldTier
  payloads;
- every backend file, the API, the engine, comparator and discovery.

## Owner test list

| # | Requirement | Evidence |
|---|---|---|
| 1 | Garden: 4 assessed, 2 assumed-basis matches, 0 provisional | `UboSummary.test.tsx` "Garden: four assessed…" (stats, chip, no `is-ubo` rows, empty-state variant) |
| 2 | ABCD123 51.14%, LIM CHOON HUAT 37.5% listed | "lists ABCD123 and LIM CHOON HUAT…" (exact heading and explanation, labels, MET, REVIEW_REQUIRED) |
| 3 | TAN WEI LING and EFGH2345 absent | same test |
| 4 | Selected holder separates MET from INDETERMINATE | "shows the assumed-basis comparison…" (ABCD123 MET; TAN WEI LING NOT_MET) |
| 5 | Provisional fixture unchanged | "keeps the existing provisional UBO fixture…" plus the unchanged structure, explorer and Review & Send suites |
| 6 | Field absent gives the previous UI | "keeps the previous behaviour when the optional field is absent" |
| 7 | Review & Send shows the distinction without enabling submission | `ReviewAndSend.test.tsx` "explains assumed-basis matches…": no "Confirm and send", "Review outstanding items" shown |
| 8 | Five-layer: BEATRICE LIM and DIANA KOH | Vitest fixture test, and the real browser E2E `five-layer-hybrid.e2e.ts:78` (stats 0/2, region names, overlay label, DIANA KOH selected-holder row) |
| 9 | Client-detail owners exclude these matches | `UboSummary.test.tsx` "never adds assumed-basis matches to the client-detail owners" |
| 10 | No readiness, Option B or GoldTier change | No backend file changed (delta above); Review & Send gating is untouched and tested in #7; Option B is pinned by the unchanged backend tests |

Garden POC browser coverage: the offline E2E harness's five-layer transport has no SIM LIM
shareholder rows, so it yields the D-079 outcome without POC links. A Garden POC browser
test would need harness or fixture changes, which are outside this frontend-only scope.
Garden POC rendering is therefore covered by Vitest (a fixture shaped like the backend
response) and by the owner visual review on the live Mock.

## Evidence on the working tree with content `f79e319`

| Check | Result |
|---|---|
| Frontend typecheck (`tsc -b`) | PASS |
| Full Vitest | **64 files, 1058 tests passed** |
| Focused Vitest (UboSummary, ReviewAndSend, OwnershipStructure, OwnershipPathExplorer, ownershipDisplay) | 80 passed |
| Vite production build | PASS (chunk-size advisory warning only) |
| Focused browser E2E (`--keep-going`) | 7 selectors: 6 PASS on the first run. `five-layer-hybrid.e2e.ts:78` failed once on **my new assertion's ordering** (the backend lists DIANA KOH before BEATRICE LIM). The assertion was made order-independent and the rerun PASSED |
| Full browser E2E | see below |
| CI unittest lanes (contract 44 incl. the `types.ts` contract check, delivery, secrets, pre-PR, policy, provider readiness, skill pointers, provider evidence, GoldTier examples) | All OK |
| dev-context / project-state / architecture tests | 55 OK; routine benchmark 30.047% (unchanged) |
| Repository checkers | PASS |
| `git diff --check`; EOL churn | Clean; `--stat` = `--ignore-cr-at-eol --stat`. New files: no trailing whitespace or tabs, final newline |
| Backend | Not rerun: 0 backend, script or backend-test files changed since `ff8f7ab`. Its evidence (3004 passed, physical 169/169) still applies |

Focused selectors: five-layer `:78`, ownership-document-streamline `:79` and `:235`,
slice-b Garden partnership `:94`, garden happy path `:218`, S2 creator flow `:55`,
authenticated Garden partial `:956`.

| Check | Result |
|---|---|
| Full browser E2E (`--keep-going`, ports 9300/4600 to avoid the owner smoke server on 8791) | **115/115 PASS**, complete=True, 1506 s. Slowest `e2e/performance-browser.e2e.ts:137` 54.671 s of 60. An earlier attempt stopped before any test because lifecycle 27 was assigned the occupied port 8791 (`e2e_full_port_conflict.*`) |

## Ownership structure presentation cleanup (owner task, tree `97fcc8c`)

The scope audit (`SIM_LIM_D081_SCOPE_AUDIT.md`) was accepted. Final candidate tree:
`97fcc8c94876a5811018787ba4bb579501524c76`.
- The code tree is `84a4bb2f29e3d774e4dece1bdf3c085e23a3023a`; `97fcc8c` adds only a
  6-line demo-guide note on top of it.
- Delta vs `f79e319`: `OwnershipStructure.tsx` (+33/−4), `OwnershipStructure.test.tsx`
  (+87) and `FIVE_LAYER_ACRA_HYBRID_DEMO.md` (+6).
- Delta vs the accepted `ff8f7ab`: 0 files under `apps/backend`, `scripts`, `tests` or
  `apps/assistant`.

**Change (presentation only, `OwnershipStructure.tsx`).** The hierarchy built effective
values only from natural-person candidate paths. Every company, including the client, fell
back to "Not retained".
- `entityLabel()` now gives:
  - root: "Root entity — N/A";
  - a company with exactly one occurrence, held directly by the client: the retained
    relationship percentage, labelled "… — direct holding in client";
  - a company on more than one path: "Not calculated — held through multiple paths";
  - a deeper corporate holder: "Not calculated for indirect corporate holders".
- Persons, cycles and unlinked rows are unchanged.
- The selected-holder panel uses the same labels. The root's direct holding reads
  "Root entity — N/A".
- No company percentage is calculated in the browser. Backend candidates, paths and
  provenance are untouched.

**Banner.** `calculatedForVerification()` shows **Ownership calculated — verification
required**, with the owner's explanation and "Legal UBO determination and ownership
readiness remain subject to review." It applies only when all of these hold:
- the state is REVIEW_REQUIRED;
- `LOCAL_POC_ASSUMED_EQUAL_UNITS` links are present;
- every issue is one of `OWNERSHIP_DENOMINATOR_REQUIRED`, `SYNTHETIC_OWNERSHIP_EVIDENCE` or
  `UBO_REVIEW_REQUIRED`.

Every other non-ANALYZED record keeps "Partial or disputed ownership evidence — review
required." The banner uses the existing `ds-banner ds-banner-warn` / `<strong>` + `<p>`
pattern.

**Before → after (live Garden case `092cb3e8…`, D-081 servers, 0 new provider calls).**

| Row | Before | After |
|---|---|---|
| GARDEN BUSINESS (root) | Effective "Not retained"; holder direct "Not retained", effective "Not calculated by retained analysis" | "Root entity — N/A" (row and holder panel) |
| SIM LIM PTE. LTD. | Direct 62.5%, Effective "Not retained" | Direct 62.5%, Effective "62.5% — direct holding in client" |
| ABCD123 / TAN WEI LING / EFGH2345 / LIM CHOON HUAT | 51.14% / 5.68% / 5.68% / 37.5% | unchanged |
| Banner | "Partial or disputed ownership evidence — review required." | "Ownership calculated — verification required" + explanation + review statement |
| Stats / readiness | 4 assessed, 0 provisional, 2 assumed-basis; `OWNERSHIP_REVIEW_REQUIRED`, GoldTier null | unchanged |

An in-progress capture showed the banner sentences running together inline. They were
switched to `<p>` before freezing.

**Tests** (`OwnershipStructure.test.tsx`, 9 new; all 12 existing tests unchanged and
passing):
- Garden labels, holder panel and banner;
- the general warning kept for `CORPORATE_OWNERSHIP_UNRESOLVED`,
  `CONTRADICTORY_OWNERSHIP_EVIDENCE`, `CYCLE_DETECTED` and `PERSON_IDENTITY_UNRESOLVED`;
- five-layer deeper holder "Not calculated…", with L2 "80% — direct holding in client" and
  the general warning (no POC links);
- diamond ("held through multiple paths" on both occurrences), cycle and unlinked rows
  still "Not retained";
- the ANALYZED fixture keeps no banner, root/holding labels and person values.

**Evidence on `84a4bb2` (code), still valid for `97fcc8c` (doc-only delta):**
- typecheck PASS; full Vitest **64 files / 1067 tests PASS**; build PASS;
- focused browser E2E **10/10 PASS** on the frozen code (`ui2\e2e_focused.*`):
  - `authenticated-zero-touch:956`, `:1044`;
  - `five-layer-hybrid:78` (asserts the general warning stays);
  - `garden-happy-path:218`;
  - `ownership-document-streamline:79`, `:235`;
  - `phase24-identity:187`;
  - `s2-ownership:55`, `:194`;
  - `slice-b-registry-demo:94`.

  An earlier identical run (`e2e_focused_pre_banner_p.*`, 10/10) started before the
  `<p>` change and is superseded.
- On `97fcc8c`: `check_project_state`, `check_architecture`, `check_secrets` PASS;
  dev-context/project-state/architecture tests 55 OK; `git diff --check` clean; EOL stats
  identical.

Not rerun: the full browser suite (115/115 on `f79e319`) and backend suites (no backend
change).

## Next authorized action

Fresh independent QG on `f79e319`. Then owner visual review. Then OWNER VISUAL REVIEW /
PUBLICATION AUTHORIZATION PENDING.
