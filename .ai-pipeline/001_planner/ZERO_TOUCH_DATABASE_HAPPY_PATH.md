# Post-UAT database happy path remediation

Authority: explicit owner request, 2026-10-05. BASE_SHA and latest origin/main: 771a9696e1e31e3865da4fbbb3f9b33b5959cb6a. Branch: fix/zero-touch-registry-reuse-happy-path. Managed worktree: zero-touch-registry-reuse-happy-path.

Scope: retain successful NO_MATCH progression and failure distinction; ordinary bounded database reuse through RegistryAcquisitionCoordinator; four synthetic normalized fixtures, idempotent guarded seed, scanned PDFs, UAT guide and regression coverage. No external ACRA/GoldTier calls, owner .env access, clm_poc access, push, PR, merge or worktree removal. Commit only after fresh independent exact PASS, at most two remediation rounds.

Architecture review: PROCEED. Existing RegistrySnapshotRepository and MongoRegistryCacheStore fit; no new cache/provider/ownership owner or dependency reversal. A separate synthetic dataset identity is explicitly admitted for non-production Mock lanes only and never populated by an external request. Fresh COMPLETE exact-key reads precede normal provider namespace acquisition. Invalid decoding remains fail-closed; missing/expired/incomplete adjacent seed evidence proceeds to configured acquisition. Existing partial/negative provider-cache behavior and CAS remain. ADR-010 records this trust/default amendment.

Write boundaries: config/composition, registry coordinator/domain identity, task fixture and seed/generation scripts, focused tests and physical harness suite registration, current cache/architecture/config docs, demo/sample-pack guidance. Search adapter/DTO changes only for a proved construction bug (none found initially). One implementation writer/coordinator; fresh independent reviewer writes only assigned gate report after freeze.

Verification: exact requested 38 criteria plus full backend, frontend, Ruff, strict mypy, typecheck/build, contracts/security/governance, affected browser E2E, four real Tesseract scans and generated allowlisted Mongo seed/restart/reuse/CAS/adverse tests. No pre-PR gate for this local-only run. Source, tested and reviewed identities recorded separately.

Capabilities: exec and managed-worktree tools, independent subagent reviewer, Python 3.12.10 primary repo .venv with backend toolchain, Node 22.23.3, primary frontend dependencies, installed local Tesseract. Mongo loopback probe requires host execution; tests use generated clm_p16_<24 hex> databases exclusively and verify cleanup. Browser uses existing lifecycle harness owned ports and fake transports; serialize heavy runs. No sponsor vault needed for current query-construction diagnosis.

Current finding: NO_MATCH semantics already implemented; tests will substantiate. XPI query_items omits None and urlencode encodes exact documented aliases; actual rejection root cause unproved without authorized real UAT. Preserve safe SEARCH_REQUEST_REJECTED. KYC/segment remain explicit per-case decisions; no inferred company classification.

Verification discovery: ordinary cache binding exposed the existing entity-equality
constraint during authorized legal-name correction. Fix at prepare_reconciled_value:
clear only the active binding on a changed name, retain original acquisition and shared
snapshot; prove normal auto-mode Mongo correction/restart/no-replay. Update older direct
case-store test composition explicitly; do not add memory fallback in Mongo runtime.
