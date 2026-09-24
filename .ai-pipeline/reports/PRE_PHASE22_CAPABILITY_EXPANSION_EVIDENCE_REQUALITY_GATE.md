# Pre-Phase 22 Capability Expansion Evidence Re-Quality Gate

Date: 2026-09-24
Reviewer: fresh independent quality-gate role
Reviewed source revision: `3ca232b58c3842f413c4552dbd3b85aabea4591c`
Reviewed behavior: frozen working-tree candidate at the fingerprint recorded below

## 1. Findings First

### Minor — ERQG-01: the advisory demo contains a stale GoldTier XPI availability statement

`docs/demo/PRE_PHASE22_INTELLIGENCE_DEMO.md:42-43` says that GoldTier XPI mapping
preview and Customer Search are unavailable because the provider artefacts and
configuration were not supplied. That statement is no longer current: the canonical
project state, D-048/ADR-004, owning source, and this candidate describe and implement a
guarded `SANDBOX_PARTIAL` XPI mapping-preview and read-only Customer Search lane. The
walkthrough may remain intentionally Mock-only, but its reason must distinguish that
demo boundary from the currently available partial sandbox capability and must continue
to avoid a Live or mutation claim.

Impact: documentation truthfulness only. Runtime behavior, provider identity ownership,
Q-016, and the Phase-22 hold are unaffected.

### Minor — ERQG-02: one task-owned untracked Markdown file fails whitespace hygiene

`docs/demo/PRE_PHASE22_INTELLIGENCE_DEMO.md:49` is an extra blank line at end of file.
Candidate-scoped `git diff --no-index --check` reported `new blank line at EOF`, and the
file ends in `0a0a`.

Impact: hygiene only; no behavioral or security consequence.

No Critical or Important defect was found. The physical provider-identity and browser
evidence closures themselves resisted the reviewed false-success paths.

## 2. Executive Result

The two requested acceptance-evidence gaps are substantively closed:

- the new real-Mongo suite passed all six provider-identity cases and the complete
  guarded physical runner passed all 35 collected tests with zero skip;
- five independent fresh-process Case Activity browser runs and the exact complete
  configured browser suite passed without retry, timeout, sleep, or assertion changes.

The provider identity remains owned by `GoldTierSubmissionPlan`; schema-v5 validation,
mapper/connector compatibility assertions, restart rejection, and plan-only behavior
remain aligned. The guarded Vite keep-alive agent is activated only by the E2E frontend
marker and does not change ordinary development or production behavior.

The result is **PASS WITH MINOR FIXES** because ERQG-01 and ERQG-02 are bounded,
low-risk documentation corrections. This is not the exact `PASS` required to authorize
the coordinator's publication workflow.

## 3. Phase Acceptance Checklist

