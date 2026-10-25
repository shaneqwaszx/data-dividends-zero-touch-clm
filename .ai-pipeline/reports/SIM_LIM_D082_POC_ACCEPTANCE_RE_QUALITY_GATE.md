# Sim Lim D-082 opt-in POC ownership acceptance: independent re-Quality Gate (Stage 3)

Reviewer: an independent Stage 3 re-gate. I did not author or remediate this content, and I
did not perform the previous gate. This report is my only repository write. Probes, junit
files, logs, a comparison extract of the failed tree and temporary indexes are under the
scratchpad folder `qg_d082_r1\`.

## 1. Executive Result

**PASS WITH NON-BLOCKING FINDINGS.** In the skill's vocabulary this is **PASS**: no fix is
required. Two Low findings and some Info notes are recorded for owner awareness (§3–§6).

- **R1 / F1 is resolved.** Garden's D1=B exemption now binds the exact observed officer set:
  three current and one ceased Owner role.
  - Each role's adapter-derived stable evidence id and its status are compared, as a set,
    against a protected backend-only HMAC-SHA256 allowlist.
  - My probe B reproduction is refused. It swaps all four identities for synthetic unknowns
    and keeps the 3 current / 1 ceased shape.
  - Also refused: every status swap, duplicate, missing or extra role, wrong provenance or
    issuer, and malformed, short, duplicate or absent configuration.
  - Readiness revalidates with the *current* allowlist, so changing or removing it revokes
    an existing acceptance.
- **F2 to F6 are resolved** as the owner directed.
  - F2: the toggle from enabled to disabled and back is consistent through real Mongo
    restarts. Nothing advances or dispatches while authority is withdrawn.
  - F3: the authority checks the document binding.
  - F4 and F5: the wording and counts are corrected on accepted cases only, and the
    snapshot is unchanged.
  - F6: authority is revalidated just before the first irreversible GoldTier write.
- **Residuals (non-blocking).**
  - N1 (Low): the F2 recovery predicate also changes recovery for an interrupted *non-D-082*
    manual replacement. The new behaviour is stricter and fails closed, but it is not
    disclosed and not tested.
  - N2 (Low): after re-enabling, the stale ownership hold clears only on an API resume. The
    browser offers no resume control in that state.

Verdict scope: the frozen product tree `5e7ca651e1903c09947bf8d9d162cf7d2ff554cd` only.

## 2. Reviewed identity and acceptance checklist

**Identity.**
- Branch `feat/sim-lim-acra-ownership-followthrough-20261024`. HEAD = BASE = `origin/main` =
  `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322`. The work is uncommitted.
- I recomputed the tree twice with a temporary `GIT_INDEX_FILE` under `qg_d082_r1\`, once at
  the start and once after every test and E2E run. The steps were `read-tree HEAD`, `add -u`,
  then the three new files. Both results were
  **`5e7ca651e1903c09947bf8d9d162cf7d2ff554cd`**.
- The real index stayed empty (`git diff --cached`: 0 files).
- The previous FAIL report `SIM_LIM_D082_POC_ACCEPTANCE_QUALITY_GATE.md` is preserved. Its
  `git hash-object` was `2ac85dc107822764376af61c90f501f33f4f5b89` at the start and at the
  end.

**Delta reviewed in depth.**
- Remediation delta `08c5ad4c…` → `5e7ca651…`: 18 files, +769/−90. The EOL-insensitive stat
  is identical, and `git diff --check` is clean.
- The full delta `ceefe1e` → `5e7ca651…` (59 files, +4470/−185, `--check` clean) was used
  as context only.
- Neither delta touches an AI Assistant, GoldTier or `scripts/` path. The remediation also
  touches no connector or discovery path.

| Requirement (owner decisions) | Result | Evidence |
|---|---|---|
| Exact role-id binding via backend-only env, absent by default | PASS | `config.py:41-45` (`SecretStr \| None = None`); `composition.py:378-400` parses only under the opt-in; the service nulls it unless enabled (`ownership_analysis.py:847-848`) |
| Exact observed set: 3 current + 1 ceased, any order | PASS | `_POC_ACCEPTANCE_SCENARIOS` `(UEN, 3, 1)` at `ownership_analysis.py:314-316`. Role block at `:469-493` checks: statuses `None`/`CEASED` only; counts; distinct parties and ids; id = adapter id (`:374-377` equals `registry_ownership._evidence_id`); kind, role, operation, provider, environment and issuer UEN; set match `matches` (`:346-353`, sorted, `hmac.compare_digest`) |
| Refuse substitution, addition, removal, status change; empty evidence | PASS | 29 suite mutations at `test_poc_ownership_acceptance.py:576`, 12 configuration mismatches at `:904`, fixture status variants. My probes: probe B, every ceased-swap position, and an empty or extra entry (§4) |
| Fail closed on absent, malformed, duplicate, short or other-key configuration | PASS | `parse_poc_officer_role_allowlist` (`:356-371`). My parser probes (§4) |
| Revalidation uses the current allowlist (and the flag) | PASS | `poc_acceptance_current(record, self._poc_officer_roles)` (`:511-528, 878`). Probe: 7 configuration changes revoke a stored acceptance; the same configuration keeps it |
| Ceased role is history only; evidence retained truthfully | PASS | Roles create no edge, party or candidate. Test `:819` shows identical candidates, edges and issues for the ceased and all-current fixtures. Provenance-retention test at `:753` |
| Protected values never stored, returned or logged | PASS | Acceptance stores only `descriptive_current_role_count`/`_ceased_role_count` (`domain/ownership.py:709-714`). Dataclass fields are `repr=False`. No new logging. Test `:954`. `.env.example` has empty values and placeholder syntax only |
| HMAC is the protected comparison for the unsalted stable id | PASS | Adequate for configuration. Info N6 covers the pre-existing runtime projection |
| Docs and contract say "three current and one ceased"; no corroboration claim | PASS | `DECISION_LOG.md:629-651`, `OWNERSHIP_UBO_PROFILE.md:431-445`, demo §8 `:288-311`. No remaining "four current", "four known" or recorded-role-id wording in the D-082 text |
| F2 enable → disable → enable consistency | PASS (Low N1, N2) | `zero_touch_orchestration.py:2841-2852, 2876-2890, 2930-2937`. In-memory test `:987`; physical restart test re-run (passed). My allowlist-withdrawal probe |
| F3 document binding in authority | PASS | `ownership_analysis.py:877`; test `test_the_authority_requires_the_current_document_binding` |
| F4 wording on accepted cases only | PASS | `UboSummary.tsx:5-7,13-14,42-46`; banner role-count disclosure `OwnershipStructure.tsx:113-114`. Vitest asserts the accepted and non-accepted variants |
| F5 Review & Send counts; snapshot unchanged | PASS | `ReviewAndSend.tsx:27-34,468` reads "4 natural person(s) assessed, 0 provisional UBO candidate(s), 2 assumed-basis threshold match(es)". The change is display only; snapshot code is untouched |
| F6 pre-write revalidation | PASS (Info N3) | `clm_orchestration.py:647-656, 818-828`, inside `before_first_write` only. `ANALYZED` and absent snapshots short-circuit (probe). Attempted-write recovery is unaffected. Test `:1018` |
| Owner regression list | PASS | Every listed regression has a suite test (§4 test quality), except a stored-acceptance-vs-changed-allowlist test (Info N4, covered by my probe) |

## 3. Contract and Integration Findings

No contract or mapping finding.
- Authority stays `USER_AUTHORIZED_POC` / `PROJECT_DEFINED_PROVISIONAL`. No contradictory
  example became a fixture or enum.
- The offline fixture stays `SYNTHETIC-ROLE-1..4`. Tests derive the ceased variant by
  setting `withdrawalDate` in a test helper, so no live identifier enters the repository.
- No ACRA, Live, denominator (Q-012), legal UBO (Q-004), reviewer authority (Q-014) or
  hierarchy (Q-002) claim is made. These later sponsor dependencies are unchanged.

The live Garden acceptance was **not re-smoked** with the R1 code. The implementer
discloses this, and I did not do it either: it needs ACRA Marketplace Mock calls and the
protected values. The exact-match path with the owner's configured digests is therefore
verified only through synthetic equivalents. The code path is identical.

## 4. Tester and Adversarial Findings

**Commands I ran on the frozen working tree** (product tree `5e7ca651…`).
- Backend: venv Python from `apps\backend`, `APP_ENV=test`, `PYTHONPATH=tests;.;../..`,
  `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider -o faulthandler_timeout=300`, junit
  output to scratch.
- Physical: `PHASE12_MONGO_URI` pointed at the disposable loopback mongo:7 on port 27094.
  Each test generated and dropped its own allowlisted database. `clm_poc` was never touched,
  and the URI was never printed or written.

| Check | Result |
|---|---|
| `tests/test_poc_ownership_acceptance.py` | **64 passed**, 0 failed/skipped (junit) |
| Physical `tests/test_recursive_ownership_real_mongo.py`, including the D-082 restart test (disable → hold only, re-enable → target confirmation) | **5 passed** |
| Physical subset: `test_s3_submission_real_mongo`, `test_garden_uen_partial_resume_real_mongo`, `test_zero_touch_database_real_mongo`, `test_classification_conflict_real_mongo` | **14 passed** |
| Chunk A, 15 recovery files (am18, phase24b ×5, document-refresh, slice-C, s3-retained, target-reliability, exception-remediation, manual-ownership, target-classification, classification-conflict, policy-provider-recovery) | **329 passed** |
| Chunk B, 18 files (CLM, s3 preview/status, hybrid overlay/journey, official-shareholder, ownership analysis/api/discovery-policy/recursive, phase12 persistence, slice-A/B, S2 intelligence/security, database happy path, ownership-document streamline, phase24 evidence) | **773 passed** |
| `tests/test_zero_touch_orchestration.py` | **88 passed** |
| My probes `qg_d082_r1\probes\test_qg_r1_probes.py` | **19 passed** (details below) |
| `python -m mypy app` (cache in scratch) | **Success: no issues in 129 files** |
| `python -m ruff check --no-cache .` (backend) | **All checks passed**. `ruff format --check` flags 5 changed files, all equally flagged at HEAD `ceefe1e`. Format is not a CI lane |
| `tests/contract` lane (`unittest discover`) | **44 OK** |
| `unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture`; `test_check_secrets.py` | **55 OK**; **8 OK** |
| `check_secrets`, `check_architecture`, `check_project_state`, `check_policy_authority`, `check_external_provider_readiness`, `check_tooling_config` | all PASS |
| Frontend `tsc -b` | PASS (exit 0) |
| Vitest: OwnershipStructure, ReviewAndSend, UboSummary, OwnershipPathExplorer, ownershipDisplay, S2OwnershipReview, ManualOwnershipEvidenceForm | **122 passed** (7 files) |
| Vitest: S3SubmissionStatus, UiV2Integration, Phase15CNavigation | **133 passed** (3 files) |
| Browser E2E, one selector `e2e/five-layer-hybrid.e2e.ts:78` (ports 9600/4900, Tesseract on PATH, `CLM_E2E_SYNTHETIC_MONGO_PORT=27094`) | **PASS 1/1** |
| Hygiene | The remediation diff is clean with `--check` and has no EOL churn. The three new product files and the implementer report have a final newline, no tabs and no trailing spaces |
| Heuristic leak scan of the added lines, `.env.example` and both D-082 reports (counts only) | 0 matches for 64-hex digests, `e-`+48-hex evidence ids or NRIC/FIN-format tokens. The only UEN-format token is the whitelisted public test UEN |

**Adversarial probes** (scratch only; synthetic values only; I did not look for or read the
real protected values).
- **Probe B reproduction:** all four identities are replaced with synthetic unknowns while
  the 3 current / 1 ceased shape is kept. Result: `eligible_poc_acceptance` returns None, and
  both `poc_acceptance_current` and `poc_basis_accepted` are false.
- **Ceased status moved** onto each of the three current roles: refused in every case.
- **Reordered evidence:** the set still matches. Only the content fingerprint differs, so a
  stored acceptance would correctly become non-current.
- **Stored acceptance revalidated** under each of these configurations: allowlist removed,
  key removed, a 31-character key, a different key, three entries only, a status moved, or
  the flag off. All revoke it. The original configuration keeps it.
- **Parser:**
  - Refused (returns None): an empty value, a trailing comma, newline separators, a
    lowercase status, one digest listed with two statuses, a 63-character digest,
    `= CURRENT` (space after `=`), a 31-character key, and an empty key.
  - Parses but never matches: well-formed entries with wrong statuses, five entries, and
    digests made under another key.
  - Accepted: whitespace around commas, which is benign because the identity is unchanged.
  - No repr shows the key or a digest.
- **Digest over the raw officer id** instead of the evidence id: never matches, so it fails
  closed.
- **F6:** `_poc_authority_is_current` returns True for an absent or `ANALYZED` snapshot
  without consulting ownership.
- **F6 with the allowlist withdrawn** between freeze and submit: technical failure
  `CLM_NOT_READY`, no attempted operation, no GoldTier result, snapshot retained.
- **F2 with the allowlist withdrawn** (the flag stays on):
  - repeated resumes stay at OWNERSHIP with only `OWNERSHIP_INCOMPLETE` and no target
    execution;
  - after the allowlist is restored, resume reaches `TARGET_CONFIRMATION_REQUIRED`, and the
    confirmation completes the Mock send;
  - after the send, the case stays `COMPLETED` even when authority is withdrawn again.
- **Non-D-082 comparison** (N1): this probe runs the am18 harness on both trees. The failed
  tree was extracted read-only from `08c5ad4c…` into scratch.

**N1 — Low (non-blocking). F2 recovery also changes non-D-082 interrupted-replacement
recovery.**
- Location: `zero_touch_orchestration.py:2877-2890` (and `:2933-2936`).
- `current_review` is true for *every* REVIEW_REQUIRED analysis while the policy is off. So
  the new `unproved_ownership_checkpoint` disjunct and `poc_revoked` also fire for ordinary
  records that hold a completed OWNERSHIP checkpoint next to a REVIEW_REQUIRED analysis.
- Reproduced through a real non-D-082 path: a manual replacement that writes a
  REVIEW_REQUIRED graph, whose automation save then fails, followed by resume.
  - Failed tree: the case stays `WAITING_FOR_REVIEW`/OWNERSHIP. OWNERSHIP stays in
    `completed_stages`, and `TARGET_CONFIRMATION_REQUIRED` stays active beside
    `OWNERSHIP_INCOMPLETE`.
  - Candidate: the case is rebuilt. The stages become REGISTRY, GOLDTIER_SEARCH and
    DOCUMENT; only `OWNERSHIP_INCOMPLETE` remains; the confirmation hold is cancelled; the
    event code is `CURRENT_OWNERSHIP_PREREQUISITE_RESTORED`.
  - Both trees make no target call, and the later manual correction succeeds on both.
- The candidate's outcome fails closed and matches the uninterrupted manual-replacement
  result (`test_am18_ownership_checkpoint.py:130`), so it is arguably a correction.
- However, the code comment, the decision log and the report present it as D-082-only, and
  no test covers it.
- Recommendation: either disclose it as intended stricter recovery and add a non-D-082
  test, or scope the new disjunct to POC-completed checkpoints.

**N2 — Low (non-blocking). The re-enable recovery has no browser trigger.**
- After re-enabling, `poc_basis_accepted` is true, so the CaseDetail header shows
  "Ownership calculated — POC basis accepted." (`CaseDetail.tsx:1299-1300`). Meanwhile the
  automation still holds `OWNERSHIP_INCOMPLETE` until `POST …/resume`.
- The UI offers resume only for these states (`CaseDetail.tsx:1492-1521, 1718-1721`):
  - `PENDING_INPUTS`;
  - `RECOVERY_PENDING`;
  - document-refresh recovery.
- The demo guide says only "the next resume" (`FIVE_LAYER_ACRA_HYBRID_DEMO.md:311`).
- So the contradictory display the previous gate reported under F2 remains in the browser
  until an out-of-band resume. The case still fails closed: confirmation requires an active
  confirmation hold.
- This is based on code inspection. It was not browser-verified, because no D-082 E2E exists
  and a live smoke was out of scope.
- Recommendation: document the resume step, or record it as a POC limitation. A UI change
  needs owner authorization.

**Test quality.**
- The mutation suite asserts `eligible_poc_acceptance(...) is None` directly, so each clause
  is exercised independently of the fingerprint.
- The configuration-mismatch suite runs real analysis. It also asserts that the
  calculations, issues and the four role records are unchanged.
- The F2 in-memory test toggles the private `_poc_acceptance_enabled`. The physical test
  covers real restarts.
- Every owner-listed regression has a test. Exact match, one substituted identity, reorder,
  duplicates, missing, additional, ceased, issuer, provenance, the disabled flag and missing
  configuration are all covered. So are: arithmetic unchanged, non-hybrid unchanged,
  disable revokes, re-enable consistent, existing cases not accepted, no-replay, a snapshot
  with 0 provisional UBO ids, and no protected values in API, settings or repr.

**Not run by me** (I rely on implementer evidence only where stated):
- the full backend suite (implementer: 3244 tests, 3068 passed, 176 skipped, 0 failed);
- the full physical runner (implementer: 25 suites, 170/170);
- the full browser E2E. The implementer reports 114/115 with one transient that passed when
  rerun alone. A separate full run was in progress on 9300/4600 during this gate; I did not
  touch it or use its results;
- the full Vitest suite and the build (implementer: 64 files, 1070 tests; build PASS);
- `pre_pr_check.py`, which does not apply to an uncommitted handoff;
- a live Garden re-smoke.

## 5. Code and Architecture Review

- There is still one readiness authority on the existing ownership owner, and no second
  owner was added. The allowlist is composition-scoped and re-read at each composition. The
  persisted acceptance is audit only, and it now carries counts rather than identifiers.
- R1 is cohesive: the parser, the dataclass, the adapter-id helper and one eligibility block
  sit in one place. The helper duplicates `registry_ownership._evidence_id`; a test pins the
  equality.
- F6 adds one guarded check inside the existing `before_first_write` gate. Normal dispatch,
  ledger ordering, CAS and no-replay are unchanged.
- **N3 — Info.** An F6 refusal becomes a terminal zero-touch `TECHNICAL_FAILURE`
  (`zero_touch_orchestration.py:3383-3394`) with the snapshot retained.
  - Re-enabling does not recover it: no retry path exists for `CLM_NOT_READY`.
  - This fails closed, and it matches how an existing `CLM_TARGET_CONFIRMATION_REQUIRED`
    from submit is handled.
  - The decision log names the refusal but not the terminal automation outcome.
- **N5 — Info.** A malformed, short or duplicate allowlist silently disables the exception,
  with no value-free operator signal. This is documented: Garden stays under ordinary
  review.
- **N7 — Info.** Unreleased envelope 14 renamed a field: `descriptive_role_evidence_ids`
  became two counts, with `extra=forbid`. Any dev-only data that the failed tree wrote with
  an acceptance would now fail closed on load. The smoke server runs in memory mode.
- The evidence tagger tags each retained role `OWNER_ROLE` whether or not it has ceased.
  This is pre-existing and descriptive only: it does not feed percentages or
  classification.

## 6. Security Review

No blocking security finding.
- Settings use `SecretStr`, default None and are backend-only. `PocOfficerRoleAllowlist`
  fields are `repr=False`.
- Parsing never raises or echoes a value. No logging was added.
- Values appear in no API field, acceptance or zero-touch summary (test `:954`).
- `.env.example` holds names and syntax only.
- HMAC-SHA256 under a key of at least 32 characters, with a constant-time compare of the
  canonical set, is an adequate protected comparison. Without the key, the configured
  digests cannot be dictionary-reversed.
- **N4 — Info (test gap).** No suite test revalidates a *stored* acceptance against a
  changed or removed allowlist (my probe covers it). No automated scan of tracked files for
  role identifiers exists; the implementer's manual scan and my heuristic scan found none.
- **N6 — Info (pre-existing).** The keyed digests protect only the configuration. The stored
  analysis and the ownership API still project each role's raw officer `party_id` and its
  unsalted evidence id. That is D-077/D-079 runtime behaviour, and the owner directed that
  the complete evidence be retained. The docs do not present these values as anonymized.
- RBAC and team scope are unchanged.

## 7. Required Fixes

None. Recommended, non-blocking:
- N1: disclose and test the stricter non-D-082 recovery, or scope it to POC-completed
  checkpoints.
- N2: document the API resume step after re-enabling, or record it as a POC limitation.
- N4: add a stored-acceptance revocation test.

N3, N5, N6 and N7 are owner awareness only.

## 8. Readiness

- **Stage 3:** PASS WITH NON-BLOCKING FINDINGS for tree
  `5e7ca651e1903c09947bf8d9d162cf7d2ff554cd`. The skill-equivalent verdict is PASS.
  Publication still needs explicit owner authorization, unchanged reviewed content, and a
  clean committed pre-PR check.
  - The owner should acknowledge N1 and N2.
  - Any change to the reviewed content needs a fresh focused review.
- **Live Garden acceptance with the owner's protected allowlist:** not exercised. It needs an
  owner-authorized live Mock smoke.
- **Real ACRA / GoldTier:** unchanged and not claimed. Only Mock and offline evidence was
  used, and no Live or Sandbox call was made.

## 9. Git Status

- Branch `feat/sim-lim-acra-ownership-followthrough-20261024`, HEAD `ceefe1e`.
- 56 tracked files modified; 3 task-owned untracked product files; untracked
  `.ai-pipeline/reports/*`. Nothing staged.
- The previous gate report is byte-identical (`2ac85dc1…`).
- My only repository write is this report.
- Probes, junit files, logs, the mypy cache, the failed-tree extract and temporary indexes
  are under the scratchpad folder `qg_d082_r1\`.
- E2E runtime evidence went to the gitignored `tmp/`.
- No implementation fix, commit, push, stash, branch change, install, merge or next phase
  occurred.
- `.env` and the scratchpad `smoke\` folder were not opened.
- No ACRA or GoldTier host was called.
- Ports 8791/5791 and 9300/4600 were not touched.
