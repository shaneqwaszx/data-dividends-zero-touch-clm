# Phase 13 Final Targeted Independent Re-Quality Gate

**Phase:** Case Prioritisation, Authentication & Team-Based RBAC
**Review role:** Fresh independent reviewer
**Review date:** 2026-09-07
**Branch reviewed:** `phase/13-case-priority-auth-rbac`
**Gate result:** **PASS**

## 1. Executive summary

The targeted Phase 13 re-quality gate passes. P13-QG-001 through P13-QG-004 are independently closed, no remediation-related Critical, High, Medium, or Low finding was discovered, and the mandatory Phase 12/13 genuine Mongo 7 suite passed 12/12 without an environment skip.

The remediation now rejects every non-integer schema discriminator, refetches authoritative frontend projections after priority mutation, proves raw schema-v2 and team immutability through physical Mongo, and validates the complete mounted 42-route graph by exact equality. Representative authentication, session, CSRF, team isolation, non-enumeration, creation, priority, frontend-auth, and secret/log controls remain green. Full backend, frontend, contract, POC catalogue, and Windows lifecycle regressions also pass.

This result means Phase 13 is ready for the repository owner's controlled commit/latest-main/pre-PR/PR workflow. It is not authorization to perform integration and is not a production IAM, live ACRA, real GoldTier, or Ready-for-Approval claim.

Critical: **0**
High: **0**
Medium: **0**
Low: **0**

## 2. Baseline

`git fetch origin` completed before review. The baseline remains exact:

| Check | Observed result |
|---|---|
| Branch | `phase/13-case-priority-auth-rbac` |
| `HEAD` | `36d0247befce04bbed85e3dced9f9c1c2b617855` |
| `origin/main` | `36d0247befce04bbed85e3dced9f9c1c2b617855` |
| Merge base | `36d0247befce04bbed85e3dced9f9c1c2b617855` |
| Main drift | None |
| Staged paths | None |

The feature remains an intentionally dirty, uncommitted owner-controlled delta. No branch switch, merge, rebase, reset, clean, stage, commit, or push was performed.

## 3. Scope

The re-gate was deliberately bounded to closure of P13-QG-001 through P13-QG-004 and representative regression of the previously passing security properties: authentication, session lifecycle and rotation, CSRF, Team A/Team B isolation, Director visibility, IDOR/non-enumeration, creation policy, priority validation and authorization, backend ordering, frontend authentication, secret/log safety, and existing CLM behavior.

The planner, implementation report, original quality gate, architecture, access/priority contract, project context, D-034, Q-016, branch protocol, security checklist, and current POC regression catalogue were read. Relevant remediation code and tests were inspected directly rather than accepting the execution report's claims.

The unrelated untracked filename beginning `e workspace and multi-document intake` and all `pytest-cache-files-*` artifacts were not opened, read, modified, renamed, deleted, staged, or treated as findings.

## 4. Previous finding closure matrix

| Prior finding | Severity | Re-gate status | Independent basis |
|---|---:|---|---|
| P13-QG-001 — schema discriminator accepted numeric lookalikes | Medium | **CLOSED** | Exact-type implementation inspection, independent 1/2/unknown/non-integer probe, focused/full tests |
| P13-QG-002 — stale frontend order and mixed timestamp semantics | Medium | **CLOSED** | Parent projections now refetch; exact A/B/C reorder test passes; no frontend priority sort; list timestamp retained |
| P13-QG-003 — incomplete genuine-Mongo assertions | Medium | **CLOSED** | Test inspection plus 12/12 physical Mongo 7 execution |
| P13-QG-004 — incomplete route-inventory regression | Low | **CLOSED** | Recursive exact-equality test, adverse included-router test, and independent 42/42/43-route probe |

P13-QG-001: **CLOSED**
P13-QG-002: **CLOSED**
P13-QG-003: **CLOSED**
P13-QG-004: **CLOSED**

## 5. Schema discriminator evidence

