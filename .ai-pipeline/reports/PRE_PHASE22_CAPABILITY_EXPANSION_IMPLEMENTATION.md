# Pre-Phase 22 Capability Expansion Implementation Report

Date: 2026-09-24
Branch: `feature/pre-phase22-capability-expansion`
BASE_SHA: `3ca232b58c3842f413c4552dbd3b85aabea4591c`
Accepted base tree: `848dcde901a33908bc5a3a6446021da2489d6be1`
Phase 22: on hold

## Integrated outcome

The separable local intelligence, persistence, policy, SME, UI, activity-event, and CSV
slices are implemented. GoldTier XPI transformation/preview/connector/search and
Exception Workbench assignment/note/SLA mutations are not implemented because their
named contract artefacts or sponsor authority are absent. No external request or target
write occurred. The default target remains Mock GoldTier.

This candidate is not publishable unless the fresh independent gate returns the exact
verdict `PASS`. Verification and gate evidence are recorded below when complete.

## GoldTier XPI

- Named guideline PDF and Postman collection: absent from the supplied attachment
  directory and repository.
- Host, user ID, and write opt-in variables: absent by presence-only inspection.
- DNS/TLS/HTTP/Search/write evidence: `NOT_EXECUTED`.
- XPI DTO, mapper, preview, connector, and mode: deliberately not created.
- Existing EDS-shaped Mock connector and replay ledger: unchanged.
- The reconciliation includes an operation comparison and provisional mapping matrix;
  every proprietary value remains `UNKNOWN_BLOCKING`.
- Related-party child-ID acquisition remains contract-blocked.

See `docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md` and
`.ai-pipeline/reports/GOLDTIER_XPI_SANDBOX_DIAGNOSIS.md`.

## Onboarding intelligence

One source-neutral `onboarding_intelligence` owner now produces a versioned,
case-bound safe projection:

- entity resolution: exact identifier/country rules before weighted linkage;
  `EXACT_MATCH | PROBABLE_MATCH | REVIEW_REQUIRED | NO_MATCH | CONFLICT`; bounded
  candidate IDs, deterministic probability proxy, feature evidence, top contributions,
  safe source labels, and model/reason metadata;
- UBO assistance: consumes the current deterministic Decimal candidate; emits
  `LIKELY_UBO | REVIEW | UNLIKELY_UBO`, `ML_ASSISTED`, and
  `NOT_LEGAL_UBO_DETERMINATION`; never recalculates or overwrites ownership;
- mock risk: uses entity/document/ownership evidence only; unavailable external groups
  are `NOT_ASSESSED`; emits bounded score/band/contributions and the permanent labels
  `MOCK_ADVISORY_RISK / NOT_COMPLIANCE_DECISION`.

Exact name-only/address-only auto-match is prohibited. Ties, identifier-country
conflicts, and weak evidence route to review. The risk readiness flag defaults false;
if explicitly bound true on a new case, only the existing workflow owner creates a
typed high-risk review stop before target execution.

Synthetic evaluation `synthetic-adverse-v3` observed entity outcomes `17/17`, UBO advice
`3/3`, and mock-risk bands `5/5`. Entity auto-match metrics on the 17-case adverse set
were precision/recall/F1 `1.000000`, false-positive rate `0.000000`, and false-negative
rate `0.000000` (TP 5, FP 0, TN 12, FN 0). These are tiny synthetic deterministic metrics,
not production accuracy, fairness, calibration, or sponsor validation.

## Policy and persistence

The existing Policy Catalogue adds 13 runtime rules: entity auto-match/review/ambiguity,
five feature weights, UBO likely/unlikely thresholds, mock-risk medium/high thresholds,
and `MOCK_RISK_BLOCKS_READINESS`. Cross-rule validation rejects overlapping thresholds
or weights that do not total one. The exact historical eight-rule catalogue receives a
single audited migration; unknown partial shapes fail closed.

New cases bind the advisory policy immutably. Case-envelope schema is v5 with one
optional intelligence projection. Strict v1-v4 reads preserve legacy state; schema-v4
cases retain `intelligence = null` and are not reinterpreted or rewritten. Memory and
Mongo repositories use identity checks, version CAS, whole-case deletion, and no stale
resurrection. Schema-v5 reads cross-bind catalogue version, entity weights/outcome,
UBO/risk thresholds, model versions, and the risk readiness flag to the immutable case
policy; unknown risk-limitation names and contradictory evidence fail closed. No
parallel audit store or policy owner was added.

## Exception Workbench and audit

Implemented:

- the existing Attention Queue automatically carries the new typed entity-resolution
  and mock-risk exception categories and opens the owning case;
