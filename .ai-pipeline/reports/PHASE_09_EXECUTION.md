# 1. Executive Summary

Phase 09 establishes a source-aware jurisdiction decision gateway before registry
acquisition while preserving the existing Singapore/ACRA POC path. Optional user input
and explicit Singapore UEN-format evidence are retained as independent observations.
Agreement resolves; absence and conflict stop safely without guessing. Only Singapore
selects the existing ACRA implementation; recognised Australia, Malaysia, and Hong Kong
requests stop as provider not implemented.

The ACRA implementation is now consumed through a provider-neutral registry interface
and adapter. Its strict source DTO reconstruction, requested/returned UEN binding,
canonical mapping, provenance, not-found behavior, safe technical errors, and existing
mock/sandbox connector selection remain intact. No foreign registry, expanded ACRA
dataset, MongoDB persistence, document-first reorder, ACRA+, or live-provider switch was
added.

Final verification is clean: 523 backend tests, 45 frontend tests, 44 contract tests, 5
secret-unit tests, and 13 Windows lifecycle tests passed, with lint, strict typing,
production build, secret scan, dependency checks, and sponsor-example validation also
passing.

# 2. Scope Implemented

- Added bounded jurisdiction codes `SG`, `AU`, `MY`, and `HK`.
- Added source-aware observations with source, UTC time, safe evidence reference, and
  optional confidence.
- Added deterministic `RESOLVED`, `UNRESOLVED`, and `CONFLICT` outcomes with no source
  precedence.
- Added explicit omitted-country compatibility: accepted Singapore UEN format produces
  `IDENTIFIER_FORMAT -> SG`.
- Added provider-neutral `RegistryProvider`, Singapore ACRA adapter, and closed backend
  router.
- Added controlled `JURISDICTION_UNRESOLVED`, `JURISDICTION_CONFLICT`, and
  `REGISTRY_PROVIDER_NOT_IMPLEMENTED` case/exception outcomes.
- Propagated optional `country_of_incorporation` through onboarding, CLM, zero-touch,
  API, and frontend boundaries.
- Added truthful frontend selection and decision/provenance display.
- Added sponsor-readable ACRA mock/API profile and Phase 09 architecture documentation.
- Added Phase 09 regression tests and evolved the accepted POC regression catalogue.

# 3. Files Changed

Phase 09 implementation files:

- `apps/backend/app/domain/jurisdiction.py` — new evidence, resolution, and routing
  models plus deterministic resolver.
- `apps/backend/app/connectors/registry.py` — new provider-neutral interface, ACRA
  adapter, and router.
- `apps/backend/app/connectors/errors.py` — trusted adapter-boundary ACRA errors.
- `apps/backend/app/domain/models.py` — case-owned jurisdiction resolution and route.
- `apps/backend/app/domain/zero_touch.py` — typed registry exceptions and safe evidence.
- `apps/backend/app/services/onboarding.py` — pre-registry resolution/routing and
  provider-neutral acquisition.
- `apps/backend/app/services/clm_orchestration.py` and
  `apps/backend/app/services/zero_touch_orchestration.py` — input propagation, typed
  blocker projection, and pre-IDP stopping.
- `apps/backend/app/composition.py` — explicit ACRA adapter/router composition around
  the unchanged mock/sandbox connector factory.
- `apps/backend/app/main.py` and `apps/backend/app/api_models.py` — bounded request and
  safe browser response contract.
- `apps/frontend/src/App.tsx`, `api.ts`, `types.ts`, and `styles.css` — selector,
  serialization, decision display, and blocked-upload stopping.
- `apps/backend/tests/test_phase09_jurisdiction_gateway.py` and
  `apps/frontend/src/App.test.tsx` — new gateway/API/UI regression coverage.
- `apps/backend/tests/test_onboarding_resilience.py` and
  `apps/backend/tests/test_phase02_remediation.py` — existing adversarial mapper tests
  retargeted from the former orchestration location to the new ACRA adapter seam.
- `README.md`, `docs/architecture/ARCHITECTURE.md`,
  `docs/architecture/README.md`, `docs/architecture/PHASE_09_JURISDICTION_GATEWAY.md`,
  `docs/contracts/README.md`, `docs/contracts/ACRA_MOCK_API_PROFILE.md`,
  `docs/decisions/DECISION_LOG.md`, and
  `docs/sponsor-questions/OPEN_QUESTIONS.md` — current architecture, contract,
  decision, and sponsor-dependency truth.
