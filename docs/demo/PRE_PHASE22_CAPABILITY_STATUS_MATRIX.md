# Pre-Phase-22 Capability Status Matrix

Date: 2026-09-24
Scope: provider orchestration and sandbox testing increment
Phase 22: **DEFERRED / ON HOLD**

The statuses below describe current POC behavior only. `IMPLEMENTED` does not mean Live,
production-approved, customer-approved, or sponsor-approved unless the authority column
explicitly says so.

| Capability | Status | Implemented behavior | Authority / source | Limitations | How to demo | How to test technically | Next dependency |
|---|---|---|---|---|---|---|---|
| Singapore onboarding | IMPLEMENTED | Closed Singapore route from jurisdiction/Registry through evidence, ownership, advisory intelligence, readiness, and Mock GoldTier completion | Current source/tests; project POC decisions | Synthetic/local default; completion is not approval | Start a supported SG synthetic case | Full backend/frontend plus Garden and zero-touch suites | Production provider and policy authority |
| ACRA local Mock | IMPLEMENTED | Default deterministic multi-operation synthetic Registry provider | Project Mock contracts | Not official ACRA data or Live | Run a normal synthetic SG onboarding | ACRA contract and regression suites | None for local demo |
| ACRA API Marketplace Mock | BLOCKED | Explicit `api_marketplace_mock` mode, readiness row, safe configuration truth, and fail-closed composition | Official provider documentation; D-050; one `OFFICIAL_MOCK_OBSERVED` 401 | Exact auth/subscription and successful response contract unknown; no fallback | Show execution-profile/readiness documentation; activation fails closed | Provider-readiness, configuration, governance, and fail-closed composition tests | Q-012 plus approved credentials/test UEN |
| IDP / Certificate profile | IMPLEMENTED | Main demo defaults to `CERTIFICATE_OF_INCORPORATION_POC`; legal name, registration number, and jurisdiction required; address optional | User-authorized POC / `PROJECT_DEFINED_POC` | Local text extraction, not OCR or document-authenticity proof | Upload supported synthetic PDF/DOCX/TXT certificate evidence | Document API/processing/reconciliation/replacement suites | Q-003 production document policy |
| Reconciliation | IMPLEMENTED | Source-neutral comparison and bounded human resolution; absent optional COI address is explicit non-blocking `REGISTRY_ONLY` and does not fabricate document evidence; supplied mismatch and legacy required-address absence still block | Existing project decision D-030 refined by user-authorized D-052 | No global source precedence | Exercise missing-address COI, supplied address mismatch, and legacy required profile | Integrated zero-touch/reconciliation/persistence tests | Q-015 authority |
| Ownership graph | IMPLEMENTED | Registry evidence feeds one deterministic Decimal graph engine | Current architecture / D-021 | Local POC; no external ownership service | Use Garden Business indirect ownership | Ownership/contract/Garden suites | Production ownership evidence contract |
| UBO calculation | IMPLEMENTED | Direct/indirect Decimal aggregation yields provisional ownership candidates | Project-defined D-021 | Not a legal/controller determination | Inspect Garden ownership paths | Garden and UBO evaluation suites | Q-004 final UBO policy |
| Entity resolution | IMPLEMENTED | One deterministic resolver handles Registry/document/GoldTier candidates with hard-identifier dominance and review for ambiguity | D-047 plus sponsor-directed early Search use | Bounded local scoring, no autonomous fuzzy merge | Use exact and ambiguous synthetic candidates | CLM orchestration and synthetic evaluation | Sponsor thresholds/production validation |
| ML-assisted UBO | IMPLEMENTED | `ubo-advisory-linear-v1` consumes deterministic ownership and remains advisory | `PROJECT_DEFINED_PROVISIONAL` | Never replaces legal UBO owner | Open case intelligence panel | Synthetic UBO evaluation | Sponsor/legal policy |
| Mock risk | IMPLEMENTED | Versioned local LOW/MEDIUM/HIGH advisory band with `NOT_COMPLIANCE_DECISION` | `PROJECT_DEFINED_PROVISIONAL` | No regulatory or approval effect by default | Open case intelligence panel | Synthetic risk evaluation | Q-017 |
| GoldTier Search | IMPLEMENTED | Read-only Search runs after canonical Registry identity and before document/ownership; safe checkpoint retains candidates and timestamp | Sponsor-confirmed workflow intent D-051 | XPI non-empty candidate response remains unproved externally | Start exact/no-match/ambiguous Mock cases; HR can run bounded sandbox Search | CLM/zero-touch/XPI/HR-console tests | Successful authorized sandbox evidence |
| GoldTier Shell | PARTIAL | Created exactly once only for no-match cases after readiness; exact existing party skips Shell | D-051; existing ledger | Sandbox mutation not executed; seven target values remain `TBD_SPONSOR` | Run Mock no-match and exact-existing cases | Orchestration/ledger/no-replay tests | Approved sandbox test values and credentials |
| GoldTier Policy | PARTIAL | Separate durable checkpoint after target ID; uses immutable case policy snapshot | D-048/D-051 | Sandbox mutation not executed; vocabularies unresolved | Run Mock incremental target flow or inspect dry-run | Target mapping, policy, orchestration tests | Q-006/Q-007/Q-009/Q-010 |
| GoldTier Amend | PARTIAL | Separate durable checkpoint after Policy with retained target identity | Sponsor-confirmed amend route; D-051 | Sandbox mutation not executed | Run Mock incremental target flow or inspect dry-run | Target mapping, orchestration, recovery tests | Approved values and response evidence |
| GoldTier related parties | BLOCKED | Local preparation/preview/readiness remains available with explicit typed blocker | Sponsor expects first-level RP later | `childId` creation/retrieval lifecycle and relationship authority unproved; zero dispatch | Inspect CLM preparation and HR console blocker | Related-party preparation/contract tests | Proved child-ID lifecycle and mappings |
| Continuous target synchronization | IMPLEMENTED | Search plus Shell/Policy/Amend advance as distinct checkpoints in the sole target ledger | Sponsor-confirmed D-051 / ADR-005 | Current customer operations only; RP dispatch blocked | Observe operation events/statuses during Mock onboarding | Incremental, restart, uncertainty, no-replay tests | Further authorized target exchanges |
| Progress inspector | IMPLEMENTED | Optional collapsed/expanded backend-authored stage/event/operation view, including early Search | User-authorized POC | No raw payloads or client-invented stages | Toggle “Show processing details” on a running case | Frontend detailed-processing tests | None for current POC |
| HR Sandbox tester | PARTIAL | HR-only status, bounded Search, offline preview/dry-run, safe timeline; HR still has no case access | User-authorized POC D-052 | Standalone writes blocked by case-ledger boundary; timeline is process-local | Sign in as HR and open `/admin/goldtier-sandbox` | Backend RBAC/search/dry-run and frontend cache/navigation tests | Case-bound guarded-write design plus approved values |
| Exception Workbench | IMPLEMENTED | Existing read-only typed attention/triage includes GoldTier ambiguity | D-009 and current workbench | Assignment, notes, SLA, routing, escalation, notification deferred | Open an ambiguous Search case in Attention Queue | Existing queue and orchestration tests | Q-016 |
| Audit Trail | PARTIAL | Case events record early Search and durable target checkpoints; HR console exposes a bounded safe operation timeline | Current event owners; NIST minimization guidance | Not a production compliance audit; HR diagnostic timeline is process-local | Inspect case activity and console timeline | Activity, API projection, and console tests | Actor-attributed durable provider-diagnostic policy |
| Mongo persistence | IMPLEMENTED | Explicit optional schema-v5 case envelope persists Search checkpoint and incremental ledger state with CAS/no replay; stage-order v1 records are read truthfully and safe non-terminal continuation CAS-rebases to v2 without inventing Search completion | D-033/D-051 / ADR-005 | Single-instance POC; current physical run depends on available disposable Mongo | Restart a disposable Mongo-backed synthetic case | Raw base-v5 compatibility/recovery/no-replay tests; physical Mongo when available | Production durability/retention design |
| RBAC | IMPLEMENTED | Backend capabilities remain authoritative; only HR receives `PROVIDER_SANDBOX_TEST`, and HR has no `CASE_ACCESS` | User-authorized POC D-052 | Local bootstrap identity/session, not production IdP | Compare HR navigation/direct API with case roles | Phase 13 auth/RBAC and console tests | Q-016 / production IdP |
| Phase 22 | DEFERRED | No Phase 22 planner or runtime activation was started | Explicit task boundary | All Phase 22 work remains out of scope | Show project status and decision records | Governance/project-state checks | New explicit Phase 22 authorization |

