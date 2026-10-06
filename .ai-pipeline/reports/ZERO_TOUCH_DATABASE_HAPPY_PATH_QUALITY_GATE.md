# Database-first zero-touch happy-path independent quality gate

Date: 2026-10-05. Fresh independent review under `fyp-quality-gate`; reviewer-only run, with no implementation, test, configuration, ordinary documentation or Git mutation.

## Executive result

**PASS — P0/P1/P2 = 0/0/0.** The current owner-authorized remediation meets all 38 requested acceptance criteria. No required fix remains on the exact frozen content identified below. The verdict permits the explicitly authorized local commit and owner review only. It does not establish PR readiness, external Sandbox absence, Live interoperability or permission to push, open a PR, merge, delete the worktree or begin another phase.

## Current, tested and reviewed identity

- Branch: `fix/zero-touch-registry-reuse-happy-path`.
- Worktree: `C:/Users/shane/.codex-clean2/worktrees/zero-touch-registry-reuse-happy-path/data-dividends-zero-touch-clm`.
- HEAD, BASE_SHA and inspected `origin/main`: `771a9696e1e31e3865da4fbbb3f9b33b5959cb6a`.
- Frozen reviewed payload: exactly 32 paths, recorded in `ZERO_TOUCH_DATABASE_HAPPY_PATH_REVIEW_MANIFEST.json`.
- Raw-content aggregate SHA256: `fbe9a00d3171e6dbef83c44c8f89ec90ffb66a014b2cbb398b340c0d71ef27f6`.
- Aggregate formula: lexically ordered UTF-8 concatenation of `path + NUL + raw_sha256 + NUL`, then SHA256.
- Every individual raw SHA256, recorded Git clean-filter blob ID and aggregate was independently recomputed. All matched at review start and completion. No unexpected modified/untracked path appeared.
- Current source is the above parent plus the frozen uncommitted payload. Tests exercise that content, rather than a future local commit. The coordinator must verify staged/committed blob identities against the manifest before claiming the new commit contains accepted content.
- The manifest and this report are explicitly excluded derivative evidence. Changes to any of the 32 reviewed paths invalidate this verdict.

The full path set is reproduced at the end of this report.

## Acceptance checklist

Evidence labels: F = independent focused 185-test execution; M = independent physical 10-test execution; A = independent additional assertions/CLI probes; B = frozen full backend; E = coordinator frozen browser execution; S = inspected current source/contracts/decisions.

