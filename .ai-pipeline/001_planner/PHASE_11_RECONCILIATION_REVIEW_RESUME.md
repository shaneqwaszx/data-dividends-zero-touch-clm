# Phase 11 — Multi-Source Reconciliation & Human Review/Resume Foundation

**Project:** Delta Capita FYP — Zero-Touch Onboarding / Client Lifecycle Management (CLM)  
**Phase type:** Bounded feature development  
**Predecessor:** Phase 10 — Expanded ACRA Mock Registry Acquisition  
**Status:** Ready for Execution after Phase 10 is committed and merged into `main`

## 1. Purpose

By the end of Phase 10, the accepted POC supports:

```text
Jurisdiction evidence
→ jurisdiction resolution
→ SG / ACRA routing
→ multi-step registry acquisition
→ canonical entity
→ document / IDP evidence
→ ownership / UBO analysis
→ CLM readiness
→ Mock GoldTier
```

The next missing capability is a reusable reconciliation layer that compares source facts, surfaces discrepancies, records a human decision, and resumes the current in-process workflow without silently overwriting source evidence.

Sponsor-aligned requirements already established:

- retrieve fresh source data even if existing data exists;
- compare/reconcile rather than overwrite;
- do not assume source authority on conflicts;
- discrepancies require human review;
- retain observations, discrepancies, and human decisions separately;
- save decisions and resume the stopped workflow;
- preserve provenance;
- build toward recoverable human-in-the-loop onboarding.

This phase builds the reconciliation/review/resume foundation only.

## 2. Core Objective

Target flow:

```text
Source observations
  ├─ user/onboarding input
  ├─ registry
  ├─ document/IDP
  └─ existing current-case facts
        ↓
Reconciliation Engine
        ↓
Field-level outcomes
        ├─ MATCH
        ├─ MISSING_IN_SOURCE
        ├─ CONFLICT
        ├─ UNVERIFIABLE
        └─ INVALID
        ↓
Discrepancy / Review Required
        ↓
Human Decision
        ↓
Canonical decision/update
        ↓
Safe resume
```

No automatic source precedence is allowed.

## 3. Accepted Baseline to Preserve

Preserve:

- Phase 09 jurisdiction observations/resolution;
- no hidden jurisdiction precedence;
- SG-only implemented registry route;
- Phase 09 blocker zero-call guarantees;
- Singapore identifier eligibility;
- Phase 10 four-operation ACRA Mock acquisition;
- acquisition bundle invariants;
- strict provenance/DTO boundaries;
- registry ownership feeding the existing Decimal ownership engine;
- existing UBO rules and graph/path limits;
- local PDF text IDP;
- existing CLM readiness;
- Mock GoldTier only;
- process-local persistence;
- MongoDB diagnostic-only boundary.

## 4. Open Sponsor Dependencies

### Q-012
Live/subscribed ACRA contract/access remains open. Phase 11 must not depend on live ACRA.

### Q-015
Source precedence, disagreement authority, reviewer authority, and production resume policy remain open.

Therefore:
- no automatic source winner;
- human decisions are explicit POC/operator decisions;
- no production authorization claim;
- no fake reviewer identity.

## 5. Initial Reconciliation Scope

Limit active fields to:

1. `legal_name`
2. `registration_identifier`
3. `registered_address`
4. `country_of_incorporation`

These already exist across current registry/canonical/document flows.

Do not expand into officer, shareholder, ownership, or GoldTier reconciliation yet.

## 6. Source Observation Model

Introduce a source-neutral model conceptually equivalent to:

```text
ReconciliationObservation
    observation_id
    field_name
    raw_value?
    normalized_value?
    source_kind
    source_system?
    environment?
    observed_at
    safe_source_reference?
    confidence?
    validity
```

Possible source kinds:

- USER_INPUT
- REGISTRY
- DOCUMENT_IDP
- EXISTING_CASE

Only populate sources that actually exist.

No fabricated database/upstream observations.

## 7. Field Reconciliation Result

Conceptually:

```text
FieldReconciliationResult
    field_name
    observations[]
    outcome
    discrepancy_id?
```

Active outcomes:

- MATCH
- MISSING_IN_SOURCE
- CONFLICT
- UNVERIFIABLE
- INVALID

Do not generate POSSIBLY_STALE in this phase unless a source-neutral, evidence-based rule already exists. It does not today.

## 8. Deterministic Comparison Rules

### Legal name
Reuse existing normalization where safe.

Formatting-only differences may match.

Do not over-normalize distinct legal names.

### Registration identifier
Exact normalized identifier equality.

Conflicting nonblank identifiers → CONFLICT.

### Country of incorporation
Normalized bounded country-code equality.