| Requirement | Result | Direct independent evidence |
| --- | --- | --- |
| Frozen candidate identity before review | Pass | 151 paths; SHA-256 `3836b8a4eb7d2119dc1c33d833f0a4d61a122272dc118964bb2a9e479cbbf482`; expected first and last entries matched; zero staged paths. |
| Stable Mock and Sandbox identity across Mongo restart | Pass | Parameterized physical cases persisted, reconstructed, and compared each identity. Isolated suite: 6/6. Complete runner: 35/35. |
| Both plan/submission-input contradiction directions | Pass | Physical tests separately replace persisted plan identity and submission-input identity and require fail-closed `PersistenceError`. |
| Matching-ledger contradiction | Pass | Physical test corrupts matching submission ledger identity and requires fail-closed recovery. |
| Valid Sandbox plan-only/no-submission | Pass | Physical plan-only case reconstructs valid Sandbox identity with no submission ledger. |
| Disposable database ownership, exact collections, cleanup | Pass | Each physical case generates an allowlisted `clm_p12_*` database, proves it absent before use, checks the exact permitted collection inventory, removes it in `finally`, and proves absence afterwards. Runtime completed with zero skips. |
| URI non-disclosure | Pass | Container binding and `PHASE12_MONGO_URI` were derived only inside the command; neither value was printed or persisted. The task-owned container was not stopped. |
| Complete physical-runner registration and sanitization | Pass | New suite is the ninth guarded suite; unit inventory passed 48/48 with E2E runner units. Complete physical execution reported `SUITES=9; COLLECTED=35; PASSED=35; FAILED=0; ERRORS=0; SKIPPED=0`. |
| Browser stall diagnosis is proportional | Pass | Installed Vite's bundled `http-proxy` behavior was inspected: absent agent forces connection close; the change supplies one keep-alive agent only in guarded E2E. The evidence supports connection-lifecycle stabilization and does not claim a broader browser/backend defect. |
| Repeated fresh-process Case Activity evidence | Pass | Five separate backend/frontend Playwright lifecycles on distinct port pairs passed the selected Case Activity tests, 7/7 per run, in 3.1-3.5 seconds. |
| Exact complete configured browser suite | Pass | `scripts/run_e2e.py` passed 14/14 isolated lifecycle tests; the Case Activity selection passed 7/7; cleanup succeeded. Playwright retains `retries: 0`, one worker, and the existing timeout. |
| Guarded activation and no ordinary dev/production drift | Pass | `HttpAgent` is created only when `CLM_E2E_FRONTEND_PORT` is present and is applied only to the Vite dev proxy. Without the marker, `agent` is undefined; production does not use the Vite development proxy. |
| No hidden retry/sleep/timeout/assertion weakening | Pass | Full closure diff and runner/config/test inspection found none. Exact configured runs passed without retries. |
| Canonical provider-identity ownership | Pass | `GoldTierSubmissionPlan` remains the immutable owner; persistence validation cross-checks plan, input, and ledger; mapper/connector compatibility assertions remain present; no duplicate provider owner/router/fallback or schema version was introduced. |
| Temporary activity tracing retired | Pass | No temporary trace instrumentation remains in the reviewed frontend/backend path; the durable Case Activity behavior is covered by normal E2E assertions. |
| Scope and authority boundaries | Pass | No provider activation, external mutation, GoldTier redesign, Live claim, Q-016 answer, or Phase-22 implementation was found. Mock/Sandbox/Local/Partial/Dormant/Live distinctions remain explicit. |
| Candidate hygiene | Minor fix | Tracked `git diff --check` found no error, but candidate-scoped untracked-file checking found ERQG-02. |
| Candidate documentation truth | Minor fix | ERQG-01 must be corrected before an exact-pass publication gate. |

## 4. Contract and Integration Findings

The current authority chain was read in the required order: constitution and development
workflow; architecture/project state; persistence, Case Activity, external-provider,
and GoldTier discrepancy contracts; decisions and open questions; then the owning
source/tests and the nearest reports/checkpoint. The implementation and prior gate were
used as supporting evidence, not as authority over current contracts or source.

- `GoldTierSubmissionPlan` remains the single durable provider-identity owner. Persisted
  submission input and target-call ledger values are compatibility assertions, not new
  ownership paths.
- Schema v5 remains current. The closure adds evidence; it does not add a migration or a
  schema version.
- Mock remains the default GoldTier target. XPI remains `SANDBOX_PARTIAL`; Customer
  Search is read-only, and no mutation or interoperability claim is made.
- Q-016 remains deferred. Assignment, SLA, notes, mutation history, and Phase 22 remain
  held.
- No contradictory GoldTier example was promoted into a DTO, fixture, enum, mapping, or
  assertion.
- ERQG-01 is the sole contract-language discrepancy found in the candidate: an auxiliary
  demo's explanation lags the canonical current state.

## 5. Tester and Adversarial Findings

### Fresh independent runtime evidence

| Command/check | Exact result |
| --- | --- |
| `python scripts/run_physical_mongo_tests.py --timeout-seconds 900` with the URI derived internally from `clm-provider-identity-mongo-20260924` | `PHYSICAL_MONGO_RESULT=PASSED; SUITES=9; COLLECTED=35; PASSED=35; FAILED=0; ERRORS=0; SKIPPED=0` |
| `python -m pytest -o addopts= -p no:cacheprovider apps/backend/tests/test_provider_identity_real_mongo.py -q` with the same guarded derivation | `6 passed in 2.32s` |
| Five fresh `scripts/run_e2e.py` Case Activity selections on distinct port pairs | Five passes; each selection was `7 passed`, elapsed 3.1-3.5 seconds; each lifecycle cleaned up. |
| `python scripts/run_e2e.py --backend-port 20765 --frontend-port 21173 --timeout-seconds 900` | Complete configured suite `14 passed`; Case Activity selection `7 passed in 3.2s`; cleanup succeeded. |
| Focused orchestration/persistence/provider-conformance/activity pytest set | `320 passed`; only the three expected Pydantic warnings from deliberately malformed provider fixtures. |
| `python -m pytest -p no:cacheprovider tests/test_run_physical_mongo_tests.py tests/test_run_e2e.py -q` | `48 passed in 10.74s`. |
| Frontend `npm.cmd test` | `22` files, `282` tests passed; existing React SSR/useLayoutEffect and `act` warnings only. |
| Frontend `npm.cmd run typecheck` | Exit 0. |
| `python -m unittest discover -s tests/contract -p "test_*.py"` | `44` tests, `OK`. |
| `python -m ruff check apps/backend/app apps/backend/tests tests scripts` | All checks passed. |
| Backend `python -m mypy app --no-incremental` | Success: no issues in 105 source files. |
| `check_project_state.py`, `check_architecture.py`, `check_policy_authority.py`, `check_external_provider_readiness.py` | All four direct checks passed. |

