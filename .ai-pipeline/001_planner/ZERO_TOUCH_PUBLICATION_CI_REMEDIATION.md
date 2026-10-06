# Publication CI remediation — bounded round 1

Owner authority: publication/CI-closure attachment dated2026-10-06.
Branch:fix/zero-touch-registry-reuse-happy-path.
Initial publication HEAD:c45c106792aa36dc5ae7bf1fd7530432808a9da1.
Original BASE:771a9696e1e31e3865da4fbbb3f9b33b5959cb6a.
Current integrated main:1fc097f12c84af52b1e6d70a336cc22b03f3bef4.
PR75 is open; initial push37387899924 and PR37387964897 test the same feature SHA.

First causal failure: both e2e jobs fail isolated selection8/65, Singapore clean fixture,
at authenticated-zero-touch.e2e.ts:1069 expecting an absent-binding message. Current
accepted registry acquisition records a PROVIDER_FETCH case binding, which the existing
RegistryProvenancePanel displays from the backend projection. The old absent-binding
assertion is a deterministic test mismatch, independently reproduced locally exit1/25.02s.
No transient rerun is justified; no timeout/assertion weakening or product change.

Write scope: only the owning browser assertion/import plus this compact planner and
task-owned implementation/freeze/independent gate evidence. Preserve all current product,
schema10, cache, classification, Decimal, ledger, auth, provider, CI/dependency owners.
The new test must verify a non-null exact backend-authored binding, PROVIDER_FETCH,
each safe receipt field in the UI, truthful provisional disclaimer, and absence of the
unknown-binding banner. Keep all existing completion/no-extra-request/storage assertions.

Change class:CI_TOOLING (test-only). Architecture review not required: no owner/dependency/
business contract changes. Current runtimes:Python3.12.10,Node22.23.3,Docker29.8.1,existing
task Playwright/dependencies and localTesseract. Source edits/evidence/runtime use the
assigned worktree with scoped escalation; no owner dotenv or protected database read.

Verification: narrow original failing selector RED->GREEN at unchanged60-second harness
deadline; owning file selections and complete current guarded65-lifecycle suite, using
isolated memory/Mock and a new task-owned disposable Mongo only where harness requires it.
Run proportional harness/governance/security/whitespace/type checks, inspect complete
delta, freeze exact content, obtain fresh independentPASS0/0/0. Then create a normal new
remediation commit, pre-PR-check on clean committed state, normal push, update samePR75,
and observe all push+PR CI on new reviewed HEAD. Maximum2 CI remediation rounds.

Current isolation:explicit allowlisted subprocess environment; no owner.env,clm_poc,
protected ownerDB,externalACRA/GoldTier,production/PingFed/provider-family/policy change.
Historical protected non-access remainsNOT_CERTIFIED/owner-accepted; do not investigate.
No PR merge,auto-merge,branch/worktree deletion,nextphase. Stop only at fullygreen open
non-draft mergeable/clean PR with latestHEAD reviewed; owner manually merges.


Second causal owner discovered before any R1 commit: both initial backend jobs
112025743146/112025954844 fail Government classification/no-share-graph test because a
Windows Tesseract executable literal is relative on POSIX. Both report1FAIL/2466PASS/
134SKIP. The backend lane lacks host OCR; actual scanned OCR remains separately owned.

Extend this same uncommitted R1 to only the Government test's fixture/imports: existing
native TXT fixture form of exact approved Government identity/classification fields and default
LocalPdfTextIdpProvider, with OCR.recognize explicitly forbidden. Preserve unconditional
classification/no-graph/no-target-mutation assertions; do not skip test or relax adapter
path validation. All actual scan fixtures/generator/real OCR tests remain byte-identical.
Full65 must preserve real Government scan browser coverage. Exact Government selector,
full owning continuation suite, Ruff and proportional backend tests after current browser
suite ends. No CI/dependency/product change. Renew freeze/review to include this third path.

