# Phase 14 Final Independent Re-Quality Gate

Date: 2026-09-11
Reviewer role: final independent Phase 14 re-quality-gate reviewer; this reviewer did not implement or remediate Phase 14.
Result: **FAIL**
Verdict: **FAIL — P14-QG-001, P14-QG-002, AND P14-QG-003 ARE CLOSED, BUT THE REQUIRED PHYSICAL-MONGO VERIFIER HAS A REPRODUCIBLE REQUEST-CONTRACT DEFECT AND DOES NOT COVER THE COMPLETE REQUIRED PHYSICAL MATRIX.**

## 1. Reviewer independence

The implementation and remediation handoff was treated as untrusted. Production exception,
lifecycle, deletion, cache, API, authorization, persistence, and test paths were inspected.
Fresh Python and TanStack Query harnesses were built outside the repository rather than
accepting implementation-authored assertions alone. No subagent, implementation author, or
remediation author participated. No implementation, test, existing report, execution report,
planner, or documentation file was modified by this gate.

## 2. Baseline and drift

- Branch: `phase/14-case-management-performance`
- `HEAD`: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- Fetched `origin/main`: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- Merge base: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- `HEAD..origin/main`: empty
- Initial main drift: none
- Initial tracked-only status: expected unstaged Phase 14 delta; staged path list empty

The pre-gate fetch succeeded. The required stop condition was not triggered.

## 3. P14-QG-001 independent production attack

**Status: CLOSED.** Production `ZeroTouchOrchestrator.create_case` reserves identity, enters
the one canonical `OnboardingService.case_lock(case_id)`, completes onboarding, initial CLM,
automation, and the optional demo registration inside that reentrant boundary, and performs
bounded same-case rollback before releasing it. `ClmOrchestrationService._lock_for` delegates
to that same lock owner; no second per-case lock map was found.

A fresh deterministic harness used a distinct `PrimaryFailure` instance with code
`ZERO_TOUCH_CASE_CREATION_FAILED` and safe message `Primary establishment failure.` at the
late demo-registration stage. A distinct `RollbackFailure` with a private sentinel was then
raised by rollback. The caller observed the exact original primary object and subclass; code,
safe message, and type were unchanged. The rollback error was retained only as the primary's
explicit `__cause__`. Its private sentinel did not appear in `str(primary)` or the HTTP body,
and no false success occurred.

## 4. Rollback-success control

**PASS.** The same primary exception instance remained externally observed when rollback
succeeded. The attempted onboarding, CLM, automation, documents, ownership, reconciliation,
demo, and portfolio state was absent. An unrelated established case remained present. Source
inspection and a provider-bomb deletion harness confirmed no Registry, IDP, Ownership-provider,
or GoldTier deletion method is invoked.

## 5. Rollback double-failure preservation

**PASS.** Independent result:

- primary identity/type/code/safe message preserved;
- rollback failure retained only as `__cause__`;
- rollback internal detail absent from the primary/public projection;
- attempted aggregate absent;
- unrelated aggregate preserved;
- no false success.

The implementation-authored adversarial selection independently reran as **3 passed in
1.24s**.

## 6. API mapping attack

**PASS.** The actual demo HTTP path was driven with simultaneous establishment and rollback
failure. It returned exactly `409` with the primary
`ZERO_TOUCH_CASE_CREATION_FAILED / Primary establishment failure.` mapping. No rollback
message, persistence/delete error, raw exception, or `500`/`503` replacement appeared.

## 7. Lifecycle concurrency regressions

**PASS in memory.** The focused 17-test Phase 14 suite and direct production-path inspection
verified:

- create versus DELETE: DELETE waits; final aggregate absent;
- demo registration versus DELETE: DELETE waits; no post-delete demo resurrection;
- established mutation versus DELETE: mutation completes first; final aggregate absent;
- two concurrent DELETE operations: one succeeds and the follower returns safe not-found;
- stale save after delete: update-only save cannot recreate the case.

No competing lifecycle lock owner or route-local lock map was found.

## 8. Memory hard delete

**PASS.** A fresh rich-flow harness completed a case through document, ownership,
reconciliation, CLM, automation, and Mock target execution, added demo scenario/recovery
transient and non-default case provider binding state, then deleted through the authorized
HTTP path. Post-delete checks found all case-owned state absent: onboarding, automation, CLM,
documents, ownership, reconciliation, target execution, demo scenario, demo transient,
provider binding, portfolio/list input, and detail source. The unrelated case remained.
Provider boundaries were replaced with failure probes before DELETE; none was invoked. The
response was an empty `204`.

