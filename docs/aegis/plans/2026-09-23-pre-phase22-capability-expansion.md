# Pre-Phase 22 Integrated Capability Expansion Implementation Plan

## Goal

Deliver the authorized pre-Phase 22 proof-of-concept expansion on
`feature/pre-phase22-capability-expansion`: explainable entity resolution,
ML-assisted UBO advice, mock advisory risk, bounded audit/workbench improvements,
and an SME demo path. Preserve the deterministic Decimal UBO engine, target ledger,
case authorization, provider-mode truth, and Phase 22 hold. Publish only after a
fresh independent exact-content quality-gate PASS.

## Architecture

- Keep strict provider payloads and dialect mappers at connector boundaries. The
  existing EDS-shaped Mock GoldTier connector remains unchanged. Any future XPI
  implementation is a distinct DTO/adapter/mapper dialect whose activation is
  bound into durable target state; it is not inferred from the absent artefacts.
- Add a source-neutral, deterministic `onboarding_intelligence` domain/service
  owner for explainable entity-resolution evidence and advisory projections.
- Consume the existing Decimal ownership result for ML-assisted UBO advice. Never
  create a second ownership graph/calculation owner or legal UBO determination.
- Bind configurable thresholds and model/policy versions into the existing case
  policy snapshot so later catalogue changes cannot reinterpret an existing case.
- Extend the existing retained zero-touch activity projection with safe, bounded
  advisory metadata. Do not turn it into a compliance audit system.
- Reuse the existing queue/query and case-detail surfaces. Assignment mutation is
  fenced out until eligible roles/capabilities have durable authority.
- Put frontend presentation in focused page/components; `App.tsx` receives wiring
  only because it is already an oversized integration hotspot.

## Tech Stack

Python 3.12, FastAPI, Pydantic, Decimal, PyMongo, pytest, React 18,
TypeScript 5.9, TanStack Query, Vitest, Playwright, repository validation scripts.
No unsafe pickle/joblib artefacts and no new hosted/production dependency.

## Baseline/Authority Refs

- `AGENTS.md` and `origin/main@3ca232b58c3842f413c4552dbd3b85aabea4591c`
- `docs/DEVELOPMENT_WORKFLOW.md`, `docs/ARCHITECTURE.md`, `docs/PROJECT_STATE.md`
- `docs/contracts/OWNERSHIP_UBO_PROFILE.md`
- `docs/contracts/POLICY_AUTHORITY_MATRIX.md`
- `docs/contracts/POLICY_ACTIVATION_CONTRACT.md`
- `docs/contracts/POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md`
- `docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md`
- `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`
- `docs/contracts/CASE_ACTIVITY_QUERY_PROFILE.md`
- `docs/contracts/GOLDTIER_CONTRACT_BASELINE.md`
- `docs/contracts/GOLDTIER_CONTRACT_DISCREPANCIES.md`
- `docs/contracts/EXTERNAL_PROVIDER_ACTIVATION_CONTRACT.md`
- `docs/contracts/INTEGRATION_ADAPTER_CONTRACTS.md`
- `docs/decisions/DECISION_LOG.md` and `docs/sponsor-questions/OPEN_QUESTIONS.md`
- accepted Phase 21 planner and quality-gate evidence
- user-supplied `Pasted text.txt`, dated 2026-09-23

### BaselineUsageDraft

- Required baseline refs: all references above plus current owning source/tests.
- Delivered context refs: user request and repository constitution.
- Acknowledged before plan refs: all required refs listed above.
- Cited in plan refs: all required refs listed above.
- Missing refs: GoldTier XPI guideline PDF and Postman collection named by the
  request were not attached or present in the task attachment directory.
- Decision: continue only on independent authorized slices; fence XPI-dependent
  work as blocked.

## Compatibility Boundary

- Legacy persisted cases and events remain readable in memory and Mongo modes.
- Existing Mock provider behavior, EDS mappings, target ledger order, and replay
  protection remain unchanged.
- Existing API fields are additive; authenticated inaccessible cases remain 404.
- Existing user/session/team-scoped query keys and logout/401 cancellation remain.
- Advisory scores never become source, legal, regulatory, compliance, approval,
  or readiness authority. `MOCK_RISK_BLOCKS_READINESS` defaults false.
- Phase 22 and all Live GoldTier/PingFed claims remain on hold.

## TDD Route

- Mode: strict
- Decision: strict
- Strict authority: explicit user/project request (the supplied workflow requires
  owner inspection, a focused failing test, then implementation and rerun).
- Strict signals: public API, policy snapshot, persistence, authorization, shared
  producer/consumer types, and user-visible behavior.
