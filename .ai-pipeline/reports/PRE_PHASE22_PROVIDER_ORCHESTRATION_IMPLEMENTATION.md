# Pre-Phase 22 Provider Orchestration and Sandbox Testing — Implementation Report

Date: 2026-09-25
Branch: `feature/pre-phase22-provider-orchestration`
BASE_SHA: `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3`
Accepted source baseline: `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3`
Phase 22: **on hold**

## Outcome and authority

This increment implements the sponsor-confirmed early GoldTier Search and incremental
target synchronization through the existing CLM orchestration and target ledger. It also
adds the user-authorized Certificate of Incorporation POC profile, a backend-authored
processing inspector, and an HR-only GoldTier Sandbox testing console. The sole runtime
registry route remains Singapore ACRA.

Authority remains explicit:

- early Search and incremental Shell/Policy/Amend ordering: `SPONSOR_CONFIRMED` by the
  assigned development instruction;
- Certificate of Incorporation simplification: `USER_AUTHORIZED_POC`;
- editable `accountEntityType`: `PROJECT_DEFINED_PROVISIONAL` under the user-authorized
  POC boundary;
- ACRA API Marketplace Mock existence: `OFFICIAL_PROVIDER_DOCUMENTATION`;
- ACRA Marketplace authentication mechanism and seven GoldTier policy values:
  `TBD_SPONSOR`;
- related-party child-ID lifecycle: unresolved and dispatch-blocking.

No local default, observed HTTP status, Mock response, or provisional value has been
elevated to sponsor confirmation or Live-provider proof.

## GoldTier orchestration

GoldTier Search now occurs immediately after canonical registry identity becomes
available. The Search checkpoint is read-only, identity-fingerprint bound, retained in
the case envelope, and rerun when canonical identity changes. Every candidate is passed
through the existing entity resolver.

- Exact existing customer: retain the proved customer ID, mark Shell `SKIPPED`, continue
  evidence and ownership work, then perform Policy and Amend as separate durable ledger
  checkpoints.
- No match: continue evidence and ownership work, then perform Shell, Policy, and Amend
  as separate checkpoints.
- Probable, ambiguous, multiple, or conflicting candidates: create the existing typed
  human-review stop and perform no mutation.
- Search failure: block the target lane without silently treating the result as no match.
- Mutation uncertainty: retain `IN_PROGRESS`; do not replay. A retained provider outcome
  may be converted into a receipt without a second provider call.

The CLM target ledger remains the only mutation-intent, compare-and-swap, ordering,
stopping, uncertainty, and no-replay owner. There is no direct ACRA-to-GoldTier mapping,
second resolver, second ledger, or provider fallback.

## GoldTier Sandbox evidence and HR tester

The existing XPI adapter remains `SANDBOX_PARTIAL`, never Live. No external GoldTier
mutation was executed. Seven required policy fields remain `TBD_SPONSOR`, so a complete
safe write request is unavailable. Related-party submission is separately blocked until
the sponsor-defined `childId` lifecycle is proved.

The additive `/api/provider-sandbox/goldtier/*` surface and
`/admin/goldtier-sandbox` UI require the backend capability
`PROVIDER_SANDBOX_TEST`, granted only to HR. The console provides:

- a sanitized provider status exposing host identity, mode, classification, and blockers
  without credentials;
- bounded read-only Search;
- an assessed Search result from the existing entity-resolution owner;
- offline request preview/dry-run with ephemeral test-only values;
- a bounded process-local safe timeline;
- explicit related-party readiness and write blockers.

The guarded write endpoint currently returns a typed conflict before any provider call:
standalone console mutation cannot bypass the case-bound target ledger. The browser never
receives provider credentials, and the console has no client-case read capability. All
three non-HR roles are denied.

## ACRA historical and official Mock reconciliation

The default `mock` mode remains the local deterministic connector. The explicit
`api_marketplace_mock` mode names ACRA's official API Marketplace Mock environment and
is classified `MOCK`, not Sandbox or Live. Generic sandbox-shaped support remains a
separate partial capability; dormant BizFile composition is not revived.

A safe no-auth GET to the official Marketplace host was observed returning HTTP 401
with a bounded JSON response. This proves endpoint reachability and that authentication
is required; it does not prove the credential scheme. Because the current official
documentation and supplied repository evidence do not authorize an exact header or
OAuth exchange, Marketplace Mock composition fails closed with a typed configuration
error. Speculative OAuth and guessed authentication headers were not restored. No Live
ACRA endpoint was called and no provider mutation occurred.

