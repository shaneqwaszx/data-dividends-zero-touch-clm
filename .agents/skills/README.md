# Repository-scoped Codex skills

These workflows live at the official repository skill location, `.agents/skills/`.
They supplement the project control documents; they do not replace them.

## Skills and explicit invocation

| Skill | Purpose | Example |
|---|---|---|
| `fyp-phase-execution` | Execute one assigned planner phase through implementation, tests, and handoff without starting the next phase. | `Use $fyp-phase-execution to implement the assigned Phase 03 planner handoff.` |
| `fyp-quality-gate` | Run the combined independent contract, test, architecture, security, and adversarial review and write the sole phase gate report. | `Use $fyp-quality-gate to review Phase 03 and write PHASE_03_QUALITY_GATE.md.` |
| `sponsor-contract-reconciliation` | Reconcile conflicting sponsor/API evidence, quarantine invalid examples, and update discrepancies, decisions, or open questions. | `Use $sponsor-contract-reconciliation to reconcile the createRelatedParty mandatory fields.` |
| `ci-failure-triage` | Find the first causal CI failure, reproduce and classify it, then apply and verify the smallest authorized fix. | `Use $ci-failure-triage to diagnose and fix the failing backend typecheck job.` |
| `integration-security-review` | Review ACRA, IDP/upload, GoldTier/PingFed, HTTP, credential, TLS, KYC/PII, logging, and sponsor-artefact boundaries. | `Use $integration-security-review to review the new document-upload and IDP path.` |
| `poc-regression-check` | Verify accepted synthetic scenarios, terminal statuses, connector call stopping, truthful mode labels, and no false completion. | `Use $poc-regression-check after the connector changes and report every canonical scenario.` |
| `integration-safe-development` | Keep feature work based on latest `origin/main`, resolve conflicts by intent, and audit deterministic pre-PR hazards without broad rewrites or unsafe Git operations. | `Use $integration-safe-development to sync this feature branch and assess PR readiness.` |
| `architecture-change-review` | Review any new/replaced owner, dependency direction, major library, persistence ownership, or compatibility retirement before implementation. | `Use $architecture-change-review before adding the new provider manager.` |
| `phase-closeout-context-refresh` | Reconcile current state/architecture/provider/question context after independent acceptance or merge without inventing a squash SHA. | `Use $phase-closeout-context-refresh after the accepted phase is merged.` |
| `external-provider-integration` | Implement or change ACRA, GoldTier/PingFed, vendor IDP, ownership-service, sandbox/auth/TLS, or other external API boundaries. | `Use $external-provider-integration for the authorized ACRA sandbox operation.` |
| `persistence-schema-change` | Change a durable schema, repository CAS/create/update/delete behavior, index, migration, or restart recovery. | `Use $persistence-schema-change for the case-envelope version change.` |
| `frontend-state-cache-change` | Change React Query keys, session cache lifecycle, cancellation, invalidation, mutation retry, or stale-response/deletion behavior. | `Use $frontend-state-cache-change for Dashboard query caching changes.` |

Skill descriptions also support implicit triggering when a request clearly matches. Use
the `$skill-name` form when a teammate wants to require a particular workflow.

## When not to use and composition

| Skill | Do not use when | Relationship / precedence |
|---|---|---|
| `fyp-phase-execution` | the task is review-only, CI-only, or not an assigned phase/remediation | coordinates applicable specialist skills; never starts the next phase |
| `fyp-quality-gate` | implementation or remediation is requested | independent review-only owner after implementation/regression |
| `sponsor-contract-reconciliation` | no evidence conflict or sponsor/API authority question exists | runs before provider/domain implementation; feeds decisions/questions |
| `ci-failure-triage` | checks are green or no actual failing log exists | diagnoses the first causal failure; then invokes the owning change skill |
| `integration-security-review` | no trust, secret, auth, upload, external-data or logging boundary changes | mandatory review component of external/security work; normally read-only |
| `poc-regression-check` | a change cannot affect accepted POC behavior/calls/labels | follows affected implementation/integration; catalogue changes need planner authority |
| `integration-safe-development` | no branch/integration/PR lifecycle is involved | owns Git baseline/drift/merge-safety procedure, not product acceptance |
| `architecture-change-review` | edits stay inside an existing owner/invariant | precedes every specialist skill when ownership/dependency/retirement changes |
| `phase-closeout-context-refresh` | work is unaccepted implementation or a speculative future phase | follows independent acceptance; publishes current main only after merge verification |
| `external-provider-integration` | a purely internal Mock fixture changes without parity/claim impact | composes contract reconciliation, architecture review and security review |
| `persistence-schema-change` | state is memory-only and cannot affect storage | composes architecture review if ownership changes; physical Mongo only when relevant |
| `frontend-state-cache-change` | UI-local presentation state has no server/cache effect | uses backend API/auth authority; architecture review if adding a new state owner/library |

Overlap order: phase coordinator -> architecture existence review -> contract
reconciliation -> provider/persistence/cache procedure -> security review -> POC
regression -> integration-safe development -> independent QG -> closeout refresh.

## How the control layers differ

- `AGENTS.md` is the authoritative repository-wide policy: project scope, evidence
  hierarchy, architecture, security, testing, and definition of done.
- `.ai-pipeline/001_planner/` contains the authoritative bounded scope and acceptance
  criteria for the currently assigned phase. The other `.ai-pipeline/` role files are
  supporting review/execution references, and `.ai-pipeline/reports/` records final gate
  evidence and readiness.
- `.agents/skills/` contains reusable procedures for recurring types of work. A skill
  tells Codex how to execute a workflow consistently; it cannot broaden a planner scope,
  override `AGENTS.md`, authorize a commit/push/merge, or start the next phase.

## Sharing through Git

The skills are ordinary repository files. After a human-approved commit is pushed,
teammates receive them by cloning the repository or pulling the branch containing the
commit. Codex can then discover the repository-scoped skills from `.agents/skills/` in
that checkout. Until committed and shared, the files exist only in the current working
tree. Review skill changes like other project documentation and keep global rules in
`AGENTS.md` rather than duplicating them across skills.