`apps/backend/app/persistence/mongo_case_store.py:187-199` now requires `type(schema_version) is int` before choosing a decoder. Exact integer 1 uses the strict v1 model; exact integer 2 uses the v2 model; another integer produces `PersistenceSchemaUnsupportedError`; every non-integer produces `PersistenceDataInvalidError`.

The independent raw-envelope probe confirmed:

- integer `1` accepted and decoded through v1;
- integer `2` accepted and decoded through v2;
- integer `3` rejected as unsupported schema;
- `True`, `False`, `1.0`, `2.0`, `1.5`, `"1"`, `"2"`, null, list, and object rejected as malformed persistence;
- a valid v1 input was unchanged by read and projected `team_id=null`, `priority=null`.

The focused remediation suite includes an additional non-primitive object case. All of its discriminator cases passed.

## 6. Frontend reorder evidence

`PriorityControl` now performs `updateCasePriority` and then awaits an authoritative refresh callback. `CaseQueue` refetches the current backend list plus detail projections and replaces `cases`; `OnboardedClients` refetches the server-filtered completed list and replaces `clients`; `CaseDetail` invokes its full `refreshEvidence` path. None locally moves a row after mutation.

The required sequence was reproduced by the focused frontend regression:

```text
initial: A(10), B(1), C(null)
mutation: C -> 9
server refetch: A(10), C(9), B(1)
rendered order: A, C, B
```

The exact test passed independently (`1 passed`, six unrelated tests deselected). The full Phase 13 frontend module passed 7/7 and the full frontend suite passed 103/103. A repository-wide frontend search found no `.sort()` or priority-sort implementation.

## 7. Timestamp-semantics evidence

The priority mutation response's case timestamp is no longer patched into list state. Queue and Onboarded views discard the mutation projection for list rendering and replace state with server-returned list/detail projections. The reorder test uses distinct automation and case-mutation timestamps and confirms C retains the original server-list automation timestamp after refetch.

`CaseDetail` no longer merges mutation timestamps into summary fields. Its successful priority callback refetches the authoritative case, documents, and ownership projections before updating state. P13-QG-002 is closed without introducing a client-side ordering owner.

## 8. Real-Mongo test review

`apps/backend/tests/test_phase13_real_mongo.py` now explicitly proves:

- all three raw documents contain an exact built-in integer `schema_version`;
- raw `schema_version == 2`;
- physical repository `TEAM_A -> TEAM_B` reassignment raises `CaseTeamImmutableError`;
- immediate decoded and raw reload retain `TEAM_A` and priority 10;
- recomposition retains Team A, Team B, priority `10`, `8`, and null;
- Director order remains high, mid, unset;
- Team A and Team B authorized lists remain isolated;
- detail/list recovery after restart performs no Registry, IDP, Ownership, or GoldTier calls;
- post-restart raw state still contains exact integer schema v2, original team, and priority.

The companion Phase 12 physical module remains in the same mandatory command and covers its existing recovery, identity, CAS, interrupted-document, target-ledger, and provider-free restart invariants.

## 9. Genuine Mongo execution evidence

Genuine Mongo: **PASS**

`PHASE12_MONGO_URI` was not preconfigured. Docker 29.7.2 was available, port 27018 was free, and no container existed at the selected exact name. A temporary `mongo:7` container was created and readiness was confirmed with `db.adminCommand({ping:1}).ok == 1`.

The exact mandatory command was run with a process-only URI:

```text
python -m pytest tests/test_phase12_real_mongo.py tests/test_phase13_real_mongo.py -p no:cacheprovider
............ [100%]
12 passed in 9.29s
```

There were no skips. The process environment value was removed when the command ended. The exact temporary container was force-removed after testing, and a subsequent container query returned no match. No Mongo listener, repository configuration, credential, or test database remains.

## 10. Route inventory evidence

The route test now recursively traverses mounted routes, nested route collections, and FastAPI's included-router `original_router`. It requires `actual == expected`, not subset inclusion. It also asserts 42 policies with the exact classification counts:

| Route class | Count |
|---|---:|
| Public | 2 |
| Actor-only | 5 |
| Case-creation | 4 |
| Case-scoped | 31 |
| Total | 42 |