No source wins automatically.

### Registered address
Reuse existing address normalization/comparison logic.

No external geocoding or fuzzy service.

## 9. Missing vs Conflict vs Invalid

Distinguish:

```text
Registry has value
Document has no usable value
→ MISSING_IN_SOURCE
```

```text
Registry=A
Document=B
A != B
→ CONFLICT
```

```text
Document has extracted value but it cannot be safely normalized/validated
→ INVALID or UNVERIFIABLE
```

Do not collapse all three into a single conflict state.

## 10. First-Class Discrepancy Model

Conceptually:

```text
ReconciliationDiscrepancy
    discrepancy_id
    field_name
    outcome
    observations[]
    created_at
    status
    allowed_actions[]
    resolution?
```

Requirements:

- source observations immutable;
- losing values preserved;
- bounded evidence references;
- deterministic fingerprint/version semantics where appropriate;
- backend-authored allowed actions.

## 11. Human Review Decision

Conceptually:

```text
ReconciliationDecision
    discrepancy_id
    action
    selected_observation_id?
    corrected_value?
    decided_at
    note?
```

Preferred bounded Phase 11 actions:

- KEEP_REGISTRY_VALUE
- USE_DOCUMENT_VALUE

Only add ENTER_CORRECTED_VALUE if it can be implemented through a fully validated backend service without recreating the unsupported frontend-only manual correction previously removed.

No automatic registry-wins/document-wins rule.

## 12. Reviewer Authority Boundary

There is no production RBAC/authenticated reviewer identity.

Therefore:

- do not claim decisions are compliance-approved;
- store no fake name/email;
- decisions are explicit current-POC operator actions;
- Q-015 remains the blocker for production reviewer authority.

## 13. Canonical Decision Application

A decision may update canonical case data only through a typed backend service.

Requirements:

- preserve original observations;
- preserve discrepancy;
- preserve decision;
- record selected/corrected value and time;
- re-run canonical validation;
- do not mutate registry evidence;
- do not mutate document evidence;
- do not rewrite history.

## 14. Resume Semantics

When all blocking discrepancies are resolved:

```text
WAITING_FOR_REVIEW
→ RESUMING
→ re-evaluate
→ continue existing workflow
```

Requirements:

- idempotent resume;
- expected-version/fingerprint checks;
- resolving one of multiple discrepancies keeps the case blocked;
- repeated reads do not rerun registry/IDP;
- repeated resume does not duplicate ownership/GoldTier calls;
- durable restart recovery remains out of scope.

Do not build a general workflow engine.

## 15. Placement in Current Flow

Preferred bounded ordering:

```text
Jurisdiction / Registry Acquisition
        ↓
Document / IDP
        ↓
Multi-source Reconciliation
        ↓
if blocked:
    WAITING_FOR_REVIEW
        ↓
    explicit decision(s)
        ↓
    resume
        ↓
Ownership / UBO
        ↓
Readiness / Mock GoldTier
```

Do not move IDP before registry in Phase 11.

## 16. Existing Document Review Integration

Reuse the existing document evidence rather than creating a parallel evidence model.

Requirements:

- current document source-conflict behavior should feed the new reconciliation layer;
- preserve replacement-document behavior;
- preserve backend-authorized actions;
- do not reintroduce frontend-only correction;
- avoid two competing definitions of source conflict.

Legacy document-review APIs may remain if safely compatible.

## 17. Current-Case / Existing Data Boundary

Current application state is process-local.

`EXISTING_CASE` may mean facts already held in the current case.

Do not pretend MongoDB or GoldTier is an authoritative existing-client database unless real retrieval is implemented.

No Mongo persistence in Phase 11.

## 18. Provenance

Each observation retains where available:

- source kind;
- source/provider;
- environment;
- observed/retrieved time;
- safe reference;
- confidence only if genuinely supplied.

Each human decision retains:

- decision/action;
- selected/corrected value;
- decision time;
- optional bounded note;
- case/version/fingerprint context.

Observations, discrepancies, and decisions remain separate.

## 19. API

Expose safe reconciliation state, e.g.:

```text
reconciliation:
    status
    fields[]
    discrepancies[]
```

Expose:
- field;
- outcome;
- safe normalized values;
- source summaries;
- discrepancy status;
- allowed actions;
- decision summary.

Do not expose:
- raw PDF text;
- raw ACRA payload;
- connector URLs;
- credentials;
- raw exceptions;
- internal class/module names.

## 20. Review Endpoint

Add the smallest typed action required to resolve a discrepancy.

Requirements:

- case-bound;
- discrepancy-bound;
- version/fingerprint-bound;
- enum-bounded action;
- corrected value validated if supported;
- stale/replayed action fails safely;
- no arbitrary canonical JSON patch;
- backend decides if/when resume occurs.

