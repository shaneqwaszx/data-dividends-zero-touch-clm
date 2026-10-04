# Slice D2 local Mock provider hardening

Date: 2026-10-03 (Asia/Singapore).
Status: IMPLEMENTED_UNCOMMITTED; fresh independent D2 verdict belongs exclusively to POST_PHASE24_SLICE_D2_QUALITY_GATE_R1.md. The initial FAIL in POST_PHASE24_SLICE_D2_QUALITY_GATE.md remains preserved; D2-QG-001 has corrective implementation and final verification below.
Scope: D2 only. D1 is closed and unchanged. D3/E/F/G and publication are not authorized.

## Revision, model and preservation

Requested development model: GPT-6.1 Sol / Ultra or highest available reasoning. The primary agent's actual model and reasoning setting are not exposed by the session tools; they cannot be independently attested. The fresh-context reviewer is explicitly selected as GPT-6.1 Sol / xhigh. Its verdict is not supplied by this implementation report.

Worktree: C:/Users/shane/.codex-clean2/worktrees/post-phase24-stability-provider-hardening/data-dividends-zero-touch-clm.
Branch: feat/post-phase24-stability-provider-hardening.
BASE_SHA, HEAD, main and observed local origin/main: 707765b1d51172c64b851c9e46e68b3c23006789. No remote fetch or freshness claim. Index remains empty. All changes are uncommitted and unpushed.

D2 began from 81 accepted dirty paths. The task-owned baseline snapshot preserves their exact pre-D2 bytes. D2 intentionally overlaps six existing A/B/C files; their before-images are retained, and all other 75 accepted paths remain byte-exact. The A/B/C candidate/gate anchors and both D1 Markdown documents are unchanged. No historical gate is represented as reviewing the D2 changes. The current D2 path hashes, before/after identities and safe evidence receipts are frozen separately in POST_PHASE24_SLICE_D2_CANDIDATE_R1.json. The initial candidate manifest and FAIL report remain unchanged; all 20 initial reviewed files have exact before-images under tmp/slice_d2_20261003/review_round0.

AGENTS.md and the EXTERNAL_PROVIDER, BACKEND_DOMAIN, BACKEND_API and PERSISTENCE workflow classes were applied. BACKEND_API was treated conservatively because consumers expose operation progress; no HTTP route or DTO was changed. External integration/security, sponsor reconciliation, architecture, persistence, anti-entropy and POC regression skills were applied within the existing owners. No new ADR or replacement owner was needed.

## D1 authority boundary

D1's sole authorized exact synthetic Legal Name search returned "No results found": OBSERVED_SANDBOX_UI / NO MATCH. No record was opened or search broadened. That observation supports retaining the existing NO_MATCH presentation only. It supplies no API matching rule, identity schema, lifecycle, Policy, Amend, task, history, retry, atomicity, authentication or approval semantics.

All implemented D2 behavior below uses exactly one of EXISTING_ACCEPTED_CONTRACT or EXISTING_PROJECT_DECISION. UNKNOWN and INFERENCE are not implementation authority. D-063's optional XPI Amend is not applied to the EDS-shaped Mock.

## Behavior authority

