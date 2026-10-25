# Quality Gate: D-087 (declared intermediate officer roles as POC descriptive context)

Reviewer: fresh, independent, read-only QG run (2026-10-25). The reviewer did not write this change.
Nothing in the worktree was edited, staged, committed, stashed, reset or cleaned. All scratch work is under `scratchpad\qg-d087\`.

## 1. Identity

| Item | Value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\generalized-poc-acceptance-int-20261025` |
| Branch | `feat/generalized-poc-acceptance-multilayer-20261025-int` |
| HEAD | `8451e2a70030f74c50d68194b060bf106aebe7b4` (PR #111 head; HEAD tree `758eff3`) |
| origin/main | `5de7f24c2dbf678bbb9de02ad627be777bc2f28c`. Fetched at the start and again at the end; it did not move. It equals the merge-base. |
| Delta | 13 uncommitted modified files, exactly those in `d087_paths.txt`. There are no untracked files and the real index is empty (0 cached). |
| Frozen tree | **`db56b8e104e5fbcbda955c089063ed221f75b51c` verified**. I used a copied index (`GIT_INDEX_FILE`) with `add --pathspec-from-file` and `write-tree`. I did this at the start and again at the end of the review, and got the same result both times. |
| EOL | `git diff --stat 8451e2a` and `--ignore-cr-at-eol` are identical: 13 files, +579/−112. There is no EOL churn. The "LF will be replaced by CRLF" warnings come from the working copy only. |
| Reviewed content | The tree `db56b8e` above, and nothing else. |

## 2. Checks

### Check 1: global bypass (critical)
Code review of `services/ownership_analysis.py::_undeclared_intermediate_roles`, `eligible_poc_acceptance` and `connectors/hybrid_ownership_overlay.py`:

- **No declaration means no acceptance.** `eligible_poc_acceptance` returns `None` when `scenario.poc_acceptance is None`. The scenarios as loaded at runtime are:
  - `FIVE_LAYER_MARKETPLACE_HYBRID_V1`: `poc_acceptance=None`.
  - `GARDEN_DIRECT_OVERLAY_V1`: declares no intermediate roles.
  - `OPQ_GARDEN_SIM_LIM_V1`: the only declaration, which is `(11111999A, {OWNER})`.
- **The five-layer fixture cannot become POC-ready.** It has no declaration, and its intermediate issuers are `LOCAL_SYNTHETIC_IDENTITY`, which the existing D-085 check rejects. The smoke artefact A confirms this: accepted=false, blocked at OWNERSHIP, aggregates unchanged.
- **Garden-root roles are untouched.** Discovery records have `depth>=1`, so the root's roles stay on the D-085 root-evidence path (`causes.unresolved_roles` / `DESCRIPTIVE_OFFICER_ROLES`). As a second layer, the scenario validator forbids naming the root, and the service rejects a record whose registration is the root.
- **Undeclared issuers and undeclared role kinds are blocked.** `descriptive_roles_of(issuer)` returns an empty set for any issuer that is not named. Any ownership-like role outside the named kinds blocks.
- **The scenario configuration is re-evaluated.** `poc_acceptance_current` recomputes eligibility against the composition's current catalogue. A changed or removed declaration therefore revokes the acceptance, and the fingerprint covers `discovery`.

Mutation testing used scratch copies of `apps/backend` under `qg-d087\mut\<id>\apps\backend`, with `PYTHONPATH=<copy>;<worktree root>`. Each run printed `app.__file__`, and each one pointed at its copy, as recorded in `mutation_results.txt`. The control copy passed 116/116. The full table is in section 3.

- The four requested mutants:
  - The `descriptive_roles_of` mutant (M01) is **killed**, by 4 parametrised role-kind cases.
  - The count-limit mutant (M04) is **killed**.
  - The root-check mutant (M02) and the assumption-check mutant (M03) **survive the committed suite**.
- **Why M02 and M03 survive.** Both are *equivalent under validated construction*:
  - `HybridOverlayScenario` rejects a root (or any non-scenario issuer) named in `descriptive_intermediate_roles`. Mutant M12 shows the tests kill the loss of that check.
  - `PocAcceptanceDeclaration` requires the assumption if and only if issuers are named. Mutant M13 shows the tests kill the loss of that check too.
  - So `descriptive_roles_of(root)` is always empty, and the role check (M01, killed) already blocks.
- **Probes against the surviving guards.** I wrote an extra QG-only probe, `qg-d087\test_qg_probe_guards.py`, run on scratch copies only. It builds declarations with `model_construct`, which bypasses the validators:
  - On the control copy, all 3 probes pass: root, non-scenario issuer and missing assumption are all blocked by the runtime guards.
  - On M02, M03 and M05, the matching probe fails (`probe_results.txt`).
  - So these runtime guards are live defence in depth that the committed suite never exercises on its own. That gap is finding F1 (P3).

**Conclusion:** a global bypass is not possible through any validated configuration. Every way of reaching acceptance requires a trusted catalogue declaration that names a non-root scenario issuer and a role kind. The guards that enforce this have killed mutants (M01, M11, M12, M13).

### Check 2: genuine evidence errors still block
- Focused run in the worktree, with `app.__file__` pointing at the worktree: `test_opq_garden_sim_lim_scenario.py`, `test_poc_ownership_acceptance.py` and `test_simulation_calculation_status.py` give **116 passed**.
- The D-085 suite still passes unchanged, including `test_genuine_defects_and_undeclared_causes_stay_blocking` and its parameters, ineligible journeys, document binding, identity/version binding, and revoke-after-freeze.
- New OPQ tests:
  - Tampered observations: LOCAL identity, PROVIDER_PARTIAL outcome, root registration, `None` registration, SANDBOX environment, non-OFFICERS operation, other provider, UNKNOWN status, 36 roles, and a duplicate record.
  - Revocation when a role changes.
  - Root contradictions, now run with Garden's officers present, which makes the test stronger than before.
  - Default-off, selector reverted, and policy disabled.
  - Policy withdrawal reinstates the OWNERSHIP hold.
- Mutants M04, M06 and M08–M10 are killed by the tamper test.
- M07 (identity-basis check) is equivalent. The existing `LOCAL_SYNTHETIC_IDENTITY` rejection covers it, as does the domain validator that roles require `OFFICIAL_MOCK_ENTITY_PROFILE` and that the overlay outcome requires an identity basis.

### Check 3: arithmetic and provenance unchanged
- The backend diff touches only:
  - eligibility helpers, imports and the `eligible_poc_acceptance` guard/count lines;
  - the acceptance model fields and validator;
  - one legacy-rejection clause;
  - the scenario declaration.
- No traversal, aggregation, Decimal or classification code changed, and `simulation_calculation_complete` is unchanged.
- Tests assert the candidate percentages equal `EXPECTED` and the 6 relationships, both in every role-kind variant and through the API.
- Entity interests are unchanged: Garden 100, SIM LIM 62.5.
- Only the OPQ→Garden edge is owner-declared, and `source_reference` is not projected.
- Smoke B matches: 51.13636375 / 37.5 / 5.681818125 ×2, all classified `REVIEW_REQUIRED`.

### Check 4: readiness and GoldTier safety
- The readiness authority is still `OwnershipAnalysisService.poc_basis_accepted`. It requires all of:
  - the runtime opt-in;
  - the hybrid lane;
  - ownership being current;
  - the current document binding;
  - `poc_acceptance_current`.
- That authority is consulted in readiness and revalidation (`clm_orchestration.py` around lines 916 and 1407) and in zero-touch ownership progression. None of those files changed.
- The existing tests `test_revoking_the_policy_after_the_freeze_blocks_the_first_target_write` and `test_a_confirmed_mock_send_carries_no_assumed_basis_ubo_and_never_replays` pass.
- The new end-to-end test covers this path: READY with 0 blockers, then `TARGET_CONFIRMATION_REQUIRED`, then an explicit Mock send. After it, `ownership_reference.status == REVIEW_REQUIRED`, so no provisional UBO ids are fabricated.
- The withdrawal test shows the hold returns when the policy is withdrawn, with no target executions.
- In smoke B, `launch_offline.py` asserts `goldtier_connector_mode == "mock"` and that sandbox writes are off. The send status is COMPLETED.

### Check 5: persistence
- **New fields.** `descriptive_intermediate_{current,ceased}_role_count` are int fields with default 0 and a range of 0–32.
- **New assumption.** `accepted_assumptions` now allows at most 5 entries, which equals the number of enum values.
- **Validator.** The assumption must be present if and only if the counts are non-zero. A D-082 acceptance must have zero counts.
- **Legacy envelopes.** For schema ≤14, `reject_scenario_poc_legacy_fields` now also rejects non-zero counts. It is used by both `models.py:748` and `mongo_case_store.py:614`.
- **Schema 15.** The version number stays the same. The docs record it as unreleased, which is true because PR #111 is not merged. Records written by PR #111 deserialize with zero counts, and the Garden acceptance stays equal.
- **Tests and mutants.**
  - The schema-15 round trip passes, and legacy rejection is tested for both role-only and count-only payloads.
  - M14 (legacy persistence rejection) and M15 (count coupling) are killed.
  - M16 (the D-082 ban on counts) survives, because no test builds an otherwise-valid D-082 acceptance with counts. That is finding F2 (P3). Its impact is nil: D-082 records are never honoured under D-085, and schema ≤14 envelopes reject the counts.
- **Physical Mongo.** In the full run, 268 Mongo-named tests executed with 0 skipped.

### Check 6: frontend wording
- **Accepted banner.** It renders only when the backend flag `poc_basis_accepted` is set. It shows the heading "Ownership calculated — POC basis accepted" and keeps the existing limitation lines: denominators unverified, not a legal UBO determination, target confirmation still required, and the unclassified legal form.
- **New lines.** It adds two lines:
  - an intermediate-role disclosure with the counts (3 current, 1 ceased), stating they are "not shareholdings";
  - an owner-declared-link disclosure, shown only when some edge has `owner_declared_percentage`.
- **No stale warnings.** The D-087 test asserts that "verification required", the generic warning, "do not clear ownership readiness" and `.ubo-summary__warning` are all absent, and that `ds-banner-warn` is not set.
- **Non-accepted path.** It is the unchanged ternary: verification-required banner, then simulation banner, then partial-evidence warning. "Never infers acceptance from the record" still passes.
- **Gap.** There is no OPQ-specific test that the non-accepted render shows the warning banner. That is finding F3 (P3).
- **Runs.** `vitest src/pages/OwnershipStructure.test.tsx` passed 29/29, the full `vitest run` passed 1082/1082 (`vitest_full.log`), and `tsc --noEmit` exited 0.
- **Screenshot.** `smoke_d087\screenshots_B\B-ubo-summary.png` shows the accepted banner with every disclosure line present.
- **Mojibake.** The smoke JSON shows the em dash as garbled text. This is an encoding artefact of the smoke script's capture, not of the product; the screenshot renders it correctly.

### Check 7: docs
- **`DECISION_LOG` D-087 entry.** It is accurate against the code:
  - the new assumption accepts no issue code;
  - the declaration is Garden `OWNER` only;
  - the blocking list matches the guards;
  - the counts carry no identity;
  - schema 15 is unchanged and ≤14 envelopes reject the counts;
  - the results are the 4 assumptions with counts 3/1, READY, and `TARGET_CONFIRMATION_REQUIRED`.
- **D-086 open question.** It is marked as answered by D-087.
- **Other docs.** `OWNERSHIP_UBO_PROFILE`, the demo §7, `PROJECT_STATE` and `ARCHITECTURE` are consistent with this.
- **Authority labels.** They are `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`. There is no Live, ACRA-ownership or sponsor claim.

### Check 8: static checks
| Check | Result |
|---|---|
| `ruff check app tests` (0.16.2) | All checks passed |
| `mypy` on the 4 changed backend files (1.20.2) | Success, no issues |
| `git diff --check 8451e2a` | clean |
| Secret scan of added lines | nothing found |

`ruff format --check` reports 3 of the 5 changed backend files as unformatted. CI and `pre_pr_check` gate only on `ruff check`, so I record this as information, not a finding.

### Check 9: scope
The "ABC COMPANY 201688888A" follow-up is **not** in this candidate. The 13 files and the diff contain no such scenario, UEN or code.

### Evidence artefacts (verified)
- **Full backend run.** `full_backend_d087b.xml`: 3296 tests, 0 failures, 0 errors, 6 skipped. All 6 skips are Tesseract OCR tests (no OCR is claimed). The run took 1449 s and started at 20:30:49, after the last source edit at 19:28:32.
  - The relevant suite counts match the focused run: opq 22, poc 68, sim 26.
  - The first attempt, `full_backend_d087.log`, stalled. That is the known Windows socketpair issue, and it was correctly superseded.
- **E2E.** `d087-e2e/full_results.json` reports status PASS, 115/115, at 21:20. It records `head=8451e2a` and `tree=758eff3`, with `dirty=true`. The run postdates every edit, but it does not pin the working-tree content hash (see F4).
- **Smoke A and B** (19:32–19:35, after the edits): all checks PASS, as summarised above.

## 3. Mutation table
Suites: `test_opq_garden_sim_lim_scenario.py`, `test_poc_ownership_acceptance.py` and `test_simulation_calculation_status.py`. The control copy passed 116/116.

| ID | Mutation | Result | Killing test(s) / note |
|---|---|---|---|
| M01 | `descriptive_roles_of` check neutralised | **KILLED** | `test_only_the_declared_intermediate_role_kinds_are_accepted[SHAREHOLDER/PARTNER/MEMBER/OWNER+SHAREHOLDER]` |
| M02 | root check removed | survived (equivalent under validation) | Guarded by the M12 validator plus M01. QG probe `test_probe_root_guard` kills it (F1). |
| M03 | assumption check removed | survived (equivalent under validation) | Guarded by the M13 validator plus M01. QG probe `test_probe_assumption_guard` kills it (F1). |
| M04 | 32-record limit removed | **KILLED** | `test_malformed_or_improperly_bound_intermediate_roles_still_block` |
| M05 | scenario-issuer check removed | survived (equivalent under validation) | QG probe `test_probe_scenario_issuer_guard` kills it (F1). |
| M06 | duplicate-record check removed | **KILLED** | tamper test |
| M07 | identity-basis check removed | survived (equivalent) | Covered by the existing `LOCAL_SYNTHETIC_IDENTITY` rejection plus the domain validators. |
| M08 | outcome check removed | **KILLED** | tamper test |
| M09 | status check removed | **KILLED** | tamper test |
| M10 | environment check removed | **KILLED** | tamper test |
| M11 | whole `_undeclared_intermediate_roles` guard removed (global bypass) | **KILLED** | role-kind cases, declaration test, tamper test |
| M12 | scenario validator (named issuers must be non-root scenario issuers) removed | **KILLED** | `test_intermediate_roles_need_the_trusted_declaration_naming_their_issuer` |
| M13 | declaration coupling validator (assumption iff issuers, unique) removed | **KILLED** | same |
| M14 | schema ≤14 count rejection removed | **KILLED** | `test_the_acceptance_round_trips_in_schema_fifteen_and_older_readers_reject_it` |
| M15 | acceptance assumption↔counts coupling removed | **KILLED** | same |
| M16 | D-082 ban on intermediate counts removed | survived | No test builds an otherwise-valid D-082 acceptance with counts (F2). |

Raw results: `qg-d087\mutation_results.txt`, `qg-d087\probe_results.txt` and `qg-d087\control.log`.

## 4. What I did not run
- **Full backend suite and physical Mongo.** I did not rerun them; I accepted the implementer's artefact after checking its counts, skips, timestamps and suite coverage.
- **Full E2E (115).** I did not rerun it; I used the artefact.
- **Visual smoke.** I did not rerun it; I used the JSON and screenshots.
- **Frontend build.** I did not run `vite build`, because it would write into the worktree. I ran `tsc` instead.
- **Hosted CI.** Not run. It is known to be billing-blocked.
- **`pre_pr_check.py`.** Not run. It is a publication gate, and the candidate is intentionally uncommitted.
- **No `.env` access, no external providers, and no Mongo URIs printed.**

## 5. Verdict: **PASS**

There are no P0, P1 or P2 findings. The owner decision D-087 is implemented as specified:
- scenario-declared and issuer- and role-kind-scoped;
- no global bypass;
- the five-layer fixture is not POC-ready, and Garden direct stays accepted;
- formal classifications, arithmetic and provenance are unchanged;
- GoldTier still requires explicit confirmation and Mock-only, revalidated sends.

Advisory findings (non-blocking, P3):
- **F1 (P3).** The runtime root, scenario-issuer and assumption guards in `_undeclared_intermediate_roles` are defence in depth behind the declaration validators. The committed suite does not exercise them on their own (M02, M03 and M05 survive; the QG probes kill them). Suggestion: add `model_construct`-based tests like `qg-d087\test_qg_probe_guards.py`.
- **F2 (P3).** `OwnershipPocAcceptance` forbids intermediate counts on a D-082 record, but no test covers it (M16 survives). It has no runtime impact.
- **F3 (P3).** There is no OPQ-specific frontend assertion that the non-accepted render keeps the verification or warning banner. The generic coverage and the unchanged ternary make the risk low.
- **F4 (P3, evidence traceability).** The E2E results record `dirty=true` against the HEAD tree rather than the content tree `db56b8e`. Recency (it postdates every edit) and an unchanged tree support it, but it is not content-pinned.
- **Observation.** A discovery record is bound to its issuer by `registration_number` only. Nothing cross-checks `party_id` against the graph party's registration. The audit is produced by the system and is fingerprint-bound, so this is not a finding.

Any change made to address F1–F4 would change the reviewed content (`db56b8e`) and would need a fresh independent review.
