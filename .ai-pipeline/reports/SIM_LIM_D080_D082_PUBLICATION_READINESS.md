# D-080 / D-081 / D-082 publication readiness (Stage 4 preparation only)

This was prepared on 2026-10-25 under the owner's "MASTER HANDOFF — Publication Readiness"
instruction. Nothing was committed, pushed, opened as a PR or merged. No product file was
changed and no provider call was made. Evidence labels used below: OBSERVED (directly shown
by a command or file), INFERRED, and ASSUMED.

## 1. Identity (OBSERVED)

| Item | Value |
|---|---|
| Repository | `shaneqwaszx/data-dividends-zero-touch-clm` |
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\sim-lim-acra-ownership-followthrough-20261024` |
| Branch | `feat/sim-lim-acra-ownership-followthrough-20261024` (no upstream; not on origin) |
| HEAD = BASE | `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322` (no branch commits) |
| `origin/main` after `git fetch origin --prune` | `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322` |
| Ahead / behind | 0 / 0; `git log HEAD..origin/main` is empty |
| Staging index | empty |
| Recomputed product tree | **`51ce37012d845e4545335b79e71754a87f09873a`**, built with a temporary index: `read-tree HEAD`, `add -u`, plus the 3 new product files. It equals the tree given the final independent PASS. |
| Product delta | 59 paths (+4509/−185): 56 modified, 3 added |
| Untracked, not in the product tree | 16 task reports in `.ai-pipeline/reports/` plus this readiness report |

No product file changed after the final gate: the recomputed tree is identical. The only
change since then is report-only: one line in the implementer report now withholds the
protected file's local path (§6). That leaves the product tree and every gate report
unchanged.

## 2. Publication blocker — decision-id collision with open PR #108 (OBSERVED)

- **The collision.** `shaneqwaszx/data-dividends-zero-touch-clm#108` (head `0b2c8dd`, by
  `tash-abe2304`, open and mergeable, base `main`) adds **"D-080 - proposed AI Assistant
  feedback, enhancement requests and single-reviewer POC mode (PROPOSED)"**. This branch's
  D-080, D-081 and D-082 are owner-authorized candidates.
- **Simulated merge.** A three-way merge in a scratch folder (`git merge-file`, no repository
  change) gives:
  - `docs/decisions/DECISION_LOG.md`: **1 conflict hunk**, and the merged file would hold two
    "D-080" decisions;
  - `docs/ARCHITECTURE.md`: merges cleanly.

  No other file overlaps; PR #108 touches only assistant files, its own QG reports, ADR-012,
  ARCHITECTURE and DECISION_LOG.
- **Cost to PR #108 of renumbering.** About 46 added lines mention D-080, across 14 files in
  its diff. Its own report says the number was already moved once (D-076 → D-080), and that
  the decision "still needs Shane's explicit acceptance before merge".
- **Cost to this branch of renumbering.** About 100 added lines mention D-080–D-082,
  including the persisted policy literal `D082_HYBRID_POC_EQUAL_UNITS_V1`. Changing them
  changes reviewed product content and needs a fresh independent gate.

**Owner decision (2026-10-25): option A.**
- Sim Lim / ACRA ownership keeps D-080, D-081 and D-082 unchanged, including the policy
  identifier `D082_HYBRID_POC_EQUAL_UNITS_V1`.
- **D-083 is reserved for AI Assistant PR #108's** currently proposed "D-080".
- Intended merge order: this ownership PR first, then PR #108 after it is updated to D-083
  and revalidated.
- The allocation does **not** approve PR #108's proposed relaxation of the two-person review
  control. The owner will arrange the D-083 amendment on PR #108. This task does not touch
  that branch.

The options considered were:
- **A (recommended):** this PR takes D-080–D-082 and is published and merged first. PR #108
  renumbers its proposed decision to D-083 when it next integrates `main`. This reviewed tree
  is unchanged.
- **B:** PR #108 merges first. This branch must then merge `main`, resolve the DECISION_LOG
  conflict and renumber D-080–D-082 (including the policy literal), followed by a fresh
  focused QG and revalidation by effect.

