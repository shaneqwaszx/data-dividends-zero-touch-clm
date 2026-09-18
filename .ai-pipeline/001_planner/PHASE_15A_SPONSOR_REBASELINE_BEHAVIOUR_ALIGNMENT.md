# Phase 15A — Sponsor Rebaseline and Behaviour Alignment

## 1. Objective

Rebaseline the accepted Phase 14/14.5 POC before further functional work.  Make the
implemented behaviour, sponsor direction, project defaults, future architecture, and
open sponsor decisions unambiguous; correct only user-visible claims that contradict
established POC truth.  This phase neither adds a new workflow capability nor resolves
a sponsor decision.

## 2. Rationale and authority

This plan prevents future work from turning roadmap language into product policy.  It
uses the following authority order: current source/tests; current contracts and
decisions; current composition/configuration; open sponsor questions; then historical
phase evidence.  In particular, D-020 through D-040 are project/technical decisions
unless their status expressly says sponsor-confirmed; Q-001 through Q-016 remain open.

The verified planning baseline is `origin/main` and this branch at
`1893f74e744bb1f6da32e2be9b27b68deed5ad6a`; their merge base is the same commit.
`python scripts/dev_context.py` reports the tracked worktree clean and the provider
matrix as ACRA Mock (generic sandbox partial, BizFile dormant), local deterministic
IDP, local Decimal ownership, Mock GoldTier, and no Camunda runtime.

## 3. Scope fence and explicit non-goals

In scope:

- authority-labelled documentation/context and sponsor-question refinement;
- the smallest truthful copy-only frontend corrections identified in section 8;
- tests that prove those corrected claims remain truthful.

Out of scope:

- an ACRA cache, live ACRA, a freshness store, a risk calculation, numeric scoring,
  OCDD, periodic refresh, perpetual-KYC, a scheduler, sanctions/PEP/adverse-media,
  Camunda runtime/model deployment, PingFed, live GoldTier, vendor OCR, a second UBO
  engine, autonomous approval, fuzzy-name identity, new provider, new persistence
  schema, or a priority-policy rewrite.

Do not access `.env`, private sponsor artefacts, the quarantined Postman material,
Mongo URIs, `clm_poc`, credentials, keys, or certificates.  Do not modify
`camunda-modeler-sync`.

## 4. Verified current-state findings

| Area | Current implementation and evidence | Documentation / authority | Finding |
|---|---|---|---|
| Intake | A signed-in user creates a case with UEN, optional country, and optional P1–P10; the browser supplies PDF/DOCX/TXT files. `ZeroTouchOrchestrator.start` requires at least one current non-failed document and, when supplied, exactly the client-declared document count. | D-032 defines the bounded multi-document intake; D-020/D-032 keep document types, fields and completion policy provisional. | The POC receives a package; it is not an upstream solicitation or CRM. “Intake complete” is the technical `start` boundary, not proof that a real-world package is complete. |
| Registry | `JurisdictionResolver` retains observations and routes only resolved SG to ACRA. `RegistryAcquisitionBundle` binds UEN, provider/environment, operation provenance, opaque evidence reference, and UTC retrieval times. ACRA is Mock by default. | D-019, D-028, D-029 and Q-012. | UEN is the exact SG routing/returned-entity binding. No source is Live. |
| Documents/evidence | Document records preserve original extraction, normalised value, confidence, provenance, comparison, review state/event history, and explicit supersession links. | D-020, D-025, D-027, Q-003/Q-013/Q-014. | A document can be present, processed, reviewed, auto-confirmed under a POC rule, or superseded; none alone is sponsor-approved verification. |
| Reconciliation | `ReconciliationObservation` retains immutable source observations; discrepancies retain all observations and a fingerprint-bound bounded decision. `CoordinatedReconciliationUnitOfWork` commits the allowed legal-name change and reconciliation state atomically. | D-030/D-031 and Q-015. | There is no implicit global precedence. `KEEP_REGISTRY_VALUE`/limited `USE_DOCUMENT_VALUE` are bounded POC actions, not source-authority policy. |
| UBO | `OwnershipAnalysisService` is the sole deterministic Decimal graph/calculation owner. The immutable case snapshot supplies the current project default threshold and fixed `>=` comparator. | D-021/D-022, D-029, D-040, Q-004. | `25.000000` and inclusive comparator are project-defined/provisional, not a final legal/controller rule. |
| Priority / portfolio | `CasePriority` currently accepts integers 1–10. Backend ordering calls the numerically larger value “highest”; UI renders 10 Highest and 1 Lowest. Portfolio records retain UTC `created_at`, `updated_at`, and optional `completed_at`; no elapsed-age field, ageing service, SLA, due date, escalation, or refresh exists. | D-040 and Q-016 say priority affects ordering only and production priority/SLA policy is open. | Current P1–P10/highest-lowest semantics conflict with the emerging 1–3 direction and lack authority for orientation. Existing timestamps are factual case history, not an ageing subsystem. |
| Boundary | CLM is an external project-owned orchestration layer; readiness creates an immutable snapshot and invokes Mock GoldTier in ledger-owned order. | Architecture, D-023–D-025, Q-001/Q-005/Q-008. | This is a POC architecture, not a confirmed production deployment or final handoff boundary. |

