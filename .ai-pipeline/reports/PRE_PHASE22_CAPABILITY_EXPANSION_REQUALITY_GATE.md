# Pre-Phase 22 Capability Expansion Re-Quality-Gate Report

Date: 2026-09-24

## 1. Executive Result

**Verdict: FAIL**

Publication is **not authorized** and Phase 22 remains on hold.

The remediated candidate closes the first gate's CSV-formula finding and supplies the
required accepted project ADR. It also improves Unicode identifier handling, rejects a
country conflict when both countries are present, excludes generic legal form from
independent corroboration, and adds useful nested model validation. Those corrections
are real but insufficient:

1. a different usable registration identifier can still be automatically selected as
   `PROBABLE_MATCH` when either country is missing;
2. schema-v5 model and Mongo encode/decode boundaries still accept contradictory entity
   outcomes and intelligence records that are not bound to the case's immutable policy;
3. current canonical contracts still describe eight policy rules, only two runtime
   rules, schema-v1-v4 activity reads, and no CSV export, while this candidate implements
   a 21-rule catalogue, 13 intelligence rules, schema v5, and CSV export.

The first two are current high-severity false-success/fail-closed defects. The third is
an important governance/contract synchronization defect. Separately, the named GoldTier
XPI PDF/Postman artefacts and approved configuration are absent, and Q-016 does not
authorize assignment, note, or SLA mutations. Omitting guesses was correct and is not a
code defect; however, the original assignment requested one combined outcome and permits
publication only after exact independent `PASS`. Those dependent lanes therefore remain
combined-acceptance blockers even after the current code defects are fixed.

This review is independent of both the implementation and first gate. The immutable
first-gate report was read but not edited.

## 2. Findings First

### P22-RQG-001 — High — Distinct usable identifiers can still auto-match when country is absent

**Status:** current defect; first-gate finding P22-QG-001 remains open.

`apps/backend/app/services/onboarding_intelligence.py:290-295` returns
`NOT_ASSESSED` as soon as either country is absent, before it compares two present,
usable registration identifiers. The automatic-selection guard at lines 145-152 blocks
only an identifier feature assessed as disagreement. Consequently, a different
identifier plus a missing country bypasses the disagreement guard and descriptive
features can select it automatically.

The independent probe used:

- source identifier `202400001A`, country `SG`;
- candidate identifier `209999999Z`, country absent;
- identical legal name and registered address.

Observed result:

```text
outcome=PROBABLE_MATCH
selected_candidate_id=candidate
probability=1.000000
identifier_assessment=NOT_ASSESSED
corroborating_feature_count=2
```

This contradicts `docs/models/ENTITY_RESOLUTION_MODEL_CARD.md:19-20` and D-047 in
`docs/decisions/DECISION_LOG.md:58`, both of which state that distinct usable identifiers
cannot auto-match. It also triggers the assignment's explicit stop condition for
unacceptably bounded false positives. The 15-case synthetic evaluation does not falsify
this path: its `same_name_different_identifier_no_match` candidate inherits country
`SG` from the helper (`apps/backend/app/services/intelligence_evaluation.py:16-20,
224-227`).

**Impact:** a duplicate-search candidate representing a different legal entity may be
selected automatically. The workflow stops only `REVIEW_REQUIRED` and `CONFLICT` entity
outcomes (`apps/backend/app/services/zero_touch_orchestration.py:1212-1220`), so this
false probable match is not converted into a human-review stop.

**Required correction:** make any two present, usable, unequal identifiers prevent
automatic selection regardless of missing country; keep missing/lossy evidence
explicitly unassessed; add both source-country-missing and candidate-country-missing
adverse cases with strong descriptive similarity to unit and versioned synthetic
evaluation coverage.

### P22-RQG-002 — High — Schema-v5 semantic integrity is still fail-open

**Status:** current defect; first-gate finding P22-QG-002 remains open.

The new validators check useful local arithmetic and selected-candidate shape, but they
do not bind the complete persisted meaning:

- `EntityResolutionResult.outcome_matches_candidate_evidence` at
  `apps/backend/app/domain/onboarding_intelligence.py:170-208` validates selected
  outcomes but does not reject `NO_MATCH` with exact identifier evidence, or otherwise
  derive non-selected outcomes from the full candidate set.
