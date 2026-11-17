# ADR-018: Conditional, entity-specific workflow stages and fields (P2-3)

## Status

**Proposed. Not accepted.** Drafted 2026-11-17 for separate owner approval, within the scope the
owner fixed in advance (programme decision D-10, 2026-11-17).

This ADR is a design record only:
- **Nothing in it is implemented.** Current behaviour is unchanged.
- It is not sponsor-confirmed. Authority: `USER_AUTHORIZED_POC`.
- Implementation (PR-9 backend, PR-10 UI) needs this ADR's acceptance, then its own QGs.

Decision record: **D-XXX (to be allocated by the integrator)** in [DECISION_LOG](DECISION_LOG.md).

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
- Fixed scope (D-10): add-only; deterministic on the backend `RegistryLegalForm` only; evaluated
  once at run creation and frozen; fail closed; RR-8; no reduced UBO or compliance obligations;
  governed like all other content.

## Decision

### 1. Scope, restated as rules

| ID | Rule |
|---|---|
| CA-1 | **Add-only.** A condition only ever **adds** obligations for matching entities. Nothing conditional removes, relaxes, skips or replaces an unconditional obligation, a code-owned stage or the engine order |
| CA-2 | **Deterministic on `RegistryLegalForm` only.** Only the existing enum values are used. No new classification is introduced. There are no free-text, numeric, ownership, risk, country, policy or AI conditions |
| CA-3 | **Evaluated once, frozen.** Applicability is resolved when a run is created. The basis is stored on the run and never re-evaluated (see §3.4 for rebasing) |
| CA-4 | **Fail closed.** If the classification is unknown, missing, unverified or `OTHER`, **every** conditional obligation applies |
| CA-5 | **RR-8.** Applicability is never narrowed. An unconditional obligation stays unconditional. The baseline keeps the broadest applicability ever published |
| CA-6 | **No editor-controlled reduction of UBO or compliance obligations.** UBO thresholds, ownership, screening and policy rules stay outside the editor. D-136 E1–E4, the dispatch fence, ledgers and the mandatory engine order are unaffected |
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
  `COMPANY, BUSINESS_PARTNERSHIP, LLP, LP, GOVERNMENT`. **`OTHER` cannot be selected**, because
  an `OTHER` entity is treated as unverified and already receives every conditional obligation
  (OQ-4).
- **Canonical form.** Duplicates are refused. Values are sorted ascending by enum value. A model
  validator normalises the order, so equal sets always serialise the same way. A tuple naming
  every selectable form is refused (`WORKFLOW_PROPOSAL_INVALID`, "use All entities"), so ALL has
  one representation only.
- **Stage and field.** A stage's `applies_to` governs the whole stage. A field's `applies_to`
  applies within its stage. A field set must be a subset of its stage set, otherwise it is
  refused. The **effective applicability** of a field is the intersection of the two, with ALL
  as the identity.
- **Not allowed:** `applies_to` on code-owned locked stages. They are not `WorkflowStage`
  records, and RR-9 is unchanged. Anchors (`after_node_id`) are unchanged.
- **Non-onboarding minimum.** A non-onboarding version must keep at least one stage that applies
  to ALL and holds at least one ALL field (an extension of `WORKFLOW_PROPOSAL_EMPTY`). This
  ensures no run is created with zero stages (OQ-5).

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

### 3. Evaluation at run creation

#### 3.1 Source of the legal form

The legal form comes only from the backend case record. It never comes from a request, a
document, AI output or the frontend:
- `case.entity.party_type`, classified by the existing `classify_registry_legal_form`. No second
  classifier is added. CT-23 checks that the mapping table is the only one used.

#### 3.2 What counts as verified

A legal form `F` is **verified** only when all of these hold at evaluation time:
1. `case.entity` is present, and `case.entity.source.source_system == ACRA`.
2. `case.registry_evidence_binding` is present. Its model validator already guarantees a
   `COMPLETE` acquisition, `entity == acquisition.entity_profile`, a matching UEN and per-operation
   provenance.
3. `classify_registry_legal_form(case.entity.party_type)` is not `OTHER`.

Anything else (no case, no entity, no binding, `OTHER`, a decode or read failure, a workflow-only
`WorkflowCompany` case) gives the basis **`UNVERIFIED`**. The source environment (Mock or
Sandbox) is recorded but not used to decide (OQ-3).

#### 3.3 Resolution and freezing

At creation, the run's stage copy is computed from the version with the basis `B`:
- **Stage.** A stage is kept if it is ALL, if `B` is `UNVERIFIED`, or if `B` is in its
  `applies_to`.
