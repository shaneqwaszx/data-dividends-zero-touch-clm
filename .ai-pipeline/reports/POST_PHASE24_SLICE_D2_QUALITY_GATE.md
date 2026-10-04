# Slice D2 fresh-context independent quality gate

Date: 2026-10-03 (Asia/Singapore).
Result: **FAIL** for the frozen D2 candidate. One current high-risk required fix remains: D2-QG-001. Ordinary suites pass, but independently injected contradictory prior proof authorizes verified customer reuse in both memory and physical Mongo after restart. D2 is not accepted, publication is not ready, and D3/E/F/G must not begin.

## Independence, scope and reviewed identity

The owner explicitly requested a fresh-context independent D2 gate. This reviewer was dispatched with tool-selected model `gpt-6.1-sol`, reasoning `xhigh`, and `fork_turns=none`; the coordinator confirmed those exact dispatch arguments. There is no separate runtime model/effort self-attestation API. The coordinator's actual model/effort is not exposed and is not attested here. This reviewer did not implement or fix reviewed content and did not spawn another agent.

Worktree: C:/Users/shane/.codex-clean2/worktrees/post-phase24-stability-provider-hardening/data-dividends-zero-touch-clm.
Branch: feat/post-phase24-stability-provider-hardening.
BASE_SHA = HEAD = main = observed local origin/main: 707765b1d51172c64b851c9e46e68b3c23006789.
This is a local-ref observation; no fetch or remote-main freshness claim.

| Frozen identity | SHA256 |
|---|---|
| POST_PHASE24_SLICE_D2_CANDIDATE.json | 5c73533e60147e525b15fc02427dbf0df77f9b1cc184f002612fdf471be5089a |
| Complete 20-path reviewed aggregate | 2c05b15ba543358dd23df9576774573c90fc3d00a130acf469e70c6a5163cc04 |
| Exact D2-start delta artifact | 36df1211aa2203ca1a6e227462f92e78036719295ede2673aa1734d8616001dd |

The aggregate is SHA256 of UTF-8 concatenation of the lexicographically ordered manifest entries as `path + ' ' + sha256 + LF`. It was independently recomputed. All 20 final paths, all nine declared evidence receipts, and the delta artifact matched their frozen hashes before and after review. All 81 accepted before-images match their original hashes. The 75 untouched accepted paths, A/B/C candidate/gate anchors, and both D1 documents remain byte-exact. Six deliberate D2 overlaps are attributed to D2, not retroactively covered by earlier gates. The candidate manifest and this assigned report exclude themselves from the aggregate.

The complete reviewed path inventory is:

- .agents/skills/poc-regression-check/references/regression-catalogue.md
- .ai-pipeline/reports/POST_PHASE24_SLICE_D2_IMPLEMENTATION.md
- apps/backend/app/connectors/mock_goldtier.py
- apps/backend/app/persistence/repositories.py
- apps/backend/app/services/onboarding.py
- apps/backend/app/services/target_execution_repository.py
- apps/backend/tests/test_clm_orchestration.py
- apps/backend/tests/test_onboarding_resilience.py
- apps/backend/tests/test_phase06_provider_conformance.py
- apps/backend/tests/test_phase11_reconciliation.py
- apps/backend/tests/test_phase12_persistence.py
- apps/backend/tests/test_phase12_real_mongo.py
- apps/backend/tests/test_phase_07_uat.py
- apps/backend/tests/test_phase_08_input_driven.py
- apps/backend/tests/test_pre_phase12_workspace_multidoc.py
- apps/backend/tests/test_slice_d_mock_goldtier.py
- apps/backend/tests/test_slice_d_real_mongo.py
- apps/backend/tests/test_zero_touch_orchestration.py
- docs/ARCHITECTURE.md
- docs/PROJECT_STATE.md