The physical adverse paths use raw persisted-document corruption followed by both
`get` and `initialize` recovery attempts. Therefore the tests do not merely assert
constructor behavior: they exercise restart reconstruction and reject both stale and
contradictory durable representations. Positive cases also assert exact identity,
revision, absence/presence of the submission ledger as appropriate, collection
inventory, and cleanup, which limits false success through skip, empty collection, or
unowned database reuse.

### Restricted-environment failures retained in the record

- The first Docker query in the restricted sandbox was denied. The same read-only
  container query and physical executions were rerun with the required permission and
  succeeded. No result was borrowed from the denied attempt.
- The first browser attempt failed because esbuild/Vite could not spawn a child process
  (`EPERM`) in the restricted sandbox. The exact browser evidence was rerun with process
  permission and passed.
- A first combined runner-unit invocation in the restricted temp environment produced
  43 passes and 5 `PermissionError` failures while creating test-owned temporary files.
  The exact runner-unit set was rerun with permission and passed 48/48.
- The implementer report records an initial restricted full-backend run whose unchanged
  live-loopback demo-seeder test timed out. It also records the exact test passing 3/3
  and the complete permitted run passing afterward. This gate did not relabel that
  history as a product failure and did not borrow the reported full-backend count as
  fresh independent evidence; the gate independently ran the 320-test affected set.
- An initial manifest command used Git's quoted-path output, so the displayed protected
  filename did not match the literal exclusion filter and `git hash-object` rejected
  the quoted token with `could not open` before reading it. The command was abandoned;
  the protected path was not opened, hashed, staged, or altered. The manifest was then
  recomputed with `core.quotepath=false`, the literal prefix exclusion, and the expected
  identity matched.

### Supporting implementer evidence not independently re-run in full

The implementation report records 1,343 collected backend tests (1,308 passes and 35
intentionally physical-only skips), the full pre-PR/CI, lifecycle, delivery,
governance/security, synthetic evaluation, and GoldTier example-validation matrices.
Those results support the candidate but are not substituted for this gate's fresh
runtime checks listed above.

## 6. Code and Architecture Review

The evidence closure is narrow and consistent with the owning architecture.

- `apps/backend/tests/test_provider_identity_real_mongo.py` adds physical evidence only;
  it does not create a repository, provider, state owner, router, fallback, or business
  rule.
- `scripts/run_physical_mongo_tests.py` registers the suite in the complete guarded
  inventory. Its summary exposes collection/pass/fail/error/skip counts; this gate's
  actual run had zero skips.
- `apps/frontend/vite.config.ts` adds a Node `HttpAgent({ keepAlive: true })` only when
  the guarded E2E frontend-port marker is set and supplies it to the existing proxy.
  The ordinary dev configuration retains the prior behavior, and build/runtime
  production code is unchanged.
- Installed bundled `http-proxy` source was inspected and supports the diagnosis: it
  assigns `options.agent` to the outgoing request and forces `connection: close` when
  no agent is provided. The conclusion is limited to the observed proxy connection
  lifecycle.
- Provider identity validation remains centralized in the domain/persistence boundary.
  Mapping and connector paths consume the retained plan and assert compatibility; they
  do not infer a second identity.
- No temporary Case Activity trace path, duplicate old path, compatibility shim with an
  unowned lifetime, or dormant BizFile composition was found.

No accepted technical debt was added by this bounded closure. ERQG-01 and ERQG-02 are
required current-candidate fixes, not deferred architecture work.

## 7. Security Review

No Critical, Important, or Minor security finding was identified.

- Only the named task-owned Mongo container was queried. The unrelated `safetrace`
  container was not inspected, touched, or stopped.
- The Mongo URI was derived inside each process, used only through
  `PHASE12_MONGO_URI`, and removed afterward. It was not printed, written to a report,
  or persisted.
- Physical tests require a fresh allowlisted disposable database, reject pre-existing
  ownership, constrain collection inventory, and clean up in `finally`.
