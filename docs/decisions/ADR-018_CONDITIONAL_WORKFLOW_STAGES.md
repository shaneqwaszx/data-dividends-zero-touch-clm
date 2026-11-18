# ADR-018: Conditional, entity-specific workflow stages and fields (P2-3)

## Status

**ACCEPTED by the owner (2026-11-18):** decisions B1–B11 as recorded. The targeted independent
design review was READY WITH NOTES (R3), and its notes are resolved in R4.

Drafted 2026-11-17 for separate owner approval, within the scope the
owner fixed in advance (programme decision D-10, 2026-11-17). "D-10" here always means the
workflow designer programme's owner decision (`WORKFLOW_DESIGNER_PROGRAMME.md` §10). It is not
DECISION_LOG `D-010`, which is unrelated (deterministic UBO calculation). Revised 2026-11-18
after an independent doc review (READY WITH NOTES), then again for the owner's decisions B1 to B11
of 2026-11-18 (B1 and B2 revised: conditional onboarding, with the basis frozen at the first
registry binding).

This ADR is a design record only:
- **Nothing in it is implemented.** Current behaviour is unchanged.
- It is not sponsor-confirmed. Authority: `USER_AUTHORIZED_POC`.
- Implementation (PR-9 backend, PR-10 UI) follows this acceptance, each with its own QG.

Decision record: to be allocated in [DECISION_LOG](DECISION_LOG.md) at integration.

**Extends:** ADR-017 (§2 ratchet, RR-8 and the baseline; §1.3 permanent-obligation warning; §6
simulation), ADR-016 (designer), ADR-014 (Director-managed workflows).
**Activates:** the reserved `FieldSignature.applicability` and RR-8, inert until this ADR.
**Replaces, when PR-10 ships:** the P2-2 C-5 "Entity applicability" placeholder.

## Date

2026-11-17

## Context

- Every workflow stage and field applies to every case. HR cannot add an obligation that only
  applies to, for example, limited partnerships.
- ADR-017 reserved the hook. RR-8 refuses narrowing applicability. The baseline keeps "the
  broadest applicability ever published". `FieldSignature.applicability` is fixed at `None` in
  the frozen M1 contract (`WORKFLOW_GOVERNANCE_API.md`, `workflow_governance.py`).
- P2-2 ships a frontend-only placeholder (C-5). "All entities" is the only selectable value, and
  the six `RegistryLegalForm` options are shown disabled.
- The backend already has one bounded legal-form classification:
  `RegistryLegalForm {COMPANY, BUSINESS_PARTNERSHIP, LLP, LP, GOVERNMENT, OTHER}`
  (`domain/registry_legal_form.py`). It is derived from the canonical entity's `party_type`,
  which comes from ACRA `company.entityType` (`ACRA_CANONICAL_MAPPING.md`) through
  `classify_registry_legal_form`. Unmapped values become `OTHER`.
- How runs are made today (`services/workflow_management.py`):
  - **Non-onboarding run.** `start_run` builds it once, copying `version.stages`, and only for a
    case that has finished onboarding. Workflow-only (`NEW_CASE`) runs hold a `WorkflowCompany`
    with no legal form.
  - **Onboarding run.** `_onboarding_run` builds it from `case.created_at`, before registry
    verification. While the case is open, `_rebased` moves the run to each newly active version
    (owner decision 2026-11-14: open cases rebase).
  - **Send check.** `send_hold_code` enforces the run's own `stages`.
- **Where the registry binding is set** (`services/onboarding.py`,
  `_acquire_required_registry_evidence`):
  - The case receives `registry_acquisition`, `entity` and `registry_evidence_binding` together.
  - The engine then records `WorkflowState.REGISTRY_FETCHED`, which is the ACRA registry stage
    (`ACRA_REGISTRY`) completing.
  - The binding is created only through the registry acquisition coordinator
    (`registry_acquisition.py`, `_bound_result`). The direct-provider path and the government
    register path leave `registry_evidence_binding` as `None`.
  - An identity correction (`_acquire_registry_after_identity_recheck`) can replace the entity
    and the binding later.
- **Owner decisions of 2026-11-18** (B1 to B11): corporate onboarding must support
  entity-specific conditional stages, with the basis frozen once, at the first eligible
  authoritative registry binding.
- Fixed scope (D-10): add-only; deterministic on the backend `RegistryLegalForm` only; evaluated
  once at run creation and frozen; fail closed; RR-8; no reduced UBO or compliance obligations;
  governed like all other content.

## Decision

### 1. Scope, restated as rules

| ID | Rule |
|---|---|
| CA-1 | **Add-only.** A condition only ever **adds** obligations for matching entities. Nothing conditional removes, relaxes, skips or replaces an unconditional obligation, a code-owned stage or the engine order |
| CA-2 | **Deterministic on `RegistryLegalForm` only.** Only the existing enum values are used. No new classification is introduced. There are no free-text, numeric, ownership, risk, country, policy or AI conditions |
| CA-3 | **Evaluated once, frozen.** A non-onboarding run resolves its basis at creation. An onboarding run starts `UNVERIFIED` and freezes its basis once, at the first eligible authoritative registry binding (§3.5). The basis is stored on the run and never re-evaluated afterwards. Rebasing reuses it (§3.4) |
| CA-4 | **Fail closed.** If the classification is unknown, missing, unverified or `OTHER`, **every** conditional obligation applies |
| CA-5 | **RR-8.** Applicability is never narrowed. An unconditional obligation stays unconditional. The baseline keeps the broadest applicability ever published |
| CA-6 | **Mandatory, UBO and compliance obligations stay unconditional and protected.** The code-owned onboarding stages (`ONBOARDING_LOCKED_STAGES`) and the engine order cannot be conditional (RR-9, unchanged). UBO thresholds, ownership, screening, policy and existing compliance rules stay outside the editor. D-136 E1–E4, the dispatch fence and ledgers are unaffected |
| CA-7 | **Governed.** HR proposes and one Director approves (ADR-017 §1). The permanent-obligation warning covers every new conditional obligation and every broadening (§4.4) |

**Out of scope:**
- listed companies and financial institutions (they need a separate classification decision)
- any other jurisdiction
- conditions on anything but the legal form
- conditional removal or optionality ("required for X, optional for others")
- conditional mandatory stages

Listed companies and financial institutions fall inside `COMPANY` today. They receive every
`COMPANY` obligation, which is consistent with add-only.

