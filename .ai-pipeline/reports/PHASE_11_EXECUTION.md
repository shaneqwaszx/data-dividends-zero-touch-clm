# Phase 11 — Execution Report

## 1. Executive Summary

Phase 11 implements a bounded, source-neutral reconciliation and human-review/resume
foundation for legal name, registration identifier, registered address, and country of
incorporation. Registry, document/IDP, user-input, and available current-case facts are
represented as separate observations. Deterministic comparison produces one of five
typed outcomes; any disagreement or unusable evidence remains an explicit discrepancy.

The implementation introduces no automatic source winner. A usable conflict is resolved
only by a backend-advertised `KEEP_REGISTRY_VALUE` or, for the one currently safe
canonical update, `USE_DOCUMENT_VALUE`. The selected value is applied through typed
backend logic while the original Registry and IDP observations, discrepancy, and decision
remain intact. Multiple blockers stop ownership and GoldTier until every blocker is
resolved, after which the existing process-local workflow resumes exactly once.

The full verification matrix is green. No unresolved Critical or High implementation or
integration-security finding remains. This report is the Execution handoff only; no
independent Phase 11 Quality Gate was performed.

Baseline: `d472702f1259d9b493edd66b6111246085a29b7a` on `main`. In accordance with the
execution prompt, all work remains unstaged and uncommitted.

## 2. Scope Implemented

- Four active reconciliation fields: legal name, registration identifier, registered
  address, and country of incorporation.
- Source-neutral, provenance-bearing observations and complete field results.
- Distinct `MATCH`, `MISSING_IN_SOURCE`, `CONFLICT`, `UNVERIFIABLE`, and `INVALID`
  outcomes.
- First-class self-validating discrepancies with retained observations, status,
  backend-authorized actions, decision, and evidence/version binding.
- Typed POC operator decisions without fabricated reviewer identity or authority.
- Evidence-preserving legal-name canonical update through the onboarding service.
- Multi-discrepancy call stopping, stale-action rejection, replacement-document
  re-evaluation, and process-local resume.
- A safe reconciliation API projection and the smallest case/discrepancy/version-bound
  resolution endpoint.
- A focused frontend reconciliation panel driven only by backend-advertised actions.
- Architecture, contract, decision, sponsor-question, project-context, README, and
  regression-catalogue updates.

## 3. Files Changed

Backend implementation:

- `apps/backend/app/domain/reconciliation.py` — new observation, result, discrepancy,
  decision, and case-level reconciliation models and invariants.
- `apps/backend/app/services/reconciliation.py` — new deterministic comparison,
  discrepancy, decision, evidence-fingerprint, replacement, and freshness logic.
- `apps/backend/app/services/reconciliation_repository.py` — new atomic process-local
  repository with optimistic version checks and full model revalidation on save.
- `apps/backend/app/services/reconciliation_errors.py` — safe request/infrastructure
  error boundary.
- `apps/backend/app/services/onboarding.py` — canonical entity fingerprinting and typed,
  validated legal-name application without changing Registry evidence.
- `apps/backend/app/services/zero_touch_orchestration.py` — reconciliation checkpoint,
  per-discrepancy business exceptions, decision/resume path, legacy-safe evidence refresh,
  and call stopping.
- `apps/backend/app/services/clm_orchestration.py` — optional reconciliation-readiness
  boundary and immutable reconciliation-cleared document reference.
- `apps/backend/app/domain/zero_touch.py` — bounded reconciliation action/event/error
  enums.
- `apps/backend/app/api_models.py` — minimized browser-safe reconciliation projections.
- `apps/backend/app/main.py` — typed resolution request and discrepancy resolution route.
- `apps/backend/app/composition.py` — shared process-local reconciliation composition.

Tests and frontend:

- `apps/backend/tests/test_phase11_reconciliation.py` — 20 focused model, comparison,
  workflow, API, security, replacement, and idempotency tests.
- `apps/backend/tests/test_zero_touch_orchestration.py` — migrated legacy source-conflict
  assertion to the authoritative reconciliation decision.
