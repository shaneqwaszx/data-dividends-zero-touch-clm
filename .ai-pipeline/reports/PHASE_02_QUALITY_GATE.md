# Phase 02 Quality Gate

## Executive Result

PASS

The final post-remediation gate closes every previous Phase 02 HIGH, MEDIUM, and LOW
finding. Required source strings can no longer pass as semantically blank, canonical
minimums independently stop malformed future connector output, connector error text is
projected through fixed trusted mappings, the smoke script is import-safe, browser
responses omit the internal registry endpoint, and status translations are explicitly
provisional pending Q-012.

Final sign-off confirms the remaining LOW optional-field finding is closed. Blank or
whitespace-only `unit` and `buildingName` values normalize to `None`; the canonical
mapper emits `address_line_2=None` when neither value is meaningful; unit-only,
building-only, and combined populated values retain the expected mapping; and the
mapping contract now explicitly documents `entityStatus` trimming.

## Phase 02 Acceptance Checklist

| Requirement | Result | Evidence |
|---|---|---|
| Required ACRA source strings are trimmed and reject empty-after-trim values | PASS | `NonBlankSourceText` is applied to UEN, name, company country, entity type, and supplied-address block/street/postal/country in both project response and source DTO models; 16 empty/whitespace adversarial cases passed. |
| Optional address parts normalize without empty canonical values | PASS | `OptionalSourceText` trims `unit`/`buildingName` and converts empty-after-trim to `None`; five focused combinations prove `address_line_2=None`, unit-only, building-only, and combined mappings. |
| Malformed required source data terminalizes safely | PASS | All application-level required-field injections returned HTTP 503 with `ACRA_MALFORMED_RESPONSE`, persisted retrievable `FAILED`, and made zero GoldTier calls. |
| Invalid source values/raw bodies do not leak | PASS | Fixed malformed-response output contains no source validation details; raw response bodies are not persisted or logged. |
| Canonical defense is independent of the current decoder | PASS | Seven whitespace-valued canonical minimums were injected through a mapper replacement; every case stopped at `REVIEW_REQUIRED` before GoldTier. |
| Connector/auth error output is structurally sanitized | PASS | Authentication, timeout, unavailable, hostile subclass, and generic private sentinels were absent from HTTP and persisted history; public fields came from the trusted mapping. |
| Optional smoke script is import-safe and opt-in | PASS | Disabled, missing/invalid configuration, and safe injected-success paths produced status-only output without traceback, UEN, configuration, credentials, headers, or payloads; CI does not call the script. |
| Internal provenance retains the registry reference | PASS | Canonical `SourceMetadata` retains `source_system=ACRA`, separate `MOCK`/`SANDBOX`, query-free `registry_source_link`, and UTC sourcing time. |
| Browser/API minimizes registry provenance | PASS | Dedicated browser response models omit `registry_source_link`; create/get responses and frontend types contain only source system, environment, and sourcing time. |
| Current HTTP/error translations are clearly provisional | PASS | Code comment and architecture document label them **PROJECT-DEFINED PROVISIONAL ADAPTER POLICY** pending Q-012 and do not claim official ACRA semantics. |
| Mock mode remains safe default | PASS | Default composition selects unchanged `MockAcraConnector`, requires no ACRA settings/credentials, and performs no network access. |
| Sandbox-shaped composition remains replaceable | PASS | Injected transport/authorizer/decoder use the same `AcraConnector` and existing `OnboardingService`; synthetic success reaches Mock GoldTier. |
| Phase 01 scenarios retain their exact outcomes | PASS | `COMPLETED`, `REVIEW_REQUIRED`, `FAILED`, `REVIEW_REQUIRED`, `FAILED` for the five required UENs. |
| GoldTier remains mock-only and Phase 03 scope is absent | PASS | Composition uses only `MockGoldTierConnector`; no PingFed, IDP/OCR/PDF, UBO, related-party, hierarchy, Ready-for-Approval, worker, database, or Camunda runtime was introduced. |
| Full configured validation passes | PASS | Final sign-off: backend 108/108, contract 15/15, frontend 8/8, focused optional-field 9/9, Ruff, and strict mypy all passed; the earlier full repository/security/dependency/whitespace gate remains passing. |
| Live ACRA interoperability verified | BLOCKED | Q-012 still lacks the authoritative subscribed endpoint/path, schema, authentication, error/not-found semantics, access, credentials, rate limits, and TLS/mTLS/private-CA requirements. |

## ACRA Integration Readiness

**ACRA connector implementation: READY**

The implementation is safe and replaceable behind `AcraConnector`. Final subscribed
details can be implemented mainly inside connection/configuration, transport,
authorizer, decoder, source DTO, mapper, and composition boundaries without rewriting
the onboarding workflow, GoldTier orchestration, or frontend workflow logic. The final
optional-field cleanup preserves this boundary and canonical integrity.