### 2. Applicability model

#### 2.1 Field shape (proposed)

`WorkflowStage` and `WorkflowField` (`domain/workflows.py`) each gain one optional field:

```python
applies_to: tuple[ConditionalLegalForm, ...] | None = Field(
    default=None, min_length=1, max_length=5, exclude_if=lambda v: v is None
)
```

- **`None` means ALL** (unconditional). This is the default and the only value existing content
  has.
- **A non-empty tuple** means the obligation also applies to entities verified as one of these
  forms. Unverified entities get it too (CA-4).
- `ConditionalLegalForm` is the subset of `RegistryLegalForm` that can be selected:
  `COMPANY, BUSINESS_PARTNERSHIP, LLP, LP, GOVERNMENT`. **`OTHER` cannot be selected.**
- **Canonical form.** Duplicates are refused. Values are sorted ascending by enum value. A model
  validator normalises the order, so equal sets always serialise the same way. A tuple naming
  every selectable form is refused (`WORKFLOW_PROPOSAL_INVALID`, "use All entities"), so ALL has
  one representation only. `OTHER` is not selectable, because an `OTHER` entity is treated as
  unverified and already receives every conditional obligation (B5).
- **Stage and field.** A stage's `applies_to` governs the whole stage. A field's `applies_to`
  applies within its stage. A field set must be a subset of its stage set, otherwise it is
  refused. The **effective applicability** of a field is the intersection of the two, with ALL
  as the identity.
- **Not allowed:** `applies_to` on code-owned locked stages. They are not `WorkflowStage`
  records, and RR-9 is unchanged. Anchors (`after_node_id`) are unchanged.
- **Non-onboarding minimum.** A non-onboarding version must keep at least one stage that applies
  to ALL and holds at least one ALL field (an extension of `WORKFLOW_PROPOSAL_EMPTY`). This
  ensures no run is created with zero stages (B6).
- **Onboarding anchor eligibility (decided, B2).** On the onboarding workflow, a stage, or a
  field inside it, may carry `applies_to` only when the stage's `after_node_id` is
  `ACRA_REGISTRY` or a later anchor: `DOCUMENT_IDP`, `RECONCILIATION`, `OWNERSHIP_UBO`,
  `ADVISORY` or `GOLDTIER_DETAILS`.
  - At those anchors, the registry basis exists before the stage is reached in engine order.
  - Anything else is refused at validate, submit and approve (`WORKFLOW_PROPOSAL_INVALID`,
    issue "conditional before registry verification"). That covers the earlier anchors
    (`CASE_START`, `INITIAL_IDENTITY`, `JURISDICTION`, `GOLDTIER_SEARCH`) and a missing
    `after_node_id`.
  - Moving a conditional stage to an earlier anchor is refused for the same reason.
  - This is a structure rule, not a ratchet rule, so it also applies to optional content.
  - Display order does not stop an RM answering a later stage early. §3.5 rule F3 covers that.
- **Optional ALL → conditional required (decided, B9: refused).** An optional ALL field cannot
  become a conditional required field, because that would remove it for non-matching entities.
  HR keeps the optional ALL field and adds a new conditional required field beside it.
  Refused with `WORKFLOW_PROPOSAL_INVALID`.

#### 2.2 Content hash

- `proposal_content_hash` is unchanged. Because `applies_to` is excluded when it is `None`,
  every existing stage serialises byte-for-byte as before. **Existing proposal, version and
  record hashes are unchanged.** A golden-hash test proves this (CT-21).
- When it is set, `applies_to` serialises as a sorted JSON array of enum strings, under the
  existing `canonical_json` (sorted keys, no whitespace).

#### 2.3 Mapping into the baseline

The frozen contract reserves `FieldSignature.applicability: None`. Proposed:

| Model | Change |
|---|---|
| `FieldSignature.applicability` | `tuple[ConditionalLegalForm, ...] \| None`. `None` = ALL. Holds the field's **effective** applicability (§2.1), canonically sorted |
| `BaselineStage` | Gains `applicability: tuple[ConditionalLegalForm, ...] \| None = None` (the stage's own `applies_to`) |
| `BaselineField.representative`, `BaselineStage` representative content | Carry the baseline (broadest) applicability, so a safe target renders with it (§4.3) |

Every existing baseline entry already holds `None`, which now means ALL. **No baseline
migration is needed.**

**Reader break.** `FieldSignature`, `BaselineStage` and the other contract models use
`extra="forbid"` (`_Frozen`). Once a baseline holds a non-`None` applicability, or a
`BaselineStage.applicability` key, P2-1 code that predates this ADR cannot decode the
definition's top-level `required_baseline`. This is the same hazard as the payload break in §9,
and it is covered by the same rollout gate.

### 3. Evaluation at run creation

#### 3.1 Source of the legal form

The legal form comes only from the backend case record. It never comes from a request, a
document, AI output or the frontend:
- `case.entity.party_type`, classified by the existing `classify_registry_legal_form`. No second
  classifier is added.
- **Two adapter paths fill `party_type`.** Both are normalised in `connectors/registry.py`:
  - **ACRA Sandbox:** `entityType` (`connectors/acra_sandbox.py`).
  - **ACRA API Marketplace Mock:** `companyType` (`connectors/acra_api_marketplace_mock.py`).
- **Known defect and owner rule A4.** The review reports a `companyType` decoder defect that
  classifies OPQ as `OTHER`. Under this ADR such a case is `UNVERIFIED`, so every condition
  applies. That fails closed.
  - **Owner rule A4 (2026-11-18):** the decoder must use the documented canonical legal-form
    mapping (`ACRA_CANONICAL_MAPPING.md`). An unrecognised, ambiguous or conflicting
    classification must fail closed and never narrow silently.
  - The decoder fix is a **prerequisite change outside this ADR**. It needs its own review,
    and it must not alter `classify_registry_legal_form` without the CT-31 gate.
  - **Conflicting**, for this ADR: the classified form disagrees with the case's `uen_route`
    category. For example, the `GOVERNMENT` form under an ACRA route, or a non-`GOVERNMENT`
    form under the government register route. A conflict gives `UNVERIFIED`
    (`CONFLICTING_CLASSIFICATION`).
- **Residual risk (decided, B10: CT gate).** "Registry-bound" means **bound and classified**,
  not proven correct. A wrong but known form would drop the conditions for the true form; it
  never drops an unconditional obligation. CT-31 (now mandatory) freezes the mapping table: any
  change to it fails until it is reviewed.
- **Single classifier, enforced.** The evaluator imports `classify_registry_legal_form` only. A
  CT-23 source check fails if `services/workflow_*` or the evaluator contains its own `party_type`
  string table, or compares `party_type` text directly.

#### 3.2 What counts as registry-bound

A legal form `F` is **registry-bound** only when all of these hold at evaluation time:
1. `case.entity` is present.
2. `case.registry_evidence_binding` is present. Its model validator already guarantees a
   `COMPLETE` acquisition, `entity == acquisition.entity_profile`, a matching UEN and per-operation
   provenance.
3. `classify_registry_legal_form(case.entity.party_type)` is not `OTHER`, and does not conflict
   with `uen_route` (§3.1).

`SourceSystem` has only `ACRA` today, so a source-system check would always pass. It is kept
only as a defensive assertion: a future non-ACRA value is `UNVERIFIED`.

Anything else (no case, no entity, no binding, `OTHER`, a conflict, a decode or read failure, a
workflow-only `WorkflowCompany` case) gives the basis **`UNVERIFIED`**.

- **No binding means `UNVERIFIED`.** The government register path and the direct-provider path
  create no binding (Context), so they stay `UNVERIFIED`. A `GOVERNMENT` condition therefore
  never narrows today. This is fail-closed, and recorded rather than changed.
- **Environment (decided, B4).** A Mock ACRA binding counts. The source environment is
  recorded on the basis and is **always shown** with it, for example "Registry-bound (Mock):
  LLP".
- **Status naming (decided, B11).** `REGISTRY_BOUND` and `UNVERIFIED`. This ADR's prose word
  "verified" means registry-bound.

#### 3.3 Resolution and freezing

At creation, the run's stage copy is computed from the version with the basis `B`:
- **Stage.** A stage is kept if it is ALL, if `B` is `UNVERIFIED`, or if `B` is in its
  `applies_to`.
- **Field.** Within a kept stage, a field is kept by the same test on its own `applies_to`.
- **Emptied stage.** A stage dropped from the run only if applicability resolution **emptied**
  it: it had at least one field in the version, and none applies. A stage authored with zero
  fields (allowed for onboarding, which has no `WORKFLOW_PROPOSAL_EMPTY` rule) is copied
  unchanged, exactly as today. CT-23 tests both cases.
- **One resolved copy everywhere.** `start_run`, `_loaded_answers` (case-data prefill),
  `_onboarding_run`, `_rebased`, `send_hold_code` and D1 all work on the copy resolved with the
  **effective basis** (below). None of them reads the version's unresolved `stages` directly, so
  answers are never prefilled or kept for a stage or field the run does not hold. CT-24 asserts
  this.
- **The one named exception: `active_onboarding_stages`.** It is the read-only display of what
  the active version would enforce on a new open case. It shows the **unresolved** stages,
  labelled with their applicability. It never feeds the send check, D1 or a run.
- **Locked stages are untouched.** Resolution never removes or reorders
  `ONBOARDING_LOCKED_STAGES`, and never changes an added stage's anchor.
- **`applies_to` is kept** on the copied stages and fields, so the run shows why each one
  applies.

`WorkflowRun` gains `applicability_basis` (optional, excluded when `None`):

```python
class ApplicabilityBasis(_Frozen):
    legal_form: ConditionalLegalForm | None   # None when UNVERIFIED
    status: Literal["REGISTRY_BOUND", "UNVERIFIED"]   # naming: B11
    reason: Literal["REGISTRY_BINDING", "NO_ENTITY", "NO_BINDING", "OTHER_FORM",
                    "CONFLICTING_CLASSIFICATION", "AMBIGUOUS_BINDING",
                    "TOO_LATE_TO_NARROW", "NO_CASE_RECORD", "READ_FAILED"]
    source_environment: SourceEnvironment | None
    evaluated_at: datetime
    evaluated_from_version: int
    frozen: bool          # onboarding: False until the freeze write (§3.5); always True otherwise
    binding_ref: BindingRef | None   # cache_id, cache_revision, bound_to_case_at; no source text

class BasisConflict(_Frozen):       # onboarding only (§3.5, F5)
    detected_at: datetime
    observed_status: Literal["REGISTRY_BOUND", "UNVERIFIED"]
    observed_legal_form: ConditionalLegalForm | None
    binding_ref: BindingRef | None
    escalated_by: ActorId | None = None   # set by the audited escalation (F6)
    escalated_at: datetime | None = None
    escalation_reason: DecisionReason | None = None   # 10–240 characters, operator-entered
```

`WorkflowRun` also gains two fields, each excluded when it is `None` or empty:
- `basis_conflict: BasisConflict | None`
- `ever_touched: tuple[ObligationKey, ...]` (§3.5 F3). This is a **monotonic** record of every
  stage and field that has ever had an answer or a confirmation. Entries are only ever added,
  even when the answer is later cleared or the confirmation superseded.
  - It is **bounded**: it holds only keys that exist in some version the run has held, and each
    key at most once. That is at most 32 stages × (1 + 32 fields).
  - It is counted in the run's byte budget, which is checked before every run write.

**Effective basis.** Every consumer uses the run's **effective basis**:
- **Before the freeze:** `UNVERIFIED`.
- **After the freeze:** the frozen basis.
- **After an escalation** (`basis_conflict.escalated_at` set): `UNVERIFIED`, **permanently**.
  Nothing clears `escalated_at`.

The consumers are `_rebased`, `_onboarding_run`, `_loaded_answers`, `start_run`,
`send_hold_code` and D1. So a later version can never drop a stage that the escalation added.

- A run without a basis (every run created before this ADR) is treated as `UNVERIFIED`. Its
  stages were copied from unconditional content, so this changes nothing.
- A **frozen** basis is **never recomputed**. Later changes to the case record do not change the
  run: identity corrections, re-acquisition, a different `party_type`. They are handled by §3.5
  F5.
- **Determinism.** The same version and the same basis always give the same stage copy. The
  evaluator is a pure function, with no clock, I/O or randomness in the selection.

#### 3.4 Onboarding runs and rebasing

- **Non-onboarding `EXISTING_CASE` runs.** `start_run` requires a case that has finished
  onboarding, so the binding normally exists and the evaluation is meaningful.
- **Non-onboarding `NEW_CASE` runs.** The basis is `UNVERIFIED`, so everything applies.
- **Onboarding runs.** These start with `UNVERIFIED (NO_BINDING)`, `frozen: False`. Every
  conditional obligation applies until the freeze (§3.5).
- **Rebasing (decided, B3).** When an open onboarding case rebases to a newer version
  (`_rebased`), its **effective basis** (§3.3) is reapplied to the new version's stages:
  `UNVERIFIED` before the freeze, the frozen basis after it, and `UNVERIFIED` after an
  escalation. The classification is never re-evaluated by a rebase. Confirmations are kept only for a stage whose resolved copy is unchanged, as today.
  Answers are kept only for fields in the resolved copy (§3.3). A rebase never performs the
  freeze.

#### 3.5 Onboarding: freezing the basis at the first eligible registry binding (B1)

**F1. The freeze event.**
- **Trigger.** The first time a case snapshot write that sets a non-`None`
  `registry_evidence_binding` and records `REGISTRY_FETCHED` has been **committed**, in
  `_acquire_required_registry_evidence` after the case compare-and-set succeeds.
- **The hook.** The onboarding service then calls one new workflow hook,
  `freeze_onboarding_basis(case_id)`.
- **Where it runs.** It runs **inside the same `case_lock` critical section** as the binding
  write, which every run writer already takes. It reads the committed case and computes the
  basis (§3.2).
- **Locks.** It takes neither the per-workflow confirmation gate lock nor the definition lock.
  The existing lock order is unchanged: gate before case, and case before definition. The hook
  needs only the case lock and reads the definition without locking it.
- **Eligibility.** Every freeze, not only a late one, first applies the F4 eligibility tests.
- **The write.** It writes the onboarding run once, using the run repository's existing
  safeguards:
  - **A never-saved run:** insert-only `create`, with the basis.
  - **A stored run:** an `update` that compare-and-sets `revision` and asserts
    `payload.applicability_basis.frozen != true` **in the filter** (ADR-017 §3.2 style).
- **Duplicate key or no match.** Re-read under the lock, and repeat at most once. A run that
  already holds a frozen basis is never rewritten.
- **A Mock binding counts** (B4).

**F2. Safeguards and their limits.**
- **What they are.** Run documents use revision compare-and-set and insert-only create. They do
  **not** carry ADR-017's `write_nonce`, because that rule covers case snapshot and definition
  documents only.
- **Losing a freeze write fails safe.** That can happen through an ambiguous write outcome, a
  crash or a rollback. The run is then left `frozen: False`, which means `UNVERIFIED`, which
  means every condition applies. Loss can only broaden obligations, never narrow them.
- **What is not relied on.** A read-back is never treated as proof of the freeze.
- **The decision.** Adding a run `write_nonce` is therefore **not required** for safety. It is
  noted as optional hardening for the design review.

**F3. Too late to narrow.**
- **The test.** Resolve the run with `F`. Let `X` be the conditional stages and fields present
  in the current `UNVERIFIED` copy that `F` would exclude. **If any item in `X` is touched, the
  freeze writes `UNVERIFIED (TOO_LATE_TO_NARROW)`, `frozen: True`.**
- **Touched** is defined from **run history**, not from the current answers. Any of these
  counts:
  - an entry in `ever_touched` for a field in `X`, or for any field of a stage in `X`, from any
    source, including document suggestions and case-data prefill
  - a confirmation ever recorded for a stage in `X`
  - the case is already sent, or has a `target_dispatch_confirmation`
  - the case has any `workflow_dispatch` claim
- **Why history.** A lost `TOO_LATE` freeze followed by a cleared answer still counts as
  touched, so it cannot narrow on retry.
- **What it guarantees.** Completed, started or confirmed obligations are never removed
  retroactively. The run keeps everything.
- **Otherwise** the freeze writes `F` and the narrowed resolved copy in the same write. That is
  the only narrowing that ever happens, and it happens only once.

**F4. Ambiguous or late binding.**
- The hook can fail, for example because the store is unavailable or the process crashed after
  the case write. If so, the next run write under the case lock retries the freeze, but only if
  **all** of these hold:
  - the case's current binding is still its first
  - `identity_corrections` is empty
  - exactly one successful `REGISTRY_FETCHED` event exists
- Otherwise the freeze writes `UNVERIFIED (AMBIGUOUS_BINDING)`, `frozen: True`.
- F3 always applies to a late freeze.
- The same eligibility tests run first on **every** freeze (F1).

**F5. Freeze-once, and conflicts.**
- **The basis never changes after the freeze.** Re-acquisition, an identity correction or a new
  binding cannot change it, and nothing can narrow it.
- **Enforcement does not depend on the hook.** `send_hold_code` and D1 recompute the basis
  **read-only**, from the case they already load. They return the conflict hold if all of these
  hold:
  - the run's frozen basis is `REGISTRY_BOUND`
  - the recomputed basis differs from it in `binding_ref`, legal form or status
  - no escalation is recorded
- **One pure function.** The recompute is a single shared pure function,
  `basis_conflict_of(case, run) -> BasisConflictCheck`. Its callers are `send_hold_code`, D1,
  the hook and the escalation's persist-first step.
  - It is deterministic, with no clock, I/O or randomness. Times come from the caller.
  - It returns no conflict, a conflict, or `WORKFLOW_STAGE_CHECK_UNAVAILABLE` when the case or
    run cannot be read or decoded. The send check and D1 refuse on that result.
- **The hook only persists the conflict.** On every later case write that changes
  `registry_evidence_binding` or `entity`, the onboarding service calls the same hook. It writes
  `basis_conflict` so that the conflict is visible and can be escalated. If the hook is lost,
  enforcement still holds.
- **Only a `REGISTRY_BOUND` basis can conflict.** A run frozen as `UNVERIFIED` (for any reason)
  already applies everything, so a later binding adds nothing, and no conflict or hold arises.
- **A conflict** is a different legal form, a different status, or a binding for another
  identity. On a conflict, the hook:
  - writes `basis_conflict` to the run, under the same filter rules as F1
  - keeps the frozen stage copy unchanged
  - logs `WORKFLOW_APPLICABILITY_BASIS_CONFLICT`, with safe identifiers only
- **If the run was never frozen,** it stays `UNVERIFIED`. The F4 tests then make any later freeze
  `AMBIGUOUS_BINDING`.

**F6. Safe, audited recovery (add-only).**
- **The hold.** While a conflict exists (persisted, or recomputed under F5) and is unescalated,
  `send_hold_code` returns a new hold, `WORKFLOW_APPLICABILITY_BASIS_CONFLICT`. D1 refuses, and
  the run view shows an operator-visible notice.
- **The only recovery** is the **audited escalation** "Apply all conditional steps":
  - a filler-role action under the case lock, with a reason of 10–240 characters
  - it sets the run's effective basis to `UNVERIFIED` permanently (every condition applies),
    keeps all answers and confirmations, and records `escalated_by`, `escalated_at` and
    `escalation_reason`
  - if no conflict was persisted yet (because the hook was lost), it first persists the
    recomputed conflict
  - it **only adds** obligations
- **Narrowing after a freeze is impossible.** No action, route or tool can narrow a run's
  obligations after the freeze.
- **Records.**
  - **The run record is the authoritative audit:** `basis_conflict`, with the escalation
    fields and the reason.
  - **The case event is appended afterwards.** It goes through the onboarding owner
    (`OnboardingService._record`, under the case snapshot's revision-and-nonce compare-and-set),
    as one `WorkflowEvent`:
    - a new **`code` string only** (`WORKFLOW_APPLICABILITY_ESCALATED`, or
      `WORKFLOW_APPLICABILITY_BASIS_CONFLICT`)
    - `stage = case.state`
    - an existing `EventOutcome` value
    - a safe summary
  - **No new enum values.** Adding values to `WorkflowState` or `EventOutcome` is **forbidden**.
  - **No definition writes.** Nothing is written to the workflow definition document, which
    holds no case data.
  - **Effect on event counts.** Appending the event changes `len(case.events)`. The consumers of
    that token see the change and fail closed or retry; they never accept stale evidence:
    - `expected_case_event_count`
    - document processing
    - target-confirmation `evidence_version`

**F7. Unchanged.** Mandatory engine stages, UBO and compliance rules are never conditional
(CA-6, RR-9). The freeze touches only added workflow stages.

### 4. Ratchet extension (RR-8 made active)

#### 4.1 Definition

Let `A(o)` be an obligation's effective applicability, where ALL is the top element:
- ALL ⊇ any set
- a set `S1 ⊇ S2` by inclusion

**RR-8 refuses**, at validate, submit and approve, and for every publication kind (including
M2 restore, reset, reactivate and emergency fallback), checked against **both** the active
version **and** `required_baseline`:
- **RR-8a.** A required obligation (stage or field) whose candidate `A` does not include the
  baseline or active `A`. This is narrowing.
- **RR-8b.** A required obligation with baseline or active `A` = ALL that becomes a set. This is
  unconditional becoming conditional, a special case of 8a stated for clarity.
- **RR-8c.** A required field whose effective applicability narrows because its **stage's**
  `applies_to` narrowed, even if the field's own `applies_to` is unchanged.

**Allowed:**
- adding forms to a set
- set → ALL
- new conditional stages or fields
- optional → required with a condition (a new, conditional obligation)
- any change to optional content (D4)

RR-8 maps to `WORKFLOW_REQUIRED_OBLIGATION_WEAKENED` (it is already outside `REMOVAL_RULES`).

#### 4.2 Baseline maintenance

- **Seeding.** No change. Migrated content is ALL.
- **On every governed publication,** the baseline `A` for each required obligation becomes
  `A_baseline ∪ A_candidate`, which by RR-8 equals `A_candidate`. ALL absorbs every set. The
  update is in the same compare-and-set as the version (ADR-017 §1.1).
- **Deactivation keeps the baseline.** Reactivation must satisfy it (unchanged).

#### 4.3 Safe targets

A recovery publication's safe target (`base ∪ required_baseline`) uses the **baseline (broadest)**
applicability for every baseline obligation, even when `base` held it narrower. A safe target
never narrows:
- **Field widening.** Each baseline field takes its baseline effective applicability.
- **Stage widening.** If a baseline field's applicability is wider than its stage in `base`
  allows (the field ⊆ stage rule, §2.1), the stage's `applies_to` is widened to the baseline
  stage applicability, or to ALL if that is still too narrow.
- **No silent fallback.** If no widening can satisfy §2.1 and the baseline together, building
  the safe target raises `SafeTargetError`, and the recovery is refused. No partial target is
  published.

**Why a safe target never broadens beyond the baseline.** The baseline is a monotonic union of
every applicability ever published (§4.2). The safe target takes, per obligation,
`A_base ∪ A_baseline`. Since `A_base` was itself published, it is already inside `A_baseline`,
so the result equals `A_baseline` exactly. A safe target therefore adds no applicability that
was never approved, and it never changes the baseline.

#### 4.3a Emergency fallback (owner policy 2026-11-18)

This records the owner's clarification in ADR-017 §4 ("Owner clarification", integration
branch):
- **The baseline does not expand.** An emergency fallback's permanent-obligation set must be
  **empty**: no `NEW_REQUIRED_STAGE`, `NEW_REQUIRED_FIELD`, `TIGHTENED` or
  `APPLICABILITY_BROADENED`, and no new conditional obligation. Otherwise it is refused.
- **`required_baseline` is byte-identical** after a fallback (canonical BSON or JSON, compared
  before and after the compare-and-set).
- A safe target meets both rules by construction (above). The check is still enforced
  explicitly, so a future change to safe-target building cannot bypass it.
- Tested in CT-30.

#### 4.4 Permanent-obligation warning

- A new conditional required stage or field is a permanent obligation. It is listed with its
  applicability: "Applies to: LLP, LP, and any entity whose legal form is not verified".
- **Broadening** a required obligation's applicability is a permanent tightening. It is listed
  under a proposed new `PermanentObligationChange.APPLICABILITY_BROADENED`.
- `acknowledged_permanent_obligations` must still equal the set exactly (ADR-017 §1.3).

### 5. Editor UX (PR-10)

The C-5 placeholder becomes functional within scope:
- **Controls.** "Entity applicability" offers **All entities** (default) or **Only these legal
  forms**. The five selectable forms come from the backend enum, and the parity test is kept
  from C-5. `OTHER` is not offered. Its absence is explained: "Entities with another or
  unverified legal form always receive every condition."
- **Fixed explanatory text:** "Conditions only add steps for matching entities. They never remove
  or relax a step that applies to everyone. If an entity's legal form is unknown, every
  conditional step applies."
- **Ratchet-locked controls.** Controls that RR-8 would refuse are shown disabled, with the rule
  named. Examples: narrowing a published required obligation, making an ALL obligation
  conditional. The backend remains authoritative.
- **Onboarding anchors (B2).** For a stage placed before "Registry verification", the
  applicability control is disabled, with the explanation: "Conditions need the registry
  result, so they are available only from Registry verification onwards."
- **Run view.** Shows the basis, for example "Registry-bound (Mock): LLP", or "Not verified: all
  conditional steps apply". It also shows the conflict notice and the escalation action (§3.5,
  F6).
