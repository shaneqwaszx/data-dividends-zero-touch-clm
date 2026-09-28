# Final Pre-Phase-22 External Provider POC Re-Quality Gate

## Executive Result

**FAIL**

The first-gate historical-v1 ordering defect, QG-01, is fixed on the frozen
candidate: v1 records omit the top-level early Search and retain Search under the
historical target sequence, while v2 records keep the early Search and omit the
duplicate target Search. Independent focused, broad, browser, type, build,
security, and governance checks pass on this remediated identity.

The whole assignment nevertheless remains incomplete. No GoldTier sandbox customer
was created or safely reused, no Shell/Policy/Amend result exists, no GoldTier ID was
retained, no real read-back found that same customer/ID, and no portal customer was
verified. The implementation stopped correctly before ledger reservation or network
mutation because the canonical route is Singapore/UEN-only while the only supplied
bounded mutation vocabulary is Australian `ABN`. Inventing a UEN-to-ABN mapping or an
Australian registry route is forbidden; this is a genuine external/authority blocker,
not a code pass.

The re-gate also found one new, reproducible local inspector defect, QG-02: while an
early GoldTier Search is actively running but has not produced its checkpoint, the
backend projects the Search node as `NOT_REACHED` rather than `IN_PROGRESS`. Criterion
10 therefore remains failed independently of the external blocker.

## Final Acceptance Checklist

| # | Acceptance criterion | Result | Direct evidence |
|---:|---|---|---|
| 1 | `.env` selects official ACRA API Marketplace Mock | PASS | Sanitized candidate evidence records `api_marketplace_mock`; `.env` is ignored/untracked. This reviewer did not read `.env`. |
| 2 | `.env` selects actual GoldTier XPI Sandbox | PASS | Sanitized candidate evidence records explicit `sandbox` selection with the configured XPI host/environment and validated safety bounds. This reviewer did not read `.env`. |
| 3 | Real GoldTier Search succeeds through the application connector | PASS | Sanitized retained evidence records two configured application-service/XPI connector Searches on 2026-09-27, both `NO_MATCH / 0`, against the authorized `anz-nutmeg` sandbox. External network use was prohibited in this re-gate. |
| 4 | Configured POC runtime does not use local GoldTier Mock | PASS | Explicit sandbox composition, no-fallback implementation/tests, and sanitized runtime evidence show no local-Mock use. Ordinary tests explicitly isolate themselves to Mock rather than inheriting local runtime settings. |
| 5 | One bounded sandbox customer is created, or an exact prior test customer is safely reused | **FAIL** | The exact duplicate Search returned no match; execution stopped before ledger reservation or mutation. No customer was created or reused. |
| 6 | Shell/Policy/Amend results are externally observed as applicable | **FAIL** | No Shell, Policy, or Amend request was sent, so no external operation result exists. |
| 7 | Returned GoldTier ID is retained by the target ledger | **FAIL** | No exact match or mutation returned an ID; no target-ledger reservation occurred. |
| 8 | Subsequent real Search finds the same customer/ID | **FAIL** | There is no created/reused customer or retained ID to read back. |
| 9 | Portal visibly shows the sandbox customer if technically available | **FAIL** | The implementation session had portal capability, but no created/reused customer existed to locate. No portal-visible customer evidence exists. |
| 10 | Decision-tree pipeline inspector works | **FAIL** | QG-01 is fixed and v1/v2 ordering is independently tested, but QG-02 reproduces an active `GOLDTIER_SEARCH / RUNNING` state projected as `NOT_REACHED`. The inspector is therefore not truthful for every required state. |
| 11 | Garden remains truthful | PASS | Retained official-Mock evidence records `REVIEW_REQUIRED / PARTIAL`, zero shareholders and relationships, and no synthetic ownership fallback. |
| 12 | No synthetic provider fallback | PASS | Composition and failure behavior remain explicit and fail closed. No XPI-to-Mock or official-ACRA-Mock-to-local-Mock downgrade was found. |
| 13 | Secret scan passes | PASS | Independent `scripts/check_secrets.py` passed. `.env` and private sponsor artefacts were not opened; no credential, raw provider response, or session material is in the candidate. |
| 14 | Independent Quality Gate PASS | **FAIL** | This fresh independent re-Quality Gate verdict is `FAIL`. |