Local full65 preflight exposed lifecycle53 stale-policy test's removed rebind button
label and closed policy receipt disclosure. First52 passed; exact unchanged selector
reproduced timeout66.47s. Extend same uncommitted R1 only to current owning UI button
locator and explicit disclosure opening in slice-c-recovery.e2e.ts. Preserve selected
values, policy revision, target ordering/currentness and completion assertions. Backend
rebind retains frozen business/classifier policy and changes accepted target constants
only. No timeout, retries, skip, product or policy change. Require exact selector GREEN
and complete65 PASS, then freeze all four paths for fresh independent review.

Rejected first fixture adaptation: synthetic native PDF extracted CRLF lines, while
existing classification label parser accepts LF fixture lines; identity accepted but
classification observations zero (41PASS/1FAIL). Do not broaden publication into a PDF
parser change. Reuse existing supported native TXT labelled fixture form already used
by classification tests, identical Government fields and explicit media type. Retain
OCR-forbidden guard, all classification/no-graph assertions and separate real scan
coverage. This diagnostic is failed evidence, not a passing gate or another CI round.

Lifecycle55 revealed a real continuation bug: after resolving the last classification
exception with retained failed Search, the owning orchestrator saved RESUMING and
returned before its existing readiness/failure transition. Full preflight54PASS then
55FAIL; exact offline XPI API regression reproduces persisted RESUMING instead of
D-060/D-061-required TECHNICAL_FAILURE. Do not weaken the browser assertion.

Change Necessity: existing owner must resume its current readiness transition; no
configuration/test-only change can make a stuck executing case truthful. Decision:
code-change, minimum boundary bind_target_classification's final continuation call.
PatchShape: reconnect existing owning transition; CanonicalOwner:ZeroTouchOrchestrator;
no new branch/owner/provider call. Preserve active sibling exceptions, frozen target
checks, current fingerprint, explicit finalSend, failed Search identity and no-replay.
Reuse _advance_locked just as existing policy-rebind path does.
TDD Mode:off / Route:skipped; diagnostic RED API test precedes repair regardless.
A first mock-mode test did not reach sandbox-required classification; task-added test
removed with exact frozen original-byte proof. New regression uses existing actual
offline XPI/API fixture and asserts persisted failure, retained classification/checkpoint,
zero ACRA calls and zero target mutations/ledger attempts.

Same uncommitted CI R1 expands to one existing runtime owner and its owning regression.
Change classes now CI_TOOLING + BACKEND_DOMAIN + BACKEND_API. API/type/schema/connector/
config/business-rule/mapping/auth/security/architecture/provider status unchanged;
runtime correction restores existing accepted technical-failure continuation. No sponsor
policy invention or target dispatch. Required verification: focused103 classification,
owning recovery/orchestration and adverse paths, full backend, Ruff/strict mypy, contracts/
regression/security, exact55 and complete65 browser lifecycles, then renew whole freeze
and fresh independent review. Do not publish old854664/b946 test-only freeze.

Fresh independent adverse review of dfd3/9e83: FAIL0/0/1, PUB-R1-001 P2. Existing
locked advance persists sanitized technical failure and raises ZeroTouchInfrastructureError,
but classification route lacks the existing infrastructure HTTP projection catch. Fault
probe confirms generic500, persisted safe failure, no leak/replay. Root owning regression
RED confirms500 instead of503. Extend this same uncommitted R1 only to that route's
existing _zero_touch_infrastructure_http_error catch, authored fault regression and
standard TestClient raise_server_exceptions option. Reuse trusted existing error schema,
code/message/IDs; do not invent a new error model, policy, auth or credential handling.

The five-path2478PASS/124SKIP fullbackend is successful superseded-tree evidence, not
a final-six-path claim. Renew complete freeze including main.py; fresh fullbackend,
focused104+recovery9, contracts/security, frontend checks, exact browser regressions and
complete65 required before independent finalPASS0/0/0 and any new commit/push.
API classification infrastructure status/envelope projection changes500->existing
sanitized503; runtime failed-Search continuation is restored. Route/request/shared type/
schema/connector/config/business-rule/mapping/RBAC/TLS/architecture/provider status
remain unchanged. This is safe error-boundary restoration, not security weakening.
