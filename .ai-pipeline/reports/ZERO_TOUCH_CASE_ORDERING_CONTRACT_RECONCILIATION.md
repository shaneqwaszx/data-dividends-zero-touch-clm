# RQG-02 — Zero-Touch Case Ordering Contract Reconciliation

## 1. Executive summary

Authoritative project evidence supports Option A: the zero-touch case list is ordered
by the automation record's `updated_at` descending, with a deterministic stable case-ID
tie-break when timestamps are exactly equal. Identical persisted automation timestamps
have equal temporal rank; the tie-break does not claim create or save chronology. The
historical second-created-first assertion is therefore over-specified.

The bounded reconciliation cannot proceed to test/document changes because memory and
Mongo do not currently implement that one contract consistently. Memory sorts by
automation `updated_at`; Mongo inherits complete-envelope order by envelope
`updated_at`. The API displays automation `updated_at`, not envelope `updated_at`.
A controlled probe produced opposite list orders for the same automation records when
automation and envelope update order differed. The handoff requires an immediate stop
for this condition.

No implementation, test, canonical documentation, schema, API, frontend, lifecycle,
security-tooling, or ACRA change was made. This report records the contract decision and
the remaining runtime mismatch.

## 2. Worktree / branch

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-ordering`
- Branch: `fix/zero-touch-case-ordering`
- Starting status: only
  `.ai-pipeline/reports/ZERO_TOUCH_CASE_ORDERING_REMEDIATION.md` was untracked.

The separate UI V2 worktree was not used or modified. No branch switch occurred.

## 3. Starting SHA

- `HEAD`: `74a5fd2f8bc8a37c02a24dadaaa32a895ce2ee93`
- `origin/main`: `74a5fd2f8bc8a37c02a24dadaaa32a895ce2ee93`

## 4. Original RQG-02 finding

The final UI V2 re-quality gate observed an intermittent failure in:

`apps/backend/tests/test_pre_phase12_workspace_multidoc.py::test_repository_listing_is_empty_ordered_and_defensively_copied`

The assertion assumed that case B, created immediately after case A, must list first.
When both automation `updated_at` values collided, the repository instead used UUID
lexical order, so the assumption could fail.

## 5. Previous persistence stop result

`ZERO_TOUCH_CASE_ORDERING_REMEDIATION.md` correctly established that strict cross-case
save chronology is not represented durably. Automation `version` and envelope
`revision` are per-case concurrency counters. A new durable cross-case sequence would
be a persistence design/schema expansion and was therefore not implemented.

## 6. Contract evidence inventory

| Source | Exact ordering evidence | Timestamp semantics | Tie behavior | Normative? | Predates Phase 12? |
| --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | Contradictions must not be resolved silently | No list field defined | No tie rule | Global project authority | No |
| D-032 decision | Adds backend-authored case index/review queue | Automation-backed case index | Not stated | Working project decision | Yes |
| Pre-Phase 12 architecture | `updated_at` descending | In-memory automation record | Stable case-ID tie-break | Authoritative architecture for feature | Yes |
| Memory repository docstring/code | “newest update first” | Automation `updated_at` | Case ID, descending in code | Runtime owner | Yes |
| Pre-Phase 12 quality gate | Sorts by updated time then case ID | Automation repository time | Stable case ID | Independent accepted evidence | Yes |
| Phase 12 planner | Persistence choice without changing accepted flow; existing repository interfaces remain | Existing business/repository behavior is inherited | No new ordering policy | Phase scope authority | No |
| Phase 12 architecture | Persistence does not change business policy | Envelope gains its own timestamps | No new list contract | Current architecture | No |
| Phase 12 quality gate | Mongo store order is envelope `updated_at`, then `case_id`, descending | Complete envelope persistence time | Stable case ID | Independent implementation evidence | No |
| API model | Exposes `record.updated_at` | Automation `updated_at` | Preserves repository order | Public runtime contract | No |
| UI | “Recent CLM cases”; `Updated` column; “Updated” queue label | Displays API automation `updated_at` | No explicit promise | User-facing evidence | No |
| Historical test | Second-created case must list first | Assumes clock order implies creation order | No equal-time rule | Regression evidence, not product authority | Yes |

No decision, contract, architecture document, API schema, or user-facing copy promises
strict cross-case save order when timestamps are identical.

## 7. Architecture evidence

The most specific ordering statement is in
`docs/architecture/PRE_PHASE_12_CLM_WORKSPACE_MULTIDOC.md`: deep defensive copies are
ordered by `updated_at` descending with a stable case-ID tie-break. Phase 12 explicitly
preserves existing repository interfaces and says persistence does not change business
policy. It adds envelope timestamps for durable case storage but does not declare those
timestamps to replace automation `updated_at` as the case-list key.

D-032 establishes the automation-backed case index. D-033 establishes durable envelope
persistence and per-envelope CAS, not a new list-ordering policy.

## 8. API evidence

`GET /api/clm/zero-touch/cases` iterates `ZeroTouchOrchestrator.list_cases()` without
re-sorting. `ZeroTouchCaseListItemResponse.from_domain()` exposes
`ZeroTouchAutomationRecord.updated_at`. No envelope timestamp is in the DTO. The request
has only an optional typed status filter and makes no create-order/save-order promise.

## 9. Test evidence

Only the historical Pre-Phase 12 test asserts two-case positional order. It creates two
cases using the real clock and assumes the second call's case must be first. Other list
tests check empty results, one-case membership, status filtering, cross-case isolation,
durable membership, and defensive copies; genuine Mongo coverage checks membership and
status but explicitly does not verify exact order.

The prior remediation's deterministic probe showed why the historical assumption is
not valid for exact timestamp ties. That finding does not establish Option B; it shows
that the test demanded chronology absent from the accepted contract.

## 10. User-facing ordering semantics

The dashboard says “Recent CLM cases” and displays an `Updated` column. The review queue
displays “Updated <timestamp>”. It does not say “created most recently”, “last saved”,
or guarantee strict order between equal timestamps. Two rows with the exact same
displayed persisted automation timestamp have no observable temporal distinction under
the published data.

## 11. Memory ordering semantics

`InMemoryZeroTouchAutomationRepository.list_records()` sorts defensive copies by:

1. `ZeroTouchAutomationRecord.updated_at` descending;
2. `str(case_id)` descending.

This exactly implements Option A. Automation `version` remains a per-case optimistic
concurrency value and has no list-order role.

## 12. Mongo ordering semantics

`MongoZeroTouchAutomationRepository.list_records()` returns automation records in
`MongoCaseStore.list()` order. The store sorts complete snapshots by:

1. `DurableCaseSnapshot.updated_at` descending;
2. `case_id` descending.

`MongoCaseStore.replace()` refreshes envelope `updated_at` on every envelope mutation,
including document, ownership, reconciliation, CLM, automation, target-execution, and
demo repository writes. That field is not the automation `updated_at` returned by the
case-list API.

## 13. Durable chronology capability

Strict cross-case automation-save chronology cannot be represented by existing fields.
Automation `version` and envelope `revision` are per case. `created_at` is immutable and
can collide. Automation and envelope `updated_at` represent different update domains
and can both collide. UUID is stable identity only.

No schema change is authorized or required for Option A itself. A schema change would be
required only for Option B's stronger strict-save guarantee.

## 14. Option A assessment

**Confirmed by authoritative evidence.** The accepted rule is automation `updated_at`
descending plus deterministic stable case-ID order for exact ties. It is directly stated
by the feature architecture, implemented by the original memory repository, confirmed
by the accepted Pre-Phase 12 quality gate, inherited by Phase 12's no-policy-change
boundary, and consistent with the API/UI surface.

## 15. Option B assessment

**Not supported by authoritative evidence.** The only source implying strict chronology
is one historical test assertion. No product wording or architecture/decision/contract
requires later repository saves to win exact timestamp ties. Implementing Option B
would introduce a stronger product and persistence concept rather than repair an
accepted existing contract.

## 16. Final contract decision

Option A is the canonical contract. The historical second-created-first assertion is
over-specified for exact timestamp collisions.

The decision does not authorize test reconciliation in the present worktree because
the memory/Mongo implementation mismatch is independently material and triggers the
handoff's explicit stop condition.

## 17. Canonical ordering rule

For the zero-touch case-list repository and API:

1. primary key: automation `updated_at` descending;
2. exact automation timestamp tie: canonical string `case_id` descending;
3. the stable identity key produces a total deterministic order only; it does not
   represent creation, repository-save, or envelope-write chronology.

## 18. Equal-timestamp semantics

Cases with identical persisted automation `updated_at` have equal temporal rank. The
stable case-ID tie-break makes repeated reads deterministic. Changing a UUID may change
relative order only within an exact timestamp tie; it cannot outrank a different
automation timestamp.

## 19. Files changed

Added in this reconciliation:

- `.ai-pipeline/reports/ZERO_TOUCH_CASE_ORDERING_CONTRACT_RECONCILIATION.md`

Pre-existing task artifact retained unchanged:

- `.ai-pipeline/reports/ZERO_TOUCH_CASE_ORDERING_REMEDIATION.md`

No implementation, test, or canonical architecture/contract file was changed.

## 20. Historical test reconciliation

Not performed. Although Option A confirms that the assertion should eventually be
replaced with explicit timestamp/tie behavior, doing so now would hide the independently
proven memory/Mongo primary-key mismatch. The handoff requires a stop instead.

## 21. Deterministic tie test

No repository test was added because test reconciliation is blocked by the parity stop.
The prior deterministic probe remains valid evidence that exact automation timestamp
ties follow stable UUID order in memory. A future bounded runtime-alignment task should
add one shared semantic test against both repository implementations before correcting
the historical API test.

## 22. Memory/Mongo parity

**Mismatch confirmed.** A controlled adapter probe used two valid automation records:
B had the later automation `updated_at`, while A's containing envelope had the later
envelope `updated_at`. Results were:

- expected/API-visible automation-time order: B, A;
- memory repository order: B, A;
- envelope order: A, B;
- Mongo automation adapter order: A, B.

This difference is material because the API displays automation time while Mongo orders
by a different hidden time. No documentation states that envelope time intentionally
replaces automation time for this endpoint.

Memory/Mongo semantic mismatches remaining: `1`.

## 23. Historical test 20-run result

Not rerun after reconciliation because the mandatory parity stop occurred before test
changes. The immediately preceding remediation report records `20 passed, 0 failed`
across 20 independent pytest invocations of the unchanged historical node; that is
historical evidence, not a fresh post-reconciliation readiness gate.

Historical ordering-test failures across 20 fresh reconciliation runs: `N/A`.

## 24. Equal-timestamp test 20-run result

Not executed as a committed test because the parity stop occurred before test
reconciliation. No post-change equal-timestamp readiness result exists.

Equal-timestamp deterministic-test failures across 20 runs: `N/A`.

## 25. Backend full run #1

Not executed. The mandatory memory/Mongo contract inconsistency stop occurred before
implementation or test reconciliation.

## 26. Backend full run #2

Not executed for the same reason.

## 27. Backend full run #3

Not executed for the same reason.

Backend full-suite failures across three runs: `N/A — 0 of 3 runs executed`.

## 28. Phase regressions

Phase 09, Phase 10, Phase 11, Pre-Phase 12, Phase 12, and repository/persistence suites
were not run after the mandatory stop. `PHASE12_MONGO_URI` and `MONGO_URI` are absent;
real Mongo verification was not executed locally. No adapter double is represented as
genuine Mongo evidence.

## 29. Contracts/static/security

Contract tests, Ruff, strict mypy, `pip check`, and the GoldTier validator were not run
because no eligible test/document reconciliation or implementation was made. Report-only
checks completed as follows:

- `python scripts/check_secrets.py`: passed; no supported secret patterns found;
- `python -m unittest discover -s tests -p "test_check_secrets.py"`: 5 tests passed;
- `git diff --check`: passed with no tracked-diff output;
- no-index `git diff --check` for both untracked reports: no whitespace-error output;
  exit 1 is the expected difference status and Git emitted only LF-to-CRLF working-copy
  warnings.

Readiness is not claimed.

## 30. Persistence schema impact

Persistence schema changes: `0`. No field, schema version, migration, CAS behavior,
recovery behavior, or stored envelope was changed.

## 31. API impact

API contract changes: `0`. `GET /api/clm/zero-touch/cases` and its response DTO are
unchanged.

## 32. Git hygiene

All task artifacts remain unstaged. No add, commit, push, merge, rebase, reset, clean,
stash, branch switch, checkout, or PR action was performed.

Final status contains only the two expected untracked ordering reports. Ordinary
`git diff --name-status` and `git diff --stat` are empty because untracked files are not
included. Direct inspection and no-index checks cover both report files.

Scope audit:

- frontend changes: `0`;
- Windows lifecycle changes: `0`;
- ACRA connector changes: `0`;
- security-tool changes: `0`;
- persistence schema changes: `0`;
- API DTO changes: `0`;
- unrelated changes: `0`.

## 33. Remaining limitations

- Mongo orders the automation list by envelope `updated_at`, while memory and the API
  contract use automation `updated_at`.
- Genuine Mongo exact-order coverage is absent; the existing gate checks membership.
- The historical test remains over-specified and intermittent until runtime parity is
  repaired and the test is reconciled together.
- Strict cross-case save chronology remains intentionally unsupported.

Explicit metrics:

| Metric | Result |
| --- | ---: |
| Ordering contract ambiguities remaining | 0 |
| Memory/Mongo semantic mismatches remaining | 1 |
| Historical ordering-test failures across 20 runs | N/A (not rerun) |
| Equal-timestamp deterministic-test failures across 20 runs | N/A (test not added) |
| Backend full-suite failures across 3 runs | N/A (not run) |
| Persistence schema changes | 0 |
| API contract changes | 0 |
| Frontend changes | 0 |
| Lifecycle changes | 0 |
| Security changes | 0 |
| ACRA changes | 0 |
| Unrelated changes | 0 |

## 34. Readiness

Option A is authoritative, but the current memory and Mongo repositories do not express
one consistent primary timestamp contract. The handoff explicitly prohibits masking
that mismatch through test-only reconciliation and requires this stop.

MEMORY/MONGO ORDERING CONTRACT STILL INCONSISTENT
