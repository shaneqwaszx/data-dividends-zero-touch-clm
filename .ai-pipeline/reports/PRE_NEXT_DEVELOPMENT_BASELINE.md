# Pre-Next-Development Baseline

**Review date:** 2026-08-28  
**Review type:** Pre-development re-baseline / familiarisation  
**Repository:** Data Dividends — Zero-Touch Onboarding CLM  
**Implementation performed:** None

## 1. Executive Summary

The refreshed `main` baseline is commit `7199c94f4a823d421649d3bcaf7ccf3d4abdc020`, and the refreshed `origin/main` resolves to the same commit. The working tree was clean before this report, apart from a pre-existing inaccessible untracked directory warning for `apps/frontend/pytest-cache-files-89airr88/`.

Two independent teammate merge lines landed after the previous verifiable baseline, `99316df`:

1. A large frontend presentation change added purpose-based workspace tabs, a dashboard, richer evidence/review presentation, a simple ownership graph, a local reviewer workbench, manual field-correction controls, extensive CSS, and several narrative UI reports. It did not change backend API models, frontend TypeScript contracts, or backend workflow code.
2. A MongoDB connectivity helper added `MONGO_URI`, `pymongo==4.15.1`, client/ping/count functions, and `scripts/check_mongodb.py`. It did **not** connect MongoDB to onboarding, document, ownership, CLM, zero-touch, provider-binding, or target-ledger repositories. All application state remains process-local and is lost on restart.

The actual current sponsor path is still:

```text
UEN
  -> create staged case and synchronously fetch one ACRA company profile
  -> validate/map canonical Singapore entity
  -> wait for one PDF
  -> local PDF text extraction and registry comparison
  -> deterministic ownership load and UBO-path analysis
  -> CLM readiness evaluation and immutable target snapshot
  -> Mock GoldTier SEARCH -> conditional SHELL -> POLICY -> AMEND
  -> COMPLETED / MOCK_GOLDTIER_SUBMITTED
```

The flow is synchronous and linear inside one FastAPI process, but it has explicit in-memory checkpoints, expected-version writes, typed review pauses, document replacement/resume, per-case locking, idempotent start/resume, and a narrow replay-free target-finalization recovery path. It is not durable orchestration.

The code is **not yet jurisdiction-routing ready**. Country data exists in several source/domain/target fields, but there is no jurisdiction observation model, evidence resolver, provider-neutral registry interface, registry router, provider catalogue, country input, conflict state, unresolved state, or unsupported-jurisdiction state. The current request contains only a Singapore-format UEN; `OnboardingService` directly calls an `AcraConnector`; `SourceSystem` contains only `ACRA`; and shared canonical validation rejects any `country_of_incorporation` other than `SG`.

The ACRA Mock is a useful but narrow reusable adapter. It exposes one monolithic `fetch_company(uen)` operation returning entity identity/profile/address/provenance. It does not retrieve officers, directors, shareholders, related parties, relationships, ownership, or documents. A sandbox-shaped adapter exists, but its schema and authorization are explicitly provisional and live verification remains blocked by Q-012.

The current baseline is not green. Backend pytest has one accepted-scenario failure; contract discovery errors on the new frontend emoji under Windows default encoding; strict mypy and the Mongo check fail because `pymongo` is not installed in the active editable environment. These failures, plus the unresolved omission/default rule for an optional jurisdiction input, should be addressed or explicitly dispositioned before issuing the next implementation prompt.

## 2. Git / Repository State

| Item | Observed state |
|---|---|
| Branch | `main` |
| Local HEAD | `7199c94f4a823d421649d3bcaf7ccf3d4abdc020` |
| Refreshed `origin/main` | `7199c94f4a823d421649d3bcaf7ccf3d4abdc020` |
| Ahead/behind | None reported |
| Initial working tree | No tracked or accessible untracked changes reported |
| Git limitation | Git cannot inspect `apps/frontend/pytest-cache-files-89airr88/` because access is denied |
| Remote refresh | `git fetch --prune origin` succeeded; it discovered `origin/mongodb-integration` and `origin/ui-edits` and did not move `origin/main` |
| Mutating Git actions | None: no commit, push, merge, rebase, stash, reset, clean, checkout, or discard |

Recent main history verified after fetching:

```text
7199c94 Merge pull request #14 from shaneqwaszx/mongodb-integration
203cf74 Update mongo.py
7201d45 Update check_mongodb.py
1b012d8 Update mongo.py
f047b74 Update mongo.py
fc9663c Update mongo.py
65c4452 mongodb integration
fcf0881 Merge pull request #13 from shaneqwaszx/ui-edits
140053f ui edits
84ae188 edited UI and logic edits
99316df Phase 08 — Evidence-Driven Onboarding & Demo Realism (#11)
```

`99316df..7199c94` is the most defensible recent-change boundary available from Git. No files were removed. Thirteen files changed: six new narrative/UI documents, three frontend files, one new backend Mongo module, one backend configuration file, one backend project manifest, and one new script.

Neither `AGENTS.md`, `.agents/`, `.codex/`, nor `.ai-pipeline/` changed in this boundary. Repository-scoped instructions and skills were therefore not modified by these two merges.

## 3. Recent Changes on Main

### 3.1 Frontend merge (`fcf0881`, commits `84ae188` and `140053f`)

Changed application/test files:

- `apps/frontend/src/App.tsx`: 512 insertions and 79 deletions relative to `99316df`.
- `apps/frontend/src/styles.css`: 912 inserted lines.
- `apps/frontend/src/App.test.tsx`: 36 insertions and 10 deletions.

Added narrative files:

- `BUILD_COMPLETE.md`
- `COMPREHENSIVE_UI_AUDIT_REPORT.md`
- `EXECUTION_SUMMARY.md`
- `UI_IMPROVEMENTS_INDEX.md`
- `docs/UI_DEMO_QUICK_START.md`
- `docs/UI_IMPROVEMENTS_SUMMARY.md`

What changed and behavioural impact:

