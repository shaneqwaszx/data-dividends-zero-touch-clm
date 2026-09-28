# GoldTier sandbox pipeline inspector intent

## TaskIntentDraft

- Requested outcome: complete the bounded external-provider POC using the official
  ACRA API Marketplace Mock and the Delta Capita GoldTier XPI sandbox, prove one
  synthetic Search -> Shell -> Policy -> Amend execution with read-back, and replace
  the table-first processing inspector with a collapsed accessible visual pipeline.
- Source baseline: branch `feat/goldtier-sandbox-pipeline-inspector`; `BASE_SHA`,
  `HEAD`, merge base, and `origin/main` are all
  `463ecdcb4357bb44618cdd5b277671766543dbfc`; initial worktree clean.
- Scope: XPI contract reconciliation, optional policy fields, explicit provider
  composition/no-fallback evidence, existing-ledger execution, local untracked
  configuration, sanitized sandbox/portal evidence, backend-authored pipeline
  projection, frontend inspector, tests, security review, and independent QG.
- Non-goals: Production ACRA/GoldTier, PingFed, related-party writes, hierarchy
  creation, invented Singapore target mappings, final approval, autonomous approval,
  raw sponsor/provider payload retention, or Git publication/integration.
- Stop conditions: sandbox unavailability; a mutation requiring undocumented provider
  vocabulary or Singapore mapping; unsafe secret handling; unproved non-empty response
  shape that cannot be decoded strictly; portal access requiring credential disclosure;
  or a change that would bypass the existing target ledger.

## Continuation authority

The final continuation resolves the Singapore identity mapping to canonical ACRA legal
name/address, unchanged UEN, both country fields `SG`, and
`registrationType=ACRA`. It fixes bounded POC values `DSD`, `Singapore`, and
`ANZBGL (Singapore Branch)`. The corrected standalone OpenAPI 1.0.0 controls exact
KYC Customer Type and Client Segment vocabularies; those two values are selected and
frozen per case rather than globally defaulted. Australia and `ABN` remain prohibited.

The later continuation authorizes a GoldTier-first POC flow. Bounded initial legal name
and country feed Search before bootstrap registry acquisition. Exact match reuses the
existing target ID and skips ACRA acquisition and Shell; no match proceeds to the
official ACRA Marketplace Mock; ambiguous results stop without either external
acquisition or target mutation. New document evidence may reconcile and amend existing
target state but GoldTier is not an automatic source-precedence winner. This is a POC
orchestration requirement, not a global target-value default or Production claim.

The same continuation preserves a stricter prerequisite: recovering the prior uncertain
Shell must transition its original ledger checkpoint. Recreating that process-local
checkpoint, substituting ID `143878` into new persistence, or sending another Shell is
outside authority even when portal evidence proves the customer identity.

## BaselineReadSetHint and BaselineUsageDraft

Acknowledged before edits:

- root, backend, and frontend `AGENTS.md`;
- `docs/DEVELOPMENT_WORKFLOW.md`, `docs/ARCHITECTURE.md`,
  `docs/PROJECT_STATE.md`, `docs/PROJECT_CONTEXT.md`, and current open questions;
- GoldTier XPI contract, discrepancy, mapping, reconciliation, ADR-004, ADR-005,
  configuration, activation, security, and regression procedures;
- authorized private XPI guide/collection, verified by the previously recorded hashes;
- exact owning connector, mapper, composition, orchestration/ledger, API/UI, and tests.

No matching active planner exists for this final pre-Phase-22 task; the explicit user
assignment supplies the bounded goal and acceptance criteria. Historical reports are
Tier 2 and will be loaded only for a named current-source question.

## ImpactStatementDraft

Change classes are `EXTERNAL_PROVIDER`, `AUTH_RBAC_SECURITY`, `BACKEND_DOMAIN`,
`BACKEND_API`, and `FRONTEND_UI`. No persistence schema, repository owner, target
ledger owner, cache owner, or architecture boundary is intended to change. API/type
impact is limited to a safe backend-authored processing projection if required to keep
the tree factual for both stage-order versions.

## Execution Readiness View

- Intent lock: real sandbox proof remains `SANDBOX`, never Production or Live.
- Scope fence: customer Search/Shell/Policy/Amend only; related-party operations blocked.
- Baseline lock: current source/tests and the supplied v2 XPI artefacts control.
- Owner constraints: reuse composition, target mapper, entity resolver, CLM plan,
  target ledger, and backend API owners; no browser-owned business state.
- Compatibility boundary: isolated test doubles stay supported; configured normal POC
  runtime gets explicit official-Mock ACRA plus XPI sandbox with no fallback.
- Test obligations: focused provider/orchestration/UI first, then all affected backend,
  frontend, contract, security, architecture/project-state, browser, and regression
  checks; real external evidence stays sanitized.
- Review gates: implementation self-review, integration-security review, then a fresh
  independent QG; any content remediation requires fresh re-QG.
- Drift rule: stop the dependent slice when authority or response shape would require a
  guessed value, fallback, retry, or false success.

## 2026-09-28 bounded local continuation

- External mutation fence: no further GoldTier Shell, Policy, Amend, related-party, or
  hierarchy call is authorized. The retained Garden record remains the only external
  case; read-only evidence must not be presented as a completed acceptance lifecycle.
- Local outcome: make backend-authored onboarding progress visible during retained
  document intake, correct registry partial/unavailable/malformed presentation, verify
  the official Marketplace Mock read-only, and provide sanitized teammate preflight.
- Change classes added: `FRONTEND_STATE_CACHE`, `CI_TOOLING`, and `DOCS_ONLY` alongside
  the already active frontend/backend/provider classes. No persistence owner, target
  ledger, provider fallback, or business mapping changes.
