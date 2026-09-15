# Development Workflow

This document is the canonical lifecycle and change-verification guide. `AGENTS.md`
sets constitutional rules; `docs/development/BRANCH_MERGE_PROTOCOL.md` supplies detailed
human Git integration procedure; repository skills supply specialized procedures.

## Lifecycle

```text
requirement or sponsor input
  -> planner and authority reconciliation
  -> bounded phase/change class
  -> synchronized feature branch
  -> implementation and focused verification
  -> broad affected verification
  -> independent quality gate
  -> bounded remediation
  -> independent re-quality gate
  -> latest-main integration when authorized
  -> affected regression and physical evidence where relevant
  -> pre-PR check
  -> human-approved push/PR
  -> CI
  -> human merge
  -> project-state/architecture/context refresh
```

No step grants authority for the next one. In particular, implementation does not
perform its own independent gate, a gate does not fix findings, and an agent does not
merge to main.

## Responsibilities

| Role | Owns | Must not do |
|---|---|---|
| PLANNER | authority read-set, goals, acceptance, non-goals, exact files, risks, checks | invent sponsor rules or implement before plan |
| IMPLEMENTER | smallest assigned delta and meaningful tests | broaden phase, self-approve, push/merge without instruction |
| QUALITY GATE | independent contract/test/architecture/security/adversarial evidence and verdict | remediate reviewed work |
| REMEDIATION | only gate findings and their regressions | reinterpret the gate or add unrelated features |
| INTEGRATION | latest-main intent reconciliation and complete affected regression | rebase shared history, blindly choose conflict sides, merge PR |
| OWNER | sponsor/product decisions, risk acceptance, external account/secrets/settings, PR approval/merge | delegate irreversible authority implicitly |

One person/agent may perform multiple roles only in distinct assigned runs. Independent
QG and re-QG must remain independent from implementation/remediation.

## Task start

1. Read in order: `AGENTS.md`, `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`, this
   workflow, relevant contracts/decisions/sponsor questions, the relevant skill, then
   current source and tests.
2. Run `python scripts/dev_context.py` and the Git baseline commands in `AGENTS.md`.
3. Record branch, clean tracked state, `BASE_SHA`, HEAD and `origin/main`.
4. Classify every affected change class below; use all applicable rows.
5. Identify canonical owners, hotspots, contract/security/persistence effects, required
   authority, explicit non-goals and stop conditions.
6. Write or select a bounded planner handoff before medium/high-risk implementation.

Historical phase reports are consulted only for a question that current source,
contracts/decisions, architecture and state do not answer.

## Change classes and required verification

Legend: **R** required when the class applies; **A** required when that surface is
affected; **—** not required solely because of this class. Planner/gate may add checks.

| Check | DOCS_ONLY | FRONTEND_UI | FRONTEND_STATE_CACHE | BACKEND_DOMAIN | BACKEND_API | AUTH_RBAC_SECURITY | PERSISTENCE | EXTERNAL_PROVIDER | ARCHITECTURE_REFACTOR | CI_TOOLING |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| focused tests/check | R | R | R | R | R | R | R | R | R | R |
| full backend pytest | — | — | — | R | R | R | R | A | R | A |
| Ruff | A | — | — | R | R | R | R | R | R | R |
| mypy backend | — | — | — | R | R | R | R | A | R | A |
| focused frontend test | — | R | R | — | A | A | — | A | A | A |
| full frontend tests | — | R | R | — | A | A | — | A | R | A |
| frontend typecheck | — | R | R | — | A | A | — | A | R | A |
| frontend build | — | R | R | — | A | A | — | A | R | A |
| contract tests | A | — | — | A | R | R | A | R | R | A |
| POC lifecycle/regression | — | — | A | A | A | R | R | R | R | A |
| secret scanner/tests | A | — | — | A | A | R | R | R | R | R |
| physical Mongo | — | — | — | — | — | A | R | A | A | A |
| integration-security review | — | — | — | — | A | R | A | R | A | A |
| independent QG | A | A | R | R | R | R | R | R | R | R |
| `check_project_state`/`check_architecture` | R | A | A | A | A | A | A | R | R | R |
| `pre_pr_check.py` | R | R | R | R | R | R | R | R | R | R |

### Change class definitions

- `DOCS_ONLY`: tracked prose/templates/indexes with no executable/configuration change.
- `FRONTEND_UI`: rendering, accessibility, layout, or view behavior without shared
  server-state/cache semantics.
- `FRONTEND_STATE_CACHE`: query keys, cached state, session lifecycle, cancellation,
  invalidation, mutation or stale-response behavior.
- `BACKEND_DOMAIN`: domain/service rules, transitions, calculations or evidence models.
- `BACKEND_API`: routes, request/response models, error/status or shared browser contract.
- `AUTH_RBAC_SECURITY`: identity, session, CSRF/origin, capability, team scope, sensitive
  mutation, logging/redaction or trust boundary.
- `PERSISTENCE`: repository semantics, durable schema, migration/read compatibility,
  CAS, indexes, restart, deletion or recovery.
- `EXTERNAL_PROVIDER`: ACRA, IDP/vendor OCR, ownership service, GoldTier, PingFed or
  other external transport/contract/adapter behavior.
