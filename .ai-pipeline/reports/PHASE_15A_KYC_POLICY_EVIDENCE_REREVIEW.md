# Phase 15A — Sponsor Rebaseline and Behaviour Alignment

## Fresh Independent KYC Policy & Evidence Re-Review

**Reviewer role:** Fresh Independent KYC Policy & Evidence Re-Reviewer. I did not
plan, implement, remediate, or perform the preceding failed review. This re-review is
read-only apart from creation of this report.

**Verdict: PASS.** P15A-KPE-001 is fully closed and no HIGH, MEDIUM, or LOW finding
remains in the final scoped Phase 15A state.

## Baseline and reviewed remediation

- Branch: `codex/phase15a-sponsor-rebaseline`
- HEAD: `1893f74e744bb1f6da32e2be9b27b68deed5ad6a`
- `origin/main`: `1893f74e744bb1f6da32e2be9b27b68deed5ad6a`
- Merge base: `1893f74e744bb1f6da32e2be9b27b68deed5ad6a`
- A fresh `git fetch origin` completed before the review; baseline identifiers remain
  the expected identical SHA.

I directly inspected the full scoped tracked diff, the intended untracked planner,
implementation evidence, previous KYC review, remediation evidence, focused test, and
the current implementation/docs named in the review assignment. The remediation under
review adds Q-017 and Q-018 to the `PROJECT_STATE.md` structured inventory and its
current-blocker summary; it makes no runtime change.

## P15A-KPE-001 closure

**Status: CLOSED.** The `project-state` JSON parses successfully and its
`open_sponsor_questions` is exactly the ordered set Q-001 through Q-018. It contains
both Q-017 and Q-018. `PROJECT_STATE.md` also contains:

- a Q-017 blocker which keeps the supplied LOW/MEDIUM/HIGH direction while leaving
  producer/source, validation/provenance, update authority, workflow reactions,
  EDD/approval, and readiness blocking unresolved, and explicitly does not authorize
  a calculated score;
- a Q-018 blocker which correctly limits the external Zero-Touch -> Mock GoldTier
  sequence to POC architecture and leaves production placement, handoff, transferred
  state/evidence, and ownership unresolved.

The blocker wording does not answer either question. `python
scripts/check_project_state.py` passes, and `python scripts/dev_context.py` reports
Q-001 through Q-018 as open.

## Semantic re-review

| Lens | Result | Direct final-state evidence |
|---|---|---|
| A. Risk | PASS | The diff adds no field or engine. Q-017 and the blocker describe supplied direction only, prohibit calculation, and leave reaction authority open. No numeric score, weighting, probability, MAS-derived score, priority mapping, or ML classification is introduced. |
| B. Present != verified | PASS | D-042 and architecture text state `PRESENT != VERIFIED`; the registry UI label is `Registry acquisition`, not verification. |
| C. Evidence model | PASS | Value + Source + Evidence + Date + Confidence + Status is expressly descriptive; it does not assign every property to every value or make confidence/status authority. |
| D. Source authority | PASS | No global winner is added. The current UI retains separate observations and says no source wins automatically; Q-015 remains open. |
| E. ACRA cache/freshness | PASS | Cache-first is future-only; 90 days is example/configurable future policy only; no cache or current policy is implemented/claimed. |
| F. UBO | PASS | The existing Decimal ownership engine remains sole owner. The 25% inclusive comparator remains project-defined/provisional pending Q-004. |
| G. Priority | PASS | P1-P10 behavior is unchanged. No 1-3 orientation, SLA, due date, routing, escalation, or risk consequence is invented; Q-016 remains open. |
| H. Case ageing | PASS | Case timestamps remain factual history only. No ageing, SLA, due-date, or escalation engine is claimed. |
| I. OCDD/refresh/perpetual KYC | PASS | These remain Future/KIV only; no periodic, event-driven, or scheduled intervention exists or is claimed. |
| J. Zero-Touch/GoldTier boundary | PASS | Current external Zero-Touch -> readiness -> Mock GoldTier is explicitly prototype/POC architecture. Production placement and handoff remain unresolved in Q-018. |
| K. Provider/environment truth | PASS | ACRA default Mock, generic sandbox partial, BizFile dormant, local deterministic IDP, and Mock GoldTier remain explicit. No live ACRA, GoldTier, or PingFed claim was introduced. |
| L. Camunda | PASS | No runtime adapter, worker, dependency, composition, or runtime claim is introduced. |
| M. AI | PASS | Deterministic registry identity, reconciliation, UBO, readiness, and approval owners remain unchanged; no AI decision ownership is introduced. |

## Sponsor-question, decision, and frontend review

- Q-001 through Q-016 are preserved in the structured open inventory. Q-004, Q-015,
  and Q-016 remain unresolved, with Q-016 correctly requesting the unsettled 1-3
  direction, orientation, ownership, and consequences.
- Q-017 and Q-018 remain unresolved in both the question log and operational project
  state. No surrounding prose supplies the producer, risk rule, production placement,
  or handoff model that the questions request.
- D-042 is present and explicitly labelled **PROVISIONAL / PROJECT WORKING DECISION**.
  It is not sponsor confirmation, regulation, final production architecture, or runtime
  authorization.
- `HomeOnboarding` truthfully says the user supplies the registration identifier and
  supporting corporate documents, processing starts after supply, and the POC does not
  solicit or collect upstream documents.
- `RegistryStatePanel` renders `Registry acquisition`; the retired `Registry
  verification` stage label is absent. Its reconciliation copy preserves separate
  observations and no automatic winner.

## Reproduced checks

| Command | Result |
|---|---|
| `npm.cmd --prefix apps/frontend test -- --run src/Phase15ASponsorRebaseline.test.tsx` | PASS — 1 file, 2 tests |
| `python scripts/check_project_state.py` | PASS |
| `python scripts/check_architecture.py` | PASS |
| `python scripts/dev_context.py` | PASS — reports Q-001 through Q-018 and the expected provider matrix |
| `git diff --check` | PASS — no whitespace errors; only non-failing line-ending warnings |

No physical Mongo test or external-provider access was performed.

## Findings and readiness

**Findings:** NONE.

- HIGH: 0
- MEDIUM: 0
- LOW: 0
- Non-claims verified: YES
- Ready for the normal independent Quality Gate: YES

This means the Phase 15A state is ready for the separate normal independent Quality
Gate only. It does not establish readiness for live ACRA verification, real GoldTier
integration, production deployment, or sponsor-policy adoption.

## Git and data safety

- Stage, commit, push, merge, rebase, reset, stash, clean, and branch switch: not
  performed.
- `camunda-modeler-sync` modification: not performed.
- `.env` accessed, secrets printed, Mongo URI accessed, private key/certificate
  accessed, `clm_poc` accessed, protected unrelated artefacts accessed: no.
- The only review-authored change is this report. Existing Phase 15A working-tree
  changes were inspected but not altered.
