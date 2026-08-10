# Phase 01 Quality Gate

## Executive Result

PASS

The final remediation rerun closes every previously blocking Phase 01 finding. All
accepted connector and mapping failures now persist a sanitized terminal `FAILED` case
before a safe HTTP 503 response is returned; explicit search outcomes prevent duplicate
shell creation; UEN normalization rejects blank input while retaining the modeled unknown-
UEN path; ACRA provenance and demo discovery are separated; Mock GoldTier no longer
depends on Mock ACRA or application identifier parsing; and configured regression tests
cover the new invariants.

All configured backend, frontend, contract, repository, security, validator, dependency,
build, diff, and untracked-whitespace checks passed after the environment-specific reruns
documented below. The five original deterministic scenarios passed without regression.

This gate modified only this report. It did not change application code or tests, stage,
commit, push, merge, or begin Phase 02.

## Phase 01 Acceptance Checklist

| Requirement | Result | Evidence |
|---|---|---|
| Review remained on `phase/01-vertical-slice` and within Phase 01 | PASS | Branch and complete status/diff verified; no Phase 02 implementation found or started. |
| Happy path traverses both connector boundaries | PASS | Independent recording probe observed ACRA fetch followed by GoldTier search, shell, policy, and amend. |
| Canonical model is distinct from ACRA and GoldTier models | PASS | Source payload, canonical entity/provenance, and GoldTier request DTOs remain separately modeled and mapped. |
| Every injected connector failure terminalizes safely | PASS | ACRA fetch and GoldTier search/shell/policy/amend exceptions each returned safe 503 and persisted retrievable `FAILED`. |
| Failure prevents prohibited downstream operations | PASS | Recorded call lists stopped exactly at the injected failing stage. |
| Search semantics prevent duplicate shell creation | PASS | Only `NO_MATCH` reached shell; `MATCH_FOUND` stopped non-destructively in review; modeled `FAILURE` stopped in failed state. |
| Input normalization is safe | PASS | Blank-after-trim returned 422; padded lowercase valid UEN normalized; well-formed unknown UEN remained an accepted request ending in registry-not-found `FAILED`. |
| ACRA boundary is replaceable | PASS | A replacement connector implementing only `fetch_company` completed the workflow and produced `ACRA/SANDBOX` provenance without service changes. |
| Mock connector boundaries are isolated | PASS | Mock GoldTier imports no Mock ACRA code/constants and uses explicit composition-time behavior keys plus prior policy request data. |
| Regression tests cover remediation invariants | PASS | Raising connectors, call stopping, all search outcomes, input normalization, state isolation, workflow invariants, and mapper errors are configured tests. |
| Original five scenarios remain correct | PASS | `COMPLETED`, `REVIEW_REQUIRED`, `FAILED`, `REVIEW_REQUIRED`, `FAILED` outcomes matched expectations. |
| Case retrieval and history remain coherent | PASS | GET equaled POST for original cases; sequence/timestamps/IDs were coherent and terminal state occurred only last. |
| UI remains clearly simulated | PASS | Backend supplies simulation profile; frontend renders ACRA/GOLDTIER mock environments and no-real-data labeling. |
| `COMPLETED` means only Phase 01 mock completion | PASS | Final event and documentation explicitly limit completion to required mock stages; no Ready-for-Approval claim exists. |
| Provisional GoldTier mock contract remains compliant | PASS | Mandatory overlays, source-case equality, canonical amend route, DTO aliases/enums, quarantine rules, and 207 concept remain intact. |
| Phase 01 remains credential-free and mock-only | PASS | No real auth/network connector, sponsor-private runtime dependency, raw sensitive logging, or later-phase feature was introduced. |
| Complete configured verification suite passes | PASS | Backend 26, contract 8, repository 18, validator 5, scanner 5, frontend 7, static checks, build, integrity, and whitespace checks passed. |

## Remediation Closure Summary

