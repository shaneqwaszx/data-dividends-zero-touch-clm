# Phase 10 Execution — Expanded ACRA Mock Registry Acquisition

Date: 2026-08-28  
Branch: `phase/10-expanded-acra-registry-acquisition`  
Baseline / HEAD at task start: `2ca3ad67d16d7f6fa2e48b44bce37b909bf2b8f8`  
Scope: execution only; no independent Phase 10 quality gate performed

## 1. Executive Summary

Phase 10 expands the eligible Singapore Mock registry path from one entity-profile call
into four explicit project-owned operations: entity profile, officers, ownership
parties, and relationships. Each response crosses a strict bounded DTO boundary and is
normalized into one provider-neutral acquisition bundle with ordered operation status,
count, provenance, safe errors, and explicit complete/partial/failed semantics.

Registry ownership evidence now enters the normal Mock Singapore ownership stage
through an `OwnershipProvider` adapter and the existing `OwnershipAnalysisService`. The
existing Decimal arithmetic, path aggregation, provisional inclusive threshold, graph
validation, cycle/incomplete handling, and path/depth limits remain authoritative. No
second ownership or UBO engine was added.

The backend and frontend truthfully display the multi-step Mock acquisition. Empty
officers may be legitimate; missing expected ownership evidence stops for review;
malformed or unavailable later operations fail technically and stop all downstream
work. Full verification is green: 566 backend tests, 48 frontend tests, 44 contract
tests, 5 secret-unit tests, 5 GoldTier validation tests, 4 delivery-asset tests, and 13
Windows lifecycle tests passed, with lint, strict typing, build, dependency, secret,
GoldTier fixture, and whitespace checks also passing.

## 2. Scope Implemented

- Decomposed project-owned Mock operations for entity profile, officers, ownership
  parties, and relationships.
- Added strict source DTOs and bounded normalized evidence models.
- Added a provider-neutral acquisition bundle and operation result/status contract.
- Added legitimate empty, partial expected-data, malformed-response, timeout/unavailable,
  and not-attempted semantics.
- Added registry ownership integration through the existing ownership provider/domain.
- Added safe API/browser acquisition summaries and frontend operation/evidence display.
- Added synthetic normal, legal-owner, multiple-owner, multi-level, empty, missing,
  malformed, failure, and registry-fed cycle fixtures.
- Expanded the ACRA Mock profile, architecture, decision/open-question context, README,
  and accepted regression catalogue.
- Preserved all Phase 09 routing, jurisdiction, and identifier call-stopping controls.

## 3. Files Changed

Backend implementation:

- `apps/backend/app/connectors/acra.py`
- `apps/backend/app/connectors/mock_acra.py`
- `apps/backend/app/connectors/acra_sandbox.py`
- `apps/backend/app/connectors/registry.py`
- `apps/backend/app/connectors/registry_ownership.py`
- `apps/backend/app/domain/models.py`
- `apps/backend/app/services/onboarding.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/app/composition.py`
- `apps/backend/app/api_models.py`

Backend tests:

- `apps/backend/tests/test_phase10_registry_acquisition.py`
- `apps/backend/tests/test_phase09_jurisdiction_gateway.py`
- `apps/backend/tests/test_phase06_provider_conformance.py`
- `apps/backend/tests/test_acra_modes.py`

Frontend:

- `apps/frontend/src/types.ts`
- `apps/frontend/src/App.tsx`
- `apps/frontend/src/styles.css`
- `apps/frontend/src/App.test.tsx`

Documentation and regression evidence:

- `README.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/architecture/FINAL_POC_ARCHITECTURE.md`
- `docs/architecture/PHASE_10_EXPANDED_REGISTRY_ACQUISITION.md`
- `docs/architecture/README.md`
- `docs/contracts/ACRA_MOCK_API_PROFILE.md`
- `docs/contracts/README.md`
- `docs/decisions/DECISION_LOG.md`
- `docs/sponsor-questions/OPEN_QUESTIONS.md`
- `.agents/skills/poc-regression-check/references/regression-catalogue.md`
- `.ai-pipeline/reports/PHASE_10_EXECUTION.md`

The user-supplied planner handoff
`.ai-pipeline/001_planner/PHASE_10_EXPANDED_ACRA_MOCK_REGISTRY_ACQUISITION.md` was
already untracked at task start and was read/preserved, not attributed as an execution
change. Nothing was staged, committed, pushed, merged, rebased, stashed, reset, or
cleaned.

## 4. Registry Acquisition Contract

`RegistryProvider` now exposes one provider-neutral bounded acquisition call. The
onboarding service consumes only `RegistryAcquisitionBundle`; it does not import or use
ACRA source DTOs. The bundle contains:

