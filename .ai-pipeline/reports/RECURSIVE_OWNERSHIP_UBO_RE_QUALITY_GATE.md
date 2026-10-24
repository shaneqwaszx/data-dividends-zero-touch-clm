# Recursive Ownership and UBO Discovery — Stage 3 Independent Re-Quality Gate (R2)

## 1. Executive Result

**PASS.**

The remediation delta `08f8a24..d10d9e1` fixes M1 correctly and completely, and it fixes L1.

- **M1.** Every catalogue migration path now keeps `trace <= UBO` before anything is written.
  - I checked the history-free rebuild and the schema-3 `MIGRATED` path, each at the 35, 29, 21 and 8 rule prefixes.
  - A positive UBO below 10% seeds the trace at exactly that UBO value and records the audit marker.
  - A 0% UBO stops startup with `PolicyValidationError`. The stored catalogue stays byte-for-byte unchanged and the repository is never updated.
  - For a UBO of 10% or more, the candidate writes the same catalogue that `08f8a24` wrote.
  - I checked all of this in a 72-cell probe matrix and an equivalence probe, both run by me.
- **New tests.** Run against the `08f8a24` module, exactly the 5 new tests fail and the 21 existing tests pass.
- **L1.** The contract text now matches the code.
- **No regressions.** The delta introduces no regression in startup, RBAC/authority, CAS or the case snapshot freeze.
- **Stage 2 R2 evidence.** Each item is valid for exactly `d10d9e1`/`0b69166`, or validly reused (section 5).

I found one new issue, N1 (Low). It sits in code this delta did not introduce. A legacy `PENDING_APPROVAL` proposal that lowers UBO below the migrated trace threshold becomes undecidable after migration: the Director can neither approve nor reject it.

- It was already present at `08f8a24`, and this delta narrows the set of affected proposals.
- It fails closed and has a governance workaround.
- I accept it as a recorded limitation for later hardening (section 8). The owner may choose to require it before publication instead.

L2–L4 are unchanged and remain acceptable. No required fix remains, and no evidence gap is open for this exact content.

**Consequence.** The candidate is ready for Stage 4 publication **only with explicit owner authorization**. This verdict is not publication permission.

## 2. Reviewed identity (observed by me, read-only git)