- A strong-pattern secret scan was run only over the exact 151 candidate paths and
  returned `151 text paths, 0 findings`. The repository-wide secret helper was not run
  because its broad untracked traversal would have violated the protected-path
  exclusion.
- The unrelated untracked path whose displayed name begins
  `ersshaneDesktopFYP_sponsor_inputsgoldtier` was excluded from inspection, hashing,
  staging, and modification throughout.
- No new external provider call, credential path, PII logging, raw provider payload
  logging, authorization owner, or frontend authorization decision was found.

## 8. Required Fixes

1. Correct `docs/demo/PRE_PHASE22_INTELLIGENCE_DEMO.md:42-43` so the walkthrough remains
   explicitly Mock-only while accurately acknowledging the current guarded
   `SANDBOX_PARTIAL` XPI preview/read-only search capability and its non-Live,
   non-mutation boundaries.
2. Remove the extra blank EOF line from that file.
3. After those fixes, obtain a fresh exact-content independent recheck. The coordinator
   must not treat this non-exact verdict as publication authorization.

Later dependencies remain separate: Q-016 sponsor authority, GoldTier mutation/live
activation, and Phase 22 work are not fixes for this gate and remain out of scope.

## 9. Readiness

- Provider-identity physical evidence: ready and independently verified.
- Case Activity browser evidence: ready and independently verified.
- Publication workflow: **not authorized** because this report is not an exact `PASS`.
- Phase 22: remains held; this gate does not authorize starting it.
- Live ACRA/GoldTier or PingFed integration: not ready and not claimed.

## 10. Git Status and Candidate Identity

- Branch: `feature/pre-phase22-capability-expansion`
- `BASE_SHA`: `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- `HEAD_SHA`: `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- `origin/main` at freeze and recheck: `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- Staged paths: `0`
- Candidate inventory: 100 tracked modifications plus 51 task-owned untracked paths,
  for 151 paths total. The protected unrelated untracked path and this report are
  excluded.
- Manifest convention: ordinal path sort; each line is
  `path<TAB>git hash-object --no-filters`; UTF-8 lines joined with LF and a terminal LF.
- First entry:
  `.ai-pipeline/reports/GOLDTIER_XPI_SANDBOX_DIAGNOSIS.md<TAB>90435639a8598b270a90c7ca10c49c983318b9ca`
- Last entry:
  `tests/test_run_physical_mongo_tests.py<TAB>02a5318536e389c7ac94a3a94aec8b2cd52a56e9`
- Reviewed `WORKTREE_CONTENT_SHA256`:
  `3836b8a4eb7d2119dc1c33d833f0a4d61a122272dc118964bb2a9e479cbbf482`

Before report creation, the identity was re-derived and matched exactly. This reviewer
made no implementation, test, configuration, ordinary documentation, checkpoint, prior
report, Git index, ref, branch, commit, PR, merge, or external-provider-state change.
The only reviewer-created file is this assigned report. The candidate fingerprint is
rechecked after report creation below, excluding this report as required.

## 11. Command and Inspection Record

The capability preflight found Python 3.12.10, Node v22.23.2, npm 10.9.8, and Docker
client/server 29.8.0. The named task container was healthy on a random loopback port.

Required context selection ran successfully for all applicable classes:

- `python scripts/dev_context.py --change-class PERSISTENCE`
- `python scripts/dev_context.py --change-class EXTERNAL_PROVIDER`
- `python scripts/dev_context.py --change-class FRONTEND_UI`
- `python scripts/dev_context.py --change-class CI_TOOLING`

The emitted Tier-1 authorities, triggered repository skills, architecture/contracts,
decisions/open questions, owning source/tests, implementation report, prior
provider-identity gate, current checkpoint/evidence, and planner/intent were read.
`git diff`, `rg`, and targeted file reads covered all candidate paths and the relevant
owner/retirement paths. No protected-path content was read.

Candidate validation commands and results were:

- Identity/status derivation: branch/base/head/origin matched; 151 candidate paths;
  zero staged; expected first/last entries and SHA-256 matched both pre-review and
  pre-report.
- `git diff --check HEAD`: no whitespace error; only Windows LF-to-CRLF informational
  warnings.
- Per-task-owned-untracked-path `git -c core.autocrlf=false diff --no-index --check --
  NUL <path>`: exactly one finding, ERQG-02.
- Candidate-limited strong-pattern secret scan: 151 text paths, zero findings.
- All runtime/static commands and exact outcomes are recorded in Section 5.

No command staged, committed, pushed, merged, switched branches, modified external
provider state, or stopped a container.

## 12. Final Verdict

PASS WITH MINOR FIXES
