# Pre-Phase-22 Capability Status Matrix

Date: 2026-09-28
Scope: provider orchestration and sandbox testing increment
Phase 22: **DEFERRED / ON HOLD**

The statuses below describe current POC behavior only. `IMPLEMENTED` does not mean Live,
production-approved, customer-approved, or sponsor-approved unless the authority column
explicitly says so.

| Capability | Status | Implemented behavior | Authority / source | Limitations | How to demo | How to test technically | Next dependency |
|---|---|---|---|---|---|---|---|
| Singapore onboarding | IMPLEMENTED | Closed Singapore route from jurisdiction/Registry through evidence, ownership, advisory intelligence, readiness, and Mock GoldTier completion | Current source/tests; project POC decisions | Synthetic/local default; completion is not approval | Start a supported SG synthetic case | Full backend/frontend plus Garden and zero-touch suites | Production provider and policy authority |
| ACRA local Mock | IMPLEMENTED | Default deterministic multi-operation synthetic Registry provider | Project Mock contracts | Not official ACRA data or Live | Run a normal synthetic SG onboarding | ACRA contract and regression suites | None for local demo |
| ACRA API Marketplace Mock | PARTIAL | Explicit opt-in `api_marketplace_mock` mode with fixed Mock token/entity/shareholder transport, strict decoders, memory-only token cache, and no fallback | Supplied Postman exports; authorized 2026-09-26 Mock observations; D-050/D-053/D-054 | Garden shareholders empty; no compatible percentage denominator; provider errors/limits and Production/Live contracts unresolved | Select the official Mock mode and retrieve an approved entity; observe truthful relationship-data stop | Auth/provider fake-transport suites, sanitized smoke receipt, routing/governance, and application stop test | Remaining Q-012 relationship/error/limit authority |
| IDP / Certificate profile | IMPLEMENTED | Main demo defaults to `CERTIFICATE_OF_INCORPORATION_POC`; legal name, registration number, and jurisdiction required; address optional | User-authorized POC / `PROJECT_DEFINED_POC` | Local text extraction, not OCR or document-authenticity proof | Upload supported synthetic PDF/DOCX/TXT certificate evidence | Document API/processing/reconciliation/replacement suites | Q-003 production document policy |
| Reconciliation | IMPLEMENTED | Source-neutral comparison and bounded human resolution; absent optional COI address is explicit non-blocking `REGISTRY_ONLY` and does not fabricate document evidence; supplied mismatch and legacy required-address absence still block | Existing project decision D-030 refined by user-authorized D-052 | No global source precedence | Exercise missing-address COI, supplied address mismatch, and legacy required profile | Integrated zero-touch/reconciliation/persistence tests | Q-015 authority |
| Ownership graph | IMPLEMENTED | Registry evidence feeds one deterministic Decimal graph engine | Current architecture / D-021 | Local POC; no external ownership service | Use Garden Business indirect ownership | Ownership/contract/Garden suites | Production ownership evidence contract |
| UBO calculation | IMPLEMENTED | Direct/indirect Decimal aggregation yields provisional ownership candidates | Project-defined D-021 | Not a legal/controller determination | Inspect Garden ownership paths | Garden and UBO evaluation suites | Q-004 final UBO policy |
| Entity resolution | IMPLEMENTED | One deterministic resolver handles Registry/document/GoldTier candidates with hard-identifier dominance and review for ambiguity | D-047 plus sponsor-directed early Search use | Bounded local scoring, no autonomous fuzzy merge | Use exact and ambiguous synthetic candidates | CLM orchestration and synthetic evaluation | Sponsor thresholds/production validation |
| ML-assisted UBO | IMPLEMENTED | `ubo-advisory-linear-v1` consumes deterministic ownership and remains advisory | `PROJECT_DEFINED_PROVISIONAL` | Never replaces legal UBO owner | Open case intelligence panel | Synthetic UBO evaluation | Sponsor/legal policy |
| Mock risk | IMPLEMENTED | Versioned local LOW/MEDIUM/HIGH advisory band with `NOT_COMPLIANCE_DECISION` | `PROJECT_DEFINED_PROVISIONAL` | No regulatory or approval effect by default | Open case intelligence panel | Synthetic risk evaluation | Q-017 |
| GoldTier Search | IMPLEMENTED | Read-only Search runs from bounded initial identity after SG eligibility and before optional ACRA; safe checkpoint retains candidates and timestamp | Sponsor-confirmed workflow intent D-051/D-058 | Sandbox candidate fields remain bounded by the supplied XPI response | Start exact/no-match/ambiguous cases; HR can run bounded sandbox Search | CLM/zero-touch/XPI/HR-console tests | Production interoperability remains unproved |
| GoldTier Shell | PARTIAL | Created only for no-match cases after readiness; exact existing party skips Shell | D-051/D-058; existing ledger | One Garden Shell outcome was uncertain and later exact-ID recovered without replay | Inspect recovery chronology and run Mock branch tests | Orchestration/ledger/no-replay/recovery tests | Production interoperability remains unproved |
| GoldTier Policy | PARTIAL | Separate durable checkpoint for new-customer target ID; exact existing party skips new-policy creation | D-048/D-051/D-058/D-059 | First Garden Policy was attempted once with an uncertain transport outcome, then provider-verified read-only as one `Singapore / Requested` request and durably recovered without replay; `Requested` is not approval or completion | Inspect the retained attempt and provider-recovery chronology; never replay uncertainty | Target mapping, policy, orchestration, restart, and no-replay tests | Production interoperability and policy-state authority |
| GoldTier Amend | PARTIAL | Durable checkpoint after Policy for new customers or directly after exact reuse for existing customers | Sponsor-confirmed amend route; D-051/D-058 and retained provider audit | Exactly one Garden Amend was attempted; provider audit ended `Created -> Valdiation Failed` with the clue `Amendment requires a KYC user`. The ledger retains `PROVIDER_VALIDATION_FAILED`; no retry or successful read-back is authorized | Inspect the retained failed-Amend chronology and run Mock incremental new/existing flows only | Target mapping, orchestration, recovery, failure-reconciliation, and no-replay tests | Sponsor/API-owner clarification of validation cause and safe retry/idempotency semantics |
| GoldTier related parties | BLOCKED | Local preparation/preview/readiness remains available with explicit typed blocker | Sponsor expects first-level RP later | `childId` creation/retrieval lifecycle and relationship authority unproved; zero dispatch | Inspect CLM preparation and HR console blocker | Related-party preparation/contract tests | Proved child-ID lifecycle and mappings |
| Continuous target synchronization | IMPLEMENTED | Initial identity drives GoldTier-first Search; new-customer Shell/Policy/Amend and exact-existing Amend/read-back remain in the sole target ledger | D-051/D-058 / ADR-005/ADR-006 | Current customer operations only; RP dispatch blocked | Observe branch and operation evidence during onboarding | Ordering, incremental, restart, recovery, uncertainty, no-replay tests | Further authorized target exchanges |
| Progress inspector | IMPLEMENTED | Optional collapsed/expanded backend-authored stage/event/operation view, including early Search | User-authorized POC | No raw payloads or client-invented stages | Toggle “Show processing details” on a running case | Frontend detailed-processing tests | None for current POC |
| HR Sandbox tester | PARTIAL | HR-only status, bounded Search, offline preview/dry-run, safe timeline; HR still has no case access | User-authorized POC D-052 | Standalone writes blocked by case-ledger boundary; timeline is process-local | Sign in as HR and open `/admin/goldtier-sandbox` | Backend RBAC/search/dry-run and frontend cache/navigation tests | Case-bound guarded-write design plus approved values |
| Exception Workbench | IMPLEMENTED | Existing read-only typed attention/triage includes GoldTier ambiguity | D-009 and current workbench | Assignment, notes, SLA, routing, escalation, notification deferred | Open an ambiguous Search case in Attention Queue | Existing queue and orchestration tests | Q-016 |
| Audit Trail | PARTIAL | Case events record early Search and durable target checkpoints; HR console exposes a bounded safe operation timeline | Current event owners; NIST minimization guidance | Not a production compliance audit; HR diagnostic timeline is process-local | Inspect case activity and console timeline | Activity, API projection, and console tests | Actor-attributed durable provider-diagnostic policy |
| Mongo persistence | IMPLEMENTED | Explicit optional schema-v6 case envelope persists initial Search, target provenance, recovery and incremental ledger state with CAS/no replay; exact schema-v1–v5 reads remain supported | D-033/D-058 / ADR-006 | Single-instance POC; physical runs require an allowlisted disposable Mongo database | Restart a disposable Mongo-backed synthetic case | Raw compatibility/recovery/no-replay tests; physical Mongo | Production durability/retention design |
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

- Search early: from bounded initial identity after SG eligibility and before optional
  ACRA bootstrap or evidence collection.
- Resolve: exact existing ID is retained; ambiguous candidates stop for human review;
  no match follows the new-customer path.
- Synchronize: Shell then Policy if new; exact existing customers skip both and Amend
  the retained ID. Both paths use same-ID read-back.
- Protect: attempted-but-not-completed mutation state is uncertain and never replayed
  automatically. Related-party dispatch remains blocked.
- Test: HR safe console plus end-to-end synthetic Mock onboarding and recovery suites.

### ACRA

- Local Mock is the safe default and provides deterministic synthetic operations.
- Official API Marketplace Mock is a distinct explicit opt-in `MOCK` mode in activation
  state `MOCK_INTEROPERABILITY_OBSERVED`. Bounded authorized token, entity, shareholder,
  and schema-only capital observations exist; Garden relationships remain unavailable.
- Generic sandbox remains a separate partial scaffold; dormant BizFile is not composed;
  none of these lanes is Live.
- Test: provider-mode diagnostics, governance checkers, strict connector tests, and SG
  onboarding regressions.