- requested identifier and deterministic root-party ID;
- canonical entity profile;
- bounded normalized officer, ownership-party, and relationship collections;
- exactly four ordered operation results;
- overall `COMPLETE`, `PARTIAL`, or `FAILED` status;
- bounded safe issues and UTC retrieval time.

The bundle stores no UBO conclusion, candidate, threshold result, GoldTier field, raw
payload, endpoint, credential, or provider object.

## 5. ACRA Mock Operations

Implemented project concepts:

| Operation | Mock connector method | Bound | Normal status |
|---|---|---:|---|
| `ENTITY_PROFILE` | `fetch_company` | one entity | `COMPLETE` |
| `OFFICERS` | `fetch_officers` | 32 | `COMPLETE` or legitimate `EMPTY` |
| `OWNERSHIP_PARTIES` | `fetch_ownership_parties` | 64 | `COMPLETE`; `EMPTY` makes bundle partial |
| `RELATIONSHIPS` | `fetch_relationships` | 128 | `COMPLETE`; `EMPTY` makes bundle partial |

These are not official ACRA operation names or endpoints. The existing sandbox-shaped
entity-profile seam remains strict, but expanded sandbox operations fail closed as
`REGISTRY_OPERATION_UNAVAILABLE` because Q-012 provides no authoritative operations or
schemas. No synthetic expanded data is represented as sandbox/live interoperability.

## 6. Entity Profile

The existing entity fields and mapping remain intact: UEN, legal name, incorporation
country, entity type, registration date, entity status, optional registered address,
environment, internal query-free HTTPS provenance, and UTC retrieval time. The adapter
retains fresh primitive reconstruction, requested/returned UEN identity binding,
canonical mapping, and the shared canonical-minimum validation.

No entity result remains `ACRA_ENTITY_NOT_FOUND`; later operations are not called.

## 7. Officers / Directors

The strict project-owned officer DTO and normalized model contain only officer ID, name,
role, optional appointment/cessation dates, optional country, and provenance. Role
strings are project fixture vocabulary, not claimed official ACRA codes or legal
semantics. The collection is capped at 32, deterministically ordered, and synthetic.

`202400010J` verifies that an empty officer collection is legitimately `EMPTY` while the
overall bundle remains `COMPLETE` when ownership evidence exists.

## 8. Ownership Parties

The strict project-owned ownership-party DTO/model supports natural persons and legal
entities, bounded fictional name, optional registration identifier/country, optional
exact Decimal ownership evidence, and per-record provenance. Party IDs must be unique.
Ownership percentage is source evidence only, not a UBO conclusion.

Fixtures cover direct persons, a legal-entity shareholder, multiple owners, multi-level
ownership, and a cycle-compatible legal-entity graph.

## 9. Relationships

The strict relationship model contains unique relationship ID, owned entity, owner
party, project relationship type `SHARE_OWNERSHIP`, exact Decimal percentage, and
provenance. Owners must reference returned ownership parties; owned entities must be the
root or returned legal entities; self-edges and inconsistent references fail safely.

No control-based UBO rule, official ACRA relationship vocabulary, `createRelationship`,
or GoldTier hierarchy write was added.

## 10. Acquisition Bundle / Operation Status

Each successful entity retrieval yields the four operation results in fixed order. An
operation is `COMPLETE`, `EMPTY`, `FAILED`, or `NOT_ATTEMPTED`; record counts must match
the normalized collections. Every attempted result retains ACRA source, Mock/Sandbox
environment, operation, UTC time, and an opaque evidence reference. Failed operations
retain only fixed safe errors plus safe operation provenance.

The bundle validates deterministic order, collection bounds, unique IDs, record counts,
relationship references, overall/operation status consistency, and required issue
semantics.

## 11. Ownership Integration

`RegistryAcquisitionOwnershipProvider` maps the retained complete Mock acquisition into
the existing `OwnershipSourceResult`:

```text
registry ownership evidence
  -> RegistryAcquisitionOwnershipProvider
  -> Party / OwnershipRelationship
  -> existing OwnershipAnalysisService
```

The normal SME produces the existing exact 60% and 40% direct candidates under the
same provisional inclusive threshold. The registry-fed `202400006F` cycle produces the
existing `REVIEW_REQUIRED / CYCLE_DETECTED` result. The provider performs no traversal,
aggregation, thresholding, candidate classification, or UBO decision.

`InputDrivenOwnershipProvider` and explicit Mock graph scenarios remain available for
developer/test fault injection; normal Mock Singapore composition now uses registry
evidence.

## 12. Empty / Partial / Failure Semantics

- Officers empty: operation `EMPTY`; bundle `COMPLETE`; continue.
- Ownership parties or relationships empty: operation `EMPTY`; bundle `PARTIAL`;
  `REVIEW_REQUIRED / REGISTRY_EXPECTED_DATA_MISSING`; no downstream call.
