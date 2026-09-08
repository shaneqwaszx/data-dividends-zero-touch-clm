# Phase 13 Final Quality-Gate Remediation

Date: 2026-09-08
Role: original implementation/remediation owner (not the independent quality gate)

## 1. Executive summary

**Result: PASS — ready for a fresh independent quality gate.** The two High findings
and two Low findings from the prior gate are remediated. The requested historical-list
priority filters/sort are implemented behind existing authentication and RBAC. All
required qualifying checks pass. No commit, stage, push, merge, rebase, reset, clean,
stash, or branch switch was performed.

## 2. Branch, baseline, and origin state

- Branch: `fix/phase13-demo-login-identities`.
- `HEAD`, refreshed `origin/main`, and merge-base are all
  `dcb52937d46882a5b1b6ba7f2d545829e6fda662`.
- The index is empty. The complete Phase 13 implementation/remediation remains
  intentionally uncommitted.

## 3. Failed quality-gate findings addressed

- High: request-controlled `Host` expanded browser-origin trust.
- High: ordinary tests inherited root `.env` and wrote to shared `clm_poc`.
- Low: a transient physical-Mongo teardown leaked remote driver detail and temporarily
  retained one test database.
- Low: two task-owned RUF100 findings and non-formatted task-owned Python.
- Owner addition: historical case-list priority filtering/sorting in the existing API
  and relevant frontend views.

## 4. Browser-origin root cause

`BrowserOriginPolicy.request_is_trusted` derived an accepted origin from
`request.url`, whose authority was populated from request-controlled `Host`, and unioned
it with configured origins. A shared URL-to-origin helper also discarded paths, queries,
and fragments, so malformed `Origin` values could normalize to an accepted origin.

## 5. Browser-origin remediation

`PHASE13_BROWSER_ORIGIN` is the single backend-owned canonical production origin.
Development/test owns exact backend and Vite loopback origins. Production requires one
explicit exact HTTPS origin; missing, HTTP, path-bearing, or malformed values fail before
persistence initialization. Origin/Referer checks consult configured origins only.

## 6. Host-spoof proof

Adversarial login coverage sends a foreign `Host` plus the matching foreign `Origin`.
The response is `403 CSRF_VALIDATION_FAILED`. Neither `Host` nor forwarding metadata can
expand the configured allowlist.

## 7. Malformed-Origin proof

Tests reject Origin values with `/`, a path, query, fragment, userinfo, invalid port,
`null`, and multi-origin syntax. A valid same-origin Referer may retain path/query.
Foreign Referer remains `403`. Exact default-port normalization is deterministic.

## 8. Ordinary-test isolation root cause

Ordinary tests constructed `Settings(app_env="test")`; Pydantic still loaded the root
`.env`, allowing root `CLM_PERSISTENCE_MODE=mongo`, URI, and `MONGO_DATABASE=clm_poc` to
reach application composition during collection/test execution.

## 9. Ordinary-test isolation architecture

`apps/backend/tests/phase13_test_settings.py` owns deterministic ordinary settings. The
central conftest applies safe environment values before application imports and before
every test: memory persistence, no service URI, and non-shared database namespace.
Phase 13 ordinary app tests use `ordinary_test_settings()`; physical tests retain an
explicit separate path.

## 10. Hostile-environment proof

The ordinary Phase 13 suite passed while its parent environment explicitly contained
`CLM_PERSISTENCE_MODE=mongo`, `MONGO_DATABASE=clm_poc`, and the intentionally dead
`mongodb://127.0.0.1:1`. The child probe composed an application in memory. Any attempted
Mongo initialization would have failed this proof.

## 11. Physical-Mongo explicit opt-in

Phase 12/13 physical tests alone receive `PHASE12_MONGO_URI` internally and construct
`Settings` with `_env_file=None`, `clm_persistence_mode="mongo"`, the explicit URI, and
a generated isolated database. Ordinary tests do not infer Mongo from root settings.

## 12. Test-database safety guard

One shared helper accepts only `^clm_p(?:12|13)_[0-9a-f]{24}$`. It rejects `clm_poc`,
arbitrary suffixes, other phases, traversal-like values, and blank names before any drop.
The physical runner and dashboard validator use the same owner.

## 13. Shared `clm_poc` incident state