- the case detail view shows advisory evidence and explicit labels;
- successful intelligence evaluation emits a safe `INTELLIGENCE_EVALUATED` activity
  event with bundle/policy context;
- `/api/clm/zero-touch/activity.csv` reuses backend case/team authorization and current
  filters, exports a maximum of 100 projected rows, retains UTC, uses fixed columns,
  hardens spreadsheet formulas, and sets no-cache/no-sniff/download headers.

Not implemented:

- claim/assign/unassign, notes, due time, or SLA policy. Q-016 supplies no authorized
  capability/role, target-user rules, CAS contract, or audit semantics. Implementing
  them would invent backend authority.
- dedicated risk/entity list fields beyond the typed exception filter. Existing queue
  priority/status/team/exception filters remain authoritative.
- a production compliance audit, immutable archive, retention policy, historical actor
  attribution, or complete new-action ledger.

## SME scenarios

- `SME_STRAIGHT_THROUGH`: Mock ACRA and local document/reconciliation/Decimal ownership,
  advisory intelligence, then the unchanged Mock GoldTier path.
- `SME_AMBIGUOUS_ENTITY`: two fictional equal descriptive candidates produce a
  deterministic ambiguity and typed review before target execution.
- Original scenarios remain available and covered by regression tests.

See `docs/demo/PRE_PHASE22_INTELLIGENCE_DEMO.md`.

## APIs, schemas, configuration, and authority changes

- Additive authenticated GET: `/api/clm/zero-touch/cases/{case_id}/intelligence`;
  inaccessible and absent cases share the existing safe 404.
- Additive authenticated GET: `/api/clm/zero-touch/activity.csv`.
- Case schema: v4 to v5; backward-compatible read only, no on-read rewrite.
- Business exceptions: `ENTITY_RESOLUTION_REVIEW_REQUIRED` and
  `MOCK_RISK_REVIEW_REQUIRED`.
- Provider/connector/config status: no GoldTier/ACRA/IDP provider activation or mode
  change; no network allowlist or secret change.
- Architecture: one new advisory owner, accepted in canonical ADR-003 and D-047;
  the earlier Aegis plan record ADR-0001 is superseded by that project decision.
- Sponsor questions: Q-004, Q-016, Q-017, and all GoldTier contract questions remain
  open; none is closed by configurable local defaults.

## Security and privacy

The projection omits raw provider payloads, identity values, ownership display names,
document bodies, credentials, cookies, private notes, and target responses. Fingerprints
are SHA-256 over safe case-bound inputs. Frontend cache keys include user and case,
preserve cancellation, invalidate on supporting mutation, and cancel/remove on deletion.
CSV formula hardening covers `=`, `+`, `-`, `@`, tab, CR, and leading whitespace before
those prefixes. No `.env` or secret value was inspected.

## Industry sources and governance

GLEIF/ISO identity concepts, FATF beneficial-ownership/risk guidance, NIST AI RMF,
NIST log guidance, and Fellegi-Sunter/Splink technical practice are recorded in
`docs/research/INDUSTRY_STANDARD_USAGE.md`. All numeric weights, thresholds, and scoring
contributions are project-defined and editable where materially useful. Three model
cards state purpose, method, data classification, evaluation, thresholds, limitations,
human boundary, prohibited uses, and last evaluation date.

## Complexity closeout

Complexity status is `exceeded-and-governed`. The existing `main.py`, zero-touch
orchestrator, Mongo store, `App.tsx`, and several historical test files remain above
the preferred local size threshold. The capability does not add a duplicate owner or
fallback: scoring, evaluation, export, API projection, repository behavior, and UI
presentation are extracted into focused modules, while hotspot edits are limited to
composition, canonical workflow integration, schema compatibility, or route wiring.
Further decomposition is a follow-up architecture task, not a reason to move ownership
out of the current canonical boundaries.

## Verification evidence

Current source revision remains uncommitted `HEAD`
`3ca232b58c3842f413c4552dbd3b85aabea4591c`; no path is staged. The independent reviewer
must compute and record the final pre-gate working-tree content fingerprint after this
report update.

Final implementation verification:

- backend full pytest suite: `PASS`, 1,236 passed / 29 environment-skipped; the final
  rerun included the live-memory seeder test that had previously shown one intermittent
  15-second timeout;
- Ruff over backend application/tests, repository scripts, and governance tests:
  `PASS`; strict mypy: `PASS`, 101 source files;
- frontend Vitest: `PASS`, 21 files / 276 tests; TypeScript typecheck: `PASS`;
  production build: `PASS`, 113 modules;
