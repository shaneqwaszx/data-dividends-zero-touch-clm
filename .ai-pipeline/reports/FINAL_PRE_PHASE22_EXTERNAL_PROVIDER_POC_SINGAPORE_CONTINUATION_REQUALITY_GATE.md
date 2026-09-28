# Final Pre-Phase-22 External-Provider POC Singapore Continuation Re-Quality Gate

**Review date:** 2026-09-27

**Review mode:** Fresh independent combined re-Quality Gate; report-only writer

**Verdict:** **FAIL**

## 1. Executive result

QG-SG-01 is **closed**. The corrected reconciliation now states seven total bounded
Searches and identifies the last three as the 2026-09-27 configured
`OnboardingService`/actual-XPI calls. That prose agrees with all seven table rows and the
retained chronology.

The whole current acceptance nevertheless remains **FAIL**. The official ACRA API
Marketplace Mock supplied the Garden Singapore identity and an actual XPI Search through
the configured application service returned `NO_MATCH / 0` with no local GoldTier Mock
fallback. The flow then stopped correctly before target-ledger reservation or mutation
because `kycCustomerType`, `clientSegment`, `policy`, and `bookingEntity` still lack
authorized Singapore-safe values. There is consequently no Shell, Policy, Amend,
retained target ID, same-ID read-back, portal verification, or actual sandbox customer
evidence. Local correctness cannot waive those required external criteria.

No implementation, architecture, or security defect was found. Prior findings QG-01,
QG-02, and QG-03 remain closed. One new Low evidence-accounting defect remains locally:
the current work record reports `1,401 passed / 35 skipped` for the canonical backend
suite, while this gate's exact repository-root execution completed with `1,353 passed /
35 skipped / 4 warnings`. Fresh collection under the same command also agrees with the
executed 1,388-item inventory. This is QG-SG-02; it does not change product behavior or
the external blocker, but the mutable work record must not retain a count that the
recorded command does not reproduce.

No external-provider request, portal action, `.env` access, secret access, customer
mutation, or Mongo operation was performed by this reviewer.

## 2. Frozen reviewed identity and scope

| Item | Independently observed value |
|---|---|
| Repository | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm` |
| Branch | `feat/goldtier-sandbox-pipeline-inspector` |
| `HEAD` | `463ecdcb4357bb44618cdd5b277671766543dbfc` |
| Review base | `463ecdcb4357bb44618cdd5b277671766543dbfc` |
| `origin/main` | `463ecdcb4357bb44618cdd5b277671766543dbfc` |
| Staged paths | none |
| Tracked diff identity | `5c3a6c9fd4ff30ede4e84bd721496c8a09aa5a74` from `git diff --binary --no-ext-diff | git hash-object --stdin` |
| Reviewed candidate path count | 35: 26 tracked modified paths plus 9 pre-existing untracked paths |

### Reviewed tracked paths

- `apps/backend/app/api_models.py`
- `apps/backend/app/connectors/goldtier_xpi_models.py`
- `apps/backend/app/domain/policy.py`
- `apps/backend/app/domain/target_preparation.py`
- `apps/backend/app/main.py`
- `apps/backend/app/mappers/goldtier_xpi.py`
- `apps/backend/app/services/policy_management.py`
- `apps/backend/tests/phase13_test_settings.py`
- `apps/backend/tests/test_garden_business_fixture.py`
- `apps/backend/tests/test_goldtier_xpi_sandbox.py`
- `apps/frontend/src/App.test.tsx`
- `apps/frontend/src/GoldTierSandbox.test.tsx`
- `apps/frontend/src/pages/CaseStatePanels.tsx`
- `apps/frontend/src/pages/PolicyRules.tsx`
- `apps/frontend/src/styles.css`
- `apps/frontend/src/types.ts`
- `docs/ARCHITECTURE.md`
- `docs/PROJECT_STATE.md`
- `docs/aegis/INDEX.md`
- `docs/contracts/EXTERNAL_PROVIDER_ACTIVATION_CONTRACT.md`
- `docs/contracts/POLICY_AUTHORITY_MATRIX.md`
- `docs/decisions/ADR-004_GOLDTIER_XPI_SANDBOX_ADAPTER.md`
- `docs/decisions/DECISION_LOG.md`
- `docs/integration/GOLDTIER_XPI_MAPPING_MATRIX.md`
- `docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md`
- `docs/sponsor-questions/OPEN_QUESTIONS.md`

### Reviewed pre-existing untracked paths and SHA-256

