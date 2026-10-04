# Session 3 independent pre-mutation gate

PRE_MUTATION: FAIL

Prepared on 2026-10-04 (Asia/Singapore) by the independent GPT-6.1 Sol xhigh reviewer. One required P2 test/evidence correction remains: the complete backend suite fails its stale route-inventory totals after the deliberately classified status-check route was added. The held external SEND must remain stopped pending bounded remediation, current checks and a fresh independent gate. It is not Session 3 final acceptance, a combined program PASS, proof of successful external writes, or Live readiness.

## Reviewed identity and independence

- Worktree: C:/Users/shane/.codex-clean2/worktrees/onboarding-intelligence-goldtier-sandbox/data-dividends-zero-touch-clm.
- Branch: feat/onboarding-intelligence-goldtier-sandbox.
- BASE_SHA = HEAD = cached origin/main: 1d426e0ceddc32d80b0aaec293c62fb761f2fecf; staged files: zero. No fetch or Git mutation occurred.
- Frozen candidate: db21e640e845a1807a0fe470d824059ee5132dba3772b4e7e694f36e2fbdf5ed.
- Manifest raw SHA256: 3c2a97b9023b3107db812491ba1ba0e3233d370f1b67039a6c99bae77a00fb4d.
- Complete reviewed pathset: 168 paths, 116 tracked changes and 52 task-owned new files. Every raw file SHA256 and the exact complete Git changed/untracked pathset were independently verified at entry, before this report and after writing it.
- S3 manifest format is a path-to-raw-SHA256 mapping. Aggregate calculation is SHA256 of UTF-8 json.dumps(files, sort_keys=True, separators=(',', ':')); relative paths are case-sensitive POSIX paths. This is distinct from the S2 record-array manifest algorithm.
- Immutable preparation receipt raw SHA256: 07093e722acc3a25e04501adde8f633ecf44038b90d6586ad6eaf7de510e7628.
- Exact accepted S1 gate SHA256: 813c495bdca13531204b4ed8e8f054c3855952fc4f9ba0ce13038ce398b202e4.
- Exact accepted S2 round1 gate SHA256: f3460459000d73e69cb4d0d465efd404d92ee8d01b2e1f73cc6884c82b5fd608. Original S2 FAIL/P2-01 and bounded round1 correction/history remain intact.
- S2 round1 manifest raw SHA256: 3d68243df62e37fdd425bccb1b75fc1cc8ab86fce4faffea633e3ffd59d9337d.
- Against the accepted S2 manifest, 131 earlier reviewed paths retain identical bytes, 16 existing paths change and 21 additional paths enter the current freeze. This same reviewer previously reviewed the unchanged cumulative S1/S2 source and freshly reviewed every S3 delta and new file.
- The manifest itself, this gate and the designated future S3 external receipt are the three excluded outputs. The immutable preparation receipt, implementation report, local evidence and both accepted gates are included in the freeze.
- The reviewer implemented no candidate content and wrote only this report. No private configuration, raw sponsor artifact, provider payload, original database or external service was inspected or called.

Controlling context: owner's three-session request, S3.1-S3.16/global/hard safety; AGENTS.md and backend/frontend extensions; current workflow/dev_context selector; fyp-quality-gate and report template; integration-security-review/checklist and triggered provider/cache/persistence workflows; current planner; D-055/D-056/D-057/D-062/D-063; XPI mapping/reconciliation and current readiness contract. Historical EDS Mock rules are not substituted into XPI.

## Requirement assessment

Results below assess the pre-mutation prerequisite and implementation boundary. Actual external outcomes remain pending.

| Requirement | Pre-mutation result | Direct evidence |
| --- | --- | --- |
| S3.1 Configuration | PASS | Mock stays default. Explicit Sandbox normal composition; backend-only SecretStr configuration; exact authorized HTTPS origin/environment guard; only three named XPI fields consumed; duplicate/missing configuration fails safely; preparation presence flags verified without reading private values. |
| S3.2 HR console | PASS | Current diagnostic router uses composed onboarding/XPI Search, safe candidate projection and HR capability. Six console tests plus independent authenticated normal-composition HR Search 200/NO_MATCH; standalone write 409 and onboarder 403 with zero extra calls. |
| S3.3 Case-bound Sandbox destination | PASS | Normal create_app forwards the existing optional transport port. Existing canonical mapper, case confirmation, lock/CAS and durable target ledger own Search -> eligible Shell -> required Policy -> conditional Amend -> exact-ID readback. No alternate execution owner or fallback. |
| S3.4 Final local approval/status | PASS | Backend projection distinguishes not submitted, sending, confirmed, failed, uncertain and finalization pending. Confirmed Sandbox requires successful retained outcome/receipt, required readback and application completion. Frozen Review & Send remains visible; no second local approval. |
| S3.5 Complete field inventory | PASS | Independently parsed 226 substantive inventory rows with all 13 requested columns, plus the separate 23-scalar exact prepared table. Current DTO, mapper, source, provenance, optional/null/unmapped and blocking distinctions inspected. Placeholders are preview descriptors only. |
| S3.6 Business sources | PASS | Canonical business fields retain case-owned registry/document/reconciliation lineage; integration values remain explicit frozen policy; application UUID/key bindings are separate from provider IDs. Current extraction does not invent contact, group-company, industry or RP enrichment. |
| S3.7 Search | PASS | Strict four-alias query DTO; no UEN/registration query; bounded name+country initial Search and retained-ID readback. Existing resolver/currentness checks reject non-exact or ambiguous reuse. Preparation retains one HTTP200 NO_MATCH. |
| S3.8 Customer creation | PASS | Strict frozen Shell request, safe bounded response decoder and returned customer-ID binding. Malformed/timeout/ambiguous/unconfirmed mutation result retains uncertainty and stops dependent calls/no replay. |
| S3.9 Policy | PASS | Required current Policy request bound to actual retained customer ID; technical status never claims KYC/approval/RFA. Missing optional Policy ID remains absent; actual supplied ID must be retained when returned. |
| S3.10 Amend/history | PASS | Current builder has no supported reviewed enrichment, preview omits Amend and existing ledger records AMEND_NOT_REQUIRED. Acceptance guard refuses Amend. Historical Garden uncertainty/failed KYC Edit Pool evidence and recovery remain separate. |
| S3.11 Related parties | PASS | Child lifecycle and relationship authority remain unsupported; local ownership/UBO evidence retained. No fake child ID, RP dispatch or external RP-success claim; current parent contract does not establish mandatory RP. |
| S3.12 Original documents | PASS | Current six-operation contract exposes no original-document upload API. Inventory/runbook distinguish structured business-field submission from original-file transfer. No invented upload operation. |
| S3.13 Uncertainty/no replay UX | PASS | One automatic read-only observation per session/user/case/submission; AbortSignal and generation checks reject late scope responses; no automatic mutation/resume/retry. Customer identity observation cannot resolve uncertain Policy or alter retained ledger. Independent verified recovery remains the existing owner. |
| S3.14 Bounded mutation authorization | HOLD: P2-01 | S1/S2 exact gates and current local evidence verified; immutable valid package and synthetic-only identity verified; on-disk reservation before provider access; guard reserves Search<=2, Shell<=1, Policy<=1 and readback<=2 before calls. The runner release additionally requires a fresh exact passing gate; this failed candidate is not released. |
| S3.15 Synthetic case | PASS | Unique ZERO TOUCH POC ACCEPTANCE 9CD9A457 / 202655266Z / case74af14cb-c691-485a-bfc0-ca89de40dc65; explicitly Mock synthetic registry source, not a real registered business. Reviewed document, creator-reviewed explicit70/30 evidence and sole Decimal engine analyzed both candidates. |
| S3.16 Actual acceptance | PENDING EXTERNAL EXECUTION | This pre-mutation verdict permits the bounded attempt; it does not satisfy final actual-Sandbox acceptance. Actual customer/Policy outcomes, provider ID and readback, final truthful state and retained restart evidence remain to be obtained or classified EXTERNAL_DEPENDENCY_BLOCKED. |