The owner authorization attachment e514e920-2890-44b6-8fa0-d603397b922e/Pasted text.txt, AGENTS.md, quality-gate skill/template, reviewer/security roles, workflow, current owner map/state, D1 observation/preflight, planner D boundary, EDS contract, XPI mapping matrix, decisions D-015/D-018/D-024/D-033/D-061/D-063, ADR-006/007, persistence/recovery contract, owning source and changed tests were inspected. `dev_context.py` ran with BACKEND_DOMAIN, PERSISTENCE, EXTERNAL_PROVIDER and DOCS_ONLY. BACKEND_API was also assessed conservatively because progress consumers see READBACK; HTTP routes and DTO schemas are unchanged. The full D2 delta and task-owned new tests were inspected; the manifest was navigation evidence rather than a substitute for source review.

Current capability evidence: Python 3.12.10 from the existing project venv, local execution tools, installed Ruff/mypy/pytest, Docker server 29.8.1 and cached mongo:7.0 were available. The cached image ID was sha256:1b70d5bf141c2c93946a8f8e39f3f22a0a04a6d24e22cf47472b703856c715de. Browser/portal and external-provider activity were neither needed nor used. No dependencies were installed. Only the assigned gate report is a durable reviewer write.

## D2-QG-001 — P1: contradictory prior proof is accepted as verified reuse

Location: apps/backend/app/services/onboarding.py:425-462, `_find_verified_target_case`; invoked by initial bootstrap/recheck, canonical Search resolution, direct execution and incremental reuse guards.

The new guard checks FINALIZED, success labels, matching receipt/outcome party IDs, VERIFIED labels, completed READBACK and canonical name/registration/country. It does not bind receipt or outcome case/submission/correlation identities and fingerprints back to the immutable submission, nor require retained ledger progress IDs/readback facts to agree with the receipt/outcome and prior case. Consequently, internally contradictory evidence is sufficient to return the prior case and hydrate verified existing-target state.

Independent reproduction started from a real successful local Mock case, copied its finalized entry as ordinary model data, changed one proof fact, validated it with `GoldTierExecutionLedgerEntry.model_validate`, replaced it through the repository, then created a new identity-first case with the same synthetic identity. No source/test/fixture implementation was changed.

| Independently changed proof fact | Memory result | Strict Mongo write + reopened-store result |
|---|---|---|
| Receipt case_id replaced by another fresh UUID | EXACT_MATCH; existing_target_state hydrated | Same |
| Outcome submission_id replaced by another fresh UUID | EXACT_MATCH; existing_target_state hydrated | Same |
| Outcome input/idempotency fingerprints and receipt input fingerprint replaced by contradictory 64-character digests | EXACT_MATCH; existing_target_state hydrated | Same |
| Ledger resolved_party_id and ledger readback_party_id changed together to another safe synthetic ID, leaving outcome/receipt on the original ID | EXACT_MATCH; existing_target_state hydrated | Same |

These are accepted structured values, not invalid unchecked Python objects: all four pass the ledger model, Mongo repository replacement, complete strict envelope decode and store reopening. The persistence binding currently validates the enclosing submission-input case but does not reject these nested contradictions. The existing `_build_execution_receipt` checks immutable identity/fingerprints during original finalization; the new reuse read path bypasses those checks when consuming an already finalized row. Therefore a previously valid finalization does not prove that a subsequently read contradictory row remains trustworthy.

This violates the owner's same-identity/same-provider-ID/verified prior case plus ledger-proof criterion and the current persistence contract's nested case/submission identity agreement. The underlying permissive model existed before D2; D2 newly consumes those rows as sufficient authorization for verified Mock reuse. This is a current D2 defect, not accepted debt or a later sponsor question. It is not a claim that an unauthenticated UI endpoint can edit the ledger.

Required repair: within the existing owning boundary, reject prior proof whose case/submission/correlation IDs, recomputed immutable-input/idempotency fingerprints, provider mode, terminal classifications/states and retained party/readback progress disagree with the corresponding prior case, submission, outcome or receipt. Preserve strict historical compatibility, fail-closed reuse, current owner separation and no replay. Add meaningful negative regressions for each contradiction and physical restart decoding/consumption. Do not weaken validation or install fabricated prior success. The reviewer made no repair.