## 5. Semantics and source/authority classification matrix

Classification key: **A** confirmed current implementation; **B** confirmed
sponsor/project direction; **C** provisional policy/working assumption; **D**
KIV/future direction; **E** open sponsor question; **F** current implementation
conflict; **G** not applicable.

| Semantic | Class | Current truth / rebaseline direction | Gap and required treatment |
|---|---|---|---|
| Onboarding input boundary | A | Users currently provide UEN/country and files. The app receives and processes evidence after that boundary. | Document that zero-touch starts after package supply; do not imply collection/sourcing ownership. Correct only misleading intake copy. |
| ACRA cache-first | D | No cache or reuse decision exists. Future flow may evaluate a retained observation before retrieval. | Describe only the future decision shape: acceptable cached observation → reuse with provenance; stale/missing → retrieve and preserve timestamps/evidence. No runtime cache. |
| 90-day freshness | C | “90 days” is a working example only; no code/configuration/policy uses it. | State it as configurable policy subject to source, attribute, jurisdiction, and sponsor authority; never a universal KYC fact. |
| Supplied risk | B | The requested rebaseline direction is LOW/MEDIUM/HIGH supplied input, not calculated risk. Current POC has no risk field or scoring engine. | Add an open question for owner, source, validation, persistence, workflow reaction, evidence and approval authority. Do not add a model, score, mapping or UI. |
| Priority 1–3 | F | Current 1–10 API/UI and “10 highest/1 lowest” are project POC ordering mechanics; emerging direction says values 1–3 but supplies no orientation or consequences. | Clarify Q-016; do not alter the public priority contract until sponsor/project owner defines value set and orientation. Current UI copy is an identified misleading claim and must be changed only after the decision resolves it. |
| Evidence model | A/C | Existing records already carry value/observation, source/provenance, evidence reference, UTC date, confidence where document-supplied, validity/review/status where applicable. | Document the conceptual Value + Source + Evidence + Date + Confidence + Status model as a lens, not a claim that every source or field has every property. Explicitly state PRESENT != VERIFIED. |
| Source authority / reconciliation | A/E | Current sources and discrepancies are preserved; actions are fingerprint/version bound and atomic. | Preserve no-precedence rule; sponsor must define attribute-specific authority, reviewer role and durable audit/recovery requirements (Q-015). |
| Entity matching | A/C | UEN binds Singapore routing and returned registry entity identity. Legal name is an observation compared during reconciliation. | Record UEN-first as present POC identity/routing evidence; prohibit fuzzy name as authoritative identity. Sponsor must define future cross-source identity/review rules under Q-015. |
| UBO | A/C/E | One Decimal engine, snapshots, default 25% inclusive comparator, deterministic evidence. | Preserve unchanged. Q-004 remains necessary for threshold/comparator/policy confirmation. |
| Case ageing | A/D | UTC creation/update/completion timestamps and factual lists exist; no age calculation or operational action exists. | Do not duplicate. Ageing/SLA policy is a future decision linked to priority policy (Q-016). |
| OCDD / refresh / perpetual KYC | D | Not implemented and no confirmed requirement exists. | Keep as KIV architecture; require sponsor scope, trigger, data authority, retention, scheduling, roles and target boundary before any design/implementation. |
| Zero-Touch / GoldTier boundary | A/E | Current external orchestration → readiness → Mock GoldTier sequence is implemented. | Add a deployment/handoff sponsor question: external service, inside/alongside GoldTier, and handoff point. No architecture change. |
| Camunda | G | No runtime adapter, worker, dependency or composition exists. | Separate design/Git Sync work is not authority to introduce runtime Camunda. |
| AI | C/D | AI is not used for registry, reconciliation, UBO, readiness, or approval. D-010 permits only advisory/extraction direction. | Retain deterministic owners and require an explicit, separately authorised advisory scope before any AI use. |

