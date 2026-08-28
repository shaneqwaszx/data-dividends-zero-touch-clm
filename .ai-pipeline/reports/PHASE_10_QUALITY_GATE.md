# Phase 10 Independent Quality Gate — Expanded ACRA Mock Registry Acquisition

Date: 2026-08-28  
Branch reviewed: `phase/10-expanded-acra-registry-acquisition`  
Accepted Phase 09 baseline / HEAD: `2ca3ad67d16d7f6fa2e48b44bce37b909bf2b8f8`  
Review mode: independent, report-only combined quality gate

## 1. Verdict

**FAIL.** The normal composed Singapore Mock path is genuinely decomposed, makes the
expected `1 / 1 / 1 / 1` calls, preserves all Phase 09 zero-call blockers, fails the
undocumented sandbox expansion closed, and correctly feeds evidence into the existing
Decimal ownership engine. All configured automated suites pass after required
process-control permissions are granted.

Phase 10 is nevertheless not acceptable because the provider-neutral
`RegistryAcquisitionBundle` is not self-validating at the required authority boundary.
Independent direct construction accepted both:

- an overall `COMPLETE` bundle with empty required ownership parties and relationships;
- an overall `COMPLETE` bundle with `OWNERSHIP_PARTIES` and `RELATIONSHIPS` marked
  `NOT_ATTEMPTED`.

That permits a conforming-looking provider result to bypass the required
`PARTIAL / REGISTRY_EXPECTED_DATA_MISSING` branch and advance onboarding despite absent
or unattempted ownership acquisition. This is a High false-success/call-stopping defect
under the Phase 10 planner and quality-gate rules. The same aggregate also accepts
duplicate officer IDs and operation-mismatched record provenance. Remediation is
required before next-development planning.

## 2. Scope Reviewed

The review covered the Phase 10 planner and execution report, accepted Phase 09
implementation/remediation/re-gate, project context/workflow, decision and open-question
logs, regression catalogue, ACRA profile and architecture, the complete working-tree
diff from `2ca3ad6`, all changed backend/frontend code and tests, integration-security
controls, and direct adversarial construction/execution probes.

### Phase acceptance checklist

| # | Planner acceptance requirement | Result | Direct evidence |
|---:|---|---|---|
| 1 | Four explicit bounded Singapore operations | PASS | Adapter invokes entity, officers, parties, relationships distinctly |
| 2 | Provider-neutral orchestration | PASS | Onboarding consumes `RegistryProvider.retrieve_acquisition`; ACRA DTOs stay in adapter |
| 3 | Phase 09 routing/identifier protections | PASS | 39 Phase 09 tests and direct call-count evidence |
| 4 | Zero acquisition for Phase 09 blockers | PASS | All four blockers produced `0 / 0 / 0 / 0` registry calls and no downstream activity |
| 5 | Existing entity mapping retained | PASS | Strict reconstruction, identity binding, mapper and canonical regression pass |
| 6 | Strict officer DTO/evidence | **FAIL** | Source DTO is strict, but normalized model/aggregate accepts duplicate IDs and mismatched provenance |
| 7 | Strict ownership-party DTO/evidence | PASS with finding | Bounds/types/Decimal/reference checks pass; aggregate completeness defect affects authority |
| 8 | Strict relationship DTO/evidence | PASS with finding | IDs/references/percentages are validated; aggregate completeness defect remains |
| 9 | Operation provenance preserved | **FAIL** | Normal adapter preserves it, but aggregate accepts officer provenance labelled `RELATIONSHIPS` |
| 10 | Empty/partial distinguishable from complete | **FAIL** | Normal factory path works; direct aggregate accepts false `COMPLETE` without required evidence |
| 11 | Malformed later response fails safely | PASS | Fixed safe error, failure prefix and zero downstream calls verified |
| 12 | Registry evidence uses existing ownership analysis | PASS | `RegistryAcquisitionOwnershipProvider` maps to existing graph domain/service |
| 13 | No second UBO engine | PASS | Registry adapter performs no traversal, aggregation, thresholding or classification |
| 14 | Existing UBO arithmetic/rules unchanged | PASS | Decimal outputs, inclusive comparator and cycle behavior independently probed |
| 15 | Synthetic scenarios labelled synthetic | PASS | Code/docs/UI are explicit |
| 16 | No ACRA+ provider | PASS | None found |
| 17 | ACRA Mock profile is truthful | **FAIL in part** | Mock/live caveat is strong, but its whole-bundle validation claim overstates implementation |
| 18 | Unknown GoldTier mappings remain `TBD_SPONSOR` | PASS | All four mapping sections retain `TBD_SPONSOR` |
| 19 | Frontend makes no live ACRA claim | PASS | UI says project-owned synthetic and not verified live ACRA |
| 20 | Mongo diagnostic-only | PASS | No application repository/schema/migration added |
| 21 | Q-012 and Q-015 remain open | PASS | Both remain explicitly open |
| 22 | Full backend passes | PASS | 566 passed |
| 23 | Phase 10 focused tests pass | PASS | 18 passed |
| 24 | Phase 09 adversarial tests pass | PASS | 39 passed |
| 25 | Focused POC/provider regressions pass | PASS | 197 passed |
| 26 | Ruff passes | PASS | All checks passed |
| 27 | Strict mypy passes | PASS | 60 source files |
| 28 | Contract tests pass | PASS | 44 passed |
| 29 | Frontend typecheck/tests/build pass | PASS | typecheck; 48 tests; 29-module production build |
| 30 | Secret/security checks pass | PASS with finding | Scanner/unit checks pass; aggregate provenance authority remains deficient |
| 31 | GoldTier validation remains green | PASS | 5 tests; 19 valid, 19 quarantined, 48 not validated |
| 32 | Lifecycle checks pass | PASS | 13 passed in 178.223s after permissioned rerun |
| 33 | `git diff --check` passes | PASS | Line-ending notices only; no whitespace errors |
| 34 | No unresolved Critical/High implementation finding | **FAIL** | PH10-QG-001 is High |