- Malformed/identity-inconsistent result: failed operation with
  `REGISTRY_OPERATION_MALFORMED_RESPONSE`; technical `FAILED`; later operations and all
  downstream work stop.
- Timeout: `REGISTRY_OPERATION_TIMEOUT`; technical `FAILED`.
- Controlled provider/unavailability failure: `REGISTRY_OPERATION_UNAVAILABLE`;
  technical `FAILED`.
- Operations after an earlier acquisition failure: `NOT_ATTEMPTED`.

Transport success is therefore not treated as complete evidence. No sponsor-owned
waiver/fill/preference rule was invented.

## 13. API / Browser Projection

`OnboardingCaseResponse` includes a minimized acquisition view with normalized records,
operation, status, record count, ACRA source, environment, UTC time, opaque evidence
reference, and fixed safe issue. It excludes canonical internal source URL, raw ACRA
endpoint, response body, headers, authorization, configuration, provider objects, and
exception internals.

Backend tests assert that browser JSON contains neither `source_endpoint` nor
`mock.acra.gov.sg` nor authorization-like material.

## 14. Frontend Changes

The new ACRA Registry Acquisition panel shows backend-authored:

- overall complete/partial/failed state;
- Entity Profile, Officers, Ownership Parties, and Relationships statuses;
- record counts and fixed safe error codes;
- bounded normalized officer/ownership names where present;
- an explicit “project-owned synthetic Mock contract — not verified live ACRA” label.

Partial evidence displays its missing-data issue and is not presented as success.
Registry-blocked foreign/unresolved/conflicting/ineligible cases render no fake ACRA
acquisition panel. No exception workbench or case-management redesign was added.

## 15. ACRA Mock API Profile Update

`docs/contracts/ACRA_MOCK_API_PROFILE.md` now documents all four operations, request,
strict response fields/types, required/optional nested fields, common provenance,
synthetic examples, bounds, empty/partial/failure behavior, operation status, ownership
integration, fixture catalogue, safe errors, limitations, and mapping readiness.

The profile prominently states that these are project-owned Mock contracts pending
Q-012 and not authoritative subscribed ACRA APIs.

## 16. Sponsor Mapping Readiness

The profile contains separate entity, officer/director, ownership-party, and
relationship tables from source fields to normalized internal fields. Every unknown
GoldTier field/value-list/role/relationship mapping remains exactly `TBD_SPONSOR`.
Phase 10 performs no new GoldTier mapping or related-party/relationship write.

## 17. Security / Bounds

The repository integration-security checklist was applied.

- All source records are untrusted and freshly reconstructed through strict DTOs.
- Required text is nonblank, trimmed, control-character-free, and length bounded.
- IDs and percentages use bounded grammars and exact Decimal constraints.
- Collections are capped at 32/64/128; existing ownership graph/path bounds remain.
- Every operation is request-UEN-bound and environment-consistent.
- Source endpoints remain query-free HTTPS and server-internal.
- Browser provenance is opaque/minimized; no raw payload or endpoint is projected.
- Errors are fixed codes/messages; raw exceptions/validation details are discarded.
- Provider and routing selection remain backend-owned and closed.
- No new logging, credential, secret, auth handling, dependency, or dynamic import was
  added.
- Mock/Sandbox labels are truthful; no adapter is labeled live.
- Secret unit tests and repository scan pass.

Security findings: Critical none; High none; Medium none. Accepted limitations and
sponsor dependencies are recorded separately below.

## 18. Call Counts / Call Stopping

Verified actual normal eligible Singapore calls:

| Operation | Calls |
|---|---:|
| Entity profile | 1 |
| Officers | 1 |
| Ownership parties | 1 |
| Relationships | 1 |

Reading the retained case makes no duplicate acquisition call.

For each Phase 09 blocker—`JURISDICTION_UNRESOLVED`, `JURISDICTION_CONFLICT`,
`REGISTRY_PROVIDER_NOT_IMPLEMENTED`, and `REGISTRY_IDENTIFIER_NOT_ELIGIBLE`—actual
counts remain:

| Boundary | Calls |
|---|---:|
| All four registry acquisition operations | 0 |
| IDP/document provider | 0 |
| Ownership provider/analysis | 0 |
| GoldTier search/shell/policy/amend | 0 |

A deliberately wrong officer-operation identity produces entity profile 1, officers 1,
ownership parties 0, and relationships 0. Malformed and provider-failed relationship
fixtures each make the expected four-operation prefix once, then make zero IDP,
ownership, and GoldTier calls. Partial expected-data cases likewise make zero downstream
calls. Target API evidence remains `NOT_ATTEMPTED`.

## 19. Exact Test Results

