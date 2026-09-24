# Pre-Phase 22 capability expansion — GoldTier XPI exact-candidate re-quality gate

## 1. Executive Result

**FAIL**

The frozen 122-path candidate is not eligible for staging, commit, push, PR creation,
or publication CI. Three current-scope safety/truthfulness defects and one strict-DTO
defect remain:

1. invalid authority-labelled target enrichment can be marked dispatch-ready and allow
   Search to reach the network before the invalid mutation payload is rejected;
2. an oversized response received after a mutation was dispatched is recorded as a
   definitive terminal failure instead of a non-replayable uncertain outcome;
3. the backend execution profile and principal frontend journey still label GoldTier as
   Mock while the configured target connector and case plan can be Sandbox;
4. the related-party `ownerPercent` DTO accepts values above 100.

This verdict is against the exact pre-write candidate identity below. The fingerprint
was recomputed immediately before this report was written and matched the supplied
freeze:

- branch: `feature/pre-phase22-capability-expansion`
- source revision / `HEAD`: `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- `origin/main`: `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- candidate paths: 122 (76 tracked modifications, 46 nonignored untracked paths,
  zero staged paths)
- candidate fingerprint:
  `afdb940366dbf54079a7c34c1afe8504ff799d93ae766b8cb8d79fa0d97feb6d`
- fingerprint basis: SHA-256 over the ordinal/case-sensitive sorted union of tracked
  modified, staged, and nonignored untracked candidate paths; every line is
  `path<TAB>git-hash-object`, LF joined with no terminal LF
- exclusions: this report path and the preserved unexpected root path whose name begins
  `ersshaneDesktopFYP_sponsor_inputsgoldtier`; the latter was not opened, hashed, or
  otherwise inspected by this review

Q-016-dependent Exception Workbench mutations are deliberately deferred and are **not**
a reason for this FAIL. Phase 22 remains on hold and is also **not** a condition for this
gate. The candidate correctly preserves those two scope boundaries.

## 2. Phase Acceptance Checklist

| Requirement | Result | Direct evidence |
|---|---:|---|
| Reconcile the supplied XPI guide and Postman collection without copying secrets or raw confidential examples | PASS | Independently verified guide SHA-256 `b4fedf629019d17a33c05d74a248fcf4973aef740c491e91dc63ce7d6c06ef55` and collection SHA-256 `e0c20335213e15cf566ea45b262e4e3f2c3cd27d326330c2e7c1b73c1a71a708`; operation/path/header/body-key structure agrees with the mapping matrix and discrepancy record. |
| Keep canonical entity/provider-neutral ownership and use a sandbox-specific adapter boundary | PASS | XPI request/response DTOs and mapper are isolated under the connector/mapper boundary; no direct ACRA-to-XPI mapping or second target execution owner was found. |
| Strict local six-operation DTO family | FAIL | The local RP transform permits `ownerPercent="100.000001"` and `"100.1"`; see GT-QG-04. |
| TLS 1.3, certificate verification, redirects off, bounded timeout/body, safe auth/user-id boundary | PASS WITH LIMITATION | `ssl.create_default_context`, TLS min/max 1.3, verified `httpx` context, redirects disabled, bounded timeout/body, backend-only `SecretStr` user id, and safe fixed errors are present. The post-dispatch response-size classification remains unsafe; see GT-QG-02. |
| Explicit write opt-in and no Mock fallback | PASS | Mutations are blocked when writes are disabled; configuration selects exactly Mock or Sandbox; Sandbox does not recover through Mock. |
| Search classification and call stopping: no match, exact one match, ambiguity/conflict | PASS | Focused tests cover NO_MATCH create, one exact identifier/country reuse, multiple/probable/conflicting review, and zero Shell for non-exact results. |
| Required enrichment fails before any network dispatch | FAIL | Whitespace/control-shaped policy text is accepted as present/valid; an actual service-path probe reached Search before rejecting the Shell DTO. See GT-QG-01. |
| Immutable case target-policy snapshot is the mutation source | FAIL | `execute_submission_input` does not compare the submitted target policy/catalogue version to the owning case snapshot. See GT-QG-01. |
| Target ledger ordering, stopping, uncertain mutation no-replay | FAIL | Timeout uncertainty is covered, but the exact oversized-response exception bypasses uncertain classification and finalizes the ledger. See GT-QG-02. |
| Policy authority values remain explicit; no example-derived sponsor policy | PASS WITH DEFECT | All eight defaults remain `TBD_SPONSOR`, and no optional customer write was executed. Runtime policy string validation is not strict enough; see GT-QG-01. |
| Composition is explicit and fails closed | PASS | Mock remains default, Sandbox is explicit, production refusal is retained, and no runtime provider fallback was found. |
| Safe case-scoped preview, backend RBAC, and existing authenticated cache owner | PASS WITH TRUTHFULNESS DEFECT | Preview excludes credentials/raw responses, uses the existing authenticated plan/cache owner, and preserves case-scoped authorization. Its presence/readiness calculation accepts invalid policy text, and the wider UI simultaneously mislabels Sandbox as Mock; see GT-QG-01 and GT-QG-03. |
| Additive schema-v5 compatibility, memory/Mongo parity, no silent historical rewrite | PASS WITH FRESH-EVIDENCE LIMITATION | Source/tests preserve optional backward reads and existing owners. Fresh physical Mongo verification was unavailable because the Docker daemon pipe was absent; historical 8-suite/29-test evidence is supporting evidence only. |
| Governance registry/checkers/docs and provider status remain Sandbox/Partial, never Live | FAIL | Registry/docs/checkers correctly classify `GOLDTIER_XPI` as `PARTIAL / SANDBOX_PARTIAL`, but the runtime execution-profile/UI contract still says GoldTier Mock under Sandbox configuration. See GT-QG-03. No Live claim was found. |
| Secret, credential, raw response, and PII containment | PASS | No credential/raw body logging was found; preview is bounded; no `.env`, portal password, bearer token, or provider secret was inspected by this reviewer. |
| Q-016 mutation omission is truthful | PASS | Assignment, note, due-time, and SLA mutations remain absent/deferred; no sponsor authority was invented. |
| Related-party external execution remains blocked pending `childId` lifecycle/relationship authority | PASS | RP network dispatch remains blocked; only local DTO transformation is present. |
| Phase 22 remains untouched/on hold | PASS | No Phase 22 implementation or activation was found or performed. |
| Exact candidate suitable for staging/one commit/push/PR/CI observation | FAIL | GT-QG-01 through GT-QG-04 require remediation and a new frozen candidate/fresh independent gate. |

