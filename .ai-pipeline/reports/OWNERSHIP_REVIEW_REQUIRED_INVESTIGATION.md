# Ownership & UBO REVIEW_REQUIRED investigation — Garden hybrid and OPQ five-layer

Stage 1 implementer report, 2026-10-24. It is implementer evidence only, not an
independent QG verdict.

## Identity and method

- Worktree `C:\Users\shane\Desktop\claude-worktrees\ownership-review-investigation-20261024`.
- Branch `fix/ownership-review-required-investigation-20261024`.
- BASE = `origin/main` = `b867e2c7dc53a4fe29a40b4f80e176d8cd25e9e9`. That is merged PR
  #105, whose tree `24fe8a4…` equals the published PR #105 head.
- Change class: `BACKEND_DOMAIN` (from `dev_context.py`). No API, provider or persistence
  class is affected.
- **Reproduction.** I used the normal zero-touch API with these settings:
  `api_marketplace_mock`, `hybrid_direct_overlay`, `registry_cache_mode=auto` and memory
  persistence.
- **Transport.** All calls went to the offline `OfflineFiveLayerProtocolTransport`
  (`AUTOMATED_OFFLINE_SIMULATION`, 0 external calls). Its profiles mirror the 2026-10-23
  live probe:
  - Garden: partnership profile with 4 `OWNER` roles. The live record had 4 people with
    OWNER/PARTNER/MEMBER roles; all four are ownership-like roles, so the outcome is the
    same.
  - OPQ: profile without `constitution`.
  - L2–L5 and SIM LIM: empty.
- **No live calls.** This assignment did not authorize credential use, so no live
  Marketplace call was made. Live facts below cite the Stage 3.5 probe (1 OAuth + 10 reads,
  all HTTP 200).
- Scratch scripts and outputs stayed outside the repository.

## 1. Garden (`11111999A`) — exact cause of REVIEW_REQUIRED

Case state:
- Status `WAITING_FOR_REVIEW`, stage `OWNERSHIP`.
- Ownership `REVIEW_REQUIRED`, source `OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY`.
- `legal_form` `BUSINESS_PARTNERSHIP`, scenario `GARDEN_DIRECT_OVERLAY_V1`.

| Check | Observed |
|---|---|
| Root identity | Official Marketplace entity profile (root legal form from the official constitution) |
| Root edges | Only 2, both `LOCAL_SYNTHETIC_RELATIONSHIP`/`LOCAL`: SIM LIM 62.5%, LIM CHOON HUAT 37.5%. Root units 5000/3000 kept in `supplemental_evidence` |
| SIM LIM | `LEGAL_ENTITY`, UEN `111111111M`, own cache-first official lookup |
| Cache | Run 1: 1 provider-backed lookup, 0 cache hits. Run 2: 0 provider-backed, 1 cache hit (fresh definitive `NOT_FOUND`). Transport total: 1 token + 3 GETs, none on the rerun |
| SIM LIM record | `NOT_FOUND`, depth 1, `max_effective_percent` 62.5. `identity_basis`/`official_entity_lookup` are null by design: the validator reserves them for overlay records, and SIM LIM has no scenario holders |
| Legacy 900/100/100 | Not loaded. The parties are Garden, SIM LIM and LIM CHOON HUAT only, and only official-namespace calls were made |
| Exposure | One path, 62.5%. Record maximum = audit bound = 62.5%; no double counting |
| LIM CHOON HUAT | Direct 37.5%. `threshold_result` INDETERMINATE, `classification` REVIEW_REQUIRED, `synthetic_basis_threshold_result` MET (an unresolved branch can only add) |

Four independent issues:
1. **`INCOMPLETE_LEGAL_ENTITY`** (engine) — the reachable legal entity SIM LIM has no
   disclosed owners.
2. **`CORPORATE_OWNERSHIP_UNRESOLVED`** (discovery) — 1 branch, up to 62.5%.

   Both 1 and 2 follow from SIM LIM's empty official profile plus the deliberately
   direct-only overlay.