## First-Gate Finding Disposition

### QG-01 — historical v1 pipeline order — FIXED

`project_processing_pipeline()` now imports the canonical legacy stage-order version,
omits the top-level early Search for v1, keeps Search as the first child of the legacy
target sequence, and retains the top-level Search without a duplicate target child for
v2. The backend v1 projection assertion and v2 no-match branch assertion pass. The
frontend v1 test verifies that it renders the exact server-provided order.

Independent evidence:

- focused backend Garden/XPI suite: **72 passed**;
- focused frontend inspector suite: **4 passed**;
- direct source inspection of `apps/backend/app/api_models.py:1157` and
  `apps/backend/app/api_models.py:1313` confirms the two versioned projections.

QG-01 is closed for this frozen identity. It is not a basis for an overall PASS because
the external criteria remain unmet and QG-02 remains open.

## Contract and Integration Findings

### Current acceptance blockers

1. **External customer lifecycle is unproved.** Search-only interoperability does not
   establish customer creation/reuse, Shell/Policy/Amend behavior, retained target ID,
   read-back, or portal visibility.
2. **Registration mapping/jurisdiction authority is genuinely missing.** The current
   canonical application route admits Singapore/UEN. The bounded collection example
   supplies Australian `ABN`. The candidate correctly refused to relabel a UEN, add an
   unauthorized Australian registry route, or bypass the ledger. Sponsor-controlled
   Singapore registration vocabulary, or separately authorized non-Singapore canonical
   and registry scope, is required before mutation.

### Verified contract behavior

- `accountEntityType` and `productType` are compatibility-optional only for the bounded
  XPI sandbox policy request. Unconfirmed placeholders serialize as explicit empty
  strings; explicit sponsor-supplied or sandbox-observed non-empty values may pass.
- The other six target-policy values remain fail-closed prerequisites.
- XPI remains explicit `SANDBOX_PARTIAL` behind the existing mapper, connector,
  entity-resolution, CLM-plan, and ledger owners. Mock is retained for isolated tests
  and as the repository default, never as sandbox failure recovery.
- Search remains bounded and safe-projected. A no-match response is not upgraded into
  customer mutation, approval, Production, or Live evidence.
- Official ACRA API Marketplace Mock remains Mock. Garden's empty ownership evidence
  remains partial and does not acquire the local synthetic Garden chain.
- No direct ACRA-to-GoldTier mapping, second target ledger, provider fallback, or
  related-party/hierarchy expansion was found.

## Tester and Adversarial Findings

### Independently executed on the frozen candidate

- Focused backend:
  `pytest -p no:cacheprovider test_goldtier_xpi_sandbox.py test_garden_business_fixture.py`
  — **72 passed**, one dependency warning.
- Full backend: `pytest -p no:cacheprovider apps/backend/tests` — **1,347 passed,
  35 skipped**, four warnings. Skips are not represented as physical or external passes.
- Ruff for backend application/tests plus repository scripts/tests with `--no-cache`
  — **PASS**.
- mypy for `apps/backend/app` with `--no-incremental` — **PASS**, 108 source files.
- Focused frontend inspector suite — **4 passed**.
- Full frontend — **287 passed across 23 files**; existing React test warnings did not
  fail the suite.
- Frontend typecheck — **PASS**.
- Frontend production build to a temporary directory — **PASS**, 116 modules transformed.
- Guarded authenticated local-Mock Playwright: the first full attempt passed scenarios
  1–3, then scenario 4 timed out with a review button disabled. An isolated rerun of
  that exact scenario passed in 4.6 seconds; the subsequent complete inventory passed
  **14/14** in isolated lifecycles. The initial failure is classified as non-reproducible
  timing evidence, not erased. This remains local Mock/browser evidence only.
- `check_project_state.py`, `check_architecture.py`,
  `check_external_provider_readiness.py`, `check_policy_authority.py`, and
  `check_secrets.py` — **PASS**.
