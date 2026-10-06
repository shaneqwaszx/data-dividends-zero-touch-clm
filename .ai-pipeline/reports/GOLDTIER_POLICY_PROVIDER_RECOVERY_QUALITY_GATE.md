# Provider-verified Policy recovery independent quality gate

## Current verdict — remediation round 1

**PASS — P0/P1/P2 = 0/0/0.** The initial manual CLM compatibility regression is
closed. The current complete backend run passes, and the independent reviewer
reproduced normal Shell success -> uncertain Policy -> Requested provider proof ->
zero-replay recovery -> exact-prefix continuation, including durable restart.
No required fix remains for this bounded owner assignment.

The reviewer was not an implementation/remediation writer and wrote only this report.
No source/test/configuration/other-document fix or Git mutation occurred during this
gate. The initial FAIL and its reproduction remain below as superseded history.

## Reviewed identity and boundary

Owner assignment: 2026-10-06 provider-verified Policy recovery remediation, sections
A-N, preserving existing recovery and the API while adding the normal-Shell shape.
Worktree:
`C:/Users/shane/.codex-clean2/worktrees/goldtier-policy-provider-recovery/data-dividends-zero-touch-clm`.
Branch `fix/goldtier-policy-provider-recovery`; base, precommit HEAD and inspected
origin/main are `529efea3966fb561027973e6d932cecb0e8f6bb8`. No files were staged.
The task changes were uncommitted throughout review.

Fourteen reviewed paths were independently hashed before and after execution.
Frozen identity remained
`6aaf1b469219847820b968c39b74f15b9a01db076727929dd135e3c15845f9e7`.
Algorithm: sort changed tracked and task-owned untracked paths; concatenate each UTF-8
path, NUL, its UTF-8 content normalized CRLF to LF, NUL; SHA-256. This report is excluded.

Reviewed paths:

- `.ai-pipeline/001_planner/GOLDTIER_POLICY_PROVIDER_RECOVERY_PLAN.md`
- `.ai-pipeline/reports/GOLDTIER_POLICY_PROVIDER_RECOVERY_IMPLEMENTATION.md`
- `apps/backend/app/connectors/errors.py`
- `apps/backend/app/connectors/goldtier_xpi.py`
- `apps/backend/app/main.py`
- `apps/backend/app/services/onboarding.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/tests/test_policy_provider_recovery.py`
- `apps/backend/tests/test_policy_recovery_real_mongo.py`
- `docs/ARCHITECTURE.md`
- `docs/PROJECT_STATE.md`
- `docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md`
- `docs/integration/GOLDTIER_POLICY_PROVIDER_RECOVERY.md`
- `scripts/run_physical_mongo_tests.py`

## Acceptance and independently reproduced behavior

| Assignment requirement | Independent result and evidence |
|---|---|
| A-C / J1-4: both predecessor shapes and truthful ledger recovery | PASS. Historical definitive SEARCH + recovered SHELL and new definitive SEARCH/SHELL both accept only the exact unresolved POLICY prefix. Attempted operations remain SEARCH/SHELL/POLICY; lifecycle resolution includes all three; normal definitive completion remains SEARCH/SHELL. Separate POLICY recovery retains original uncertainty, no replay and Requested. |
| D / J18-19: original Shell fact and chronology | PASS. Normal case and ledger preserve SHELL_CREATED and no fabricated Shell recovery; historical Shell recovery remains intact. Policy ID stays unknown. Shell and Policy transport totals remain one each in API/manual/physical continuation. |
| A / J5-12: identity, status, frozen input, invalid and terminal prefixes | PASS. Conflicting ID/name/UEN/country/Policy, Active/unsupported status, unattempted/resolved Policy, later Amend/readback and terminal outcome/receipt reject without calls. Source binds current canonical identity, current case policy/catalogue and exact retained submission. Two additional valid current-policy/catalogue drift probes reject without ledger change or dispatch. |
| E / J15-17: automation reconciliation, one intent and existing confirmation | PASS. Matching target-stage CLM_TARGET_OUTCOME_UNCERTAIN reconciles through existing RESUMING -> RECOVERY_PENDING with historical failure retained. Recovery itself makes zero calls. Explicit resume completes with one original submission and identical input/confirmation. Unrelated failure cannot be cleared. |
| E / adverse local checkpoint interruption | PASS. Injected failure at each automation save yields controlled 409 after retained proof; identical retry completes local checkpoints without duplicate proof or calls. |
| F / J20: frozen downstream plan | PASS. No-Amend normal path dispatches only exact-ID readback. Required-enrichment paths dispatch Amend once then readback. No Shell/Policy replay and no repeated Final Review & Send. |
| Existing manual CLM compatibility | PASS. Genuine manual cases with no automation cover both predecessor forms through the API, repeated local recovery, original explicit CLM continuation and unchanged intent/confirmation. No automation is synthesized. |
| G / authorization and UI boundary | PASS. Existing bounded API remains the interface; no browser form is claimed. Director capability remains required, RM denial is 403, HR inaccessible case remains 404, and service callback reauthorization is inside the case lock. |
| H-I / J21: safe diagnostics and timeout | PASS. Six bounded reasons use fixed existing event codes/text; private sentinel is absent. Blocked advancement retains ledger/no-call semantics. Ten-second default is unchanged. Original Delta cause remains unknown. |
| K / protected case and provider boundary | PASS. Only synthetic memory/fake transport and generated task-owned Mongo data used. No dotenv, shared UAT, clm_poc, browser, ACRA or GoldTier access. |
| J13-14 / L: physical persistence | PASS. Independently executed application reconstruction and separate actual Mongo server restart both preserve recovered prefix and same-intent continuation; raw reads/startup/idempotent recovery do not rewrite. Generated database cleanup verified. |
| L-M: checks and independent review | PASS. Full current backend and required affected checks completed; this verdict applies only to the frozen identity above. |

