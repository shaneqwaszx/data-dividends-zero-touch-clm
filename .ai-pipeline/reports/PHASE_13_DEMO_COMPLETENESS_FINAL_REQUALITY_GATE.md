# Phase 13 Demo Completeness Remediation — Fresh Independent Re-Quality Gate

## 1. Executive summary

**Result: FAIL.** The four findings from the previous final gate are independently
resolved: request `Host` no longer expands origin trust; ordinary tests remain in
memory under a hostile Mongo-shaped parent environment; task-owned Ruff/format pass;
and guarded physical Mongo cleanup/redaction passes with no temporary database left.
The requested priority filter/sort addition and the broader Phase 13 regression suite
also pass.

One new **Medium** security-contract finding prevents PASS. The browser-source policy
reads only the first `Origin` and `Referer` field. Production-mode probes containing a
trusted first field plus a foreign duplicate were accepted: login returned `200`, an
authenticated unsafe mutation returned `201`, and a duplicated Referer returned `200`.
This violates the explicit requirement to reject multiple/ambiguous Origin
serialization and leaves login/unsafe-mutation origin parity incomplete.

Evidence labels in this report are **MEASURED** for executed commands/probes,
**OBSERVED** for code/diff/document inspection, **INFERRED** for severity/readiness, and
**UNKNOWN** where live or sponsor-controlled capability was not established.

## 2. Branch / baseline / origin-main drift

| Item | Evidence |
|---|---|
| Branch | **MEASURED:** `fix/phase13-demo-login-identities` |
| Declared base | **MEASURED:** `dcb52937d46882a5b1b6ba7f2d545829e6fda662` |
| `HEAD` | **MEASURED:** `dcb52937d46882a5b1b6ba7f2d545829e6fda662` |
| Final fetched `origin/main` | **MEASURED:** `dcb52937d46882a5b1b6ba7f2d545829e6fda662` |
| Merge base | **MEASURED:** same SHA |
| `HEAD..origin/main` | **MEASURED:** empty |
| Index / unresolved paths | **MEASURED:** empty / empty |
| Tracked worktree | **MEASURED:** expected 39 modified files |

No main drift was found. The complete implementation remains intentionally
uncommitted in the working tree.

## 3. Previous failed findings

| Previous finding | Re-QG result | Direct evidence |
|---|---|---|
| P13-DC-FQG-001 — Host-derived production trust | **RESOLVED** | **MEASURED:** foreign Host + matching foreign Origin `403`; foreign Host + configured Origin accepted based on configuration; forwarding headers did not expand trust. |
| P13-DC-FQG-002 — ordinary tests could use shared Mongo | **RESOLVED** | **MEASURED:** hostile parent environment test passed; standard full backend ran without a persistence override and passed `876`, with physical tests skipped. Shared count stayed `46`. |
| P13-DC-FQG-003 — task-owned Ruff/format | **RESOLVED** | **MEASURED:** Ruff PASS; `29 files already formatted`. |
| P13-DC-FQG-004 — physical teardown/redaction | **RESOLVED** | **MEASURED:** eight safety tests passed; physical runner passed `12`, emitted sanitized output, left `0` temporary databases. |

The remediation owner's report was treated as a claim source only; each result above
was reproduced independently.

## 4. Review scope

**OBSERVED:** The review covered AGENTS.md, project context, the Phase 13 planner,
repository role files, integration/security/regression/CI workflows, branch protocol,
the five mandatory Phase 13 handoff/gate reports, changed source/tests/docs, task-owned
new files, and the complete tracked diff against `origin/main`.

The gate was review-only. No implementation, test, configuration, ordinary
documentation, shared-data cleanup, or Phase 14 change was made. The sole repository
write is this report.

## 5. Production canonical origin configuration

**OBSERVED / MEASURED: PASS.** `PHASE13_BROWSER_ORIGIN` is the backend-owned production
authority. Production requires one explicit HTTPS origin; missing, HTTP, path-bearing,
or non-origin values fail before persistence initialization. Production does not add
the Vite origin. Development/test retains exact backend and Vite loopback origins.

## 6. Host-spoof remediation verification

**MEASURED: PASS.** The following production probes passed:

- configured Origin accepted;
- foreign Origin rejected;
- foreign Host + matching foreign Origin rejected;
- foreign Host + configured Origin accepted based on configured Origin;
- `Forwarded`, `X-Forwarded-Host`, and `X-Forwarded-Proto` did not add trust;
- authenticated unsafe mutation with foreign Host/Origin was rejected.

The original `200` Host-spoof exploit is no longer reproducible.