## 6. Requirement-ready and architecture checks

**Requirement Ready Check:** ready for documentation/copy alignment. The supplied
Phase 15A brief fixes scope, classifications, acceptance criteria and stop conditions.
It does not supply authority to implement priority, supplied-risk reactions, cache
freshness, source precedence, OCDD or a production boundary.

**Change Necessity:** documentation alone cannot remove the existing browser claim
“Registry verification”; the minimum code boundary is the display-only label in
`CaseStatePanels.tsx` and its focused rendering regression. Intake copy is likewise
frontend-only and must say that the user supplies the package. All semantic behaviour
otherwise remains documentation-only. Priority wording/validation is blocked rather
than changed.

**Architecture Integrity Lens:** retain the existing canonical owners: source DTO →
canonical evidence → reconciliation → Decimal ownership → readiness → target
ledger. No new owner, compatibility path, state store, or schema is justified. A
frontend label must not become a browser source-authority or policy decision.

**TDD Route:**

- Mode: off.
- Decision: skipped.
- Strict authority: not applicable to this planning-only pass.
- Test posture: post-change focused rendering regression for the two approved copy-only
  changes; no behaviour test is appropriate for unimplemented future direction.

## 7. Implementation gaps and proposed files

The implementation owner must re-check current `origin/main`, this plan, Q-016–Q-018,
and the current UI before every write.  Do not modify a listed file unless its stated
condition still holds.

| Proposed file | Reason and exact bounded change |
|---|---|
| `.ai-pipeline/001_planner/PHASE_15A_SPONSOR_REBASELINE_BEHAVIOUR_ALIGNMENT.md` | This authoritative planning handoff and evidence matrix. Created in this pass. |
| `docs/PROJECT_STATE.md` | Add a dated Phase 15A rebaseline section: package-supplied intake, provider non-claims, no risk engine, priority conflict pending Q-016, no cache/refresh/OCDD, and prototype GoldTier boundary. |
| `docs/ARCHITECTURE.md` | Add only the authority-labelled evidence/reconciliation, UEN-first identity, future cache policy, no-ageing/refresh, and boundary constraints; do not alter the owner map or provider classifications. |
| `docs/decisions/DECISION_LOG.md` | Record one working project decision that the conceptual evidence lens is descriptive, PRESENT != VERIFIED, 90 days is an example configurable freshness policy, and future directions do not authorise implementation. It must cite Q-016–Q-018 and remain provisional. |
| `docs/sponsor-questions/OPEN_QUESTIONS.md` | Refine Q-016 with 1–3 values, orientation and consequences; add one risk-input question and one deployment/handoff-boundary question, unless an authoritative existing ID is found during implementation. Preserve every existing question. |
| `apps/frontend/src/pages/HomeOnboarding.tsx` | Copy only: identify the user-supplied onboarding package and distinguish the POC’s technical start boundary from upstream collection/completeness. No field, API, validation, or workflow change. |
| `apps/frontend/src/pages/CaseStatePanels.tsx` | Copy only: replace “Registry verification” with “Registry acquisition” and retain Mock/partial/live truth. No change to stage state, provider route or response model. |
| `apps/frontend/src/Phase15ASponsorRebaseline.test.tsx` | Focused rendering assertions for the revised intake and registry language, including absence of the retired “Registry verification” claim. |

No persistence, API, DTO, target mapper, provider, policy-catalogue, UBO, risk, cache,
Camunda, dependency, lockfile, or configuration change is proposed.

## 8. Exact runtime changes, conditions and compatibility

1. In `HomeOnboarding.tsx`, replace the introductory text with wording equivalent to:
   “Provide the onboarding package available to you: registration ID and supporting
   corporate documents. This POC begins processing after the package is supplied; it
   does not collect documents from upstream systems.”  Retain the existing file limits,
   browser form, UEN/country fields, and current technical intake completion behaviour.
