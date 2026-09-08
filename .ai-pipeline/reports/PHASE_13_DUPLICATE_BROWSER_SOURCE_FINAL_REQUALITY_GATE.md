# Phase 13 Duplicate Browser-Source Remediation — Final Independent Re-Quality Gate

Date: 2026-09-08
Role: Fresh Independent Final Re-Quality Gate
Reviewed finding: `P13-DC-RQG-001`

## 1. Executive summary

**Result: PASS.** The bounded browser-source remediation passes independent review.
Actual repeated physical
`Origin` and `Referer` fields were delivered to an in-process ASGI application and were
rejected regardless of order, value equality, or header-name capitalization. Referer
path/query was accepted, a Referer fragment was rejected, login and authenticated unsafe
mutation used the same policy, Host/forwarding spoofing remained rejected, and the
targeted plus broad regression checks passed.

`P13-DC-RQG-001` is therefore **CLOSED**. No Critical, High, Medium, or Low code finding
was identified.

The recovered final direct read-only shared `clm_poc` count is **MEASURED** at `46`,
matching the initial measured count of `46`; difference `0`. The count used direct
PyMongo `count_documents({})` only. No application composition/recovery or shared write
path was used. `P13-DC-FRQG-BLOCKER-001` is **CLOSED**.

Evidence classifications in this report are **MEASURED** for executed probes/checks,
**OBSERVED** for source/diff/document inspection, and **INFERRED** for conclusions
supported by those observations. Live and sponsor-controlled production capabilities
remain **UNKNOWN** and outside this gate.

## 2. Branch and baseline

| Item | Result |
|---|---|
| Branch | **MEASURED:** `fix/phase13-demo-login-identities` |
| Declared baseline | **MEASURED:** `dcb52937d46882a5b1b6ba7f2d545829e6fda662` |
| `HEAD` | **MEASURED:** `dcb52937d46882a5b1b6ba7f2d545829e6fda662` |
| Final fetched `origin/main` | **MEASURED:** `dcb52937d46882a5b1b6ba7f2d545829e6fda662` |
| Merge base | **MEASURED:** same baseline |
| `HEAD..origin/main` | **MEASURED:** empty; no main drift |
| Index | **MEASURED:** empty |
| Unresolved paths | **MEASURED:** none |
| `git diff --check` | **MEASURED:** PASS; line-ending notices only |

The complete Phase 13 implementation remains intentionally uncommitted. No branch
switch, stage, commit, push, merge, rebase, reset, clean, stash, restore, or discard was
performed.

## 3. Previous finding

The authoritative previous finding was:

`P13-DC-RQG-001 — MEDIUM — duplicate browser-source fields are accepted by first-value order`.

The original exploit accepted trusted-first/foreign-second duplicate `Origin` and
`Referer` fields on login and accepted a trusted-first duplicate Origin on an
authenticated unsafe mutation. Reversed order behaved differently. The previous gate
also observed that a configured-origin Referer containing a fragment was accepted.

**INFERRED final disposition: CLOSED.** The original exploit shape and its reverse,
identical duplicate values, foreign duplicate values, mixed-capitalization names,
Referer fragment, and authenticated-mutation variants were all independently reproduced
after remediation and failed closed.

## 4. Review scope

The review covered AGENTS.md, project context, the Phase 13 planner, relevant reviewer,
tester, and security roles, integration/quality/regression workflows and checklists, the
four mandatory prior reports, the current authentication implementation/tests, the
three browser-source contract/configuration documents, the tracked diff, and required
regression checks.

The review was implementation-read-only. This report is the only repository file
created by the gate.

## 5. Header-cardinality implementation

**OBSERVED: PASS.** `BrowserOriginPolicy.request_is_trusted` calls
`_single_header_value` independently for `origin` and `referer` before syntax/trust
validation. `_single_header_value` calls Starlette `request.headers.getlist(name)`,
rejects `len(values) > 1`, returns `None` for zero fields, and returns the sole value for
exactly one field. Header lookup is case-insensitive through the header collection.

Scalar `request.headers.get(...)` is not used as authority for duplicate-sensitive
Origin/Referer validation. Login and authenticated unsafe methods invoke the same
`BrowserOriginPolicy` instance from the central middleware.

## 6. Origin duplicate matrix

The independent in-process probe constructed a production-mode FastAPI application with
memory persistence and sent header tuple lists through `TestClient`. A temporary outer
middleware counted raw `request.scope["headers"]` entries and measured two physical
Origin entries for every duplicate case.