| Implemented behavior | Classification | Exact authority and limit |
|---|---|---|
| Store accepted synthetic ID, legal name, country, role/type and representable registered address only | EXISTING_ACCEPTED_CONTRACT | GOLDTIER_CONTRACT_BASELINE.md corrected EDS schemas/mandatory overlay; app/mappers/goldtier.py Mock Shell, Policy, Amend and readback methods; existing GoldTierSearchCandidate. No extra portal fields or schema changes |
| Keep state inside the existing process-local Mock connector, with a lock and bounded customer capacity | EXISTING_PROJECT_DECISION | D1 reconciliation rows for Shell/identity and restart; existing Mock boundary; explicit D2 A/H authorization. The 1,000 default / 10,000 maximum is a local capacity safeguard, not a GoldTier business limit |
| Use a complete synthetic correlation UUID for Shell ID; reject capacity or ID collision | EXISTING_PROJECT_DECISION | Existing Mock-generated synthetic ID convention plus D2 bounded-state direction. This removes truncated-prefix collisions and does not implement provider idempotency |
| Preserve exact EDS registration Search, configured synthetic matches and default NO_MATCH; ambiguous duplicates do not select a party | EXISTING_ACCEPTED_CONTRACT | Existing SearchPartyRequest, GoldTierSearchResult/outcome models and Mock registration dialect in D1 reconciliation. No fuzzy search, aliases or UI-derived filters. XPI registration/UEN query remains unsupported |
| Policy binds registration only from the accepted ACRA external-system/key request, and retains technical POLICY_CREATED | EXISTING_ACCEPTED_CONTRACT | Mock mapper build_policy_request and accepted EDS Policy/result models. Shell source_case_id is never parsed as registration. This is a technical request outcome only |
| Missing local customers fail Policy/Amend; an established identity cannot be rebound | EXISTING_PROJECT_DECISION | D2 A/C/G truthful-state and no-false-reuse requirements; existing required-stage fail-closed owner. These are local safety guards, not new Sandbox validation rules |
| Preserve mandatory Mock Amend, success and partial failure; allow a constructor-only deterministic validation-failure fixture | EXISTING_ACCEPTED_CONTRACT | Existing MockGoldTierRequestMapper.requires_amend, Amend DTO and GoldTierOperationResult outcomes; D1 conditional failure-fixture reconciliation and explicit D2 E. No inferred atomicity, retry or enrichment |
| Successful Mock execution now performs existing identity readback after required Amend | EXISTING_PROJECT_DECISION | D1 identity-readback reconciliation; current _readback_identity_matches and durable execution owner; ADR-006/007. Mock reuses the existing readback comparison and ledger, without applying XPI query syntax |
| Same-customer reuse requires prior same-identity case, same ID and finalized successful same-ID READBACK ledger evidence | EXISTING_PROJECT_DECISION | D1 verified-case/reuse boundary; D2 C/G; existing identity resolver and case repository; ADR-006/007. Seeds and case projections alone never prove prior success |
| Bind prior receipt/outcome identities, recomputed fingerprints, ledger progress and case projection before reuse | EXISTING_PROJECT_DECISION | PERSISTENCE_RECOVERY_PROFILE.md case-envelope nested-identity invariant; ADR-006/007 verified same-ID proof; existing _submission_fingerprint/_idempotency_fingerprint and finalization checks. Reject contradictions inside the existing Mock reuse owner; no general schema/decoder change |
| Read prior case ledger entries through defensive list_for_case snapshots in existing memory/Mongo repositories | EXISTING_PROJECT_DECISION | Existing target-ledger/persistence owner and PERSISTENCE_RECOVERY_PROFILE.md. Read-only lookup; no collection, schema, CAS, index, mutation or persistence owner added |
| Constructor fixtures and fresh connector instances are the sole setup/reset boundary | EXISTING_PROJECT_DECISION | D1 fixture/reset reconciliation and D2 F. No generic runtime seed/reset API or external setup action |
| State loss fails truthfully; uncertain attempts cannot replay; retained durable receipts/outcomes may finalize without provider reconstruction | EXISTING_PROJECT_DECISION | Existing durable execution/uncertainty/finalization owner, ADR-006/007 and D2 G/H. No cross-process provider-state persistence or fixture reconstruction |

Contract sources retain their recorded provisional/project limitations. This report supplies no sponsor confirmation or external interoperability evidence.

## State, execution and identity design

_MockCustomer contains a validated frozen identity plus minimal technical role/type, external-system, Policy ID/status and Amend status. The existing MockGoldTierConnector owns a private dictionary protected by RLock. Accepted candidate fields are bounded by their existing strict model. Customer capacity is constructor-only, defaults to 1,000 and accepts 1..10,000; fixture counts may not exceed capacity. Search returns at most the accepted 25 candidates, with safe failure beyond that result bound.

Shell stores its returned complete synthetic ID and actual accepted request fields. It does not establish registration. Successful ACRA Policy establishes the accepted registration binding. Other external-system keys are not interpreted as ACRA registrations. Policy cannot successfully target a missing local customer or rebind an established identity.