- **No UBO, ownership, screening, policy or risk options** are shown. The "Coming soon" label is
  removed only for legal-form applicability.
- **Accessibility.** Existing styling tokens and `aria-disabled` descriptions, as in C-5.
- **Director comparison.** Shows each applicability change, and the warning set (§4.4).

### 6. Send check and the dispatch fence

- **The send check enforces the resolved copy.** `send_hold_code` enforces the run's copy
  resolved with the **effective basis** (§3.3). It also runs the read-only conflict recompute of
  §3.5 F5, which does not depend on the post-write hook. A non-applicable conditional stage is
  absent from the run, so it neither holds nor is bypassed. An applicable one blocks the send exactly like any added
  required stage (`stage_blocks_send`).
- **D1 under version `V`** evaluates the hold on the run's copy resolved for `V`, with the
  effective basis. A publication that adds a conditional stage triggers ADR-017 §3.7 re-confirmation only
  for cases where it applies after resolution. For an onboarding case not yet frozen, that is
  every open case (`UNVERIFIED`).
- **New hold, onboarding only:** `WORKFLOW_APPLICABILITY_BASIS_CONFLICT` (§3.5 F6). It is
  treated like `WORKFLOW_STAGE_INCOMPLETE`: it returns the case to target confirmation, and
  never ends automation. Integration points that must handle it (line numbers approximate):
  - **Zero-touch.** `services/zero_touch_orchestration.py` `_FENCE_RECONFIRMATION_CODES`
    (around line 161) must include it. Otherwise the refusal falls through to
    `_technical_failure` (around line 4006) instead of returning to target confirmation.
  - **CLM.** The refusal handler in `services/clm_orchestration.py` (around line 786) already
    passes `exc.code` through, so **no code change is needed there**. CT-37 still covers it.
  - **Fence (option (a)).** The fence's `_on_hold` callback is **not** fired for the conflict
    hold; it stays limited to `HOLD_INCOMPLETE`.
    - The refusal alone holds the send, and the conflict hold never supersedes a confirmation.
    - After escalation, the added stages that are not yet confirmed produce
      `WORKFLOW_STAGE_INCOMPLETE`. That supersedes the confirmation through the existing path
      (ADR-017 §3.7).
