# Sim Lim D-082 opt-in POC ownership acceptance: independent Quality Gate (Stage 3)

Reviewer: independent Stage 3 gate. I did not author or remediate this content. This report
is the only file I wrote in the repository. My probes, logs and temporary indexes live under
the scratchpad folder `qg_d082\`.

## 1. Executive Result

**FAIL.** One required fix, which is narrow and bounded (R1).

Most of the work verifies well:
- the readiness authority, runtime revocation across real restarts, and downstream GoldTier
  semantics;
- the persistence extension, frontend truthfulness and scope;
- the never-gated U1–U4 / structure-cleanup presentation delta.

One sub-requirement of an owner P1 guardrail is not met. The durable decision, the contract
and the implementer evidence all state it as met.

- Guardrail: "D1=B only for the whitelisted Garden POC scenario **and the exact known
  Marketplace Mock officer-role evidence** … genuine unrelated discrepancies stay blocking".
- What the code binds: a *shape*. That is exactly four distinct-party
  `ROLE`/`OWNER`/`OFFICERS`/`ACRA_REGISTRY_ACQUISITION`/`MOCK` items whose entity identifier
  is `11111999A`. It does not bind the identities of the known roles, and it does not
  exclude ceased roles.
- My probe B swapped all four officer identities and evidence ids for unknown ones. The
  result was still eligible, and the acceptance recorded the unknown ids.
- `DECISION_LOG.md:628-635` says "exactly the four known … records" and "Any other role …
  stays blocking". The contract (`OWNERSHIP_UBO_PROFILE.md:431-433`) and the implementer
  report (line 139: "the exact four known `OFFICERS` `ROLE = OWNER` records") say the same.

Consequence: the candidate is not ready for publication. It returns to bounded remediation
followed by a focused re-QG of the changed delta. Unaffected evidence in §4 can be reused.

Verdict scope: the frozen product tree `08c5ad4cba4ff120f92d5e9b7a4e8fa5c366d2d8` only.

## 2. Reviewed identity and acceptance checklist

**Identity.**
- Branch `feat/sim-lim-acra-ownership-followthrough-20261024`. HEAD = BASE = `origin/main` =
  `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322`. The work is uncommitted.
- I recomputed the tree twice with a temporary `GIT_INDEX_FILE` under `qg_d082\`: once at the
  start and once after every test run. The steps were `read-tree HEAD`, `add -u`, then the
  three new files. Both times the result was **`08c5ad4cba4ff120f92d5e9b7a4e8fa5c366d2d8`**.
- The real index stayed empty (`git diff --cached` showed 0 files).

**Deltas reviewed in depth.**
- D-082 delta `97fcc8c…` → `08c5ad4c…`: 24 files, +1519/−22.
- Presentation delta `ff8f7ab…` → `97fcc8c…`: 13 files, +442/−11. It is frontend, E2E and
  docs only.

| Requirement | Result | Evidence |
|---|---|---|
| D3 opt-in, default off, Mock hybrid lane only | PASS | `config.py:36-40,150-156`; service guard `ownership_analysis.py:770-771`; composition `composition.py:384-387`. Tested in `test_poc_ownership_acceptance.py:220` |
| D2 classification and state unchanged | PASS | Acceptance is set only on the REVIEW_REQUIRED write (`ownership_analysis.py:1658-1687`). Candidates stay REVIEW_REQUIRED/INDETERMINATE. Test `:268` compares a disabled and an enabled run value for value, including identical provider calls |
| D4 extend unreleased envelope 14; exact v13 rejection | PASS | `persistence/models.py:850-861`. Unit test `:796`. The physical test sets `schema_version` 13 and gets `PersistenceDataInvalidError` |
| P1 runtime revocation | PASS | Authority `ownership_analysis.py:791-805` needs this composition's opt-in plus a hybrid overlay. I re-ran the physical restart test: enabled → restart disabled / legacy / local Mock → blocker returns, confirmation 409, stored ownership byte-identical; resume while disabled restores the hold. It passed. See F2 for the reverse direction |
| P1 Garden officer roles | **FAIL (partial)** | Whitelist, root, count, retention, audit ids, no reconciliation and the retained `UBO_REVIEW_REQUIRED` are all correct. "Exact known" evidence is bound by shape only (F1) |
| P1 downstream GoldTier | PASS | `_build_snapshot` takes only `PROVISIONAL_UBO_CANDIDATE` ids (`clm_orchestration.py:1405-1410`). `build_submission_input` uses the case alone. Test `:366`: snapshot `provisional_ubo` (0, ()), related-party (0, ()), ownership reference `REVIEW_REQUIRED`, one execution, replay 409 |
| P2 freshness and persistence | PASS, one low gap | Binding fields, the fingerprint, terminal immutability (`ownership_repository.py:66-76` and the Mongo equivalent `persistence/repositories.py:268-280`), no copy on replacement or reload (`ownership_analysis.py:982-1025,1084-1099`), snapshot retention (`:2162`), existing cases not accepted (test `:465`). The physical test proves the Mongo round trip keeps the fingerprint (`poc_basis_accepted` is true after a restart). F3 is a low gap |
| Authority is the only grant; every consumer routed | PASS | Both CLM `_evaluate_readiness` callers (`clm_orchestration.py:893-895,1384-1386`; `_start_submission` runs inside the CLM lock in `confirm_target_dispatch`). Zero-touch stage `:3152-3192` and restoration `:2867-2871`. API analyze/get `main.py:3153-3155,3179-3181`. `grep` finds no other `poc_acceptance` reader |
| No AI Assistant, GoldTier, connector, discovery, engine or Option B change | PASS | Overall diff: 0 files under assistant, GoldTier or `scripts/`. The D-082 delta touches no connector or discovery code (only an ADR-013 doc line) |
| Owner wording change | PASS, owner note | "UBO classification remains review-required…" appears on no surface. Generic and non-accepted warnings are unchanged (Vitest `OwnershipStructure.test.tsx` D-082 block, test 2). F4 is a residual for the owner |
| Presentation delta U1–U4 + structure cleanup | PASS | Frontend, E2E and docs only. Matches the presentation report's owner authorizations. No company percentage is computed in the browser. Formal counts are unchanged |
| Docs and decision accuracy | FAIL (F1 wording); otherwise PASS | D-082 matches the code except the "four known" / "any other role" claims |

## 3. Contract and Integration Findings

**F1 — Medium (required). D1=B role evidence is bound by shape, not by the known identities.**
- `ownership_analysis.py:311` sets `(GARDEN_BUSINESS_UEN, 4)`. Lines `:408-426` check count,
  distinct `party_id`, kind, `raw_value`, operation, provider, environment and
  `entity_identifier`.
- No identity is checked: neither `evidence_id`/`party_id` nor the known officers.
  `source_status` is also unchecked, and the mapper sets it to `CEASED` for ceased officers
  (`connectors/registry_ownership.py:233-247`).
- Probe B (`qg_d082\probes\test_qg_d082_probes.py`) replaced all four roles with
  `QG-OTHER-OFFICER-0..3` / `qg-other-0..3`. Result: eligible = True, and those ids were
  recorded as `descriptive_role_evidence_ids`.
- So a changed official Marketplace Mock roster for `11111999A` with the same shape would be
  silently treated as descriptive context. The guardrail names exactly that case ("genuine
  unrelated discrepancies stay blocking").
- The 20 mutations in `test_poc_ownership_acceptance.py:488-600` include no identity swap
  and no ceased role.
- Feasibility note:
  - The evidence ids are stable, non-PII hashes of the source `officerId`
    (`registry_ownership.py:259-260`), so pinning is technically possible.
  - The offline transport uses `SYNTHETIC-ROLE-1..4` (`scripts/five_layer_hybrid_fixture.py:104-112`),
    which differs from the live Mock's identifiers (the investigation saw 3 person-format and
    1 UEN-format).
  - Pinning the live identities therefore needs the offline fixture aligned (an owner-scope
    fixture decision). The alternative is an explicit owner ruling that shape binding is
    intended, with corrected wording.

**Quarantine and authority.** No contradictory example was converted into a fixture or
enum. Authority stays `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`. No ACRA, Live,
denominator (Q-012), legal UBO (Q-004), reviewer authority (Q-014) or GoldTier hierarchy
(Q-002) claim is made. These later sponsor dependencies are unchanged and block nothing
here.

## 4. Tester and Adversarial Findings

**Commands I ran on the frozen working tree** (product content `08c5ad4c…`).
- Backend: venv Python from `apps\backend`, `APP_ENV=test`, `PYTHONPATH=tests;.;../..`,
  `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`.
- Physical: `PHASE12_MONGO_URI` pointed at the disposable loopback mongo:7 on 27094. Each test
  generated and dropped its own allowlisted database. `clm_poc` was never touched and the URI
  was never printed.

| Check | Result |
|---|---|
| `tests/test_poc_ownership_acceptance.py` | **34 passed**, 0 failed/skipped (junit) |
| Physical `tests/test_recursive_ownership_real_mongo.py`, including the D-082 restart test | **5 passed** |
| Physical subset: `test_phase12_real_mongo`, `test_classification_conflict_real_mongo`, `test_s2_intelligence_real_mongo`, `test_slice_c_real_mongo`, `test_phase24c_real_mongo`, `test_garden_uen_partial_resume_real_mongo` | **65 passed**, 0 skipped |
| Regression chunk A: 23 ownership, CLM, hybrid, official-shareholder, manual-evidence, persistence, legacy, slice-B, target-classification, remediation and priority files | **935 passed**, 0 failed/skipped |
| `tests/test_zero_touch_orchestration.py` | **88 passed** |
| `python -m mypy app` (strict, cache in scratch) | **Success: no issues in 129 files** (the implementer report lists no mypy) |
| `python -m ruff check .` from `apps/backend` (CI form, `--no-cache`) | **All checks passed**. My broader ad-hoc call over `../../scripts` with the backend config reported 150 findings, outside the CI scope; not attributed |
| Contract lane as CI runs it (`unittest discover -s ../../tests/contract`) | **44 OK**. A first call with a different top-level gave 2 import errors from the invocation; not a product result |
| `check_secrets`, `check_architecture`, `check_project_state`, `check_policy_authority`, `check_external_provider_readiness` | all PASS |
| Frontend `tsc -b` | PASS |
| Vitest, 9 files: OwnershipStructure, UboSummary, ReviewAndSend, OwnershipPathExplorer, ownershipDisplay, S2OwnershipReview, ManualOwnershipEvidenceForm, UiV2Integration, Phase15CNavigation | **211 passed** |
| Browser E2E, one selector `e2e/five-layer-hybrid.e2e.ts:78` (ports 9600/4900, Tesseract on PATH, `CLM_E2E_SYNTHETIC_MONGO_PORT=27094`) | **PASS 1/1** |
| `git diff --check ceefe1e 08c5ad4c` | clean |
| EOL churn | `--stat` = `--ignore-cr-at-eol --stat` (58 files, +3786/−180) |
| New files | final newline, no tabs, no trailing spaces |

**Environmental incident (not a product result).** My first combined regression run stalled
at zero CPU. The stack was the known Windows `socket._fallback_socketpair` → `accept` hang
inside Starlette TestClient portal setup, at
`test_zero_touch_orchestration.py:1094` (`test_missing_initial_identity_is_repaired…`). I
stopped only my own process and re-ran the same files in two chunks. All passed.

**Not run by me.**
- Full backend suite. The implementer reports 3214 tests: 3037 passed, 176 skipped and 1
  environmental live-HTTP timeout that passed on rerun.
- Full physical runner. The implementer reports 170/170 (`d082_physical\run.log`).
- Full browser E2E. The implementer reports 115/115 (`d082_e2e\results.json`, started
  21:25:11 +08:00, finished about 21:50). Its identity records only `HEAD^{tree}` and
  dirty=true. The latest product-file mtime is 21:15:00 +08:00, so the binding to `08c5ad4c`
  holds by timing and by my recomputation.
- Full Vitest and the build. The implementer reports 64 files / 1069 tests and a PASS build.
- `pre_pr_check.py`. It is not applicable to an uncommitted handoff.

**Adversarial probes** (scratch only, `qg_d082\probes\`):
- **B (F1):** unknown officer identities are accepted.
- **A (F2), physical:** enabled → accepted; restart disabled → resume holds the case at
  OWNERSHIP with an `OWNERSHIP_INCOMPLETE`/`OWNERSHIP_DENOMINATOR_REQUIRED` exception. Restart
  enabled again: `poc_basis_accepted` = true and readiness blockers = `[]`, but the case stays
  `WAITING_FOR_REVIEW`/OWNERSHIP with the hold active. Resume does not clear it, and target
  confirmation returns `409 ZERO_TOUCH_TARGET_CONFIRMATION_NOT_ALLOWED`.
- **C (F3):** with document bindings made non-current, `get()` returns None, yet
  `poc_basis_accepted(record)` returns True.

The ordinary in-memory suite cannot share a bundle across two `create_app` calls ("cannot
rebind a populated reconciliation repository"). That is why probe A and the implementer's
restart proof need physical Mongo.

**F2 — Medium (non-blocking, recommended). Re-enabling after a restored hold leaves the case
stuck with contradictory status.**
- `_recover_obsolete_registry_ownership_locked` raises the ownership hold while the analysis
  is not accepted (`zero_touch_orchestration.py:2867-2883`). Nothing resolves that hold once
  the authority is current again.
- `_advance_locked_impl` returns while exceptions are active (`:2957-2960`).
- Ownership exceptions cannot be resolved generically. They need replacement evidence
  (`:2457-2461`), and Option B refuses keeping or redeclaring the POC links.
- Recovery therefore needs a different manual declaration, which replaces the POC basis, or
  a document/identity reload.
- Meanwhile the header shows "Ownership calculated — POC basis accepted." It overrides
  `stageNeedsAttention(["OWNERSHIP"])` (`CaseDetail.tsx:1299-1302`).
- The behaviour is fail-closed and no guardrail requires re-enable recovery. However, the
  implementer report says "re-enabling restores acceptance" (line 134), and the physical test
  checks only the flag after re-enabling (`test_recursive_ownership_real_mongo.py:490-493`).
- Recommendation: either treat an ownership hold bound to the same `ownership:{id}:{version}`
  as obsolete when the authority is current, or state the limitation in the demo guide and
  the decision ("onboard a new case").

**F3 — Low.** `poc_basis_accepted` checks identity currency but not document-binding
currency (`ownership_analysis.py:791-805`). It relies on callers passing `get()` output,
which returns None for stale bindings (`:1720-1729`).
- Readiness, zero-touch and GET use `get()`, so readiness is unaffected.
- `POST …/ownership/analyze` (`main.py:3131-3155`) passes `analyze()` output. That returns a
  terminal record with only an identity check (`ownership_analysis.py:1276-1297`), so it can
  report `poc_basis_accepted: true` for an analysis that GET treats as not loaded. The
  frontend `analyzeOwnership` (`api.ts:972`) is used in `App.tsx`.
- Recommendation: include the document-binding check in the authority.

**Test quality.**
- The mutation suite asserts `eligible_poc_acceptance(...) is None` independently of the
  fingerprint, so each eligibility clause is genuinely exercised.
- The P2 binding-change unit test proves the fingerprint, but not the real document-change
  mechanism (stale `get()`). That mechanism is older and covered elsewhere.
- The CaseDetail header has no unit test (disclosed by the implementer).

## 5. Code and Architecture Review

- There is one readiness authority on the existing ownership owner and no second owner.
  Persisted acceptance is audit only, and runtime authority is composition-scoped. The
  ledger, CAS and no-replay paths are unchanged.
- `len(codes) != len(issues)` is sound:
  - issues are appended per cause, with no de-duplication by code;
  - the one collapsed block (`ownership_analysis.py:1580-1632`) can, under the all-ROLE
    evidence constraint, only be caused by the roles themselves (CONFLICT, unbound, unsupported
    activity, units and unquantified all need other evidence kinds or a `None` entity);
  - a second `UBO_REVIEW_REQUIRED` from a document discrepancy is caught twice.
- `ownership_version = version + 1` matches both repositories' `expected + 1` and the terminal
  immutability rule (REVIEW_REQUIRED records cannot be re-saved).
- The fingerprint field set omits only derived or volatile fields: `tagging` (derived from
  evidence), events, times, version, state and correlation. No ownership model has
  `exclude=True` fields. Mongo stores datetimes as ISO strings and Decimals as strings, so the
  round trip is exact (proven physically).
- Validators: the record and the snapshot bind `analysis_id`, REVIEW_REQUIRED, the hybrid
  classification and no receipt; the record also binds `case_id`.
  `OwnershipPocAcceptance` enforces the policy literal, UTC, sorted unique codes ⊆ the POC
  set ⊇ the required codes, and roles ⇔ `UBO_REVIEW_REQUIRED`.
- Minor design note: if declarations were ever to explain the roles (so no
  `UBO_REVIEW_REQUIRED`), the case would become ineligible. That is fail-closed and
  irrelevant for Garden.
- **F4 — Low (owner decision).** An accepted case still shows the U1–U4 heading "Meets the
  threshold on an assumed basis — review required" and the line "… do not clear ownership
  readiness" (`UboSummary.tsx:4,39`). It is literally true but sits beside "POC basis
  accepted". The implementer disclosed it.
- **F5 — Info (pre-existing, out of scope).** Review & Send's "N provisional candidate(s)"
  (`ReviewAndSend.tsx:458`, since #64) counts all candidates. An accepted Garden case, now
  confirmable, reads "4 provisional candidate(s)" while the snapshot carries 0.
- **F6 — Info (residual, not exercised).** Between the confirmation freeze and the first
  write, `submit` checks only snapshot currency and confirmation validity
  (`clm_orchestration.py:633-645`), not the POC authority. A crash in that window followed by
  a disabled restart could still send the confirmed frozen package. This matches existing
  frozen-review semantics. Owner awareness only.
- Presentation delta: `entityLabel`, `calculatedForVerification` and the assumed-basis
  helpers are presentation only and read only backend values. There is no new coupling. No
  defect found.

## 6. Security Review

No security finding.
- No secret, credential, URI or PII was added.
- The acceptance exposes a UEN that is already present, hashed role evidence ids and a
  sha256 digest.
- There is no new logging. RBAC and team scope are unchanged.
- The setting cannot be enabled outside the Mock hybrid lane: the settings validator and the
  service constructor both refuse it.
- A corrupted policy id fails closed (`PersistenceDataInvalidError`).
- The frontend has no authority: it only displays the backend flag.

## 7. Required Fixes

- **R1 (F1).** Make D1=B match the owner guardrail. Choose one:
  - (a) Bind the four known Garden role evidence identities (for example the expected
    `evidence_id`s or officer ids) and exclude `CEASED` roles. Add identity-swap and ceased-role
    mutation tests. Align the offline fixture under owner authority.
  - (b) Obtain an explicit owner ruling that shape binding is intended. Then correct
    `DECISION_LOG.md:628-635`, `OWNERSHIP_UBO_PROFILE.md:431-433` and the handoff wording to
    state that role identities are not pinned and that ceased roles are counted.

  Either path changes reviewed content and needs a focused re-QG.

Recommended, non-blocking: F2 (code or documented limitation, and correct the report claim),
F3 (add the document check to the authority), F4 (owner wording decision). F5 and F6 are
owner awareness only.

## 8. Readiness

- **Stage 3:** FAIL for tree `08c5ad4cba4ff120f92d5e9b7a4e8fa5c366d2d8`. Not ready for
  publication. Next authorized action: bounded remediation of R1 (and optionally F2/F3), then
  a fresh focused independent re-QG.
- The presentation delta (`ff8f7ab` → `97fcc8c`) found no defect and needs no rework, but
  this verdict covers the combined tree only.
- **Real ACRA / GoldTier:** unchanged and not claimed. Mock and offline evidence only; no
  Live or Sandbox call was made.

## 9. Git Status

- Branch `feat/sim-lim-acra-ownership-followthrough-20261024`, HEAD `ceefe1e`.
- 55 tracked files modified. Three task-owned untracked product files. Untracked
  `.ai-pipeline/reports/*`. Nothing staged.
- My only repository write is this report. Probes, junit files, logs and temporary indexes
  are under the scratchpad `qg_d082\`. One mypy cache went to scratch.
- No implementation fix, commit, push, stash, branch change, install, merge or next phase
  occurred.
- `.env` was not opened. No ACRA or GoldTier host was called. Ports 8791 and 5791 were not
  touched.
