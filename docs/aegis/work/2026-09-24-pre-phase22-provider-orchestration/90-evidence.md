# Pre-Phase 22 provider orchestration and sandbox testing - Evidence

## Evidence boundary

- Current source revision: uncommitted candidate on
  `feature/pre-phase22-provider-orchestration`.
- BASE_SHA and accepted main: `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3`.
- Tested content: current working candidate including implementation report, except later
  evidence-only closeout wording which does not change business behavior.
- Independent review revision: not yet assigned; publication is blocked until exact
  candidate fingerprint and fresh `PASS`.

## Direct and regression evidence

- Backend: `1289 passed / 35 skipped`; three expected malformed-fixture warnings plus
  the TestClient deprecation warning.
- Frontend: `23 files / 286 tests`; TypeScript and production build passed, 116 modules.
- Browser: `14/14` configured isolated Playwright lifecycles passed before remediation;
  a fresh post-stage-order run also passed `14/14`.
- Static/dependency: the exact backend CI Ruff scope, strict Mypy over 106 files,
  TypeScript, production build, and `pip check` passed. Task-owned governance Python is
  covered by the 242-unit expanded matrix and direct checkers.
- Contracts/governance: 44 contracts, 4 delivery assets, and 242 scoped
  governance/security tests passed.
- Direct checkers: project state, architecture, tooling, policy authority, provider
  readiness, secrets, GoldTier examples, and whitespace passed. External-provider
  evidence schema/validator behavior is covered by the passing governance unit matrix;
  no unsupported external evidence record was manufactured.
- Intelligence: entity 17/17, UBO 3/3, mock risk 5/5 on bounded synthetic fixtures.
- Windows lifecycle: first full run 22/23 plus one pre-header loopback timeout; exact
  failing test passed 1/1; unchanged full rerun passed 23/23. A fresh post-remediation
  full run passed 23/23 and removed its owned processes. The post-stage-order run also
  passed 23/23 and removed its owned processes.
- Physical Mongo: missing infrastructure; Docker Linux daemon unavailable. No database
  URI was read or used.

## Provider evidence

- ACRA Marketplace Mock no-auth connectivity: observed bounded HTTP 401 JSON response;
  authentication required, exact scheme unresolved. No Live call and no mutation.
- GoldTier: no external write. Customer writes remain blocked by seven `TBD_SPONSOR`
  policy values; related-party writes are additionally blocked by child-ID lifecycle.
- HR console: read-only Search and offline dry-run are available; guarded standalone
  write is a typed zero-dispatch blocker because the case ledger is mandatory.

## Evidence slots

- Evidence action / check performed: focused provider/orchestration/RBAC/persistence/UI
  tests followed by complete backend/frontend/static/contract/governance/browser runs.
- Result / exit status: green except fresh physical Mongo unavailable; one retained
  intermittent Windows-loopback failure recovered in exact isolation and then in the
  unchanged complete suite.
- Covered scope: early Search, exact/no-match/ambiguous branches, incremental durable
  writes, no replay, official ACRA mode separation, COI profile, HR RBAC, cache scope,
  progress projection, governance truth, and accepted POC regressions.
- Uncovered scope: physical Mongo on this candidate; actual ACRA Marketplace
  authentication; GoldTier write interoperability; related-party child-ID lifecycle;
  production providers.
- Residual risk: bounded host lifecycle flake plus unexercised physical persistence and
  external mutation paths.
- Confidence grade: `B` pending the independent gate and publication CI.

## Complexity closure

- Budget status: `exceeded-and-governed`.
- Governed now: retained one canonical owner for Search, mutation ledger/no-replay,
  resolution, persistence, authorization, and frontend cache lifecycle; extracted the
  provider console and its cache owner into focused modules.
- Deferred follow-up: decompose the existing large onboarding/orchestration owners when
  a separately authorized architecture slice can preserve their invariants.
- Completion impact: `needs-verification` until exact independent gate and CI.

## First independent gate and remediation evidence

- Frozen fingerprint `70ee1102996ba8b9db26e7442e174c141e0b0518c9bf5ebd96cb5ab70ec41858`
  received `FAIL`; the report is preserved under the `_FAILED` suffix.
- PP22-QG-001: RED registry-only restart skipped Search; GREEN canonical transition,
  in-memory resume, and Mongo-codec checkpoint coverage.
- PP22-QG-002: RED Mock status exposed `SANDBOX_PARTIAL`; GREEN Mock/Mock with writes
  disabled and Sandbox/Sandbox Partial coverage.
- PP22-QG-003: RED console Search exposed `NOT_ASSESSED`; GREEN Search uses the existing
  resolver and returns `REVIEW_REQUIRED` for the bounded name-only fixture.
- Affected backend: 170/170; focused frontend: 3/3; post-repair full backend:
  1323 passed with 35 expected physical-only skips; full frontend: 23 files/285 tests;
  Ruff, Mypy, and TypeScript pass.
- Post-repair broad refresh: contracts 44/44, delivery assets 4/4,
  governance/security 159/159, synthetic entity/UBO/risk 17/17, 3/3, and 5/5,
  GoldTier examples 19 valid / 19 quarantined / 48 not validated, Playwright 14/14,
  and Windows lifecycle 23/23.
- Status: `needs-verification` pending one fresh independent gate against the new frozen
  fingerprint.

## Second independent gate and COI remediation evidence

- The re-gate closed the first three findings, then found PP22-RQG-001: missing optional
  COI address still became a reconciliation/document blocker. Its review-only report is
  preserved under the `_REQUALITY_GATE_FAILED` suffix.
- RED: the integrated journey stopped `WAITING_FOR_REVIEW` with
  `DOCUMENT_REQUIRED_FIELD_MISSING` after Search.