| Item | Value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\recursive-ownership-ubo-20261023` |
| Branch | `feat/recursive-ownership-ubo-registry-20261023` (local, no upstream) |
| HEAD / tree | `d10d9e1de26c7b468259e61877d199671a4bfa2a` / `0b691661cb7814132e1e6908387b3238de05a08c` (`cat-file -p`: parent `08f8a24`) |
| Previously reviewed | `08f8a24ee905fa7249e66cf39f52483e8e3780db` (verdict PASS WITH MINOR FIXES) |
| Base / `origin/main` | `2f45324daec055b0929d17d2ad5fa518791c499d`. `git ls-remote origin refs/heads/main` returns the same SHA. Not fetched, per brief. |
| Exact content reviewed | `git diff 08f8a24..d10d9e1`, plus the code it reaches in the unchanged candidate. The delta is 5 files, +154/-10: `policy_management.py` +56/-6, `persistence/models.py` +1, `test_ownership_discovery_policy.py` +72/-2, `POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md` +8/-2, `RECURSIVE_OWNERSHIP_UBO_STAGE1_IMPLEMENTATION.md` +17. No other commit exists after `08f8a24`. |
| EOL | `--stat` equals `--ignore-cr-at-eol --stat`, both for the delta and for `2f45324..d10d9e1` (60 files, +4286/-319). Per-blob CRLF/LF counts are unchanged except for added LF lines. The one added `models.py` line is LF, matching its LF neighbours in that historically mixed-EOL file. |
| Whitespace | `git diff --check` exits 0 for both `08f8a24..d10d9e1` and `2f45324..d10d9e1`. No trailing whitespace in any delta blob. |
| Worktree status | Start and end: only `?? .ai-pipeline/reports/RECURSIVE_OWNERSHIP_UBO_QUALITY_GATE.md` (SHA-256 `B02B089A…DEACE`, 27845 bytes, mtime 17:29:07). It is unchanged, apart from this new report. |
| On-disk vs commit | The three changed Python blobs equal the `d10d9e1` blobs (`hash-object`; `--no-filters` for the mixed-EOL `models.py`). |

## 3. Acceptance checklist (re-QG scope)

| # | Check | Result | Direct evidence |
|---|---|---|---|
| 1 | Delta is exactly the 5 expected files with no EOL churn | **MET** | Section 2. |
| 2 | Every migration path keeps trace <= UBO **before any write** | **MET** | Seeding runs before candidate construction: `_upgrade_legacy_catalogue` → `_seed_trace_within_ubo` (`policy_management.py:142-148`). A pre-write `_ownership_discovery_snapshot(candidate)` check runs before `update` (`:179-184`). The `MIGRATED` path receives the seeded rules (`:178`, `_additive_migration` `:224-300`). Probe `probe_migration_matrix.py` covered the history-free rebuild and schema-3 `MIGRATED` paths × prefixes 35/29/21/8 × UBO {0, 0.000001, 5, 9.999999, 10, 10.000000, 10.000001, 25.000000, 100}: **72/72 as expected**. |
| 3 | Positive UBO < 10% seeds trace = UBO with audit marker | **MET** | Every positive sub-10 cell: trace equals the UBO string exactly; `trace_threshold_seeded_from_ubo: True`; `case_snapshot()` OK; restart idempotent. On `08f8a24` the same cells give trace `10.000000` and `case_snapshot()` raises, which reproduces M1. |
| 4 | 0% UBO fails closed, unchanged, not silent, not partial | **MET** | Every 0% cell, both paths and all prefixes: `PolicyValidationError` raised in `_seed_trace_within_ubo` (`:208-209`); `repository.get() == stored`; **0 `update` calls** (counting repository). It is not silent: `create_app` calls `PolicyManagementService(persistence.policies)` with no handler (`main.py:585`, module-level `app = create_app()` at `:3527`), so the process does not start. The operator-facing remediation detail is thin (O1). |
| 5 | Approvals, proposals, superseded versions, audit preserved | **MET** (see N1) | Every `MIGRATED` cell: legacy rules kept as prefix; `superseded_versions[:-1]` equal, last entry = legacy active rules/version; audit prefix equal; APPROVED/REJECTED proposals byte-equal; undecided proposals rebased with the migrated trace value. N1 covers the decidability of one sub-case. |
| 6 | Decimal precision and boundaries | **MET** | Seeding copies the stored decimal string (`:211-213`) with no float or rounding. UBO `10` / `10.000000` keep trace `10.000000` (equal, allowed). `9.999999` seeds `9.999999`. `10.000001` keeps 10. `0.000001` (trace minimum, `:1355`) seeds `0.000001` and the snapshot validates at 6 dp. `0` and the pattern-legal `0.000000` fail closed (`Decimal <= 0`). |
| 7 | New tests fail without the fix and are not weakened | **MET** | Mutation run: the candidate test file run against the `08f8a24` module (scratch plugin; worktree untouched) gives **26 run, 5 failed** — exactly the 5 new tests, failing on trace `10.000000` and DID NOT RAISE — and 21 passed. Existing assertions are unchanged. The helper refactor (`_as_legacy_35`, test file `:205-223`) keeps both original assertions. The exact-metadata assertion for UBO 25 (`:311-315`) still holds, so the marker is only added when seeding. |
| 8 | Contract text matches code (L1 + amendment) | **MET** (doc nits D1/D2) | `POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md:165-167` now excludes the impact preview, matching `proposal_impact` → `_validate_runtime(..., include_discovery=False)` (`policy_management.py:595-597`). The migration paragraph (`:177-181`) matches the seeding, fail-closed and pre-write check behaviour. `check_policy_authority.py`: PASS. D-076 (`DECISION_LOG.md:371-372`, "0% UBO can no longer be activated") stays consistent. |
| 9 | No regression in startup, RBAC/authority, CAS, snapshot freeze | **MET** | All new code runs only inside the legacy-migration branch. The fully-current catalogue still returns early (`:123-124`); memory mode always starts empty (`persistence/composition.py:128`); Mongo runs it once per legacy store (`:200`). `update(candidate, expected_version=current.version)` is unchanged. `_authorized_actor`, `decide_proposal`, `_persist`, `case_snapshot` and `_ownership_discovery_snapshot` are byte-unchanged. For UBO >= 10 the migrated document equals `08f8a24`'s: **25/25 equivalent** (event IDs normalised), including the exact `_legacy_catalogue_with_history` fixture used by the physical test. |
| 10 | L2–L4 still acceptable unchanged | **MET** | Section 6. |
| 11 | Stage 2 R2 evidence valid for `d10d9e1`/`0b69166` | **MET** | Section 5. |

## 4. Contract and integration findings

### N1 (Low; fail-closed; pre-existing since `f05aa69`, narrowed by this delta): a migration-rebased PENDING proposal can become undecidable

- **Where.**
  - `_additive_migration` rebases undecided current-base proposals by filling the new rules from the migrated active rules (`policy_management.py:245-262`).
  - The trace is therefore the migrated active trace: 10, or the seeded active UBO. It is never adjusted to the proposal's *own* proposed UBO.
  - `decide_proposal` runs full runtime validation, including discovery, for both approval **and rejection** (`:518`; base also validated on rejection).
- **Failure scenario.**
  - A pre-D-076 persisted catalogue has active UBO 25% and a `PENDING_APPROVAL` HR proposal setting UBO to 5%.
  - After upgrade, the rebased proposal carries UBO 5 and trace 10.
  - The Director's approve and reject both raise `PolicyValidationError`, and the catalogue is unchanged.
  - The proposer cannot edit it, because edits are DRAFT-only.
- **Reproduced.** `probe_rebased_proposals.py`:

  | Active UBO → proposal UBO | Candidate `d10d9e1` | `08f8a24` |
  |---|---|---|
  | 25 → 5 | stuck | stuck |
  | 25 → 0 | stuck | stuck |
  | 5 → 3 | stuck | stuck |
  | 5 → 7 | decidable | stuck |
  | 5 → 30 | decidable | decidable |

  The delta only narrows the affected set.
- **Containment.**
  - No rule is activated and no case is affected. There is no false success and no security effect.
  - Workaround: any other approved proposal makes the stuck one stale. The probe showed this, and stale is the ordinary terminal state of superseded pending proposals.
  - The DRAFT variant is recoverable: submission fails until HR edits in a consistent trace, then it succeeds (probe).
- **Authority read.**
  - Planner decision 7 ("rebases undecided proposals on the migrated base") and the migration paragraph are literally satisfied.
  - "Director alone approves/rejects…" (`POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md:100-101`) is an authority statement. Other validation and capacity failures can already block a decision today.
  - The implementation's own intent ("the rebased draft remains actionable", test `:326`) is not met for this sub-case.
- **Classification.** Accepted limitation, later hardening, explicitly permitted by this gate. It is not a required fix for this candidate.
- **Possible hardening** (owner/project choice, with a regression test):
  - (a) seed a rebased proposal's trace at its own positive UBO when that is lower;
  - (b) leave such a proposal un-rebased, so it is retained as stale;
  - (c) do not require runtime validation for a rejection.

### O1 (Low; operability/doc): 0% UBO refusal has no diagnostic message and only a vague remediation

- **What happens.** `_seed_trace_within_ubo` raises a bare `PolicyValidationError` (`policy_management.py:208-209`). That is the same type as every other migration refusal: unknown prefix, audit or superseded capacity.
- **What the contract says.** It only says the catalogue is left unchanged "for owner correction" (`POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md:180-181`).
- **Failure scenario.** A persisted dev or UAT store with an active 0% UBO stops starting after upgrade. The traceback names `_seed_trace_within_ubo`, but nothing says how to recover. The in-app HR/Director flow is unavailable while the app cannot start.
- **Recovery.** Approve a UBO above 0 on the previous release, then upgrade. Because the stored document is untouched, the previous release can still read it.
- **Classification.** Not required. It is fail-closed, consistent with D-076, and the earlier gate's mandatory items ("validate before the write", tests, "record the chosen behaviour in the amendment") are all met. Adding one remediation sentence is a recommended doc improvement.

### D1 / D2 (nits, doc)

- **D1.** The contract says undecided proposals are "rebased by adding only the new default rules" (`:175-176`). With seeding, rebased proposals receive the *seeded* trace (= active UBO), not the 10% default. The probe shows `rebased_trace == migrated trace`. The next sentence implies this, but the wording could be explicit.
- **D2.** `:167` is 97 characters long, against the file's ~90-column wrap. Cosmetic.

### Other notes

- **Observation (no action).** A catalogue already migrated by the unpublished `f05aa69`–`08f8a24` code with trace > UBO would hit the early return (`:123-124`) and not be repaired. That code was never published, so this is reachable only in a store someone ran unpublished candidate code against. It fails closed at snapshot time and governance can recover it.
- **Pre-existing, very low.** On a startup refusal, the persistence bundle opened at `main.py:584` is not closed before the exception propagates; the shutdown handler is registered at `:588`. This applies to every migration refusal since base, and the process exits anyway.
- **Sponsor dependencies (unchanged, later).** Q-004, Q-012, Q-019 and Q-002. Nothing in the delta claims Live, Sandbox or sponsor authority.

## 5. Tester and adversarial findings

### Commands I ran

All were run on `d10d9e1` in MEMORY mode with `PHASE12_MONGO_URI` unset and `PYTHONDONTWRITEBYTECODE=1`.

- **PYTHONPATH.** Set to the worktree root (plus `apps/backend` for scratch probes).
- **Module resolution.** `app.__file__` and `app.services.policy_management.__file__` both resolve inside the worktree.
- **Interpreter.** The main checkout `.venv` (Python 3.12.10).

| Check | Result |
|---|---|
| `pytest tests/test_ownership_discovery_policy.py -p no:cacheprovider` | **26/26 passed** |
| Focused pytest (16 files): `test_phase14_5_policy`, `test_phase24c_policy`, `test_phase14_5_administration`, `test_policy_provider_recovery`, `test_slice_e_policy_impact`, `test_blocker_decision_policy`, `test_s2_persistence_security`, `test_s3_retained_recovery`, `test_post_uat_remediation`, `test_goldtier_xpi_sandbox`, `test_zero_touch_orchestration`, `test_recursive_ownership_discovery`, `test_ownership_discovery_policy`, and three `*_real_mongo` files | **645 collected: 631 passed, 14 skipped, 0 failed/errors** (269 s). All 14 skips are physical Mongo with the URI unset, as intended. |
| Mutation: same test file with the `08f8a24` `policy_management` module substituted in-process | **5 failed (exactly the 5 new tests), 21 passed** |
| `ruff check apps\backend scripts tests --no-cache` | All checks passed |
| `mypy app --cache-dir <scratch>` | Success: no issues in 128 source files |
| `python -B scripts\check_policy_authority.py` | POLICY AUTHORITY CHECK: PASS |
| `git diff --check` (delta and full candidate), EOL comparisons | exit 0; no churn |

### Adversarial probes

All probes are in-memory with synthetic data. Scripts and outputs are under `...\scratchpad\reqg\`.

| Probe | Result |
|---|---|
| `probe_migration_matrix.py`: legacy catalogues built with the **base `2f45324`** workflow (real HR/Director approvals plus draft and rejected proposals), migrated by the candidate and by `08f8a24` | 72/72 candidate cells as expected. `08f8a24` reproduces M1 in every sub-10 cell. |
| `probe_equivalence.py`: candidate vs `08f8a24` migrated document for UBO >= 10 (history/free × 4 prefixes × {10, 25, 100}, plus the physical-test fixture) | 25/25 identical |
| `probe_rebased_proposals.py`: pending/draft proposals lowering UBO | N1 (section 4) |
| `pyc_source_check.py`: Stage 2's 18:03 bytecode headers vs current sources | Source mtime and size match for all 3 changed files. This weakly corroborates that R2 ran on this content. |
| `verify_r1_reuse.py`: R1 E2E JSONs and root junit | See the reuse table below |

### Stage 2 R2 evidence and reuse decisions

Raw artefacts were read by me in `...\spare-qbv2J6\...\scratchpad\stage2\`. The commit time of `d10d9e1` is 17:33:29 +08:00.

| Evidence | Source / identity | Decision |
|---|---|---|
| Full backend pytest with Mongo URI | `backend-junit-r2.xml`: **3089 tests, 0 failures/errors, 6 skipped**, timestamp 17:34:18 (after the commit). The 6 skips are OCR (`test_s2_local_ocr`). `test_ownership_discovery_policy` 26/26, including the 5 new cases. 173 real-Mongo cases executed. | **Valid for `d10d9e1`.** Identity rests on the report, timing, the clean worktree and the pyc stamps. The junit itself carries no identity, which is the same standard the earlier gate accepted. |
| OCR rerun with Tesseract | `backend-ocr-junit-r2.xml`: 36/36, 18:02:34 | Valid |
| Root focused | `r2-root-focused-junit.xml`: 52/52 (policy authority 14, project state 19, physical runner 19), 17:35:08 | Valid. `test_check_policy_authority` is the only root test that reads a delta file (the contract); I also reran the checker. |
| Physical Mongo | `r2b-physical.log`: `PASSED; SUITES=25; COLLECTED=167; PASSED=167; SKIPPED=0`, 18:13–18:19, exit 0. `r2-physical.*` is an interrupted attempt with an empty log and START only, correctly reported as no result. | **Valid.** The log has no embedded identity, but the timing is post-commit and the worktree has stayed clean. The delta's only physical-relevant effect is `_legacy_catalogue_with_history`/migration in `test_recursive_ownership_real_mongo.py:135-153`. For that path the candidate writes a document identical to `08f8a24`'s (25/25), and the earlier gate physically verified `08f8a24` itself. Seeding and the 0% refusal are repository-agnostic: the refusal happens before `update`, and seeding only changes a string value plus one bool audit key. |
| ruff / mypy / checkers | R2 report | Re-executed by me (ruff, mypy, policy authority). The architecture, project-state and secrets checkers are reused: the delta touches none of their inputs except a blank line in `models.py` (`CASE_SNAPSHOT_SCHEMA_VERSION` unchanged) and adds no secret. |
| Frontend (typecheck, Vitest 1050, build) | Stage 2 on `512a424` | **Valid.** `git diff --stat 512a424..d10d9e1 -- apps/frontend` is empty, and the delta has no API or type change. |
| E2E 114/114 union | R1 JSONs: all three `head 08f8a24`, `tree 87a8ae7`, `dirty:false`, `origin_main 2f45324` | **Valid reuse; I verified it myself.** The full run has 76 PASS, 1 `ASSERTION_FAILURE` (`s3-sandbox-submission.e2e.ts:383`) and 37 NOT_RUN. Rerun set = failed set, all PASS; remainder = NOT_RUN set, all PASS; union 114 selectors, disjoint, equal to the discovered set. **The reuse reasoning holds** (see the note after this table). Caveat carried from the earlier gate: no single uninterrupted unfiltered 114/114 run exists. That is an owner publication preference, not a candidate defect. |
| Root full suite and contract tests | R1 `r1-root-junit.xml`: 445 tests, 24 failures = `DemoLifecycleWindowsTests` 21 ("port 8000 occupied") + `ResourceReadinessTests` 3 (`No module named 'psutil'`); contract 44/44 | **Valid reuse.** `scripts/`, root `tests/` and `.github/` are unchanged in the delta. The only root consumer of a delta file is `test_check_policy_authority`, which was rerun. The 24 failures are environment-only and identical on base. They leave the demo-lifecycle and performance-resource claims **unverified**, not passed, and are unrelated to this content. |

Why the E2E reuse holds:

- The changed code runs only in `_upgrade_legacy_catalogue` past the early return.
- E2E backends run in memory mode with a fresh `InMemoryPolicyRepository` (`e2e_backend_server.py:116,159`; `composition.py:128`).
- The Slice C fixture uses a fresh `InMemoryPolicyRepository()` (`slice_c_recovery_fixture.py:103`).
- The Mongo fixtures use newly generated `clm_{p16|uat}_<hex>` databases (`run_e2e.py:625-631`). The synthetic-seed path seeds only registry snapshots (`e2e_backend_server.py:279-306`), and no E2E fixture writes a policy catalogue.
- `scripts/`, `apps/frontend/` and `.github/` are unchanged in `08f8a24..d10d9e1`.

## 6. Code and architecture review

- **The fix is minimal and well-placed.**
  - Seeding is a pure static function over the assembled rule tuple. It reads the UBO from the legacy prefix (the active value), not from defaults.
  - The trace is always the appended default. It can never be in a legacy prefix: the prefix IDs must equal `required_ids[:count]`, the trace is at index 35, and the tail rules may not be required IDs.
  - The pre-write discovery check is defence in depth. After seeding it cannot fail for a valid legacy catalogue. It maps validation errors to the same typed refusal.
  - The `MIGRATED` validator (`domain/policy.py:518-528`) still holds: predecessor rules are unchanged and the seeded rule is new.
- **No new owner or coupling.** There is no second persistence, authority or ownership owner, and no API/DTO, schema, connector, configuration or frontend change.
- **`models.py`.** The change is whitespace only; it resolves the earlier gate's E302 nit.
- **L2–L4, unchanged code, still acceptable as recorded.**
  - **L2.** The business budget is stricter than its description. It is conservative and leads to more review.
  - **L3.** Over-allocated holder sets reaching ANALYZED is base behaviour and needs later hardening; only project-controlled Mock data reaches it.
  - **L4.** Mock-only containment is structural, and it is still unreachable today.
  - Nothing in the delta changes their reach.
- **Test quality.** The new tests are focused and fail without the fix. The 21/8 prefixes, the history-bearing 0% case and the boundary values are not pinned by repository tests; I covered them by probe. Pinning them would be a nice-to-have, not required.

## 7. Security review

- **Audit metadata.** The new audit metadata key `trace_threshold_seeded_from_ubo` has a bool value, is 31 characters (cap 48), and avoids the forbidden markers (`domain/policy.py:257-262`).
- **No sensitive data.** The delta contains no secrets, credentials, URIs, KYC data or raw payloads. No `.env` read, no network access, no Mongo access by me, and no `clm_poc` involvement.
- **Authorization and CAS.** Reauthorization inside the lock and CAS are untouched. Seeding activates nothing (`MIGRATED` origin, system-bootstrap audit), so there is no automatic approval.
- **Findings.** No security finding. N1 and O1 have no security impact.

## 8. Required fixes

**None.**

The following are recorded and not required:

- **N1 (Low, accepted limitation, later hardening).** This gate explicitly permits it. The owner may instead require one of the hardening options (a), (b) or (c) in section 4 before publication.
- **O1 (Low).** Optionally add one remediation sentence for the 0% refusal.
- **D1 and D2 (nits).** Contract wording (rebased proposals receive the seeded trace) and one long line.
- **L2–L4.** Unchanged and accepted, as before.

**Operational note for the owner.** Before the first start of this candidate against any existing persisted policy store, check two things:

- The active UBO threshold is above 0%. Otherwise startup refuses (O1).
- No `PENDING_APPROVAL` proposal lowers UBO below the migrated trace threshold. Otherwise that proposal stays undecidable until another approval supersedes it (N1).

## 9. Readiness

- **This candidate.** Stage 3 is complete with `PASS` for `d10d9e1`/`0b69166` only. Stage 4 publication needs the owner's **explicit authorization**; this report grants none. Any change to the reviewed content requires a fresh independent review.
- **Real ACRA / GoldTier.** Not demonstrated and not claimed. All discovery evidence is synthetic Mock/LOCAL (Q-012, Q-019, Q-002 open).
- **Unverified claims, not gaps in this delta.**
  - Hosted CI is not evidenced here.
  - The demo-lifecycle (21) and performance-resource (3) root claims remain unverified because the infrastructure is missing; these failures are identical on base.
  - No single uninterrupted unfiltered 114/114 E2E run exists; union coverage is accepted.
- **Not run by me, per brief.** Physical Mongo, the full backend suite and E2E. Their Stage 2 evidence is judged valid in section 5, and no re-acceptance is required.

## 10. Git status

- **Branch and HEAD.** Branch `feat/recursive-ownership-ubo-registry-20261023`; HEAD `d10d9e1` and tree `0b69166` were unchanged from start to end.
- **Status at start.** `?? .ai-pipeline/reports/RECURSIVE_OWNERSHIP_UBO_QUALITY_GATE.md` only.
- **Status at end.** That file, unchanged (same SHA-256), plus this new untracked report `.ai-pipeline/reports/RECURSIVE_OWNERSHIP_UBO_RE_QUALITY_GATE.md`. Nothing is staged or modified.
- **No mutation.** No implementation fix, edit, stage, commit, push, fetch, reset, stash, clean, checkout, branch or worktree change, PR or merge.
- **Read-only git commands used beyond the listed set:** `cat-file -p`, `ls-files --eol`, `hash-object` without `-w`, `worktree list`, `config --get`.
- **No caches or bytecode written to the worktree.** I used `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`, `ruff --no-cache`, and a mypy cache in scratch. The only `__pycache__` entries in the worktree are Stage 2's, from 18:03:09.
- **Scratch only.** Probes, the exported `08f8a24` and `2f45324` modules, junit files and outputs are under `C:\Users\shane\AppData\Local\Temp\claude\C--Users-shane-Desktop-FYP-data-dividends-zero-touch-clm\7f464013-1918-4820-8b33-d152dd6a6acd\scratchpad\reqg\`.
- **No containers, servers, ports or Mongo connections** were used.