- `git diff --check HEAD` — **PASS**. Explicit trailing-whitespace/final-newline checks
  for all four task-owned untracked Markdown records — **PASS**.

Physical Mongo was not run because this candidate changes no persistence schema,
repository semantics, CAS/index behavior, or driver-dependent boundary. The uncommitted
publication gate `pre_pr_check.py` was not run. This re-gate used no external network,
portal/browser account, `.env`, credential, or private sponsor artefact.

### QG-02 — Medium — active early Search is projected as not reached

`project_processing_pipeline()` derives the early Search status only from
`BrowserTargetOperationEvidence` (`apps/backend/app/api_models.py:1055-1061`). Before a
Search checkpoint exists, that evidence defaults to `NOT_ATTEMPTED`, which maps to
`NOT_REACHED`, even when the automation record is `RUNNING` with
`current_stage == GOLDTIER_SEARCH`.

A read-only adversarial projection reproduced:

```text
current_stage=GOLDTIER_SEARCH automation_status=RUNNING projected_search_status=NOT_REACHED
```

This state is reachable while the CLM service has persisted its Search-start event and
the external connector call has not yet produced a checkpoint. The inspector therefore
temporarily falsifies actual backend execution and does not satisfy the required
`IN_PROGRESS` state. Remediation must derive the checkpoint-absent active Search status
from authoritative automation stage/status without inferring success, then cover the
state directly in backend/API tests. No fix was made by this reviewer.

No second reproducible code, contract, security, or adverse-path defect was found.

## Code and Architecture Review

- The v1/v2 remediation preserves persistence truth and uses the existing persisted
  stage-order version; it does not rewrite historical records.
- Backend API projection remains the processing-tree owner. The frontend recursively
  renders server order/status and does not reconstruct business state.
- The safe recursive DTO is bounded, strict, and excludes raw payloads, credentials,
  document content, endpoints, sessions, and internal exceptions.
- Optional XPI policy-field handling is narrow: it does not relax the other six
  dispatch prerequisites or promote example vocabulary into policy authority.
- No repository, schema, cache, authorization, entity-resolution, provider-router,
  target-ledger, framework, or dependency-direction owner was added or replaced.
- No unrelated dependency, lockfile, generated-file, jurisdiction, or persistence
  change is present.

Change-impact statement for this candidate:

- API/type: **changed** — safe stage-order version and recursive processing projection.
- Durable schema/persistence: **unchanged**.
- Connector contract: **changed narrowly** — two XPI sandbox policy fields accept and
  serialize explicit empty strings.
- Tracked configuration: **unchanged**; ignored local runtime configuration is reported
  only through sanitized evidence.
- Business rule/mapping: **changed narrowly** for sandbox-only optional-field handling;
  no Singapore registration mapping was invented.
- Auth/security boundary: **unchanged**.
- Architecture ownership: **unchanged**; current documentation was reconciled.
- Provider classification: **unchanged** — ACRA Marketplace remains Mock and XPI
  remains Sandbox/Partial.
- Runtime behavior: **changed** — backend-authored processing tree plus optional-field
  request projection; no external mutation behavior was proved.

## Security Review

No active security defect was found in the reviewed delta.

- XPI transport remains HTTPS-only, certificate-verified, TLS-1.3-only,
  redirect-disabled, time/body bounded, and safely error-projected.
- The backend-only `user_id` transport identity is not exposed in the new API/UI
  projection.
- Pipeline fields are bounded to safe provider/environment/operation/stage/status,
  timestamps/counts/codes, safe summaries, and an appropriate retained target ID.
- `.env` and private sponsor artefacts remain ignored and untracked. The reviewer did
  not open them. No new sensitive file is staged or tracked.
- The independent secret scan passed. It does not substitute for production secret
  governance, credential rotation, or external authorization.

Production PingFed/authentication, Live GoldTier, Ready-for-Approval, retention, and
related-party child-ID/relationship semantics remain unresolved later dependencies,
not current security successes.

## Required Blockers and Later Dependencies

### Required current acceptance work

