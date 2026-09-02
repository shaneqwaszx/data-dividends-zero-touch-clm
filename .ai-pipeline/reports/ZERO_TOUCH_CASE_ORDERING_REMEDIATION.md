# RQG-02 — Zero-Touch Case Ordering Remediation

## 1. Executive summary

The intermittent ordering failure is confirmed and has a deterministic reproduction.
The current in-memory repository orders automation records by
`(updated_at, str(case_id))` descending. When `updated_at` values are equal, UUID
lexical order decides the result and can contradict repository save chronology.

The bounded remediation cannot safely implement the requested chronological tie-break
with the existing persistence contract. Memory mode has process-local write order, but
Mongo mode has no durable cross-case automation-save sequence. Automation `version` and
envelope `revision` are per-case concurrency counters, not comparable chronology across
cases. Envelope `updated_at` is changed by every envelope repository write, not only an
automation-record save, and can itself collide. Adding a durable cross-case ordering
field or counter would cross the task's explicit persistence-schema stop condition.

No source, test, API, persistence schema, frontend, lifecycle, security-tooling, or ACRA
connector change was made. This report records the mandatory bounded stop.

## 2. Worktree path

`C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-ordering`

The separate primary UI worktree was not used or modified.

## 3. Branch

`fix/zero-touch-case-ordering`

No branch switch, rename, merge, rebase, or checkout was performed.

## 4. Starting HEAD

`74a5fd2f8bc8a37c02a24dadaaa32a895ce2ee93`

The dedicated worktree was clean at task start.

## 5. origin/main reference

`74a5fd2f8bc8a37c02a24dadaaa32a895ce2ee93`

Starting `HEAD` exactly matched `origin/main`.

## 6. Historical failing evidence

The supplied re-quality-gate evidence recorded one failure in the second of two full
backend runs:

`apps/backend/tests/test_pre_phase12_workspace_multidoc.py::test_repository_listing_is_empty_ordered_and_defensively_copied`

The supplied totals were `1 failed, 710 passed, 11 skipped`; the exact node later passed
10/10 isolated reruns. In this remediation worktree, the unchanged exact node passed
20/20 independent invocations.

## 7. Root cause

The proximate mechanism is the UUID secondary key in the in-memory repository. Equal
`updated_at` values exhaust the primary key, so descending UUID text—not create, save,
or update order—selects the first record.

The deeper recurrence generator is a contract/data gap: no common repository contract
stores a cross-case automation-save chronology that both memory and Mongo can compare.
The failure recurs whenever the application clock gives two relevant records the same
effective automation `updated_at` and the UUID lexical relationship opposes save order.

Falsifier checked: if UUID lexical order did not control tied records, adversarial UUIDs
would still return later-saved B before A. With A saved first, B saved second, exactly
equal timestamps, A UUID `ffff...`, and B UUID `0000...`, the repository returned A, B
on all 20 diagnostic runs.

## 8. Existing ordering contract

The sources do not currently express one consistent chronological contract:

| Source | Current statement/behavior |
| --- | --- |
| In-memory repository | Automation `updated_at` descending, UUID text descending |
| Pre-Phase 12 architecture | `updated_at` descending with stable case-ID tie-break |
| Historical test | Second-created case must precede first-created case |
| Mongo store | Envelope `updated_at` descending, case ID descending |
| API | Preserves repository order; performs no independent sort |

The architecture document's stable-ID rule is deterministic but not chronological. The
historical test and remediation acceptance criteria require chronology. That conflict is
material because the durable model lacks the data needed to implement the latter rule.

## 9. In-memory repository analysis

`InMemoryZeroTouchAutomationRepository.save()` stores defensive copies in a Python
dictionary. Record `version` increments per case for optimistic concurrency. Updating
an existing dictionary key does not encode a comparable cross-case update sequence.
`list_records()` copies records and sorts by automation `updated_at`, then UUID text.

Memory mode could maintain a process-local repository write counter without a schema
change. That would be valid only for process-local chronology and would be lost on the
documented memory-mode restart boundary.

## 10. Mongo repository analysis

`MongoZeroTouchAutomationRepository.list_records()` inherits `MongoCaseStore.list()`
order. The store sorts complete case envelopes by envelope `updated_at`, then case ID.
Each envelope replacement increments that case's `revision` and replaces envelope
`updated_at` with `datetime.now(UTC)`.