## Owner acceptance checklist

| Criterion | Result and evidence |
|---|---|
| 1. Existing deterministic NO_MATCH | PASS: new Mock tests and fresh execution preserve exact registration search and no broad/fuzzy match |
| 2. Configured accepted exact match | PASS for provider outcome; fixture candidates remain review-only without prior proof |
| 3. Accepted Shell identity fields only | PASS: accepted synthetic ID/name/country/role/type; registration absent until Policy |
| 4. Accepted Policy registration binding | PASS: ACRA external-system/key binding; technical POLICY_CREATED only |
| 5. No source_case_id-to-UEN inference | PASS: source inspection and explicit fake case-ID test |
| 6. Required successful Amend | PASS: mapper remains mandatory; successful order adds existing READBACK afterward |
| 7. Partial/validation Amend failure | PASS: required failure stops before readback/final success; no invented optional-field commitment |
| 8. Truthful local readback | PASS on ordinary and challenged returned fields; accepted optional projection semantics preserved |
| 9. Same-process readback | PASS: actual provider state and exact retained party ID through existing ledger |
| 10. Fresh connector/process loses state | PASS: fresh instance lacks runtime customers; no provider-state persistence claimed |
| 11. Ledger prevents replay after state loss | PASS: definitive-operation and uncertainty adverse tests, including fresh physical restart |
| 12. Seeded provider cannot establish prior verified case | PASS for seed-only, missing-ledger, incomplete/nonfinalized and stale-case controls; inconsistent proof remains D2-QG-001 |
| 13. Same identity requires existing resolver/ledger proof | FAIL: contradictory proof accepted by new guard, D2-QG-001 |
| 14. Different identity/customer cannot be reused | FAIL for inconsistent retained customer progress; ordinary different identity/current provider conflicts do stop |
| 15. Unsupported registration API query | PASS: EDS/XPI dialect separation and unchanged XPI rejection |
| 16. No portal task/RFA/audit fields | PASS: private customer state fields and complete source delta inspected |
| 17. No new HTTP/auth | PASS: local connector has neither transport nor authentication; operation tests forbid HTTP |
| 18. No Mock/Sandbox fallback | PASS: both retained-plan mode-drift tests ran in fresh CLM suite; composition unchanged |
| 19. No second persistence owner | PASS for ownership/schema/CAS; proof-consumption integrity fails under D2-QG-001 |
| 20. Setup/reset remains test-local | PASS: constructor fixtures/fresh instance and test-local helpers only; no runtime API |

## Explicit 14-risk challenge

| Owner risk | Independent disposition |
|---|---|
| Second workflow owner | Not found: connector dictionary/lock holds technical provider facts; service/ledger retain stages and finalization |
| Provider state treated as verified-case proof | Seed alone is rejected; contradictory case/ledger proof can still be trusted, D2-QG-001 |
| source_case_id-to-UEN fabrication | Not found: Shell does not parse source_case_id; Policy supplies accepted external key |
| False identity/customer reuse | Reproduced through inconsistent receipt/outcome/progress evidence, D2-QG-001 |
| Process restart/state loss | Ordinary loss fails Policy/Amend or readback; no fabricated success; fresh physical 28/28 |
| Uncertain-operation replay | Fresh connector/store uncertainty probes leave attempts unchanged and make zero subsequent calls |
| Policy approval mislabeling | Not found: POLICY_CREATED is technical; no KYC, regulatory, customer approval or RFA claim |
| Amend drift | Not found: Mock Amend stays required; D-063 optional XPI path remains separate |
| Portal fields entering contracts | Not found: D1 NO_MATCH supplies no new DTO/schema/query vocabulary |
| Hidden Sandbox assumptions | Not found in implemented delta: LOCAL/IN_PROCESS/NO_HTTP/NO_AUTH/PROCESS_LOCAL is explicit |
| Generic runtime seed/reset exposure | Not found: no new route/control/API; test helpers stay in tests |
| Mock/Sandbox fallback | Not found: mode checks fail closed; both drift directions executed |
| Persistence duplication | Not found: read-only list_for_case extends existing ledger repositories; no new schema/collection/owner; nested-proof integrity remains a required fix |
| Fixtures affecting runtime | Not found: current runtime constructor fixtures are explicitly synthetic; private test mutations and verified-case builders are confined to tests |

