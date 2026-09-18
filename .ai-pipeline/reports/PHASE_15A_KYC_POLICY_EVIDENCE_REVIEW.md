# Phase 15A — Sponsor Rebaseline and Behaviour Alignment

## Independent KYC Policy & Evidence Review

**Reviewer role and independence:** Independent KYC Policy & Evidence Reviewer. I did not plan or implement Phase 15A. This review was read-only except for this report; no remediation was performed.

## Baseline

- Branch: `codex/phase15a-sponsor-rebaseline`
- HEAD: `1893f74e744bb1f6da32e2be9b27b68deed5ad6a`
- `origin/main`: `1893f74e744bb1f6da32e2be9b27b68deed5ad6a`
- Merge base: `1893f74e744bb1f6da32e2be9b27b68deed5ad6a`
- Expected baseline identifiers match. `git fetch origin` was attempted but could not write `.git/FETCH_HEAD` in the sandbox; the locally recorded `origin/main` identifier was verified and did not move.

## Files reviewed

- `AGENTS.md`
- `.ai-pipeline/001_planner/PHASE_15A_SPONSOR_REBASELINE_BEHAVIOUR_ALIGNMENT.md`
- `.ai-pipeline/reports/PHASE_15A_IMPLEMENTATION.md`
- `docs/PROJECT_STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT_WORKFLOW.md`
- `docs/decisions/DECISION_LOG.md`
- `docs/sponsor-questions/OPEN_QUESTIONS.md`
- `apps/frontend/src/pages/HomeOnboarding.tsx`
- `apps/frontend/src/pages/CaseStatePanels.tsx`
- `apps/frontend/src/Phase15ASponsorRebaseline.test.tsx`
- The final uncommitted diff for each intended tracked Phase 15A file.

## Semantic lenses A–M

| Lens | Result | Evidence reviewed |
|---|---|---|
| A. Risk | PASS | Risk is described as a supplied LOW/MEDIUM/HIGH direction; no score, weighting, calculation, classification, or runtime field was added. Q-017 asks for producer and permitted workflow authority. |
| B. Present is not verified | PASS | D-042 and architecture text state `PRESENT != VERIFIED`; the registry-stage UI now says `Registry acquisition`, not `Registry verification`. |
| C. Evidence model | PASS | The Value + Source + Evidence + Date + Confidence + Status model is expressly descriptive, with no assertion that every source/attribute has every property. |
| D. Source authority | PASS | Documentation and the rendered reconciliation panel retain separate observations and no automatic source winner. Q-015 remains open. |
| E. ACRA freshness/cache | PASS | Cache-first reuse is future-only; 90 days is an example configurable future policy; no current cache is claimed. |
| F. UBO | PASS | Deterministic Decimal ownership remains the sole calculation owner. The 25% inclusive comparator remains project-defined/provisional pending Q-004. |
| G. Priority | PASS | Runtime P1–P10 is not changed; no 1–3 orientation, risk/SLA, routing, escalation, or due-date consequence is invented. Q-016 remains open. |
| H. Case ageing | PASS | The documentation describes timestamps as factual records and denies an ageing/SLA/due-date/escalation engine. |
| I. OCDD/refresh/perpetual KYC | PASS | These are KIV/future only and are not represented as current capability. |
| J. Zero-Touch/GoldTier boundary | PASS | Current external Zero-Touch -> readiness -> Mock GoldTier is correctly labelled POC/prototype architecture; production placement and handoff remain open under Q-018. |
| K. Providers/environments | PASS | ACRA Mock/default, partial generic sandbox seam, dormant BizFile, local deterministic IDP, Mock GoldTier, and absence of live ACRA/GoldTier/PingFed claims are preserved. |
| L. Camunda | PASS | No Phase 15A text introduces a Camunda runtime claim. |
| M. AI | PASS | No AI decision ownership is introduced for registry identity, reconciliation, UBO, readiness, or approval. |