- The app now starts on a **Dashboard** tab. The actual UEN/PDF start form is under **Start onboarding**, so the form is no longer visible on initial render.
- New tabs expose **Dashboard**, **Start onboarding**, **Review**, **Logs**, and **Account info**. Review/account concepts are local presentation only; authentication and durable queues remain absent.
- The dashboard adds session metrics, a case identity strip, collapsed evidence/readiness detail, and navigation to review.
- The Review tab adds a local reviewer-workbench presentation and a manual `CORRECTED` field action using the existing document-review API.
- Ownership presentation now includes a simple breadth-first graph plus the pre-existing detailed table and backend-authored arithmetic.
- Document comparison and blocker explanations were restyled and made more explicit.
- Error text was mapped to friendlier messages.
- Developer controls are rendered only on the Start tab when their environment gate is enabled.

Why it appears to have changed: the commit content is presentation/demo polish and workspace reorganisation, not a backend workflow redesign.

Future impact:

- An optional jurisdiction input will need to be added to the Start tab, the request API function, and TypeScript types without making the dashboard or legacy/demo paths disagree.
- The manual field-correction UI is not integrated with zero-touch exception resolution. It mutates a document record through a legacy endpoint, refetches the automation summary, and does not automatically resume the zero-touch checkpoint. It also presents correction controls even where `available_actions` is empty. This should be reconciled before extending reviewer/jurisdiction conflict behaviour.
- The friendly `DOCUMENT_TOO_LARGE` message says 25 MB, while backend configuration defaults to 5 MiB.
- The added emoji cause the current Windows contract test's default CP1252 read of `App.tsx` to fail.

No backend route, Pydantic response, `types.ts`, or `api.ts` contract was changed by this merge. The new UI relies on existing endpoints.

### 3.2 MongoDB merge (`7199c94`, commits `65c4452` through `203cf74`)

Files changed:

- `apps/backend/app/config.py`: adds optional secret `mongo_uri`, populated from `MONGO_URI`.
- `apps/backend/app/mongo.py`: adds `create_mongo_client`, `ping_mongodb`, and `count_users` with a five-second server-selection timeout and explicit client closure.
- `apps/backend/pyproject.toml`: adds `pymongo==4.15.1`.
- `scripts/check_mongodb.py`: imports the helper, pings MongoDB, counts documents in hard-coded `FYP.users`, and prints only the count or safe exception class.

What it affects:

- It provides a local connectivity diagnostic and a future service boundary.
- It does not create a database schema, migration, onboarding repository, FastAPI dependency, health check, startup hook, or persistence adapter.
- It does not persist onboarding cases or influence the zero-touch pipeline.
- `FYP.users` is unrelated to the current CLM aggregates and must not be interpreted as an onboarding persistence design.

Current gaps introduced with the merge:

- No tests cover `app.mongo` or the check script.
- `.env.example`, the configuration reference, README, and security/persistence documentation do not define `MONGO_URI` or its operational boundary.
- The existing virtual environment was not refreshed; `pymongo` is absent, so the script and mypy fail.
- The editable package metadata is stale and lists only the older dependencies, which is why `pip check` can pass despite the missing newly declared package.

### 3.3 Changes not found

- No backend domain-model, workflow-state, connector-interface, ACRA, GoldTier, document, ownership, CLM, zero-touch, API-route, or repository implementation changed in the recent range.
- No backend tests were added or modified for MongoDB.
- No frontend API/type contracts changed.
- No repository instructions, skills, decision logs, sponsor questions, phase plans, or quality-gate reports changed.

## 4. Current End-to-End Pipeline

### 4.1 Actual normal zero-touch path

```text
POST /api/clm/zero-touch/cases { uen }
  -> ZeroTouchOrchestrator.create_case
  -> ClmOrchestrationService.create_case
  -> OnboardingService.create_staged_case
  -> configured AcraConnector.fetch_company(uen)
  -> strict AcraCompanyPayload reconstruction + requested-UEN binding
  -> map_acra_company -> CanonicalLegalEntity
  -> validate_entity (includes country == SG)
  -> in-memory OnboardingCase + CLM + automation records
  -> PENDING_INPUTS at DOCUMENT

POST /api/clm/zero-touch/cases/{case_id}/documents [PDF bytes]
  -> bounded upload checks
  -> LocalPdfTextIdpProvider (normal composition)
  -> four extracted fields + confidence + provenance
  -> compare with current canonical entity
  -> zero-touch document checkpoint
       -> auto-confirm if complete, matching and >= threshold
       -> otherwise WAITING_FOR_REVIEW / replacement or permitted action
  -> InputDrivenOwnershipProvider
  -> OwnershipAnalysisService graph validation + Decimal paths/aggregation
       -> ANALYZED or WAITING_FOR_REVIEW/TECHNICAL_FAILURE
  -> ClmOrchestrationService.evaluate
  -> immutable submission snapshot
  -> MockGoldTierConnector
       SEARCH
       -> MATCH_FOUND: stop for review
       -> NO_MATCH: SHELL -> POLICY -> AMEND
  -> COMPLETED / MOCK_GOLDTIER_SUBMITTED
```

### 4.2 Stage responsibilities