| # | Requirement | Result and evidence |
|---|---|---|
| 1 | Successful zero-result Search is NO_MATCH | PASS: strict HTTP200/list/zero-candidate branch; F four new-customer journeys. |
| 2 | NO_MATCH completes Existing-customer search | PASS: F requires GOLDTIER_SEARCH in completed stages. |
| 3 | NO_MATCH is not an exception/review blocker | PASS: F requires final confirmation as sole remaining blocker. |
| 4 | Workflow continues after NO_MATCH | PASS: F documents, ownership, readiness and submission complete. |
| 5 | Request rejection remains failure | PASS: F HTTP400 produces FAILED / SEARCH_REQUEST_REJECTED and confirmation409. |
| 6 | Timeout remains failure/uncertain | PASS: F timeout failure injection cannot dispatch. |
| 7 | Malformed response remains failure | PASS: F non-list HTTP200 cannot establish absence. |
| 8 | Failure is never converted into NO_MATCH | PASS: F rejection/timeout/transport/malformed cases; S unchanged adapter. |
| 9 | Fresh exact COMPLETE DB evidence suppresses ACRA | PASS: F/M all four fixtures, connector counters require zero calls. |
| 10 | Missing DB evidence uses provider acquisition | PASS: F exact miss requires one configured-provider acquisition. |
| 11 | Expired DB evidence uses provider acquisition | PASS: F/M exclusive90-day expiry, seed retained unchanged. |
| 12 | Wrong-UEN evidence cannot bind | PASS: F adjacent key ignored; mismatched returned entry fails closed. |
| 13 | Wrong provider/dataset cannot bind | PASS: F contract/dataset mismatch; A wrong environment/unapproved seed identity rejected; S exact provider comparison. |
| 14 | Incomplete evidence cannot create false COMPLETE state | PASS: F incomplete synthetic seed bypassed without mixing provider namespaces. |
| 15 | Fresh DB evidence survives restart | PASS: M all four normal Mongo journeys and retained seed revisions. |
| 16 | Case gets deep/current bound copy | PASS: F fresh binding timestamp; mutating returned entity does not mutate shared snapshot. |
| 17 | All four fixtures seed successfully | PASS: F/M CLI and repository seed create exactly four known keys. |
| 18 | Seed is idempotent | PASS: F/M rerun leaves fresh entries/revisions unchanged; expired refresh uses CAS. |
| 19 | Every bundle validates COMPLETE | PASS: F/M existing strict domain and storage decode. |
| 20 | All graphs validate | PASS: F normal existing ownership engine returns ANALYZED. |
| 21 | Direct parent totals equal100% | PASS: F Decimal totals at every represented parent. |
| 22 | Expected UBO calculations pass | PASS: F direct/nested percentages and inclusive>=25 candidate classifications. |
| 23 | No real PII | PASS: S names/identifiers entirely DEMO; no natural-person registration identifiers/NRIC. |
| 24 | Seed performs no provider HTTP calls | PASS: S utility imports domain/repository only; F/M local repository/driver execution. |
| 25 | Every company gets fake successful NO_MATCH | PASS: F normal XPI fake transport; real Sandbox absence expressly unclaimed. |
| 26 | Every company uses DB registry evidence | PASS: F/M ordinary default settings and CACHE_HIT. |
| 27 | ACRA count is zero | PASS: F/M NoAcra assertions across all four cases and restart. |
| 28 | Scanned PDF identity auto-confirms | PASS: F four image-only PDFs processed by actual installed Tesseract; AUTO_CONFIRMED/all ACCEPTED/score>=0.85. |
| 29 | Ownership needs no manual declaration | PASS: F/M complete registry graph, ANALYZED and null manual-review receipt. |
| 30 | Readiness reaches final confirmation | PASS: F only TARGET_CONFIRMATION_REQUIRED remains. |
| 31 | New-customer path includes one Shell | PASS: F exactly GET,GET,POST,POST,GET; Shell/Policy CREATED, Amend SKIPPED. |
| 32 | ID comes from Shell response | PASS: F retains fake Shell response ID SYNTHETIC-GT-S3; S ledger mapping. |
| 33 | Exact-ID readback verifies same ID | PASS: F last query exactly goldTierID=SYNTHETIC-GT-S3; READBACK SUCCESS. |
| 34 | No mutation replay | PASS: F repeated confirmation409; M restart/repeated confirmation leaves counters unchanged. |
| 35 | Unsafe database names rejected | PASS: F allowlist tests including clm_poc; S guard before client creation. |
| 36 | Production refused | PASS: F guard and A actual CLI production refusal/no document changes. |
| 37 | No secret/raw payload output | PASS: M/A safe stdout, S fixed error projection, independent secret scan. |
| 38 | Authorization/currentness/no-replay preserved | PASS: S existing lock/CAS/reconciliation/ledger owners retained; F/M/B adverse and regression evidence. |

## Contract and integration review

No contract/mapping defect found. Successful absence and technical uncertainty remain distinct in the current XPI adapter and early-Search/CLM owners. The current request DTO rejects blank/control-bearing values, emits only supplied documented aliases, and the connection uses urlencode. Independent punctuation/query coverage confirms omitted optional criteria and correct legalName/countryOfIncorporation construction. No deterministic request-construction bug was established; the original real SEARCH_REQUEST_REJECTED cause remains unknown without separately authorized external UAT. Rejection still blocks all target mutations. Independent registry/document collection may continue under D-061.

