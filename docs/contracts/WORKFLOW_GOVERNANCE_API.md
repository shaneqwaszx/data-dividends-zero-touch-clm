# Workflow governance API contract (C0 freeze)

Status: **FROZEN for M1** (2026-11-17). Authority: ADR-017 (D-135), B-0 final (D-1), the
workflow designer programme (D-1 to D-12, owner-approved 2026-11-17).

| Artefact | Path |
|---|---|
| Domain and storage models, limits, error codes, hashing | `apps/backend/app/domain/workflow_governance.py` |
| Request and response models | `apps/backend/app/api_workflow_governance_models.py` |
| TypeScript types | `apps/frontend/src/workflowGovernanceTypes.ts` |
| Synthetic fixtures (generated from the models) | `docs/contracts/fixtures/workflow-governance/` via `scripts/generate_workflow_governance_fixtures.py` |
| Contract tests | `apps/backend/tests/test_workflow_governance_contract.py`, `apps/frontend/src/workflowGovernanceContract.test.ts` |

**Changing the contract** after the freeze needs a short contract-change note in this file and
the integrator's approval. A workstream never changes it on its own. Regenerate the fixtures
with the generator; the contract tests fail on any drift.

## 1. Principles (unchanged by this contract)

- Backend-authoritative. Every route is `ACTOR_ONLY` in `ROUTE_POLICIES`, and the actor is
  **reauthorized inside the definition lock**. The `can_*` flags in responses only shape the UI.
- `ROLE_CAPABILITIES` does not change. HR (`POLICY_MUTATE`) authors. One Director
  (`POLICY_APPROVE`) decides. **Self-decision is refused three ways:** role, a service identity
  check, and the `WorkflowProposal` / `VersionProvenance` model validators.
- Every mutation is one compare-and-set on the definition document (revision **and**
  `write_nonce`) under the durable write rule. Requests carry `expected_workflow_revision` and,
  for an existing proposal, `expected_proposal_revision`. A mismatch is `409 WORKFLOW_CONFLICT`
  (existing code).
- Simulation is **synthetic only**: a fixed scenario catalogue, no case read, no provider call,
  no write.
- No route-to-Mongo access, no second persistence owner. The assistant gets no new tool or data,
  and cannot author, decide or fall back.

## 2. Storage (B-0 final)

- The definition `payload` keeps its exact P2-0 shape (`WorkflowDefinition`, `extra="forbid"`).
- Governance state is in reserved top-level fields: `required_baseline`, `open_proposal`,
  `decided_proposals`, `governance_events`, `notices`, `outbox`, `version_provenance`,
  `p2_1_migration_marker`, `governance_sequence`. The P2-0 reverse-migration tool already
  refuses documents carrying the stored names (contract test).
- Cold, insert-only collections: `workflow_versions` (`logical_id = <wid>:<version>`),
  `workflow_proposals` (`logical_id = <proposal_id>`), `workflow_governance_events`
  (`logical_id = <wid>:<sequence>`). `_id = <logical_id>#<attempt>`; index on `logical_id`;
  the only mutable field is `archive_confirmations` (ADR-017 §5, R1-5).
- **Case snapshot schema stays 21. Schema 22 stays reserved for D-117.** No run schema change.

### 2.1 Immutable history (owner condition)

- A decided proposal stays in `decided_proposals` with its **complete record** (`record`) until
  its cold copy is durably acknowledged (`archived = true`). Only then may the hot entry drop to
  a summary. The model refuses an unarchived summary.
- An outbox entry is a reference (`collection`, `logical_id`, `content_hash`, `attempt`) to a hot
  record that **is still present in full**. A referenced version, proposal or event is never
  removed from the hot document before durable archival acknowledgement.
- Compaction moves only acknowledged items. Unacknowledged notices are never compacted. The
  silent 256-event truncation is removed. Nothing is truncated: past the ceiling a mutation is
  `503 WORKFLOW_HISTORY_UNAVAILABLE`.
- ADR-017 byte budget unchanged: version ≤ 1 MiB, proposal ≤ 1 MiB, notice ≤ 4 KiB, outbox ≤ 32,
  baseline ≤ 1 MiB, compaction from 4 MiB, ceiling 8 MiB. Fallback mode (no confirming writes)
  is the default for the archiver.

