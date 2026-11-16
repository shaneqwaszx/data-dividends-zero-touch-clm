# ADR-014 — Director-managed workflows as an additive owner

## Status

Accepted by owner direction (D-123). `USER_AUTHORIZED_POC`; not sponsor-confirmed.
Amended in part by D-136 (2026-11-15): every send path enforces stored required stages,
including when the manager is switched off.

## Date

2026-11-05

## Context

The owner wants the Director to change a pipeline, or create a pipeline for another use
case, without code changes, in the manner of a Camunda process. The six automation
stages and the path to GoldTier are hard-coded in `ZeroTouchOrchestrator`, and the owner
requires that current logic is not rewritten. Camunda has no runtime role (ARCHITECTURE).

## Decision

`WorkflowManagementService` owns workflow definitions, versions and case field
collection in new files and two new Mongo collections.

- A workflow's name is its use case. Onboarding has exactly one workflow; its
  eleven existing stages are locked and added stages are displayed after a chosen stage.
- A new use case gets a separate workflow, shown as a tab once active. The RM or
  onboarder runs it for an onboarded company, or opens a workflow-only case that holds
  its own company details and never becomes an onboarding case.
  Onboarding cases never move onto one.
- A stage is a name and the fields it collects. The RM or onboarder fills and confirms
  it; the Director cannot. Stage completion is a person's confirmation, so no new
  business rule is evaluated.
- An open onboarding case follows the latest active version, so a new stage reaches
  it, and a changed stage must be confirmed again. A sent case stays as it was. A run
  freezes its version when started.
- It is on by default and inert until a Director activates a stage. Setting
  `WORKFLOW_MANAGER_ENABLED` and `VITE_WORKFLOW_MANAGER_ENABLED` to false removes the
  workflow routes, screens, upload suggestions and workflow-data deletion. It does not
  remove the send check (D-136 E4): stored activated stages are still enforced, and an
  unreadable store refuses any send that has not started; an already-started legacy
  Submit continues under D-136 E3. With the flag off, every stored required stage
  that is not yet confirmed keeps blocking the send, and it cannot be filled, confirmed
  or changed. A required stage already confirmed does not block. To proceed, switch it
  back on and restart, then complete and confirm the outstanding stages. An unconfirmed
  required stage is never bypassed.

Existing code gains only optional hooks:
every send path asks whether required added stages are confirmed and refuses the send
otherwise, failing closed (D-136 E1-E3). These are the zero-touch
`confirm_target_dispatch` and the legacy target-confirmation and Submit routes.
Document processing offers each upload for
suggestions, which can never fail the upload; case deletion removes collected answers
first. The rail merges added stages at display time, outside
`summary.processing_pipeline`.

## Alternatives considered

- Extend `PolicyManagementService`: it owns bounded rule values, and the owner requires
  no change to existing owners. ADR-012 set the precedent of a separate aggregate.
- Drive the orchestrator from definitions: the real Camunda-style result, but it rewrites
  the highest-risk owner, which the owner excluded.
- Hold a case at the stage's own position: needs new statuses and exception types across
  orchestration and persistence. Final review & send is the zero-touch send point.
- Advisory stages with no send check: rejected by the owner.

## Consequences

- Existing onboarding stages still change only through code. Definitions control added
  stages and new workflows.
- A case keeps moving past an unconfirmed added stage and stops at Final review & send.
- The older `/api/clm/cases/{case_id}/target-confirmation` and `/submit` routes, which
  predate this work, now pass the same send check (D-136 E1-E3). It runs inside the CLM
  case lock after reauthorization and the D-124 check. Submit continues only a send
  whose first GoldTier write is already in the persisted ledger, so recovery is never
  replayed or stranded. Confirmation has no such exception.
- Still open, accepted for the FYP staging POC only (D-136 E6-E7):
  - R1: a publish can add a required stage after the check and before the write.
  - R2: a case sent through the legacy routes is not counted as sent for workflow
    versions.
  - N3: in Mongo mode the backend needs the workflow store reachable at startup.
- Removing or skipping workflow stages is prohibited by owner policy (D-136 E5,
  D-135: design approved 2026-11-15, ADR-017 Proposed, not implemented): HR proposes, exactly one Director approves or rejects, and stages
  are never removed or skipped. The current code does not yet enforce this. One
  Director edits and activates workflows with no second approver (D-123 W1), and
  nothing technically stops a version that drops an added stage, which would remove it
  from open cases. That is a known implementation gap, not permission to remove
  stages. Until the governance fix is implemented, no workflow publication that removes
  an existing stage is authorised. It is separate from D-064 policy four-eyes.
- Collected answers can include KYC/PII. They stay case-scoped, are never logged and are
  deleted with the case. They are not sent to GoldTier, ownership or reconciliation.
- Autofill matches `label: value` lines in native text, DOCX and TXT, during upload only.
  Scanned documents and images give no suggestions, and earlier uploads are not re-read.
- Two Mongo guarantees remain single-process, as for the rest of the POC.