## How it works

### Entity Resolution

- Inputs: canonical Registry identity, reconciled document identity, and bounded safe
  GoldTier candidates.
- Method: deterministic normalization plus the versioned weighted local resolver;
  usable identifier/country conflicts fail closed.
- Output: exact, probable/review, no-match, or conflict evidence. Only exact match can
  retain a target ID automatically.
- Test: synthetic exact-duplicate, descriptive ambiguity, tie, and hard-conflict cases.

### UBO

- Inputs: normalized Registry ownership graph.
- Method: the authoritative local Decimal engine calculates direct and indirect paths;
  `ubo-advisory-linear-v1` is a separate advisory projection only.
- Output: provisional ownership candidates plus advisory likelihood, never a legal UBO
  determination.
- Test: Garden Business and the bounded synthetic UBO evaluation.

### Risk

- Inputs: only available POC entity, document, ownership, and configured local factors;
  absent groups stay `NOT_ASSESSED`.
- Method: project-defined rules and score in `mock-advisory-risk-rules-v1`.
- Output: LOW/MEDIUM/HIGH mock band labelled `NOT_COMPLIANCE_DECISION`.
- Test: bounded synthetic risk scenarios; no automatic customer approval/rejection.

### GoldTier

- Search early: after canonical Registry identity and before evidence collection.
- Resolve: exact existing ID is retained; ambiguous candidates stop for human review;
  no match follows the new-customer path.
- Synchronize: Shell if new, then Policy and Amend as independent durable checkpoints.
- Protect: attempted-but-not-completed mutation state is uncertain and never replayed
  automatically. Related-party dispatch remains blocked.
- Test: HR safe console plus end-to-end synthetic Mock onboarding and recovery suites.

### ACRA

- Local Mock is the safe default and provides deterministic synthetic operations.
- Official API Marketplace Mock is a distinct explicit `MOCK` mode, currently in
  activation state `BLOCKED_AUTHORITY` after a bounded no-auth `401`.
- Generic sandbox remains a separate partial scaffold; dormant BizFile is not composed;
  none of these lanes is Live.
- Test: provider-mode diagnostics, governance checkers, strict connector tests, and SG
  onboarding regressions.