## 7. Strict Origin syntax

**MEASURED: FAIL overall.** A single serialized Origin correctly rejects `/`, path,
query, fragment, userinfo, malformed port, missing hostname, unsupported scheme,
`null`, and comma/space multi-origin strings. Default HTTPS port normalization passes.

However, `BrowserOriginPolicy.request_is_trusted` uses
`request.headers.get("origin")` at `apps/backend/app/api_auth.py:120`. With duplicate
header fields, trusted-first/foreign-second returned `200`, while the reverse order
returned `403`. The decision therefore depends on field order and does not reject an
ambiguous multiple-Origin request.

## 8. Referer semantics

**MEASURED: PARTIAL / FAIL overall.** A configured-origin Referer containing
`/cases/ABC?tab=1` is accepted; a foreign Referer and userinfo-bearing malformed
Referer are rejected. A trusted-first/foreign-second duplicate Referer returned `200`
because `request.headers.get("referer")` at `apps/backend/app/api_auth.py:123` reads one
field only. Referers containing a fragment were also accepted even though the accepted
contract names path/query support, not fragment-bearing field syntax. These behaviors
are included in P13-DC-RQG-001.

## 9. Session / CSRF / cookie non-regression

**OBSERVED / MEASURED:** Opaque server-side sessions, digest lookup, bounded expiry,
one active session per profile, relogin rotation, host-only HttpOnly `SameSite=Strict`
`Path=/api` cookies, production Secure cookies, fail-closed insecure-production
configuration, session-bound CSRF, CSRF-protected logout, generic login failure, and no
browser-storage authority remain covered by the focused pass.

Correct Vite Origin + wrong password reaches generic credential `401`; unknown user and
wrong password remain non-enumerating. Missing/wrong CSRF is rejected. The duplicate
browser-source defect prevents the combined origin/CSRF boundary from passing.

## 10. Ordinary-test isolation architecture

**OBSERVED: PASS.** `apps/backend/tests/conftest.py` applies memory-safe environment
values before application imports and before every test. `ordinary_test_settings()`
uses `_env_file=None`, fixes memory persistence, rejects persistence overrides, and uses
the non-shared `clm_ordinary_tests` namespace. Physical tests use a separate explicit
path.

## 11. Hostile-environment proof

**MEASURED: PASS.** With parent values `CLM_PERSISTENCE_MODE=mongo`,
`MONGO_DATABASE=clm_poc`, and dead loopback `MONGO_URI`, the dedicated isolation module
passed `2/2`; its child composition remained memory-backed. No Mongo initialization was
observed. The normal full backend suite then passed without manually overriding the
owner's root persistence configuration.

## 12. Physical Mongo explicit opt-in

**OBSERVED: PASS.** Phase 12/13 physical tests obtain `PHASE12_MONGO_URI` only through
the guarded runner and construct settings with `_env_file=None`, explicit Mongo mode,
the internally supplied URI, and generated isolated `clm_p12_*` / `clm_p13_*`
databases. They do not derive the test database from root `MONGO_DATABASE`.

## 13. Mongo test DB guard

**OBSERVED / MEASURED: PASS.** The shared helper full-matches
`^clm_p(?:12|13)_[0-9a-f]{24}$` before cleanup. Local tests passed generated p12/p13
names and rejected `clm_poc`, blank/arbitrary/wrong-phase/traversal-like names before
any drop call. The exact grammar also excludes suffixes and overlong names.

## 14. Cleanup retry / redaction

**OBSERVED / MEASURED: PASS.** Cleanup validates the name, uses three bounded attempts
with bounded linear backoff, verifies absence, fails on exhaustion, and retains only the
exception class/category. The physical runner uses `--tb=no`. Eight Mongo-safety tests
passed, including retry and redaction doubles. The qualifying physical run printed no
URI, hostname, credential, or topology detail.

## 15. Shared clm_poc before/after

**MEASURED:**

- `SHARED_CLM_POC_COUNT_BEFORE=46`
- `SHARED_CLM_POC_COUNT_AFTER=46`
- difference: `0`

The count operations were direct read-only projections. No application recovery,
seeder, update, completion, deletion, or cleanup was run against shared `clm_poc`.
The 30 prior incident records remain untouched.

## 16. Task-owned Ruff

**MEASURED: PASS.** Ruff check over the exact 29 modified/new task-owned Python files
returned `All checks passed!`.

## 17. Task-owned Ruff format

**MEASURED: PASS.** The same 29-file set returned `29 files already formatted`. No
repository-wide formatting command was run.

## 18. Priority filter API contract