- contract unittest suite: `PASS`, 44 tests;
- scoped security/governance unittest suite: `PASS`, 203 tests;
- Windows lifecycle suite: `PASS`, 23 tests, including occupied-port, reset, auth
  probe, ownership, and shutdown paths;
- Playwright: final isolated lifecycle run `PASS`, 14/14. An earlier full run had one
  reload-timing failure; the exact test then passed with diagnostics, once ordinarily,
  five consecutive ordinary reruns, and the final full run without a source workaround;
- physical Mongo: final disposable-container run `PASS`, 8 suites / 29 tests. The
  initial 22/28 result exposed BSON rejection of a `frozenset`; a failing BSON
  round-trip test reproduced it, the canonical serializer was fixed, and the entire
  physical matrix passed. The task-owned container was removed and Docker Desktop,
  which this task started, was stopped;
- architecture, project-state, tooling-config, policy-authority,
  external-provider-readiness, and secret checks: `PASS`;
- synthetic intelligence evaluation: `PASS`, entity 17/17, UBO 3/3, mock risk 5/5,
  with the bounded synthetic-only limitations stated above;
- GoldTier example validator: command `PASS`, with the expected current contract truth
  `VALID=19`, `INVALID_QUARANTINED=19`, `NOT_VALIDATED=48`;
- Python dependency check: `PASS`; tracked diff whitespace check: `PASS`.

The first sandboxed frontend invocation was blocked by child-process `EPERM`; the same
command passed outside the restricted sandbox. The first security harness attempt was
blocked by temporary-directory permissions and then exposed one real unbounded
`dev_context.py` status-output defect; that defect was fixed and the final scoped
203-test run passed. A later unscoped root discovery was invalid because it traversed
the separately configured contract package without its discovery path; the exact
44-test contract command and 203-test governance command both passed. These are retained
as failure history rather than hidden by the final green evidence.

The first independent gate reviewed fingerprint
`67f209d3ea6a5debbbc2f44d9d7cff273a78ff12198a775a61215c79ff00e163`
and returned `FAIL`. Its four current-slice findings were remediated under focused
RED/GREEN evidence:

- loss-aware Unicode alphanumeric normalization now treats unusable normalized values
  as unassessed; distinct usable identifiers cannot auto-match; country conflict is
  fail-closed; and generic legal-form agreement is excluded from independent strong
  corroboration;
- `EntityResolutionResult`, `EntityCandidateEvidence`, `UboAdviceResult`, and
  `MockRiskAssessment` now enforce outcome/candidate, feature/probability,
  ownership/probability/threshold, score/band/signal, and missingness invariants. Raw
  schema-v5 corruption tests cover entity, UBO, and risk nested values;
- CSV hardening now skips every leading Unicode whitespace or Unicode control character
  before checking `=`, `+`, `-`, or `@`, with NUL, vertical-tab, form-feed, no-break-space,
  and em-space adverse cases;
- accepted project ADR-003 now records the canonical owner and is linked from D-047;
  the earlier Aegis plan ADR is marked superseded.

The refreshed `synthetic-adverse-v3` set has 17/17 entity outcomes with TP 5, FP 0,
TN 12, and FN 0. After the final semantic-validator change, the full backend suite,
Ruff, strict mypy, frontend 21-file/276-test suite, TypeScript/build, 44 contract tests,
203 security/governance tests, direct governance/security checks, and the guarded
physical Mongo 8-suite/29-test matrix all passed again. The exact task-owned Mongo
container auto-removed and Docker Desktop was stopped after the run.

The first re-quality gate reviewed fingerprint
`fe45c03b11efd6c71bd3458266b0f93311aef1d44de85d5f9a820073e2892d5d`
and returned `FAIL`. It independently closed the CSV and canonical-ADR findings, then
reproduced three remaining current-slice defects. The second remediation cycle added
RED/GREEN coverage and corrected them:

- two usable unequal identifiers now produce assessed disagreement before any missing-
  country early return, so descriptive similarity cannot auto-select either one-sided
  missing-country case;
- entity outcome/evidence semantics and the complete persisted intelligence projection
  are validated against the immutable case policy; catalogue, weights, thresholds,
  model versions, readiness flag, and a closed risk-limitation vocabulary fail closed at
  schema-v5 decode and service read/reuse boundaries;
- the canonical policy and activity profiles now state the 21-rule/13-intelligence-rule
  catalogue, schema-v5 reads, and bounded authorized CSV behavior. The governance
  checker and its adverse unit test enforce those clauses.