## 3. Independent quality-gate chain (OBSERVED; reports preserved)

| Scope | Gate report | Verdict | Reviewed tree |
|---|---|---|---|
| D-080 share class / currency | `SIM_LIM_ACRA_OWNERSHIP_FOLLOWTHROUGH_QUALITY_GATE.md` | PASS WITH MINOR FIXES | `4944456…` |
| D-080 recheck | `SIM_LIM_ACRA_OWNERSHIP_FOLLOWTHROUGH_RE_QUALITY_GATE.md` | **PASS** | `5dfa844…` |
| D-081 POC equal units | `SIM_LIM_D081_POC_DISTRIBUTION_QUALITY_GATE.md` | FAIL (F1 creator `CURRENT_EVIDENCE` laundering) | `1fa01fb…` |
| D-081 Option B remediation | `SIM_LIM_D081_POC_DISTRIBUTION_RE_QUALITY_GATE.md` | **PASS** | `ff8f7ab…` |
| U1–U4 presentation + structure cleanup (`ff8f7ab → 97fcc8c`) | reviewed inside D-082 QG 1 | no defect found | `97fcc8c…` (via `08c5ad4c…`) |
| D-082 opt-in POC acceptance | `SIM_LIM_D082_POC_ACCEPTANCE_QUALITY_GATE.md` (blob `2ac85dc1…`) | FAIL (R1 shape-only role binding; F2–F6) | `08c5ad4c…` |
| R1 exact 3 current + 1 ceased, F2–F6 | `SIM_LIM_D082_POC_ACCEPTANCE_RE_QUALITY_GATE.md` (blob `b8c711cd…`) | PASS WITH NON-BLOCKING FINDINGS (skill-equivalent **PASS**) | `5e7ca651…` |
| N1/N2 follow-up | `SIM_LIM_D082_POC_ACCEPTANCE_RE_QUALITY_GATE_2.md` (blob `7a29701f…`) | PASS WITH NON-BLOCKING FINDINGS (skill-equivalent **PASS**, no fix required) | **`51ce3701…`** |

There are no unresolved required findings. The remaining items are informational:
- **I1:** no automated test asserts the D-082 CaseDetail header.
- **I2:** after re-enabling and before a resume, the panel shows "accepted" while the header
  shows ownership attention.
- **I3:** one demo-guide sentence on the re-enable path is imprecise. It says the case "shows
  the ordinary ownership hold" until resumed, but that holds only if it was resumed while the
  policy was off.
- **I4:** the N1 regression test does not assert every detail of the restored hold.
- **Earlier N4–N7:** informational.

The historical FAIL reports and their remediation are retained.

## 4. Changed-file inventory and classification

All 59 product paths are **INTENDED** or **SUPPORTING**; none is **UNEXPECTED**. There is no
`apps/assistant` change, and no GoldTier connector, mapping or navigation change.
`CaseDetail.tsx` changes only the ownership header line.

- **Backend (INTENDED):**
  - `app/config.py`, `app/composition.py`;
  - `app/domain/models.py`, `app/domain/ownership.py`;
  - `app/connectors/acra.py`, `acra_bizfile_sandbox.py`, `hybrid_ownership_overlay.py`,
    `registry.py`;
  - `app/services/ownership_analysis.py`, `ownership_discovery.py`,
    `registry_acquisition.py`, `clm_orchestration.py` (D-082 readiness and F6 pre-write
    guard), `zero_touch_orchestration.py` (D-082 stage and F2);
  - `app/api_models.py`, `app/main.py`;
  - `app/persistence/models.py`, `mongo_case_store.py`.
- **Backend tests (SUPPORTING), 20 files:**
  - new `tests/test_poc_ownership_acceptance.py`;
  - D-080/D-081 updates to the hybrid overlay, official-shareholder, manual-ownership and
    discovery-policy suites;
  - schema-14 updates to the persistence suites (`phase12*`, `phase13*`, `phase14_5`,
    `phase24c`, `s2_*`, `slice_a`, `slice_c`, `classification_conflict*`,
    `target_classification_continuation`, `zero_touch_orchestration`);
  - `test_recursive_ownership_real_mongo.py` (physical D-082 restart).