## 3. Contract and Integration Findings

### GT-QG-01 — HIGH — invalid target enrichment can dispatch, and execution is not bound to the case snapshot

**Authority:** current source and direct failure injection; explicit user acceptance
requires target policy to come from the immutable case snapshot and missing/invalid
required enrichment to fail before network dispatch.

`StringPolicyValue.value` and `AuthorityLabelledTargetValue.value` enforce only length.
Whitespace and control-shaped text are therefore accepted. The target snapshot and XPI
preview classify a field as missing only when its authority or exact value is
`TBD_SPONSOR`:

- `apps/backend/app/domain/policy.py:111-115`
- `apps/backend/app/domain/policy.py:309-350`
- `apps/backend/app/mappers/goldtier_xpi.py:76-93`

The preview labels every other value `VALID`. `execute_submission_input` then checks
case/source/state/entity and provider mode, but does not compare
`submission_input.target_policy` or its catalogue version with
`case.policy_snapshot.goldtier_target` before starting the ledger:

- `apps/backend/app/services/onboarding.py:595-646`

An in-memory probe through the actual service, mapper, connector, and ledger used one
authority-labelled required value containing only spaces and a fake HTTP transport
returning a safe empty Search result. It reproduced:

```text
INVALID_ENRICHMENT_PREVIEW_READY=True
INVALID_ENRICHMENT_NETWORK_CALLS=1
INVALID_ENRICHMENT_RESULT=receipt:FAILED:FAILED
INVALID_ENRICHMENT_LEDGER_STATE=FINALIZED
```

The strict Shell DTO eventually rejected the value, but only after Search reached the
network and the ledger started. This contradicts both the pre-dispatch enrichment gate
and the claimed immutable case-bound source. The same invalid value is reachable through
the current editable string-policy model; it is not limited to raw-model corruption.

**Required correction:** reject blank/control-only and otherwise unusable target-policy
text at the policy/snapshot boundary; validate the complete operation-specific prepared
payload before any network/ledger start; compare the submitted target-policy content and
catalogue version to the owning case snapshot. Add adverse tests for whitespace/control
values and snapshot substitution, asserting zero transport calls and `NOT_STARTED`.

### GT-QG-02 — HIGH — oversized post-dispatch mutation response is falsely finalized