| Previous finding | Previous severity | Final result | Closure evidence |
|---|---:|---|---|
| Unexpected connector exceptions stranded persisted nonterminal cases | HIGH | CLOSED | `_run_required_stage` persists sanitized `FAILED` before raising `OnboardingInfrastructureError`; API returns retrievable safe 503 detail. Independent fault injection passed at every required connector stage. |
| Whitespace-only UEN returned `201 FAILED` | MEDIUM | CLOSED | Request-model before-validator trims/uppercases, rejects blank, and applies the explicit Phase 01 synthetic pattern; API regression and independent probes return 422. |
| Search `SUCCESS` semantics could create duplicate shells | MEDIUM | CLOSED | Dedicated `NO_MATCH`, `MATCH_FOUND`, and `FAILURE` result; only `NO_MATCH` reaches shell. |
| Canonical provenance and ACRA protocol contained mock-only concerns | MEDIUM | CLOSED | Canonical provenance is business source `ACRA` plus environment; demo discovery/configuration moved to a separate scenario catalogue. |
| Regression suite omitted resilience/search/isolation/input invariants | MEDIUM | CLOSED | New resilience/API/contract tests cover every listed invariant. |
| Mock GoldTier depended on Mock ACRA/application case formatting | LOW | CLOSED | Behavior keys are injected at composition; amend behavior uses policy external-key association by party ID. |
| Mapper preconditions used runtime `assert` | LOW | CLOSED | Explicit `MappingError` preconditions and regression tests replace assertions. |

## Required Re-verification

### 1. Unexpected Connector Failures

Independent ASGI fault injection was performed separately from the authored regression
tests. Each exception carried a unique internal sentinel to detect leakage.

| Injected stage | HTTP result | Persisted/GET result | Recorded connector calls | Safe terminal code | Result |
|---|---|---|---|---|---|
| ACRA fetch | 503 | GET 200, terminal `FAILED` | ACRA only; no GoldTier calls | `ACRA_RETRIEVAL_UNEXPECTED_FAILURE` | PASS |
| GoldTier search | 503 | GET 200, terminal `FAILED` | `search` | `GT_SEARCH_UNEXPECTED_FAILURE` | PASS |
| GoldTier shell | 503 | GET 200, terminal `FAILED` | `search`, `shell` | `GT_SHELL_UNEXPECTED_FAILURE` | PASS |
| GoldTier policy | 503 | GET 200, terminal `FAILED` | `search`, `shell`, `policy` | `GT_POLICY_UNEXPECTED_FAILURE` | PASS |
| GoldTier amend | 503 | GET 200, terminal `FAILED` | `search`, `shell`, `policy`, `amend` | `GT_AMEND_UNEXPECTED_FAILURE` | PASS |

Every 503 response contained exactly safe `code`, `message`, `case_id`, and
`correlation_id` detail. Original exception text, the sentinel, `RuntimeError`, and
`traceback` were absent. The last stored event had `stage=FAILED`, `outcome=FAILED`, and
the stage-specific code. No `COMPLETED` event or operation after the failing stage was
observed.

The configured suite additionally covers an ACRA mapping exception, which persisted
`FAILED/ACRA_MAPPING_UNEXPECTED_FAILURE` and made no GoldTier call.

### 2. Search Semantics

| Search outcome | Actual behavior | Result |
|---|---|---|
| `NO_MATCH` | Shell permitted; exact path `search -> shell -> policy -> amend`; final `COMPLETED`. | PASS |
| `MATCH_FOUND` | Shell skipped; search only; final `REVIEW_REQUIRED/GT_EXISTING_PARTY_REVIEW_REQUIRED`; no target result or completion. | PASS |
| `FAILURE` | Shell skipped; search only; controlled final `FAILED/GT_SEARCH_FAILED`; no infrastructure 5xx or completion. | PASS |

`MATCH_FOUND -> REVIEW_REQUIRED` is explicitly documented as a conservative,
non-destructive project behavior while the sponsor's existing-candidate NTB behavior is
unresolved. It is not represented as known GoldTier production behavior.

### 3. Input Normalization

| Input | Actual result | Result |
|---|---|---|
| Whitespace-only UEN | 422; no case created. | PASS |
| Empty/missing/malformed UEN | 422. | PASS |
| Padded lowercase `202400001a` | Normalized to `202400001A`; normal happy path. | PASS |
| Well-formed unknown `999999999Z` | Accepted with 201; terminal `FAILED/ACRA_ENTITY_NOT_FOUND`. | PASS |