- **Frontend (INTENDED):** `src/types.ts`, `src/ownershipDisplay.ts`,
  `pages/OwnershipStructure.tsx`, `OwnershipPathExplorer.tsx`, `UboSummary.tsx`,
  `ReviewAndSend.tsx`, `CaseDetail.tsx`.
- **Frontend tests (SUPPORTING):** `OwnershipStructure.test.tsx`, `ReviewAndSend.test.tsx`,
  new `UboSummary.test.tsx`, new `ownershipAssumedBasisFixture.ts`,
  `e2e/five-layer-hybrid.e2e.ts`.
- **Config and docs (SUPPORTING):**
  - `.env.example`;
  - `docs/decisions/DECISION_LOG.md` (D-080, D-081, D-082 and narrowing notes);
  - `docs/contracts/OWNERSHIP_UBO_PROFILE.md`, `ACRA_MOCK_API_PROFILE.md`,
    `REGISTRY_CACHE_FRESHNESS_PROFILE.md`;
  - `docs/decisions/ADR-013_*.md`, `docs/ARCHITECTURE.md`, `docs/PROJECT_STATE.md`;
  - `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md`;
  - `docs/integration/ACRA_API_MARKETPLACE_MOCK_READINESS.md`.

**Report-only evidence to include** (`.ai-pipeline/reports/`):

| Kind | Files |
|---|---|
| Implementer and investigation reports | `SIM_LIM_ACRA_OWNERSHIP_FOLLOWTHROUGH_REPORT.md`, `SIM_LIM_BUSINESS_PROFILE_FIVE_LAYER_INVESTIGATION.md`, `SIM_LIM_POSTMAN_CONTRACT_REVIEW.md`, `SIM_LIM_D081_POC_DISTRIBUTION_REPORT.md`, `SIM_LIM_D081_SCOPE_AUDIT.md`, `SIM_LIM_D081_UBO_PRESENTATION_INVESTIGATION.md`, `SIM_LIM_D081_UBO_PRESENTATION_REPORT.md`, `SIM_LIM_POC_ACCEPTANCE_POLICY_INVESTIGATION.md`, `SIM_LIM_D082_POC_ACCEPTANCE_REPORT.md` |
| Independent gates (7, including the two FAILs) | the seven gate reports in §3 |
| Publication readiness | this file |

The V1 UI-smoke artifacts the owner deferred stayed in the scratchpad and are **not** part of
this PR.

## 5. Acceptance matrix (final tree `51ce3701…` unless noted)

