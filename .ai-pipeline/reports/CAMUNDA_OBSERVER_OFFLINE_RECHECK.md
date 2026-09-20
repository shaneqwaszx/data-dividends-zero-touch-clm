# Camunda Observer Offline Contract — Independent Recheck

## Executive result

The frozen test-only implementation satisfies the authorized offline observation
contract. It remains isolated from production composition, uses only fake read and
engine ports, maps the pinned public response fields and existing enums exactly, limits
each invocation to no more than two reads, minimizes process output, and represents
completion uncertainty without retrying or issuing a contradictory failure command.

This gate proves only the bounded offline contract. It does not prove a Camunda worker,
real authentication, backend connectivity, persistence behavior, deployment, job-worker
concurrency, an atomic aggregate snapshot, exactly-once delivery, or production
readiness. The only permitted success language is **OFFLINE CONTRACT VERIFIED**.

## Authority, scope, and preflight

- Review role: fresh independent focused quality gate. No implementation or remediation
  was performed.
- Source handoff: Codex task `01a0bddd-614f-76a3-a80f-04892a94ad9f`, title
  `Define Camunda read-only contract`; its completed final answer was read in full.
- Implementation authorization: Codex task
  `01a0bded-d117-7183-9657-0f4cdcc4a40e`, title
  `Add Camunda observation contract`; its complete attached task text was read from the
  task attachment.
- Relevant authority read: `AGENTS.md`, `docs/PROJECT_STATE.md`,
  `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT_WORKFLOW.md`, the current sponsor questions,
  Zero-Touch/integration contracts, decision log, `fyp-quality-gate`,
  `integration-safe-development`, its pre-PR checklist, and the branch/merge protocol.
- Change classification: bounded test-contract evidence plus documentation; no
  production `BACKEND_DOMAIN`, `BACKEND_API`, authentication, persistence, provider,
  runtime-composition, dependency, or CI change.
- Available and used: local PowerShell, Git 2.55.0, Python 3.12.10, repository-pinned
  pytest 8.4.2, Ruff 0.16.2, mypy 1.20.2, task-reading tool, and read/write access scoped
  to this worktree. The reviewer wrote only this report.
- Prohibited and unused: network, Git fetch/mutation, services, ports, browser,
  databases, credentials, `.env`, backend server/application boot, Camunda runtime/SDK,
  BPMN deployment, providers, and sibling worktrees.

## Evidence identity