Raw/BSON tests cover the policy-binding corruptions, and the physical Mongo suite now
includes a restart/initialize rejection case for a deliberately corrupted catalogue
binding. The historical re-quality-gate report remains unchanged.

No GoldTier DNS, TLS, HTTP, Search, or write call was executed. The pre-PR check and
publication checks remain publication-role work after an exact independent `PASS`.

## Historical blockers before the XPI continuation

1. The exact GoldTier XPI PDF/Postman and bounded sandbox access were then supplied;
   their closure is recorded in the continuation addendum below.
2. Obtain sponsor authority for Q-016 before assignment/note/SLA mutations.
3. Submit the remediated exact content to a fresh independent re-quality gate. Without exact `PASS`,
   do not commit, push, create a PR, or run publication CI.
4. Keep Phase 22 on hold regardless of this bounded pre-phase gate result.

## Continuation addendum — GoldTier XPI sandbox closure (2026-09-24)

The previously missing sponsor XPI PDF and Postman collection were supplied and
reconciled without copying transport identity values or raw examples into the
repository. Their SHA-256 hashes and the field-level authority matrix are recorded in
`docs/integration/GOLDTIER_XPI_MAPPING_MATRIX.md`.

Implemented under proposed ADR-004 and D-048:

- explicit `mock | sandbox` GoldTier composition, with Mock still the default and no
  failure fallback;
- strict six-operation XPI DTO family, customer Search/Shell/Policy/Amend mapper and
  connector, and local related-party DTO validation;
- TLS-1.3-only certificate-verifying HTTPS, redirects off, bounded timeout/body,
  backend-only `user_id`, fixed safe errors, and separate mutation opt-in;
- eight editable authority-labelled target-policy values frozen into each new case;
- bounded case-scoped request preview through the existing CLM plan and authenticated
  cache owner;
- exact identifier/country match reuse through the existing advisory resolver;
  multiple, probable, conflicting, or otherwise non-exact candidates stop at human
  review with zero mutation;
- one existing target ledger for both new-party and exact-existing-party operation
  prefixes, including non-replayable `IN_PROGRESS` treatment for uncertain mutations;
- additive schema-v5 backward reads for records without provider/target-policy fields.

Four bounded synthetic read-only searches returned HTTP 200 empty arrays. No customer
write was executed because all eight authoritative target-policy defaults remain
`TBD_SPONSOR`; copying collection examples would invent business authority. No related-
party write was executed because `childId` lifecycle and relationship-value authority
remain unproved. Classification is `SANDBOX_PARTIAL`, never Live.

Fresh continuation verification at the unstaged working candidate:

- backend: `1219 passed, 29 skipped`;
- Ruff: pass; strict Mypy: pass over 105 source files;
- frontend: `22 files / 278 tests` pass; type-check and production build pass (114
  modules);
- contract unittests: `44 passed`; delivery-asset unittests: `4 passed`;
- focused XPI suite: `29 passed` after composition/preview additions;
- physical Mongo: not freshly runnable because the local Docker daemon is unavailable;
  earlier candidate evidence is retained as historical evidence only.

The sandbox adapter changes connector/configuration, target DTO/API projection,
immutable policy snapshot, additive schema-v5 fields, and request-preview UI. It does
not add a production/Live provider, PingFed, approval, Q-016 mutation, new persistence
owner, new cache owner, direct ACRA-to-XPI mapping, or second resolution/ledger owner.

The next authorized action is to freeze an exact candidate fingerprint, obtain one
fresh independent `PASS` against that exact content, then perform publication checks
and create a human-review PR. Phase 22 remains on hold and repository-owner humans
retain merge authority.

## Final local verification before exact XPI re-quality gate

The repository governance model was synchronized with the implemented boundary:
`GOLDTIER_XPI` is now machine-recorded as `PARTIAL / SANDBOX_PARTIAL`, the only
selectable target modes are exactly `mock | sandbox`, Mock remains the default, and
adverse checks reject both a `live` mode and a sandbox default. `GOLDTIER_REAL` and
`PINGFED_AUTH` remain `NOT_IMPLEMENTED / BLOCKED`. The provider evidence vocabulary
accepts the XPI identity without treating the current read-only observations as full
`SANDBOX_VERIFIED` evidence.

Final local commands against the candidate all passed:

- backend pytest: `1219 passed, 29 skipped, 4 expected malformed-fixture warnings`;
- Ruff across backend/scripts/tests and strict Mypy over 105 source files;
- frontend Vitest: `22 files / 278 tests`, TypeScript, dependency inspection, and
  production build: `114 modules`;
