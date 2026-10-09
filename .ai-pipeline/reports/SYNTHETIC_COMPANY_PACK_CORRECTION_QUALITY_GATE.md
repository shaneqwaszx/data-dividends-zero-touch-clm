# Synthetic company pack correction - independent Quality Gate

## Outcome

**FAIL** on the frozen 32-path correction candidate. The corrected database-first
runtime satisfies the focused A-H checks, but an affected internal API test consumer
still expects the former seven-field binding. The independently reproduced failure
blocks the required affected backend regression lane. No reviewer fix was made.
The prior Quality Gate PASS certifies only the superseded assignment and bytes.

## Reviewed identity and scope

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/synthetic-happy-path-company-pack/data-dividends-zero-touch-clm`.
- Branch: `feat/synthetic-happy-path-company-pack`.
- HEAD, BASE_SHA, inspected origin/main and merge base:
  `21124498cb1b8fd47b1406534d6fd9c24af0e2ea`; ahead/behind 0/0.
- Current source is intentionally uncommitted. HEAD alone is not the tested content.
- Reviewed and independently tested correction identity:
  `48802656a0c5c7a57b20b3610f1b606abcc52d3b2ed126fd11ead48f37a7d0a4`.
  Algorithm: SHA256 of sorted path + NUL + raw-byte file SHA256 + LF.
  The exact 32 paths and individual hashes are in
  `SYNTHETIC_COMPANY_PACK_CORRECTION_MANIFEST.json`; every path was inspected,
  including the task-owned new files and four PDFs. Aggregate and individual hashes
  matched before and after independent execution.
- The three historical report hashes match the manifest. Reports are excluded
  derivative evidence; this verdict does not alter the reviewed payload identity.
- Two additional Git-status paths, `apps/backend/app/connectors/mock_acra.py` and
  `apps/frontend/e2e/slice-b-registry-demo.e2e.ts`, were inspected and independently
  proved byte-equal to HEAD after CRLF/LF normalization. They have no substantive diff.
- Retired task paths `apps/backend/app/connectors/synthetic_company_pack.py` and
  `scripts/warm_synthetic_company_pack.py` are absent.

Authority: the complete explicit owner correction, AGENTS.md, workflow/change matrix,
ADR-010/D-069, registry freshness/persistence profiles, current source/tests, current
architecture/provider matrix and open questions. Applied `fyp-quality-gate` with
integration-security and POC regression review. Classes: BACKEND_DOMAIN/BACKEND_API,
PERSISTENCE, FRONTEND_UI and CI_TOOLING; ownership/retirement implications also reviewed.
Canonical workflow context was emitted with the scoped selector and full diagnostic.

## Acceptance evidence

| Challenge | Result | Direct evidence |
|---|---|---|
| A. Marketplace remains configured | PASS | Actual create_app builds the configured connector; runtime API and browser retain API_MARKETPLACE_MOCK. No runtime composition/default was changed. |
| B. New fresh seeds make zero token/HTTP calls | PASS | Four normal-composition API journeys, four normal Mongo runtime/restart journeys, four real browser journeys. Only default HTTP/token factories are replaced; the BaseException request guard escapes normal sanitization and any request fails immediately. |
| C. CACHE_HIT uses the local dataset | PASS | All eight fixtures use local_synthetic_registry_identity; exact retained local binding, COMPLETE four-operation evidence and original local references/timestamps are checked. Physical restart preserves full bundles/microseconds and leaves the official namespace empty. |
| D. Missing/expired fallback is real Marketplace | PASS | Unseeded eligible 202400018R and expired Orion reach the composed TOKEN then ENTITY_PROFILE transport and retain ACRA_ENTITY_NOT_FOUND without synthetic evidence. Existing mismatch/incomplete/corruption controls also executed. |
| E. No official provenance relabelling | PASS | Configured banner and actual evidence are separate. Original LOCAL_SYNTHETIC_SEED references survive. API label requires full approved identity equality and is nullable/allowlisted; eight independent projection probes reject adjacent/forged labels. |
| F. All four new full journeys | PASS | Orion70/30; Pacific40/35/25 inclusive; Straits48/40/12 effective; Meridian30/20/30/20 effective. Exact Decimal direct/indirect values and candidates, PDF MATCH/ACCEPTED/HIGH, explicit classification and Review & Send, COMPLETED/SUBMISSION_CONFIRMED, exact-ID readback and no replay executed. |
| G. Existing four remain supported | PASS | Alpha/Beta/Gamma/Delta actual Marketplace-composition journeys and existing physical cases passed. Independent execution of baseline fixture source proves all four full normalized snapshots unchanged. |
| H. Existing owners, no shortcut | PASS | New definition module feeds HappyPathCompany and existing seed manager/repository. No direct BSON writes, new store/coordinator, UEN-specific orchestrator branching or ordinary startup seed. Decimal engine and target ledger unchanged. |
| Warm/check safety and document preservation | PASS | Actual CLI creates8, rerun creates0, check finds8; guarded target validation precedes connection. CAS refresh/conflict, deep copy and exclusive expiry covered. Four PDF raw-byte hashes match the historical manifest and deterministic identity-only generation. |
| Required broader affected backend regression | FAIL | QG-CORRECTION-01 reproduced independently; coordinator broad run also contains another unresolved failure at this report cutoff. No broad PASS claimed. |

## Finding and required remediation

**QG-CORRECTION-01 [P2, acceptance blocker] - stale exact API binding assertion.**
`apps/backend/tests/test_slice_b_registry_demo.py:201`,
`test_third_merlion_owner_warmed_cache_uses_zero_new_acra_calls`, asserts the exact
former seven-field set. `BrowserRegistryEvidenceBinding` intentionally adds
`synthetic_seed_namespace`, so the ordinary Mock cache-hit response now contains
that eighth nullable field. Independent reproduction collected/executed one test:
**1 failed**, 1 inherited warning, 3.03 seconds. The assertion reports precisely the
extra `synthetic_seed_namespace` field. The earlier zero-new-ACRA-call and CACHE_HIT
assertions already pass, so this is a missed API test consumer, not evidence of a
Marketplace request or bad cache behavior.

Required bounded fix: preserve the exact minimized-key assertion, include the approved
new field, and assert its value is `None` for this ordinary non-seed Mock hit. Inspect
all other exact binding consumers and rerun this suite plus affected broad backend.
Do not weaken the assertion, remove the projection, infer local seed provenance from
CACHE_HIT, or add a new fallback. Freeze the changed path set and obtain a fresh
independent gate. Investigate the other broad failure from its actual traceback;
an isolated passing suite alone does not establish why that broad failure occurred.

## Independently executed evidence

All Python commands used the shared Python executable with BOTH the task root and
its apps/backend on PYTHONPATH; ordinary test conftest disables dotenv and provisions
runtime-only synthetic authentication. No primary-checkout result is reused.

| Command / observation | Exact result |
|---|---|
| pytest, no cache provider: test_synthetic_company_pack, its real_mongo suite, test_zero_touch_database_happy_path, its real_mongo suite, test_evidence_workbench_registry_projection | 63 collected/executed PASS; 0 skips/failures. New pack17, new physical5, existing owner29, existing physical6, projection6. Inventory independently recollected. |
| pytest, no cache provider: test_slice_f_document_pack and test_phase_07_delivery_assets | 21 PASS, 0 skips, 15.68s. |
| npm test -- --run src/pages/RegistryProvenancePanel.test.tsx | 1 file /17 tests PASS. |
| run_e2e.py --registry-demo synthetic-seed --grep 'Synthetic company pack' --backend-port 8825 --frontend-port 4225 --timeout-seconds 240 | 4/4 PASS, 29.3s; disposable database cleanup VERIFIED. Actual local HTTP/processes and Mongo, browser network-policy violations0. |
| Inline projection falsification (no source writes) | 8 PASS: exact identity label; mismatched provider/contract/three namespaces get no label; non-Mock fails closed; arbitrary browser namespace rejected. |
| Baseline fixture source executed in ephemeral module | Full normalized snapshot equality4/4 for Alpha/Beta/Gamma/Delta. |
| Historical manifest vs relocated PDFs | Raw-byte hashes preserved4/4. |
| check_architecture; check_project_state; check_secrets; check_policy_authority; check_external_provider_readiness | All PASS. Secret scanner supports bounded pattern coverage, not universal secret absence. |
| git diff --check and explicit all task-owned text whitespace check | PASS; tracked EOL conversion warnings only. Staged diff empty. |
| pytest QG-CORRECTION-01 node, no cache provider | 1 collected/executed FAIL at line201, confirmed exact stale key-set assertion. |

The 84 independently passing backend/governance tests above are separate executions
from the single failed regression probe; counts are not presented as a full backend PASS.
Inherited Starlette/httpx deprecation warnings remain. No passing evidence was obtained
by changing tests or implementation.

Coordinator-reported frozen-content broader evidence: focused73 PASS; physical Mongo20
suites/132 collected and executed PASS/0skips; frontend47files/562tests, type/build and
dependency integrity PASS; Ruff PASS, mypy126 source files PASS; contracts44 PASS;
governance/security/tooling159 PASS and extra security/governance152 PASS. These are
attributed coordinator evidence, supplemented by the direct independent executions
above, not falsely claimed as reviewer-run commands. The correct-source broad backend
run collected2712 tests and was still resolving failures at this cutoff. One reported
failure is independently reproduced above; isolated phase13_demo_scripts11 PASS does
not resolve the other broad failure's cause. A mistaken initial primary-checkout import
run was discarded by the coordinator and supplies no acceptance evidence.

Physical execution used only freshly generated allowlisted clm_p16 databases on the
existing task-owned mongo:7 loopback port27149. Tests verify cleanup absence; the browser
runner reports cleanup VERIFIED. No protected clm_poc access, .env read, URI/credential
printing, raw provider payload access, shared-container shutdown or unrelated-port
mutation was performed. Runtime-generated local test outputs are derivative only.

## Architecture, security and boundaries

Existing fixture and snapshot owners safely hold this responsibility; no new durable
owner or ADR is needed. The separate definition module contains fictional immutable
identity/graph data, not persistence behavior. CLI preflights all known keys, uses
insert-only create/update-only CAS and leaves fresh evidence unchanged; a batch remains
non-transactional across keys. No schema, codec, index, recovery or repository semantic
change was introduced. A new browser field does not become durable schema.

API/type and UI changed additively: nullable allowlisted local seed namespace and
truthful local evidence copy. Runtime fixture availability changes: four new UENs now
use approved local database evidence under ordinary configured Marketplace operation.
Normal connector configuration/composition, connector implementations, mapping,
business rules/thresholds, auth/security authority, canonical architecture ownership,
provider classifications and target sequencing are unchanged. Isolated E2E gains a
reserved Mongo port and seed scenario; CI lifecycle budget becomes234 minutes for73
selectors. Dependencies and lockfile are unchanged.

Browser data remains minimized: no private key/revision/fingerprint/arbitrary namespace,
endpoint or contract identifier is projected by the new label. Existing authorized
case routes and full retained domain binding validation remain the owners. Read/reopen
uses retained state, never registry/target replay. Synthetic officers are not promoted
to ownership candidates; PDFs carry no quantitative ownership. All parties/data are
explicitly fictional, no real personal identifiers or sponsor artefacts added.

## Readiness, limitations and Git handoff

No correction-specific unsafe runtime/architecture/security defect was found, but the
current candidate **fails acceptance** due to the confirmed regression test mismatch
and unresolved broad evidence. Required next action is bounded implementer remediation,
new frozen identity and fresh independent recheck. No next phase or publication is ready.
The report itself authorizes no Git action.

Marketplace remains MOCK, local seed remains LOCAL PROJECT SYNTHETIC MOCK, extraction
and Decimal ownership remain LOCAL, target acceptance here is Mock GoldTier. No new
real ACRA/GoldTier interoperability, Live/Production, KYC completion, final/legal UBO,
regulatory approval or Ready-for-Approval claim is established. Open Q-001..Q-018 retain
their current broader scope; subscriber/Live/provider/policy questions are later
assigned dependencies, not excuses for the current failing test.

Reviewer writes only this assigned report. Source manifest32 unchanged at final hash
verification; historical reports3 unchanged; no implementation/test/config/doc fixes,
staging, commit, push, PR, merge, fetch or new phase performed. Current task branch
remains intentionally dirty/uncommitted at the inspected base. Latest remote-main
integration and the clean committed pre-PR publication gate were not run because
publication is explicitly stopped.