1. Fix QG-02 so an actively running checkpoint-absent early Search projects
   `IN_PROGRESS`, with focused backend/API coverage and proportional frontend checks.
2. Obtain authoritative Singapore XPI registration type/value mapping, or explicit
   authority for a separate non-Singapore canonical registry route. Do not infer either.
3. After authority exists, repeat the exact duplicate Search and perform at most one
   ledger-owned synthetic Shell -> Policy -> Amend run; retain the returned ID; execute
   real read-back Search; and verify the same sandbox customer in the portal with
   sanitized evidence.
4. Freeze the changed candidate and obtain another fresh independent re-Quality Gate.
   Exact `PASS` remains mandatory.

### Later dependencies, not current fixes

- related-party `childId` lifecycle and relationship vocabulary;
- production PingFed/authentication, Live classification, and deployment/handoff;
- Ready-for-Approval, four-eyes, final approval, and retention authority;
- sponsor-approved production target vocabularies beyond this bounded sandbox task.

## Readiness

- **Final pre-Phase-22 task completion:** NOT READY.
- **Phase 22 readiness:** NOT READY; this report grants no next-phase authorization.
- **GoldTier XPI Search interoperability:** observed only for bounded no-match Search.
- **GoldTier customer mutation/read-back/portal proof:** NOT PROVED.
- **Live ACRA or Live GoldTier:** NOT PROVED and not claimed.
- **Publication/PR readiness:** NOT READY. Exact independent `PASS` is absent, the
  candidate remains uncommitted, and publication was not authorized.

## Git Status and Frozen Reviewed Identity

- Repository: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`
- Branch: `feat/goldtier-sandbox-pipeline-inspector`
- `BASE_SHA = HEAD = origin/main = 463ecdcb4357bb44618cdd5b277671766543dbfc`
- Staged files: none.
- Reviewed tracked delta: 22 modified files; deterministic
  `git diff --binary HEAD | git hash-object --stdin` identity
  `7e9124752c2d89cd7f0b3a7a27585ffa9788432f`.
- Reviewed task-owned untracked files:
  - `10-intent.md` — `DC9568BA6645C13D2C4E55B960A350C9EB67CFC4D5E62C2610B92BE8AE6828EC`
  - `20-checkpoint.md` — `BF92A3898A28E88CA363119029307C36870955F4E64152BDAC7478D7A2045B07`
  - `90-evidence.md` — `E7F05F41E8218DD4567FB5A9038062228E4DE871225110B97B9519F25371FB41`
  - `99-reflection.md` — `425AEC0F60F25552E462C93ABEE8D48B3A40A6454C8C4F821D764C17243F6C0C`
- Complete tracked path set:
  - backend application: `api_models.py`, `connectors/goldtier_xpi_models.py`,
    `domain/policy.py`, `main.py`, `mappers/goldtier_xpi.py`, and
    `services/policy_management.py`;
  - backend tests: `phase13_test_settings.py`, `test_garden_business_fixture.py`, and
    `test_goldtier_xpi_sandbox.py`;
  - frontend: `App.test.tsx`, `GoldTierSandbox.test.tsx`,
    `pages/CaseStatePanels.tsx`, `styles.css`, and `types.ts`;
  - documentation: `docs/ARCHITECTURE.md`, `docs/PROJECT_STATE.md`,
    `docs/aegis/INDEX.md`, `docs/contracts/POLICY_AUTHORITY_MATRIX.md`,
    `docs/decisions/ADR-004_GOLDTIER_XPI_SANDBOX_ADAPTER.md`,
    `docs/decisions/DECISION_LOG.md`,
    `docs/integration/GOLDTIER_XPI_MAPPING_MATRIX.md`, and
    `docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md`.
- The historical first-gate report is review input and excluded from candidate identity.
- This re-Quality Gate report is the reviewer's only intentional repository write and
  is excluded from candidate identity.

The frozen identity was verified before review and again immediately before writing
this report. The reviewer made no implementation, configuration, test, ordinary
documentation, stage, commit, branch, push, PR, merge, external-provider, portal, or
next-phase mutation. Any candidate-content change requires a fresh independent review.