2. In `CaseStatePanels.tsx`, replace the `Registry verification` card kicker with
   `Registry acquisition`.  Preserve the existing backend-derived status/provenance,
   `Mock` labels, Q-012 disclosure, and every call/stopping behaviour.
3. Do **not** change priority controls. Their 1–10/highest-lowest copy is a real
   conflict, but resolving it requires Q-016. The implementer must stop if asked to
   substitute P1–P3, an order, SLA, escalation, or risk mapping without authority.

Compatibility boundary: browser/API payloads, case state, persisted records, priority
values, ownership threshold, evidence/reconciliation records, source selection, and
target calls are unchanged.  Removing either correction must be a one-file frontend
revert plus its focused test; documentation has no runtime recovery action.

## 9. Documentation/context sequence

1. Revalidate the source and baseline; if `origin/main` changed, stop for an
   authorised rebaseline rather than merging/rebasing in this phase.
2. Add the Phase 15A section to project state and architecture using the classification
   terms in section 5. Do not state a future item as current functionality.
3. Add the one provisional decision-log entry and refine/add sponsor questions. Do not
   mark Q-001–Q-016 resolved or claim that a new question has sponsor authority.
4. Apply the two tightly scoped copy corrections, if their current wording still exists.
5. Update only this plan if discovery finds a material contradiction; otherwise preserve
   historical planners/reports.

## 10. Test and verification plan

Focused copy regression after runtime copy changes:

```powershell
npm.cmd --prefix apps/frontend test -- --run src/Phase15ASponsorRebaseline.test.tsx
npm.cmd --prefix apps/frontend run typecheck
npm.cmd --prefix apps/frontend run build
```

Affected baseline regression because the changed views are in the application shell:

```powershell
npm.cmd --prefix apps/frontend test -- --run
python scripts/check_project_state.py
python scripts/check_architecture.py
git diff --check
```

Documentation-only changes require the two context checks and `git diff --check`.
No backend, physical Mongo, provider, contract, lifecycle, or secret scan change is
created by copy-only work; the independent quality gate may nevertheless run the
repository-required DOCS_ONLY/FRONTEND_UI matrix and must report any skipped evidence.
Before any future PR readiness, an authorised owner must fetch latest main, complete the
pre-PR checklist, and run `python scripts/pre_pr_check.py` on a clean committed tree.

## 11. Sponsor questions preserved and added

Preserve Q-001 through Q-016 without resolution.  Pay particular attention to Q-004
(UBO threshold/comparator), Q-006 (related parties), Q-007/Q-009/Q-010/Q-011
(GoldTier authority/mapping), Q-012 (ACRA contract/access), Q-013/Q-014 (privacy and
review), Q-015 (source authority), and Q-016 (priority/IAM/SLA).

Refine Q-016 to request: whether only 1–3 are permitted; whether 1 or 3 is most urgent;
who assigns/changes it; whether it drives routing/SLA/escalation/due dates; and whether
it has any risk relation.  Add, subject to duplicate-ID check:

- **Q-017 — Supplied risk input and workflow authority:** authoritative producer,
  LOW/MEDIUM/HIGH vocabulary, validation/evidence/provenance, permitted updates,
  retention, which reactions are required, human approval/EDD authority, and whether
  risk can block readiness.  It expressly excludes a calculated score.
- **Q-018 — Production Zero-Touch/GoldTier deployment and handoff boundary:** whether
  orchestration remains external, sits within/alongside GoldTier, where it hands off,
  what state/evidence is transferred, target ownership, and production identity/audit
  implications.

## 12. Security, data and regression risks

The material risk is semantic: words such as “verified,” “risk,” “fresh,” “priority,”
or “completed” can overstate evidence or imply policy.  The focused labels must not
expose raw documents, provider payloads, credentials, URLs with query material, or
private exception detail.  Copy changes must preserve authentication, RBAC, cached
query identity, call stopping, and the explicit Mock/Local/Partial/Dormant labels.

Documentation risk: a decision-log entry can accidentally promote a project default to
sponsor confirmation.  Every new assertion must state its classification and evidence.
No source precedence, document winner, risk-routing rule, freshness duration,
ageing/SLA, or production deployment shape may be inferred.

## 13. Independent review sequence

### A. KYC Policy & Evidence Review

