# GoldTier sandbox pipeline inspector evidence

## 2026-09-28 provider-verified recovery and GoldTier-first continuation

- Schema v6 retains the original uncertain Shell chronology and a separate
  `PROVIDER_VERIFIED_RECOVERY` fact for exact Garden ID `143878`; it does not claim the
  Shell response returned that ID. Recovery is idempotent, RBAC/case-lock protected,
  rejects adverse identity/state cases, and sends zero Shell requests.
- Mongo restart evidence proves mutation intent, uncertain state, recovered ID, and
  no-replay behavior survive process replacement. The latest full physical run passed
  all 36 tests across the nine explicit suites against a new localhost-only Mongo 7
  container; the container was then stopped and removed.
- GoldTier-first source now validates bounded initial identity and Singapore eligibility
  before Search. Exact verified prior state skips ACRA, Shell, and new Policy creation;
  no match alone acquires ACRA and later uses the new-customer target path; ambiguity
  performs zero ACRA and zero target mutation. A direct exact-existing regression proves
  `SEARCH, AMEND, READBACK` with no Shell or Policy call and same-ID reuse.
- Before the Policy-recovery slice, the candidate passed backend `1,416 passed / 36
  skipped`, Ruff, strict mypy over 108 source files, frontend `291/291` tests across 24
  files, typecheck, a 117-module production build, 44/44 contract tests, all 14 isolated
  Playwright lifecycles, governance/security checks, and 36 physical-Mongo tests. That
  broad evidence is now stale for the changed recovery slice. Current focused evidence
  passes the complete XPI sandbox file plus Phase-12 persistence and Garden pipeline
  suites, Ruff, and strict mypy over the same 108 source files. A new full matrix was not
  run after the external Amend failure because the acceptance sequence did not reach
  candidate freeze.
- The first real Policy intent was persisted and dispatched once. Its network outcome
  remains uncertain, but authenticated read-only portal evidence proved exactly one
  `Singapore / Requested` Policy request on ID `143878`. The ledger retains a separate
  Policy provider-recovery fact with `replayed=false`; both Shell and Policy recoveries
  survived a separate-process Mongo reload, and no Shell/Policy replay occurred.
- Exactly one ledger-owned Amend was then attempted after connector/environment/ID/
  recovery/no-prior-Amend and sanitized-preview checks. Its transport outcome was
  uncertain. The ledger stops at attempted `SEARCH,SHELL,POLICY,AMEND`, definitive
  `SEARCH`, lifecycle-resolved `SEARCH,SHELL,POLICY`. Same-record portal audit proves
  one API-connect Amendment sequence, `Created` at 08:47:48 then `Valdiation Failed` at
  08:47:49 on 2026-09-28. This is a failed provider outcome, not success; Amend was not
  replayed and no read-back or second Garden external case was started.
- The existing ledger owner now retains a separate provider-verified Amend-failure fact.
  Two bounded runner invocations (record+reload and fresh verify-only) each reported
  `PROVIDER_VERIFIED_FAILURE`, normalized `PROVIDER_VALIDATION_FAILED`, Amend complete
  false, replay false, zero network calls, and restart recovery PASS.
- Durable mapper reconstruction proved the sent field set was exactly `goldTierId` present
  as `143878`, `policy` present as `Singapore`, `anzsic` omitted,
  `groupCompanyName` omitted, and zero empty fields. This matches the XPI guideline
  minimum and current matrix; the Postman four-field body remains an example, and the
  standalone OpenAPI is the separate EDS dialect.
- Read-only task detail showed `KYC Edit Pool`, "This amendment was automatically generated
  by the API", and "Amendment requires a KYC user". Both dependency tables contained zero
  items; audit Reason/Output were blank. Because no failed field, rule, policy-state
  prerequisite, ANZSIC/GCN requirement, or no-application guarantee is exposed, the exact
  diagnosis is `E. INSUFFICIENT_EVIDENCE`. No local mapper remediation was performed.