- `apps/frontend/src/types.ts`, `apps/frontend/src/api.ts`,
  `apps/frontend/src/App.tsx`, and `apps/frontend/src/styles.css` — typed API support and
  neutral reconciliation/review presentation.
- `apps/frontend/src/App.test.tsx` — match, conflict/action, resolved-decision, and
  multi-blocker rendering coverage.

Documentation and regression evidence:

- `docs/architecture/PHASE_11_RECONCILIATION_REVIEW_RESUME.md` — new architecture record.
- `docs/contracts/RECONCILIATION_PROFILE.md` — new bounded contract/profile.
- `docs/architecture/ARCHITECTURE.md`, `docs/architecture/README.md`, `README.md`, and
  `docs/PROJECT_CONTEXT.md` — current flow and limitation updates.
- `docs/decisions/DECISION_LOG.md` — D-030 working decision.
- `docs/sponsor-questions/OPEN_QUESTIONS.md` — Q-012/Q-015 status preserved.
- `.agents/skills/poc-regression-check/references/regression-catalogue.md` — Phase 11
  scenarios, invariants, and evolution record.
- `.ai-pipeline/reports/PHASE_11_EXECUTION.md` — this report.

The user-supplied Phase 11 planner was read as the primary source of truth and was not
modified. The pre-existing inaccessible untracked
`apps/frontend/pytest-cache-files-89airr88/` directory was not accessed or changed.

## 4. Observation Model

`ReconciliationObservation` retains:

- immutable observation ID and field;
- raw value only in the backend domain record and a bounded normalized value for safe
  projection;
- `USER_INPUT`, `REGISTRY`, `DOCUMENT_IDP`, or `EXISTING_CASE` source kind;
- actual source system/environment where supplied;
- UTC observation/retrieval time;
- an opaque, URL-rejecting evidence reference;
- document confidence only when IDP genuinely supplied it;
- `VALID`, `MISSING`, `INVALID`, or `UNVERIFIABLE` validity.

Observations are never rewritten when a decision selects another value. Raw values,
backend-only observation source-record IDs, raw ACRA data, and raw PDF text are not in
the browser observation projection. Bounded case document IDs/versions and opaque
discrepancy fingerprints are exposed only for replacement and decision binding.

## 5. Field Comparison Rules

| Field | Deterministic Phase 11 rule |
|---|---|
| Legal name | Trim, collapse whitespace, and compare case-normalized text. Formatting-only differences match; distinct legal names are not over-normalized. |
| Registration identifier | Trim/case-normalize, validate against the bounded identifier shape, then require exact normalized equality. |
| Country of incorporation | Normalize and validate a bounded two/three-letter country code, then require exact equality. |
| Registered address | Reuse the existing deterministic whitespace/case normalization and require exact normalized equality. No fuzzy match, geocoder, or external enrichment. |

Existing document normalization is reused rather than replaced by an unrelated
algorithm. Confidence never selects a winner: confidence below the configured document
review threshold makes the observation `UNVERIFIABLE`.

## 6. Reconciliation Outcomes

- `MATCH` — every usable normalized observation agrees.
- `MISSING_IN_SOURCE` — the document source lacks a usable field.
- `CONFLICT` — usable nonblank values disagree.
- `UNVERIFIABLE` — supplied evidence cannot be trusted sufficiently for deterministic
  comparison, including genuinely low IDP confidence.
- `INVALID` — supplied evidence violates the bounded field shape.

Missing, invalid, unverifiable, and conflicting evidence remain distinct. No
`POSSIBLY_STALE` rule or freshness authority was introduced.

## 7. Discrepancy Model

Each `ReconciliationDiscrepancy` contains one field, every competing observation, its
non-match outcome, creation time, `OPEN`/`RESOLVED`/`CANCELLED` status, backend-authored
allowed actions, an evidence fingerprint, and an optional validated decision. Direct
model construction rejects duplicate observation/discrepancy IDs, mismatched fields,
`MATCH` discrepancies, unknown selected observations, decision/source disagreement,
unauthorized actions, fingerprint mismatch, and resolved cases with open blockers.

The repository revalidates the complete record and all nested instances before every
save. Replacement evidence cancels superseded open discrepancies but retains them for
history, then creates or clears the current discrepancy from the new evidence.

