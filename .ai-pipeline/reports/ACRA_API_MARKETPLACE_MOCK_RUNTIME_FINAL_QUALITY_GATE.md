# ACRA API Marketplace Mock Runtime — Final Independent Quality Gate

Date: 2026-09-27

Reviewer role: fresh independent combined Quality Gate after two immutable failed gates

Reviewed scope: frozen, uncommitted Official ACRA API Marketplace Mock runtime candidate

## 1. Executive Result

**PASS**

The frozen candidate satisfies the bounded Official ACRA API Marketplace Mock
acceptance boundary. A fresh reviewer run reached the official Mock host with verified
TLS, retrieved and strictly decoded Garden entity evidence, observed the Garden
shareholder response as explicitly empty, and exercised the configured application to
the truthful `REVIEW_REQUIRED / REGISTRY_EXPECTED_DATA_MISSING` stop without a
GoldTier result. The candidate contains no synthetic provider fallback, Garden
ownership relationship, derived ownership percentage, Production host, Bearer
assumption, TLS bypass, or Live classification.

The two prior gate blockers are closed. The receipt validator and JSON Schema now bind
operation, exact safe endpoint, and permitted outcome tuple. The Phase 13 loopback
failure independently reproduces on clean accepted main but the frozen candidate's
minimal Windows threaded-server loop repair is repeatably green. No unresolved P0,
P1, or P2 finding remains. This verdict applies only to the exact 43-path frozen
content identity below and does not authorize push, PR, merge, Live ACRA, Production,
GoldTier/PingFed activity, or another product phase.

## 2. Reviewed Content Identity and Scope

| Identity | Independently established value |
|---|---|
| Repository/worktree | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm` |
| Branch | `feat/acra-marketplace-mock-runtime` |
| `HEAD` / base / `origin/main` / merge base | `f7e6f65dbcd927f8357c2876d5b8cf293ff81f18` |
| Candidate state before this report | 30 tracked modifications, 13 task-owned untracked files, 0 staged |
| Reviewed paths | 43 |
| Canonical prospective-index fingerprint | `0269b5053fe355524e9137d4fb99e86d3f37882bacf165b1044265cb78f3a9fe` |
| Fingerprint definition | SHA-256 over ordinal case-sensitive sorted lines `path<TAB>git hash-object --path=<path> <path>`, LF-joined with no terminal LF |
| Report exclusion | This final gate report is excluded; both earlier immutable FAIL reports are included |

The supplied frozen identity reproduced exactly before review. The current source
revision is still the base Git commit; behavioral evidence and this verdict apply to
the uncommitted working-tree fingerprint, not a feature commit.

Complete reviewed path set:

```text
.agents/skills/poc-regression-check/references/regression-catalogue.md
.ai-pipeline/reports/ACRA_API_MARKETPLACE_MOCK_RUNTIME_QUALITY_GATE.md
.ai-pipeline/reports/ACRA_API_MARKETPLACE_MOCK_RUNTIME_REQUALITY_GATE.md
.env.example
apps/backend/app/composition.py
apps/backend/app/config.py
apps/backend/app/connectors/acra.py
apps/backend/app/connectors/acra_api_marketplace_auth.py
apps/backend/app/connectors/acra_api_marketplace_mock.py
apps/backend/app/connectors/acra_bizfile_sandbox.py
apps/backend/app/connectors/acra_sandbox.py
apps/backend/app/main.py
apps/backend/app/services/clm_orchestration.py
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

## 3. Acceptance Checklist

| Requirement | Result | Direct evidence |
|---|---|---|
| 1. Official ACRA Mock external connection | **PASS** | Fresh bounded smoke reached only `api-sandbox.bizfile.gov.sg`; token, entity, shareholder, and schema-only capital calls returned sanitized HTTP 200 evidence. |
| 2. Garden Business official retrieval | **PASS** | Fresh entity call returned requested identity equality, strict schema pass, and approved Mock name `GARDEN BUSINESS`; configured application run used `api_marketplace_mock`. |
| 3. No synthetic fallback | **PASS** | Composition selects one explicit connector; no fallback branch exists. The configured Garden run stopped partial instead of substituting local Mock evidence. |
| 4. No synthetic Garden ownership relationship leakage | **PASS** | Garden shareholder call returned explicit empty evidence; `fetch_relationships` performs no provider call and returns no relationship; application stopped before target work. |
| 5. No invented ownership percentage | **PASS** | `shareAllotted` is exact Decimal source evidence only; every mapped provider party has `ownership_percentage=None`; fresh smoke reported no derived percentage. |
| 6. Token/credential non-leakage | **PASS** | Credentials are backend `SecretStr`; tokens are repr-suppressed and memory-only; errors are sanitized; supported direct secret scan passed; no raw payload or authorization value is retained. |
| 7. No Production host in active path | **PASS** | Active token/API constants contain only the fixed Mock host; source search found no Production ACRA host in the runtime path; production app mode rejects the Mock connector. |
| 8. No Bearer assumption | **PASS** | Token request uses HTTP Basic and downstream requests use the raw header named `token`; implementation search found no Bearer branch. |
| 9. TLS verification | **PASS** | Both token and provider clients use `ssl.create_default_context()`, disable redirects and environment proxy inheritance, and contain no `verify=False`. |
| 10. Truthful MOCK classification | **PASS** | Provider registry, source DTOs, application profile, receipt, docs, and smoke consistently classify the lane as `MOCK / MOCK_INTEROPERABILITY_OBSERVED`. |
| 11. Production/Live out of scope | **PASS** | Q-012 and current state retain all subscriber Sandbox, Production, and Live claims as open/not proved; no Live activation or smoke occurred. |
| 12. Repository regressions repeatably green | **PASS** | Reviewer: complete backend exit 0 at 100%, lifecycle repair 10/10, 275 non-contract repository tests, 44 contract tests, focused provider/evidence lanes, Ruff, mypy, checkers, and secret scan all green. Frozen work record also retains three consecutive exact-candidate backend runs. |