- Light eligibility: docs-only reconciliation and reports only.
- TDD-fit exception: environment-bound GoldTier diagnostic evidence and prose docs.
- Test posture: strict RED test for every behavior slice; focused GREEN then related
  regression.
- Reason: the expansion changes cross-layer contracts and durable interpretation.
- Verification: focused tests per task, then the full project matrix and independent
  gate over an exact revision/content tree.

## Requirement Ready Check

- Requirement source refs: user-supplied integrated capability request.
- Goals and scope refs: sections A-H and the request's non-goals/stop conditions.
- User/scenario refs: Merlion SME straight-through plus one ambiguous adverse case.
- Requirement item refs: exact output labels, risk disclaimer, policy binding,
  audit safety, bounded CSV, and publication protocol in the request.
- Acceptance/verification refs: request verification matrix and repository workflow.
- Open blocker questions: exact XPI schemas/enums/headers/examples/host; eligible
  assignment roles and assignment capability authority.
- Decision: ready for the explicitly separable intelligence, advisory-risk,
  safe-audit, read-only workbench, SME, research, and documentation slices. XPI DTO,
  XPI request execution, and assignment mutations are blocked and omitted from
  implementation tasks until their named authority arrives.

## Change Necessity

- User-visible need: show explainable advisory evidence and filterable safe activity
  in the POC, including a deterministic SME path.
- No-change/non-code option: documents alone cannot expose or verify the requested
  runtime outputs, case-bound thresholds, or UI behavior.
- Why code change is necessary: the current owners have no entity-resolution model,
  advisory outputs, policy fields, or bounded export projection.
- Minimum change boundary: new focused intelligence owner plus additive wiring in
  policy snapshot, case persistence, safe activity projection, APIs, and UI.
- Decision: code-change for ready slices; docs-only for blocked XPI reconciliation.

## Existence Check

- Proposed new surface: source-neutral onboarding intelligence module.
- Existing reuse candidates: ownership calculator, reconciliation service, policy
  catalogue, target connector/mappers, zero-touch service.
- Why insufficient: none owns cross-source identity similarity or advisory model
  evidence; putting it in ownership would create a second mixed responsibility,
  while putting it in a connector would couple a domain decision to a provider.
- Creation proof: one domain/service owner consumes canonical evidence and existing
  ownership results; no provider I/O and no readiness/approval mutation.
- Entropy/retirement impact: versioned deterministic rules and plain JSON-safe model
  parameters; remove when replaced only through a reviewed successor owner.
- Decision: add-with-proof. Reuse all policy, persistence, query, ledger, and
  authorization owners.

## Architecture Integrity Lens

- Invariant: canonical evidence enters advice; advice never alters canonical source,
  legal UBO results, readiness, target selection, or approval.
- Canonical owners: policy catalogue/snapshot for thresholds; Decimal ownership
  engine for UBO truth; zero-touch ledger for target order; case access service for
  scope; activity query for bounded history.
- Responsibility overlap: prevented by keeping feature extraction/scoring in the new
  module and wiring-only changes elsewhere.
- Higher-level simplification: one immutable `IntelligenceAssessment` projection per
  case view rather than separate mutable ML stores.
- Retirement/falsifier: an approved replacement owner or evidence that recomputation
  cannot meet restart/audit requirements triggers a new persistence decision.
- Verdict: proceed for ready slices; do not add XPI or assignment fallbacks.

## Complexity Budget

- Artifact class: domain/service/API/persistence/frontend contract expansion.
- Target files/artifacts: focused new backend and frontend modules; existing policy,
  persistence, main/composition, and `App.tsx` only for narrow additive wiring.
- Current pressure: `main.py`, Mongo store, and `App.tsx` are already large hotspots.
- Projected pressure: over-budget if rules or UI are added inline.
- Budget result: at-risk.
- Planned governance: extract API router/serialization helpers and focused UI page;
  keep hotspot edits declarative and small.

### Plan-Time Complexity Check

- Target files: `apps/backend/app/main.py`, `apps/backend/app/persistence/*`,
  `apps/frontend/src/App.tsx`.
- Existing shape signals: mixed large composition/API/storage/UI files.
- Owner fit: wiring fits; new scoring/query/export logic does not.
- Add-in-place risk: duplicated rules, hard-to-test branches, accidental authority.
- Better boundary: new intelligence, export, and UI modules with typed ports.
- Recommendation: add owner files; edit hotspots only for registration/wiring.

## Execution Readiness View

- Intent Lock: implement only the authorized pre-Phase 22 expansion and publication
  flow; no Phase 22 start or unproved provider activation.
- Scope Fence: ready slices above; XPI DTO/request and assignment mutations blocked.
- Baseline Lock: exact clean `origin/main` SHA and branch base stated above.
- Approved Behavior: exact labels/disclaimers, deterministic advice, case-bound policy,
  safe audit/export, SME demonstrations.