**OBSERVED / MEASURED: PASS.** The existing
`GET /api/clm/zero-touch/cases` owns the typed
`all|prioritised|unset|10..1` filter. Omission/all returns every authorized case;
prioritised selects non-null; unset selects null; numeric members select exact values.
Invalid values return `422`. No duplicate list API was added.

## 19. Priority sort API contract

**OBSERVED / MEASURED: PASS.** `highest_first` and `lowest_first` are typed, with
highest-first as the default. Independent controlled-record probes returned
`10..1..unset` and `1..10..unset`; unset remained last in both directions.

## 20. Priority filter/sort RBAC

**OBSERVED / MEASURED: PASS.** `CaseQueryService` loads canonical automation/case
records, applies `CaseAccessPolicy`, then filters and sorts. Independent probes showed
Team A only Team A, Team B inverse coverage in focused tests, and Director both teams.
No actor/team/role query parameter exists.

## 21. Priority tie-breakers/default ordering

**OBSERVED / MEASURED: PASS.** Controlled equal-priority/equal-timestamp records
retained `automation.updated_at DESC` then `case_id DESC` under both primary sort
directions. Unset ties follow the same rule. All ten requested filter/sort combinations
and a zero-result case passed. Omitted parameters preserve the canonical highest-first
order. Dashboard top-active continues to call the default query and is independent of
UI list controls.

## 22. Frontend priority controls

**OBSERVED / MEASURED: PASS.** Cases and Onboarded render all/prioritised/unprioritised,
exact 10..1, and both sort directions. Defaults are all/highest-first. The API client
sends only typed non-default query parameters; React filters search/jurisdiction locally
without re-sorting backend rows or performing authorization. Backend order rendering,
combined query construction, Open/detail, sanitized failures, and no browser-storage
authority are covered by the 116-test frontend pass.

## 23. Priority-at-create non-regression

**OBSERVED / MEASURED: PASS.** Omitted/null and strict integers 1..10 are accepted;
zero, 11, negatives, floats, booleans, numeric strings, and arbitrary strings are
rejected before creation. Priority flows through zero-touch → CLM → onboarding into the
first case write. The frontend uses one create POST and no create-then-priority-PATCH.
Later PATCH remains supported and does not change automation `updated_at`.

## 24. Shared-store RBAC/direct-ID

**MEASURED: PASS.** Maya/Ethan see Team A, Sophia/Ryan see Team B, and Olivia sees both.
Cross-team detail and priority mutation in both directions match nonexistent-case `404`
status/body. Header/query/body spoofing does not alter server-authored scope.

## 25. Synthetic identities/team metadata

**OBSERVED / MEASURED: PASS.** Active IDs are `maya-lim`, `ethan-tan`, `sophia-ng`,
`ryan-lee`, and `olivia-koh`. Persisted IDs remain `TEAM_A`/`TEAM_B`. Display metadata
is DBS/OCBC Corporate Onboarding with common Corporate Client Onboarding type and
DBS/OCBC coverage. Director remains global.

## 26. Deterministic seeder

**OBSERVED / MEASURED: PASS in memory/isolated evidence.** First run is `10 created / 0
reused`; second run is `0 created / 10 reused`; each team has five cases with priorities
`10,8,5,1,unset`; final states are genuine `COMPLETED /
MOCK_GOLDTIER_SUBMITTED`. The seeder authenticates and uses application APIs only. It
was not run against shared `clm_poc`.

## 27. Memory mode

**MEASURED: PASS.** Ordinary memory composition, authentication, RBAC, Dashboard,
priority create/filter/sort, seeding, and process-restart clearing via the lifecycle
suite passed without Mongo connectivity.

## 28. Remote Mongo connectivity

**MEASURED:** URI configured `YES`; scheme `mongodb+srv`; target `REMOTE`; configured
mode `mongo`. The repository-owned ping returned `MongoDB connection successful.` No
URI or hostname was emitted.

## 29. Physical Mongo tests

**MEASURED: PASS.** The guarded runner completed `12 passed / 0 failed / 0 skipped` in
generated isolated databases. `PHYSICAL_TEST_DATABASES_REMAINING=0`. No test used
`clm_poc` as its write database.

## 30. Mongo restart durability

**MEASURED: PASS.** Isolated physical app recreation preserved case, team, priority,
status/outcome, schema v2, team authorization, Dashboard reconstruction, and canonical
history. Priority clear after restart also succeeded.

## 31. Provider-free historical reads

**MEASURED: PASS.** Counting connector evidence remained unchanged across list,
detail, and Dashboard reads after restart: provider historical-read calls = `0` for
Registry/ACRA, IDP, ownership, and GoldTier.