- `.agents/skills/poc-regression-check/references/regression-catalogue.md` — Phase 09
  accepted scenarios and superseding registration-identifier input rule.

The branch already contained uncommitted/untracked Mongo remediation, baseline, quality
gate, fixture-attribute, and UI documentation work before Phase 09. It was preserved and
not attributed to this phase. No commit, push, merge, rebase, stash, reset, or clean was
performed.

# 4. Jurisdiction Domain Model

`JurisdictionObservation` contains:

- `jurisdiction`: recognised bounded code;
- `source`: `USER_INPUT`, `IDENTIFIER_FORMAT`, or a named future evidence source;
- `observed_at`: timezone-aware UTC;
- `source_reference`: bounded safe evidence reference;
- `confidence`: optional `[0,1]`, unused for deterministic active sources.

`JurisdictionResolution` retains all observations, resolution status, optional resolved
jurisdiction, and UTC decision time. Its validation forbids a resolved result without
evidence and forbids a selected jurisdiction for unresolved/conflicting results.

Future source names `EXISTING_CASE`, `DOCUMENT_IDP`, and `UPSTREAM_SYSTEM` are modelled
but not populated. This supports later evidence intake without claiming those data paths
exist now.

# 5. Resolution Rules

The resolver is deterministic and source-neutral:

1. No observation -> `UNRESOLVED`, no selected jurisdiction.
2. One observation -> `RESOLVED` to its jurisdiction.
3. Multiple observations with one unique jurisdiction -> `RESOLVED`; every observation
   remains retained.
4. Multiple unique jurisdictions -> `CONFLICT`, no selected jurisdiction.

Insertion order and source type never select a winner. The active request can therefore
represent user/document/system disagreement later without embedding an authority rule.

# 6. Omitted-Input Compatibility Rule

When `country_of_incorporation` is omitted and the identifier matches the accepted
synthetic Singapore UEN pattern (nine digits and one letter), onboarding records an
explicit `IDENTIFIER_FORMAT -> SG` observation. Existing calls such as `202400001A`
continue through ACRA unchanged.

The rule is visible in the domain/API and is not a default country. A non-matching
bounded identifier with no country creates an unresolved-jurisdiction case. Explicit SG
plus SG-format inference produces two agreeing observations. Explicit AU plus an
SG-format identifier produces a conflict.

# 7. Registry Router

The backend-owned closed table is:

| Jurisdiction | Routing result | Provider |
|---|---|---|
| SG | `SELECTED` | ACRA |
| AU | `PROVIDER_NOT_IMPLEMENTED` | None |
| MY | `PROVIDER_NOT_IMPLEMENTED` | None |
| HK | `PROVIDER_NOT_IMPLEMENTED` | None |

The router accepts a trusted enum, never a URL, module, class name, credential, or
caller-selected connector. No ASIC, SSM, Hong Kong Companies Registry, or other foreign
integration exists.

# 8. ACRA Adapter / Compatibility

`AcraRegistryProviderAdapter` wraps the existing `AcraConnector` and returns a canonical
entity. It preserves:

- existing `MockAcraConnector` / `AcraSandboxConnector` selection;
- one `fetch_company(uen)` call;
- fresh strict `AcraCompanyPayload` reconstruction, including nested data;
- requested and returned normalized UEN equality;
- source-to-canonical `map_acra_company` transformation;
- business source `ACRA`, `MOCK`/`SANDBOX` environment, internal query-free HTTPS proof,
  and UTC retrieval time;
- `None` -> `ACRA_ENTITY_NOT_FOUND`;
- existing connector errors and adapter-specific safe response/identity/mapping errors.

Canonical minimum validation remains in onboarding after adapter mapping. Existing ACRA
mock scenario behavior and Singapore GoldTier mapping are unchanged.

# 9. API Changes

Case-creation requests now accept:

```json
{
  "uen": "202400001A",
  "country_of_incorporation": "SG"
}
```

`country_of_incorporation` is optional and enum-bounded. The existing `uen` property is
retained for compatibility but now accepts a bounded uppercase alphanumeric/hyphen
registration identifier of 1–32 characters so a foreign identifier can reach the
gateway without being treated as an ACRA UEN. Blank, over-length, unknown country, extra
property, and invalid-character requests remain rejected.