### 2.2 Migration (roll forward only)

- Until `p2_1_migration_marker` exists, every governance mutation is
  `503 WORKFLOW_GOVERNANCE_NOT_MIGRATED`, and the dispatch fence stays unavailable.
- The migration tool is **dry run only** in M1. It must be validated against (owner condition):
  mixed-version access (a P2-0 process against a migrated store fails closed with
  `P2_1_CONTENT_NOT_SUPPORTED_BY_P2_0` and makes 0 provider calls), an interrupted migration
  (re-running is idempotent and the marker is written last), and an accidental old-writer start.
- **Old-writer exclusion is partly operational (CC-2).** The P2-1 code refuses every legacy write
  to a migrated document, and P2-0 startup refuses migrated documents. The deployed P2-0 release
  itself cannot be changed, so the backend must be stopped for the whole migration window and no
  P2-0 process may be started against a migrated store.

### 2.3 Empty workflows (owner condition, D-7)

- HR creates **empty non-onboarding workflows** (`POST /api/workflows`, now `POLICY_MUTATE`).
  They have `active_version = 0`, start no runs and are `DRAFT` until an approved proposal
  publishes a first version.
- A `CHANGE` proposal for a non-onboarding workflow with zero stages, or with a stage without
  fields, is refused at validate, submit and approve (`WORKFLOW_PROPOSAL_EMPTY` /
  existing structure codes). Nothing in a workflow proposal can remove or bypass the code-owned
  onboarding stages or engine order (RR-9), D-136 E1–E4, or the dispatch fence.

## 3. Routes

All paths are under `/api`. `wid` = workflow id, `pid` = proposal id.

| Method and path | Who | Request | 200 response | Milestone |
|---|---|---|---|---|
| `POST /workflows` | HR | existing `CreateWorkflowRequest` | `WorkflowResponse` | M1 (role moves to HR, D-7) |
| `GET /workflows`, `GET /workflows/{wid}` | HR, Director (read) | — | `WorkflowResponse` + `governance: WorkflowGovernanceView \| null` | M1 |
| `POST /workflows/{wid}/proposals` | HR | `CreateProposalRequest` | `ProposalResponse` (201) | M1 (`CHANGE` only) |
| `PUT /workflows/{wid}/proposals/{pid}` | HR author | `UpdateProposalRequest` | `ProposalResponse` | M1 |
| `POST /workflows/{wid}/proposals/{pid}/validate` | HR | `ValidateProposalRequest` | `ValidationReport` (read-only) | M1 |
| `POST /workflows/{wid}/proposals/{pid}/simulate` | HR | `SimulateProposalRequest` | `SimulationResult` (read-only) | M1 (D-5) |
| `GET /workflows/simulation-scenarios` | HR | — | `SimulationScenario[]` | M1 |
| `POST /workflows/{wid}/proposals/{pid}/submit` | HR author | `SubmitProposalRequest` | `ProposalResponse` | M1 |
| `POST /workflows/{wid}/proposals/{pid}/withdraw` | HR author | `WithdrawProposalRequest` | `ProposalResponse` | M1 |
| `GET /workflow-approvals` | Director | — | `ApprovalInboxResponse` | M1 |
| `GET /workflows/{wid}/proposals/{pid}/comparison` | Director | — | `ComparisonResponse` | M1 |
| `POST /workflows/{wid}/proposals/{pid}/decision` | Director, not author | `DecisionRequest` | `DecisionResponse` | M1 |
| `POST /workflows/{wid}/activate` | — | — | **410 `WORKFLOW_ROUTE_RETIRED`** | retired in PR-4 |
| `PUT /workflows/{wid}/draft` | — | — | **410 `WORKFLOW_ROUTE_RETIRED`** | retired in PR-5, together with its UI |
| restore, reset, emergency fallback, deactivate, reactivate, release, copy, notices | HR, Director | M2 contract addendum | — | M2 |

