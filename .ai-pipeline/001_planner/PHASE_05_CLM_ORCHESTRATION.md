# Phase 05 — End-to-End CLM Orchestration and Mock GoldTier Submission

## Goal

Connect the accepted Phase 01–04 capabilities into one staged, source-neutral CLM
case journey:

`ACRA -> canonical entity -> document review -> ownership/UBO analysis -> readiness -> Mock GoldTier submission -> unified case summary`

The existing `POST /api/onboarding/cases` flow remains a regression contract. Phase
05 adds a separate staged path that stops before GoldTier until current authoritative
local evidence satisfies the project-defined readiness policy.

## Acceptance criteria

### Shared services and staged intake

- Refactor shared registry intake and GoldTier submission behavior only as needed to
  avoid duplicating the Phase 01 onboarding implementation.
- Preserve the original onboarding endpoint, terminal states, workflow ordering,
  stopping rules, safe errors, correlation behavior, and accepted Phase 01–04
  regression scenarios.
- Add `POST /api/clm/cases` for UEN/registration-number intake through the existing
  ACRA connector, canonical mapping, and canonical validation. Persist the case and
  stop before GoldTier.
- A staged case must be addressable by the existing document and ownership APIs.

### Orchestration and readiness

- Associate a source-neutral, versioned orchestration aggregate with the existing
  case ID. Store readiness/status metadata and safe lifecycle events, not copies of
  raw canonical, document, or ownership records.
- Use truthful lifecycle states: `COLLECTING_EVIDENCE`, `REVIEW_REQUIRED`,
  `READY_FOR_MOCK_SUBMISSION`, `SUBMITTING`, `MOCK_GOLDTIER_SUBMITTED`, and
  `FAILED` (or a demonstrably cleaner equivalent).
- Implement a deterministic server-side readiness evaluator over current repository
  records for registry, document, ownership, and Mock GoldTier readiness.
- Return typed Mock-submission blockers separately from real-integration warnings.
- Registry readiness requires a successfully validated staged canonical case.
- Document readiness is a provisional POC policy: at least one successfully
  `REVIEWED` document, none `PROCESSING`, and no unresolved `REVIEW_REQUIRED` or
  processing `FAILED` document. Human-reviewed evidence must agree with registry
  values for automatic Mock submission.
- A corrected/rejected document value that conflicts with registry data must not
  overwrite the canonical entity. It yields `REVIEW_REQUIRED` with
  `SOURCE_CONFLICT_REQUIRES_POLICY` (or an equivalent typed blocker).
- Ownership readiness requires a completed `ANALYZED` Phase 04 result. Any
  `REVIEW_REQUIRED`, `FAILED`, cycle, incomplete chain, graph limit, or indeterminate
  outcome blocks submission.
- Recompute readiness from authoritative records immediately before submission; do
  not trust a frontend flag or stale previously evaluated result.

### Submission preparation and Mock GoldTier

- Expose a safe submission plan describing base operation ordering and unresolved
  real-integration boundaries without exposing raw HTTP payloads, endpoints, auth,
  credentials, or sponsor artefacts.
- Before execution create an immutable, minimized submission snapshot containing the
  canonical entity data needed for Mock GoldTier plus evidence references/versions,
  readiness policy/version, correlation/submission ID, and timestamp. Do not copy raw
  PDFs/text, ACRA/provider responses, ownership provenance, secrets, or private
  endpoint information.
- Reuse the existing `GoldTierConnector` and accepted base sequence:
  `search -> create shell only on NO_MATCH -> policy -> amend`.
- Preserve call stopping, safe partial-amend handling, and error projection.
- `MATCH_FOUND` yields review and no shell/policy/amend. Search/shell/policy failure
  yields terminal failure and stops later calls. Partial amend yields review, not
  success. Unexpected failure leaves no stranded `SUBMITTING` state.
- Provide a related-party submission-preparation representation only. Real
  `createRelatedParty` payloads/writes remain blocked by Q-006/Q-007 and must be
  labelled `PENDING_SPONSOR_CONFIRMATION` / `RELATED_PARTY_WRITE_NOT_EXECUTED`.
- Serialize or compare-and-set submission so one case performs at most one accepted
  Mock execution. Duplicate calls return the existing idempotent result; stale work
  cannot overwrite terminal status or erase terminal history.

### API and frontend

- Add a coherent Phase 05 API, normally:
  - `POST /api/clm/cases`
  - `GET /api/clm/cases/{case_id}`
  - `POST /api/clm/cases/{case_id}/readiness/evaluate`
  - `GET /api/clm/cases/{case_id}/submission-plan`
  - `POST /api/clm/cases/{case_id}/submit`