## Sponsor questions and decision

- Q-001 through Q-016 are preserved; Q-004, Q-015, and Q-016 remain unresolved.
- Q-017 is present and asks for supplied-risk producer, evidence, validation, updates, and authorized workflow reaction; it does not authorize a calculated score.
- Q-018 is present and asks for the production Zero-Touch/GoldTier placement and handoff boundary; it does not answer it.
- D-042 exists and is explicitly `PROVISIONAL / PROJECT WORKING DECISION`; it does not claim sponsor confirmation, regulatory status, an approved KYC policy, or final production architecture.

## Frontend rendered-copy review

- `HomeOnboarding` says users provide the registration ID and supporting documents available to them, and that processing starts after supply. It explicitly disclaims upstream solicitation/collection.
- `RegistryStatePanel` renders `Registry acquisition`; its surrounding copy says that routing/acquisition are backend-reported and no source decision is invented by the browser.
- Existing reconciliation copy retains separate registry/document observations and says no source wins automatically.

## Test and check evidence

| Check | Result |
|---|---|
| `npm.cmd --prefix apps/frontend test -- --run src/Phase15ASponsorRebaseline.test.tsx` | PASS: 1 test file, 2 tests passed. Initial sandbox attempt failed before execution with process-spawn `EPERM`; the same command passed when permitted to spawn its local helper. |
| `python scripts/check_project_state.py` | PASS |
| `python scripts/check_architecture.py` | PASS |
| `python scripts/dev_context.py` | PASS; it also confirmed branch/base identifiers and current provider matrix. |
| `git diff --check` | PASS (line-ending warnings only; no whitespace error) |

## Findings

- **P15A-KPE-001 | MEDIUM | `docs/PROJECT_STATE.md:31,202-215` | The machine-readable `open_sponsor_questions` list remains Q-001 through Q-016 after this phase adds Q-017 and Q-018 as unresolved questions. The current-blockers summary also omits Q-017 supplied-risk authority and Q-018 production deployment/handoff authority. | `PROJECT_STATE.md` is the concise operational snapshot consumed by `dev_context.py`; its metadata now conflicts with the question log and can lead future work to overlook two unresolved authority boundaries. | Add Q-017 and Q-018 to `open_sponsor_questions`, and add concise current-blocker entries identifying their unresolved risk-workflow and production-boundary authority. Re-run the project-state check and this independent review after remediation. |

## Verdict and remediation

**VERDICT: FAIL.**

The changed runtime copy and the policy/evidence wording meet the reviewed KYC semantic constraints. However, the required authority state for Q-001 through Q-018 is not consistently recorded in the operational project-state snapshot. The single MEDIUM finding must be remediated by a separate implementation/remediation owner; this reviewer made no changes beyond this report.

## Non-claims verified

YES. Apart from the incomplete project-state question inventory in P15A-KPE-001, reviewed Phase 15A material does not claim calculated risk, implicit global source precedence, implemented ACRA cache/90-day policy, authoritative UBO policy, priority orientation/consequences, an ageing/SLA engine, OCDD/refresh/perpetual-KYC runtime, resolved production Zero-Touch/GoldTier boundary, live providers, Camunda runtime, or AI ownership of deterministic decisions.

## Git and data safety

- Stage: not performed
- Commit: not performed
- Push: not performed
- Merge: not performed
- Rebase: not performed
- Reset: not performed
- Stash: not performed
- Clean: not performed
- Branch switch: not performed
- `camunda-modeler-sync` modification: not performed
- `.env` accessed: no
- Secrets printed: no
- Mongo URI accessed: no
- Private key/certificate accessed: no
- `clm_poc` accessed: no
- Protected unrelated artifacts accessed: no

## Normal independent quality-gate readiness

NO. Remediate P15A-KPE-001 and obtain a fresh independent KYC Policy & Evidence review before the separate normal independent quality gate.