- `ARCHITECTURE_REFACTOR`: canonical owner, module boundary, dependency direction,
  framework/library or compatibility/retirement surface.
- `CI_TOOLING`: CI, build/test orchestration, repository scripts, scanners or governance
  validation.

Physical Mongo is required only when a change can affect Mongo schema, repository
semantics, CAS/index/startup/read/write/restart behavior, or security boundaries that
must be proved against the real driver/server. Use a fresh generated allowlisted test
database; never `clm_poc`.

## Focused, broad and independent evidence

- Focused evidence directly falsifies the changed behavior and its adverse paths.
- Broad affected evidence covers all consumers and accepted regressions named by the
  change-class rows.
- Independent QG inspects code and tests, runs relevant checks, challenges false-success
  and security paths, and writes the sole gate verdict.
- Remediation reruns the failed focus plus affected suites; re-QG independently verifies
  the repaired delta.
- Physical evidence supplements deterministic tests when real Mongo, operating-system
  process behavior or an authorized sandbox is materially affected. It is not inferred
  from mocks.

## Specialized skill routing

| Trigger | Required skill | Composition/precedence |
|---|---|---|
| bounded FYP implementation | `fyp-phase-execution` | top-level phase procedure |
| independent gate | `fyp-quality-gate` | review-only; never compose with remediation writes |
| source/contract discrepancy | `sponsor-contract-reconciliation` | authority before implementation |
| CI failure | `ci-failure-triage` | diagnose first causal failure before fix |
| external boundary/security | `integration-security-review` | review component of provider/security work |
| accepted POC regression | `poc-regression-check` | after affected implementation/integration |
| branch/integration/PR | `integration-safe-development` | Git lifecycle owner |
| new/replaced owner/boundary | `architecture-change-review` | run before implementation/ADR decision |
| accepted phase closeout | `phase-closeout-context-refresh` | update current context after acceptance/merge |
| external provider | `external-provider-integration` | composes contract reconciliation and security review |
| durable schema/repository | `persistence-schema-change` | persistence-specific requirements |
| React Query/state cache | `frontend-state-cache-change` | cache/session-specific requirements |

Where triggers overlap, use the phase skill as coordinator, apply architecture review
first for owner/boundary decisions, reconcile contracts before provider implementation,
then apply persistence/cache procedures, security review, regression, integration and
independent QG.

## Stop conditions

Stop the dependent work and record the reason when:

- a material requirement, sponsor rule, contract, source precedence, policy or mapping
  is ambiguous/contradictory;
- current source disproves the planner baseline or required canonical owner is unclear;
- the requested provider/credential/account/secret authority is absent;
- a new owner cannot pass the existence/architecture review;
- an unsafe destructive Git/database action or protected artefact access would be needed;
- current tracked changes are not clean/owned or the required branch already exists;
- a checker cannot be narrow, deterministic and baseline-green;
- required evidence fails, is unavailable, or is narrower than the completion claim;
- latest main introduces an intent conflict that cannot be safely reconciled.

Do not disable tests, add fallback behavior, loosen security, use fake success, or call
Mock/Sandbox evidence Live to cross a stop condition.

## ADR criteria

Create a new ADR from `docs/decisions/ADR_TEMPLATE.md` when a change:

- creates/replaces a canonical service, repository, provider, state owner or framework;
- changes module/dependency direction, persistence ownership/schema strategy, external
  contract interpretation, trust/security boundary, compatibility/migration strategy,
  or a durable architecture invariant;
- introduces a major library/framework or intentionally retires a supported surface;
- selects among materially different alternatives with long-lived consequences.

Do not create an ADR for routine implementation within an existing decision, mechanical
refactoring, or facts whose original historical rationale cannot be proven. Link the
new ADR from the decision log and update architecture/context after acceptance.

## Sponsor-authority criteria

Sponsor/API-owner authority is required before claiming or implementing final/live:
external endpoints/schemas/mandatory fields/value lists/mappings; authentication/TLS
details; document/retention/reviewer policy; source precedence; UBO/control rules;
related-party/hierarchy semantics; production RBAC/assignment; Ready-for-Approval; or
regulatory/compliance outcomes. A provisional POC rule must be labeled as such and
recorded in decisions/open questions.

## Integration and PR readiness

Before PR readiness, fetch and compare latest `origin/main` to `BASE_SHA`. Merge main
only when authorized; never rebase a shared branch. Resolve conflicts by current-main
intent and the smallest feature delta. Run affected regression against the integrated
state, then `python scripts/pre_pr_check.py` on a clean committed feature tree.

The PR records change class, baseline, owners/invariants, sponsor/provisional behavior,
provider truth, security/persistence impact, verification, independent QG, and context
refresh. CI evidence and human review precede the human merge.

## Closeout and context refresh

After accepted/merged work, use `phase-closeout-context-refresh` to reconcile current
state, architecture, provider classifications, sponsor questions, completed phases,
tests/CI evidence and next candidates. A squash merge may produce a different SHA; do
not invent it before merge. Record pending-merge state until the accepted main commit is
known, then set `verified_main_sha` to the inspected main baseline.