| Area | Requirement | Status | Evidence |
|---|---|---|---|
| ACRA acquisition | Garden official root lookup | PASS | Live smoke: root `ACRA_REGISTRY_ACQUISITION · MOCK`; 3 `entityBasicInformation` GETs |
| | Sim Lim independent shareholder lookup | PASS | Live smoke: 1 `coShareholdersDetails` GET, `SHAREHOLDERS_FETCHED` |
| | Cache-first | PASS (tests) | Repeat-onboarding zero-call tests; physical restart reuses the cache (`SHAREHOLDERS_CACHE_REUSED`). Live smoke ran in fresh memory mode, so it fetched |
| | Live Mock provenance | PASS | Rows tagged `ACRA_REGISTRY_ACQUISITION / MOCK / ACRA_API_MARKETPLACE_MOCK_V1 / OWNERSHIP_PARTIES`. Rows differ from the local fixture body (FGH SERVICES, INC.; Preference/Others classes) |
| | 4 rows; classes, currencies, status kept | PASS | FGH 10000 Ordinary Withdrawn; ABCD123 900 Ordinary; TAN WEI LING 100 Preference; EFGH2345 100 Others (D-080 tests) |
| | Withdrawn row excluded | PASS | Only 1100 active units form the POC denominator |
| Calculation | Garden → Sim Lim 62.5%, → Lim Choon Huat 37.5% | PASS | Local synthetic overlay declaration (`LOCAL_SYNTHETIC_RELATIONSHIP`) |
| | Sim Lim 900/100/100 → 81.818182 / 9.090909 / 9.090909 | PASS | `LOCAL_POC_ASSUMED_EQUAL_UNITS` links; D-081 tests and live smoke |
| | ABCD123 51.13636375; Lim 37.5; Tan, EFGH 5.681818125 each | PASS | Tests and live smoke |
| | Decimal engine unchanged | PASS | Engine and comparator untouched; QG confirmed |
| UBO presentation | 4 assessed, 2 assumed-basis matches, 0 provisional | PASS | Vitest, live smoke, Review & Send line (F5) |
| | Source labels, selected-holder values, root and corporate labels | PASS | U1–U4 and cleanup Vitest; screenshots |
| | Desktop and mobile layout | PASS (earlier) | Mobile overflow check 390/390 in the D-082 v1 smoke; not re-shot for R1 |
| D-082 | Opt-in, default off; Mock hybrid lane only | PASS | Config validator and composition tests |
| | Exact Garden officer set, 3 current + 1 ceased | PASS | 29 mutations, 12 configuration/identity cases, live smoke match |
| | Protected HMAC allowlist | PASS | `SecretStr`; counts-only acceptance; leak scans 0 |
| | No unknown, changed or additional officer accepted | PASS | QG probe B and mutation suite |
| | Roles never treated as shareholdings | PASS | No edge, party or candidate derived; calculations identical with ceased vs current |
| | Fresh, case-bound acceptance | PASS | Version, identity, fingerprint and document-binding tests |
| | Toggle and restart consistency | PASS | In-memory F2 test and physical restart test |
| | Formal classification unchanged | PASS | `REVIEW_REQUIRED`/`INDETERMINATE` throughout |
| | No false UBO ids in the GoldTier snapshot | PASS | Snapshot `provisional_ubo` = 0 / () (confirmed-send test) |
| | Manual correction still possible | PASS | Creator replacement test; Option B 409 refusals retained |
| | Target confirmation mandatory | PASS | Live smoke: button present, not clicked, 0 submissions |
| | Revocation before target mutation (F6) | PASS | `CLM_NOT_READY` before first write, no attempted operation |

**Integrated test evidence on `51ce3701…` (OBSERVED, reused, not rerun):**

| Check | Result |
|---|---|
| Full backend | 3245 tests: 3069 passed, 176 skipped (physical lanes skip without a URI), 0 failed |
| mypy `app` | no issues in 129 files |
| Physical Mongo runner | 25 suites, 170/170 |
| Frontend | typecheck PASS; Vitest 64 files, 1070 tests PASS; build PASS (chunk-size advisory only) |
| CI unittest lanes and checkers (incl. contract 44, `pre_pr_check` unit tests 64, `dev_context` 55) | 16/16 PASS |
| dev_context benchmark | 30.047% (floor 30%) |
| Full browser E2E | **113/115, not a clean full pass** |

The E2E failures, in detail:
- **`authenticated-zero-touch.e2e.ts:1248`:** a `Network.getResponseBody` race. It reproduces
  on **unmodified `main` `ceefe1e`** in 3 of 5 runs of the pair `:1044 → :1248`, so it is a
  pre-existing test-harness issue.
- **`slice-b-registry-demo.e2e.ts:122`:** an individual timeout that passed 2 of 2 isolated
  reruns. An earlier `ownership-document-streamline:79` timeout passed 3 of 3.

**Not run:** hosted CI; the clean-tree `pre_pr_check.py` (it belongs after the authorized
commits); a live smoke of five-layer.

## 6. Security and privacy (OBSERVED)

- **Scanner:** `scripts/check_secrets.py` passes (no supported secret patterns).
- **Content scan (counts only) of every task-owned new or changed file:** zero matches for
  JWT or bearer tokens, secret assignments, NRIC/FIN-format ids, `e-<48 hex>` evidence ids,
  64-hex digests or the protected key. The exported Postman token is never reproduced.
