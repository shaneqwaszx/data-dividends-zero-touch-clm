# ADR-014 — Director-managed workflows as an additive owner

## Status

Accepted by owner direction (D-123). `USER_AUTHORIZED_POC`; not sponsor-confirmed.

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
  `WORKFLOW_MANAGER_ENABLED` and `VITE_WORKFLOW_MANAGER_ENABLED` to false removes it.

Existing code gains only optional hooks:
`confirm_target_dispatch` asks whether required added stages are confirmed and refuses
the send otherwise, failing closed; document processing offers each upload for
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
  predate this work, do not pass the send check. It holds for the zero-touch send only.
- One Director can add a stage that blocks an RM's send with no second approver. This
  is a deliberate POC choice, separate from D-064 policy four-eyes.
- Collected answers can include KYC/PII. They stay case-scoped, are never logged and are
  deleted with the case. They are not sent to GoldTier, ownership or reconciliation.
- Autofill matches `label: value` lines in native text, DOCX and TXT, during upload only.
  Scanned documents and images give no suggestions, and earlier uploads are not re-read.
- Two Mongo guarantees remain single-process, as for the rest of the POC.