- Final focused verification after the ledger-failure slice passed 161 backend tests
  across the XPI sandbox, Phase-12 persistence, Garden fixture, and provider-sandbox API
  files; Ruff; strict configured mypy over 108 source files; frontend typecheck; and the
  focused frontend sandbox suite (5/5). Architecture, project-state, policy-authority,
  external-provider-readiness, secret, diff, and task-owned whitespace checks passed.
  The final separate-process retained-Mongo check again reported zero network calls and
  restart recovery PASS. The complete expensive matrix and independent Quality Gate were
  intentionally not run because this diagnosis-only task found no authorized external
  continuation or local mapping defect.
- No Mock fallback, local commit, push, PR, or merge occurred. Candidate freeze and the
  requested fresh independent Quality Gate were not reached because the external Amend
  failed.

## 2026-09-27 authenticated-portal recovery continuation (historical checkpoint)

- Codex accessed the human's already-authenticated Delta Capita portal session without
  inspecting credentials, cookies, authorization headers, browser storage, or unrelated
  customer records. The visible environment was `anz-nutmeg`.
- The only Garden Search result and its overview bind GoldTier ID `143878`, legal name
  `GARDEN BUSINESS`, UEN `11111999A`, legal country Singapore, entity type `Shell
  Record`, and KYC Customer Type `Partnership - Unregulated`.
- The record exposes one DSD external-system cross-reference. Its opaque external ID was
  inspected only for case linkage and is not reproduced in tracked evidence.
- Customer audit contains one `Requested` event at 21:45:48 by the API-connect user.
  Lifecycle status audit contains no items. Policy rows were scaffolded at 21:45:49;
  Singapore is present, but policy status is blank and all request flags are unset.
  This is consistent with shell creation and is not proof of an application Policy or
  Amend call. Registration type and booking entity were not independently visible.
- Recovery classification is `EXACT_RECOVERY_PROVED`: ID, legal name, and UEN match,
  with Singapore, DSD, shell state, and aligned audit time as additional evidence.
- The original target ledger cannot be recovered. The ignored acceptance harness used
  the default `InMemoryTargetExecutionRepository`, exited immediately on the uncertain
  Shell, and its own prior evidence states that only a sanitized attempted/completed
  prefix survived. There is no durable checkpoint to transition idempotently.
- No Shell replay, direct storage edit, manual ID substitution, Policy, Amend, read-back,
  or second Garden onboarding occurred. The user-authorized GoldTier-first orchestration
  remains unimplemented; current source continues to acquire ACRA before Search.

## 2026-09-27 final completion continuation

- Sponsor reconciliation established the corrected standalone OpenAPI 1.0.0 as the
  current machine-vocabulary owner: 17 KYC Customer Types and 23 Client Segments.
  Older conflicting lists remain quarantined.
- Current source maps Singapore UEN unchanged with `registrationType=ACRA`, both
  country fields `SG`, `DSD`, `Singapore`, and `ANZBGL (Singapore Branch)`. The four
  fixed values are closed against global drift.
- KYC Customer Type and Client Segment now use a backend-owned allowed vocabulary plus
  a validated write-once case selection retained as `USER_AUTHORIZED_POC`. The owning
  lock reauthorizes the case mutation; the UI renders backend options only while the
  decision is unresolved/editable.
- Sandbox target execution adds a ledger-owned post-Amend Search by retained
  `goldTierID`. Local adverse tests reject no match, wrong ID, and multiple matches and
  prove completed outcomes do not replay.
- Garden official-Mock evidence establishes legal form `PARTNERSHIP`, address and four
  owner/officer records, but not regulated status, shareholders, or a compatible
  capital denominator. SIM LIM evidence remains fragmented and cannot support an
  ownership percentage. No ownership fact was invented.
- Current local evidence: Ruff passes; strict mypy passes 108 source files; frontend
  typecheck passes; the complete frontend suite passes 291 tests across 24 files. The
  affected backend subset passes. The complete repository-defined backend suite exits
  zero and reaches 100%; a separate current-candidate collection records 1,392 tests.
  The later bounded external result is recorded separately below.
- The canonical POC regression selection passes across onboarding, resilience,
  document, ownership, CLM, zero-touch, UAT, jurisdiction, registry-acquisition,
  reconciliation, workspace, and persistence modules. The focused ACRA/XPI/sandbox-
  console/RBAC integration-security selection also passes.
- A physical disposable Mongo 7 run passed all 35 tests across the nine selected
  persistence suites. The localhost-only disposable container was stopped and removed;
  no project database or URI was printed or used.