| Stage | Responsible module | Input | Output / persisted state | Dependency | Failure / pause | Next |
|---|---|---|---|---|---|---|
| Intake / registry | `services/onboarding.py` via `services/clm_orchestration.py` and `services/zero_touch_orchestration.py` | Validated 10-character synthetic UEN | `OnboardingCase`, canonical entity, events; CLM and automation records in memory | Configured `AcraConnector` | Not found becomes underlying onboarding `FAILED`, projected by zero-touch as registry review with no action; malformed/provider faults persist failure and become `TECHNICAL_FAILURE` | Wait for PDF when validated |
| Document upload | `services/document_processing.py` | Case ID, display name, `application/pdf`, bounded bytes | `DocumentProcessingRecord`; bytes/raw text not retained | Normal `LocalPdfTextIdpProvider`; Mock only through demo path | Invalid request rejected; accepted processing faults terminalise document `FAILED` and automation technical failure | Document checkpoint |
| Document checkpoint | `ZeroTouchOrchestrator` + document semantic assessment | Current unsuperseded documents and canonical entity | `AUTO_CONFIRMED`, `REVIEWED`, exception, or replacement history | None beyond stored evidence | Typed source conflict, low confidence, missing/text-unavailable; only source conflict advertises `KEEP_REGISTRY_VALUE`; replacement can supersede and auto-resume | Ownership |
| Ownership acquisition | `InputDrivenOwnershipProvider` + `OwnershipAnalysisService` | Case ID, canonical registration number/name | Case-linked ownership parties/relationships and provenance | UEN-keyed synthetic Mock provider | Provider/malformed graph -> `FAILED`; cycles/incomplete/limits -> `REVIEW_REQUIRED` | UBO analysis is part of same service |
| Ownership / UBO | `services/ownership_analysis.py` | Validated graph | Decimal direct/indirect paths, aggregated percentages, provisional candidates/issues | None | Cycle/incomplete/limit prevents definitive result and pauses automation | Readiness |
| Readiness | `services/clm_orchestration.py` | Current case, current documents, latest ownership result | `ClmReadinessAssessment`, warnings, status; later immutable snapshot | None | Any blocker prevents target submission; unexpected inconsistency becomes technical failure in integrated path | Mock target |
| GoldTier | `OnboardingService` target execution + `ClmOrchestrationService` finalisation | Immutable submission input | In-memory execution ledger, target outcome, receipt, CLM result | `MockGoldTierConnector` only | Existing party/partial amend -> review; malformed/provider failures -> failed; finalisation-only fault -> `RECOVERY_PENDING` without replay | Complete or stop |
| Frontend | `src/App.tsx`, `src/api.ts`, `src/types.ts` | UEN, PDF, case APIs | Browser-only current summary, evidence, tabs, polling | FastAPI | Stops polling on review/terminal/recovery; no durable session catalogue | User review/recovery as exposed |

The pipeline is synchronous/linear but not purely stateless. It has in-process checkpoints, case locks, compare-and-set versions, pause/resume, explicit document replacement, idempotent re-entry, and target-finalisation recovery. It has no durable queue, worker, scheduler, general retry policy, restart recovery, or distributed lock.

## 5. Backend Architecture Baseline

- FastAPI application composition is centralised in `app/composition.py` and instantiated once in `app/main.py`.
- External boundaries use protocols: `AcraConnector`, `IdpProvider`, `OwnershipProvider`, and `GoldTierConnector`.
- Registry business code is source-decoupled after `source payload -> canonical entity`, but the interface itself remains ACRA-specific.
- Domain aggregates are separate: onboarding case, document record, ownership record, CLM record, and zero-touch automation record.
- Every repository implementation used by composition is `InMemory...`; the new Mongo module is not imported by composition or any repository.
- Business orchestration uses a shared per-case in-process lock. Ownership, CLM, and zero-touch repositories use expected-version writes; document ordering has a locked insertion sequence.
- The target execution ledger is a dictionary inside `OnboardingService`, separate from the onboarding repository.
- Restart loses cases, documents, ownership, CLM state, automation state, provider bindings, target outcomes, idempotency bindings, and recovery state.
- No database migration system, persistence DTO, serialization-version policy, or repository transaction spanning aggregates exists.

## 6. Current Jurisdiction / Country Model

### Existing fields

| Concept | Location | Current meaning |
|---|---|---|
| `AcraCompanyPayload.country_code` | `connectors/acra.py` | Company incorporation country from the source DTO |
| `AcraAddressPayload.country_code` | `connectors/acra.py` | Registered-address country |
| `CanonicalLegalEntity.country_of_incorporation` | `domain/models.py` | Canonical incorporation country |
| `RegisteredAddress.country_code` | `domain/models.py` | Canonical address country, default `SG` |
| IDP `country_of_incorporation` | `domain/documents.py`, IDP providers | One of four provisional extracted/compared fields |
| `Party.country` | `domain/ownership.py` | Optional 2–3 character country on an ownership party |
| `SubmissionCanonicalEntity.country_of_incorporation` | `domain/target_submission.py` | Required target snapshot field |
| `SubmissionRegisteredAddress.country_code` | `domain/target_submission.py` | Target snapshot address country, default `SG` |
| GoldTier `countryOfIncorporation` | `connectors/goldtier_models.py` | Required provisional shell field |

### What does not exist

- No `jurisdiction` field on `StartOnboardingRequest`, `OnboardingCase`, zero-touch request, or frontend start form.
- No jurisdiction observation/evidence object with source, timestamp, reference, confidence, or authority.
- No resolver for multiple observations and no conflict representation.
- No incorporation-jurisdiction enum or canonical country normaliser shared across subsystems.
- No registry provider ID on the case or routing decision.
- No provider-neutral registry interface/factory/router.
- No `UNSUPPORTED_JURISDICTION`, `JURISDICTION_UNRESOLVED`, or `JURISDICTION_CONFLICT` state/error.
- No stored company/case database from which jurisdiction can currently be read.

### Hard-coded Singapore assumptions

- `StartOnboardingRequest` accepts only the current Singapore-shaped UEN pattern.
- `canonical_validation.validate_entity` requires `country_of_incorporation == "SG"`.
- `SourceSystem` contains only `ACRA`; source environments are only `MOCK`/`SANDBOX`.
- `OnboardingService` invokes ACRA before any document exists.
- Mock ACRA, Mock ownership roots/legal entities, target defaults, tests, fixtures, labels, and frontend copy assume Singapore/SG.

### Overlap to reconcile

Incorporation country, address country, ownership-party country, document-extracted country, and target country are different facts and should not be collapsed. The current names are mostly semantically distinct, but there is no common jurisdiction evidence model connecting them. The IDP country cannot currently influence initial registry routing because document processing occurs after ACRA retrieval. Adding another plain `country` field without a source/evidence model would duplicate rather than resolve this problem.

## 7. Current Registry Provider Architecture

The runtime registry abstraction is `AcraConnector.fetch_company(uen)`. Composition selects `MockAcraConnector` or `AcraSandboxConnector` using `ACRA_CONNECTOR_MODE`. This is a mode factory for one provider, not a jurisdiction router.

Reusable elements:

- strict source DTO validation and reconstruction;
- requested-identifier binding;
- source-to-canonical mapper;
- safe fixed connector errors;
- isolated transport/authorization/decoder seams;
- Mock vs sandbox mode selection without changing business logic;
- safe provenance and browser minimisation;
- connector conformance tests.

Missing gateway elements:

- source-neutral `RegistryProvider` contract;
- jurisdiction-to-provider decision object;
- resolver with multiple evidence inputs;
- provider catalogue/factory keyed by jurisdiction;
- controlled recognised-but-not-implemented outcome;
- controlled unknown/conflicting-jurisdiction outcome;
- provider selection persisted with the case;
- API/UI contract for optional jurisdiction.

The safest reuse is to wrap/adapt the existing ACRA connector behind a new source-neutral registry boundary, not to rename country fields or branch inside generic business logic.

## 8. Current ACRA Mock/API Implementation

### Current actual flow

```text
requested UEN
  -> AcraConnector.fetch_company(UEN)
  -> AcraCompanyPayload or None
  -> fresh strict reconstruction
  -> requested/returned UEN equality check
  -> map_acra_company
  -> CanonicalLegalEntity
  -> shared canonical minimum validation
```

This is one monolithic operation (**A**, not separate profile/officer/shareholder operations).

### Currently retrievable fields

| Information | Present? | Detail |
|---|---|---|
| UEN / registration number | Yes | Required |
| Legal/company name | Yes | Required |
| Incorporation country | Yes | 2–3 letter source country; current workflow later requires `SG` |
| Entity type | Yes | Required source code |
| Registration/incorporation date | Yes, optional | `date | None` |
| Entity status | Yes, optional | Bounded source code |
| Registered address | Yes, optional as a block | Block, street, optional unit/building, postal code, country |
| Source/provider identity | Yes | `ACRA` plus `MOCK` or `SANDBOX` |
| Source reference | Yes internally | Query-free HTTPS endpoint; omitted from browser case response |
| Retrieval timestamp | Yes | UTC required |
| Officers/directors | No | No DTO, operation, fixture, route, mapping, or test |
| Shareholders/owners | No | No ACRA ownership data |
| Related parties/relationships | No | Ownership is supplied by a separate synthetic provider |
| Ownership percentages | No | Not sourced from ACRA |
| Business activities | No | Documented as absent |
| Registry documents | No | No ACRA binary/document retrieval |

### Mock dataset

`MockAcraConnector` contains six recognised synthetic UENs: normal SME, incomplete address, target policy failure, partial amend, existing target party, and ownership-cycle cases. All use `SG`, one entity type, a fixed registration date and live status, with UEN-specific name/address. An unknown UEN returns `None`.

### Sandbox-shaped adapter

`AcraSandboxConnector` supports query-free HTTPS GET, injected authorization headers, timeout, no redirects, TLS verification, provisional status mapping, and an injected response decoder. `ProjectAcraResponseDecoder` validates a project-owned envelope. It is not generated from an approved ACRA subscriber contract. Q-012 still blocks the authoritative path, schema, auth, error semantics, rates, URL, and authorised live/sandbox verification.

### Errors

- 404/Mock miss -> `None` -> onboarding `ACRA_ENTITY_NOT_FOUND`.
- 401/403 -> `ACRA_AUTHENTICATION_ERROR`.
- 408/504 -> `ACRA_TIMEOUT`.
- 429/5xx/transport -> `ACRA_SERVICE_UNAVAILABLE`.
- invalid status/body/schema -> `ACRA_MALFORMED_RESPONSE`.
- identity mismatch -> `ACRA_RESPONSE_IDENTITY_MISMATCH`.
- mapping failure -> `ACRA_SOURCE_MAPPING_FAILED` or safe unexpected mapping code.
- untyped service faults are terminalised with safe fixed errors.

### Gap to expanded acquisition

The current connector can seed a canonical company profile, but it has no acquisition plan or partial-operation result for profile, officers, shareholders, and relationships. Expanding it later will require explicit operation DTOs, provenance per acquisition, partial/failure semantics, and a decision about which ownership source is authoritative. That expansion should not be mixed into the first jurisdiction-gateway phase.

## 9. IDP / Document Integration

- The normal provider is `LocalPdfTextIdpProvider`, not the Mock IDP.
- It reads at most 10 pages and 64,000 extracted characters using `pypdf` strict mode; it performs no OCR or network call.
- It extracts four labelled provisional fields: legal name, UEN, registered address, and country of incorporation.
- Confidence is deterministic parser evidence: `0.97`, `0.90`, `0.40`, or `0.00`; it is not calibrated ML confidence.
- Each field retains original value, normalised value, confidence, page/source reference, captured canonical value, comparison, review status/value/time/note.
- Uploaded bytes and full extracted text are not retained.
- Replacement creates fresh evidence, supersedes only the active current document, retains history, and re-enters zero-touch evaluation.
- IDP evidence currently arrives too late to choose the initial registry provider. Supporting document-derived jurisdiction before registry retrieval would require reordering/intake changes or a pre-registry document-extraction phase; neither exists now.
- The project has no source-precedence rule for user vs document vs stored vs registry jurisdiction. Q-005 and Q-014 remain relevant.

## 10. Related Parties / Ownership / UBO Baseline

### Party and relationship model

- `PartyType`: `LEGAL_ENTITY`, `NATURAL_PERSON`.
- Party has bounded ID/name, optional registration number, and optional 2–3 character country.
- `OwnershipRelationship` is directed from owned legal entity (`parent_party_id`) to owner (`child_party_id`).
- Relationship type is only `OWNERSHIP`; basis is only `SHARE_OWNERSHIP`.
- Every edge retains provider/environment/source reference/sourced-at provenance internally.
- Legal entities must be the owned/intermediate party; natural persons terminate paths.

### Calculation

- Iterative bounded traversal avoids recursion and tracks the active path for cycles.
- Direct paths have one edge; indirect paths have multiple edges.
- Effective percentage is the product of edge percentages using `Decimal`.
- Unique relationship-ID paths aggregate once.
- Direct and indirect percentages are separately summed, then aggregated.
- Default threshold is configurable inclusive `>= 25%`, explicitly provisional.
- Multiple paths are supported.
- Cycles, incomplete legal-entity leaves, depth limits, and path limits yield issues and indeterminate/review classifications rather than a false definitive result.
- Malformed/disconnected/unsafe graphs terminalise as `FAILED`.

### Current source and integration

- `InputDrivenOwnershipProvider` selects a UEN-keyed synthetic scenario; only `202400006F` maps to cycle, otherwise direct owners.
- Ownership does not call ACRA or GoldTier and does not mutate the canonical case.
- Related-party target preparation is only a summary marked `PENDING_SPONSOR_CONFIRMATION` / `RELATED_PARTY_WRITE_NOT_EXECUTED`.
- No `createRelatedParty`, hierarchy retrieval, `createRelationship`, or foreign registry integration exists.