**Live ACRA sandbox verification: BLOCKED**

No authorized live call was made. Q-012, including the approved-access requirement it
records, remains the sole external live-verification blocker; this does not fail the
Phase 02 mock/adapter implementation.

## Previous Finding Closure

| Previous finding | Severity | Final status | Closure evidence |
|---|---:|---|---|
| Blank/whitespace required source fields could complete and execute GoldTier | HIGH | CLOSED | Trim/nonblank source constraints plus 16 decoder and 16 application-level cases; all rejected, terminal `FAILED`, retrievable, zero GoldTier. |
| Typed connector errors could expose arbitrary adapter text | MEDIUM | CLOSED | Constructor input is private context; service uses fixed trusted type-to-public mappings. Authentication/timeout/unavailable and hostile-subclass sentinels did not leak. |
| Smoke script could compose the app before its guard | LOW | CLOSED | Composition moved to a side-effect-free module; guard runs before settings/connector construction; invalid configuration produces sanitized `FAILED` only. |
| Browser received the full registry endpoint/reference | LOW | CLOSED | Internal model retains the reference; browser response DTO and frontend types omit it. |
| Status mappings were not locally labelled provisional | LOW | CLOSED | Architecture and connector now state the current mappings are project-defined provisional behavior pending Q-012. |
| Optional address fields could produce `address_line_2=""` and status trimming was under-documented | LOW | CLOSED | Optional source text now normalizes blank-after-trim to `None`, the mapper emits `None` when no line-2 parts remain, populated mappings pass, and the contract explicitly documents `entityStatus` trimming. |

## Contract / Source Findings

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

None.

The final LOW finding is closed. `OptionalSourceText` applies a pre-validation trim and
converts empty results to `None` at both provisional decoder and source DTO boundaries.
The mapper independently joins only meaningful optional address parts and falls back to
`None`. The contract table now says `entityStatus` is trimmed before the remaining
source text is preserved, without adding status enum assumptions.

All required mapping rows accurately record source, canonical target, transformation,
requiredness, confidence/evidence, and confirmation need. The response envelope,
property names, authorizer, and status mappings remain clearly synthetic/project-owned,
not an ACRA-published subscriber contract. Q-012 remains unresolved. Officer,
shareholder, document, ownership, UBO, and relationship information remains outside
Phase 02.

## Tester Findings

### Configured commands and results

| Check | Result |
|---|---|
| `.venv\Scripts\python.exe -B -m pytest apps/backend/tests -p no:cacheprovider` | PASS — 108 tests |
| Final optional-field/mapping sign-off subset | PASS — 9/9 |
| Ruff over `apps/backend`, `scripts`, and `tests` | PASS |
| Strict mypy over `apps/backend/app` | PASS — 25 source files |
| Contract tests | PASS — 15/15 |
| Repository regression tests | PASS — 25/25 |
| Phase 01 backend subset | PASS — 26/26 |
| Original Phase 02 ACRA subset | PASS — 26/26 |
| Remediation adversarial suite | PASS — 44/44 |
| Smoke-script suite | PASS — 4/4 |
| Secret-scanner tests | PASS — 5/5 |
| Phase 00 validator regression | PASS — 5/5 |
| Sponsor GoldTier example validator | PASS — 19 valid, 19 invalid/quarantined, 48 not validated |
| Sponsor validator `--fail-on-invalid` | Expected exit 1 confirmed |
| Secret scanner | PASS |
| `pip check` | PASS — no broken requirements |
| `npm.cmd ls --all` | PASS — dependency tree intact; optional packages absent as expected |
| Frontend typecheck | PASS |
| Frontend Vitest | PASS — 1 file, 8 tests |
| Frontend production build | PASS — 28 modules transformed to a temporary output directory |
| `git diff --check` | PASS — CRLF conversion warnings only |
| `git diff --cached --check` | PASS |
| Equivalent untracked-file whitespace checks | PASS — 16 files |

Frontend test/build commands required approved execution because the local esbuild
subprocess is restricted by the normal sandbox. The approved reruns passed. No required
check was skipped. Hosted GitHub Actions was not invoked.

### Adversarial source and canonical results

- Eight required source paths were independently tested with both empty and
  whitespace-only input: UEN, entity name, company country, entity type, address block,
  street, postal code, and address country.
- All 16 decoder cases and all 16 accepted-case paths were rejected as
  `ACRA_MALFORMED_RESPONSE`; each accepted case was retrievable as terminal `FAILED`,
  with no traceback/raw source detail and zero GoldTier calls.