- **Unchanged:** D3, D4–D6, leases, the durable write rule, no-replay recovery and D-136 E1–E4.
- **Failure.** If resolution fails (an unreadable basis, an unknown enum value in stored content),
  the check returns `WORKFLOW_STAGE_CHECK_UNAVAILABLE`, which fails closed.

### 7. Simulation

- The synthetic scenario catalogue (`GET /api/workflows/simulation-scenarios`) gains one
  scenario per selectable legal form, plus **"Legal form not verified"** and **"Other legal
  form"**.
- Each outcome's `steps` now differs by scenario, according to §3.3.
- Simulation stays synthetic: no case read, no provider call, no write.
- `SimulationScenario.legal_form` changes from a free label to
  `ConditionalLegalForm | "UNVERIFIED" | "OTHER"` (contract note, §10).

### 8. Schema and persistence impact

| Store | Change | Numbered schema change? |
|---|---|---|
| Case snapshot document | **None.** The legal form and binding are read from existing fields. The escalation event is one `WorkflowEvent` in the existing `events` list: a new `code` string, with `stage = case.state` and an existing `EventOutcome`. No new field, and no new `WorkflowState` or `EventOutcome` value (forbidden) | **No.** Stays 21; 22 stays reserved for D-117 (targeted design review: no escalation needed) |
| Workflow definition `payload` (`versions[].stages`, `draft_stages`) | Optional `applies_to` on stages and fields, excluded when `None` | No numbered schema. It is a payload shape change (§9) |
| Top-level `required_baseline` | `FieldSignature.applicability` typed; `BaselineStage.applicability` added | Contract change (§10) |
| `workflow_runs` payload | Optional `applicability_basis` (with `frozen`, `binding_ref`), `basis_conflict` (with `escalation_reason`) and `ever_touched`; `applies_to` on copied stages | No numbered schema. It is a payload shape change (§9). The basis lives here, **not** in the case snapshot |
| Cold `workflow_versions` and `workflow_proposals` | The same optional field inside records | None (content is insert-only and unchanged for existing records) |