## 8. Human Decision Model

Implemented actions:

- `KEEP_REGISTRY_VALUE` for a usable value conflict;
- `USE_DOCUMENT_VALUE` only for exactly one unambiguous, valid document legal-name
  observation that the backend can safely validate and apply.

Missing, invalid, and unverifiable evidence advertises no selection action and requires
replacement evidence. Address, registration-identifier, and country document selection
is not advertised because the current canonical backend cannot safely reconstruct a
structured address or change the request-bound identity/routing facts without broader
sponsor rules. `ENTER_CORRECTED_VALUE` was not implemented, avoiding the removed
frontend-only correction bypass.

The decision retains the selected observation/value, action, UTC decision time,
reconciliation version, and evidence binding. It deliberately stores no reviewer name,
email, role, approval claim, or caller-supplied note.

## 9. Canonical Decision Application

`USE_DOCUMENT_VALUE` calls the typed `OnboardingService.apply_reconciled_value` method
under the case lock with an expected canonical fingerprint. The service supports only
legal name in Phase 11, bounds and validates the selected text, creates a fresh canonical
entity, re-runs canonical validation, and records a safe case event.

The original `registry_acquisition.entity_profile` remains unchanged, as do the document
record and all reconciliation observations. The discrepancy and decision retain the
selected value and time. A rejected canonical update fails safely and does not become an
arbitrary JSON patch.

## 10. Resume / Idempotency Semantics

- Resolving one of several discrepancies leaves the automation
  `WAITING_FOR_REVIEW` and ownership/GoldTier uncalled.
- Remaining reconciliation exception evidence is refreshed after a canonical change, so
  both the dedicated endpoint and the compatible legacy exception path remain bound to
  current evidence.
- Final valid resolution records `RESUMING`, re-evaluates readiness, and proceeds through
  the existing ownership and target pipeline.
- Expected automation version, expected reconciliation version, case/discrepancy IDs,
  and a constant-time-compared evidence fingerprint reject stale or cross-evidence use.
- A duplicate identical reconciliation-service decision returns the existing record;
  stale external retries fail safely.
- Repeated reads do not call ACRA or IDP. Starting an already completed automation is a
  no-op. Ownership and GoldTier ledger/idempotency behavior remains unchanged.
- State is process-local; restart recovery is explicitly not claimed.

## 11. API Changes

The zero-touch summary now includes a safe `reconciliation` object containing status,
version, source document versions, field outcomes, normalized observation summaries,
discrepancy status/actions/fingerprint, and decision summary.

New endpoint:

```text
POST /api/clm/zero-touch/cases/{case_id}/reconciliation/discrepancies/{discrepancy_id}/resolve
```

The request is extra-field-forbidden and accepts only a reconciliation action enum,
expected automation version, expected reconciliation version, and a 64-character
lowercase hexadecimal evidence fingerprint. The endpoint is case- and discrepancy-bound
and delegates canonical update/resume authority entirely to backend services.

## 12. Frontend Changes

The reconciliation panel shows field, Registry value, Document value, outcome, source
kind/system/environment/time/confidence, backend-advertised actions, and any resolved
decision. Registry and Document use neutral parallel cards; neither is marked preferred
or authoritative. Resolved copy states that the choice was an explicit POC operator
action and claims no reviewer/compliance identity.

The review view hides duplicate legacy exception cards for reconciliation discrepancy
IDs and renders only actions supplied by the reconciliation response. Missing/invalid/
unverifiable evidence points to replacement-document behavior. There is no arbitrary
field editor, general exception dashboard, assignment queue, or production RBAC UI.

## 13. Existing Document Review Integration

Current IDP evidence is adapted into reconciliation observations after Registry
acquisition. Reconciliation, not the legacy document review record, is authoritative for
cross-source conflicts in the zero-touch path. The document record remains evidence and
does not receive a competing conflict-resolution decision.

Replacement documents retain prior records, cancel superseded open reconciliation
discrepancies, compute new current evidence, and resume only if all current blockers are
cleared. Text-unavailable behavior retains the accepted blocker mapping. Existing manual
document APIs remain compatible outside the new authoritative zero-touch path.

