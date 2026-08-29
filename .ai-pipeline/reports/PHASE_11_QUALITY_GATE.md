# Phase 11 Independent Quality Gate

Date: 2026-08-29

Branch reviewed: `main`

Accepted Phase 10 baseline / HEAD: `d472702f1259d9b493edd66b6111246085a29b7a`

Review mode: independent, report-only combined quality gate

## 1. Verdict

**FAIL.** Phase 11's normal factory and HTTP paths demonstrate deterministic
four-field reconciliation, no automatic source winner, multi-blocker call stopping,
replacement history, and replay-free continuation in the authored scenarios. The full
configured regression and quality matrix is green.

Two independently reproduced High integrity defects nevertheless block acceptance:

1. `USE_DOCUMENT_VALUE` persists the canonical legal-name change before the separate
   reconciliation record is saved. An injected reconciliation repository conflict left
   the document-selected canonical name committed while the discrepancy and decision
   remained `OPEN`/absent.
2. The reconciliation domain aggregate is not self-validating at its authority boundary.
   Direct construction and repository revalidation accepted contradictory observations
   as `MATCH`; a forged `MATCHED` current record then passed
   `is_currently_cleared() == True`.

Two Medium contract/invariant defects also remain: a stale duplicate service decision is
accepted after current evidence changes, and a low-confidence conflicting observation
receives a backend `KEEP_REGISTRY_VALUE` action despite being `UNVERIFIABLE`.

Phase 11 requires remediation and an independent re-quality gate. This verdict does not
authorize Phase 12 or next-development planning.

## 2. Scope Reviewed

The review covered the complete Phase 11 working tree against accepted Phase 10, including:

- `AGENTS.md`, project context/workflow, Phase 11 planner and execution handoff;
- accepted Phase 09 and Phase 10 planners, implementation behavior, original gates,
  remediation reports, and passing re-gates;
- current document/IDP evidence and normalization, canonical update service, ownership
  pipeline, CLM readiness, Mock GoldTier flow, zero-touch orchestration, API and frontend;
- the Phase 11 reconciliation domain, comparison service, process-local repository,
  composition, focused tests, architecture/profile documentation, decisions, sponsor
  questions, and regression catalogue;
- integration-security trust boundaries, browser projection, repository hygiene, and
  adversarial failure paths.

The implementation remains within the assigned four fields. No live ACRA, foreign
registry, ACRA+, automatic freshness/source authority, `POSSIBLY_STALE`, Mongo application
repository, workflow-engine replacement, exception queue, assignment/SLA, production
RBAC, authenticated reviewer, full audit service, real GoldTier, Ready-for-Approval,
new UBO rule, or officer/shareholder/ownership reconciliation was found.

## 3. Diff / Working-Tree Assessment

Before this gate report, the Phase 11 working set contained 20 modified tracked paths and
9 untracked paths. Nothing was staged. The working tree is based on accepted Phase 10 HEAD
`d472702f...` on `main`; HEAD and branch did not move during review.

The tracked implementation diff was 1,301 insertions and 71 deletions before including
the nine untracked Phase 11 files. The untracked set included the planner/execution
handoffs, four reconciliation backend modules, the focused test file, and two Phase 11
documents. Git also reports a pre-existing inaccessible ignored frontend pytest-cache
directory; no result depended on it.

This quality gate made no application, test, configuration, ordinary-documentation,
staging, commit, push, merge, rebase, stash, reset, or clean change. Its sole repository
write is this report.

## 4. Observation Model Assessment

**PASS with aggregate findings below.** `ReconciliationObservation` has a closed source
kind and field enum, bounded raw/normalized values, UTC timestamp validation, bounded
opaque URL/query-rejecting references, explicit validity, and document-only confidence.
Raw values and backend-only document source-record IDs are excluded from serialization;
the browser receives normalized bounded evidence only.

Actual source labels are truthful in the exercised path: Registry observations retain
ACRA/Mock provenance; Document observations retain the local IDP provider/environment;
the request identifier alone receives `USER_INPUT`; no fabricated `EXISTING_CASE`
observation is populated.

Human decisions do not rewrite either observation tuple. Normal keep-Registry,
use-Document, and replacement probes retained winning and losing Registry/Document
evidence and provenance.

## 5. Comparison Rules

**PASS for service-generated results.** Independent execution verified:

| Field | Result |
|---|---|
| Legal name | Case/whitespace-only `ACME PTE LTD` versus `Acme   Pte Ltd` semantics match; materially distinct names conflict; no suffix stripping or fuzzy normalization exists |
| Registration identifier | Internal whitespace is removed, case normalized, bounded grammar checked, and nonblank inequality is `CONFLICT` |
| Country of incorporation | Bounded two/three-letter uppercase equality; no country/source priority |
| Registered address | Existing deterministic trim/whitespace/case normalization is reused; materially different addresses conflict; no geocoder/fuzzy service |

The implementation does not contain Registry-, Document-, user-, confidence-, recency-,
current-canonical-, first-observation-, or insertion-order winner logic. It compares the
set of usable normalized values and stops disagreement.

## 6. Outcome Semantics

**PASS for service output; FAIL for direct aggregate construction.** The focused and
independent probes reproduced distinct `MATCH`, `MISSING_IN_SOURCE`, `CONFLICT`,
`UNVERIFIABLE`, and `INVALID` results. Low document confidence reuses the existing `0.85`
document review threshold and does not select a winner. Registry and request confidence
are not fabricated. No `POSSIBLY_STALE` outcome exists.

However, `FieldReconciliationResult.validate_result()` checks only field/ID uniqueness
and whether a discrepancy ID is present. It does not validate the declared outcome
against observation validity or normalized values. This is part of P11-QG-002.

## 7. No-Precedence Assessment

**PASS.** A Registry legal name and a distinct Document legal name remain `CONFLICT`,
with Ownership and GoldTier at zero until an explicit backend-authorized decision. The
normal comparison implementation has no implicit winner. `KEEP_REGISTRY_VALUE` and the
legal-name-only `USE_DOCUMENT_VALUE` are explicit POC operator actions, not evidence
priority rules.

## 8. Discrepancy Model Invariants

**FAIL — P11-QG-002 (High).** Some direct invariants work: `MATCH` cannot be a
discrepancy; duplicate observation IDs, a resolved discrepancy without a decision, an
open discrepancy with a decision, an unknown selected observation, action/source
disagreement, and duplicate aggregate discrepancy IDs are rejected.

The authority boundary remains incomplete:

- contradictory Registry/Document values were accepted as a direct `MATCH` field result;
- an `INVALID` discrepancy with two valid observations and an advertised
  `KEEP_REGISTRY_VALUE` action was accepted;
- an arbitrary non-hex 64-character fingerprint was accepted by the domain model;
- `REVIEW_REQUIRED` was accepted when the only open discrepancy was not referenced by
  any current field result;
- after changing the contradictory field to `MATCH`, cancelling its discrepancy, and
  saving the forged record through `InMemoryReconciliationRepository.save`, the record
  was retained as `MATCHED` and `ReconciliationService.is_currently_cleared()` returned
  `True` against unchanged conflicting evidence.

Evidence: `apps/backend/app/domain/reconciliation.py:168`, `:217`, and `:251-284`.
Repository revalidation cannot repair semantics that the aggregate does not encode.
This can create false-cleared reconciliation authority for CLM readiness and is a High
false-success defect.

Required remediation: make field-result, discrepancy, and case-record validators derive
and enforce outcome/validity/value/action/current-discrepancy semantics; constrain digest
shape; ensure only current open discrepancies establish `REVIEW_REQUIRED`; and add direct
primitive construction plus repository-revalidation regressions for every planner
counterexample and valid control.

## 9. Decision Model / Allowed Actions

**FAIL in part.** Normal usable conflicts advertise `KEEP_REGISTRY_VALUE`; only one
unambiguous valid Document legal-name observation can advertise `USE_DOCUMENT_VALUE`.
Direct attempts to select Document for address, registration identifier, and country all
returned `RECONCILIATION_ACTION_NOT_ALLOWED`. Missing and invalid service-generated
results advertise no action.

**P11-QG-004 (Medium):** a low-confidence legal-name value that also differs creates an
`UNVERIFIABLE` discrepancy with no action and a second `CONFLICT` discrepancy that
advertises `KEEP_REGISTRY_VALUE`, even though its Document observation is itself
`UNVERIFIABLE`. This contradicts the planner and
`docs/contracts/RECONCILIATION_PROFILE.md:12`, which require no value-selection action
for unusable evidence. The remaining `UNVERIFIABLE` blocker prevents progression, so
this did not become false completion, but the backend and frontend expose an action that
should not exist for the available evidence.

Evidence: `apps/backend/app/services/reconciliation.py:374` and `:554-570`.

## 10. Canonical Update Boundary