## 3. Diff / Working-Tree Assessment

The branch and HEAD match the accepted Phase 09 baseline. Before this report, the tree
contained 25 modified tracked files and five untracked files. The untracked Phase 10
planner is the supplied task input and is not attributed to implementation. The remaining
untracked implementation/report artifacts are the execution report, registry ownership
adapter, focused Phase 10 test file, and Phase 10 architecture document.

The tracked diff is 1,833 insertions and 170 deletions across 25 files. The changed
surface is consistent with Phase 10: registry connector/domain/orchestration/API/UI,
focused regressions, ACRA contract/architecture, project context, decisions/questions,
and regression catalogue. No staged files existed. No older accepted Phase 09 change was
misclassified as Phase 10.

The quality gate created only this report. It made no implementation, test,
configuration, ordinary-documentation, catalogue, staging, commit, push, merge, rebase,
stash, reset, clean, or next-phase change.

## 4. Registry Acquisition Architecture

The implementation uses the appropriately bounded flow:

```text
OnboardingService
  -> provider-neutral RegistryProvider
  -> AcraRegistryProviderAdapter
  -> four ACRA connector calls / strict source DTOs
  -> RegistryAcquisitionBundle
  -> RegistryAcquisitionOwnershipProvider
  -> existing OwnershipAnalysisService
```

Generic orchestration does not import ACRA source DTOs. Provider, URL, class, module and
operation selection remain backend-owned. The abstraction is small rather than a new
provider-mode framework. No foreign-provider assumption or dynamic provider injection
was found in business logic.

## 5. Operation Decomposition / Call Counts

The acquisition is not four labels over one payload. `fetch_company`, `fetch_officers`,
`fetch_ownership_parties`, and `fetch_relationships` return separate strict envelopes,
are invoked sequentially, and create distinct statuses/provenance.

Normal `202400001A` actual counts were:

| Operation | Calls | Status / records |
|---|---:|---|
| Entity profile | **1** | `COMPLETE / 1` |
| Officers | **1** | `COMPLETE / 1` |
| Ownership parties | **1** | `COMPLETE / 2` |
| Relationships | **1** | `COMPLETE / 2` |

Reading the stored case did not repeat acquisition. An officer-step identity mismatch
produced `1 / 1 / 0 / 0` with the last two operations `NOT_ATTEMPTED`. A relationship
failure produced `1 / 1 / 1 / 1` and zero downstream work.