D-069/ADR-010 transparently authorize one separate LOCAL_SYNTHETIC_UAT_V1 dataset in the two existing non-production Mock lanes. Seed references and sourcing times remain local/synthetic, never fabricated HTTP provenance. The current configured provider's cache namespace is preserved. Missing, expired or valid-but-incomplete seed evidence proceeds to configured acquisition; malformed/corrupt persisted data remains a fail-closed storage error under the unchanged decoding contract. This preserves the explicit user requirement not to weaken fail-closed decoding.

The sample-catalogue correction is operation-specific and does not promote XYZ ACCOUNTING or another basic-profile sample into a coherent whole-company fixture. Garden retains its bounded special-case authority. No quarantined example, new jurisdiction, provider endpoint, vocabulary, related-party/hierarchy creation or final sponsor approval is introduced. Q-012/Q-015/Q-016 and other existing sponsor dependencies remain open at their broader boundaries.

## Testing and adversarial evidence

### Independently executed

- Focused pytest with addopts override and cacheprovider disabled: test_zero_touch_database_happy_path.py, test_phase16_registry_cache.py, test_slice_b_registry_demo.py and test_goldtier_xpi_sandbox.py: **185 passed**, no skips, 28.49s.
- Physical pytest for test_zero_touch_database_real_mongo.py plus test_slice_c_real_mongo.py: **10 passed**, no skips, 33.37s. Newly generated allowlisted clm_p16 databases only; cleanup helpers verified absence. These execute the real Mongo7 driver/server and normal app composition.
- Four actual installed Tesseract scans passed inside the focused run. Each PDF has zero native extracted text and exact identity evidence auto-confirms. Independent in-memory regeneration reproduces all four PDF bytes exactly.
- Additional isolated assertions: wrong source environment, cancellation and unapproved seed identity reject before provider calls. All passed.
- Additional actual CLI checks: missing --check creates no database; populated --check changes neither four documents nor index metadata; production --seed exits2 without changes; generated database cleanup verified absent. An earlier optional hand-driven probe observed a nonzero seed return without retaining its inner result; subsequent diagnostic and complete probes passed unchanged. Its isolated cause is not established and the first attempt is not counted as passing evidence. No required test was skipped or assertion relaxed.
- Full frontend: npm test -- --reporter=dot, **42 files / 517 tests passed**.
- npm run typecheck: **PASS**. npm run build: **PASS**.
- Full backend Ruff from apps/backend: **PASS**. Strict mypy: **125 source files, PASS**.
- Contract unittest discovery: **44 passed**.
- check_secrets, check_architecture, check_project_state, check_policy_authority and check_external_provider_readiness: **PASS**.
- Tracked git diff --check and explicit whitespace check of every reviewed Markdown file: **PASS**.

### Coordinator execution on the same frozen payload

- Full backend: **2,524 collected;2,396 passed;128 conditional skips;4 warnings;968.39s;exit0. The128 skips are122 Mongo items plus6 legacy real-OCR items, all executed in the separate required lanes below**.
- Supplemental legacy actual-OCR acceptance: **6 passed**,9.11s, installed Tesseract PATH and CLM_REAL_OCR_REQUIRED=1 (PNG/JPEG/TIFF/scan PDF/mixed PDF/poor PNG).
- Full guarded physical harness: **17 suites,122 collected,122 passed,0 failures/errors/skips**.
- Security/governance unittest modules: **170 passed**,98.903s. Includes scanner, pre-PR unit tests (not publication gate), development context, architecture/state/policy/provider checks and external-provider/GoldTier evidence validators.
- Four affected real-browser/HTTP lifecycle tests: **4 passed**, each separately owned and cleaned: SliceB fresh-cache Merlion7.3s; SliceC legal-name discrepancy6.5s; normal S3 Sandbox-fake submission4.2s; Garden scanned existing-customer7.8s with installed Tesseract in process PATH. **Zero browser network-policy violations.**
- Script Ruff, check_tooling_config and pip check: **PASS**.