## 4. Contract and Integration Findings

### Severity findings

- **P0: none.**
- **P1: none.**
- **P2: none.**
- **P3 candidate findings: none.**

The previous operation/outcome finding is closed in both enforcement layers. The
Python validator maps each operation to its exact safe endpoint and permitted outcome;
the JSON Schema mirrors that binding. Reviewer-executed adversarial tests reject
capital-as-strict-success, entity-as-schema-only-success, and cross-operation endpoint
pairing. HTTP `404` is no longer treated as company absence; it fails closed as a
sanitized malformed response while Q-012 remains open.

The external dependency direction remains:

```text
fixed Mock transport -> strict source decoder/DTO -> existing registry adapter
  -> canonical evidence -> existing orchestration/ownership/target boundaries
```

The candidate extends the existing ACRA connector/composition owner. It does not add a
second registry router, ownership engine, target mapper, persistence owner, direct
route-to-Mongo access, direct ACRA-to-GoldTier mapping, or runtime BizFile composition.
No ADR is required for this bounded extension because owner and dependency direction
remain unchanged; D-054 and current architecture/state record the mode activation.

## 5. Tester and Adversarial Findings

### Independently executed evidence

| Command/evidence | Result |
|---|---|
| Frozen identity and path inventory | **PASS** — 43 paths, 0 staged, exact fingerprint reproduced |
| Official Mock auth/connector/mode/evidence focused pytest | **PASS** — 70 tests; one existing Starlette deprecation warning |
| External-provider readiness pytest on host-permission rerun | **PASS — 19 passed** |
| Candidate exact Phase 13 live-loopback test repeated | **PASS — 10/10** |
| Clean accepted-main exact loopback baseline repeated | **BASELINE_REPRODUCED — 16 passed, 4 timed out of 20** with traceback suppressed |
| Complete backend pytest | **PASS** — reached 100%, exit 0; duplicate quiet flags suppressed numeric summary; four known warning groups |
| Supported non-contract repository pytest | **PASS — 275 passed** |
| Full contract unittest discovery | **PASS — 44 passed** |
| Ruff over `apps/backend`, `scripts`, and `tests`, no cache | **PASS** |
| Strict mypy over backend app, no incremental cache | **PASS — 108 source files** |
| Project-state / architecture / policy-authority / provider-readiness checkers | **PASS** |
| Dedicated ACRA Marketplace Mock receipt validator | **PASS** |
| Direct supported-secret scan | **PASS** |
| Fresh official Mock smoke | **PASS** — fixed host, sanitized HTTP 200 JSON evidence, strict Garden identity, empty Garden shareholders, no percentage |
| Fresh configured process-level Garden application | **PASS** — `PARTIAL`, operation statuses `COMPLETE/COMPLETE/EMPTY/EMPTY`, `REVIEW_REQUIRED`, no GoldTier result |
| `git diff --check` and explicit untracked-file whitespace/conflict scan | **PASS** — no findings; Git emitted only configured LF/CRLF notices |

The first combined focused run was invalid only for the 19 readiness tests because the
Windows sandbox denied temporary-repository directory access. Their host-permission
rerun passed 19/19; the other 70 focused tests passed independently. A separate
operator invocation of `validate_external_provider_evidence.py` without its required
path produced usage text and supplied no evidence; the task-specific ACRA receipt
validator was invoked correctly and passed.

### Lifecycle regression closure

The clean accepted-main worktree independently reproduced four timeouts in twenty
isolated runs, confirming `BASELINE_REPRODUCED`. The candidate changes only the
in-thread Uvicorn test-server configuration to return `asyncio.SelectorEventLoop` on
Windows. The listener ownership, application networking, request timeout, server
startup deadline, worker shutdown deadline, one-backend/two-seeder flow, and all result
assertions remain unchanged. The diff adds no retry, skip, arbitrary sleep, timeout
inflation, assertion weakening, or production runtime branch. Ten consecutive reviewer
runs and the complete backend run were green.

### Environment-only note