- `OnboardingIntelligenceRecord.policy_catalogue_version` at line 359 is merely a
  non-negative integer. `DurableCaseSnapshot._validate_case_bindings` at
  `apps/backend/app/persistence/models.py:291-316` binds only the intelligence `case_id`;
  it does not require an intelligence policy snapshot, equal catalogue versions, or
  equality between policy-bound weights/thresholds/flags and persisted projection
  fields.
- `MockRiskAssessment.not_assessed_signals` at
  `apps/backend/app/domain/onboarding_intelligence.py:292` is an unbounded
  `frozenset[str]`; its validator requires known missing signals to be listed but permits
  arbitrary extra strings. The API returns the domain record and the frontend renders
  those strings.

Independent probes demonstrated all three gaps:

```text
contradictory-entity-outcome:
  accepted=true, outcome=NO_MATCH, exact_identifier_agreement=1

case-policy-binding:
  accepted=true, case_catalogue_version=0,
  case_has_intelligence_policy=false, record_catalogue_version=99

unknown-risk-limitation:
  accepted=true, not_assessed_signals=[ownership, unexpected_external_signal]
```

A combined schema-v5 document with exact identifier agreement, outcome `NO_MATCH`, no
case intelligence policy, and record catalogue version `999` also survived
`MongoCaseStore._encode` followed by `_decode` unchanged:

```text
accepted=true, decoded_outcome=NO_MATCH, identifier_agreement=1,
case_catalogue_version=0, record_catalogue_version=999
```

This is not limited to display. The evaluator returns an existing record unchanged when
its stored input fingerprint equals the freshly computed fingerprint
(`apps/backend/app/services/onboarding_intelligence.py:641-643`); a semantically corrupted
record can therefore reach workflow decisions. A corrupted `NO_MATCH` can suppress the
review stop, while a corrupted risk threshold or `blocks_readiness` flag can change
workflow behavior without matching the immutable case policy.

**Required correction:** enforce the whole persisted semantic relation at the canonical
model/persistence boundary: entity outcome and selection versus all evidence; unique
exact/conflict/ambiguity semantics; record catalogue version and intelligence-policy
presence versus the case snapshot; persisted entity weights, UBO/risk thresholds, and
risk readiness flag versus that snapshot; and a closed, bounded risk-limitation
vocabulary. Add direct raw schema-v5 corruption tests through memory, BSON/Mongo decode,
restart/recovery, and the physical Mongo suite.

### P22-RQG-003 — Important — Canonical policy and activity contracts contradict the candidate

**Status:** new current-slice governance defect, not an external dependency.

The plan makes both profiles baseline authorities and Task 8 requires contracts to be
updated. They were not synchronized:

- `docs/contracts/POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md:69` still states that the
  catalogue has eight seed rules, and line 107 says only IDP confidence and UBO
  percentage affect runtime. The candidate migrates to 21 rules
  (`apps/backend/tests/test_phase14_5_policy.py:184,321`), including the 13 intelligence
  identifiers declared at `apps/backend/app/domain/policy.py:19-31`.
- `docs/contracts/CASE_ACTIVITY_QUERY_PROFILE.md:61` still limits supported case
  envelopes to v1-v4 and line 76 states `Export remains unavailable.` The candidate's
  canonical envelope is schema v5, and it exposes
  `GET /api/clm/zero-touch/activity.csv` at `apps/backend/app/main.py:1513-1523` with a
  live frontend export.

The direct architecture/project-state/policy checks pass because they do not reconcile
these clauses. Passing those tools therefore cannot be treated as proof that all
baseline owners are synchronized.

**Required correction:** update the current contracts to the reviewed 21-rule/13-rule,
schema-v5, bounded-authorized-CSV behavior, or explicitly supersede the stale clauses
through the repository's canonical contract mechanism. Extend governance tests so these
specific owner/runtime contradictions fail automatically.

### No additional current defect found in the following reviewed areas

- Unicode alphanumerics are retained with NFKC/case-fold normalization, empty/lossy
  identifiers are unassessed, an explicit country conflict fails closed when both
  countries are present, and generic legal form is excluded from corroboration.