- Reuse existing document and ownership routes rather than creating duplicates.
- The case summary returns current stage states, blockers, warnings, safe timeline,
  provisional UBO summary, and Mock submission result without raw external payloads,
  PDF data/text, private provenance, or business decisions reimplemented in JS.
- Extend the frontend into Registry, Document Review, Ownership & UBO, Readiness, and
  Mock GoldTier Submission stages. Enable submission only when backend status is
  `READY_FOR_MOCK_SUBMISSION`.
- Clearly label ACRA, IDP, ownership, and GoldTier environments and provisional/live
  dependencies. Never display an achieved `Ready-for-Approval` state.

### Required synthetic scenarios

- Happy end to end: matching reviewed document + `ANALYZED` ownership + Mock
  `NO_MATCH/shell/policy/amend` -> `MOCK_GOLDTIER_SUBMITTED`.
- Document blocked -> review, zero GoldTier calls.
- Document source conflict -> `SOURCE_CONFLICT_REQUIRES_POLICY`, zero calls.
- Ownership cycle/incomplete -> review, zero calls.
- Multiple blockers -> all typed blockers, zero calls.
- GoldTier match found -> review, search only.
- GoldTier policy failure -> failed, no amend.
- Partial amend -> review, not success.
- Duplicate and synchronized concurrent submits -> one business execution and an
  immutable terminal result.
- Stale readiness and cross-case isolation are explicitly tested.

### Documentation and CI

- Create `docs/contracts/CLM_READINESS_POLICY.md` with sponsor-confirmed,
  project-defined/provisional, and unresolved classifications.
- Create `docs/contracts/GOLDTIER_SUBMISSION_PREPARATION.md` documenting Mock base
  operation behavior and real-integration blockers.
- Create `docs/architecture/PHASE_05_CLM_ORCHESTRATION.md` documenting components,
  trust/data flow, finality, and the future real GoldTier seam.
- If the workflow display name remains phase-specific, rename only that display name
  to `Project CI`; do not weaken checks.
- Update the canonical POC regression catalogue only for implemented and verified
  Phase 05 scenarios authorized here.

## Security invariants

- Trace browser -> CLM API -> ACRA/canonical -> document/ownership repositories ->
  readiness -> snapshot -> Mock GoldTier.
- Keep readiness server-controlled and revalidate it inside the serialized submission
  boundary to prevent stale/TOCTOU submission.
- Enforce case isolation and prevent duplicate concurrent Mock writes.
- Do not expose raw document content, private ownership provenance, raw provider
  payloads, unsafe exception detail, credentials, auth headers, or private endpoints.
- Preserve explicit Mock/sandbox/live labels. Mock success is not real
  interoperability evidence.

## Explicit non-goals

- Phase 06 work.
- Real GoldTier HTTP, PingFed, OAuth/token acquisition, live credentials, real
  related-party writes, live hierarchy retrieval, or a Ready-for-Approval endpoint.
- Final sponsor UBO policy or a document master-data override policy.
- ACRA live ownership retrieval, authentication/RBAC, durable database, worker/queue,
  Camunda, sanctions screening, AML scoring, analytics dashboard, or a full exception
  workbench.

## Dependencies and unresolved sponsor questions

- Q-003/Q-005/Q-014: final document profile, validation ownership, sequencing, and
  conflict/master-data authority remain unresolved. Phase 05 uses a conservative,
  explicit provisional policy and blocks source conflicts.
- Q-002/Q-004: live hierarchy and final UBO policy remain unresolved. Phase 04's
  threshold and decisions remain provisional.
- Q-006/Q-007: final related-party mapping/write semantics remain unresolved; Phase 05
  prepares only an internal summary and performs no related-party write.
- Live ACRA and real GoldTier/PingFed remain dependent on sponsor environment,
  contracts, and approved credentials. They do not block credential-free Mock work.

## Required validation

Run all configured full backend tests, Ruff, strict mypy, contract and repository
regressions, Phase 01–05 scenario tests, readiness/stale-readiness, concurrency,
terminalization, isolation, security/adversarial and secret checks, GoldTier validator
regressions, frontend typecheck/tests/production build, `pip check`, `npm ls --all`,
`git diff --check`, cached diff check, and untracked whitespace checks. Apply the
integration-security-review and poc-regression-check workflows after implementation.

## Stop condition

Do not stage, commit, push, merge, change branches, or begin Phase 06. Hand the
completed Phase 05 implementation to the independent Phase 05 quality gate.
