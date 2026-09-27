# ACRA API Marketplace Mock Runtime — Independent Re-Quality Gate

Date: 2026-09-26

Reviewer role: fresh independent combined re-Quality Gate

Reviewed scope: remediated, uncommitted ACRA API Marketplace Mock runtime candidate

## 1. Executive Result

**FAIL**

The remediated candidate closes the unsupported HTTP `404 -> company absent`
interpretation and preserves the core runtime controls: fixed official Mock hosts,
verified TLS, disabled redirects and environment proxy trust, bounded transport,
memory-only tokens, raw downstream `token` authentication, strict returned/requested
identity binding, no provider fallback, and no invented ownership percentage or
relationship.

Two current blockers remain:

1. **High — the evidence-contract remediation is incomplete.** The validator and JSON
   Schema bind status/schema/identity values to broad outcome labels, but do not bind
   those outcomes to the operation. They accept `coCapitalDetails` as strict
   `SUCCESS / PASS` even though the recorded authority is schema observation only, and
   accept entity retrieval as `SUCCESS_SCHEMA_ONLY`. The JSON Schema additionally
   accepts an operation paired with another operation's endpoint. This is the same
   false-success governance class identified by the first gate.
2. **Medium / required-evidence blocker — the full backend gate remains unstable.** One
   exact-content run passed, but an immediate second run reproduced the same Phase 13
   live-loopback seeder timeout: `1 failed, 1391 passed, 35 skipped`. The test-only
   socket-owner remediation therefore did not reliably close the first gate's required
   backend-evidence blocker.

The retained receipt itself is internally consistent and the official connector's
`404` behavior is now fail-closed. This verdict applies only to the frozen 39-path
candidate below. It does not authorize remediation, commit, push, PR creation, merge,
external execution, or another phase.

## 2. Reviewed Content Identity and Scope