3. **`SYNTHETIC_OWNERSHIP_EVIDENCE`** — always raised for hybrid analyses (D-077).
4. **`UBO_REVIEW_REQUIRED`** ("Unquantified role/control evidence…") — the 4 official
   partnership `OWNER` role rows are bound to no ownership edge. The Garden-fixture role
   exemption in `ownership_analysis.py` applies only to the legacy supplement source.

## 2. OPQ (`201511222D`) — exact cause of REVIEW_REQUIRED

Case state:
- Status `WAITING_FOR_REVIEW`, stage `OWNERSHIP`.
- Ownership `REVIEW_REQUIRED`, `legal_form` `OTHER`, scenario `FIVE_LAYER_MARKETPLACE_HYBRID_V1`.

Two issues:
1. **`SYNTHETIC_OWNERSHIP_EVIDENCE`** — affects the root and the 5 overlay issuer nodes.
   All 11 edges are `LOCAL_SYNTHETIC_RELATIONSHIP`.
2. **`OWNERSHIP_METHOD_UNSUPPORTED`** — the official OPQ profile carries no
   `entityConstnDetailsAndType.constitution`. The documented mapping therefore classifies
   the legal form as `OTHER` (also observed live). The live record had the
   `entityConstnDetailsAndType` object, but its other sub-keys were outside the probe's
   safe-field list and were never captured.

No `INCOMPLETE_LEGAL_ENTITY` or `CORPORATE_OWNERSHIP_UNRESOLVED` is raised; the topology
is complete.

## 3. Calculations and classifications — correct

- **Levels:** discovery records sit at depths 1, 2, 3, 3, 4 (L2, L3, L4A/L4B, L5).
- **Single L5 fetch:** L5 `111111111K` was fetched once (1 GET, one record).
  `max_effective_percent` 40 = 30 + 10.
- **Paths:** each path is retained separately and summed exactly:

  | Person | Paths | Total |
  |---|---|---|
  | DIANA KOH | 18.75 + 6.25 | 25 |
  | EDWARD NG | 11.25 + 3.75 | 15 |
  | BEATRICE LIM | 30 | 30 |
  | ALEX TAN | 20 (direct) | 20 |
  | CHARLES ONG | 10 | 10 |

  The totals sum to 100, so nothing is double-counted.
- **Inclusive threshold:** DIANA KOH's aggregate is exactly 25 at full Decimal precision,
  so the synthetic-basis result is MET (inclusive ≥ 25%).
- **Threshold semantics:** every candidate has `threshold_result` INDETERMINATE and
  `classification` REVIEW_REQUIRED. `synthetic_basis_threshold_result` is MET for DIANA
  KOH and BEATRICE LIM and NOT_MET for the others. That matches the contract: the synthetic
  basis is a separate, labelled comparison, never a classification or readiness input.
- **Evidence separation:**
  - `topology_complete=true`;
  - `official_identity_complete=false` (L2–L5 are `LOCAL_SYNTHETIC_IDENTITY`, lookup
    `NOT_FOUND`);
  - `quantitative_evidence_complete=false`;
  - certainty `UNCERTAIN`;
  - `graph_complete=false`. The domain model defines it as evidence completeness: every
    record is `FETCHED`/`CACHE_HIT`, and the validator enforces this.
- **Readiness:** blocked for both cases (`OWNERSHIP_REVIEW_REQUIRED`). No GoldTier result
  and no submission.

## 4. The unchanged UI's statements

| UI statement | Backend source | OPQ value | Assessment |
|---|---|---|---|
| "Graph partial" | `discovery.graph_complete` | false | Correct value (evidence completeness); the label does not show the separate `topology_complete=true` |
| "Up to 0% … undisclosed" | `unresolved_upper_bound_percent`, shown whenever the graph is partial | 0 | Correct topology bound; combining it with "partial" is ambiguous |
| "0 provisional UBOs" | Natural persons with `PROVISIONAL_UBO_CANDIDATE` and `threshold_result` MET | 0 | Correct. The synthetic-basis MET is deliberately not a classification |
| Generic "Review required" | `issues` | 2 codes | Both reasons are in the API. The frontend issue-code type predates `SYNTHETIC_OWNERSHIP_EVIDENCE` |

These are correct backend values presented ambiguously. There are no projection or
calculation defects. The frontend is out of scope and unchanged.

