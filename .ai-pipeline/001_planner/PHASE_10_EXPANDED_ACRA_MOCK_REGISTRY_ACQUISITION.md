# Phase 10 — Expanded ACRA Mock Registry Acquisition

**Project:** Delta Capita FYP — Zero-Touch Onboarding / Client Lifecycle Management (CLM)  
**Phase type:** Bounded feature development  
**Predecessor:** Phase 09 — Jurisdiction Decision Gateway & ACRA Retrieval Foundation  
**Status:** Ready for Execution after Phase 09 is committed and merged into `main`

## 1. Purpose

Phase 09 established:

```text
Available jurisdiction evidence
→ jurisdiction resolution
→ registry provider routing
→ Singapore / ACRA
→ existing onboarding pipeline
```

Phase 10 should make the Singapore registry step more realistic.

Today, the ACRA path is still essentially:

```text
fetch_company(identifier)
→ one company profile
```

Sponsor feedback indicates that registry retrieval should eventually represent multiple steps:

```text
identify entity
→ retrieve entity profile
→ retrieve officers/directors
→ retrieve shareholders / related parties
→ retrieve relationships
→ build ownership / corporate hierarchy
```

Phase 10 implements this against the **project-owned ACRA Mock boundary only**. It must not claim that these operations or schemas are the authoritative subscribed/live ACRA API while Q-012 remains open.

---

## 2. Core Objective

Evolve the Singapore path from:

```text
ACRA
→ one company profile
```

to:

```text
Resolved Singapore
      ↓
ACRA Registry Provider
      ↓
Entity Profile
      ↓
Officers / Directors
      ↓
Ownership Parties / Shareholders
      ↓
Relationships
      ↓
Normalized Registry Acquisition
      ↓
Existing canonical / ownership pipeline
```

The goals are:

- architectural realism;
- decomposed registry operations;
- strict source validation;
- operation-level provenance;
- safe empty/partial/failure semantics;
- compatibility with the existing deterministic ownership/UBO engine;
- a sponsor-readable Mock API contract.

This is **not live ACRA integration**.

---

## 3. Accepted Baseline to Preserve

Phase 09 is independently accepted. Preserve:

- optional jurisdiction input;
- source-aware jurisdiction observations;
- `IDENTIFIER_FORMAT -> SG` compatibility evidence;
- deterministic `RESOLVED / UNRESOLVED / CONFLICT`;
- no hidden source precedence;
- SG routes to ACRA only;
- AU/MY/HK are recognised but provider-not-implemented;
- explicit SG identifiers must pass current Singapore UEN eligibility before ACRA;
- `REGISTRY_IDENTIFIER_NOT_ELIGIBLE` stops before any provider call;
- strict ACRA DTO reconstruction and identity binding;
- truthful Mock/Sandbox labels;
- process-local persistence;
- MongoDB diagnostic-only boundary;
- existing ownership/UBO arithmetic;
- Mock GoldTier only.

---

## 4. Open Sponsor Dependencies

### Q-012 — Live ACRA contract/access

Still open:

- authoritative endpoints/operations;
- official request/response schemas;
- authentication;
- not-found/error semantics;
- service/rate limits;
- TLS/mTLS/private-CA requirements;
- authorised sandbox/live access;
- whether officers/shareholders/relationships are separate official operations.

Therefore, all new Phase 10 operation contracts are **project-owned Mock contracts**.

### Q-015 — Jurisdiction evidence authority

Still open:

- source precedence;
- reviewer authority;
- conflict resolution;
- correction/resume semantics.

Phase 10 must not introduce these rules.

---

## 5. Scope

Implement a bounded expanded Singapore registry-acquisition model with separate concepts for:

1. entity profile;
2. officers/directors;
3. ownership parties/shareholders;
4. relationships;
5. acquisition operation status/result;
6. normalization into existing internal models.

No foreign registry implementation is allowed.

---

## 6. Provider-Neutral Acquisition Boundary

Keep generic onboarding provider-neutral.

Do not push ACRA-specific DTOs into generic orchestration.

Introduce the smallest clean contract, conceptually equivalent to:

```text
RegistryProvider
    retrieve_entity_profile(identifier)
    retrieve_officers(identifier)
    retrieve_ownership_parties(identifier)
    retrieve_relationships(identifier)
```

Equivalent naming/structure is acceptable if it fits the current codebase better.

