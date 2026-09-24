# Pre-Phase 22 Capability Expansion — Fresh Independent Quality Gate

## 1. Executive Result

**Verdict: FAIL**

The frozen candidate contains useful, well-contained ready-slice work and its configured
regression suites are green. Exact acceptance is nevertheless unavailable. Fresh
adversarial review reproduced an entity-resolution false automatic match, showed that
schema-v5 advisory types accept contradictory states at the persistence trust boundary,
and found control-prefixed CSV formula cells that are exported without neutralization.
The durable advisory owner also lacks the canonical project ADR required by the
development workflow.

GoldTier XPI mapping/request/search/sandbox work and assignment/note/SLA mutations are
separately classified as unavailable dependent lanes: the named PDF/Postman artefacts
and sandbox configuration are absent, and Q-016 remains open. Omitting unsafe guesses
was correct, but the explicit user request includes those capabilities and requires one
exact independent `PASS` for the combined outcome. They therefore also prevent an
overall exact PASS without being reclassified as ready-slice implementation defects.

Publication is not ready. Phase 22 remains on hold.

## 2. Findings First

### P22-QG-001 — High — Entity normalization can manufacture exact identity and weak descriptive evidence can auto-select

- Classification: **Design Defect — scope: requirements and architecture**.
- `apps/backend/app/services/onboarding_intelligence.py:52-58` deletes every character
  outside ASCII `a-z0-9`/`A-Z0-9`. `_identifier_feature` at lines 252-290 compares the
  resulting strings without rejecting an empty normalization.
- Fresh reproduction supplied different valid model inputs `公司甲` and `公司乙` as
  registration numbers in the same country. Both normalize to the empty string and the
  resolver returned `EXACT_MATCH`, selected the candidate, and reported one
  corroborating feature.
- A separate source/candidate pair containing only the same legal name and the generic
  legal form `PRIVATE_COMPANY_LIMITED_BY_SHARES` returned `PROBABLE_MATCH` with
  probability `1.000000`. Missing stronger features shrink the denominator, and the
  generic legal-form equality is counted as a second corroborating feature.
- This violates the user's key false-positive boundary, the strict source DTO rule, and
  the model-card claims at `docs/models/ENTITY_RESOLUTION_MODEL_CARD.md:30-32,49-52`.
  The authored six-scenario evaluation does not cover normalization-to-empty or the
  name-plus-generic-form combination, so its reported zero false-positive rate does not
  bound these cases.
- Required correction: define a loss-aware Unicode/identifier normalization contract;
  reject unusable normalized values before comparison; require independently strong
  identity evidence for automatic selection; add the full required same-name/different
  identifier, same-name/different-country, punctuation/suffix/abbreviation/address,
  normalization-empty, and name-plus-generic-form adverse matrix; then refresh the
  synthetic evaluation and model card.

### P22-QG-002 — High — Persisted advisory models do not enforce their semantic invariants

- Classification: **Implementation Drift — scope: persistence architecture and
  requirements**.
- `apps/backend/app/domain/onboarding_intelligence.py:99-163` constrains field shapes but
  does not bind outcome to selected candidate, selected candidate to the candidate set,
  risk score to risk band, `NOT_ASSESSED` to a null score, or UBO label to probability,
  ownership percentage, and a non-empty bounded party identity.
- Fresh construction accepted all of the following without validation error:
  `NO_MATCH` with selected candidate `ghost` and no candidates; score `100` with band
  `LOW` and no signals; and an empty-party `LIKELY_UBO` result with null probability and
  zero authoritative ownership.
- The memory and Mongo repositories call `OnboardingIntelligenceRecord.model_validate`,
  and the Mongo decoder nests the same models through
  `DurableCaseSnapshot.model_validate`. These contradictory states therefore pass the
  schema-v5 read/write validation boundary rather than failing closed.
- CAS, whole-envelope deletion/no-resurrection, legacy v1-v4 reads, case binding, and
  BSON `frozenset` serialization are implemented and their configured tests pass. Those
  mechanisms do not compensate for missing nested semantic validation.
