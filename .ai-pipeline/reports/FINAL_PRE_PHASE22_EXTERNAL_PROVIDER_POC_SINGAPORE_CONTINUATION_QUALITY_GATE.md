# Final Pre-Phase-22 External-Provider POC Singapore Continuation Quality Gate

**Review date:** 2026-09-27

**Review mode:** Fresh independent combined Quality Gate; report-only writer

**Verdict:** **FAIL**

## 1. Executive result

The frozen candidate does not satisfy the whole current acceptance. The official ACRA
Marketplace Mock supplied the Garden Singapore identity, and an actual XPI Search through
the configured application service returned `NO_MATCH / 0` with no local GoldTier Mock
fallback. The guarded flow then stopped correctly before ledger reservation or mutation
because four mandatory target fields still lack safe authority:
`kycCustomerType`, `clientSegment`, `policy`, and `bookingEntity`.

Consequently there is no Shell, Policy, Amend, retained target ID, same-ID read-back, or
portal verification evidence. Acceptance criteria 7-12 are unmet and the final independent
gate criterion is therefore unmet. This is an **external sponsor-authority and evidence
blocker**, not a defect in the reviewed runtime implementation.

The independent code, contract, architecture, security, test, and adversarial review found
no current implementation or security defect. Prior findings QG-01 through QG-03 remain
closed. One new low-severity documentation accuracy defect is recorded as QG-SG-01: the
tracked reconciliation prose counts six searches and calls the last two application-service
searches, while its table contains seven searches and the current chronology records three
such 2026-09-27 searches.

No external-provider request, portal action, `.env` access, secret access, customer mutation,
or Mongo operation was performed by this reviewer.

## 2. Frozen review identity and scope