- Owner/Contract Constraints: preserve all canonical owners and access/CAS rules.
- Compatibility Boundary: additive/read-compatible as stated above.
- Retirement Boundary: no fallback, dual adapter activation, or parallel persistent
  model; future approved XPI dialect must retire no current Mock behavior implicitly.
- Task Batches: documentation/decision; intelligence; policy/persistence; API/audit;
  frontend/workbench; SME/demo; verification; independent gate; publication.
- Test Obligations: RED/GREEN per behavior plus full matrix.
- Review Gates: implementer self-review, fresh independent quality gate, exact PASS,
  then separate publisher and CI observation.
- Drift/Rewind Rules: stop any slice needing missing schema/role authority; after two
  failed repair cycles escalate rather than inventing a new owner or fallback.
- Evidence Required Before Completion: commands, counts, revision/tree identities,
  blocked diagnostics, gate decision, commit/push/PR/CI links.
- Advisory Boundary: Aegis method guidance only; not a project GateDecision,
  PolicySnapshot, or completion authority.

## File Map

Likely new owners:

- `apps/backend/app/domain/onboarding_intelligence.py`
- `apps/backend/app/services/onboarding_intelligence.py`
- `apps/backend/app/api/intelligence.py`
- `apps/backend/app/services/activity_export.py`
- `apps/frontend/src/pages/IntelligenceWorkbench.tsx`
- focused backend/frontend tests mirroring these owners
- `docs/models/ENTITY_RESOLUTION_MODEL_CARD.md`
- `docs/models/UBO_ADVISORY_MODEL_CARD.md`
- `docs/models/MOCK_ADVISORY_RISK_MODEL_CARD.md`
- `docs/research/INDUSTRY_STANDARD_USAGE.md`

Narrow existing edits:

- policy domain/service and API types for versioned editable thresholds
- case/persistence models and repositories for backward-compatible snapshots/events
- composition/main for dependency/router wiring only
- existing case/query types for additive filters and safe projection
- frontend API/types/query keys and `App.tsx` route/navigation wiring only
- demo controls/fixtures for named SME scenarios
- canonical contracts, project state, architecture, decision/open-question logs
- required integration/implementation/diagnosis reports

Blocked files remain untouched until authority arrives:

- XPI DTO, connector, and mapper implementation
- GoldTier sandbox request runner and write methods
- assignment mutation/service/API/frontend controls

## Tasks

### Task 1: Record architecture and authority reconciliation

1. Create the ADR for the source-neutral advisory owner and immutable case-bound
   interpretation; record rejected connector/ownership/persistent-shadow alternatives.
2. Update decision/open-question/contract docs so mock advisory risk is explicitly
   project-defined and Q-017 remains open.
3. Create GoldTier reconciliation and diagnosis reports that enumerate missing
   artefacts/variables and mark every network/write attempt NOT EXECUTED.
4. Write the industry-standard usage ledger with primary-source citations and a clear
   regulatory-versus-technical classification.
5. Verify doc validators and whitespace checks.

### Task 2: Entity-resolution domain and service (strict RED/GREEN)

1. Add failing unit tests for normalization, missingness, weighted comparison,
   deterministic evidence, conflict handling, and exact UEN+country dominance.
2. Verify RED for missing owner/API.
3. Implement typed immutable inputs/features/evidence/outcomes with exact labels:
   `EXACT_MATCH`, `PROBABLE_MATCH`, `REVIEW_REQUIRED`, `NO_MATCH`, `CONFLICT`.
4. Add failing tests that name-only and address-only matches never auto-select.
5. Implement thresholded classification and deterministic tie/ambiguity behavior.
6. Add synthetic evaluation fixtures and adverse tests; verify focused GREEN.

### Task 3: UBO advice and mock risk (strict RED/GREEN)

1. Add failing tests proving UBO advice consumes the existing ownership result and
   emits probability, `LIKELY_UBO|REVIEW|UNLIKELY_UBO`, `ML_ASSISTED`, and
   `NOT_LEGAL_UBO_DETERMINATION` without changing legal outputs.
2. Implement the minimum deterministic explainable projection and model metadata.
3. Add failing tests for mock risk bands, missing-signal `NOT_ASSESSED`, immutable
   disclaimer, explicit signal limitations, and no readiness effect by default.
4. Implement the minimum advisory risk projection and safe reason codes.
5. Add reproducibility/evaluation tests and verify all ownership regressions.

### Task 4: Policy snapshot and persistence compatibility (strict RED/GREEN)

1. Add failing policy tests for editable thresholds/weights/bands with validation,
   RBAC, audit metadata, and case snapshot immutability.
