# Zero-Touch Case Ordering Parity Remediation

## 1. Executive summary

RQG-02 runtime ordering parity is repaired at the automation repository boundary.
Memory and Mongo-backed automation listings now share one canonical sort definition:
automation `updated_at` descending, then canonical string `case_id` descending for an
exact timestamp tie. Focused, phase, static, security, and three complete backend gates
passed. Changes remain unstaged.

## 2. Worktree / branch

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-ordering`
- Branch: `fix/zero-touch-case-ordering`
- The separate `data-dividends-zero-touch-clm` worktree was not used or modified.

## 3. Starting SHA

- `HEAD`: `74a5fd2f8bc8a37c02a24dadaaa32a895ce2ee93`
- `origin/main`: `74a5fd2f8bc8a37c02a24dadaaa32a895ce2ee93`
- Starting tracked implementation diff: empty.
- Pre-existing untracked reports: `ZERO_TOUCH_CASE_ORDERING_REMEDIATION.md` and
  `ZERO_TOUCH_CASE_ORDERING_CONTRACT_RECONCILIATION.md`.

## 4. Authoritative Option A contract

Zero-touch case lists rank automation records by automation `updated_at` descending.
Exact equal timestamps have equal temporal rank and are ordered by canonical string
`case_id` descending for deterministic output only. Case ID and repository save order
do not represent chronology.

## 5. Confirmed memory/Mongo mismatch

The pre-change strict-TDD probe constructed automation order `B, A` and opposing
envelope order `A, B`. Memory returned `B, A`; the Mongo adapter returned `A, B`.
The focused test failed on the Mongo assertion before production code changed.

## 6. Root cause

`MongoZeroTouchAutomationRepository.list_records()` preserved the order returned by
`MongoCaseStore.list()`. That store correctly sorts complete envelopes by envelope
`updated_at`, which is not the automation timestamp exposed through the case-list API.

## 7. Canonical ordering rule

`order_zero_touch_automation_records()` applies one key to both implementations:
`(automation.updated_at, str(case_id))`, with descending ordering. Existing datetime
values are sorted directly; no timezone coercion or accepted datetime semantics changed.

## 8. In-memory behavior

The in-memory repository still creates deep copies under its lock and applies the same
byte-for-byte-equivalent ordering rule through the shared helper. Regression tests cover
empty results, deterministic newer-first order, updates, ties, repeated reads, and copies.

## 9. Mongo case-store behavior

`MongoCaseStore.list()` was not changed. Its envelope `updated_at` and case-ID ordering
remain intact, and the parity regression explicitly proves the fake case-store envelope
order remains opposite to the automation order where constructed.

## 10. Mongo automation-adapter behavior

The adapter retrieves durable snapshots, extracts deep copies of non-null automation
records, then applies the canonical automation sort. Snapshot order no longer defines
the automation repository result.

## 11. Chosen implementation boundary

The fix is owned by the existing automation repository seam. It does not redesign the
shared case store or introduce another persistence layer, fallback, or public API.

## 12. Files changed

- `apps/backend/app/services/zero_touch_repository.py`
- `apps/backend/app/persistence/repositories.py`
- `apps/backend/tests/test_pre_phase12_workspace_multidoc.py`
- `apps/backend/tests/test_phase12_persistence.py`
- `docs/architecture/PRE_PHASE_12_CLM_WORKSPACE_MULTIDOC.md`
- `docs/architecture/PHASE_12_DURABLE_PERSISTENCE_RESTART_RECOVERY.md`
- `.ai-pipeline/reports/ZERO_TOUCH_CASE_ORDERING_PARITY_REMEDIATION.md`

## 13. Implementation details

The memory repository delegates its existing sort to the shared helper. The Mongo
automation adapter constructs a generator of defensive automation copies from store
snapshots and delegates the final order to the same helper.

## 14. Shared sort-rule design

The helper is a small repository-level function, accepts an iterable, and returns a new
ordered list. It is not exposed by an API route or DTO and adds no abstraction beyond
the repository behavior that must be shared.

## 15. Historical test reconciliation

`test_repository_listing_is_empty_ordered_and_defensively_copied` now uses fixed UTC
timestamps with `A.updated_at < B.updated_at`, asserts `B, A`, retains empty and API
shape coverage, and directly verifies defensive copies. It no longer relies on clock
resolution or assumes second-created always ranks first.

## 16. Equal-timestamp regression

`test_repository_equal_timestamps_use_case_id_not_save_chronology` uses exact equal UTC
timestamps and controlled lowest/highest UUIDs. Save order is deliberately opposed to
the asserted descending identity order, and repeated reads are stable.

## 17. Memory/Mongo parity regression

`test_automation_repository_order_is_independent_of_envelope_order` reproduces the
original mismatch: automation order `B, A`, envelope order `A, B`. Both automation
repositories now return `B, A`. A second test proves exact-timestamp behavior in both
modes.

## 18. Update semantics

The parity test starts with `T2 > T1`, producing `B, A`, then updates A to `T3 > T2`
and proves both repositories return `A, B`. The unchanged envelope order does not
override the automation result.

## 19. Defensive-copy verification

Tests mutate nested metrics and clear returned lists from both implementations, then
read again and prove stored state and ordering remain unchanged.

## 20. MongoCaseStore non-regression

Production `MongoCaseStore`, CAS filtering, revision increments, envelope timestamps,
decoding, identity checks, and restart recovery were not edited. Phase 12 tests passed;
case-store ordering regressions: 0.

## 21. API compatibility

`GET /api/clm/zero-touch/cases` request and response models are unchanged. Existing API
field-shape coverage passes. API contract changes: 0.

## 22. Persistence schema compatibility

No envelope field, `schema_version`, migration, serialization, CAS, recovery, or
durability behavior changed. Persistence schema changes: 0.

## 23. Historical test 20-run result

20 consecutive isolated invocations passed: 20/20; failures: 0.

## 24. Equal-timestamp test 20-run result

20 consecutive isolated invocations passed: 20/20; failures: 0.

## 25. Memory/Mongo parity test 20-run result

20 consecutive isolated invocations passed: 20/20; failures: 0.

## 26. Repository-focused tests

- Pre-Phase 12 plus Phase 12 persistence focused files: 50 passed.
- Phase 12 persistence and real-Mongo file selection: 18 passed, 11 skipped.
- Coverage includes list/save/load behavior, updates, copies, envelope identity, CAS,
  restart/recovery, and the case-list API.

## 27. Backend full run #1

Repository-correct command from the repository root with `PYTHONPATH=apps/backend`:
complete suite passed, exit 0; 762 passed and 11 environment-gated real-Mongo skips,
with 3 expected Phase 06 adversarial serializer warnings. A preliminary non-qualifying
invocation from `apps/backend` stopped during collection because that working directory
shadowed the repository `scripts` package; no test executed, and it was not counted as
a full run.

## 28. Backend full run #2

762 passed, 11 skipped, 3 expected warnings in 24.05 seconds; exit 0.

## 29. Backend full run #3

762 passed, 11 skipped, 3 expected warnings in 23.26 seconds; exit 0.

## 30. Phase regressions

- Phase 09: 39 passed.
- Phase 10: 52 passed.
- Phase 11: 58 passed.
- Pre-Phase 12: 32 passed.
- Phase 12: 18 passed, 11 genuine-Mongo tests skipped.

## 31. Real-Mongo status

`PHASE12_MONGO_URI` was unavailable. Real Mongo verification not executed locally.
The passing `MemoryEnvelopeStore` adapter tests are not represented as genuine Mongo
runtime verification; the environment-gated CI suite remains the genuine gate.

## 32. Contracts/static/security

- Contract tests: 44 passed.
- Ruff: passed after correcting one mechanical import-order finding.
- Strict mypy: passed, no issues in 73 source files.
- `pip check`: no broken requirements.
- Secret scanner: passed; scanner unit tests: 5 passed.
- GoldTier validator unit tests: 5 passed.
- GoldTier example validator: exit 0, `NOT VALIDATED` because optional private sponsor
  archives were absent; no private file was read.

## 33. Documentation reconciliation

The Pre-Phase 12 architecture now defines automation time and the identity-only tie.
The Phase 12 architecture explicitly separates Mongo envelope read ordering from the
automation repository/API case-list ordering.

## 34. Diff audit

The tracked diff contains two repository implementation files, two backend test files,
and two focused architecture documents. `git diff --check` passed. There are no
frontend, lifecycle, ACRA, API DTO, schema, secret-scanner, or unrelated changes.

## 35. Git hygiene

All changes are unstaged. No branch switch, add, commit, push, merge, rebase, reset,
clean, stash, or PR operation was performed.

## 36. Remaining limitations

Genuine Mongo runtime verification could not run without `PHASE12_MONGO_URI`. Optional
private GoldTier examples were absent. These are recorded environment limitations, not
substituted by adapter doubles or synthetic validation claims.

## 37. Readiness

- Memory/Mongo ordering semantic mismatches: 0
- Historical ordering-test failures across 20 runs: 0
- Equal-timestamp test failures across 20 runs: 0
- Memory/Mongo parity-test failures across 20 runs: 0
- Full backend suite failures across 3 qualifying complete runs: 0
- MongoCaseStore ordering regressions: 0
- Repository regressions: 0
- Contract regressions: 0
- Security regressions: 0
- Persistence schema changes: 0
- API contract changes: 0
- Frontend changes: 0
- Lifecycle changes: 0
- ACRA changes: 0
- Security-tool changes: 0
- Unrelated changes: 0

The bounded runtime parity remediation meets its readiness conditions, subject to the
explicitly recorded external real-Mongo and optional private-example limitations.
