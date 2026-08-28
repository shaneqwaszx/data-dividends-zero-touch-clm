# Phase 09 — Independent Quality Gate

## 1. Verdict

**FAIL.** Phase 09 has one High implementation defect at the Singapore identifier-to-ACRA boundary and one Medium domain-integrity defect. The full repository quality suite is green, the normal resolver/router flow has no hidden precedence, non-Singapore routes stop correctly, and the strict ACRA response boundary remains intact. Those positives do not outweigh the reproduced High defect: an explicitly selected Singapore jurisdiction allows a non-UEN identifier accepted by the widened generic grammar to invoke ACRA.

This gate was review-only. No application code, test, fixture, or existing report was changed.

## 2. Scope Reviewed

The independent review covered:

- branch `phase/09-jurisdiction-gateway-acra-foundation` at `7199c94f4a823d421649d3bcaf7ccf3d4abdc020`;
- the Phase 09 planner and execution report;
- the pre-next-development baseline, remediation execution report, and accepted remediation quality gate;
- the complete tracked and accessible untracked working-tree diff;
- jurisdiction observations, resolution, routing decisions, registry abstraction, ACRA adapter, onboarding/CLM/zero-touch ordering, API/browser projections, frontend behavior, security, persistence, documentation, and tests;
- the accepted POC regression catalogue and integration-security checklist;
- direct adversarial probes that were not present in the authored Phase 09 suite;
- all required backend, frontend, contract, static, security, dependency, GoldTier, delivery, and Windows lifecycle checks.

No live ACRA or MongoDB connection was required or attempted.

## 3. Diff / Working-Tree Assessment

`HEAD` and baseline `7199c94` are identical. All remediation and Phase 09 work is uncommitted: there are 33 tracked changed files with 778 insertions and 188 deletions, no staged files, and accessible untracked planner/report, implementation, test, architecture, profile, baseline-remediation, and `.gitattributes` files. Git continues to report the pre-existing inaccessible untracked `apps/frontend/pytest-cache-files-89airr88/` directory; this gate did not change its permissions or contents.

The combined diff was classified as follows:

- accepted pre-Phase-09 remediation: binary PDF handling and regenerated UAT fixtures, UTF-8 source inspection, optional/read-only Mongo diagnostic reconciliation, 5 MiB UI wording, removal of unsupported zero-touch manual field correction, documentation reconciliation, and their tests/reports;
- Phase 09: jurisdiction domain types, resolver, source-neutral registry boundary, ACRA adapter/router, onboarding/CLM/zero-touch integration, API/browser models, optional frontend selector and evidence display, Phase 09 tests, catalogue update, decision/question updates, architecture, and ACRA Mock/API profile;
- no foreign provider, Mongo application repository, ownership/UBO redesign, GoldTier expansion, Ready-for-Approval transition, or Phase 10 work was found.

`git diff --check` and `git diff --cached --check` passed. The only output was the repository's LF-to-CRLF working-copy notices.

## 4. Jurisdiction Domain Assessment

The bounded enums, frozen models, UTC-aware timestamps, observation count limit, source labels, optional confidence range, and extra-field rejection are appropriate. Active observations use fixed, safe source references.

However, `JurisdictionResolution.enforce_resolution_invariants` checks only that `RESOLVED` has some observations and a selected jurisdiction, and that non-resolved states omit the selected jurisdiction. Direct runtime probes proved that it accepts all of these contradictory objects:

- `RESOLVED / SG` supported only by an `AU` observation;
- `UNRESOLVED` with an `SG` observation;
- `CONFLICT` with only one agreeing `SG` observation.

`RegistryRoutingDecision` similarly accepts `SELECTED / AU / ACRA` and `PROVIDER_NOT_IMPLEMENTED / SG`. The current resolver and router factories do not generate those combinations, but the foundational domain objects can represent states their own names and public contract declare impossible. This is finding **P09-QG-002 (Medium)**.

## 5. Resolution / No-Precedence Assessment

The implemented resolver itself is deterministic and contains no source precedence. It retains input order, resolves no observations as `UNRESOLVED`, resolves one distinct jurisdiction as `RESOLVED`, and returns `CONFLICT` for multiple distinct jurisdictions. Confidence and source type are not used to select a winner.