An independent reviewer, not the implementation agent, must inspect the final diff and
rendered UI.  It must verify that: risk is supplied input only; no numeric score or
MAS-like rule appears; `PRESENT != VERIFIED`; `Registry acquisition` has not become a
verification claim; 90 days is configurable/example-only; reconciliation has no global
precedence; UBO stays provisional/deterministic; OCDD/refresh/perpetual KYC are KIV;
and Mock/partial/local modes are not represented as Live.  The reviewer must check that
every sponsor question remains open unless authoritative evidence is recorded.

### B. Normal Independent Quality Gate

A separate QG owner must inspect scope, changed code/tests, frontend behaviour,
architecture ownership, security/data minimisation, regression results, documentation
classification, sponsor-question preservation, Git discipline, and absence of
unrequested provider/persistence/API changes.  It must independently run or reproduce
the section 10 evidence and issue the sole gate verdict.  Remediation, if required,
must be a separate run; a re-QG must be independent again.

## 14. Acceptance criteria

The implementation is accepted only if all the following are objectively evidenced:

1. Every semantic in section 5 is visibly A–G classified.
2. No provisional direction is described as confirmed sponsor policy.
3. No risk score/calculation, priority/risk mapping, ACRA cache, refresh/OCDD, Camunda,
   Live ACRA/GoldTier/PingFed, vendor OCR, or AI decision path exists in the diff.
4. Documentation says a 90-day period is configurable/example-only and records no
   universal KYC assertion.
5. Evidence documentation and UI distinguish acquisition/presence from verification;
   reconciliation still retains observations and decisions without a global winner.
6. UEN remains routing/identity evidence, legal-name comparison remains reconciliation
   evidence, and the Decimal UBO engine/threshold comparator are unchanged.
7. Case timestamps are not relabelled as an ageing/SLA service or duplicated.
8. The prototype Zero-Touch → Mock GoldTier boundary and the lack of Camunda runtime
   remain explicit.
9. Q-001–Q-016 remain open; Q-016 is refined and Q-017/Q-018 are added only after a
   duplicate check.
10. The focused/broad checks in section 10 pass, the two independent reviews pass, and
    no broader application behaviour changes.

## 15. Stop conditions and recovery

Stop dependent implementation and return to the sponsor/owner when a change would
require a priority orientation/value set, risk source or reaction, cache acceptance
rule, source authority, UBO rule, retention requirement, production deployment decision,
or external access not already supported by authority. Stop if baseline/main drifts,
tracked work becomes unowned/dirty, a protected artefact would be needed, a focused test
cannot distinguish the changed claim, or a copy change implies a backend truth that
cannot be proven.

Recovery is deliberately simple: the two UI changes are isolated display copy and can
be reverted without state/data migration. Documentation corrections revert as a bounded
commit only if they are proven inaccurate; never delete preserved historical questions
or reports. No target call, database record, credential, cache, schema, provider or
Camunda artefact is created by this phase.

## 16. Execution readiness view

- **Intent lock:** align claims and durable context; do not implement future semantics.
- **Scope fence:** files in section 7 only; priority contract/risk/cache/refresh remain
  blocked.
- **Baseline lock:** `1893f74e744bb1f6da32e2be9b27b68deed5ad6a` unless an owner
  authorises a fresh rebaseline.
- **Approved behaviour:** two truthful display-copy changes only; all backend and
  provider behaviour remains fixed.
- **Owner/contract constraints:** backend owns policy, evidence, routing, reconciliation,
  UBO and target sequencing; browser owns presentation only.
- **Task batches:** documentation/question update; copy alignment; focused/broad checks;
  two independent reviews.
- **Review gates:** KYC Policy & Evidence Review, then normal independent QG.
- **Drift/rewind:** stop on authority/main drift; revert only the isolated copy/document
  delta if a review disproves it; never rebase/reset/merge to force continuation.
- **Evidence before completion:** section 10 results, review reports, clean scoped diff,
  no secrets, preserved questions and explicit provider non-claims.
- **Advisory boundary:** this is implementation guidance, not a sponsor decision,
  GateDecision, or authority to complete a PR.

## 17. Execution route

**Decision:** inline.  The documentation and two shared frontend components have a
small, coupled terminology boundary; parallel implementation would add coordination
cost without independent owner boundaries.  Separate independent review agents/runs are
required after implementation.  No user confirmation is required for the planned
copy/documentation work; any blocked policy decision requires sponsor/owner direction.