An independent OpenAPI-derived route probe found `CURRENT_ACTUAL=42`, `POLICY=42`, `EXACT=True`. A fresh application with a test-only unclassified included-router endpoint produced `AUGMENTED_ACTUAL=43`, `POLICY=42`, and was rejected by exact comparison. The authored adverse included-router regression also passed. P13-QG-004 is closed.

## 11. Security regression evidence

A bounded representative selection passed 19/19. Together with inspected implementation and the focused/full suites, it reconfirmed:

- valid authentication for the five fixed profiles;
- generic invalid-password/unknown-user behavior;
- old-cookie revocation on login rotation;
- exactly one valid session after concurrent same-profile login;
- fixed CSRF/origin rejection;
- server identity unaffected by spoofed role/team headers and query values;
- Team A cannot access Team B, and Team B cannot access Team A;
- Director sees both teams and legacy-unassigned cases;
- cross-team and nonexistent identifiers have the same fixed 404 body/status;
- team actors receive server-owned creation teams and Director must select a fixed team;
- cross-team priority mutation returns 404 and leaves state unchanged;
- strict priority validation and deterministic backend ordering remain intact.

The authentication/session/CSRF and non-enumeration owners were not altered by the targeted remediation. Secret/log tests remain green, and a protected-boundary-safe scan covered 380 tracked and explicit Phase 13 files with zero findings while opening neither the protected filename nor cache artifacts.

## 12. Full regression evidence

| Check | Qualifying result |
|---|---|
| Focused Phase 13/12 backend command | 69 passed, 1 environment-marker skip |
| Separate genuine Mongo 7 Phase 12/13 command | **12 passed, 0 skipped** |
| Full backend | 815 passed, 12 environment-gated Mongo skips |
| Current POC catalogue selection | 456 passed, 1 environment-marker skip |
| Representative security selection | 19 passed |
| Ruff | Pass; inaccessible protected-cache warnings only |
| mypy | Success, 78 source files |
| `pip check` | No broken requirements |
| Contract discovery | 44 passed |
| Frontend dependency tree | Exit 0; optional platform/feature dependencies only |
| Frontend typecheck | Pass |
| Frontend Vitest | 103 passed across 3 files |
| Frontend production build | Pass; 45 modules transformed |
| Windows lifecycle | 17 passed in 189.385s |
| Secret-check unit suite | 5 passed |
| Pre-PR checker unit suite | 37 passed |
| Protected-boundary-safe secret scan | 380 files, 0 findings |
| `git diff --check` | Exit 0; line-ending notices only |

The three Pydantic warnings in the backend/catalogue runs are produced by existing adversarial malformed-provider tests and are not failures. The catalogue's one skip and the full suite's 12 skips are ordinary no-URI markers; the separately required physical Mongo run passed all 12 tests.

Frontend tests initially encountered sandbox `spawn EPERM`; the same suite passed under the required local process permission. Pre-PR checker unit tests initially could not create temporary Git repositories under sandbox restrictions; the qualifying rerun passed 37/37. These were host restrictions, not product failures.

The production `scripts/pre_pr_check.py` was not run against the intentionally dirty, uncommitted tree, as required by the brief and repository protocol.

## 13. Diff audit

Before this report, the tracked Phase 13 delta contained 47 modified files, 961 insertions, and 165 deletions. The remediation increase is confined to the four prior findings:

- exact persistence-discriminator code and tests;
- frontend authoritative refresh/timestamp behavior and tests;
- physical Mongo v2/immutability assertions;
- recursive exact route-inventory and adverse included-router test;
- execution-report evidence describing that remediation.

The broader working delta remains Phase 13 implementation/supporting tests, UI, CI, documentation, and authenticated regression harness changes. No connector interface, ACRA/GoldTier contract, package manifest, lockfile, `.env`, credential file, or raw sponsor artefact changed. `apps/backend/pyproject.toml`, `apps/frontend/package.json`, and `apps/frontend/package-lock.json` have no diff.

