# Phase 14.5 CI Secret Scanner Remediation

## Outcome

The Phase 14.5 secret-scanner failure was caused by a rule that treated every
occurrence of a sensitive field name as a committed credential, including typed
request-model fields and runtime forwarding expressions. No real committed
secret was identified in the ten reported findings.

## Finding classification

| Finding locations | Classification | Remediation |
| --- | --- | --- |
| `apps/backend/app/api_admin.py` (two findings) | Safe typed request-model field and runtime request forwarding | No production change; scanner now recognises source-code references. |
| `apps/backend/app/services/administration.py` | Safe typed service parameter | No production change; scanner now recognises source-code references. |
| `apps/backend/tests/test_phase14_5_administration.py` (four findings) | Safe test fixture data, previously expressed as inline values | Reused the existing shared test credential constant. |
| `apps/backend/tests/test_phase14_5_real_mongo.py` | Safe typed test-helper default | No change; scanner now recognises source-code references. |
| `apps/frontend/src/Phase14_5AdminPolicy.test.tsx` | Safe test fixture data, previously expressed as an inline value | Replaced with a recognised test placeholder reference. |
| `apps/frontend/src/api.ts` | Safe typed request-model field | No production change; scanner now recognises source-code references. |

## Scanner correction

`scripts/check_secrets.py` now permits only unquoted identifier/member
references in supported source-code files when matched by the sensitive
assignment rule. It continues to flag literal credential assignments and
unquoted values outside supported source-code files. The scanner also now
detects credential-bearing connection URIs for supported datastore schemes.

Regression tests prove that runtime field forwarding is accepted, while a
literal credential assignment and a credential-bearing connection URI are
blocked. Existing token, client-secret, sensitive-file-type, and placeholder
coverage remains in place.

## Validation

- Scanner unit tests: 8 passed.
- Full repository secret scan: passed.
- Backend Phase 14.5 administration, case-access, and authentication/RBAC
  tests: 86 passed.
- Backend type checking: passed with no issues in 91 source files.
- Ruff for changed Python and scanner files: passed.
- Frontend Phase 14.5 administration/policy test: 26 passed.
- Frontend type check: passed.

The remediation does not alter the physical Mongo helper, connector behavior,
database schema, API routes, shared types, or production security policy.

## Physical Mongo decision

A physical Mongo rerun is not required. The physical-Mongo test helper was not
changed, and the backend fixture edits only replace synthetic inline values with
the existing shared test constant; they do not change persistence behavior.

## Residual findings and readiness

There are no residual scanner findings after the full repository scan. The
remediation is ready for the explicit staging, pre-commit, merge-safety, and
push checks required for this branch.