Fresh negative controls rejected missing ledger, missing receipt/nonfinalized state, stale prior case state, conflicting prior name, missing READBACK completion and failed receipt. Fresh readback probes for conflicting legal name, registration, country, legal form and address, a missing candidate, malformed status and invalid party ID all produced REVIEW_REQUIRED or FAILED rather than VERIFIED success. Existing comparison semantics allow omitted optional projection fields; this review does not invent a new Sandbox response requirement or claim that missing fields were returned/verified.

## Fresh independent execution

Ordinary backend execution used PYTHONDONTWRITEBYTECODE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 and worktree-only PYTHONPATH. Before pytest/application creation, Settings dotenv loading was disabled with `Settings.model_config['env_file']=None`; ordinary runs removed PHASE12_MONGO_URI. Pytest used `-q -p no:cacheprovider -p anyio.pytest_plugin --tb=line --show-capture=no --disable-warnings`. Non-loopback socket connections were blocked in focused and physical runs. Raw test output was captured in memory; retained output consists of counts, test IDs, status and sanitized probe facts. No .env or owner credentials were read.

| Fresh lane | Actual result |
|---|---|
| Focused + every changed ordinary consumer suite | 592 collected, 592 passed, 0 skips/failures |
| D2 physical + complete Phase12 physical | 28 collected, 28 passed, 0 skips/failures |
| Independent inconsistent-proof probes | Four memory + four strict Mongo/restart reproductions of D2-QG-001 |
| Additional prior-proof/readback negative controls | Required stops observed; no VERIFIED success on challenged conflicting/malformed fields |
| Root contracts | 44 passed, 0 skips/errors |
| Secret-scanner tests | 8 passed after narrow fixture-write permission retry |
| GoldTier synthetic example validator tests | 5 passed after same permission retry |
| Ruff app/tests; new connector/two new-test full-file format | All exit 0; no cache |
| Strict mypy backend app | Exit 0; temporary cache removed |
| Six governance/security scanners | check_secrets, check_project_state, check_architecture, check_policy_authority, check_external_provider_readiness and check_tooling_config all exit 0 |
| Tracked git diff --check | Exit 0; existing Windows EOL conversion notices only |
| Every final D2 path: UTF-8/replacement characters/trailing whitespace | 0 replacement characters; 0 trailing-whitespace lines, including new Markdown/tests |
| Supplementary Phase07 delivery assets | 4 run: 3 passed, 1 inherited failure; detailed below |

The 592-test invocation covered test_slice_d_mock_goldtier, test_phase24_identity, test_intelligence_evaluation, test_goldtier_xpi_sandbox, and all changed ordinary suites: CLM orchestration, zero-touch orchestration, onboarding resilience, Phase06 conformance, Phase11 reconciliation, Phase12 persistence, Phase07 UAT, Phase08 input-driven and pre-Phase12 multi-document workspace. Both mode-drift cases ran. The newly authored Mock suite contains 30 executed cases, not a permanent inventory constant.

Ordinary sandbox permissions initially denied creation of the two existing scanner/validator fixture directories, producing 8 and 5 setup errors. This was infrastructure permission failure, not a passing result or product defect. Each directory was verified absent before a narrow authorized escalated retry; 8/8 and 5/5 passed and both test-owned directories were absent afterward. Docker ordinary access was also unavailable; narrow scoped escalation enabled only the owned resource operations. No automatic approval review rejected an action.

### Independent physical resource proof