The nine-digits-plus-letter rule remains explicitly limited to Phase 01 synthetic/demo
input and is not claimed as the final production ACRA rule.

### 4. ACRA Replaceability

PASS. Canonical provenance now uses `SourceSystem.ACRA` independently from
`SourceEnvironment.MOCK/SANDBOX/LIVE`. `AcraConnector` requires only `fetch_company`; mock
scenario discovery and behavior configuration are owned by `MockScenarioCatalogue`.

An independent `ReplacementAcraConnector` implementing only registry fetch completed the
full workflow through the unchanged `OnboardingService`, produced canonical
`ACRA/SANDBOX` provenance, and did not implement demo discovery. The discovery endpoint
continued to operate through the separate catalogue.

### 5. Mock Isolation

PASS. `MockGoldTierConnector` imports no Mock ACRA module or constants. Composition passes
policy-failure and partial-amend external keys explicitly. Generated party IDs derive from
correlation ID, not application source-case formatting. Successful policy requests store
their external key by party ID, and partial amend behavior uses that prior request data.

### 6. Regression Protection

Configured tests now cover:

- ACRA retrieval and mapping exceptions;
- GoldTier search, shell, policy, and amend exceptions;
- safe 503 fields, retrievable terminal case, sanitized final event, and stopped calls;
- `NO_MATCH`, `MATCH_FOUND`, and modeled search `FAILURE`;
- blank/padded-lowercase/well-formed-unknown input;
- multiple mixed-outcome cases and repository isolation;
- contiguous event sequence, nondecreasing timestamps, identifier consistency, and
  terminal-only final events; and
- explicit mapper errors rather than runtime assertions.

### 7. Original Scenario Results

| Scenario | Expected | Actual | GoldTier call behavior | Result |
|---|---|---|---|---|
| `202400001A` | `COMPLETED` | `COMPLETED` | Search, shell, policy, amend; exact eight-stage history. | PASS |
| `202400002B` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | Stops after incomplete canonical validation; no GoldTier calls. | PASS |
| `202400003C` | `FAILED` | `FAILED` | Search, shell, policy failure; no amend or later success. | PASS |
| `202400004D` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | Partial `GT_ENRICHED`, then review; no completion. | PASS |
| `999999999Z` | `FAILED` | `FAILED` | ACRA not found; no GoldTier calls. | PASS |

GET returned the same current case generated by POST for every original scenario.
Multiple-case probes retained independent states and unique party/case identifiers across
mixed execution order and separate service instances.

### 8. Architecture Answers

1. **Can MockAcraConnector be replaced by a real ACRA connector without rewriting
   OnboardingService?** Yes. The service consumes the retrieval-only protocol and maps its
   source payload to source-neutral canonical provenance; demo discovery is separate.
2. **Can MockGoldTierConnector later be replaced by a real GoldTier connector without
   changing the fundamental onboarding workflow?** Yes at the architectural level. A real
   adapter can implement the four typed connector methods and explicit search outcomes;
   workflow branching and failure handling do not depend on the mock implementation.
3. **Can any modeled or unexpected covered failure leave a persisted case in a false
   nonterminal state?** No. Modeled failures/review outcomes terminate explicitly, and
   exceptions at every connector/mapping stage first persist sanitized `FAILED`. Regression
   and independent probes found no false completion or stranded intermediate case.

Real GoldTier implementation is still not authorized or ready; the architectural answer
does not imply sponsor contract, authentication, networking, or Ready-for-Approval
readiness.

## Contract Analyst Findings

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

None.

The independent contract workstream concluded that remediation introduced no provisional-
contract violation. Search outcomes are internal adapter/application semantics, not
standalone transport enums. The mock 200/no-match, validation failure, 207 partial amend,
and non-destructive existing-candidate review remain visibly synthetic behavior rather
than sponsor production claims.

Mandatory shell country and policy external-reference fields remain required; canonical
amend and source-case forms remain unchanged; stale DSD forms and the stale amend path are
absent from application/frontend source; quarantined sponsor JSON remains excluded; mock
identifiers/constants remain development-only; and GoldTier paths remain connector-
internal.