## 6. Phase 09 Call-Stopping Regression

Each accepted blocker retained exact zero-call behavior:

| Outcome | Entity | Officers | Parties | Relationships | IDP | Ownership | GoldTier |
|---|---:|---:|---:|---:|---:|---:|---:|
| `JURISDICTION_UNRESOLVED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `JURISDICTION_CONFLICT` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `REGISTRY_PROVIDER_NOT_IMPLEMENTED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `REGISTRY_IDENTIFIER_NOT_ELIGIBLE` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

`202400001A + SG` remained eligible and began acquisition. `AU-REG-123 + SG` stopped as
`REGISTRY_IDENTIFIER_NOT_ELIGIBLE` without becoming entity-not-found. The 39-test Phase
09 suite and 197-test focused POC/provider regression suite remained green.

## 7. ACRA Trust Boundary

The current adapter path freshly converts returned Pydantic/dictionary/list structures
to primitives and revalidates strict DTOs. Source text is trimmed, bounded and checked
for Unicode control categories before normalization. UEN identity, source environment,
UTC time and internal query-free HTTPS provenance are checked. Decimal percentages and
collections are bounded. Connector exceptions are translated to fixed safe codes.

The defect is after this DTO boundary: the provider-neutral aggregate is intended to be
the trusted handoff but does not intrinsically enforce mandatory-completeness,
failure-prefix, record-provenance or officer-uniqueness invariants. Current well-behaved
ACRA factories mask that gap.

## 8. Entity Profile Assessment

The retained profile contains only supported UEN, legal name, incorporation country,
entity type, registration date, status, address and provenance. Entity not found returns
`ACRA_ENTITY_NOT_FOUND` and does not call officers/parties/relationships. Requested and
returned UENs remain bound, and the canonical mapper is unchanged. Existing canonical
minimum validation still routes incomplete data to review.

## 9. Officers Assessment

The source DTO bounds ID/name/role/country, rejects control characters, parses dates and
caps the collection at 32. Role values are documented as project vocabulary rather than
official ACRA codes. The empty-officer fixture produces `OFFICERS = EMPTY`, overall
`COMPLETE`, and downstream continuation; the UI does not call it a failure.

However, direct aggregate construction accepted two officers with the same
`OFFICER_A` ID, and accepted an officer whose provenance operation was
`RELATIONSHIPS`. The normalized officer/bundle boundary therefore does not meet the
required strict uniqueness and operation-specific provenance guarantees.

## 10. Ownership Parties Assessment

Natural-person/legal-entity typing, IDs, names, optional registration/country,
six-decimal exact percentage bounds, provenance, uniqueness and 64-record cap are
present. Party percentages are retained only as evidence. No UBO classification occurs
inside registry acquisition.

The aggregate-level missing-evidence defect allows an empty ownership collection to be
labelled `COMPLETE` when constructed outside the ACRA adapter, despite the declared
mandatory semantics.

## 11. Relationships Assessment

Relationship IDs are unique; owners must reference returned parties; owned entities
must be the root or a returned legal entity; self-edges and missing/invalid references
are rejected; relationship percentages remain exact Decimal values. The vocabulary is
limited to project-owned `SHARE_OWNERSHIP`, with no invented control semantics.

Malformed reference construction was rejected in the implementation path. Empty
relationships with otherwise present ownership were independently probed and correctly
produced `PARTIAL / REGISTRY_EXPECTED_DATA_MISSING` through the adapter.

## 12. Acquisition Bundle / Invariant Assessment

Positive controls passed: exactly four ordered operations, collection/result counts,
duplicate ownership-party and relationship IDs, relationship endpoints, failed-status
presence, and safe issue presence are partly validated.

Independent negative construction produced these results:

| Probe | Expected | Actual |
|---|---|---|
| `COMPLETE` with no ownership parties/relationships and both operations `EMPTY` | reject | **accepted** |
| `COMPLETE` with required operations `NOT_ATTEMPTED` | reject | **accepted** |
| Duplicate officer IDs | reject | **accepted** |
| Officer record provenance says `RELATIONSHIPS` | reject | **accepted** |
| Wrong operation order | reject | rejected |
| Count/collection mismatch | reject | rejected |
| Failed result without error/provenance | reject | rejected |
| Invalid relationship endpoint/self-edge | reject | rejected |

