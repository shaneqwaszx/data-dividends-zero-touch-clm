# Pre-Phase 22 integrated capability expansion - Checkpoint

- Task ID: PRE-PHASE22-CAPABILITY-EXPANSION
- Current todo: Complete broad verification of the bounded exact-gate remediation,
  freeze a new GoldTier XPI candidate, obtain a fresh exact-candidate independent
  quality gate, then publish the reviewed paths without merging.
- Active slice: The first exact XPI gate returned `FAIL` on four boundary omissions.
  Focused RED/GREEN remediation now binds policy/catalogue to the case snapshot,
  validates every prepared request before dispatch, treats post-dispatch response
  ambiguity as non-replayable uncertainty, projects Sandbox truthfully, and bounds RP
  ownership percentages. Broad verification and a fresh gate remain. No sandbox
  mutation occurred.
- Blocked on: Q-016 assignment/note/SLA authority remains intentionally deferred.
  Related-party external execution is separately blocked until the `childId` lifecycle
  is conclusively established. Docker is currently unavailable for fresh physical
  Mongo evidence.
- Completed: ready slices implemented; first gate's four current-slice findings
  remediated; full backend/frontend/static/contract/security and final physical-Mongo
  evidence is green. Earlier lifecycle/browser evidence remains applicable.
- Starting identity: branch `feature/pre-phase22-capability-expansion`; HEAD and
  `origin/main` `3ca232b58c3842f413c4552dbd3b85aabea4591c`; 84 known candidate
  paths; fingerprint
  `57933423940d0b063adac8d45a742847dabb7afc4b6d05827bc493627f36a43d`.
  One additional strangely named root file is preserved as an unowned inventory
  anomaly and excluded from the candidate fingerprint.
- Next step: complete repository checks and fingerprint the frozen candidate. Do not
  execute a customer write: the eight authoritative target-policy defaults remain
  `TBD_SPONSOR`, so the required enrichment/authority prerequisite is unsatisfied.
  Do not execute any related-party write because child-ID lifecycle remains blocked.

### Slice Card - GoldTier XPI contract reconciliation

- Goal: Establish a field-complete, authority-labelled XPI dialect boundary before
  transport implementation.
- Parent plan/spec: `docs/aegis/plans/2026-09-23-pre-phase22-capability-expansion.md`
  plus the owner-supplied GoldTier continuation handoff dated 24 September 2026.
- Files: XPI mapping matrix, GoldTier discrepancy catalogue, this checkpoint.
- Boundary: Documentation only; no source, configuration, provider, database, Git
  index, or external-system mutation.
- Verification: Sponsor-file hashes, visual PDF inspection, redacted collection
  structure extraction, matrix self-review, and Markdown hygiene.
- Stop: Any missing/contradictory field authority remains explicit and blocks only its
  dependent operation.

### Architecture Review - GoldTier XPI sandbox adapter

- Verdict: `PROCEED` within the boundary below.
- Requirement/change classes: `EXTERNAL_PROVIDER`, `BACKEND_DOMAIN`, `BACKEND_API`,
  `AUTH_RBAC_SECURITY`, `PERSISTENCE`, `FRONTEND_STATE_CACHE`, `FRONTEND_UI`,
  `ARCHITECTURE_REFACTOR`.
- Existence check: reuse the existing GoldTier connector port, target ledger,
  policy catalogue/case snapshot, entity-resolution engine, case envelope, case-scoped
  CLM plan API and authenticated frontend query. A second execution, policy, resolver,
  persistence, authorization, audit or cache owner is prohibited.
- Dependency direction: sponsor XPI payload -> strict adapter DTO/safe projection;
  canonical case + immutable policy snapshot -> target mapper -> connector; target
  results -> existing ledger -> case/CLM projections. Routes/UI never call providers or
  persistence directly.
- Entropy/retirement: one explicit `sandbox` adapter and mapper beside retained Mock;
  no fallback and no runtime provider router. Mock is a compatibility mode, not a
  recovery path. RP dispatch stays disabled until its child lifecycle is proved.
- ADR: required because composition, external contract interpretation and the
  trust/security boundary change. Proposed ADR-004 records the forward decision;
  `docs/ARCHITECTURE.md` and provider state are the required baseline-sync targets.
- Verification: focused DTO/transport/mapper/orchestration/policy/preview tests, all
  affected regressions, architecture/security/provider checks and fresh independent QG.

### Strict TDD slice - XPI contract, policy and transport

- TDD Route: `Mode: off`, `Decision: strict`, authority: the existing approved plan's
  literal `TDD Route: strict` decision.