Requirements:

- each acquisition step is distinguishable;
- each step can fail independently;
- each step retains provenance;
- generic orchestration consumes normalized results;
- no user input can select endpoints, modules or provider classes.

Avoid building a large generic framework.

---

## 7. ACRA Adapter

Evolve the existing ACRA adapter rather than bypassing it.

```text
RegistryProvider
      ↓
AcraRegistryProviderAdapter
      ↓
project-owned ACRA connector operations
```

Preserve:

- Singapore identifier eligibility guard;
- strict DTO reconstruction;
- requested/returned identity binding;
- safe error translation;
- provenance controls;
- Mock/Sandbox labels;
- no raw exception projection;
- no dynamic provider selection.

Do not implement new mock/sandbox/live switching.

Do not implement `ACRA+`.

---

## 8. Project-Owned Mock Operations

Suggested operation concepts:

```text
GET_ENTITY_PROFILE
GET_OFFICERS
GET_OWNERSHIP_PARTIES
GET_RELATIONSHIPS
```

These are project concepts, not claims about official ACRA endpoint names.

Each operation should define:

- bounded request;
- strict response DTO;
- deterministic synthetic fixtures;
- operation-specific provenance;
- empty behavior;
- not-found behavior where applicable;
- malformed-response behavior;
- provider failure behavior.

---

## 9. Entity Profile

Retain the current supported entity/profile fields:

```text
registration number / UEN
legal name
country of incorporation
entity type
registration/incorporation date
entity status
registered address
source metadata
retrieval timestamp
safe source reference
```

Do not fabricate additional live ACRA fields.

---

## 10. Officers / Directors

Add a project-owned normalized officer model, e.g.:

```text
RegistryOfficer
    officer_id
    name
    role
    appointment_date?
    cessation_date?
    country/nationality?
    provenance
```

Use only fields needed for the POC and sponsor mapping discussion.

Do not invent official ACRA role codes or legal semantics.

---

## 11. Ownership Parties / Shareholders

Add a project-owned ownership-party model able to represent:

```text
natural-person owner
legal-entity owner
ownership percentage
country/jurisdiction where known
registration identifier where applicable
provenance
```

Conceptually:

```text
RegistryOwnershipParty
    party_id
    party_type
    name
    registration_identifier?
    country?
    ownership_percentage?
    provenance
```

Ownership percentage is evidence, not a UBO conclusion.

Do not alter final UBO threshold/business rules.

---

## 12. Registry Relationships

Add a bounded project-owned relationship representation, conceptually:

```text
RegistryRelationship
    relationship_id
    owned_entity_id
    owner_party_id
    relationship_type
    ownership_percentage?
    provenance
```

Keep relationship types minimal.

Prefer alignment with the existing ownership vocabulary so the system does not develop two incompatible relationship models.

Do not add control-based UBO rules without sponsor confirmation.

---

## 13. Integration With Existing Ownership Engine

The existing system already has:

```text
OwnershipProvider
→ Party / OwnershipRelationship
→ graph validation
→ deterministic path calculation
→ provisional UBO analysis
```

Do not build another ownership calculator.

Preferred Phase 10 direction:

```text
ACRA Mock acquisition
        ↓
registry ownership evidence
        ↓
normalization / adapter
        ↓
existing ownership graph input
        ↓
existing OwnershipAnalysisService
```

The normal Singapore demonstration should increasingly show registry-acquired ownership evidence feeding the existing ownership engine.

If the current synthetic `InputDrivenOwnershipProvider` is still required for fault-injection/regression scenarios, keep it behind an explicit developer/test boundary.

Do not remove useful cycle/incomplete/provider-failure test scenarios merely to force all synthetic behavior into ACRA.

---

## 14. Registry Acquisition Result

Introduce a provider-neutral acquisition aggregate/result conceptually similar to:

```text
RegistryAcquisitionBundle
    entity_profile
    officers[]
    ownership_parties[]
    relationships[]
    operation_results[]
    retrieved_at
```

Requirements:

- bounded collection sizes;
- deterministic ordering;
- strict internal consistency;
- provenance retained;
- no UBO conclusion stored in the bundle;
- browser-safe projection only.

---

## 15. Operation Status

Do not treat acquisition as one opaque success/failure.

Track concepts similar to:

```text
ENTITY_PROFILE       COMPLETE
OFFICERS             COMPLETE / EMPTY / FAILED
OWNERSHIP_PARTIES    COMPLETE / EMPTY / FAILED
RELATIONSHIPS        COMPLETE / EMPTY / FAILED
```

Exact enums/names should fit the current architecture.

Do not build a durable workflow engine.

The purpose is operation-level observability and testability.

---

## 16. Empty / Missing / Partial Semantics

A successful HTTP/provider operation does not automatically mean usable data exists.

Distinguish, where meaningful:

```text
EMPTY_REGISTRY_RESPONSE
ENTITY_NOT_RETURNED
NO_OFFICERS_RETURNED
NO_OWNERSHIP_PARTIES_RETURNED
NO_RELATIONSHIPS_RETURNED
MISSING_EXPECTED_REGISTRY_DATA
```

Not every empty collection is an error.

Define clearly:

- which collections may legitimately be empty;
- which data is mandatory for the current scenario;
- which missing data should block;
- which missing data should continue with a warning/indeterminate ownership result.

Do not invent sponsor policy. Keep uncertain business semantics explicit.

---

## 17. Failure Semantics

Use typed safe failures, reusing existing conventions where possible.

Possible bounded concepts:

```text
REGISTRY_ENTITY_NOT_FOUND
REGISTRY_OPERATION_MALFORMED_RESPONSE
REGISTRY_OPERATION_UNAVAILABLE
REGISTRY_OPERATION_TIMEOUT
REGISTRY_EXPECTED_DATA_MISSING
```

Avoid unnecessary error-code proliferation.

No raw external exception should reach the browser.

---

## 18. Workflow Integration

The conceptual Singapore path should become:

```text
Resolve SG
      ↓
Select ACRA
      ↓
Validate SG identifier
      ↓
Retrieve entity profile
      ↓
Retrieve officers
      ↓
Retrieve ownership parties
      ↓
Retrieve relationships
      ↓
Normalize acquisition
      ↓
Canonical entity + registry evidence
      ↓
Existing document / ownership / UBO / readiness / Mock GoldTier flow
```

Preserve the accepted document stage order unless a small change is strictly required.

Do not perform document-first jurisdiction extraction in this phase.

---

## 19. Provenance

Every operation and important record must retain:

```text
provider/source
environment
operation type
retrieved_at
safe source reference
```

Do not overwrite source observations with downstream canonical decisions.

Do not expose raw connector URLs or credentials to the browser.

---

## 20. API / Browser Projection

Expose enough safe information to demonstrate multi-step registry acquisition.

Candidate fields:

```text
operation
status
record_count
provider
environment
retrieved_at
safe evidence summary
```

Where officer/ownership/relationship evidence is shown, expose only normalized POC-required fields.

Do not expose:

- raw provider payloads;
- authorization headers;
- credentials;
- internal connector configuration;
- class/module names;
- unsafe source references.

---

## 21. Frontend

Update the registry/evidence presentation so a Singapore case can show something like:

```text
ACRA Registry Acquisition

Entity Profile       Complete
Officers             Complete
Ownership Parties    Complete
Relationships        Complete
```

and normalized supporting records where useful.

Keep the labels truthful:

- ACRA business source;
- Mock/Sandbox-shaped project environment;
- not verified live ACRA;
- no foreign provider integration.

Do not build the full case-management/exception dashboard in this phase.

---

## 22. ACRA Mock API Profile

Expand:

```text
docs/contracts/ACRA_MOCK_API_PROFILE.md
```

For every project-owned operation, document:

- purpose;
- request;
- response schema;
- required/optional fields;
- nested structures;
- provenance;
- synthetic payload examples;
- empty behavior;
- error behavior;
- known limitations.

State prominently:

> These are project-owned Mock contracts used to exercise the POC architecture. They are not asserted to be the authoritative subscribed ACRA API contract while Q-012 remains open.

---

## 23. Sponsor Mapping Readiness

Expand mapping tables:

| Mock ACRA Field | Canonical/Internal Field | GoldTier Field | Transformation / Notes |
|---|---|---|---|
| ... | ... | `TBD_SPONSOR` | ... |

Use sections for:

- entity;
- officer/director;
- ownership party;
- relationship.

Do not invent GoldTier mappings or value lists.

---

## 24. Synthetic Scenario Catalogue

Use/extend the existing project-owned Mock scenarios deliberately.