- **Live values:** the live HMAC key, the four digests and the four live role evidence ids
  appear in no repository file, report, log or smoke artifact.
- **One live officer `party_id`** already appears in six files unchanged from `main`: the
  Garden fixture `apps/backend/app/connectors/garden_business.py`, two backend tests, two
  assistant fixtures, and one older report. This is pre-existing baseline Mock fixture data.
  This PR does not introduce or modify it.
- **No env files:** no `.env` is tracked or staged. `.env.example` holds names and syntax
  only; a test asserts empty values.
- **Temporary artifacts are gitignored and must not be staged:** `tmp/` (E2E browser
  evidence), `apps/frontend/dist`, `node_modules`, caches and `.runtime`.
- **Local paths:** reports contain local worktree and scratch paths, as 135 of the 1135
  merged reports already do. The one path that located the protected allowlist file was
  removed from the implementer report (report-only edit).
- **Secret supply:** an authorized local developer adds
  `ACRA_MARKETPLACE_POC_OWNERSHIP_ACCEPTANCE=accept_eligible_poc` and the two protected
  values (`ACRA_MARKETPLACE_POC_OFFICER_ROLE_KEY`, `ACRA_MARKETPLACE_POC_OFFICER_ROLE_ALLOWLIST`)
  to their own backend env file. This is documented in `.env.example` and in demo guide §8.
  The owner's prepared values live outside the repository.

## 7. Configuration, persistence and rollback

- **New settings (all default off or absent):**
  - `ACRA_MARKETPLACE_POC_OWNERSHIP_ACCEPTANCE`: `disabled` or `accept_eligible_poc`. The
    validator requires `api_marketplace_mock` with `hybrid_direct_overlay`.
  - `ACRA_MARKETPLACE_POC_OFFICER_ROLE_KEY`, `ACRA_MARKETPLACE_POC_OFFICER_ROLE_ALLOWLIST`:
    `SecretStr`, read only under the opt-in.
- **Case envelope 13 → 14.** D-080 introduced it; D-081 and D-082 extend the still-unreleased
  14. An exact v13 reader (`DurableCaseSnapshotV13`) accepts prior cases and rejects in v13:
  share class/currency, POC links/records, and a non-null `poc_acceptance` (current or prior
  analyses).
- **Registry cache schema 4** under contract `MARKETPLACE_SHAREHOLDERS_V2` (D-080). D-079 V1
  entries are never reused or rewritten.
- **Acceptance binding:** case, analysis id, ownership version, identity and correction
  version, scenario, policy literal, role counts, and a content fingerprint, all revalidated
  at use.
  - Any change, reanalysis or replacement revokes it, and so does withdrawn runtime authority
    (flag, lane or allowlist).
  - A corrupted policy fails closed with `PersistenceDataInvalidError`, confirmed on
    physical Mongo.
- **Rollback.** Code older than this PR reads at most envelope 13 and cache schema 3. In Mongo
  mode it therefore fails closed on v14 cases and schema-4 cache entries rather than
  misreading them (INFERRED from the unchanged older readers; matches the D-080 record).
  A rollback needs those cases or entries removed or restored by an operator, and never in
  `clm_poc` without explicit authority.
- **Protected database:** no work touched `clm_poc`. Physical tests used generated
  disposable databases on a disposable `mongo:7` (loopback port 27094).

## 8. Live smoke evidence (OBSERVED; owner-authorized, tree `51ce3701…`)

- **Calls:** exactly **1 OAuth token + 4 read-only GETs** (3 `entityBasicInformation`,
  1 `coShareholdersDetails`), all 200. No further calls were made.