## Independent executed verification

All checks below exercised the current frozen S3 bytes, rather than borrowing previous-session results.

| Check | Command or independent method | Result |
| --- | --- | --- |
| Target contract/status/budget/preview | python -B -m pytest apps/backend/tests/test_s3_acceptance_safety.py apps/backend/tests/test_s3_submission_status.py apps/backend/tests/test_s3_target_activity.py apps/backend/tests/test_s3_submission_preview.py apps/backend/tests/test_goldtier_xpi_sandbox.py -q -p no:cacheprovider -o addopts= | 122 passed, zero skips, 5.91s; one existing Starlette/httpx deprecation warning. |
| HR diagnostics | Same pytest flags, test_provider_sandbox_api.py | Six passed, zero skips, 0.25s; same existing warning. |
| Required route inventory | Same pytest flags, test_phase13_auth_rbac.py::test_every_current_application_route_is_deliberately_classified | One FAILED in1.11s: expected81 versus actual82. Exact application/policy equality passed before this assertion. |
| Frontend state and review | npm test -- --run src/pages/S3SubmissionStatus.test.tsx src/pages/ReviewAndSend.test.tsx | 42 passed / two files; 2.14s; no skips. |
| Offline harness/tooling | Same pytest flags, tests/test_run_e2e.py tests/test_run_physical_mongo_tests.py | 60 passed, zero skips, 4.21s. No real browser/physical runtime was launched. |
| Contracts/quarantine | python -B -m unittest discover -s tests/contract -p test_*.py | 44 passed; 1.582s. |
| Ruff | Backend cwd: python -B -m ruff check --no-cache app tests; root cwd: corresponding scripts tests | Both PASS with owning configurations. |
| Strict mypy | Backend cwd: python -B -m mypy app --no-incremental --cache-dir=nul | PASS: no issues in 124 source files. |
| Governance/security | check_secrets.py, check_architecture.py, check_project_state.py, check_external_provider_readiness.py, check_policy_authority.py, check_tooling_config.py | All six PASS. No secret pattern output or private-file read. |
| Complete task hygiene | Explicit raw-text scan of all168 paths, including untracked content, plus git diff --check | Trailing whitespace PASS168; Markdown final newline PASS28; diff check PASS. Machine JSON without final newline is valid and is not misclassified as a Markdown whitespace defect. |
| Prepared package/local proof | Independent receipt/model assertions and raw hashes | All442 local-proof files match current bytes. Document REVIEWED, ownership ANALYZED, two70/30 candidates, both MATCH/REVIEWED proposal decisions, CURRENT_EVIDENCE receipt, Sandbox/valid preview, all23 actual preview scalars match prepared matrix. SEARCH1/HTTP200; other operation counts0. |

Independent adverse execution additionally used a delegate that cannot access a network or database. Fourteen attempted unauthorized-origin/query/method/RP, changed-preview, post-uncertainty and over-budget requests were blocked before any extra delegate call. Policy timeout retained one Shell and one Policy attempt, stopped every subsequent write and permitted only two retained-ID observations. The production Httpx transport was instantiated against a mocked client: SSLContext enforced TLS1.3 minimum/maximum, CERT_REQUIRED and hostname verification; redirects disabled and timeout supplied. This verifies construction, not a new real TLS handshake.

An additional authenticated TestClient used normal explicit Sandbox composition, synthetic ephemeral credentials, in-memory repositories and an offline delegate. HR Search succeeded with one GET; standalone write409 and onboarder Search403 produced no extra delegate call. No secret/credential value was printed or persisted.

Frontend execution independently covers all six backend states, uncertain Policy remaining uncertain after customer observation, disabled frozen edits/confirm/retry, no check for definitive/finalizing/sending states, exactly one automatic check over rerender/remount/StrictMode, explicit user-triggered read-only check, actor/case/submission/logout cancellation, stale-response rejection and inaccessible-case containment.