- **Field.** Within a kept stage, a field is kept by the same test on its own `applies_to`.
- **Empty stage.** A stage left with no fields is dropped from the run.
- **`applies_to` is kept** on the copied stages and fields, so the run shows why each one
  applies.

`WorkflowRun` gains `applicability_basis` (optional, excluded when `None`):

```python
class ApplicabilityBasis(_Frozen):
    legal_form: ConditionalLegalForm | None   # None when UNVERIFIED
    status: Literal["VERIFIED", "UNVERIFIED"]
    reason: Literal["REGISTRY_BINDING", "NO_ENTITY", "NO_BINDING", "OTHER_FORM",
                    "NO_CASE_RECORD", "READ_FAILED"]
    source_environment: SourceEnvironment | None
    evaluated_at: datetime
    evaluated_from_version: int
```

- A run without a basis (every run created before this ADR) is treated as `UNVERIFIED`. Its
  stages were copied from unconditional content, so this changes nothing.
- The basis is **never recomputed**. Later changes to the case record do not change the run:
  identity corrections, re-acquisition, a different `party_type`.
- **Determinism.** The same version and the same basis always give the same stage copy. The
  evaluator is a pure function, with no clock, I/O or randomness in the selection.

#### 3.4 Onboarding runs and rebasing

- **Non-onboarding `EXISTING_CASE` runs.** `start_run` requires a case that has finished
  onboarding, so the binding normally exists and the evaluation is meaningful.
- **Non-onboarding `NEW_CASE` runs.** The basis is `UNVERIFIED`, so everything applies.
- **Onboarding runs.** These are created from `case.created_at`, before ACRA verification, and
  are materialised lazily on read. To stay deterministic and literal to D-10, the **proposed
  default** is that every onboarding run's basis is `UNVERIFIED (NO_BINDING)`, whenever it is
  first materialised. All conditional onboarding obligations then apply to every onboarding case.
  This is safe, but it means conditional stages have no differentiating effect on onboarding.
  The owner decides whether to accept that or choose an alternative (**OQ-1**).
- **Rebasing.** When an open onboarding case rebases to a newer version (`_rebased`), the
  **frozen basis is reapplied** to the new version's stages. The classification is never
  re-evaluated. Confirmations are kept only for a stage whose resolved copy is unchanged, as
  today. Answers are kept by the existing rule. This reading of "never re-evaluated" needs owner
  confirmation (**OQ-2**).

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
applicability for every baseline obligation, even when `base` held it narrower or unconditional
content held it as a set. A safe target never narrows.

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
- **No UBO, ownership, screening, policy or risk options** are shown. The "Coming soon" label is
  removed only for legal-form applicability.
- **Accessibility.** Existing styling tokens and `aria-disabled` descriptions, as in C-5.
- **Director comparison.** Shows each applicability change, and the warning set (§4.4).

### 6. Send check and the dispatch fence

- **The send check is unchanged in logic.** `send_hold_code` enforces the run's **frozen,
  resolved** stage copy. A non-applicable conditional stage is absent from the run, so it
  neither holds nor is bypassed. An applicable one blocks the send exactly like any added
  required stage (`stage_blocks_send`).
- **D1 under version `V`** evaluates the hold on the run's copy resolved for `V`, with the frozen
  basis. A publication that adds a conditional stage triggers ADR-017 §3.7 re-confirmation only
  for cases where it applies after resolution. Under the OQ-1 default that is every open
  onboarding case.
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
| Case snapshot document | **None.** The legal form is read from existing fields | **No.** Stays 21; 22 stays reserved for D-117 |
| Workflow definition `payload` (`versions[].stages`, `draft_stages`) | Optional `applies_to` on stages and fields, excluded when `None` | No numbered schema. It is a payload shape change (§9) |
| Top-level `required_baseline` | `FieldSignature.applicability` typed; `BaselineStage.applicability` added | Contract change (§10) |
| `workflow_runs` payload | Optional `applicability_basis`; `applies_to` on copied stages | No numbered schema. It is a payload shape change (§9) |
| Cold `workflow_versions` and `workflow_proposals` | The same optional field inside records | None (content is insert-only and unchanged for existing records) |

If implementation finds that the case snapshot must change after all, it stops. The number is
allocated by the integrator with the D-117 owner. This ADR picks no number.

Byte budget: at most 5 short enum strings per stage or field. This is negligible against the
1 MiB version budget, and budget checks are unchanged.

### 9. Migration and rollout

- **Existing content = ALL.** No data migration. Existing documents decode unchanged. Existing
  hashes are unchanged (§2.2).