**FAIL — P11-QG-001 (High).** The typed onboarding method correctly rejects every field
except legal name, checks the expected canonical fingerprint under the case lock, bounds
the selected text, creates a fresh canonical entity, re-runs validation, and leaves the
Registry acquisition entity profile and Document record unchanged.

The cross-repository operation is not atomic. `resolve_discrepancy()` calls
`OnboardingService.apply_reconciled_value()` first, which saves the changed onboarding
case, and only later saves the reconciliation decision. An injected
`ReconciliationRepositoryConflictError` produced this observed state:

```text
public result: RECONCILIATION_CONFLICT
canonical legal name: DOCUMENT SELECTED PTE. LTD.
reconciliation discrepancy: OPEN
reconciliation decision: absent
```

Evidence: `apps/backend/app/services/reconciliation.py:227-253` and
`apps/backend/app/services/onboarding.py:1189`. This violates the evidence-preserving
decision boundary and permits canonical mutation without a retained authorizing
decision.

Required remediation: make canonical application and reconciliation decision one
coordinated process-local unit of work, or provide a proven rollback/commit protocol that
cannot expose either half-state under repository/model/clock/event/save faults. Add
fault-injection tests before and after each fallible post-mutation operation.

## 11. Stale / Fingerprint Safety

**PASS at the HTTP/orchestration boundary; FAIL at the service boundary.** API probes
returned 409 for stale reconciliation version, wrong fingerprint, unknown discrepancy,
cross-case discrepancy, and an old cancelled replacement discrepancy. Extra request
properties and unknown actions returned 422. Fingerprints bind case ID, requested
identifier, current canonical entity, complete Registry acquisition, and current
Document records; discrepancy digests additionally bind field and observations. They
are compared with `hmac.compare_digest` and are not represented as authentication.

**P11-QG-003 (Medium):** the duplicate-decision early return at
`apps/backend/app/services/reconciliation.py:165` occurs before expected-version and
current-evidence verification. After resolving an old discrepancy, changing canonical
evidence, and generating a new current reconciliation, replaying the old action and old
fingerprint directly against the reconciliation service returned the new version-3
`REVIEW_REQUIRED` record instead of rejecting the stale duplicate. It did not mutate the
new record, and the public orchestration boundary rejects it because no active exception
exists, but it violates the required reconciliation-service freshness invariant.

Required remediation: perform case/current-discrepancy/version/current-evidence checks
before any idempotent return; accept a duplicate only in the same current context.

## 12. Multi-Discrepancy Behavior

**PASS for the normal generated path.** Independent counting probe:

```text
initial two conflicts: IDP=1, Ownership=0, GoldTier=[]
after resolving legal name only: Ownership=0, GoldTier=[]
after resolving final address conflict: Ownership load/analyze=1,
  GoldTier=[search, shell, policy, amend]
repeated start after completion: same version; no additional call
```

No premature progress occurred. The automation stayed `WAITING_FOR_REVIEW` until every
current open discrepancy was resolved.

## 13. Resume / Idempotency

**PASS for the normal public path, subject to P11-QG-001/P11-QG-003.** Final valid
resolution records `RESUMING` and re-enters the existing pipeline once. Repeated reads
made no IDP or target call. Repeated completed start returned the same automation
version. The no-match target path remained exactly one `search`, `shell`, `policy`, and
`amend`; Ownership loaded/analyzed once.

The implementation correctly describes this as process-local idempotency, not durable
or production exactly-once behavior.

## 14. Replacement-Document Behavior

**PASS for the exercised valid replacement path.** Independent probe observed:

```text
old IDP provider calls=1
replacement IDP provider calls=1
Registry acquisition unchanged=True
old discrepancy=CANCELLED and retained
new evidence=MATCHED
Ownership load/analyze=1
GoldTier=[search, shell, policy, amend]
old fingerprint resolution HTTP=409
terminal automation=COMPLETED
```

The old observation/discrepancy remains in history; the old Document record is retained
as superseded; only the new Document is processed; Registry is not reacquired. A
replacement that remains blocked continues to stop Ownership/GoldTier through the same
current-reconciliation check.

## 15. Legacy Review Integration

**PASS.** The zero-touch path now projects reconciliation discrepancies as its
authoritative cross-source review items. Reconciliation exception IDs are hidden from
the duplicate legacy review-card rendering, and the legacy exception endpoint delegates
reconciliation-bound evidence versions to the same backend decision service. The changed
legacy regression confirms the Document record no longer stores a competing source-
conflict resolution while the reconciliation decision is retained. No arbitrary manual
correction form was reintroduced.

