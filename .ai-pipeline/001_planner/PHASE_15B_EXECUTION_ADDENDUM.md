# Phase 15B Execution Addendum

Date: 2026-09-19<br>
Branch: `phase/15b-review-rework`<br>
Planning baseline: `a81e7da1c677f063408952e2ae1a1a2478afc22b`<br>
Observed `HEAD` / locally known `origin/main`: `a81e7da1c677f063408952e2ae1a1a2478afc22b`

This addendum refines, but does not replace,
`PHASE_15B_REVIEW_REWORK_STABILIZATION.md`. It records the implementation-time
feasibility boundary before automatic continuation is changed.

## Feasibility decision

The bounded backend repair may proceed inside the existing document, reconciliation,
zero-touch, authentication, and persistence owners. It requires no frontend, schema,
repository, provider, cache, Camunda, assignment, reviewer-identity, or UBO change.

The supported guarantee remains the documented single-application-process POC. The
repair can provide monotonic durable checkpoints and explicit recovery; it cannot claim
one atomic transaction across document, reconciliation, automation, and target-ledger
sections or general multi-instance exactly-once execution.

## A. Stale request boundary

`DocumentFieldReviewRequest` contains exactly:

- `field_key`;
- `decision`;
- `corrected_value`;
- `note`.

It contains no expected document event count, document version, reconciliation
fingerprint, or automation version. Therefore the review API can and will distinguish:

1. a document that is already non-current/superseded;
2. a contradictory final decision already persisted for a current field;
3. an exact repeated final decision, which remains idempotent;
4. version/fingerprint mismatch on the separate exception and reconciliation-resolution
   contracts that already carry those values.

It cannot distinguish a stale browser whose submitted field-review body is byte-for-byte
identical to a currently valid request. No hidden header, optional token, new request
field, or second version system will be added. The API contract and this limitation stay
explicit.

Within one application process, the existing case `RLock` serializes review mutations.
Across application processes, Mongo envelope revision CAS admits one durable repository
write winner in the bounded physical race test. The review request still has no
client-supplied compare-and-set token, and the losing raw repository conflict is not a
stable public stale-review contract. That stronger API guarantee remains outside Phase
15B.

## B. Persistence and commit boundary

### Candidate preparation and commits

- `DocumentProcessingService` reads defensive copies, changes a candidate, and commits
  each document event through `DocumentProcessingRepository.save`.
- `ReconciliationService` prepares a complete current reconciliation candidate and
  commits it through `ReconciliationRepository.save`; legal-name canonical selection
  alone uses the existing reconciliation unit of work.
- `ZeroTouchOrchestrator` prepares automation candidates and commits them through
  `ZeroTouchAutomationRepository.save(expected_version=...)`.
- The target execution service remains the sole owner of durable intent, attempted
  operation, outcome, receipt, and finalization checkpoints before/after external calls.

In Mongo mode, each repository save acquires the store lock, reloads the current whole
case envelope, updates its owned section, and replaces the envelope with revision CAS.
The reconciliation legal-name unit of work commits canonical and reconciliation state
in one envelope CAS. Ordinary document + reconciliation + automation refresh is a
sequence of individually durable section commits, not one transaction.

### Failure and visibility

- In-memory repositories persist validated deep copies; an uncommitted candidate is not
  exposed by a rejected save.
- Mongo rejected-CAS candidates are not persisted, and another writer's accepted
  envelope is retained.
- A failure after an earlier section commit intentionally retains that earlier durable
  evidence. The operation does not roll it back and does not call the target from a
  rejected later automation save.
- A repeated identical review and the explicit `/resume` mutation are recovery paths:
  they compare current document/reconciliation evidence and repair a stale waiting
  checkpoint without appending another document decision.
- Expected replacement-processing failure is distinct from rejected upload and
  persistence failure. Only the expected provider-processing failure, after the
  document owner has retained a current failed replacement and superseded history,
  triggers the document re-upload checkpoint.
- A repository write/CAS failure is not translated into successful recovery and is not
  described as atomic. It fails without target continuation; the retained state and
  explicit retry/resume evidence determine the next safe action.

The repair will persist an automation invalidation/progression checkpoint before any
new downstream stage can call the target. A losing automation CAS therefore performs
no target operation. This is narrower than a distributed workflow guarantee.

## C. Existing persisted cases and fingerprint compatibility

The reconciliation fingerprint stays the one canonical owner and persisted field. Its
domain namespace will advance from `phase-11-reconciliation-evidence-v1` to a Phase 15B
revision because effective-value semantics now include final review decisions. No new
persisted version field or parallel hash is introduced.

