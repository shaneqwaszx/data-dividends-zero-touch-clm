# Sim Lim D-082 opt-in POC ownership acceptance: focused re-Quality Gate 2 (Stage 3, N1/N2 delta)

Reviewer: an independent, read-only focused re-gate. I did not author or remediate this
content, and I did not perform either earlier gate. This report is my only repository write.
Probes, junit files, logs, two read-only tree extracts and temporary indexes are under the
scratchpad folder `qg_d082_r2\`.

## 1. Executive Result

**PASS WITH NON-BLOCKING FINDINGS.** In the skill's vocabulary this is **PASS**: no fix is
required. Four Info findings are recorded for owner awareness (§3–§5).

- **N1 is resolved.** The F2 rebuild (`poc_revoked`) now fires only for an analysis that
  carries a POC acceptance.
  - For every analysis without one, the recovery logic is now the same as on HEAD/`main`.
    `poc_basis_accepted` is always false when `poc_acceptance is None`, so `current_review`
    equals HEAD's, `poc_revoked` is false, and `unproved_ownership_checkpoint` equals HEAD's.
  - My parity probe ran the same interrupted non-D-082 manual replacement, two resumes, a
    confirmation attempt and a correction on the candidate and on a read-only HEAD extract.
    The two JSON dumps of states, stages, exceptions, event codes, HTTP codes and target
    calls are byte-identical.
  - Every D-082 revocation I tried still rebuilds, withdraws the confirmation hold and
    never dispatches: flag off, lane change, allowlist removed, allowlist changed, key
    rotated without new digests, and an acceptance that is no longer current.
- **N2 is resolved.** The header claims "POC basis accepted" only when the backend accepts
  the basis and no active exception or intervention owns OWNERSHIP. I evaluated the exact
  predicate over real API responses in six states, and it was truthful in each.
- **Docs.** The N1, N2 and N3 statements in D-082 F2/F6 and the demo guide are accurate.
  One demo sentence is imprecise (I3, Info).
- **Delta.** Exactly five files changed between `5e7ca651…` and `51ce370…`. Nothing else
  changed.

Verdict scope: the frozen product tree `51ce37012d845e4545335b79e71754a87f09873a` only.

## 2. Reviewed identity and acceptance checklist

**Identity.**
- Branch `feat/sim-lim-acra-ownership-followthrough-20261024`. HEAD = BASE = `origin/main` =
  `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322`. The work is uncommitted.
- I recomputed the tree with a temporary `GIT_INDEX_FILE` under `qg_d082_r2\` at the start,
  and again after every test, probe and E2E run. The steps were `read-tree HEAD`, `add -u`,
  then the three task-owned new files. Both results were
  **`51ce37012d845e4545335b79e71754a87f09873a`**.
- The real index stayed empty (`git diff --cached`: 0 files) at the start, mid-gate and at
  the end.
- Preserved reports, checked by `git hash-object` at the start, mid-gate and the end:
  - `SIM_LIM_D082_POC_ACCEPTANCE_QUALITY_GATE.md` = `2ac85dc107822764376af61c90f501f33f4f5b89`;
  - `SIM_LIM_D082_POC_ACCEPTANCE_RE_QUALITY_GATE.md` = `b8c711cd9c04c769203f187d05e062ef279bdf34`.

**Delta reviewed in depth: `5e7ca651…` → `51ce370…`.**
- 5 files, +47/−8. The EOL-insensitive stat is identical, and `git diff --check` is clean:
  - `zero_touch_orchestration.py`;
  - `test_poc_ownership_acceptance.py` (one new test plus an import);
  - `CaseDetail.tsx`;
  - `DECISION_LOG.md`;
  - `FIVE_LAYER_ACRA_HYBRID_DEMO.md`.
- A `git diff --no-index` of the extracted `5e7ca651…` backend `app/` against the
  candidate's `app/` shows only `zero_touch_orchestration.py` (+11/−5).
- The full delta `ceefe1e` → `51ce370…` (59 files, +4509/−185, `--check` clean) was used as
  context only.
- The delta touches no AI Assistant, GoldTier, connector, discovery, `scripts/` or config
  path.

| Requirement | Result | Evidence |
|---|---|---|
| N1: rebuild only analyses carrying a POC acceptance | PASS | `zero_touch_orchestration.py:2882-2896`. Logic proof (§4). The new test fails on `5e7ca651…` and passes on `51ce370…`. HEAD parity probe byte-identical |
| N1: every revoked D-082 case still rebuilds | PASS | Probe, 6 variants: flag, lane, allowlist removed, allowlist changed, rotated key, tampered acceptance. Each gives OWNERSHIP_INCOMPLETE only, OWNERSHIP removed from completed stages, confirmation refused, no target write. Restoring authority then resuming returns to `TARGET_CONFIRMATION_REQUIRED` with no blockers. Existing F2 test and physical restart test pass |
| N1: a stale acceptance from a replaced analysis cannot matter | PASS | Both replacement constructors build a fresh record (`ownership_analysis.py:1056-1098, 1158-1170`). The validator forbids an acceptance with another analysis id, another state or a manual receipt (`domain/ownership.py:738-751, 863-872`). `get()` returns None for a stale identity or binding. Probe: an interrupted replacement of an accepted analysis, with authority on or off, gets the pre-D-082 restoration and stays fail-closed |
| `poc_revoked` withdrawal of every `target-confirmation:` hold, limited to D-082 | PASS | `:2930-2947`. D-082 variants cancel the hold. The non-D-082 parity dump keeps it active exactly as on HEAD |
| N2 header truthful in every state | PASS (Info I1, I2) | `CaseDetail.tsx:1252-1253, 1299-1304`. Predicate probe across 6 states (§4) |
| No other surface regressed | PASS | Only the header expression changed. Vitest 15 files / 458 tests pass. `tsc -b` passes. E2E `five-layer-hybrid.e2e.ts:78` passes |
| Docs N1–N3 accurate | PASS (Info I3) | `DECISION_LOG.md:664-669, 673-675`; demo `:311-313` (§3) |

## 3. Contract and Integration Findings

No contract or mapping finding. Authority stays `USER_AUTHORIZED_POC` /
`PROJECT_DEFINED_PROVISIONAL`. No Live, ACRA, legal UBO, denominator or hierarchy claim is
added.

**Docs checked against code and probes.**
- F2, "applies only to analyses carrying a POC acceptance; every other review analysis keeps
  the existing restoration": matches `:2885-2896` and the HEAD parity dump.
- F2, "Until that resume, the case header shows the ordinary ownership-attention status":
  matches the probe state "re-enabled, not resumed". The case is held at OWNERSHIP and the
  header predicate is false.
- F2, "no dedicated resume control … the existing resume operation clears it": matches
  code inspection. The browser calls resume only for these states (`CaseDetail.tsx:803-830,
  1716-1722`):
  - recovered intake;
  - document-refresh recovery;
  - safe target continuation;
  - `RECOVERY_PENDING`.
- F6, "terminal technical failure at the GoldTier stage; re-enabling does not resume it;
  no target operation": probe result is `TECHNICAL_FAILURE` / `CLM_NOT_READY` /
  `current_stage` `MOCK_GOLDTIER`. After re-enabling it is still `TECHNICAL_FAILURE`. An
  explicit resume returns HTTP 200 and changes nothing. There are no attempted operations
  and no GoldTier result.
- `OWNERSHIP_UBO_PROFILE.md:444-445`, "Withdrawn authority re-raises the ownership hold on
  resume (F2)", stays accurate for D-082 cases.

**I3 — Info. One demo sentence assumes a resume happened while disabled.**
- Location: `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md:311-313`.
- "Until then it shows the ordinary ownership hold" is true only if a resume ran while the
  policy was off.
- My probe re-enabled without an intervening resume. The case was still at
  `TARGET_CONFIRMATION_REQUIRED`, the header showed acceptance, and confirmation completed
  the Mock send.
- The preceding bullet ("resume restores the ordinary ownership hold") gives the intended
  context, so this is wording only.

## 4. Tester and Adversarial Findings

**Commands I ran on the frozen working tree** (product tree `51ce370…`).
- Backend: venv Python from `apps\backend`, `APP_ENV=test`, `PYTHONPATH=tests;.;../..`,
  `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider -o faulthandler_timeout=300`, junit
  output to scratch.
- Probes: scratch files loaded with `-p conftest`.
- Physical: `PHASE12_MONGO_URI` pointed at the disposable loopback mongo:7 on port 27094.
  Each test generated and dropped its own database. `clm_poc` was never touched, and the URI
  was never printed or written (0 matches in junit and logs).

| Check | Result |
|---|---|
| `test_poc_ownership_acceptance.py` + `test_zero_touch_orchestration.py` + `test_am18_ownership_checkpoint.py` | **168 passed** (65 + 88 + 15), 0 failed/skipped (junit) |
| Physical `test_recursive_ownership_real_mongo.py`, including the D-082 restart test | **5 passed**, 0 skipped |
| Recovery regression, 18 files (classification-conflict review, document-refresh, Garden partial resume, hybrid overlay, manual ownership, official shareholder, phase24b ×5, policy-provider, s3-retained, slice-C ×2, target-classification, target-reliability, exception remediation) | **423 passed**, 0 failed/skipped |
| New N1 test against the `5e7ca651…` extract (its `app/` plus the candidate test file) | **FAILED as expected**: OWNERSHIP not in completed stages. So the test discriminates the N1 behaviour |
| N1 parity probe on the candidate and on the HEAD `ceefe1e` extract | 1 passed on each. JSON dumps **byte-identical** (`cmp`) |
| D-082 probes `probes_d082\` | **12 passed** (details below) |
| `ruff check --no-cache` (both changed backend files); `mypy app` (cache in scratch) | All checks passed; **no issues in 129 files** |
| Frontend `tsc -b --pretty false` | PASS (exit 0). Build info goes to the ignored `node_modules/.tmp` |
| Vitest: OwnershipStructure, ReviewAndSend, UboSummary, OwnershipPathExplorer, ownershipDisplay, S2OwnershipReview, ManualOwnershipEvidenceForm, OwnershipDiscovery | **126 passed** (8 files) |
| Vitest, CaseDetail renderers: S3SubmissionStatus, UiV2Integration, Phase15CNavigation, AM03SearchStage, PendingDocumentsBanner, EvidenceWorkbenchIsolation, ResumeDocumentRecovery | **332 passed** (7 files). The `act()` warnings are console noise, not failures |
| Browser E2E, one selector `e2e/five-layer-hybrid.e2e.ts:78` (ports 9600/4900, Tesseract on PATH, `CLM_E2E_SYNTHETIC_MONGO_PORT=27094`) | **PASS 1/1** (discovered 115, selected 1) |
| Hygiene | Delta and full `git diff --check` clean, with no EOL churn. Count-only leak scan of the 52 added delta lines: 0 matches for 64-hex digests, `e-`+48-hex ids, NRIC/FIN-format tokens, `mongodb`, or credential words |

**N1 logic proof.** When `poc_acceptance is None`, `poc_acceptance_current` is false
(`ownership_analysis.py:516-518`), so `poc_basis_accepted` is false (`:871-879`). That makes
`current_review` identical to HEAD's, `poc_revoked` false, and `unproved_ownership_checkpoint`
identical to HEAD's. The `target-confirmation:` withdrawal is gated on `poc_revoked`. So
every non-acceptance analysis takes exactly HEAD's path. The parity dump confirms this at
runtime:
- after the interrupted replacement and resume, `OWNERSHIP_INCOMPLETE` and the
  `TARGET_CONFIRMATION_REQUIRED` hold are both active;
- OWNERSHIP stays completed;
- confirmation gets 409, and the target calls stay `["search"]`;
- the later correction returns 200 and goes back to target confirmation.

**Adversarial probes** (scratch only; synthetic values only).
- **Six revocation variants** of an accepted Garden case: the flag disabled; the hybrid
  overlay removed (lane change); the allowlist removed; the allowlist changed (ceased status
  moved); the key rotated without re-derived digests; and the stored fingerprint tampered
  (acceptance not current). Each one:
  - still has `poc_acceptance` on the record, with `poc_basis_accepted` false;
  - after resume: `WAITING_FOR_REVIEW`/OWNERSHIP, only `OWNERSHIP_INCOMPLETE`, OWNERSHIP
    removed from completed stages, readiness blocked;
  - refuses confirmation; a second resume stays held; no execution and no GoldTier result;
  - with authority restored, the next resume returns to READINESS with only
    `TARGET_CONFIRMATION_REQUIRED` and no blockers.
- **A rotated key with re-derived digests** for the same identities keeps the acceptance
  current. This is correct: the stored acceptance holds only counts and a fingerprint, with
  no key-dependent value.
- **Interrupted replacement of an accepted analysis**: an independent incomplete creator
  declaration, with the automation save failing, then 503. The ownership record becomes a
  manual REVIEW_REQUIRED analysis with `poc_acceptance` None. With authority on or off,
  resume gives the pre-D-082 restoration: `OWNERSHIP_INCOMPLETE` beside the old
  confirmation hold, OWNERSHIP still completed. Confirmation is refused and no target write
  happens. An acceptance cannot outlive its analysis.
- **F6 terminal**: covered in §3.
- **N2 header predicate** `poc_basis_accepted && !(active_exceptions[].stage ==
  OWNERSHIP || interventions[].owning_stage == OWNERSHIP)`, evaluated on real API
  responses:

  | State | Accepted header shown |
  |---|---|
  | Accepted at READINESS (`TARGET_CONFIRMATION_REQUIRED` only) | yes |
  | Disabled, not yet resumed | no |
  | Disabled and resumed (held at OWNERSHIP) | no |
  | Re-enabled, not yet resumed (backend accepted, hold at OWNERSHIP) | no |
  | Re-enabled and resumed | yes |
  | Sent (`COMPLETED`) | yes |

  Interventions come only from active exceptions and the REGISTRY initial-identity
  projection (`api_models.py:863-1145`). An ordinary accepted case therefore never
  suppresses the accepted header spuriously.

**I4 — Info (test quality).** The new N1 test (`test_poc_ownership_acceptance.py:1241-1260`)
does not assert the resume HTTP status or the restored `OWNERSHIP_INCOMPLETE` hold. It still
discriminates: it fails on `5e7ca651…`. My parity probe confirms resume returns 200 and the
state matches HEAD exactly.

**Not run by me** (I rely on implementer evidence only where stated):
- the full backend suite (implementer R7: 3245 tests, 3069 passed, 176 skipped, 0 failed);
- the full physical runner (implementer: 25 suites, 170/170);
- the full Vitest suite and the build (implementer: 64 files, 1070 tests; build PASS);
- the full browser E2E. The implementer reports 113/115, **not a clean full pass**. Two
  isolated failures passed on rerun, and the `:1248` race is attributed to `main`. I did not
  verify that attribution, and ports 9300/4600 were not touched;
- `pre_pr_check.py`, which does not apply to an uncommitted handoff;
- a live Garden re-smoke, which needs owner authorization and live Mock calls.

## 5. Code and Architecture Review

- N1 is a minimal, well-placed narrowing: one boolean predicate inside the existing owner,
  under the case lock. It adds no new owner, persistence path or target path. The
  `ownership is not None` term is redundant at runtime, but it is harmless and keeps the
  types narrowed.
- N2 is a one-expression change that reuses the existing `stageNeedsAttention` helper. It
  is defined before use (`:1252`), and non-accepted cases are unaffected.

**I1 — Info (test gap).**
- No Vitest or E2E asserts the CaseDetail ownership header for D-082. That covers both the
  accepted text and the new N2 suppression (`CaseDetail.tsx:1299-1304`).
- I verified it by inspection and by the API-level predicate probe, not by rendering.

**I2 — Info (residual mixed message, not a regression).**
- In the "re-enabled, not yet resumed" state:
  - the header now reads "Ownership: REVIEW REQUIRED. Attention required — review ownership
    evidence.";
  - the stale `OWNERSHIP_DENOMINATOR_REQUIRED` intervention offers ownership-details and
    upload actions;
  - CLM readiness shows no blockers, with ownership readiness READY;
  - the panel body still shows "Ownership calculated — POC basis accepted"
    (`OwnershipStructure.tsx:110`, `OwnershipPathExplorer.tsx:192`).
- The real remedy is the API resume. That is disclosed (`DECISION_LOG.md:666-669`, demo
  `:311-313`).
- The state fails closed: there is no confirmation hold, so nothing can be sent. The
  header text itself is truthful about the workflow hold.

## 6. Security Review

No security finding.
- The delta adds no setting, logging, API field or persistence change.
- Protected officer-role values were not touched. My probes used only the synthetic test
  key and the `SYNTHETIC-ROLE-n` fixture.
- I did not open `.env` or anything under the scratchpad `smoke\` folder.
- I called no ACRA or GoldTier host, and printed or persisted no Mongo URI.
- RBAC, team scope, CAS and no-replay are unchanged.

## 7. Required Fixes

None. I1–I4 are owner awareness only. Optional follow-ups are a CaseDetail header Vitest
(I1) and the demo wording (I3); any such change would need a fresh focused review.

## 8. Readiness

- **Stage 3:** PASS WITH NON-BLOCKING FINDINGS for tree
  `51ce37012d845e4545335b79e71754a87f09873a`. The skill-equivalent verdict is PASS.
  Publication still needs explicit owner authorization, unchanged reviewed content, a clean
  committed pre-PR check, and owner acknowledgement that the full E2E run was not clean
  (implementer evidence).
- **Live Garden acceptance with the owner's protected allowlist:** not exercised.
- **Real ACRA / GoldTier:** unchanged and not claimed. Only Mock and offline evidence was
  used.

## 9. Git Status

- Branch `feat/sim-lim-acra-ownership-followthrough-20261024`, HEAD `ceefe1e`.
- 56 tracked files modified; 3 task-owned untracked product files; untracked
  `.ai-pipeline/reports/*`. Nothing staged; the real index is empty.
- Both earlier gate reports are byte-identical (`2ac85dc1…`, `b8c711cd…`).
- My only repository write is this report.
- Probes, junit files, logs, the mypy cache, the `ceefe1e` and `5e7ca651…` extracts and
  temporary indexes are under the scratchpad folder `qg_d082_r2\`.
- E2E runtime evidence went to the gitignored `tmp/`, with results in scratch.
- No implementation fix, commit, push, stash, branch change, install, merge or next phase
  occurred.
- `.env` and the scratchpad `smoke\` folder were not opened.
- No ACRA or GoldTier host was called.
- Ports 8791/5791 and 9300/4600 were not used.