`git diff --check` passes. No path is staged. Lifecycle metadata is absent; no listener remains on ports 8000, 5173, or 27018; and the temporary Mongo container is absent. This re-gate created only `.ai-pipeline/reports/PHASE_13_REQUALITY_GATE.md` and did not modify either prior report or any implementation file.

## 14. Findings

No new remediation-related finding was identified.

P13-QG-001: **CLOSED**
P13-QG-002: **CLOSED**
P13-QG-003: **CLOSED**
P13-QG-004: **CLOSED**

Critical: **0**
High: **0**
Medium: **0**
Low: **0**

## 15. Final metrics

| Metric | Result |
|---|---:|
| Prior findings closed | 4/4 |
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |
| Current routes classified | 42/42 exact |
| Unclassified included-router adverse probe | Rejected at 43/42 |
| Genuine Mongo 7 | 12 passed, 0 skipped |
| Focused backend | 69 passed, 1 marker skip |
| Full backend | 815 passed, 12 marker skips |
| Frontend | 103 passed |
| Contract | 44 passed |
| POC catalogue | 456 passed, 1 marker skip |
| Windows lifecycle | 17 passed |
| Secret/pre-PR unit tests | 5 passed / 37 passed |

## 16. Remaining limitations

- Authentication and sessions remain local POC-only; Q-016 still governs production IdP, role, assignment, priority, and identity-governance policy.
- This PASS does not establish live ACRA, PingFed, real GoldTier, production RBAC, regulatory audit, distributed session, or Ready-for-Approval readiness.
- The feature is uncommitted and the repository is intentionally dirty. Owner-controlled commit, fresh main-drift confirmation, clean-tree pre-PR check, push, CI, PR review, and repository-owner merge remain separate authorized steps.
- The full and catalogue runs intentionally lacked a persistent Mongo URI, but the mandatory separate Mongo 7 run supplied direct physical evidence with no skips.
- The repository scanner's unfiltered entry point was not used because it would open the protected untracked artifact. Its scanning logic ran over the explicitly permitted 380-file set with zero findings.

Evidence classification: command/test results are **measured**; code/diff/runtime state is **observed**; closure/readiness conclusions are **inferred** against the declared planner and contract; production policy beyond D-034/Q-016 remains **unknown** and outside scope. Confidence grade: **A** for the targeted Phase 13 closure and regression claims.

### Aegis impact and safety receipt

- **Key judgment:** all four prior defects are closed at their canonical owners, and mandatory physical-Mongo plus broad regression evidence supports the targeted PASS.
- **Avoided misfix:** no duplicate schema path, browser sort, persistence adapter, authorization owner, or test-only product accommodation was introduced.
- **Boundary held:** review-only; one report created; protected/cache/user state preserved; temporary infrastructure removed.
- **Baseline alignment:** aligned with the Phase 13 planner, architecture, D-034, access/priority contract, and exact `origin/main` baseline.
- **Complexity control:** within budget; the remediation adds localized guards/refetches/assertions without a new fallback or responsibility owner.
- **Evidence strength:** direct static inspection, independent falsifying probes, 12/12 Mongo 7, focused and full suites, confidence A.
- **Uncovered risk:** only declared production/live-integration non-goals and the owner-controlled Git/CI workflow remain.
- **Next most valuable verification:** after the owner commits and integrates any future main drift, run the clean-tree production pre-PR check and repository CI without altering the reviewed Phase 13 semantics.

Goal Closure:

- Goal status: **done** for the requested independent re-quality gate.
- Success evidence: four finding closures, zero blocking findings, mandatory Mongo pass, and complete required regressions.
- Stop state: report delivered at the owner-controlled integration boundary.
- Non-goals respected: no remediation, implementation edits, staging, commit, push, merge, rebase, reset, clean, branch switch, or next-phase work.

## 17. Final verdict

All PASS criteria are satisfied: Critical/High/Medium are zero, P13-QG-001 through P13-QG-004 are closed, and the genuine Mongo 7 Phase 12/13 suite passed without skips. Phase 13 is ready to enter the separately authorized owner-controlled integration workflow.

PASS — PHASE 13 READY FOR OWNER-CONTROLLED INTEGRATION
