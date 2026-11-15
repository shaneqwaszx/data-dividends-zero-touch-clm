# ADR-016 — Read-only onboarding Workflow Designer (P1)

## Status

Proposed. Owner-authorised for local P1 implementation on 2026-11-15; not sponsor-confirmed.
Governance for any future editing stays in the provisional D-135 draft and is not implemented.

## Date

2026-11-15

## Context

The owner asked for a visual workflow designer under HR Admin › Policy & Workflow. P1 is the
read-only first phase: show the onboarding process the backend actually runs, with no editing,
moving, saving or publishing.

Current authority this view must reflect, not redefine:

- The mandatory business stages are the D-123 `ONBOARDING_LOCKED_STAGES` plus the human approval
  gate. The orchestrator owns their order (`AUTOMATION_STAGE_ORDER`); nothing in P1 changes it.
- GoldTier search and ACRA registry verification swap order by environment: staging with the
  GoldTier Sandbox identity policy runs the registry first; otherwise search runs first when a
  legal name and country are supplied (ADR-006), and a UEN-only case searches after the registry.
- Director-managed added stages (ADR-014) are enforced at every send path under D-136, also with
  the workflow manager switched off. They hold the final send; they do not pause automation.
- The policy catalogue owns rule values, ranges and enforcement classes. D-127 SLA and attention
  constants are provisional display rules in `dashboard_attention.py`.

## Decision

1. **Backend owner.** A new read-only `ExecutionPlanService` builds the plan from the authoritative
   sources above: a static domain description of the twelve stages
   (`domain/onboarding_execution_plan.py`), the onboarding service's environment order, the provider
   modes and `WorkflowManagementService.active_onboarding_stages()`.
2. **Route.** `GET /api/workflows/onboarding/execution-plan`, `ACTOR_ONLY` in `ROUTE_POLICIES`. The
   session is reauthenticated on every call; only `POLICY_MUTATE` (HR) or `POLICY_APPROVE`
   (Director) may read it, otherwise `403 EXECUTION_PLAN_FORBIDDEN`.
3. **No write on read.** `active_onboarding_stages()` reads the stored definition directly and never
   creates the baseline. It distinguishes `ACTIVE`, `NO_ACTIVE_WORKFLOW` and `UNAVAILABLE` (store
   unreadable), so an outage is never shown as "nothing enforced".
4. **Content.** The response contains only stage descriptions, rule IDs, fixed controls, provider
   lane classifications (never `LIVE`) and added-stage metadata (names, counts, flags). It contains
   no case data, PII, provider payloads or credentials. `branches_supported` is `false`; no branch
   is drawn.
5. **Rule placement (QG P2-1).** Every catalogue rule has exactly one primary binding (a stage or
   workflow-wide), where its single definition and live value are shown. A stage whose code also
   reads a rule bound elsewhere carries a *usage reference* (`policy_rule_references`: rule, primary
   stage, traced consumer, effect). The eight entity-resolution rules are bound to Risk assessment
   (catalogue category "Intelligence") and referenced by Existing-customer search
   (`_resolve_target_candidates`) and Final review & send (existing-party reuse in
   `_submit_to_goldtier`). Catalogue ownership is not runtime use: Risk assessment runs entity
   resolution only when demo candidate data is enabled (demo controls on; off by default), and
   the plan reports a `conditional_rule_usage` entry with whether it runs in this environment
   (QG r1 N1). Search and Send always read the rules. Two call sites are excluded as
   non-workflow, each with its reason: the HR provider-sandbox search route and the offline
   synthetic evaluation harness. A test scans every module under `app/` for resolver calls and
   fails on any call site not in its explicit inventory (QG r1 N2). The panel shows "Also used
   by ..." on the primary rule and a labelled usage reference elsewhere; values always come from
   the one catalogue entry. No rule, threshold, weight, demo control or execution path changed.
6. **Frontend.** A "Workflow designer" sub-tab beside "Policy rules", visible only to HR and
   Directors. The canvas uses `@xyflow/react` 12.12.0 (exact pin, approved at P1-G2), lazy-loaded
   so it stays out of the main bundle. Every node is fixed: not draggable, connectable, selectable
   for editing, deletable or reconnectable. An accessible Outline view lists the same stages.
   Policy values come from the existing policy API and query keys are user-scoped. The plan is
   fetched through the app's `authenticatedFetch` (QG P2-2): the session cookie is sent also to a
   separate backend origin, and a `401` ends the session through the auth owner, which clears every
   session-scoped query.

Unchanged: mandatory stage order, orchestrator transitions, GoldTier provider behaviour, ACRA
identity provenance and staging identity policy, D-136 enforcement, policy approval authority,
workflow publishing, case data and persistence schemas, the AI Assistant and AWS.

## Alternatives considered

- **Draw the stages from frontend constants.** Rejected: the order is environment-dependent and
  the added-stage state must come from the store, so a frontend copy would drift.
- **Reuse `GET /api/workflows` for the plan.** Rejected: its read path creates the baseline
  definition, which P1 must not do, and it does not carry the environment order.
- **Render without a canvas library (outline only).** Kept as the accessible Outline view; the
  owner approved React Flow for the visual canvas.
- **Use dagre for layout.** Not added: a single fixed column needs no layout engine.

## Consequences

- HR and Directors can see what runs, which rules apply where and how added stages hold the send.
- One more authenticated route (inventory 104 routes, 43 `ACTOR_ONLY`).
- The lazy canvas chunk is about 191 kB (63 kB gzip). The main chunk grows by about 13 kB for the
  page itself; its pre-existing size warning is unchanged and was not addressed here.
- 12.12.0 lacks upstream fix #6054. Measured: each mount creates three ResizeObservers; after
  unmount two stay attached to detached DOM until garbage collection. No error, warning or stale
  callback was observed. Upgrading is a separate, approval-gated change.

## Architecture invariants affected

Preserved: backend-authoritative RBAC and safe refusal; reauthorization per request; no direct
route-to-Mongo access; one orchestration and one workflow owner; user/session-scoped frontend
server state. Added: the execution-plan read must never initialise or mutate a workflow definition.

## Security and persistence implications

Read-only. No schema, persistence, CAS or migration change. No secrets, case data or PII are
returned. Authorization is enforced in the backend; the frontend tab visibility is convenience only.

## Migration and retirement implications

None. Removing the route and tab restores the previous behaviour. Editing (P2) and governance (P3)
need their own approvals, D-135 acceptance and a superseding or amending ADR.

## Verification

Backend `test_onboarding_execution_plan.py` (B1–B9, rule placement and traced consumers) and the
route-inventory test; frontend `WorkflowDesigner.test.tsx` (F1–F7, shared rules),
`WorkflowDesignerAuth.test.tsx` (session transport, 401, 403, cross-origin, retry) and
`ExecutionPlanDiagram.test.tsx` (read-only canvas and mount/unmount cleanup); Playwright
`workflow-designer.e2e.ts`; existing C1/C2 and D-136 suites as regression; independent Quality
Gate on the frozen candidate and a delta review of the P2 remediation.

## Revisit conditions

A change to the mandatory stages or their order, conditional branching in the backend, approval of
P2 editing or D-135 governance, or a React Flow version change.

## Related contracts and sponsor questions

ADR-006, ADR-014, D-123, D-127, D-135 (provisional), D-136.