## Independently executed checks

Primary repository virtualenv Python, APP_ENV=test, PYTHONDONTWRITEBYTECODE=1,
PYTHONPATH set to the reviewed worktree/backend. Ordinary tests enforce memory/fake
providers and disable dotenv. Pytest used unique task-owned TEMP basetemp paths;
Ruff used --no-cache; mypy cache was outside the frozen worktree. No installs.

| Check | Current independent result |
|---|---|
| Full `apps/backend/tests` pytest | 2,506 passed, 131 skipped, 4 warnings; 2,637 total; zero failures/errors |
| Recovery/XPI/retained-recovery plus hostile isolation/physical runner suites | 178 passed, 1 known TestClient warning |
| New physical Mongo recovery/restart suite | 1 passed, 1 known TestClient warning |
| Additional actual Mongo server-restart probe | PASS; exact owned container ID checked, recovered prefix/raw document preserved, same-intent completion, cleanup verified |
| Additional current-policy/catalogue drift probes | 2 passed; rejection without ledger change or provider calls |
| Secret scanner/architecture/project-state adverse unit suites | 45 passed |
| Contract unittest suite | 44 passed |
| Ruff application/backend tests/changed runner | PASS |
| Strict mypy application | PASS, 126 source files |
| Secret scan, architecture and project-state scripts | PASS |
| Tracked diff whitespace and every new Markdown file | PASS |
| Frontend tests/browser E2E/TypeScript/build | Not required/not run: no frontend surface change |
| Pre-PR/publication gate | Not run: local commit only is authorized; no PR readiness claim |

Full command: `python -m pytest apps/backend/tests -o addopts='' -q -p no:cacheprovider
--tb=short --basetemp <unique task-owned TEMP path>`. Focused command selects
`test_policy_provider_recovery.py`, `test_goldtier_xpi_sandbox.py`,
`test_s3_retained_recovery.py`, `tests/test_contract_test_isolation.py` and
`tests/test_run_physical_mongo_tests.py` with the same isolation flags. The 33 current
new recovery cases are included in focused and full execution. Root checker tests
select `test_check_secrets.py`, `test_check_architecture.py` and
`test_check_project_state.py`. Contracts use unittest discovery in `tests/contract`.

The full ordinary run deliberately leaves opt-in physical Mongo suites unconfigured;
local Tesseract availability also gates unrelated OCR cases. These skips are not passes
or borrowed physical evidence. The affected new physical test was independently run
with the task-owned server configured. Four broad warnings comprise the known
Starlette TestClient deprecation and three serializer warnings from existing hostile
provider-conformance tests that deliberately bypass model validation. No warning
required a current-scope fix.

## Physical evidence distinction

The authored physical test closes/reconstructs normal persistence/application runtimes,
reads the raw snapshot repeatedly and reopens again after completion. This proves
application restart with Mongo, separate recovery facts, no read-time rewrite and
original confirmation/input retention against the real driver/server.

A separate reviewer probe additionally verified the exact task-owned container
`clm-policy-recovery-20261006` ID, retained a new generated allowlisted case, closed
its runtime, restarted that Mongo process, and reconstructed normal composition.
Recovered ledger and RECOVERY_PENDING were intact before any provider call. Startup
and identical recovery preserved the raw snapshot; explicit resume then completed
with the same frozen input/confirmation. Shell/Policy each had one fake transport
call total, no Amend was required, and only downstream readback followed recovery.
The existing fixture cleaned only its generated database and verified its absence.
No URI or secret was printed, persisted or placed in this report.

## Contract, architecture and security assessment

Current owner assignment explicitly extends the prior Garden-only recovery authority
to the normal-Shell shape; it does not approve Active, automatic provider verification,
external replay or real UAT mutation. Requested proves provider request existence,
not KYC completion, regulatory approval or Live interoperability. Existing XPI
contract/mapping/TLS/auth/write opt-in and provider classifications remain unchanged.