The historical teammate artefacts, provider-evidence schema, readiness registry,
configuration reference, mapping contract, decision log, and open-question record are
reconciled to this boundary. Official Marketplace Mock is distinct from the Garden
synthetic fixture and from local Mock.

## Certificate of Incorporation POC profile

`CERTIFICATE_OF_INCORPORATION_POC` requires legal name, registration identifier, and
country. Registered address is optional; when supplied it is compared against registry
evidence rather than invented or forced. The profile remains a local deterministic POC,
not production OCR or legal document certification.

## Progress inspector

The zero-touch sequence now includes `GOLDTIER_SEARCH`. Case detail can optionally show
backend-authored Search disposition, target-operation states, blockers, and processing
events. The UI neither infers missing stages nor owns workflow transitions. Collapsed
and expanded views consume the authenticated user/case-scoped cache and retain existing
logout, identity-change, cancellation, and 401 clearing behavior.

## Intelligence, exception, and audit regression boundary

Entity resolution remains the single existing owner for exact/probable/ambiguous/no-match
decisions. UBO output remains advisory over the deterministic Decimal ownership engine,
never a legal UBO determination. Mock risk remains advisory and is not a regulatory or
compliance decision. Q-016 assignment/note/SLA mutations were not added.

The provider console timeline is bounded process-local operational evidence, not a
durable enterprise audit archive. Existing case activity and typed business-exception
owners are unchanged.

## API, model, persistence, cache, and configuration changes

- Additive case projection: GoldTier Search disposition/candidates and per-operation
  target status.
- Additive domain state: retained Search checkpoint, identity fingerprint, blockers,
  events, and incremental target-operation status.
- Additive schema-v5 compatibility: automation now persists stage-order version v2;
  records without the field are decoded as the pre-Search v1 order. Read-only decode
  does not manufacture a Search checkpoint or rewrite storage. A safe non-terminal
  continuation CAS-rebases to the earliest unproved v2 stage, while terminal and
  uncertain target states remain non-replayed. No envelope schema increase occurs.
- Additive reconciliation semantics: `REGISTRY_ONLY` is non-blocking only for a missing
  optional registered address backed by usable registry evidence. The durable
  `document_required` flag defaults to `true` for legacy reads, is exposed through the
  additive API projection, and requires no schema-version increase or migration.
- GoldTier modes remain `mock | sandbox`; Mock remains the default.
- ACRA registry modes are `mock | api_marketplace_mock | sandbox`; Mock remains the
  default, and the official Marketplace mode is intentionally blocked on auth authority.
- Frontend query keys remain user-scoped; the HR console adds its own user-scoped key and
  does not prefetch client cases.
- Architecture decision ADR-005 records the early read-only Search owner and incremental
  ledger boundary. D-051 and D-052 record the instruction-level authority without
  converting provisional values to sponsor truth.

## External calls and data handling

One bounded no-auth ACRA Marketplace Mock diagnostic returned HTTP 401. No credential,
cookie, bearer token, raw KYC payload, confidential document body, or provider response
body was retained. No GoldTier write, ACRA write, related-party write, or shared database
mutation occurred. Repository development did not inspect `.env`.

## Verification evidence

Fresh evidence against the post-fourth-remediation uncommitted candidate:

- backend pytest: `1289 passed / 35 expected physical-only skipped`, with three expected
  malformed-fixture serializer warnings in addition to the TestClient deprecation;
- frontend Vitest: `23 files / 286 tests` passed; TypeScript typecheck passed;
  production build passed with `116 modules`;
- the exact backend CI Ruff scope passed over backend application/tests; strict Mypy
  passed over `106 source files`; TypeScript and `pip check` passed. Task-owned
  governance Python is covered by the `159/159` governance/security matrix and the
  direct repository checkers;
- contract suite: `44/44`; Phase 07 delivery assets: `4/4`; expanded scoped
  governance/security: `242/242`;
- direct project-state, architecture, tooling, policy-authority, provider-readiness,
  secret, and whitespace checks passed; the external-provider evidence schema/validator
  is covered by the passing governance unit matrix rather than a fabricated new external
  evidence document;
- GoldTier validator passed with the truthful contract split `VALID=19`,
  `INVALID_QUARANTINED=19`, `NOT_VALIDATED=48`;
- synthetic intelligence evaluation passed: entity resolution `17/17`, UBO assistance
  `3/3`, mock risk `5/5`; these are bounded deterministic synthetic results only;