An explicit `AU` observation plus the Singapore identifier-format observation returned `CONFLICT`, retained both observations in their stable assembly order, selected no route, advertised no review action, and made zero ACRA or downstream calls. Reversing source importance or supplying confidence cannot change the set-based result. Q-015 therefore remains open rather than being silently implemented.

The model-construction weakness in section 4 does not create hidden precedence in the current service path, but it must be fixed before the domain foundation is accepted.

## 6. Omitted-Input Compatibility Assessment

Omitting `country_of_incorporation` while supplying `202400001A` produced exactly one visible `IDENTIFIER_FORMAT -> SG` observation with `request.uen:accepted_sg_format`, resolved Singapore, selected ACRA, and called ACRA once. The existing valid Singapore path reached the Document `PENDING_INPUTS` checkpoint. This is explicit provenance, not a silent default.

Omitting the country for `UNKNOWN-123` produced `JURISDICTION_UNRESOLVED`, no route, zero ACRA calls, a Registry review checkpoint, and a retrievable unchanged case.

## 7. Registry Router Assessment

The runtime router is a closed backend-owned table. It accepts a trusted `JurisdictionCode`, holds one configured ACRA provider, selects it only for `SG`, and returns provider-not-implemented with no provider for `AU`, `MY`, and `HK`. User input cannot supply an endpoint, module, class, credential, provider identifier, or foreign connector. Generic orchestration imports no foreign-provider DTO.

Direct integrated probes produced zero ACRA calls for each of `AU`, `MY`, and `HK`. No foreign registry functionality is present. The invalid standalone routing objects described in P09-QG-002 remain a domain validation issue, not evidence that the runtime table dynamically routes foreign traffic.

## 8. ACRA Adapter / Trust-Boundary Assessment

The adapter preserves the prior ACRA response trust boundary:

- exactly one `fetch_company(identifier)` operation;
- fresh primitive reconstruction through strict `AcraCompanyPayload` validation, including nested DTO validators;
- requested/returned normalized identifier equality;
- existing source-to-canonical mapping and canonical validation;
- original control-character rejection and query-free HTTPS provenance controls inherited from the source DTO/mapper;
- safe connector/mapping error allowlisting without raw exception projection;
- truthful `ACRA` plus `MOCK`/`SANDBOX` labels.

The retargeted mapper-fault tests patch the adapter's actual mapper seam and retain their original call-stopping assertions; no adversarial assertion was removed. The 197-test POC/provider regression run and the 523-test backend suite passed. No live ACRA interoperability claim is justified because Q-012 remains open.

The response boundary is sound; the High finding is instead an outbound request-eligibility failure before this adapter is invoked.

## 9. Registration-Identifier Contract Assessment

The generic API boundary normalizes padding/lowercase and enforces a 1–32 character uppercase alphanumeric/hyphen grammar. Independent probes verified:

- blank, 33-character, control-character, unexpected-symbol, unknown-country, and extra-property requests each returned `422` and made zero ACRA calls;
- padded lowercase `202400001a` normalized to `202400001A`, returned `201`, and called ACRA once;
- the compatibility property name `uen` is documented future API debt, not by itself a current defect.

The widened grammar is not narrowed again after a request resolves to Singapore. Independent calls using `{country_of_incorporation: "SG"}` with `AU-REG-123`, `BAD-ID`, and `123` each returned `201`, reached ACRA exactly once, and were then reported as `ACRA_ENTITY_NOT_FOUND`. Before Phase 09, the API required exactly nine digits plus one uppercase letter. The current behavior therefore lets identifiers that are intentionally accepted for gateway/foreign routing bypass Singapore UEN request eligibility and reach the ACRA connector. This violates the gate's explicit requirement that widening must not accidentally expose ACRA to unsupported identifiers and is **P09-QG-001 (High)**.

## 10. Workflow / Call-Stopping Assessment

Independent results and direct call counts were:

| Scenario | Result | ACRA | IDP/document | Ownership | GoldTier |
|---|---|---:|---:|---:|---:|
| country omitted + `202400001A` | `RESOLVED / SG`, Document `PENDING_INPUTS` | 1 | 0 before upload | 0 | 0 |
| explicit SG + `202400001A` | `RESOLVED / SG`, Document `PENDING_INPUTS` | 1 | 0 before upload | 0 | 0 |
| explicit AU + `202400001A` | `JURISDICTION_CONFLICT`, Registry review | 0 | 0 | 0 | 0 |
| omitted country + `UNKNOWN-123` | `JURISDICTION_UNRESOLVED`, Registry review | 0 | 0 | 0 | 0 |
| explicit AU/MY/HK + matching bounded foreign-style identifier | `REGISTRY_PROVIDER_NOT_IMPLEMENTED`, Registry review | 0 each | 0 | 0 | 0 |
| document attempt on blocked MY case | original blocked record returned | 0 | no document record; no IDP | no analysis | all operations `NOT_ATTEMPTED` |
| explicit SG + `AU-REG-123`, `BAD-ID`, or `123` | `ACRA_ENTITY_NOT_FOUND` after retrieval attempt | **1 each** | 0 | 0 | 0 |

Controlled jurisdiction blockers remain retrievable, expose no action, do not resume into later stages, and cannot falsely complete. The frontend sends a selected PDF only when the create response is `PENDING_INPUTS`; the backend document method also returns an existing Registry-blocked record without creating a document or invoking IDP. The incorrect SG/non-UEN ACRA calls are the sole reproduced call-stopping failure.

## 11. API / Browser Evidence Assessment

The API accepts an optional bounded jurisdiction enum and rejects extra properties. Browser case responses expose the resolution, all retained bounded observations, safe evidence-reference aliases, and the minimized routing decision. They do not expose ACRA URLs, query strings, credentials, raw provider payloads, connector classes, configuration, private exceptions, or authority fingerprints.

Registry exceptions expose at most four safe evidence items and no available action. The active evidence references are fixed application strings. The direct use of domain routing models in responses remains safe in the current runtime path, although P09-QG-002 means those domain models need stronger semantic validation before they can be treated as self-validating persisted or reconstructed facts.

## 12. Frontend Assessment

The frontend selector is optional and bounded to Not specified, Singapore, Australia, Malaysia, and Hong Kong. Foreign options truthfully state that their provider is not implemented. The API helper omits `country_of_incorporation` entirely when no selection is made and sends the stable code when selected. Backend responses remain authoritative for the displayed resolution, observations, provider decision, blocker, and actions.

The combined journey stores the create response first and uploads the selected PDF only when the backend returns `PENDING_INPUTS`; Registry-blocked cases therefore do not upload or process it. The UI still requires the operator to select a local PDF before case creation even when the case will stop at Registry; this is a documented Low usability debt, not a false processing claim.

Frontend typecheck, 45/45 tests, and the 29-module production build passed. The initial sandbox-only Vitest `spawn EPERM` was rerun with the child-process permission required by bundled esbuild and passed; it is not a product failure.

## 13. ACRA Mock API Profile Assessment

`docs/contracts/ACRA_MOCK_API_PROFILE.md` accurately labels itself synthetic and non-authoritative. It documents the one monolithic operation, request/response binding, actual canonical fields, address structure, provenance, six synthetic UEN scenarios, not-found behavior, malformed/unavailable/safe error distinctions, current mappings, absent officer/shareholder/ownership/document/activity data, and future `TBD_SPONSOR` mappings.

It truthfully distinguishes ACRA business source from Mock/Sandbox environment and leaves live binding blocked by Q-012. Its request section says ACRA is called only after SG resolution, which is true but incomplete in light of P09-QG-001: remediation must also make Singapore identifier eligibility explicit and enforced.

## 14. Security Assessment

No secret, raw credential, private sponsor artefact, unsafe log statement, dynamic provider selection, URL/provider injection path, raw exception leak, browser source URL, or unbounded request/evidence field was found. Secret unit tests and the repository scanner passed. Crafted ACRA response, nested validation, identity mismatch, control-character, provenance, and mapper-failure regressions remain green.

P09-QG-001 is also a trust-boundary and availability concern: a caller can cause the configured ACRA boundary to receive arbitrary bounded alphanumeric/hyphen identifiers merely by asserting `SG`. The input is not code/URL injection, but the external request is outside the accepted Singapore UEN grammar and can consume provider calls or produce misleading ACRA not-found outcomes.

## 15. Mongo / Persistence Boundary

MongoDB remains optional connectivity/read-only diagnostic code. `pymongo==4.15.1` is installed, `pip check` passes, `MONGO_URI` remains optional/secret, and no FastAPI composition, onboarding repository, document repository, ownership repository, CLM repository, automation repository, provider-binding store, or target ledger imports `app.mongo`.