The invalid sandboxed readiness invocation left 19 inaccessible `tmp*` directories in
the repository root. They contain no Git-visible candidate file and do not change the
43-path fingerprint or index. The reviewer's narrowly constrained cleanup request was
rejected by the execution safety layer, so no deletion workaround was attempted. This
is a local environment-cleanup item requiring explicit user-approved removal if desired,
not a candidate defect and not a publication-content finding.

No browser/E2E or physical Mongo run was required because this candidate changes no
frontend behavior or durable persistence schema. No Production ACRA, subscriber
Sandbox, provider mutation, raw payload capture, GoldTier/PingFed call, or Live proof
was attempted.

## 6. Code and Architecture Review

The official Mock authentication owner is cohesive: it validates dedicated credentials,
uses fixed HTTPS token authority, bounds body/time, strictly validates the observed
token schema, retains only an opaque cached token in memory, and projects stable safe
errors. The provider owner is separately cohesive: fixed read-only paths, strict token
header cardinality, strict status/content/body/identity checks, query-free provenance,
and explicit empty semantics.

The existing source DTO gained provider category/status/share-count evidence without a
second business owner. Counts reject binary floats and remain exact Decimal-compatible
values. The existing registry acquisition and ownership owners decide readiness; the
connector does not infer percentages, relationships, legal ownership, or UBO status.

The ordinary-test settings owner explicitly restores synthetic `mock` mode so local
developer environment selection cannot contaminate regression tests. The baseline
mypy findings were repaired with type-only enum/Literal annotations; no public API,
durable schema, persistence, frontend, business-rule, target mapping, authorization,
or approval behavior changed.

Change effects: internal source types, connector, configuration, external auth/security,
composition, provider status, evidence contract, and runtime behavior changed. Public
API shape, durable schema, target mapping, ownership calculation/business policy,
authorization/RBAC semantics, persistence ownership, and frontend behavior did not.

## 7. Security Review

No active security finding remains in the reviewed boundary.

- Fixed HTTPS hosts prevent caller-controlled endpoint selection, userinfo, fragments,
  secret query data, or Production-host drift.
- OS trust-store verification is explicit; redirects and `trust_env` are disabled for
  both Mock transports; time and response bodies are bounded.
- Credentials are backend-only and fail closed when missing. Tokens are never settings,
  fixtures, evidence, logs, error text, provenance, browser projections, or durable
  case history.
- Status, content type, byte count, JSON shape, required fields, and requested/returned
  identity are validated before canonical use. Raw provider bodies stop at the transport
  boundary.
- Errors expose fixed connector codes/messages rather than body, endpoint query,
  credential, token, or underlying exception details.
- The tracked receipt holds fixed safe operation metadata only: no UEN, name,
  authorization value, token, credential, raw payload, provider error detail, KYC/PII,
  or Production endpoint.
- Direct secret scanning passed. The reviewer did not read or print `.env`, credential,
  token, Postman, private sponsor, or raw provider content.

Deferred ACRA token-failure/error/not-found/rate/retry details, collection limits,
mTLS/private-CA requirements, complete mapping/relationship semantics, subscriber
Sandbox, Production, and Live security remain explicit Q-012 dependencies. They are
later authority gaps, not defects in this bounded Mock lane.

## 8. Required Fixes

**None.**

The two historical reports remain immutable FAIL evidence and are not upgraded in
place. Their required receipt-binding, unsupported-404, and repeatable-backend closures
were independently verified on this new frozen identity.

The environment-only inaccessible temporary directories are not candidate content and
require no source remediation. Their removal, if desired, is a separate local cleanup
action subject to explicit approval.

## 9. Readiness

- **Independent gate:** **PASS** for the exact frozen candidate.
- **Local publication step:** ready for the coordinator's separately authorized scoped
  local commit and clean-state pre-PR checks, provided reviewed content is unchanged.
- **Push / PR / merge:** not performed and not authorized by this gate.
- **Bounded Official ACRA API Marketplace Mock runtime:** ready as explicit opt-in
  `MOCK_INTEROPERABILITY_OBSERVED` with truthful partial Garden outcome.
- **Next product phase:** not authorized.
- **Subscriber Sandbox / Production / Live ACRA:** **NOT READY / NOT CLAIMED**.
- **Real GoldTier/PingFed and Ready-for-Approval:** unchanged and **NOT READY**.

## 10. Git Status and Reviewer Boundary

At review freeze, the candidate had 30 tracked modifications, 13 task-owned untracked
files, and no staged file. This Quality Gate created only:

`.ai-pipeline/reports/ACRA_API_MARKETPLACE_MOCK_RUNTIME_FINAL_QUALITY_GATE.md`

The two prior gate reports were retained unchanged. No implementation, test,
configuration, contract, decision, ordinary documentation, schema, evidence receipt,
index entry, or reviewed Git path was changed by this reviewer. Excluding this report,
the implementation path set and fingerprint remain the exact recorded 43-path identity.

No commit, stage, push, PR, merge, rebase, stash, reset, clean, branch switch, provider
mutation, Production/Live call, GoldTier/PingFed call, or next phase occurred.