Mock Amend remains mandatory. Success retains the supplied legal name and the existing mapper's one-address comma-separated projection. Other address shapes do not invent a primary address; legal form and unseen enrichment are not inferred. The accepted partial fixture retains a technical partial status and does not assert which optional fields committed. The new validation fixture retains no fabricated enriched fields. Required-stage partial/failure still stops completion and subsequent readback.

New-customer success is SEARCH -> SHELL -> POLICY -> AMEND -> READBACK in the existing ledger. Identity-first/CLM flows may have an additional preflight Search. Reuse with actual verified prior evidence skips Shell/Policy and still performs Amend and READBACK. Seed-only matches require review without customer writes. The obsolete Mock completion branch after Amend was removed so both direct and incremental execution use the existing readback/finalization owner. Sandbox/XPI ordering and D-063 optional Amend remain unchanged.

The existing identity resolver still determines candidate resolution. For Mock, the owning onboarding service adds prior-proof checks to bootstrap/recheck, canonical resolution, direct execution and incremental intent creation. Proof requires a prior GT_ENRICHED/COMPLETED case with VERIFIED readback, a FINALIZED same-Mock ledger entry, SUCCESS receipt/result and target outcome, matching target/readback IDs, VERIFIED status, completed READBACK, and matching immutable canonical name/registration/country. Present current provider identity fields are checked with the existing exact readback comparison. A seeded selected ID cannot bypass this guard. A conflicting current provider identity cannot reuse a prior case. Receipt/outcome case, submission and target-correlation IDs must agree with the immutable submission; the submission case must be the actual prior case. Input and idempotency fingerprints are recomputed with the existing owner helpers. Ledger resolved/readback IDs and technical progress must agree with outcome/receipt, successful receipt state/results must be consistent and contain no error/infrastructure-failure claim, and the prior case result projection must equal the retained result. Case correlation and target-submission correlation are distinct accepted scopes; they are not forced equal. Proof reading compares existing typed fields and never invokes the rich receipt mapper or a finalization-fault callback.

The added list_for_case method returns defensive snapshots from existing repositories. Mongo reads the existing strict case envelope; physical tests verify that lookup does not alter its revision/content. The provider holds no case ID history, actor, task, queue, approval, audit stream, intent, attempt counter, completion receipt, retry or idempotency state.

## Restart and durable ownership

| Situation with a fresh provider instance | Actual local result | Durable owner |
|---|---|---|
| Previously completed Shell, provider customer lost | Next Policy fails for missing local customer; Shell is not replayed | Existing attempted/completed markers and required-stage failure |
| Previously completed Policy, provider customer lost | Next Amend fails; Policy is not duplicated | Same ledger and error owner |
| Previously completed Amend, provider customer lost | Readback gives NO_MATCH and review; no fabricated VERIFIED/final success | Existing readback comparison/outcome owner |
| Policy may have committed but response was lost | Subsequent advances raise existing uncertainty with zero provider calls | Durable attempted-without-definitive-completion boundary |
| Durable verified outcome/receipt already retained | Finalization/retrieval returns retained result without provider reconstruction/calls | Existing target outcome/finalization owner |
| New case after restart | Provider Search truthfully gives NO_MATCH; old customer facts are not inferred from the ledger or fixtures | Existing identity/case owner determines subsequent authorized work |

These checks use new connector objects and, in physical tests, reopened Mongo stores/repositories. They prove process-local state-loss semantics and durable restart behavior. They do not establish distributed exactly-once delivery or persistence of Mock customers across processes.

## D2 files

Product files (four):
- apps/backend/app/connectors/mock_goldtier.py
- apps/backend/app/services/onboarding.py
- apps/backend/app/services/target_execution_repository.py
- apps/backend/app/persistence/repositories.py

Existing test files (ten):
- apps/backend/tests/test_clm_orchestration.py
- apps/backend/tests/test_zero_touch_orchestration.py
- apps/backend/tests/test_onboarding_resilience.py
- apps/backend/tests/test_phase06_provider_conformance.py
- apps/backend/tests/test_phase11_reconciliation.py
- apps/backend/tests/test_phase12_persistence.py
- apps/backend/tests/test_phase12_real_mongo.py
- apps/backend/tests/test_phase_07_uat.py
- apps/backend/tests/test_phase_08_input_driven.py
- apps/backend/tests/test_pre_phase12_workspace_multidoc.py

