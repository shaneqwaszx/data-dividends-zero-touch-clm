# Recursive Ownership and UBO Discovery — Stage 1 Implementation Report

Implementer self-review evidence only; this is not an independent Quality Gate.

## Outcome

Stage 1 stable candidate: Garden `11111999A` discovers SIM LIM `111111111M` from Garden's
own direct shareholder record, then acquires SIM LIM separately through the existing
registry coordinator (fresh cache first, configured local Mock on miss/stale) and
attaches SIM LIM's own holders to the single Decimal graph. Accepted Garden results are
unchanged. Bounded, case-frozen, editable discovery policy and an additive catalogue
migration are in place.

## Identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\recursive-ownership-ubo-20261023`,
  branch `feat/recursive-ownership-ubo-registry-20261023` (no upstream).
- `BASE_SHA` = `origin/main` = `2f45324daec055b0929d17d2ad5fa518791c499d` at implementation.
- Tested content: the uncommitted working tree that became the frozen candidate commit
  recorded in the Stage 2 report (no edits between the last focused runs and freeze
  other than this report).

## Delta (by owner)

- Mock fixture/provider: `connectors/garden_business.py` (exact owner body for Garden,
  separate SIM LIM body, strict synthetic row model + existing official-Mock decoder,
  per-issuer D-046 derivation; flattened `derive_garden_ownership()` kept only for the
  official-Mock supplement), `connectors/mock_acra.py` (SIM LIM profile, per-issuer
  ownership, namespace `MOCK_ACRA_SYNTHETIC_V2`).
- Registry: `services/onboarding.py` `acquire_subsidiary_registry_evidence()` (read-only,
  existing router + coordinator), `services/registry_acquisition.py`
  (`SubsidiaryRegistryEvidence`, V2 seed admission), `connectors/registry_ownership.py`
  (`acquisition_ownership_source()` extracted, behavior unchanged).
- Ownership: new `services/ownership_discovery.py` (scheduling only); `services/
  ownership_analysis.py` (discovery hook under the case lock for SINGLE_SOURCE registry
  graphs, post-acquisition currentness recheck, two new review issues, additive
  `unresolved_entity_shares`); `domain/ownership.py` (audit models, issue codes, record
  fields).
- Policy: `domain/policy.py` (rule IDs, `OwnershipDiscoveryPolicySnapshot`, snapshot
  field/validation, catalogue schema 3 `MIGRATED`), `services/policy_management.py`
  (4 rules, cross-rule trace <= UBO, snapshot freeze, additive migration),
  `services/policy_impact_advisor.py` (Ownership stage label), `api_policies.py`.
- Persistence: `persistence/models.py`, `persistence/mongo_case_store.py` (envelope
  schema 11, v10 legacy reader, non-null discovery rejection for v1-v10).
- API/frontend: `api_models.py` optional `discovery`; `types.ts`, `PolicyRules.tsx`
  (explanations/units), `OwnershipPathExplorer.tsx` (read-only discovery summary, partial
  issue codes).
- Docs/governance: ADR-013, D-076, Q-019, five contract amendments, ARCHITECTURE delta,
  PROJECT_STATE envelope metadata, policy-authority checker claim (39 rules).
- Tests: new `test_recursive_ownership_discovery.py`, `test_ownership_discovery_policy.py`,
  `test_recursive_ownership_real_mongo.py`, `OwnershipDiscovery.test.tsx`; existing tests
  updated only where they pinned the old flattened Garden shape, the 35-rule count,
  schema 10 as current, or derived historical envelopes from current snapshots.

## Garden trace (local Mock, discovery policy frozen)