2. Extend the existing policy owners; do not add a second policy store.
3. Add failing memory/Mongo round-trip tests for the new snapshot/event fields and
   legacy record reads.
4. Apply the smallest schema-version/read-compatibility change, preserving strict
   identity, CAS, insert/update, deletion, and restart invariants.
5. Run physical Mongo lifecycle/restart tests when the existing harness provisions a
   newly generated disposable database.

### Task 5: Authorized API, audit, and export surface (strict RED/GREEN)

1. Add failing API tests for case-scoped intelligence projection, 404 non-disclosure,
   team scope, bounded paging, and safe fields.
2. Wire the intelligence service through the existing case-access owner.
3. Add failing activity tests for safe actor/source/category/model/policy metadata,
   unchanged bounded retention, and prohibited raw fields.
4. Add failing CSV tests for authorization, row/page bounds, UTC formatting, stable
   safe columns, and formula-injection neutralization.
5. Implement focused serializer/export owners and verify API/security regressions.

### Task 6: Read-only workbench and frontend projection (strict RED/GREEN)

1. Add failing frontend tests for status/priority/risk/entity-ambiguity/open/due/age/
   stage filters and advisory labels/disclaimers.
2. Extend user/team-scoped query keys and cancellation tests for new parameters.
3. Implement a focused workbench page/component and narrow route wiring.
4. Keep claim/assign/unassign controls absent and explicitly explained while authority
   is unresolved; preserve current notes/actions only where already authorized.
5. Verify typecheck, unit tests, and authenticated browser flows including logout/401.

### Task 7: SME demo scenarios (strict RED/GREEN)

1. Add failing tests for `SME_STRAIGHT_THROUGH` and one ambiguous adverse scenario
   whose outputs are input-driven and synthetic.
2. Add Merlion-labelled synthetic inputs without embedding scenario branches in
   generic providers/services.
3. Verify success, ambiguity, missing-signal, and safe-label outputs end to end.
4. Update demo runbook and UAT evidence mappings without claiming Live integration.

### Task 8: Integration docs, full verification, and implementer report

1. Update architecture, contracts, project state, API handoff, decision/open-question
   records, model cards, and required implementation report.
2. Run focused suites, backend full suite, Ruff, mypy, frontend tests/typecheck/build,
   repository policy/contract/security checks, POC regression, E2E/browser flows,
   physical Mongo, pre-PR check, tracked/task-owned hygiene, and secret-path checks.
3. Inspect the entire diff against acceptance/adverse cases and rerun affected checks
   after the last source change.
4. Record current source revision, tested tree/revision, and evidence separately.

### Task 9: Independent gate, remediation loop, and publication

1. Hand the exact diff/tree and evidence to a fresh independent reviewer; only that
   reviewer writes the required quality-gate report.
2. If not PASS, remediate under the same strict loop and request a fresh exact review.
3. After exact PASS, use a separate publication role to check latest `origin/main`,
   run pre-PR evidence, create one coherent commit, push the branch, open the PR, attach
   the PR artefact, and observe all CI to a terminal state.
4. Stop before human squash merge and keep Phase 22 on hold.

## Plan Pressure Test

- Owner/contract/retirement: one new advisory owner is justified; all authoritative
  business, persistence, access, query, and ledger owners are reused.
- Architecture integrity/higher-level path: connector or ownership-engine placement
  was rejected; immutable projection plus existing snapshot owner is the narrower path.
- Verification scope: full producer/consumer, compatibility, security, UI, persistence,
  E2E, and independent review are explicit.
- Task executability: ready tasks have exact owners and checks; blocked tasks are not
  disguised as executable work.
- Pressure result: proceed with Task 1 and ready slices; pause only affected lanes.

## Risks

- Missing XPI artefacts prevent truthful DTOs, request construction, or sandbox/TLS
  evidence. Mitigation: docs-only reconciliation and explicit NOT EXECUTED evidence.
- Assignment authorization is unresolved. Mitigation: no mutation or invented role;
  retain/read-only workbench scope.
- Recomputed advisory projections could drift if versions are not bound. Mitigation:
  case snapshot contains versioned thresholds/model identifiers and output evidence.
- Hotspot growth could obscure ownership. Mitigation: focused modules and wiring-only
  edits in existing hotspots.
- Advisory terminology could imply authority. Mitigation: exact immutable labels,
  UI/API assertions, and negative tests.

## Retirement

- No compatibility fallback or duplicate scoring/persistence owner is created.
- Synthetic evaluation artefacts remain plain source-controlled data and can be
  replaced only with a reviewed versioned model owner.
- Blocked XPI and assignment tasks are not partially scaffolded; their future plan must
  start from authoritative artefacts/roles and this plan's recorded boundaries.
- Phase 22 starts only through a separately authorized planner after human merge.