- The isolated browser lifecycle passes all 14 configured Playwright tests after the
  required host-permission rerun. Its first sandboxed attempt was invalid because Vite's
  esbuild child process was denied with `EPERM`; that attempt is not passing evidence.
- A sanitized fresh settings/composition check confirms the ignored local `.env` selects
  ACRA `api_marketplace_mock` and GoldTier `sandbox`, host
  `portal.gt.deltacapita.net`, environment `anz-nutmeg`, 10-second timeout, 131072-byte
  response limit, writes enabled, and a present backend-only user identifier. The
  composed target connector is `GoldTierXpiSandboxConnector` with the XPI mapper.
- The stale console screenshot's reproducible cause is the explicit synthetic demo
  launcher override to ACRA/GoldTier `mock`. That launcher is labelled Mock and remains
  isolated test/demo infrastructure. The corrected status projection now requires both
  Sandbox settings and the actually composed Sandbox target provider, while the intended
  `.env` process composes Sandbox. The later acceptance run exercised that corrected
  status and diagnostic projection before its ledger-owned mutation attempt.

## 2026-09-27 bounded external acceptance result

- The human authorized Garden-only `Partnership - Unregulated` and
  `Commercial SBB (Small Business Banking)` with authority `USER_AUTHORIZED_POC`.
  They remain write-once case selections, not global defaults or ACRA-derived facts.
- The first guarded harness attempt failed reproducibly at case classification because
  the harness initially used the legacy policy-snapshot provider. A read-only staged
  rerun proved the failure occurred before target preparation, ledger reservation, or
  mutation. The harness was corrected to use the same policy-management snapshot owner
  as application composition; no product source changed for this harness defect.
- Corrected read-only preflight passed. The HR console API reported configured
  `SANDBOX / SANDBOX_PARTIAL`, safe host `portal.gt.deltacapita.net`, writes enabled,
  10-second timeout, 131072-byte response bound, an updated diagnostic timeline, and a
  dispatch-ready Search/Shell/Policy/Amend/Readback preview. The immediately preceding
  case Search returned `NO_MATCH / 0`.
- The authorized ledger run retained Search as definitively complete, attempted exactly
  one Shell, and received an uncertain mutation outcome. Its ledger prefix was attempted
  `SEARCH, SHELL` and definitively completed `SEARCH`; automatic replay was stopped.
- A subsequent read-only duplicate Search changed from the prior `NO_MATCH` results to
  exactly one `GARDEN BUSINESS` candidate with GoldTier ID `143878`. An ID-based Search
  returned the same ID and legal name. Both responses omitted registration number,
  country, and address, so the existing resolver truthfully returned
  `REVIEW_REQUIRED`/insufficient API identity rather than an exact reusable match. The
  later authenticated-portal continuation at the top of this record supersedes only
  that identity-evidence limitation; it does not restore the exited in-memory ledger.
- No second Shell, Policy, or Amend request was sent. The uncertain Shell ledger was
  process-local and its attempted/completed prefix is retained only as sanitized task
  evidence; the run did not claim a Shell-returned ID or completed lifecycle.
- At that historical checkpoint, the authorized portal tab was at the login screen
  with no active session or autofilled credential. The later authenticated-portal
  continuation at the top of this record supersedes that availability result. In both
  checks, no password or browser-session material was read, printed, or persisted.

## Baseline and contract evidence

- Git preflight matched the required branch, exact HEAD/origin-main/merge-base, and
  clean state.
- `.env` is ignored/untracked; `private/sponsor-artifacts-v2` is covered by the narrow
  existing `private/` ignore and is untracked.
- The private XPI PDF and collection SHA-256 values match the current tracked
  reconciliation record.
- Safe inspection confirmed the six XPI routes, `noauth` collection metadata,
  `Content-Type` and backend-only `user_id` header names, fixed host/environment, and
  empty sample `accountEntityType`/`productType` values.
- The guide supplies operation minimum categories and generic `200/400/500` guidance;
  the collection contains no saved response examples. Non-empty response decoding and
  errors must therefore remain strict, bounded, sanitized, and evidence-driven.

## Implementation and external evidence