### Jurisdiction-routing fit

The ownership graph can carry party country and is source-neutral enough for later jurisdiction-aware enrichment. Structural changes are still required for provider routing and incomplete external-registry branches: party country is optional field data, not a routing decision; parties do not each carry jurisdiction evidence/provenance; and no model represents “recognised jurisdiction but provider unavailable.” The deterministic graph/UBO arithmetic itself should not need redesign for the first gateway phase.

## 11. Provenance / Existing Data Sources

| Source | Current representation | Source/time/reference/confidence retained? |
|---|---|---|
| User/onboarding input | `requested_uen`, case timestamps/events | Input value and case time; no explicit source observation or confidence/reference |
| Existing system/database | None for onboarding | Mongo helper only counts unrelated `FYP.users`; no case lookup |
| Document/IDP | Per-field extraction/provenance and human review | Provider, environment, page, safe reference, value, confidence, captured canonical comparison, review time/note |
| ACRA | Canonical entity `SourceMetadata` | Source system, environment, internal HTTPS source link, UTC retrieval time; link omitted from browser |
| Mock providers | Explicit environment/provider labels | Yes at ACRA/document/ownership boundaries; proves synthetic source only |
| Ownership provider | Edge provenance; provider metadata on analysis | Provider/environment/time/reference on edges; browser omits internal reference |
| GoldTier | Request source context, target outcome/receipt/operation markers | Correlation/source-case/idempotency internally; browser sees minimised operation/result evidence |
| Human decision | Document field review or zero-touch resolution | Decision, reviewed value/time/note or exception resolution/time; no authenticated reviewer identity |

There is no general-purpose observation model capable of holding competing jurisdiction evidence. Existing source-specific provenance should inform its design, but no source-precedence policy should be inferred from it.

## 12. Workflow State / Error / Recovery Behaviour

### Status catalogues

- Onboarding: `REQUESTED`, `REGISTRY_FETCHED`, `VALIDATED`, target stages, `COMPLETED`, `REVIEW_REQUIRED`, `FAILED`.
- Document: `UPLOADED`, `PROCESSING`, `REVIEW_REQUIRED`, `REVIEWED`, `FAILED`.
- Ownership: `LOADING`, `LOADED`, `ANALYZING`, `REVIEW_REQUIRED`, `ANALYZED`, `FAILED`.
- CLM: `COLLECTING_EVIDENCE`, `REVIEW_REQUIRED`, `READY_FOR_MOCK_SUBMISSION`, `SUBMITTING`, `MOCK_GOLDTIER_SUBMITTED`, `FAILED`.
- Zero-touch: `PENDING_INPUTS`, `RUNNING`, `WAITING_FOR_REVIEW`, `RESUMING`, `RECOVERY_PENDING`, `COMPLETED`, `TECHNICAL_FAILURE`.
- Readiness stages include `READY`, `MISSING`, `IN_PROGRESS`, `REVIEW_REQUIRED`, `FAILED`, `BLOCKED`, `NOT_SUBMITTED`, `SUBMITTED`.

There is no general `RETRYING`, `WAITING`, `UNSUPPORTED`, or `INDETERMINATE` workflow status. Indeterminacy exists only in ownership candidate results. `RECOVERY_PENDING` is limited to Mock target finalisation.

### Required failure cases

| Situation | Current behaviour |
|---|---|
| Company cannot be identified | ACRA returns `None`; onboarding case becomes `FAILED/ACRA_ENTITY_NOT_FOUND`, while zero-touch exposes `WAITING_FOR_REVIEW` at Registry with no action. It is controlled but not resolvable in the current UI/API. |
| ACRA no data | Same as above |
| ACRA malformed data | Onboarding persists safe `FAILED`; CLM records failure; zero-touch becomes `TECHNICAL_FAILURE`; no later calls |
| Registry provider failure | Fixed safe connector error, persisted terminal failure, no automatic retry |
| Jurisdiction unknown | Not modelled; request has no such input/state |
| Ownership incomplete/cycle | Ownership `REVIEW_REQUIRED`; zero-touch typed exception; no target call and no click-through action |
| Unexpected provider/service exception | Accepted document/ownership/onboarding paths terminalise to fixed safe failure; zero-touch progression has a catch-all terminalisation boundary |
| Existing GoldTier match | Review exception after SEARCH only; no writes |
| Partial target amend | Review exception; cannot become completion |
| Target finalisation fault after retained outcome | `RECOVERY_PENDING`; later resume delegates to Phase 05 finalisation without repeating target operations |

The tested service boundaries are designed not to strand records in `PROCESSING`/`ANALYZING`. However, registry-not-found, ownership exceptions, and target-review states are intentionally non-progressable until new evidence or sponsor policy exists. All recovery guarantees disappear on backend restart.

No current state can correctly express recognised non-Singapore/unsupported provider or unresolved/conflicting jurisdiction.

## 13. GoldTier Touchpoints

### Runtime reads

- `search_party` is the only runtime GoldTier-shaped read.
- It is implemented only by `MockGoldTierConnector`.
- `retrieveParty`, `getPolicy`, and seeded hierarchy retrieval are present only in broader contract artefacts/validation documentation, not runtime connectors or orchestration.

### Runtime writes

- `create_shell_customer` only after `NO_MATCH`.
- `create_policy` after shell success.
- `amend_party` using canonical `/v1/eds/parties/{partyId}/amend` semantics.
- No `createRelatedParty` write and no `createRelationship`.

### Mapping and validation

- `mappers/goldtier.py` maps the immutable canonical snapshot to SEARCH/SHELL/POLICY/AMEND request DTOs.
- Source context and per-operation idempotency metadata are explicit.
- Connector responses are freshly revalidated and checked for operation-specific status/outcome shape.
- A process-local target ledger records attempted-operation prefix, minimal target outcome, and rich receipt.

### Mock/real boundary

- `GOLDTIER_CONNECTOR_MODE` permits only `mock`; composition always builds `MockGoldTierConnector`.
- PingFed/GoldTier environment variables in `.env.example` are unconsumed placeholders.
- Real authentication remains blocked by Q-008/D-018; Singapore mapping by Q-007/Q-009–Q-011; approval transition by Q-001; hierarchy reads by Q-002.

