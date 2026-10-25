# Sim Lim D-081 POC equal-unit distribution: independent re-Quality Gate (Stage 3)

Reviewer: independent Stage 3 re-review after the F1 remediation. I did not author or
remediate this content. Review only. This file is the only repository file written.
Date: 2026-10-24.

## 1. Executive Result

**PASS.**

The owner's option B restriction is implemented at the single manual replacement
boundary, and I verified it independently:
- A creator `CURRENT_EVIDENCE` decision on a graph holding `LOCAL_POC_ASSUMED_EQUAL_UNITS`
  links is refused with HTTP `409 OWNERSHIP_POC_EVIDENCE_REVIEW_REQUIRED`. So is a refusal
  through an earlier kept copy.
- So is a `USER_SUPPLIED_DECLARATION` that keeps any POC link unchanged (same parent party,
  holder party and value). This holds when edges are reordered, relationship ids change,
  or the decimals have a different exponent.
- The refusal happens inside the case lock. It comes after the existing CAS and staleness
  checks, and before `before_replace`, the repository write, the CLM refresh and the
  automation save. Nothing is persisted, and the analysis, rows, readiness and gate state
  stay unchanged.
- D-078 behavior for non-POC evidence, including the five-layer declaration, is unchanged.

F2 to F5 are remediated adequately. Every required check I ran or re-verified passes on
the frozen tree. No required fix remains.

Some owner-visible residuals remain (O1, O2). An authorized creator can still enter the
POC numbers deliberately as an ordinary accountable declaration:
- under re-keyed party identifiers; or
- after an intermediate declaration with different values.

This is consistent with the owner's instruction not to ban manual declarations or alter
the creator role. Most of it is disclosed in the implementer report. It is not a defect,
but the owner should see it before authorizing publication.

## 2. Reviewed identity and acceptance checklist