- Change necessity: documentation cannot execute the authorized sandbox path, enforce
  local missing-enrichment failure, or prove ledger no-replay. Minimum code boundary is
  focused XPI DTO/mapper/connector modules plus narrow policy/composition/ledger/preview
  wiring. Decision: `code-change`.
- RED/GREEN proof: outgoing contract shape, safe transport and deterministic local
  decisions only. It does not prove sandbox success, full candidate acceptance or
  production interoperability.
- Complexity budget: focused new source/test owners are within budget; `onboarding.py`
  (1,490 lines), `clm_orchestration.py` (892 lines) and frontend `App.tsx` are pressure
  points. New transport/mapping/preparation logic must not be added there. Their edits
  are limited to ledger orchestration and declarative wiring; preview UI belongs in a
  focused component.
- Missing Aegis references: the installed ADR skill names
  `docs/adr/ADR-CREATION-GATE.md` and `docs/current/AEGIS_ADR_AUTO_BACKFILL.md`, but
  neither resource exists in the installed skill tree. The project-owned ADR criteria,
  template, architecture baseline and decision log therefore remain the operative
  fallback.

### GoldTier XPI implementation and verification closure

- Explicit composition: `mock` remains default; `sandbox` selects the XPI adapter and
  never falls back.
- Transport: HTTPS/TLS 1.3, certificate verification, redirects off, bounded timeout
  and response bytes, backend-only `user_id`, safe fixed errors.
- Mapping: canonical identity/address plus eight authority-labelled target-policy
  values; contact, group company, address type and ANZSIC omitted.
- Resolution: no-match creates Shell; one exact identifier/country candidate reuses the
  party without Shell; multiple/probable/conflicting/non-exact candidates stop at
  review with zero mutation.
- Ledger: both Search/Shell/Policy/Amend and Search/Policy/Amend prefixes are valid.
  Uncertain mutation outcomes remain `IN_PROGRESS` and cannot replay automatically.
- Preview/UI: existing case-scoped CLM plan carries bounded operation fields,
  provenance, authority, missing/validation state and policy version. No credential or
  raw provider response is exposed, and no new cache/query owner was added.
- Persistence: additive optional schema-v5 fields; earlier schema-v5 records without
  target preparation read as Mock/no-enrichment without rewrite.
- External evidence: four bounded synthetic searches returned HTTP 200 empty arrays.
  No write was executed because all target-policy defaults remain `TBD_SPONSOR`.
- Fresh local evidence at the working candidate: backend `1219 passed, 29 skipped`;
  frontend `278 passed`, type-check and production build pass; Ruff and strict Mypy
  pass; contract `44 passed`; scoped governance/tooling/security `239 passed`; Windows
  lifecycle `23 passed`; final isolated Playwright `14/14 passed`; provider-readiness,
  architecture, project-state, policy-authority and tooling checks pass. Physical Mongo
  is not freshly runnable because the local Docker daemon is unavailable; prior
  candidate evidence is not relabelled as current.
- Browser failure history: two earlier full attempts stopped at different transient
  focus/response waits. Each exact point passed five same-port reruns and the unchanged
  final full suite passed 14/14. No source workaround was added.
- Readiness truth: `GOLDTIER_XPI` is `PARTIAL / SANDBOX_PARTIAL`; Mock remains default;
  `GOLDTIER_REAL` and `PINGFED_AUTH` remain blocked. This is not full sandbox
  verification or a Live claim.

### Exact XPI gate failure and remediation cycle 1

- Reviewed identity: 122 paths at
  `afdb940366dbf54079a7c34c1afe8504ff799d93ae766b8cb8d79fa0d97feb6d`.
- Verdict: `FAIL`; preserved verbatim in
  `.ai-pipeline/reports/PRE_PHASE22_CAPABILITY_EXPANSION_GOLDTIER_REQUALITY_GATE_FAILED.md`.
- Concrete findings: unusable target-policy text and missing case-snapshot binding;
  oversized mutation response finalized instead of uncertain; Sandbox presented as
  Mock; RP percentages above 100 accepted.
- Remediation: existing policy/mapper/service, connector/ledger, execution-profile/UI,
  and strict DTO owners were corrected without a new state, cache, provider, or
  execution owner.
- Focused evidence: XPI `54 passed`; affected frontend `102 passed`; TypeScript and
  focused Ruff pass. Complete matrix pending.
- Stop boundary: if a fresh exact gate fails again for the same underlying design issue,
  stop for planner/human review under the two-cycle convergence rule.

### Final remediation verification

- Backend: 1,273 collected, `1,244 passed / 29 environment-skipped`; full Ruff and
  strict Mypy pass over 105 source files.
