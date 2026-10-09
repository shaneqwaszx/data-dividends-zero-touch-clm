# Synthetic company pack correction - fresh final independent Quality Gate

## Outcome

**PASS** for the exact frozen 33-path candidate below. All owner challenges A-H are
verified, QG-CORRECTION-01 is closed by the bounded assertion correction, and the clean
complete backend rerun has no failures. No required task fix remains. This is a fresh
assigned review and verdict; no earlier PASS or FAIL is transferred to amended content.

The candidate is ready to return for owner publication review. This gate authorizes
no staging, commit, push, PR, merge, or next phase. No new Live/provider approval claim
is made.

## Current, tested and reviewed identity

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/synthetic-happy-path-company-pack/data-dividends-zero-touch-clm`.
- Branch: `feat/synthetic-happy-path-company-pack`.
- HEAD, BASE_SHA, inspected origin/main and merge base:
  `21124498cb1b8fd47b1406534d6fd9c24af0e2ea`; ahead/behind 0/0.
- Current source is intentionally uncommitted. Commit HEAD alone is not its tested tree.
- Exact reviewed/tested final aggregate:
  `12cf9e2606161e7436d6b0bf105c4d8a5e8ba458e4343a52bce12fcd811d841c`.
  Algorithm: SHA256 of sorted path + NUL + raw-byte file SHA256 + LF.
  `SYNTHETIC_COMPANY_PACK_CORRECTION_MANIFEST.json` contains the complete33 paths and
  their raw-byte hashes. Every path was inspected. Independent path-set comparison
  proved these are every substantive tracked diff and task-owned new source/asset path,
  excluding derivative reports. Individual/aggregate hashes matched before and after
  decisive independent execution and immediately before this verdict.
- The earlier32 payload hashes are identical in this candidate. Its only additional
  change is `apps/backend/tests/test_slice_b_registry_demo.py`: preserve the exact
  minimized key-set assertion, include `synthetic_seed_namespace`, and assert `None`
  for an ordinary provider cache hit. No runtime edit occurred during remediation.
- The earlier correction FAIL report remains unchanged at SHA256
  `c0c65a9ecf1dd1d1bc0a8d3a2833770c4f3fc0f4e5294d6c13be83f4f7a95bbc`.
  Its old manifest is preserved as `CORRECTION_ATTEMPT1_MANIFEST.json`. The original
  superseded pack implementation/manifest/QG reports also retain their three hashes.
- Two additional Git-status files have only CRLF/LF differences and are independently
  equal to HEAD after EOL normalization: `apps/backend/app/connectors/mock_acra.py`
  (raw SHA256 `380842bf1cb41a2a37865f0929be71ec9d5c8ce944b0ba03266bdab040e5e00f`)
  and `apps/frontend/e2e/slice-b-registry-demo.e2e.ts`
  (`93d37e14c90b92fbd38e7c09e44091193fda8209a7bd8f6ca2d28595389c56ff`).
  They were inspected as context and have no substantive change.

Authority is the complete explicit owner correction, AGENTS.md, current source/tests,
ADR-010/D-069, registry freshness/persistence contracts, architecture/provider matrix,
workflow/change matrix and open questions. The scoped context selector and full
diagnostic were read. Applied fyp-quality-gate with integration-security and POC
regression review. Affected classes are BACKEND_DOMAIN, BACKEND_API, PERSISTENCE,
FRONTEND_UI and CI_TOOLING; owner reuse and retirement were also independently reviewed.

## Owner acceptance A-H

| Challenge | Result and decisive evidence |
|---|---|
| A. Actual api_marketplace_mock stays configured | PASS. Normal create_app builds the official Marketplace connector/router/coordinator. The runtime API reports API_MARKETPLACE_MOCK and the real browser retains the configured Marketplace banner. Normal composition and defaults were not replaced by MockAcraConnector. |
| B. Fresh new company makes zero Marketplace token/HTTP calls | PASS. Four fresh API journeys, four physical normal-runtime/restart journeys and four fresh browser journeys. Only default token/HTTP factories are patched. The BaseException transport guard escapes ordinary connector sanitization, so any attempted request fails the test immediately. Token/entity/officer/shareholder requests are all absent. |
| C. CACHE_HIT is LOCAL_SYNTHETIC_UAT_V1 | PASS. All eight seeds use local_synthetic_registry_identity, exact UEN and COMPLETE four-operation evidence. Retained case binding, original timestamps and LOCAL_SYNTHETIC_SEED references are asserted. Physical round-trip preserves full bundle/microseconds; the adjacent official namespace is empty. |
| D. Unseeded/expired uses actual configured fallback | PASS. Unseeded eligible202400018R and expired Orion reach TOKEN then ENTITY_PROFILE through the composed Marketplace connector and return safe ACRA_ENTITY_NOT_FOUND without local seed evidence. Existing incomplete/mismatched/expired/corrupt controls preserve fallback or fail-closed behavior without mixing namespaces. |
| E. No provenance relabelled as official | PASS. Configured provider and actual evidence are separate. The allowlisted nullable browser label requires full retained approved identity equality; original local references remain visible. Eight fresh independent projection probes reject adjacent/forged classification and arbitrary namespaces. Ordinary cache hits explicitly project None. |
| F. All four new full journeys | PASS. Exact Decimal results and provisional candidates, four matching identity fields, accepted current document evidence, ANALYZED ownership and no evidence blockers. Classification stays explicit and Review & Send is required before any target mutation. COMPLETED/SUBMISSION_CONFIRMED and exact-ID readback follow confirmation; repeated read/reopen and Mongo restart do not replay target or Marketplace calls. |
| G. Alpha/Beta/Gamma/Delta preserved | PASS. All four fresh actual Marketplace-composition journeys complete through the same owner with zero requests. Full normalized snapshots independently match accepted baseline4/4; existing physical cases and scanned fixtures passed on byte-identical owners. |
| H. No direct Mongo/orchestrator shortcut | PASS. Data definitions feed existing HappyPathCompany and seed manager/snapshot repository. No direct BSON writer, second cache/provider/store, UEN-specific orchestrator branching or ordinary application-start automatic seeding. Existing Decimal engine and target ledger remain sole owners. |

Expected new ownership evidence remains unchanged: Orion70/30 direct; Pacific40/35/25
direct with inclusive25% candidate; Straits48/40/12 effective (48 and40 qualify);
Meridian30/20/30/20 effective (the two30 interests qualify). Direct/indirect components
and all names are asserted exactly, not inferred from browser rendering. Seeded officers
remain separate from owners. These are fictional POC graphs, not legal UBO findings.

Warm/check uses the existing manager for8 fixtures: preflight all known keys, insert-only
create, fresh idempotence, exclusive expiry and expected-revision CAS refresh/conflict.
Actual CLI creates8, rerun creates0 and read-only check finds8. Unsafe/protected database
names and production are rejected before connection. No index initialization occurs
on check. The four relocated native-text PDFs retain their historical raw-byte hashes
and deterministic one-page identity-only content; no quantitative ownership is embedded.
Operator instructions retain api_marketplace_mock/mongo/auto and the same warmed
dedicated database with privately provisioned credentials.

## Fresh independent execution on final33

All Python runs used BOTH the task root and task apps/backend on PYTHONPATH, with the
shared provisioned Python executable. Ordinary test conftest disables dotenv and
provisions runtime-only synthetic authentication. No primary-checkout result is used
as candidate evidence. Counts below are per run and are not summed as unique tests.

| Direct reviewer command / probe | Result |
|---|---|
| pytest -p no:cacheprovider -o addopts='' on test_synthetic_company_pack, its real_mongo suite, test_slice_b_registry_demo and test_evidence_workbench_registry_projection | **38 collected/executed PASS,0skips**,38.98s: pack17, new physical5, full SliceB10, projection6. This includes QG-CORRECTION-01's exact field assertion and explicit None. |
| run_e2e.py --registry-demo synthetic-seed --grep 'Synthetic company pack' --backend-port 8825 --frontend-port 4225 --timeout-seconds 240 | **4/4 PASS**,29.2s; actual local HTTP/processes and Mongo; network-policy violations0; disposable database cleanup VERIFIED. CLM_E2E_SYNTHETIC_MONGO_PORT was privately set to the reserved27149. |
| Exact inherited local HTTP seeder node, no cache provider, --tb=short | **1/1 PASS**,7.56s. |
| Inline projection falsification, no source writes | **8 PASS**: exact approved identity labelled; mismatched provider/contract/three namespaces not labelled; non-Mock identity fails closed; arbitrary browser namespace rejected. |
| Complete substantive diff/new-file set vs manifest; raw hashes before/after | All33 covered and unchanged. Earlier32 byte identities, prior correction FAIL and historical reports preserved. |
| git diff --check and explicit whitespace check over every frozen text path | PASS. Only ordinary EOL conversion warnings; staged diff empty. |

Earlier direct reviewer executions on the verified byte-identical32 portion remain
precisely identified as execution evidence, not inherited verdict: focused63 PASS/0skip
(including existing physical6 and owner/adverse29); document/assets21 PASS/0skip;
provenance UI17 PASS; baseline full normalized fixture equality4/4; historical PDF
raw-byte equality4/4; architecture/project-state/secrets/policy-authority/external-provider
checks PASS. Their owning files are unchanged in final33, and fresh decisive A-H
execution above supplements that evidence.

## Complete broader verification and failure history

Coordinator-supplied final evidence is separately attributed; these commands are not
falsely described as reviewer executions:

- Clean **FINAL33 full backend**:2712 collected; **2574 passed,138 conditional skipped,
  0failed,4 inherited warnings**,938.74s. Exact task backend source/import paths were
  selected. The unchanged HTTP seeder passed within this run in6.76s.
- Required guarded physical Mongo:20 configured suites;132 collected/executed PASS;
  0skips/failures/errors. Includes actual8-record CLI/idempotence/check, all new normal
  Marketplace Mongo completion/restart/no-replay and existing four durable cases.
- Frontend47files/562tests PASS; typecheck/build/dependency integrity PASS. Relevant
  runtime/frontend bytes are identical to final33. Existing React test warnings and
  build chunk-size warning remain; dependencies/lockfile unchanged.
- Final backend Ruff PASS; mypy126 source files PASS; changed tooling/script Ruff PASS.
  Contracts44 PASS; governance/security/tooling159 PASS and extra security/governance152
  PASS; final focused73 PASS and post-remediation focused33 PASS. Inherited browser1
  PASS; fresh reviewer browser4 is independently recorded above.
- Project state, architecture, tooling policy, policy authority, external-provider
  readiness, secret scanner and pip check PASS. The scanner covers supported bounded
  secret patterns, not universal absence of every possible confidential value.

The138 ordinary broad skips are132 physical cases exercised in the separate zero-skip
physical lane, plus6 broader real-OCR variants gated by Tesseract on PATH. Those six
are not counted as passing and are outside this native-text pack's changed surface.
The existing four scanned database fixtures executed with their explicit installed
Tesseract path and passed. No required current correction claim depends on an unexecuted
variant or an external smoke test.

The old32 broad attempt is retained as failed diagnostic evidence:2failed,2572passed,
138skipped,4warnings,979.23s. Its stale seven-field assertion was independently
reproduced and caused the earlier FAIL; the two-line remediation now passes both
focused and complete final regression. Its other failure was a socket TimeoutError
reading local target-confirmation HTTP in unchanged seed_phase13_demo.py:181, also
seen in an isolated coordinator attempt. The earlier entire demo suite11 passed;
the accepted baseline exact node passed7.58s; fresh reviewer exact node passed7.56s;
and the final full run passed it6.76s. This establishes intermittent execution behavior,
not a proven load cause or deterministic correction defect. No timeout increase,
implementation change or test suppression was used. A mistaken initial primary-source
import run was discarded and provides no acceptance evidence.

## Architecture, security and findings

No open current defect or required fix remains. QG-CORRECTION-01 is closed by fresh
execution of the exact minimized response contract. The final gate is independent of
the implementer; reviewer made no source/test fixes and changed no acceptance criterion.

Existing owners are sufficient: immutable data definitions feed the existing fixture
bundle/snapshot owner; the existing repository/coordinator preserves strict identity,
frozen policy, CAS, COMPLETE-only binding and configured-provider fallback. No new ADR,
cache owner, provider, persistence owner, source precedence or target bypass is needed.
Batch warm remains non-transactional across keys and single-process POC guarantees
remain explicit. Strict schema10/legacy compatibility, cache schema1/2, codecs/indexes,
insert/update separation, deletion safety and target recovery are unchanged.

API/type and UI change additively through nullable allowlisted synthetic_seed_namespace
and truthful local evidence copy. Durable schemas/persistence formats are unchanged.
Runtime fixture availability changes: four new UENs use existing approved local database
evidence under ordinary Marketplace configuration. Connector implementation/composition,
normal configuration authority, business rules/thresholds, mappings, auth/security
policy, canonical architecture owners, provider statuses and target sequencing remain
unchanged. Isolated E2E adds the reserved-port/seed fixture; CI budget becomes234minutes
for73 discovered lifecycles. No dependency or lockfile change.

The new label exposes no private cache key/revision/fingerprint, arbitrary namespace,
endpoint, contract identifier or raw data. Existing authorized case routes, private
binding validation and safe inaccessible-case404 are retained. Test guard and count
endpoint exist only in the isolated E2E server; normal application startup never seeds.
Only fictional identities and generated identity documents are added. PDFs contain
no ownership quantities, and officers are not promoted to owners.

Physical/browser checks used freshly generated allowlisted clm_p16 databases on the
owned isolated Mongo port27149 and verified cleanup. The coordinator subsequently
verified disposable databases absent and released only its exact owned container.
Reviewer did not stop containers or touch shared services. No .env, protected clm_poc,
credentials/URI output, real KYC/PII, raw provider payload or confidential sponsor
artefact was accessed or added. The remaining source/evidence files were inspected for
hygiene; no new secret material was found by the supported checks.

## Readiness and Git handoff

The corrected bounded pack is accepted for owner publication review on the exact33
identity. No next phase is assigned. No real ACRA/GoldTier readiness is promoted by
this gate: configured Marketplace is MOCK, seed is LOCAL PROJECT SYNTHETIC MOCK,
extraction and Decimal ownership are LOCAL, and exercised target delivery is Mock
GoldTier. Subscriber/Live access, legal/control UBO, production policy, KYC completion,
GoldTier-internal/regulatory approval and Ready-for-Approval remain separate unproved
capabilities. Q-001..Q-018 retain their broader current scopes and later assigned
sponsor dependencies.

Reviewer wrote only this assigned FINAL report. Branch/HEAD/origin-main remain as
recorded, with uncommitted reviewed task changes and unstaged derivative reports.
No implementation/test/config/document fixes, staging, commit, push, PR, merge, fetch
or next phase occurred. The original FAIL/report/manifest remain historical evidence.
Latest remote-main integration and the clean committed pre-PR publication gate were
not run: publication is explicitly stopped and requires separate owner authorization.
Any subsequent reviewed-content change requires a new exact independent review.