| Origin case | Raw count | HTTP | Result |
|---|---:|---:|---|
| configured trusted only | 1 | 200 | **MEASURED: PASS**, credential path |
| foreign only | 1 | 403 | **MEASURED: PASS** |
| trusted then foreign | 2 | 403 | **MEASURED: PASS** |
| foreign then trusted | 2 | 403 | **MEASURED: PASS** |
| trusted then identical trusted | 2 | 403 | **MEASURED: PASS** |
| foreign then identical foreign | 2 | 403 | **MEASURED: PASS** |

Mixed `Origin`/`origin`/`ORIGIN` input names were used. Duplicate rejection is therefore
cardinality-based and order/value independent; no deduplication, first/last selection,
or trusted-value preference was observed.

## 7. Referer duplicate matrix

The same probe measured two raw physical Referer entries for every duplicate case.

| Referer case | Raw count | HTTP | Result |
|---|---:|---:|---|
| configured trusted only | 1 | 200 | **MEASURED: PASS**, credential path |
| trusted with path/query | 1 | 200 | **MEASURED: PASS**, credential path |
| foreign | 1 | 403 | **MEASURED: PASS** |
| trusted then foreign | 2 | 403 | **MEASURED: PASS** |
| foreign then trusted | 2 | 403 | **MEASURED: PASS** |
| trusted then identical trusted | 2 | 403 | **MEASURED: PASS** |
| foreign then identical foreign | 2 | 403 | **MEASURED: PASS** |

Mixed `Referer`/`referer`/`REFERER` input names were used. All rejections returned the
fixed `CSRF_VALIDATION_FAILED` projection.

## 8. Referer fragment and path/query

**MEASURED: PASS.** `https://configured.example/cases/ABC?tab=1` reached the credential
path with HTTP 200. `https://configured.example/cases/ABC#section` returned HTTP 403
with `CSRF_VALIDATION_FAILED`.

**OBSERVED / MEASURED: PASS.** `_parse_http_url` rejects fragments for both header
kinds, while `allow_resource=True` for Referer permits legitimate path/query. The
independent probe also rejected unsupported scheme, userinfo, missing host, and malformed
port inputs. Existing full-auth coverage retains malformed/ambiguous serialization and
default-port behavior.

## 9. Comma/multi-value single field

**MEASURED: PASS.** One physical Origin field containing
`https://configured.example, https://foreign.example` returned HTTP 403 with
`CSRF_VALIDATION_FAILED`. Duplicate-field cardinality handling did not weaken the
existing single-field syntax validation.

## 10. Login and unsafe-mutation parity

**MEASURED: PASS.** With a legitimate production-mode authenticated session and the
session-bound CSRF token:

| Mutation case | HTTP | Result |
|---|---:|---|
| single configured trusted Origin | 201 | normal mutation behavior |
| trusted Origin then foreign Origin | 403 | `CSRF_VALIDATION_FAILED` |
| foreign Origin then trusted Origin | 403 | `CSRF_VALIDATION_FAILED` |
| trusted then identical trusted Origin | 403 | `CSRF_VALIDATION_FAILED` |
| duplicate Referer | 403 | `CSRF_VALIDATION_FAILED` |
| single valid Origin plus duplicate Referer | 403 | `CSRF_VALIDATION_FAILED` |
| duplicate Origin plus single valid Referer | 403 | `CSRF_VALIDATION_FAILED` |

No existence, team, user, or credential information appeared in the fixed rejection.

## 11. Host and forwarding non-regression

**MEASURED: PASS.** Foreign `Host` plus a matching foreign Origin returned HTTP 403.
`Forwarded`, `X-Forwarded-Host`, and `X-Forwarded-Proto` values did not expand trust.
The configured backend origin remained authoritative. Production configuration still
requires one explicit HTTPS `PHASE13_BROWSER_ORIGIN` before persistence initialization.

## 12. Development/Vite non-regression

**MEASURED: PASS.** In test/development configuration,
`http://127.0.0.1:5173` plus a wrong password reached the normal generic credential path
and returned HTTP 401, not the browser-origin/CSRF 403. The 65-test auth owner suite also
passed the production regression that does not trust the Vite origin.

## 13. Session, cookie, and CSRF compact regression

**MEASURED: PASS through the 65-test auth owner.** Representative coverage includes
opaque sessions, re-login rotation, expiration, server-authored identity, host-only
HttpOnly `SameSite=Strict` `Path=/api` cookies, production Secure behavior, missing and
wrong CSRF, logout CSRF, generic login failure, and route protection.

## 14. Test-isolation compact regression

**MEASURED: PASS — 2 passed.** The hostile-environment module creates a child process
whose parent environment is Mongo-shaped with the shared database name and a dead
loopback URI. Ordinary composition remains memory-backed. No ordinary test attempted
Mongo.

## 15. Mongo safety unit regression

