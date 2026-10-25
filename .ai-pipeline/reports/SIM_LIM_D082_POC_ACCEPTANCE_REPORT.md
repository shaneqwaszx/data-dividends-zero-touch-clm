# D-082 opt-in POC ownership acceptance — implementer report

Owner direction, 2026-10-24: "Remove Unnecessary Manual Ownership Verification in Approved
POC Lane". Owner decisions: D1 = B, D2 = keep REVIEW_REQUIRED/INDETERMINATE, D3 = opt-in
setting (default off), D4 = extend unreleased envelope 14. This report also covers the
owner design-review guardrails (P1 ×3, P2) and the owner wording change (remove "UBO
classification remains review-required…").

- Worktree `C:\Users\shane\Desktop\claude-worktrees\sim-lim-acra-ownership-followthrough-20261024`.
- Branch `feat/sim-lim-acra-ownership-followthrough-20261024`.
- HEAD = BASE = `origin/main` = `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322`. Uncommitted.
- **Candidate product tree `08c5ad4cba4ff120f92d5e9b7a4e8fa5c366d2d8`.** It is built from a
  temporary index: `read-tree HEAD`, `add -u`, plus the three new files
  `apps/backend/tests/test_poc_ownership_acceptance.py`,
  `apps/frontend/src/pages/UboSummary.test.tsx` and
  `apps/frontend/src/pages/ownershipAssumedBasisFixture.ts`.
- The D-082 delta is measured from the cleanup tree `97fcc8c…` (24 files, +1519/−22). The
  U1–U4 and structure-cleanup delta (`ff8f7ab…` → `97fcc8c…`) has never been independently
  gated, so it is in scope for the QG.
- No commit, push, PR or merge.

## 1. Policy decision as implemented

- **Setting.** `ACRA_MARKETPLACE_POC_OWNERSHIP_ACCEPTANCE`, `disabled` (default) or
  `accept_eligible_poc`.
  - The settings validator rejects `accept_eligible_poc` unless the connector is
    `api_marketplace_mock` with `hybrid_direct_overlay`.
  - `OwnershipAnalysisService(poc_acceptance_enabled=True)` raises without a hybrid overlay
    catalogue.
  - Composition passes `hybrid and setting == accept_eligible_poc`.
- **Record.** `OwnershipPocAcceptance` (domain, frozen, `extra=forbid`) is stored as
  `OwnershipAnalysisRecord.poc_acceptance` and in prior snapshots. Its fields:
  - policy literal `D082_HYBRID_POC_EQUAL_UNITS_V1`, and a UTC `accepted_at`;
  - `case_id`, `analysis_id`, `ownership_version`;
  - `identity_registration_number`, `identity_correction_version`;
  - `overlay_scenario_id`;
  - sorted `accepted_issue_codes`, a subset of the three POC codes that always contains
    DENOMINATOR and SYNTHETIC;
  - sorted `poc_relationship_ids`;
  - sorted `descriptive_role_evidence_ids`, non-empty if and only if UBO_REVIEW_REQUIRED is
    accepted;
  - `basis_fingerprint`, a sha256 over every eligibility input.

  Validators on the record and the snapshot bind it to its own analysis id and case, to the
  `REVIEW_REQUIRED` state and the hybrid classification, and to no manual receipt.
- **Creation.** Acceptance is set only inside `analyze()`, on the new analysis's
  REVIEW_REQUIRED write. That event keeps type and outcome REVIEW_REQUIRED, with code
  `OWNERSHIP_POC_BASIS_ACCEPTED`.
  - State, issues, evidence, candidates, Decimal values and classifications are unchanged.
  - Terminal analyses are never re-analysed.
- **Eligibility** (`eligible_poc_acceptance`, fail-closed). All of these must hold:
  - the whitelisted `GARDEN_DIRECT_OVERLAY_V1` scenario, rooted at 11111999A;
  - provider `ACRA_REGISTRY_ACQUISITION`/MOCK and the hybrid classification;
  - a legal form that is set and not OTHER; no error; no manual receipt; no supplemental
    relationships;
  - complete topology with no unresolved persons;
  - every retained issuer POC-distributed with a lookup, and the POC edge parents exactly
    those issuers;
  - only overlay or POC links, and only overlay/LOCAL supplemental evidence;
  - no document discrepancy that needs review;
  - no duplicate issue codes, and codes within the POC set while including DENOMINATOR and
    SYNTHETIC;
  - candidates present, every classification REVIEW_REQUIRED or INDETERMINATE, and every
    assumed-basis result MET or NOT_MET;
  - **D1 = B:** evidence either empty (and then no UBO_REVIEW_REQUIRED) or exactly 4
    distinct-party `ROLE`/`OWNER`/`OFFICERS`/`ACRA_REGISTRY_ACQUISITION`/`MOCK` items bound to
    11111999A, with UBO_REVIEW_REQUIRED present.
- **Authority** (`OwnershipAnalysisService.poc_basis_accepted`). It returns true only when
  all of these hold:
  - the running composition enables the policy, with a hybrid overlay;
  - the parent case identity is current;
  - `poc_acceptance_current(record)`: state REVIEW_REQUIRED, version equal to the bound
    `ownership_version`, and recomputed eligibility equal to the stored acceptance (so any
    content, identity, issue, evidence or fingerprint change fails).

  The authority is consulted by:
  - CLM `_evaluate_readiness`, via both callers including `_start_submission` inside the
    CLM lock: ownership READY with the analysis id as reference;
  - zero-touch OWNERSHIP stage completion: `OWNERSHIP_AUTOMATED`, code
    `OWNERSHIP_POC_BASIS_ACCEPTED`, no exception;
  - zero-touch restoration (`_recover_obsolete_registry_ownership_locked`): no ownership
    hold re-raised while accepted;
  - the API (`poc_basis_accepted` on the analyze and get responses, plus `poc_acceptance`
    for audit).
- **Persistence.** Envelope 14 is extended with the optional field. The exact v13 guard
  (`reject_share_class_legacy_fields`) rejects a non-null `poc_acceptance` on current and
  prior analyses.
- **UI** (backend flag only):
  - Ownership & UBO header: "Ownership calculated — POC basis accepted."
  - Structure banner (neutral style), the POC and Marketplace Mock workaround disclosure:
    "Ownership percentages use retained ACRA Marketplace Mock shareholder quantities and
    declared POC assumptions, accepted for readiness by the opt-in D-082 demonstration
    policy. Official share denominators and share-class rights remain unverified. This is
    not verified ownership or a legal UBO determination. Target confirmation is still
    required before any GoldTier send."
  - Explorer state: "Calculated — POC basis accepted".
  - Explorer summary: "Calculated on the accepted POC basis."
  - The red UBO review warning is not rendered for an accepted case. Per the owner, the
    "UBO classification remains review-required…" text was removed.
  - The candidate cards still show the backend classification `REVIEW_REQUIRED`, and the
    manual form stays available.

## 2. Before / after readiness (fresh live Garden case on the Marketplace Mock)

| | Before (setting disabled) | After (`accept_eligible_poc`) |
|---|---|---|
| Ownership state | REVIEW_REQUIRED | REVIEW_REQUIRED (unchanged) |
| Issues | DENOMINATOR, SYNTHETIC, UBO_REVIEW_REQUIRED | identical codes and messages |
| Candidates | 4, REVIEW_REQUIRED/INDETERMINATE, 0 provisional | identical (ABCD123 51.13636375, LIM CHOON HUAT 37.5, TAN/EFGH 5.681818125) |
| Readiness blockers | `OWNERSHIP_REVIEW_REQUIRED` | `[]`; ownership READY |
| Zero-touch | WAITING_FOR_REVIEW at OWNERSHIP, `OWNERSHIP_INCOMPLETE` | WAITING_FOR_REVIEW at READINESS, `TARGET_CONFIRMATION_REQUIRED` only |
| CLM / GoldTier | blocked, no submission | `READY_FOR_MOCK_SUBMISSION`, no submission, no GoldTier result until explicit confirmation |
| Provider calls | — | 1 token POST + 4 GETs (fresh process cache) |

## 3. The four owner guardrails

**P1 — runtime policy revocation.** A persisted acceptance grants nothing by itself.
Readiness asks the ownership service, which needs its own composition-time opt-in in the
Mock hybrid lane. Policy authority is the literal policy id: a corrupted id fails
persistence validation.
- `test_readiness_authority_belongs_to_the_current_composition` (shared repositories):
  - the enabled composition gives READY;
  - each of disabled-hybrid, disabled-legacy-lane and local-mock compositions gives
    `OWNERSHIP_REVIEW_REQUIRED`, with the stored record unchanged and still current;
  - re-enabling gives READY again.
- Physical Mongo: `test_poc_acceptance_survives_restart_but_grants_readiness_only_while_enabled`
  runs real app restarts on a disposable database:
  - enabled → accepted, no blockers;
  - restart disabled, legacy lane, or local Mock → the audit record is byte-identical in
    Mongo, `poc_basis_accepted` is false, `OWNERSHIP_REVIEW_REQUIRED` returns, target
    confirmation is refused with 409, and there is no GoldTier result or submission;
  - resume while disabled restores the ordinary OWNERSHIP hold (`OWNERSHIP_INCOMPLETE`) and
    confirmation is still refused;
  - re-enabling restores acceptance;
  - a corrupted policy id, and the exact v13 envelope, both fail closed with
    `PersistenceDataInvalidError`.

**P1 — Garden official role evidence.** D1 = B applies only to `GARDEN_DIRECT_OVERLAY_V1` at
11111999A and the exact four known `OFFICERS` `ROLE = OWNER` records.
- The roles stay in `evidence`; their ids are recorded on the acceptance; they create no
  edge, party or candidate; UBO_REVIEW_REQUIRED stays on the analysis.
- `test_the_officer_roles_stay_retained_and_unreconciled` covers that retention.
- 20 parametrized mutations in `test_only_the_known_garden_roles_and_poc_markers_are_accepted`
  all fail closed:
  - a fifth, non-owner, other-entity, local-source or other-operation role, or only three
    roles;
  - share-unit evidence;
  - a contradiction, a second review cause, an unresolved corporate holder, or a missing
    synthetic marker;
  - a document discrepancy;
  - another scenario or root, incomplete topology, or a D-079 issuer;
  - a Live provider or a non-overlay link;
  - an uncalculated person or a provisional classification.
- The five-layer journey and the D-079 refusal journey stay blocked with the policy enabled.

**P1 — downstream GoldTier semantics.** Traced through `_start_submission`,
`_build_snapshot` and `RelatedPartySubmissionPreparation`.
- Only `PROVISIONAL_UBO_CANDIDATE` ids enter the snapshot. Accepted cases keep
  REVIEW_REQUIRED/INDETERMINATE, so `provisional_ubo` is count 0 with no ids, and
  related-party preparation is count 0 with no ids.
- `ownership_reference` is (analysis id, version, `REVIEW_REQUIRED`).
- `build_submission_input` is built from the case alone, so no UBO payload exists or was
  added.
- `test_a_confirmed_mock_send_carries_no_assumed_basis_ubo_and_never_replays`:
  - the explicit confirmation completes the Mock send with one execution;
  - the ownership record is unchanged;
  - a repeated confirmation is refused with 409, with no new execution.
- Final review (visual smoke) still shows "Confirm and send to Mock GoldTier", which was
  not clicked.

**P2 — freshness and persistence.**
- **Binding.** Case, analysis id, ownership version, identity number and correction
  version, scenario, policy, codes, link ids, role ids and the fingerprint.
- **Invalidation** (`test_the_acceptance_is_bound_to_its_case_version_content_and_identity`).
  The acceptance becomes not current on any of: version+1, another analysis id, an identity
  correction, a changed document binding, a tampered fingerprint or version, state
  ANALYZED, a changed link percentage, or a removed acceptance.
- **Creator replacement.** It creates a new ANALYZED manual analysis with no acceptance; the
  old acceptance stays in `prior_analyses`. D-081 Option B still refuses `CURRENT_EVIDENCE`
  and unchanged redeclaration (409) on an accepted case.
- **Document replacement.** A document without ownership observations leaves the same bound
  analysis accepted (its binding is unchanged), and the old confirmation becomes stale
  (409). A binding change makes `get()` stale, and reload builds a fresh record with no
  acceptance.
- **Existing cases.** Existing review cases are not accepted when the flag is enabled
  (`test_enabling_the_policy_never_accepts_an_existing_review_case`).
- **Schema.** Envelope 14 is still unreleased, so no released v14 data exists, and the field
  is optional (pre-D-082 v14 documents read as `None`).
  - Exact v13 rejects a non-null acceptance on current and prior analyses; an explicit null
    keeps the legacy meaning.
  - A v13 reader (main) already rejects every v14 envelope (fail-closed rollback).
  - `test_the_acceptance_round_trips_in_schema_fourteen_and_never_in_schema_thirteen` plus
    the physical test cover this.

## 4. Changed files (D-082 delta)

- **Backend:**
  - `app/config.py` (setting + validator), `app/composition.py` (wiring);
  - `app/domain/ownership.py` (model, constants, binding validators);
  - `app/services/ownership_analysis.py` (eligibility, fingerprint, authority, analyze hook,
    snapshot copy);
  - `app/services/clm_orchestration.py` (readiness parameter, both callers);
  - `app/services/zero_touch_orchestration.py` (stage completion, restoration);
  - `app/api_models.py`, `app/main.py` (response fields, analyze/get);
  - `app/persistence/models.py` (v13 guard).
- **Tests:** `tests/test_poc_ownership_acceptance.py` (new, 34 tests) and
  `tests/test_recursive_ownership_real_mongo.py` (+1 physical test).
- **Frontend:** `src/types.ts`, `src/pages/OwnershipStructure.tsx`,
  `src/pages/OwnershipPathExplorer.tsx`, `src/pages/UboSummary.tsx`,
  `src/pages/CaseDetail.tsx` (ownership header string only) and
  `src/pages/OwnershipStructure.test.tsx` (+2 tests).
- **Config/docs:** `.env.example`, `docs/decisions/DECISION_LOG.md` (D-082 plus a D-081
  narrowing note), `docs/contracts/OWNERSHIP_UBO_PROFILE.md`, ADR-013,
  `docs/ARCHITECTURE.md`, `docs/PROJECT_STATE.md`, `docs/demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md` §8.
- Not touched: the AI Assistant, GoldTier connectors/mapping, discovery, the
  connector/cache, the engine/comparator and the Option B logic.

## 5. Evidence (on the working tree whose product content is `08c5ad4c…`, except where noted)

| Check | Result |
|---|---|
| Visual smoke **before** focused tests (owner order), live Marketplace Mock, setting enabled | 11/12 scripted checks PASS. The 12th was the script's wrong selector for the header; a read-only retake confirmed the header text. Screenshots in `smoke_d082\screenshots\` and, after the wording change, `smoke_d082\screenshots_v2\`. Provider log: 1 token + 4 GETs, unchanged by the retakes |
| Focused backend `test_poc_ownership_acceptance.py` | 34 passed |
| Physical D-082 restart test (disposable mongo:7 :27094) | passed |
| Full backend (4 chunks, junit) | 3214 tests: 3037 passed, 176 skipped (physical lanes skip without a URI), 1 failed. The failure was `test_phase13_demo_scripts.py::test_http_seeder_runs_twice_against_one_live_memory_backend`, a live HTTP read timeout while Vitest and the CI lanes ran in parallel; rerun alone it passed. The run started before the last test-only edits (document-replacement test and wording); those files were rerun after |
| Physical Mongo full suite (`scripts/run_physical_mongo_tests.py`, disposable mongo:7 :27094) | PASSED: 25 suites, 170/170 (`d082_physical\run.log`) |
| Full browser E2E (`--keep-going`, ports 9300/4600, `CLM_E2E_SYNTHETIC_MONGO_PORT=27094`) on the frozen tree | 115/115 PASS (`d082_e2e\run.log`, `d082_e2e\results.json`); tree recomputed afterwards: still `08c5ad4c…` |
| Frontend typecheck / Vitest / build | PASS / 64 files, 1069 tests PASS (after the wording change) / PASS (chunk-size advisory) |
| CI unittest lanes (incl. `tests/contract` 44, pre-PR 64, dev_context 55) and repository checkers | all OK |
| ruff check backend + scripts | PASS. Format flags on 3 CRLF files are pre-existing at HEAD; new files are formatted |
| `git diff --check`; untracked Markdown | clean |
| dev_context routine benchmark | 30.047% (≥ 30.0; headroom 0.047 pp) |

## 6. Change declarations

- **API/type:** yes. Additive response fields `poc_acceptance`, `poc_basis_accepted`; a
  frontend type.
- **Schema:** yes. An optional field in unreleased envelope 14; the exact-v13 guard.
- **Connector:** no.
- **Configuration:** yes. A new opt-in setting, default off.
- **Business rule:** yes (D-082 candidate, owner-authorized), at the readiness boundary only.
- **Mapping:** no.
- **Auth/security:** no RBAC change. Acceptance is backend-authoritative and the frontend
  only displays it.
- **Architecture:** a new readiness-authority method on the existing ownership owner. There
  is no second owner.
- **Provider status:** unchanged (Mock; never Live).
- **Runtime behavior:** unchanged with the default. With the opt-in, eligible new Garden
  analyses reach target confirmation.

## 7. Notes and open items

- The owner-approved U1–U4 explanation under "Meets the threshold on an assumed basis —
  review required" still says the matches "do not clear ownership readiness". That stays
  literally true (the D-082 policy clears readiness, not the matches), but next to an
  accepted case it may read as contradictory. It is unchanged pending an owner decision.
- The CaseDetail ownership header string has no dedicated Vitest test. It is covered by the
  visual smoke and by E2E only where exercised.
- The live smoke backend (8791, memory mode, setting enabled) and Vite (5791) are still
  running for owner review.

Next authorized action: fresh independent Quality Gate on `08c5ad4c…`, then **OWNER REVIEW /
PUBLICATION AUTHORIZATION PENDING**.

---

## R1 remediation and F2–F6 (owner decisions, 2026-10-24)

The fresh independent QG on `08c5ad4c…` returned **FAIL (R1)**. That report,
`SIM_LIM_D082_POC_ACCEPTANCE_QUALITY_GATE.md`, is preserved unchanged. The owner then made two
decisions:
- "AUTHORIZE EXACT ROLE-ID BINDING VIA ENVIRONMENT CONFIGURATION".
- "Option 1: EXACT OBSERVED SET". The live Mock shows exactly 4 Owner role records for
  11111999A: 3 current and 1 ceased. The earlier "four current" premise came from my
  investigation, which omitted the roles' status.

This section supersedes the D1=B text in §1, §3 and §4 above. The candidate tree is the new
frozen tree reported in §R6.

### R1. Exact configured identity-match rule

Garden's role exemption (`eligible_poc_acceptance`) holds only when every one of these is true:
1. **Opt-in and lane.** The opt-in POC policy is enabled in the Mock hybrid lane, and the
   protected allowlist parsed successfully. `parse_poc_officer_role_allowlist` returns
   nothing for:
   - a missing key or allowlist;
   - a key shorter than 32 characters;
   - any entry not matching `^[0-9a-f]{64}=(CURRENT|CEASED)$`;
   - duplicate digests.

   Composition passes the allowlist only under the opt-in.
2. **Scenario and evidence shape.** The scenario is `GARDEN_DIRECT_OVERLAY_V1` at
   11111999A, and the analysis evidence is exactly the officer role records. Each one is
   `ROLE`/`OWNER`, `OFFICERS`, `ACRA_REGISTRY_ACQUISITION`/`MOCK`, and bound to 11111999A,
   with distinct officers and distinct evidence ids.
3. **Statuses.** Exactly **3 current and 1 `CEASED`**. Any other status refuses.
4. **Stable identity.** Each evidence id equals the registry adapter's stable id
   `e-` + sha256(`<officer_id>:ROLE`)[:48]. A test asserts that equality with the adapter
   function.
5. **Exact set match.** The **set** of (`HMAC-SHA256(key, evidence_id)`, status) equals the
   configured set, compared in canonical sorted form with `hmac.compare_digest`. Response
   order does not matter, and any substitution, addition, removal or status change refuses.

The acceptance no longer stores role ids. It stores only
`descriptive_current_role_count` = 3 and `descriptive_ceased_role_count` = 1, so no identifier
or digest is on the record, the API or the browser.

Readiness revalidates all of this on every call. Changing or removing the allowlist revokes
the acceptance just as disabling the flag does.

The ceased role is history only. Roles never create edges, parties or candidates, so
percentages, UBO calculation and classification are identical with the role ceased or
current (`test_the_ceased_role_never_changes_calculated_ownership`).

### R2. Proof that unknown-role substitution now fails

- **QG probe B** (all four identities replaced, observed shape kept: 3 current, 1 ceased) →
  `None`. This is the mutation "four unknown identities in the observed shape".
- **Other mutations that now refuse:**
  - one substituted identity;
  - the ceased role becoming current;
  - the ceased status on a different role;
  - a duplicated role record;
  - an evidence id not derived from its officer;
  - an unknown role status;
  - a fifth role, only three roles, or no roles;
  - a non-owner role, another entity, a local source, or another operation;
  - share-unit evidence.

  All 29 mutations pass.
- **Configuration and identity mismatches through real analysis** (12 cases): missing key,
  missing allowlist, short key, different key, malformed status, malformed digest, duplicate
  entry, missing role, additional role, substituted identity, status on another role, and
  all-current. Each leaves the state REVIEW_REQUIRED with no acceptance, and leaves the
  calculations, issues and four role records unchanged.
- **Fixture status variants:** none ceased, role 1 ceased, or roles 3 and 4 ceased → refused.
- **Response order:** the officers reversed in the provider response → still accepted.

### R3. Configuration and secret handling

- **Settings.** `ACRA_MARKETPLACE_POC_OFFICER_ROLE_KEY` and
  `ACRA_MARKETPLACE_POC_OFFICER_ROLE_ALLOWLIST` are `SecretStr`, default `None`, and
  backend-only. `.env.example` shows only names and placeholder syntax; a test asserts both
  names have empty values.
- **No exposure.** `PocOfficerRoleAllowlist` fields use `repr=False`. Parse failures never
  echo values. A test (`test_protected_role_values_are_never_exposed`) asserts that the key
  and digests appear in none of: the settings repr or dump, the allowlist repr, the
  ownership response, or the zero-touch summary.
- **Your protected values.** They were prepared from the evidence the running smoke server
  already held, with **no new ACRA request** (the provider log stayed at 1 token + 4 GETs).
  A fresh random 32-byte key and four HMAC digests (3 `CURRENT`, 1 `CEASED`) were written
  only to a protected local file outside the repository (location given to the owner
  directly and withheld here). Nothing was printed. The backend parser accepts it.
- **Leak scan.** Neither the key, the digests, nor the four live unsalted role ids appear
  in any of the 2269 tracked or untracked repository files, or in any scratch evidence
  artifact (`.json/.md/.log/.txt`). The temporary id file used for that scan was deleted.
- **Tests** use only synthetic identities (`SYNTHETIC-ROLE-n`) and a synthetic test key.

### R4. F2–F6 dispositions

| Finding | Disposition |
|---|---|
| F2 toggle consistency | Fixed in `_recover_obsolete_registry_ownership_locked` and `_is_obsolete_registry_ownership_exception`. **Disable + resume:** an OWNERSHIP checkpoint completed on a no-longer-current acceptance is treated as unproved and rebuilt; the ordinary hold (`OWNERSHIP_INCOMPLETE`) is raised and every earlier `target-confirmation:` hold is withdrawn. **Re-enable + resume:** a hold raised on the same analysis that is now accepted is obsolete and cleared, and the case returns to READINESS/`TARGET_CONFIRMATION_REQUIRED` with no blockers. Nothing advances or dispatches while authority is withdrawn, and a submitted or attempted target remains frozen. Tests: in-memory `test_toggling_the_policy_keeps_readiness_and_the_workflow_consistent`, plus the physical restart test with real app restarts (off → hold only; on → target confirmation). |
| F3 document binding | Fixed earlier: the authority also requires the current document binding. |
| F4 wording | On accepted cases only: heading "Meets the threshold on an assumed basis"; the explanation keeps the POC disclosure ("not verified legal UBO determinations or provisionally classified UBOs") and drops "do not clear ownership readiness". Non-accepted cases are unchanged. The banner discloses the 3 current / 1 ceased role records as descriptive context for this named exception and says they do not corroborate the synthetic links. |
| F5 Review & Send | "Ownership: 4 natural person(s) assessed, 0 provisional UBO candidate(s), 2 assumed-basis threshold match(es), …". The snapshot is unchanged. |
| F6 pre-write revalidation | `ClmOrchestrationService.submit`, inside the existing `before_first_write` gate: a snapshot frozen on a POC acceptance (`ownership_reference.status == REVIEW_REQUIRED`) needs `poc_basis_accepted` immediately before the first irreversible write, otherwise `CLM_NOT_READY` with no target operation. `ANALYZED` dispatch and recovery of an attempted write (`retained_submission_is_current`) are unchanged. Test `test_revoking_the_policy_after_the_freeze_blocks_the_first_target_write` revokes between freeze and submit: no attempted operation, no GoldTier result, technical failure `CLM_NOT_READY`. |

The "Ownership calculated — POC basis accepted" header and the earlier wording change
stand. No AI Assistant, GoldTier mapping, connector, discovery, engine, POC distribution or
Option B code changed.

### R5. Updated test results (on the working tree whose product content is the frozen R6 tree)

| Check | Result |
|---|---|
| Focused `test_poc_ownership_acceptance.py` | 64/64 pass (junit `r1_focused.xml`): 29 mutations, 12 configuration/identity mismatches, order independence, ceased-role arithmetic, protected-value exposure, F2 toggle, F6 pre-write refusal, and the earlier D-082 journeys |
| Physical D-082 restart test, then full physical suite (disposable mongo:7 :27094) | pass; full runner PASSED, 25 suites, 170/170 (`r1_physical\run.log`) |
| Full backend (4 chunks) | 3244 tests: 3068 passed, 176 skipped (physical lanes skip without a URI), 0 failed (`r1_backend\`) |
| mypy `app` | no issues in 129 files |
| Frontend typecheck / Vitest / build | pass / 64 files, 1070 tests pass / pass |
| CI unittest lanes and repository checkers | 16/16 exit 0 |
| ruff (backend, as CI runs it); `git diff --check` | pass; clean |
| dev_context routine benchmark | 30.047% (≥ 30.0) |
| Full browser E2E (`--keep-going`, 9300/4600) | 114/115. `authenticated-zero-touch.e2e.ts:1248`, a non-Garden document-review journey with D-082 not enabled, failed on a Chromium `Network.getResponseBody: No resource with given identifier found` transient (`r1_e2e\run.log`). The isolated rerun of that selector **passed** (`r1_e2e\rerun.log`). A fresh full run is in progress at hand-off (see R7) |
| Protected-value leak scan | key, digests and live unsalted role ids: 0 hits in 2269 repo files and in scratch evidence artifacts |

The live Garden acceptance was not re-smoked with the R1 code. It needs a fresh case on the
live Marketplace Mock (1 token + 4 GETs). That is offered to the owner as a bounded,
authorization-gated step and was not performed.

### R6. Candidate tree

- Revised frozen product tree: **`5e7ca651e1903c09947bf8d9d162cf7d2ff554cd`**. It was built
  with a temporary index (`read-tree HEAD`, `add -u`, plus the three new files) and
  recomputed after E2E.
- Previous failed QG tree: `08c5ad4c…`. Its report's blob `2ac85dc107822764376af61c90f501f33f4f5b89`
  is unchanged.

### R7. N1/N2 follow-up after the re-QG (PASS WITH NON-BLOCKING FINDINGS on `5e7ca651…`)

The re-QG report `SIM_LIM_D082_POC_ACCEPTANCE_RE_QUALITY_GATE.md` (blob `b8c711cd…`) is preserved
unchanged. Two of its findings conflicted with the owner's "preserve unrelated functionality"
and truthful-status requirements, so they were addressed:
- **N1.** The F2 rebuild (`poc_revoked`, folded into `unproved_ownership_checkpoint`) now
  applies only to an analysis carrying a POC acceptance (`ownership.poc_acceptance is not
  None`). Every other REVIEW_REQUIRED analysis keeps the pre-D-082 restoration. New test:
  `test_a_non_poc_interrupted_manual_replacement_keeps_its_existing_recovery` (the reviewer's
  probe: OWNERSHIP stays completed, no target call).
- **N2.** The CaseDetail header shows "Ownership calculated — POC basis accepted." only when no
  active exception or intervention holds the OWNERSHIP stage. Otherwise it shows the ordinary
  ownership-attention status.
- **N3 and N2 disclosure.** D-082 now states that the F6 refusal is the existing terminal
  technical failure (not auto-resumed on re-enable), and that the stale hold clears via the
  existing resume operation. The demo guide names that operation.
- **Not changed (owner decision):** N4–N7 (informational).

Evidence on the revised frozen tree **`51ce37012d845e4545335b79e71754a87f09873a`**:

| Check | Result |
|---|---|
| Focused D-082 tests incl. N1 regression, F2, F6 | pass (65 tests in the file) |
| Full backend (4 chunks) | 3245 tests: 3069 passed, 176 skipped, 0 failed (`n1_backend\`) |
| mypy `app` | no issues in 129 files |
| Physical Mongo full runner | PASSED, 25 suites, 170/170 (`n1_physical\run.log`) |
| Frontend typecheck / Vitest / build | pass / 64 files, 1070 tests / pass |
| CI lanes and checkers | 16/16 exit 0 |
| Full browser E2E (`--keep-going`) | 113/115 (`n1_e2e\run.log`). Failed: `authenticated-zero-touch.e2e.ts:1248` (response-body race) and `slice-b-registry-demo.e2e.ts:122` (individual timeout). Isolated reruns: `:122` 2/2 pass. **Not a clean full pass.** |

**E2E `:1248` root cause (pre-existing on `main`).** The test registers `waitForResponse`
for the documents GET before `page.goto` to the same case URL. A documents response from the
page being replaced can therefore be matched and then evicted (`Network.getResponseBody: No
resource with given identifier found`).

Reproduction with the preceding lifecycle (`:1044` then `:1248`):
- current tree: 1 of 3 runs failed;
- an unmodified `git archive` export of HEAD/`main` `ceefe1e` (node_modules junction, removed
  afterwards; worktree dependencies verified intact): **3 of 5 runs failed** with the identical
  error.

Earlier full runs on this branch also showed it (114/115 and 113/115). The other two full-run
failures were individual timeouts (`ownership-document-streamline:79`,
`slice-b-registry-demo:122`), and each passed its isolated reruns (3/3 and 2/2). Hardening
`:1248` (for example registering the wait after navigation) is a separate test fix on `main`
and is outside this task.

### R8. Owner-authorized live Garden smoke with the protected allowlist (tree `51ce3701…`)

The owner authorized one bounded live Garden smoke on the Marketplace Mock: at most 1 token +
4 GETs, read-only after onboarding, no target confirmation. My own smoke backend was
restarted on 8791 (memory mode, opt-in setting on). It loaded the protected allowlist into
the process environment only; nothing was printed. One new Garden case was onboarded through
the UI.

- **Provider calls:** exactly **1 token + 4 GETs** (3 `entityBasicInformation`, 1
  `coShareholdersDetails`), all HTTP 200. Later read-only re-checks made no further calls.
- **Ownership:**
  - `REVIEW_REQUIRED`, with `poc_basis_accepted = true`.
  - The acceptance (policy `D082_HYBRID_POC_EQUAL_UNITS_V1`, scenario `GARDEN_DIRECT_OVERLAY_V1`,
    3 POC links) records **3 current, 1 ceased** roles, is bound to the current version, and
    carries no role-id field.
  - All 4 official role records are retained, 3 current and 1 ceased, each
    OFFICERS/ACRA_REGISTRY_ACQUISITION/MOCK/11111999A.
  - The issues are the three POC codes, unchanged.
  - Candidates unchanged: ABCD123 51.13636375, LIM CHOON HUAT 37.5, TAN WEI LING and EFGH2345
    5.681818125, all `REVIEW_REQUIRED`.
- **Readiness:** no blockers, and ownership is READY.
- **Zero-touch:** WAITING_FOR_REVIEW at READINESS, with only `TARGET_CONFIRMATION_REQUIRED`.
  The CLM status is `READY_FOR_MOCK_SUBMISSION`, there is no submission and no GoldTier
  result, and **Confirm and send to Mock GoldTier** is present and was not clicked.
- **UI:**
  - The header reads "Ownership calculated — POC basis accepted."
  - The banner discloses "(3 current, 1 ceased) … descriptive context for this named POC
    exception only. They do not corroborate the synthetic shareholder relationships."
  - The assumed-basis section is headed "Meets the threshold on an assumed basis", keeps the
    POC and not-verified disclosure, and has no "do not clear ownership readiness".
  - There is no red UBO review warning.
  - Review & Send reads "Ownership: 4 natural person(s) assessed, 0 provisional UBO
    candidate(s), 2 assumed-basis threshold match(es)".

  The first scripted UI pass flagged three checks because of selector issues in my own
  script (CSS uppercase seen through `innerText`, and text inside collapsed details). A
  read-only re-check with `textContent` on the same case passed all six, and the case stayed
  unsent.
- **Leak scan (counts only):** the 4 live role evidence ids, the 4 role party ids, the key and
  the 4 digests have 0 hits in the smoke results, backend log, provider log and the case page's
  visible text.
  - Repository: the evidence ids, key and digests have 0 hits.
  - One officer `party_id` already appears in six files unchanged from `main`
    (`apps/backend/app/connectors/garden_business.py`, two backend tests, two assistant
    fixtures, and an older tracked report). That is pre-existing Mock fixture data, not
    introduced or changed by D-082.
- **Artifacts:** scratchpad `smoke_d082\d082_r1_smoke_results.json`,
  `d082_r1_recheck_results.json` and `screenshots_r1\`. They hold counts and statuses only.