Jurisdiction evidence and routing decisions are stored only in the existing process-local onboarding aggregate; restart clears them. With `MONGO_URI` absent, `scripts/check_mongodb.py` exited 1 with only `MongoDB check failed: ValueError`, as designed. No live connectivity was required and no application persistence or migration was introduced.

## 16. Ownership / UBO Regression Assessment

Phase 09 does not change ownership graph acquisition, Decimal path arithmetic, aggregation, thresholds, provisional candidate semantics, cycle/incomplete handling, or related-party behavior. Registry blockers stop before ownership, and direct inspection of a blocked case returned no ownership analysis. The focused 197-test zero-touch/UAT/input-driven/provider suite, including the strict-PDF `OWNERSHIP_CYCLE` path and call-stopping regressions, passed. The full backend suite also passed 523/523.

No legal UBO, compliance approval, foreign ownership source, or new GoldTier hierarchy claim was introduced.

## 17. GoldTier Regression Assessment

No GoldTier connector, mapper, contract, call order, idempotency/recovery authority, or Ready-for-Approval behavior changed. Conflict, unresolved, and provider-not-implemented probes left every target operation `NOT_ATTEMPTED`. Existing POC regressions preserved straight-through, existing-party, controlled failure, partial amend, malformed response, and replay-safe recovery behavior.

GoldTier validator unit tests passed 5/5. Example validation retained the expected non-failing classification of 19 valid, 19 invalid/quarantined, and 48 not validated. No foreign registry or jurisdiction outcome was presented as sponsor-approved GoldTier mapping.

## 18. Full Test / Quality Results

| Exact command | Independent result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest apps\backend\tests` | PASS — 523 passed; 1 upstream Starlette/httpx deprecation warning |
| `.\.venv\Scripts\python.exe -m pytest apps\backend\tests\test_phase09_jurisdiction_gateway.py -q -p no:cacheprovider` | PASS — 14 passed; same warning |
| `.\.venv\Scripts\python.exe -m pytest apps\backend\tests\test_zero_touch_orchestration.py apps\backend\tests\test_phase_07_uat.py apps\backend\tests\test_phase_08_input_driven.py apps\backend\tests\test_phase06_provider_conformance.py` | PASS — 197 passed; same warning |
| `.\.venv\Scripts\python.exe -m ruff check apps\backend scripts tests` | PASS |
| `.\.venv\Scripts\python.exe -m mypy --no-incremental apps\backend\app` | PASS — 59 source files |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests\contract -p "test_*.py"` | PASS — 44/44; same warning |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_check_secrets.py"` | PASS — 5/5 |
| `.\.venv\Scripts\python.exe scripts\check_secrets.py` | PASS — no supported secret patterns |
| `.\.venv\Scripts\python.exe -m unittest tests.test_validate_goldtier_examples -v` | PASS — 5/5 |
| `.\.venv\Scripts\python.exe scripts\validate_goldtier_examples.py --if-present` | PASS — expected `VALID=19`, `INVALID_QUARANTINED=19`, `NOT_VALIDATED=48` |
| `.\.venv\Scripts\python.exe -m pip check` | PASS — no broken requirements |
| `.\.venv\Scripts\python.exe -c "import pymongo; print(pymongo.__version__)"` | PASS — `4.15.1` |
| `.\.venv\Scripts\python.exe scripts\check_mongodb.py` | EXPECTED UNAVAILABLE — exit 1, safe `ValueError`; no `MONGO_URI`, live service not required |
| `npm.cmd run typecheck` in `apps/frontend` | PASS |
| `npm.cmd test` in `apps/frontend` | PASS — 45/45 after permissioned esbuild spawn; initial sandbox-only `spawn EPERM` was not a product failure |
| `npm.cmd run build -- --outDir C:\Users\shane\AppData\Local\Temp\phase09-qg-build-20260828` in `apps/frontend` | PASS — 29 modules; output directed outside the repository |
| `npm.cmd ls --all` in `apps/frontend` | PASS — exit 0; listed expected unmet optional platform/feature packages |
| `.\.venv\Scripts\python.exe -m unittest tests.test_phase_07_delivery_assets -v` | PASS — 4/4 |
| `.\.venv\Scripts\python.exe -m unittest tests.test_demo_lifecycle_windows -v` | PASS — 13/13 in 170.136 seconds; final launcher-owned processes stopped |
| `git diff --check` and `git diff --cached --check` | PASS — LF/CRLF notices only |

