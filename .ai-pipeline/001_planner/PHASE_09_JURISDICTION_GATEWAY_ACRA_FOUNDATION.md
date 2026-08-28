# Phase 09 — Jurisdiction Decision Gateway & ACRA Retrieval Foundation

**Project:** Delta Capita FYP — Zero-Touch Onboarding / Client Lifecycle Management (CLM)  
**Phase type:** Bounded feature development  
**Planner status:** Ready for Execution after the remediation branch is merged into `main`  
**Current accepted baseline before remediation merge:** `7199c94`  
**Predecessor:** Phase 08 + pre-next-development baseline remediation and independent Quality Gate

---

# 1. Purpose

Delta Capita onboards companies from multiple jurisdictions. The backend therefore must not assume that every onboarding request should immediately call ACRA.

The immediate architectural requirement is to introduce a **jurisdiction decision gateway** at the beginning of onboarding:

```text
Onboarding Request
        ↓
Collect available jurisdiction evidence
        ↓
Resolve country / jurisdiction
        ↓
Registry Provider Router
        ↓
Singapore → ACRA
Other recognised jurisdiction → provider not implemented
Unknown / conflicting jurisdiction → controlled review/block state
```

The current POC remains **Singapore / ACRA only**.

This phase establishes the routing foundation without expanding the implementation to foreign registry integrations.

The second goal is to make the current **ACRA Mock retrieval contract explicit and sponsor-readable**, so Delta Capita can understand what company information the POC currently retrieves and later provide the necessary domain mappings into GoldTier.

---

# 2. Inputs and Evidence Used for This Plan

This plan is based on:

- the current repository baseline after Phase 08;
- the pre-next-development re-baseline;
- the completed baseline remediation;
- the independent remediation Quality Gate;
- Delta Capita sponsor feedback captured in the existing project handoff;
- existing ACRA, IDP, ownership/UBO, CLM and Mock GoldTier boundaries.

The latest independent gate concluded:

```text
PASS — READY FOR NEXT DEVELOPMENT PLANNING
```

No jurisdiction or registry-routing functionality currently exists.

---

# 3. Current Pipeline Before Phase 09

The current implemented POC flow remains:

```text
UEN
  ↓
ACRA company profile
  ↓
Canonical Singapore entity
  ↓
PDF / Local PDF Text IDP
  ↓
Document comparison / review
  ↓
Ownership / UBO analysis
  ↓
CLM readiness
  ↓
Mock GoldTier
  ↓
COMPLETED / review / technical failure
```

Important current properties:

- `OnboardingService` directly depends on an ACRA-specific connector.
- ACRA retrieval is currently one `fetch_company(uen)` operation.
- The current request starts with a UEN and no jurisdiction field.
- Country fields exist downstream but are not used for routing.
- The current canonical validator requires Singapore.
- Ownership parties may contain a country field, but this is not a registry-routing decision.
- All application repositories remain process-local/in-memory.
- MongoDB remains an optional connectivity diagnostic only.
- The normal document provider is Local PDF Text IDP.
- GoldTier remains Mock-only.
- The workflow already has typed review/terminal states, call-stopping behaviour and in-process checkpoints that can be reused.

---

# 4. Sponsor Requirement

The sponsor wants the onboarding pipeline to determine which corporate registry should be used according to the company's jurisdiction.

Conceptually:

```text
Singapore → ACRA
Australia → future ASIC/provider
Malaysia → future provider
Hong Kong → future provider
Other jurisdictions → future provider
```

Only the Singapore path should be implemented now.

The jurisdiction may eventually come from:

1. optional user-supplied company country/jurisdiction;
2. existing company/case data;
3. upstream system/database information;
4. uploaded document / IDP information;
5. other future trusted sources.

This phase must build a model that can support those sources later, but it should only implement sources that are actually available at the start of the current pipeline.

---

# 5. Core Design Principle

**Jurisdiction resolution and registry-provider routing are separate responsibilities.**

Do not implement:

```text
if country == SG:
    call ACRA
elif country == AU:
    ...
```

inside generic onboarding business logic.

Instead:

```text
Available evidence
      ↓
JurisdictionResolver
      ↓
JurisdictionResolution
      ↓
RegistryProviderRouter
      ↓
Registry provider
```

The resolver determines **where the company belongs**.

The router determines **which registry provider is available for that jurisdiction**.

---

# 6. Phase 09 Scope

Phase 09 should implement only the following bounded capabilities.

## 6.1 Jurisdiction Observation Model

Introduce a source-aware representation for a jurisdiction observation.

Conceptually:

```text
JurisdictionObservation
    jurisdiction
    source
    observed_at
    source_reference?
    confidence?
```

Suggested source types:

```text
USER_INPUT
IDENTIFIER_FORMAT
EXISTING_CASE
DOCUMENT_IDP
UPSTREAM_SYSTEM
```

Not every source needs to be active in this phase.

For Phase 09, the implemented inputs are expected to be:

```text
USER_INPUT
IDENTIFIER_FORMAT
```

The remaining source types may be represented only if doing so keeps the design clean and does not create fake data.

Do not fabricate existing-case or document evidence before those stages actually exist.

---

# 7. Omitted-Jurisdiction Compatibility Rule

The existing POC starts with only a Singapore-shaped UEN.

To preserve the current happy path without silently assuming every company is Singaporean, Phase 09 should use the following explicit compatibility rule:

```text
No explicit jurisdiction supplied
+
identifier satisfies the current accepted Singapore UEN format
        ↓
JurisdictionObservation
    jurisdiction = SG
    source = IDENTIFIER_FORMAT
        ↓
resolved jurisdiction = SG
```

This is a **POC routing observation**, not a claim that identifier format is always legally authoritative.

It must be visible in provenance.

Do NOT implement:

```text
missing country → silently default SG
```

---

# 8. Explicit User Input

The onboarding start request should accept an **optional** jurisdiction/country-of-incorporation input.

Preferred API representation:

```text
country_of_incorporation: Optional[str]
```

The backend remains authoritative for validation and normalisation.

The frontend may present a country selector, but it should submit stable country codes rather than infer provider logic.

For the current sponsor environment, the architecture should at minimum understand the known jurisdiction codes:

```text
SG
AU
MY
HK
```

Only:

```text
SG
```

has an implemented registry provider.

Do not add ASIC or any foreign registry connector.

Do not silently map arbitrary free text to a country using an LLM.

---

# 9. Jurisdiction Resolution Rules

The resolver must be deterministic.

## 9.1 No usable observations

```text
→ JURISDICTION_UNRESOLVED
```

No registry provider should be called.

## 9.2 One usable observation

```text
SG
→ RESOLVED(SG)
```

or:

```text
AU
→ RESOLVED(AU)
```

The router then determines provider availability.

## 9.3 Multiple agreeing observations

Example:

```text
USER_INPUT = SG
IDENTIFIER_FORMAT = SG
```

Result:

```text
RESOLVED(SG)
```

Retain both observations.

## 9.4 Conflicting observations

Example:

```text
USER_INPUT = AU
IDENTIFIER_FORMAT = SG
```

Result:

```text
JURISDICTION_CONFLICT
```

Do NOT pick one source based on:

- ordering;
- confidence;
- source type;
- hard-coded precedence;
- "ACRA is more authoritative";
- current POC scope.

No registry provider should be called.

The safe observations involved in the conflict should be retrievable for review.

---

# 10. Jurisdiction Resolution Result

Introduce a result object conceptually equivalent to:

```text
JurisdictionResolution
    status
    resolved_jurisdiction?
    observations[]
    resolved_at
```

Suggested statuses:

```text
RESOLVED
UNRESOLVED
CONFLICT
```

Do not overload ACRA errors to represent jurisdiction decisions.

---

# 11. Registry Provider Routing

Introduce a provider-neutral routing boundary after jurisdiction resolution.

Conceptually:

```text
RegistryProviderRouter.resolve(SG)
        ↓
ACRA provider adapter
```

For Phase 09:

| Jurisdiction | Behaviour |
|---|---|
| SG | Route to existing ACRA implementation |
| AU | `REGISTRY_PROVIDER_NOT_IMPLEMENTED` |
| MY | `REGISTRY_PROVIDER_NOT_IMPLEMENTED` |
| HK | `REGISTRY_PROVIDER_NOT_IMPLEMENTED` |
| unresolved | stop before router/provider call |
| conflict | stop before router/provider call |

The generic onboarding orchestration should not import ASIC or future-country source DTOs.

---

# 12. Provider-Neutral Registry Boundary

The current runtime interface is ACRA-specific:

```text
AcraConnector.fetch_company(uen)
```

Do not delete or unnecessarily rewrite the current connector.

Add the smallest clean provider-neutral seam around it.

Conceptually:

```text
RegistryProvider
    fetch_company_profile(identifier)
```

and:

```text
AcraRegistryProviderAdapter
    → existing AcraConnector
```

The current strict ACRA behaviour must remain intact:

- source DTO reconstruction;
- requested-UEN binding;
- safe source mapping;
- safe provenance;
- connector error handling;
- Mock/sandbox behaviour already present in the codebase.

Do not build new mock/sandbox/live switching.

Do not implement the proposed synthetic `ACRA+` provider.

Those decisions remain deferred pending sponsor confirmation.

---

# 13. Workflow Behaviour

The jurisdiction gateway must run **before ACRA retrieval**.

Target beginning of pipeline:

```text
Start Onboarding
      ↓
Build available jurisdiction observations
      ↓
Resolve jurisdiction
      ↓
 ┌─────────────────────────────┐
 │ conflict / unresolved?      │
 └──────────────┬──────────────┘
                │ YES
                ↓
        controlled stop/review
                │
                └── no registry / ownership / GoldTier calls

                NO
                ↓
      Registry Provider Router
                ↓
        provider implemented?
        ┌───────┴────────┐
       NO               YES
       ↓                 ↓
provider-not-        fetch company
implemented             profile
       ↓                 ↓
controlled stop       existing flow
```

---

# 14. Controlled Outcomes / Error Codes

Introduce explicit, safe states/codes rather than reusing unrelated ACRA failures.

Expected concepts:

```text
JURISDICTION_UNRESOLVED
JURISDICTION_CONFLICT
REGISTRY_PROVIDER_NOT_IMPLEMENTED
```

These should be represented through the existing workflow/review machinery where reasonable.

Requirements:

- no false completion;
- no unhandled exception;
- no ACRA call for conflict/unresolved/non-SG unsupported provider;
- no ownership call;
- no Mock GoldTier call;
- case remains retrievable;
- safe jurisdiction evidence is visible to the frontend/API.

Do not invent a sponsor resolution action if none has been approved.

A non-actionable controlled review/block state is acceptable for Phase 09.

---

# 15. Existing Singapore Behaviour

The normal existing Singapore happy path must continue to work.

Example:

```text
Start:
UEN = current valid Singapore test UEN
country_of_incorporation = omitted

Observation:
SG from IDENTIFIER_FORMAT

Resolution:
SG

Provider:
ACRA

Then:
existing ACRA profile
→ canonical entity
→ document / IDP
→ ownership / UBO
→ readiness
→ Mock GoldTier
```

Explicit:

```text
country_of_incorporation = SG
```

should also work.

---

# 16. Conflict Example

Example:

```text
UEN = current valid Singapore-formatted UEN
country_of_incorporation = AU
```

Evidence:

```text
USER_INPUT      → AU
IDENTIFIER_FORMAT → SG
```

Expected:

```text
JURISDICTION_CONFLICT
```

Then:

```text
ACRA calls = 0
ownership calls = 0
GoldTier calls = 0
```

Do not silently continue with ACRA.

---

# 17. Unsupported Jurisdiction Example

A request that resolves cleanly to a recognised non-Singapore jurisdiction should not call ACRA.

Example conceptual result:

```text
Jurisdiction:
AU

Resolution:
RESOLVED

Registry routing:
REGISTRY_PROVIDER_NOT_IMPLEMENTED
```

The system should expose a controlled case state.

This does **not** mean ASIC should be implemented.

---

# 18. Relationship to Documents / IDP

The sponsor eventually wants jurisdiction to be detectable from uploaded documents.