## 21. Frontend

Add focused reconciliation/review presentation:

```text
Field
Registry value
Document value
Outcome
Evidence/source
Required action
Decision
```

For conflict:
- show both values;
- show only backend-authorized actions;
- do not visually imply source authority;
- display decision after resolution.

Preserve existing registry acquisition, document replacement, ownership/UBO, and Mock labels.

Do not build the full exception queue/dashboard.

## 22. Case-Level Reconciliation State

Add a bounded case-level state such as:

- NOT_STARTED
- MATCHED
- REVIEW_REQUIRED
- RESOLVED
- FAILED

Exact names should fit the repo.

The model must be self-validating.

A case cannot be RESOLVED while blocking discrepancies remain unresolved.

## 23. Business vs Technical Failure

Business discrepancy:

```text
CONFLICT / missing comparable evidence
→ WAITING_FOR_REVIEW
```

Technical reconciliation failure:

```text
malformed internal evidence / unexpected processing failure
→ TECHNICAL_FAILURE
```

Do not send technical failures into human review as if they were value disagreements.

## 24. Call-Stopping

When reconciliation is blocked:

```text
ownership = 0
GoldTier = 0
```

Registry/IDP may already have run.

Reads/review-page loads must not rerun providers.

After final valid resolution:

```text
ownership proceeds once
GoldTier proceeds only through existing readiness logic
```

## 25. Required Scenarios

At minimum:

1. all four fields match;
2. legal-name formatting-only match;
3. legal-name conflict;
4. registration identifier conflict;
5. country conflict;
6. address conflict;
7. document missing one field;
8. document invalid/unverifiable field;
9. multiple simultaneous discrepancies;
10. resolve one of several → still blocked;
11. resolve all → resume;
12. replacement document removes applicable discrepancy and resumes.

## 26. Decision Scenarios

At minimum:

- keep registry value;
- use document value;
- stale/version mismatch rejected;
- unadvertised action rejected;
- duplicate identical resolution safe/idempotent where current patterns allow;
- both observations preserved after resolution;
- decision visible in API/frontend.

Only add corrected-value entry if it can meet the same guarantees safely.

## 27. Security

- bounded fields/notes;
- no raw PDF text;
- no raw source payload;
- no arbitrary JSON patch;
- enum-bounded actions;
- discrepancy/case/version binding;
- safe error translation;
- no fake reviewer identity;
- no hidden source precedence;
- no unsafe evidence rendering;
- secret scan remains green.

## 28. Persistence Boundary

Do not use MongoDB.

Reconciliation state/decisions may remain process-local.

Document clearly that restart loses this state.

Durable persistence is a later phase.

## 29. GoldTier Boundary

Do not change GoldTier.

Existing Mock flow remains:

```text
SEARCH
→ conditional SHELL
→ POLICY
→ AMEND
```

No new mapping.

## 30. Explicit Non-Goals

Do NOT implement:

- live ACRA;
- foreign registry;
- ACRA+;
- automatic source precedence;
- freshness priority / POSSIBLY_STALE automation;
- durable Mongo persistence;
- general workflow engine;
- case assignment;
- exception queue;
- aging/SLA;
- production RBAC;
- authenticated reviewer identity;
- full audit service;
- real GoldTier;
- Ready-for-Approval;
- new UBO rules;
- officer/shareholder/ownership reconciliation.

## 31. Documentation

Update:

```text
docs/architecture/ARCHITECTURE.md
docs/architecture/README.md
docs/decisions/DECISION_LOG.md
docs/sponsor-questions/OPEN_QUESTIONS.md
README.md
```

Recommended:

```text
docs/architecture/PHASE_11_RECONCILIATION_REVIEW_RESUME.md
docs/contracts/RECONCILIATION_PROFILE.md
```

Document:
- active fields;
- normalization;
- outcomes;
- allowed actions;
- no-precedence rule;
- provenance;
- unauthenticated POC review boundary;
- process-local resume limitation.

## 32. Required Tests

### Domain
1. observation validation/provenance;
2. MATCH direct construction;
3. CONFLICT direct construction;
4. MISSING_IN_SOURCE direct construction;
5. UNVERIFIABLE/INVALID consistency;
6. discrepancy invariants;
7. case-level status invariants;
8. RESOLVED impossible with unresolved blockers;
9. decision cannot reference unknown discrepancy/observation;
10. duplicate IDs rejected.

### Comparison
11. legal-name normalized match;
12. legal-name conflict;
13. identifier match/conflict;
14. country match/conflict;
15. address match/conflict;
16. missing field;
17. invalid/unverifiable field.