Browser case responses expose resolution status, resolved jurisdiction, observations,
safe evidence references, route status, and selected provider. They exclude internal
ACRA source links, endpoints/configuration, credentials, raw payloads, dynamic provider
details, and authority digests.

# 10. Frontend Changes

The start form offers:

- Not specified;
- Singapore;
- Australia — provider not implemented;
- Malaysia — provider not implemented;
- Hong Kong — provider not implemented.

The form labels the identifier as “Company registration identifier / UEN” and sends the
country only when selected. `JurisdictionDecision` displays the backend-authored outcome,
provider decision, and observation sources. Foreign/unresolved/conflicting cases show
the Registry-stage blocker rather than claiming progress.

The existing combined Start journey still requires a local synthetic PDF selection, but
the file is not uploaded when case creation returns a Registry blocker. The backend also
refuses document processing for such a case, so frontend behavior is not the security or
workflow authority.

# 11. ACRA Mock API Specification

`docs/contracts/ACRA_MOCK_API_PROFILE.md` now specifies the actual monolithic retrieval
operation, request binding, retrievable identity/profile/address fields, internal/browser
provenance split, all six synthetic UEN fixtures, not-found and safe error semantics,
and explicit limitations.

The current operation retrieves no officers/directors, shareholders, related parties,
relationships, ownership percentages/graphs, UBO conclusions, documents, or business
activities. Current ownership evidence comes from the separate synthetic ownership
provider. Every future ACRA-to-GoldTier field/value mapping remains `TBD_SPONSOR`.

# 12. Call-Stopping Behaviour

Verified outcomes:

| Scenario | Actual result | Calls |
|---|---|---|
| Omitted country + SG UEN | `RESOLVED/SG`, `PENDING_INPUTS` at Document | ACRA once; no later call before PDF |
| Explicit SG + SG UEN | Two agreeing observations; same checkpoint | ACRA once |
| Explicit AU + SG UEN | `WAITING_FOR_REVIEW/JURISDICTION_CONFLICT` at Registry | Zero ACRA/IDP/ownership/GoldTier |
| AU identifier + AU | `WAITING_FOR_REVIEW/REGISTRY_PROVIDER_NOT_IMPLEMENTED` | Zero ACRA/IDP/ownership/GoldTier |
| Unknown identifier + no country | `WAITING_FOR_REVIEW/JURISDICTION_UNRESOLVED` | Zero provider/downstream calls |
| PDF attempt on registry blocker | Existing blocked case returned; zero document records | Zero IDP/ownership/GoldTier |

Target evidence truthfully reports all four GoldTier operations as `NOT_ATTEMPTED`, not
as an empty or successful sequence. Cases remain retrievable. No new resolution action
is advertised.

# 13. Security Review

The repository integration-security checklist was applied.

- Provider selection is backend-controlled and fail-closed.
- Country/identifier inputs are normalized, length/grammar/enum bounded, and cannot
  control URLs, imports, classes, headers, or credentials.
- ACRA result reconstruction, original control-character rejection, identity binding,
  HTTPS provenance validation, and canonical mapping remain mandatory.
- Safe public error allowlisting was extended for adapter failures; raw exceptions are
  not projected.
- Internal ACRA source links and connector configuration remain out of browser models.
- Observations use fixed safe references and contain no document bytes/raw payloads.
- No new log statement or KYC/PII retention was added.
- Mock/sandbox labels remain truthful; no result claims live ACRA, foreign-provider, real
  GoldTier, legal UBO, approval, or Ready-for-Approval status.
- No secret-bearing file or dependency change was introduced.

# 14. Tests and Exact Results

