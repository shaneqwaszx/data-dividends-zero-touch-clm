# Final Pre-Phase-22 External Provider POC Quality Gate

## Executive Result

**FAIL**

The candidate safely proves two real, read-only GoldTier XPI sandbox Searches through
the configured application connector, keeps the official ACRA API Marketplace Mock
truthful, preserves fail-closed provider composition, and passes the affected local
test/security/governance suites. It does not meet the assignment's end-to-end external
acceptance: no sandbox customer was created or safely reused, no Shell/Policy/Amend
result exists, no GoldTier ID was retained, no read-back found the same customer, and
no portal record could be verified. The run stopped correctly before ledger
reservation/network mutation because the canonical route is Singapore/UEN-only while
the supplied bounded mutation vocabulary provides `ABN`; inventing UEN-to-ABN mapping
or an Australian registry route is forbidden.

There is also one current inspector defect: the backend projector always inserts the
v2 early-Search node before Document even for a preserved `stage_order_version == 1`
historical record. That contradicts the canonical pre-Search v1 order and the explicit
requirement that the tree match actual backend execution ordering.

## Phase Acceptance Checklist

| # | Acceptance criterion | Result | Direct evidence |
|---:|---|---|---|
| 1 | `.env` selects official ACRA API Marketplace Mock | PASS | Sanitized task evidence records `api_marketplace_mock`; `.env` is ignored and untracked. The reviewer did not read `.env`, as required. |
| 2 | `.env` selects actual GoldTier XPI Sandbox | PASS | Sanitized task evidence records explicit `sandbox` selection and validated XPI settings; `.env` is ignored and untracked. The reviewer did not read it. |
| 3 | Real GoldTier Search succeeds through the application connector | PASS | Two 2026-09-27 configured `OnboardingService`/XPI connector Searches reached `portal.gt.deltacapita.net`, environment `anz-nutmeg`, and returned `NO_MATCH` with zero candidates. This is supplied sanitized external evidence; the independent gate was explicitly network-prohibited. |
| 4 | Configured POC runtime does not use local GoldTier Mock | PASS | Explicit sandbox composition, tests, and evidence show no Mock fallback; ordinary tests now explicitly isolate themselves to Mock rather than inheriting local runtime configuration. |
| 5 | One bounded sandbox customer is created, or an exact prior test customer is reused | **FAIL** | Exact duplicate Search returned no match; preparation stopped before reservation/mutation. No customer was created or reused. |
| 6 | Shell/Policy/Amend results are externally observed as applicable | **FAIL** | No Shell, Policy, or Amend request was sent; therefore no external result exists. |
| 7 | Returned GoldTier ID is retained by the target ledger | **FAIL** | No mutation/exact match produced a GoldTier ID, and no ledger reservation occurred. |
| 8 | Subsequent real Search finds the same customer/ID | **FAIL** | There is no created/reused customer or retained ID to read back. |
| 9 | Portal visibly shows the sandbox customer if portal verification is technically available | **FAIL** | Portal capability was available to the implementation session, but there was no created/reused record to locate. No portal customer evidence exists. |
| 10 | Decision-tree pipeline inspector works | **FAIL** | The v2 inspector is collapsed by default, semantic, accessible, responsive, and locally tested, but `project_processing_pipeline()` ignores `stage_order_version` and always emits `GOLDTIER_SEARCH` before `DOCUMENT_IDP` (`apps/backend/app/api_models.py:924`, `:1223`, `:1246`). Historical v1 terminal records canonically retain the pre-Search order (`docs/ARCHITECTURE.md:286-290`), so the tree is not universally factual. |
| 11 | Garden remains truthful | PASS | Supplied official-Mock evidence records `REVIEW_REQUIRED / PARTIAL`, zero shareholders/relationships, and no provider fallback. The synthetic Garden ownership path remains isolated to explicit local-Mock tests and is not used by configured runtime evidence. |
| 12 | No synthetic provider fallback | PASS | Composition and failure behavior remain explicit and fail closed; no XPI-to-Mock or official-ACRA-Mock-to-local-Mock downgrade was found. |
| 13 | Secret scan passes | PASS | Independent `scripts/check_secrets.py` passed. `.env` and `private/sponsor-artifacts-v2` are ignored, untracked, and were not opened. |
| 14 | Independent Quality Gate PASS | **FAIL** | This fresh independent gate is `FAIL`. |

## Contract and Integration Findings

### Current blockers

1. **Acceptance blocker — external customer lifecycle is unproved.** Search-only
   interoperability does not satisfy customer creation, operation observation,
   retained-ID, read-back, or portal acceptance. These are missing required external
   criteria, not minor fixes.