## 16. API / Browser Projection

**PASS.** The resolution request is case/discrepancy bound, enum bound, requires both
positive versions and a lowercase 64-hex fingerprint, and forbids extras. Independent
results were:

| Probe | Result |
|---|---:|
| Unknown discrepancy | 409 |
| Cross-case discrepancy | 409 |
| Unsupported action | 422 |
| Stale reconciliation version | 409 |
| Wrong fingerprint | 409 |
| Extra property | 422 |

The browser response excludes raw PDF text, raw ACRA payload, raw observation values,
backend-only Document source-record IDs, Registry URL, credentials, connector config,
private authority digest, raw exception text, and class/module details. It retains only
normalized values and bounded safe references needed for review.

## 17. Frontend Assessment

**PASS, except that it faithfully exposes the backend's P11-QG-004 action defect.** The
React view shows Registry and Document in neutral parallel columns, renders backend
outcomes/actions only, performs no local source selection or canonical mutation, escapes
evidence through normal React rendering, retains replacement for unusable evidence, and
states that decisions are explicit POC operator actions with no reviewer/compliance
authority. It does not render duplicate legacy reconciliation actions.

Frontend typecheck, 52 tests, and the 29-module production build passed.

## 18. Security Assessment

**FAIL because P11-QG-001 is an unsafe integrity boundary; otherwise PASS.** No Critical
finding, secret, credential, authorization header, raw source payload, PII log, provider
configuration leak, action injection, cross-case public resolution, XSS-prone raw HTML,
URL reference injection, fake reviewer identity, TLS bypass, or new outbound HTTP path
was found. The repository scanner and secret unit tests passed.

P11-QG-001 is ranked High because a recoverable repository failure can persist an
unauthorized-by-record canonical state. Production reviewer authorization remains
explicitly absent and deferred under Q-015; this POC must not be treated as a production
decision service.

## 19. Phase 09 Regression

**PASS.** All 39 Phase 09 focused/adversarial tests passed. The accepted blockers retain
these exact prohibited call counts:

| Blocker | Entity | Officers | Ownership parties | Relationships | IDP | Ownership | GoldTier |
|---|---:|---:|---:|---:|---:|---:|---:|
| `JURISDICTION_UNRESOLVED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `JURISDICTION_CONFLICT` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `REGISTRY_PROVIDER_NOT_IMPLEMENTED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `REGISTRY_IDENTIFIER_NOT_ELIGIBLE` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Phase 11 reconciliation is not meaningfully started before Registry and current Document
evidence exist.

## 20. Phase 10 Regression

**PASS.** All 52 Phase 10 focused/adversarial tests passed. Normal eligible Singapore
acquisition remains entity profile `1`, officers `1`, ownership parties `1`, and
relationships `1`; read/reconciliation does not reacquire. Empty officers remain a
complete valid outcome; missing required ownership remains partial/review-required;
malformed/unavailable acquisition stops before IDP/reconciliation/Ownership/GoldTier;
the remediated aggregate invariants remain green.

## 21. Ownership / GoldTier Regression

**PASS.** No ownership domain/service or GoldTier connector/mapper file changed. The 197
focused POC/provider tests and 620-test full backend suite preserve Decimal path
multiplication/aggregation, threshold, cycle/incomplete handling, provisional UBO
classification, and target failure/recovery behavior. GoldTier remains Mock-only with
`SEARCH -> conditional SHELL -> POLICY -> AMEND`; blocked reconciliation performs no
target call, and completion still means only `MOCK_GOLDTIER_SUBMITTED`, never approval or
Ready-for-Approval.

## 22. Mongo / Persistence Boundary

**PASS.** Reconciliation composition uses the lock-protected
`InMemoryReconciliationRepository`. No `pymongo` import, application repository, schema,
migration, or durable restart claim was added. Restart loses cases, discrepancies,
decisions, and replay protection. Installed PyMongo is `4.15.1`; with no `MONGO_URI`, the
diagnostic returned the expected safe `MongoDB check failed: ValueError` and exit 1.

## 23. Sponsor Dependencies

- **Q-012 remains OPEN.** Live/subscribed ACRA operation contracts, access, auth,
  endpoint/schema/error/limit/TLS details, and live verification remain unresolved.
- **Q-015 remains OPEN.** Source authority/precedence, authenticated reviewer role,
  separation of duties, production audit/resume semantics, and current/master-data
  ownership remain unresolved.

No code or documentation closes either question. Current behavior remains
synthetic/Mock or Local POC and process-local.

