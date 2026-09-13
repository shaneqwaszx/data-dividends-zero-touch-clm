# Phase 14.5 Narrow Physical Re-Quality Gate

## RESULT

**PASS.** P145-PHYS-001's structural remediation remains verified. The owner has now supplied the exact approved real-Mongo execution result: one physical restart-and-cleanup test passed in 33.03 seconds. That evidence is consistent with the independently reviewed physical-test contract; no structural finding is reopened.

## Repository State

- **BRANCH:** `phase/14-5-policy-team-admin`
- **HEAD:** `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- **ORIGIN MAIN:** `b8f9406b57929c7ede537b0262ea78f655b48c27`
- **MAIN DRIFT:** YES — expected Phase 14 merge pending later integration.
- **Merge base:** `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- **Main-only commit:** `b8f9406 feat: add Phase 14 case management and performance optimisation (#29)`.

The repository was already dirty with the owner’s Phase 14.5 changes. This review left those changes untouched and did not merge `origin/main`.

## P145-PHYS-001

**P145-PHYS-001: CLOSED.**

**ROOT CAUSE VERIFIED: YES.** Profile persistence stores `_id = user_id`, while team-scoped profiles also carry a different `team_id`. Selecting `team_id` as the profile identity makes a valid profile such as `maya-lim` / `TEAM_A` fail after restart.

The decoder is now symmetric with persistence and explicitly selects its identity by record type:

| Record type | Persisted `_id` | Decoder identity |
| --- | --- | --- |
| `TeamRecord` | `team_id` | `team_id` |
| `UserAccountRecord` | `user_id` | `user_id` |
| `PolicyCatalogue` | `catalogue_id` | `catalogue_id` |

**STRICT DECODING: PASS.** `_decode` still requires a string `_id`, performs strict model validation, recursively rejects unknown fields, rejects mismatched IDs, and rejects unsupported record types. No fallback or validation weakening was introduced.

The round-trip regression covers Maya Lim/`TEAM_A`, Ethan Tan/`TEAM_A`, Olivia Koh/no team, HR/no team, and new Gamma RM/`TEAM_B`; it checks identity, role, optional team, security version, and protected credential-hash equivalence. Its adversarial companion rejects corrupt `security_version`, injected unknown fields, and mismatched `_id` documents.

**ROUND-TRIP REGRESSION: PASS.** Reviewer run:

```text
python -B -m pytest tests/test_phase14_5_administration.py -p no:cacheprovider --tb=short
20 passed in 2.49s
```

**STRUCTURAL/SAFETY REGRESSION: PASS.** Reviewer run:

```text
python -B -m pytest tests/test_phase13_mongo_test_safety.py -p no:cacheprovider --tb=short
8 passed in 0.31s
```

The physical-test contract creates only `clm_p145_<24 lowercase hex>` databases, starts one composition to persist records, creates a second composition against the same database, asserts administration/case/policy persistence after restart, and calls an allowlisted cleanup helper in `finally`. The helper rejects shared/arbitrary names, retries drops, and verifies final database absence.

**PHYSICAL MONGO: OWNER-EVIDENCE PASS.** The supplied owner execution used the approved command from `apps/backend` and reported `1 passed in 33.03s`. This is consistent with the reviewed contract and proves the previously missing restart and cleanup acceptance criterion. The URI was not requested, read, or printed by this reviewer.

- **PHYSICAL EXECUTION:** owner-run — 1 passed in 33.03s.
- **RESTART:** PASS.
- **GENERATED DB CLEANUP:** PASS.
- **STRUCTURAL / SAFETY:** PASS — owner-run 8 passed in 0.17s; repeat: 8 passed in 0.17s.

## Findings

| Severity | Finding |
| --- | --- |
| Critical | None in this narrow review. |
| High | None in this narrow review. |
| Medium | None. |
| Low | None. |

## Receipts and Readiness

- **FOCUSED ADMIN:** PASS — 20 passed in 2.49s, reviewer-run.
- **MYPY RECEIPT:** 26 existing Phase 14.5 full-app findings remain outside this narrow gate; not rerun.
- **READY FOR OWNER CHECKPOINT COMMIT:** YES.
- **READY FOR PHASE14 INTEGRATION:** NO.
- **READY FOR PR:** NO.
- **READY FOR MERGE:** NO.

The physical re-QG is ready for the owner checkpoint commit. Phase 14 integration remains deliberately deferred: it requires the later owner-controlled integration sequence and is not authorized by this narrow physical evidence update.

## Data Safety and Git Receipt

| Item | Result |
| --- | --- |
| `.env` accessed | NO |
| Mongo URI printed | NO |
| Password/hash material printed | NO |
| Shared `clm_poc` inspected | NO |
| Shared `clm_poc` written | NO |
| Phase 14 worktree accessed | NO |
| Protected artifacts accessed | NO |
| Production code/tests modified by reviewer | NO |
| Files staged, committed, pushed, merged, rebased, reset, stashed, cleaned, or branches switched | NO |

**FILES MODIFIED: report only** — this report.
