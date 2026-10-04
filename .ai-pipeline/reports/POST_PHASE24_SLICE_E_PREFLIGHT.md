# Slice E preflight and E1 inventory

Date: 2026-10-03 (Asia/Singapore). Scope: Slice E only; one coordinator writes implementation.
Requested coordinator/specialist/reviewer: GPT-6.1 Sol Extra High; coordinator runtime model/effort and 1.5x speed are not exposed. Specialist explicitly dispatched gpt-6.1-sol/xhigh with fresh context and read-only ownership.

Worktree: C:/Users/shane/.codex-clean2/worktrees/post-phase24-stability-provider-hardening/data-dividends-zero-touch-clm.
Branch feat/post-phase24-stability-provider-hardening; BASE/HEAD/main/observed local origin/main 707765b1d51172c64b851c9e46e68b3c23006789.
99 accepted dirty paths, empty index, original main clean. D2 20-path aggregate 1decaa4f93cfdf6a2af8eeaa2be31e3b39effde353e450d93c00c9b7785387a4 and final gate 8ba722c7d25d96a4364a794b959c4274c17a363cacca60cea8ecd881d5d9fccb exact. All earlier unchanged anchors and eight D2 receipts exact.
No post-D2 product/test drift. Before-images of all99 accepted paths and explicit planned owners saved under tmp/slice_e_20261003/start; snapshot has105 files. No Git mutation/fetch/publication.
Secret scanner passed within tracked/nonignored task paths. No .env or sponsor credentials read.
Python3.12.10, Node22.23.3; installed frontend18.3.1 React/1.56.1 Playwright pinned. Tool capabilities: local PowerShell/Python/Node, purpose-built app file panels, subagent tools, configured local Playwright; no portal/provider tools needed. Authorized worktree writes require narrow sandbox escalation. Docker initially unavailable; installed Desktop started hidden, then daemon available. No earlier Slice-D containers remain; ports27040..27043 freely bound. Unrelated Docker resources preserved. Slice-E fresh physical resources and browser ports will be separately labelled/reserved and cleaned.

## Canonical owner and necessity

PolicyManagementService.proposal_impact owns read-only proposal comparison; api_policies GET impact projects it; PolicyRules renders it. Existing impact has current/default/proposed,14-case classifier before/after, registry durations, three document and ownership booleans. This does not explain named transitions, materiality, cache boundaries or unknowns, and stale comparisons use current ACTIVE rather than retained base.
Extend this owner with a pure helper and strict response projection. Reuse document_semantic_assessment, registry-owner exclusive expiry predicates, Decimal graph/path/aggregation/candidate helpers, OwnershipEvidenceTagger.tag/benchmark.
No policy/ownership/classifier/cache engine, repository, scheduler, persistence state or activation capability is added. ADR-sized owner replacement: none. Architecture review PROCEED within existing direction.
Frontend impact remains proposal-scoped memory with AbortSignal and actor/proposal/catalogue identity. No QueryClient/storage/key owner replacement or mutation retries.
Policy/case schemas, CAS, four-eyes, frozen-case and target ledger owners remain authoritative.

## E1 current-source inventory

Values below are current source-seeded defaults, not a read of an owner's Mongo population. The existing catalogue endpoint supplies actual retained ACTIVE values. All rules belong to domain/policy.py and PolicyManagementService. There are35 seeds:21 editable business parameters,8 protected target definitions,6 fixed definitions.