| Identity | Independently established value |
|---|---|
| Repository/worktree | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm` |
| Branch | `feat/acra-marketplace-mock-runtime` |
| `HEAD` / base / `origin/main` / merge base | `f7e6f65dbcd927f8357c2876d5b8cf293ff81f18` |
| Candidate state before this report | 28 tracked modifications, 11 task-owned untracked files, 0 staged |
| Reviewed paths | 39 |
| Canonical fingerprint | `4c4d74b44ba4be441ead87cd28a92b6c33d2aa5738adca483c1142d9d52995e0` |
| Fingerprint definition | SHA-256 over ordinal case-sensitive sorted lines `path<TAB>git hash-object --path=<path> <path>`, LF-joined with no terminal LF |
| Report exclusions | Both `ACRA_API_MARKETPLACE_MOCK_RUNTIME_QUALITY_GATE.md` and this re-gate report are excluded |

The supplied frozen identity reproduced exactly before review and after all read-only
checks. The candidate did not change during review.

Complete reviewed path set:

```text
.agents/skills/poc-regression-check/references/regression-catalogue.md
.env.example
apps/backend/app/composition.py
apps/backend/app/config.py
apps/backend/app/connectors/acra.py
apps/backend/app/connectors/acra_api_marketplace_auth.py
apps/backend/app/connectors/acra_api_marketplace_mock.py
apps/backend/app/connectors/acra_bizfile_sandbox.py
apps/backend/app/connectors/acra_sandbox.py
apps/backend/tests/phase13_test_settings.py
apps/backend/tests/test_acra_api_marketplace_auth.py
apps/backend/tests/test_acra_api_marketplace_mock_connector.py
apps/backend/tests/test_acra_modes.py
apps/backend/tests/test_phase13_demo_scripts.py
apps/backend/tests/test_phase13_test_isolation.py
docs/ARCHITECTURE.md
docs/PROJECT_STATE.md
docs/aegis/INDEX.md
docs/aegis/work/2026-09-26-acra-marketplace-mock-runtime/10-intent.md
docs/aegis/work/2026-09-26-acra-marketplace-mock-runtime/20-checkpoint.md
docs/aegis/work/2026-09-26-acra-marketplace-mock-runtime/90-evidence.md
docs/aegis/work/2026-09-26-acra-marketplace-mock-runtime/99-reflection.md
docs/contracts/ACRA_CANONICAL_MAPPING.md
docs/contracts/ACRA_MOCK_API_PROFILE.md
docs/contracts/EXTERNAL_PROVIDER_ACTIVATION_CONTRACT.md
docs/contracts/acra_api_marketplace_mock_evidence.schema.json
docs/contracts/external_provider_readiness_registry.json
docs/decisions/DECISION_LOG.md
docs/demo/PRE_PHASE22_CAPABILITY_STATUS_MATRIX.md
docs/evidence/acra_api_marketplace_mock_2026-09-26.json
docs/integration/ACRA_API_MARKETPLACE_MOCK_READINESS.md
docs/integration/ACRA_TEAMMATE_RECONCILIATION.md
docs/integration/CONFIGURATION_REFERENCE.md
docs/sponsor-questions/OPEN_QUESTIONS.md
scripts/acra_marketplace_mock_smoke.py
scripts/check_external_provider_readiness.py
scripts/validate_acra_marketplace_mock_evidence.py
tests/test_check_external_provider_readiness.py
tests/test_validate_acra_marketplace_mock_evidence.py
```

Current source revision remains the base Git commit. Behavioral evidence and this
review apply to the uncommitted working-tree fingerprint, not to a committed feature
revision.

## 3. Prior-Blocker Closure Checklist

| First-gate blocker | Result | Direct evidence |
|---|---|---|
| Contradictory receipt binding | **PARTIAL / FAIL** | The original HTTP 500 + identity mismatch + schema PASS + SUCCESS probe is rejected. However, operation/outcome bindings remain absent: capital strict success and entity schema-only success both return no Python validation failures; the JSON Schema accepts both and also accepts an endpoint/operation mismatch. |
| Unsupported HTTP `404` semantics | **PASS** | `AcraApiMarketplaceMockConnector._raise_for_status` treats every non-200 outside explicit auth/timeout/service classes as malformed; focused test maps `404` to `AcraMalformedResponseError`. Q-012 retains not-found/error semantics as open. |
| Exact-content full backend evidence | **FAIL** | First reviewer run reached 100% with no failure. Immediate repeat produced the same live HTTP seeder timeout: `1 failed, 1391 passed, 35 skipped, 3 warnings`. The claimed stabilization is not repeatable. |

## 4. Contract and Integration Findings

### ACRA-MOCK-REQG-001 — High — Evidence operation/outcome binding remains incomplete

`scripts/validate_acra_marketplace_mock_evidence.py` lines 40–44 define outcome
bindings without an operation dimension; lines 113–121 apply only the broad
outcome/status/schema/identity tuple. The schema's `oneOf` branches at lines 61–91 have
the same omission, and its operation and endpoint enums are independent.

Independent probes against the frozen candidate produced:

```text
coCapitalDetails + strict schema PASS + SUCCESS -> [] validation failures
entityBasicInformation + SCHEMA_OBSERVED_ONLY + SUCCESS_SCHEMA_ONLY -> [] validation failures
entityBasicInformation + coShareholdersDetails endpoint -> Python rejected; JSON Schema accepted
```

The first combination can elevate the capital observation from its recorded
schema-only authority to strict success. The second can downgrade an implemented strict
entity result into a different evidence class while still passing. The third shows the
machine-readable contract can pair an operation with the wrong safe endpoint. These
records are individually well-typed but contradict the fixed per-operation evidence
boundary in `ACRA_API_MARKETPLACE_MOCK_READINESS.md` and the first gate's explicit
required fix for incompatible operation/status/identity/schema/outcome combinations.

Required closure: encode an explicit per-operation outcome matrix in both the Python
validator and JSON Schema. At minimum, entity/shareholder strict success and explicit
empty outcomes must be operation-compatible, capital must remain schema-observation-only
for this receipt, and each operation must bind to its exact endpoint. Add independent
adverse tests for every forbidden cross-operation combination.

### Closed contract behavior

- HTTP `404` is no longer interpreted as company absence; it fails closed as a
  sanitized malformed response pending Q-012 authority.
- Current receipt records are consistent with the observed operation boundary.
- Q-012 remains open for provider error/not-found schemas, failure schemas, limits,
  retry/TLS-private-CA details, complete officer/address/constitution semantics,
  same-entity denominator/share-class semantics, relationships/control, and every
  non-Mock contract.
- Garden shareholder absence and the lack of a compatible denominator remain truthful
  partial evidence; no percentage, graph, legal UBO result, Sandbox, Production, or
  Live claim is introduced.

## 5. Tester and Adversarial Findings

### Independently executed evidence

| Command/evidence | Result |
|---|---|
| Focused auth/provider/mode/evidence pytest | **69 passed** |
| External-provider readiness tests outside the Windows temporary-directory ACL boundary | **19 passed** |
| Phase 09/10, Garden, ownership, and zero-touch POC regression selection | **234 passed** |
| Full backend run 1 on the frozen tree | **PASS**; repository double-quiet output suppressed the numeric summary |
| Full backend run 2 on the same frozen tree | **FAIL — 1 failed, 1391 passed, 35 skipped, 3 existing Pydantic warnings** |
| Failing test | `test_http_seeder_runs_twice_against_one_live_memory_backend`; first create-case HTTP response timed out after server startup |
| Ruff over the backend tree, no cache | **PASS** |
| Strict mypy over backend app, no incremental cache | **PASS — 108 source files** |
| Full contract unittest discovery | **44 passed** |
| Project-state / architecture / policy-authority / provider-readiness checkers | **PASS** |
| Dedicated evidence validator on retained receipt | **PASS**, but falsified by ACRA-MOCK-REQG-001 |
| Direct supported-secret scan | **PASS** |
| `git diff --check`, explicit all-39-path trailing-whitespace and conflict-marker scans | **PASS — 0 findings** |
| Frozen-content recheck | **39 paths, 0 staged, fingerprint unchanged** |

The initial combined focused command also encountered the known Windows sandbox ACL
failure in readiness tests that create temporary repositories. The reviewer removed
only the 19 directories created by that command, reran that network-free lane outside
the ACL boundary, obtained 19/19 pass, and confirmed zero such temporary directories
remained. This is missing sandbox capability, not a candidate defect.

No external network, provider credential, `.env`, Postman/Downloads material, raw
provider payload, Live smoke, GoldTier/PingFed call, browser run, or physical Mongo run
was used by this gate. Those lanes are not needed for the defects above and provide no
Live or persistence claim.

### ACRA-MOCK-REQG-002 — Medium / release-blocking — Phase 13 loopback timeout recurs

The candidate changes `test_http_seeder_runs_twice_against_one_live_memory_backend` so
the listener is created and passed to Uvicorn on the server thread. The same frozen
content nevertheless produced one full-suite pass followed immediately by the same
15-second client response timeout in that test. The server had reported started, but
the first create-case request did not return.

This is not evidence of an ACRA runtime defect. It is a reproducible exact-content
regression-gate instability in a test that the remediation itself changes and cites as
the closure for the first gate's full-backend blocker. A single green run cannot prove
the claimed stabilization once the same candidate immediately fails the mandatory
suite again.

Required closure: diagnose the remaining lifecycle/test interaction without weakening
timeouts or skipping the test, obtain repeatable focused evidence, then obtain a green
full backend run on the final exact content and freeze a new identity.

## 6. Code and Architecture Review

Outside the findings above, the runtime implementation remains aligned with the current
architecture:

- Composition extends the existing ACRA connector boundary and selects the official
  Mock lane only by explicit mode; local synthetic Mock remains the repository default.
- Generic sandbox configuration and authorization are not consulted by the official
  lane, BizFile remains uncomposed, and no fallback branch exists.
- Token acquisition, caching and downstream authorization are isolated from strict
  provider decoding and application business behavior.
- Source DTOs carry exact Decimal-compatible share-count evidence. Binary floats are
  rejected and no denominator, ownership percentage, controller status, relationship,
  or legal UBO conclusion is derived.
- Empty required ownership evidence reaches the existing partial Registry acquisition
  and downstream stop before ownership analysis or GoldTier.
- No route/persistence bypass, direct ACRA-to-GoldTier mapping, second registry router,
  second ownership engine, durable schema change, public API change, or frontend change
  was introduced.

Change effects: internal source types, connector/configuration, auth/security,
composition, provider status and runtime behavior change. Durable persistence schema,
public API, target mapping, ownership calculation/business rule, and frontend behavior
do not change.

## 7. Security Review

### Active governance-security finding

ACRA-MOCK-REQG-001 remains a trust-boundary evidence defect: a manipulated receipt can
upgrade or cross-assign the authority of one operation while still passing the dedicated
contract. It exposes no secret, but it weakens the evidence used to justify
`MOCK_INTEROPERABILITY_OBSERVED` runtime status.

### Controls that passed

- Client ID and secret key are backend-only `SecretStr` values; token fields suppress
  representation and cached tokens remain process-local and memory-only.
- Runtime source contains no Production ACRA host, Bearer injection, TLS disablement,
  redirect following, generic-sandbox fallback, or synthetic Garden special case.
- Token and provider transports use fixed HTTPS hosts, OS trust, no redirects,
  `trust_env=False`, bounded time/body retention, content checks, and sanitized errors.
- Provenance is query-free. The retained receipt contains no UEN, name, token/header,
  credential, raw payload, provider error text, or customer/KYC data.
- Direct secret scanning passed; no secret, key, certificate, password, token,
  authorization value, raw Postman export, or confidential payload is newly tracked in
  the reviewed scope.

Deferred ACRA mTLS/private-CA, failure/error/rate/retry, subscriber Sandbox/Production
secret delivery, and Live security remain correctly open under Q-012.

## 8. Required Fixes

1. Bind exact operation, endpoint and permitted outcome/status/schema/identity tuples in
   both the dedicated JSON Schema and Python validator; add cross-operation adversarial
   tests.
2. Diagnose and stabilize the recurring Phase 13 live-loopback timeout without a skip,
   timeout inflation, or weakened assertion; rerun the exact full backend gate.
3. Freeze the changed path set/content identity and obtain another fresh independent
   Quality Gate. Neither the prior report nor this report may be upgraded in place.

The absence of a Garden provider relationship chain, compatible ownership denominator,
Sandbox/Production/Live ACRA, and final legal UBO authority are accepted truthful
limitations, not defects to fill with synthetic or inferred data.

## 9. Readiness

- **Publication / PR readiness:** **NOT READY**. Exact independent `PASS` is absent.
- **Bounded official Mock implementation:** runtime controls are substantially present,
  but acceptance remains blocked by the evidence-contract and repeatable-backend-gate
  findings.
- **Next-phase readiness:** **NOT READY**; no next phase is authorized.
- **Live ACRA verification:** **NOT READY / NOT CLAIMED**. Q-012 remains open.
- **Real GoldTier/PingFed integration:** unchanged and **NOT READY**.
- **Ready-for-Approval / final human approval:** unchanged and unresolved.

## 10. Git Status and Reviewer Boundary

At the review freeze, the candidate had 28 tracked modifications, 11 task-owned
untracked files, and no staged files. This re-gate created only:

`.ai-pipeline/reports/ACRA_API_MARKETPLACE_MOCK_RUNTIME_REQUALITY_GATE.md`

The prior failed gate report was retained unchanged and excluded from the candidate
identity. No implementation, test, configuration, contract, decision, ordinary
documentation, schema, evidence receipt, index, or Git index entry was changed by this
reviewer. No commit, push, PR, merge, rebase, stash, reset, clean, branch switch,
provider call, external smoke, or next phase occurred.