2. **Genuine authority blocker — registration mapping/jurisdiction.** The current
   canonical application route admits Singapore/UEN. The supplied bounded sandbox
   example supplies Australian `ABN`. The candidate correctly refused to map a UEN as
   an ABN, invent Singapore vocabulary, add a second jurisdiction route, or bypass the
   target ledger. Sponsor-controlled Singapore registration vocabulary, or separately
   authorized non-Singapore canonical/registry scope, is required before mutation.

### Verified contract behavior

- `accountEntityType` and `productType` are empty-compatible only for the bounded XPI
  policy request. Unconfirmed/project placeholder values serialize as empty; only
  `SPONSOR_SUPPLIED` or `SANDBOX_OBSERVED` usable text passes through. The other six
  target-policy fields remain fail-closed prerequisites.
- XPI remains an explicit `SANDBOX_PARTIAL` dialect behind the existing target port,
  mapper, entity resolver, policy snapshot, and target ledger. Mock remains a supported
  test/default composition, not a runtime fallback.
- Search is strict, bounded, safe-projected, and no-match evidence is not upgraded to
  mutation or Live interoperability.
- Garden's official API Marketplace Mock result remains Partial/Mock. Empty ownership
  evidence is not replaced by local synthetic ownership.
- Invalid examples remain quarantined. Supplied classifier evidence is 19 `VALID`, 19
  `INVALID / QUARANTINED`, and 48 `NOT_VALIDATED`; it was not rerun because this gate
  was prohibited from opening private sponsor artefacts.

No direct ACRA-to-GoldTier mapping, provider fallback, second execution owner, or target
ledger bypass was found.

## Tester and Adversarial Findings

### Independently executed on the frozen candidate

- Focused backend:
  `pytest -p no:cacheprovider test_goldtier_xpi_sandbox.py test_garden_business_fixture.py`
  — **71 passed**, one dependency deprecation warning.
- Full backend: `pytest -p no:cacheprovider apps/backend/tests` — **1,346 passed,
  35 skipped**, four warnings. The skipped set is not represented as passing physical
  or external evidence.
- Ruff for `apps/backend/app` and `apps/backend/tests` — **PASS**.
- mypy for `apps/backend/app` — **PASS**, 108 source files.
- Focused frontend (`GoldTierSandbox.test.tsx`, `App.test.tsx`) — **65 passed**.
- Full frontend — **286 passed across 23 files**; existing React test warnings did not
  fail the run.
- Frontend typecheck — **PASS**.
- Frontend production build — **PASS**, Vite transformed 116 modules.
- `check_project_state.py`, `check_architecture.py`,
  `check_external_provider_readiness.py`, `check_policy_authority.py`, and
  `check_secrets.py` — **PASS**.
- `git diff --check HEAD` — **PASS**. Task-owned untracked Markdown has no trailing
  whitespace.

### Supplied revision-specific evidence not rerun by this gate

- Isolated authenticated local-Mock Playwright: **14/14 passed**. This is local
  browser/runtime evidence only, not XPI or portal evidence.
- Two real configured XPI Searches: `NO_MATCH / 0`; no Mock fallback.
- Official ACRA Mock Garden run: `REVIEW_REQUIRED / PARTIAL`, zero shareholders and
  relationships.
- GoldTier example classification: 19 valid, 19 quarantined, 48 not validated.

The gate did not access external network, portal/browser, credentials, `.env`, or
private sponsor artefacts. Physical Mongo was not rerun because the candidate changes
no durable schema/repository/CAS behavior. `pre_pr_check.py` was correctly not run on
this intentionally uncommitted review candidate.

### Adversarial conclusion

The candidate stops before mutation when mapping authority is missing, keeps uncertain
mutation/no-replay behavior in the existing ledger, sanitizes browser fields, and does
not turn no-match Search into false success. However, direct projector coverage is too
narrow: the added backend assertion covers only a v2 completed local-Mock path, and the
frontend uses a fabricated generic node list. There is no direct acceptance test for
the projector's historical v1 order, early-Search exact/no-match/review branches,
official Garden partial projection, or target uncertain/failure projection. The v1
defect demonstrates that this gap is material.

## Code and Architecture Review

### Finding QG-01 — Medium — historical v1 pipeline order is falsified

`project_processing_pipeline()` receives the automation record but never branches on
`automation.stage_order_version`. Its returned tuple always places
`GOLDTIER_SEARCH` before `DOCUMENT_IDP`. Canonical architecture and persistence truth
preserve terminal v1 records as the historical pre-Search order; only safe non-terminal
continuations rebase to v2. Consequently, opening the new inspector for a historical
v1 terminal case displays a stage/order that did not exist in that execution. Showing
the inserted stage as `NOT_REACHED` does not make the sequence the actual v1 pipeline.

Required remediation: project v1 and v2 order separately from the persisted
`stage_order_version` (historical terminal v1 should not be presented as having early
Search), and add API/projector plus frontend assertions for both versions and the
required Search/Garden/failure states.