| POLICY PARAMETER | CURRENT OWNER / CONSUMER | VALUE TYPE / DEFAULT | CURRENT IMPACT SIMULATION | CURRENT TEST FIXTURE | CURRENT LIMITATION |
|---|---|---|---|---|---|
| REGISTRY_FRESHNESS_DAYS | RegistryAcquisitionCoordinator | INTEGER90,1..365 | seconds only | test_phase24c_registry | No named age transition; exact-key Mock only |
| REGISTRY_NOT_FOUND_TTL_SECONDS | same | INTEGER600,1..3600 | seconds only | test_phase24c_registry | Definitive NOT_FOUND only; uncertain errors excluded |
| DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD | DocumentProcessingService/document_semantic_assessment | DECIMAL0.85,0..1 |0.84/0.85/0.90 booleans | test_document_processing;test_phase24c_policy | Existing impact omits semantic blockers |
| OWNERSHIP_UBO_THRESHOLD_PERCENT | OwnershipAnalysisService | DECIMAL25.000000,0..100 |24.999999/25/30 booleans | test_ownership_analysis | Existing impact omits graph/issues/aggregation; engine candidate model requires threshold>0 |
| OWNERSHIP_UBO_COMPARATOR | same | fixed STRING GREATER_THAN_OR_EQUAL_TO | none | test_phase24c_policy,test_ownership_analysis | Not editable; inclusive |
| EVIDENCE_KIND_WEIGHT | OwnershipEvidenceTagger | DECIMAL0.50 |14-example benchmark | test_phase24c_policy,test_phase24_ownership_evidence | Weights sum1; semantic only |
| EVIDENCE_BINDING_WEIGHT | same | DECIMAL0.25 | same | same | Unknown entity binding stays UNKNOWN |
| EVIDENCE_CONFIDENCE_WEIGHT | same | DECIMAL0.25 | same | same | Source confidence does not establish arithmetic/legal facts |
| EVIDENCE_CLASSIFICATION_THRESHOLD | same | DECIMAL0.50 | same | same | Inclusive semantic score; no workflow decision |
| ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD | OnboardingIntelligenceService.resolve_entity | DECIMAL0.85 | NOT SIMULATED | test_onboarding_intelligence | Review<=auto; identifier/country/conflict gates retained |
| ENTITY_RESOLUTION_REVIEW_THRESHOLD | same | DECIMAL0.60 | NOT SIMULATED | same | Coupled thresholds |
| ENTITY_RESOLUTION_AMBIGUITY_MARGIN | same | DECIMAL0.03 | NOT SIMULATED | same | Candidate ties remain review |
| ENTITY_RESOLUTION_IDENTIFIER_WEIGHT | same | DECIMAL0.55 | NOT SIMULATED | same | Five weights sum1 |
| ENTITY_RESOLUTION_NAME_WEIGHT | same | DECIMAL0.25 | NOT SIMULATED | same | Name alone is not identity proof |
| ENTITY_RESOLUTION_ADDRESS_WEIGHT | same | DECIMAL0.10 | NOT SIMULATED | same | Address alone is not identity proof |
| ENTITY_RESOLUTION_LEGAL_FORM_WEIGHT | same | DECIMAL0.05 | NOT SIMULATED | same | Generic legal form is not independent corroboration |
| ENTITY_RESOLUTION_INCORPORATION_DATE_WEIGHT | same | DECIMAL0.05 | NOT SIMULATED | same | Coupled weights |
| UBO_ADVISORY_LIKELY_THRESHOLD | OnboardingIntelligenceService.advise_ubo | DECIMAL0.65 | NOT SIMULATED | test_onboarding_intelligence | unlikely<likely; consumes Decimal result |
| UBO_ADVISORY_UNLIKELY_THRESHOLD | same | DECIMAL0.35 | NOT SIMULATED | same | Advisory; no legal UBO |
| MOCK_RISK_MEDIUM_THRESHOLD | OnboardingIntelligenceService.assess_mock_risk | INTEGER30 | NOT SIMULATED | test_onboarding_intelligence | medium<high; insufficient signals NOT_ASSESSED |
| MOCK_RISK_HIGH_THRESHOLD | same | INTEGER60 | NOT SIMULATED | same | Advisory POC only |
| MOCK_RISK_BLOCKS_READINESS | same/ZeroTouchOrchestrator | BOOLEANfalse | NOT SIMULATED | test_onboarding_intelligence | Advisor cannot authorize readiness changes |
| REGISTRY_SUPPORTED_JURISDICTIONS;REGISTRY_PROVIDER | closed registry owner | STRING_LIST[SG];STRING ACRA | none | registry/jurisdiction tests | Fixed; no proposal change |
| DOCUMENT_SUPPORTED_MEDIA_TYPES | document owner | STRING_LIST PDF/DOCX/UTF-8 TXT | none | document tests | Fixed technical profile |
| WORKFLOW_SUPPORTED_STAGES | workflow owner | STRING_LIST supported stages | none | zero-touch tests | Fixed |
| RECONCILIATION_SOURCE_PRECEDENCE | reconciliation owner | STRING NONE | none | reconciliation tests | No inferred precedence |
| Eight GOLDTIER_* target rules | case snapshot/target mapper | STRING authority-labelled values | none | target policy/provider tests | Protected from business proposals; no target approval forecast |

## Bounded implementation and tests

Eight core editable parameters get authoritative synthetic scenarios. Thirteen remaining editable Intelligence parameters return NOT_ASSESSED, actual values, affected stage/coupling and stable reason; unknown never means zero. Fixed/protected definitions remain noneditable.
Named pack: document semantic confidence boundaries and blockers, registry freshness/negative expiry boundaries, Decimal threshold boundaries/multipath/incomplete/synthetic60/40, existing14 classifier examples. Same inputs before/after; deterministic IDs/version/hash; maximum64 scenarios,64 changed rules,14 benchmark cases,256KiB serialized output. No real case scan or production-volume forecast.
Stale proposals compare against retained base, separately identify current ACTIVE and remain stale/nonapprovable. Missing base fails closed. Proposer and Director use identical endpoint evidence; no new approval capability.
Use failing-first; focused owner/advisor/cache/Decimal/classifier/stale/RBAC/API/frontend/browser/frozen-case evidence, cumulative A+B+C+D floor, broad backend/frontend/types/build/contracts/scanners, guarded fresh Mongo only for relevant persisted policy/case-freeze proof, then freeze and fresh independent mini-gate. Maximum two bounded review remediation rounds.
Known unrelated Phase07 PDF allowlist failure remains INHERITED_INTEGRATION_DEBT / PUBLICATION_BLOCKER; do not repair.
External ACRA/Sandbox UI/API/mutations/Production/other-provider counters all0.
Stop uncommitted/unpushed after independent E PASS. No F/G or publication.