**Authority:** current source, architecture no-replay rule, explicit user acceptance,
and direct failure injection.

The streaming transport raises `GoldTierXpiResponseTooLargeError` after the request has
already been sent and response bytes are arriving. That error inherits ordinary
`ConnectorError`, not `MutationOutcomeUncertainError`:

- `apps/backend/app/connectors/goldtier_xpi.py:56-68`
- `apps/backend/app/connectors/goldtier_xpi.py:105-129`

The connector's mutation wrapper re-raises every `ConnectorError` unchanged and only
maps lower-level timeout/transport/unknown exceptions to mutation uncertainty:

- `apps/backend/app/connectors/goldtier_xpi.py:295-328`

The service consequently handles the oversized mutation response as terminal
infrastructure failure and finalizes the ledger:

- `apps/backend/app/services/onboarding.py:1465-1498`

An actual service-path probe returned Search NO_MATCH and then raised the exact
oversized-response exception on Shell POST. It reproduced:

```text
OVERSIZE_NETWORK_CALLS=2
OVERSIZE_RESULT=receipt:FAILED:FAILED
OVERSIZE_LEDGER_STATE=FINALIZED
OVERSIZE_UNCERTAIN=False
```

After dispatch, response truncation cannot prove that GoldTier did not accept the
mutation. A definitive failure is false success/failure classification and weakens the
no-replay owner.

**Required correction:** convert any response-size/decoding failure that occurs after a
mutation dispatch into the existing safe mutation-uncertain error and retain
`IN_PROGRESS`; retries of the same submission must make zero additional calls. Add
focused service/ledger tests for oversized post-dispatch responses at every supported
mutation stage.

### GT-QG-03 — HIGH — configured Sandbox is presented as Mock in the runtime profile and UI

**Authority:** current source and the user's explicit frontend/provider-truthfulness
acceptance criterion.

The backend profile constrains `target_environment` to literal `MOCK`, and
`execution_profile()` derives the ACRA and IDP environments but never the configured
GoldTier environment:

- `apps/backend/app/demo/scenarios.py:23-33`
- `apps/backend/app/main.py:483-500`

The frontend contract likewise permits only `MOCK`, while the visible banner, journey,
submission button, operation/result labels, and case target id are hard-coded as Mock:

- `apps/frontend/src/types.ts:133-147`
- `apps/frontend/src/App.tsx:341-347`
- `apps/frontend/src/App.tsx:764-791`
- `apps/frontend/src/App.tsx:862-901`
- `apps/frontend/src/App.tsx:1508`
- `apps/frontend/src/App.tsx:1699`
- `apps/frontend/src/pages/CaseDetail.tsx:555`

The case submission plan separately and correctly exposes `environment="SANDBOX"` and
`provider_classification="SANDBOX_PARTIAL"`. Under Sandbox composition the application
therefore exposes mutually inconsistent provider truth: the request preview says
Sandbox while the main environment/profile/journey says GoldTier Mock.

**Required correction:** make the backend profile expose the configured target
environment/classification, expand the frontend type safely, and derive visible target
labels from backend-authoritative environment/plan state. Add Mock and Sandbox rendering
tests that prevent either mode from being mislabeled. Preserve `SANDBOX_PARTIAL`; do not
introduce Live wording.

### GT-QG-04 — MEDIUM — RP `ownerPercent` accepts values above 100

**Authority:** current DTO and direct model probe; user acceptance requires strict local
related-party transformation.

`XpiOwnerPercent` uses this shape:

```text
^(?:0|[1-9][0-9]?|100)(?:\.[0-9]{1,6})?$
```

Because the decimal suffix is also allowed after `100`, the strict DTO accepts
`100.000001` and `100.1`. A direct model probe produced:

```text
100=ACCEPTED
100.000000=ACCEPTED
100.000001=ACCEPTED
100.1=ACCEPTED
101=REJECTED
```

The defect is currently contained by the separate `childId`/relationship-authority
dispatch blocker, but the implemented DTO is nevertheless not a strict ownership
percentage boundary.

**Required correction:** enforce a finite decimal in the inclusive range 0 through 100
with the intended scale, using semantic Decimal validation rather than this regex alone;
add lower/upper/scale/nonfinite adverse cases.

### Contract authority and quarantines

- The corrected standalone XPI guide/collection structure is the machine/request-shape
  authority used by the candidate. Collection examples were not treated as policy or
  provider-success proof.