- **What was found:**
  - *Official Mock facts:* Garden root registry details; four officer Owner roles (3 current,
    1 ceased); Sim Lim's four shareholder rows and their units, classes and status.
  - *Local POC declarations:* Garden → Sim Lim 62.5% and Garden → Lim Choon Huat 37.5%.
  - *Calculated POC assumptions:* Sim Lim's equal-unit percentages and the resulting indirect
    interests.
  - *Formal outcome:* the POC basis was accepted for workflow progression: no readiness
    blockers, `TARGET_CONFIRMATION_REQUIRED` only, 0 GoldTier submissions. This is **not** a
    legal UBO verification or a production ACRA determination.
- The exact officer allowlist matched, and the candidate tree was unchanged.
- **Artifacts:** screenshots and counts-only JSON in the session scratchpad
  (`screenshots_r1`, `d082_r1_*`).

## 9. Outstanding POC limitations (for the PR body)

- Garden's 62.5% and 37.5% links are local synthetic declarations, not ACRA data.
- Sim Lim has no ACRA entity profile, so its identity is unverified, and the Mock has no
  issued-share denominator (`coCapitalDetails` is empty). The percentages assume equal
  units across classes.
- D-082 is a demonstration policy: opt-in, Garden-only, Mock-only. Formal classification
  stays `REVIEW_REQUIRED`, and the GoldTier snapshot carries **no** provisional UBO ids.
- Recognising the officer roles does not mean they corroborate the shareholder links.
- Sponsor items stay open: Q-004 (UBO policy), Q-012 (denominator semantics), Q-019
  (person identity). None of this is Live evidence.
- **Operator behaviour:** after re-enabling the policy, the stale ownership hold clears only
  through the existing resume operation, and the UI has no button for it (I2/I3). An F6
  refusal is a terminal technical failure.
- **E2E:** `:1248` is a race that already exists on `main` and is outside this PR.

## 10. Proposed Stage 4 sequence (awaiting authorization; not executed)

```powershell
# 0. After the §2 owner decision. Re-verify identity:
git fetch origin; git rev-parse origin/main; git log --oneline HEAD..origin/main
#    then recompute the tree with a temporary index; it must equal 51ce37012d845e4545335b79e71754a87f09873a.

# 1. Product commit: exactly the 59 reviewed paths (list in §4 / scratch pathspec file).
git add --pathspec-from-file=<reviewed-paths.txt>
git diff --cached --check; git diff --cached --stat
git write-tree   # must print 51ce37012d845e4545335b79e71754a87f09873a
git commit -m "feat(ownership): Sim Lim official share classes, POC equal-unit links and opt-in POC acceptance (D-080 to D-082)"

# 2. Report commit: the 17 report files in §4.
git add -- .ai-pipeline/reports/SIM_LIM_*.md .ai-pipeline/reports/SIM_LIM_D080_D082_PUBLICATION_READINESS.md
git commit -m "docs(qg): D-080 to D-082 implementation, investigation and independent gate reports"

# 3. Drift and clean-tree gate.
git fetch origin; git log --oneline HEAD..origin/main   # must be empty
git status --short                                      # must be empty
python scripts/pre_pr_check.py                          # then complete PRE_PR_CHECKLIST.md

# 4. Push and PR (authorized only).
git push -u origin feat/sim-lim-acra-ownership-followthrough-20261024
git rev-parse HEAD origin/feat/sim-lim-acra-ownership-followthrough-20261024   # must match
gh pr create --base main --head feat/sim-lim-acra-ownership-followthrough-20261024 --title "<§11 title>" --body-file <§11 body>
```

The report-only commit does not change the product tree, so the gates stay bound. Hosted CI
has historically not executed on this repository because of billing. Each push and
`pull_request` run is classified from GitHub job evidence; blocked CI is never reported as
passed. The repository owner performs the squash merge.

## 11. Proposed PR

**Title:** `feat(ownership): Sim Lim official share classes, POC equal-unit links and opt-in POC acceptance (D-080–D-082)`

**Body (draft):**