Consequences:

- a retained pre-Phase-15B reconciliation no longer compares equal after an explicit
  review/recovery mutation;
- `reconcile_current` cancels old open discrepancies as historical evidence and creates
  current results under the existing owner;
- reads alone remain read-only and do not migrate or recover state;
- an exact repeated review can repair an interrupted composite update without another
  document event;
- explicit `/resume` may refresh a document-stage waiting case, but `/start` and GET
  retain their current non-refresh behavior;
- completed or target-attempted histories are never reopened or rewritten by review.

## D. Effective reviewed evidence

The immutable per-case policy snapshot supplies the confidence threshold. Global policy
changes after case creation do not reinterpret the case.

- `ACCEPTED`: original provider value, provenance, timestamp, and confidence remain the
  effective observation.
- `CORRECTED`: only a present, valid original at or above the snapshot threshold may
  use the corrected value. Existing field normalization/validators determine whether
  the correction is valid.
- A corrected effective observation is projected as `source_system=HUMAN_REVIEW`, an
  opaque review reference, the decision timestamp, and no invented extraction
  confidence. The document record continues to retain the original IDP value and
  provenance separately.
- `REJECTED`: unusable/replacement-required.
- Missing, unavailable, invalid, or below-threshold original evidence remains unusable
  even when the operator entered a correction.
- Once any field review has begun, remaining `PENDING` fields remain review-blocking;
  partial review cannot clear reconciliation or resume.
- The original all-pending clean automatic-confirmation path remains unchanged.

No correction directly overwrites canonical data. The existing legal-name
`USE_DOCUMENT_VALUE` reconciliation unit of work remains the only bounded document-value
canonical update.

## E. Authorization linearization point

The API captures the session cookie and supplies a narrow reauthorization callback.
Each covered service invokes it after acquiring the canonical case lock and immediately
before reading actionable evidence or writing state. The callback calls the existing
`AuthenticationService.authenticate_session` and `CaseAccessPolicy.require_case_access`;
it does not reuse `request.state.actor` as current authority.

Covered mutations are field review, replacement, failed-document retry, reconciliation
resolution, exception resolution, intake completion/start, and explicit resume. Invalid
or revoked session remains `401`; inaccessible/cross-team case remains the fixed safe
`404`.

The linearization claim is process-local: authority is current when checked inside the
case mutation lock. This is not distributed instantaneous revocation. Administration
persists profile authority before revoking sessions and does not hold its repository
critical section while the reauthorization callback acquires the session/profile read
path, avoiding an inverted case/admin lock cycle.

## F. Narrow state changes and recovery

- Current zero-touch review is allowed only during `PENDING_INPUTS` or a document-stage
  `WAITING_FOR_REVIEW`. Manual documents without an automation record keep their lawful
  document-service behavior and do not create automation implicitly.
- Current evidence cannot be reviewed after workflow progression has bound it to
  Ownership, readiness, an attempted target operation, terminal completion, recovery,
  or technical failure.
- A changed decision cancels only active document-stage exceptions, saves a
  `RESUMING / DOCUMENT` checkpoint, and advances through the existing reconciliation,
  stage, and target-ledger owners.
- A coherent exact repeat changes no document event, reconciliation version, automation
  version, provider call count, or target call count.
- An explicit resume refreshes only a document-stage waiting case whose current
  fingerprint/checkpoint is stale. An unchanged unresolved case returns unchanged.
- Expected processing failure for an accepted replacement cancels document-stage
  exceptions and writes the narrow `PENDING_INPUTS / DOCUMENT` recovery state with
  `DOCUMENT_REUPLOAD_REQUIRED`, retaining the failed replacement, superseded history,
  unrelated evidence, and target ledger.
- The legal transition validator admits `WAITING_FOR_REVIEW -> PENDING_INPUTS` only for
  that exact document-stage recovery event/invariant; it is not added to the general
  status transition set.

## G. Stop and verification boundaries

Stop the dependent slice if implementation requires a public review-version field,
schema change, repository redesign, second authorization/evidence owner, generic
override, frontend edit, or an atomic/distributed guarantee beyond the boundaries above.

Required verification remains the planner matrix. Physical Mongo evidence must use an
explicitly authorized generated allowlisted disposable database. If such access is not
available, implementation/unit work may finish but the final status must remain
`BACKEND IMPLEMENTATION PARTIAL — REQUIRED EVIDENCE/BLOCKER OUTSTANDING`.