### Architecture result

- Canonical owner reuse is sound: API projection stays at the backend boundary and the
  frontend only renders server-authored order/status.
- No state/cache owner, persistence owner/schema, provider router, entity resolver,
  policy owner, or ledger owner was added or replaced.
- The recursive DTO is bounded and excludes raw provider/request payloads.
- Optional XPI fields are narrowly reconciled without weakening the six required
  authority gates or promoting example vocabulary.
- No unrelated dependency, framework, lockfile, persistence, or jurisdiction change
  was introduced.

## Security Review

No active security defect was found in the reviewed delta.

- External transport remains HTTPS-only, certificate verified, TLS-1.3-only for XPI,
  redirect-disabled, response-size/time bounded, and safe-error projected.
- Backend-only transport identity is not exposed in the new API/UI projection.
- Pipeline fields contain only provider/environment/operation/stage/timestamp/status,
  safe counts/codes, and a bounded retained target ID; no raw provider body, document
  text, credentials, session material, internal exception, endpoint secret, or Mongo
  URI is projected.
- `.env` and `private/sponsor-artifacts-v2` are ignored and untracked. Their contents
  were not read. No sensitive file is staged or newly tracked.
- Independent secret scan passed. Its pattern coverage does not replace external
  credential rotation, sponsor access governance, or production secret storage.

Production PingFed/authentication, production GoldTier, Ready-for-Approval, retention,
and related-party child-ID/relationship semantics remain later unresolved dependencies;
they are not current security successes or current implementation scope.

## Required Fixes and Blockers

### Current acceptance work

1. Obtain authoritative Singapore XPI `registrationType`/value mapping, or explicit
   authority for a separate non-Singapore canonical registry route. Do not infer either.
2. After authority exists, repeat duplicate Search and perform at most one ledger-owned
   synthetic Shell -> Policy -> Amend run; retain the returned ID; perform real
   read-back Search; and verify the same sandbox customer in the portal with sanitized
   evidence.
3. Fix QG-01 so the visual pipeline respects persisted v1 versus v2 execution order,
   and add the missing projector/browser adverse-state tests.
4. Freeze the changed candidate and obtain a fresh independent Quality Gate. Exact
   `PASS` is still required.

### Later dependencies, not current fixes

- Related-party `childId` lifecycle and relationship vocabulary.
- Production PingFed/authentication, Live classification, and deployment/handoff.
- Ready-for-Approval/four-eyes/final approval authority.
- Sponsor-approved production target vocabularies beyond the bounded sandbox task.

## Readiness

- **Final pre-Phase-22 task completion:** NOT READY.
- **Phase 22 readiness:** NOT READY; this report does not authorize Phase 22.
- **GoldTier XPI Search interoperability:** observed for bounded no-match Search only.
- **GoldTier customer mutation/read-back/portal proof:** NOT READY / NOT PROVED.
- **Live ACRA or Live GoldTier:** NOT PROVED and not claimed.
- **Publication/PR readiness:** NOT READY. The required exact independent `PASS` is
  absent, the candidate is uncommitted, and publication was not authorized.

## Git Status and Frozen Reviewed Identity

- Repository: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`
- Branch: `feat/goldtier-sandbox-pipeline-inspector`
- `BASE_SHA = HEAD = origin/main = 463ecdcb4357bb44618cdd5b277671766543dbfc`
- Staged files: none.
- Reviewed tracked delta: 22 modified files; deterministic
  `git diff --binary HEAD | git hash-object --stdin` identity
  `9ad10687ef573dd883bf35ec2a48a5067e8afa46`.
- Reviewed task-owned untracked files:
  - `10-intent.md` — `DC9568BA6645C13D2C4E55B960A350C9EB67CFC4D5E62C2610B92BE8AE6828EC`
  - `20-checkpoint.md` — `BAFF94C48D0CCCA07EBA19D7A0334C20CBE442716A67DEC254279876BD855152`
  - `90-evidence.md` — `9747C705F13E76B50AFF00EE42067ADE9942A35AE4AE287DBC387BDE768183BF`
  - `99-reflection.md` — `8C2447DE7966EDDD9C19CC40551259CBF15B435985F492CF611E45369F674812`
- Complete tracked path set: the six backend application files, three backend test
  files, five frontend source/test files, and eight documentation/decision/contract
  files listed by `git diff --name-status HEAD` at gate start.
- This report is the reviewer's only intentional repository write and is excluded from
  candidate identity. No implementation, configuration, test, ordinary documentation,
  branch, stage, commit, push, PR, merge, external provider, portal, or next-phase
  mutation was performed by the reviewer.

The frozen identity was verified before review and again immediately before writing
this report. Any candidate-content change requires a fresh independent review.