The current pipeline performs registry retrieval before document processing.

Phase 09 should **not** reorder the whole pipeline or implement pre-registry IDP.

Instead:

- design the jurisdiction observation model so `DOCUMENT_IDP` can be added later;
- document that document-derived jurisdiction cannot yet participate in the initial decision because document processing currently occurs later;
- avoid pretending this source is already active.

A later phase may introduce pre-registry document intake or reconciliation.

---

# 19. Relationship to Existing Database / MongoDB

The sponsor also described using existing knowledge/data about the company.

The current application does not have durable onboarding/company persistence.

MongoDB is currently only an optional connectivity/read-only diagnostic.

Therefore Phase 09 must NOT:

- build Mongo repositories;
- look up onboarding cases from MongoDB;
- invent company collections;
- persist jurisdiction decisions into MongoDB;
- create migrations/schemas.

The architecture should simply allow `EXISTING_CASE` / `UPSTREAM_SYSTEM` observations to be added later.

Current storage remains through the existing process-local repositories.

---

# 20. Ownership / Related-Party Compatibility

Do not redesign the ownership engine.

Current ownership parties already have an optional country field.

The future architecture may eventually need to resolve a registry provider for each legal entity encountered in a cross-border ownership graph.

Phase 09 should only ensure the root-company routing design does not prevent that future extension.

Do not recursively fetch foreign registries in this phase.

Do not modify current UBO calculation rules.

---

# 21. Canonical Validation

The current canonical legal-entity validation is Singapore-specific.

Do not globally make the canonical model multi-country in this phase unless required for clean call-stopping.

Correct ordering should be:

```text
jurisdiction resolution
→ provider routing
→ SG selects ACRA
→ ACRA result
→ existing Singapore canonical validation
```

A non-SG unsupported case should stop **before** Singapore canonical validation.

Do not weaken the existing Singapore validation merely to accept unsupported foreign entities.

---

# 22. API Changes

Update the appropriate start request model(s) to support:

```text
country_of_incorporation?: string
```

The normal and demo start paths should remain contractually consistent where applicable.

The response/case summary should expose enough safe routing information to understand:

```text
observations
resolution status
resolved jurisdiction
registry provider / provider status
```

Do not expose internal secrets or raw provider URLs.

Do not make frontend code infer the provider.

---

# 23. Frontend Changes

On the **Start onboarding** view:

Add an optional country/jurisdiction field.

Preferred behaviour:

```text
Country of incorporation (optional)
```

Possible presented choices for the current POC:

```text
Not specified
Singapore
Australia
Malaysia
Hong Kong
```

Stable codes should be sent to the backend:

```text
SG
AU
MY
HK
```

The UI should make it clear that:

- Singapore/ACRA is currently implemented;
- other jurisdictions are recognised for orchestration demonstration only;
- no foreign registry integration exists yet.

Do not make non-SG options appear as working external integrations.

The case/review surface should render backend-authored jurisdiction outcomes.

---

# 24. ACRA Mock Retrieval Foundation

The current ACRA Mock should remain the active Singapore provider path.

This phase should make its contract explicit rather than expanding it into an invented full registry.

Current operation:

```text
fetch_company(uen)
```

Current data includes, where available:

```text
registration number / UEN
legal name
country of incorporation
entity type
registration/incorporation date
entity status
registered address
source/provider metadata
retrieval timestamp
safe source reference
```

The current ACRA Mock does NOT provide:

```text
directors/officers
shareholders
related parties
relationships
ownership percentages
registry documents
business activities
```

Do not fabricate these fields merely to make the API look complete.

---

# 25. Required ACRA Mock API Specification

Create/update:

```text
docs/contracts/ACRA_MOCK_API_PROFILE.md
```

The document must be sponsor-readable.

Include at minimum:

## Purpose

Explain that this describes the project-owned current ACRA Mock/provider contract used by the POC.

## Current operation

Document:

```text
fetch_company / equivalent project endpoint or interface
```

## Input

Example:

```text
UEN / registration identifier
```

## Response fields

For each field document:

```text
field name
type
required/optional
meaning
canonical target field
example
```

## Registered-address structure

Document nested fields individually.