- GREEN: the same COI journey records `REGISTRY_ONLY` and completes; a supplied address
  mismatch remains `CONFLICT`; legacy required-address absence remains
  `MISSING_IN_SOURCE`.
- The additive durable requiredness flag defaults safe for legacy models, and a fresh
  adapter restart plus Mongo codec encode/decode preserves `REGISTRY_ONLY` without
  fabricating document evidence.
- Refreshed broad evidence passes backend `1327/35`, frontend `23 files/286 tests`,
  contracts `44/44`, delivery `4/4`, governance/security `159/159`, synthetic
  entity/UBO/risk `17/17`, `3/3`, and `5/5`, GoldTier `19/19/48`, Playwright `14/14`,
  and Windows lifecycle `23/23`.
- Status remains `needs-verification` pending a third fresh independent exact-content
  gate.

## Third independent gate and stage-order compatibility evidence

- The third gate matched 94 paths at fingerprint
  `130dd4bb51f98500aa3901b2582caa9ba661c8c46d429b44812471fed72a4f25`, closed all four
  prior findings, and returned `FAIL` on PP22-FQG-001. Its report is preserved under the
  `_FINAL_QUALITY_GATE_FAILED` suffix.
- The gate's decoder probe omitted the excluded persistence-only ownership binding, so
  its immediate rejection was not a valid raw Mongo reproduction. Canonical `_encode`
  evidence proves the exact base-v5 pending prefix decodes.
- The underlying continuation risk was real: a decoded pre-Search prefix could not be
  transitioned safely under the v2 prefix invariant. The repair persists an explicit
  automation stage-order version, interprets missing metadata as legacy v1 without
  mutating the raw input, and CAS-rebases only safe non-terminal continuation to the
  earliest unproved v2 stage.
- GREEN: raw base-v5 pending decode; pending and review continuation with Search before
  Shell/Policy/Amend; interrupted-document recovery without invented Search; legacy and
  current uncertain-target no-replay; historical terminal no-replay. Persistence passes
  53 tests, zero-touch/CLM passes 122, focused Ruff passes, and focused strict Mypy passes.
- Fresh broad evidence passes backend `1334/35`, frontend `23 files/286 tests`, contracts
  `44/44`, delivery `4/4`, expanded governance/security `242/242`, synthetic
  entity/UBO/risk `17/17`, `3/3`, and `5/5`, GoldTier `19/19/48`, Playwright `14/14`,
  and Windows lifecycle `23/23`; direct governance, secrets, dependencies, Ruff, Mypy,
  TypeScript, and production build also pass.
- Status remains `needs-verification` pending a fourth fresh independent exact-content
  gate.

## Fourth independent gate and durable decode evidence

- The fourth gate matched 95 paths at fingerprint
  `917df3133084f5e0326244047e19a889727e2d30da66b4c8054acbe92345418a`, closed all five
  prior findings, and returned `FAIL` on PP22-4QG-001. Its report is preserved under the
  `_FOURTH_QUALITY_GATE_FAILED` suffix.
- RED: canonical raw persistence representations with explicit current-v2/legacy-prefix,
  legacy-v1/current-prefix, and malformed current-v2 terminal combinations decoded
  without rejection.
- GREEN: `_decode` invokes the existing aggregate validator after schema conversion,
  strict model and unknown-field checks, and Mongo/envelope identity verification. The
  existing exception boundary converts failure to `PersistenceDataInvalidError`.
- Existing valid base-v5 legacy decode, unmodified raw input, CAS rebase before Search,
  terminal no-replay, and uncertain-target no-replay remain covered and passing.
- Persistence passes `56/56`; combined persistence/zero-touch/CLM passes `174/174`;
  focused Ruff and strict Mypy pass.
- Fresh broad evidence passes backend `1289/35`, frontend `23 files/286 tests`, contracts
  `44/44`, delivery `4/4`, governance/security `242/242`, synthetic entity/UBO/risk
  `17/17`, `3/3`, and `5/5`, GoldTier `19/19/48`, Playwright `14/14`, and canonical
  Windows lifecycle `23/23`. Static, dependency, direct-governance, secret, and
  whitespace checks pass.
- One invalid combined root discovery run is excluded: it used the wrong contract import
  context and encountered one retained pre-header lifecycle timeout. Canonical separated
  suites passed and all owned processes were removed.
- Physical Mongo remains unavailable because the Docker Linux daemon is absent. Status
  remains `needs-verification` pending a fifth fresh independent exact-content gate.

## Published-candidate CI remediation evidence

- Published commit `9c17fc0634ca23b019cb3aba2ff339519288c530` passed frontend,
  backend, security, E2E, and Windows lifecycle jobs in push run `36032038372`; the
  physical Mongo harness reported `31 passed / 4 failed`.
- The first remediation changed three zero-call assertions and one current-v2 uncertainty
  fixture, but the fresh independent gate correctly rejected treating those as four
  failed pytest items because two assertions share one test function. Its FAIL report is
  preserved as
  `PRE_PHASE22_PROVIDER_ORCHESTRATION_CI_REMEDIATION_QUALITY_GATE_FAILED.md`.
- The complete four-item mapping is: review-refresh call count; failed-replacement call
  count (with both sequential expectations retaining Search); current-v2 uncertainty
  prefix; and the three-case aggregate, where two Search calls plus Shell, Policy, and
  Amend produce five total GoldTier calls.
- The remediation is test-only. It does not change runtime code, schema, provider
  classification, mutation behavior, or replay policy.
- Focused persistence/zero-touch evidence passes `111/111`; the physical Phase 12 file
  collects all 15 tests; whitespace hygiene passes.
- Status: `needs-verification` pending a fresh exact-content independent quality gate and
  successful physical Mongo CI execution.
