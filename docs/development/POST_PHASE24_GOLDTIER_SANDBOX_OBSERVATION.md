# Post-Phase24 GoldTier Sandbox observation

Date: 2026-10-03, Asia/Singapore.
Checkpoint timestamp: 2026-10-03 11:48:45 SGT / 03:48:45 UTC.
Status: D1 READ_ONLY_STUDY_COMPLETE_WITH_NO_MATCH; RECONCILIATION_COMPLETE; D2 NOT_STARTED.

The exact authorized synthetic legal-name search returned "No results found". This establishes NO MATCH for that UI search only. No record was opened and no search was broadened. Record-specific concepts remain UNKNOWN. The mandatory reconciliation table is complete below; coordinator must report this checkpoint in the same chat and STOP before D2.

## Access and record boundary

Exact owner-supplied login URL: https://portal.gt.deltacapita.net/anz-nutmeg/#/login.
The coordinator opened that URL, observed the login screen, stopped, and gave the prescribed manual-login handoff. The owner explicitly confirmed authentication and authorized continuing read-only D1.

The original tab initially timed out through supported DOM/accessibility reads and a same-tab handle refresh. A fresh tab in the same Codex in-app browser, opened at the exact authorized login URL, recovered usable portal navigation and the customer search form. No browser switch or credential entry was performed. The earlier request to foreground the portal became unnecessary after this documented recovery. These are access-procedure facts, not proof of production authentication or interoperability.

Starting and sole searched identity: ZERO TOUCH SYNTHETIC ACCEPTANCE 779F8111C9CE06A6.
Authority: docs/development/OVERNIGHT_ACRA_GOLDTIER_DEMO_READINESS_REPORT.md:157-161 documents the synthetic identity and historical no-match execution. Historical results were not used as current UI evidence.

Only Legal Name was filled, its value was checked against the exact owner-authorized synthetic string, and the visible Search button was used once. The coordinator did not populate/change any alternative filter, perform arbitrary customer search/enumeration, or open a result. Garden, retained recovery identities, local Merlion fixtures, nearby names and unrelated records were not searched.

No credentials, password values, cookies, localStorage, sessionStorage, authentication headers/tokens, developer-network authentication data, raw provider responses, raw HTML or unrelated customer details were retrieved or retained. No direct API request or create/update/amend/policy/workflow/approval/delete/retry/resubmit action was performed.

## Evidence classification

Each portal observation below has exactly one classification. Only OBSERVED_SANDBOX_UI, EXISTING_ACCEPTED_CONTRACT and EXISTING_PROJECT_DECISION may later justify Mock behavior. INFERENCE is not implementation authority; UNKNOWN remains unknown.

| Classification | Meaning / permitted use |
|---|---|
| OBSERVED_SANDBOX_UI | Directly visible, sanitized UI evidence within this authorized session/search |
| EXISTING_ACCEPTED_CONTRACT | Existing accepted project contract within its recorded dialect and provisional limits |
| EXISTING_PROJECT_DECISION | Existing explicit project decision/current accepted owner behavior within its bounded scope |
| INFERENCE | Interpretation without direct accepted authority; documentation only |
| UNKNOWN | Not safely observed or established; cannot justify implementation |

## Sanitized portal observations

Context for O-002 through O-006: owner-confirmed manual authentication; same-browser recovered tab; exact synthetic legal-name search only.