## Source/provenance metadata

Document safe provider/environment/timestamp/reference concepts.

## Current Mock scenarios

Document the scenario catalogue and what each scenario is intended to exercise, without presenting synthetic fixtures as real ACRA data.

## Empty/not-found behaviour

Clearly explain the difference between:

```text
entity not found
malformed response
provider unavailable
```

## Error semantics

Document current safe error classes/codes.

## Known limitations

Explicitly list the missing registry capabilities:

```text
officers
directors
shareholders
related parties
relationships
ownership
```

## Future mapping section

Provide a table structure:

| ACRA / Source Field | Canonical Field | GoldTier Field | Transformation / Notes |
|---|---|---|---|
| ... | ... | `TBD_SPONSOR` | ... |

Unknown GoldTier fields must remain:

```text
TBD_SPONSOR
```

Do not invent sponsor mappings.

---

# 26. Mapping Preparation

Prepare the mapping framework conceptually as:

```text
ACRA / registry source
        ↓
Canonical internal model
        ↓
validation / transformation
        ↓
GoldTier
```

Phase 09 should document this chain.

Do not alter final GoldTier payloads unless absolutely required for compatibility.

Do not invent:

- final GoldTier field names;
- value lists;
- related-party mappings;
- authentication;
- final source authority.

---

# 27. Data Provenance

Jurisdiction evidence must preserve provenance.

At minimum:

```text
source
jurisdiction
observed_at
```

If a source provides a safe source reference, retain it.

Confidence should only exist when the underlying source genuinely provides a confidence value.

Do not create fake confidence scores for:

```text
USER_INPUT
IDENTIFIER_FORMAT
```

---

# 28. Audit / Timeline

Where consistent with the existing event/timeline model, record important routing events such as:

```text
JURISDICTION_OBSERVED
JURISDICTION_RESOLVED
JURISDICTION_CONFLICT
REGISTRY_PROVIDER_SELECTED
REGISTRY_PROVIDER_NOT_IMPLEMENTED
```

Use existing event patterns instead of creating a second unrelated audit system.

---

# 29. Security Requirements

Maintain existing security boundaries.

Requirements include:

- no credentials in responses/logs;
- no raw Mongo URI;
- no internal registry secrets;
- no arbitrary dynamic imports/providers from user input;
- backend owns provider selection;
- country input cannot directly select a class/module/URL;
- safe bounded validation of request values;
- no user-supplied registry endpoint;
- no weakening of existing ACRA response validation;
- no weakening of strict PDF behaviour;
- no weakening of GoldTier call-stopping.

---

# 30. Required Tests

Add focused tests for the jurisdiction layer.

At minimum:

## Resolver tests

1. explicit SG only → resolved SG;
2. identifier-format SG only → resolved SG;
3. explicit SG + inferred SG → resolved SG with both observations;
4. explicit AU + inferred SG → conflict;
5. no usable evidence → unresolved;
6. malformed country input → bounded validation failure;
7. observations are preserved and ordered deterministically.

## Router tests

8. SG → ACRA provider;
9. AU → provider not implemented;
10. MY → provider not implemented;
11. HK → provider not implemented;
12. unresolved → no provider lookup/call;
13. conflict → no provider lookup/call.

## Integrated onboarding tests

14. omitted jurisdiction + valid current Singapore UEN preserves current happy path;
15. explicit SG preserves current happy path;
16. explicit conflicting AU stops before ACRA;
17. supported-resolution/non-SG case stops safely;
18. no ownership call on conflict;
19. no GoldTier call on conflict;
20. no downstream calls on provider-not-implemented state;
21. case remains retrievable after controlled stop;
22. restart/resume/idempotency behaviour does not duplicate ACRA calls within existing process-local guarantees.

## ACRA regression tests

23. existing ACRA Mock scenarios still behave identically;
24. malformed/not-found/provider failures retain existing safe semantics;
25. requested-UEN binding remains enforced;
26. existing canonical Singapore validation remains enforced after ACRA retrieval.

## Frontend tests