The bundle also does not enforce that non-failed operation statuses form a valid
execution prefix or that every record provenance provider/environment/operation agrees
with its collection and entity. It therefore relies on well-behaved construction for
properties the planner explicitly assigns to the domain model.

## 13. Empty / Partial / Failure Semantics

The normal adapter path behaves correctly:

- empty officers: `EMPTY`, bundle `COMPLETE`, downstream may continue;
- missing parties: `EMPTY`, bundle `PARTIAL`, review required, no downstream call;
- missing relationships with present parties: independently probed as `EMPTY`, bundle
  `PARTIAL`, `REGISTRY_EXPECTED_DATA_MISSING`;
- malformed relationship response: failed operation and technical stop;
- relationship unavailable: safe `REGISTRY_OPERATION_UNAVAILABLE` and technical stop;
- officer timeout: independently probed as `REGISTRY_OPERATION_TIMEOUT`, followed by
  two `NOT_ATTEMPTED` operations;
- no entity: later acquisition is not called.

Transport success is not treated as usable evidence by the adapter. The High finding is
that these semantics are not intrinsic to the normalized result accepted by onboarding.

## 14. Ownership Engine Integration

The integration follows the required existing path and contains no second calculator.
The registry provider only maps parties/edges. Existing graph validation, traversal,
path multiplication, aggregation, cycle handling, threshold comparison and limits
remain in `OwnershipAnalysisService`.

Independent registry-fed results were:

| Fixture | Result |
|---|---|
| Normal direct owners | `60`, `40`; analyzed; inclusive threshold unchanged |
| Legal-entity shareholder | `30` met, `10` not met; analyzed through existing graph |
| Multiple owners | `50`, `30` met, `20` not met |
| Multi-level | `30` met, `10` not met; existing indirect multiplication |
| Cycle | `REVIEW_REQUIRED / CYCLE_DETECTED`; no candidates |

No graph/path limit bypass, control-based classification, final UBO fabrication or
threshold change was found.

## 15. Synthetic Fixture / Sandbox Truthfulness

Fixtures, names, endpoints and scenarios are consistently described as project-owned,
fictional and synthetic, never sponsor-approved golden cases. No ACRA+ or foreign
registry implementation exists. The configured sandbox-shaped entity-profile seam
remains isolated; the first expanded sandbox operation fails closed as
`REGISTRY_OPERATION_UNAVAILABLE`, leaves later operations `NOT_ATTEMPTED`, and is not
labelled live.

Q-012 continues to block authoritative expanded sandbox/live binding. No live ACRA call
was attempted or required.

## 16. API / Browser Evidence Assessment

The API exposes overall status, four operation statuses/counts, ACRA provider,
Mock/Sandbox environment, UTC time, opaque evidence reference, safe issues and bounded
normalized records. It excludes raw payloads, raw connector URLs, authorization/headers,
configuration, provider objects/classes/modules, exception text and credentials.

The normal HTTP response was endpoint-free and authorization-free in both focused tests
and inspection. The API truthfulness is nevertheless downstream of the deficient
aggregate: a directly accepted false `COMPLETE` bundle would be projected as complete.

## 17. Frontend Assessment

The React UI renders all four backend-authored operation results and does not derive
status locally. It distinguishes `COMPLETE`, `EMPTY`, `PARTIAL`, `FAILED` and
`NOT ATTEMPTED`, shows safe issues, and prominently says:
`Project-owned synthetic <environment> contract — not verified live ACRA.`

Foreign/unresolved/conflicting/ineligible cases have no acquisition panel. Frontend and
backend contracts align; typecheck, 48 tests and production build pass. No Phase 11 or
exception-workbench redesign was added.

## 18. ACRA Mock API Profile Assessment

The profile accurately and prominently states that all operations, paths, schemas,
limits and errors are project-owned Mock behavior pending Q-012. It documents requests,
responses, types, bounds, nested structures, provenance, synthetic examples,
empty/partial/failure behavior, fixtures and limitations. Every expanded GoldTier
mapping remains `TBD_SPONSOR`.

