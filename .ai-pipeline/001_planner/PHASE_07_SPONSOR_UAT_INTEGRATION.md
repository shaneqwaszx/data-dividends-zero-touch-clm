# Phase 07 — Sponsor UAT, Integration Handoff and Demo Readiness

## Authority and bounded goal

This handoff records the Phase 07 assignment supplied on 15 August 2026. It is
subordinate to `AGENTS.md` and preserves the independently accepted Phase 06 baseline.
The bounded goal is to turn the technically accepted Mock POC into a reproducible,
truthful sponsor-evaluation package:

`structured UAT + low-friction demo + safe evidence + integration handoff`

Phase 07 is delivery hardening. It is not authority to add a business workflow, change
document or UBO policy, connect an unapproved live system, or begin another phase.

## Accepted baseline to preserve

- One sponsor-facing `UEN + PDF + Start` journey through registry, document, ownership,
  readiness, and Mock GoldTier.
- Clean straight-through completion as `COMPLETED / MOCK_GOLDTIER_SUBMITTED` with zero
  human interventions after Start.
- Exception-only HITL, blocker-specific `KEEP_REGISTRY_VALUE`, and automatic resume.
- Low-confidence, multiple-blocker, ownership-cycle, ownership-incomplete,
  existing-party, policy-failure, partial-amend, and recovery call-stopping behavior.
- Deterministic document semantics and ownership arithmetic.
- Strict registry reconstruction, requested-UEN binding, safe provenance, and malformed
  response stopping.
- Phase 05 retained-outcome recovery without target replay.
- Source-neutral provider interfaces, explicit Mock/SANDBOX labels, fail-closed demo
  controls, sanitized errors, and process-local POC claim boundaries.

## Required deliverables

### Sponsor UAT and evidence

- Create `docs/uat/PHASE_07_UAT_CATALOGUE.md` covering UAT-01 through UAT-12 with a
  consistent acceptance format: purpose, inputs, integrated profile, automated stages,
  interactions, blockers, target calls, terminal state, timeline, metrics, warnings,
  result, and evidence location.
- Add focused higher-level UAT automation without duplicating lower-level unit tests.
- Provide a bounded safe JSON evidence export that contains no PDF bytes, raw provider
  payload, private fingerprints, secrets, endpoints, or exception internals.
- Keep integrated deterministic presets for straight-through, discrepancy, low
  confidence, ownership cycle/incomplete, existing party, target failure, and recovery.
- Provide a clearly marked synthetic document pack for clean, mismatch, missing,
  low-confidence, invalid-PDF, and case-isolation demonstrations.

### Demo setup, reset, and sponsor UX

- Provide a supported Windows startup path which validates Python/Node/dependencies,
  uses safe Mock defaults, starts backend/frontend, reports URLs, and fails clearly.
- Provide a deterministic reset limited to known process-local demo state. Because the
  accepted repositories are in memory, reset may be implemented as a narrowly gated
  API/service reset or documented process restart; it must not delete arbitrary files.
- Create `docs/demo/SPONSOR_DEMO_SCRIPT.md` and `docs/demo/DEMO_RUNBOOK.md`.
- Keep development controls separate and disabled by default.
- Present a concise sponsor summary containing entity, current state, completed stages,
  blocker, interventions, ownership/UBO result, Mock target result, elapsed local POC
  time, warnings, and a bounded safe timeline.
- Keep environment and claim labels explicit; `MOCK_GOLDTIER_SUBMITTED` must never be
  rendered as approval, Ready-for-Approval, or live submission.

### Integration handoff

- Create:
  - `docs/integration/INTEGRATION_HANDOFF.md`;
  - `docs/integration/PROVIDER_REPLACEMENT_GUIDE.md`;
  - `docs/integration/ADAPTER_CONFORMANCE_CHECKLIST.md`;
  - `docs/integration/API_HANDOFF.md`;
  - `docs/integration/CONFIGURATION_REFERENCE.md`;
  - `docs/integration/FAILURE_RECOVERY_GUIDE.md`.
- Cover Registry, IDP, Ownership, and GoldTier interfaces, validation, configuration,
  errors, provenance, call order, idempotency/recovery, and missing sponsor inputs.
- Create `docs/architecture/FINAL_POC_ARCHITECTURE.md` with source-neutral Mock-to-real
  replacement seams and unchanged generic orchestration.
- Create `docs/security/POC_SECURITY_BOUNDARIES.md` with both implemented controls and
  explicit production limitations.
- Create `docs/sponsor-questions/PHASE_07_SPONSOR_DEPENDENCY_MATRIX.md` by referencing,
  not duplicating or closing, Q-001 through Q-014 and D-018 where applicable.
- Add explicit ACRA and GoldTier live-integration decision gates.

### Handoff navigation

- Restructure the top-level README into a concise purpose, capability, quick-start,
  flow, demo, tests, integration, environment-status, dependency, and layout guide.
- Create `docs/FINAL_DELIVERABLE_INDEX.md` linking the handoff package and independent
  quality-gate location.

## Sponsor UAT catalogue