- contract suite: `44 tests`; scoped governance/security/tooling suite: `239 tests`;
- Windows lifecycle: `23 tests`; configured isolated Playwright: `14/14`;
- policy-authority, external-provider-readiness, architecture, project-state, and
  tooling checks;
- synthetic intelligence: entity `17/17`, UBO `3/3`, risk `5/5`;
- GoldTier examples: `VALID=19`, `INVALID_QUARANTINED=19`, `NOT_VALIDATED=48`;
- Python dependency check.

Two earlier complete Playwright attempts failed at different transient points: one
Case Activity focus predicate and one case-portfolio response wait. Each exact point
then passed five consecutive reruns on the same allocated ports, and the unchanged
complete suite passed all 14 tests. No speculative source workaround was added; the
divergent failures remain recorded as bounded platform/browser timing history rather
than being misreported as application defects or omitted.

Docker client availability was reconfirmed, but the Docker Desktop Linux daemon pipe
was absent. No fresh physical Mongo execution was possible; the earlier same-candidate
lineage result remains historical supporting evidence only. No external mutation was
executed during final verification.

## Exact XPI gate failure and bounded remediation

The first exact XPI re-quality gate reviewed 122 candidate paths at fingerprint
`afdb940366dbf54079a7c34c1afe8504ff799d93ae766b8cb8d79fa0d97feb6d` and returned
`FAIL`. Its report is preserved verbatim as
`PRE_PHASE22_CAPABILITY_EXPANSION_GOLDTIER_REQUALITY_GATE_FAILED.md`; it was not edited
into a pass. Q-016 deferral and the Phase 22 hold were explicitly accepted as correct
non-blockers.

The four concrete findings were reproduced with focused RED tests and remediated within
the existing owners:

- target-policy strings now reject blank/control-bearing input, corrupted prepared
  values make the preview non-dispatchable, execution compares both target-policy
  content and catalogue version to the owning case snapshot, and every customer request
  DTO is constructed locally before ledger/network start;
- oversized, undecodable, or ambiguous mutation responses are projected to the existing
  mutation-uncertain boundary, retain the ledger `IN_PROGRESS`, and cannot replay;
- the execution profile now exposes GoldTier `MOCK` or `SANDBOX` plus `MOCK` or
  `SANDBOX_PARTIAL`, and visible journey/result labels derive from backend profile/plan
  state or use provider-neutral GoldTier wording;
- related-party `ownerPercent` retains the six-decimal contract shape and now also
  enforces a finite semantic range of 0 through 100 inclusive.

Focused remediation evidence is green: the XPI suite passes 54 tests; the affected
frontend set passes 102 tests; TypeScript and focused Ruff pass. The complete required
backend/frontend/static/contract/governance/lifecycle/browser matrix must be rerun after
the final documentation update, followed by a new fingerprint and a fresh independent
gate. No provider or database mutation occurred during this remediation.

## Final post-remediation verification before fresh exact gate

The complete matrix was rerun against the remediated working candidate. Backend pytest
collected 1,273 tests and completed with `1,244 passed / 29 environment-skipped`; the
only warnings were the known Starlette deprecation plus three intentionally malformed
provider-fixture serialization warnings. Full Ruff and strict Mypy remain green over
105 backend source files.

Frontend Vitest passes `22 files / 280 tests`; TypeScript, the dependency-tree
inspection, and the production build pass with 114 modules. The contract suite passes
44 tests, the scoped governance/security/tooling suite passes 239 tests, and the Windows
lifecycle suite passes 23 tests. Direct project-state, architecture, policy-authority,
external-provider-readiness, tooling, secret, dependency, and whitespace checks pass.
Synthetic intelligence remains entity `17/17`, UBO `3/3`, and risk `5/5`; the GoldTier
example classification remains `VALID=19`, `INVALID_QUARANTINED=19`, and
`NOT_VALIDATED=48`.

The first complete browser attempt after remediation stopped at selection 2/14 because
the E2E assertion still expected the retired hard-coded `Completed Mock workflow` copy.
Inspection confirmed the application now intentionally renders provider-neutral POC
completion wording while the backend-profile surfaces separately render `GoldTier Mock`
or `GoldTier Sandbox (SANDBOX_PARTIAL)`. The stale assertion and remaining generic
completed-client Mock labels were corrected without changing workflow behavior. The
exact failed selection then passed in a fresh lifecycle and the unchanged full isolated
suite passed `14/14`. Focused frontend coverage passes 108 tests and the full 280-test
suite, typecheck, build, and dependency checks were rerun after the copy correction.