## 14. Call-Stopping

For the default ACRA Mock/IDP/ownership/Mock GoldTier route:

| Point | ACRA acquisition | IDP | Ownership | Mock GoldTier |
|---|---:|---:|---:|---:|
| Conflict first reaches review | entity profile `1`, officers `1`, shareholders `1`, appointments `1` | `1` for the current document | `0` | `0` |
| Read or one of several decisions | unchanged | unchanged | `0` | `0` |
| Final valid resolution | unchanged | unchanged | graph load/analyze once | `search`, `shell`, `policy`, `amend` once each on the no-match path |
| Repeated completed start/resume | unchanged | unchanged | no duplicate | no duplicate |
| Replacement document | Registry unchanged | one processing call for the new document | still `0` until clear, then once | still `0` until clear, then existing sequence once |

The Phase 11 integrated tests assert zero target calls while blocked and exactly
`[search, shell, policy, amend]` after final resolution. Phase 09/10 regression suites
retain the precise Registry zero-call blockers and four-operation acquisition counts.

## 15. Security / Provenance

The integration-security checklist was applied to the new ACRA/IDP/browser boundary.
No new outbound HTTP call, credential flow, TLS setting, or GoldTier payload was added.
Findings:

- no unresolved Critical or High finding;
- raw Registry payloads, raw PDF text, backend-only observation source-record IDs, raw
  values, internal exceptions, and credentials are excluded from the browser model;
- evidence references reject URLs/query strings and are bounded opaque labels;
- normalized values and all request fields are length/shape bounded;
- enum actions plus case/discrepancy/version/fingerprint checks prevent arbitrary patch
  or client-asserted authority;
- safe errors expose stable codes/messages only;
- no PII/KYC or raw evidence logging was added;
- no fake reviewer identity or production approval claim exists;
- Mock/local provider and environment labels remain truthful.

The remaining authorization limitation is known and tied to open Q-015: this POC has no
authenticated reviewer/RBAC boundary and must not be deployed as a production decision
service.

## 16. Mongo / Persistence Boundary

Reconciliation state, discrepancies, and decisions use a lock-protected in-memory
repository and are lost on process restart. MongoDB is not imported into reconciliation,
onboarding, document, ownership, CLM, or zero-touch composition. No schema, migration, or
durable audit claim was introduced.

`pymongo` remains the pre-existing diagnostic dependency at `4.15.1`. With no
`MONGO_URI`, the diagnostic returned the expected safe unavailable result
`MongoDB check failed: ValueError`; live Mongo is not required.

## 17. GoldTier / Ownership Regression

GoldTier DTOs, connector behavior, endpoint paths, mapping, and operation ordering were
not changed. The accepted Mock sequence remains `SEARCH -> conditional SHELL -> POLICY ->
AMEND`. Ownership graph retrieval, Decimal path multiplication/aggregation, thresholds,
cycle/incomplete handling, and provisional UBO semantics were not changed.

Reconciliation is placed after Registry and IDP and before ownership. A blocker therefore
cannot reach either ownership or GoldTier. The Phase 09 adversarial, Phase 10 acquisition,
197-test POC/provider, and 620-test backend suites are green.

## 18. Exact Test Results