If implementation finds that the case snapshot must change after all, it stops. The number is
allocated by the integrator with the D-117 owner. This ADR picks no number.

Byte budget: at most 5 short enum strings per stage or field. This is negligible against the
1 MiB version budget, and the version budget checks are unchanged. Runs add the bounded
`ever_touched` set, plus the basis and conflict records (each under 1 KiB), to the run document's
size check.

### 9. Migration and rollout

- **Existing content = ALL.** No data migration. Existing documents decode unchanged. Existing
  hashes are unchanged (§2.2).
- **Rollback hazard.** `WorkflowStage`, `WorkflowField`, `WorkflowRun`, `FieldSignature` and
  `BaselineStage` use `extra="forbid"`. After the first conditional version, baseline entry or
  run is written, pre-ADR-018 code (including the P2-1 reader) cannot decode that definition or
  run (§2.3). It then returns `WORKFLOW_UNAVAILABLE`, and the send check and fence refuse.
  That is safe, but cases stall.
- **Proposed rollout:**
  1. PR-9 ships the evaluator, the ratchet, the model fields and the API, with conditional
     authoring **refused** until a separate enablement step (`WORKFLOW_PROPOSAL_INVALID`,
     "conditional content not enabled").
  2. PR-10 ships the UI and lifts the refusal.

  So a rollback from PR-10 to PR-9 is always decodable. A rollback below PR-9 is safe only
  before any conditional content is published. After that it is a fail-closed stop that needs a
  forward fix. The owner chose this rollout (B7).

### 10. API and contract changes (proposed contract-change note)

