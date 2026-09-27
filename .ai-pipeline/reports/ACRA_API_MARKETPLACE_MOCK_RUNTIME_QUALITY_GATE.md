# ACRA API Marketplace Mock Runtime — Independent Quality Gate

Date: 2026-09-26

Reviewer role: fresh independent combined Quality Gate

Reviewed scope: uncommitted ACRA API Marketplace Mock runtime candidate

## 1. Executive Result

**FAIL**

The frozen candidate correctly keeps the official ACRA API Marketplace lane explicit,
Mock-only, fixed-host, certificate-verifying, redirect-disabled, bounded, memory-only
for tokens, and free of synthetic/provider fallback. Strict happy-path decoding retains
share counts only as source evidence; it derives no percentage or relationship. Empty
Garden shareholder evidence reaches the truthful existing
`REVIEW_REQUIRED / REGISTRY_EXPECTED_DATA_MISSING` stop before ownership analysis or
GoldTier.

Three current blockers nevertheless prevent acceptance:

1. **High — false-success evidence validation:** the dedicated receipt validator accepts
   an internally contradictory record with HTTP `500`, requested/returned identity
   mismatch, schema `PASS`, and result `SUCCESS`. The new activation-evidence path is
   therefore not whole-record bound and can certify false provider success.
2. **Medium — unsupported provider error semantics:** the official connector converts
   HTTP `404` directly into company absence even though current Q-012 explicitly leaves
   authoritative not-found and provider-error semantics open. This is fail-closed for
   downstream calls, but it makes an unproved provider-semantic claim.
3. **Required-evidence blocker:** the final exact content has no green full-backend run.
   The post-hardening run reports `1390 passed, 35 skipped, 1 failed`, and the Phase 13
   loopback seeder timeout repeated twice in isolation. It appears unrelated to the ACRA
   delta, but `BACKEND_DOMAIN` / `AUTH_RBAC_SECURITY` require a passing full backend
   suite and the earlier `1391 passed` run predates the final client-ID `SecretStr`
   content.

This verdict applies only to the frozen 36-path candidate below. It does not authorize
remediation, commit, push, PR creation, merge, external execution, or another phase.

## 2. Reviewed Content Identity and Scope