- UBO advice consumes the existing Decimal ownership result and does not replace the
  legal/provisional ownership owner.
- Mock risk remains labelled `MOCK_ADVISORY_RISK / NOT_COMPLIANCE_DECISION` and does
  not block readiness by default.
- The case-scoped intelligence API reuses backend case access and safe 404 behavior.
- Frontend intelligence keys include user and case identity, propagate cancellation,
  and are cancelled/removed on relevant session and deletion paths.
- The target ledger/order/no-replay owner is not bypassed, and no XPI/live connector or
  fallback was added.

These observations do not offset the findings above.

## 3. First-Gate Remediation Checklist

| First-gate finding | Re-quality result | Independent evidence |
|---|---|---|
| P22-QG-001 entity false matches | **NOT CLOSED** | Unicode and weak-legal-form examples are fixed, but a distinct usable identifier with missing country reproduces `PROBABLE_MATCH` at `1.000000`. |
| P22-QG-002 contradictory schema-v5 models | **NOT CLOSED** | Local arithmetic validation improved, but exact evidence with `NO_MATCH` and policy-unbound intelligence both survive model and Mongo encode/decode boundaries. |
| P22-QG-003 CSV control-prefix injection | **CLOSED** | `_formula_significant_text` skips every leading Unicode whitespace or Unicode category `C` character before testing `=+-@`; NUL, VT, FF, NBSP, and em-space probes and tests pass. |
| P22-QG-004 missing canonical ADR | **CLOSED** | `docs/decisions/ADR-003_ONBOARDING_INTELLIGENCE.md` exists with `Accepted` status and every project-template section; D-047 links it; the earlier Aegis ADR is marked `superseded-by-project-adr`. |

Closing P22-QG-004 does not close the separate canonical-contract drift in
P22-RQG-003.

## 4. Full Acceptance Checklist

| Acceptance area | Result | Evidence / consequence |
|---|---|---|
| Frozen candidate and review identity | **PASS** | Before review and again before report creation: 78 paths, 43 tracked modifications, 35 untracked paths, 0 staged, SHA-256 `fe45c03b11efd6c71bd3458266b0f93311aef1d44de85d5f9a820073e2892d5d`. |
| ADR, decision, sponsor-question, research, and model governance | **PARTIAL** | Canonical ADR/D-047/model cards/research ledger exist and preserve provisional labels; two baseline contracts remain contradictory. |
| GoldTier XPI contract/mapping and sandbox proof | **DEPENDENT BLOCKED** | Named guideline PDF/Postman collection and approved non-secret host/user/write configuration are absent; diagnosis correctly records `NOT_EXECUTED`; no XPI DTO/connector/request was guessed. |
| Entity-resolution false-positive boundary | **FAIL** | P22-RQG-001. |
| UBO advisory authority | **PASS for the separable local slice** | Advice consumes deterministic Decimal ownership and retains `NOT_LEGAL_UBO_DETERMINATION`; no second graph/ownership owner found. |
| Mock-risk labeling and default workflow effect | **PASS for service-generated records; FAIL at persistence boundary** | Service labels/default are correct; P22-RQG-002 permits policy-unbound/corrupt persisted meaning. |
| Policy editing, validation, and immutable case binding | **FAIL** | Catalogue/RBAC/CAS tests pass, but persisted intelligence is not cross-bound to the immutable case policy and the canonical policy profile is stale. |
| Schema-v5 compatibility, CAS, deletion, restart, no resurrection | **PARTIAL / FAIL** | v1-v4 compatibility and repository semantics are covered and broad tests pass; semantic corruption survives schema-v5 encode/decode. |
| Case-scoped API, backend authorization, safe 404 | **PASS for reviewed surface** | Case access remains backend-authoritative; no cross-team intelligence disclosure found. |
| Safe activity event and bounded CSV | **PASS in code; contract update required** | Stable safe columns, bounded query reuse, UTC output, `no-store`, and control/whitespace formula neutralization verified; current contract still says export unavailable. |
| Frontend evidence, cache scoping, cancellation, logout/401 | **PASS for reviewed surface** | User/case-scoped keys, AbortSignal propagation, cancellation/removal, labels, and 276-test frontend suite pass. |
| Assignment, note, and SLA mutations | **DEPENDENT BLOCKED** | Q-016 leaves roles, reassignment, note history, SLA/routing/escalation authority unresolved; controls and mutations were correctly not invented. Combined request remains incomplete. |
| SME straight-through and adverse local scenarios | **PASS for local Mock/Local slice** | Input-driven synthetic scenarios and labels are covered; XPI preview/search/write portions are absent because their contract lane is blocked. |
| Reproducible evaluation | **PARTIAL / FAIL for claimed false-positive bound** | Reported entity 15/15, UBO 3/3, and risk 5/5 reproduce, but the entity set omits the missing-country/different-identifier counterexample. |
| Security/privacy/provider truth | **PARTIAL** | No secret/provider call/raw-document logging/live claim found; identity false match and fail-open persisted semantics remain high risk. |
| Full verification and exact independent gate | **FAIL** | Many suites pass, but tests do not cover the reproduced defects; fresh physical Mongo was unavailable to this reviewer; exact verdict is not `PASS`. |
| Publication and PR/CI | **NOT AUTHORIZED** | Publication is gated on exact independent `PASS`; no commit, push, PR, CI mutation, merge, or Phase 22 action may occur. |