- **Rollback hazard.** `WorkflowStage`, `WorkflowField` and `WorkflowRun` use `extra="forbid"`.
  After the first conditional version or run is written, pre-ADR-018 code cannot decode that
  definition or run. It then returns `WORKFLOW_UNAVAILABLE`, and the send check and fence refuse.
  That is safe, but cases stall.
- **Proposed rollout:**
  1. PR-9 ships the evaluator, the ratchet, the model fields and the API, with conditional
     authoring **refused** until a separate enablement step (`WORKFLOW_PROPOSAL_INVALID`,
     "conditional content not enabled").
  2. PR-10 ships the UI and lifts the refusal.

  So a rollback from PR-10 to PR-9 is always decodable. A rollback below PR-9 is safe only
  before any conditional content is published. After that it is a fail-closed stop that needs a
  forward fix. Whether to require a reviewed reverse migration instead is **OQ-6**.

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
7. Run view: `applicability_basis` (status, legal form, reason; never raw source values).
8. Fixtures regenerated with `scripts/generate_workflow_governance_fixtures.py`, with
   contract-test updates.

No new routes. `ROUTE_POLICIES` and `ROLE_CAPABILITIES` are unchanged.

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
| CT-22 | The RR-8a/b/c matrix at validate, submit and approve, against the active version and the baseline. An interleaved broader publication. Deactivate then reactivate. Baseline union. Safe targets keep the broadest applicability |
| CT-23 | Evaluation for every legal form, `OTHER`, no entity, no binding, non-ACRA source, read failure, and `NEW_CASE`. A single classifier. Determinism (the same inputs give the same copy) |
| CT-24 | Freezing: a later case change (identity correction, re-acquisition) never changes the run. Rebase reapplies the frozen basis. Confirmations are kept only for unchanged resolved stages |
| CT-25 | Send check and fence: a non-applicable stage neither holds nor is bypassed. An applicable one holds. D1/D3 against the publication of an applicable versus a non-applicable conditional stage. Re-confirmation only when applicable. Resolution failure gives `WORKFLOW_STAGE_CHECK_UNAVAILABLE`. A recording mock GoldTier shows exact call counts |
| CT-26 | Simulation: per-scenario step sets differ as specified. No case read, provider call or write |
| CT-27 | Permanent-obligation set includes new conditional obligations and `APPLICABILITY_BROADENED`. An inexact acknowledgement is refused |
| CT-28 | Rollout: conditional authoring refused before enablement. Pre-ADR-018 code against conditional content fails closed with 0 provider calls |
| CT-29 | Privacy: runs, definitions, simulation and logs hold no `party_type` text or PII. Frontend option parity with `ConditionalLegalForm`. UI disabled-state and accessibility tests (Vitest, Playwright) |

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
| `OTHER` as a selectable condition | Rejected. It is redundant under fail-closed (OQ-4) |

## Consequences

- **Gains:**
  - HR can add form-specific obligations under the same governance as other content.
  - The placeholder becomes real.
  - RR-8 is enforced.
- **Accepted costs:**
  - A mistaken conditional obligation is permanent and can only broaden.
  - Unverified entities carry every conditional obligation.
  - Under the OQ-1 default, onboarding gains no differentiation.
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
- A change to onboarding run creation or rebasing (OQ-1, OQ-2).

## Open questions for the owner

- **OQ-1, onboarding runs.** Accept the default (every onboarding run is `UNVERIFIED`, so all
  conditional onboarding obligations always apply)? Or choose **(B)**: the onboarding basis is
  fixed exactly once when the registry evidence binding first exists, and is `UNVERIFIED` until
  then? (B) reinterprets "run creation", and needs a rule for identity corrections after the
  basis is fixed.
- **OQ-2, rebasing.** Confirm that reapplying the frozen basis to a newer version on rebase is
  consistent with "never re-evaluated".
- **OQ-3, evidence class.** Should a Mock-environment ACRA binding count as verified (proposed:
  yes, recorded in the basis), or only Sandbox/Live (staging would then always apply
  everything)?
- **OQ-4, `OTHER`.** Confirm that `OTHER` is unverified and not selectable. This differs from
  the C-5 placeholder, which lists "Other".
- **OQ-5, non-onboarding minimum.** Confirm the rule that a non-onboarding version keeps at least
  one ALL stage with an ALL field.
- **OQ-6, rollback.** Accept the fail-closed rollback with the enablement gate (§9), or require a
  reviewed reverse migration before enablement.

## Related decisions

D-123, D-135, D-136, D-10 (programme), C-5 (P2-2 placeholder); ADR-014, ADR-016, ADR-017.