The route delegates to existing ZeroTouchOrchestrator, which retains locked session,
capability and team/case reauthorization and calls the existing case/ledger owner.
Automation lookup is optional for existing manual CLM cases; the frozen CLM snapshot
remains required. No second workflow, ledger, persistence owner, route-to-Mongo access,
schema/version/migration or Policy ID is introduced. The two legal automation saves
are monotonic local checkpoints with tested idempotent repair; they do not dispatch.

Safe uncertainty classification retains only a controlled enum-derived code and fixed
text through existing WorkflowEvent persistence. Connector private context, payloads,
headers and credentials do not enter the new evidence. Identity/policy mismatches and
unrelated failure stay fail-closed. Existing broader authorization, CAS, deletion,
provider conformance, lifecycle/order/call-stopping and terminal-state regression
suites completed in the full backend run. No catalogue change or new Live claim.

Current required findings: none. P0 = 0, P1 = 0, P2 = 0. Later sponsor/production,
real-case authority, browser evidence-form and multi-instance exactly-once claims
remain outside this bounded implementation; no new guarantee is asserted.

## Historical initial gate — superseded FAIL

The initial frozen identity was
`89bfe6a0350548a875b5db024cf4f33436ba89558838315779810029ad3d4734`.
That independent gate returned FAIL with P0/P1/P2 = 0/0/1 and stopped its broad run
at approximately 60% after reproducing the required compatibility regression.
It was not a completed full-suite PASS. The reproduction below refers only to that
initial source; its unconditional automation lookup has now been removed.

### Initial required finding and reproduction

**P2 — Policy recovery now requires automation and rejects existing manual CLM cases.**
`apps/backend/app/main.py:2511` replaces the existing direct Policy recovery delegate
with `ZeroTouchOrchestrator.record_provider_policy_recovery`. Its unconditional
`_require_record(case_id)` at `apps/backend/app/services/zero_touch_orchestration.py:711`
raises `ZERO_TOUCH_CASE_NOT_FOUND` before validating or retaining provider evidence if
the case has no automation record.

Manual CLM creation, target confirmation and submission remain supported through
`/api/clm/cases` and the existing CLM owner. They create a CLM snapshot and the same
incremental target ledger without an automation record. Before this change, the
target-recovery route required the frozen CLM snapshot and locked TARGET_RECOVERY
authorization; it did not require automation. Its zero-touch URL does not establish
an automation-only precondition. Neither the assignment nor the current recovery
authority retires manual CLM recovery.

Independent reproduction used existing `make_ready_case` and synthetic XPI transport,
ordinary test isolation, supported manual CLM confirmation/submit, and an empty
automation repository. The transport supplied successful bounded early Search,
uncertain Shell, exact-ID Shell verification, then uncertain Policy. This produced
the previously supported historical prefix:

- attempted SEARCH/SHELL/POLICY;
- definitive SEARCH;
- lifecycle-resolved SEARCH/SHELL;
- retained provider-recovered Shell;
- frozen CLM submission and no automation record.

Calling the new route owner with matching Requested Policy proof rejected it with
`ZERO_TOUCH_CASE_NOT_FOUND`. Calling the route's previous OnboardingService delegate
with identical proof accepted POLICY recovery, resolved all three operations and made
zero additional transport calls. A separately created normal definitive-Shell manual
case reproduced the same rejected precondition. No fixture or source file was edited
for these probes; the fake connector received only the helper's synthetic `_match_found`
attribute required by the existing manual readiness helper.

Remediation: retain the existing Policy recovery capability for CLM cases without
automation, while allowing the existing ZeroTouch owner to reconcile automation when
one exists. Do not synthesize automation or bypass locked TARGET_RECOVERY authorization.
Add a manual CLM API regression for the historical and normal predecessor forms,
idempotent recovery, zero provider calls, and unchanged intent/confirmation. Existing
zero-touch recovery and unrelated-failure rejection must remain covered.


### Round 1 closure

The current method uses an optional automation repository lookup inside the same
case lock, still requires the frozen CLM snapshot, and delegates to OnboardingService.
When automation is absent it returns retained recovery without creating automation.
When present it reconciles only matching target uncertainty. Both genuine manual API
prefix tests, idempotent retries and original CLM continuation independently pass;
zero-touch reconciliation, unrelated-failure rejection and fault retry remain passing.
The initial P2 is closed on the current frozen identity, not waived as technical debt.

## Next authorized action

The owner-authorized local commit may proceed only with the fourteen reviewed paths
unchanged and this assigned gate report included. No commit was performed by the
reviewer. No push, PR, merge, next phase, real UAT read/write or external provider
operation is authorized by this PASS. Stop for owner review after the local commit.

External ACRA calls = 0; external GoldTier calls = 0; shared UAT reads/writes = 0.