| Identity | Observed value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-camunda-observer` |
| Branch | `spike/camunda-observer-contract` |
| `BASE_SHA` | `cab05d7dc98d4c50c8fc096835fe49802d5896e2` |
| Current `HEAD` | `cab05d7dc98d4c50c8fc096835fe49802d5896e2` |
| Locally observed `origin/main` | `cab05d7dc98d4c50c8fc096835fe49802d5896e2` |
| Merge base | `cab05d7dc98d4c50c8fc096835fe49802d5896e2` |
| Tracked state before report | Clean |
| Task-owned state before report | Exactly three untracked files; no staged files or unresolved paths |

Frozen reviewed paths and Git blob identities, recomputed before the review and again
after verification:

| Reviewed path | Git blob identity |
|---|---|
| `apps/backend/tests/camunda_observer_contract_support.py` | `8ffaf7d0cb830c176edb70fc8398bd166a69d57e` |
| `apps/backend/tests/test_camunda_observer_contract.py` | `d78458abdf6317b41ed532c4807402cad3eda965` |
| `docs/integration/CAMUNDA_OBSERVER_OFFLINE_SPIKE.md` | `7d4bdcb7acd4e81f001fd24599b3cc7fb734776b` |

The current source revision, tested behavioral baseline, and reviewed content are thus:

- current source revision: `HEAD cab05d7d...` plus the three untracked blobs above;
- tested behavioral baseline: the same `HEAD` and exact three frozen blobs;
- independently reviewed content: the same three paths and blob identities.

## Acceptance checklist

| Criterion | Result | Independent evidence |
|---|---|---|
| Strict test-only placement and production isolation | Verified | Handler/support and tests exist only under `apps/backend/tests`; bounded search found no import, composition, or job-type reference under `apps/backend/app`, `apps/frontend`, or `.github`. No production/config/dependency file changed. |
| Exact job/input/output contract | Verified | Job type is `clm.observe-case.v1`; variables must be exactly one canonical UUID string `caseRef`; output is freshly constructed under `clmObservation` with only the authorized observed or unavailable fields. Extra/stale variables fail before any read. |
| Exact source mapping and enum authority | Verified | Direct source inspection confirms `case.case_id`, root `status`, root `current_stage`, root `version`, and `clm.version` in `ZeroTouchCaseSummaryResponse`; validation imports the existing `AutomationStatus` and `AutomationStage` enums rather than creating a second business authority. |
| Limited observation guarantee | Verified | The handler compares only the selected projection across two reads. A test changes unobserved CLM/debug content while selected fields match and still completes, explicitly demonstrating that no atomic aggregate snapshot or intervening-change guarantee is claimed. Documentation repeats the limitation. |
| Safe absence and second-read disappearance | Verified | First `404` performs one read and returns only fresh `NOT_AVAILABLE`; `200` then `404` discards all first-read statuses/versions and returns only the three unavailable fields. Missing/inaccessible/deleted labels are deliberately indistinguishable. |
| Authentication failure semantics | Verified | `401` and `403` on either read produce `AUTHENTICATION_CONFIGURATION_FAILURE`, never `NOT_AVAILABLE`, and emit no completion variables. Fake identity success is not described as real access proof. |
| Failure handling and sanitization | Verified | Timeout, typed transport failure, `5xx`, unexpected status, malformed JSON/shape, wrong case identity, invalid enums/types, missing fields, and oversized bodies fail closed. Raw response and exception text are not included in dispositions. Size is checked before JSON parsing. |
| At-most-two reads and no internal retry | Verified | Static control-flow inspection shows invalid input uses zero reads, first `404` one, and every other path at most two. Exact-count tests cover success and failures on each read. There is no loop, sleep, polling, background task, or recursive retry. |
| Completion acknowledgement and rejection | Verified | Acknowledged completion is modeled; rejection returns a rejected state with no fail command; lost acknowledgement returns an ambiguous state after exactly one completion attempt with no fail command or compensating mutation. |
| Redelivery and overlapping fake workers | Verified | Redelivery performs fresh reads without inherited output. Two fake handlers for one job key simulate a single completion winner and rejected loser. Documentation accurately limits this to fake protocol behavior, not proof of Camunda concurrency or delivery bounds. |
| Data minimization | Verified | Broad synthetic responses contain prohibited UEN/name/team/document/reconciliation/target/auth markers. Exact-output and sanitization assertions prove they are neither forwarded nor captured in the tested result/failure records. `NOT_AVAILABLE` has no stale status/version fields. |
| No mutation/provider/repository capability | Verified | The application-facing protocol exposes only `read_case`; the handler has no mutation/provider/repository port. Tests verify absence of forbidden methods and fail-fast spy behavior. No real application, provider, repository, or persistence layer is executed. |
| Documentation honesty | Verified | The spike document distinguishes fake offline evidence from real execution; preserves session-housekeeping and broad-response limitations; makes no machine-auth, runtime, atomicity, exactly-once, end-to-end, Live, or production-readiness claim. |
| Normal pytest discovery | Verified | Normal backend `python -m pytest --collect-only -q` discovered `tests/test_camunda_observer_contract.py: 58` in a 1,076-test inventory. All 58 focused observer tests then executed and passed. |

## Findings by severity

- Critical: none.
- High: none.
- Medium: none.
- Low: none requiring remediation.

Informational limitations are correctly retained rather than treated as accepted runtime
proof: production machine identity and least privilege are unresolved; the real GET
returns a broad browser response; current session validation may perform process-local
housekeeping; a future transport needs streaming/body limits; the actual Camunda
version, tenant, SDK, authorization, endpoint, TLS/network, licence, deployment, and
cleanup authority remain unverified.

## Commands and results

| Command | Result |
|---|---|
| `python scripts/dev_context.py` | Branch `spike/camunda-observer-contract`; `HEAD`, local `origin/main`, and merge base all `cab05d7d...`; tracked tree clean; exactly the three task files untracked. |
| `git hash-object -- <three frozen paths>` | Exact assigned blobs `8ffaf7d...`, `d78458a...`, `7d4bdcb...` before review and after checks. |
| `python -m pytest --collect-only tests/test_camunda_observer_contract.py -q` | 58 tests collected. |
| `python -m pytest tests/test_camunda_observer_contract.py -q` | 58 passed. |
| `python -m pytest --collect-only -q` | Normal backend discovery included the observer module with 58 tests; 1,076 tests collected overall. Collection only; the broad suite was not executed by this reviewer. |
| `python -m ruff check --no-cache tests/camunda_observer_contract_support.py tests/test_camunda_observer_contract.py` | All checks passed. |
| `python -m ruff format --check --no-cache <two observer Python files>` | Two files already formatted. |
| `python -m mypy --no-incremental <two observer Python files>` | Success; no issues in two source files. |
| `python scripts/check_project_state.py` | `PROJECT STATE CHECK: PASS`. |
| `python scripts/check_architecture.py` | `ARCHITECTURE CHECK: PASS`. |
| `python scripts/check_tooling_config.py` | Exact optional Docs/disabled cluster configuration check passed. |
| `python scripts/check_secrets.py` | No supported secret pattern in tracked or non-ignored untracked files. |
| `git diff --check` plus per-new-file `git -c core.autocrlf=false diff --no-index --check` | No whitespace error; explicit untracked-file coverage completed. |
| Conflict-marker scan of the three task files | No marker found. |
| Bounded production-reference search | No support-module, test-module, or job-type reference in production backend, frontend, or CI paths. |

## Skipped and nonapplicable checks

- Full backend pytest was not independently rerun. It is unnecessary for this frozen
  test-only reference module under the user's proportionate local-fake-only review
  boundary. The evidence document's prior broad result is implementation evidence, not
  substituted independent evidence.
- Backend server/application boot and real HTTP were prohibited. The handler imports
  existing domain enums only; all observer execution used fake ports.
- Physical Mongo, browser/Playwright, Windows lifecycle, provider, real authentication,
  network, Camunda cluster/SDK/worker, BPMN deployment, and credential checks are
  nonapplicable to this test-only slice and explicitly unauthorized.
- Remote fetch, PR, and CI observation were prohibited. `origin/main` here is a local
  observation, not fresh remote evidence.
- `python scripts/pre_pr_check.py` was not run because the accepted three files and this
  gate report remain intentionally untracked; the checker is a clean committed-tree
  publication gate owned by the separately authorized publisher.

## Security and architecture conclusion

No secret, credential, raw response body, raw exception text, KYC/PII field, target
identifier, broad input map, or stale prior observation is projected by the verified
paths. The fake ports do not create a new production owner, authentication shortcut,
transport abstraction, worker framework, or mutation surface. Current architecture
truth remains unchanged: Camunda is not implemented, and the existing authenticated
case GET remains the only mapped future read boundary.

## Required fixes and publication readiness

No current fix is required for the frozen content. Exact publication eligibility is
limited to these three reviewed blobs plus this report, subject to the separate
publisher rechecking unchanged identities, scoped staging, clean-tree pre-PR evidence,
latest-main drift, push/PR authorization, and applicable CI. The owner must not infer
authorization for any real experiment or runtime action from this gate.

## Final verdict

PASS