Test resources were task-owned loopback Mongo7 and fake ACRA/GoldTier transports. No external ACRA or GoldTier call occurred. No owner .env, private sponsor artefact or clm_poc access was required. No final manual-UAT database remains seeded: execution evidence used newly generated disposable targets with verified cleanup. The utility and guide provide the owner’s reproducible safe seed procedure.

Existing warnings are Starlette/httpx TestClient deprecation, React SSR/useLayoutEffect/act test warnings and the Vite>500kB bundle advisory. These are not new defects introduced by this payload.

## Code and architecture review

No P0/P1/P2 finding. The existing RegistryAcquisitionCoordinator, RegistrySnapshotRepository and MongoRegistryCacheStore remain the only registry reuse/persistence owners. The default changes from disabled to auto for ordinary non-production Mock composition; explicit disabled and legacy mock retain defined compatibility. Auto production/generic Sandbox does not enable cache use. Mongo composition requires the real registry repository rather than falling back to memory.

The new seed lookup is read-only, exact-key, COMPLETE-only and fresh under frozen case policy. It returns defensive copies with the original seed timestamps and binding identity. Provider namespace operation-prefix/negative cache behavior, bounded single-flight and existing CAS remain intact. The seed preflights all four deterministic expected entries, inserts missing entries, leaves fresh entries alone and refreshes only expired matching entries with expected revision. No direct raw Mongo insertion, upsert, second cache, route-to-storage access or second ownership calculation was introduced.

Ordinary default binding exposed the existing entity-equality constraint during an authorized legal-name reconciliation. The narrow owner-local fix clears only the active equality binding when the canonical legal name changes. It preserves the original acquisition bundle and shared registry snapshot and does not weaken the binding validator. Independent physical SliceC execution proves correction, retained acquisition, remaining discrepancy, restart and repeated resume; read-only Search recheck remains required before later target mutation.

Fixture percentages are Decimal graph inputs. The existing engine computes ALPHA60/40, BETA42/28/30, GAMMA50/30/20 and DELTA30/10/40/20; below-threshold results remain distinct from PROVISIONAL_UBO_CANDIDATE. Unsupported SSIC/business activity is explicitly omitted. There is no legal UBO or compliance-engine claim.

## Security review

No P0/P1/P2 finding. Production/unsafe seed targets and collection collisions are refused before connection. --check does not initialize indexes or write. CLI output is bounded to synthetic names/UENs/counts or fixed error text, with no underlying exception/body/connection disclosure. All fixture identities and documents are visibly fictional. No natural-person identification number or real customer/provider payload is newly added.

Existing backend RBAC, safe inaccessible-case404, reauthorization inside sensitive lock/CAS boundaries, CSRF/session/team scope, strict storage decode and target confirmation/no-replay remain. No auth/TLS relaxation, public endpoint, client authority, provider retry, raw document retention or frontend persistent cache was introduced. The secret scan inspected the current tracked/untracked task paths and passed; scanner pattern coverage is not a claim of universal secret detection.

## Required fixes and readiness

Required fixes: **none**. Behavioral remediation rounds during this independent gate: **0**.

Ready for the explicitly authorized local commit of exactly accepted content and derivative manifest/report, followed by clean-index/worktree verification and owner review. The coordinator must retain the worktree and stop there. No pre-PR publication gate was run; PR readiness is unclaimed. Real Sandbox Search for these four names, external target mutations and Live/Production claims remain unexecuted and require separate owner authorization. No next phase is authorized by this gate.

Change classification: internal settings/coordinator API types and ordinary runtime reuse changed; public HTTP/API contract and persisted schema versions did not. Configuration and owner-authorized POC registry source precedence changed. External connector transport/DTO/mapping, business KYC/segment choices, Decimal threshold, authentication/TLS, target ordering and provider status did not change. Architecture extends existing owners with an explicit synthetic dataset trust admission; no new service/repository/provider owner is introduced.

## Git and reviewer write boundary