## 14. Frontend Baseline

- The application now defaults to a Dashboard with a prominent button that switches to Start onboarding.
- Start onboarding collects only a Singapore UEN and one PDF. Country/jurisdiction cannot be entered.
- A case can be reopened by case ID in the Start view.
- The dashboard displays current stage, case status/health, interventions, timing, case identity, progress, evidence/readiness, and Mock target operation evidence.
- Review shows active exceptions, evidence, server-authorised resolution buttons, replacement upload, and the newly added manual field-correction controls.
- Logs show the safe automation timeline.
- Account is an explicit unauthenticated placeholder.
- Ownership shows parties, a new simple graph, detailed directed relationships, provenance, path arithmetic, direct/indirect/aggregate percentages, provisional UBO classifications, and issues.
- ACRA data is shown as the canonical entity/profile, not as a separate raw ACRA response.
- `types.ts` mirrors current backend states and fields; it has no jurisdiction decision/provider fields.
- `api.ts` posts `{ uen }` for normal start and `{ uen, scenario }` for demo start. It has no jurisdiction parameter.

Likely future UI impact is small but cross-cutting: optional country/jurisdiction input, request type/body, case summary/routing result, unsupported/unresolved/conflict presentation, and tests. The UI must render actions/states authored by the backend rather than inventing provider choices. The separate normal/demo start paths must remain consistent.

## 15. Test / Quality Results

Commands were run against unmodified `main`. No dependency was installed and no failure was fixed.

| Command | Result |
|---|---|
| `git fetch --prune origin` | PASS; `origin/main` remained `7199c94` |
| `.\.venv\Scripts\python.exe -m pytest apps\backend\tests` | **FAIL** — 501 passed, 1 failed, 1 deprecation warning. `test_cycle_uen_fixture_passes_document_before_input_driven_cycle` expected an ownership-stage response but received a 503 body without `current_stage`. Focused inspection identified `IDP_PROCESSING_FAILED`; the synthetic PDF raises `PdfReadError: Broken xref table` under pinned `pypdf 5.6.1` strict parsing. |
| `.\.venv\Scripts\python.exe -m ruff check apps\backend scripts tests` | PASS |
| `.\.venv\Scripts\python.exe -m mypy apps\backend\app` | **FAIL** — 2 `import-not-found` errors for `pymongo`/`pymongo.errors`; 57 source files checked |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests\contract -p "test_*.py"` | **FAIL** — 44 run, 1 error. Windows default CP1252 cannot decode a newly added emoji byte in `App.tsx`; the contract test calls `Path.read_text()` without an encoding. |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_check_secrets.py"` | PASS — 5/5 |
| `.\.venv\Scripts\python.exe scripts\check_secrets.py` | PASS |
| `.\.venv\Scripts\python.exe -m unittest tests.test_phase_07_delivery_assets -v` | PASS — 4/4 |
| `.\.venv\Scripts\python.exe -m unittest tests.test_validate_goldtier_examples -v` | PASS — 5/5 |
| `.\.venv\Scripts\python.exe scripts\validate_goldtier_examples.py --if-present` | PASS normal classification — 19 valid, 19 invalid/quarantined, 48 not validated |
| `.\.venv\Scripts\python.exe -m pip check` | PASS, but the editable package metadata is stale and does not list newly declared `pymongo`; this result does not prove the merged dependency is installed |
| `.\.venv\Scripts\python.exe scripts\check_mongodb.py` | **FAIL** — `ModuleNotFoundError: No module named 'pymongo'`; no Mongo connection was attempted |
| `npm.cmd run typecheck` | PASS |
| `npm.cmd test` | Initial sandbox run could not spawn esbuild (`EPERM`); rerun with local child-process permission PASS — 42/42 |
| `npm.cmd run build -- --outDir <outside-repository>` | PASS — 29 modules; output intentionally directed outside the repository |
| `npm.cmd ls --all` | PASS / exit 0; only expected optional platform/feature packages reported absent |
| `.\.venv\Scripts\python.exe -m unittest tests.test_demo_lifecycle_windows -v` | PASS — 13/13 in 175.562 seconds; final launcher-owned processes cleaned up |

The inaccessible `apps/frontend/pytest-cache-files-89airr88/` directory remained uninspectable throughout. Final Git status still reported `main...origin/main` with no tracked or accessible untracked changes before report creation.

## 16. Code-vs-Documentation Discrepancies

1. Recent UI documents repeatedly say there is no MongoDB configuration/change and list MongoDB as future work. Current code now has `MONGO_URI`, `pymongo`, and a check script, although it still has no application persistence.
2. Recent UI documents describe the normal IDP as `MockIdpProvider`; current normal composition and launcher use `LOCAL_PDF_TEXT`. Mock IDP is demo/test-only.
3. Recent UI documents and frontend friendly errors say the upload maximum is 25 MB; backend default and `.env.example` are 5 MiB (`5,242,880` bytes).
4. `.env.example`, README configuration guidance, and `docs/integration/CONFIGURATION_REFERENCE.md` omit the newly consumed `MONGO_URI`.
5. Some new UI reports use non-existent class names such as `AcraMockConnector`/`GoldTierMockConnector`; code uses `MockAcraConnector`/`MockGoldTierConnector`.
6. `UI_IMPROVEMENTS_INDEX.md` calls the application “production-ready.” The authoritative README/security/architecture documents correctly state it is a process-local synthetic POC without durable persistence, RBAC, live integrations, production PDF controls, or Ready-for-Approval.
7. Historical Phase 08 quality reports record a green 502-test/44-contract/40-frontend baseline. Current main produces 501+1 backend failure, a contract encoding error, and 42 frontend tests. Those reports are historical evidence, not current-main truth.
8. The README correctly says state is process-local. The mere presence of `app/mongo.py` does not contradict that, but names such as “mongodb integration” and new top-level UI reports could mislead planners into assuming onboarding persistence now exists.
9. The new manual field-correction UI suggests a correction/re-evaluation capability, but it does not use the zero-touch exception resolution/resume boundary and is not covered by an end-to-end test.

## 17. Open Sponsor Dependencies Relevant to This Work