| Item | Independently observed value |
|---|---|
| Repository | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm` |
| Branch | `feat/goldtier-sandbox-pipeline-inspector` |
| `HEAD` | `463ecdcb4357bb44618cdd5b277671766543dbfc` |
| Review base | `463ecdcb4357bb44618cdd5b277671766543dbfc` |
| `origin/main` | `463ecdcb4357bb44618cdd5b277671766543dbfc` |
| Merge base | `463ecdcb4357bb44618cdd5b277671766543dbfc` |
| Staged paths | none |
| Tracked diff identity | `3cd46546eb001498d09b5b7db6bb2cdd0d4ae64e` from `git diff --binary --no-ext-diff | git hash-object --stdin` |
| Reviewed candidate path count | 34: 26 tracked modified paths plus 8 pre-existing untracked paths |

The reviewer read the root, backend, and frontend `AGENTS.md` instructions; the complete
`fyp-quality-gate` skill and report template; the assigned user task; current work records;
all four prior immutable gates; the relevant architecture, contracts, decisions, mapping,
reconciliation, policy-authority, and open-question records; and the complete tracked diff,
untracked candidate files, changed source, and changed tests.

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
| `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/10-intent.md` | `9f03bf32222daba23c0226c78e2bf4768485de71ce4d22d6ddea39db84b1d134` |
| `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/20-checkpoint.md` | `4005f7565a63f0cd88d92ea86aa187b82d757ec9c3acae0c19cc7f71e2cef036` |
| `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/90-evidence.md` | `566768f9fff3bc1552dbe6b4ae4eebdc396542e4fe610f0d90fb2b47dd6e770f` |
| `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/99-reflection.md` | `93e37cd7e68366399484a9c21234ebed7f82a35e369a01491404928835c43d60` |

The ignored `.env` and private sponsor-artifact area were not opened or scanned. No value
from either surface is reproduced here.

## 3. Exact acceptance evaluation

| # | Acceptance requirement | Result | Independent basis |
|---:|---|---|---|
| 1 | Official ACRA Marketplace Mock active | **PASS** | The retained sanitized evidence identifies the official-Mock Garden Singapore company; provider classification remains Mock, not Live. |
| 2 | Actual XPI sandbox active | **PASS** | The configured application-service Search reached actual XPI and returned `NO_MATCH / 0`; this proves bounded Search connectivity only. |
| 3 | No local GoldTier Mock fallback | **PASS** | Evidence, composition, and tests preserve no-fallback behavior. |
| 4 | Singapore identity remains Singapore | **PASS** | Both country fields remain `SG`; exact registration type is `UEN`. |
| 5 | No ABN/Australia/Melbourne substitution | **PASS** | Historical Australian diagnostics are quarantined from Singapore mapping and execution. |
| 6 | Real XPI Search executed | **PASS** | The actual configured Search result is the sanitized `NO_MATCH / 0` observation. |
| 7 | Shell created or a valid existing target reused | **FAIL** | No target match existed and dispatch stopped before reservation or Shell. |
| 8 | Policy executed where required | **FAIL** | No Shell/ID existed and `policy` lacks safe authority. |
| 9 | Amend executed where required | **FAIL** | No Shell/ID existed; no Amend request was sent. |
| 10 | Returned target ID retained | **FAIL** | Search returned no candidate and no write occurred, so no target ID exists. |
| 11 | Same-ID read-back verified | **FAIL** | There is no retained ID to read back. |
| 12 | Portal verified where technically possible | **FAIL** | The lifecycle never produced a target customer/ID; no portal verification occurred. |
| 13 | Pipeline inspector accurately represents execution | **PASS** | Ordered projection, active pre-checkpoint states, Search-ID provenance, target path, unresolved approval, and safe event-code rendering are covered by changed tests and reviewer inspection. |
| 14 | Security and governance pass | **PASS** | Direct checkers/secret scan pass; backend-only provider header, bounded Search, safe projection, no raw response retention, and fail-closed mutation controls remain intact. |
| 15 | Fresh independent Quality Gate passes | **FAIL** | This gate is `FAIL` because mandatory end-to-end external acceptance evidence is absent. |

Items 7-12 are not waived by the correctness of the stop. The code is right to stop, but
the requested external POC lifecycle remains incomplete.

## 4. Findings

### QG-SG-01 — Low — Search-count chronology in the reconciliation is internally inconsistent

`docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md:70-83` states that six searches
were executed and that the last two ran through `OnboardingService`, then lists seven query
rows. The current work chronology distinguishes the two earlier 2026-09-27 configured
application-service Searches from the later official-Mock Garden continuation Search, so
three listed rows belong to that continuation-era application-service evidence.

This does not alter runtime behavior, provider safety, or the external blocker, but it makes
the durable audit record arithmetically inaccurate. Before a fresh gate, reconcile the prose
count and provenance wording with the seven rows and the authoritative chronology. Do not
remove or reclassify any observation to make the count fit.

### External acceptance blocker — not a code defect

The official-Mock Garden flow cannot safely construct the required target write request
because `kycCustomerType`, `clientSegment`, `policy`, and `bookingEntity` have no current
safe authority. The supplied examples do not authorize values for this company. `UEN` is
only `USER_AUTHORIZED_POC`; `DSD` is only `SPONSOR_EXAMPLE`. Neither label upgrades those
values to sponsor-confirmed production policy.

The ACRA SIM LIM shareholder observations contain share counts but no same-entity profile,
address, or compatible capital denominator. The candidate correctly derives no ownership
percentage, canonical related party, or target hierarchy from that fragmented evidence.

Resolution requires explicit safe authority for all four mandatory fields, followed by a
new bounded execution through the existing ledger-owned sequence and fresh retained,
sanitized evidence for Shell/reuse, Policy and Amend where required, target-ID retention,
same-ID read-back, and portal verification if then technically possible. No Australian
identity or example may be substituted.

## 5. Contract, integration, code, and architecture review

- The canonical flow remains untrusted provider DTO to canonical evidence/model to target
  mapping; no direct ACRA-to-GoldTier mapping was introduced.
- Singapore defaults are exact and visibly classified: `SG`/`UEN` with
  `USER_AUTHORIZED_POC`, and independent source-system example `DSD` with
  `SPONSOR_EXAMPLE`.
- `accountEntityType` and `productType` remain compatible only as collection-observed empty
  optional values. The four unresolved mandatory fields fail closed.
- Search remains bounded and precedes any write. No-match produces no target-ID claim and
  cannot bypass ledger-owned reservation, ordering, call stopping, or no-replay handling.
- Prior QG-01 is closed: historical v1 ordering remains distinct from v2 early Search.
- Prior QG-02 is closed: active checkpoint-absent Search states no longer project as
  `NOT_REACHED` when current-stage status is authoritative.
- Prior QG-03 is closed: a no-match Search cannot display an ID later created by Shell.
- The final unresolved human-approval node is explicit and remains unresolved; the UI does
  not imply autonomous or final approval.
- Frontend rendering consumes backend-authored safe pipeline nodes. Collapsed semantic and
  technical disclosures preserve accessibility, and the technical view uses safe event
  codes rather than retained free-text event messages.
- No persistence owner, schema, dependency direction, provider composition owner,
  authorization owner, or architecture boundary was duplicated or bypassed.

## 6. Security and failure-path review

- External errors and evidence remain sanitized; no raw response body or authorization
  material is retained or rendered.
- The sponsor-supplied `user_id` header remains backend-only. Collection `noauth` metadata
  is not generalized to production authentication policy and does not replace PingFed.
- Missing authority, malformed/oversized responses, transport failures, ambiguous mutation
  outcomes, and unsupported provider states fail closed without local Mock fallback.
- A mutation ambiguity remains `IN_PROGRESS` and is not automatically replayed.
- Backend authority, RBAC/team scope, safe inaccessible-case behavior, and sensitive
  mutation authorization ownership are unchanged by this slice.
- No external request was repeated for this gate. No portal, write endpoint, physical Mongo,
  secret-bearing surface, or protected raw artifact was accessed.

No security finding is open in the reviewed candidate.

## 7. Test and adversarial evidence

| Evidence | Result |
|---|---|
| Focused backend Garden/XPI tests | **PASS — 78 passed**, one known Starlette deprecation warning |
| Complete backend pytest | **PASS — exit 0 and reached 100%**; current exact-candidate inventory records **1,401 passed / 35 skipped / 3 known serializer warning groups** |
| Ruff | **PASS** |
| Strict mypy | **PASS — 108 source files** |
| Focused frontend pipeline-inspector tests | **PASS — 5 tests** on host-permission rerun after sandboxed esbuild returned `EPERM` |
| Complete frontend suite | **PASS — 288 tests across 23 files**; existing React test warnings only |
| Frontend typecheck | **PASS** |
| Frontend production build | **PASS — 116 modules transformed**, using a temporary output directory |
| Contract unittest discovery | **PASS — 44 tests** |
| Supported non-contract repository selection | **Current selection independently collected exactly 275 tests**; frozen exact-candidate evidence records **275 passed** |
| Isolated Playwright lifecycle suite | **Frozen exact-candidate evidence: PASS — 14 tests**; local UI/runtime regression only, not external-provider or portal proof |
| Project-state, architecture, provider-readiness, policy-authority, tooling, and direct secret checks | **PASS** |
| Tracked diff check and explicit pre-existing untracked Markdown whitespace/final-newline check | **PASS**; Git emitted only configured LF/CRLF notices |

One intentionally uncounted broad probe used raw combined root `unittest discover`. It ran
315 tests and ended with the two known contract-import errors because that command does not
provide the contract runner's required path setup. The supported contract command passed 44;
the supported non-contract selection contains 275. The invalid broad command is not reported
as passing evidence and revealed no candidate behavior defect. Its test-created temporary
directories were removed, and its launcher-owned demo processes were stopped.

No test result is used as evidence of external Shell/Policy/Amend/read-back/portal success.

## 8. Change-impact statement

| Change class | Result |
|---|---|
| API/type | Changed: safe pipeline node and technical event-code projection used by the frontend |
| Durable schema/persistence | Unchanged |
| Connector contract | Narrowly changed for evidence-backed optional empty fields; no new endpoint or live claim |
| Configuration | No tracked runtime-secret or deployment activation change |
| Business rule/mapping | Changed for exact SG/UEN POC authority, DSD example classification, and fail-closed mandatory fields |
| Authentication/security | No authority relaxation; backend-only header and sanitization remain |
| Architecture | Owners and dependency directions unchanged |
| Provider status | ACRA remains official Mock; GoldTier remains bounded Sandbox/Partial, not Live |
| Runtime behavior | Search-first fail-closed continuation and backend-authored pipeline inspector changed; no external mutation proven |

## 9. Required next actions and readiness

1. Correct QG-SG-01 in the reconciliation record without changing or deleting the underlying
   observations.
2. Obtain explicit safe authority for all four unresolved mandatory GoldTier fields.
3. Only then perform a newly authorized bounded continuation using the Singapore Garden
   identity, with no ABN/Australia/Melbourne substitution and no inferred ownership.
4. Retain sanitized evidence for each required external stage, same-ID read-back, and portal
   verification when technically possible.
5. Freeze the changed content and request another fresh independent combined Quality Gate.

The candidate is **not ready for whole-acceptance sign-off, publication, or Phase 22**. The
local implementation is regression-green and no implementation/security defect was found,
but local correctness does not replace the missing external lifecycle evidence. Nothing in
this report classifies either provider as Live or authorizes a later phase, commit, push, PR,
merge, or external write.