## 9. P14-QG-002 cache-race regression

**Status: CLOSED.** Production `caseDeletedEffect` awaits cancellation of the authenticated
user's list family, Dashboard, detail, documents, and ownership queries before filtering or
removing cache state. Queue and detail callers await server DELETE and then await the effect.

A fresh real-`QueryClient` harness used old list and Dashboard promises that ignored abort,
applied the production effect, and resolved both old responses afterward. The deleted list row
and Dashboard did not republish. A different user's list was unchanged. A later legitimate
refetch populated a fresh result. Separate production-transport checks verified that a pending
DELETE keeps the row, a failed `503` keeps the row, and removal occurs only after `204`.

Focused frontend evidence: **10 passed in 1 file**. Full frontend evidence: **126 passed in
5 files**.

## 10. P14-QG-003 execution-evidence review

**Status: CLOSED for the stated evidence claims.** The execution report now names the exact
dialog path `apps/frontend/src/pages/DeleteCaseDialog.tsx`, identifies `python -m pytest` from
`apps/backend` as the canonical full-backend command, and reports the independently reproduced
backend and formatter evidence accurately.

The separate physical-test finding in section 17 means the report's expectation that CI can
supply the complete physical proof is not currently achievable, but it does not change the
correctness of the original P14-QG-003 dialog/formatter/backend corrections.

## 11. Formatter attribution

The direct bounded command over all 33 final classified Python paths is non-green:
**27 files would be reformatted; 6 are already formatted**. Independent relative-path,
LF-normalized baseline attribution reproduced exactly:

- Phase 14-introduced semantic formatter defects: **0**
- retained baseline semantic findings: **10**
- EOL-only paths: **17**
- clean paths: **6**

No formatting was applied and no repository-wide formatter pass is claimed.

## 12. Canonical backend evidence

From the exact `apps/backend` directory, the canonical command `python -m pytest` ran with
dotenv loading disabled before imports, ordinary persistence forced to memory, bytecode
disabled, and pytest cache redirected outside the repository. Result: **914 passed, 13
skipped, 3 warnings in 83.21s**; 927 collected outcomes. This exactly reproduces the execution
report's `927 / 914 / 13 / 3` evidence.

## 13. Backend and static evidence

| Check | Fresh result |
|---|---:|
| Phase 14 focused | 17 passed in 1.72s |
| Rollback adversarial selection | 3 passed in 1.24s |
| Impacted CLM/zero-touch/provider | 244 passed, 3 warnings in 19.41s |
| Phase 13 auth/priority/Dashboard | 114 passed in 25.80s |
| Pre-Phase-12 multi-document | 32 passed in 4.24s |
| Full backend | 914 passed, 13 skipped, 3 warnings in 83.21s |
| Ruff lint, 32 explicit task-owned backend/tool paths | all checks passed |
| Ruff lint, root Windows lifecycle baseline file | 13 retained baseline findings |
| Ruff format, 33 classified paths | 27 would reformat; 6 clean; attribution in section 11 |
| MyPy `app` | success; 83 source files |
| `pip check` | no broken requirements |

The three backend warnings are the existing adversarial Pydantic serializer warnings. The
initial sandboxed Windows/pre-PR unit attempts were invalidated because owned child-process
termination and disposable Git initialization were denied; scoped reruns below passed.

## 14. Frontend evidence

| Check | Fresh result |
|---|---:|
| Focused Phase 14 Vitest | 10 passed in 1 file |
| Typecheck | passed |
| Full Vitest | 126 passed in 5 files |
| Production build | passed; 94 modules transformed |
| `npm.cmd audit` | 0 vulnerabilities |

The first focused Vitest attempt was sandbox-blocked by `spawn EPERM`; the scoped rerun passed.
No audit fix or dependency modification was performed.

## 15. Contracts, lifecycle, and security

- Contract unittest discovery: **44 passed**.
- Windows lifecycle: **18 passed in 202.215s** under explicit memory isolation.
- Secret-checker units: **5 passed**.
- Pre-PR checker units: **37 passed in 46.826s**.
- GoldTier examples: **19 valid, 19 invalid/quarantined, 48 not validated**.
- Bounded secret scan: **61 exact Phase 14 tracked/new paths, 0 files with findings**.
- Actual `scripts/pre_pr_check.py`: not run, as required for this uncommitted tree.
- Broad `scripts/check_secrets.py`: not run, to avoid protected/unrelated artifacts.