- The local ignored `.env` selects `api_marketplace_mock` for ACRA and `sandbox` for
  GoldTier; the configured XPI host/environment and safety bounds validate through
  `Settings`. Existing ACRA credentials were preserved and never printed.
- Two 2026-09-27 read-only Searches ran through the configured application service and
  actual XPI connector. Both returned `NO_MATCH`, zero retained candidates, and no
  Mock fallback. The restricted-network attempt failed before reaching the provider;
  the approved unsandboxed runs produced the retained results.
- At that historical checkpoint, the duplicate Search returned no match and preparation
  stopped before reservation or mutation. The later final-completion continuation at
  the top of this record supersedes its then-unresolved mapping conclusions.
- Focused backend XPI/pipeline/registry suites pass. Frontend typecheck and the focused
  pipeline-inspector suite pass; the latter required an approved unsandboxed run because
  sandboxed esbuild process creation returned `EPERM`.
- The backend now projects ordered safe pipeline nodes; the frontend renders those nodes
  as a collapsed semantic decision tree and retains raw-free tables under a second
  collapsed technical-details disclosure.
- The final full backend pytest suite passed after ordinary-test settings were made
  explicitly Mock-isolated from the configured sandbox `.env`; Ruff passed for `app`
  and `tests`, and mypy passed for all 108 backend source files.
- The final frontend suite passed 286 tests across 23 files; TypeScript typecheck and
  the production Vite build passed. The isolated authenticated local-Mock Playwright
  regression passed all 14 configured tests. These browser tests prove local UI/runtime
  regression only and are not external-provider or portal evidence.
- Project-state, architecture, external-provider-readiness, policy-authority, and secret
  checks passed. The GoldTier example classifier completed with 19 `VALID`, 19
  `INVALID / QUARANTINED`, and 48 `NOT_VALIDATED`; quarantined and unvalidated material
  was not promoted into runtime mappings, DTO vocabulary, fixtures, or assertions.
- `git diff --check` passed for tracked changes. The ignored `.env` and `private/`
  sponsor artefacts are not tracked, and no credential, raw provider response, browser
  session, or portal secret was added to the candidate.

This section records the earlier candidate checkpoint and does not claim later
customer/read-back/portal success or a final independent gate. Current status is in the
final-completion continuation above.

## 2026-09-27 Singapore continuation evidence

- This historical continuation used the then-current UEN interpretation. It is
  superseded by D-056 and the corrected OpenAPI mapping `registrationType=ACRA` with
  unchanged UEN as `registrationNumber`.
- The sponsor collection's source-system value `DSD` is independent of registration
  identity and is labelled `SPONSOR_EXAMPLE`. It is not presented as ACRA evidence or
  sponsor-approved production policy.
- Australia-specific customer/policy/booking examples were not promoted. The remaining
  dispatch blockers are exactly `kycCustomerType`, `clientSegment`, `policy`, and
  `bookingEntity`.
- The official ACRA Mock returned four SIM LIM shareholder records with share counts,
  but no same-UEN entity profile and no compatible same-UEN capital denominator. No
  percentage, relationship, or canonical root was inferred from the fragmented samples.
- A fresh configured application-service XPI Search for the official-Mock Garden SG
  identity returned `NO_MATCH / 0`, with no target ID and no fallback. No target ledger
  row, Shell, Policy, Amend, related-party request, or read-back was attempted after the
  prerequisite check failed.
- The inspector now appends an explicit unresolved human-approval node after the target
  path, and the technical timeline renders backend event codes rather than retained
  free-text messages. Focused backend tests passed 127 cases; the focused frontend
  inspector suite passed five cases and typecheck passed.
- Final continuation verification passed with the repository-defined root/venv command:
  backend `1,353 passed / 35 skipped` with four known warning groups; Ruff passed;
  strict mypy passed 108 source files;
  frontend passed 288 tests across 23 files, typecheck, and the production build with
  116 transformed modules; contract tests passed 44; the supported non-contract
  repository suite passed 275; and all 14 isolated Playwright lifecycles passed.
- Architecture, project-state, external-provider-readiness, policy-authority, tooling,
  and secret checks passed. The GoldTier example classifier remained at 19 `VALID`,
  19 `INVALID / QUARANTINED`, and 48 `NOT_VALIDATED`. `git diff --check` passed. The
  initial raw repository-root pytest and sandboxed process/temp runs were invalid runner
  attempts; their supported entry points and required host-permission reruns passed.