- configured Playwright discovery found 14 tests; the isolated guarded browser suite
  passed `14/14` before remediation and again after the stage-order repair; dependency
  inspection exited zero with expected optional platform packages absent;
- Windows lifecycle initially passed `22/23` and recorded one pre-header loopback read
  timeout before target dispatch. The exact test immediately passed `1/1`; the unchanged
  full suite then passed `23/23`. A fresh post-remediation full run also passed `23/23`
  and removed its owned processes. A fresh post-stage-order run also passed `23/23` and
  removed its owned processes;
- physical Mongo is `MISSING_INFRASTRUCTURE`: the Docker client is installed but the
  Docker Desktop Linux daemon pipe is absent. No unknown or shared Mongo URI was used,
  and historical results are not relabelled as current.

The invalid combined root `unittest discover` attempt is not test evidence: it pulled
contract modules into the wrong import context and also observed one pre-header loopback
timeout in a lifecycle test. Contracts, the 242-test governance/security scope, and the
23-test Windows lifecycle suite were then rerun separately under their canonical
commands and passed. The intermittent Windows loopback history is retained rather than
hidden or treated as a product success.

### Independent gate failure and bounded remediation

The first independent gate reviewed 85 candidate paths at fingerprint
`70ee1102996ba8b9db26e7442e174c141e0b0518c9bf5ebd96cb5ab70ec41858` and returned
`FAIL`. Its report is preserved unchanged as
`PRE_PHASE22_PROVIDER_ORCHESTRATION_QUALITY_GATE_FAILED.md`. The reviewer found three
bounded acceptance defects, each reproduced before repair:

- the generic zero-touch stage helpers retained the old Registry-to-Document transition,
  so a registry-complete restart could bypass early Search;
- the HR status projection paired Mock mode with `SANDBOX_PARTIAL` classification;
- the HR Search response exposed a hard-coded `NOT_ASSESSED` value rather than using the
  existing resolver.

The repair makes the canonical helpers traverse
`REGISTRY -> GOLDTIER_SEARCH -> DOCUMENT`, adds an in-memory resume test and a strict
schema-v5 Mongo-codec round trip for the registry-only checkpoint, derives Mock versus
Sandbox Partial classification from the active mode, forces Mock status writes disabled,
and returns the existing resolver's bounded outcome for console Search. It adds no second
resolver, migration owner, provider mode, write path, fallback, or replay route.

Focused post-repair evidence passes `170/170` across provider-console, zero-touch,
persistence, and CLM orchestration tests; the focused frontend console remains `3/3`.
The complete post-repair backend is `1323 passed / 35 skipped`, frontend is
`23 files / 285 tests`, Ruff passes, strict Mypy passes over 106 files, and TypeScript
passes. The post-repair contract suite is `44/44`, delivery assets are `4/4`, scoped
governance/security is `159/159`, synthetic intelligence remains `17/17`, `3/3`, and
`5/5`, GoldTier examples retain the truthful `19/19/48` split, Playwright is `14/14`,
and Windows lifecycle is `23/23`. The new candidate fingerprint and fresh independent
gate are recorded only after the evidence documents are frozen.

### Second independent gate failure and bounded COI remediation

The fresh re-gate closed PP22-QG-001 through PP22-QG-003 but returned `FAIL` on a new
integrated acceptance defect, PP22-RQG-001. The COI semantic profile made registered
address optional, while the downstream reconciliation owner still converted its
absence into `MISSING_IN_SOURCE`; zero-touch therefore raised
`DOCUMENT_REQUIRED_FIELD_MISSING` and stopped after Search. The review-only report is
preserved unchanged as
`PRE_PHASE22_PROVIDER_ORCHESTRATION_REQUALITY_GATE_FAILED.md`.

The repair keeps the existing reconciliation owner and adds the explicit
`REGISTRY_ONLY` field outcome. It is non-blocking only when the field is registered
address, every current document profile makes address optional, the registry retains a
usable address, and every document observation is missing. Registry and missing-document
observations remain separate; no document value is fabricated and no global source
precedence is introduced. A supplied mismatch, invalid value, or unverifiable value
still blocks, while the legacy `PROVISIONAL_CORPORATE` profile still treats absence as
`MISSING_IN_SOURCE`. The evidence fingerprint domain advances from v2 to v3 so a
retained reconciliation is recomputed under this profile-derived rule rather than
silently reusing stale semantics. The additive durable field defaults to required for
legacy reads, is projected through the API, and is exercised across encode/decode and
adapter restart.