## 24. Documentation Assessment

**FAIL until implementation and claims align.** The field list, comparison rules,
five outcomes, no-precedence policy, legal-name-only Document update, replacement
history, unauthenticated POC operator boundary, process-local persistence, Q-012/Q-015,
and Mock limitations are accurately described.

The execution report's claims that discrepancies are fully self-validating and stale
service retries fail safely are disproved by P11-QG-002/P11-QG-003. The contract says
`UNVERIFIABLE` advertises no action, while P11-QG-004 advertises a conflict action over
the same unusable observation. Documentation must be corrected only after the intended
remediation behavior is implemented and verified.

## 25. Full Test / Quality Results

| Independent check | Result |
|---|---|
| Phase 11 focused | **20 passed** |
| Phase 10 focused/adversarial | **52 passed** |
| Phase 09 focused/adversarial | **39 passed** |
| Focused zero-touch/UAT/input/provider regression | **197 passed** |
| Full backend from repository root | **620 passed** |
| Ruff, no cache | **PASS** |
| Strict mypy, no incremental cache | **PASS**, 64 source files |
| Contract tests | **44 passed**; existing Starlette/httpx deprecation warning |
| Frontend typecheck | **PASS** |
| Frontend tests | **52 passed** |
| Frontend production build | **PASS**, 29 modules; output directed to OS temp |
| Frontend dependency tree | **PASS**; only expected optional platform/feature packages absent |
| Secret unit tests | **5 passed** |
| Repository secret scan | **PASS** |
| Python dependency consistency | **PASS** |
| GoldTier validator unit tests | **5 passed** |
| GoldTier example validation | **PASS**, 19 valid / 19 invalid-quarantined / 48 not validated |
| Delivery asset tests | **4 passed** |
| Windows lifecycle | **13 passed in 150.881s**; launcher-owned processes stopped |
| PyMongo version | **4.15.1** |
| Mongo diagnostic without `MONGO_URI` | **Expected unavailable**, safe `ValueError` |
| `git diff --check` / cached diff check | **PASS**; line-ending notices only; nothing staged |
| Adversarial direct construction/failure/API probes | **FAIL**, reproduced P11-QG-001 through P11-QG-004; public negative API cases otherwise safe |

Non-authoritative invocation notes: a system-Python/root focused attempt and an
apps/backend full-suite attempt lacked the repository's installed/root import context;
the documented `.venv` commands in the correct working directories passed. An invalid
Vitest `--runInBand` attempt was discarded; the supported command passed. Sandboxed
Vitest/Vite initially hit the known Windows `esbuild spawn EPERM`; permissioned reruns
passed. No test was weakened or skipped.

## 26. Findings by Severity

### Critical

None.

### High

- **P11-QG-001 — Canonical update and reconciliation decision are not atomic.** A
  reconciliation save conflict leaves changed canonical data with an open discrepancy
  and no decision.
- **P11-QG-002 — Reconciliation aggregates accept false semantic states.** Contradictory
  evidence can be stored as current `MATCHED` and pass `is_currently_cleared()`.

### Medium

- **P11-QG-003 — Stale duplicate service decision is accepted after evidence changes.**
  The public orchestration layer rejects the replay, but the reconciliation authority
  service does not enforce same-current-context idempotency.
- **P11-QG-004 — Low-confidence conflicting evidence advertises a selection action.**
  Progress remains blocked by the separate `UNVERIFIABLE` discrepancy, but backend/UI
  action semantics contradict the contract.

### Low

None newly classified. The existing Starlette/httpx deprecation warning and
process-local/durable-auth limitations remain known maintenance/deferred boundaries.

## 27. Remaining Technical Debt

Accepted future/dependency work remains separate from current defects: process restart
loses all workflow/reconciliation state; reviewer identity/RBAC and audit retention are
not implemented; real ACRA and real PingFed/GoldTier interoperability are unverified;
the `0.85` IDP threshold and 25% inclusive UBO threshold remain project defaults; and
structured address/identity/country Document application is deliberately unsupported.

These accepted limitations do not excuse P11-QG-001 through P11-QG-004.

## 28. Next-Development Readiness

Phase 11 is **not ready** for next-development planning. Remediation must close both High
integrity defects and the Medium service/action-contract defects, add direct model and
failure-injection regressions, rerun the full matrix, and undergo a separate report-only
re-quality gate.

Real ACRA verification and real GoldTier integration remain separately blocked and were
not attempted. Phase 12 was neither designed nor started.

FAIL — REMEDIATION REQUIRED