New test files (two):
- apps/backend/tests/test_slice_d_mock_goldtier.py
- apps/backend/tests/test_slice_d_real_mongo.py

Affected durable documentation (three):
- docs/ARCHITECTURE.md
- docs/PROJECT_STATE.md
- .agents/skills/poc-regression-check/references/regression-catalogue.md

D2 report and candidate manifest are additional governance files. The independent reviewer owns only its separately assigned gate report. Existing tests were adapted to actual readback call ordering; legitimate reuse fixtures execute a real prior local onboarding and ledger readback, then clear only recorder traces. Fake historical success is not installed into product runtime.

## D2-QG-001 remediation and review rounds

The first fresh independent gate returned FAIL with one P1: internally contradictory finalized rows could hydrate verified reuse. It reproduced four structured contradictions in memory and after strict Mongo replacement/reopening. Other owner boundaries and fresh 592 ordinary / 28 physical cases passed, but that did not excuse false proof. The original FAIL and candidate manifest are immutable.

Corrective tests began from actual successful local onboarding, changed one structured proof fact, and revalidated through the existing ledger model/repository. All 17 new focused cases reproduced EXACT_MATCH before the guard repair. They cover receipt and outcome case/submission/target-correlation IDs, both immutable fingerprints, retained customer/readback progress, technical status, receipt state/result/error/infrastructure flags, and a conflicting case projection. Four representative contradictions additionally pass through strict Mongo replacement and store reopening.

The fix stays inside _find_verified_target_case: it compares existing proof to the immutable input, prior case and retained progress/results. No schema, collection, persistence mutation, generic fixture/reset API, HTTP/auth, workflow or retry owner is added. It does not reconstruct provider facts or invoke rich receipt mapping during a read.

Two implementer corrections were necessary during verification: target correlation was preserved as distinct from the case correlation, and an early pure-looking result-mapper call was removed after the existing CLM finalization fault test exposed an ownership/timing regression. That regression is now covered in the final 202-case focus; the rich mapper remains at finalization, and recovery still makes no target replay. Failed invocation/attempt receipts are retained and are not passing evidence. Final full and physical runs below execute the exact corrected source bytes, with no subsequent Python edits.

Current acceptance is not self-attested by this report. POST_PHASE24_SLICE_D2_QUALITY_GATE_R1.md is the separately assigned fresh-context verdict for the newly frozen content.

## Focused acceptance matrix

The final new Mock suite contains 47 executed cases, including 17 proof-consistency additions. New physical coverage contains nine executed cases, including four new strict-decoding/restart proof-consistency cases.

| Owner criterion | Executed evidence |
|---|---|
| 1. Existing NO_MATCH | test_default_no_match_is_unchanged_and_exact_only |
| 2. Configured exact match | test_configured_match_does_not_invent_policy_or_legal_name |
| 3. Accepted Shell fields only | test_shell_never_parses_source_case_id_for_registration |
| 4. Policy registration binding | test_policy_success_establishes_registration_binding_not_approval |
| 5. No case-ID-to-UEN inference | test_shell_never_parses_source_case_id_for_registration |
| 6. Required successful Amend | test_required_amend_then_truthful_readback_in_same_process |
| 7. Partial/validation Amend | test_amend_failure_fixtures_have_truthful_technical_state (two cases) |
| 8. Truthful readback | test_direct_success_is_verified_by_existing_ledger |
| 9. Same-process readback | test_required_amend_then_truthful_readback_in_same_process |
| 10. Fresh connector loses state | test_new_connector_loses_state_and_unknown_mutations_cannot_succeed |
| 11. Ledger prevents false replay after loss | test_uncertain_operation_blocks_replay_after_provider_state_loss plus physical uncertainty/restart |
| 12. Provider seeds cannot prove prior case | test_seeded_provider_cannot_establish_prior_verified_case_or_reuse; completed projection without ledger; seeded selected-ID bypass |
| 13. Same identity needs real prior proof | test_same_identity_reuse_requires_case_and_real_ledger_proof; test_actual_same_identity_reuse_skips_shell_policy_and_verifies_again |
| 14. Different/current conflicting identity cannot reuse | same-identity test's different-name case; test_current_provider_identity_conflict_cannot_reuse_prior_verified_case |
| 15. Unsupported registration API query | test_unsupported_query_dialects_fail_closed plus complete existing XPI suite |
| 16. No task/RFA/audit state | test_mock_internal_state_has_no_workflow_audit_http_or_persistence_owner and source inspection |
| 17. No new HTTP/auth | test_local_provider_operations_never_use_http_or_auth; local-only runtime wrapper; source inspection |
| 18. No cross-mode fallback | both existing CLM Mock/Sandbox plan-drift tests |
| 19. No second persistence owner | internal-field inspection; existing ledger repositories; physical read-only lookup/restart and complete Phase12 physical suite |
| 20. Constructor/test-local reset | test_snapshot_is_defensive_and_fixture_reset_is_connector_local |

