# ACRA Hybrid Five-Layer Onboarding (D-077) — Stage 1 Implementation and Stage 2 Acceptance

Implementer and integration/testing evidence only. This is not an independent Quality
Gate.

## Outcome

Stage 1 is a stable candidate, and Stage 2 acceptance is recorded against the frozen
tree below. Under the opt-in official-lane setting
`ACRA_MARKETPLACE_OWNERSHIP_OVERLAY=hybrid_direct_overlay`, a user can onboard the new
five-corporate-layer root `201511222D` (OPQ PTE. LTD.) through the normal New Onboarding
UI with the generated PDF. Each corporate holder gets a cache-first official Marketplace
Mock lookup. Declared direct holders from the whitelisted overlay attach as
`LOCAL_SYNTHETIC_RELATIONSHIP`/`LOCAL` links, and the analysis always remains
REVIEW_REQUIRED. Garden uses the same concept: official entity and people facts, a
direct-only overlay, and an official SIM LIM lookup. The default setting keeps the
accepted flattened Garden fixture.

**Live Marketplace probe: `NOT_RUN_CREDENTIALS`.** The session's permission classifier
denied a boolean-only presence check of the Marketplace credentials. Zero Marketplace
calls were made. All network-shaped evidence below uses an allowlisted in-process
protocol transport (`AUTOMATED_OFFLINE_SIMULATION`).

## Identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\acra-hybrid-five-layer-20261023`,
  branch `feat/acra-marketplace-hybrid-five-layer-ubo-20261023`.
- `BASE_SHA` = `HEAD` = `origin/main` = `24c3de385ba5cda099a3dc3b1b266fdf93aa4738`
  (re-fetched at Stage 2; unchanged, so no integration merge was required).
- The candidate is uncommitted (no commit authorization). Content identity is a tree
  computed with a temporary index (`git read-tree HEAD`, explicit path add of the
  modified and new files, `git write-tree`); the real index is untouched.
  - Original Stage 2 candidate: tree `3b19e398f0c3a940b12dcb6151b04622c4e3d59a`
    (56 files, +4116/−112). Superseded by the owner scope correction.
  - **Corrected candidate: tree `1bf13a8bd7fdfe91c77394dc9a232f0e223ab94e`**
    (50 files, +3177/−103, identical with `--ignore-cr-at-eol`). The only later
    difference is this report's text, which carries no behavioural evidence.
- Input catalogue: the assignment's input folder did not exist. A byte-identical
  candidate in the user's Downloads test pack matched the described document: 7 pages,
  "Last updated 18-November-2025", every cited UEN on the cited page. SHA-256
  `121b908f21867108a256e8af9d4914d856a8e64b80702f3286bf5f679eebf2f9`. It was read in
  memory only and is not tracked.

## Owner scope correction (2026-10-23, mid Stage 2)

The owner restricted the work to the backend. Changes to the existing Ownership & UBO
frontend design, components, graph presentation, navigation or shared frontend types
are not authorized.

- Audit against `24c3de3`: four modified frontend source files were out of scope:
  - `src/types.ts`: optional display fields and new literal values.
  - `src/ownershipDisplay.ts`: badge and comparison label helpers.
  - `src/pages/OwnershipPathExplorer.tsx`: hybrid banner, evidence-separation list,
    identity column, L-level cell, labelled comparison and one partial-issue code.
  - `src/pages/OwnershipStructure.tsx`: L1..L5, identity, synthetic-link and review
    badges, plus the comparison row.

  Two new UI-only test files and their export helper were also out of scope:
  `OwnershipFiveLayerHybrid.test.tsx`, `ownershipFiveLayerHybridFixture.json` and
  `scripts/export_five_layer_hybrid_fixture.py`. The browser spec is in scope.
- Remediation, bounded to those paths only: the four files were restored from `HEAD`
  with an explicit per-path restore, the three UI-only files were deleted, and the
  browser spec now asserts only what the existing components render. No backend,
  persistence or API change was needed.
- The unchanged UI renders the scenario. Verified in the browser:
  - five layers;
  - the indented L1→L2→L3→L4A/L4B→L5 chain with holdings;
  - per-link `LOCAL_SYNTHETIC_RELATIONSHIP · LOCAL` source and the root
    `ACRA_REGISTRY_ACQUISITION · MOCK` source;
  - the exact path calculation and two retained paths;
  - REVIEW_REQUIRED / INDETERMINATE;
  - the raw `LOCAL_SYNTHETIC_OVERLAY` discovery outcome.
- Limitation for owner decision (not implemented): per-issuer `identity_basis` /
  `official_entity_lookup`, the evidence-separation booleans and
  `synthetic_basis_threshold_result` are available only through the API. They are
  additive optional fields that current frontend types and rendering ignore. The TS
  `source_classification` union does not list the new value. This has no runtime
  effect; updating it would need owner authorization.

## QG round 1 remediation (FAIL on review tree `2f53d78…`)