- **Q-012:** authoritative ACRA Business Profile API operation/schema/auth/error/rate/TLS/access. This blocks live ACRA binding, not a credential-free jurisdiction gateway or Mock ACRA work.
- **Q-005:** validation responsibility and source authority. This is directly relevant when user, document, stored, and registry jurisdiction observations disagree.
- **Q-014:** confidence and authenticated review policy. Relevant if jurisdiction observations carry confidence or require human conflict resolution.
- **Q-003:** final IDP document types/fields. Relevant before treating a document-derived country as an authoritative input.
- **Q-013:** document privacy/retention/security. Relevant if pre-registry documents are retained or processed earlier.
- **Q-004:** jurisdiction/policy-dependent UBO rule. It does not block the first router but blocks jurisdiction-specific UBO policy claims.
- **Q-002:** hierarchy retrieval. It blocks live complex ownership acquisition, not the gateway.
- **Q-006/Q-007:** related-party semantics and Singapore mapping. They block real related-party writes/final mapping, not gateway foundations.
- **Q-008/D-018:** real GoldTier/PingFed. Not a gateway blocker.
- **Q-001:** Ready-for-Approval semantics. Not a gateway blocker.

No current sponsor decision defines precedence among explicit user jurisdiction, document jurisdiction, existing-record jurisdiction, and inferred/current-scope jurisdiction. The first phase may implement conflict detection, but it must not invent precedence.

## 18. Risks / Technical Debt Before Next Phase

| Severity | Risk | Why it matters / required disposition |
|---|---|---|
| **HIGH** | Current main quality baseline is red | Backend accepted-scenario pytest and contract discovery fail. New development would make regressions harder to attribute. Remediate or formally baseline/waive each failure first. |
| **HIGH** | Mongo dependency/environment is inconsistent | Code imports a newly declared package absent from the active environment; mypy and the check script fail while `pip check` misleadingly passes due stale editable metadata. Refresh/install policy and tests/documentation need a separate remediation decision. |
| **HIGH** | No explicit omitted-jurisdiction rule | Optional input plus “unknown -> unresolved” conflicts with the current UEN-only happy path unless a clearly named current-scope default or UEN-format observation is approved. The Planner must specify this; it must not be silently coded. |
| **MEDIUM** | Registry abstraction is ACRA-specific | Adding country branches directly to `OnboardingService` would duplicate provider logic and make future providers unsafe. Introduce a source-neutral decision/router seam first. |
| **MEDIUM** | Singapore assumptions are widespread | Validator, DTO patterns, defaults, fixtures, labels, target mapping and tests assume SG. The first phase must isolate rather than globally remove these assumptions. |
| **MEDIUM** | New UI manual correction bypasses zero-touch action semantics | It calls the legacy document review endpoint even when the exception advertises no action and does not auto-resume. It is fail-safe in that it does not falsely complete, but it can mislead/strand a reviewer and complicate future jurisdiction conflict handling. |
| **MEDIUM** | No provenance model for jurisdiction observations | A plain request field cannot safely reconcile user/document/database/registry inputs. Build an explicit observation/resolution model without precedence. |
| **MEDIUM** | Mongo helper could be mistaken for persistence foundation | It has no repository adapters, schema, migration or CLM aggregate model. The gateway phase should remain process-local unless persistence is explicitly assigned. |
| **MEDIUM** | ACRA retrieval is monolithic and profile-only | It cannot satisfy a future officers/shareholders/relationships acquisition workflow without separate contracts and partial-failure semantics. Defer this expansion to a bounded later phase. |
| **MEDIUM** | Registry-not-found is represented inconsistently across aggregates | Underlying onboarding/CLM fail, while zero-touch shows a non-actionable registry review. New unresolved/unsupported states should not copy this ambiguity. |
| **LOW** | Frontend upload limit text is wrong | Says 25 MB while backend is 5 MiB; misleading operational guidance. |
| **LOW** | New narrative documents overstate readiness or use stale names | Planners should follow code and authoritative architecture/security documents. |
| **LOW** | Inaccessible cache directory limits local audit coverage | It is untracked/inaccessible and repeatedly noted in prior gates; resolve workstation permissions separately if complete untracked scanning is required. |

No teammate implementation of a jurisdiction gateway, source conflict resolver, registry router, or expanded ACRA acquisition was found. There is therefore no duplicate gateway implementation to preserve.

## 19. Reusable Components for the New Requirement

- `AcraConnector` implementations and strict source DTOs, wrapped behind a new provider-neutral registry seam.
- `build_acra_connector` for ACRA Mock/sandbox mode selection after the jurisdiction router selects ACRA.
- `AcraCompanyPayload` reconstruction, requested-UEN binding, safe connector errors, and `map_acra_company`.
- `CanonicalLegalEntity.country_of_incorporation` and ACRA/IDP country fields as downstream facts, not routing authority by themselves.
- Per-case locks, defensive repositories, expected-version transitions, safe events/errors, and browser projections.
- Zero-touch typed exception and stage machinery, extended with explicit jurisdiction outcomes rather than overloaded registry review codes.
- Document per-field provenance/confidence pattern as a design reference for jurisdiction observations.
- Ownership `Party.country` for future party-level enrichment; deterministic graph/UBO engine can remain unchanged initially.
- Frontend start/request/summary patterns and backend-authored action rendering.
- Existing connector conformance testing style and call-stopping tests.

## 20. Missing Components for the New Requirement

- `JurisdictionObservation` model: value, source kind, observed time, safe reference, optional confidence where genuinely supplied.
- `JurisdictionResolution` result: resolved, unresolved, conflict, and supporting observations.
- Explicit no-precedence conflict behaviour.
- Optional request/API/frontend jurisdiction field with normalisation and validation.
- A recorded and approved fallback for omitted input in the existing Singapore-only POC.
- Provider-neutral registry request/result/protocol.
- Registry decision router/catalogue mapping resolved Singapore to ACRA.
- Controlled recognised-non-Singapore provider-not-implemented outcome.
- Controlled unknown/conflicting jurisdiction states and API/UI projections.
- Tests proving no registry/provider/ownership/GoldTier call occurs when unresolved, conflicting or unsupported.
- Persistence shape for the decision in the current process-local aggregate; durable Mongo persistence is a separate concern.
- Expanded ACRA operations/data for officers/shareholders/relationships/ownership (later phase).