At minimum cover:

1. normal SME with officers and direct owners;
2. legal-entity shareholder;
3. multiple shareholders;
4. multi-level ownership where compatible with the current graph;
5. legitimately empty optional collection;
6. missing expected ownership data;
7. malformed operation response;
8. failure at a later acquisition step.

Do **not** create a separate `ACRA+` provider.

All scenarios must be labelled synthetic.

---

## 25. Golden-Case Readiness

Prepare fixture structures so sponsor-approved golden cases can later define:

```text
entity profile
officers
ownership parties
relationships
expected canonical entity
expected ownership graph
expected UBO result
expected discrepancies
expected GoldTier mapping
```

Current synthetic fixtures must not be called sponsor-approved golden cases.

---

## 26. Phase 09 Call-Stopping Must Remain Intact

For:

```text
JURISDICTION_UNRESOLVED
JURISDICTION_CONFLICT
REGISTRY_PROVIDER_NOT_IMPLEMENTED
REGISTRY_IDENTIFIER_NOT_ELIGIBLE
```

verify:

```text
registry acquisition operations = 0
IDP = 0
ownership = 0
GoldTier = 0
```

Only an eligible resolved Singapore request may begin ACRA acquisition.

---

## 27. Operation Call Counts

For a normal Singapore case, independently verify expected operation calls.

Preferred:

```text
entity profile       = 1
officers             = 1
ownership parties    = 1
relationships        = 1
```

If the implementation intentionally combines operations, document and justify the bounded alternative.

No silent duplicate acquisition on re-entry/idempotent paths.

---

## 28. Bounds / Security

Registry ownership structures are untrusted external data.

Enforce/reuse bounded limits for:

```text
max officers
max ownership parties
max relationships
```

Requirements:

- strict DTO validation;
- bounded strings/collections;
- no uncontrolled recursion;
- safe malformed-response handling;
- identity binding;
- safe provenance;
- no URL/provider injection;
- no dynamic imports;
- no secrets;
- existing ownership graph/path limits remain active.

Do not claim production-scale limits or SLA.

---

## 29. Non-Goals

Phase 10 MUST NOT implement:

```text
live ACRA
authoritative official ACRA schema claims
ASIC / SSM / Hong Kong / foreign registry connectors
ACRA+
new provider mode framework
Mongo application persistence
multi-source reconciliation engine
source precedence
human-review redesign
case-management dashboard redesign
workflow-engine replacement
new UBO threshold/rules
control-based UBO rules
real GoldTier
final GoldTier mappings
Ready-for-Approval
production RBAC
```

---

## 30. Required Documentation

Update where applicable:

```text
docs/contracts/ACRA_MOCK_API_PROFILE.md
docs/architecture/ARCHITECTURE.md
docs/architecture/README.md
docs/decisions/DECISION_LOG.md
docs/sponsor-questions/OPEN_QUESTIONS.md
README.md
```

Recommended:

```text
docs/architecture/PHASE_10_EXPANDED_REGISTRY_ACQUISITION.md
```

---

## 31. Required Tests

At minimum cover:

### Acquisition contract
1. entity-profile retrieval;
2. officers retrieval;
3. ownership-party retrieval;
4. relationship retrieval;
5. deterministic ordering;
6. provenance preservation;
7. collection bounds;
8. malformed response;
9. later-step provider failure;
10. legitimate empty optional collection;
11. missing expected data.

### Integrated SG path
12. valid SG performs expected operations;
13. canonical entity remains correct;
14. registry ownership evidence reaches the existing ownership analysis;
15. no duplicate acquisition on supported re-entry;
16. browser acquisition summary is safe/truthful.

### Phase 09 blockers
17. unresolved → zero acquisition;
18. conflict → zero acquisition;
19. provider-not-implemented → zero acquisition;
20. identifier-not-eligible → zero acquisition.

### Existing regressions
21. document review remains intact;
22. ownership cycle/incomplete cases remain safe;
23. Mock GoldTier call-stopping remains intact;
24. finalisation recovery remains intact;
25. no false completion.

### Frontend
26. operation statuses render;
27. counts/statuses are backend-authored;
28. Mock/Sandbox labeling remains truthful;
29. empty/partial acquisition is not presented as full success;
30. foreign/blocker cases do not display fake ACRA acquisition.

---

## 32. Acceptance Criteria