| ID | Observation | Classification | Scope / limitation |
|---|---|---|---|
| O-001 | Login screen presented a Login button before manual sign-in | OBSERVED_SANDBOX_UI | No authentication implementation, credential or production-security conclusion |
| O-002 | Visible navigation/control text contained TASKS, CUSTOMER, CUSTOMERS and SEARCH. A control read "SEARCH FOR A SPECIFIC CUSTOMER"; separate account/request search controls were also visible | OBSERVED_SANDBOX_UI | Only customer search was opened. Task/account/request destinations were not inspected |
| O-003 | Customer Search exposed a Legal Name field and Search / Clear Search controls | OBSERVED_SANDBOX_UI | Exact Legal Name used once; Clear Search not used |
| O-004 | Search Results displayed "No results found" after the exact authorized synthetic legal-name search: NO MATCH | OBSERVED_SANDBOX_UI | No global nonexistence claim, broader search, opened customer or record ID |
| O-005 | Search labels included Short Name, Masked Legal Name, GoldTier ID, Parent Legal Name, Entity Type, KYC Customer Type, Date of Birth, Does this entity need to be verified, Alert Acronym, Alert Code, Markit Institution Name, AVID, Legal Entity Identifier, Registration Number, Tax ID, SWIFT / BIC, RAZOR Code, External System, External ID, Group Company Name and Group ID | OBSERVED_SANDBOX_UI | Labels only; these filters were not used. No data values, enum choices, query semantics or API schema established |
| O-006 | Search labels included Is Verified Migrated Profile, Exclude Managed Funds, Include Inactive Customers and Exclude Individuals | OBSERVED_SANDBOX_UI | Labels only; no control was changed. Default/filter semantics not established |
| O-007 | One/multiple-match presentation, current GoldTier ID/UEN, Shell versus full-record distinction, overview fields/lifecycle/status/external reference/country/customer type/client segment | UNKNOWN | NO MATCH prevented authorized record-specific observation |
| O-008 | Policy states, Requested context, request chronology, completion/approval | UNKNOWN | No allowed record or Policy view opened |
| O-009 | Amend status, validation-failure presentation, retained failure, failed fields/reasons | UNKNOWN | No allowed record or amendment view opened |
| O-010 | Task/workflow queue/state details, KYC Edit Pool or equivalent, post-API workflow boundary | UNKNOWN | Only navigation labels observed; no task queue or customer workflow inspected |
| O-011 | Audit/history events, actor categories, timestamp/timezone and state chronology | UNKNOWN | No allowed record/history opened |
| O-012 | Ready-for-Approval presence/absence, label and exact context | UNKNOWN | No allowed record or relevant view; no absence or API-transition claim |

NO MATCH is the required stop for the record search. The remaining checklist is closed as UNKNOWN for this D1 study, rather than searched on other identities or exposed through mutations.

## Existing authority, separated from new UI evidence

| Fact | Classification | Source / limitation |
|---|---|---|
| EDS-shaped Mock contract is implementation-ready for credential-free Mock only; corrected schemas/mandatory overlay and quarantine precedence remain | EXISTING_ACCEPTED_CONTRACT | docs/contracts/GOLDTIER_CONTRACT_BASELINE.md; no external interoperability or sponsor-confirmation claim |
| Mock Shell has no registration UEN; accepted Policy external key supplies registration binding | EXISTING_ACCEPTED_CONTRACT | apps/backend/app/mappers/goldtier.py:65-96; never derive UEN from source_case_id |
| XPI Search supports four supplied aliases; current case mapper deliberately uses legal name plus country; registration/UEN API query remains unsupported | EXISTING_ACCEPTED_CONTRACT | docs/integration/GOLDTIER_XPI_MAPPING_MATRIX.md:25-50; O-005 Registration Number label does not change this |
| D-063 permits optional supported reviewed XPI Amend followed by exact identity readback; no fabricated ANZSIC/group-company enrichment | EXISTING_PROJECT_DECISION | docs/decisions/DECISION_LOG.md:75; current XPI acceptance only; EDS Mock mapper still requires Amend |
| D-063 Policy success proves the requested operation under its bounded XPI semantics, not completed KYC, screening, risk, RFA, regulatory approval or Production onboarding | EXISTING_PROJECT_DECISION | D-063; D-059 is a separate historical bounded recovery decision, not authority to inspect/recover another customer |
| Existing target ledger/domain/CLM/persistence owners retain ordering, attempted/completed operations, uncertainty, no replay, finalization and restart | EXISTING_PROJECT_DECISION | current owners; ADR-006/007; no second provider/workflow/persistence owner |
| Current Mock is credential-free/in-process with only successful Policy party-to-external-key state; configured exact match/no match, Policy validation failure, Amend success/partial failure | EXISTING_PROJECT_DECISION | apps/backend/app/connectors/mock_goldtier.py; accepted current implementation, not external behavior |
| Current Mock readback request is registration Search and ordinary Mock progression skips the Sandbox-only READBACK branch | EXISTING_PROJECT_DECISION | apps/backend/app/mappers/goldtier.py:204; apps/backend/app/services/onboarding.py:2059-2064; a provider seed cannot create prior verified case evidence |
| Portal labels establish API schema, retry/idempotency/atomicity, Ready-for-Approval transition, production authentication or compliance approval | INFERENCE | Not established; prohibited implementation basis |