## 32. Dashboard architecture/RBAC

**OBSERVED / MEASURED: PASS.** The authenticated route calls `CaseQueryService` before
`DashboardService`; there is no provider or persistence-mode branch. Team A, Team B,
and Director scoping passed in memory and isolated Mongo evidence. Unauthenticated
access is `401`; query/header spoofing does not alter scope.

## 33. Dashboard metrics/distributions

**MEASURED: PASS.** Totals, completed/non-completed, completion rate,
prioritised/unprioritised, exact canonical status distribution, priority 10..1 plus
unset, authorized team distribution, recent cases, and fixed top-active cases passed.
No SLA/risk/approval/BI meaning was introduced.

## 34. Dashboard trend

**OBSERVED / MEASURED: PASS.** The trend contains 30 UTC calendar days oldest to
newest, zero-filled, with created values from stable automation `created_at` and
completed values from exact completed timestamps. Authorization precedes aggregation
and provider calls remain zero.

## 35. Route inventory

**MEASURED: PASS.** The focused suite verified all 43 current operations are classified.
The only intentionally public operations remain `GET /health` and
`POST /api/auth/login`; Dashboard and case query/filter/sort are authenticated.

## 36. Focused backend

**MEASURED:** the core remediation selection passed `99 / 0 / 0`; the wider focused
auth/RBAC/priority/isolation/Mongo-safety/seeder/Dashboard selection passed
`114 / 0 / 0` in 21.38 seconds.

## 37. Full backend

**MEASURED: PASS.** The exact normal command
`python -m pytest apps/backend/tests -p no:cacheprovider`, without a manual persistence
override, returned `876 passed / 0 failed / 12 skipped / 3 warnings` in 62.44 seconds.
The skips are explicit physical tests; the three warnings are known malformed-provider
Pydantic serializer warnings.

## 38. Frontend

**MEASURED:** typecheck PASS; Vitest `116 passed / 0 failed` across four files; build
PASS with 46 modules. Vitest/build required an approved local-process rerun after the
sandbox blocked esbuild spawn. Build output was directed to a verified temporary
directory and removed.

## 39. Contracts

**MEASURED: PASS.** Test-safe memory environment plus required `PYTHONPATH` returned
`44 passed / 0 failed`.

## 40. Windows lifecycle

**MEASURED: PASS.** The explicit memory-safe Windows lifecycle suite returned
`17 passed / 0 failed` in 172.818 seconds. It includes real backend/frontend ownership,
Vite-proxy login, stop/reset, occupied-port, and fail-closed metadata coverage.

## 41. Mypy/pip/diff

| Check | Result |
|---|---|
| `python -m mypy apps/backend/app` | **MEASURED: PASS**, 80 source files |
| `python -m pip check` | **MEASURED: PASS** |
| `git diff --check` | **MEASURED: PASS**, line-ending notices only |

## 42. Secret/pre-PR units

**MEASURED: PASS on qualifying local-process run.** The two allowed unit files returned
`42 passed / 0 failed`. The initial sandbox run passed the five secret tests but could
not initialize temporary Git repositories; no product failure was inferred. The broad
secret-scanner entry point was not run. A bounded 50-file task-owned pattern inspection
found zero private-key, bearer-token, non-test Mongo URI, or scrypt-hash literals.

## 43. Persistence schema

**OBSERVED / MEASURED: PASS.** `CASE_SNAPSHOT_SCHEMA_VERSION` remains exact integer
`2`. No migration was added for origin configuration, test safety, Dashboard, or
filter/sort. Strict version-1 read conversion and version-2 physical persistence remain
covered.

## 44. Diff/scope audit

**OBSERVED: PASS.** The tracked delta is 39 modified files plus the task-owned new
Dashboard/test-safety/Mongo-runner/report files listed in the remediation handoff. No
connector interface, ACRA or GoldTier behavior, UBO comparator/engine, Policy & Rules,
mutable UBO configuration, PingFed/SSO, production IAM, per-user assignment,
Onboarder/RM permission divergence, persisted team rename, new migration, warehouse,
custom BI builder, SLA/risk metric, dependency, manifest, or lockfile change was found.

## 45. Documentation audit

**OBSERVED: PASS.** Current project/architecture/contract/configuration/runbook material
states backend-owned production origin configuration, Vite development behavior,
non-authoritative Host/forwarding headers, Origin versus Referer semantics, ordinary
test isolation, explicit physical opt-in and `clm_poc` rejection, filter/sort values,
unset-last behavior, fixed Dashboard top-active order, POC-auth/BI limitations, and no
live ACRA/GoldTier or sponsor-approved mutable UBO/policy claim. The remediation report
records that the 30 incident records remain pending owner-controlled disposition; no
current document claims they were cleaned.

