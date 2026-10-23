# Recursive Ownership and UBO Discovery — Planner Handoff (Stage 1)

## Identity and authority

- Worktree `C:\Users\shane\Desktop\claude-worktrees\recursive-ownership-ubo-20261023`,
  branch `feat/recursive-ownership-ubo-registry-20261023` (no upstream).
- `BASE_SHA` = `origin/main` = `2f45324daec055b0929d17d2ad5fa518791c499d` (post PR #102/#103).
- Owner-authorized bounded Singapore Mock POC (Master Assignment v4, 2026-10-23):
  task-local edits, later local Stage 2 integration. No push/PR/merge. Not sponsor
  approval of legal UBO policy, real ACRA subsidiary operations or GoldTier hierarchy.
- Change classes: `BACKEND_DOMAIN`, `BACKEND_API`, `PERSISTENCE`, `EXTERNAL_PROVIDER`
  (Mock fixture/provider parity), `FRONTEND_UI`. Skills: `fyp-phase-execution`,
  `external-provider-integration`, `persistence-schema-change`,
  `architecture-change-review`, `integration-security-review`.

## Baseline audit (current source, read-only)

- Local `MockAcraConnector` returns `derive_garden_ownership()` for `11111999A`: one
  flattened response (Garden 62.5/37.5 plus SIM LIM 81.818182/9.090909/9.090909). No
  company profile exists for `111111111M`. Baseline Garden analysis: `ANALYZED`;
  ABCD123 `51.13636375`, LIM CHOON HUAT `37.500000`, two holders `5.681818125`.
- `RegistryAcquisitionOwnershipProvider.load()` reads only the root
  `case.registry_acquisition`; no subsidiary interface exists.
- Official Marketplace Mock lane: no relationships operation; Garden uses the separately
  labelled `LOCAL_SYNTHETIC_SUPPLEMENT` (flattened `derive_garden_ownership()`).
- Registry cache key = UEN + ACRA/MOCK/`PHASE10_ACQUISITION_V1`/namespace;
  `MOCK_ACRA_SYNTHETIC_V1` entries for Garden hold the flattened shape.
- Policy catalogue: 35 rules; `_upgrade_legacy_catalogue()` handles only 29/21/8 prefixes
  and rebuilds a DEFAULT catalogue (would drop proposals/approval history).
- Existing fixtures place eligible UENs only on non-leaf corporate owners (seed pack) or
  use `SYN-` identifiers, so leaf-only discovery changes no other accepted scenario.

## Decisions (project-defined, provisional)

1. Garden and SIM LIM are separate local Mock issuers. Each serves only its own direct
   holders from an exact synthetic `coShareholdersDetails`-shaped body validated by a
   strict fixture adapter (category, issuer echo, Decimal units, single share class,
   explicit Active/Withdrawn) and D-046 equal-unit six-decimal derivation. SIM LIM gains
   its own company profile. `derive_garden_ownership()` is retained only for the
   official-Mock supplement and now derives from the same per-issuer bodies.
2. Local synthetic dataset namespace becomes `MOCK_ACRA_SYNTHETIC_V2`, isolating old
   flattened V1 cache entries (adjacent miss). Bound V1 case evidence is never rewritten.
3. `OnboardingService.acquire_subsidiary_registry_evidence()` is the narrow read-only
   subsidiary interface over the existing router/coordinator (cache-first, provider on
   miss/stale, no case mutation).
4. `OwnershipDiscoveryCoordinator` (new service) schedules bounded iterative retrieval
   for corporate leaves with verified SG UEN and COMPANY legal form. All Decimal path
   math stays in the existing engine (`calculate_ownership_paths` reports unresolved
   legal-entity shares additively).
5. Identity: issuer nodes dedupe by verified UEN; subsidiary persons are namespaced per
   issuer and never merged by source identifier or name. A repeated source person
   identifier across issuers raises `PERSON_IDENTITY_UNRESOLVED` review. An explicit
   verified-binding seam exists; no current provider supplies bindings.
6. 10% trace threshold defers branches only when a global bound proves no threshold
   change; otherwise deferred branches are expanded. Any unresolved branch keeps the graph
   partial and the existing REVIEW_REQUIRED/INDETERMINATE behavior.
7. Policy: four new rules (trace 10%, depth 5 (1..7), budget disabled, budget max 10
   (1..32)); cross-rule trace <= UBO threshold. Catalogue schema 3 adds an additive
   `MIGRATED` activation that retains prior active rules as superseded, keeps proposals
   and audit history, and rebases undecided proposals on the migrated base.
8. `CasePolicySnapshot.ownership_discovery` is optional; absent means legacy semantics
   (no subsidiary acquisition). Case snapshot schema 11 rejects the new fields in older
   envelopes.
9. Technical safeguards (non-editable): 32 subsidiary issuer lookups, 60 s deadline,
   sequential acquisition, existing graph/evidence caps.
10. Company C: test-scoped fixtures only; no new runtime demo company.
11. Discovery runs only for `SINGLE_SOURCE` registry graphs; the official-Mock lane's
    merged local supplement is never a lookup source (no mixed-lane evidence).
12. The read-only policy impact preview validates only what it evaluates; the
    trace <= UBO rule is enforced on submission, approval and every case snapshot. A UBO
    threshold of 0% can no longer be activated (it is below any positive trace value).
13. Legacy-envelope rejection follows the Phase24C precedent: v1-v10 envelopes may not
    carry a non-null discovery policy/audit; an explicit null is the legacy meaning.

## Non-goals

Other jurisdictions, invented ACRA endpoints, Sandbox/Live caching, control/voting/
nominee inference, legal UBO decisions, GoldTier hierarchy writes, frontend redesign,
CI/E2E tooling changes.