## 5. Finding classification

| ID | Finding | Classification |
|---|---|---|
| G1 | SIM LIM official profile empty, so 62.5% stays unresolved | Provider limitation + expected safeguard |
| G2 / O2 | `SYNTHETIC_OWNERSHIP_EVIDENCE`; authoritative INDETERMINATE vs synthetic MET | Expected safeguard (D-077) |
| G3 | Garden partnership `OWNER` roles raise `UBO_REVIEW_REQUIRED` | Expected safeguard. The official unquantified partner roles are not reconciled with the overlay; extending the legacy exemption would be a new rule. The issue lists no affected parties (coarse but accurate) |
| O1 | OPQ legal form `OTHER` raises `OWNERSHIP_METHOD_UNSUPPORTED` | Provider limitation (constitution absent); any other mapping needs Q-012 authority |
| U1–U4 | UI wording in §4 | Correct backend values presented ambiguously (frontend out of scope) |
| P1 | An officially found non-scenario Marketplace issuer is always `PROVIDER_UNSUPPORTED`: the connector lacks the relationships operation, so acquisition is never COMPLETE, and unit rows carry no authoritative denominator | Provider limitation / Q-012. The generic non-COMPLETE branch was already tested for `PROVIDER_PARTIAL` (`test_recursive_ownership_discovery`). The `PROVIDER_UNSUPPORTED` outcome, and an officially found non-scenario issuer in the hybrid lane, had no test, so a regression test was added |
| D1 | The contract said original units are retained as `supplemental_evidence`; only the root's units are | Diagnostic (documentation) defect; wording corrected |
| A1 | A manual declaration can replace a hybrid analysis with the same synthetic content. `CURRENT_EVIDENCE` does it without retyping, on complete and incomplete graphs alike | **Authority/design gap**, resolved by owner decision **D-078** (option 1: keep current behavior, no restriction). Recorded in the decision log and contract and pinned by a test; no runtime change |

No actual calculation, classification, cache, provenance or graph defect was found, and no
application code was changed.

## 6. Legitimate resolution with existing authority

The review-decision API covers only document and reconciliation decisions. There is no
ownership approval decision, and none was added. The existing route is the creator's
manual ownership evidence: a declaration bound to a current reviewed case document,
recorded as `MANUAL_DECLARATION_POC`/`LOCAL` with a receipt. It is not ACRA verification
and not a legal UBO determination.

Observed offline:
- **`USER_SUPPLIED_DECLARATION`** (complete graph, each parent = 100%) → ANALYZED, then
  `TARGET_CONFIRMATION_REQUIRED`, which is a separate human gate before any GoldTier
  dispatch. `DOCUMENT_OBSERVATIONS` is likewise legitimate when the selected reviewed
  document rows match every edge.
- **Garden `CURRENT_EVIDENCE`** (incomplete graph) → `409
  ZERO_TOUCH_MANUAL_OWNERSHIP_REVIEW_REQUIRED`. Readiness stays blocked. By existing design
  (AM18), the creator's replacement is nevertheless saved:
  - provider `MANUAL_DECLARATION_POC`, state still REVIEW_REQUIRED;
  - only `INCOMPLETE_LEGAL_ENTITY` remains. `SYNTHETIC_OWNERSHIP_EVIDENCE`,
    `CORPORATE_OWNERSHIP_UNRESOLVED` (and its 62.5% bound) and `UBO_REVIEW_REQUIRED`
    disappear from the current analysis;
  - the hybrid analysis moves to `prior_analyses`.

  So the synthetic relabel also happens on an incomplete graph, even though the case
  stays blocked.
- **OPQ `CURRENT_EVIDENCE`** (exact complete synthetic graph, with no new evidence; the
  bound PDF declares no ownership values) → **accepted**:
  - state ANALYZED, source `SINGLE_SOURCE`;
  - links relabelled `MANUAL_DECLARATION_POC`;
  - `SYNTHETIC_OWNERSHIP_EVIDENCE` gone;
  - `OWNERSHIP_METHOD_UNSUPPORTED` also gone, because manual sources carry no registry
    legal form;
  - DIANA KOH and BEATRICE LIM become `PROVISIONAL_UBO_CANDIDATE`/MET;
  - readiness has no blockers, so the case reaches `TARGET_CONFIRMATION_REQUIRED`.

  The prior hybrid analysis, with its source classification, its synthetic issue and its
  `LOCAL_SYNTHETIC_RELATIONSHIP` links, is kept in `prior_analyses`, so the audit trail
  survives.