The document overstates implementation where it says references, IDs, percentages and
provenance are revalidated as a whole and defines `COMPLETE` as requiring ownership
evidence. Those are intended rules, but direct bundle construction disproves their
enforcement. This documentation must be reconciled after code remediation; it must not
be weakened to normalize the defect.

## 19. Security / Bounds Assessment

No Critical secret/auth/TLS/raw-payload issue was found. Collection limits are
32/64/128; strict source DTOs reject malformed text/percentages/identity/environment/
HTTPS/time; errors are sanitized; provider selection is closed; browser projection is
minimized; existing ownership graph/path limits remain active. No new logging or secret
handling was added. Secret tests and scan are green.

Security/truth-boundary finding PH10-QG-002 remains Medium because normalized evidence
can carry duplicate officer identities and false operation provenance if supplied by an
alternate/internal provider construction. Current ACRA adapter output is safe, but the
trusted provider-neutral model is not intrinsically safe as required.

## 20. Mongo / Persistence Boundary

MongoDB remains a diagnostic/read-only connectivity seam. No acquisition repository,
Mongo schema, migration or application import was added. Restart still clears
process-local cases/acquisition/ownership state. `pymongo` is `4.15.1`; running the
diagnostic without `MONGO_URI` returned the expected safe unavailable `ValueError`.
This accepted limitation is not a Phase 10 defect.

## 21. GoldTier Regression

No GoldTier connector, mapping or sequence file changed. Mock search, conditional shell,
policy and amend behavior; existing-party handling; finalization recovery; and
call-stopping remain covered by the 197-test focused suite and 566-test backend suite.
GoldTier validation remains 19 valid, 19 invalid/quarantined and 48 not validated.
There is no real GoldTier/PingFed integration, final mapping, hierarchy write or
Ready-for-Approval behavior.

## 22. Sponsor Dependencies

- **Q-012 remains OPEN:** authoritative ACRA operations/paths/schemas/auth/errors,
  role/relationship vocabulary, pagination/limits, TLS/mTLS/private CA, access and live
  verification remain unknown.
- **Q-015 remains OPEN:** jurisdiction evidence precedence, disagreement authority,
  correction evidence, authenticated reviewer role and resume semantics remain unknown.
- Ownership/UBO policy and final GoldTier mappings remain provisional/open where
  previously recorded. Phase 10 does not falsely close them.

These are later sponsor dependencies, not the cause of this gate failure.

## 23. Full Test / Quality Results

| Check | Independent result |
|---|---|
| Phase 10 focused | **18 passed**, 1 existing deprecation warning |
| Phase 09 adversarial | **39 passed**, 1 existing deprecation warning |
| Phase 10 + Phase 09 total | **57 passed** across the two focused runs |
| Focused zero-touch/UAT/input/provider regression | **197 passed**, 4 existing warnings |
| Full backend | **566 passed**, 4 existing warnings |
| Ruff | **PASS** |
| Strict mypy, no incremental cache | **PASS**, 60 source files |
| Contract tests | **44 passed** |
| Secret-unit tests | **5 passed** |
| Repository secret scan | **PASS** |
| GoldTier validator unit tests | **5 passed** |
| GoldTier fixture validation | **PASS**: 19 valid, 19 quarantined, 48 not validated |
| Delivery asset tests | **4 passed** |
| Python dependency consistency | **PASS** |
| Frontend dependency tree | **PASS**; expected optional platform/feature packages absent |
| Frontend typecheck | **PASS** |
| Frontend tests | **48 passed** after permissioned `esbuild` spawn |
| Frontend production build | **PASS**, 29 modules, output outside repository temp directory |
| Windows/demo lifecycle | **13 passed in 178.223s** after permissioned process-control rerun; owned processes stopped |
| PyMongo / diagnostic | `4.15.1`; expected safe unavailable result without `MONGO_URI` |
| `git diff --check` / staged check | **PASS**; CRLF notices only; nothing staged |

The initial sandboxed frontend test failed only because `esbuild` spawn returned
`EPERM`; the permissioned authoritative rerun passed. The initial sandboxed lifecycle
run failed because owned-process stop returned `Access denied`; the permissioned rerun
passed all 13 tests and cleaned up. Git continues to report the pre-existing inaccessible
untracked `apps/frontend/pytest-cache-files-89airr88/` directory; this review did not
inspect, remove or rely on it.