Final commands/results:

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest apps\backend\tests` | PASS — 523 passed, 1 Starlette/httpx deprecation warning |
| `.\.venv\Scripts\python.exe -m pytest apps/backend/tests/test_phase09_jurisdiction_gateway.py -q -p no:cacheprovider` | PASS — 14 passed, same deprecation warning |
| `.\.venv\Scripts\python.exe -m ruff check apps/backend/app apps/backend/tests tests/contract` | PASS |
| `.\.venv\Scripts\python.exe -m mypy apps/backend/app` | PASS — 59 source files |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests\contract -p "test_*.py"` | PASS — 44 tests |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_check_secrets.py"` | PASS — 5 tests |
| `.\.venv\Scripts\python.exe -m unittest tests.test_demo_lifecycle_windows -v` | PASS — 13 tests in 179.566s; run with required process-management permission |
| `.\.venv\Scripts\python.exe scripts\check_secrets.py` | PASS — no supported secret patterns |
| `.\.venv\Scripts\python.exe -m pip check` | PASS — no broken requirements |
| `.\.venv\Scripts\python.exe scripts\validate_goldtier_examples.py --if-present` | PASS — expected 19 valid, 19 invalid/quarantined, 48 not validated |
| `npm.cmd run typecheck` in `apps/frontend` | PASS |
| `npm.cmd test` in `apps/frontend` | PASS — 45 tests |
| `npm.cmd run build` in `apps/frontend` | PASS — 29 modules, production assets built |
| `npm.cmd ls --all` in `apps/frontend` | PASS (exit 0); expected platform/feature optional dependencies shown unmet |
| `git diff --check` | PASS — no whitespace errors; only Git line-ending notices |

Intermediate verification findings were resolved before the final run:

- seven older mapper-bypass tests failed because they patched the pre-adapter module;
  they now patch `app.connectors.registry.map_acra_company`, and the 523-test suite passes;
- an attempted Vitest `--runInBand` option was unsupported; the documented `npm test`
  command passes;
- sandboxed Vitest/build initially could not spawn bundled `esbuild`; permissioned
  documented reruns pass;
- the sandboxed Windows lifecycle run could not terminate its exact temporary process.
  The repository's verified stop script removed the retained process, and the permissioned
  lifecycle rerun passed all 13 tests with final cleanup.

# 15. Sponsor Assumptions Preserved

- Singapore/ACRA remains the only implemented corporate registry path.
- No source authority is inferred when jurisdiction observations disagree.
- ACRA subscribed transport/schema/auth details remain Q-012.
- Source confidence/precedence and reviewer authority remain Q-015.
- Existing document auto-clear, ownership threshold/UBO, related-party, existing-party,
  partial-target, and Ready-for-Approval assumptions remain provisional/open.
- `COMPLETED` still means only credential-free Mock GoldTier submission, never approval.
- GoldTier mappings derived from candidate artefacts remain provisional; expanded ACRA
  fields are `TBD_SPONSOR`.

# 16. Non-Goals Confirmation

Not implemented:

- ASIC, SSM, Hong Kong, or any other foreign connector;
- synthetic ACRA+ provider;
- expanded ACRA officer/shareholder/ownership operations or fixtures;
- new mock/sandbox/live switching;
- document-first jurisdiction extraction or source precedence;
- jurisdiction conflict resolution/retry/restart workflow;
- MongoDB application persistence or migration;
- ownership/UBO calculation changes;
- real GoldTier/PingFed integration, related-party writes, or Ready-for-Approval;
- broad workflow/state-machine rewrite.

# 17. Remaining Risks

- **HIGH — Sponsor authority:** Q-015 must define source precedence, conflict resolution,
  reviewer authority, and resumption before a human resolution action is safe.
- **HIGH — Live ACRA contract:** Q-012 still blocks exact sandbox/live binding and any
  expanded retrieval operation.
- **MEDIUM — Process-local durability:** jurisdiction evidence, cases, and replay guards
  remain in memory. Restart loses them; the Mongo change present on the branch remains
  connectivity-only.
- **MEDIUM — API naming:** the compatibility property remains `uen` even when it carries
  a bounded foreign registration identifier. A later versioned contract may need a
  neutral name without breaking existing clients.
- **MEDIUM — Future evidence volume:** browser exception evidence is intentionally
  bounded to four items while the case retains up to eight observations. A future
  multi-source design must define safe pagination/summary behavior.
- **LOW — UI input sequence:** the combined UI asks the user to select a PDF before
  creating even a case that will stop at Registry; it does not upload/process that PDF
  when blocked.
- **LOW — Deprecation warning:** tests report the pre-existing Starlette TestClient/httpx
  deprecation warning. No dependency upgrade was authorized in this phase.

# 18. Readiness

The bounded Phase 09 planner requirements are implemented and verified. The branch is
ready for an independent Phase 09 quality gate. That gate should pay particular
attention to the widened registration-identifier API grammar, browser-safe evidence
projection, no-call guarantees for all registry blockers, preservation of strict ACRA
adversarial tests at the new adapter seam, and the explicit Q-015 no-precedence boundary.

READY FOR PHASE 09 QUALITY GATE