Q-001/Q-006/Q-007/Q-008/Q-009/Q-010/Q-011/Q-018 remain open at their recorded boundaries. This study closes none of those sponsor-controlled questions.

## Mandatory D1 reconciliation checkpoint

COMPLETE for the authorized NO MATCH study, including explicit UNKNOWN dispositions. Source/contract classifications in the authority column apply to those named facts; each portal observation retains its single classification above. No product implementation is performed or approved by a label alone.

| OBSERVED CONCEPT | CURRENT MOCK SUPPORT | CURRENT SANDBOX ADAPTER SUPPORT | SAFE TO MODEL LOCALLY? | AUTHORITY | PROPOSED CHANGE | DO NOT IMPLEMENT / UNKNOWN |
|---|---|---|---|---|---|---|
| Exact legal-name search; NO MATCH ("No results found") | Default NO_MATCH and configured registration match; registration-based EDS DTO | XPI aliases accepted; case mapper legal name plus country | YES for existing deterministic NO_MATCH outcome; dialect boundaries preserved | OBSERVED_SANDBOX_UI O-003/O-004; EXISTING_ACCEPTED_CONTRACT EDS/XPI Search | Preserve NO_MATCH behavior. Any later stateful Mock search remains under its accepted DTO | UI matching rules and one/multiple-match display UNKNOWN; no API query changes from UI labels |
| Additional search labels, including GoldTier ID and Registration Number | No portal-filter surface; current EDS registration query unchanged | Four supplied XPI aliases; registration/UEN API query unsupported | Labels may be documented; no new API/filter contract | OBSERVED_SANDBOX_UI O-005/O-006; EXISTING_ACCEPTED_CONTRACT mapping matrix | Documentation only; keep unsupported API queries fail-closed | Filter values, defaults, combination rules and schemas UNKNOWN; no broader search |
| Current synthetic Shell/overview/identity | Shell returns synthetic ID; accepted fields not stored as a customer model | Accepted XPI Shell mapping and safe identity projection | YES only for existing accepted Mock request/response data, labelled LOCAL / MOCK | UNKNOWN O-007; EXISTING_ACCEPTED_CONTRACT Shell; EXISTING_PROJECT_DECISION accepted Mock owner | Conditional D2 candidate: process-local storage of accepted synthetic identity fields/returned IDs | No portal-derived lifecycle, extra fields, case-ID-to-UEN mapping or interoperability claim |
| Policy request/state/chronology | Technical POLICY_CREATED; successful Policy binds accepted registration external key | Existing createPolicy seam; no policy/task/history read operation | Existing EDS technical outcomes only; no new portal state justified | UNKNOWN O-008; EXISTING_ACCEPTED_CONTRACT Policy; EXISTING_PROJECT_DECISION D-063 within XPI scope | Conditional D2 candidate: retain accepted technical Policy state in process-local Mock storage | Requested/UI internals UNKNOWN; no completion/approval/RFA; do not relabel POLICY_CREATED from unseen UI |
| Amend/validation failure/optional enrichment | Success and configured partial Amend; current mapper requires Amend | Optional supported reviewed enrichment or AMEND_NOT_REQUIRED/readback under D-063 | Existing contract outcomes only; Mock skip progression needs separate owner-safe implementation assessment | UNKNOWN O-009; EXISTING_ACCEPTED_CONTRACT results; EXISTING_PROJECT_DECISION D-063 | Conditional D2 candidate: local deterministic failure fixtures under accepted result models; assess optional-Amend owner interaction before changing it | No UI-derived validation, atomicity, retry or enrichment semantics; no fabricated ANZSIC/group-company data |
| Identity readback and same-customer reuse | Readback mapper exists; ordinary Mock execution lacks Sandbox READBACK; no built-in customer state readback | Exact identity readback supported by current Sandbox path | Conditional on existing identity resolver/ledger ownership; provider fixtures never prove prior verified case | UNKNOWN O-007; EXISTING_PROJECT_DECISION current identity/readback owners | Conditional D2 candidate: truthful local state readback; retain existing same-identity/same-ID verified-case requirements | No synthesized prior verified checkpoint, arbitrary customer reuse, skipped workflow owner or replay |
| Tasks/workflow/audit/history/actors/timestamps | No provider task/audit/customer event store | No task/history/audit read operation in current adapter seam | NO new portal semantics; any later test events must be MOCK / PROJECT_DEFINED and ledger-subordinate | OBSERVED_SANDBOX_UI O-002 for navigation only; UNKNOWN O-010/O-011 | No portal-derived task/audit change. Existing-contract test events may be considered separately in D2 | KYC Edit Pool, actors/timezone, queues, chronology and workflow outcomes UNKNOWN; no second audit/workflow/persistence owner |
| Ready-for-Approval and compliance approval | No sponsor-confirmed RFA API transition or autonomous approval | No confirmed RFA transition | NO | UNKNOWN O-012; EXISTING_PROJECT_DECISION D-063 preserves boundary | NONE | RFA label/presence/absence/transition and Q-001/Q-018 remain unresolved; no compliance approval |
| Restart, idempotency, uncertainty and retained finalization | Durable ledger owns attempt/no-replay/recovery; provider state process-local | Existing adapter uncertainty boundary and same durable owner | Existing owner behavior only; process-local loss must fail truthfully | EXISTING_PROJECT_DECISION current domain/CLM/persistence and ADR-006/007; no new UI evidence | Any later Mock state remains process-local; cross-process persistence is proposal-only | Portal study proves no retry/idempotency/atomicity; no provider replay or persistence owner |
| Seed/reset/fixture controls for later local Mock testing | Constructor configuration for current deterministic scenarios; no new seed/reset endpoint | No external seed/reset operation authorized | Test/constructor-local synthetic fixtures only, under explicit Mock boundary | EXISTING_PROJECT_DECISION accepted Mock implementation / bounded Slice-D scope | Conditional D2 candidate: fixture-local setup/reset; no generic runtime endpoint | No Sandbox seed/reset/mutation; demo_controls_enabled alone is not production-like exclusion |