Authored green tests do not override the independently reproduced aggregate
counterexamples.

## 24. Findings by Severity

### Critical

None.

### High

**PH10-QG-001 — The normalized acquisition aggregate permits false `COMPLETE` states.**

- Evidence: `apps/backend/app/domain/models.py:246-294` validates counts for only
  complete/empty operations and failed-status presence, but does not require ownership
  parties/relationships for `COMPLETE`, reject `NOT_ATTEMPTED` inside `COMPLETE`, or
  enforce a valid operation-status prefix.
- Reproduction: direct `RegistryAcquisitionBundle.model_validate(...)` accepted
  `COMPLETE` with empty ownership evidence and also accepted `COMPLETE` with both
  ownership operations `NOT_ATTEMPTED`.
- Consequence: an alternate/internal provider can bypass
  `REGISTRY_EXPECTED_DATA_MISSING`, let onboarding mark Registry validated, and invoke
  downstream IDP/ownership work despite absent acquisition. API/UI can project the
  false complete state.
- Required remediation: encode the complete/partial/failed operation matrix and failure
  prefix intrinsically; require present usable ownership evidence for `COMPLETE`; bind
  issues to status/failed operation; add direct adversarial model tests and service-level
  call-stopping regression.

### Medium

**PH10-QG-002 — Record identity/provenance invariants are not intrinsic.**

- Evidence: `apps/backend/app/domain/models.py:151-189` validates individual shapes;
  `:263-281` checks only ownership-party/relationship uniqueness and relationship
  endpoints. It does not enforce unique officer IDs or bind record provenance
  operation/provider/environment to its collection/entity.
- Reproduction: duplicate `OFFICER_A` records and an officer with provenance operation
  `RELATIONSHIPS` were both accepted.
- Consequence: normalized evidence can be ambiguous or falsely attributed and then
  projected to the browser. The current ACRA adapter is well behaved, but the trusted
  provider-neutral boundary is bypassable.
- Required remediation: enforce unique officer IDs and collection-specific consistent
  provenance for every record/result, then probe provider/environment/time/identity
  contradictions directly.

**PH10-QG-003 — Tests and documentation claim unverified whole-bundle guarantees.**

- Evidence: the 18-test Phase 10 suite covers normal factories and selected failures but
  has no direct aggregate tests for false complete, not-attempted complete, duplicate
  officer IDs, or record-provenance mismatch. The ACRA profile says these properties are
  revalidated as a whole.
- Consequence: all automated checks pass while required acceptance invariants fail.
- Required remediation: add the planner's direct-construction matrix and reconcile the
  profile to the remediated behavior.

### Low

None newly blocking Phase 10. The accepted pre-existing PDF-before-registry UI
selection debt, process-local persistence and upstream deprecation warnings remain.

## 25. Remaining Technical Debt

- Process-local onboarding/acquisition/ownership state is deliberately non-durable;
  MongoDB remains diagnostic-only.
- Expanded ACRA operations are Mock-only; sandbox-shaped acquisition stops at the first
  undocumented expanded operation.
- Current UEN eligibility is intentionally narrow and is not an official full UEN
  validator.
- Existing ownership threshold/legal semantics and target mappings remain provisional.
- The frontend may select a PDF before registry routing, but registry blockers do not
  upload or process it.
- Starlette/httpx deprecation and intentional adversarial Pydantic serializer warnings
  remain pre-existing.

These items are separate from PH10-QG-001 through PH10-QG-003 and do not excuse them.

## 26. Next-Development Readiness

Next-development planning **must not begin**. Phase 10 requires a bounded remediation
and independent re-gate for the acquisition aggregate's complete/partial/failed matrix,
operation prefix, record uniqueness/provenance binding, direct adversarial tests, and
truthful contract evidence.

This verdict is separate from external readiness: live ACRA remains blocked by Q-012;
jurisdiction authority remains blocked by Q-015; real GoldTier/PingFed, final mappings,
durability and Ready-for-Approval remain unavailable and were not required for this
quality gate.

FAIL — REMEDIATION REQUIRED