| Check | Final result |
|---|---|
| `python -m pytest apps/backend/tests/test_phase11_reconciliation.py -q --disable-warnings --maxfail=1` | PASS — 20 passed |
| `python -m pytest apps/backend/tests/test_phase10_registry_acquisition.py -q --disable-warnings --maxfail=1` | PASS — 52 passed |
| `python -m pytest apps/backend/tests/test_phase09_jurisdiction_gateway.py -q --disable-warnings --maxfail=1` | PASS — 39 passed |
| Focused `test_zero_touch_orchestration.py`, `test_phase_07_uat.py`, `test_phase_08_input_driven.py`, and `test_phase06_provider_conformance.py` | PASS — 197 passed, 4 existing warnings |
| `python -m pytest apps/backend/tests --disable-warnings --maxfail=1` | PASS — 620 passed, 4 warnings in 13.85s |
| `python -m ruff check apps/backend scripts tests` | PASS — all checks passed |
| `python -m mypy --no-incremental apps/backend/app` | PASS — 64 source files, no issues |
| `python -m unittest discover -s tests/contract -p 'test_*.py'` | PASS — 44 tests; one existing Starlette/httpx deprecation warning |
| `npm.cmd run typecheck` | PASS |
| `npm.cmd test` | PASS — 1 file, 52 tests |
| `npm.cmd run build` | PASS — 29 modules; production assets built |
| `npm.cmd ls --all` | PASS — exit 0; platform/feature packages shown as optional only |
| Secret-check unit discovery | PASS — 5 tests |
| `python scripts/check_secrets.py` | PASS — no supported secret patterns found |
| `python -m pip check` | PASS — no broken requirements |
| GoldTier validator unit suite | PASS — 5 tests |
| `python scripts/validate_goldtier_examples.py --if-present` | PASS — expected classification: 19 valid, 19 invalid/quarantined, 48 not validated |
| Phase 07 delivery-asset unit suite | PASS — 4 tests |
| Windows demo lifecycle suite | PASS — 13 tests in 152.054s; start/health/reset/ownership/stop behavior verified |
| `python -c "import pymongo; print(pymongo.__version__)"` | PASS — `4.15.1` |
| `python scripts/check_mongodb.py` without `MONGO_URI` | EXPECTED UNAVAILABLE — exit 1, safe `ValueError`; live Mongo not required |
| `git diff --check` | PASS — no whitespace errors; CRLF conversion notices only |
| `git diff --cached --check` | PASS — no staged changes |

The frontend test/build and Windows lifecycle commands were rerun with host process
permission because the restricted sandbox cannot spawn esbuild or terminate the exact
launcher-owned Windows process trees. Their permitted final runs passed. No test was
weakened or skipped.

## 19. Sponsor Dependencies Preserved

- **Q-012 remains OPEN:** authoritative live/subscribed ACRA contract/access is not
  available. Phase 11 uses the accepted ACRA Mock boundary and makes no live claim.
- **Q-015 remains OPEN:** source precedence, disagreement authority, authenticated
  reviewer authority, production resume policy, durable decision/audit behavior, and
  current-versus-master-data ownership are not sponsor-confirmed.
- D-030 records the bounded development choice without presenting it as sponsor approval.
- No source precedence exists: Registry, Document, User Input, confidence, and recency do
  not automatically win. The only canonical selection is an explicit current-POC
  operator action advertised by the backend.

## 20. Non-Goals Confirmation

Not implemented: Phase 12, live ACRA, foreign registry/ACRA+, automatic precedence or
freshness authority, `POSSIBLY_STALE`, durable Mongo persistence, workflow-engine
replacement, case queue/assignment/aging/SLA, production RBAC, authenticated reviewer
identity, full audit service, real GoldTier, Ready-for-Approval, new UBO rules,
multi-level GoldTier hierarchy creation, or officer/shareholder/ownership reconciliation.

## 21. Remaining Risks

- Process restart loses reconciliation state and recorded decisions; this is explicit
  POC behavior, not recoverable workflow persistence.
- POC operator decisions are unauthenticated. Production use requires sponsor-confirmed
  reviewer authority/RBAC and audit semantics under Q-015.
- `USE_DOCUMENT_VALUE` is intentionally limited to legal name. Structured address,
  request identity, and jurisdiction/routing replacement require a separately designed
  and sponsor-aligned canonical change contract.
- Live ACRA interoperability remains unverified under Q-012.
- Existing dependency warnings include the known Starlette TestClient/httpx deprecation;
  it does not affect the green test result but should be handled in dependency maintenance.
- Git reports a pre-existing inaccessible untracked frontend pytest-cache directory; it
  is outside Phase 11 and was left untouched.

## 22. Readiness

The assigned Phase 11 scope is implemented, documented, security-reviewed, and verified
against the full Planner matrix. The working tree is deliberately unstaged and ready for
an independent report-only Phase 11 Quality Gate.

READY FOR PHASE 11 QUALITY GATE