| Path | SHA-256 |
|---|---|
| `.ai-pipeline/reports/FINAL_PRE_PHASE22_EXTERNAL_PROVIDER_POC_CLOSURE_REQUALITY_GATE.md` | `e55012f2da4646742d869bba18386543635e3a31273dc80257e8d362f33f7e51` |
| `.ai-pipeline/reports/FINAL_PRE_PHASE22_EXTERNAL_PROVIDER_POC_FINAL_REQUALITY_GATE.md` | `5da270ebcb92c6610c92f70f404b0609e25b0c722da5fcb8dd27fe1909b0e771` |
| `.ai-pipeline/reports/FINAL_PRE_PHASE22_EXTERNAL_PROVIDER_POC_QUALITY_GATE.md` | `8b4c4e9f3a2a1e7324411de06dd50641675ab6d30705d92aaa3fbd204afc8887` |
| `.ai-pipeline/reports/FINAL_PRE_PHASE22_EXTERNAL_PROVIDER_POC_REQUALITY_GATE.md` | `fb8938f3abcc2c98bbf3ee6861617ea59d412fabe4eead7b9d59816f4f3290da` |
| `.ai-pipeline/reports/FINAL_PRE_PHASE22_EXTERNAL_PROVIDER_POC_SINGAPORE_CONTINUATION_QUALITY_GATE.md` | `3af52ec5508fb754c2d1f98d019d48b3930f3532cfa14d483511c81087c30fa6` |
| `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/10-intent.md` | `9f03bf32222daba23c0226c78e2bf4768485de71ce4d22d6ddea39db84b1d134` |
| `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/20-checkpoint.md` | `f882fcea84d324aea8407c1b67490c10bd11668ab44c75affd8d773268299dca` |
| `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/90-evidence.md` | `e88420f0f26ea29106850254acdaaf4f2262e5cc6a7b41336724c867c61019cd` |
| `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/99-reflection.md` | `93e37cd7e68366399484a9c21234ebed7f82a35e369a01491404928835c43d60` |

The ignored `.env` and private sponsor-artifact area were not opened. The assigned report
is excluded from the reviewed candidate identity.

## 3. Final acceptance checklist

| # | Acceptance requirement | Result | Independent basis |
|---:|---|---|---|
| 1 | Official ACRA API Marketplace Mock active | **PASS** | Retained sanitized evidence identifies the official-Mock Garden Singapore identity. The lane remains Mock, not Live. |
| 2 | Actual GoldTier XPI sandbox active | **PASS** | Retained sanitized evidence records an actual configured-service Search returning `NO_MATCH / 0`; this proves bounded Search connectivity only. |
| 3 | No normal-runtime local provider Mock fallback | **PASS** | Composition, tests, and retained execution evidence preserve explicit modes and no fallback. |
| 4 | Singapore identity used | **PASS** | Canonical legal name/UEN and both `SG` country fields remain the source identity. |
| 5 | No ABN/Australia/Melbourne substitution | **PASS** | `registrationType=UEN` remains `USER_AUTHORIZED_POC`; Australian examples are not promoted into Singapore data. |
| 6 | Real XPI Search executed | **PASS** | The official-Mock Garden Search reached XPI and returned `NO_MATCH / 0`. |
| 7 | Shell created or valid existing customer reused | **FAIL** | Search found no match and preparation stopped before reservation/Shell. |
| 8 | Policy completed where required | **FAIL** | No Shell/ID exists and `policy` plus `bookingEntity` lack safe authority. |
| 9 | Amend completed where required | **FAIL** | No target ID exists and no Amend request was sent. |
| 10 | Returned target ID retained | **FAIL** | No match or write produced a target ID. |
| 11 | Same-ID real read-back verified | **FAIL** | There is no retained ID or created/reused customer to read back. |
| 12 | Portal-visible sandbox record verified where technically possible | **FAIL** | No customer was created or reused, so no portal record could be verified. |
| 13 | Pipeline inspector accurately represents retained execution | **PASS** | Versioned ordering, active checkpoint-absent Search coherence, ID provenance, safe event projection, collapsed semantic rendering, and unresolved approval are covered by source inspection and fresh tests. |
| 14 | Security/governance checks pass | **PASS** | Direct checkers, focused governance/security tests, safe DTO/transport review, and secret scan pass. |
| 15 | Fresh independent Quality Gate passes | **FAIL** | This gate is `FAIL` because criteria 7-12 remain unmet. |

## 4. Findings and prior-finding disposition

### QG-SG-01 — Search-count chronology — CLOSED

`docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md` now records seven total
Searches, says the last three were the configured-service calls on 2026-09-27, and lists
exactly seven corresponding rows. No observation was deleted or reclassified. The fix is
accurate and requires no further local correction.