RED evidence reproduced the exact full-journey `WAITING_FOR_REVIEW` defect. GREEN
evidence proves missing-address COI completion through Search/Shell/Policy/Amend,
supplied-address mismatch review, legacy required-address blocking, strict domain
construction, and restart/codec retention. Publication remains blocked until the full
post-remediation matrix and a third fresh exact-content gate pass. The refreshed matrix
passes backend `1327/35`, frontend `23 files/286 tests`, contracts `44/44`, delivery
assets `4/4`, governance/security `159/159`, synthetic entity/UBO/risk `17/17`, `3/3`,
and `5/5`, GoldTier examples `19/19/48`, Playwright `14/14`, and Windows lifecycle
`23/23`. Ruff, strict Mypy, TypeScript, production build, dependency, and direct
governance checks also pass.

### Third independent gate failure and stage-order compatibility remediation

The third reviewer matched 94 paths at fingerprint
`130dd4bb51f98500aa3901b2582caa9ba661c8c46d429b44812471fed72a4f25`, closed all four
earlier findings, and returned `FAIL` on PP22-FQG-001. Its unchanged report is preserved
as `PRE_PHASE22_PROVIDER_ORCHESTRATION_FINAL_QUALITY_GATE_FAILED.md`.

The report's direct decoder probe used `model_dump(mode="json")`, which intentionally
omits the backend-only `ownership_provider_binding_id`; that raw object was therefore
not a valid Mongo representation, and the reported decode rejection did not isolate the
stage prefix. Reproduction with the canonical `_encode` representation proved the exact
base-v5 pending shape does decode. The review nevertheless exposed a real next-step
compatibility gap: after decode, a pre-Search automation record could not be safely saved
under the new stage-prefix validator when work resumed.

The bounded repair keeps envelope schema v5 and adds an explicit automation
`stage_order_version`. New records use v2; strict persistence decode treats a missing
field as v1 on an unmodified copy, preserving the raw record. Domain validation accepts
the exact historical v1 prefix. A safe non-terminal continuation performs one repository
CAS rebase to v2 at Registry or GoldTier Search, then actually runs Search and re-evaluates
later deterministic stages. Decode and interrupted-document recovery never insert Search
into completed stages. Historical completed/technical-failure records remain terminal,
and legacy recovery-pending target uncertainty remains stopped without replay.

Focused GREEN evidence covers raw base-v5 pending decode, CAS-backed pending and review
continuation with Search before Shell/Policy/Amend, both interrupted-document states,
current and legacy uncertain-target no-replay, and historical terminal no-replay. The
complete persistence file passes 53 tests, combined zero-touch/CLM orchestration passes
122 tests, focused Ruff passes, and focused strict Mypy passes. Publication remains
blocked until the full matrix is refreshed and a fourth fresh exact-content gate returns
`PASS`.

### Fourth independent gate failure and durable decode remediation

The fourth reviewer matched 95 paths at fingerprint
`917df3133084f5e0326244047e19a889727e2d30da66b4c8054acbe92345418a`, confirmed all five
prior findings closed, and returned `FAIL` on the new PP22-4QG-001. Its unchanged report
is preserved as
`PRE_PHASE22_PROVIDER_ORCHESTRATION_FOURTH_QUALITY_GATE_FAILED.md`.

The reviewer proved that strict Mongo decode parsed schema and field shapes but did not
run the existing cross-field automation invariant validator. Explicit v2 metadata with a
legacy prefix, explicit v1 metadata with a v2 prefix, and a malformed v2 terminal state
therefore crossed the durable read boundary even though the domain validator rejected
them. RED tests reproduced all three corrupt raw representations through the canonical
Mongo encoder/decoder.

The bounded repair invokes the existing `validate_automation_record` after schema
conversion, model validation, unknown-field rejection, and Mongo/envelope identity
verification. Its existing exception boundary converts invariant failure to
`PersistenceDataInvalidError`. No schema version, migration, recovery policy, workflow
owner, provider behavior, or replay rule changes. Canonical missing-field schema-v5
legacy records still decode on an unmodified copy, safe continuation still CAS-rebases
before Search, and historical terminal or uncertain target state remains non-replayed.