27. country input is optional;
28. omitted input submits correctly;
29. stable country code is sent;
30. jurisdiction conflict is rendered from backend state;
31. provider-not-implemented is rendered honestly;
32. frontend does not claim ASIC/foreign registry integration;
33. existing Singapore start/PDF/review flow remains functional.

---

# 31. Call-Stopping Requirements

These are important acceptance criteria.

For:

```text
JURISDICTION_UNRESOLVED
JURISDICTION_CONFLICT
REGISTRY_PROVIDER_NOT_IMPLEMENTED
```

verify:

```text
ACRA call count = 0
ownership provider call count = 0
GoldTier call count = 0
```

For resolved Singapore:

```text
ACRA call count = expected existing behaviour
```

Do not let unsupported paths accidentally reach Singapore-specific canonical validation.

---

# 32. Backward Compatibility

Existing Phase 08 / remediation behaviour must remain intact.

Specifically preserve:

- current valid Singapore synthetic UEN scenarios;
- Local PDF Text IDP;
- document comparison/review;
- ownership/UBO arithmetic;
- existing cycle/incomplete-path review behaviour;
- CLM readiness;
- Mock GoldTier search/write sequence;
- target call-stopping;
- finalisation recovery;
- frontend backend-authorised review actions;
- 5 MiB default upload messaging;
- process-local persistence boundary;
- Mongo connectivity-only boundary.

---

# 33. Non-Goals

Phase 09 MUST NOT implement:

```text
ASIC integration
Malaysia registry integration
Hong Kong registry integration
any foreign live registry
ACRA officers/directors retrieval
ACRA shareholders retrieval
ACRA related-party retrieval
ACRA relationships retrieval
cross-border recursive registry traversal
ACRA+ synthetic provider
new configurable mock/sandbox/live provider system
live ACRA verification
Mongo onboarding persistence
workflow-engine replacement
full reconciliation engine
source-precedence policy
document-first/pre-registry IDP redesign
new UBO thresholds/business rules
real GoldTier integration
GoldTier field mappings not supplied by sponsor
Ready-for-Approval
RBAC/authentication redesign
```

---

# 34. Sponsor Assumptions / TBDs

Keep the following explicitly open:

```text
TBD_SPONSOR:
- authoritative source precedence by field;
- whether user jurisdiction should override or merely contribute evidence;
- use of document-extracted jurisdiction before registry lookup;
- use of existing GoldTier/client data as jurisdiction evidence;
- exact ACRA live/sandbox API contract;
- expanded ACRA operations for officers/shareholders/relationships;
- GoldTier source-to-domain field mappings;
- final UBO jurisdiction-specific rules;
- review/resolution policy for jurisdiction conflicts.
```

Phase 09 should detect conflicts, not resolve them through invented policy.

---

# 35. Documentation Updates

Update relevant current documentation:

```text
docs/architecture/ARCHITECTURE.md
docs/contracts/ACRA_MOCK_API_PROFILE.md
docs/decisions/DECISION_LOG.md
docs/sponsor-questions/OPEN_QUESTIONS.md
README.md
```

Where appropriate, add a focused architecture document such as:

```text
docs/architecture/PHASE_09_JURISDICTION_GATEWAY.md
```

Document:

- decision gateway;
- evidence/resolution model;
- registry-provider router;
- Singapore-only implementation scope;
- unsupported/non-actionable foreign provider behaviour;
- current ACRA Mock contract;
- future extension points;
- explicit non-goals.

---

# 36. Acceptance Criteria

Phase 09 is accepted only if all of the following are true:

1. Jurisdiction resolution occurs before registry retrieval.
2. Optional user jurisdiction input is supported.
3. Omitted input preserves the existing Singapore POC through an explicit `IDENTIFIER_FORMAT → SG` observation.
4. The omission rule is visible in provenance and is not a silent default.
5. Agreeing observations resolve deterministically.
6. Conflicting observations do not use hidden precedence.
7. Conflict produces a typed controlled outcome.
8. No ACRA call occurs on conflict.
9. No ACRA call occurs on unresolved jurisdiction.
10. SG resolves to the existing ACRA path.
11. Recognised AU/MY/HK routes to controlled `REGISTRY_PROVIDER_NOT_IMPLEMENTED`.
12. No foreign registry connector is implemented.
13. The generic router does not directly depend on future provider source DTOs.
14. Existing ACRA strict validation/mapping remains intact.
15. Existing Singapore happy-path scenarios remain green.
16. Ownership/UBO logic is not redesigned.
17. Mongo remains connectivity-only.
18. No sponsor-unconfirmed source-precedence rule is added.
19. The frontend exposes optional jurisdiction without implying foreign integration exists.
20. The backend remains authoritative for routing and actions.
21. A sponsor-readable `ACRA_MOCK_API_PROFILE.md` exists and accurately documents current fields, behaviours and limitations.
22. Unknown GoldTier mappings remain `TBD_SPONSOR`.
23. Full backend tests pass.
24. Focused regressions pass.
25. Ruff passes.
26. strict mypy passes.
27. contract tests pass.
28. frontend typecheck passes.
29. frontend tests pass.
30. frontend production build passes.
31. secret/security checks pass.
32. GoldTier existing validation remains green.
33. lifecycle/regression checks remain green.
34. `git diff --check` passes.
35. No Critical/High unresolved implementation issue remains before Quality Gate.

---

# 37. Expected Quality Commands

Use the repository's current authoritative commands.

At minimum include:

```text
backend pytest
focused Phase 09 / zero-touch / provider regressions
Ruff
strict mypy
contract tests
secret tests
secret scanner
GoldTier validation
frontend typecheck
frontend tests
frontend build
dependency checks
Windows/demo lifecycle where applicable
git diff --check
```

A live Mongo connection is not a Phase 09 acceptance requirement.

A live ACRA connection is not a Phase 09 acceptance requirement.

---

# 38. Execution Report

Execution must create:

```text
.ai-pipeline/reports/PHASE_09_EXECUTION.md
```

Include:

1. Executive Summary
2. Scope Implemented
3. Files Changed
4. Jurisdiction Domain Model
5. Resolution Rules
6. Omitted-Input Compatibility Rule
7. Registry Router
8. ACRA Adapter / Compatibility
9. API Changes
10. Frontend Changes
11. ACRA Mock API Specification
12. Call-Stopping Behaviour
13. Security Review
14. Tests and Exact Results
15. Sponsor Assumptions Preserved
16. Non-Goals Confirmation
17. Remaining Risks
18. Readiness

End with exactly:

```text
READY FOR PHASE 09 QUALITY GATE
```

or:

```text
NOT READY FOR PHASE 09 QUALITY GATE
```

---

# 39. Quality Gate

Phase 09 must receive an independent report-only Quality Gate after Execution.

Quality Gate must verify:

- implementation matches this plan;
- resolver behaviour;
- no hidden precedence;
- provider-neutral routing;
- correct SG → ACRA path;
- foreign provider call-stopping;
- no foreign registry implementation;
- no Mongo persistence scope creep;
- ACRA Mock contract truthfulness;
- frontend/backend contract compatibility;
- regression safety;
- security/secrets;
- documentation;
- full quality command results.

Expected report:

```text
.ai-pipeline/reports/PHASE_09_QUALITY_GATE.md
```

Final gate verdict:

```text
PASS — READY FOR NEXT PHASE
```

or:

```text
FAIL — REMEDIATION REQUIRED
```

---

# 40. Future Work After Phase 09

Phase 09 intentionally creates the foundation for later work.

Likely later phases include:

```text
expanded registry acquisition
→ entity details
→ officers/directors
→ shareholders
→ related parties
→ relationships

multi-source reconciliation
→ existing data
→ documents
→ registry

human review / exception management
workflow persistence / resumability
case-management dashboard
operational analytics
GoldTier mapping/integration
```

Those should be separately scoped after Phase 09 is independently accepted.

---

# 41. Phase Principle

The result of Phase 09 should change the beginning of the POC from:

```text
UEN
→ ACRA
```

to:

```text
Available company information
→ jurisdiction evidence
→ jurisdiction resolution
→ registry provider routing
→ Singapore / ACRA
→ existing onboarding pipeline
```

while remaining truthful that **Singapore / ACRA is the only implemented external-registry path in the current POC**.