Docker client availability was reconfirmed, but the Docker Desktop Linux daemon pipe is
absent. Fresh physical Mongo evidence is therefore unavailable and prior evidence is not
relabeled as current. No provider, customer, related-party, or database mutation was
executed. The next authorized action is an exact candidate fingerprint and one fresh
independent re-quality gate; publication remains blocked until that gate returns exact
`PASS`.

## Third narrow remediation — GoldTier provider-message truthfulness

The final GoldTier re-quality gate found one remaining High issue: a Sandbox execution
could carry authoritative `SANDBOX / SANDBOX_PARTIAL` fields while retained workflow
narratives and frontend outcome rendering still claimed `Mock GoldTier`. The proved root
cause was split across existing owners: Mock-era hard-coded human messages in
`OnboardingService`, `ClmOrchestrationService`, and `ZeroTouchOrchestrator`, plus UI
consumers that rendered the legacy `MOCK_GOLDTIER_SUBMITTED` business-status identifier
as provider truth. The durable status/event identifiers remain compatibility values;
they were not renamed and no second provider owner was added.

Retained target narratives are now provider-neutral. When provider mode is intentionally
shown, frontend labels derive from the existing immutable CLM submission-plan
`environment`; Mock renders `Mock GoldTier`, while Sandbox renders `GoldTier Sandbox`.
List projections that do not carry environment use `GoldTier target` rather than guess a
mode. Sandbox success, review, controlled failure, malformed-response, uncertain/no-
replay, activity, CSV, API, and frontend paths therefore cannot claim Mock. Historical
Mock records and schema-v1-through-v5 compatibility are unchanged; a schema-v5 codec
round trip proves the existing Sandbox environment and neutral narratives survive
reconstruction without a migration or schema-v6 change.

Test-first evidence reproduced the prior defect before the repair: new Sandbox success,
review/failure, malformed-target, persistence-codec, frontend journey, and sponsor-summary
assertions failed on the Mock claim, and the no-replay assertion failed on its Mock-era
message. After the repair, the focused backend target/orchestration/API/persistence set
passes `151 tests`, and the focused frontend target/case/activity set passes `112 tests`.
The CSV projection assertion exercises the existing formula-injection-safe exporter; the
existing Mock frontend assertion continues to require `Mock GoldTier submitted`.

Fresh broad verification against the final remediation content:

- backend pytest: `1,297 passed / 29 infrastructure-skipped`, with only three expected
  malformed-fixture serializer warnings;
- Ruff: pass; strict Mypy: pass over 105 source files; Python dependency check: pass;
- frontend Vitest: `22 files / 282 tests`; TypeScript, dependency inspection, 14-test
  Playwright discovery, and production build: pass (`114 modules`);
- contract tests: `44 passed`; delivery-asset tests: `4 passed`;
- context/project-state/architecture governance: `51 passed`; policy-authority:
  `14 passed`; provider-readiness: `14 passed`; sanitized provider-evidence validation:
  `17 passed`; secret-scanner unit tests: `8 passed`;
- direct project-state, architecture, tooling, policy-authority,
  external-provider-readiness, and secret checks: pass;
- Windows lifecycle: `23 passed`;
- isolated configured Playwright: final serialized run `14/14 passed`; two earlier
  unrelated timing failures each passed a fresh diagnostic rerun before that final run;
- GoldTier example classification remains `VALID=19`, `INVALID_QUARANTINED=19`, and
  `NOT_VALIDATED=48`; whitespace check reports no defect beyond informational Windows
  LF-to-CRLF warnings.

The Docker client remains installed but its local daemon is unavailable, so fresh
physical Mongo evidence is `MISSING_INFRASTRUCTURE`; prior implementer evidence remains
historical only. This cycle changed no persistence schema/repository behavior and made no
external provider or database mutation. Target ordering, ledger/no-replay, Sandbox
authentication, authorization, cache ownership, Q-016 deferral, and the Phase 22 hold are
unchanged. The previous gate FAIL remains preserved as historical evidence.

## Authorized remediation — immutable GoldTier provider identity

The preserved final re-quality gate reported `GT-FINAL-RQG-01`: a CLM plan could retain
one provider identity while submission input was later rebuilt from mutable mapper
configuration. The owner-authorized remediation treats this as one architecture-root
defect, not a presentation or routing exception. The existing retained
`GoldTierSubmissionPlan` now owns one immutable environment/classification pair for the
logical submission. Its mode is copied into the immutable execution input; current
mapper and connector modes are used only as compatibility assertions.

Strict test-first evidence reproduced both directions before implementation: a retained
Sandbox plan could execute after Mock drift, and a retained Mock plan surfaced only a
generic failure after Sandbox drift. Schema-v5 also accepted contradictory provider
bindings. The bounded repair now:

- rejects mapper or connector drift with typed internal code
  `GT_PROVIDER_CONTEXT_MISMATCH`, projected at CLM as the sanitized
  `CLM_TARGET_PROVIDER_CONTEXT_MISMATCH`;
- performs that check before target-ledger access or any outbound provider call;
- derives request preview and execution input from the retained plan for an existing
  CLM record, while configuration remains only the default when creating a new plan;
- validates schema-v5 plan environment/classification consistency and rejects plan,
  submission-input, or matching-ledger provider contradictions;
- retains plan-only cases, historical schema-v1-through-v4 reads, legacy durable status
  identifiers and schema version 5; no provider registry/router, fallback or schema v6
  was added.

Focused GREEN evidence covers both drift directions independently (connector-only
Sandbox-to-Mock and mapper-only Mock-to-Sandbox), stable Mock/Sandbox behavior,
matching provider-bound schema-v5 reconstruction, plan-only reconstruction, and each
contradictory persistence shape. The prior gate FAIL report remains unmodified. Broad
verification, exact candidate fingerprint, fresh independent gate and publication
evidence are recorded only after they are executed. Q-016 remains deferred, Phase 22
remains on hold, and no external provider, customer, related-party or database write was
performed.

### Verification after provider-identity remediation

Focused provider-identity and persistence tests pass in both directions and shapes. The
final unchanged backend run passes `1,308 passed / 29 infrastructure-skipped`; the only
warnings are the three established malformed-fixture serializer warnings. An earlier
complete run had one loopback demo-seeder HTTP timeout (`1,307 passed`) at a changing
request position; the exact test subsequently both failed and passed in isolation, and
the unchanged complete rerun passed. Full Ruff, strict Mypy over 105 source files, and
Python dependency validation pass.

Frontend TypeScript, dependency inspection, 14-test Playwright discovery, Vitest
(`22 files / 282 tests`) and production build (`114 modules`) pass. Contract tests pass
`44/44`, delivery-asset tests pass `4/4`, the selected governance/security suite passes
`163/163`, and direct project-state, architecture, tooling, policy-authority,
external-provider-readiness and secret checks pass. Windows lifecycle passes `23/23`
and removes its owned processes. Synthetic evaluation remains entity `17/17`, UBO
`3/3`, mock risk `5/5`; GoldTier examples remain `VALID=19`,
`INVALID_QUARANTINED=19`, `NOT_VALIDATED=48`.

The Docker 29.8.0 client is present but the Docker Desktop Linux daemon pipe is absent,
so fresh physical Mongo evidence is `MISSING_INFRASTRUCTURE`; prior results are not
relabeled. The isolated browser suite repeatedly passes selections 1 through 6 but its
pre-existing Case Activity selection times out at varying response/visibility waits.
Two focused reruns, including one diagnostics-enabled run, reached different points in
the same unchanged test and also failed. No provider-identity, GoldTier, persistence,
or application source was changed to mask that out-of-scope instability, and the
browser result is recorded as unresolved rather than passed.

### Implementer self-review

The final remediation diff was re-read against `GT-FINAL-RQG-01`, both adverse drift
directions, schema-v5 reconstruction and the owner/retirement constraints. The
recurrence root is closed at the existing plan: no CLM execution-input path reads the
current mapper mode once the plan exists; both mapper and connector identity are checked
before ledger access; and persistence rejects each contradictory current-schema shape.
The old mutable capture is retired rather than retained as a fallback.

No direct ACRA-to-GoldTier mapping, second ledger, provider registry/router, parallel
persistence model, frontend authority, schema v6, dual write, Mock/Sandbox fallback,
new sponsor rule, Q-016 behavior or Phase 22 behavior was introduced. Legacy status
identifiers, Mock-default composition, plan-only cases and older-schema reads remain.
No private/provider detail is included in the mismatch error. The localized browser
failure above is unrelated to these owners and remains visible for independent review;
the implementer does not convert it into a self-issued quality-gate pass.

## Acceptance evidence closure — physical provider identity and Case Activity browser

This bounded closure addresses only the two evidence gaps named by the owner. It does
not redesign GoldTier, activate a provider, answer Q-016, authorize Phase 22, or change
the immutable provider-identity owner described above.

### Physical Mongo provider-identity evidence

Docker Desktop 29.8.0 was started locally and a task-owned disposable Mongo 7.0
container, `clm-provider-identity-mongo-20260924`, was bound to a random loopback port.
The Mongo URI was derived only inside the invoking process, was removed from the child
environment after each command, and was never printed or persisted. The unrelated
pre-existing `safetrace` container was neither inspected nor modified.