- The fresh Singapore-continuation Quality Gate returned `FAIL` for the unmet external
  lifecycle acceptance, not for a runtime defect. It found no implementation,
  architecture, or security defect and kept QG-01/QG-02/QG-03 closed. Its sole local
  finding, QG-SG-01 (Low), proved that the reconciliation prose said six Searches and
  “last two” while the table and chronology show seven total and three configured-service
  Searches on 2026-09-27. The prose is corrected at its owning record; changed reviewed
  content requires a fresh independent re-gate. All five direct architecture/state/
  readiness/authority/secret checks passed after the correction, as did the 66 focused
  governance regression tests and `git diff --check`.
- QG-SG-02 reproduced and is closed as evidence accounting, not product behavior. The
  earlier `1,401 / 35` result came from a non-canonical system-Python environment with
  Pydantic 2.13.5 and 48 additional generated schema cases. The repository-defined
  `.venv` (Pydantic 2.13.4, clean `pip check`) collects 1,388 cases and passes exactly
  `1,353 / 35`; both working directories produce the same canonical collection.
- Closeout structural tooling did not produce a bundle: this Markdown-only work record
  has no helper-generated `task-intent-draft.json`. The workspace-wide helper check also
  reports pre-existing unindexed historical Markdown and two pre-existing advisory-value
  incompatibilities in the 2026-09-23 work record. These are structural/process-tooling
  limitations, not product-test or external-provider evidence, and were not changed in
  this task.

## Independent-gate chronology and remediation

- The first fresh independent gate wrote
  `.ai-pipeline/reports/FINAL_PRE_PHASE22_EXTERNAL_PROVIDER_POC_QUALITY_GATE.md` and
  returned `FAIL`. It confirmed the external acceptance blocker and found QG-01: the
  projector inserted the v2 early-Search node into historical v1 execution order.
- QG-01 was remediated without changing persistence facts or frontend ownership. V1
  Search now remains within the historical target sequence, while v2 retains the early
  Search node. Backend and frontend tests explicitly cover both versions.
- Post-remediation focused backend tests passed; the full backend suite passed; Ruff
  passed on the changed backend files. The focused frontend inspector suite passed four
  tests, the full frontend suite passed 287 tests across 23 files, typecheck passed,
  and the production build passed with 116 modules transformed.
- These fixes do not alter the external blocker or supply missing Shell, Policy, Amend,
  retained-ID, read-back, or portal evidence. A fresh independent re-gate is required
  for the changed candidate.
- The first fresh re-gate wrote
  `.ai-pipeline/reports/FINAL_PRE_PHASE22_EXTERNAL_PROVIDER_POC_REQUALITY_GATE.md`,
  verified QG-01 closed, and returned `FAIL` for the external criteria plus QG-02. It
  reproduced an active checkpoint-absent Search as incorrectly `NOT_REACHED`.
- QG-02 was fixed at the projector owner by using the existing automation-stage status
  only while Search is current, checkpoint-absent, and transport evidence remains
  `NOT_ATTEMPTED`. Focused regression covers `IN_PROGRESS`, `REVIEW_REQUIRED`,
  `BLOCKED`, and `FAILED`; 76 focused Garden/XPI backend tests, Ruff, and mypy pass.
- A second fresh independent re-gate is required. No external operation was repeated,
  and no new customer, ledger row, provider write, or portal action occurred.
- Before that final re-gate, an adversarial read found that the top-level Search node
  could display an ID later created by Shell after a no-match. The candidate was not
  reviewed while moving. The projector now exposes a Search ID only for an exact-match
  checkpoint, and the completed no-match Garden regression proves the ID is absent from
  Search but present on the target path. The same 76-test focused suite, Ruff, and mypy
  pass after this correction.
- The next fresh re-gate verified QG-01, QG-02, and ID provenance, then found QG-03:
  checkpoint-absent Search still emitted `Search not reached` and no timestamp even
  when status was active/review/blocked/failed and a CLM Search event existed.
