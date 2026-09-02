# ACRA BizFile Security Remediation — Independent Quality Gate

**Gate date:** 2026-09-01  
**Result:** PASS  
**Review type:** Review-only, bounded security remediation  
**Implementation changes made by this gate:** None

## 1. Executive summary

**PASS.** The remediation safely removes the dormant speculative ACRA OAuth2
client-credentials authorizer and its token-fetch/cache lifecycle while preserving the
currently supported no-auth connector behavior. The scanner was neither changed nor
evaded, no credential material was found, Q-012 remains open, and the connector remains
uncomposed. Static analysis, the complete backend suite, focused Phase 09–12 regressions,
contracts, security checks, dependency health, connector tests, and Git whitespace checks
all pass.

The remediation is ready to commit. This result does not establish live ACRA readiness,
approve an authentication contract, activate the dormant adapter, authorize another
phase, or imply real GoldTier/PingFed readiness.

## 2. Reviewed branch/worktree

- Requested branch: `codex/acra-bizfile-security-remediation`
- Actual remediation worktree:
  `C:\Users\shane\.codex\visualizations\2026\09\01\01a05c35-31f6-7ec3-95d1-fb0aa9936638\acra-bizfile-security-remediation`
- The initially supplied repository path was independently checked and found on
  `fix/acra-bizfile-security-guardrail` with unrelated UI work. It was not used as the
  remediation evidence source and was not modified by this gate.

## 3. Reviewed SHA / working-tree state

- Branch: `codex/acra-bizfile-security-remediation`
- `HEAD`: `b196d887964f0d93b93dfd2d39c271195eb19af9`
- Commit range `origin/main...HEAD`: empty
- Remediation state: uncommitted working-tree changes
- Staged changes: none
- Review included tracked modifications and all accessible untracked files.

## 4. origin/main baseline SHA

`origin/main` resolved independently to
`b196d887964f0d93b93dfd2d39c271195eb19af9`, equal to `HEAD`. Therefore the material
review boundary is the working-tree diff plus untracked remediation files, not a commit
range.

## 5. Diff inventory

| File | State | Classification | Assessment |
|---|---:|---|---|
| `apps/backend/app/connectors/acra_bizfile_sandbox.py` | Modified; 12 insertions, 101 deletions | EXPECTED SECURITY REMEDIATION | Removes only speculative OAuth/token code, its unused imports, and updates boundary comments/docstrings. |
| `apps/backend/tests/test_acra_bizfile_sandbox_connector.py` | Untracked/new | TEST | Five bounded tests for import/exposure, no-auth requests, HTTPS configuration, decoding, and fail-closed relationships. |
| `.ai-pipeline/reports/ACRA_BIZFILE_SECURITY_GUARDRAIL_REMEDIATION.md` | Untracked/new | DOCUMENTATION | Implementation report; treated as context, not proof. |
| `.ai-pipeline/reports/ACRA_BIZFILE_SECURITY_REMEDIATION_QUALITY_GATE.md` | Created by this gate | DOCUMENTATION | Sole review artifact created by this gate. |

No frontend, API, workflow, persistence, orchestration, GoldTier, ownership/UBO,
reconciliation, provider-routing, or UI file is part of the remediation worktree delta.

## 6. Original scanner finding

Running the repository scanner against the detached `origin/main` baseline produced
exactly two findings, with matched values suppressed:

- connector line 157: `sensitive-assignment` in the speculative authorizer's
  credential-member assignment;
- connector line 213: `sensitive-assignment` in response-token extraction.

Direct use of the scanner's own `scan_file` function reproduced those two rule/line
results. The baseline class was explicitly documented as not currently needed, retained
only on standby for a hypothetical future Marketplace endpoint, and not referenced by
application composition.

Classification: **SECRET-SCANNER POLICY VIOLATION**, not an actual credential leak.

## 7. Credential-leak assessment

No real client secret, access token, password, API key, bearer value, private key,
certificate, sponsor credential, or credential-bearing environment file was found in the
reviewed delta. The two baseline findings matched source-code expressions, not committed
credential literals, and the scanner suppressed the matched expressions as designed.

**Actual committed credentials found: 0**

## 8. Remediation approach

The connector removes `OAuth2ClientCredentialsAcraAuthorizer` in full, including:

- constructor/configuration for speculative credential inputs;
- token request and response parsing;
- bearer-header generation;
- in-memory token and expiry cache;
- lock and clock handling used only by that lifecycle;
- `threading` and `time` imports made unused by removal.

No replacement authentication mechanism was introduced. Existing connector code outside
that removal is unchanged apart from boundary comments/docstrings and a final newline.

## 9. Scanner weakening/evasion audit

- `scripts/check_secrets.py`: no diff
- `tests/test_check_secrets.py`: no diff
- `.github/workflows/ci.yml`: no diff
- No connector-specific exclusion, allowlist, suppression, ignore annotation, encoding,
  string splitting, identifier obfuscation, placeholder credential, renamed token flow,
  environment credential, or CI suppression was added.
- Current connector scan result: no findings.
- Repository-wide current scan result: PASS.