The prior quality gate created 30 shared records (27 Team A, 3 Team B). They remain
untouched pending owner-authorized cleanup. No seeder, completion, update, deletion, or
validator write was run against shared `clm_poc` during this remediation.

## 14. Shared database before/after non-mutation evidence

- Read-only count before remediation: **46**.
- Read-only count after all physical verification: **46**.
- Difference: **0**.
- The 30 quality-gate-created records were not removed, updated, completed, or hidden.

## 15. Physical-Mongo cleanup and redaction remediation

Cleanup validates the database name, retries three times with bounded backoff, drops,
and verifies absence via database listing. Exhaustion reports only a safe exception class
and uses `--tb=no` in the physical runner. Unit proofs cover rejection, retry success,
post-drop verification, and removal of connection/host detail. The final remaining-test-
database count was zero.

## 16. Ruff remediation

The two unused `# noqa: E402` directives were removed by moving the password-hash helper
imports into its runtime entry point. Task-owned Ruff now reports `All checks passed!`.

## 17. Priority-filter backend contract

The existing `GET /api/clm/zero-touch/cases` accepts typed
`priority_filter=all|prioritised|unset|10|9|8|7|6|5|4|3|2|1`. Semantics are all
authorized cases, non-null, null, or exact priority. Invalid values return `422`; no
duplicate history endpoint was added.

## 18. Priority-sort backend contract

`priority_sort=highest_first|lowest_first`, defaulting to `highest_first`. Numbered
priorities sort in the requested direction; unset always sorts last. Existing
automation `updated_at` then canonical case-ID descending tie-break behavior is retained.

## 19. Priority filter/sort RBAC

`CaseQueryService` now explicitly performs canonical case load and authorization first,
then status/priority filtering, then ordering. Tests prove a Team A filter cannot reveal
a matching Team B case while Director receives the authorized cross-team result.

## 20. Priority filter/sort frontend

Cases and Onboarded expose All, Prioritised, Unprioritised, exact 10..1 filters and both
sort directions. Requests go to the existing authenticated backend list endpoint; React
does not obtain global history or perform authorization filtering.

## 21. Dashboard non-regression

Dashboard remains an authenticated provider-free projection. Its fixed top-active
canonical highest-first order is unchanged and independent of historical-list controls.
Focused Dashboard coverage and the full frontend/backend suites pass.

## 22. Focused backend tests

Final falsifying suite over auth/RBAC, priority, hostile isolation, and Mongo-test safety:
**99 passed**. The wider focused Phase 13 suite (including seeder and Dashboard) also
passed **114 tests** before final contract naming; the final affected suites were rerun.

## 23. Full backend tests

Qualifying current-code command `python -m pytest apps/backend/tests -p no:cacheprovider`:
**876 passed, 12 skipped, 3 warnings**. Skips are the explicit physical opt-in tests.
Warnings are existing Phase 06 Pydantic serializer warnings. One earlier run had a single
live-memory HTTP seeder timeout; the test passed immediately in isolation and the two
subsequent complete backend runs passed, including the final current-code run.

## 24. Physical-Mongo tests

Guarded runner result: **12 passed, 0 failed, 0 skipped** in 38.51 seconds. Only generated
ephemeral databases were used; post-run remaining count was **0**. A first runner launch
failed locally before test collection due an import path and was corrected without any
Mongo operation.

## 25. Frontend

- `npm run typecheck`: PASS.
- `npm test -- --run`: **116 passed across 4 files**.
- `npm run build`: PASS; 46 modules transformed.
- Initial sandboxed Vitest startup hit Windows `spawn EPERM`; approved qualifying runs
  passed.

## 26. Contracts

Accepted contract suite with explicit memory/test-safe environment and required
`PYTHONPATH`: **44 passed**.

## 27. Windows lifecycle

Accepted Windows lifecycle suite with explicit memory/test-safe environment:
**17 passed** in 181.44 seconds. It covered real local backend/frontend lifecycle and
cleanup without inheriting shared Mongo configuration.

## 28. Mypy, dependency, and diff checks

- `python -m mypy apps/backend/app`: PASS, 80 source files.
- `python -m pip check`: PASS, no broken requirements.
- `git diff --check`: PASS; only Windows LF/CRLF notices.

## 29. Task-owned Ruff and format