**Route retirement (owner condition).** A route is retired in the **same PR** as the frontend
change that stops calling it: `activate` has no caller since Track A (#197); `PUT …/draft` is
retired in PR-5 with the editor that replaces "Save draft".

### 3.1 Semantics

- **Create.** One open proposal per workflow (`409 WORKFLOW_PROPOSAL_OPEN`). `base_version` is
  the stored `active_version` (0 when none). Without `stages`, the proposal starts from the
  active version's stages. M1 accepts `CHANGE` only (`422 WORKFLOW_PROPOSAL_KIND_NOT_AVAILABLE`).
- **Edit.** `DRAFT` only, author only. Updates `last_activity_at`.
- **Validate.** Structure, the byte budget (`WORKFLOW_PROPOSAL_TOO_LARGE`) and the ratchet
  RR-1 to RR-10 against **both** the active version and `required_baseline`. Returns every issue
  with its rule, and the permanent obligations the proposal would add (§1.3). Writes nothing.
- **Submit.** Author only, `DRAFT` only. The ratchet and budget re-run; refused with the first
  rule's code (`422 …_REMOVED` / `…_WEAKENED`, `rule` set, all `issues` listed). The supplied
  `content_hash` must equal the recomputed one (`409 WORKFLOW_PROPOSAL_CONTENT_CHANGED`).
  `base_version` must equal the active version (`409 WORKFLOW_PROPOSAL_STALE`). The content is
  then frozen.
- **Withdraw.** Author only, `DRAFT` or `PENDING_APPROVAL`. Terminal `WITHDRAWN`.
- **Decision.** Inside the lock after reauthorization: capability; workflow and proposal
  revision; `PENDING_APPROVAL`; not the author (`403 WORKFLOW_SELF_DECISION_REFUSED`); content
  hash; base version still active (`409 …_STALE`); the ratchet; and, on `APPROVE`,
  `acknowledged_permanent_obligations` exactly equal to the comparison's set
  (`409 WORKFLOW_PERMANENT_OBLIGATION_ACKNOWLEDGEMENT_REQUIRED`). Reason 10–240 characters.
  **Approve** writes, in one durable compare-and-set: the terminal proposal (full record), the
  new version (`latest_version + 1`), `active_version`, `latest_version`, a new `write_nonce`,
  the stricter baseline, the `GOVERNED_APPROVAL` provenance, the events and the outbox
  references. **Reject** writes the terminal proposal, its event and outbox reference. A second
  decision fails on revision or state; a decision never publishes twice.
- **Publication report.** After commit, from case ledger records only (never the D3 counter);
  live `TENTATIVE` claims are reported as possibly authorised.
- **Read.** `governance` is `null` until the marker exists. Legacy versions show
  `PRE_GOVERNANCE_DIRECTOR_ACTIVATION` with the fixed note and are never shown or counted as
  approved.

## 4. Error codes (frozen)

`GOVERNANCE_ERROR_STATUS` in the domain module is authoritative. The body is
`GovernanceErrorBody {code, message, rule, issues}` in `HTTPException.detail`, the same
`{code, message}` shape existing routes use. Existing codes (`WORKFLOW_FORBIDDEN` 403,
`WORKFLOW_NOT_FOUND` 404, `WORKFLOW_CONFLICT` 409, `WORKFLOW_UNAVAILABLE` 503 and the structure
codes) keep their meaning. Inaccessible items stay a safe `404`.
`WORKFLOW_PUBLICATION_FROZEN` is removed when activation is retired (PR-4).

## 5. Workstream ownership (exclusive)

| Workstream | Owns |
|---|---|
| WS-A persistence | `services/workflow_repository.py`, `persistence/mongo_workflow_store.py`, new `persistence/workflow_governance_store.py` (cold store and archiver), new `persistence/p2_1_migration.py`, their tests |
| WS-B service and routes | `services/workflow_management.py`, new `services/workflow_governance.py`, new `services/workflow_ratchet.py`, new `services/workflow_simulation.py`, `api_workflows.py`, their tests |
| WS-C HR editor | `pages/WorkflowDesigner*`, `pages/WorkflowManager.tsx`, `workflowApi.ts`, new `workflowGovernanceApi.ts`, new editor components, their tests |
| WS-D Director UI | new `pages/WorkflowApprovals*`, `pages/WorkflowCompare*`, new `workflowApprovalsApi.ts`, their tests |
| WS-E physical harness | new `tests/test_workflow_governance_*_real_mongo.py` and helpers |
| Integrator | this contract, the two contract modules, fixtures, `app/main.py`, `services/authorization.py`, `apps/frontend/src/types.ts`, `App.tsx` routing, `docs/decisions/DECISION_LOG.md`, `docs/PROJECT_STATE.md` |

## 6. Contract-change notes

- **CC-1 (2026-11-17, integrator).** Fixtures only: the sample simulation scenario now uses a
  real `RegistryLegalForm` value (`COMPANY`, id `company-clear`) instead of an invented label.
  `SimulationScenario.legal_form` must always be a `RegistryLegalForm` value. The frontend reads
  the fixtures through `apps/frontend/src/test-fixtures/workflowGovernance.ts` (static JSON
  imports), so the browser tsconfig needs no Node types. No model or route changed.
- **CC-2 (2026-11-17, integrator).** Wording only. `PermanentObligationChange.TIGHTENED` also
  covers a dropped `case_data_key` (ADR-017 §1.3 with §2 "absent once absent"; PR-2 QG P2-1).
  §2.2 now states that old-writer exclusion is partly operational (PR-1 QG P2-2).
- **CC-3 (2026-11-17, integrator).** Sequencing only. The backend retires both `POST …/activate`
  and `PUT …/draft` in PR-3/PR-4, while the frontend stops calling `PUT …/draft` in PR-5. The two
  are integrated together on `feat/workflow-governance-m1` and must never be merged or deployed
  apart, so the route and its UI still retire together (PR-3/PR-4 QG P2).
- **CC-4 (2026-11-17, integrator). M2 addendum (additive).** Recovery and administration, per
  ADR-017 §1.2, §4 and §5. New models: `EmergencyFallbackRequest`/`Response`,
  `ReleaseDraftRequest`, `CopyProposalRequest`, `WorkflowVersionResponse`, `NoticeItem`,
  `NoticeListResponse` and `AcknowledgeNoticeRequest`.
  - **Restore and reset.** `RESTORE_VERSION` (with `restore_target_version`) and
    `RESET_TO_DEFAULT` go through the existing create and decision routes. HR proposes and one
    Director decides. The published content is always the **safe target**:
    `base ∪ required_baseline`. The proposal's stages are computed by the backend, never by the
    client.
  - **Deactivate and reactivate.** `DEACTIVATE` (no stages) and `REACTIVATE` (full stages that must
    satisfy the baseline) apply to non-onboarding workflows only.
    - Deactivation writes `active_version = 0`, keeps `latest_version` and the baseline, never
      modifies a run, and blocks new runs.
    - It is refused with `409 WORKFLOW_RUN_CONFIRMATION_IN_PROGRESS` while any run of that workflow
      is inside a required-stage confirmation. The confirmation-gate lock is shared by both paths.
  - **Emergency fallback** (`POST /workflows/{wid}/emergency-fallback`).
    - It is the Director's single-actor exception, and a mandatory reason is required.
    - It publishes the safe target of a version or of the default, with origin
      `EMERGENCY_FALLBACK` and `approved_by = null`.
    - It marks any open proposal `STALE`, keeping it, and raises a persisted notice that stays until
      an HR user acknowledges it.
    - At 64 unacknowledged notices it is refused with `409 WORKFLOW_NOTICES_UNACKNOWLEDGED`.
    - It can never bypass the ratchet, the mandatory stages, D-136, the fence or the ledgers.
  - **Release** (`…/proposals/{pid}/release`). Any HR user except the author may release a draft
    after 14 days without activity, or when its author's account is disabled or deleted. Otherwise
    it is refused with `409 WORKFLOW_DRAFT_NOT_RELEASABLE`. The draft becomes `WITHDRAWN` with
    `released_by`, and its content is kept. Directors cannot release.
  - **Copy** (`…/proposals/{pid}/copy`). It creates a new `DRAFT` authored by the copier, with
    `copied_from`. One open proposal per workflow still applies.
  - **Notices.**
    - `GET /workflows/notices` lists unacknowledged notices.
    - `POST /workflows/notices/{id}/acknowledge` is HR only. It sets `acknowledged_by` and
      `acknowledged_at`, which is the only permitted change, and records an event.
  - **Versions.** `GET /workflows/{wid}/versions/{n}` reads hot, then cold. Legacy versions are
    never shown as approved.
  - **Simulation** stays synthetic only.