Envelope `revision` is local to one case and covers writes from onboarding, documents,
ownership, reconciliation, CLM, automation, target execution, and demo state. It cannot
compare which of two cases was persisted later. Envelope `updated_at` is durable, but it
is case-envelope persistence time rather than automation-save chronology, advances on
unrelated repository writes, and has no guaranteed unique value. Case ID is a UUID, not
chronology.

## 11. Memory/Mongo parity analysis

There is one confirmed semantic mismatch. Memory's primary field is the automation
record's `updated_at`; Mongo's primary field is the containing case envelope's
`updated_at`. Equal-key fallback in both modes is case identity, but the primary event
being timed is not the same.

A memory-only sequence would fix the historical failure while leaving Mongo with a
different and incomplete rule. Reinterpreting per-case revision as a global sequence
would also be incorrect. Memory/Mongo parity therefore cannot be established safely
within the existing durable fields.

## 12. Exact chosen ordering rule

The required rule, if persistence design is expanded in a separately approved task, is:

1. automation `updated_at` descending, so updating an older case moves it to the top;
2. durable cross-case automation-repository save sequence descending when timestamps
   are equal;
3. stable identity only for legacy records whose chronology was never recorded and is
   therefore unknowable.

This rule is analysis, not an implemented or approved schema change. The current task
stopped before adding the required durable sequence.

## 13. Why the secondary key represents chronology

No existing candidate does. Automation `version` and envelope `revision` are per-case
counters; `created_at` is immutable and can collide; envelope `updated_at` times any
envelope write and can collide; UUID is arbitrary identity. A correct secondary key must
be assigned from one cross-case automation-save sequence and persisted with the record.

## 14. Update semantics

The established primary behavior remains `updated_at` first. Normally:

- create A, then create B: B appears before A;
- update A later: A moves before B;
- equal timestamps: the later automation-repository save must win.

An immutable creation-order tie-break alone would be wrong because it would not preserve
the expected movement of `WAITING_FOR_REVIEW`, `COMPLETED`, `RECOVERY_PENDING`, or other
later automation updates.

## 15. Deterministic reproduction

An in-process diagnostic constructed two valid `PENDING_INPUTS` automation records with
the exact same aware UTC `created_at` and `updated_at`. A had a lexically high UUID and
was saved first; B had a lexically low UUID and was saved second. Expected chronological
order was B, A. Actual order was A, B in 20/20 runs.

This is deterministic reproduction of the equal-key defect. It is distinct from the
historical API test, whose timestamps collide only intermittently.

## 16. Files changed

- `.ai-pipeline/reports/ZERO_TOUCH_CASE_ORDERING_REMEDIATION.md` — this analysis and
  mandatory stop report.

No implementation or test file was changed because the persistence-schema stop
condition was reached before implementation.

## 17. Implementation details

No implementation was made. Re-sorting by UUID, per-case version/revision, mutable
test-only state, increased timestamp precision, sleeps, retries, or frontend order would
not satisfy the chronology and parity requirements.

## 18. API compatibility

`GET /api/clm/zero-touch/cases` was not changed. Request schema, response DTO, fields,
filtering, and projection remain unchanged.

API contract changes: `0`.

## 19. Persistence compatibility

No envelope field, schema version, migration, recovery rule, Mongo CAS behavior, or
durable record was changed.

Persistence schema changes: `0`.

## 20. Equal-timestamp test

No repository test was committed because there is no bounded GREEN implementation and
the task requires source changes to stop at the schema boundary. The deterministic
diagnostic was executed 20 times against the actual in-memory repository and failed the
required B, A order 20/20 times.

## 21. Defensive-copy verification

The unchanged historical node includes the repository/API defensive-copy expectations
and passed 20/20 isolated invocations. Code inspection also confirms both memory and
Mongo adapters return deep copies. No defensive-copy behavior was changed.

## 22. Historical test — 20-run result

`test_repository_listing_is_empty_ordered_and_defensively_copied`: **20 passed, 0
failed** across 20 separate pytest invocations.

One earlier attempt to import the test module directly as a package failed with
`ModuleNotFoundError`; this was an invocation error before the required pytest-based
20-run loop and is not a product-test failure.

Historical ordering-test failures across 20 runs: `0`.