### Integrated workflow
18. all match → no review → ownership continues;
19. one conflict → wait → ownership/GoldTier zero;
20. multiple conflicts → resolve one → still blocked;
21. resolve all → resume exactly once;
22. keep-registry preserves both observations;
23. use-document updates canonical through backend service;
24. stale/version mismatch rejected;
25. invalid action rejected;
26. reads do not rerun registry/IDP;
27. repeated resume does not duplicate ownership/GoldTier;
28. replacement document can clear applicable discrepancy.

### Regression
29. Phase 09 blockers remain zero-call;
30. Phase 10 acquisition remains intact;
31. ownership/UBO arithmetic unchanged;
32. Mock GoldTier unchanged.

### Frontend
33. match summary renders;
34. conflict shows both values;
35. only backend-authorized actions render;
36. resolved decision renders;
37. multiple blockers remain visible;
38. no source visually marked authoritative;
39. no fake reviewer identity;
40. typecheck/tests/build pass.

## 33. Acceptance Criteria

Phase 11 passes only if:

1. observations are source-neutral and provenance-preserving;
2. four active fields are compared deterministically;
3. MATCH/MISSING_IN_SOURCE/CONFLICT/UNVERIFIABLE/INVALID are distinct;
4. no source precedence exists;
5. discrepancies are first-class in-process domain objects;
6. decisions never delete/overwrite source observations;
7. decisions are explicit, typed, backend-authorized;
8. canonical updates occur only through backend service logic;
9. multiple discrepancies remain blocking until all required ones resolve;
10. final resolution resumes exactly once;
11. stale/replayed decisions fail safely;
12. blockers stop ownership and GoldTier;
13. replacement-document behavior remains compatible;
14. registry acquisition unchanged;
15. ownership/UBO unchanged;
16. GoldTier unchanged;
17. frontend is backend-authoritative and no-precedence;
18. Q-015 remains open;
19. process-local durability is documented truthfully;
20. no Mongo persistence is added;
21. full backend passes;
22. Phase 11 focused tests pass;
23. Phase 10/09 regressions pass;
24. Ruff passes;
25. strict mypy passes;
26. contracts pass;
27. frontend typecheck/tests/build pass;
28. security/secret checks pass;
29. dependency checks pass;
30. GoldTier validation passes;
31. lifecycle passes;
32. `git diff --check` passes;
33. no unresolved Critical/High implementation finding remains before Quality Gate.

## 34. Execution Report

Create:

```text
.ai-pipeline/reports/PHASE_11_EXECUTION.md
```

Include:

1. Executive Summary
2. Scope Implemented
3. Files Changed
4. Observation Model
5. Field Comparison Rules
6. Reconciliation Outcomes
7. Discrepancy Model
8. Human Decision Model
9. Canonical Decision Application
10. Resume / Idempotency Semantics
11. API Changes
12. Frontend Changes
13. Existing Document Review Integration
14. Call-Stopping
15. Security / Provenance
16. Mongo / Persistence Boundary
17. GoldTier / Ownership Regression
18. Exact Test Results
19. Sponsor Dependencies Preserved
20. Non-Goals Confirmation
21. Remaining Risks
22. Readiness

End exactly:

`READY FOR PHASE 11 QUALITY GATE`

or:

`NOT READY FOR PHASE 11 QUALITY GATE`

## 35. Independent Quality Gate

After Execution, run a separate report-only Quality Gate.

It must challenge:

- hidden source precedence;
- comparison correctness;
- observation preservation;
- discrepancy/decision model invariants;
- stale/invalid decision safety;
- ownership/GoldTier call stopping;
- exactly-once resume;
- frontend-only action bypass;
- fake reviewer authority;
- duplicated document/reconciliation logic;
- Mongo/persistence scope creep;
- Phase 09/10 regressions;
- full security/quality matrix.

Expected report:

```text
.ai-pipeline/reports/PHASE_11_QUALITY_GATE.md
```

Verdict:

`PASS — READY FOR NEXT DEVELOPMENT PLANNING`

or:

`FAIL — REMEDIATION REQUIRED`

## 36. Future Work

After Phase 11, later bounded phases can add:

```text
durable persistence
→ general workflow checkpoint storage
→ case/exception queue
→ assignment/aging
→ retry policy
→ richer audit trail
→ STP/intervention metrics
```

Do not mix these into Phase 11.

## 37. Phase Principle

Phase 11 should turn:

```text
source conflict
→ narrow document review
```

into:

```text
multiple source observations
→ deterministic reconciliation
→ explicit discrepancy
→ human decision
→ evidence preserved
→ safe resume
```

without inventing source authority, reviewer authority, or durable production semantics not yet approved by Delta Capita.