**Security scanner weakening: 0**  
**Scanner-evasion mechanisms: 0**

## 10. OAuth deferral verification

Repository searches covered `OAuth2ClientCredentialsAcraAuthorizer`, `client_secret`,
`access_token`, `token_url`, `Bearer`, and `client_credentials` across relevant backend,
scripts, tests, and documentation. Context review found:

- no speculative ACRA OAuth implementation remaining;
- no moved or renamed equivalent implementation;
- only legitimate scanner rules, contract/security assertions, and GoldTier contract
  documentation outside the remediated connector;
- no ACRA token-fetch, bearer-header, or token-cache path.

**Dormant speculative ACRA OAuth implementations remaining: 0**

## 11. Q-012 status

**OPEN.** `docs/sponsor-questions/OPEN_QUESTIONS.md` still contains Q-012 and continues to
request authoritative ACRA operation paths, schemas, authentication/authorization,
errors, rate/timeout guidance, TLS/mTLS/private-CA requirements, authorized subscription,
and approved credential delivery. Contracts, decisions, architecture, project context,
and the connector comments continue to defer live binding and authentication.

The remediation does not claim that no-auth is authoritative for future operations; it
limits the statement to the currently tested dormant entityQuery behavior.

## 12. No-auth behavior

**PASS.** Independent evidence establishes that:

- `app.connectors.acra_bizfile_sandbox` imports successfully;
- `NoAuthAcraAuthorizer.authorization_headers()` returns an empty mapping;
- the default request carries only `Accept: application/json`;
- UEN input is trimmed and uppercased and request query generation is preserved;
- HTTP base URLs are rejected by `AcraBizfileConnection`;
- invalid paths/credentials-in-URL/query/fragment and invalid timeout protections remain
  unchanged in the reviewed diff;
- HTTP error and transport-exception mapping code is unchanged;
- company, officer, and ownership-party decoding is unchanged;
- the unconfirmed relationship operation still fails closed.

## 13. Connector dormancy/composition

**PASS.** Current and `origin/main` composition import and instantiate only the established
`MockAcraConnector` and `AcraSandboxConnector`. The BizFile module is referenced only by
itself and its new focused test. The remediation does not modify composition or settings,
does not activate network traffic, and does not change the safe default Mock ACRA path.

**Unexpected provider/composition changes: 0**

## 14. Scope-boundary review

No live ACRA implementation, ACRA+ synthetic provider, ASIC or other jurisdiction
provider, real GoldTier, PingFederate, production authentication/RBAC, source-precedence
policy, UBO legal rule, workflow behavior, frontend behavior, persistence behavior, or
Ready-for-Approval behavior was introduced.

## 15. Secret-scan evidence

Command from remediation repository root:

`python scripts/check_secrets.py`

Result: **PASS** — `Secret scan passed: no supported secret patterns found.`

Baseline comparison from the detached `origin/main` worktree produced only the two
suppressed `sensitive-assignment` findings described in section 6.

## 16. Secret-scanner test evidence

Command from remediation repository root:

`python -m unittest discover -s tests -p "test_check_secrets.py"`

Result: **PASS — 5 tests, 0 failures, 0 errors.** The unchanged tests independently prove
detection of fake sensitive assignments and fake bearer headers, placeholder handling,
sensitive file-type detection, and output value suppression.

An initial sandboxed run was unable to create its repository-local temporary fixture
directory and reported five permission errors. The unchanged command was rerun with the
required fixture-write permission and passed 5/5; the failed sandbox invocation is not
treated as product evidence.

## 17. Ruff

CI-equivalent command from `apps/backend`, with repository cache disabled:

`python -m ruff check --no-cache .`

Result: **PASS — All checks passed.**

## 18. mypy

CI-equivalent strict analysis from `apps/backend`, using the checked-in strict config and
an external writable cache:

`python -m mypy --cache-dir <external-temp> app`

Result: **PASS — no issues in 73 source files.**

An initial no-incremental attempt hit a mypy 1.20.2 internal error while operating in the
read-only isolated worktree. The unchanged analysis with a writable external cache
completed successfully; no type error was reported.

## 19. Full backend suite

CI-equivalent command from `apps/backend`, with the repository root on `PYTHONPATH`:

`python -m pytest -p no:cacheprovider`

Result: **PASS — 711 passed, 11 skipped, 4 warnings, 0 failed in 28.62s.**

The 11 skips are the expected real-Mongo tests when `PHASE12_MONGO_URI` is unavailable.
Warnings comprise one existing Starlette/httpx deprecation and three deliberate malformed
provider-fixture serialization warnings. The previous approximate 706-pass baseline plus
the five new connector tests explains the current 711-pass result.

## 20. Phase regressions

Focused command executed the Phase 09, Phase 10, both Phase 11, Pre-Phase 12, Phase 12
persistence, and Phase 12 real-Mongo modules together.

Result: **PASS — 196 passed, 11 expected Mongo skips, 1 existing warning, 0 failed in
7.96s.** This preserves jurisdiction call-stopping, Mock registry acquisition, ownership
integration, reconciliation/resume, multi-document intake, persistence, and recovery
behavior.