## 5. Contract and Integration Findings

### Current contract truth preserved

- ACRA remains Mock by default; no Live ACRA claim is introduced.
- GoldTier remains Mock only. The EDS-shaped Mock connector is not renamed or presented
  as NutMeg XPI.
- PingFed/live target integration remains inactive.
- The deterministic Decimal engine remains the sole ownership/UBO calculation owner.
- Mongo remains optional and explicit; memory remains the default; no silent fallback
  was found.
- Target calls remain behind the existing execution ledger and no-replay ordering.
- Advisory outputs remain non-legal/non-compliance and do not grant final approval.

### Dependent blockers, not code defects

1. **GoldTier XPI:** the named guideline PDF and Postman collection are absent from the
   available attachment/repository evidence. Exact schemas, enums, required fields,
   authentication, host, response behavior, related-party child-ID semantics, and TLS
   evidence are therefore unproved. The correct next action is to supply those exact
   artefacts and approved non-secret configuration, reconcile them under the recorded
   source hierarchy, and begin with an authorized read-only search diagnostic. No write
   is authorized by this report.
2. **Assignment/note/SLA:** Q-016 remains open on roles, reassignment, history, sharing,
   priority meaning, SLA, routing, escalation, notification, and due-date behavior. The
   correct next action is an explicit sponsor decision and contract/ADR reconciliation,
   not speculative implementation.

Because the original request required the combined XPI/intelligence/workbench/SME
outcome and exact `PASS`, these are combined-acceptance blockers. They would cease to
block only through the missing authority/evidence being supplied or an explicit owner
change to the acceptance scope; a reviewer cannot make that scope change.

## 6. Tester and Adversarial Evidence

### Independent commands and results