Phase 10 is accepted only if:

1. Singapore registry acquisition is decomposed into explicit bounded operations.
2. Generic orchestration remains provider-neutral.
3. Phase 09 routing/identifier protections remain intact.
4. No acquisition occurs for any Phase 09 blocker.
5. Existing entity-profile strict mapping remains intact.
6. Strict project-owned officer/director DTO/evidence exists.
7. Strict project-owned ownership-party DTO/evidence exists.
8. Strict project-owned relationship DTO/evidence exists.
9. Every operation preserves provenance.
10. Empty/partial results are distinguishable from complete usable data.
11. Malformed later-step responses fail safely.
12. Registry ownership evidence integrates with the existing ownership analysis.
13. No second UBO engine is introduced.
14. Existing UBO arithmetic/rules remain unchanged.
15. Synthetic scenarios are labelled synthetic.
16. No separate ACRA+ provider exists.
17. `ACRA_MOCK_API_PROFILE.md` truthfully documents the expanded Mock contract.
18. Unknown GoldTier mappings remain `TBD_SPONSOR`.
19. Frontend does not claim live ACRA.
20. Mongo remains diagnostic-only.
21. Q-012 and Q-015 remain open.
22. Full backend tests pass.
23. Focused Phase 10 tests pass.
24. Phase 09 adversarial tests remain green.
25. focused POC/provider regressions remain green.
26. Ruff passes.
27. strict mypy passes.
28. contract tests pass.
29. frontend typecheck/tests/build pass.
30. secret/security checks pass.
31. GoldTier validation remains green.
32. lifecycle checks remain green.
33. `git diff --check` passes.
34. no Critical/High unresolved implementation finding remains before Quality Gate.

---

## 33. Execution Report

Execution must create:

```text
.ai-pipeline/reports/PHASE_10_EXECUTION.md
```

Include:

1. Executive Summary
2. Scope Implemented
3. Files Changed
4. Registry Acquisition Contract
5. ACRA Mock Operations
6. Entity Profile
7. Officers / Directors
8. Ownership Parties
9. Relationships
10. Acquisition Bundle / Operation Status
11. Ownership Integration
12. Empty / Partial / Failure Semantics
13. API / Browser Projection
14. Frontend Changes
15. ACRA Mock API Profile Update
16. Sponsor Mapping Readiness
17. Security / Bounds
18. Call Counts / Call Stopping
19. Exact Test Results
20. Sponsor Dependencies Preserved
21. Non-Goals Confirmation
22. Remaining Risks
23. Readiness

End with exactly one:

`READY FOR PHASE 10 QUALITY GATE`

or:

`NOT READY FOR PHASE 10 QUALITY GATE`

---

## 34. Independent Quality Gate

After Execution, run a separate report-only Quality Gate.

It must independently verify:

- no fabricated live ACRA behavior;
- acquisition operations are genuinely decomposed;
- provider-neutral orchestration remains clean;
- strict trust boundaries remain;
- empty/partial responses are truthful;
- registry ownership evidence feeds the existing ownership engine;
- no parallel UBO calculation exists;
- Phase 09 call-stopping remains intact;
- synthetic scenarios remain clearly synthetic;
- frontend labels remain truthful;
- no Mongo persistence or foreign-provider scope creep;
- all quality/security/regression checks pass.

Expected report:

```text
.ai-pipeline/reports/PHASE_10_QUALITY_GATE.md
```

Verdict:

`PASS — READY FOR NEXT DEVELOPMENT PLANNING`

or:

`FAIL — REMEDIATION REQUIRED`

---

## 35. Future Work

After Phase 10, the next architectural step should be separately scoped:

```text
Existing system data
+
Documents / IDP
+
Registry acquisition
        ↓
Multi-source reconciliation
        ↓
Discrepancy detection
        ↓
Human intervention
        ↓
Checkpoint / resume
        ↓
Case management / exception queue
```

Do not mix this larger workflow into Phase 10.

---

## 36. Phase Principle

Phase 10 should make the Singapore registry part of the POC behave like a realistic multi-step acquisition:

```text
Singapore / ACRA
→ entity profile
→ officers
→ ownership parties
→ relationships
→ normalized registry evidence
→ existing onboarding / ownership pipeline
```

while remaining explicit that these operation contracts are **project-owned Mock behavior pending Q-012**, not verified live ACRA integration.