- Four inherited bounded read-only Sandbox searches returned HTTP 200 with empty arrays:
  legal name 1589 ms; legal name plus SG 509 ms; group company name 487 ms; impossible
  GoldTier ID 381 ms. No blank/omitted query, undocumented registration-number query,
  write, portal-password handling, or Live claim occurred.
- All eight target policy values remain `TBD_SPONSOR`; the optional one-customer write
  was correctly not run. RP write remains blocked on the `childId` lifecycle and
  relationship authority.
- GoldTier example validation remains `19 VALID`, `19 INVALID_QUARANTINED`, and
  `48 NOT_VALIDATED`. Quarantined examples were not used to invent DTO or mapping truth.
- Current provider classification is `PARTIAL / SANDBOX_PARTIAL`; neither these reads nor
  local green tests prove full Sandbox interoperability or Live readiness.

## 4. Tester and Adversarial Findings

### Fresh independent checks

| Check | Result |
|---|---|
| Context selector for `BACKEND_DOMAIN`, `BACKEND_API`, `EXTERNAL_PROVIDER`, `AUTH_RBAC_SECURITY`, `FRONTEND_UI`, `FRONTEND_STATE_CACHE`, and `PERSISTENCE` | PASS; branch/base identity matched and required Tier 1 owners were reviewed. |
| `python -m pytest -p no:cacheprovider tests/test_goldtier_xpi_sandbox.py -q` from `apps/backend` | PASS: 29 tests; one known Starlette/httpx deprecation warning. |
| Invalid target-enrichment service-path injection | FAIL as expected: preview dispatch-ready, one Search call, terminal failed receipt, finalized ledger. |
| Oversized mutation-response service-path injection | FAIL as expected: Search plus Shell calls, terminal failed receipt, finalized ledger, uncertainty false. |
| RP percentage DTO boundary probe | FAIL as expected: `100.000001` and `100.1` accepted. |
| Sponsor artefact hashes and sanitized operation/header/query/body-key structure | PASS; no secret/raw example values copied. |
| Exact candidate fingerprint immediately before report write | PASS: 122 paths, frozen fingerprint matched. |

The focused 29-test suite passes because it covers TBD missing enrichment and timeout
uncertainty, but it does not cover unusable non-TBD enrichment, target-snapshot
substitution, oversized post-dispatch mutation responses, the >100 percentage boundary,
or truthful Sandbox profile/UI rendering.

### Inherited frozen-candidate evidence

The implementation owner reported the following on this exact frozen candidate. It was
reviewed as evidence but not relabelled as independently rerun:

- backend: 1219 passed, 29 skipped, four expected malformed-fixture warnings;
- Ruff PASS; strict Mypy PASS over 105 files;
- frontend Vitest: 22 files / 278 tests PASS; typecheck, production build (114 modules),
  and npm tree PASS;
- Windows lifecycle: 23 PASS;
- contract suite: 44 PASS;
- scoped governance/tooling/security: 239 PASS;
- synthetic evaluation: entity 17/17, UBO 3/3, risk 5/5;
- `pip check`, project-state, architecture, policy-authority,
  external-provider-readiness, tooling, `git diff --check`, candidate hygiene, and
  candidate secret scan: PASS.

Browser history is retained accurately. The first full attempt failed the Case Activity
focus assertion at test 7/14 after 15 seconds; the exact isolated retry passed and the
same port pair passed 5/5. The second full attempt failed a portfolio-filter response
wait at test 5/14 after 120 seconds; its exact port pair passed 5/5. The final unchanged
full suite passed 14/14. No source workaround was made. The bounded classification is
transient divergent browser/process scheduling; root cause remains unknown, no stable
reproduction exists, and the evidence supports no change rather than a speculative fix.

One unscoped root `unittest` discovery invocation was invalid and produced two import
failures because it crossed separately configured discovery roots. The exact contract
suite passed 44 and the scoped governance suite passed 239; the invalid invocation is
failure history, not a product failure and not omitted.

Fresh physical Mongo verification was not possible: the Docker client was present but
the Docker Desktop Linux daemon pipe was absent. Earlier same-lineage 8-suite/29-test
physical evidence remains historical support only. This limitation would have been a
residual publication risk even without the current defects.

## 5. Code and Architecture Review

The core direction is sound: one connector port, explicit Mock/Sandbox composition, one
canonical Decimal ownership engine, one entity-resolution owner, one target ledger, one
case-envelope persistence owner, and one authenticated frontend cache owner. The XPI
DTO/transport/mapper split avoids polluting the canonical entity with institution fields.
No direct provider calls from routes/UI, provider fallback, second policy owner, second
ledger, or direct Mongo route logic was found.