The bounded fix covers only the gate's findings.

- **Medium (false success):** `scripts/phase24_acra_mock_discovery.py` printed
  `evidence_class: MOCK_INTEROPERABILITY_OBSERVED` unconditionally. A new pure
  `evidence_class(receipts)` now derives the label:
  - `MOCK_INTEROPERABILITY_OBSERVED` only when at least one official data read returned
    HTTP 200;
  - otherwise `AUTHENTICATION_FAILED` (401/403), `TRANSPORT_FAILURE` (no HTTP response)
    or `NO_SUCCESSFUL_READ`.

  It is emitted only for the `five-layer-hybrid` lane, so the other lanes keep main's
  output shape. `test_five_layer_probe_lane.py` now has 4 tests: the success derivation,
  token 401 with zero reads, transport failure, and absent/failed reads plus lane
  scoping.
- **Low (docs):** the demo guide no longer claims a UI label for officially verified
  issuers (that field is API-only). It now states that repeat-onboarding cache reuse
  applies to NOT_FOUND issuers, while an official COMPANY profile re-reads its required
  shareholder operation. It documents the derived `evidence_class` values.
- **Not changed (non-blocking observations/test gaps):** no backend app, persistence,
  API, frontend source or E2E code changed. All behavioural evidence for backend,
  physical, frontend and browser remains valid.

## Delta (by owner)

- Overlay fixture boundary (new): `connectors/hybrid_ownership_overlay.py`. It holds the
  strict models, two whitelisted scenarios and the official-root eligibility predicate.
  `garden_business.py` exposes the existing six-decimal unit rule.
- Discovery: `services/ownership_discovery.py` takes an optional scenario. For a scenario
  issuer it still performs the official lookup, then attaches declared holders via the
  extracted `_merge` (shared with the official path). It records the official lookup and
  identity basis, plus the hybrid evidence separation. Provider failure, mismatch,
  another lane or official shareholder rows leave the branch unresolved.
- Registry cache signals: `services/registry_acquisition.py` (`negative_cache_hit`,
  `entity_profile_reused`) and `services/onboarding.py` (a fresh definitive NOT_FOUND
  hit now counts as a cache hit with zero provider calls).
- Ownership service: `services/ownership_analysis.py`. It applies the root overlay after
  eligible official evidence. The discovery gate admits the hybrid classification but
  never the flattened supplement. Validation accepts LOCAL overlay provenance only in
  hybrid mode. Every hybrid analysis gets `SYNTHETIC_OWNERSHIP_EVIDENCE`. Unresolved
  branches count against topology. The labelled `synthetic_basis_threshold_results` uses
  the same inclusive comparator.
- Domain/persistence: `domain/ownership.py` adds the new outcome, issue, record/audit/
  candidate fields and validators. `persistence/models.py` and `mongo_case_store.py`
  move the envelope to schema 12; the exact v11 reader and the v1..v11 readers reject
  hybrid values.
- Config/composition/API: `config.py` (validated setting), `composition.py` (exclusive
  compositions), `api_models.py` (literal alias), `.env.example`.
- Frontend: **none.** After the owner scope correction (see below), every
  `apps/frontend/src` file matches `origin/main`. The only remaining frontend path is
  the browser-verification spec `apps/frontend/e2e/five-layer-hybrid.e2e.ts`, which
  asserts what the existing components already render.
- Document: `scripts/generate_five_layer_marketplace_hybrid_client.py` produces
  `apps/backend/tests/fixtures/uat/five-layer-marketplace-hybrid-client.pdf`
  (SHA-256 `a2d9b1985d53e31414b00af40ba3902689f4dffcd67a5fd7a620abe7e5555551`). It is
  listed in the UAT README and the exact allowlist test.
- Offline fixture/E2E/tooling: `scripts/five_layer_hybrid_fixture.py`,
  `scripts/e2e_backend_server.py` / `scripts/run_e2e.py` (registry demo
  `five-layer-hybrid`), `apps/frontend/e2e/five-layer-hybrid.e2e.ts`, and
  `scripts/phase24_acra_mock_discovery.py` lane `five-layer-hybrid` (owner-run probe).
- Docs: D-077, an ADR-013 amendment, the contract section, ARCHITECTURE/PROJECT_STATE
  candidate notes (schema 12), the Phase 24 note and `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md`.
- Tests: new `test_hybrid_five_layer_overlay.py` (28), `test_five_layer_hybrid_journey.py`
  (2), `test_five_layer_probe_lane.py` (1), one physical test in
  `test_recursive_ownership_real_mongo.py` and one browser spec. Existing tests changed
  only where they pinned schema 11 as current or 12 as the unknown version (now 13),
  plus one renamed physical test.

## Five-layer result (offline protocol fixture)