Early reviewer read invocations used a nonexistent guessed template/ADR filename; actual skill-indicated/discovered files were then read. Initial custom assertions assumed wrong discrepancy-key/table-subsection shapes; corrected assertions against the current DTO and separate prepared table passed. These were reviewer invocation errors, not candidate failures or silently passing evidence. No candidate was edited.

## Reviewed implementation evidence and limits

The implementer's current S3 report and local evidence supply: 189 focused tests, guarded physical112/112 across16 suites with zero skips/cleanup, frontend500/41 files plus typecheck/build, three genuine offline Sandbox browser journeys under the original60s lifecycle guard, strict mypy124, Ruff, contracts44 and scanners. Their test/source identity is backed by all442 current local-proof hashes. The reviewer inspected the physical restart and browser test bodies, including exact target/document/ownership retention, stale confirmation409, zero new provider calls, frozen review visibility, customer-vs-Policy distinction, and widths320/720/1280. These counts are implementer execution evidence, not independently rerun browser/physical claims.

The reviewer deliberately did not mutate a physical database, start a browser lifecycle or duplicate the full backend while the held acceptance and coordinator's complete final backend lane owned those resources. The coordinator's complete current backend finished during review: 2276 PASS / 1 FAIL / 118 opt-in SKIP, 847.63s. The sole failure is P2-01 below, independently reproduced. This full run is FAILED, never presented as a passing suite. Complete final program/browser/lifecycle/external acceptance and cleanup/final combined gate remain separate requirements. Earlier Windows complete29-pass/2-deadline-failure plus two unchanged focused passes remain historical coverage, never a fresh whole31 PASS. Prior OCR/browser/full-front evidence remains attributed to its original recorded bytes and sessions.

## Contract, architecture and security findings

No P0/P1 production safety or authorization defect was reproduced. One P2 required test/evidence correction was independently reproduced:

- The target port, mapper, policy snapshot, canonical evidence, authorization/case lock, schema9 envelope and durable target execution ledger retain their existing owners. S3's volatile active-submission set explains active sending without becoming a durable replay authority.
- Read-only status check accepts only the expected retained submission UUID; route-policy authentication/CSRF/case scope and fresh lock-bound reauthorization apply. Provider composition drift, frozen identity drift, stale UUID and inaccessible actor fail before Search. Results neither adopt a discovered ID nor rewrite/finalize/resume the uncertain ledger.
- Sandbox response projection and errors are bounded safe identifiers/fixed summaries. Payload/credential/header/exception text does not enter normal history/browser reports. Private XPI configuration is consumed only by the owner-authorized runner; this reviewer did not read it.
- Before SEND, the harness checks the accepted gates, exact local files and the frozen manifest/report identity. The real guard validates origin/environment, synthetic query identity, exact reviewed Shell payload and bound Policy fields; reserves operations before execution; rejects unapproved mutations, broad enumeration, RP/Amend/delete and replay.
- HTTPS/TLS1.3 verification, no redirects, bounded response retention/timeouts, explicit write opt-in and uncertainty stopping remain mandatory. No production-authentication or OS/container-security guarantee is inferred from offline execution.
- Current D-055 optional-empty account/product semantics, D-056 Singapore values and D-057 case-selected vocabulary remain distinct from unresolved production authority. D-062 final local review/inclusive25% and D-063 conditional Amend apply without rewriting history.
- Source review includes all S3 cumulative-diff changes and task-owned new files. Unchanged S1/S2 content keeps its exact historical independent review identity; it is not used as newly executed S3 behavioral evidence.

Current limitation: the reserved external identity has only a NO_MATCH Search observation. No customer, Policy, Amend or readback success has occurred. Later dependencies remain production/PingFed authentication, Live ACRA, complete legal/controller or screening authority, related-party child lifecycle/relationship mappings, original-file transfer and provider-internal approval. None is silently turned into a current parent prerequisite or success claim.

## Required fixes

P2-01 - Update the deliberately classified route inventory for the new status check.

Evidence: apps/backend/tests/test_phase13_auth_rbac.py:1160 still requires81 total routes and line1166 still requires41 CASE_SCOPED routes. The current exact application-vs-policy inventory equality at line1159 passes; policy inventory independently contains82 total /42 CASE_SCOPED, with exactly one POST /api/clm/zero-touch/cases/{case_id}/target-status-check classified CASE_SCOPED in services/authorization.py. The complete current backend run fails this assertion. Reviewer focused reproduction: one failed in1.11s with the same82 !=81 assertion, zero provider/database calls. This is a stale acceptance-test inventory, not evidence of an unclassified or unauthorized production route.

Correction: update expected totals to82 and CASE_SCOPED42; add an explicit assertion for the new POST status-check route's CASE_SCOPED classification. Retain the exact actual==expected invariant, all other expected access counts and the unclassified-included-router rejection test. Do not remove the count checks, loosen authorization or alter product/package/harness semantics to hide the failure.

Verification: rerun the owning route-inventory/auth tests and current complete backend, relevant contract/security checks, record truthful counts/skips, freeze a new candidate including the changed test and obtain fresh independent review before SEND. The immutable preparation may remain unchanged if the correction affects only test expectations. Archive the initial failed report/manifest byte-exact; this gate does not authorize remediation writes by the reviewer.

Do not create another synthetic identity if the attempt rejects or becomes uncertain. Preserve the reservation and retained operation evidence. Any candidate/source/preparation change requires a fresh independent review before mutation.

## Readiness and next authorized action

Mutation authorization readiness: NOT RELEASED on this failed R0 candidate. The coordinator must perform only the bounded P2-01 remediation, rerun checks, freeze new content and request a fresh independent review. The held runner remains before writes. An eventual passing reviewed release still requires the normal authenticated final confirmation to validate expected automation/CLM/event versions and compute its server review digest before ledger-owned writes.