- Ruff check over the explicit 29-file task-owned Python set: PASS.
- Ruff format check over the same set: **29 files already formatted** after remediation.
- No repository-wide format or arbitrary untracked-file scan was run.

## 30. Secret-scanner and pre-PR unit checks

Only `tests/test_check_secrets.py` and `tests/test_pre_pr_check.py` were run:
**42 passed**. The production secret scanner and its help mode were not run. The first
sandboxed unit attempt could not create temporary Git repositories; the approved
qualifying rerun passed.

## 31. Files changed

The complete uncommitted Phase 13 working set includes:

- Backend source: `.env.example`, `api_auth.py`, `composition.py`, `config.py`,
  `domain/access.py`, new `domain/dashboard.py`, `main.py`, `authorization.py`,
  `case_query.py`, `clm_orchestration.py`, new `dashboard.py`, `onboarding.py`, and
  `zero_touch_orchestration.py`.
- Backend tests/helpers: `conftest.py`, `phase13_test_clients.py`, new
  `phase13_test_settings.py`, `test_phase12_real_mongo.py`, `test_phase13_auth_rbac.py`,
  `test_phase13_dashboard.py`, `test_phase13_demo_scripts.py`, new
  `test_phase13_mongo_test_safety.py`, `test_phase13_priority.py`,
  `test_phase13_real_mongo.py`, and new `test_phase13_test_isolation.py`.
- Frontend: `App.tsx`, `api.ts`, `types.ts`, `design-system.css`, Cases, Dashboard,
  HomeOnboarding, LoginPage, OnboardedClients, and PriorityControl pages plus App,
  Dashboard, Phase13AuthPriority, and UiV2Integration tests.
- Scripts/lifecycle: `generate_phase13_demo_password_hashes.py`,
  `seed_phase13_demo.py`, new `mongo_test_safety.py`, new
  `run_phase13_physical_tests.py`, new `validate_phase13_mongo_dashboard.py`, and
  `tests/test_demo_lifecycle_windows.py`.
- Documentation/reports: `PROJECT_CONTEXT.md`, Phase 13 architecture, access/priority
  contract, decision log, demo runbook, configuration reference, the three prior Phase
  13 implementation reports, the independent final-quality-gate report, and this report.

## 32. Git status

Tracked task files are modified and task-created files/reports remain untracked; the index
is empty. The protected untracked artifacts whose names begin `e workspace and
multi-document intake` and `tatus --short`, and protected pytest-cache directories, were
not content-read, hashed, modified, deleted, staged, or committed. No command targeted
their contents; the initial required Git-status snapshot only reported the two paths and
returned access-denied warnings for the protected cache directories. Final status used
`--untracked-files=no` to avoid another untracked traversal. Repository status is
intentionally dirty for owner review.

## 33. Limitations, residual risk, and blockers

- No independent re-quality-gate was performed; that remains the next authority step.
- Production IAM, live ACRA, live GoldTier/PingFed, distributed workflow, retention, and
  sponsor policy questions remain outside this Phase 13 remediation.
- The 30 incident records remain in shared `clm_poc` pending separately scoped owner
  authorization. This is intentional confirmation-first data governance, not a code
  blocker.
- No unresolved Critical, High, or Medium issue is known within the assigned scope.

## 34. Re-quality-gate readiness and safety receipt

**Ready for independent re-QG; confidence A for the assigned remediation scope.** Fresh
direct and regression evidence covers the origin boundary, Host/malformed inputs,
ordinary/hostile test isolation, guarded physical Mongo with zero leftovers, unchanged
shared count, RBAC-first filtering, both sort directions, Dashboard, frontend, contracts,
lifecycle, static checks, and unit-only safety tooling.

Aegis impact and safety receipt: the key judgment was to retire request-derived origin
authority and root-environment test persistence rather than add exceptions. The boundary
held: no shared data mutation, no Phase 14/policy/UBO expansion, no protected-artifact
inspection, and no Git integration action. Baseline alignment is restored from
implementation drift to the Phase 13 security/test-safety contract. Complexity remains
within budget through focused owners (`BrowserOriginPolicy`, ordinary test settings,
Mongo test safety, and `CaseQueryService`); no duplicate API or compatibility fallback
was added. Residual risk is limited to out-of-scope production integrations and owner-
controlled disposition of shared incident data. The next most valuable verification is
the independent combined Phase 13 quality gate against this unchanged working tree.