Current blocking architecture defects are boundary-invariant defects rather than a need
for a new owner:

- GT-QG-01 is a validation/binding omission at the existing policy/mapper/service
  boundary;
- GT-QG-02 is an error-classification omission at the existing transport/connector/
  ledger boundary;
- GT-QG-03 is a projection/truthfulness omission in the existing profile/UI boundary;
- GT-QG-04 is a strict DTO range omission.

Existing large orchestration/UI owners remain accepted governed debt for this gate.
Remediation should remain narrow and must not create a second target preparation,
execution, provider-status, policy, or cache owner.

## 6. Security Review

Positive controls verified in source include TLS-1.3-only transport, certificate
verification, disabled redirects, bounded response bytes/time, safe base-URL validation,
backend-only user-id secret handling, write opt-in, fixed public errors, correlation
metadata, bounded Search candidates, authenticated case-scoped preview, and omission of
raw provider bodies/credentials from projections.

Security-relevant blockers:

- GT-QG-01 permits unvalidated policy-controlled text to cross the external read
  boundary and fails to bind execution to the owning case snapshot.
- GT-QG-02 converts an unknowable post-dispatch mutation result into a definitive
  failure, weakening no-replay safety.
- GT-QG-03 presents false environment status to operators, which can cause an operator
  to mistake a real Sandbox call for a Mock-only action.

No `.env`, token, password, user-id value, raw confidential KYC/provider payload, or
private portal content was read or written. The reviewer made no external call and no
provider/database mutation.

## 7. Required Fixes

Only the following current-candidate defects are required before another gate:

1. Enforce safe nonblank target-policy values, bind submission target policy/catalogue
   version to the immutable case snapshot, and prove all invalid enrichment stops before
   ledger/network activity.
2. Treat oversized and equivalent ambiguous post-dispatch mutation response failures as
   mutation-uncertain; retain `IN_PROGRESS` and prove zero automatic replay.
3. Project the configured GoldTier environment/classification truthfully through the
   backend execution profile and frontend journey/status labels, with Mock/Sandbox tests.
4. Bound RP `ownerPercent` semantically to 0..100 inclusive and add adverse DTO tests.

After remediation, rerun affected focused tests plus the full required backend,
frontend, static, contract, security/governance, lifecycle, and browser matrices. Freeze
a new exact fingerprint and dispatch a fresh independent re-quality gate. If Docker is
available then, refresh physical Mongo evidence; otherwise preserve the limitation
without claiming a fresh pass.

Do **not** implement Q-016 assignment/note/SLA mutations, do **not** invent RP
`childId`/relationship authority, and do **not** start Phase 22 as part of these fixes.

## 8. Readiness

- **Publication readiness:** NOT READY. No staging, commit, push, PR, or publication CI
  is authorized by this gate.
- **Pre-Phase 22 candidate readiness:** NOT READY pending GT-QG-01 through GT-QG-04 and a
  fresh exact-candidate independent PASS.
- **GoldTier XPI readiness:** partial local/Sandbox adapter only. The four read-only
  searches prove bounded reachability for those exact calls; there is no successful
  mutation evidence, no full Sandbox interoperability proof, and no Live readiness.
- **ACRA readiness:** unchanged from project truth; Mock by default, generic sandbox-
  shaped support partial, BizFile dormant, no Live ACRA proof.
- **Q-016:** OPEN and intentionally deferred; not a gate blocker.
- **Related party:** external dispatch blocked pending `childId` lifecycle and
  relationship authority; not a reason to invent a flow.
- **Phase 22:** remains on hold regardless of this gate outcome.

## 9. Git Status

- branch: `feature/pre-phase22-capability-expansion`
- `HEAD`: `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- `origin/main`: `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- staged paths at review time: 0
- frozen candidate before this report: 122 paths (76 tracked modifications, 46
  nonignored untracked paths)
- exact reviewed fingerprint:
  `afdb940366dbf54079a7c34c1afe8504ff799d93ae766b8cb8d79fa0d97feb6d`
- permitted reviewer write: this report only
- implementation/source/test/configuration/governance files changed by reviewer: none
- Git index/refs changed by reviewer: none
- external provider/database state changed by reviewer: none
- commit/push/PR/merge/next-phase action: none

The unexpected root artefact was preserved and excluded exactly as instructed. It was
not opened, hashed, moved, deleted, or otherwise touched.