| ID | Sponsor-observable result |
|---|---|
| UAT-01 | Straight-through Mock submission, target sequence once, interventions `0`. |
| UAT-02 | Document discrepancy pauses; one allowed registry-retention action resumes automatically; interventions `1`. |
| UAT-03 | Low confidence remains blocked with no fake action and zero target calls. |
| UAT-04 | Multiple document blockers are retained; resolving one cannot clear another. |
| UAT-05 | Ownership cycle requires review; no definitive UBO or target call. |
| UAT-06 | Incomplete legal-entity chain requires review; no false completion. |
| UAT-07 | Existing deterministic direct-plus-indirect path arithmetic aggregates once. |
| UAT-08 | Existing GoldTier party performs search only and requires review. |
| UAT-09 | Policy failure stops before amend and cannot complete. |
| UAT-10 | Partial amend requires review and cannot become Mock-submitted success. |
| UAT-11 | Target-finalization fault persists `RECOVERY_PENDING`; later reconciliation is replay-free. |
| UAT-12 | Wrong identity, malformed registry data, or unsafe provenance fails before canonical progression. |

The UAT implementation may reuse existing deterministic scenario controls and test
helpers. It must verify sponsor-observable state, blockers, metrics, ordered calls, safe
timeline/evidence, and warnings rather than duplicating internal assertions.

## Contract and sponsor boundary

No new authoritative sponsor artefact or approved live access was supplied with the
assignment. Contract assumptions therefore remain unchanged. The sponsor-contract
reconciliation activity is an evidence/status audit only unless authoritative new
material is discovered.

- Q-001: Ready-for-Approval/four-eye semantics remain unconfirmed.
- Q-002: seeded hierarchy retrieval remains blocked.
- Q-003/Q-005/Q-013/Q-014: final document, confidence, source-authority, reviewer,
  privacy, and retention policy remain unconfirmed.
- Q-004: the UBO threshold/comparator remains project-provisional.
- Q-006/Q-007: related-party semantics and Singapore mappings remain unconfirmed.
- Q-008/D-018: real GoldTier/PingFed remains blocked; quarantined material is prohibited.
- Q-012: live ACRA subscriber binding/access remains blocked.

Mock POC completion is permitted despite these dependencies, but every sponsor-facing
surface must keep them visible and must distinguish `MOCK`, `SANDBOX`, and `LIVE`.

## Security and privacy requirements

- Use synthetic data only. Never track real customer/KYC data or raw sponsor artefacts.
- Do not open, test, copy, or sanitize the quarantined authentication collection.
- Never expose uploaded PDF bytes, raw OCR/provider/target payloads, authorization
  material, credentials, private fingerprints, endpoints with secrets, stacks, or
  exception text in exports, APIs, UI, logs, fixtures, or reports.
- Demo/reset/export endpoints must fail closed when demo controls are disabled.
- Keep Mock defaults credential-free and network-free.
- Do not claim production RBAC, antivirus/CDR, durable audit storage, encryption policy,
  distributed locking, live TLS/auth verification, or monitoring.

## Explicit non-goals

- Live ACRA subscriber networking or a guessed ACRA contract.
- Real GoldTier/PingFed, credential handling, or unverified LIVE labeling.
- Live hierarchy or related-party writes.
- Ready-for-Approval or any autonomous approval decision.
- Sponsor-final IDP confidence/source/reviewer policy or sponsor-final UBO policy.
- Production RBAC, durable database/queue, distributed orchestration, enterprise
  monitoring, analytics platform, workflow engine, or new business workflow.
- Browser E2E if it would add destabilizing dependencies; an evidence-backed decision
  to rely on backend sponsor-observable tests plus existing frontend tests is allowed.
- Any later phase.

## Verification

Run and report every relevant configured check:

- full backend pytest;
- focused Phase 01, 02, 03, 04, 05, 06, and 07/UAT suites;
- adapter conformance, contract, repository, reset/export/configuration, and safe-error
  tests;
- Ruff and strict mypy;
- `pip check`;
- secret scanner tests and standalone scan;
- GoldTier validator tests, classification, and expected quarantine failure;
- frontend typecheck, tests, and production build;
- `npm ls --all`;
- supported startup/runbook checks and a bounded clean-room reproducibility audit;
- tracked diff, cached diff, tracked private files, and explicit untracked whitespace.

After implementation stabilizes, apply the integration-security and POC-regression
review workflows and create:

- `.ai-pipeline/reports/PHASE_07_INTEGRATION_SECURITY_REVIEW.md`;
- `.ai-pipeline/reports/PHASE_07_POC_REGRESSION.md`.

These are implementation-side supporting reviews and do not replace an independent
Phase 07 quality gate.

## Acceptance and stop condition

Phase 07 is implementation-ready only when UAT-01 is reproducible with zero human
interventions, UAT-02 resumes after exactly one allowed intervention, review/failure
scenarios stop target calls correctly, recovery remains replay-free, the demo/runbook is
reproducible, exports and fixtures are safe, integration seams and dependency gates are
clear, environment claims are truthful, Phase 01–06 regressions remain green, and no
Critical/High supporting-review finding remains.

Do not stage, commit, push, merge, change branch, begin another phase, or issue the
independent Phase 07 quality gate.