Paths are L1 `201511222D` → L2 `200811111M` 80% → L3 `201688888A` 62.5% →
L4A `200811111K` 60% / L4B `199801111H` 40% → L5 `111111111K` 100% / 50% (diamond,
acquired once). Persons: ALEX TAN 20; BEATRICE LIM 30; CHARLES ONG 10; DIANA KOH
18.75 + 6.25 = 25; EDWARD NG 11.25 + 3.75 = 15. All candidates are REVIEW_REQUIRED /
INDETERMINATE. On the synthetic basis, BEATRICE LIM and DIANA KOH are MET (DIANA KOH
exactly 25, inclusive) and the rest are NOT_MET. Issues are SYNTHETIC_OWNERSHIP_EVIDENCE
and OWNERSHIP_METHOD_UNSUPPORTED (root `OTHER`). The audit is topology complete,
official identity incomplete, quantitative evidence false, certainty UNCERTAIN.
Counters: first onboarding 1 token and 7 GETs; repeat onboarding 0 and 0 (5 cache hits);
past the 600 s negative TTL the 5 issuer reads recur.

## Stage 2 acceptance

The corrected tree `1bf13a8…` differs from `3b19e39…` only in frontend sources (restored
to `origin/main`), removed UI-only tests and their helper, the browser spec, the demo
guide and this report. Backend, persistence, API, contract and script behaviour is
byte-identical, so that evidence is reused. Frontend, browser, governance and hygiene
evidence was rerun on `1bf13a8…`.

| Check | Content run on | Result |
|---|---|---|
| Ruff (`apps/backend scripts tests`) | `1bf13a8…` (rerun) | PASS |
| mypy (`python -m mypy app` in `apps/backend`) | backend identical; reused | PASS, 129 files |
| Full backend pytest (`apps/backend/tests`, pinned worktree `PYTHONPATH`, JUnit) | `2340f21…`; backend identical to `1bf13a8…` except one physical-only test that this lane skips; reused | PASS: 3120 collected, 2947 passed, 173 skipped (physical-only), 0 failed, 1063 s |
| Physical Mongo (`run_physical_mongo_tests.py`, task-owned disposable `mongo:7` on 127.0.0.1:27219, generated allowlisted DBs) | `3b19e39…`; backend identical; reused | PASS: 25 suites, 168/168, 0 skipped (includes the new hybrid restart/schema-11 test) |
| CI-equivalent unittest lanes: contract (44), secrets, pre-PR, policy authority, `test_run_e2e` | `3b19e39…`; unaffected; reused | PASS (all OK) |
| Delivery-asset allowlist, dev-context/project-state/architecture unittests | `1bf13a8…` (rerun) | PASS |
| Frontend typecheck / full Vitest / build | `1bf13a8…` (rerun) | PASS / 63 files, 1050 tests (baseline inventory) / PASS |
| Targeted browser selector `e2e/five-layer-hybrid.e2e.ts:78` against the unchanged UI | `1bf13a8…` (rerun) | PASS |
| Full browser suite (`run_e2e.py --timeout-seconds 60`, Tesseract on PATH, `CLM_E2E_SYNTHETIC_MONGO_PORT`) | `3b19e39…`: 115/115 PASS (1470 s; superseded). `1bf13a8…`: rerun | PASS: 115/115 selectors in isolated lifecycles, 1693 s. The slowest is the pre-existing `performance-browser.e2e.ts:137` at 59.1 s against its 60 s budget (timing margin, not a failure) |
| `check_secrets.py`, `check_project_state.py`, `check_architecture.py` | `1bf13a8…` (rerun) | PASS / PASS / PASS |
| Whitespace (`git diff --check` plus every new untracked file) | `1bf13a8…` (rerun) | clean |
| Windows demo lifecycle (`test_demo_lifecycle_windows.py`) | `3b19e39…` | NOT EXECUTED (missing infrastructure). The launcher requires a worktree-local `.venv`; this worktree uses the primary checkout's venv. The run reported 9 environment failures ("Python virtual environment is missing", then one occupied-port consequence). The lifecycle scripts are not touched by this delta. CI creates the `.venv` |
| Live Marketplace Mock probe | — | NOT_RUN_CREDENTIALS |

## Self-review notes (implementer, not independent)

- No calculator, service or router branches on scenario UENs. The legacy Garden UEN
  checks remain only in the pre-existing legacy supplement.
- The hybrid lane cannot reach ANALYZED, and the synthetic-basis field is forbidden on
  non-review classifications.
- The offline OPQ root profile carries a visibly synthetic address so the canonical
  minimum can pass offline. Against the live Mock, a profile without an address would
  stop at `CANONICAL_DATA_INCOMPLETE` (documented).

## Authority and limitations

`USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL` (D-077). This is not ACRA
ownership, Live evidence, legal UBO policy (Q-004), Marketplace relationship/denominator
capability (Q-012), person identity authority (Q-019) or GoldTier hierarchy (Q-002). The
live probe is NOT_RUN_CREDENTIALS. No commit, push, PR or merge is authorized.