- **`USER_SUPPLIED_DECLARATION` with the same synthetic numbers** reproduces the same OPQ
  outcome. The creator's declaration authority does not depend on `CURRENT_EVIDENCE`.

**A1 — decision required from the owner.** May any manual declaration resolve a D-077
demonstration case using its synthetic content? If not, at which level should that be
barred?
- The PR #69 contract allows `CURRENT_EVIDENCE` to keep "the exact current graph" and
  lets the creator declare any complete graph. D-077 makes only the hybrid analysis
  REVIEW_REQUIRED, and bars only the synthetic-basis field from classification and
  readiness; it does not address manual replacement.
- Keeping the synthetic graph is functionally "declaring a synthetic fixture complete".
  Any restriction would be a new business rule, so none was implemented.
- Options for the owner:
  1. **Keep current behavior.** The creator remains accountable through the receipt and
     the retained prior analysis, and target confirmation remains a separate human gate.
  2. **Stop the silent relabel only.** `replace_review_required_source` would reject
     `CURRENT_EVIDENCE` when any current link has `LOCAL_SYNTHETIC_RELATIONSHIP`
     provenance (reusing `OWNERSHIP_SELECTED_SOURCE_MISMATCH`, 409), on complete and
     incomplete graphs. It does not stop a creator from retyping the same numbers as a
     `USER_SUPPLIED_DECLARATION`.
  3. **Bar manual resolution of D-077 demonstration cases altogether.** This is a
     stronger new rule; its scope and authority would need defining first.

  Options 2 and 3 each need one regression test and a contract note.

**Owner decision, 2026-10-24 (D-078): option 1, keep current behavior.** The creator
stays accountable through the receipt, the retained prior analysis and target
confirmation, with no restriction. The decision is recorded as D-078 in
`docs/decisions/DECISION_LOG.md` and as a "Manual replacement (D-078)" bullet in the
contract's D-077 section. A journey test pins those three safeguards. No runtime
behavior changed.

Two limits on those safeguards:
- The retained prior analysis is bounded to the latest four prior analyses. After four
  further snapshot-creating changes (manual replacements or document/identity reloads),
  the hybrid snapshot drops out of the ownership record. The hybrid analysis itself
  carries no receipt. The `CURRENT_EVIDENCE` receipt that names it is held by the next
  analysis and drops out one change later.
- Target confirmation gates GoldTier target mutations. The read-only GoldTier Search has
  already run before ownership review.

## 7. Changes (uncommitted)

- **`apps/backend/tests/test_hybrid_five_layer_overlay.py`** — adds `sim_lim_unit_rows`
  and `test_an_officially_found_non_scenario_issuer_stays_unresolved[False|True]`
  (official SIM LIM profile without rows, and with active plus withdrawn unit rows). It
  pins the following:
  - `PROVIDER_UNSUPPORTED`;
  - no overlay, no local fixture and no percentage inferred from units;
  - the 62.5% bound;
  - the review state;
  - one official shareholder read.

  Mutation check: accepting partial bundles fails both variants (`FETCHED`,
  `PROVIDER_INVALID`).
- **`apps/backend/tests/test_five_layer_hybrid_journey.py`** — adds
  `test_garden_hybrid_journey_keeps_the_unresolved_sim_lim_branch_out_of_readiness`. It
  covers the API journey: the four issue codes, the 62.5% exposure, the readiness blocker,
  no GoldTier result or submission, and the 409 for `CURRENT_EVIDENCE` on the incomplete
  graph.

  The same module adds a `keep_current_evidence` helper and
  `test_a_creator_may_keep_the_synthetic_graph_through_the_accountable_path` for
  D-078. On OPQ, `CURRENT_EVIDENCE` gives:
  - ANALYZED, with `MANUAL_DECLARATION_POC` links;
  - a receipt with the selection, the actor and the replaced analysis;
  - the prior hybrid analysis kept, with its classification, synthetic issue and
    `LOCAL_SYNTHETIC_RELATIONSHIP` links;
  - only `TARGET_CONFIRMATION_REQUIRED`, with no GoldTier result or submission.
