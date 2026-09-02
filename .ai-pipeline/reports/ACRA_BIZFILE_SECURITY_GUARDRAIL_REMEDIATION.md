# ACRA BizFile Security Guardrail Remediation

Date: 2026-09-01  
Baseline: `origin/main` at `b196d887964f0d93b93dfd2d39c271195eb19af9`  
Scope: dormant ACRA BizFile sandbox connector security guardrail only

## 1. Root cause

`apps/backend/app/connectors/acra_bizfile_sandbox.py` contained an unused,
speculative OAuth2 client-credentials authorizer. Its in-memory credential and
token assignments matched the repository secret scanner's
`sensitive-assignment` rule at two lines. The class was not required by the
currently supported entityQuery behavior and was not composed into the
application.

The remediation removes the entire speculative authorizer, including token
request, parsing, caching, expiry, and locking logic. It also removes only the
imports made unused by that deletion (`threading` and `time`). `Callable`
remains because the connector's deterministic clock seam still uses it.

## 2. Why this is not a credential leak

The findings were structural scanner matches against Python assignments, not
detected credential values. Inspection found no real credential, token,
environment secret, private key, or hardcoded placeholder. The scanner
suppressed matched values as designed, and no credential material was added by
this remediation.

## 3. Why speculative OAuth is being deferred

The currently tested entityQuery endpoints operate without an Authorization
header, and the dormant connector already provides `NoAuthAcraAuthorizer` for
that behavior. There is no authoritative project-owned ACRA authentication
contract for additional operations. Implementing or retaining a guessed token
flow would create an unsupported security boundary. No replacement token
implementation was introduced.

## 4. Q-012 relationship

Q-012 remains **OPEN**. It still requests the authoritative subscribed ACRA
operation schemas, authentication and authorization mechanism, sandbox access,
error semantics, rate and timeout guidance, and TLS requirements. This
remediation neither answers nor narrows Q-012; it explicitly defers future
authentication work until that evidence is supplied and approved.

## 5. Files changed

- `apps/backend/app/connectors/acra_bizfile_sandbox.py`
  - removed the dormant OAuth2 authorizer and token lifecycle;
  - removed now-unused `threading` and `time` imports;
  - documented the Q-012 deferral and retained no-auth boundary.
- `apps/backend/tests/test_acra_bizfile_sandbox_connector.py`
  - added bounded import, exposure, no-auth, HTTPS, decoder, and fail-closed
    relationship tests.
- `.ai-pipeline/reports/ACRA_BIZFILE_SECURITY_GUARDRAIL_REMEDIATION.md`
  - records this remediation and verification evidence.

No frontend, API contract, application composition, workflow, or Phase 09–12
behavior file changed.

## 6. Connector behavior preserved

- The module imports successfully.
- `NoAuthAcraAuthorizer.authorization_headers()` still returns an empty mapping.
- Default connector requests add only `Accept: application/json`; no
  Authorization header is added.
- Base URLs remain HTTPS-only and reject unsafe configuration.
- Existing company, officer, and ownership-party DTO decoding remains unchanged.
- Withdrawn shareholder filtering and unset ownership percentages remain
  unchanged.
- The unconfirmed relationships operation still fails closed.
- The connector remains dormant and is not composed or activated.

## 7. Secret-scan result

**PASS**

Command from repository root:

`python scripts/check_secrets.py`

Result: `Secret scan passed: no supported secret patterns found.` The scanner
implementation, rules, exclusions, and failure behavior were not changed. No
bypass, suppression, obfuscation, or placeholder credential was added.

## 8. Ruff

**PASS**

Command from repository root:

`python -m ruff check .`

Result: `All checks passed!`

## 9. mypy

**PASS**

Command from `apps/backend`:

`python -m mypy app`

Result: strict mypy reported no issues in 73 source files.

## 10. Backend tests

**PASS**

Command from `apps/backend`, with the repository root supplied through the same
`PYTHONPATH` used by CI:

`python -m pytest`

Result: 711 passed, 11 skipped, 4 existing warnings, 0 failed. This includes the
five new bounded ACRA BizFile connector tests and the established POC regression
coverage for Phase 09–12 call stopping, routing, acquisition, reconciliation,
persistence, and recovery behavior.

An initial local invocation without the CI `PYTHONPATH` stopped during collection
because two tests could not import the repository-root `scripts` package; no test
ran or failed in that invocation. The project-correct CI import context above was
then used for the complete green run.

## 11. Contract tests

**PASS**

Command from `apps/backend`:

`python -m unittest discover -s ../../tests/contract -p "test_*.py"`

Result: 44 tests passed.

## 12. Security tests

**PASS**

Command from repository root:

`python -m unittest discover -s tests -p "test_check_secrets.py"`

Result: 5 tests passed. The repository secret scan also passed after all source
and test changes. `python -m pip check` reported no broken requirements.

## 13. Remaining limitations

- The ACRA BizFile connector remains dormant and uncomposed.
- No live ACRA or newly activated provider mode exists.
- Authentication requirements beyond the currently tested no-auth endpoints are
  unknown pending Q-012.
- Existing DTO mappings remain based on bounded sample evidence and retain their
  documented unconfirmed fields and defaults.
- No relationships endpoint is confirmed; that operation continues to fail
  closed.
- This remediation does not begin further ACRA integration, alter Phase 09–12,
  or change any frontend/API/workflow contract.

## 14. Readiness

**READY FOR INDEPENDENT QUALITY GATE**

The speculative OAuth implementation is removed, supported no-auth and decoding
behavior is preserved, every required gate is green, the scanner remains intact,
Q-012 remains open, and the bounded security review identifies no Critical or
High finding. The remediation is intentionally left unstaged and has not been
merged or pushed.