## 23. New equal-timestamp test — 20-run result

Deterministic diagnostic: **0 passed, 20 failed** against required chronological order.
Every run returned A, B after save order A, B with equal timestamps and UUID order
opposed to chronology.

Equal-timestamp regression failures across 20 runs: `20`.

## 24. Repository-focused tests

Executed:

- exact historical repository/API node once: passed;
- exact historical repository/API node 20 independent times: 20 passed;
- deterministic equal-timestamp repository diagnostic 20 times: 20 expected failures.

The broader repository, CAS, save/load, restart, and case-list suites were not run after
the mandatory persistence-schema stop. No implementation candidate exists to qualify
for the requested regression gate.

## 25. Full backend run #1

Not executed. The task stopped before implementation under the explicit persistence
schema stop condition.

## 26. Full backend run #2

Not executed for the same reason.

## 27. Full backend run #3

Not executed for the same reason.

Full backend suite failures across 3 runs: `N/A — 0 of 3 required runs executed`.

## 28. Phase regressions

Phase 09, Phase 10, Phase 11, Pre-Phase 12, and Phase 12 regression groups were not run
after the mandatory design stop. The historical Pre-Phase 12 node was the only phase
test executed. Readiness is not claimed.

## 29. Real-Mongo verification status

`PHASE12_MONGO_URI` is absent. `MONGO_URI` is also absent.

Real Mongo verification not executed locally. No mock or in-memory envelope adapter is
presented as genuine-Mongo evidence.

## 30. Contracts/static/security checks

No source implementation exists to qualify for the requested Ruff, strict mypy,
contract, dependency, or GoldTier validation gate. Readiness is not claimed.

Executed report-only safety checks:

- `python scripts/check_secrets.py`: passed; no supported secret patterns found;
- `python -m unittest discover -s tests -p "test_check_secrets.py"`: 5 tests passed;
- `git diff --check`: passed with no output for tracked changes;
- `git diff --no-index --check -- NUL <report>`: no whitespace-error output; exit 1 is
  the expected no-index difference status for a new file, and Git emitted only the
  repository's LF-to-CRLF working-copy warning.

## 31. Diff audit

Final audit target:

- frontend changed files: `0`;
- Windows lifecycle changed files: `0`;
- security scanner changed files: `0`;
- ACRA connector changes: `0`;
- API DTO contract changes: `0`;
- unrelated changed files: `0`.

`git status --short` shows only the untracked required report. `git diff --name-status`
and `git diff --stat` are empty because the report is intentionally unstaged and Git's
ordinary diff excludes untracked files. The report was inspected directly and through
the no-index whitespace and secret scans above.

## 32. Git hygiene

All changes remain unstaged. No `git add`, commit, push, merge, rebase, reset, clean,
stash, branch switch, checkout, or PR action was performed.

## 33. Remaining limitations

- The documented stable UUID tie-break conflicts with the chronological expectation.
- The durable model has no cross-case automation-save sequence.
- Memory and Mongo time different persistence events for list order.
- Exact timestamp collision remains capable of returning non-chronological order.
- A separately approved persistence design is required before implementation; it must
  define legacy-record ordering, schema/versioning, migration or compatibility,
  concurrency scope, and memory/Mongo parity.

Explicit metrics:

| Metric | Result |
| --- | ---: |
| Historical ordering-test failures across 20 runs | 0 |
| Equal-timestamp regression failures across 20 runs | 20 |
| Full backend suite failures across 3 runs | N/A (not run) |
| Memory/Mongo ordering semantic mismatches | 1 |
| API contract changes | 0 |
| Persistence schema changes | 0 |
| Frontend changes | 0 |
| Windows lifecycle changes | 0 |
| Security-tooling changes | 0 |
| ACRA connector changes | 0 |
| Backend regressions | N/A (not assessed by full gate) |
| Contract regressions | N/A (not assessed by full gate) |
| Security regressions | 0 |
| Unrelated changed files | 0 |

## 34. Readiness

The deterministic bug is not fixed. The current persistence model cannot represent the
required cross-case chronological tie-break, and the brief explicitly forbids expanding
the persistence schema within this remediation. Independent quality-gate entry criteria
are therefore not met.

NOT READY FOR ZERO-TOUCH CASE ORDERING INDEPENDENT QUALITY GATE