- **`docs/contracts/OWNERSHIP_UBO_PROFILE.md`** — D1 wording, plus the D-078 "Manual
  replacement" bullet.
- **`docs/decisions/DECISION_LOG.md`** — new entry D-078 (owner decision A1, option 1).
- This report.

No change to the API/types, schema, connector, configuration, business rules, mappings,
auth/security, architecture, provider status, runtime behaviour or frontend.

## 8. Evidence

| Check | Result |
|---|---|
| Focused pytest: hybrid overlay, hybrid journey, probe lane, recursive discovery, discovery policy, manual evidence, AM18 checkpoint, Slice B registry demo | 154 passed, 0 failed, 0 skipped |
| Mutation of the fail-closed classification | New test fails as intended (2/2) |
| Ruff check and format check (changed tests) | PASS |
| `git diff --check`; EOL churn (`--stat` vs `--ignore-cr-at-eol`) | Clean; identical |
| Contract lane (unittest, CI invocation) / delivery assets / dev-context, policy-authority and project-state tests | 44 OK / 4 OK / 51 passed |
| `check_secrets` / `check_project_state` / `check_architecture` / `check_policy_authority` | PASS |
| Full backend, physical Mongo, frontend, browser | Not rerun: application code is byte-identical to PR #105's accepted content (3120/0, 168/168, 1050, 115/115). Only test modules and contract/decision text changed |
| D-078 delta: hybrid overlay, hybrid journey, manual evidence, AM18, P2 remediation, recursive discovery | 137 passed, 0 failed, 0 skipped |
| D-078 delta: governance scripts / dev-context, policy-authority and project-state tests / ruff / whitespace and EOL | PASS / 51 passed / PASS / clean, no churn |

## 9. Remaining provider and sponsor limitations

- **Marketplace Mock data:**
  - SIM LIM basic information empty (Garden branch unresolved);
  - OPQ constitution absent;
  - no relationships operation and no share-capital denominator, so official issuers
    cannot resolve (Q-012);
  - no ownership graph beyond the root.
- **Live-lane application onboarding:** NOT_RUN.
- **Sponsor questions:** Q-004 (legal UBO rule), Q-012 (authoritative ACRA contract and
  denominators), Q-019 (person identity), Q-002 (hierarchy).
- **Owner decision A1:** resolved as D-078. Its retained-history safeguard is bounded to
  the latest four prior analyses.

## 10. Next authorized action

- **Round-1 independent QG:** PASS WITH MINOR FIXES on tree
  `114df971868f26fcd058ea9d5e03a00bcc7a1324`.
- **Remediation:** the required findings F1 (Garden `CURRENT_EVIDENCE` replacement is
  saved) and F2 (narrowed test-coverage claim) and the advisory F3/F4 were corrected in
  this report only. No test, contract or code content changed.
- **Recheck (round 2):** PASS on tree `c798dcfaf5422ff748c3b4c656f732c090685e3c`.
- **Owner decision A1 (2026-10-24):** option 1, recorded as D-078 in the decision log and
  contract, plus one pinning test and the two round-2 advisory wording fixes (R2-A, R2-B).
  No runtime behavior changed.
- **Recheck (round 3):** PASS WITH MINOR FIXES on tree
  `dd7f7e46e31d9dc75f21c3339ffaa8c6e0175aca`. The required R3-1 (target *mutation*, not
  any GoldTier operation), R3-2 (prior-analysis retention bounded to four) and R3-3 (§9
  A1 status) were fixed, along with the advisory R3-A to R3-C. Wording and the test name
  changed only.
- **Recheck (round 4):** PASS WITH MINOR FIXES on tree
  `2ac3d7fbbb5a13d45ba978eb855fa58eef34f3a1`. R4-1 (which receipt drops out, and when;
  reloads also use history slots) was corrected in D-078 and §6.
- **Next:** a focused independent recheck of that sentence. Commit, push and PR need
  separate owner authorization.