Additional cases cover duplicate registration, bounded capacity, full UUID collisions, concurrent distinct IDs, identity rebinding, retained receipt retrieval and loss after each definitive mutation. Existing identity-resolver/evaluation, onboarding/CLM/zero-touch, partial/failure, uncertainty, mapper, provider conformance, persistence and Sandbox lifecycle regressions ran in the full suite.

## Verification provenance

All ordinary backend runs disabled Settings dotenv loading before pytest/application imports, disabled bytecode and pytest cache output, and blocked non-loopback socket connections. No .env was read. Physical runs used only the freshly generated task-owned loopback Mongo resource and existing allowlisted disposable-database fixture. Captured receipts persist only lane names, counts, test IDs, safe resource identities, timing and exit codes.

| Lane | Actual result |
|---|---|
| Pre-change required Mock Amend reproduction | 9 passed, baseline evidence only |
| Final focused Mock + identity resolver/evaluation + Phase24 identity + XPI + mode-drift + four finalization mapper-fault cases | 202 passed, 0 failed/skipped; exact final repaired source/test bytes |
| Full backend | 1,957 passed; 87 skipped; 2,044 collected; exit 0; 343.765s; exact final repaired source/test bytes |
| Physical new D2 plus complete Phase12 | 32 passed; 0 failures/errors/skips; 32 collected; exit 0; 47.235s; exact final repaired source/test bytes |
| Contract tests | 44 passed, 0 failures/errors/skips |
| Frontend unit tests | 415 passed across 35 files |
| Frontend typecheck/build | Both exit 0 |
| Installed Python/frontend dependency integrity | pip check and npm ls --all exit 0; no dependency installation |
| Ruff | All backend app/tests exit 0 |
| Strict mypy | Backend app exit 0; 115 source files |
| Formatting | New/replaced Mock and two D2 test files: ruff format --check exit 0; existing shared-file changes kept narrow |
| Governance scanners | secrets, project state, architecture, policy authority, provider readiness and tooling config: all exit 0 |
| Scanner/example unit tests | 8 secret-scanner tests and 5 GoldTier example-validation tests passed |
| Whitespace | Native git diff --check exit 0; explicit untracked Markdown/new-file UTF-8/whitespace audit also recorded with the candidate |
| Supplementary Phase07 delivery assets | 3 passed, 1 failed: test_synthetic_document_pack_is_explicit_and_bounded |

The initial D2 full/physical evidence preceded an EOL-only hygiene repair and later remediation; those older counts remain attributed only to the first candidate. Original non-ASCII prose was restored after a Windows default-encoding mistake. The final R1 full backend, focused and physical runs above all execute the current corrected Python bytes; no subsequent Python edit or formatting step occurs. Frontend415/type/build/dependency evidence is attributed to unchanged frontend/dependency content. Final R1 contracts/scanner/example tests were rerun. The final candidate binds exact source hashes and safe evidence receipts.