The unified metadata object still carries POST metadata when passed to the search mock,
which ignores it. A future real GET adapter must emit operation-appropriate headers. With
no Phase 01 HTTP transport, this is an acceptable mock simplification rather than an active
contract violation.

## Tester Findings

### Commands and exact results

| Command / check | Result |
|---|---|
| `.venv\Scripts\python.exe -B -m pytest apps/backend/tests -p no:cacheprovider` | PASS — 26 tests in 0.55s. |
| `.venv\Scripts\python.exe -B -m ruff check --no-cache apps/backend scripts tests` | PASS. |
| `.venv\Scripts\python.exe -B -m mypy --no-incremental --cache-dir <temporary-path> apps/backend/app` | PASS — strict mode, 22 files. |
| `.venv\Scripts\python.exe -B -m unittest discover -s tests/contract -p test_*.py -v` | PASS — 8/8. |
| `.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_*.py -v` | Environment-only import failure after 13 passing tests because backend venv lacks separately pinned `jsonschema`. |
| `python -B -m unittest discover -s tests -p test_*.py -v` | PASS rerun — 18/18 repository tests. |
| `python -B -m unittest discover -s tests -p test_validate_goldtier_examples.py -v` | PASS — 5/5 Phase 00 validator regressions. |
| `.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_check_secrets.py -v` | PASS — 5/5. |
| `python -B scripts/validate_goldtier_examples.py --if-present` | PASS — `VALID=19`, `INVALID_QUARANTINED=19`, `NOT_VALIDATED=48`. |
| `python -B scripts/validate_goldtier_examples.py --fail-on-invalid` | Expected exit 1 with the same classification; quarantine enforcement confirmed. |
| `.venv\Scripts\python.exe -B scripts/check_secrets.py` | PASS. |
| `.venv\Scripts\python.exe -B -m pip check` | PASS — no broken project requirements. |
| `npm.cmd ls --all` in `apps/frontend` | PASS — dependency tree valid; only expected optional platform/feature packages absent. |
| `npm.cmd run typecheck` | PASS. |
| `npm.cmd test` | Initial sandbox `spawn EPERM`; approved rerun PASS — 1 file, 7 tests. |
| `npm.cmd run build -- --outDir <temporary-path>` | Initial sandbox `spawn EPERM`; approved rerun PASS — 28 modules; output outside repository. |
| `git diff --check` and `git diff --cached --check` | PASS; CRLF conversion warnings only. |
| Per-file untracked `git diff --no-index --check -- NUL <file>` | PASS — 31 files, zero whitespace issues. |

No required check was skipped. Hosted GitHub Actions itself was not invoked; every
constituent local command was run. No frontend lint or dependency-vulnerability audit
script is configured. Validator/repository checks used the existing system Python because
the backend venv intentionally lacks the validator-only `jsonschema` dependency. The
system environment has an unrelated package mismatch, while the isolated project venv
passed integrity checks.

### Severity findings

- CRITICAL: None.
- HIGH: None.
- MEDIUM: None.
- LOW: None.

## Code & Architecture Review

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

Frontend tests remain component/API-helper oriented rather than a fully mounted
interactive App test. They do not exercise the actual `useEffect`, form loading transition,
or UI recovery using the safe 503 case ID. This is a non-blocking test-depth observation;
the required backend resilience, API contract, simulation metadata, and frontend rendering
are covered.

### Architecture assessment

| Area | Result | Evidence |
|---|---|---|
| Connector abstraction | PASS | `OnboardingService` depends only on ACRA, GoldTier, and repository protocols; mocks live at composition. |
| Canonical boundary | PASS | Source, canonical, and target DTOs are distinct with dedicated mappers; mockness is separate provenance environment. |
| Orchestration separation | PASS | Workflow, search branching, and terminal error handling remain in the service rather than FastAPI or React. |
| Mock replaceability | PASS | Real ACRA needs retrieval only; real GoldTier can implement typed methods/outcomes without fundamental workflow change. |
| Persistence | PASS for Phase 01 | Repository protocol/deep copies and isolation tests support later replacement; in-memory lifetime remains accepted. |
| Frontend/backend separation | PASS | React presents backend state/profile through a separate API client and does not determine workflow state. |
| Scope | PASS | No real connector/auth, IDP, UBO, hierarchy, Camunda, Ready-for-Approval, analytics, or extra jurisdiction was introduced. |