- Trimmed-valid values decoded to the normalized source DTO.
- Seven canonical minimums were independently set to whitespace: registration number,
  legal name, country, party type, address line 1, postal code, and address country.
  Every case stopped at `REVIEW_REQUIRED` before any GoldTier call.

### Failure injection

| Injection | HTTP / safe code | Persisted result | GoldTier after failure |
|---|---|---|---|
| Configuration | 503 / `ACRA_CONFIGURATION_ERROR` | Retrievable `FAILED` | None |
| Authorization | 503 / `ACRA_AUTHENTICATION_ERROR` | Retrievable `FAILED` | None |
| Timeout | 503 / `ACRA_TIMEOUT` | Retrievable `FAILED` | None |
| Service unavailable | 503 / `ACRA_SERVICE_UNAVAILABLE` | Retrievable `FAILED` | None |
| Not found | 201 / `ACRA_ENTITY_NOT_FOUND` | Retrievable `FAILED` | None |
| Malformed response | 503 / `ACRA_MALFORMED_RESPONSE` | Retrievable `FAILED` | None |
| Decoder failure | 503 / `ACRA_MALFORMED_RESPONSE` | Retrievable `FAILED` | None |
| Source mapping failure | 503 / `ACRA_SOURCE_MAPPING_FAILED` | Retrievable `FAILED` | None |
| Unexpected transport | 503 / `ACRA_CONNECTOR_UNEXPECTED_FAILURE` | Retrievable `FAILED` | None |
| Unexpected connector | 503 / `ACRA_RETRIEVAL_UNEXPECTED_FAILURE` | Retrievable `FAILED` | None |

Private authentication, timeout, unavailable-service, hostile-subclass, and generic
connector sentinels were absent from HTTP output and persisted case/event history.

### Mode, regression, isolation, and smoke results

- Mock mode stayed credential-free/network-free and produced:
  `202400001A -> COMPLETED`, `202400002B -> REVIEW_REQUIRED`,
  `202400003C -> FAILED`, `202400004D -> REVIEW_REQUIRED`, and
  `999999999Z -> FAILED`.
- Sandbox-shaped synthetic success followed transport -> provisional decoder ->
  `AcraCompanyPayload` -> ACRA mapper -> canonical entity -> existing
  `OnboardingService` -> Mock GoldTier and completed with `ACRA/SANDBOX`, UTC time, and
  an internal case-specific reference. This is not live-contract evidence.
- Multiple-case isolation passed with unique IDs/references/timestamps and no failed
  case contaminating later successes.
- Live smoke: **NOT EXECUTED / BLOCKED**. Disabled and invalid-config probes, plus a
  safe fake success, were exercised without external network access.

Tester severity findings: no CRITICAL, HIGH, MEDIUM, or LOW findings.

## Code & Architecture Review

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

None.

### Architectural assessment

| Area | Result | Assessment |
|---|---|---|
| Adapter replaceability | PASS | Endpoint/path/auth/schema changes remain localized to adapter boundaries; `OnboardingService` still depends only on `AcraConnector`. |
| Transport/auth/decoder boundaries | PASS | Small injectable seams isolate unknown Q-012 details without a speculative framework. |
| Source DTO vs canonical model | PASS | Models remain separate and source-neutral. Required semantics are enforced, and blank optional address text cannot create an empty canonical line 2. |
| Error boundary | PASS | HTTP-library behavior and private connector context do not enter business/API errors. |
| Configuration composition | PASS | Deterministic, centralized, mock-default, backend-only, and fail-closed for invalid sandbox settings. |
| Provenance | PASS | ACRA identity, separate environment, query-free internal reference, and UTC time support later proof mapping; browser projection minimizes the reference. |
| Phase 01 stability | PASS | Workflow states, terminalization, search semantics, repository isolation, and original scenarios remain stable. |
| Scope discipline | PASS | No real GoldTier, PingFed, Phase 03 IDP/document, UBO, hierarchy, worker, database, or additional-registry implementation. |

## Architecture Questions

1. **Can final ACRA endpoint/auth/schema still be implemented mainly inside the ACRA
   adapter boundaries?** Yes. Connection/configuration, transport, authorizer, decoder,
   source DTO, mapper, and composition contain the unknown binding.
2. **Can semantically malformed required source data reach GoldTier?** No. The current
   decoder/source DTO rejects it as malformed, terminalizes the case, and performs no
   GoldTier work.
3. **Can a future connector bypass source validation and still cause false completion
   through malformed canonical required values?** No in the tested business invariant.
   Canonical validation independently diverts whitespace-valued required minimums to
   `REVIEW_REQUIRED` before GoldTier.
4. **Can a future connector/authorizer leak arbitrary exception text through a typed
   error?** No through the recognized boundary. Constructor context is private and the
   service derives public fields from fixed trusted type mappings; unknown connector
   errors receive a fixed generic projection.