HEAD and origin/main remained at the stated baseline during review. The reviewed implementation was intentionally uncommitted:18 tracked modified paths plus14 new reviewed paths; index empty. The only reviewer-authored repository file is this assigned gate report. Test/build outputs are ignored runtime artifacts, not reviewed source changes. Reviewer performed no source fix, stage, commit, push, merge, branch/worktree mutation or next-phase work. Final raw hashes/Git blob identities and unexpected-path/whitespace checks remain clean.

## Complete reviewed path set

- .ai-pipeline/001_planner/ZERO_TOUCH_DATABASE_HAPPY_PATH.md
- .env.example
- apps/backend/app/composition.py
- apps/backend/app/config.py
- apps/backend/app/domain/registry_dataset.py
- apps/backend/app/persistence/composition.py
- apps/backend/app/services/onboarding.py
- apps/backend/app/services/registry_acquisition.py
- apps/backend/tests/fixtures/uat/zero-touch-database/README.md
- apps/backend/tests/fixtures/uat/zero-touch-database/demo-alpha-scanned.pdf
- apps/backend/tests/fixtures/uat/zero-touch-database/demo-beta-scanned.pdf
- apps/backend/tests/fixtures/uat/zero-touch-database/demo-delta-scanned.pdf
- apps/backend/tests/fixtures/uat/zero-touch-database/demo-gamma-scanned.pdf
- apps/backend/tests/test_phase12_real_mongo.py
- apps/backend/tests/test_phase16_registry_cache.py
- apps/backend/tests/test_s3_retained_recovery.py
- apps/backend/tests/test_slice_c_real_mongo.py
- apps/backend/tests/test_zero_touch_database_happy_path.py
- apps/backend/tests/test_zero_touch_database_real_mongo.py
- docs/ARCHITECTURE.md
- docs/PROJECT_STATE.md
- docs/contracts/README.md
- docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md
- docs/decisions/ADR-010_DATABASE_FIRST_SYNTHETIC_REGISTRY_REUSE.md
- docs/decisions/DECISION_LOG.md
- docs/demo/ZERO_TOUCH_DATABASE_HAPPY_PATH_UAT.md
- docs/integration/ACRA_API_MARKETPLACE_MOCK_READINESS.md
- docs/integration/CONFIGURATION_REFERENCE.md
- scripts/generate_zero_touch_happy_path_documents.py
- scripts/run_physical_mongo_tests.py
- scripts/seed_zero_touch_happy_path_companies.py
- scripts/zero_touch_happy_path_fixtures.py

## Independent staged-content receipt

The coordinator's post-PASS staging check found four differences between the original
clean-filter `git_blob` predictions and the actual index objects. This is an EOL
representation difference, not an implementation change. The derivative manifest now
retains the original fields and adds actual `staged_git_blob` and `staged_sha256`.

The reviewer independently verified all32 original raw SHA256 values and the unchanged
aggregate `fbe9a00d3171e6dbef83c44c8f89ec90ffb66a014b2cbb398b340c0d71ef27f6`.
For every staged source path, SHA256(index bytes) matches staged_sha256 and
SHA1(`blob ` + byte length + NUL + index bytes) matches both the actual Git index ID
and staged_git_blob. Thirty paths are raw-byte exact; the fixture README and
test_zero_touch_database_happy_path.py differ only by exact CRLF-to-LF normalization.
All four PDFs remain byte exact.

The four predicted-versus-index differences are composition.py, config.py,
test_phase12_real_mongo.py and PROJECT_STATE.md. Their index objects retain the exact
reviewed raw bytes, including existing CRLF; no source byte was changed to reconcile
metadata. The complete staged set is precisely32 reviewed paths plus the two excluded
derivative evidence artifacts. Source-path staged whitespace and the secret scan pass.
The earlier staged report's extra EOF blank line was removed when appending this receipt;
the coordinator must restage this report and the updated manifest and rerun the whole
staged whitespace check before commit.

**Exact PASS reaffirmed — P0/P1/P2 = 0/0/0; behavioral remediation rounds = 0.**
No implementation or acceptance criterion changed. Local-commit-only readiness remains
subject to the coordinator's final derivative restaging, clean-state and commit-object
verification. This reviewer made no Git mutation.