The new guarded suite `test_provider_identity_real_mongo.py` creates a fresh allowlisted
`p12` database per test, proves that only `clm_case_snapshots` exists, and proves exact
database removal during teardown. Its six physical cases cover:

- stable Mock and stable Sandbox schema-v5 reconstruction across repository restart;
- both plan/submission-input provider-identity contradiction directions;
- a matching-ledger provider contradiction;
- valid Sandbox plan-only reconstruction with no submission or ledger entry.

The stable fixtures intentionally use a `NOT_STARTED` target ledger. An initial
`IN_PROGRESS` fixture was correctly recovered as an orphan by the production owner and
was therefore repaired as a test-fixture mistake, not treated as a production defect.
Final evidence is `6/6` for the new suite and
`PHYSICAL_MONGO_RESULT=PASSED; SUITES=9; COLLECTED=35; PASSED=35; FAILED=0;
ERRORS=0; SKIPPED=0` for the complete registered physical runner. Every owned database
was absent after its test. The task-owned container is retained only for the fresh
independent gate and must be stopped by the coordinator immediately after that gate.

### Case Activity browser diagnosis and correction

The unchanged pre-correction candidate was not stable: a ten-run fresh-process,
fresh-port matrix passed `8/10`; one failure stalled before the initial activity
response and one stalled waiting for the document filter. Subsequent request-ID probes
reproduced the failure at different filter requests. The deepest correlated failure
proved all of the following for one request: Chromium dispatched it, Vite accepted it,
the backend received it, completed the query, projected status 200, made the response
start and body chunk ready, and completed the body iterator; Vite received the upstream
200 headers but received no body bytes and no response end. This excludes listener
timing, authentication readiness, React Query dispatch/cancellation, activity query,
projection, and response construction as the cause.

The installed Vite `http-proxy-3` path creates a new upstream connection with
`Connection: close` when no agent is configured. Rapid activity-filter reads
intermittently lost the completed body on that Windows loopback lifecycle. The smallest
correction adds one keep-alive `HttpAgent` only when `CLM_E2E_FRONTEND_PORT` identifies
the guarded E2E process. Ordinary development and production paths retain their prior
configuration; application API, cache, authorization, activity, persistence, timeout,
and provider behavior are unchanged. No retry, sleep, timeout increase, assertion
weakening, or false-success path was added.

The strict counterfactual passed `5/5` fresh diagnostic lifecycles with complete proxy
body milestones. Temporary activity tracing was then removed. The clean final content
passed `10/10` isolated Case Activity runs with a fresh backend, frontend, browser worker
and port pair each time, followed by the exact configured suite at `14/14` isolated
lifecycles. Case Activity was selection 7 and passed in 4.2 seconds.

### Final unchanged-content verification

- backend: `1,343` collected, `1,308 passed / 35 expected physical-only skips`; the
  permitted final run is green with the three established malformed-fixture serializer
  warnings. A restricted run and a restricted isolated diagnostic reproduced the known
  live-loopback demo-seeder timeout; the unchanged exact test passed `3/3` with permitted
  loopback execution before the complete permitted backend pass;
- focused provider/persistence/provider-conformance/activity backend selection:
  `320/320`; physical-runner plus E2E-runner units: `48/48` after their owned temporary
  fixture directory was permitted; Ruff passes; strict Mypy passes over 105 files;
  dependency validation reports no broken requirements;
- frontend: focused Case Activity `8/8`, Vite fallback `1/1`, full Vitest
  `22 files / 282 tests`, TypeScript pass, production build pass at 114 modules,
  dependency inspection pass with only platform/feature optional packages absent, and
  Playwright discovery reports 14 tests;
- contracts `44/44`, delivery assets `4/4`, scoped governance/security `120/120`,
  pre-PR/CI helper tests `67/67`, and direct project-state, architecture, tooling,
  policy-authority, provider-readiness and secret checks pass;
- Windows lifecycle `23/23`, with owned process trees removed; synthetic evaluation is
  entity `17/17`, UBO `3/3`, mock risk `5/5`; GoldTier examples remain
  `VALID=19`, `INVALID_QUARANTINED=19`, `NOT_VALIDATED=48`.

No external provider call, customer/related-party write, shared database mutation,
provider-status expansion, schema version change, cache-owner change, business rule, or
sponsor decision was introduced. Q-016 remains deferred and Phase 22 remains on hold.
The next authorized action is to freeze this exact content and obtain one fresh
independent re-quality-gate verdict. Only exact `PASS` authorizes publication steps.
