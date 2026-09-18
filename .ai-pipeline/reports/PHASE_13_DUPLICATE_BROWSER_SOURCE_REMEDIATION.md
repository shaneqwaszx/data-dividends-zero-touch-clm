# Phase 13 Duplicate Browser-Source Remediation

Date: 2026-09-08
Role: original implementation/remediation owner (not the independent quality gate)

## 1. Executive summary

**Result: PASS — ready for a fresh independent re-quality gate.** P13-DC-RQG-001 is
remediated at the canonical `BrowserOriginPolicy` owner. Origin and Referer now each
permit zero or one physical header field only; duplicates fail closed independently of
order, value equality, or header-name capitalization. Referer fragments are rejected
while legitimate path/query use remains accepted. The full required verification
sequence passes. No independent re-QG was run in this chat.

## 2. Branch/baseline

- Branch: `fix/phase13-demo-login-identities`.
- `HEAD`, refreshed `origin/main`, and merge-base:
  `dcb52937d46882a5b1b6ba7f2d545829e6fda662`.
- `origin/main` did not advance from the declared baseline.
- The index remained empty. The complete Phase 13 working tree remains intentionally
  uncommitted.

## 3. P13-DC-RQG-001 root cause

`BrowserOriginPolicy.request_is_trusted` used scalar `request.headers.get` reads. The
Starlette header abstraction retains repeated physical fields, but scalar retrieval
selected one value and made the trust decision depend on field order. Separately, the
shared URL parser allowed a fragment whenever resource syntax was enabled for Referer.
A pre-repair 21-case run reproduced 10 failures, including trusted-first duplicate
acceptance on login/mutation and Referer-fragment acceptance.

## 4. Header-cardinality design

One `_single_header_value` helper calls Starlette's case-insensitive multi-value
`getlist` API. It returns a value only for zero/one physical field and marks cardinality
greater than one invalid. `BrowserOriginPolicy` invokes this helper for both Origin and
Referer before existing syntax/trust parsing, so login and authenticated unsafe methods
share exactly one policy path. No raw Host/request URL/forwarding metadata is consulted.

## 5. Origin duplicate handling

Actual repeated header tuples prove rejection for trusted+foreign, foreign+trusted,
trusted+trusted, and foreign+foreign. Case-varied field names are covered. Identical
trusted duplicates are not deduplicated. Existing single-field comma/multiple-origin
serialization remains malformed and rejected.

## 6. Referer duplicate handling

Actual repeated header tuples prove rejection for trusted+foreign, foreign+trusted,
trusted+trusted, and foreign+foreign Referers, including case-varied names. Identical
trusted duplicates fail under the same cardinality rule as Origin.

## 7. Referer fragment rule

The shared parser now rejects any non-empty parsed fragment for both header kinds.
Referer remains less restrictive than Origin only where intended: an HTTP(S) same-origin
Referer may carry path and query. Unsupported schemes, missing/invalid hosts, userinfo,
malformed ports, foreign origins, and whitespace/multi-value ambiguity remain rejected.

## 8. Login adversarial evidence

The production-mode matrix passed all 14 login cases: single trusted Origin allowed;
single foreign Origin rejected; all four duplicate-Origin combinations rejected; single
trusted Referer and trusted Referer with path/query allowed; foreign Referer rejected;
all four duplicate-Referer combinations rejected; and a fragment-bearing trusted
Referer rejected. Every rejection retained the fixed `CSRF_VALIDATION_FAILED` response.

## 9. Unsafe-mutation adversarial evidence

With an otherwise valid authenticated session and CSRF proof, a single configured
Origin reached normal case creation (`201`). Duplicate Origin in either mixed order,
duplicate identical trusted Origin, duplicate Referer, valid Origin plus duplicate
Referer, and duplicate Origin plus valid Referer all returned the fixed `403
CSRF_VALIDATION_FAILED` response. No separate route-level duplicate logic was added.

## 10. Host/configured-origin non-regression

The full auth suite retains coverage that request Host and forwarding headers cannot
expand trust, malformed Origin path/query/fragment/userinfo/port/scheme/multi-value
inputs fail, configured production HTTPS Origin works, missing/malformed production
configuration fails before persistence initialization, and the documented Vite
loopback Origin works only in development/test. Backend configuration remains the sole
trust authority.

## 11. Session/CSRF/cookie non-regression

`tests/test_phase13_auth_rbac.py` passed 65 tests. Session creation, rotation, expiry,
logout, server-authored profile, host-only HttpOnly SameSite-Strict cookie behavior,
generic credential failures, session-bound CSRF, and login/unsafe-method browser-source
parity remain green. The credential-verification path still returns the generic `401`
for a wrong credential from the valid Vite Origin.

## 12. Test-isolation non-regression

The hostile-parent-environment isolation module passed **2/2**. Ordinary settings
remained memory-backed and a root Mongo-shaped environment could not activate Mongo or
the shared namespace.

## 13. Mongo safety non-regression

The Mongo test-safety unit module passed **8/8**. Physical Mongo remains explicit opt-in,
and the database guard continues to reject `clm_poc` and non-allowlisted names before
cleanup. This auth-only remediation ran no physical Mongo tests and performed no Mongo
writes.

## 14. Priority filter/sort non-regression

`tests/test_phase13_priority.py` passed **45/45**, covering the authoritative all,
prioritised, unset, exact-priority, highest-first, lowest-first, unset-last, tie-break,
strict create/update validation, persistence parity, and authorization-before-filter
contracts. No priority implementation or frontend control was changed.