## 21. Recommended Scope for the FIRST Next Development Phase

The smallest coherent phase should establish only the jurisdiction foundation and Singapore routing:

1. Add a source-neutral jurisdiction observation/resolution domain model.
2. Accept an optional explicit user-supplied incorporation jurisdiction in the normal and demo start contracts.
3. Resolve observations deterministically:
   - no usable observation -> unresolved;
   - one distinct normalised jurisdiction or several agreeing observations -> resolved;
   - several distinct jurisdictions -> explicit conflict/review;
   - no source precedence or silent overwrite.
4. Record the resolution and evidence on the case/automation response using the current process-local repositories.
5. Introduce a provider-neutral registry router/adaptor seam.
6. Route resolved Singapore to the existing ACRA connector and preserve current ACRA mapping/validation.
7. Return a controlled provider-not-implemented/blocked outcome for recognised non-Singapore jurisdictions, with zero ACRA or downstream calls.
8. Return a controlled unresolved/conflict outcome for missing/unknown/conflicting evidence, with zero provider or downstream calls.
9. Update the frontend to collect optional jurisdiction and render the backend-authored decision/outcome.
10. Add focused compatibility, call-stopping, provenance, conflict, API and UI tests plus decision/contract documentation.

The Planner must explicitly state how the current UEN-only Singapore happy path behaves when the optional field is omitted. Two defensible choices exist: a documented `CURRENT_POC_SCOPE_DEFAULT` Singapore observation, or a documented Singapore-UEN-format observation. Either must be visible in provenance and must not override a conflicting explicit/document/stored observation. Treating omission as silently Singapore or silently unknown is not acceptable.

Do **not** include Mongo repository integration, foreign registry connectors, ACRA officers/shareholders expansion, synthetic “ACRA+”, live ACRA, configurable new live/sandbox switching, GoldTier changes, ownership redesign, or a workflow-engine rewrite in this first phase.

## 22. Likely Files / Modules Affected

No changes are made in this review. Likely first-phase touchpoints are:

- `apps/backend/app/main.py`
- `apps/backend/app/api_models.py`
- `apps/backend/app/composition.py`
- `apps/backend/app/domain/models.py` and/or a new focused jurisdiction domain module
- `apps/backend/app/domain/zero_touch.py`
- `apps/backend/app/services/onboarding.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/app/services/canonical_validation.py` (only to separate routing from Singapore-path validation)
- `apps/backend/app/connectors/acra.py` plus a new provider-neutral registry/router module
- current in-memory repository interfaces if the decision is stored in an aggregate
- `apps/backend/tests/test_onboarding*.py`, `test_acra_modes.py`, `test_zero_touch_orchestration.py`, provider-conformance tests, and new focused jurisdiction tests
- `apps/frontend/src/types.ts`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/App.tsx`
- `apps/frontend/src/App.test.tsx`
- `.env.example` only if a new non-secret configuration value is actually introduced
- `docs/decisions/DECISION_LOG.md`
- relevant architecture/contract/sponsor-question documentation
- the active `.ai-pipeline/001_planner/` phase prompt and its reports

`apps/backend/app/mongo.py` should not be a first-phase touchpoint unless durable persistence is separately and explicitly assigned.

## 23. Recommended Acceptance Criteria

1. Existing Singapore UEN/PDF happy path remains compatible under the Planner-approved omitted-jurisdiction rule and still reaches `MOCK_GOLDTIER_SUBMITTED` with zero post-start interventions.
2. Explicit `SG`/Singapore resolves to ACRA; exactly one ACRA retrieval occurs.
3. Optional user jurisdiction is represented as an observation with source and timestamp, not copied straight into canonical authority.
4. Agreeing observations resolve deterministically; conflicting observations produce a typed conflict/review outcome and expose all safe source summaries.
5. No source wins a conflict by ordering, confidence, or hard-coded priority unless a later sponsor-approved rule explicitly says so.
6. Recognised non-Singapore jurisdiction produces a controlled provider-not-implemented/unsupported state and performs zero ACRA, ownership, or GoldTier calls.
7. Unknown/no-evidence jurisdiction produces a controlled unresolved state and performs zero provider/downstream calls.
8. The router is provider-neutral; generic orchestration does not import foreign-provider payloads or add ASIC/other integrations.
9. Existing ACRA Mock and sandbox-shaped connector contracts remain unchanged except for an adapter/wrapper required by the new generic seam.
10. ACRA source DTOs still undergo fresh validation, requested-identifier binding, safe provenance checks, and canonical mapping.
11. API and frontend types include the optional input and backend-authored decision/status; UI does not infer the provider.
12. Jurisdiction decision and observations are retrievable from the current case after creation and review pause.
13. Tests cover explicit SG, omitted-input compatibility, recognised unsupported, unknown, agreement, conflict, malformed input, duplicate/resume behaviour, and call stopping.
14. No MongoDB dependency is introduced into the gateway unless separately authorised.
15. Full existing backend, contract, lint/type, frontend, secret, regression and lifecycle checks pass, or any pre-existing baseline failure is explicitly remediated/waived before phase acceptance.
16. Documentation states Singapore/ACRA is the only implemented provider and does not claim live ACRA, foreign registries, Ready-for-Approval, or sponsor-approved source precedence.

## 24. Development Readiness

The architecture contains useful seams, and a bounded first jurisdiction phase can be designed without waiting for live ACRA or foreign-registry sponsor inputs. However, the repository is not ready for an implementation prompt yet because:

1. current main has reproducible backend pytest and contract-test regressions;
2. the Mongo merge leaves the active dependency environment inconsistent and its check/mypy red;
3. the Planner has not specified the source/provenance rule that preserves or intentionally changes the current UEN-only path when optional jurisdiction is omitted; and
4. the new frontend manual-correction behaviour should be explicitly accepted, removed, or remediated before jurisdiction conflict actions are layered onto the same review surface.

Required next action: issue a small baseline-remediation/disposition task for the red checks and recent UI/Mongo integration gaps, then write the jurisdiction phase prompt with an explicit omitted-input rule and the bounded acceptance criteria above.

NOT READY FOR NEXT DEVELOPMENT PROMPT