**MEASURED: PASS — 8 passed.** The safety owner rejects `clm_poc`, blank/arbitrary,
wrong-phase, and traversal-like database names before cleanup and covers bounded retry,
absence verification, and driver-detail redaction. No physical Mongo write test was run
for this auth-only gate.

## 16. Priority non-regression

**MEASURED: PASS — 45 passed.** `all`, `prioritised`, `unset`, exact priority values,
`highest_first`, `lowest_first`, unset-last in both directions, validation, tie-breaks,
persistence parity, and authorization-before-filter behavior remain green.

## 17. Dashboard non-regression

**MEASURED: PASS — 4 passed.** Dashboard remains authenticated, backend-RBAC scoped,
provider-free, fixed highest-first for top-active cases, and free of cross-team leakage.

## 18. Focused duplicate tests

The remediation's exact duplicate/cardinality/fragment selection returned:

`21 passed, 0 failed, 44 deselected`.

This authored-test evidence supplements rather than replaces the independent raw-ASGI
probe in sections 6–10.

## 19. Full auth owner

`python -m pytest tests/test_phase13_auth_rbac.py -p no:cacheprovider --tb=no`
returned **65 passed / 0 failed** in 16.56 seconds.

## 20. Wider focused Phase 13

The auth, priority, hostile isolation, Mongo safety, seeder, and Dashboard selection
returned **135 passed / 0 failed** in 26.27 seconds.

## 21. Full backend

`python -m pytest apps/backend/tests -p no:cacheprovider --tb=no` returned:

- **897 passed**
- **0 failed**
- **12 skipped** explicit physical opt-in tests
- **3 warnings** from the known malformed-provider Pydantic serializer cases

The ordinary run used the repository's test-isolation owner and did not receive a Mongo
persistence override.

## 22. Frontend

| Check | Result |
|---|---|
| `npm run typecheck` | **MEASURED: PASS** |
| `npm test -- --run` | **MEASURED: 116 passed / 0 failed**, four files |
| production build | **MEASURED: PASS**, 46 modules transformed |

The initial sandboxed Vitest start hit Windows `spawn EPERM`; the qualifying
local-process rerun passed. Build output was directed to a separately validated writable
directory outside the repository and then removed.

## 23. Contracts

**MEASURED: PASS — 44 passed / 0 failed.** The accepted contract discovery ran with an
explicit memory/test-safe environment and required backend/contract import paths.

## 24. Windows lifecycle

**MEASURED: PASS — 17 passed / 0 failed** in 168.986 seconds on the qualifying
local-process run. The first sandboxed attempt could not terminate its owned child
process tree; the qualifying rerun used retained ownership metadata, managed only its
own backend/frontend children, and verified final cleanup. Persistence remained memory
and the shared database was not used.

## 25. Static and quality checks

| Check | Result |
|---|---|
| Task-owned Ruff over 29 explicit Python files | **MEASURED: PASS** |
| Ruff format over the same 29 files | **MEASURED: PASS**, 29 already formatted |
| `python -m mypy apps/backend/app` | **MEASURED: PASS**, 80 source files |
| `python -m pip check` | **MEASURED: PASS** |
| `git diff --check` | **MEASURED: PASS**, line-ending notices only |

Ruff ran without a cache; the mypy cache was directed outside the repository and
removed after the check. No formatter was run.

## 26. Secret and pre-PR unit tests

**MEASURED: PASS on the qualifying run — 42 passed / 0 failed** (`5` secret-check units
plus `37` pre-PR-check units). The first sandboxed run passed the five secret units but
could not create temporary Git repositories; the permitted local-process rerun passed
all 42. `python scripts/check_secrets.py` and its help mode were not run.

No credential, hash, session token, cookie, CSRF value, Mongo URI, Mongo hostname, or
Mongo credential was printed by the gate.

## 27. Shared clm_poc before/after

| Receipt | Result |
|---|---|
| Before | **MEASURED: 46** |
| After | **MEASURED: 46** |
| Difference | **MEASURED: 0** |

The count code used PyMongo `count_documents({})` directly and never composed the
application or invoked recovery. All executable product/regression paths in this gate
used process-local memory persistence. The gate did not seed, create, update, delete,
recover, normalize, complete, or clean a shared record. The 30 prior incident records
were not targeted. Before/after equality is measured, so the mandatory DATA SAFETY
receipt is satisfied.

## 28. Diff and scope

**OBSERVED:** The tracked working delta remains the broader uncommitted Phase 13 set:
39 modified files, 2,600 insertions, and 575 deletions against the baseline. The index
is empty and no unresolved path exists.

The bounded duplicate-browser-source remediation is confined to the inspected owner,
tests, and documentation:

- `apps/backend/app/api_auth.py`
- `apps/backend/tests/test_phase13_auth_rbac.py`
- `docs/architecture/PHASE_13_CASE_PRIORITY_AUTH_RBAC.md`
- `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md`
- `docs/integration/CONFIGURATION_REFERENCE.md`
- the remediation report

No duplicate-remediation change to Mongo persistence, ACRA, GoldTier, UBO, Policy &
Rules, Dashboard, priority implementation, frontend, schema version, dependencies,
manifest, or lockfile was observed. Because all Phase 13 work is intentionally
uncommitted, bounded-slice attribution is based on direct content inspection plus the
handoff and is not mechanically separable by commit history.

## 29. Documentation

**OBSERVED: PASS.** Current architecture, contract, and configuration material states:

- zero or one physical Origin and Referer field;
- duplicate fields fail closed regardless of order, capitalization, or equality;
- comma/multiple serialization in one Origin field fails closed;
- Referer path/query is allowed and Referer fragments are rejected;
- Host and forwarding headers remain non-authoritative;
- production trust comes from an explicit configured HTTPS origin;
- development/test Vite trust is exact and does not carry into production.

No production IAM/SSO, live ACRA, real GoldTier, or Ready-for-Approval claim was added.

## 30. Findings, limitations, and final metrics

### Findings

No current product finding was identified.

- Critical: **0**
- High: **0**
- Medium: **0**
- Low: **0**

### Verification blocker closure

`P13-DC-FRQG-BLOCKER-001 — mandatory final shared-data count unavailable`: **CLOSED**.

The recovered bounded direct read-only count measured `46`, equal to the initial `46`.
It does not reopen `P13-DC-RQG-001`; both required closure boundaries now pass.

### Remaining limitations

- Production PingFed/SSO/IAM, distributed sessions, live ACRA/GoldTier,
  Ready-for-Approval/four-eye behavior, and final sponsor policy remain outside scope.
- Physical Mongo behavior was not rerun because the bounded change is auth-only; its
  safety units and ordinary-test isolation passed.
- The 30 prior shared incident records remain pending separately authorized owner
  disposition.
- The production clean-tree pre-PR entry point was not run against this intentionally
  dirty, uncommitted working tree.

### Final metrics

| Metric | Exact result |
|---|---|
| Duplicate Origin trusted→foreign | PASS |
| Duplicate Origin foreign→trusted | PASS |
| Duplicate Origin trusted→trusted | PASS |
| Duplicate Origin foreign→foreign | PASS |
| Duplicate Referer trusted→foreign | PASS |
| Duplicate Referer foreign→trusted | PASS |
| Duplicate Referer trusted→trusted | PASS |
| Duplicate Referer foreign→foreign | PASS |
| Case-insensitive duplicate | PASS |
| Referer fragment | PASS |
| Referer path/query | PASS |
| Unsafe mutation duplicate | PASS |
| Host spoof | PASS |
| New adversarial matrix | 21 passed / 0 failed |
| Full auth | 65 passed / 0 failed |
| Wider focused Phase 13 | 135 passed / 0 failed |
| Full backend | 897 passed / 0 failed / 12 skipped / 3 warnings |
| Hostile test isolation | 2 passed / 0 failed |
| Mongo safety | 8 passed / 0 failed |
| Priority | 45 passed / 0 failed |
| Dashboard | 4 passed / 0 failed |
| Frontend | typecheck PASS / 116 passed / build PASS |
| Contracts | 44 passed / 0 failed |
| Lifecycle | 17 passed / 0 failed |
| Task-owned Ruff | PASS |
| Ruff format | PASS |
| Mypy | PASS |
| `pip check` | PASS |
| `git diff --check` | PASS |
| Shared `clm_poc` before | 46 |
| Shared `clm_poc` after | 46 |
| Shared `clm_poc` difference | 0 |
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |

## 31. Final verdict

`P13-DC-RQG-001` and `P13-DC-FRQG-BLOCKER-001` are closed. The remediation and all
mandatory product, security, regression, static, and data-safety evidence are green.
Phase 13 Demo Completeness remediation is ready for owner-controlled integration after
owner review.

No implementation file was modified. Shared `clm_poc` was not written, seeded, updated,
deleted, recovered, normalized, completed, or cleaned by this gate; the 30 incident
records were untouched. `.env` was untouched. Mongo URI, hostname, credentials, auth
hashes/passwords, cookie/session values, and CSRF values were not exposed. Protected
untracked artifacts were untouched. Nothing was staged, committed, pushed, merged,
rebased, reset, cleaned, stashed, restored, discarded, or branch-switched.

PASS — PHASE 13 DEMO COMPLETENESS REMEDIATION READY FOR OWNER-CONTROLLED INTEGRATION
