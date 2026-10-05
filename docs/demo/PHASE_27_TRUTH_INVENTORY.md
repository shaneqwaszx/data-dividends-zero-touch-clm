# Phase27 merged truth inventory

Inspected 2026-10-05. BASE_SHA/source HEAD/fetched origin/main:
`4ee8819d7404d6442e064fd60dcee03ccc84cf11` (PR #70).
Inventory class: DOCS_ONLY; later bounded remediation is FRONTEND_UI. Current candidate is uncommitted. This inventory establishes
27A facts; it does not claim human UAT or an independent Phase27 PASS.

IMPLEMENTED identifies current code; PROVEN_LOCAL identifies bounded local execution;
PROVEN_EXTERNAL identifies historical external observations only. MOCK, LOCAL and
SANDBOX_PARTIAL identify evidence/provider lanes. ASSUMPTION is unproved authority;
LIMITATION is a retained capability boundary; OPEN_SPONSOR_INPUT awaits authority.
Labels may coexist on a row because implementation and proof are different dimensions.

| Statement | Classification | Current source / evidence | Boundary |
|---|---|---|---|
| PR #69 onboarding intelligence/external Sandbox program is merged | IMPLEMENTED | git history; PR69 merge `73967401379378927c810d6227b0c7aa95fba061`; current domain/services | Original combined FAIL and later narrow P2 PASS retain separate scope |
| Phase25/26 is complete and merged through PR #70 | IMPLEMENTED | git show/diff; historical PHASE_25_26_FINAL_QUALITY_GATE | PR70 adds 16 docs/evidence files, no product source change; prior PASS is not Phase27 PASS |
| Twelve named inspectable pipeline nodes end in Final review & send | IMPLEMENTED; PROVEN_LOCAL | app/api_models.py; test_s1_pipeline_projection.py; new guarded stage browser | Retained target state follows submission; no second local HUMAN_APPROVAL node |
| Singapore is the sole implemented registry route | IMPLEMENTED; LIMITATION | domain/jurisdiction.py; provider composition; ARCHITECTURE section5 | Unknown/conflicting/unsupported routes fail closed |
| Default ACRA evidence and second synthetic company | MOCK; PROVEN_LOCAL | mock_acra.py; new second-company browser | Synthetic source is not official Marketplace evidence |
| Official Marketplace token/entity/officer and bounded shareholder observations | MOCK; PROVEN_EXTERNAL | PHASE_24_ACRA_DISCOVERY; current ACRA contract/evidence records | Historical authorized Mock observations; no fresh external call; Garden percentages absent |
| Garden PARTNERSHIP declaration journey | LOCAL; MOCK; PROVEN_LOCAL | new Garden browser; garden-partnership-reviewed-client.pdf | Offline official-shaped protocol plus separate reviewed fictional60/40; no external Garden acquisition |
| Opt-in known-case recursive Garden supplement | IMPLEMENTED; LOCAL; PROVEN_LOCAL | test_s2_ownership_intelligence.py; D-046/ADR-009 | Successful compatible official-Mock evidence only; default disabled; never failure fallback or official ownership |
| Optional Mock cache suppresses fresh complete acquisition | IMPLEMENTED; MOCK; PROVEN_LOCAL | registry_acquisition.py; test_phase16_registry_cache.py; fresh separate cache browser | Distinct case adds0 ACRA; Mock namespaces only; disabled by default; not target hydration |
| Generic ACRA sandbox / BizFile / Production | SANDBOX_PARTIAL; LIMITATION | composition/config; current provider matrix | Generic sandbox partial; BizFile dormant; Production/Live not implemented |
| Native-first PDF/DOCX/TXT and optional local scanned/image OCR | IMPLEMENTED; LOCAL | local_pdf_idp.py, local_ocr.py; ADR-009; LOCAL_OCR_SETUP | Historical isolated actual OCR is revision-bound; host Tesseract absent; Phase27 actual OCR NOT_RUN |
| Provenance, quality, evidence score and source agreement stay distinct | IMPLEMENTED; LOCAL; PROVEN_LOCAL | document_processing.py; focused document/frontend tests | Score is not calibrated probability; proposed observations do not decide sources |
| Wrong-UEN recovery retains document and recomputes dependent facts | IMPLEMENTED; PROVEN_LOCAL | document owner/current comparison; new S1 wrong-UEN browser | Same case/document; structured extraction retained; raw bytes are not retained |
| Current source decisions and creator ownership edit before send | IMPLEMENTED; LOCAL; PROVEN_LOCAL | ownership_analysis.py; test_s2_ownership_intelligence.py; S2 browsers | Explicit rationale/source; immutable prior evidence; target intent freezes edits |
| One Decimal graph/path/aggregation engine | IMPLEMENTED; LOCAL; PROVEN_LOCAL | domain/ownership.py; ownership_analysis.py; S2 edit/tree browser | Direct/indirect provisional candidates; no legal/control certification |
| Inclusive >=25% bounded default | IMPLEMENTED | D-062; OWNERSHIP_UBO_PROFILE | Numeric/comparator authority only; frozen configurable case policy; Q-004 legal/control policy open |
| Advisory entity/UBO/mock risk | IMPLEMENTED; LOCAL; MOCK | onboarding_intelligence owner; pipeline test | Bounded advisory; not compliance/AML risk engine or supplied Q-017 risk |
| HR proposal, distinct Director decision, frozen existing cases | IMPLEMENTED; PROVEN_LOCAL | D-064; PolicyManagementService; focused policy/browser | No self-approval; only approval creates ACTIVE; synthetic impact is not production accuracy |
| Review & Send is final local human approval | IMPLEMENTED; PROVEN_LOCAL | D-062/ADR-007; pipeline and target browser tests | GoldTier KYC/internal approval/RFA outside local workflow |
| Mock target ledger owns Search/Shell/Policy/required Amend/readback | IMPLEMENTED; MOCK; PROVEN_LOCAL | target_execution_repository; target owner tests | Readback/currentness proof required; uncertain operation never auto-replays |
| One historical synthetic XPI parent delivery and restart retention | PROVEN_EXTERNAL; SANDBOX_PARTIAL | S3 external receipt/durable proof; GOLDTIER_CURRENT_CONTRACT_AND_SCREENING_RECONCILIATION | Search2/Shell1/Policy1/exact-ID readback1/Amend0; customer identity and Policy operation, not KYC/RFA/Live |
| Historical Garden Amend failed | LIMITATION; PROVEN_EXTERNAL | current integration reconciliation/D-059 | Failure retained; no replay or causality invented |
| Confirmed/failed/uncertain presentation and read-only uncertainty check | IMPLEMENTED; PROVEN_LOCAL | test_s3_submission_status.py; three new offline S3 browsers | Offline XPI protocol fixture; not fresh external Sandbox execution |
| Memory/Mongo; case schema9 strict schemas1..8 read compatibility | IMPLEMENTED; LOCAL | persistence/models.py; PERSISTENCE_RECOVERY_PROFILE | Strict decode/CAS/no-resurrection; no read-time rewrite; sessions/locks process-local |
| All3 retained original cases schemas2/2/8 validated via exact disposable clone | PROVEN_LOCAL | historical Phase25 receipts reviewed by PHASE_25_26_FINAL_QUALITY_GATE | Original read-only decode; actual HTTP/frontend on clone; historical evidence, no Phase27 database contact |
| Backend RBAC/team scope, safe404 and session cache clearing | IMPLEMENTED; PROVEN_LOCAL | authentication/authorization/caseQueries; new session browser | Production IdP/PingFed absent; role visibility never grants authority |
| Cases/Onboarded created-day filters | IMPLEMENTED; PROVEN_LOCAL | test_s1_date_filters.py; new date browser | Singapore UTC+08 inclusive days; server predicates before paging |
| Agent UI UAT / final closeout acceptance | PROVEN_LOCAL; LIMITATION | agent results:16 PASS/0 FAIL/5 NOT_RUN, two visibly retested fixes | AGENT_EXECUTED_UAT only; HUMAN_EXECUTED0; independent BarrierA exact PASS in the fresh recheck report; broader closeout has separate gates |
| Full production contracts, legal UBO/control, source/reviewer/retention and deployment authority | OPEN_SPONSOR_INPUT | Q-001..Q-018; current decisions/contracts | No question closed; bounded D-062/D-064 does not settle wider authority |
| Sponsor/production acceptance inferred from tests or credentials | ASSUMPTION | No supporting authority | Explicitly rejected; not used for any completion claim |
| RP child lifecycle, original-file target upload, Live providers, other registries, Camunda, OCDD, full MIS/Exception Workbench | LIMITATION | Current explicit non-capabilities | Not implemented/out of scope; no distributed exactly-once or compliance approval claim |

Current visible product sequence:

`Case created -> Initial identity -> Jurisdiction -> Existing-customer search ->
Registry verification -> Document verification -> Data reconciliation -> Ownership & UBO ->
Risk assessment (bounded advisory) -> Readiness check -> Preparing GoldTier Submission ->
Final review & send -> retained target submission state`.

Current automated evidence and precise commands/counts are in the
[Phase27 implementation record](../../.ai-pipeline/reports/PHASE_27_IMPLEMENTATION.md).
Historical receipts remain attributed to their original revision. No evidence category
is promoted by this inventory; no external execution or original database access occurred.