DELETE remains authenticated, CSRF-protected, exact-Origin/Referer protected, and authorized
inside the canonical case lock. Director/RM/Onboarder decisions and inaccessible/absent
non-disclosure remain fail-closed. No request role/team authority, raw rollback detail,
browser-persistent cache, cross-user cache mutation, external deletion, or sensitive logging
addition was found.

## 16. Physical Mongo availability

`PHASE12_MONGO_URI_CONFIGURED=NO`; therefore **PHYSICAL_MONGO=SKIPPED**. No URI value was
printed, no database was generated, and no ambient/shared Mongo was used.

The required physical proof remains absent: hard delete, restart absence, stale-save and
revision conflict behavior, durable-orphan absence, unrelated-record preservation, cleanup,
and final generated-database absence were not executed.

## 17. Findings

| ID | Severity | Evidence | Consequence / required remediation |
|---|---|---|---|
| P14-FRQG-001 | **Medium** | `apps/backend/tests/test_phase14_real_mongo.py:71-72` posts `files={...}` multipart to the intake route, while `apps/backend/app/main.py:871-880` accepts a raw request body and requires the filename through `X-Document-Name`. Replaying the physical test's exact request shape against the same memory application returned `422 DOCUMENT_NAME_INVALID` before deletion. The physical test also creates no unrelated durable case and contains no separate pre-delete revision-race/409 proof. | The opt-in physical suite cannot currently provide the mandatory Phase 14 physical proof even when a URI is configured. Align the test request with the production raw-body contract and add the missing unrelated-record and revision-conflict assertions, then run it only against generated `^clm_p14_[0-9a-f]{24}$` storage with verified cleanup. |

Finding totals: **Critical 0; High 0; Medium 1; Low 0.** The finding is a material required
verification defect, not evidence that the memory production DELETE path failed.

## 18. Incident receipts and data safety

- `.env` accessed or loaded by this review: **NO**. A process bootstrap forced every
  `BaseSettings` construction to `_env_file=None`; activation was independently confirmed.
- shared `clm_poc` inspected: **NO**.
- shared `clm_poc` written: **NO**.
- Phase 14.5 worktree accessed: **NO**.
- protected artifacts accessed/enumerated/scanned: **NO**.
- current lifecycle tests explicitly memory-isolated: **YES**.
- historical ambient-database receipt preserved without investigation: **YES**.
- prior independent re-QG indirect `.env` receipt preserved without investigation: **YES**.

No Mongo URI/host, credential, password hash, session ID, cookie, or CSRF value was printed.

## 19. Final implementation and readiness verdict

**RESULT: FAIL.** The three assigned remediation findings are independently closed, and the
memory implementation passes the required exception, lifecycle, hard-delete, cache, RBAC,
non-disclosure, CSRF, static, frontend, contract, and regression attacks. However, the only
Phase 14 physical Mongo suite is known to fail before reaching deletion and omits required
physical assertions. This is a new Medium verification defect, so the special
physical-unavailable `BLOCKED — implementation accepted` outcome does not apply.

- P14-QG-001: **CLOSED**
- P14-QG-002: **CLOSED**
- P14-QG-003: **CLOSED**
- Memory hard delete: **PASS**
- Resurrection safety: **PASS in memory; physical proof outstanding**
- Cache: **PASS**
- DELETE RBAC: **PASS**
- Non-disclosure: **PASS**
- CSRF/browser source: **PASS**
- Physical Mongo: **SKIPPED**
- Implementation accepted: **NO**
- Ready for owner-controlled commit: **NO**
- Ready for PR: **NO**
- Ready for merge: **NO**

Remaining blockers:

1. Repair the opt-in physical Mongo test's upload contract and add its missing unrelated-case
   and revision-conflict coverage.
2. Run the repaired suite with an explicitly approved URI and only a generated
   `clm_p14_<24 lowercase hex>` database; verify cleanup and final database absence.
3. Obtain owner direction separately for the two preserved historical incident receipts;
   do not inspect or mutate shared data under this gate.
4. After authorized commit/latest-main integration and a clean tree, run the actual
   `python scripts/pre_pr_check.py` before PR-ready language.

Git action receipt: implementation was not modified; nothing was staged, committed, amended,
pushed, merged, rebased, reset, stashed, or cleaned; and no branch switch occurred. This final
re-quality-gate report is the only repository file created by the reviewer.