- QG-03 is fixed as a full pre-checkpoint view, not a text-only patch. The projector
  uses the CLM Search event timestamp, status-appropriate safe result, existing stage
  exception code, no candidate count, and no ID until a checkpoint supplies result
  facts. The focused 76-test suite, Ruff, and mypy pass after the repair.

## Post-mutation gate and remediation

- The fresh independent post-mutation gate wrote
  `.ai-pipeline/reports/FINAL_PRE_PHASE22_EXTERNAL_PROVIDER_POC_POST_MUTATION_QUALITY_GATE.md`
  and returned `FAIL` for the incomplete external lifecycle plus two local findings.
- QG-PM-01 (High) found that the integration reconciliation still said no Shell had
  been sent. The owning record now states exactly one uncertain Shell attempt,
  attempted `SEARCH, SHELL` versus definitively completed `SEARCH`, no replay, later
  read-only discovery of ID `143878`, incomplete identity, and no Policy, Amend,
  post-Amend read-back, or portal verification.
- QG-PM-02 (Medium) reproduced an editable classification projection for a legacy case
  with no GoldTier target policy. `BrowserTargetClassification.from_case()` now
  requires an applicable target policy before marking the projection editable. A
  regression test covers the legacy/no-target snapshot; the existing frontend test
  confirms non-editable unresolved projections expose no form.
- Focused backend regression passed three tests. Ruff passed. The focused frontend
  panel suite passed three tests after the sandboxed esbuild attempt returned `EPERM`
  and the approved host-permission rerun succeeded. `git diff --check` passed. The
  direct per-file mypy attempt included a test module outside the repository's mypy
  target and produced pre-existing test-typing diagnostics; it is not passing evidence.
- These remediations do not resolve the external blocker and do not authorize a Shell
  replay. Changed candidate content requires a fresh independent re-gate.
- That re-gate closed QG-PM-01 and QG-PM-02, then found QG-PM-RQ-01 (High): active
  checkpoint/reflection sections still contained superseded statements that selection
  was pending, no Shell had been sent, and mandatory vocabulary was missing. The
  current-status sections now consistently record the authorized selections, one
  uncertain Shell attempt, no replay, and the exact-identity recovery requirement.
  Historical pre-selection evidence is explicitly labelled superseded. Focused tests,
  Ruff, `git diff --check`, and Markdown whitespace/final-LF checks pass after repair.

## 2026-09-28 local continuation evidence

- Sanitized runtime preflight selected `api_marketplace_mock` and composed
  `AcraApiMarketplaceMockConnector`; both dedicated credential fields were present.
  The intended Mongo profile was reachable. No secret, URI, authorization header, raw
  payload, or portal session value was printed or retained.
- Direct official Mock smoke: Garden entity basic `200 / GARDEN BUSINESS / identity
  match`; Garden shareholders `200 / EMPTY / 0`; SIM LIM shareholders `success / 4`;
  separate capital sample `success / observed-only`. No ownership percentage was
  derived, and the smoke has no local-provider fallback path.
- Focused diagnostic/provider tests pass `15/15`. Focused frontend progress, registry,
  and App tests pass `69/69`; TypeScript typecheck passes. These are local workstream
  results and do not change the retained GoldTier external acceptance blocker.
- No GoldTier Search or mutation was needed for this continuation, and none was sent.

### Independent local gate remediation

- The first independent report,
  `.ai-pipeline/reports/FINAL_PRE_PHASE22_LOCAL_CONTINUATION_QUALITY_GATE.md`, returned
  `PASS WITH MINOR FIXES` with one Low finding, QG-LC-01. The legacy rail, queue
  position, and completed-stage table still used a fixed five-stage order that could
  contradict backend v2 ordering.
- Remediation removed the fixed stage-band owner. The rail and completed-stage table
  now preserve the exact backend `processing_pipeline` order and statuses. The queue
  presents its backend current stage without inventing an ordinal. Older responses
  without a pipeline show an explicit absence message rather than a fabricated record.
- Focused remediation verification: `60/60` frontend tests and TypeScript typecheck
  pass. Full frontend verification: `302/302` tests and the production build pass
  (`117` modules). The complete isolated Playwright suite passes `16/16`, including
  live backend-stage advancement and Garden partial-registry presentation.
- `git diff --check` must be refreshed after this evidence update. A fresh independent
  re-gate is still required; this section does not self-certify exact PASS.