The duplicate-field behavior found here contradicts the documented claim that browser
source validation accepts only configured exact origins; the implementation defect is
reported below rather than repaired in documentation.

## 46. Findings

### P13-DC-RQG-001 — MEDIUM — duplicate browser-source fields are accepted by first-value order

- **Evidence:** `apps/backend/app/api_auth.py:119-124` uses scalar
  `request.headers.get` for Origin and Referer. Production probes measured:
  trusted-first/foreign-second duplicate Origin login `200`; reversed order `403`;
  trusted-first/foreign-second duplicate Referer login `200`; authenticated mutation
  with trusted-first/foreign-second duplicate Origin `201`.
- **Additional evidence:** configured-origin Referers containing a fragment returned
  `200`; the accepted contract explicitly names path/query support and requires
  malformed Referer rejection.
- **Impact:** ambiguous/multiple browser-source serialization is not rejected and the
  login/unsafe-mutation security boundary makes an order-dependent trust decision. No
  raw-Host expansion or browser-delivered cross-site exploit was demonstrated, so this
  is classified Medium rather than High; it still violates a mandatory gate criterion.
- **Required remediation:** require at most one Origin field and at most one Referer
  field before parsing; reject duplicate/combined ambiguity regardless of ordering;
  define and enforce fragment handling for Referer; add production login and
  authenticated-unsafe-mutation regressions for duplicate headers.

Finding totals: Critical **0**, High **0**, Medium **1**, Low **0**.

## 47. Remaining limitations

- POC authentication is not production PingFed/SSO, MFA, distributed sessions,
  production IAM/RBAC, or identity governance.
- Dashboard V1 is not production BI/MIS, forecasting, export, or a regulatory KPI
  source.
- Memory remains process-local; Mongo is a single-instance POC, not production
  retention/backup/HA.
- Live ACRA, real GoldTier/PingFed, Ready-for-Approval/four-eye behavior, and final
  sponsor policy remain **UNKNOWN** / outside this gate.
- The 30 prior QG incident records remain in shared `clm_poc` and require separately
  scoped owner authority for any disposition.
- Production `scripts/pre_pr_check.py` was not run against the intentionally dirty,
  uncommitted tree; only its unit tests were run.

## 48. Final metrics

| Metric | Exact result |
|---|---|
| Focused backend | 114 passed / 0 failed / 0 skipped; core remediation subset 99 passed |
| Full backend | 876 passed / 0 failed / 12 skipped / 3 warnings |
| Physical Mongo | 12 passed / 0 failed / 0 skipped |
| Physical temporary DBs remaining | 0 |
| Shared `clm_poc` before | 46 |
| Shared `clm_poc` after | 46 |
| Host spoof | PASS |
| Malformed Origin | **FAIL** — duplicate field serialization accepted |
| Hostile-env test isolation | PASS |
| Task-owned Ruff | PASS |
| Task-owned Ruff format | PASS — 29 files |
| Priority filter | PASS |
| Highest-first | PASS |
| Lowest-first | PASS |
| Unset-last | PASS |
| Priority RBAC | PASS |
| Frontend | typecheck PASS / 116 passed / build PASS |
| Contracts | 44 passed / 0 failed |
| Lifecycle | 17 passed / 0 failed |
| Mypy | PASS |
| `pip check` | PASS |
| `git diff --check` | PASS |
| Provider historical-read calls | 0 |
| Dashboard TEAM_A | PASS |
| Dashboard TEAM_B | PASS |
| Dashboard Director | PASS |
| Critical | 0 |
| High | 0 |
| Medium | 1 |
| Low | 0 |

## 49. Final verdict

**Goal closure:** the independent re-quality gate is complete and stops at **blocked**
for owner-controlled integration because mandatory malformed/ambiguous Origin handling
is not satisfied. The previous four findings are closed, all broad regression evidence
is green, and the new defect is bounded to browser-source header cardinality/parsing.
No implementation remediation or next phase was started.

No implementation files were modified. Shared `clm_poc` was not written or cleaned;
the 30 incident records remain untouched. `.env` was not modified. Mongo URI, hostname,
and credentials were not exposed. Protected artifacts were untouched. Nothing was
staged, committed, pushed, merged, rebased, reset, or cleaned.

FAIL — PHASE 13 DEMO COMPLETENESS REMEDIATION REQUIRES REMEDIATION