| Check | Exact result |
|---|---|
| Phase 10 focused | **18 passed** |
| Phase 10 + Phase 09 adversarial | **57 passed** (18 + 39) |
| Focused zero-touch/UAT/input/provider regressions | **197 passed** |
| Full backend | **566 passed** |
| Ruff | **PASS** — `apps/backend scripts tests` |
| Strict mypy | **PASS** — 60 source files, no incremental cache |
| Contract tests | **44 passed** |
| Frontend typecheck | **PASS** |
| Frontend tests | **48 passed** |
| Frontend production build | **PASS** — 29 modules transformed |
| Secret-check unit tests | **5 passed** |
| Repository secret scan | **PASS** — no supported secret patterns |
| GoldTier validator unit tests | **5 passed** |
| GoldTier fixture validation | **PASS** — 19 valid, 19 invalid/quarantined, 48 not validated |
| Python dependency consistency | **PASS** — no broken requirements |
| Frontend dependency tree | **PASS** — exit 0; expected optional platform/feature packages unmet |
| Delivery assets | **4 passed** |
| Windows/demo lifecycle | **13 passed in 183.459s**; final owned processes stopped |
| PyMongo version | **4.15.1** |
| Mongo diagnostic without `MONGO_URI` | Expected safe unavailable result: `ValueError`; live Mongo not required |
| `git diff --check` / staged check | **PASS** — line-ending notices only; nothing staged |

The backend retains the pre-existing Starlette/httpx deprecation warning and adversarial
Pydantic serializer warnings in tests that intentionally bypass typed values. They do
not affect results and were not introduced as Phase 10 product behavior. The initial
sandboxed frontend runner could not spawn bundled esbuild; the required permissioned
test/build runs passed. Git continues to report the pre-existing inaccessible untracked
frontend pytest-cache directory; it was not inspected or modified.

## 20. Sponsor Dependencies Preserved

- **Q-012 remains OPEN.** Authoritative ACRA endpoints/operations, official schemas,
  auth, errors/not-found behavior, role/relationship vocabularies, pagination/limits,
  TLS/mTLS/private CA, access, and live verification remain unknown.
- **Q-015 remains OPEN.** Jurisdiction source precedence, disagreement authority,
  correction evidence, authenticated reviewer role, and resume/restart policy remain
  unconfirmed.
- Existing Q-002/Q-004 ownership hierarchy and UBO policy dependencies remain open; the
  registry adapter does not resolve them.
- Every expanded ACRA-to-GoldTier mapping remains `TBD_SPONSOR`.
- MongoDB remains diagnostic-only; application state and acquisition evidence are
  process-local.

## 21. Non-Goals Confirmation

Not implemented:

- Phase 11 or multi-source reconciliation;
- source precedence or generic human-intervention policy;
- live ACRA or authoritative official ACRA schema claims;
- ACRA+;
- ASIC, SSM/Malaysia, Hong Kong, or any foreign registry connector;
- new mock/sandbox/live switching framework;
- Mongo application persistence or migration;
- workflow/state-machine replacement;
- new UBO threshold, comparator, aggregation, cycle, control, or legal-controller rule;
- real GoldTier/PingFed, final mappings, related-party/relationship writes;
- Ready-for-Approval or production RBAC.

## 22. Remaining Risks

- **High sponsor dependency, not an implementation defect:** Q-012 blocks all exact
  expanded ACRA sandbox/live binding and official operation/schema claims.
- **High sponsor dependency, not an implementation defect:** Q-015 blocks jurisdiction
  disagreement resolution and source authority.
- **Medium accepted limitation:** process restart loses acquisition/case/ownership state;
  MongoDB is not an application repository.
- **Medium accepted limitation:** expanded operations are Mock-only; sandbox-shaped
  profile success stops at the first undocumented expanded operation.
- **Medium sponsor dependency:** ownership threshold/legal semantics and final
  source-to-GoldTier mappings remain provisional or `TBD_SPONSOR`.
- **Low:** the pre-existing frontend PDF-before-registry selection sequence remains; a
  Registry blocker still uploads/processes nothing.
- **Low:** pre-existing Starlette/httpx and adversarial serializer warnings remain.

No unresolved Critical or High implementation finding is known.

## 23. Readiness

The assigned Phase 10 scope is implemented, documented, security-reviewed, regression-
checked, and fully verified. The normal Singapore Mock path performs one call per
acquisition operation, preserves every Phase 09 no-call blocker, presents empty/partial/
failure truthfully, and feeds registry ownership evidence into the existing deterministic
ownership engine without adding a parallel UBO implementation.

The branch is ready for the separately assigned independent Phase 10 quality gate. No
quality-gate report or next-phase implementation was performed.

READY FOR PHASE 10 QUALITY GATE