- Frontend: `22 files / 280 tests`, typecheck, dependency tree, and 114-module build
  pass. A stale `Completed Mock workflow` E2E assertion exposed remaining generic
  completed-client Mock copy; provider-neutral copy was applied, the exact case passed,
  and the unchanged isolated Playwright suite passed `14/14`.
- Contract `44`, governance/security/tooling `239`, and Windows lifecycle `23` pass.
  Project-state, architecture, policy-authority, provider-readiness, tooling, secret,
  dependency, whitespace, synthetic evaluation, and GoldTier example checks pass.
- Docker's Linux daemon pipe remains absent, so physical Mongo is not freshly verified;
  no earlier result is relabeled. No external or database mutation occurred.
- Next action: freeze the exact candidate and obtain one fresh independent XPI
  re-quality-gate `PASS` before any staging, commit, push, PR, or CI publication.

### Authorized remediation - immutable provider identity

- Gate input: preserved final re-quality-gate `FAIL`, finding `GT-FINAL-RQG-01`.
- Root owner: the existing retained `GoldTierSubmissionPlan`; no new router, registry,
  ledger, persistence owner or schema version.
- Strict RED: both Mock/Sandbox drift directions reached the old defect, and schema-v5
  accepted contradictory plan/execution provider identity.
- GREEN: submission input derives from the retained plan; mapper and connector modes
  are fail-closed compatibility assertions before ledger/network activity; schema-v5
  rejects contradictory plan/input/matching-ledger identity and preserves plan-only
  records.
- Scope retained: Q-016 deferred, Phase 22 held, no Live claim, no external/provider/
  related-party/database write, and the historical gate report remains untouched.
- Next authorized action: complete the full verification matrix, self-review the final
  diff, freeze the exact candidate, and obtain a fresh independent exact-content gate.

### Provider-identity remediation verification

- Focused RED/GREEN and affected suites: pass for connector-only Sandbox-to-Mock drift,
  mapper-only Mock-to-Sandbox drift, stable provider paths, schema-v5 matching,
  contradiction rejection and plan-only compatibility.
- Complete backend: final unchanged run `1,308 passed / 29 skipped`; Ruff, strict Mypy
  (105 source files) and dependency validation pass.
- Frontend/static: Vitest `22 files / 282 tests`, TypeScript, dependency inspection,
  Playwright discovery and 114-module production build pass.
- Contracts/governance/security/lifecycle: contract `44`, delivery assets `4`, selected
  governance/security `163`, Windows lifecycle `23`; direct architecture, project-state,
  tooling, policy, provider-readiness and secret checks pass.
- Physical Mongo: `MISSING_INFRASTRUCTURE` because the Docker Desktop Linux daemon is
  unavailable; no prior result was promoted to current evidence.
- Browser: the unchanged Case Activity selection repeatedly fails at varying response or
  visibility waits after selections 1-6 pass. Focused and diagnostics reruns reproduce
  the same localized historical instability. It is recorded, not waived or repaired
  outside scope, for the independent gate to adjudicate.
- Self-review: the duplicate mutable provider capture is retired; the retained CLM plan
  is the only logical-submission identity owner, with mapper/connector compatibility and
  schema-v5 semantic enforcement. No second owner, fallback, schema v6, provider-status
  expansion or sponsor-policy invention was found in the final remediation diff.

### Acceptance-evidence closure checkpoint

- Physical Mongo is no longer missing: task-owned Mongo 7.0 evidence passes the new
  provider-identity suite `6/6` and the complete registered runner `9 suites / 35 tests`.
  Each test owns a fresh allowlisted database and proves collection inventory and
  teardown; no URI was printed or persisted and no unrelated container was touched.
- Browser root evidence: the default Vite proxy's close-per-request Windows loopback
  lifecycle intermittently received response headers without body bytes after the
  backend completed the body iterator. An E2E-marker-scoped keep-alive agent is the only
  retained correction; no application behavior, timeout, retry, sleep or assertion was
  changed.
- Browser final evidence: keep-alive counterfactual `5/5`, clean isolated Case Activity
  `10/10`, and unchanged configured browser suite `14/14` in fresh lifecycles.
- Broad final evidence: backend `1,308 passed / 35 skipped` from 1,343 collected; Ruff,
  Mypy 105 files, dependencies, frontend `22/282`, typecheck/build, contracts `44`,
  delivery `4`, governance/security `120`, pre-PR/CI helpers `67`, lifecycle `23`, direct
  governance checks, synthetic evaluation and GoldTier example classification pass.
- Scope remains provider-identity acceptance evidence plus deterministic browser
  evidence only. Q-016 is deferred, Phase 22 is held, and no external/provider/customer
  write or Live claim occurred.
- Next action: freeze the exact candidate for one fresh independent re-quality gate.
  Publication remains prohibited unless that exact gate returns `PASS`.