Garden raw body → strict decode → Garden direct edges `ENTITY_11111999A → 111111111M`
62.500000% and `→ S9988776F` 37.500000% → SIM LIM is a LEGAL_ENTITY leaf with verified
UEN → `acquire_subsidiary_registry_evidence("111111111M")` → first case `FETCHED`
(4 SIM LIM connector operations: profile, officers, parties, relationships), later cases
`CACHE_HIT` (0 SIM LIM operations) → SIM LIM edges `111111111M → 111111111M.S123AC1234E`
81.818182%, `.S2222222E` 9.090909%, `.S23BT2997U` 9.090909% → engine: ABCD123
51.13636375% (one path), LIM CHOON HUAT 37.500000%, two holders 5.681818125%;
ANALYZED, graph complete, certainty COMPLETE. Before/after percentages identical.

## Stage 1 focused evidence

All on the uncommitted pre-freeze tree over base `2f45324` (Stage 2 re-runs the full
matrix on the frozen commit; this is implementer evidence only):

| Check | Result |
|---|---|
| Backend focused regression slice (56 files: ownership, registry/cache, ACRA/Marketplace, Garden, policy, persistence/legacy, zero-touch, new suites) | 1626 tests, 0 failed, 6 skipped (guarded) |
| New suites `test_recursive_ownership_discovery.py` / `test_ownership_discovery_policy.py` | 40 / 21 passed (rerun after final message edit) |
| Physical Mongo, all `*real_mongo*` suites + Mongo read performance, disposable `mongo:7` on loopback, generated allowlisted databases, cleanup verified by the harness | 187 run: 186 passed, 1 failed (adjacent-namespace fixture pinned to the new V2 name), fixed to V3 and that file rerun 6/6; new physical suite 2/2 |
| Ruff (`apps/backend scripts tests`), mypy (`app`, 128 files) | pass / pass |
| `check_architecture`, `check_project_state`, `check_policy_authority`; root governance tests (`test_check_policy_authority`, `test_check_project_state`, `test_dev_context`, `test_check_architecture`) | PASS; 14 + 55 passed |
| Frontend typecheck; full Vitest | pass; 63 files, 1050 tests passed |
| PR #102 runner, exact selector file (Policy & Rules at all widths, RM policy view, responsive policy, local-Mock Garden partial registry, official-Mock Garden happy path, S2 multi-level ownership edit, Garden hierarchy, golden STP, ownership blocker simulations) | `E2E SUITE PASS: 10 configured selectors passed in isolated lifecycles` |
| `git diff --check`; whitespace scan of 7 new files | clean; 0 problems |

Not run in Stage 1 (Stage 2 scope): full backend pytest, full root tests, frontend build,
unfiltered E2E.

## Stage 1 remediation R1 (after Stage 2 FAIL on `512a424`)

- F1 (candidate defect): `scripts/slice_c_recovery_fixture.py` built its legacy stale-policy
  snapshot from a current snapshot without clearing the new `ownership_discovery`, which
  the snapshot validator correctly rejects. The fixture now sets it to `None`, matching
  legacy semantics. Evidence: root `tests/test_slice_c_e2e_fixture_routing.py` 16/16;
  backend `test_slice_c_blocker_recovery.py` 9/9; selector
  `e2e/slice-c-recovery.e2e.ts:156` passed via the PR #102 runner.
- Stage 2 observation: the new physical suite is now in `PHYSICAL_SUITES`
  (`scripts/run_physical_mongo_tests.py`) with the existing inclusion assertion, so the
  hosted physical job selects it. Tooling tests 46/46 with the Slice C routing file; Ruff clean.
- F2-F4 were classified by Stage 2 as environment/pre-existing on base and are unchanged.

## Known limitations and risks

- Share units stay in the fixture source; the normalized local Mock operation keeps the
  existing six-decimal percentage shape (adding units would correctly force denominator
  review under the existing engine).
- No provider supplies verified person bindings; cross-issuer identical identifiers stay
  under review. Nominee/trustee status is not represented by the Mock DTO and is never
  inferred.
- Deferred branches always keep review; the trace threshold saves calls, never review.
- A 0% UBO threshold can no longer be activated (trace must not exceed it).
- Official Marketplace Mock lane has no separate SIM LIM operation; its labelled local
  supplement remains and is excluded from discovery.
- Rolling back to pre-schema-11 code cannot read new envelopes or schema-3 catalogues.