| Command / probe | Result |
|---|---|
| Ordinal `path<TAB>git-hash-object`, LF/no-final-LF fingerprint over tracked + staged + untracked paths, excluding only this report | **PASS** before review and before report: 78 paths; 43 tracked, 35 untracked, 0 staged; `fe45c03b11efd6c71bd3458266b0f93311aef1d44de85d5f9a820073e2892d5d`. |
| Direct missing-country/different-identifier entity probe | **FAIL candidate behavior** — `PROBABLE_MATCH`, selected candidate, probability `1.000000`, identifier `NOT_ASSESSED`, corroboration 2. |
| Direct contradictory entity/policy/risk Pydantic probes | **FAIL candidate behavior** — all invalid states accepted as detailed in P22-RQG-002. |
| Direct `MongoCaseStore._encode/_decode` contradictory schema-v5 probe | **FAIL candidate behavior** — `NO_MATCH` + exact identifier evidence + policy version `999` survived. |
| `python -B -m pytest ... test_onboarding_intelligence.py test_intelligence_evaluation.py test_activity_export.py test_phase12_persistence.py -q` | **PASS** — 58 collected/passed. The green result confirms the counterexamples are missing from the suite; it does not refute them. |
| `cd apps/backend; python -B -m pytest -p no:cacheprovider -q -o addopts=''` | **PASS** — 1,225 passed, 28 skipped, 3 expected malformed-fixture serializer warnings, 95.00s. |
| `python -B scripts/evaluate_onboarding_intelligence.py` | **PASS as written** — entity 15/15 (TP 5, FP 0, TN 10, FN 0), UBO 3/3, risk 5/5; coverage gap described in P22-RQG-001. |
| Direct CSV probe over `=`, `+`, `-`, `@`, NUL, VT, FF, NBSP, em-space | **PASS** — every dangerous significant prefix received a leading apostrophe; safe text was unchanged. |
| `python -B -m ruff check --no-cache app tests` | **PASS**. |
| `python -B -m mypy --no-incremental app` | **PASS** — 101 source files. |
| `npm.cmd test -- --cache=false` | Initial sandbox run: **NOT VALID**, `spawn EPERM`; approved unrestricted rerun: **PASS**, 21 files / 276 tests. |
| `npm.cmd exec tsc -- --noEmit --pretty false -p tsconfig.app.json` and node config equivalent | **PASS**. |
| `python -B -m unittest discover -s tests/contract -p 'test_*.py'` | **PASS** — 44 tests. |
| Direct architecture, project-state, tooling-config, policy-authority, external-provider-readiness, and secret scripts | **PASS**. The tools do not detect P22-RQG-003's stale clauses. |
| `git diff --check` and explicit strict-UTF8/NUL/conflict/final-LF scan of all 78 paths | **PASS for material hygiene**. The strict trailing-space scan found only deliberate Markdown hard-break spaces in four new Markdown reports/docs and unchanged whitespace-only lines outside the candidate diff; no code whitespace defect, NUL, conflict marker, invalid UTF-8, or missing final LF was found. |

### Unavailable or inherited evidence

- Docker client `29.8.0` was present, but the Docker Desktop Linux engine was not
  running and `mongosh` was unavailable. A fresh independent physical Mongo run was
  therefore **NOT EXECUTED**. The implementer report records exact-candidate physical
  evidence of 8 suites / 28 tests with the disposable container removed; that is
  implementation evidence, not a substituted independent rerun.
- Production build (113 modules), Windows lifecycle (23/23), and Playwright (14/14)
  were not rerun in this re-gate. Their post-remediation implementer evidence remains
  code-relevant, while the independent frontend unit/type checks above passed.
- An optional broad root `unittest` discovery attempt was invalidated by sandbox
  temporary-directory permissions, then stopped. All test-created temporary
  directories were identified by exact path/timestamp and removed; this attempt is not
  counted as candidate evidence. The focused root contract and direct governance checks
  above are valid.
- `pre_pr_check.py` was not run because the candidate has a `FAIL` verdict and remains
  an intentionally uncommitted review tree. It is a publication-role prerequisite, not
  a way to override semantic findings.

Broad green suites do not supersede the deterministic adverse probes. Both reproduced
high findings are false-success paths outside the current test corpus.

## 7. Code and Architecture Review

The candidate mostly follows the intended ownership map: it extracts focused domain,
service, repository, export, API, evaluation, and frontend-panel owners while limiting
composition/orchestrator edits to wiring and canonical workflow integration. No second
ownership engine, policy repository, authorization owner, persistence envelope, target
ledger, or provider fallback was found. Legacy schema reads are explicit rather than a
silent migration, and no dormant BizFile/XPI path is composed.

The material architecture failures are narrower but decisive:

- the combined identifier-country feature loses a known identifier disagreement when
  country is absent, allowing descriptive evidence to override a hard negative;
- nested types validate calculations locally but no canonical aggregate validator owns
  the full case-policy-to-intelligence invariant;
- documentation ownership is split in practice because the implementation and selected
  updated contracts say one thing while two unchanged canonical profiles say another.

No accepted technical debt can absorb those failures because they affect identity
selection, durable workflow meaning, and authoritative project contracts.

## 8. Security Review

### High

- **Identity false-positive / incorrect-party risk:** P22-RQG-001 can automatically
  select a candidate with a different usable registration identifier.