| Identity | Independently established value |
|---|---|
| Repository/worktree | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm` |
| Branch | `feat/acra-marketplace-mock-runtime` |
| `HEAD` / base / `origin/main` / merge base | `f7e6f65dbcd927f8357c2876d5b8cf293ff81f18` |
| Candidate state before this report | 25 tracked modifications, 11 task-owned untracked files, 0 staged |
| Reviewed paths | 36 |
| Canonical repository fingerprint | `8daddfddd8f9aef262d3f0d707ad4e9d6d502ac4daf5ec33d7b9e2cc8f1ea46b` |
| Canonical definition | SHA-256 over ordinal case-sensitive sorted lines `path<TAB>git hash-object --path=<path> <path>`, LF-joined with no terminal LF |
| Handoff compatibility fingerprint | `6b2ad137bb1c3badf13595f1022ec6fe9a454c635ee3982223f14f9bfcf13e56` |
| Handoff definition | SHA-256 over PowerShell-sorted lines `path SPACE SHA256(raw file bytes)`, LF-joined with no terminal LF |
| Report exclusion | This Quality Gate report is excluded from both candidate identities |

The two fingerprints independently reproduced the supplied frozen identity under their
respective definitions. The candidate did not change during substantive review.

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
apps/backend/tests/test_acra_api_marketplace_auth.py
apps/backend/tests/test_acra_api_marketplace_mock_connector.py
apps/backend/tests/test_acra_modes.py
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

Current source revision remains the base Git commit. Behavioral evidence and this review
apply to the uncommitted working-tree fingerprints, not to a committed feature revision.

## 3. Acceptance Checklist

| Requirement | Result | Direct evidence |
|---|---|---|
| Explicit opt-in official Mock lane; local synthetic Mock remains default | PASS | `Settings` accepts canonical `api_marketplace_mock`; composition selects it only explicitly; `.env.example` retains `ACRA_CONNECTOR_MODE=mock`; focused mode tests pass. |
| Fixed Mock hosts; no Production host, caller URL, Bearer substitution, or fallback | PASS | Token/API hosts are module constants under `api-sandbox.bizfile.gov.sg`; runtime-source scan found no Production host or Bearer behavior; composition ignores generic sandbox URL/header settings for this lane. |
| Backend-only Basic credentials, strict observed token schema, memory-only cache | PASS | Both credentials are `SecretStr`; token body/auth/cache values suppress representation; exact schema forbids extras; cache is lock-protected and process-local; focused auth tests pass. |
| Verified TLS, controlled redirects/proxy behavior, bounded timeout/body | PASS | Both transports use `ssl.create_default_context()`, `follow_redirects=False`, `trust_env=False`, bounded timeout, content type, declared/streamed byte limits, and safe exception mapping. |
| Strict successful entity/officer/shareholder decoding and identity binding | PASS for observed happy path | Exactly one returned entity and requested/returned UEN equality are required; source DTOs revalidate retained values; focused connector tests pass. Complete provider semantics remain limited by Q-012. |
| No synthetic Garden fallback or leakage into runtime owner | PASS | Runtime auth/connector/composition contains no Garden/SIM LIM special case. The dedicated smoke uses approved fixed Mock identities; the minimized tracked receipt excludes UENs/names. |
| No speculative ownership percentage or relationship derivation | PASS | `shareAllotted` is retained as exact Decimal source evidence only; `ownership_percentage` remains `None`; relationship retrieval is explicit typed absence with no provider call; application test stops before ownership/GoldTier. |
| Provider errors remain within proved Q-012 authority | **FAIL** | HTTP `404` is treated as company-not-found at connector lines 152–153 while Q-012 lines 107–113 says not-found/provider-error schemas remain open. |
| Sanitized provider evidence cannot express false success | **FAIL** | Adverse in-memory probe returned `[]` for HTTP `500` + identity mismatch + schema `PASS` + `SUCCESS`; validator lines 89–102 validate fields independently and tests contain no cross-field cases. |
| Mock/Sandbox/Live and provider-status labels are truthful | PASS | Readiness registry/state/docs consistently use `MOCK_INTEROPERABILITY_OBSERVED`; generic sandbox remains Partial, BizFile Dormant, and no current ACRA path is Live. |
| Q-012 remains open for all unevidenced semantics | PASS except the 404 defect | Open question, D-054, readiness and state documents retain errors/limits/TLS-private-CA/denominator/relationship and every non-Mock contract as unresolved. |
| Focused, static, contract, governance, evidence, secret and hygiene checks | PASS | Results are recorded below. |
| Required exact-content full backend regression | **BLOCKED / FAIL** | Final run has one repeated Phase 13 loopback failure; the only fully green run is stale relative to client-ID hardening. |

## 4. Contract and Integration Findings

### ACRA-MOCK-QG-001 — High — Receipt validator accepts false-success evidence

The new Python validator validates `http_status`, identity equality, schema result, and
result classification independently. It does not enforce compatible combinations by
operation and outcome. The JSON schema has the same omission.

Independent adverse probe supplied a syntactically valid entity-operation receipt with:

```text
http_status = 500
returned_requested_uen_equal = false
strict_schema_validation = PASS
result_classification = SUCCESS
```

`validate(...)` returned an empty failure list. This contradicts the activation
contract's strict/whole-record evidence boundary and permits an invalid receipt to be
reported as `ACRA Marketplace Mock evidence: PASS`. Because sanitized success evidence
supports the new runtime-enabled `MOCK_INTEROPERABILITY_OBSERVED` state, this is a
material false-success governance defect.

Required closure: define and enforce operation/outcome invariants in both the JSON
schema and Python validator. At minimum, successful entity/shareholder records must be
HTTP 200, JSON, within bounds, schema `PASS`, and identity-equal; `EMPTY`, `FAILURE`, and
`SCHEMA_OBSERVED_ONLY` must each have their own compatible operation/status/schema rules.
Add adverse tests for every contradictory combination.

### ACRA-MOCK-QG-002 — Medium — HTTP 404 invents unresolved not-found semantics

`AcraApiMarketplaceMockConnector.fetch_company()` returns `None` before the common
status validator when the provider returns HTTP `404`. A direct fake-transport probe
reproduced `None`. Application code interprets this as company absence rather than an
unproved provider error.

Current Q-012 explicitly leaves authoritative not-found and provider-error schemas open,
and D-054 authorizes only the observed Mock success subset. The behavior stops safely,
but false semantic classification is still a contract defect.

Required closure: until authoritative Mock not-found semantics exist, map HTTP `404` to
a stable sanitized technical failure, or supply/reconcile explicit authority and focused
tests proving that `404` means entity absence for this exact operation. Do not broaden
the claim to Sandbox/Production/Live.

### Current versus later dependencies

- The two findings above are current defects and require remediation/re-review.
- Q-012's remaining provider-error body, token-failure, rate/retry/service-limit,
  mTLS/private-CA, pagination, complete officer/address/constitution, same-entity
  denominator/share-class, relationship/control, and all non-Mock contracts remain
  later authority dependencies. Their truthful deferral is not itself a current defect.
- The current tracked receipt is minimized and internally consistent on inspection; the
  finding concerns what its acceptance mechanism permits, not evidence of a secret or
  raw-payload leak in the present receipt.

## 5. Tester and Adversarial Findings

### Independently executed evidence

| Command/evidence | Result |
|---|---|
| Focused auth/provider/mode pytest with bytecode/cache disabled | **63 passed**; one existing Starlette/httpx deprecation warning |
| Ruff over changed backend application/tests, `--no-cache` | **PASS** |
| Strict mypy over backend app, `--no-incremental` | **PASS — 108 source files** |
| Full contract unittest discovery | **44 passed**; one existing deprecation warning |
| `check_project_state.py` | **PASS** |
| `check_architecture.py` | **PASS** |
| `check_policy_authority.py` | **PASS** |
| `check_external_provider_readiness.py` | **PASS** |
| Dedicated ACRA Mock evidence validator on current receipt | **PASS**, but falsified by ACRA-MOCK-QG-001 |
| `check_secrets.py` | **PASS** |
| `git diff --check` and staged diff check | **PASS**; only Windows LF-to-CRLF notices |
| Explicit trailing-whitespace scan over all 36 paths | **PASS — 0 findings** |
| Conflict-marker scan over all 36 paths | **PASS — 0 findings** |
| False-success receipt probe | **DEFECT REPRODUCED** — contradictory HTTP 500/identity-false/schema-PASS/SUCCESS record returned no validation failures |
| HTTP 404 connector probe | **DEFECT REPRODUCED** — `fetch_company(...)` returned `None` |

One ad-hoc broader selection collected 176 tests and produced `170 passed, 6 failed`.
The six ownership-API failures were configuration-dependent `409` responses because
those legacy tests construct `Settings` without `_env_file=None` and the command
consulted repository-local environment configuration. No environment contents or values
were printed or retained. This run is discarded as invalid behavioral evidence and is
not counted against the candidate; it is recorded for transparency.

### Supplied exact-content and stale evidence

- Before client-ID `SecretStr` hardening: full backend **1391 passed, 35 skipped**.
  This is stale for the final content and cannot satisfy the required exact-content run.
- After hardening: full backend **1390 passed, 35 skipped, 1 failed**. The Phase 13
  HTTP loopback seeder timeout repeated twice in isolation. No reviewed Phase 13 source
  or test changed, and inspection found no causal ACRA path in that test's explicit
  memory/Mock settings, so it is classified as an apparently unrelated regression or
  host/lifecycle issue—not as an ACRA implementation defect. It still blocks the
  mandatory full-backend evidence claim until independently resolved or rerun green.
- Supplied POC selection `234 passed`, Ruff, mypy, contract `44`, governance/evidence
  `88`, context `18`, secret tests `8`, direct secret scan, and the sanitized real-app
  observation are implementation evidence. The reviewer independently reconfirmed the
  narrower results above but did not relabel supplied execution as independent.

No external network, provider credential, raw provider payload, Postman export,
Downloads content, Live smoke, GoldTier/PingFed call, browser run, or physical Mongo run
was used by this gate. Those lanes are not evidence for a Live or persistence claim.

## 6. Code and Architecture Review

Apart from the findings above, the implementation preserves the accepted architecture:

- Runtime composition extends the existing ACRA connector boundary; there is no route
  bypass, direct persistence access, direct ACRA-to-GoldTier mapping, second ownership
  engine, or second registry router.
- The new auth and provider modules are cohesive: token transport/cache/authorization
  is separated from entity/shareholder decoding and from business orchestration.
- Local synthetic `mock`, official `api_marketplace_mock`, generic `sandbox`, and
  dormant BizFile remain distinct. No cross-mode fallback branch exists.
- The official connector returns source DTOs; canonical mapping and the existing
  Registry acquisition/Decimal ownership owners remain downstream.
- Share counts are exact Decimal-compatible source evidence. Binary floats are rejected,
  and no denominator, percentage, controller status, or legal UBO conclusion is added.
- Expected operation stopping is preserved: empty Garden ownership evidence becomes a
  partial Registry acquisition and prevents ownership/GoldTier calls.

Change effects:

- Public API/routes: no change.
- Internal types/source schema: `AcraOwnershipPartyPayload` gains source
  category/status/share-count evidence.
- Durable persistence schema: no change.
- Connector/configuration/auth-security: changed for explicit official Mock activation.
- Business rule/ownership calculation: no change.
- Mapping: bounded observed Mock source decoding added; no target mapping or percentage.
- Architecture owner/dependency direction: existing Registry boundary extended; no new
  business owner.
- Provider status/runtime: official API Marketplace Mock becomes explicit opt-in
  `MOCK_INTEROPERABILITY_OBSERVED`; no Sandbox/Live activation.

## 7. Security Review

### Active security/governance finding

ACRA-MOCK-QG-001 is also a trust-boundary governance issue: a manipulated minimized
receipt can assert successful interoperability while its own safe fields prove failure.
It does not expose a secret, but it weakens the evidence used to authorize provider
runtime status.

### Controls that passed

- Client ID and secret key are backend-only `SecretStr` values. Access tokens and raw
  token response bodies are excluded from representations and retained only in memory.
- The exact runtime source contains no Production ACRA host, Bearer injection,
  `verify=False`, redirect-following, or Garden/SIM LIM special case.
- Token and provider transports use OS trust, disable redirects and environment proxy
  inheritance, bound time/body size, validate JSON content type, and map exceptions to
  stable errors without raw response or credential text.
- Retained provenance removes query parameters. Normal application state receives
  typed, minimized source data rather than raw provider payloads.
- The tracked receipt contains only fixed safe metadata: no UEN, name, token/header,
  credential, raw payload, provider error text, KYC/PII, or Production endpoint.
- The smoke script's approved fixed Mock identities do not enter runtime composition;
  the tracked receipt strips them. No synthetic Garden chain is substituted for empty
  official provider evidence.
- Direct supported-secret scanning passed. No new key, certificate, password, token,
  authorization value, or confidential artefact is tracked in the reviewed paths.

### Deferred hardening/authority

ACRA mTLS/private-CA requirements, complete error/rate/retry behavior, subscriber
Sandbox/Production secret delivery, and Live security remain unresolved under Q-012.
The candidate correctly does not guess or claim them.

## 8. Required Fixes

1. Repair the dedicated evidence schema/validator so incompatible operation/status/
   identity/schema/outcome combinations fail, and add adversarial tests.
2. Remove or authoritatively justify the HTTP `404 -> company absent` interpretation;
   preserve sanitized fail-closed behavior while Q-012 remains open.
3. After remediation, obtain a passing full backend run on the exact final content.
   Diagnose the Phase 13 loopback timeout separately and do not label the stale
   pre-hardening run as current evidence.
4. Freeze the changed path set/content identity and obtain a fresh independent Quality
   Gate. This report cannot be upgraded in place.

Accepted limitations and later sponsor dependencies are not required fixes. In
particular, the absence of a Garden provider relationship chain, a compatible ownership
denominator, Sandbox/Production/Live ACRA, and final legal UBO authority must remain
truthful stops rather than be filled with synthetic or inferred data.

## 9. Readiness

- **Publication / PR readiness:** **NOT READY**. Exact independent `PASS` is absent.
- **Bounded official Mock implementation:** substantially implemented, but blocked by
  the evidence-validator and Q-012 not-found defects plus the mandatory backend-evidence
  gap.
- **Next-phase readiness:** **NOT READY**; no next phase is authorized.
- **Live ACRA verification:** **NOT READY / NOT CLAIMED**. Q-012 remains open.
- **Real GoldTier/PingFed integration:** unchanged and **NOT READY**.
- **Ready-for-Approval / final human approval:** unchanged and unresolved; no such
  outcome is claimed.

## 10. Git Status and Reviewer Boundary

At review freeze, the candidate had 25 tracked modifications, 11 untracked task files,
and no staged files. This gate created only:

`.ai-pipeline/reports/ACRA_API_MARKETPLACE_MOCK_RUNTIME_QUALITY_GATE.md`

No implementation, test, configuration, contract, decision, ordinary documentation,
schema, evidence receipt, index, or Git index entry was changed by the reviewer. No
commit, push, PR, merge, rebase, stash, reset, clean, branch switch, provider mutation,
external smoke, or next phase occurred.
