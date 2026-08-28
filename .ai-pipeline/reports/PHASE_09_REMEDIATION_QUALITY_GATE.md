# Phase 09 Remediation Re-Quality Gate

Date: 2026-08-28  
Branch reviewed: `phase/09-jurisdiction-gateway-acra-foundation`  
Baseline: `7199c94f4a823d421649d3bcaf7ccf3d4abdc020`  
Review mode: independent, report-only combined quality gate

## 1. Verdict

**PASS.** The Phase 09 remediation closes P09-QG-001 and P09-QG-002 at the
required internal boundaries, not merely at the HTTP request model or through
well-behaved factories. The expanded tests cover the reported counterexamples,
and independent probes reproduced the required call-stopping and domain-invariant
behavior.

No Critical, High, or Medium finding remains. The previously accepted Low UI
sequencing debt remains bounded: the browser may select a document before case
creation, but a Registry-stage blocker neither uploads nor processes it.

This verdict authorizes next-development planning. It does not assert live ACRA
readiness, live GoldTier readiness, sponsor approval of evidence precedence, or
production durability.

## 2. Remediation Scope Reviewed

The review read and reconciled:

- `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, the Phase 09 planner, and the current
  regression catalogue;
- the original Phase 09 execution report, original quality-gate report, and
  remediation report;
- the working-tree diff against baseline `7199c94` and the repository status;
- the jurisdiction domain models, resolver, closed registry router, ACRA provider
  adapter, onboarding service, canonical validation, zero-touch projection,
  composition, API contracts, frontend behavior, tests, and updated architecture
  and ACRA profile documentation.

The remediation is correctly confined to Singapore identifier eligibility,
service/provider call stopping, truthful zero-touch projection, domain invariants,
tests, and corresponding documentation. No foreign registry implementation,
MongoDB application repository, ownership/UBO redesign, GoldTier redesign,
source-precedence policy, or Phase 10 behavior was found.

The repository was already dirty and contains the complete uncommitted Phase 09
working set plus earlier baseline-remediation changes. No staged files were found.
The review did not stage, commit, push, merge, rebase, stash, reset, or clean.

## 3. P09-QG-001 Re-Test

P09-QG-001 is **CLOSED**.

An independent HTTP probe used a counting ACRA connector and observed:

| Input | HTTP / workflow outcome | Safe error | ACRA calls |
|---|---|---|---:|
| `202400001A + SG` | `201`; `PENDING_INPUTS` at Document | none | **1** |
| `AU-REG-123 + SG` | `201`; `WAITING_FOR_REVIEW` at Registry | `REGISTRY_IDENTIFIER_NOT_ELIGIBLE` | **0** |
| `BAD-ID + SG` | `201`; `WAITING_FOR_REVIEW` at Registry | `REGISTRY_IDENTIFIER_NOT_ELIGIBLE` | **0** |
| `123 + SG` | `201`; `WAITING_FOR_REVIEW` at Registry | `REGISTRY_IDENTIFIER_NOT_ELIGIBLE` | **0** |
| `AU-REG-123 + AU` | `201`; `WAITING_FOR_REVIEW` at Registry | `REGISTRY_PROVIDER_NOT_IMPLEMENTED` | **0** |

The invalid explicit-SG cases made zero ACRA calls individually and zero in
aggregate. None was misreported as `ACRA_ENTITY_NOT_FOUND`.

The HTTP layer is not the sole protection. A direct `OnboardingService` probe with
a custom provider that did not contain the adapter guard returned
`REGISTRY_IDENTIFIER_NOT_ELIGIBLE` for `BAD-ID + SG` and recorded zero provider
calls. A separate direct `AcraRegistryProviderAdapter.retrieve_company("BAD-ID")`
probe raised `AcraIdentifierNotEligibleError` and recorded zero underlying
connector calls. The service and adapter boundaries therefore protect one another
against direct internal invocation.

## 4. Provider-Specific Identifier Boundary Assessment

The generic intake identifier grammar remains intentionally broad. It accepts a
bounded normalized registration identifier suitable for later foreign routing;
it does not globally impose Singapore UEN syntax. This was independently confirmed
by `AU-REG-123 + AU`, which reached the truthful AU
`PROVIDER_NOT_IMPLEMENTED` route rather than failing generic validation or calling
ACRA.

Singapore eligibility is then enforced by one shared
`is_eligible_singapore_uen` predicate: nine digits followed by one uppercase
letter after normalization. The resolver uses it only as Singapore-format
evidence, the onboarding service checks it immediately before provider invocation,
the ACRA adapter repeats it before connector invocation, and canonical validation
uses the same definition. This preserves foreign extensibility while making the
ACRA trust boundary fail closed.

The predicate is deliberately an eligibility rule for the current POC path, not a
claim to implement every official UEN category. Expanding that rule requires an
authoritative contract or sponsor decision.

## 5. P09-QG-002 Re-Test

P09-QG-002 is **CLOSED**.

Direct Pydantic construction was attempted without using the resolver or router.
Every impossible `JurisdictionResolution` state was rejected:

- `RESOLVED` with no observation;
- `RESOLVED` with an observation that disagrees with the selection;
- `RESOLVED` with mixed agreeing and disagreeing observations;
- `UNRESOLVED` with a selected jurisdiction;
- `UNRESOLVED` with a usable observation;
- `CONFLICT` with only one observation;
- `CONFLICT` with multiple observations that all agree;
- `CONFLICT` with a selected jurisdiction.

Direct construction also rejected contradictory `RegistryRoutingDecision` states,
including AU selected with ACRA, SG selected without ACRA, SG marked
provider-not-implemented, and AU marked provider-not-implemented while carrying
ACRA.

Valid direct constructions remained accepted: resolved SG with agreeing evidence,
unresolved with neither evidence nor selection, a two-jurisdiction conflict with no
selection, SG selected with ACRA, and AU/MY/HK provider-not-implemented with no
provider.

## 6. Domain Invariant Assessment

`JurisdictionResolution` now makes its semantic state machine intrinsic to the
model:

- `RESOLVED` requires observations and their distinct jurisdiction set must equal
  the selected jurisdiction;
- `UNRESOLVED` permits neither a selected jurisdiction nor usable observations;
- `CONFLICT` requires at least two observations, at least two distinct
  jurisdictions, and no selected jurisdiction.

`RegistryRoutingDecision` likewise encodes the current closed routing table rather
than trusting construction sites:

- only `SG / SELECTED / ACRA` is selectable;
- only `AU`, `MY`, or `HK` may be `PROVIDER_NOT_IMPLEMENTED`, and then provider must
  be absent.

These validators operate on direct model construction and are not tautological
assertions about factory output. The new tests exercise both rejected and accepted
states and use specific contradictory examples.

## 7. Regression / No-Precedence Assessment

The following regression behaviors passed through focused tests, independent
inspection, or the full suites:

- omitted-country valid Singapore identifiers retain the Phase 08 compatibility
  path and select SG/ACRA;
- explicit SG plus a valid UEN calls ACRA exactly once;
- explicit AU/MY/HK remains a retrievable provider-not-implemented Registry-stage
  blocker with no ACRA or downstream call;
- missing usable evidence remains unresolved;
- disagreeing observations remain a conflict with no selected route;
- there is no user-wins, identifier-wins, Singapore-wins, confidence, or ordering
  precedence rule;
- browser evidence remains bounded and safe; raw payloads, credentials, endpoint
  configuration, and internal connector details are not projected;
- strict ACRA source DTO reconstruction, requested/returned UEN binding, and
  canonical mapping remain in place;
- document, ownership/UBO, Mock GoldTier, and false-completion protections remain
  green in the 197-test focused regression suite and full backend suite;
- frontend/API contracts, document replacement, backend-authorized review actions,
  and the 5 MiB upload contract remain green;
- MongoDB remains a connectivity/read-only diagnostic seam and is not imported as
  an application repository or persistence dependency.

The Phase 09 focused test file expanded from 14 to 39 passing tests. Its new cases
cover direct service and direct adapter bypass attempts, exact invalid-SG call
counts, foreign grammar compatibility, and direct adversarial model construction.
They are meaningful boundary tests rather than assertions that merely repeat a
factory's normal output.

## 8. ACRA Trust-Boundary Assessment

The registry router is closed: resolved SG selects the configured ACRA provider;
AU/MY/HK select no provider. Caller-controlled URLs, provider names, modules, or
classes do not participate in routing.

For SG, the onboarding service stops an ineligible identifier immediately before
the provider call. The ACRA adapter independently repeats the eligibility check
before `fetch_company`, then retains strict DTO reconstruction, requested-UEN
identity binding, canonical mapping, and sanitized typed error translation. This is
defence in depth at both business-service and external-provider boundaries.

Failure projection is browser-safe. Ineligible identifiers receive the fixed
`REGISTRY_IDENTIFIER_NOT_ELIGIBLE` blocker; provider/raw exception text is not
leaked. Technical failures do not become human-approved business exceptions and do
not falsely advance the workflow.

The secret scanner and its unit tests passed. No credential material was introduced.
No live ACRA call was attempted or required because Q-012 remains open.

## 9. Full Test Results

All required checks were rerun independently against the reviewed working tree:

| Check | Command summary | Result |
|---|---|---|
| Phase 09 focused/adversarial | `pytest test_phase09_jurisdiction_gateway.py` | **39 passed** |
| Focused POC/provider regression | four zero-touch/UAT/provider suites | **197 passed** |
| Full backend | `pytest apps/backend/tests` | **548 passed** |
| Contract tests | `unittest discover tests/contract` | **44 passed** |
| Frontend tests | `npm.cmd test` | **45 passed** |
| Frontend typecheck | `npm.cmd run typecheck` | **PASS** |
| Frontend production build | `npm.cmd run build` to an external temporary directory | **PASS**, 29 modules transformed |
| Ruff | `ruff check apps/backend scripts tests` | **PASS** |
| Strict mypy | `mypy --no-incremental apps/backend/app` | **PASS**, 59 source files |
| Secret-check unit tests | `unittest discover -p test_check_secrets.py` | **5 passed** |
| Repository secret scan | `scripts/check_secrets.py` | **PASS** |
| Python dependency consistency | `pip check` | **PASS** |
| Frontend dependency tree | `npm.cmd ls --all` | **PASS**; only expected unmet optional platform packages |
| PyMongo version | installed environment inspection | **4.15.1** |
| Mongo diagnostic | `scripts/check_mongodb.py` with no `MONGO_URI` | expected safe unavailable result; no live check required |
| GoldTier validation tests | `tests.test_validate_goldtier_examples` | **5 passed** |
| GoldTier fixture validation | `validate_goldtier_examples.py --if-present` | **PASS**: 19 valid, 19 invalid/quarantined, 48 not validated |
| Delivery asset tests | `tests.test_phase_07_delivery_assets` | **4 passed** |
| Windows/demo lifecycle | `tests.test_demo_lifecycle_windows` | **13 passed**; owned processes stopped |
| Working-tree whitespace | `git diff --check` | **PASS**; line-ending notices only |
| Staged whitespace/status | `git diff --cached --check`; staged name check | **PASS**; nothing staged |

The Python HTTP suites emitted the existing Starlette `TestClient`/httpx
deprecation warning. It did not affect results and is not caused by this remediation.
Git status also reported an inaccessible, untracked frontend pytest-cache directory;
the review did not alter or rely on it.

## 10. Findings by Severity

### Critical

None.

### High

None. P09-QG-001 is closed.

### Medium

None. P09-QG-002 is closed.

### Low

- **P09-QG-004 remains accepted technical debt:** the browser can select a PDF
  before case creation establishes jurisdiction routing. On unresolved, conflicting,
  unsupported-provider, or ineligible-SG outcomes the file is neither uploaded nor
  processed, and downstream call stopping is preserved. Changing this sequencing
  is a later UX decision, not a Phase 09 remediation blocker.
- The public compatibility property remains named `uen` even though its grammar now
  admits recognized foreign registration identifiers. A neutral future API name
  should be introduced only with a compatibility/migration plan.
- Case and jurisdiction evidence persistence remains process-local by deliberate
  scope; restart loses it. MongoDB has not been adopted as an application repository.

The original test-coverage finding P09-QG-003 is closed by the 39-test focused suite
and the independent non-test-harness probes described above.

## 11. Remaining Sponsor Dependencies / Technical Debt

- **Q-012 remains OPEN.** The authoritative subscribed ACRA endpoint and operation,
  request/response schema, authentication, error/not-found semantics, rate/service
  limits, TLS/mTLS/private-CA requirements, authorized access, and live verification
  are not supplied. Current ACRA behavior remains Mock or project-defined
  sandbox-shaped behavior.
- **Q-015 remains OPEN.** Source confidence/precedence, conflict-resolution
  authority, authenticated reviewer role, retained correction evidence, and
  resume/restart policy are not sponsor-confirmed. Phase 09 correctly implements no
  precedence and exposes no invented resolution action.
- The current Singapore eligibility predicate is intentionally narrow and must not
  be represented as a complete official UEN validator without authoritative
  evidence.
- Live ACRA and live Mongo connectivity were not required. MongoDB remains
  diagnostic-only; no application repository uses it.

These are transparent sponsor dependencies or deferred architectural work. They do
not reopen P09-QG-001 or P09-QG-002 and do not block planning the next bounded phase.

## 12. Next-Development Readiness

Phase 09 remediation satisfies the independent combined quality gate. The system
now rejects explicit-SG identifiers that are ineligible for the current ACRA path
before any provider call, repeats that guard at the adapter boundary, preserves
broad foreign intake routing, and prevents contradictory jurisdiction/routing
domain objects from being directly constructed.

Next-development planning may begin, provided it continues to preserve the explicit
Q-012 and Q-015 boundaries and does not present Mock/sandbox-shaped behavior as live
integration evidence. No implementation beyond this report was changed by the
re-quality gate.

PASS — READY FOR NEXT DEVELOPMENT PLANNING