The authored suites are green but do not prove the absent invariants: the 14 Phase 09 tests contain no explicit-SG/non-UEN call-count case and no direct invalid-construction cases for `JurisdictionResolution` or `RegistryRoutingDecision`. The independent probes are therefore material counterexamples, not contradictions of the recorded suite totals.

## 19. Findings by Severity

### CRITICAL

None.

### HIGH

**P09-QG-001 — Explicit SG bypasses Singapore UEN request eligibility and calls ACRA.**

- Evidence: the API grammar in `apps/backend/app/main.py` accepts any 1–32 uppercase alphanumeric/hyphen identifier; `apps/backend/app/services/onboarding.py` treats explicit `SG` as sufficient resolution and invokes the selected provider without checking the accepted Singapore UEN format.
- Reproduction: `AU-REG-123`, `BAD-ID`, and `123` paired with `country_of_incorporation=SG` each made one ACRA call and became `ACRA_ENTITY_NOT_FOUND`.
- Impact: Phase 09's deliberate generic widening weakens the previous Singapore request boundary, permits unsupported outbound ACRA queries, and misclassifies malformed SG requests as registry not-found outcomes.
- Required remediation: add a fail-closed Singapore identifier eligibility check before ACRA invocation while preserving the broad generic grammar for jurisdiction resolution/unsupported foreign routes; add direct API/service call-count regressions for explicit SG with valid and invalid identifiers.

### MEDIUM

**P09-QG-002 — Jurisdiction resolution and routing models admit contradictory semantic states.**

- Evidence: direct Pydantic construction accepted `RESOLVED / SG` with only AU evidence, `UNRESOLVED` with SG evidence, `CONFLICT` with one SG observation, `SELECTED / AU / ACRA`, and `PROVIDER_NOT_IMPLEMENTED / SG`.
- Impact: the current factories are safe, but persistence/reconstruction or future internal callers can create API-visible facts that contradict the resolver/router contract. This weakens the intended jurisdiction foundation.
- Required remediation: encode complete status/observation/jurisdiction/provider consistency invariants in the domain models and add adversarial construction tests.

### LOW

**P09-QG-003 — Focused Phase 09 tests omit the two critical cross-field invariant classes.** The suite verifies the normal factory paths but not conditional SG identifier eligibility or invalid semantic model construction. This test gap allowed P09-QG-001 and P09-QG-002 to coexist with 14/14 focused passes.

**P09-QG-004 — The combined UI requires local PDF selection before a Registry decision.** It does not upload or process the file when blocked, so this is usability debt only.

## 20. Remaining Sponsor Dependencies / Technical Debt

- **Q-015:** source precedence, conflict-resolution authority, authenticated reviewer role, retained correction evidence, and resume/restart policy remain intentionally open. Phase 09 correctly exposes no resolution action.
- **Q-012:** authoritative subscribed ACRA endpoint, schema, authentication, errors, limits, TLS details, authorized access, and live verification remain open.
- Existing sponsor dependencies for document/source authority and privacy, UBO threshold/legal semantics, GoldTier/PingFed authentication, Singapore target mappings, related-party behavior, hierarchy retrieval, existing-party/partial-write handling, and Ready-for-Approval remain unchanged.
- Technical debt remains: process-local durability, the compatibility property name `uen` for a generic identifier, four-item exception-evidence projection versus eight retained observations, and the frontend's PDF-before-registry selection order.
- The pre-existing Starlette/httpx deprecation warning and inaccessible untracked frontend cache directory remain non-blocking environment/repository hygiene items.

Sponsor dependencies are not implementation failures in this gate. P09-QG-001 and P09-QG-002 are locally remediable and do not require sponsor decisions.

## 21. Phase 10 / Next-Development Readiness

Next-development planning must not begin from this Phase 09 state. Remediate the Singapore identifier-to-ACRA boundary, strengthen the domain invariants, add the missing adversarial tests, rerun the focused and full quality suite, and repeat the independent Phase 09 gate. No Phase 10 design or implementation was performed.

FAIL — REMEDIATION REQUIRED