Operation ceilings for an eventual separately passing release: at most one additional initial Search, one Shell and one required Policy; Amend zero for this package; at most two bounded readback/status observations. A second Search that becomes non-NO_MATCH must not authorize Shell. Rejection/uncertainty stops writes and retains sanitized evidence. The coordinator must classify actual provider results without modifying the product merely to force success.

Session3 final acceptance: NOT YET VERIFIED. Final combined program gate: NOT YET RUN. External customer/Policy/readback success: NOT YET OBSERVED. Provider classification remains SANDBOX_PARTIAL, never Live. No publication or Git mutation is authorized by this verdict. Reviewer runtime ownership is released; the coordinator's held runner and full backend processes were preserved.

## Git/write boundary and content ledger

Only ONBOARDING_INTELLIGENCE_S3_PRE_MUTATION_GATE.md was written by the reviewer. No implementation, test, configuration, ordinary documentation, manifest, accepted report, private file, database or provider was changed; no commit/push/PR/merge or additional-phase work occurred. Final after-report verification reconfirmed raw manifest/preparation/accepted-gate identities, all168 candidate hashes, aggregate, complete pathset, branch/baseline and empty staged state.

The following complete path-to-raw-hash ledger is the independently verified frozen set, copied without changing the source manifest.


| Reviewed path | Raw SHA256 |
| --- | --- |
| .ai-pipeline/001_planner/ONBOARDING_INTELLIGENCE_GOLDTIER_SANDBOX_PLAN.md | 509ce2ed7d5eb8de7d09c161d87cd02a1d19a455b8c889a529acf0eace1595f7 |
| .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S1_IMPLEMENTATION.md | f86e8c7f6d73d44f56fbf7d63b0969c29c1e9edc95e20aa63ced7b405756f4fc |
| .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S1_MANIFEST.json | a45c8f84978c55be2785ed9578c4dbd4f60863b83a7431c7e883a1cfb6d947c9 |
| .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S1_QUALITY_GATE.md | 813c495bdca13531204b4ed8e8f054c3855952fc4f9ba0ce13038ce398b202e4 |
| .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S2_IMPLEMENTATION.md | 3beca381afb1b3a1b4a62ca17bc99f3d7dbca1821a7a07842f516f873c0b8826 |
| .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S2_MANIFEST.json | 3d68243df62e37fdd425bccb1b75fc1cc8ab86fce4faffea633e3ffd59d9337d |
| .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S2_OCR_BROWSER_RECEIPT.md | d942fce0b0aee5498f6645df47208046607d0a2b9c90caab3a2d9439fa439088 |
| .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S2_QUALITY_GATE.md | f3460459000d73e69cb4d0d465efd404d92ee8d01b2e1f73cc6884c82b5fd608 |
| .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S2_R0_MANIFEST.json | 4926880658ea26447c433b8594fc5d3807aa11bac4daf71e2e9d531031f6a23d |
| .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S2_R0_QUALITY_GATE.md | b679b042274855429d17c9c4bd1b30e6e17e3aae388525d2d851a2f907f740c7 |
| .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S2_REMEDIATION_R1.md | 204a2a2c05399e705f3db0dd46b2bd624c67209f9d1b94d93f149200ee2bf740 |
| .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S3_IMPLEMENTATION.md | fb5269dd5d13e9dbeca012c14de1e75c10a2c5c999f9c6fc101708abd6d81b49 |
| .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S3_LOCAL_CHECKS.json | 1838dedbae2ab9fc655a34f49536b093622b2486c69b436cd83642df77289e6c |
| .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S3_PREPARATION_RECEIPT.json | 07093e722acc3a25e04501adde8f633ecf44038b90d6586ad6eaf7de510e7628 |
| .github/workflows/ci.yml | 851b6e74962b5d102630c90b5fe96ad2651d8cab804ea908491dbb616b7a1574 |
| apps/backend/app/api_auth.py | 73f91f09bef7d589f80581e24a29063477b1fda81ead7aef2331d9eebfdd3649 |
| apps/backend/app/api_models.py | adfeff8a8c96800b92a929edde3ffebc015bbb7e99e252220f213112b804fc39 |
| apps/backend/app/api_policies.py | 57da796d89b179b8c2fcd5f3ddc6b0da24138723fa4ba136072450f9f728b308 |
| apps/backend/app/composition.py | 192d4bd17ff4ad34e4d71c1b6ae641f470f367f442c2ee8f0ae02935130a6b43 |
| apps/backend/app/config.py | 020a73ea045ab62496abf6e41cd775aa48dcabdc1bf3ddaf8e61726990acd670 |
| apps/backend/app/connectors/document_ownership_parser.py | 2f07e7368e8091355d99951ea72b3f28b67a803291edac278dc74d35b475aa04 |
| apps/backend/app/connectors/idp.py | 992af18a2376d78fe3b7276ea77560ba2407c799e06f465c69749e921c3df527 |
| apps/backend/app/connectors/local_document_runtime.py | fef50405d96224f59d1e5d2c6b1dd3405290a4b05ef3829b16851b57ba76edde |
| apps/backend/app/connectors/local_document_worker.py | 85696951ea27fcc7ddda75544e7be8ef9e7297caaae6e02ccf0667b1173fe9a4 |
| apps/backend/app/connectors/local_ocr.py | bb2af8374e64d94945ca3c4d5be4d445201b440727d4feb5f113b3f2654ea2b6 |
| apps/backend/app/connectors/local_pdf_idp.py | 64e9453a9b24b9df5eade24ff92c6f949fc2a7fb8fca76a00961bc79561a86e4 |
| apps/backend/app/connectors/local_process.py | a29155fcefa01263743ec702d57b2ee75c95e30a013805fa4a1c28173c657817 |
| apps/backend/app/connectors/ownership.py | 5455ac3092b56309d2c63564029b9354bdecccb9bc2754339a81cec63a4d6c8f |
| apps/backend/app/connectors/registry_ownership.py | 0978fe2463847558d7156ededd43c1dbdba8ab56074b92fb96efdc3e632a11bf |
| apps/backend/app/domain/case_management.py | f26736991075afa518eb6cda4549577a555499d148a0eba5ee2e3b3f572e9c88 |
| apps/backend/app/domain/documents.py | f186918a6c17f8dda1476656c9d37d08482b601a099a2f3bedd68ec721049fdc |
| apps/backend/app/domain/models.py | 7176b65193f75a5c128ade9979bb1d526fc2d2e2397cd48b5ac717ed2cb04ef0 |
| apps/backend/app/domain/ownership.py | 422575beebd1c3b3afc058f584ffada98bba2ecf7c4572f94061107ffcbe5d46 |
| apps/backend/app/domain/reconciliation.py | 6ef0cfadb1f38359f2b3aee29483cabaeb2683d3c837a5e16a4437961513bf9f |
| apps/backend/app/domain/target_preparation.py | 95c9ce13b13f688b77455a2ebe0cc718206124353e34d6f1f4ec678438ee1f1e |
| apps/backend/app/main.py | 38b9b6b16c516eca9d599e1ccd1c0f18a4faac1e7429a5d83bf83d08b81d3dd8 |
| apps/backend/app/mappers/goldtier_xpi.py | 600f0f507ca684c96f8f9babacfe92dda3d267c7dc5fc41c73dd96f098c4f530 |
| apps/backend/app/persistence/models.py | 305983e18f3ea7c6cba8ea96f1cea0ce96a6ddd5951674385d26b36e9712beba |
| apps/backend/app/persistence/mongo_case_store.py | 9be769d49b6fb59271c943eb68ccc01c2f54493fb4a15338b787858f3af03f12 |
| apps/backend/app/persistence/repositories.py | 1f0f429f463c2d6626448331044298030228a7631971b8050874a2bc678bceb5 |
| apps/backend/app/services/authorization.py | 7a5f020c7970ea408bb558723210024511b7dff4f8cd6ec2c251ee6fa6635cea |
| apps/backend/app/services/blocker_decision_policy.py | bbc03cdeea56bf08ce197abc5c423c707ccab66eebb6c172329b851f6084dcc3 |
| apps/backend/app/services/case_query.py | f3d8e98d6c2d57c381c2551efad85b8ce835dbcbdf3e1b6a92cd3a92438f6dc4 |
| apps/backend/app/services/clm_orchestration.py | 0147229630307bc68acc9cf7246c3e2b193620586a526749718f43618a18ef5f |
| apps/backend/app/services/document_media.py | 6b7f27c1f007cf598c9713e7834ccc2fe92e8105e4a820605f2fcfd66afe3f35 |
| apps/backend/app/services/document_ownership.py | a09115243994948fb4e34b87d51141eb4a64ab318a268e490710288cc1105e05 |
| apps/backend/app/services/document_processing.py | ff88316757b338d6c7517031b77b997d7ab1f0c8d9442d6dac3e4272d9aacc44 |
| apps/backend/app/services/manual_ownership_evidence.py | 24a39b5ed343c5e42466823332638e866e4e8f85f07a8b4986f2e7c0ee48163f |
| apps/backend/app/services/onboarding.py | 028b5a2bc937373b332cb023ef96f0bc1b3b8009695de1cd37aec4646ef8cab2 |
| apps/backend/app/services/ownership_analysis.py | fd11283de9efd23d2225e10ecb046b9620eb9ce57fea54ce56ff7238dd3f92d9 |
| apps/backend/app/services/ownership_repository.py | 4ba8fc921ea7d0c0e206a1b81dded175c2f04a07069a5708528a090c2fcc7274 |
| apps/backend/app/services/policy_management.py | 6f564dc2eaf72d180ecb68e7c059ea9f13633e795a44707aff838c492f0f84d9 |
| apps/backend/app/services/reconciliation.py | cf365e63038ae613426a7d4cdae806d83fc075092e3c75effb74916b03ef0941 |
| apps/backend/app/services/repository.py | 81ee9eca64da26f81d8785f43c257c8f6ef0dcbdce0f88b27d7aeab16f2dc5ff |
| apps/backend/app/services/zero_touch_orchestration.py | 0e81ee33f7fe43b153bed4601b7904c520ca0b10954fc762b487acfb7298bc99 |
| apps/backend/pyproject.toml | b13b424d4cb3926e88d7212cbc1a68ab31540827d8216b22ff3ca26e50a80851 |
| apps/backend/tests/s1_date_filter_fixtures.py | 6a6e1128828c69e86071371bab62fa3f75ba2942b072b65534a7b657be1b1158 |
| apps/backend/tests/s2_legacy_schema_fixtures.py | 6bbd2d417f35e2c9d05b0392f5f40b4f004ef67eb13f0780ec13a15cb97957b2 |
| apps/backend/tests/test_garden_business_fixture.py | 80763aadadb2c6989bf606d8103f1eb8506fe360a1a13fbcd2eb63309d1c23bf |
| apps/backend/tests/test_goldtier_xpi_sandbox.py | fd90f75819052afc91eb56997bb8e4eb15ddaed668fb21f7c3d312b05b29bac1 |
| apps/backend/tests/test_manual_ownership_evidence.py | 0df4f0761a5cee63741aa02ab7e681a8033464ec68e6e84b7dbf80bbf1823e13 |
| apps/backend/tests/test_phase11_reconciliation.py | b120b69a054fd417631cfc7a356284e95a940e6c3e74e71db4014b1bf9822eb4 |
| apps/backend/tests/test_phase12_persistence.py | 7638f05c6a603d14e06da6d424be1d44c8cf115a5e05b69f367b2deb7144a6d6 |
| apps/backend/tests/test_phase12_real_mongo.py | 831b0de3fdc4f72ddc09e9ee53fac2f8388952f7d2e52266c52328cf3aead1e7 |
| apps/backend/tests/test_phase13_priority.py | 3c20ced8e5f21c4376599be97c6e21c60434d7ccb7bcbe25daa5ca4477e28550 |
| apps/backend/tests/test_phase13_real_mongo.py | d35efa78da309d965bed4d78ab2205197555cded505db5fbbaec6d409bef4e25 |
| apps/backend/tests/test_phase14_5_real_mongo.py | 87f7b0568a557f8c431683f413dd8b32ff9770751574749477672c93ed301c3e |
| apps/backend/tests/test_phase24_identity.py | 7c2b0a5a22f86fb2dec46c0564803ea709906e32a77527dc2e37e258fdb6c3d9 |
| apps/backend/tests/test_phase24b_stage_recovery_round1.py | 6d4e299868c109a895678183e0decba658aa1649d57171485c450e2bb0be5ff9 |
| apps/backend/tests/test_phase24c_real_mongo.py | 33a2b5afb01edbfed2a3cc1228ff66195c2830a0048a5a0e1da730c658b06dcc |
| apps/backend/tests/test_phase_08_input_driven.py | 98d6cb007bf18ae61fd5068b616390d7a34a1974d43e98424ff18cc5130c4b1d |
| apps/backend/tests/test_pre_phase12_workspace_multidoc.py | edc114bf919d3f07722afa687fd6d53c04ee2adae953a5d398c371516f0c166b |
| apps/backend/tests/test_s1_date_filters.py | f1924d8c5953d74df343d74f52441c345cf2dcaca7041bff994c78f40285b9de |
| apps/backend/tests/test_s1_date_filters_real_mongo.py | 7a180ff63719b718c9007e0c3c976d639c01e8f10fb9c777f0bfbfe01d7ee8ca |
| apps/backend/tests/test_s1_pipeline_projection.py | 409f90959f11d0892d7adb6018b4ec6785af14604ba194a289f6d5d965d74ae5 |
| apps/backend/tests/test_s2_intelligence_real_mongo.py | ed2440dc9c91efb89c71097a793dd59abcc0704556f8f9e2df7c3849637860ca |
| apps/backend/tests/test_s2_local_ocr.py | 50baa91021b78fd3045ea13637f32f42cd04087ffe7e1cc0b77db2609898f07a |
| apps/backend/tests/test_s2_ownership_intelligence.py | 0f0ae00c1e3b2b66779c3b2a7aebd611e1130034e20ab8c7fad7136a48ae76c6 |
| apps/backend/tests/test_s2_persistence_security.py | 5a00fc19418d6ec3e9a18e970f54462d565607b1c88b37a73b81bceb28754519 |
| apps/backend/tests/test_s3_acceptance_safety.py | fe803d2e1f25f59d11766cf948b88440aa09dcb016454f36131ab56761705d08 |
| apps/backend/tests/test_s3_submission_preview.py | 5230f86b96234b679c9d8737da60cfca479378a9fe913a34e36ca938b9f3300c |
| apps/backend/tests/test_s3_submission_real_mongo.py | ff59ce1ebf90727ea5a9588bec806a3321a510bea4f49200688a11770db3ac0c |
| apps/backend/tests/test_s3_submission_status.py | 0384112f105f89034d0804bdbb03e0ea02985ab6633d219317f3f99f8f2f4f21 |
| apps/backend/tests/test_s3_target_activity.py | 328887e4c822b94a83549df7e35d52a238dbee668808ca7192651d86072d4681 |
| apps/backend/tests/test_slice_a_legacy_compatibility.py | 8abeee539dbb7c3381cf35bff43c064b2f985cdaa4862da4a78a3df71f8ebe81 |
| apps/backend/tests/test_slice_c_blocker_catalogue.py | ab3fb28ebe84a305aff212e857dc64fcd99e4ab2a58dcc9a23c07a151307a50b |
| apps/backend/tests/test_slice_c_blocker_recovery.py | 5efa8b98e484495df39fc2891e61c447cf4c115add6cf34c9543a49eb5894892 |
| apps/backend/tests/test_slice_c_real_mongo.py | 232788926ee9e65e1f6ed4b9edd67bef415a4a6900efc884bff4be718c6e6603 |
| apps/backend/tests/test_slice_f_document_pack.py | 2ec033b2dc8fcb28a6136317e3898cd50eb483b207fa915d3551eec88318bcd1 |
| apps/backend/tests/test_zero_touch_orchestration.py | b3455abab206440a96bd93197da850d6de593f5612941af3699b90e323f5ee37 |
| apps/frontend/e2e/authenticated-zero-touch.e2e.ts | 3a34d7d72f2dd455eb9dcc035ec1a80113492321b83962cecfda45d15a13cb7e |
| apps/frontend/e2e/garden-happy-path.e2e.ts | 79bc98b27408438d17aaa4902a1a2c223697d2a5e73348316970c294a86e6e2f |
| apps/frontend/e2e/onboarding-recovery.e2e.ts | 374ef18ebea04d5c1dd9d81285d761b8b4789c27f00ef77b9b4a905a9f5a9519 |
| apps/frontend/e2e/phase24-identity.e2e.ts | 0fff8b2bacb5b6aa37c4a2a8e938c399082a31059482a9437093db3f3c3cd8f7 |
| apps/frontend/e2e/phase24c-policy.e2e.ts | 9dba173fc217097f8c3961935e370601da64217c4663f3093970e8580aad24c1 |
| apps/frontend/e2e/responsive-layout.e2e.ts | 721870ad30307a127ed09d9c132e8e7da4ae4405b05a698511f6bd940312e9cf |
| apps/frontend/e2e/s1-workspace-session.e2e.ts | 649b1de8a7b7b2de7e662c08880552a2d2496c27c56df8524486dc15b5891c38 |
| apps/frontend/e2e/s2-ownership.e2e.ts | c97927ca11d059af3b4c9ae4f7f24f7581a449c4e4541700b791ae61a710ddc6 |
| apps/frontend/e2e/s3-sandbox-submission.e2e.ts | e3678f6cbab030e9705c39c92c2f8168996e436d9c51fa043acfb8907abed399 |
| apps/frontend/e2e/slice-b-registry-demo.e2e.ts | 89534e4258502f0240a466cd4ba71bed542972589f47f1cae21017e8c1af4493 |
| apps/frontend/e2e/slice-c-recovery.e2e.ts | 1cf3b68d92aaf97604bf60e4c60f427396f5a8a28b1e1514f0da496574e45a01 |
| apps/frontend/e2e/slice-e-policy.e2e.ts | ca98425ded12b01b3f669fd5040cd9aaafcea4d05e95ebc9519438fabf588377 |
| apps/frontend/e2e/zero-touch-exception.e2e.ts | 6fa8e31ce412bfb11a023fb1670d74f691f126448568e9750b0d46e924332b73 |
| apps/frontend/src/App.test.tsx | 78bde354d02d4cba68fa01b78c45df47dc6a7682ee42dff54f6bfe21c6623971 |
| apps/frontend/src/App.tsx | eab42f74cb1e068c2d4333f48fe171f4fa62fe519cc0c890496cd873034af07e |
| apps/frontend/src/AuthSessionOrdering.test.tsx | b3e581e5c716dd0c60b3a10d3bcb3d43b58eef27cd87ce566e6d2bf4ca51ff5e |
| apps/frontend/src/DemoPerformance.test.tsx | 54f5f459d2acddfe88e532b2a758e632c054bffa450e07a2fba802ab5e93ca1c |
| apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx | 09c09db1bce92c8e0c0f1575dd41056e1a8cf6806be34d0bc6961bb4dd251e4d |
| apps/frontend/src/GoldTierSandbox.test.tsx | 895c15c13025ff698d3227bc7c1db43d4771ae54bdedb9d6f93865e40343869e |
| apps/frontend/src/Phase13AuthPriority.test.tsx | 72fa2e31a547632848a6b7425eadfbcfe1f713a6cb700d26363e732eaed537f0 |
| apps/frontend/src/Phase15CNavigation.test.tsx | 88d54346778b02d9f1ce7d421d2a6a433acdcdd83f7665357e105077c5105e32 |
| apps/frontend/src/S1CreatedDateFilters.test.tsx | af32bab90f8fa197338fed6f116232871b7e90427545cba4b04a9d25f2e82193 |
| apps/frontend/src/S1FormsSession.test.tsx | c66d271645e821b969dcf04f4a39629765665d42f07b29fdb20af0a046482af5 |
| apps/frontend/src/api.ts | 49ca3f1b581fd14e657ae63ab343a89e5030293d4c16eb87c74b55fd3f7243e2 |
| apps/frontend/src/auth.tsx | 3725f907612a8c70450b3ecce10ac2f153621707b4303e0be977df97abe5e85d |
| apps/frontend/src/caseQueries.ts | 4efb45d6486feb4d62f81bb61c65627dedd0508092111f76534504be2ce83c2a |
| apps/frontend/src/pages/AcraDiagnostics.test.tsx | 19bbe154bb2edb910cf9c642af1a5be648be24a6ec023b75d363571a67cecd21 |
| apps/frontend/src/pages/AcraDiagnostics.tsx | 150510e78743815c5bf26f2574f908d527357e1f848fde0bb6a7f562c739c24e |
| apps/frontend/src/pages/CaseDetail.tsx | c6b82f9471705c8a59cd765b9546887a2333ba1e906cb69cbca4f05c66413078 |
| apps/frontend/src/pages/CaseQueue.tsx | 16247365134cca957d5b0b6c0290b867cad5bc6732fe4e2e8c6bc09332382c9c |
| apps/frontend/src/pages/CaseStatePanels.test.tsx | 20e2e20cdb3b04a05ac7ecdf5a79ee59ddee30afda7041663c66234e53b69b9b |
| apps/frontend/src/pages/CaseStatePanels.tsx | 31ee6e173923010b0678d3bd54ee95b9a5d017426e5cf7752a837aaf663b8c9c |
| apps/frontend/src/pages/DocumentEvidencePanel.test.tsx | 38b851549cd2a4498469994fd308128ad34243327fb521ee8aa62e2c7fed6de9 |
| apps/frontend/src/pages/DocumentEvidencePanel.tsx | b3513a98c4f22aa879f67921582d45df21ab484388672f8d745d1448366e8ae9 |
| apps/frontend/src/pages/GoldTierSandbox.tsx | 307c3c883bdf3439dcddb19a2d71110948e8de20f4d6ab954d0218b4f67ee1bb |
| apps/frontend/src/pages/HomeOnboarding.tsx | 9a03578891d35f5c7e663eec5f7b24d3c87d25689296d680f1227285332a72ff |
| apps/frontend/src/pages/LoginPage.tsx | 9a7f37c4964feaf9c43b01698513b281075927da2f7e598aff8f74fb72ce8b7e |
| apps/frontend/src/pages/ManualOwnershipEvidenceForm.test.tsx | 55dbfa21bd053690bad084238919a40cfce825de9f4a173f81d630f4197e72bd |
| apps/frontend/src/pages/ManualOwnershipEvidenceForm.tsx | 5719a3db21b0f3307fddb2573f509be40fe4c21d3da137b42ba2b6458f3309c4 |
| apps/frontend/src/pages/OnboardedClients.tsx | bb8eb0fd58da6321220edf451a1b1d36cfd3f12792918937fb40e6e3ddd5449c |
| apps/frontend/src/pages/OnboardingWorkspace.tsx | 9b540d1101af970bda4f80a9ebf5057ae74ac890f6bbfcfd14ece3f103509832 |
| apps/frontend/src/pages/OwnershipPathExplorer.tsx | cf4c14847558b5225b51ca47d8132596063234dc3f064cca827c3c620567a5c3 |
| apps/frontend/src/pages/ReviewAndSend.test.tsx | 2aa1e369c5383d22b753d4c43641d193ba388473ad94fbbe60ae2b60f8307c0d |
| apps/frontend/src/pages/ReviewAndSend.tsx | 08a5f599e69e7fdd509fdb2479d600986a70cdecdd6fb9c5e4629dc8981f246b |
| apps/frontend/src/pages/S1PipelineWorkspace.test.tsx | f023aec3c58800c3abf0aaa99c75b556e3cdca60a544178312cb2356f931b81d |
| apps/frontend/src/pages/S2OwnershipReview.test.tsx | 8db09465e89bcc2ba19c369c4a4b71102fed2f814cdc30186afadd446b6c066c |
| apps/frontend/src/pages/S3SubmissionStatus.test.tsx | 249011c4d1877d45a7a0c629373ed57ec8b93b0450ac81fbb6f6a18f1bb0f4cf |
| apps/frontend/src/styles.css | edd58626d9be52570abae010647be7ca59ad52a92cd38b19ea66b3b9a7e5f034 |
| apps/frontend/src/types.ts | 7528ff6e5930c98a163a504b297d793c69d0484b9ba8b803e68ea25d82e0058b |
| docs/ARCHITECTURE.md | 95a503664fe5f6b9f31298724c425dc77b853b2410dd393ac924eb03d49ef7ba |
| docs/PROJECT_STATE.md | d9e4e932e9de807a71ac574ac13f3b43f98a79caf5be74b1cbb9c673944bb93d |
| docs/contracts/CASE_PORTFOLIO_QUERY_PROFILE.md | 0081ef9cb96f99672abe77a6c4f9dd4b8649ed65fec8839d37261247ccea005f |
| docs/contracts/CLM_READINESS_POLICY.md | ba0ea0c84b8084f1987e0923816e2a8bd15398e9621d2c510cd7cf2495d81d9c |
| docs/contracts/IDP_FIELD_PROFILE.md | 64a24ea2f0219ee9c8559ce1858f1df93c09cca428c7c2bfbda0e6396001760a |
| docs/contracts/IDP_REVIEW_CONTRACT.md | 50ec8cde1265b226d3181828d1ea51041ca7c166d8a5bedbc3137943eca8170a |
| docs/contracts/MULTI_DOCUMENT_INTAKE_PROFILE.md | 713647c99139e161657578e40c59da866773d428e89330b0dc32c4445253de19 |
| docs/contracts/OWNERSHIP_UBO_PROFILE.md | e06b09489694f1d797a893c77765cacc04c7380e5c8207850011cf0ba150f01e |
| docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md | 39780127386b6d3db4a632777e27f646d993ab4d7a27b10e82f3b9c2c9297df5 |
| docs/contracts/POLICY_ACTIVATION_CONTRACT.md | 16367107f83a51aa636377c54bf58665456b88baad23f78ddacf9422c07374c6 |
| docs/decisions/ADR-007_RECOVERABLE_ONBOARDING_AND_FINAL_CONFIRMATION.md | 255bedba05f3a84a82dc0c5772160839c8f60cb71fffa002bb51bf0bd0de57ff |
| docs/decisions/ADR-009_LOCAL_OCR_AND_REVIEWED_OWNERSHIP.md | e9ec3cd0c0d7d893630342367d92fd945d1f8fefc3d6b649ef6ad554658aa189 |
| docs/decisions/DECISION_LOG.md | 0d9aadd47d2cf8a9218a979b2c55788f53622c55ad3e6f40c8386066a50ef2b1 |
| docs/demo/BLOCKER_RECTIFICATION_GUIDE.md | af480f46bd7d1a2386a8e7dd2d894ae9a9f448212c7357960b00a99ee539a872 |
| docs/development/GARDEN_DEMO_GUIDE.md | 9732f402c2d71c0cf213ede55125539f95cde2220702346edc8251449a2db21b |
| docs/development/GOLDTIER_SANDBOX_ACCEPTANCE_RUNBOOK.md | f39ca52b94d6cdc7939447ff3343ad691b927edca4edfbd3162e55e885c417c8 |
| docs/development/LOCAL_OCR_SETUP.md | 0bcbd6e13c07e908ab266139cc02edcabe2d9b45ead04d4af726aa95fa765ec4 |
| docs/integration/ONBOARDING_INTELLIGENCE_S3_FIELD_MATRIX.md | a9672c52895634314b90ca3502214a4122dcac0c606dffdc6f8968593ca7481e |
| docs/sponsor-questions/OPEN_QUESTIONS.md | c5af6f300e1f4d5517ff62283417ece99a06856bbbd1a6ccd9c91b254d58cb92 |
| scripts/e2e_backend_server.py | b160d20db0c6b7b6aa33339634f28c01ad7e73fd5fed16d03080f57040951048 |
| scripts/ocr_validation.Dockerfile | d2301392c8e2a8b27bec5c4bf84eacc52a4b2ec97916e16ae68a7cb289ee021a |
| scripts/ocr_validation.Dockerfile.dockerignore | 0f9ae7f6f6f926053c9295f4b011004a33c6de5a2dff6bd83231d54c48033cfe |
| scripts/run_e2e.py | f1c605a00f758b19a5bd1d8548feb87c7cc867ce29fb7d8b4c80c1ee288d87d7 |
| scripts/run_physical_mongo_tests.py | 1bb75b9f7efd3e036f98cc551f70cfa912af07aa9403c37fac542ffdb07f1fbd |
| scripts/run_s3_sandbox_acceptance.py | 490a1477132f7679bedad44613da3206eb65ae2367e6312b1e27aaa6adf9b21d |
| scripts/s3_sandbox_fixture.py | 9efa01a1df4c276e6e3350f8473a49269bf47a50021d196c640164cf987cf15c |
| tests/test_check_tooling_config.py | 4e33e9ace742618299aaa746de658bbab200b7fbdcba8daa0f13ba36fc27d8b3 |
| tests/test_run_e2e.py | 74251cec04ebb468f873e123ac78c5da06d8e860c4d03bc51cd2f74cc38f36cf |
| tests/test_run_physical_mongo_tests.py | d37b0ae5b5eff7229bab59a9a6cfac59e157c7caa1a3b9cd1935547f19599ccb |
