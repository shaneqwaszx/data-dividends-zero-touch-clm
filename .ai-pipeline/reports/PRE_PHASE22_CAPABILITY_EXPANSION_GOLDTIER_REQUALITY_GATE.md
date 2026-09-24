# Pre-Phase 22 capability expansion — GoldTier XPI remediated exact re-quality gate

## 1. Executive Result

**FAIL**

The four findings from the preserved first exact gate were independently rechecked. The
target-policy validation/case-snapshot binding, mutation-uncertainty/no-replay handling,
backend execution-profile plus principal frontend labels, and related-party percentage
range are remediated. Focused backend, frontend, contract, and direct governance checks
are green.

One current-scope provider-truthfulness blocker remains. A configured
`SANDBOX / SANDBOX_PARTIAL` case plan is still processed by CLM/zero-touch paths that
persist and return messages explicitly claiming **Mock GoldTier**. Those messages are
rendered verbatim in multiple user-visible timelines. This contradicts the candidate's
backend-authoritative Sandbox classification and the requirement that Sandbox never be
presented as Mock. See GT-RQG-01.

The exact reviewed identity is:

- branch: `feature/pre-phase22-capability-expansion`
- base / `HEAD` / locally recorded `origin/main`:
  `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- candidate paths: 137
- candidate fingerprint:
  `04c523f4b21bff76d6a0c76fb590eb55ae364a2645fb3e6d78b73a2d8c8cdcc3`
- source revision: the uncommitted 137-path candidate at the commit and fingerprint
  above
- test revision: the same fingerprint; no candidate path changed during reviewer checks
- review revision: the same fingerprint; this canonical report path is the sole reviewer
  write and is deliberately excluded by the candidate verifier
- staged paths: zero
- hygiene: PASS, zero issues

The fingerprint was independently recomputed before review, immediately before report
creation, and after report creation. All three computations returned the same 137 paths
and fingerprint. The helper excludes only this canonical report and the instructed
unexpected root artefact. That artefact was not opened, hashed, moved, deleted, or
otherwise inspected.

Q-016-dependent assignment/note/SLA mutations remain deliberately deferred and are
**not** a reason for this FAIL. Phase 22 remains on hold and is also **not** a condition
for this gate. All eight target-policy defaults remain `TBD_SPONSOR`; no customer write
occurred or is authorized. Related-party execution remains blocked on child-ID lifecycle
and relationship authority.

## 2. Phase Acceptance Checklist

| Requirement | Result | Direct evidence |
|---|---:|---|
| Exact frozen branch/content identity and task-owned hygiene | PASS | Independent verifier returned 137 paths, fingerprint `04c523f4...8cdcc3`, and `HYGIENE=PASS` before and after this report; branch/HEAD/base match the assigned identity and the index is unchanged. |
| Reconcile the supplied XPI guide/Postman structure without copying secrets or treating examples as policy | PASS | Guide SHA-256 `b4fedf629019d17a33c05d74a248fcf4973aef740c491e91dc63ce7d6c06ef55` and collection SHA-256 `e0c20335213e15cf566ea45b262e4e3f2c3cd27d326330c2e7c1b73c1a71a708` match the recorded evidence. Sanitized operation/path/query/header/body-key structure agrees with the mapping matrix; no secret or raw example value was copied. |
| Prior blocker 1: unusable non-TBD policy text and immutable case-snapshot binding | PASS | Policy values reject blank/control/unusable text; preview/pre-dispatch validation is complete before ledger/network; execution compares submitted catalogue/target policy with the owning case snapshot. Focused tests assert zero calls and `NOT_STARTED` for invalid/mismatched inputs. |
| Prior blocker 2: oversized/undecodable/ambiguous post-mutation outcomes retain uncertainty and no replay | PASS | Connector converts post-dispatch response-size/decode/ambiguous-identifier failures to mutation uncertainty; service leaves the ledger `IN_PROGRESS`; focused tests cover Shell, policy, and amend stages plus zero-call retry. |
| Prior blocker 3: configured Sandbox profile and principal frontend journey are not labelled Mock | PASS WITH BLOCKER | Execution profile, plan, banner, main journey, preview, result, and party-ID labels now derive `SANDBOX / SANDBOX_PARTIAL`. Persisted CLM/automation messages still say Mock and are rendered verbatim; see GT-RQG-01. |
| Prior blocker 4: related-party `ownerPercent` is finite and 0..100 inclusive | PASS | Semantic Decimal validation rejects below-zero, above-100, excess-scale, and nonfinite values while preserving the six-decimal contract shape. |
| Strict local six-operation DTO/mapper boundary without direct ACRA-to-XPI mapping | PASS | XPI DTOs, mapper, connector, and prepared input remain a distinct dialect boundary; canonical entity and deterministic Decimal ownership owners are preserved. |
| TLS 1.3, verified certificates, redirects disabled, bounded timeout/body/candidates, backend-only user ID | PASS | Source review confirmed TLS 1.3 min/max, default verification, `follow_redirects=False`, bounded transport/response projection, secret-wrapped backend user ID, and fixed safe errors. |
| Explicit Sandbox/write opt-in, production refusal, and no Mock fallback | PASS | Composition selects exactly Mock or Sandbox, Sandbox fails closed, production activation remains refused, and no recovery path silently switches providers. |
| Search classification and downstream call stopping | PASS | Focused source/tests cover no-match creation, exact identifier/country reuse, probable/multiple/conflicting review, and no mutation after a non-exact result. |
| Target ledger ordering, durable outcome-before-finalization, uncertain no-replay | PASS | Source and adverse tests preserve Search → Shell → Policy → Amend, stop on failure/review, retain target outcome before rich finalization, and prohibit automatic replay of uncertain mutations. |
| Policy authority remains explicit and no sponsor rule is invented | PASS | All eight defaults remain `TBD_SPONSOR`; invalid non-TBD values fail closed; catalogue/snapshot versions bind interpretation; no example-derived default or customer write was introduced. |
| Safe case-scoped preview, backend RBAC/team scope, and user/session/team-scoped cache ownership | PASS | Preview omits credentials/raw responses; case access remains backend-authoritative with inaccessible 404; affected cache keys include actor/case/filter identity and preserve cancel/remove/invalidation behavior. |
| Additive persistence compatibility and no silent historical rewrite | PASS WITH FRESH-EVIDENCE LIMITATION | Schema-v5 fields are additive/optional and legacy readers, strict identity/CAS, insert/update, deletion, and memory/Mongo owner boundaries are preserved in source/tests. Fresh physical Mongo was unavailable because the Docker daemon pipe is absent. |
| Provider classification is truthful: `PARTIAL / SANDBOX_PARTIAL`, never Live and never Mock when Sandbox runs | FAIL | Registry/docs/profile and principal labels are correct, but CLM and automation messages persist/return Mock wording under the same Sandbox plan and the UI renders `event.message`; see GT-RQG-01. No Live claim was found. |
| Secret, credential, raw provider response, PII, and safe-error containment | PASS | No raw response/body logging or credential projection was found; no `.env`, portal password, bearer token, private key, or provider secret was inspected. |
| Q-016 mutation omission is truthful | PASS | Assignment, note, due-time, and SLA mutations remain absent/deferred; no capability, role, CAS, or audit authority was invented. |
| Related-party external execution remains blocked | PASS | Local DTO transformation exists, but network dispatch remains blocked pending child-ID lifecycle and relationship authority. |
| Phase 22 remains untouched/on hold | PASS | No Phase 22 implementation or activation was found or performed. |
| Candidate is suitable for publication | FAIL | GT-RQG-01 requires narrow remediation, a new frozen fingerprint, and a fresh independent exact gate. |

## 3. Contract and Integration Findings

### GT-RQG-01 — HIGH — Sandbox execution still emits persisted and user-visible “Mock GoldTier” claims

**Authority:** current source, current composition, the accepted provider-mode truth
invariant, and the explicit instruction to review truthful provider claims.

The remediation correctly makes the backend execution profile and submission plan
authoritative for Sandbox:

- `apps/backend/app/demo/scenarios.py:30-44`
- `apps/backend/app/main.py:487-496`
- `apps/backend/tests/test_goldtier_xpi_sandbox.py:219-220`
- `apps/backend/tests/test_goldtier_xpi_sandbox.py:280-283`

The CLM owner nevertheless emits provider-specific Mock wording independently of that
plan. Examples include readiness, uncertain outcome, start, finalization, success,
failure, and review messages:

- `apps/backend/app/services/clm_orchestration.py:218-220`
- `apps/backend/app/services/clm_orchestration.py:239-240`
- `apps/backend/app/services/clm_orchestration.py:268-269`
- `apps/backend/app/services/clm_orchestration.py:285-286`
- `apps/backend/app/services/clm_orchestration.py:293-294`
- `apps/backend/app/services/clm_orchestration.py:302`
- `apps/backend/app/services/clm_orchestration.py:317`
- `apps/backend/app/services/clm_orchestration.py:331`
- `apps/backend/app/services/clm_orchestration.py:372`
- `apps/backend/app/services/clm_orchestration.py:392`
- `apps/backend/app/services/clm_orchestration.py:430`
- `apps/backend/app/services/clm_orchestration.py:848`
- `apps/backend/app/services/clm_orchestration.py:856`
- `apps/backend/app/services/clm_orchestration.py:875`

The zero-touch owner likewise persists Sandbox-capable activity as Mock, including
start, technical failure, completion, and existing-party review:

- `apps/backend/app/services/zero_touch_orchestration.py:1286`
- `apps/backend/app/services/zero_touch_orchestration.py:1316`
- `apps/backend/app/services/zero_touch_orchestration.py:1328`
- `apps/backend/app/services/zero_touch_orchestration.py:1336`
- `apps/backend/app/services/zero_touch_orchestration.py:1355`
- `apps/backend/app/services/zero_touch_orchestration.py:1630`

These are not internal enum names only. The frontend renders server-authored
`event.message` verbatim in the main journey, sponsor/client views, and case timeline:

- `apps/frontend/src/App.tsx:891`
- `apps/frontend/src/App.tsx:1649`
- `apps/frontend/src/App.tsx:1736`
- `apps/frontend/src/pages/CaseDetail.tsx:567`

Consequently one screen can truthfully label the configured target “GoldTier Sandbox”
while its backend-authored timeline says “Automatic Mock GoldTier submission started”
or “Mock GoldTier submission completed automatically.” The same false label appears in
safe API errors and retained audit/activity evidence. A Sandbox request can therefore be
mistaken for a no-network Mock action. This violates truthful user-visible status and is
a current blocker even though all current target-policy defaults prevent a customer
write today.

The existing affected frontend checks verify profile/plan-derived labels but do not
exercise the server-authored Sandbox timeline/error messages. The focused suite's green
result therefore does not falsify this finding.

**Required correction:** derive persisted/public target messages from the same
backend-authoritative provider mode/plan, or use provider-neutral “GoldTier target”
wording where historical enum/status compatibility must remain. Add Sandbox and Mock
tests for readiness, start, completion, review/failure, uncertain/no-replay, and
zero-touch timeline projections. Preserve durable legacy enum/status compatibility; do
not migrate historical records or invent a second provider-status owner.

### Prior exact-gate blocker closure

- **Policy/pre-dispatch/binding:** closed. `normalize_safe_policy_text` and policy
  validators reject unusable values; mapper/service pre-dispatch validation occurs
  before ledger/network; catalogue/target-policy equality is checked against the owning
  case snapshot.
- **Post-mutation uncertainty:** closed. Oversized, undecodable, timeout/transport, and
  ambiguous mutation outcomes retain uncertainty/`IN_PROGRESS` and do not replay.
- **Profile/main UI Sandbox truth:** closed for the specifically remediated profile and
  principal labels. GT-RQG-01 is an adjacent retained-message gap, not a reopening of
  the old profile type defect.
- **Related-party percentage:** closed. The inclusive semantic bound is enforced in
  addition to scale/shape.

### Contract authority and deferred dependencies

- Corrected standalone XPI operation structure remains the machine-shape authority.
  The sponsor-directed mandatory-field overlay remains provisional authority for its
  delegated question. Examples remain validating reference only; contradictory examples
  remain quarantined.
- All eight target-policy values remain `TBD_SPONSOR`; no customer mutation was run or
  authorized. GoldTier XPI remains `PARTIAL / SANDBOX_PARTIAL`, never Live.
- Related-party execution is blocked on child-ID lifecycle/relationship authority.
- Q-016 remains open/deferred. Phase 22 remains on hold. Neither is a current blocker
  and neither may be folded into the remediation.

## 4. Tester and Adversarial Findings

### Fresh independent checks rerun on the frozen fingerprint

| Check | Result |
|---|---|
| Candidate verifier before review and immediately before report | PASS twice: 137 paths, fingerprint `04c523f4...8cdcc3`, zero hygiene issues. |
| `python -m pytest -p no:cacheprovider tests/test_goldtier_xpi_sandbox.py -q` from `apps/backend` | PASS: 54 tests; one known Starlette/httpx deprecation warning. |
| `npm.cmd test -- --run src/App.test.tsx src/GoldTierRequestPreview.test.tsx src/pages/CaseStateExplanationPanel.test.tsx` | PASS: 3 files / 66 tests. The first sandboxed attempt was blocked by local child-process `EPERM`; the authorized rerun allowing the local esbuild helper passed. Existing React Router server-render warnings remain non-failing. |
| `python -m unittest discover -s tests/contract -v` | PASS: 44 tests; one known Starlette/httpx deprecation warning. |
| `scripts/check_architecture.py` | PASS. |
| `scripts/check_project_state.py` | PASS. |
| `scripts/check_policy_authority.py` | PASS. |
| `scripts/check_external_provider_readiness.py` | PASS. |
| `docker info --format "{{.ServerVersion}}"` | UNAVAILABLE: Docker Desktop Linux daemon pipe does not exist; no fresh physical Mongo evidence. |
| Candidate verifier after report creation | PASS: 137 paths, same fingerprint, zero hygiene issues. |

One deliberately over-broad contract discovery command used `-t .` and failed to import
the two suites that rely on the contract directory's configured helper import. The
correct owned command above then ran all 44 tests successfully. This is reviewer command
failure history, not a candidate defect, and it is not used as pass evidence.

Source/adverse-path review additionally traced invalid/mismatched policy input through
pre-dispatch stopping, response-size/decode/identifier uncertainty through the connector
and ledger, repeated submission through the no-replay path, exact/multiple/conflicting
Search through call stopping, strict percentage boundaries, and Sandbox plan/message
projection. No external provider call or database mutation occurred.

### Inherited broad evidence, not independently rerun

The implementation owner recorded the following against this same exact frozen
candidate. It is retained as revision-matched supporting evidence and is not relabelled
as a reviewer rerun:

- backend: 1,244 passed / 29 environment-skipped; Ruff and strict Mypy pass;
- frontend: 22 files / 280 tests; typecheck and 114-module production build pass;
- contract 44, scoped governance/security/tooling 239, and Windows lifecycle 23 pass;
- final Playwright 14/14 after correction of a stale provider-wording assertion;
- direct governance/security, dependency, secret, and hygiene checks pass;
- synthetic evaluations: entity 17/17, UBO 3/3, mock risk 5/5;
- GoldTier examples: 19 valid, 19 invalid/quarantined, 48 not validated.

The broad green matrix does not cover the contradictory Sandbox server-message
projection identified in GT-RQG-01. Fresh physical Mongo cannot be borrowed from an
earlier candidate/session.

## 5. Code and Architecture Review

The architecture direction remains coherent: provider-specific DTO/mapper/connector at
the boundary, one canonical entity, one deterministic Decimal UBO engine, one policy
snapshot owner, one target preparation/execution ledger, explicit Mock/Sandbox
composition, one persistence owner, backend case authorization, and authenticated
user/session/team-scoped frontend cache keys. No direct ACRA-to-GoldTier mapping, second
ownership engine, parallel ledger, route-level Mongo logic, silent provider fallback, or
production activation was found.

The XPI transport correctly bounds and sanitizes external responses and the remediation
preserves uncertain mutation outcomes instead of manufacturing terminal certainty. The
schema-v5 persistence change is additive and retains legacy reads and strict identity/CAS
semantics. Q-016 mutation owners were not invented.

GT-RQG-01 is a projection defect inside existing owners, not justification for an
architecture change. The narrow correction should centralize provider-neutral or
provider-mode-derived wording and preserve durable legacy enum/status values. Existing
large orchestration and `App.tsx` files remain governed technical debt; remediation must
not create another message, provider-status, ledger, or persistence owner.

## 6. Security Review

Positive controls independently confirmed in source include TLS-1.3-only HTTPS,
certificate verification, disabled redirects, bounded timeout/body/candidate counts,
safe base-URL handling, backend-only `SecretStr` user ID, explicit write opt-in,
pre-dispatch payload validation, safe fixed errors, correlation metadata, no raw
provider-body retention, authenticated preview, inaccessible-case 404, and uncertain
mutation no-replay.

GT-RQG-01 is operationally security-relevant because an operator can mistake a real
Sandbox network/mutation attempt for a Mock-only action. It does not expose credentials
or bypass RBAC, and the current all-TBD policy stops customer dispatch, but false
environment evidence cannot be accepted at an external-provider boundary.

No `.env`, token, password, user-ID value, private key, raw confidential KYC/provider
payload, or private portal content was read or written. The sponsor inputs were inspected
read-only and only hashes plus sanitized structure were retained. The reviewer made no
external call and no provider/database mutation.

## 7. Required Fixes

1. Remove provider-false Mock wording from Sandbox-capable CLM and zero-touch retained
   messages/public errors by deriving wording from the existing authoritative provider
   mode/plan or using provider-neutral GoldTier-target wording.
2. Add focused Mock/Sandbox tests over CLM readiness, submission start, uncertainty,
   success, review/failure, and zero-touch timeline/API/frontend rendering so a Sandbox
   plan cannot emit or display a Mock claim.
3. Rerun the focused affected tests and the required broad/static/contract/governance/
   lifecycle/browser matrix, freeze a new fingerprint, and obtain a fresh independent
   exact-content gate.

Do not implement Q-016 assignment/note/SLA mutations, do not enable related-party
dispatch, do not invent sponsor policy values, and do not start Phase 22 as part of this
correction.

## 8. Readiness and Residual Risks

- **Publication readiness:** NOT READY. This gate does not authorize staging, commit,
  push, PR creation, or publication CI.
- **Pre-Phase 22 candidate readiness:** NOT READY pending GT-RQG-01 remediation and a
  fresh exact independent PASS.
- **GoldTier XPI readiness:** `PARTIAL / SANDBOX_PARTIAL` only. All eight target-policy
  defaults are TBD, no customer write occurred or is authorized, related-party dispatch
  is blocked, and there is no Live or full-interoperability proof.
- **Persistence residual:** fresh physical Mongo is unavailable because the Docker
  daemon is not running. Historical physical evidence is supporting evidence only.
- **Browser residual:** the exact-candidate final 14/14 Playwright result is inherited,
  not independently rerun in this review; the focused frontend unit projection checks
  passed but miss GT-RQG-01.
- **ACRA readiness:** unchanged project truth: Mock by default, generic sandbox-shaped
  support partial, BizFile dormant, no Live ACRA proof.
- **Q-016:** open and deliberately deferred; not a gate blocker.
- **Related party:** blocked pending child-ID lifecycle and relationship authority; not
  a gate blocker and not permission to invent a flow.
- **Phase 22:** remains on hold regardless of this verdict.

## 9. Git Status

- branch: `feature/pre-phase22-capability-expansion`
- base / `HEAD` / locally recorded `origin/main`:
  `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- staged paths: 0
- frozen candidate: 137 paths
- exact reviewed fingerprint:
  `04c523f4b21bff76d6a0c76fb590eb55ae364a2645fb3e6d78b73a2d8c8cdcc3`
- final post-report verifier: 137 paths, same fingerprint, hygiene PASS
- permitted reviewer write: this report only
- implementation/source/test/configuration/governance files changed by reviewer: none
- Git index/refs changed by reviewer: none
- external provider/database state changed by reviewer: none
- commit/fetch/push/PR/merge/next-phase action: none

The preserved first failed report was read as failure history and not edited. The
unexpected root artefact was preserved and excluded exactly as instructed; it was not
opened, hashed, moved, deleted, or otherwise touched.