| Item | Value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\sim-lim-acra-ownership-followthrough-20261024` |
| Branch | `feat/sim-lim-acra-ownership-followthrough-20261024` |
| BASE = HEAD = `origin/main` | `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322`; `git ls-remote origin refs/heads/main` returns the same SHA (no drift) |
| Reviewed content | 39 tracked modifications, all unstaged. The real index has 0 staged paths. The untracked `.ai-pipeline/reports/*` are outside the product tree |
| Recomputed product tree | `ff8f7ab5cbadb6349e3561a48fd030bd76567bfc`, computed with a temporary `GIT_INDEX_FILE` under scratchpad `qg81r` (`read-tree HEAD`, `add -u`, `write-tree`). It matches the brief at gate start and again at gate end |
| Remediation delta | `git diff 1fa01fb..ff8f7ab`: 9 files, +554/-18 (`domain/ownership.py`, `services/ownership_analysis.py`, `tests/test_official_shareholder_evidence.py`, 6 docs). `apps/frontend` has 0 changed files |

| Owner requirement (option B, F2–F5, scenarios) | Result | Direct evidence |
|---|---|---|
| `CURRENT_EVIDENCE` cannot promote POC links (direct) | PASS | `ownership_analysis.py:720-740`. Probe P1: `409 OWNERSHIP_POC_EVIDENCE_REVIEW_REQUIRED` |
| … nor through kept copies or receipt chains | PASS within the D-078 bound | `_poc_assumed_edges` follows `CURRENT_EVIDENCE` receipts through the retained priors, with a cycle guard (`ownership_analysis.py:1919-1945`). P14: one earlier relabelled keep, then CE and declaration are both refused. P13: after 5 relabelled keeps, which only round-1 code could create, the chain has left the four retained priors and CE is accepted. This is disclosed (report lines 225-227) |
| Unchanged redeclaration (the UI default pre-fill) cannot relabel | PASS | Refused when unchanged (P2), reordered (P3), with decimals at a different exponent (`81.8181820`, `81.81818200`, two-holder `50`/`50.0`: P4, P4b, P11), with new relationship ids (P6), when one POC value is kept (P6b), and when only overlay edges change (P6c) |
| No readiness clearance, no provisional candidates, no GoldTier from POC links | PASS | After every refusal: candidates REVIEW_REQUIRED/INDETERMINATE, readiness blocker `OWNERSHIP_REVIEW_REQUIRED`, `goldtier_result`/submission null, 0 external calls |
| Refusal semantics: 409 via zero-touch, before `before_replace` and every write, CAS still wins, user-safe message | PASS | `zero_touch_orchestration.py:1493-1499` maps the code to `main.py:3495-3509`, which defaults to 409. Spy probe: 0 calls to `invalidate_target_dispatch_confirmation`, `replace_review_required`, `refresh_pre_submission_evidence` and `_save` on CE or declaration refusal; the control case calls all four. Stale version gives `ZERO_TOUCH_MANUAL_OWNERSHIP_STALE` first (pinned test). The message (119 characters) names no party. The unchanged frontend shows `detail.message` (`api.ts:118`) |
| Other evidence types preserved; independently supported correction still possible | PASS | Declaration 60/25/15 returns 200 and ANALYZED, with readiness cleared and target confirmation still required (pinned test and P10). `DOCUMENT_OBSERVATIONS` is not POC-gated and stays under its exact-match rule (P9 gives the existing `OWNERSHIP_SELECTED_SOURCE_MISMATCH`). The five-layer D-078 test is unchanged and passes |
| F2: POC reason only with a valid partial outcome and positive retained units | PASS | `domain/ownership.py:464-470, 499-504`. Re-running the previous gate's `qg81/probe_validator.py`: NOT_FOUND, PROVIDER_FAILED and UNVERIFIED_UEN with the POC reason are all rejected now. The builder only ever emits PARTIAL records with positive current units, so no producible v14 shape is invalidated |
| F3: tautology replaced; above-100 rounding handled and documented without engine change | PASS | `test_official_shareholder_evidence.py:552` checks exponent −6 and ±0.0000005 against the exact unit share. `:1210` pins 6 × 16.666667 = 100.000002 with no bound, UNCERTAIN, REVIEW_REQUIRED. Documented in `DECISION_LOG.md:560-562` and the contract. The engine is untouched |
| F4: refusal tests that falsify | PASS | `:1168` (6 row cases) and `:1180` (cap, merge, graph validation). My scratch-mirror mutants for identifier normalization and the self identifier are both killed (section 4) |
| F5: accurate wording, length ≤ 200 at caps, mixed issuers | PASS | `ownership_analysis.py:1207-1235, 1248-1277`. Worst case 193 characters at 2048 rows / 31 of 32, and 194 at a theoretical 100 records × 64 rows. Garden is 185/184. Non-POC texts are byte-identical to BASE. Affected ids include POC issuers (probe: Garden root plus SIM LIM), but this is not pinned (O3) |
| Twelve mandatory regression scenarios | PASS | Each maps to a passing test (report lines 285-297). For #12, "reload" means a read after refusal, not a document/identity reload. Reload regenerates through the same hybrid provider, so the refusal still applies |
| Preservation list | PASS | The remediation touches only the 9 files above. Untouched: Decimal engine, 25% comparator, generic discovery, connector/credentials/cache, Garden and five-layer fixtures, frontend, GoldTier, security. Non-POC D-078 paths are unchanged (`_poc_assumed_edges` is empty without POC links) |
| Documentation truthful | PASS, with O1/O2/O5 notes | D-078 narrowing note (`DECISION_LOG.md:434-435`), D-081 creator-decision and rounding bullets (`:560-575`), contract `:420-423`, ADR-013, ARCHITECTURE, PROJECT_STATE, demo §8 (`:266-271`). The blocker catalogue entry (`blocker_decision_policy.py:1080-1092`) stays accurate ("unsupported declaration stays blocking") |

## 3. Contract and Integration Findings

There is no contract defect. The restriction is applied once, in the owning service
(`OwnershipAnalysisService.replace_review_required_source`). Its only caller is
zero-touch `submit_manual_ownership_evidence`. The only OWNERSHIP-stage blocker action is
`PROVIDE_CORRECTED_OWNERSHIP_EVIDENCE` (`zero_touch_orchestration.py:3962-3967`), so no
other route relabels ownership. No new endpoint, field, schema or frontend change was
made. The error code is additive inside the existing 409 contract.

**O1: Low. Owner-visible residual; documentation scope (not a defect).** The declaration
check compares by party identifier. It compares against the POC links of the current
analysis, or of the graph that analysis kept through `CURRENT_EVIDENCE` receipts. A
deliberate creator re-entry is therefore accepted as an ordinary accountable declaration.
Each of these returned `200`, ANALYZED, the ABCD123 51.13636375 / LIM CHOON HUAT 37.5
values as `PROVISIONAL_UBO_CANDIDATE`, and readiness `[]` with `TARGET_CONFIRMATION_REQUIRED`:
- P5: the POC values re-entered under re-keyed holder party ids.
- P7: a 60/25/15 declaration first, then the original POC values typed back under the
  same ids.

Assessment:
- The implementer report discloses re-keying and the four-prior chain bound (lines
  219-227). The two-step variant is not named.
- None of the residuals is recorded in the durable D-081 text. Its wording ("redeclare any
  POC-assumed link unchanged (same parent, holder and percentage)", `DECISION_LOG.md:570-571`)
  is accurate only when read as party ids of the current or kept graph.
- This sits within the owner decision. Manual declarations are not banned, the creator role
  is unchanged, and declarations remain the accountable, unverified authority of D-078/Q-014.
- In P7, step 1 already clears readiness with arbitrary values, so step 2 adds no new
  capability. The one-click relabelling paths the owner targeted are closed.
- Recommendation (non-blocking): state the comparison scope and this residual in the
  publication handoff/PR text, and have the owner acknowledge it. A durable docs change
  would alter reviewed content and need a focused recheck.

**O2: Low. Limitation by design.** While the POC analysis is current, a declaration whose
values coincide with the POC values under the same ids is refused even if it is genuinely
supported. Example: two equal holders declared 50/50 (P11). The paths that remain are
`DOCUMENT_OBSERVATIONS` matching every edge, or different values. D-081's
"unchanged … refused / different values follow existing rules" implies this. Demo §8's
"a declaration with supported values" does not mention it.

**O5: Info.** The contract's general D-078 bullet (`OWNERSHIP_UBO_PROFILE.md:362-368`) has
no forward reference to the narrowing. The D-081 bullet in the same profile states it, and
the decision log has the explicit note.

Authority: `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL` throughout. No ACRA,
Live, denominator, class-rights (Q-012), legal UBO (Q-004) or sponsor claim is made. Later
sponsor dependencies Q-004, Q-012, Q-014, Q-019 and Q-002 are unchanged. They do not block
this candidate.

## 4. Tester and Adversarial Findings

Environment: the venv interpreter with `app.__file__` confirmed inside the worktree (and
inside the scratch mirror for mutants), `PYTHONDONTWRITEBYTECODE=1` or `-B`,
`-p no:cacheprovider`. No new `.pyc` or cache was written to the repository; I checked
mtimes after the run.

| Check (this gate, tree `ff8f7ab`) | Result |
|---|---|
| Focused pytest: official shareholder (50), five-layer journey (4), manual evidence (26), hybrid five-layer (30) | 110 passed, 0 skipped, 0 failed |
| Ruff `ruff check . --no-cache`; mypy `app` (cache in scratchpad) | All checks passed; no issues in 129 files |
| Physical Mongo rerun, `test_recursive_ownership_real_mongo.py` + `test_phase12_real_mongo.py`, on loopback `sim-lim-d081r-mongo` (`mongo:7`, generated allowlisted DBs, never `clm_poc`, URI set only in the child environment and absent from the JUnit file) | 27 passed, 0 skipped |
| `tests.test_dev_context`, `test_check_project_state`, `test_check_architecture`; contract lane | 55 OK; 44 OK |
| `check_project_state`, `check_architecture`, `check_secrets`; `dev_context.py --benchmark` | PASS; routine mean 30.0% (35.6 / 21.0 / 33.5), with about 0.03 points of headroom (O6) |
| `git diff --check`; per-file `--numstat` with and without `--ignore-cr-at-eol` (candidate and remediation delta) | Clean; identical (39 files, +1829/-151; delta 9 files) |
| Untracked implementer report | No trailing whitespace, no tabs, no CR, final newline |

**Adversarial probes** (`qg81r/probe_f1r.py`, offline fixture transport, memory mode, 0
external calls):

| Probe | Outcome |
|---|---|
| P1 CE; P2 unchanged; P3 reordered; P4/P4b exponent variants; P6 new relationship ids; P6b one value kept; P6c overlay changed | All `409 OWNERSHIP_POC_EVIDENCE_REVIEW_REQUIRED`. The ownership JSON is identical after all of them |
| Zero-touch summary after refusals (`probe_summary_diff.py`) | Only read-time projection fields differ (`readiness.evaluated_at`, `clm.updated_at`, pipeline/timing). A plain re-read shows the same differences, so no mutation occurred |
| P9 `DOCUMENT_OBSERVATIONS` with no selection | Existing `409 OWNERSHIP_SELECTED_SOURCE_MISMATCH` |
| P10 three retries, then an independent declaration | 409 ×3, then 200 ANALYZED with 1 prior. No residue |
| P15 CE of an independent declaration | 200. The chain stops at a USER_SUPPLIED receipt; the values are the declared ones |
| P5 re-keyed ids; P7 two-step | 200, POC values provisional (O1) |
| P8 seven-decimal perturbations | 422. `OwnershipPercent` allows 6 dp, so perturbing by precision is impossible |
| P13 / P14 chains | See section 2 |

**Mutation check** (`qg81r/mutate_qg.py`). It runs only against a scratch mirror under
`qg81r/mirror`, never the worktree, and restores each file byte-for-byte. Baseline 50/50.

| Mutant | Result |
|---|---|
| declaration branch removed; receipt chain removed; F2 unit checks dropped; F5 mixed wording collapsed; F5 POC label wording dropped; builder identifier normalization removed; builder self-identifier check removed | All killed |
| F5 POC issuers dropped from `SYNTHETIC_OWNERSHIP_EVIDENCE` affected ids | **Survived (O3)**. Behavior is correct by probe; no test pins it |

**F3 below 100 (O4, Info).** 3 or 7 equal holders give links summing to 99.999999 or
99.999998. The bound is 0, certainty UNCERTAIN, and everything stays REVIEW_REQUIRED.
This is conservative. The generic bound counts only unresolved corporate branches, and
D-081's rounding bullet mentions only the above-100 case.

**Stage 2 evidence verification** (bound to `ff8f7ab`). The latest tracked mtime is
15:23:46 (+08). The 15:21–15:23 app and test mtimes come from the implementer's
mutation-restore run; the tree hash proves the content is identical.

| Claimed | Verified against the artifact |
|---|---|
| Full backend, 4 chunks | JUnit 732 + 1008 + 653 + 786 = 3179 tests, 175 skipped, 0 failures/errors, so 3004 passed. 146 files = 37 + 37 + 37 + 35, matching the current `tests/test_*.py` count. All chunks start after 15:27 |
| Chunk 3 stall | `chunk3_stalled.log` faulthandler shows `socket.accept` in `asyncio` `_fallback_socketpair` during `new_event_loop` inside the Starlette TestClient portal, in unrelated `test_phase24b_stage_recovery.py`. This is the known Windows environment stall. The whole chunk was rerun fresh: 596 passed, 57 skipped, 0 failed. The classification as an environment stall, not a test failure, is sound and disclosed |
| Physical Mongo | `physical_d081r.log`: PASSED, 25 suites, 169/169, 0 skipped (16:17) |
| Browser E2E | `e2e_d081r.json`: PASS, complete, keep_going, 115/115, started 08:17:40Z (16:17:40 +08). Its identity records only `HEAD^{tree}` (`2b397bf`) and dirty=true, so the binding to `ff8f7ab` is by timing plus the implementer's 16:44 re-freeze. Not rerun by this gate (frontend byte-identical) |
| CI lanes and checkers | `ci_lanes_d081r.log` (15:26): all OK/PASS. I re-ran the governance and contract lanes myself |
| Implementer focused 54 | That run (15:20) predates the restore mtimes. My 110-test run on the frozen tree supersedes it |

## 5. Code and Architecture Review

- **Correct boundary.** The check uses only server-held state: the current analysis, its
  receipts and its retained priors. It sits inside the existing lock/CAS boundary of the
  canonical owner. There is no new owner, repository, workflow or frontend logic.
- **Decimal identity.** Membership uses `(parent_party_id, child_party_id, Decimal)`.
  Equal values hash equally, so exponent variants match.
- **Ordering.** The check runs after provider validation and the document-binding check,
  and before the existing CE exact-graph comparison. On POC cases a CE graph mismatch now
  reports the POC code first; both are 409. Harmless.
- **Coupling.** The service imports `POC_EQUAL_UNITS_PROVIDER` from the connector module,
  which already happened in round 1.
- **Maintainability.** The walk is cycle-guarded and bounded by `prior_analyses` (at most
  4). Snapshot truncation at 200 relationships affects only round-1-only chains. This is
  informational.
- **Test changes** are confined to `test_official_shareholder_evidence.py`. No existing
  test was weakened. The helper `manual_decision` mirrors the frontend payload (party ids
  from the current graph).
- **Accepted debt:** none newly introduced. O3 is an optional test addition.

## 6. Security Review

There is no security finding:
- RBAC (creator-only), reauthorization inside the lock, and CAS are unchanged.
- The refusal message is static and user-safe.
- No secrets, credentials, `.env` access, logging or network path was added.
- No new PII. The holder names in tests and docs already exist in tracked HEAD content; the
  new test identifiers are synthetic.
- `check_secrets` passes.

This gate made no ACRA or GoldTier calls. The only network call was a read-only
`git ls-remote` to origin. The Mongo URI was never printed or persisted.

## 7. Required Fixes

None.

Non-blocking observations for the owner and publication:
- **O1:** acknowledge the deliberate re-entry residual (re-keyed ids, two-step, the
  four-prior bound) and the comparison scope of the declaration check. Recording it in the
  handoff/PR text suffices.
- **O2:** genuine values equal to the POC estimates must use `DOCUMENT_OBSERVATIONS`.
- **O3:** optionally pin the POC issuer in the `SYNTHETIC_OWNERSHIP_EVIDENCE` affected ids.
- **O4:** optionally mention below-100 sums in the rounding note.
- **O5:** optionally add a forward reference in the contract's D-078 bullet.
- **O6:** keep canonical-doc additions minimal (benchmark headroom about 0.03 points).

Any change to reviewed content, including docs, requires a fresh focused independent
recheck.

## 8. Readiness

- **Stage 3:** independent PASS for tree `ff8f7ab5cbadb6349e3561a48fd030bd76567bfc` only.
- **Stage 4 publication:** eligible only with explicit owner authorization and unchanged
  content. Owner acknowledgment of O1 is recommended. A clean-tree `pre_pr_check.py` is
  still required at publication; it was not run here because the content is
  intentionally uncommitted.
- **Live ACRA verification and real GoldTier integration:** not established and not
  claimed. This is Marketplace Mock plus a local POC assumption.
- This verdict authorizes no next phase, commit, push, PR or merge.

## 9. Git Status

- Branch `feat/sim-lim-acra-ownership-followthrough-20261024`. HEAD = BASE = `origin/main`
  `ceefe1e`.
- 39 tracked modifications, unstaged. The real index has no staged paths.
- Untracked: seven prior `.ai-pipeline/reports/*.md`, plus this report.
- Product tree `ff8f7ab5cbadb6349e3561a48fd030bd76567bfc` was unchanged at gate start and
  gate end.
- The only repository write is this report. Probes, the mutation mirror, logs and
  temporary indexes are under scratchpad `qg81r`.
- No implementation fix, stash, commit, push, PR, merge or next phase occurred.
