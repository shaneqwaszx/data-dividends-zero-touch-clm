# Phase 15B Backend Review/Rework Stabilization — Implementation Report

Date: 2026-09-19<br>
Status: **REMEDIATION VERIFIED — PHYSICAL EVIDENCE COMPLETE — RE-QG REQUIRED**<br>
Branch: `phase/15b-review-rework`<br>
Planning `BASE_SHA`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`<br>
Current `HEAD`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`<br>
Locally known `origin/main`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`<br>
Ahead/behind: `0/0`

This is an implementation report, not an independent quality-gate verdict. No commit,
push, PR, merge, staging operation, frontend change, or next-phase work was performed.

## Implemented behavior

- Superseded document records reject field review with
  `DOCUMENT_ALREADY_SUPERSEDED` before mutation.
- Reconciliation now applies one bounded effective-review rule:
  - accepted fields retain original provider evidence;
  - a correction is effective only when the original was present, valid, and met the
    immutable case confidence threshold;
  - effective corrections use `HUMAN_REVIEW` provenance and no invented confidence;
  - rejected, missing, unavailable, invalid, and low-confidence originals remain
    replacement-required;
  - once a human field decision starts, remaining pending fields are blocking across
    the complete current document set;
  - automatic confirmation is not mistaken for partial human review.
- The reconciliation fingerprint namespace advances to
  `phase-15b-reconciliation-evidence-v2` inside the existing fingerprint owner.
- The field-review API now delegates to `ZeroTouchOrchestrator`, which refreshes the
  current reconciliation and document-stage exception checkpoint under the case lock.
  Partial review remains waiting; clearing the final permitted blocker enters the
  existing ledger-owned resume path once. Exact final-decision repeats remain
  idempotent.
- Explicit `/resume` repairs an interrupted stale document checkpoint. `/start` and
  reads keep their prior non-refresh behavior for unresolved waiting cases.
- A replacement processing failure retains the new failed current record, cancels the
  old document exception, records `DOCUMENT_REUPLOAD_REQUIRED`, and returns automation
  to the narrowly validated `PENDING_INPUTS / DOCUMENT` targeted-retry state. The public
  response remains a sanitized retryable `503`.
- Review, replacement, targeted retry, reconciliation/exception resolution, intake
  completion/start, and resume reauthenticate and reauthorize inside the owning case
  lock. Revoked sessions remain `401`; lost/cross-team access remains safe `404`.
- Existing target-ledger ordering and no-replay behavior remain the only target-call
  path. No direct review/reconciliation target call was added.

## Contract and compatibility decisions

- Public request/response schemas and route paths are unchanged.
- No persisted field, schema version, repository, provider, cache, assignment,
  reviewer-identity, UBO, Camunda, or frontend owner was added.
- Original extracted values and historical decisions remain retained evidence.
- The narrow `WAITING_FOR_REVIEW -> PENDING_INPUTS` transition is accepted only for a
  document-stage `DOCUMENT_REUPLOAD_REQUIRED` candidate satisfying the existing pending
  invariant; it was not added to the general transition table.
- Review/reconciliation/automation updates remain sequential section saves within the
  durable envelope. They are not represented as a cross-section Mongo transaction.
  Repeated identical review and explicit resume are the bounded recovery mechanisms.
- A document field-review request still carries no expected document event/version.
  Mongo envelope revision CAS can admit one durable repository-write winner, but the
  losing raw repository conflict is not a new stable public stale-review contract.
- Q-014, Q-015, and Q-016 remain unresolved. No final reviewer role, source precedence,
  override policy, separation of duties, or assignment/rework workflow was invented.

## Files changed

Implementation:

- `apps/backend/app/api_auth.py`
- `apps/backend/app/domain/zero_touch.py`
- `apps/backend/app/main.py`
- `apps/backend/app/services/document_processing.py`
- `apps/backend/app/services/reconciliation.py`
- `apps/backend/app/services/zero_touch_orchestration.py`

Tests:

- `apps/backend/tests/test_document_api.py`
- `apps/backend/tests/test_document_processing.py`
- `apps/backend/tests/test_phase11_reconciliation.py`
- `apps/backend/tests/test_phase12_persistence.py`
- `apps/backend/tests/test_phase12_real_mongo.py`
- `apps/backend/tests/test_phase13_auth_rbac.py`
- `apps/backend/tests/test_zero_touch_orchestration.py`

Contracts and execution evidence:

- `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`
- `docs/contracts/IDP_REVIEW_CONTRACT.md`
- `docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md`
- `docs/contracts/POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md`
- `docs/contracts/RECONCILIATION_PROFILE.md`
- `docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md`
- `.ai-pipeline/001_planner/PHASE_15B_EXECUTION_ADDENDUM.md`
- `.ai-pipeline/reports/PHASE_15B_IMPLEMENTATION.md`

The supplied planner handoff remains preserved at
`.ai-pipeline/001_planner/PHASE_15B_REVIEW_REWORK_STABILIZATION.md`.

## Verification evidence

All command examples below are Windows CMD-compatible.

### Fresh focused Phase 15B falsification set

```cmd
cd /d C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-15b\apps\backend
python -m pytest tests/test_document_processing.py::test_superseded_document_rejects_review_without_appending_event tests/test_document_api.py::test_failed_zero_touch_replacement_returns_retryable_controlled_response tests/test_phase11_reconciliation.py::test_safe_review_correction_is_effective_and_preserves_original_evidence tests/test_phase11_reconciliation.py::test_rejected_missing_and_low_confidence_reviews_remain_blocking tests/test_zero_touch_orchestration.py::test_partial_review_stays_waiting_then_safe_correction_resumes_once tests/test_zero_touch_orchestration.py::test_failed_replacement_returns_to_targeted_intake_and_resumes_once tests/test_zero_touch_orchestration.py::test_in_lock_reauthorization_failure_prevents_review_mutation tests/test_zero_touch_orchestration.py::test_explicit_resume_repairs_interrupted_review_checkpoint_without_replay tests/test_phase12_persistence.py::test_partial_document_review_round_trips_across_adapter_restart tests/test_phase13_auth_rbac.py::test_review_reauthorizes_inside_case_lock_before_mutation tests/test_pre_phase12_workspace_multidoc.py::test_field_missing_from_one_document_does_not_create_false_missing_blocker tests/test_pre_phase12_workspace_multidoc.py::test_replacing_one_of_two_documents_preserves_other_and_rebuilds_reconciliation -q -p no:cacheprovider
```

Result: **PASS**, 15 cases including parameter expansions.

### Planner-required focused suites

```cmd
cd /d C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-15b\apps\backend
python -m pytest tests/test_document_processing.py tests/test_document_api.py tests/test_phase11_reconciliation.py tests/test_zero_touch_orchestration.py -q -p no:cacheprovider
python -m pytest tests/test_phase12_persistence.py tests/test_phase13_auth_rbac.py tests/test_phase14_5_administration.py -q -p no:cacheprovider
```

Result: **PASS** for both commands.

### Full backend and static checks

```cmd
cd /d C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-15b\apps\backend
python -m pytest -q -p no:cacheprovider
python -m ruff check .
python -m mypy app
```

Result: full backend **PASS** with environment-gated skips; Ruff **PASS**; mypy
**PASS** for 91 source files. The full run emitted only the pre-existing Pydantic
serializer warnings in provider-conformance negative tests.

### Governance, secret, and workspace checks

```cmd
cd /d C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-15b
python scripts/check_secrets.py
python scripts/check_project_state.py
python scripts/check_architecture.py
python scripts/dev_context.py
git diff --check
```

Result: secret scan **PASS**; project-state check **PASS**; architecture check **PASS**;
development context **PASS**; whitespace check **PASS**. The secret scan was limited to
its configured supported patterns and did not access `.env` or `private/`.

### Genuine Mongo evidence

```cmd
cd /d C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-15b\apps\backend
python -m pytest tests/test_phase12_real_mongo.py -q -p no:cacheprovider
```

Result: **13 SKIPPED** because `PHASE12_MONGO_URI` is not configured. Two Phase 15B
physical tests are present for a contradictory-review CAS race and restart-preserved
review refresh/no-target state, but neither was executed. No Mongo URI was read,
printed, or persisted; no database was created or cleaned.

## Security review

- Authentication and case authorization are freshly evaluated inside the case lock,
  before actionable evidence is read.
- Deterministic tests cover mid-request session revocation and a mid-request actor scope
  change; both produce the fixed public projection and zero document/automation/target
  mutation.
- Upload bounds, CSRF/origin enforcement, safe `404`, provider-error sanitization,
  evidence minimization, and target-ledger ownership remain unchanged.
- New events and public errors contain fixed safe messages only; no document body,
  correction, review note, credential, session token, provider payload, or URI is added
  to logs/events/errors.
- No external provider classification changed. ACRA remains Mock/default with partial
  generic sandbox support; IDP remains Local with Mock demo/fault path; ownership remains
  Local; GoldTier remains Mock.

## POC regression assessment

The full backend suite and focused document/reconciliation/zero-touch suites preserve
the accepted Registry -> Document -> Reconciliation -> Ownership -> Readiness -> Mock
GoldTier ordering, stop-on-blocker behavior, terminal status separation, and target
call-stopping/no-replay behavior. The canonical regression catalogue was not changed;
the planner required execution evidence, not a new accepted scenario catalogue entry.

## Complexity and residual risk

`apps/backend/app/services/zero_touch_orchestration.py` was already under strong size
pressure and received a net Phase 15B delta larger than the planner's approximate
single-operation guidance. The delta stays within its existing orchestration
responsibility and is separated into review-refresh and reupload-recovery helpers; it
does not add a new owner or fallback path. The execution addendum records why extracting
a new coordinator/repository owner would exceed the authorized architecture boundary.

Complexity closure: **exceeded-and-governed for this bounded slice; follow-up required**.
A later authorized architecture/refactor slice should extract cohesive document-review
checkpoint coordination from the oversized orchestrator after Phase 15B behavior is
independently accepted.

Residual risks/blockers:

1. Genuine Mongo evidence is unavailable, so physical CAS/restart/no-replay claims are
   unverified in this run.
2. The composed document/reconciliation/automation mutation is recoverable and monotonic
   but not one cross-section transaction.
3. Field-review requests have no client-supplied evidence version; an identical stale
   body cannot be distinguished from a valid idempotent repeat.
4. The raw cross-instance document repository CAS loser is not yet a stable typed public
   stale-review response.
5. Independent `fyp-quality-gate` has not run and this implementation report does not
   self-accept Phase 15B.

Confidence grade: **C** for full Phase 15B closure because required physical Mongo
evidence is missing; **B** for the executed single-process backend behavior and
memory-compatible restart adapter evidence.

## Next human action

Provide an explicitly authorized `PHASE12_MONGO_URI` for a disposable allowlisted test
database environment and run `tests/test_phase12_real_mongo.py`. If it passes, assign a
separate independent `fyp-quality-gate` run. Do not merge or begin Phase 15C from this
implementation report alone.

## Remediation after independent QG FAIL

Date: 2026-09-19

Pre-physical status: **REMEDIATION VERIFIED — PHYSICAL EVIDENCE PENDING — RE-QG NOT YET READY**

### Gate finding disposition and authority

The independent Phase 15B quality gate returned **FAIL**. `P15B-QG-001` reproduced a
rejected reconciliation prerequisite followed by a second reconciliation attempt and a
completed search/shell/policy/amend target sequence. `P15B-QG-002` found that the
implementation had substituted sequential recovery for the planner's cross-section
atomicity wording without owner approval. The architecture checkpoint was `REVISE`, and
the physical suite lacked genuine partial-review and failed-replacement restart cases.

The governing planner now contains the dated section **Owner-authorized refinement after
independent Phase 15B QG**. It supersedes only cross-section atomicity wording with
owner-authorized monotonic sequential recoverability: each existing section save remains
individually durable under its existing repository/envelope CAS; rejected reconciliation,
authorization, infrastructure, or automation prerequisites fail closed; progression
requires durable reconciliation plus automation acceptance; and recovery occurs only on
a later exact repeat or explicit `/resume`. This is project-owner authority, not sponsor
confirmation.

### Reproduction and root cause

The new test-first regressions failed before the production fix: injected
`ReconciliationRequestError` and `ReconciliationInfrastructureError` did not surface and
instead advanced the case. The rejected-save probe matched the gate's mechanism.

Root-cause claim:

- **Topology:** single-root-multi-symptom.
- **Causal closure:** `_refresh_document_checkpoint_locked` caught both typed
  reconciliation failure classes, replaced the unavailable result with an empty
  expected-version set, cancelled document blockers, saved `RESUMING`, and invoked the
  existing progression path. Request/CAS and infrastructure failures therefore produced
  the same unsafe target-progress symptom.
- **Falsifier:** if the catch-and-empty substitution were not causal, replacing it with
  typed propagation would still permit a later reconciliation/target call. Deterministic
  injections now show exactly one reconciliation attempt, unchanged blockers/checkpoint,
  and zero ownership/target calls.
- **Self-refutation:** a later `_advance_locked` retry could have remained the active
  cause; it does not run because typed propagation exits before the automation save and
  progression call.
- **Layer ceiling:** the owner-refined planner now explicitly requires fail-closed
  sequential recovery, so no upstream authority/default can regenerate an empty-success
  interpretation without contradicting the governing requirement and its regression
  tests.
- **Recurrence status:** closed for the reviewed failure classes. Repository/CAS,
  reconciliation infrastructure, authorization, and automation-save failures are
  explicitly distinct; only a durably persisted replacement with
  `IDP_PROCESSING_FAILED` can enter re-upload recovery.

### Code remediation and failure-window evidence

`ZeroTouchOrchestrator` remains the sole workflow checkpoint owner. The unsafe catch was
replaced by safe `ZeroTouchRequestError` / `ZeroTouchInfrastructureError` projection.
Current-document preparation was consolidated without adding a coordinator, repository,
schema, state machine, retry loop, target path, or fallback. Replacement recovery was
narrowed so a document repository/CAS or other infrastructure rejection preserves the
review checkpoint instead of masquerading as `DOCUMENT_REUPLOAD_REQUIRED`.

Deterministic tests prove:

1. reconciliation request/CAS rejection after the durable field decision: one
   reconciliation call, unchanged automation version/blockers, zero ownership and target;
2. reconciliation infrastructure rejection: the same fail-closed result and one call;
3. exact repeat repairs without duplicating the document event;
4. explicit refresh/resume repairs without target replay;
5. automation-checkpoint CAS rejection after successful reconciliation: typed conflict,
   unchanged blockers, zero target; both exact repeat and resume repair;
6. an independent document blocker survives a reconciliation failure;
7. an existing-party recovery reaches only the accepted search-only target prefix;
8. a synthetic document repository failure does not enter re-upload recovery;
9. the expected persisted `IDP_PROCESSING_FAILED` replacement still reaches
   `PENDING_INPUTS / DOCUMENT_REUPLOAD_REQUIRED`, then targeted retry/start completes once.

### Architecture and complexity self-check

This implementer self-check is not an independent architecture verdict.

- Baseline `zero_touch_orchestration.py`: 1,762 lines.
- Pre-remediation Phase 15B state: 1,937 lines, `+194/-19` (net `+175`).
- Post-remediation state: 1,935 lines, `+205/-32` (net `+173`).
- Net Phase 15B complexity reduced by two lines; no new owner or dependency direction was
  introduced.
- Post-remediation method sizes / structural branch constructs:
  `review_document_field` 60/3; `_refresh_document_checkpoint_locked` 44/4;
  `_return_to_document_intake` 21/1; `_current_documents` 5/0;
  `_advance_locked_impl` 291/37. The progression method fell from the gate-recorded 293
  lines and retained 37 structural branch constructs.
- Remaining logic is cohesive because the orchestrator already owns case-lock workflow
  refresh, blocker invalidation, resume, and target-ledger entry; document meaning,
  reconciliation meaning, authorization, persistence CAS, and target ordering remain in
  their existing owners.

### Physical Mongo coverage and result

`tests/test_phase12_real_mongo.py` now includes:

- a genuine partial review (one field final, three pending) persisted across a fresh app
  composition, remaining blocked with identical automation version and zero
  ownership/target calls;
- an actual replacement whose configured test IDP fails after the replacement becomes
  current, preserving `PENDING_INPUTS / DOCUMENT_REUPLOAD_REQUIRED` across restart,
  followed by targeted retry/start and exact provider call counts;
- the distinct-store contradictory-review CAS race strengthened with a third fresh store
  reload proving the single persisted winner and no losing overwrite;
- the existing physical reconciliation CAS/unit-of-work and target-ledger restart cases.

Exact physical command:

```text
python -m pytest tests/test_phase12_real_mongo.py -q -ra -p no:cacheprovider
```

Result: **14 skipped** because `PHASE12_MONGO_URI` is not configured. No `.env`, private
artefact, URI, database, or cleanup operation was accessed. Physical execution and
cleanup-absence evidence remain pending; persistence readiness is therefore **PARTIAL**.

### Verification

- Focused mandatory failure-window slice: **PASS**, 6 parameter-expanded cases before
  the replacement-CAS addition; the final two-case replacement boundary slice also
  **PASS**.
- Planner document/reconciliation/zero-touch suite: **PASS**.
- Planner persistence/auth/administration suite: **PASS**.
- Full backend: **PASS — 999 passed, 17 skipped, 1,016 collected**. The skips are the
  14 physical Phase 12 cases plus the Phase 13, Phase 14, and Phase 14.5 physical modules.
  Only the three pre-existing Pydantic negative-fixture warning groups were emitted.
- `python -m ruff check .`: **PASS**.
- `python -m mypy app`: **PASS**, 91 source files.
- `python scripts/check_secrets.py`: **PASS**; supported configured patterns only.
- `python scripts/check_project_state.py`: **PASS**.
- `python scripts/check_architecture.py`: **PASS**; this static check does not replace
  independent semantic re-review.
- `python scripts/dev_context.py`: **PASS**; branch/HEAD/origin-main remain aligned to
  `a81e7da1c677f063408952e2ae1a1a2478afc22b`.
- `git diff --check`: **PASS** with line-ending notices only.

Security review found no additional active defect: safe typed messages contain no field
value, note, payload, token, URI, or private exception; in-lock authorization remains
before mutation; failed prerequisites stop downstream calls; upload and provider labels
remain unchanged. The POC regression catalogue was not changed. Full-backend evidence
preserves accepted terminal states, Mock/Local labeling, target prefixes, no false
completion, and no Ready-for-Approval or Live claim.

### Pre-physical limitation and next action

At this point in the pre-physical report, no API/model/schema/configuration/provider
classification/source-precedence/business-rule mapping or target-ledger contract had
been added. Contracts changed only to record the owner-authorized sequential recovery
and explicit failure boundaries. Physical Mongo execution was the remaining acceptance
blocker; the dated verification below supersedes that blocker. Independent Phase 15B
re-quality-gate review remains required. Do not begin Phase 15C or self-issue PASS.

## Physical verification after test-contract remediation — 2026-09-19

Status: **REMEDIATION VERIFIED — PHYSICAL EVIDENCE COMPLETE — RE-QG REQUIRED**

The owner-supplied initial physical result was 14 executed, 13 passed, and 1 failed in
`test_real_mongo_failed_replacement_restart_requires_retry_without_replay`. The failure
was a test/API contract mismatch: the domain-only `is_current_evidence` convenience
property is defined as `superseded_by_document_id is None`, while the intentionally
bounded `DocumentProcessingResponse` exposes the underlying lineage fields and does not
expose that property. The replacement service invariant makes that public relationship
unambiguous for this one-original/one-replacement scenario: the original points to the
failed replacement, and the failed replacement has no successor. A second latent
test-projection mismatch surfaced after that correction: the case response exposes
automation events as `timeline`, not `events`.

The correction was test-only. It selects the sole current document through
`superseded_by_document_id is None`, verifies both lineage directions and the original's
supersession timestamp before and after fresh composition, and reads
`DOCUMENT_REUPLOAD_REQUIRED` through the existing public `timeline`. It also proves that
the original exception is rejected as `ZERO_TOUCH_EXCEPTION_STALE`, that targeted retry
supersedes the retained failed replacement, and that ownership/target counters remain
zero until the subsequent explicit completion/start. No production source, public API,
model, schema, connector, configuration, business rule, mapping, authorization,
architecture, provider classification, or target-ledger contract was changed by this
physical remediation.

The corrected single-test command passed before the full run:

```text
python -m pytest tests/test_phase12_real_mongo.py::test_real_mongo_failed_replacement_restart_requires_retry_without_replay -q -ra -p no:cacheprovider
```

Final physical command:

```text
python -m pytest tests/test_phase12_real_mongo.py -q -ra -p no:cacheprovider
```

Final result: **14 collected, 14 executed, 14 passed, 0 skipped**. A separate collection
check also reported exactly 14 tests. There were no acceptance-relevant skips.

Physical evidence retained by the green suite includes:

- partial-review restart: one final field decision and three pending fields remain
  durably blocked across fresh application composition with unchanged automation version
  and no ownership or target calls;
- failed-replacement restart/retry: the failed replacement remains the sole current
  evidence head in `PENDING_INPUTS / DOCUMENT`, the original remains superseded history,
  the old exception is non-actionable, targeted retry chains from the retained failed
  document, and explicit completion/start progresses only afterward;
- CAS fresh reload: the distinct-store contradictory-review race is reloaded through a
  third fresh store and retains exactly the single durable winner without loser overwrite;
- target ledger/no replay: restart and stale-action probes produce no provider work, and
  the failed-replacement case finishes with exactly one ownership call and the accepted
  four-operation Mock GoldTier sequence only after explicit completion/start;
- generated database cleanup: every physical-test fixture used a generated allowlisted
  Phase 12 database, dropped it, and verified its absence; any cleanup failure would have
  failed the suite;
- the protected shared database was not accessed, listed, modified, or cleaned;
- the connection URI was supplied only ephemerally to the process and was not persisted,
  printed, or added to this report.

Git status after the physical run remained intentionally dirty with the existing Phase
15B work: **23 paths total (19 modified, 4 untracked), 0 staged**. No stage, commit, push,
PR, merge, rebase, reset, stash, clean, or branch switch was performed. Independent Phase
15B re-quality-gate review remains required; this report does not issue QG PASS.