- Required correction: add fail-closed model invariants and corruption tests at both
  direct model and raw schema-v5 decode boundaries; prove repository parity and rerun
  physical Mongo evidence.

### P22-QG-003 — Important security finding — CSV formula hardening misses allowed control prefixes

- Classification: **Implementation Drift — scope: security and requirements**.
- `apps/backend/app/services/activity_export.py:24-35` handles direct formula markers
  plus space, tab, CR, and LF. It does not neutralize vertical tab, form feed, NUL, or a
  general leading control/whitespace family.
- Fresh probes returned `\x0b=2+2`, `\x0c@SUM(A1)`, and `\x00-1+1` unchanged.
  `AutomationEvent.message` and the retained activity message models accept these
  controls because they enforce only length.
- This fails the explicit requirement for formula protection including leading
  whitespace/control prefixes. Authorization, fixed columns, bounded paging,
  `no-store`, and inaccessible-case 404 behavior otherwise passed inspection/tests.
- Required correction: define one positive safe-cell boundary over all accepted
  leading Unicode whitespace/control characters (or reject those values before
  retention), add table/property-driven CSV tests, and verify representative spreadsheet
  import behavior without broadening the export projection.

### P22-QG-004 — Important governance finding — The new canonical owner has no canonical project ADR

- Classification: **Implementation Drift — scope: architecture/governance**.
- `docs/DEVELOPMENT_WORKFLOW.md` requires a new ADR from
  `docs/decisions/ADR_TEMPLATE.md` for a new canonical service/repository/state owner and
  requires the decision log to link it after acceptance.
- The only ADR-like file is
  `docs/aegis/adr/ADR-0001-onboarding-intelligence-advisory-boundary.md`. It uses the
  non-template status `recorded-from-plan` and explicitly states that it is an advisory
  Aegis record that does not replace project-authoritative architecture sources.
- D-047 names `ADR-0001` but does not link an accepted canonical project ADR. Updating
  `ARCHITECTURE.md` and `PROJECT_STATE.md` is baseline synchronization, not a substitute
  for the missing decision record.
- Required correction: perform the architecture decision review, record the decision in
  the canonical project ADR location/template with a valid lifecycle status, link it
  from D-047, and synchronize the architecture/project baseline only after that decision
  is accepted.

## 3. Frozen Review Identity and Independence

- Reviewer role: fresh independent combined quality gate; no implementation or
  remediation was performed.
- Sole surviving reviewer write:
  `.ai-pipeline/reports/PRE_PHASE22_CAPABILITY_EXPANSION_QUALITY_GATE.md`.
- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`.
- Branch: `feature/pre-phase22-capability-expansion`.
- `BASE_SHA`, `HEAD`, and `origin/main`:
  `3ca232b58c3842f413c4552dbd3b85aabea4591c`.
- Accepted base tree: `848dcde901a33908bc5a3a6446021da2489d6be1`.
- Frozen implementation content: 76 paths, comprising 43 tracked modifications and 33
  task-owned untracked paths; staged paths: 0.
- Fingerprint algorithm: ordinal/case-sensitive sort of the union of unstaged, staged,
  and untracked paths; exclude this report; form one `path<TAB>git hash-object` record
  per path; join with LF and no terminal LF; SHA-256 the UTF-8 bytes.
- Independently recomputed pre-review and pre-report fingerprint:
  `WORKTREE_CONTENT_SHA256=67f209d3ea6a5debbbc2f44d9d7cff273a78ff12198a775a61215c79ff00e163`.
- The post-report recomputation, excluding only this report, matched the same 76-path
  fingerprint; staged paths remained zero.
- Source revision, tested revision, and independently reviewed revision are distinct:
  source Git revision is the unchanged base commit; configured tests and this review
  exercised the exact frozen working-tree content fingerprint above.
- No implementation/instruction scope drift was observed.

Capability preflight found Python 3.12.10, Node 22.23.2, npm 10.9.8, Git 2.55.0,
installed backend/frontend dependencies, and free ports 8000/5173. Docker CLI 29.8.0
was present but its daemon was stopped; `mongosh` was unavailable. The local browser
test dependency was present. No provider, credential, endpoint, or external network
capability was used.

## 4. Acceptance Checklist

| Requirement | Result | Independent evidence |
|---|---|---|
| Preserve authority order, Mock/Local truth, Decimal ownership, and target ledger | **PASS** | Source inspection and full backend regression preserve canonical evidence, Decimal ownership, ordered target execution, no replay, and Mock/Local labels. |
| GoldTier XPI reconciliation, typed mapping/requests, search preview, and optional sandbox diagnostic | **BLOCKED / overall FAIL** | PDF/Postman absent; only `Pasted text.txt` exists in the attachment directory; host/user/write-opt-in variables are absent; no XPI DTO/connector/preview exists and no network call ran. |
| Entity-resolution false-positive boundary and required adverse set | **FAIL** | P22-QG-001 reproduces false `EXACT_MATCH` and weak `PROBABLE_MATCH`. |
| ML-assisted UBO remains advisory over authoritative Decimal results | **PASS with model-integrity blocker** | Service consumes existing Decimal ownership and preserves non-legal labels; P22-QG-002 prevents whole-slice acceptance until persisted semantic invariants are strict. |
| Mock advisory risk remains non-compliance and non-blocking by default | **PASS with model-integrity blocker** | Label/disclaimer/default readiness flag are correct; configured outcomes pass; contradictory persisted risk is accepted under P22-QG-002. |
| Case-bound editable policy and cross-rule validation/migration | **PASS** | Thirteen additive rules, exact legacy migration, immutable case snapshot, sum/threshold cross-rules, and audit event are implemented and pass the full backend suite. |
| Schema v5, legacy v1-v4 reads, CAS, deletion/no-resurrection, BSON safety | **FAIL** | Compatibility, CAS, deletion, and BSON tests pass, but P22-QG-002 disproves strict semantic schema-v5 validation. |
| Case-scoped API, backend authorization, and inaccessible 404 | **PASS** | Route policy is case-scoped; source and auth tests preserve absent/inaccessible equivalence. |
| Canonical workflow evaluates before target and stops on review/high risk | **PASS** | Orchestrator inspection and full regression show existing readiness owner creates typed stops before Mock GoldTier; risk blocking defaults false. |
| Safe activity semantics and bounded authorized CSV | **FAIL** | Event/API scoping passes; P22-QG-003 violates the explicit control-prefix formula requirement. |
| Scoped frontend evidence UI, cache identity, cancellation, and refresh | **PASS** | Query key contains user and case identity; AbortSignal, exact invalidation/removal, logout/401 clearing, and refreshed evidence are covered by source inspection and 276 passing tests. |
| Two integrated SME demo scenarios and synthetic evaluation | **PARTIAL** | Both synthetic demo routes and declared 6/6, 3/3, 5/5 set execute, but the entity evaluation omits and is falsified by P22-QG-001 adverse cases. |
| Useful bounded Exception Workbench including assignment/note/SLA | **BLOCKED / overall FAIL** | Read-only evidence/action integration exists; assignment, unassign, notes, due/SLA and related filters were intentionally omitted because Q-016 lacks authority. |
| Architecture owner, retirement, ADR, and baseline synchronization | **FAIL** | One owner and no fallback/second engine were found; baseline docs changed, but P22-QG-004 leaves the durable decision unaccepted. |
| Security/privacy/secrets and safe projections | **FAIL** | Auth, 404, secret scan, no raw payload, no external calls, and minimal API projection pass; CSV control-prefix exposure remains. |
| Evaluation/industry/provider claims remain honest | **PARTIAL** | Model cards state synthetic limitations and no Live claim; the entity card's weak-case assurance is contradicted by P22-QG-001. |
| Phase 22 hold and no publication before exact PASS | **PASS** | No Phase 22 work, commit, push, PR, or merge occurred; this FAIL keeps the hold in force. |

## 5. Contract and Integration Findings

The candidate correctly preserves the source-of-truth order and does not map ACRA
directly to GoldTier, create a second Decimal ownership engine, bypass the target ledger,
or silently activate BizFile/GoldTier/PingFed/vendor OCR. The new API is additive and
case-scoped. The normal candidate resolver is intentionally absent; only two named
synthetic demo scenarios supply entity candidates. This is truthful for the ready slice,
but it is not evidence of integration with current GoldTier candidates or reviewed
document observations.

The GoldTier examples validator remains consistent with current provisional authority:
`VALID=19`, `INVALID_QUARANTINED=19`, `NOT_VALIDATED=48`. Contradictory examples remain
quarantined. No XPI mapping was inferred from those examples.

### Separate dependent/later lanes

| Lane | Classification | Current evidence and consequence |
|---|---|---|
| GoldTier XPI PDF/Postman reconciliation, DTOs, mapping preview, Customer Search, TLS/sandbox diagnostic | **Missing external artefact/configuration; dependent lane** | The named files are not attached, all three named non-secret environment variables are absent, composition remains Mock-only, and the diagnosis is correctly `NOT_EXECUTED`. It blocks only XPI claims, but because goals A/B and minimum acceptance are part of the explicit combined request, overall exact PASS is unavailable. |
| Assignment, unassign, notes, due/SLA, assignee validation and mutation audit | **Missing sponsor authority; dependent lane** | Q-016 remains open. Omission avoids inventing authorization/policy, but goal F and its explicit acceptance/tests remain incomplete; overall exact PASS is unavailable. |
| Real ACRA/GoldTier/PingFed/vendor OCR/external ownership | **Later provider dependencies** | Remain Partial/Dormant/Not Implemented as documented; this gate grants no activation or Live claim. |

These dependencies neither excuse nor cause P22-QG-001 through P22-QG-004.

## 6. Tester and Adversarial Evidence

Fresh commands against the frozen candidate:

| Command | Result |
|---|---|
| `cd apps/backend; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m pytest` | **PASS** — 1,209 passed, 28 skipped, 3 expected malformed-fixture serializer warnings, 99.93s. |
| `cd apps/backend; python -B -m ruff check --no-cache .` | **PASS**. |
| `cd apps/backend; python -B -m mypy --no-incremental app` | **PASS** — 101 source files. |
| `cd apps/frontend; npm.cmd exec tsc -- --noEmit --incremental false -p tsconfig.app.json` and the same for `tsconfig.node.json` | **PASS**. |
| `cd apps/frontend; npm.cmd exec vitest -- run --cache=false` | Initial restricted invocation: `spawn EPERM`; approved local-child-process rerun **PASS** — 21 files, 276 tests. Existing React SSR/`act` warnings only. |
| `python -B -m unittest discover -s tests/contract -p 'test_*.py'` | **PASS** — 44 tests. |
| Direct `check_project_state`, `check_architecture`, `check_tooling_config`, `check_policy_authority`, `check_external_provider_readiness`, and `check_secrets` scripts | **PASS**. |
| `python -B scripts/evaluate_onboarding_intelligence.py` | Script **PASS** — entity 6/6, UBO 3/3, risk 5/5; P22-QG-001 independently falsifies completeness of the entity adverse set. |
| `python -B scripts/validate_goldtier_examples.py --if-present` | **PASS** — 19 valid, 19 invalid/quarantined, 48 not validated. |
| `git diff --check` plus strict UTF-8/NUL/final-LF/trailing-whitespace/conflict-marker scan over all 76 paths | **PASS**; line-ending conversion warnings only. |

The exact entity probe instantiated two `EntityIdentity` values with distinct
registration numbers `公司甲`/`公司乙` and country `SG`, then called
`OnboardingIntelligenceService.resolve_entity`; observed output was
`unicode_identifiers EXACT_MATCH CANDIDATE 1`. A second call using only equal legal
name and equal generic legal form observed
`name_plus_generic_form PROBABLE_MATCH CANDIDATE 2 1.000000`.

The model-integrity/CSV probe ran from the repository root with
`PYTHONPATH=apps/backend` and constructed the three contradictory advisory values
described in P22-QG-002, then invoked `_safe_cell` with vertical-tab, form-feed, and NUL
prefixes. All models were accepted; the three cells were returned unchanged.

One broader root governance `unittest` attempt was interrupted after the 44 contract
tests had passed because managed Windows ACLs denied temporary-directory access. It is
not counted as candidate evidence. The 43 ignored temporary directories created by that
attempt were identified by exact creation time/path, removed, and left no candidate
content change.

Configured Playwright (reported 14/14 by the implementer), production build (113
modules), Windows lifecycle (23 tests), and the final physical Mongo matrix (28 tests)
were inspected as implementation evidence but not re-run by this reviewer. Docker's
daemon was unavailable for a fresh physical run. The current FAIL is based on direct
source, broad configured regression, and independently reproduced defects; those prior
runs are not used to convert an unavailable exact PASS.

## 7. Code and Architecture Review

The implementation generally fits one bounded owner:

- scoring, evaluation, repository, API/export, and UI presentation are extracted;
- composition/orchestrator/Mongo/App edits are wiring or canonical integration;
- no second authorization, policy, persistence, audit, ownership, or target-ledger
  owner was found;
- no runtime fallback or dual adapter was introduced; and
- legacy snapshot reads are additive rather than a dual durable model.

The existing oversized `main.py`, zero-touch orchestrator, Mongo store, and frontend
`App.tsx` remain acknowledged hotspots. The new focused modules keep most feature logic
out of those files, so this is accepted pre-existing complexity debt rather than a new
finding. P22-QG-004 remains a current architecture-governance defect, not technical debt.

## 8. Security Review

P22-QG-003 is the active security finding. Otherwise the candidate preserves:

- backend-owned session/capability/team checks and non-enumerating 404 behavior;
- user/case-scoped frontend caches and cancellation/removal on identity loss;
- fixed, bounded projections with no document bytes, raw provider payloads, credentials,
  authority digests, or private exception details;
- process-local Mock/Local truth with no Live claim or external provider call;
- no newly detected supported secret pattern; and
- readiness blocking only through the existing authoritative workflow owner.

No `.env`, credential value, raw confidential sponsor payload, protected database, or
unrelated repository was accessed. GoldTier environment inspection was presence-only.

## 9. Required Fixes

1. Replace loss-making entity normalization/automatic-selection logic and expand the
   adverse/evaluation matrix as specified in P22-QG-001.
2. Add semantic validators and raw schema-v5 corruption coverage for entity, UBO, and
   mock-risk projections; rerun persistence parity and physical Mongo evidence.
3. Harden CSV output for the complete accepted leading whitespace/control family and
   add adversarial export/import coverage.
4. Complete a canonical architecture decision review/ADR and link D-047 correctly.
5. Rerun focused and affected broad checks, freeze a new candidate fingerprint, and
   request a genuinely fresh independent re-quality gate.

The GoldTier XPI and Q-016 workbench dependencies are not remediated by guessing. They
remain separate owner/sponsor inputs, but the explicit combined request cannot receive
exact PASS until they are either delivered and implemented safely or the user explicitly
changes the acceptance scope.

## 10. Publication Readiness

- Governance/publication readiness: **No**.
- Exact combined-request acceptance: **No**.
- Phase 22: **On hold; not started and not authorized by this gate**.
- ACRA sandbox/Live readiness: **Not achieved**.
- GoldTier XPI sandbox/real/PingFed readiness: **Not achieved**.
- Commit, push, PR, merge, or release: **Not authorized by this verdict**.

## 11. Git Status and Reviewer Boundary

At report creation, the branch and Git commit remained unchanged at
`3ca232b58c3842f413c4552dbd3b85aabea4591c`, equal to `origin/main`, with 43 tracked
implementation modifications, 33 implementation untracked paths, this one reviewer
report, and zero staged paths. The report is excluded from identity comparison; the
76-path candidate fingerprint remains the frozen value in section 3.

The reviewer made no implementation, test, configuration, plan, contract, ADR,
ordinary-documentation, dependency, Git-index, history, branch, or worktree change.
No implementation fix, commit, push, pull request, merge, provider call, sandbox
mutation, or Phase 22 work occurred.

### Reviewed implementation path manifest (report excluded)

```text
.ai-pipeline/reports/GOLDTIER_XPI_SANDBOX_DIAGNOSIS.md
.ai-pipeline/reports/ONBOARDING_INTELLIGENCE_SYNTHETIC_EVALUATION.md
.ai-pipeline/reports/PRE_PHASE22_CAPABILITY_EXPANSION_IMPLEMENTATION.md
apps/backend/app/api_intelligence.py
apps/backend/app/composition.py
apps/backend/app/demo/zero_touch_control.py
apps/backend/app/domain/case_management.py
apps/backend/app/domain/onboarding_intelligence.py
apps/backend/app/domain/policy.py
apps/backend/app/domain/zero_touch.py
apps/backend/app/main.py
apps/backend/app/persistence/composition.py
apps/backend/app/persistence/models.py
apps/backend/app/persistence/mongo_case_store.py
apps/backend/app/persistence/repositories.py
apps/backend/app/services/activity_export.py
apps/backend/app/services/authorization.py
apps/backend/app/services/case_deletion.py
apps/backend/app/services/intelligence_evaluation.py
apps/backend/app/services/onboarding_intelligence_repository.py
apps/backend/app/services/onboarding_intelligence.py
apps/backend/app/services/policy_management.py
apps/backend/app/services/zero_touch_orchestration.py
apps/backend/tests/test_activity_export.py
apps/backend/tests/test_intelligence_evaluation.py
apps/backend/tests/test_onboarding_intelligence.py
apps/backend/tests/test_phase12_persistence.py
apps/backend/tests/test_phase12_real_mongo.py
apps/backend/tests/test_phase13_auth_rbac.py
apps/backend/tests/test_phase13_priority.py
apps/backend/tests/test_phase13_real_mongo.py
apps/backend/tests/test_phase14_5_policy.py
apps/backend/tests/test_phase14_5_real_mongo.py
apps/backend/tests/test_phase14_case_management_performance.py
apps/backend/tests/test_phase17_case_activity.py
apps/backend/tests/test_zero_touch_orchestration.py
apps/frontend/src/api.ts
apps/frontend/src/App.tsx
apps/frontend/src/AttentionQueue.test.tsx
apps/frontend/src/caseQueries.ts
apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx
apps/frontend/src/pages/AuditTrail.tsx
apps/frontend/src/pages/CaseDetail.tsx
apps/frontend/src/pages/IntelligencePanel.tsx
apps/frontend/src/Phase15CNavigation.test.tsx
apps/frontend/src/Phase17CaseActivity.test.tsx
apps/frontend/src/PrePhase22Intelligence.test.tsx
apps/frontend/src/types.ts
docs/aegis/adr/ADR-0001-onboarding-intelligence-advisory-boundary.md
docs/aegis/INDEX.md
docs/aegis/plans/2026-09-23-pre-phase22-capability-expansion.md
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/10-intent.md
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/20-checkpoint.md
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/90-evidence.md
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/99-reflection.md
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/baseline-read-set-hint.json
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/baseline-usage-draft.json
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/drift-check-draft.json
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/impact-statement-draft.json
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/task-intent-draft.json
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/todo-checkpoint-draft.json
docs/ARCHITECTURE.md
docs/contracts/OWNERSHIP_UBO_PROFILE.md
docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md
docs/contracts/POLICY_AUTHORITY_MATRIX.md
docs/decisions/DECISION_LOG.md
docs/demo/PRE_PHASE22_INTELLIGENCE_DEMO.md
docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md
docs/models/ENTITY_RESOLUTION_MODEL_CARD.md
docs/models/MOCK_ADVISORY_RISK_MODEL_CARD.md
docs/models/UBO_ADVISORY_MODEL_CARD.md
docs/PROJECT_STATE.md
docs/research/INDUSTRY_STANDARD_USAGE.md
docs/sponsor-questions/OPEN_QUESTIONS.md
scripts/dev_context.py
scripts/evaluate_onboarding_intelligence.py
```