## 15. Dashboard non-regression

`tests/test_phase13_dashboard.py` passed **4/4**. Dashboard remains authenticated,
backend-RBAC scoped, provider-free, canonically highest-first for top-active cases, and
shared across memory/Mongo repository abstractions. No Dashboard code changed.

## 16. Focused backend

- New duplicate/cardinality/fragment matrix: **21 passed**.
- Full auth/RBAC/session/CSRF owner: **65 passed**.
- Hostile test isolation: **2 passed**.
- Mongo safety: **8 passed**.
- Priority: **45 passed**.
- Dashboard: **4 passed**.
- Wider focused Phase 13 selection including demo scripts: **135 passed**.

## 17. Full backend

`python -m pytest apps/backend/tests -p no:cacheprovider --tb=no` passed **897**,
skipped **12** explicit physical opt-in tests, and emitted the same **3** known
malformed-provider Pydantic serializer warnings. There were no failures.

## 18. Frontend

- `npm run typecheck`: PASS.
- `npm test -- --run`: **116 passed** across four files.
- `npm run build`: PASS; 46 modules transformed.

Vitest/build required the approved local-process execution path after sandboxed esbuild
spawn was denied. No frontend source was changed by this remediation.

## 19. Contracts

The test-safe memory contract suite passed **44/44** with the required backend import
path. No API schema, connector, or business contract changed.

## 20. Lifecycle

The qualifying memory-safe Windows lifecycle run passed **17/17** in 235.198 seconds.
The initial sandboxed attempt could not control its owned child processes; the approved
local-process rerun completed startup, reset, ownership, occupied-port, and cleanup
coverage successfully.

## 21. Ruff/format/mypy/pip/diff

- Task-owned Ruff check over 29 Python files: PASS.
- Ruff format check: **29 files already formatted**.
- Mypy: PASS across 80 backend source files.
- `python -m pip check`: PASS.
- `git diff --check`: PASS; Windows line-ending notices only.

## 22. Secret/pre-PR units

Only the permitted unit suites were run: `test_check_secrets.py` passed **5/5** and
`test_pre_pr_check.py` passed **37/37**, for **42 passed** total. The broad production
secret scanner and its help mode were not invoked.

## 23. Shared clm_poc before/after

- Incoming independent re-QG measured count: **46**.
- Direct read-only post-verification count: **46**.
- Difference: **0**.

The application, seeder, recovery paths, physical tests, updates, deletes, and cleanup
were not run against shared `clm_poc`. The 30 prior incident records remain untouched.

## 24. Files changed by this bounded remediation

- `apps/backend/app/api_auth.py` — canonical cardinality check and Referer fragment rule.
- `apps/backend/tests/test_phase13_auth_rbac.py` — 21 actual repeated-field adversarial
  cases across login and unsafe mutation.
- `docs/architecture/PHASE_13_CASE_PRIORITY_AUTH_RBAC.md` — cardinality and fragment
  architecture statement.
- `docs/contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md` — exact browser-source contract.
- `docs/integration/CONFIGURATION_REFERENCE.md` — operator-facing validation semantics.
- `.ai-pipeline/reports/PHASE_13_DUPLICATE_BROWSER_SOURCE_REMEDIATION.md` — this report.

All files already modified by the broader uncommitted Phase 13 implementation were
preserved; no unrelated file was changed for this slice.

## 25. Git status

The expected broader Phase 13 tracked working set remains modified and the index is
empty. `HEAD` and refreshed `origin/main` remain aligned at the declared baseline. No
unresolved path exists. Protected untracked artifacts and protected cache directories
were not opened, read, hashed, scanned, modified, renamed, deleted, copied, staged, or
cleaned. Routine status inspection used `--untracked-files=no`.

Nothing was staged, committed, pushed, merged, rebased, reset, cleaned, stashed,
restored, discarded, or branch-switched.

## 26. Remaining limitations

- A fresh independent re-QG is still required; it was deliberately not run here.
- Production PingFed/SSO/IAM, distributed sessions, live ACRA/GoldTier, sponsor policy,
  and production BI remain outside this bounded remediation.
- Physical Mongo behavior was not rerun because this auth-only correction requires no
  persistence write; its safety units and ordinary-test isolation were rerun.
- The 30 shared incident records remain pending separate owner authorization.

No Critical, High, or Medium issue is known within the assigned browser-source
remediation scope after the fresh owner verification above.

## 27. Independent re-QG readiness

**Ready for a fresh independent re-quality gate; owner confidence A for this bounded
slice.** Direct regression evidence covers the original recurrence, all required
duplicate combinations, identical fields, capitalization, comma serialization,
Referer fragments/path/query, login/mutation parity, and the relevant security and
project regression boundaries.

Aegis impact and safety receipt: the key judgment was to repair cardinality at
`BrowserOriginPolicy` instead of selecting/deduplicating a value or adding route-specific
guards. The invalid scalar-read responsibility is retired; the legitimate configured
origin parser and the shared login/unsafe-method policy remain. Complexity stayed within
budget through one small helper and one parser condition, with no fallback, adapter,
trust source, dependency, schema, or compatibility branch. Evidence strength is A for
the bounded owner remediation; the next authority step is the user-requested fresh
independent re-QG. Shared data and all stated non-goals remained outside the change.