Initial failing-first/new-state failures, stale call-order fixture failures, two stale physical counter expectations and an incorrect root unittest discovery invocation were corrected within D2; those initial runs are not reported as passing. The corrected contract discovery executed all 44 tests. No fixture silently reconstructs runtime customer success.

The supplementary delivery-assets failure is reproducible and inherited: the root test is unchanged versus HEAD (normalized line endings), and garden-partnership-reviewed-client.pdf / multiple-owner-demo-client.pdf were already present with identical hashes before D2. Their accepted A/B/C contents were preserved. This is a separate integration/publication risk; no blanket whole-tree CI PASS or publication readiness is claimed. The independent reviewer must assess whether it blocks bounded D2 acceptance. No unrelated asset/test repair was made.

Browser/Playwright journeys were not rerun during D2; there is no D2 browser-rendering claim or frontend source change. Backend API/lifecycle and frontend unit/type/build consumers were checked. Historical A/B/C browser evidence remains attributed to its earlier candidate. No remote CI state was inspected. pre_pr_check.py was not run because this is an intentionally uncommitted handoff.

## Physical resource closure

Python 3.12.10 and Docker server 29.8.1 were observed in this session. Cached Mongo 7.0 image was used without pulling. A fresh task-labelled container bound exclusively to 127.0.0.1:27042 served only newly generated allowlisted clm_p12 test databases. No unrelated server, clm_poc database or owner connection URI was accessed. The exact resource identity/label, loopback binding and exclusive anonymous volumes were checked before removal. All disposable test databases were absent, the owned container and its two exclusive volumes were removed, and the port was released. r1_physical_resource.json records sanitized cleanup proof and contains no URI.

## Change dimensions and limits

API/type: one internal read-only ledger protocol method and constructor-only Mock parameters added; HTTP routes and DTO schemas unchanged.
Schema: durable/admin schemas, compatibility versions, indexes and CAS semantics unchanged.
Connector/runtime: local Mock facts, collision/capacity/missing-ID guards and successful readback changed.
Configuration: settings, environment composition and provider selection unchanged.
Business rule: no sponsor rule introduced; local reuse is tightened to explicit owner-required prior evidence.
Mapping: existing EDS/XPI mappers, aliases and mandatory/optional Amend rules unchanged.
Auth/security: no production authentication or access rule changed; no HTTP/auth added to Mock.
Architecture: existing owner/dependency map preserved; no second workflow, persistence or identity engine.
Provider status: Mock remains PROJECT_OWNED / LOCAL / IN_PROCESS / NO_HTTP / NO_AUTH / PROCESS_LOCAL. Sandbox remains partial and has no Mock fallback.

Process-local customers are lost on restart and capacity exhaustion fails safely. Readback is identity verification under existing comparison semantics, not proof of Policy completion, optional enrichment, compliance or KYC. Unseen address shapes and legal form are not fabricated. Cross-process customer persistence, provider replay/idempotency caches and distributed exactly-once semantics are not implemented.

## External budget and next checkpoint

| D2 activity | Count |
|---|---|
| GoldTier Sandbox UI interactions | 0 |
| GoldTier Sandbox API calls | 0 |
| GoldTier Sandbox mutations | 0 |
| GoldTier Production calls | 0 |
| ACRA external calls | 0 |
| Other provider calls | 0 |

No owner/sponsor credentials, authentication state, cookies/storage/tokens/headers, network authentication data or private payloads were accessed. Existing ordinary tests generate local synthetic authentication fixtures internally; no such value was retrieved, printed or saved in evidence.

Remaining UNKNOWN: actual authorized customer's GoldTier identity; Shell/full-record UI distinction; Policy chronology/state UI; Amend/validation presentation; workflow/tasks; audit/history/actors/timezone; Ready-for-Approval API transition; approval/compliance state; retry/idempotency/atomicity; production authentication and interoperability. The applicable sponsor questions stay open.

Next checkpoint: obtain the fresh independent bounded R1 D2 verdict for the corrected candidate, preserve the exact reviewed content, then return the owner-requested handoff in this chat and STOP. The inherited delivery-assets failure needs a separately authorized integration disposition before publication. No D3/E/F/G, commit, push, PR or merge is authorized.