## 21. Contract tests

CI command from `apps/backend`:

`python -m unittest discover -s ../../tests/contract -p "test_*.py"`

Result: **PASS — 44 tests, 0 failures, 0 errors in 0.788s.**

## 22. Security tests

Focused security/integration command covered the BizFile connector, established sandbox
connector, ACRA mode composition, and provider conformance modules.

Result: **PASS — 175 passed, 3 existing deliberate-malformed-fixture warnings, 0 failed
in 1.96s.** Coverage includes HTTPS-only configuration, TLS-verifying/no-redirect shared
transport assumptions, safe configuration failure, safe external-error mapping,
sanitized exception behavior, safe discovery output, Mock-default composition, and
provenance/input reconstruction. The full backend suite and exact secret checks provide
the remaining regression evidence. No external ACRA call was made.

## 23. Dependency health

Command using the project virtual environment:

`python -m pip check`

Result: **PASS — No broken requirements found.**

A discarded system-Python invocation reported a conflict in a globally installed,
project-unrelated package. The project virtual environment used by the repository checks
is clean and is the relevant dependency context.

## 24. Focused connector tests

Command from `apps/backend`:

`python -m pytest tests/test_acra_bizfile_sandbox_connector.py`

Result: **PASS — 5 passed in 0.99s.** A separate direct import probe also imported the
module and returned the expected empty no-auth header mapping.

## 25. Behavior comparison

| Behavior | `origin/main` before remediation | Remediated | Expected |
|---|---|---|---|
| Module import | Imports | Imports; directly verified | Preserved |
| No-auth behavior | Empty authorization mapping; default | Same; focused test passes | Preserved |
| Base URL validation | HTTPS URL required; userinfo/query/fragment rejected | Executable code unchanged; HTTP rejection tested | Preserved |
| HTTPS requirement | Enforced | Enforced | Preserved |
| Request generation | Normalized UEN and URL-encoded query | Same; exact request asserted | Preserved |
| Response decoding | Company/officer/shareholder decoders present | Same executable decoder code; focused tests pass | Preserved |
| Error mapping | Typed auth/timeout/unavailable/malformed errors | Same executable mapping code; security/full suites pass | Preserved |
| Connector activation/composition | Dormant and uncomposed | Dormant and uncomposed | Preserved |
| OAuth client credentials | Dormant speculative class retained | Removed and deferred pending Q-012 | Remove/defer |
| Token caching | Dormant in-memory token/expiry/lock lifecycle retained | Removed | Remove/defer |
| Secret scan | FAIL: two policy matches | PASS: zero supported findings | Pass without weakening/evasion |

All currently supported behavior is preserved. Only speculative OAuth/token behavior and
its unused imports were removed.

## 26. Git hygiene

- `git diff --check`: PASS; only an informational Windows LF-to-CRLF warning was emitted.
- `git diff --cached --check`: PASS.
- Staged changes: none.
- Conflict markers in remediation files: none.
- Accessible changed files before this gate report: exactly three, all classified in
  section 5.
- No changed `.env`, credential file, cache artifact, generated dependency directory, or
  build output.
- The repository tracks `.env.example`; it is unchanged and the secret scan passes.
- No commit, push, merge, rebase, reset, clean, stash, checkout, or staging action was
  performed by this gate.

## 27. Findings

### Critical

None.

### High

None.

### Medium

None.

### Low

None requiring remediation.

### Informational

- The remediation remains intentionally uncommitted and unstaged at the baseline SHA.
- Eleven real-Mongo tests are unavailable locally without `PHASE12_MONGO_URI`; this is
  the accepted baseline behavior and is unrelated to the connector-only change.
- Existing non-failing warnings are recorded in sections 19–22.
- The supplied repository path contained unrelated UI work on another branch; the actual
  isolated remediation worktree was located and reviewed directly.

## 28. Remaining limitations

- The BizFile adapter remains dormant and has not been live-tested.
- Q-012 still blocks authoritative operation/schema/authentication/TLS binding and live
  sandbox verification.
- The current no-auth claim is limited to the tested dormant Mock-tier entityQuery
  behavior and is not a future authentication policy.
- Existing sample-derived DTO mappings and defaults remain provisional.
- Relationships remain unconfirmed and fail closed.
- This gate does not establish production security, live registry connectivity, real
  GoldTier/PingFed integration, or Ready-for-Approval behavior.

## 29. Final verdict

Explicit metrics:

- Critical findings: 0
- High findings: 0
- Medium findings: 0
- Security scanner weakening: 0
- Scanner-evasion mechanisms: 0
- Actual committed credentials found: 0
- Dormant speculative ACRA OAuth implementations remaining: 0
- Unexpected provider/composition changes: 0
- Unrelated changed files: 0
- Backend regressions: 0
- Contract regressions: 0

The bounded remediation satisfies every PASS criterion. It is ready to commit, subject
to normal human review. No next phase was started, and live ACRA/GoldTier readiness
remains separately blocked by documented sponsor dependencies.

PASS — READY TO COMMIT ACRA BIZFILE SECURITY REMEDIATION