Proposed D2 candidates above are grounded only in named existing accepted contract/project authority and must be assessed against the existing ledger. The absent record provides no evidence for new portal lifecycle/policy/amend/task/history/RFA behavior. D2 must not begin during this checkpoint turn.

Mock remains PROJECT_OWNED / LOCAL / IN_PROCESS / NO_HTTP / NO_AUTH / PROCESS_LOCAL. Sandbox remains DELTA_CAPITA_EXTERNAL / SANDBOX_PARTIAL / NO_MOCK_FALLBACK. Provider data/events must not become a second workflow/persistence owner or bypass the durable target ledger.

## External budget and stop boundary

Portal read-only UI access: exercised after owner-confirmed manual login.
Exact synthetic legal-name Search executions: 1.
Opened customer records: 0; broadened searches: 0.
Direct GoldTier Sandbox API calls: 0.
GoldTier Sandbox mutations: 0.
GoldTier Production calls: 0.
ACRA external calls: 0.
Other external provider calls: 0.

STOP before D2 and report this NO MATCH reconciliation checkpoint in the same chat. No Slice E/F/G, publication, stage/commit/push/PR/merge or product-source change is authorized by this D1 report.

## Verification and preserved baseline

Only this observation document and Slice-D preflight continuation status are updated in D1. API/type, schema, connector, configuration, business rule, mapping, auth/security, architecture, provider classification and product runtime behavior remain unchanged.

Fresh document/baseline checks cover UTF-8, whitespace including these untracked Markdown files, scoped secret patterns, required reconciliation columns/status, all 77 accepted C candidate files, 24 safe receipts, A/B/C anchors, branch/HEAD/local origin/main, empty index, and clean original main. No D implementation test, physical Mongo acceptance or new independent gate is claimed. Existing A/B/C evidence remains attributed to its unchanged accepted candidate.