Reviewer container: clm-d2-qg-a08cb8c1906b, label codex.task=d2-qg-a08cb8c1906b. Container ID: bf62a562d02dc8184491a5a16450721943ab5b189e974855338a758e2d4351da.
A fresh free-port bind was checked before creation. Creation used cached mongo:7.0 with `--pull never`, bound only 127.0.0.1:27041 to container 27017. Only safe label/binding/mount/running metadata was inspected; Docker Config.Env/auth was not inspected.

Tests used the existing newly generated allowlisted clm_p12 database fixture. The extra contradictory-proof lane used another freshly generated clm_p12 database and the existing validated cleanup helper. No clm_poc or unrelated service/database was connected to, read, mutated or cleaned. No Mongo URI was printed or persisted. Ordinary physical tests passed 28/28, and the four custom contradictions persisted and reproduced after strict store reopening.

After testing: custom database absence verified; remaining allowlisted database count 0. Both anonymous volumes were verified exclusive to this labelled container before `docker rm -f -v` removed the owned container/volumes. Post-removal labelled-container count 0, both owned-volume counts 0, and a new loopback listener successfully bound/released port27041. The implementation's earlier container was not reused.

## Attributed broad evidence and precise provenance

The frozen receipts are implementer evidence, not independently rerun broad results:

- Full backend: 2023 collected, 1940 passed, 83 skipped; backend_final.json.
- Final focused: 181 passed; focused_final.json. This includes the subsequently strengthened missing-ledger test and both mode-drift cases.
- Physical: 28 passed, 0 skips; physical_final.json and removed-resource receipt. This reviewer separately executed 28 current tests and obtained its own cleanup evidence.
- Contracts44, scanner tests8, synthetic example tests5; root_checks_final.json.
- Frontend415 across35 files, typecheck/build, pip check/npm dependency integrity; frontend_final.json. No frontend source changed in D2; this reviewer did not rerun frontend/build/browser lanes.
- Ruff, strict mypy, format and six scanners; checks_final.json. This reviewer separately reran the current affected lanes.

The full backend and implementation physical runs preceded Python EOL-only/UTF-8 hygiene repair. hygiene_repair.json records production executable AST parity; that historical parity assertion is attributed rather than independently reconstructed from an unavailable pre-hygiene image. Current final source was exercised by this review's 592 tests and fresh physical28. The final missing-ledger assertion was strengthened later and covered in final181 and this review's fresh suite. Thus 1940/83 is not asserted as a full-backend execution on identical final file bytes. No stale, skipped or absent external evidence is promoted to PASS. After repair, rerun the affected full evidence appropriate to the new candidate and obtain fresh independent review.

## Inherited supplementary delivery-assets failure

Fresh root Phase07 delivery-assets execution reproduces one failure: `test_synthetic_document_pack_is_explicit_and_bounded`. Its historical exact PDF-name allowlist excludes garden-partnership-reviewed-client.pdf and multiple-owner-demo-client.pdf.

Independent comparison shows the test is unchanged versus HEAD after newline normalization, both PDFs exist in the accepted D2-start snapshot, and their exact bytes/hashes remain unchanged. baseline_audit.json is consistent with these direct observations. D2 neither created the extra assets nor changed the allowlist. This is inherited repository/CI debt, not D2-QG-001 and not a new D2 implementation defect. It is not silently waived: the current worktree is not blanket whole-tree CI/publication-ready. Its integration/publication disposition requires separately authorized, reviewed work; no unrelated asset/test repair was performed in this gate.

## Contract, architecture and security review

Implemented behavior is grounded in EXISTING_ACCEPTED_CONTRACT for accepted EDS requests/results/identity projection, registration binding and mandatory Mock Amend, and EXISTING_PROJECT_DECISION for bounded local storage, no fabricated prior proof, reuse/readback integration and ledger-owned restart/no replay. D1's sole synthetic Legal Name search returned NO_MATCH, opened no record and established no new API semantics. UNKNOWN/INFERENCE, portal filter/task/history/RFA vocabulary and confidential sponsor examples were not introduced into contracts or runtime fixtures. EDS and XPI DTOs/mappers retain their separate dialects; XPI registration query stays unsupported.