## Security Review

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

- The current secret scanner is a worktree pattern scanner rather than a mature history,
  archive, or entropy scanner.
- CI actions still use mutable major-version tags rather than approved immutable revisions.

These are accepted pre-real-integration hardening items, not mock-only Phase 01 failures.

Security verification confirmed:

- no committed secret, credential, token, key, certificate, or auth implementation;
- `private/` remains ignored and no private sponsor path is tracked;
- application/tests do not import or reference the quarantined PingFed/Postman collection;
- no real ACRA/GoldTier network client or request path exists in application code;
- safe 503 responses and stored events exclude original exception text, traceback,
  payloads, credentials, and implementation details;
- case history contains safe identifiers/status/code/message only, not raw corporate/KYC
  payloads;
- frontend environment access is limited to public `VITE_API_BASE_URL`;
- CI remains credential-free and sponsor-private-artifact independent; and
- no new dependency version was introduced by remediation.

Security commands included the scanner and five tests, private-path tracking/ignore checks,
focused auth/network/logging/filesystem/frontend-environment searches, project `pip check`,
and frontend dependency-tree inspection.

## Accepted Phase 01 Technical Debt

- Process-local in-memory storage and loss of state after restart.
- Synchronous request-time orchestration.
- Credential-free mock ACRA and GoldTier connectors.
- No database, asynchronous worker, or retry engine.
- No real Ready-for-Approval action or real credentials/authentication.
- No real connector networking, IDP, UBO, hierarchy, relationship, or later-phase workflow.

These are intentional Phase 01 limits and did not reduce the gate result.

## Required Fixes Before Phase 02

None.

The low frontend test-depth observation is recommended future improvement, not a Phase 02
blocker. It does not reopen any remediated backend/API/workflow invariant.

## Later Sponsor and Real-Integration Dependencies

- Authorized real ACRA endpoint/access/provenance contract and agreed IDP document types/
  fields before real ACRA/IDP integration work that depends on them.
- UBO threshold, hierarchy retrieval, and related-party semantics before those phases.
- Sanitized authentication reference, rotation/revocation confirmation, fresh approved
  credentials, EDS/PingFed URLs, scopes/client-auth, TLS/mTLS/private-CA, and sandbox
  networking details before real GoldTier.
- Sponsor-approved Singapore mappings/value lists, corrected examples/bundle, mandatory-
  field confirmation, search matching semantics, and Ready-for-Approval behavior before
  claiming production GoldTier interoperability.
- Mature secret/history scanning, dependency-vulnerability auditing, and immutable CI
  action pinning before higher-trust integration/deployment.

## Phase 02 Recommendation

Phase 02 readiness: READY FOR PHASE 02

Real GoldTier integration readiness: NOT READY

Phase 02 may build on the remediated interfaces without redesigning the Phase 01
orchestration. Real GoldTier remains separately blocked by intentionally deferred sponsor,
authentication, environment, mapping, networking, and security-hardening prerequisites.

## Git Status

- Current branch: `phase/01-vertical-slice`
- HEAD: `901140f` (`feat: establish Phase 00 project foundation`)
- Modified tracked files: 9
  - `.github/workflows/ci.yml`
  - `README.md`
  - `apps/backend/app/config.py`
  - `apps/backend/app/main.py`
  - `apps/backend/pyproject.toml`
  - `apps/frontend/src/App.test.tsx`
  - `apps/frontend/src/App.tsx`
  - `apps/frontend/src/styles.css`
  - `apps/frontend/vite.config.ts`
- Untracked files: 31, including the Phase 01 planner/remediation documents, report,
  backend connector/demo/domain/mapper/service modules and tests, frontend API/types,
  architecture document, and Phase 01 contract tests.
- Staged files: none.
- Commits performed by this gate: no.
- Push performed: no.
- Merge performed: no.