### QG-SG-02 — Low — canonical backend-suite count is not reproducible from the work record

`docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/90-evidence.md:79`
reports `1,401 passed / 35 skipped`. The immutable prior Singapore gate repeats that
inventory as supplied evidence. From the repository root, this gate ran exactly:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider apps/backend/tests
```

Environment: Windows, Python `3.12.10`, pytest `8.4.2`, anyio plugin `4.14.2`, current
working tree at tracked diff identity
`5c3a6c9fd4ff30ede4e84bd721496c8a09aa5a74`. The result was `1,353 passed, 35 skipped,
4 warnings` in 93.51 seconds. A fresh `--collect-only -q` under the same path enumerated
the same 61 test files and 1,388 executed/skipped items. The focused changed suites are
included in that inventory and separately pass 78/78.

This is an evidence-record accuracy defect, not a product/test failure. Do not alter an
immutable prior gate. Reconcile the mutable work record only after the coordinator
reproduces and explains the different `apps/backend` working-directory observation; the
record must state the exact command, working directory, collection, and result rather
than silently choosing either number.

### Prior runtime findings — CLOSED

- QG-01: historical v1 order remains distinct from v2 early Search.
- QG-02: checkpoint-absent active Search derives its truthful status from the automation owner.
- QG-03: checkpoint-absent Search status, fixed safe result, timestamp, blocker, count,
  branches, and identity form one coherent view.
- A no-match Search never displays an ID created later by Shell; exact-match reuse may
  display only its retained matched ID.

No implementation/security defect remains open.

## 5. Contract and integration review

The reviewed candidate preserves the required boundary:

`untrusted provider DTO -> canonical evidence/model -> target mapper -> controlled connector`

- ACRA remains the explicit official API Marketplace Mock lane for the retained Garden
  observation; it is not Sandbox or Live.
- GoldTier remains explicit `SANDBOX_PARTIAL`. Local Mock remains isolated-test support,
  never sandbox recovery.
- `registrationType=UEN` is `USER_AUTHORIZED_POC`; `customerExternalSystem=DSD` is a
  registration-independent `SPONSOR_EXAMPLE`.
- Unconfirmed `accountEntityType` and `productType` serialize empty only for the bounded
  XPI customer-policy dialect. No non-empty vocabulary is inferred.
- `kycCustomerType`, `clientSegment`, `policy`, and `bookingEntity` remain mandatory,
  `TBD_SPONSOR`, and fail closed before target-ledger reservation or network mutation.
- The SIM LIM shareholder observations have counts but no provider-backed same-entity
  profile/address or compatible capital denominator. No ownership percentage,
  relationship, or canonical root is fabricated.
- Search resolution, target ordering, call stopping, retained identity, and uncertain
  no-replay handling remain with the existing resolver/ledger owners.

The current blocker is external sponsor authority/evidence, not a registration mapping
bug and not a reason to substitute ABN, Australia, or the Melbourne booking example.

## 6. Tester and adversarial evidence

### Fresh independent execution

| Evidence | Result |
|---|---|
| Focused Garden/XPI backend tests | **PASS — 78 tests**, one known Starlette deprecation warning |
| Focused pipeline-inspector frontend tests | **PASS — 5 tests** |
| Canonical backend suite from repository root | **PASS — 1,353 passed / 35 skipped / 4 warnings**; see QG-SG-02 for the count discrepancy |
| Ruff | **PASS** |
| Strict mypy | **PASS — 108 source files** |
| Complete frontend suite | **PASS — 288 tests across 23 files**; existing React warnings only |
| Frontend typecheck | **PASS** |
| Frontend production build | **PASS — 116 modules transformed**, disposable system-temp output removed |
| Contract unittest discovery | **PASS — 44 tests** |
| Supported non-contract repository suite | **PASS — 275 tests** |
| Guarded isolated Playwright lifecycle suite | **PASS — 14/14**; local Mock/browser evidence only |
| Focused governance suite | **PASS — 66 tests**; eight additional secret-scanner tests also passed |
| Project-state, architecture, provider-readiness, policy-authority, secret checkers | **PASS** |
| `git diff --check HEAD` | **PASS**; configured LF/CRLF notices only |
| Explicit untracked Markdown whitespace/final-LF check | **PASS — all 9 pre-existing Markdown files** |

The first sandboxed governance run failed because the process sandbox denied nested
temporary `.git` creation; the host-permission rerun passed all 74 selected tests. The
first sandboxed frontend run failed because esbuild could not spawn (`EPERM`); the
host-permission rerun passed 5/5. These are runner limitations, not product failures.
Only the exact test-created temporary directories from the failed attempt were removed
after every resolved target was verified inside this workspace.

Adversarial inspection found no path that converts UEN to ABN, dispatches unresolved
mandatory values, falls back from XPI to Mock, exposes retained automation free text,
attributes a Shell ID to no-match Search, replays an uncertain write, or turns local
completion into approval. No test result is represented as external Shell, Policy,
Amend, read-back, portal, Production, or Live evidence.

### Retained external evidence not replayed by this gate

- official-Mock Garden identity and empty shareholder evidence;
- real configured XPI Search `NO_MATCH / 0` with no Mock fallback;
- no target-ledger reservation, Shell, Policy, Amend, related-party call, read-back, or
  portal observation.

## 7. Code, architecture, and security review

No current implementation, architecture, maintainability, or security defect was found.

- The backend remains the sole owner of the bounded recursive pipeline projection; the
  frontend renders backend order/status without reconstructing business state.
- The DTO forbids extra fields and bounds labels, statuses, summaries, counts, children,
  blocker codes, timestamps, and retained IDs. Raw provider bodies, request payloads,
  document text, credentials, sessions, endpoints, and internal exception text are not
  projected.
- Technical event tables render fixed codes/types rather than retained free-text event
  messages.
- XPI remains HTTPS-only, certificate-verified, TLS-1.3-only, redirect-disabled, and
  time/body bounded. The backend-only `user_id` transport identity is not projected.
- Mutation remains opt-in, ledger-owned, ordered, call-stopped, and non-replayable after
  uncertain dispatch.
- No persistence owner/schema, authorization owner, cache owner, provider router,
  entity resolver, ownership engine, target ledger, framework, or dependency direction
  changed.

The work record's missing Aegis helper JSON sidecar was independently confirmed. Its
reported inability to produce a structural bundle, plus the pre-existing historical
index/advisory incompatibilities, is a **process-tooling limitation**. It supplies no
product PASS or FAIL evidence and does not alter the external acceptance result.

## 8. Required fixes, dependencies, and readiness

### Current acceptance work

1. Obtain explicit Singapore-safe authority for `kycCustomerType`, `clientSegment`,
   `policy`, and `bookingEntity`.
2. Only then run a new duplicate Search and at most one ledger-owned Shell -> Policy ->
   Amend continuation. Retain the returned ID, perform same-ID real read-back, and
   verify the customer in the portal where technically possible.
3. Reconcile QG-SG-02 in the mutable work record after reproducing the working-directory
   discrepancy. Prior immutable gates remain unchanged.
4. Freeze any changed candidate and obtain a fresh independent combined Quality Gate.

### Readiness

- QG-SG-01: **CLOSED**.
- Open local implementation/security fix: **NONE**.
- Open local documentation/evidence fix: **QG-SG-02**.
- Whole final pre-Phase-22 acceptance: **NOT READY / FAIL**.
- Phase 22, publication, commit, push, PR, or merge readiness: **NO**.
- GoldTier customer mutation/read-back/portal proof: **NOT PROVED**.
- Live ACRA or Live GoldTier: **NOT PROVED** and not claimed.

## 9. Change-impact and Git status

| Change class | Result |
|---|---|
| API/type | Changed: bounded backend-authored processing nodes and frontend contract |
| Durable schema/persistence | Unchanged |
| Connector contract | Narrowly changed for empty-compatible policy fields; no new endpoint or Live claim |
| Configuration | No tracked runtime-secret/deployment activation change |
| Business rule/mapping | Changed for exact SG/UEN POC authority, DSD example classification, and fail-closed mandatory values |
| Authentication/security | No authority relaxation; backend-only transport identity and sanitization preserved |
| Architecture | Owners and dependency directions unchanged |
| Provider status | ACRA official Mock; GoldTier Sandbox/Partial; neither Live |
| Runtime behavior | Search-first fail-closed continuation and safe pipeline projection changed; no external mutation proved |

After this report write:

- branch, `HEAD`, review base, and `origin/main` remain exactly as recorded above;
- the 26-path tracked diff remains unchanged at
  `5c3a6c9fd4ff30ede4e84bd721496c8a09aa5a74`;
- staged paths remain empty;
- the nine reviewed untracked files remain unchanged;
- this assigned report is the reviewer's sole intentional repository write;
- no implementation, test, configuration, contract, decision, work record, prior gate,
  branch, stage, commit, push, PR, merge, external provider, portal, Mongo, or next-phase
  mutation occurred.

Any candidate-content change requires a fresh independent review.