5. **Is the full registry endpoint/reference retained internally but minimized from
   browser output?** Yes.
6. **Does any recognized source failure leave a nonterminal case?** No. Every injected
   recognized connector/decoder/mapping failure persisted retrievable terminal
   `FAILED` and stopped downstream work.
7. **Has Phase 01 behavior regressed?** No.

## Security Review

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

None active.

The previous typed-error, smoke-import, and browser-endpoint security findings are
closed. No tracked ACRA credential, token, authorization value, raw live payload, or
private sponsor artefact was found. Frontend configuration remains non-secret. The
transport enforces HTTPS, certificate verification, disabled redirects, and bounded
timeouts; endpoint userinfo/query/fragment and header CRLF are rejected. CI remains
credential-free and excludes the smoke script. GoldTier quarantined authentication
material remains unused. Synthetic fixtures are explicitly labelled and contain no
real customer/sponsor data.

The current ACRA transport verifies TLS but does not claim to impose TLS 1.3. ACRA's
minimum TLS/mTLS/private-CA requirements remain a Q-012 pre-live binding question, not a
Phase 02 defect. Confirmed GoldTier TLS 1.3 requirements remain outside this mock-only
phase.

## Accepted Phase 02 Technical Debt

- Q-012 authoritative subscribed ACRA endpoint/path, request/response and error
  schemas, authentication, access, credentials, rate limits, and TLS details are not
  available.
- Live ACRA sandbox smoke verification is not executed.
- The current decoder and status policy remain synthetic/project-defined pending the
  authoritative contract.
- Cases remain process-local/in-memory and orchestration remains synchronous.
- GoldTier remains fully mocked.
- No retry engine, database, queue/worker, or full exception workbench exists.
- History/archive/entropy secret scanning, immutable CI action pins, formal
  vulnerability auditing, and SBOM generation remain deferred hardening.

## Final Sign-Off Closure

The remaining LOW finding is closed without regression:

- empty and whitespace-only optional `unit`/`buildingName` -> source `None`;
- neither meaningful value -> canonical `address_line_2=None`;
- unit-only -> trimmed unit;
- building-only -> trimmed building name;
- both populated -> `unit, buildingName`;
- `entityStatus` -> surrounding whitespace trimmed and remaining source text preserved,
  as documented;
- Phase 01 five-scenario outcomes and sandbox-shaped Phase 02 composition remain
  unchanged;
- no Phase 03 runtime scope was introduced.

## External / Sponsor Blockers

### A. Blocking live ACRA verification

- Q-012 authoritative subscribed base URL and company-by-UEN path.
- Request/response, not-found, and error schemas/semantics.
- Authentication/authorization and rate-limit/timeout requirements.
- Authorized subscription/account, network access, and approved credential delivery.
- Confirmed TLS version, mTLS, private-CA, and gateway requirements.

### B. Needed for Phase 03 IDP

- Q-003 exact document types and fields for the IDP demo.
- Approved privacy, fixture, retention, confidence, and human-review rules.
- Q-005 where the EDS/GoldTier validation responsibility split affects Phase 03.

### C. Needed for later UBO/hierarchy

- Q-002 seeded hierarchy retrieval contract.
- Q-004 configurable UBO threshold.
- Q-006 direct related-party semantics.
- Q-007 sponsor-approved Singapore mappings/value lists.

### D. Blocking real GoldTier

- Q-008/D-018 credential containment, rotation/revocation confirmation, sanitized
  reference material, and fresh approved credentials.
- PingFed/token URLs, scopes, client-auth method, TLS 1.3, mTLS/private-CA, and sandbox
  networking details.
- Remaining contract/value-list/example corrections and Ready-for-Approval semantics.

## Phase 03 Recommendation

READY FOR PHASE 03

The architecture and safety invariants are ready for Phase 03 without redesign. This
sign-off does not begin or implement Phase 03.

**Real GoldTier integration: NOT READY**

GoldTier correctly remains mock-only. Real integration remains blocked by approved
credentials/access, PingFed and TLS 1.3 binding, contract/value-list confirmation, and
later workflow semantics.

## Git Status

- Current branch: `phase/02-acra-ingestion`
- HEAD before/after gate: `c1eb10b` (`Phase 01 — Mocked End-to-End Onboarding Vertical Slice (#2)`)
- Modified tracked files: 24
- Untracked files: 16, including this overwritten report
- Staged files: none
- Commits performed: none
- Push performed: no
- Merge performed: no
- Application/test/document changes by this gate: none
- Only file modified by this gate: `.ai-pipeline/reports/PHASE_02_QUALITY_GATE.md`