To be recorded in `WORKFLOW_GOVERNANCE_API.md` §6 and approved by the integrator with PR-9:
1. `WorkflowStage.applies_to` and `WorkflowField.applies_to` (optional, canonical, ALL when
   absent), in the backend models and `workflowGovernanceTypes.ts`. They appear in proposal
   create and update requests, proposal and version views, and run views.
2. `ConditionalLegalForm`, the selectable subset of `RegistryLegalForm`, with parity tests.
3. `FieldSignature.applicability` typed (§2.3), and `BaselineStage.applicability` added.
4. `PermanentObligationChange.APPLICABILITY_BROADENED`.
5. `RatchetRule.RR_8` comment changed from "inert" to active. Issues carry RR-8a/b/c in
   `ValidationIssue.message`. No new error code.
6. `SimulationScenario.legal_form` typed (§7). The catalogue gains the new scenarios.
7. Run view: `applicability_basis` (status, legal form, reason, environment, frozen) and
   `basis_conflict`; never raw source values.
8a. `ApplicabilityBasis`, `BindingRef` and `BasisConflict` (with `escalation_reason`) models, and
    `WorkflowRun.ever_touched`. The new reasons are
    `CONFLICTING_CLASSIFICATION`, `AMBIGUOUS_BINDING` and `TOO_LATE_TO_NARROW`.
8b. The hold code `WORKFLOW_APPLICABILITY_BASIS_CONFLICT`.
8c. The escalation route `POST /api/clm/cases/{id}/workflow/applicability-escalation`
    (filler role, `ACTOR_ONLY`, reauthorized inside the case lock, reason 10–240). It is the
    only new route.
8d. The structure issue "conditional before registry verification" (§2.1).
8. Fixtures regenerated with `scripts/generate_workflow_governance_fixtures.py`, with
   contract-test updates.

One new route (8c). It is added to `ROUTE_POLICIES` and the RBAC inventory. `ROLE_CAPABILITIES`
is unchanged.

### 11. Security and privacy

- **No new PII or provider data.** Only the bounded enum value, a status, a reason code and the
  source environment are stored. `party_type` text is never copied into a run, a definition or
  simulation output.
- The legal form is read in the backend from the case record, under the case lock already taken
  by `start_run`. Clients cannot supply or override it.
- RBAC and team scope are unchanged. An inaccessible case is still a safe `404`. The AI
  Assistant gets no new tool or data, and cannot author, decide or influence applicability.
- No dormant provider is composed, and no Live claim is made.

## Verification (CT additions; mocks and disposable MongoDB only)

| ID | Covers |
|---|---|
| CT-21 | Model canonicalisation (sorted, no duplicates, no full set, field ⊆ stage, `OTHER` refused). Golden hashes of existing proposals, versions and fixtures unchanged |
| CT-22 | The RR-8a/b/c matrix at validate, submit and approve, against the active version and the baseline. An interleaved broader publication. Deactivate then reactivate. Baseline union. Safe targets keep the broadest applicability, widen stage applicability where needed, or raise `SafeTargetError` |
| CT-23 | Evaluation for every legal form, `OTHER`, no entity, no binding (including the government register and direct-provider paths), a `uen_route` conflict, read failure, and `NEW_CASE`. Both adapter paths: a Sandbox `entityType` and a Marketplace Mock `companyType` fixture (synthetic), including the OPQ-shaped `companyType` that decodes to `OTHER` and gives `UNVERIFIED`. The single-classifier source check (§3.1). An emptied stage is dropped, and a stage authored with zero fields is kept. Determinism (the same inputs give the same copy) |
| CT-24 | Freezing: a later case change (identity correction, re-acquisition) never changes the run. Rebase reapplies the effective basis (`UNVERIFIED` before the freeze, frozen after, `UNVERIFIED` permanently after an escalation), and never freezes. A rebase after an escalation, and after `TOO_LATE_TO_NARROW`, drops no stage the run held. `active_onboarding_stages` is the only consumer of unresolved stages. `start_run`, `_loaded_answers`, `_onboarding_run` and `_rebased` use the resolved copy: no prefill or kept answer for a non-applicable stage or field. Confirmations are kept only for unchanged resolved stages |
| CT-25 | Send check and fence: a non-applicable stage neither holds nor is bypassed. An applicable one holds. D1/D3 against the publication of an applicable versus a non-applicable conditional stage. Re-confirmation only when applicable. Resolution failure gives `WORKFLOW_STAGE_CHECK_UNAVAILABLE`. An unescalated `basis_conflict` holds the send. Escalation releases the hold only once every condition's stage is confirmed. A recording mock GoldTier shows exact call counts |
| CT-26 | Simulation: per-scenario step sets differ as specified. No case read, provider call or write |
| CT-27 | Permanent-obligation set includes new conditional obligations and `APPLICABILITY_BROADENED`. An inexact acknowledgement is refused |
| CT-28 | Rollout: conditional authoring refused before enablement. Pre-ADR-018 code against conditional content fails closed with 0 provider calls |
| CT-29 | Privacy: runs, definitions, simulation and logs hold no `party_type` text or PII. Frontend option parity with `ConditionalLegalForm`. UI disabled-state and accessibility tests (Vitest, Playwright) |
| CT-30 | Emergency fallback (§4.3a): it is refused when its permanent-obligation set is not empty (each of `NEW_REQUIRED_STAGE`, `NEW_REQUIRED_FIELD`, `TIGHTENED`, `APPLICABILITY_BROADENED`, and a new conditional obligation). An accepted fallback leaves `required_baseline` byte-identical. The safe target never broadens beyond the baseline (the union proof as a property test) |
| CT-31 | Mandatory (B10): a frozen snapshot of the `classify_registry_legal_form` table. Any change fails until it is reviewed. Unrecognised and conflicting inputs give `UNVERIFIED` (A4) |
| CT-32 | Freeze-once: the first committed binding freezes. Freeze and an answer write race under the case lock. A second binding never changes a frozen basis. Insert-only create and the `frozen != true` filter refuse a second freeze across two processes. A lost freeze write leaves `UNVERIFIED`. Memory and Mongo at parity |
| CT-33 | Too late to narrow: each touched kind (an answer from each source, a confirmation, sent, a dispatch confirmation, a dispatch claim) gives `TOO_LATE_TO_NARROW`, and nothing is removed. Untouched excluded items are dropped. The late-freeze eligibility rule (F4) gives `AMBIGUOUS_BINDING` otherwise |
| CT-34 | Conflict: a different form, status or identity after a `REGISTRY_BOUND` freeze writes `basis_conflict`, keeps the frozen copy and holds the send. An `UNVERIFIED`-frozen run raises no conflict or hold. **Hook loss:** with the conflict hook suppressed, `send_hold_code` and D1 still hold from the read-only recompute. The escalation is add-only, audited (reason 10–240) and reauthorized in the lock. The effective basis stays `UNVERIFIED` across later publications and rebases. No path narrows after the freeze. The case event uses a new `code` string only; no `WorkflowState` or `EventOutcome` value is added |
| CT-35 | Anchor eligibility: conditional content anchored before `ACRA_REGISTRY` (or with no anchor) is refused at validate, submit and approve, including a move to an earlier anchor. Locked stages can never be conditional (RR-9). Resolution never removes or reorders `ONBOARDING_LOCKED_STAGES` |
| CT-36 | End to end (Mock): a synthetic LLP Marketplace Mock binding through `_acquire_required_registry_evidence` freezes `REGISTRY_BOUND (Mock): LLP`, and the LLP-only stage holds the send until it is confirmed. A synthetic `COMPANY` case gets no LLP stage and is not held. Recording mock GoldTier call counts |
| CT-37 | Hold routing: `WORKFLOW_APPLICABILITY_BASIS_CONFLICT` on the zero-touch send returns the case to target confirmation (via `_FENCE_RECONFIRMATION_CODES`, never `_technical_failure`) with **0 GoldTier calls**. The CLM handler passes the code through unchanged. Option (a): `_on_hold` is **not** fired for the conflict hold, and no confirmation is superseded by it. After escalation, the unconfirmed added stages give `WORKFLOW_STAGE_INCOMPLETE`, which supersedes through the existing path. The shared recompute returns `WORKFLOW_STAGE_CHECK_UNAVAILABLE` on a read failure, and is deterministic |
| CT-38 | Event-count token: appending the escalation event changes `len(case.events)`. A stale `expected_case_event_count`, document-processing request or target-confirmation `evidence_version` is refused or retried, never accepted |
| CT-39 | Emergency fallback on a frozen run: the fallback publication rebases the open case with its effective basis. It removes no stage the run held and leaves the frozen basis and `ever_touched` unchanged |
| CT-40 | Touched from history: an answer recorded then cleared, with a lost `TOO_LATE` freeze, still gives `TOO_LATE_TO_NARROW` on retry. The F4 tests run on every freeze. The hook takes no gate or definition lock (lock-order test) |