- **Persisted decision-integrity risk:** P22-RQG-002 allows contradictory or
  policy-unbound schema-v5 intelligence to survive decode and influence whether the
  workflow stops for review.

### Important

- The open `not_assessed_signals` string set is not a safe bounded projection: raw
  corrupt strings can reach the case-scoped API and UI. Close the vocabulary and size
  at the domain boundary as part of P22-RQG-002.
- Canonical contract drift in P22-RQG-003 weakens reviewer/operator ability to determine
  the actual runtime policy and export surface.

### Controls verified

- CSV significant-character classification now covers Unicode whitespace and Unicode
  controls before `=+-@` detection.
- Intelligence reads remain authenticated, case-scoped, team-scoped, and safe-404.
- No raw document, raw provider payload, secret, bearer header, credential, or external
  customer response was observed in the new normal logs/events/API projection.
- No provider/network request or target mutation occurred in this review.

## 9. Required Fixes and Dependent Blockers

### Required current-candidate fixes

1. Close P22-RQG-001 and add missing-country/distinct-identifier adverse tests to both
   focused tests and the versioned synthetic evaluation.
2. Close P22-RQG-002 with aggregate semantic/case-policy binding and raw-corruption
   tests across memory, BSON/Mongo decode, restart, and physical Mongo.
3. Close P22-RQG-003 by reconciling the current policy/activity contracts and extending
   governance checks to prevent recurrence.
4. Rerun focused and broad affected verification after the final source/doc change,
   freeze a new fingerprint, preserve this failed report, and request another fresh
   independent re-quality gate.

### Dependent blockers — do not implement around them

- Supply and reconcile the exact named GoldTier XPI guideline PDF and Postman
  collection, plus approved non-secret sandbox configuration and explicit write
  authority before any XPI connector/DTO/write work.
- Obtain a sponsor answer to Q-016 and update governing contracts/decisions before
  assignment, private-note, SLA, routing, escalation, or notification mutations.

Those blockers are not evidence that the omission itself is defective. They are evidence
that the original combined acceptance is incomplete and cannot receive exact `PASS` yet.

## 10. Readiness and Publication

- **Separable advisory implementation readiness:** not ready; two high current defects
  and one important contract defect remain.
- **GoldTier XPI sandbox readiness:** not ready; contract/configuration evidence is
  absent and no external smoke was executed.
- **Live ACRA / live GoldTier / PingFed readiness:** not proved and not claimed.
- **Assignment/note/SLA readiness:** not authorized under unresolved Q-016.
- **Publication readiness:** **NO**. Do not stage, commit, push, open a PR, or run
  publication CI from this verdict.
- **Phase 22 readiness:** not evaluated or authorized; Phase 22 remains on hold.

## 11. Frozen Identity and Git Status

- Branch: `feature/pre-phase22-capability-expansion`
- Current source revision / HEAD: `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- `origin/main`: `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- Accepted base tree object: `848dcde901a33908bc5a3a6446021da2489d6be1`
- Candidate before this report: 78 reviewed paths, comprising 43 tracked modifications,
  35 untracked paths, and 0 staged paths.
- Candidate fingerprint algorithm: ordinal path order; one
  `path<TAB>git-hash-object` line per reviewed path; UTF-8; LF between lines; no final LF;
  this report excluded.
- Candidate fingerprint before review and immediately before this report:
  `fe45c03b11efd6c71bd3458266b0f93311aef1d44de85d5f9a820073e2892d5d`.
- Post-report recheck excluding only this report: 78 paths, 43 tracked modifications,
  35 candidate-untracked paths, 0 staged, and the same
  `fe45c03b11efd6c71bd3458266b0f93311aef1d44de85d5f9a820073e2892d5d` fingerprint.
  Total untracked paths are now 36 because this report is the sole addition.
- The report itself is the reviewer's only persistent file change. Post-report identity
  must remain the same when this report alone is excluded; any other change invalidates
  this verdict's reviewed scope.

The reviewer made no implementation, test, configuration, plan, contract, ADR,
ordinary-documentation, dependency, Git-history/index, provider, target, PR, CI, or
Phase 22 mutation. No commit, push, PR, merge, provider call, or external write occurred.