GREEN evidence passes all 56 persistence tests and the 174-test combined
persistence/zero-touch/CLM scope, focused Ruff, and strict Mypy. The refreshed full
matrix passes backend `1289/35`, frontend `23 files/286 tests`, contracts `44/44`,
delivery `4/4`, governance/security `242/242`, synthetic entity/UBO/risk `17/17`,
`3/3`, and `5/5`, GoldTier `19/19/48`, Playwright `14/14`, and Windows lifecycle
`23/23`. Ruff, strict Mypy over 106 files, TypeScript, production build, dependencies,
direct governance, secrets, and whitespace checks also pass. Physical Mongo remains
unavailable because the Docker Linux daemon pipe is absent. Publication remains blocked
until a fifth fresh exact-content independent gate returns `PASS`.

### Published-candidate CI remediation

The first published candidate, commit
`9c17fc0634ca23b019cb3aba2ff339519288c530`, completed frontend, backend, security,
E2E, and Windows lifecycle CI successfully. Push run `36032038372` reported the physical
Mongo harness at `31 passed / 4 failed`. The harness intentionally exposes only aggregate
counts, so diagnosis correlates each failed pytest item with the already-passing unit and
codec coverage for the new stage order.

The first remediation updated three zero-call assertions and one uncertain-target
fixture. A fresh independent gate rejected that mapping because two zero-call assertions
are in the same pytest function, and found the remaining stale aggregate assertion in
the three-case restart test. The complete four-item mapping is: one review-refresh call
count; one failed-replacement path whose two sequential assertions both retain the early
Search; one current-v2 uncertainty fixture missing completed `GOLDTIER_SEARCH`; and one
three-case aggregate that must include Search for the second pending Singapore case.
The last total is therefore five GoldTier calls: two Search calls plus Shell, Policy,
and Amend for the completed case. The failed gate is preserved as
`PRE_PHASE22_PROVIDER_ORCHESTRATION_CI_REMEDIATION_QUALITY_GATE_FAILED.md`.

The bounded remediation changes only those physical-test expectations and fixture data;
product code, schema, provider behavior, no-replay policy, and business rules are
unchanged. Focused persistence and zero-touch tests pass `111/111`, the physical suite
still collects all 15 owned Phase 12 tests, and diff hygiene passes. Publication of the
remediation remains blocked until a fresh exact-content independent gate passes.

## Limitations and open sponsor dependencies

1. Seven GoldTier policy fields remain `TBD_SPONSOR`; therefore external customer writes
   and a write-evidence classification are blocked.
2. Related-party dispatch remains blocked until the `childId` lifecycle and relationship
   values are sponsor-authorized.
3. ACRA API Marketplace Mock authentication is unresolved; endpoint reachability is not
   an auth contract.
4. Physical Mongo evidence is unavailable on this host because the Linux Docker daemon
   is not running.
5. Production ACRA, production GoldTier/PingFed, vendor OCR, production SSO, Camunda,
   regulatory risk, and autonomous approval remain unimplemented.
6. Q-016-dependent Exception Workbench mutations remain deferred.
7. Phase 22 remains on hold.

## Complexity closure

Status: `exceeded-and-governed`. The orchestration owners were already large and this
increment adds material checkpoint logic, but ownership remains singular: CLM owns the
read checkpoint, the target ledger owns all writes/no-replay, the existing resolver owns
candidate decisions, repositories own durable reconstruction, backend capabilities own
authorization, and React Query owns client cache lifecycle. Focused provider-console and
UI-query modules avoid creating additional responsibilities in the central API and app
files. Further decomposition is a follow-up architecture improvement, not a duplicate
owner or hidden fallback in this slice.

## Self-review answers

- Search is early and identity-bound: **yes**.
- Exact existing customer can receive Shell: **no**.
- Ambiguous candidates can mutate GoldTier: **no**.
- Uncertain target writes can replay: **no**.
- Official ACRA Mock can silently become local Mock: **no**.
- Speculative OAuth or a Live ACRA call was introduced: **no**.
- COI missing fields are invented: **no**.
- HR console can access client cases or browser credentials: **no**.
- Non-HR can access the console: **no**.
- Standalone console can write a non-synthetic customer: **no**; all standalone writes
  are blocked before dispatch.
- Progress UI invents workflow stages: **no**.
- Advisory ML became legal UBO or mock risk became regulatory: **no**.
- Did Q-016 expand? **NO.**
- Did Phase 22 start? **NO.**

Publication remains blocked until this exact candidate receives an independent verdict
of `PASS`. The repository-owner human retains merge authority.