The new private connector state is bounded and lock-protected. It owns no CLM status, finalization, workflow queue, audit actor, retry/idempotency policy or durable provider history. Existing memory/Mongo ledger repositories expose defensive read-only list_for_case snapshots; physical reads preserve envelope revision/content. No new schema, collection, repository owner, route-to-Mongo access, fallback, dependency direction or ADR-sized replacement owner appears. Current mutations remain under the existing service/ledger/lock/CAS owners. D2-QG-001 is a trust failure in consuming retained evidence within that owner.

Policy success remains technical POLICY_CREATED and does not prove completed KYC, screening, approval, regulatory outcome or Ready-for-Approval. Mock Amend remains mandatory and its accepted partial/validation failures stop subsequent completion. No invented ANZSIC/group-company enrichment, unseen atomicity/retry rule or Sandbox authentication behavior was added. Capacity/collision/missing-customer failures are local safety controls rather than sponsor business limits.

The source/whitespace/scanner review found no newly tracked secret/confidential artifact within scanner coverage. No .env, portal session, cookie/storage/token/header, private sponsor payload or document body was accessed for this review. Existing tests generate local synthetic auth fixtures internally; their values were not retrieved or reported. External activity counts for this reviewer are zero: GoldTier Sandbox UI/API/mutation, Production, ACRA and other providers. Local Mongo activity is solely the explicitly owned disposable review resource.

## Change classification and limitations

- API/type: internal ledger protocol gains list_for_case; constructor-only Mock fixture/capacity parameters change. HTTP routes/request-response DTO schemas do not change.
- Schema: durable/admin versions, compatibility readers, indexes and CAS semantics do not change.
- Connector/runtime: bounded Mock facts, truthful missing-customer/collision guards, exact local readback, mandatory successful READBACK and reuse proof change.
- Configuration: settings, environment composition and provider selection do not change.
- Business rule/mapping: no sponsor business rule or mapping is added. Existing mapper/dialect and Amend requirements remain; local reuse is intended to enforce the owner's prior-proof boundary but fails D2-QG-001.
- Auth/security: no external authentication, role or access policy changes; retained-proof integrity has the current P1 defect described above.
- Architecture: existing owners remain; no second workflow/persistence/identity owner is introduced.
- Provider status: Mock remains PROJECT_OWNED / LOCAL / IN_PROCESS / NO_HTTP / NO_AUTH / PROCESS_LOCAL; Sandbox remains partial. No Live claim follows.

Process-local customer loss, bounded capacity and omitted optional projection fields are explicit limitations. These tests do not prove distributed exactly-once delivery, cross-process Mock customer persistence, actual Sandbox customer behavior, or production interoperability. Applicable Q-001/Q-006/Q-007/Q-008/Q-009/Q-010/Q-011/Q-018 dependencies remain separate later authority constraints and do not excuse the current local P1.

## Required fixes, readiness and Git status

Required current D2 fix: D2-QG-001 only. Bind/reject contradictory prior proof in the current owner, add focused and physical adverse regressions, rerun affected verification, freeze a new candidate, and obtain a fresh independent gate. This FAIL must remain preserved as the first frozen-round verdict. Do not reuse this report as a PASS after content changes.

D2 acceptance: blocked by the reproduced proof defect. D3/E/F/G readiness: not granted and not started. Real ACRA verification/GoldTier Sandbox or Production readiness: not established by this local gate. Publication: unauthorized and not ready; inherited delivery-assets failure is also unresolved. No pre_pr_check was run on this intentionally uncommitted implementation handoff.

Before the assigned report: 96 dirty paths (51 tracked modifications,45 untracked), index empty. After this report: one additional assigned untracked gate report; implementation bytes remain frozen. No source, tests, configuration, ordinary documentation, manifest or historical report was edited by the reviewer. Only necessary temporary test/cache/resource data was created and cleaned. No Git mutation, fetch, staging, commit, push, PR, merge or next-phase work occurred. Next authorized action is coordinator D2-only remediation of the finding, followed by new frozen independent review; this reviewer stops after reporting.