> **Summary.** This PR finishes the Garden → Sim Lim ownership chain on the ACRA API
> Marketplace **Mock** (not production ACRA):
> - **D-080:** keeps each official Sim Lim shareholder row's share class, currency and status.
> - **D-081:** in the opt-in hybrid lane only, turns those official units into labelled POC
>   equal-unit links (`LOCAL_POC_ASSUMED_EQUAL_UNITS`). Option B stops the creator keeping or
>   redeclaring POC links unchanged (409).
> - **Presentation:** assumed-basis presentation and ownership-structure label fixes.
> - **D-082:** an explicit **opt-in, default-off** POC acceptance. An eligible Garden case can
>   then reach target confirmation without manual ownership verification.
>
> **What is official and what is not.**
> - *Official Mock facts:* the Garden registry profile and officer roles, and Sim Lim's four
>   shareholder rows (900 / 100 / 100 active; one withdrawn row excluded).
> - *Local declarations:* Garden → Sim Lim 62.5% and Garden → Lim Choon Huat 37.5%. These
>   are **not** ACRA data.
> - *Calculated POC assumptions:* 81.818182 / 9.090909 / 9.090909 and the indirect interests
>   (ABCD123 51.13636375%; Tan Wei Ling and EFGH2345 5.681818125%). Each assumes equal units
>   across share classes, because the Mock has no denominator.
>
> **D-082 safeguards.**
> - Garden-only, Mock hybrid lane, opt-in.
> - The officer-role exemption needs an exact protected HMAC allowlist of the observed
>   **3 current + 1 ceased** Owner roles.
> - The acceptance is bound to case, version, identity, content and runtime policy, and is
>   revalidated at readiness, in zero-touch and immediately before the first GoldTier write.
> - Formal classification stays `REVIEW_REQUIRED`, and the **target snapshot contains no
>   formally provisional UBO ids**.
> - Target confirmation remains mandatory, and manual correction remains available.
>
> **Config and schema.**
> - New settings: `ACRA_MARKETPLACE_POC_OWNERSHIP_ACCEPTANCE` (default `disabled`),
>   `ACRA_MARKETPLACE_POC_OFFICER_ROLE_KEY` and `ACRA_MARKETPLACE_POC_OFFICER_ROLE_ALLOWLIST`
>   (secrets, never committed).
> - Case envelope **14**, with an exact v13 reader; registry cache schema **4**
>   (`MARKETPLACE_SHAREHOLDERS_V2`).
> - Older code fails closed on the new records.
>
> **Evidence.**
> - Reviewed tree `51ce37012d845e4545335b79e71754a87f09873a`; `origin/main` `ceefe1e`.
> - Backend 3245 tests: 3069 passed, 176 skipped, 0 failed. mypy clean. Physical Mongo
>   170/170. Vitest 1070. Build and the 16 CI lanes pass.
> - E2E 113/115. The `:1248` race reproduces on unmodified `main`, and the other timeout
>   passed when rerun alone.
> - Owner-authorized live Garden smoke: 1 token + 4 GETs, POC accepted, 0 submissions.
>
> **Independent gates.** All reports, including FAILs, are in `.ai-pipeline/reports/`:
> - D-080: PASS on recheck.
> - D-081: FAIL, then PASS (Option B).
> - D-082: FAIL (R1), then PASS, then focused PASS on `51ce3701…`.
>
> **Limitations.**
> - Not Live and not a legal UBO determination. Q-004, Q-012 and Q-019 stay open.
> - Sim Lim's identity is unverified, and the Garden links are synthetic.
> - Re-enabling the policy needs a resume to clear a stale hold.
>
> **Coordination.** The decision ids conflict with PR #108 (see the readiness report §2).
> **Merge:** the repository owner squash-merges after reviewing CI and evidence.

## 12. Result

The initial preparation ended in **PUBLICATION PREPARATION BLOCKED — OWNER DECISION
REQUIRED** over the §2 decision-id allocation.

On 2026-10-25 the owner chose option A and authorized Stage 4 publication (not merge). The
owner also acknowledged the full browser E2E result as recorded: 113/115, with one failure
reproduced on unchanged `main` and one timeout that passed on rerun. That acknowledgement
was the final gate's stated publication condition.