The D-136 E1–E4, P2-0 fence, nonce-writer, CT-0 to CT-20, RBAC, AI Assistant and
identity-provenance suites must stay green.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Re-evaluate applicability on every read or send | Rejected. It violates D-10 (frozen), and a case could gain or lose steps silently |
| Conditions that make a step optional or remove it for some forms | Rejected. It violates add-only (CA-1) |
| Per-form `required` flags on one field | Rejected for now. It is more complex to ratchet, and is covered by presence-only applicability |
| Treat unverified entities as matching no condition | Rejected. It fails open (CA-4) |
| A new classification for listed companies or financial institutions | Out of scope. It needs a separate decision (D-10) |
| Store applicability outside the payload (a top-level map) | Rejected. It splits the content hash from what is published, and complicates run copies and the cold archive |
| `OTHER` as a selectable condition | Rejected. It is redundant under fail-closed (B5) |

## Consequences

- **Gains:**
  - HR can add form-specific obligations under the same governance as other content.
  - The placeholder becomes real.
  - RR-8 is enforced.
- **Accepted costs:**
  - A mistaken conditional obligation is permanent and can only broaden.
  - Unverified entities carry every conditional obligation.
  - A conditional onboarding stage that an RM touches before registry binding stays for that
    case (F3).
  - An applicability conflict holds the send until a person escalates (F6).
  - A wrong but known legal form drops conditional obligations for the true form (§3.1).
  - A rollback below PR-9 after use stops affected workflows (fail closed).
- **Unchanged:** RBAC, the dispatch fence, ledgers, D-136, the mandatory engine order, case
  schema 21, ACRA identity provenance, and policy values (which change only through policy
  proposals).

## Revisit conditions

- A sponsor or owner decision on listed-company or financial-institution classification.
- A change to `RegistryLegalForm` or its source mapping. A new enum value is not selectable
  until reviewed, and is treated as unverified until then.
- Another jurisdiction's registry.
- A request for non-legal-form conditions or for conditional optionality.
- A change to onboarding run creation, rebasing or the registry binding event (§3.5).
- A binding for the government register path, which would let `GOVERNMENT` conditions narrow.
- A fix to the `companyType` decoder defect (§3.1).

## Owner decisions (2026-11-18, given to the integrator)

1. **B1, decided (revised):** onboarding starts `UNVERIFIED`. The basis freezes once, at the first eligible authoritative registry binding. It stays `UNVERIFIED` if the binding is missing, ambiguous, conflicting or too late (§3.5).
2. **B2, decided (revised):** onboarding supports conditional stages only at `ACRA_REGISTRY` or later anchors. Earlier anchors are refused (§2.1).
3. **B3, decided:** a rebase reapplies the current (frozen) basis and never re-evaluates.
4. **B4, decided:** a Mock ACRA binding counts, labelled Mock.
5. **B5, decided:** `OTHER` is unverified and not selectable.
6. **B6, decided:** a non-onboarding version keeps at least one ALL stage with an ALL field.
7. **B7, decided:** fail-closed rollback with the PR-9 enablement gate.
8. **B8, decided (earlier, 2026-11-18):** an emergency fallback's permanent-obligation set is empty, and the baseline stays byte-identical (§4.3a).
9. **B9, decided:** optional ALL → conditional required is refused.
10. **B10, decided:** the CT-31 gate on the mapping table. A4: the canonical mapping, failing closed.
11. **B11, decided:** the status names are `REGISTRY_BOUND` / `UNVERIFIED`, always shown with the environment.

**For the design review (within B1/B2, not new owner decisions):**
- the escalation route and the two case event `code` strings (targeted review R2: no new case schema)
- optional run `write_nonce` hardening (F2)

## Related decisions

D-123, D-135, D-136; workflow designer programme D-10 (not DECISION_LOG D-010); C-5 (P2-2
placeholder); ADR-014, ADR-016, ADR-017 (including its §4 owner clarification of 2026-11-18).
