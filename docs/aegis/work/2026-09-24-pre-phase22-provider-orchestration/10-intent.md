# Pre-Phase 22 provider orchestration and sandbox testing - Intent

## TaskIntentDraft

- Requested outcome: deliver the user-authorized Pre-Phase-22 provider-orchestration
  increment through implementation, verification, fresh independent quality gate,
  publication, PR, and CI, stopping before human squash merge.
- Goal: add early incremental GoldTier synchronization, restore the official ACRA API
  Marketplace Mock as an explicit non-Live provider, add the Certificate of
  Incorporation POC profile, optional safe processing detail, and an HR-only GoldTier
  Sandbox console while preserving current canonical owners and truthful provider
  classifications.
- Success evidence: focused and broad change-class checks, authorized safe provider
  diagnostics, no-replay/call-stopping evidence, guarded physical/browser evidence where
  affected, an exact fresh independent `PASS`, clean publication commit, push and PR CI.
- Stop condition: finish only when the authorized scope is verified and published for
  human review; otherwise stop a dependent lane as blocked, needs-verification, or
  scope-exceeded when authority, infrastructure, safety, or convergence requirements fail.
- Non-goals: Phase 22 activation; PR merge; Live ACRA or GoldTier claims; speculative
  OAuth; fake related-party child IDs; autonomous approval; Q-016-dependent Exception
  Workbench mutation; production SSO, OCR, Camunda, risk, or non-Singapore registries.
- Scope: one implementation writer/Git coordinator in
  `feature/pre-phase22-provider-orchestration`; three bounded read-only analysis
  workstreams; a fresh review-only quality-gate role; separate publication role after
  exact `PASS`.
- Change kinds: `EXTERNAL_PROVIDER`, `BACKEND_DOMAIN`, `BACKEND_API`,
  `AUTH_RBAC_SECURITY`, `PERSISTENCE`, `FRONTEND_UI`, `FRONTEND_STATE_CACHE`,
  `ARCHITECTURE_REFACTOR`, plus affected documentation.
- Risk hints: high; external transport/auth ambiguity, replay safety, durable schema,
  backend-authoritative RBAC, cache isolation, and shared composition/API/UI hotspots.

## BaselineReadSetHint

- `origin/main@5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3`
- `AGENTS.md`, the full `scripts/dev_context.py --full` Tier-1 set, current provider,
  target-ledger, persistence, auth, API, frontend and test owners.
- Current GoldTier/ACRA contracts, mappings, decisions and open questions.
- Accepted PR #54 exact gate and the user-supplied Pre-Phase-22 assignment.

## BaselineUsageDraft

- Required baseline refs: the set above.
- Acknowledged before implementation: constitution, task/Git identity, full context
  selector, architecture, development workflow, project state, sponsor questions,
  branch protocol, triggered repository skills, and PR #54 exact gate.
- Still being read: provider contracts/decisions, security checklist, persistence/cache
  owners, exact current source/tests and requested historical ACRA evidence.
- Missing refs: none known; any newly discovered material authority gap remains explicit.
- Advisory decision: continue authority/architecture reconciliation; no product code edit
  is authorized until the read set and architecture existence check are complete.

## ImpactStatementDraft

- Compatibility boundary: current Mock defaults, legacy envelopes, target no-replay
  recovery, session-scoped caches, role names, and accepted demo scenarios remain
  compatible unless the assignment explicitly supersedes call ordering.
- Canonical owners: existing registry router/connectors/mapper, onboarding/zero-touch
  services, CLM plan, target ledger, entity resolver, case envelope repositories,
  authorization/capabilities, frontend auth/query owners, and navigation/views.
- Dependency direction: external DTO -> canonical evidence -> domain/readiness -> target
  mapper/ledger; API/UI never owns provider, persistence, or authorization behavior.
- Retirement boundary: dormant `bizfile_mock` intent may be recovered only as one
  canonical explicit API Marketplace Mock mode; no duplicate provider modes, routers,
  ledgers, resolution engines, or cache owners survive.
- Authority boundary: sponsor-confirmed early/incremental GoldTier intent and user-
  authorized provisional POC values remain distinctly labelled; unresolved contract or
  auth details block only their dependent operation.

## Execution Readiness View

- Intent lock: the user-supplied Pre-Phase-22 assignment; Phase 22 stays on hold.
- Scope fence: sections A-G and their reports/tests only; no unrelated refactor.
- Baseline lock: clean `main` and `origin/main` at `5f71b4d...`; feature branch created
  from that SHA; current project-state SHA is a known stale metadata field only.
- Owner/contract constraints: extend current ports, services, ledger, resolver,
  persistence envelope, capability model and query lifecycle; do not create substitutes.
- Compatibility boundary: Mock defaults and historical records remain valid; no silent
  provider fallback or replay.
- Task batches: context/baseline reconciliation; architecture/contract decision;
  GoldTier orchestration; ACRA official Mock; COI profile; progress details; HR console;
  integration/tests/docs; self-review; independent gate; publication/CI.
- Test obligations: full matrix from `docs/DEVELOPMENT_WORKFLOW.md` plus the assignment's
  focused provider, RBAC, progress, certificate, browser, Mongo and regression cases.
- Review gates: implementation self-review and security/regression evidence, then a fresh
  independent exact-content `PASS`; any remediation invalidates the old reviewed freeze.
- Drift/rewind: stop dependent work on missing authority; after two failed repairs of one
  design problem, escalate rather than widen scope.
- Advisory boundary: these records aid continuity and do not grant acceptance or merge.

These records are Method Pack drafts / hints, not authoritative runtime decisions.
