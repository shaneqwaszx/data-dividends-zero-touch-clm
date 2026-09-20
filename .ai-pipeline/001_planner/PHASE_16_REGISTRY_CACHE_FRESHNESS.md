# Phase 16 — Registry Cache and Freshness Implementation Handoff

## 1. Handoff result

**PLANNER HANDOFF COMPLETE — DECISIONS REQUIRED**

Phase 16 should add one backend-owned, Mock-only reusable registry snapshot cache in
front of the existing strict four-operation acquisition adapter. It must keep the
existing `RegistryProviderRouter`, `AcraRegistryProviderAdapter`,
`RegistryAcquisitionBundle`, `OnboardingService`, case envelope, ownership engine,
zero-touch coordinator, authorization owner, and target ledger as their current
canonical owners.

The smallest safe implementation is not authorized until the project owner explicitly
approves the four bounded POC choices in section 7.1: reuse at all, a fixed UTC duration,
cross-team reuse of synthetic Mock evidence, and Mock cache retention/invalidation.
Current accepted authority says only that cache-first is a future direction and that
90 days is an example. It does not approve cache reuse, 90 days, three calendar months,
manual refresh, production retention, or live-provider storage.

After those four choices are approved, the implementation may proceed independently of
the separate review/rework UI lane. A user-requested forced-refresh API, generic sandbox
or live caching, scheduled refresh/OCDD, and mutation of an existing progressing or
completed case remain separate blocked extensions.

## 2. Task identity, baseline, and preflight

| Item | Observed result |
|---|---|
| Worktree | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix` |
| Branch | `phase/16-registry-cache-freshness-planning` |
| Assigned `BASE_SHA` | `cab05d7dc98d4c50c8fc096835fe49802d5896e2` |
| Current source revision | `cab05d7dc98d4c50c8fc096835fe49802d5896e2` |
| Locally observed `origin/main` | `cab05d7dc98d4c50c8fc096835fe49802d5896e2` |
| Ahead/behind | `0 / 0` |
| Index/worktree before planner write | Clean; `git status --porcelain=v2 --branch` reported only branch metadata |
| Active Git operation | None of merge, cherry-pick, revert, bisect, rebase, or sequencer markers present |
| Existing Phase 16 planner | Absent before this write |
| Project-state behavioral baseline | `614e9ffc36bc8f0d1a9a4674d04639ad6b2bc638`, separately recorded in `docs/PROJECT_STATE.md`; it is not this branch `HEAD` |
| Independently reviewed Phase 16 content | None; this planner is not an independent quality-gate result |

`python scripts/dev_context.py` passed at task start and reported the expected branch,
HEAD, `origin/main`, clean tracked state, provider classifications, persistence modes,
and Q-001 through Q-018. No behavior suite was run because this is planning-only.

### 2.1 Capability and resource preflight

- Available and used: worktree-scoped filesystem read/write, PowerShell, Git 2.55.0,
  Python 3.12.10, and the repository context scripts. The only write is this planner.
- Installed local test/tool entry points observed without running suites: pytest 8.4.2,
  Ruff 0.16.2, mypy 1.20.2, Node 22.23.2, and npm 10.9.8.
- Frontend `node_modules` and its local Playwright package are absent in this worktree.
  No dependency installation is authorized or needed for this planner.
- `mongod` and `mongosh` executables were not found. No Mongo URI, server, database,
  collection, or external provider was probed. Physical Mongo is a later implementation
  prerequisite, not evidence from this run.
- No browser, lifecycle process, shared port, disposable database, external provider,
  network call, or connector plugin was started or reserved.
- The recommended-but-uninstalled app plugins supplied with the task are unrelated to
  this source-based planner and were not installed.
- No subagent was used. The requested planning route is Sol/High; the host did not expose
  a separately verifiable runtime model identity to record as evidence.
- `.env`, credentials, protected sponsor artefacts, sibling worktrees, and databases were
  not accessed.

### 2.2 Evidence identities

1. **Current source revision:** `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
   plus this sole uncommitted planner file.
2. **Behavior actually tested in this run:** none. Context/preflight observations apply
   to the pre-write `cab05d7...` tree; no application behavior claim is transferred
   from historical reports.
3. **Independently reviewed content:** none. Phase 15A reports establish only their own
   accepted future-only cache wording and do not review this Phase 16 design.

## 3. Scope, change classification, and readiness

### 3.1 Current planning write

- Change class: `DOCS_ONLY`.
- Authorized output: this file only.
- No implementation, configuration, source, test, dependency, decision-log,
  sponsor-question, project-state, architecture, or UI file is changed in this run.

### 3.2 Later implementation change classes

The recommended implementation is expected to be classified as:

- `BACKEND_DOMAIN` — freshness/key/binding semantics and acquisition coordination;
- `PERSISTENCE` — a new shared snapshot collection/repository, CAS, restart, and
  independent case-envelope schema v4;
- `EXTERNAL_PROVIDER` — provider acquisition is conditionally avoided or repeated;
- `ARCHITECTURE_REFACTOR` — one new canonical cache/acquisition coordinator and state
  owner are introduced;
- `CI_TOOLING` — the physical Mongo allowlist/runner must explicitly own a Phase 16
  suite;
- `BACKEND_API` and `AUTH_RBAC_SECURITY` only if a manual forced-refresh request or a
  browser-visible cache-use projection is separately approved.

No `FRONTEND_UI` or `FRONTEND_STATE_CACHE` change belongs to the smallest backend slice.
The React Query cache remains unrelated.

### 3.3 Requirement Ready Check

| Check | Result |
|---|---|
| Requirement source | The assigned Phase 16 task brief is explicit about planning scope, adverse cases, evidence semantics, and non-goals. |
| Current-source baseline | Ready; current owners, composition, persistence, tests, and fault seams were inspected. |
| Authority for architecture analysis | Ready; a cache design can be compared and bounded without adopting policy. |
| Authority for runtime reuse policy | Not ready; section 7.1 owner decisions are missing. |
| Authority for sandbox/live caching | Blocked by Q-012 plus storage/licensing/retention authority. |
| Authority for manual refresh role/API | Not ready; Q-016 remains open and no registry-refresh capability exists. |
| Decision | Ready for this planner; runtime implementation is decision-gated, not globally blocked. |

### 3.4 TDD Route

- Mode: off.
- Decision: skipped.
- Strict authority: not applicable; neither the task nor repository requires strict
  test-first TDD for this planning pass.
- Test posture for later implementation: deterministic post-change focused regression,
  race falsification, restart evidence, and physical Mongo evidence.
- No plan step may call a test-only seam a runtime guarantee.

## 4. Authority and evidence baseline

The plan applies the repository source-of-truth order. The material conclusions are:

- D-042 and the accepted Phase 15A gate say cache-first registry reuse is future-only;
  90 days is only an example configurable policy; refresh/OCDD/perpetual-KYC are not
  implemented or authorized.
- No tracked current contract, decision, sponsor question, source, or test inspected in
  this run records a sponsor-confirmed rule to retrieve ACRA for every onboarding. The
  current runtime nevertheless does retrieve for every eligible new case. If an
  authoritative retrieve-each sponsor direction exists outside the authorized tracked
  read-set, it must be supplied and reconciled before enabling reuse.
- Q-012 blocks authoritative ACRA operation schemas, access, errors, limits, TLS and live
  proof. Q-013/Q-015 leave production retention/source governance unresolved. Q-016
  leaves production role authority unresolved.
- D-029 authorizes only the project-owned four-operation Mock contract and complete,
  partial, failed, and ordered stopping semantics.
- D-033 authorizes explicit memory/Mongo persistence, strict schema/CAS, and restart
  recovery for the case aggregate; it is not authority for a new shared registry store
  or regulatory retention.
- Mock remains Mock, the generic sandbox seam remains Partial, BizFile remains Dormant,
  and no source may be labelled Live.

### 4.1 Context and evidence read-set

The planner read the local constitution, `docs/PROJECT_STATE.md`,
`docs/ARCHITECTURE.md`, `docs/DEVELOPMENT_WORKFLOW.md`, the relevant ACRA,
persistence, reconciliation, and zero-touch contracts, `docs/PROJECT_CONTEXT.md`,
`docs/decisions/DECISION_LOG.md`, and
`docs/sponsor-questions/OPEN_QUESTIONS.md` before the repository skills and current
source/tests. The relevant accepted historical boundary was then checked in
`.ai-pipeline/001_planner/PHASE_15A_SPONSOR_REBASELINE_BEHAVIOUR_ALIGNMENT.md`,
`.ai-pipeline/reports/PHASE_15A_QUALITY_GATE.md`, and
`.ai-pipeline/reports/PHASE_15A_KYC_POLICY_EVIDENCE_REREVIEW.md`. Those reports support
the future-only/non-claim boundary; they are not current implementation evidence.

There was no existing Phase 16 planner to inherit. The user's assigned brief is the
requirement source for this new handoff.

## 5. Current-state inventory and canonical owners

| Concern | Current owner and source location | Current behavior relevant to Phase 16 |
|---|---|---|
| Request normalization | `StartOnboardingRequest.normalize_uen`, `apps/backend/app/main.py:125`; `OnboardingService._create_staged_case_locked`, `apps/backend/app/services/onboarding.py:251` | The API and service trim/uppercase the identifier before routing. |
| SG identifier eligibility | `is_eligible_singapore_uen`, `apps/backend/app/domain/jurisdiction.py:12` | The current POC grammar is nine digits plus one uppercase letter. It is not a full official UEN validator. |
| Jurisdiction authority | `JurisdictionResolver`, `apps/backend/app/domain/jurisdiction.py:138`; `OnboardingService._create_staged_case_locked`, lines 268–335 | User and identifier observations are retained. Unresolved/conflicting paths stop before any provider call. |
| Registry routing | `RegistryProviderRouter`, `apps/backend/app/connectors/registry.py:381`; invoked by `OnboardingService` lines 336–358 | Only resolved SG selects ACRA. Foreign routes are closed and stop. A cache must not become a second router or precede these gates. |
| Provider acquisition interface | `RegistryProvider.retrieve_acquisition`, `apps/backend/app/connectors/registry.py:63`; `AcraRegistryProviderAdapter`, line 79 | The adapter owns the four ordered calls and reconstructs strict DTOs. |
| Four-operation aggregate | `RegistryAcquisitionBundle`, `apps/backend/app/domain/models.py:223` | Exactly four ordered results, provider/environment consistency, identity binding, record counts, provenance, and complete/partial/failed invariants are revalidated. |
| Mapping and original source provenance | `map_acra_company`, `apps/backend/app/mappers/acra.py:14`; `RegistryEvidenceProvenance`, `apps/backend/app/domain/models.py:130` | Strict ACRA DTOs become source-neutral canonical evidence. UTC provider retrieval timestamps and safe references are retained. Raw payloads are excluded. |
| Acquisition invocation/checkpoint | `OnboardingService._create_staged_case_locked`, `apps/backend/app/services/onboarding.py:251`, especially lines 360–436 | Acquisition occurs only after routing/eligibility. The bundle and entity are copied into the case, partial/failed outcomes stop, and only complete valid evidence reaches `VALIDATED`. |
| Required-stage failure handling | `OnboardingService._run_required_stage`, lines 1363–1407 | Connector/unexpected failures persist a sanitized failed case and raise a typed infrastructure error. |
| Immutable/retained per-case evidence | `OnboardingCase.registry_acquisition`, `apps/backend/app/domain/models.py:450`; `DurableCaseSnapshot.onboarding`, `apps/backend/app/persistence/models.py:161` | Each case retains a defensive copy of its acquisition in memory and schema-v3 Mongo. That is case evidence, not a reusable cross-case cache. |
| Browser projection | `BrowserRegistryAcquisition`, `apps/backend/app/api_models.py:194`; `OnboardingCaseResponse`, line 209 | Safe normalized evidence and the original acquisition time are exposed; raw endpoint/auth data is omitted. |
| Ownership consumer | `RegistryAcquisitionOwnershipProvider`, `apps/backend/app/connectors/registry_ownership.py:26`; composed in `apps/backend/app/composition.py:182` | It reads the case-bound bundle and feeds the one existing deterministic Decimal ownership engine. |
| Zero-touch establishment | `ZeroTouchOrchestrator.create_case` and `_create_case_locked`, `apps/backend/app/services/zero_touch_orchestration.py:120` | Registry/CLM/automation records are established under the case lock; rollback removes case-owned state only. |
| Resume and target replay | `ZeroTouchOrchestrator.start`, line 486; target ledger in `OnboardingService.execute_submission_input`, `apps/backend/app/services/onboarding.py:517` | Resume does not reacquire Registry. The target ledger remains the only target ordering/no-replay owner. |
| Memory case repository | `InMemoryOnboardingCaseRepository`, `apps/backend/app/services/repository.py:41` | Defensive copies, insert-only create, update-only save, and process-local locking. |
| Mongo case envelope | `MongoCaseStore`, `apps/backend/app/persistence/mongo_case_store.py:52`; adapters in `persistence/repositories.py` | Strict `_id`/case binding, schema decode, revision CAS, insert/update/delete separation, startup validation, and no memory fallback. |
| Persistence composition | `PersistenceBundle` and `build_persistence_bundle`, `apps/backend/app/persistence/composition.py:83` | Explicit memory or Mongo mode. Global team/profile/policy state already uses separate bounded owners. |
| Runtime composition | `build_onboarding_service`, `apps/backend/app/composition.py:71`; `create_app`, `apps/backend/app/main.py:248` | `main.py` assembles settings, persistence, services, and routes. Business/cache logic must not be placed in route handlers. |
| Current configuration | `Settings`, `apps/backend/app/config.py:18` | Provider mode and persistence mode are backend configuration. There is no registry cache/freshness setting. |
| Current policy catalogue | `PolicyManagementService`, `apps/backend/app/services/policy_management.py:47`; `CasePolicySnapshot`, `apps/backend/app/domain/policy.py:196` | Two mutable provisional runtime thresholds are copied immutably into each new case. No registry freshness rule exists. Adding one here would introduce dynamic policy mutation and browser/RBAC coupling; that is not needed for the smallest cache slice. |
| Case deletion | `CaseDeletionService`, `apps/backend/app/services/case_deletion.py:82` | Deletes case-owned aggregates and transients. It makes no provider call. A shared registry snapshot would not be case-owned. |
| Call/fault seams | `CountingAcraConnector`, `apps/backend/tests/test_phase10_registry_acquisition.py:47`; `test_phase09_jurisdiction_gateway.py`; `test_onboarding_resilience.py`; `test_acra_modes.py` | Existing tests count each operation, inject wrong identity/malformed/failure/timeout behavior, and prove ordered stopping. |
| Persistence/restart seams | `test_phase12_persistence.py`; `test_phase12_real_mongo.py`; `scripts/mongo_test_safety.py`; `scripts/run_physical_mongo_tests.py` | Deterministic envelope, restart, CAS, generated-database cleanup, and physical-runner patterns exist. The allowlist currently has no Phase 16 database and the runner owns four suites only. |

### 5.1 Three different retained-state concepts

1. **Per-case registry evidence** is the `RegistryAcquisitionBundle` already copied into
   `OnboardingCase` and its durable case envelope. It is immutable historical evidence
   for that case and must remain so.
2. **A reusable registry snapshot cache** does not exist. It would be shared by exact
   provider/mode/schema/identifier identity and would be consulted only after routing,
   access, and identifier gates.
3. **Frontend React Query caching** is a 45-second authenticated browser-memory cache of
   API GET results. It is user/session/team scoped, cleared on identity changes, and has
   no authority to reuse Registry evidence or suppress provider calls.

Persisting (1) or retaining (3) is not evidence that (2) exists.

## 6. Architecture existence check and alternatives

### 6.1 Existence Check

| Reuse candidate | Fit | Conclusion |
|---|---|---|
| `OnboardingCaseRepository` / case envelope | Case-owned and keyed by case UUID; cross-case reuse would require scanning or duplicate ownership and would couple deletion/team scope to shared state. | Reject as cache owner; retain only immutable per-case evidence. |
| `RegistryProviderRouter` | Owns closed jurisdiction-to-provider routing, not storage, policy, or freshness. | Reuse unchanged; do not add cache behavior. |
| `AcraRegistryProviderAdapter` | Owns strict provider acquisition and normalized bundle construction. A decorator here would mix storage/policy into the connector and could bypass application gates. | Reuse as the fetch owner; do not make it the cache owner. |
| `OnboardingService` | Owns the checkpoint at which route/identifier gates have passed and a bundle becomes case evidence. | Keep it as caller/binder, but extract cache/fetch coordination into one focused service to avoid further hotspot growth. |
| Existing policy catalogue | Owns mutable global rules and per-case snapshots. Using it would implicitly authorize runtime mutation roles and retroactive shared-cache effects. | Do not extend in the smallest slice. Construct a fixed typed freshness policy from validated backend settings. |
| Existing memory/Mongo composition | Already owns explicit mode selection and fail-closed startup. | Reuse for the new repository adapter. |

**Existence conclusion:** a focused `RegistryAcquisitionCoordinator` plus one
`RegistrySnapshotRepository` port is justified. It is the only new state owner. It must
not own routing, canonical mapping, ownership calculation, authorization, workflow
progression, or target replay.

### 6.2 Design alternatives

| Alternative | Decision | Reason |
|---|---|---|
| No cache; retrieve for every case | Safe current behavior and mandatory fallback when reuse authority is absent. | Does not deliver Phase 16 reuse once owner approval is supplied. Keep as default-disabled compatibility mode. |
| Reuse another case's envelope | Rejected. | Cross-case query, deletion coupling, team-disclosure risk, mutable historical evidence, and wrong persistence ownership. |
| Cache raw provider responses | Rejected. | Violates strict DTO/canonical flow, data minimization, schema isolation, and raw-payload prohibition. |
| Cache each of four operations independently | Rejected. | Permits mixed provider/schema/version/time bundles and creates partial-refresh semantics not authorized by D-029. |
| Connector/decorator cache | Rejected. | Mixes policy/storage into provider adapters and makes it easier to consult cache before jurisdiction/access gates. |
| External Redis/distributed cache | Rejected. | No measured need, new dependency/operations surface, no distributed-runtime requirement, and no authority. |
| One shared cache of complete normalized bundles with memory/Mongo adapters | **Recommended.** | Lowest-entropy design that preserves current mapping/validation and separates reusable snapshots from case evidence. |

### 6.3 Architecture review result

**ARCHITECTURE REVIEW: PROCEED AFTER OWNER DECISIONS.** The design preserves dependency
direction:

```text
authenticated create request + team/capability checks
  -> OnboardingService jurisdiction and identifier gates
  -> RegistryProviderRouter
  -> RegistryAcquisitionCoordinator
       -> RegistrySnapshotRepository (read/CAS write)
       -> existing RegistryProvider.retrieve_acquisition on miss/stale
  -> defensive case-bound RegistryAcquisitionBundle copy + use binding
  -> existing reconciliation/ownership/readiness/target owners
```

No API route imports persistence. No provider DTO enters the cache. No cache read can
select a provider or make an ineligible case eligible.

## 7. Authority decision table

### 7.1 Decisions required before the smallest implementation

| ID / question | Current evidence | Classification | Recommended bounded POC choice | Scope affected if not approved |
|---|---|---|---|---|
| O-16-01 — May a fresh snapshot be reused instead of retrieving Registry for each new case? | Runtime retrieves for each eligible case. D-042 says cache-first is future-only. No tracked sponsor-confirmed retrieve-each rule was found. | Unresolved owner policy; not sponsor-confirmed. | Approve reuse only for the synthetic Mock ACRA mode, behind explicit disabled-by-default configuration. Preserve retrieve-each when disabled. | Blocks cache hits and provider-call suppression; schema/repository analysis and tests can still be prepared, but no enabled runtime behavior. |
| O-16-02 — What is the freshness duration and unit? | 90 days is an example only. No rule says three calendar months. | Unresolved owner policy. | Approve one fixed UTC elapsed duration expressed in seconds. Candidate: `90 * 24h`, explicitly a provisional POC choice, not “three months.” If calendar months are required, re-plan the policy arithmetic. | Blocks freshness eligibility, expiry tests, and enabled reuse. |
| O-16-03 — May synthetic Mock snapshots be shared across cases/teams/users? | Backend case access is authoritative; no cache exists. Q-016 leaves production sharing policy open. | Unresolved owner/security choice. | Approve one backend-global Mock cache. It has no direct API; every use still creates a team-owned case and is exposed only through normal case access. | Blocks cross-case reuse. A per-team cache is possible but is not recommended because it duplicates identical synthetic Registry state and does not resolve production authority. |
| O-16-04 — What is the bounded Mock retention/invalidation rule? | Freshness and retention are absent; case deletion is case-owned only. Production retention is unresolved. | Unresolved owner retention choice. | Approve one current complete entry per exact cache key, replaced only by a successful complete refresh. Expiry is ineligibility, not deletion. Case deletion does not delete shared snapshots. No TTL, purge job, or history collection. | Blocks durable Mongo caching; memory-only experimental logic would not satisfy Phase 16 parity. |

### 7.2 Decisions that do not block the smallest core slice

| Question | Current evidence/source | Classification | Recommendation | Dependent scope |
|---|---|---|---|---|
| Forced refresh and requester | No request field, capability, or route exists; Q-016 leaves role authority open. | Sponsor/owner-dependent. | Exclude from the core slice. If separately approved, add a new `REGISTRY_FORCE_REFRESH` backend capability and grant it to Director only for a *new-case creation* request. Do not reuse unrelated `POLICY_MUTATE`. | Conditional API/RBAC/UI contract and call-chain changes. |
| Stale data after refresh failure | Existing provider failures stop downstream; D-029 preserves partial/failed evidence. | Established technical invariant; exact cache treatment is a proposed POC choice. | Never serve stale. Retain the old shared entry unchanged, fail the new case safely, and permit a later explicit retry/new case. | Implementable with the core slice. |
| Invalid/corrupt cache entry | Mongo/current domain decode fails closed; no repair-on-read. | Established persistence rule. | Fail with sanitized `REGISTRY_CACHE_INVALID`; do not treat corruption as a miss, delete it, or call the provider in that request. | Implementable with the core slice. |
| Provider/schema/version change | Strict source/bundle validation exists; no cache identity exists. | Technical design decision. | Exact key isolation by provider, environment, normalized identifier, acquisition contract version, and dataset/fixture namespace. A mismatch is a miss; an internally inconsistent returned entry is corruption. | Implementable with the core slice. |
| Live/sandbox storage or licensing | Q-012 lacks authoritative contract/access; no licensing/storage permission is recorded. | Sponsor/provider-dependent; blocked. | Cache only Mock in Phase 16. Generic sandbox remains Partial and retrieves/fails according to current behavior. BizFile remains Dormant. | Blocks sandbox/live caching and any interoperability claim. |
| Physical stale-entry deletion | No approved retention or admin purge authority. | Sponsor/owner-dependent. | Do not add a purge API, TTL index, scheduler, or case-delete cascade. Treat physical cleanup as a later retention phase. | Does not block one-current-entry Mock cache after O-16-04 approval. |
| Existing-case refresh | Current decisions/reconciliation/ownership/target snapshots bind to retained evidence. | Established immutability/no-replay constraints. | Reject. Refresh may be evaluated only before a new case crosses Registry. Progressing/completed cases keep their original evidence and decisions. | No core blocker. A future re-onboarding/reassessment workflow requires a separate phase. |

### 7.3 Retrieve-each reconciliation rule

Until O-16-01 is approved, `registry_cache_mode="disabled"` preserves current
retrieve-for-each behavior. If a sponsor/API-owner direction explicitly requires a new
Registry retrieval for every onboarding, it overrides a POC reuse proposal and the
cache must remain disabled. Cache reuse is not a reinterpretation of that direction;
it is a distinct policy choice that must be recorded as provisional.

## 8. Recommended data and ownership design

### 8.1 Canonical owners

| Responsibility | Owner after Phase 16 |
|---|---|
| Jurisdiction observations/resolution | Existing `JurisdictionResolver` and `OnboardingService` |
| Identifier normalization/eligibility | Existing request/service normalization and `is_eligible_singapore_uen` |
| Provider selection | Existing `RegistryProviderRouter` |
| Four provider calls, strict DTO reconstruction, bundle validation | Existing `AcraRegistryProviderAdapter` and `RegistryAcquisitionBundle` |
| Fresh-hit/miss/stale decision and per-key process-local single-flight | New `RegistryAcquisitionCoordinator` |
| Shared entry persistence | New `RegistrySnapshotRepository`, with memory and Mongo adapters |
| Per-case immutable acquisition and cache-use binding | Existing `OnboardingCaseRepository` / case envelope |
| Authorization/team scope | Existing API authentication, `creation_team`, `CaseAccessPolicy` |
| Reconciliation, ownership, readiness, target order/no-replay | Existing owners unchanged |

### 8.2 Cache key

Use one exact immutable key containing:

- `provider_code`: `ACRA`;
- `source_environment`: `MOCK` for the initial slice;
- `normalized_identifier`: the already-eligible uppercase UEN;
- `acquisition_contract_version`: an explicit internal Phase 10 bundle/operation version;
- `provider_dataset_namespace`: an explicit synthetic fixture revision such as
  `MOCK_ACRA_SYNTHETIC_V1`.

Mongo `_id` should be a deterministic SHA-256 digest of a canonical serialization of
those fields; the decoded fields must still be retained and validated against `_id`.
Do not include case, team, user, URL, credential, or raw provider content in the key.
Test/fault connectors without an explicit cache identity must bypass the cache, or use a
test-only unique namespace injected by the test. They must never collide with normal
Mock fixtures.

Freshness policy is not part of the data identity. A reader evaluates an entry using the
current approved policy and records that exact policy fingerprint in the case binding.
Changing duration can therefore make the same entry fresh or stale without relabelling
its provider evidence. Provider/schema/dataset changes still create a new key and cannot
mix bundles.

### 8.3 Shared cache entry schema v1

Create a strict, frozen `RegistrySnapshotEntry` with:

- `cache_schema_version = 1`;
- `cache_id` and complete decoded `RegistryCacheKey`;
- `revision >= 0` for CAS;
- one **complete** `RegistryAcquisitionBundle`;
- `freshness_anchor`: the earliest retrieval time among the four attempted operation
  provenances, so every operation remains inside the freshness window;
- `provider_effective_at: datetime | None`, populated only if a future authoritative
  provider contract actually supplies and validates it; current Mock stays `None`;
- `written_at` from the coordinator clock;
- no case/team/user, raw response, source endpoint, authorization, ownership result,
  reconciliation result, readiness state, or target state.

The model must prove the key matches the bundle's requested identifier,
provider/environment, contract/dataset descriptor, and strict complete status. Partial,
failed, empty-mandatory, malformed, wrong-identity, mixed-environment, or reordered
bundles cannot be cached.

### 8.4 Per-case evidence-use binding

Add a frozen `RegistryEvidenceBinding` beside `OnboardingCase.registry_acquisition`:

- disposition: `PROVIDER_FETCH` or `CACHE_HIT` (and `FORCED_REFRESH` only in a later
  approved extension);
- cache key digest and cache entry revision when applicable;
- original `freshness_anchor` and unchanged bundle `retrieved_at`;
- cache `written_at` when applicable;
- `bound_to_case_at` (the cache read/use time, or fresh-fetch binding time);
- the evaluated freshness policy ID/version/fingerprint, fixed duration, comparator,
  and computed `expires_at`;
- provider/environment/contract/dataset identity;
- no claim that cache use re-retrieved, re-verified, or made the evidence current at the
  use time.

The case stores a defensive deep copy of the complete bundle. Later shared-cache refresh
or replacement must not mutate that bundle, its canonical entity, reconciliation
fingerprints/decisions, ownership analysis, readiness snapshot, or target snapshot.

### 8.5 Freshness policy owner

For the smallest slice, construct a frozen `RegistryFreshnessPolicy` from validated
backend `Settings`. It should have a fixed policy ID/version, fixed elapsed duration,
exclusive expiry comparator, and a deterministic fingerprint of those semantic fields.

Do **not** add this rule to the mutable `PolicyManagementService` catalogue in Phase 16.
That would authorize RM/Director runtime mutation, require new UI/API semantics, and
retroactively alter a shared cache without sponsor role authority. A future request for
operator-editable freshness is a separate policy/RBAC phase.

Recommended settings after owner approval:

- `registry_cache_mode: Literal["disabled", "mock"] = "disabled"`;
- `registry_cache_freshness_seconds: int | None = None`, required and bounded when mode
  is `mock`;
- `mongo_registry_cache_collection`, bounded like existing collection names;
- no sandbox/live enable value.

Startup must fail closed if Mock caching is enabled without a valid duration or if its
collection conflicts with another configured collection. Disabled mode performs no
cache read/write and preserves retrieve-each behavior.

### 8.6 Cache schema versus case-envelope schema

These are separate decisions and versions:

- shared registry cache collection: schema v1, keyed by registry snapshot identity;
- durable case envelope: bump current schema v3 to v4 because the case gains an
  immutable `registry_evidence_binding`.

Add exact schema-v3 read compatibility that supplies `registry_evidence_binding=None`
in memory without rewriting. Existing v1/v2 compatibility must do the same. Unknown,
malformed, or mixed versions remain rejected. A `None` legacy binding means “Phase 16
use metadata was not recorded”; it must not be presented as a fresh provider fetch.

No transaction across the shared entry and case envelope is required. Write a complete
shared snapshot first, then bind a deep copy to the new case. If later case establishment
fails, case rollback removes case-owned state but leaves the valid shared snapshot. If a
later refresh replaces the shared entry before the case save, the case still binds the
specific bundle/revision already copied. The ADR must record this boundary.

## 9. Freshness and evidence semantics

### 9.1 Timestamp meanings

| Timestamp | Meaning | Must not mean |
|---|---|---|
| Per-operation `provenance.retrieved_at` | Original accepted provider-operation retrieval time | Cache read time or verification time |
| Bundle `retrieved_at` | Latest attempted operation retrieval time under current bundle invariant | Freshness anchor for every operation |
| `provider_effective_at` | Optional provider-declared effective/as-of time only when authoritative and validated | Backend retrieval time inferred under a new name |
| Cache `written_at` | When a validated complete snapshot was inserted/replaced | When provider data became effective or newly retrieved |
| Case `bound_to_case_at` | When this case copied/used the snapshot | Provider retrieval or re-verification |
| Freshness-policy fingerprint/version | Exact rule used for the eligibility decision | Sponsor confirmation or permanent policy |

### 9.2 Eligibility rule

For the recommended fixed-duration POC rule:

```text
freshness_anchor = minimum(all four operation provenance retrieval times)
expires_at       = freshness_anchor + approved fixed UTC duration
eligible         = evaluation_now < expires_at
stale            = evaluation_now >= expires_at
```

The exact boundary is therefore exclusive: an entry is stale at the expiry instant.
“90 days” means 90 elapsed 24-hour periods only if O-16-02 approves that candidate. It
must never be described as three calendar months. If the owner chooses calendar months,
the plan must be revised to define end-of-month and leap-year behavior before code.

### 9.3 Invalid time and evidence handling

- All times remain timezone-aware UTC.
- A missing operation provenance, malformed timestamp, incomplete operation, provider/
  environment mismatch, or bundle/key mismatch is invalid and cannot be a hit.
- An entry whose freshness anchor or write time is in the future relative to the
  injected evaluation clock fails closed as `REGISTRY_CACHE_INVALID`. Do not silently
  add an unapproved clock-skew tolerance.
- A backward wall-clock change that makes persisted evidence appear future also fails
  closed. Tests use an injected mutable UTC clock; no sleep is primary proof.
- The current Mock provider supplies no provider-effective time. Leave it absent.
- Refreshing the shared snapshot never updates an existing case. An existing case can be
  reconsidered only by a separately designed re-onboarding/reassessment workflow.

### 9.4 Freshness versus retention and scheduling

- Freshness decides eligibility for reuse.
- Retention decides how long bytes/normalized evidence remain stored.
- Expiry does not delete an entry.
- Request-triggered refresh occurs only while creating a new eligible case after a stale
  miss.
- No scheduled refresh, background worker, OCDD, periodic KYC, perpetual-KYC, TTL index,
  or purge job is authorized.

## 10. Failure, concurrency, and recovery decision table

| Situation | Recommended result | Durable effects / retained evidence | Error or blocker | Retry/resume and downstream activity |
|---|---|---|---|---|
| Valid eligible hit | Revalidate entry/key/policy, deep-copy bundle, bind case as `CACHE_HIT`. | New case retains immutable bundle and use binding; shared entry unchanged. | None. | Registry provider calls `0`; normal document/ownership/target stages remain unchanged when later inputs permit. |
| Miss | Run existing ordered four-operation acquisition. Cache only a complete bundle, then bind case as `PROVIDER_FETCH`. | Complete entry inserted revision 0; case gets its own copy. | Existing not-found/partial/failure semantics. | One call per reached registry operation; no IDP/ownership/target during case creation. |
| Stale entry | Keep old entry while fetching. On complete success CAS-replace it and bind the new case to the new revision. | Old entry is replaced only after complete success. Existing cases unchanged. | Provider/cache errors are safe technical failure. | Never serve stale; later new-case retry may try again. |
| Forced refresh | Excluded from core. If later approved, treat like stale even when eligible and serialize by the same key. | Replace only after complete success; existing cases unchanged. | Unauthorized request is 403; unsupported request field remains rejected while extension absent. | Director-only new-case request if approved; no existing-case refresh. |
| Invalid/corrupt entry | Fail closed; do not call provider or delete/repair entry in that request. | Corrupt entry retained for controlled diagnosis; no case readiness. | `REGISTRY_CACHE_INVALID`, sanitized. | Requires an authorized remediation path; ordinary retry repeats failure until data is repaired outside this phase. |
| Partial provider result | Preserve current new-case partial bundle/review outcome; do not insert/replace cache. | Previous shared entry, including stale entry, remains unchanged. | Existing `REGISTRY_EXPECTED_DATA_MISSING`. | Provider prefix as current; IDP/ownership/target `0`. |
| Provider timeout/unavailable/malformed | Preserve current sanitized technical behavior; never use stale. | Existing shared entry unchanged; case retains only evidence the existing provider path currently retains. | Existing safe provider code. | Later new-case retry; downstream `0`. |
| Cache read failure | Fail case safely before provider call. | No cache mutation and no false case readiness. | `REGISTRY_CACHE_READ_FAILED`. | Provider/IDP/ownership/target `0`; no memory fallback in Mongo mode. |
| Cache write failure after complete fetch | Fail case safely; do not return the uncommitted result as a cache-backed success. | Existing entry unchanged; failed new cache write creates no replacement. | `REGISTRY_CACHE_WRITE_FAILED`. | Four provider operations may already have occurred; downstream `0`; later new-case retry. |
| Concurrent misses, same key, one process | Process-local keyed lock; first fetches/writes, second re-reads and hits. | One entry/revision and two independent case bindings. | None on success. | Four total provider calls (one per operation), not eight. |
| Concurrent refreshes, same key, one process | Same keyed lock; second re-evaluates the first result. | No lost update or mixed bundle. | None on success. | One refresh acquisition. |
| Conflicting CAS from another process/writer | Fail the losing request without retrying or overwriting the winner. | Winning entry remains. | `REGISTRY_CACHE_CONFLICT`. | Later request re-reads. Multi-instance single-flight is not claimed. |
| Process restart, memory mode | Cache is empty. Cases are also process-local as today. | None survives. | None. | Next case is a miss/provider acquisition. |
| Process restart, Mongo mode | Strictly decode/index cache entries at startup; valid entry may be reused. | Cache and case envelopes survive independently. | Invalid schema/data or unavailable Mongo fails closed. | Hit causes zero provider calls; no target replay. |
| Case deletion | Delete only case-owned state as today. | Shared snapshot remains under O-16-04; other case bindings remain immutable. | Existing deletion result. | No Registry/IDP/ownership/target call; no cache invalidation. |
| Establishment rollback after cache write | Roll back the failed case aggregate only. | Valid shared snapshot remains because it is not case-owned. | Original establishment error. | Later case may reuse it if still eligible. |
| Wrong provider/environment/schema/dataset adjacent entry | Exact key lookup misses and fetches current provider. | Adjacent entry unchanged. | None unless repository returns it for the wrong key. | Current provider called once per reached operation. |
| Repository returns an entry inconsistent with requested key | Treat as corruption, not a miss. | Entry unchanged; no case progression. | `REGISTRY_CACHE_INVALID`. | Provider and all downstream calls `0`. |

### 10.1 Single-flight decision

A process-local per-key lock is justified because one cache miss otherwise permits two
simultaneous cases to issue the same four external-boundary calls and race the same
shared entry. This is demonstrated by the required concurrent-miss acceptance case. It
fits the accepted single-process POC and mirrors existing per-case locking.

No distributed lock, Mongo transaction, lease, scheduler, or exactly-once claim is
justified. Across multiple processes, duplicate provider calls remain possible; strict
unique identity and revision CAS prevent data overwrite but do not claim distributed
single-flight.

## 11. Adverse-case and call-count matrix

The numbers below are per new-case creation request unless stated otherwise. IDP,
ownership, and target counts are zero during initial case creation; when a valid case
later receives documents, its existing downstream call behavior remains unchanged.

| Case | Cache reads/writes | Entity | Officers | Ownership parties | Relationships | IDP / ownership / target during create | Expected case result |
|---|---:|---:|---:|---:|---:|---:|---|
| Unresolved jurisdiction | 0 / 0 | 0 | 0 | 0 | 0 | 0 / 0 / 0 | Review at Registry |
| Conflicting SG/foreign observations | 0 / 0 | 0 | 0 | 0 | 0 | 0 / 0 / 0 | Review at Registry |
| Recognized foreign jurisdiction | 0 / 0 | 0 | 0 | 0 | 0 | 0 / 0 / 0 | Provider not implemented |
| Resolved SG, ineligible identifier | 0 / 0 | 0 | 0 | 0 | 0 | 0 / 0 / 0 | Identifier not eligible |
| Fresh valid hit | 1 / 0 | 0 | 0 | 0 | 0 | 0 / 0 / 0 | Validated / pending documents |
| Miss, complete provider result | 1 / 1 | 1 | 1 | 1 | 1 | 0 / 0 / 0 | Validated / pending documents |
| Stale, complete refresh | 1 / 1 CAS | 1 | 1 | 1 | 1 | 0 / 0 / 0 | Validated with new binding |
| Approved forced refresh, complete | 1 / 1 CAS | 1 | 1 | 1 | 1 | 0 / 0 / 0 | Validated with `FORCED_REFRESH` binding |
| Entity not found | 1 / 0 | 1 | 0 | 0 | 0 | 0 / 0 / 0 | Existing not-found failure |
| Officer operation failure | 1 / 0 | 1 | 1 | 0 | 0 | 0 / 0 / 0 | Technical failure; later operations not attempted |
| Ownership operation failure | 1 / 0 | 1 | 1 | 1 | 0 | 0 / 0 / 0 | Technical failure; relationship not attempted |
| Relationship operation failure | 1 / 0 | 1 | 1 | 1 | 1 | 0 / 0 / 0 | Technical failure |
| Missing ownership evidence / partial | 1 / 0 | 1 | 1 | 1 | 1 | 0 / 0 / 0 | Review required; no cache write |
| Cache read failure | 1 failed / 0 | 0 | 0 | 0 | 0 | 0 / 0 / 0 | Technical failure |
| Cache write failure | 1 / 1 failed | 1 | 1 | 1 | 1 | 0 / 0 / 0 | Technical failure; no false readiness |
| Corrupt returned entry | 1 / 0 | 0 | 0 | 0 | 0 | 0 / 0 / 0 | Technical failure |
| Two concurrent misses, one process | 2+ / 1 | 1 total | 1 total | 1 total | 1 total | 0 / 0 / 0 | Both cases bind independent copies |
| Fresh hit followed by normal completed journey | 1 / 0 | 0 | 0 | 0 | 0 | Existing IDP count per document / one existing ownership analysis / search-shell-policy-amend once | Same accepted Mock terminal behavior |
| Failed refresh of stale entry | 1 / 0 | Ordered provider prefix only | Ordered | Ordered | Ordered | 0 / 0 / 0 | Technical/review result; stale entry retained but not served |

The test suite must assert target call counts remain exactly owned by the target ledger;
cache tests must not reproduce target replay logic inside the new coordinator.

## 12. Exact proposed implementation files and symbols

The implementer must re-check `origin/main` and file ownership before writing. At this
baseline the smallest file map is:

### 12.1 Owner/authority records first

| File | Proposed change |
|---|---|
| `docs/sponsor-questions/OPEN_QUESTIONS.md` | Add Q-019 at the next free ID if the four owner decisions are not supplied as durable authority: cache reuse, duration/unit, sharing, retention/invalidation, forced-refresh roles, and live-provider licensing/storage. Do not mark it sponsor-confirmed. |
| `docs/decisions/DECISION_LOG.md` | After owner approval, add one provisional project decision recording only the approved Mock POC choices and their non-production status. |
| `docs/decisions/ADR-002_REGISTRY_SNAPSHOT_CACHE.md` | At this baseline ADR-002 is the next ID; re-check before creation. Record the new coordinator/repository owner, separate schemas, no cross-collection transaction, single-process single-flight, CAS, failure behavior, compatibility, and rejected designs. |
| `docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md` | Define the exact key, complete-bundle-only rule, timestamp semantics, expiry comparator, error codes, retention distinction, and provider-mode restrictions. |
| `docs/contracts/README.md` | Link the accepted profile without calling it sponsor policy. |

### 12.2 Domain, configuration, and provider identity

| File / symbol | Proposed change |
|---|---|
| `apps/backend/app/domain/models.py` | Add `RegistryProviderIdentity`, `RegistryCacheKey`, `RegistrySnapshotEntry`, `RegistryFreshnessPolicy`, `RegistryEvidenceDisposition`, and `RegistryEvidenceBinding`; add optional binding to `OnboardingCase`. Keep `RegistryAcquisitionBundle` as the normalized evidence owner. |
| `apps/backend/app/config.py` / `Settings` | Add disabled-by-default Mock cache mode, required bounded fixed-duration seconds when enabled, and bounded Mongo collection name. Validate collisions/fail closed. |
| `apps/backend/app/connectors/registry.py` / `RegistryProvider`, `AcraRegistryProviderAdapter` | Add an explicit optional cache/provider identity descriptor. Preserve routing and all four-operation logic. Direct test adapters without identity bypass caching. |
| `apps/backend/app/connectors/mock_acra.py` | Export only a stable synthetic dataset namespace/version constant if needed; do not move fixture logic or add scenario-selected cache behavior. |

### 12.3 Cache/acquisition owner and persistence adapters

| File / symbol | Proposed change |
|---|---|
| `apps/backend/app/services/registry_cache_repository.py` | Create `RegistrySnapshotRepository` protocol, strict errors, and defensive-copy `InMemoryRegistrySnapshotRepository` with insert-only create and revision-aware replace. |
| `apps/backend/app/services/registry_acquisition.py` | Create `RegistryAcquisitionCoordinator`: keyed process-local lock, post-gate lookup, strict hit validation, freshness decision, existing-provider fetch, complete-only write-through, and case binding result. It must accept an injected UTC clock. |
| `apps/backend/app/persistence/mongo_registry_cache_store.py` | Create strict separate-collection Mongo adapter with deterministic `_id`, schema v1, unique identity/index validation, insert-only create, CAS replace, bounded decode, no upsert/read repair, and sanitized errors. |
| `apps/backend/app/persistence/composition.py` / `PersistenceBundle`, `build_persistence_bundle` | Add the memory/Mongo snapshot repository and shared-client Mongo store; never fall back. Keep cache separate from `MongoCaseStore`. |

### 12.4 Existing workflow integration and case compatibility

| File / symbol | Proposed change |
|---|---|
| `apps/backend/app/services/onboarding.py` / `OnboardingService` and `_create_staged_case_locked` | Inject the coordinator. Invoke it only after current route/identifier gates. Bind its defensive bundle/use metadata before existing complete/partial/failed handling. Map typed cache failures to fixed safe terminal errors. |
| `apps/backend/app/composition.py` / `build_onboarding_service` | Build the provider identity, policy, and coordinator from validated settings and the persistence repository. Keep the existing router and adapter. |
| `apps/backend/app/main.py` / `create_app` | Wire `persistence.registry_snapshots` into `build_onboarding_service`. Do not add cache business logic to route handlers. |
| `apps/backend/app/persistence/models.py` | Bump case envelope to schema v4 and add exact `DurableCaseSnapshotV3` compatibility. V1/V2/V3 reads set binding to `None` in memory without rewrite. |
| `apps/backend/app/persistence/mongo_case_store.py` | Decode schema v1–v4 strictly, preserve identity/CAS/index behavior, and update bounded portfolio projection version acceptance without exposing cache data. |
| `apps/backend/app/api_models.py` | No change in the smallest slice. Existing `retrieved_at` remains original and truthful. A safe cache-use projection is an additive later API/UI integration only if explicitly approved. |
| `apps/backend/app/services/case_deletion.py` | No production change expected. Add tests proving deletion does not delete the shared cache. |

### 12.5 Conditional forced-refresh extension only after authority

If the owner approves Director-only force on new-case creation, the extension must be a
separate reviewable slice touching:

- `apps/backend/app/domain/access.py` for a distinct `REGISTRY_FORCE_REFRESH` capability;
- `apps/backend/app/main.py` request validation and server-side capability enforcement;
- `apps/backend/app/services/zero_touch_orchestration.py`,
  `clm_orchestration.py`, and `onboarding.py` only to carry a typed directive to the
  coordinator;
- shared frontend request/types only after the parallel UI lane is integrated and owns
  that surface.

It must not permit refresh of an existing case and must not reuse `POLICY_MUTATE` as a
convenient substitute.

### 12.6 Tests and physical harness

| File | Proposed coverage/change |
|---|---|
| `apps/backend/tests/test_phase16_registry_cache.py` | Deterministic clock, hit/miss/stale/boundary/future time, key isolation, complete-only, failure, call-count, immutable case binding, deletion independence, and barrier-controlled concurrency tests. |
| `apps/backend/tests/test_phase16_registry_cache_real_mongo.py` | Physical insert/hit/restart/CAS/conflict/invalid-schema/delete-independence/cleanup evidence in a generated Phase 16 database. |
| `apps/backend/tests/test_phase12_persistence.py` | Case schema-v3 compatibility, schema-v4 round trip, unknown/malformed binding rejection, and no read rewrite. |
| `apps/backend/tests/test_phase10_registry_acquisition.py` | Preserve ordered operation and downstream call-stopping expectations with cache disabled; add enabled-mode focused assertions only where ownership fits. |
| `apps/backend/tests/test_phase09_jurisdiction_gateway.py` | Prove every route/identifier blocker makes zero cache and provider calls. |
| `apps/backend/tests/test_onboarding_resilience.py` | Safe cache read/write/conflict error persistence and zero downstream activity. |
| `apps/backend/tests/test_acra_modes.py` | Mock cache mode truth, sandbox cache prohibition, Partial/Dormant labels unchanged. |
| `apps/backend/tests/test_zero_touch_orchestration.py` | Fresh-hit journey reaches the same terminal outcome and target call counts; failed refresh never progresses. |
| `scripts/mongo_test_safety.py` | Explicitly add `p16` to the allowlist and generator; continue rejecting `clm_poc` and arbitrary names. |
| `apps/backend/tests/test_phase13_mongo_test_safety.py` | Prove generated Phase 16 names are accepted and unsafe names rejected. |
| `scripts/run_physical_mongo_tests.py` | Add the Phase 16 physical suite, remove stale hard-coded “four” wording/count, and report `len(PHYSICAL_SUITES)` dynamically. |

### 12.7 Configuration and closeout documentation

| File | Proposed change and timing |
|---|---|
| `docs/integration/CONFIGURATION_REFERENCE.md` | Document disabled/default behavior, Mock-only enablement, fixed duration semantics, collection name, and fail-closed startup. |
| `docs/ARCHITECTURE.md` | Update owner/dependency map only after implementation is accepted; distinguish shared snapshot from case evidence and React Query. |
| `docs/PROJECT_STATE.md` | Update only through closeout after exact independent acceptance/merge; record actual implemented mode and tested revision, not this proposal. |

## 13. Implementation task order and integration boundaries

1. **Authority lock:** record O-16-01 through O-16-04 decisions. If any is declined,
   narrow or stop the dependent slice. Create the ADR/profile/decision entry before
   source code so the new owner and semantics are reviewable.
2. **Domain/config slice:** add strict models and disabled-by-default settings. Verify
   model/key/time/config adverse cases without persistence.
3. **Repository slice:** implement memory and separate Mongo adapters with strict schema,
   identity, insert/update/CAS, no-upsert, no-fallback, and generated-db safety.
4. **Coordinator slice:** add cache decision/single-flight around the existing provider
   interface. Keep the router and adapter unchanged except explicit identity metadata.
5. **Workflow integration slice:** connect the coordinator after current gates and bind
   immutable case evidence. Add schema-v4 compatibility. Preserve current failure,
   reconciliation, ownership, and target behavior.
6. **Adverse/regression slice:** run focused hit/miss/stale/failure/race/restart tests,
   then broad affected suites. Remediate at most two unsuccessful cycles for the same
   design problem before escalating.
7. **Physical Mongo slice:** run the guarded Phase 16 suite only with an authorized URI
   supplied through the existing environment mechanism; generate `clm_p16_<24 hex>`,
   clean only that exact validated database, and prove absence without printing the URI.
8. **Independent review:** fresh reviewer checks the exact implementation diff and reruns
   the required matrix. Implementation self-review is not QG.
9. **Closeout/integration:** after exact `PASS` and authorized publication/integration,
   refresh current architecture/project state. Human owner merges.

### 13.1 Parallel UI lane

- This planner and the recommended core implementation own backend cache/domain/
  persistence files only.
- They must not edit frontend files or the other planner artifact while that lane is
  active.
- `main.py`, shared API models/types, configuration, persistence models, decision logs,
  `ARCHITECTURE.md`, `PROJECT_STATE.md`, CI/tooling, and lockfiles are shared hotspots.
- Integrate in this order: authority/ADR/profile; accepted UI lane; backend Phase 16
  implementation; any separately approved additive cache-use API/type projection;
  combined affected regression; independent QG; closeout context refresh.
- If the UI lane changes onboarding request/response types or `main.py` assumptions,
  re-read current intent and merge by semantics. Do not take ours/theirs wholesale and
  do not rebase shared history.

## 14. Verification plan

### 14.1 Deterministic focused proofs

Use an injected mutable UTC clock and `threading.Barrier`/events for race ordering. Do
not use wall-clock sleeps as primary proof.

Focused acceptance must cover:

- disabled mode preserves one four-operation acquisition per eligible new case;
- unresolved, conflicting, foreign, and ineligible paths make zero cache and provider
  calls;
- exact fresh hit makes zero provider calls and records original retrieval versus use;
- miss/stale refresh calls each reached operation once;
- expiry is fresh one microsecond before and stale exactly at boundary;
- 90 fixed days is not treated as three calendar months in names/docs/tests;
- future/malformed timestamps and incomplete/wrong-provider/wrong-environment/
  wrong-schema/wrong-dataset/wrong-approved-sharing-scope entries fail or miss exactly
  as section 10 specifies;
- partial/failed provider bundles never overwrite a valid entry;
- cache read/write/CAS failure produces no false readiness and no downstream activity;
- a shared refresh cannot change old case bundle, canonical entity, reconciliation,
  ownership, readiness, or target snapshot;
- two concurrent misses under one process produce one provider acquisition and two
  independent case bindings;
- Mongo restart gives a fresh eligible hit with zero provider calls;
- memory restart produces a miss;
- case deletion leaves the shared snapshot and cannot be followed by stale case
  resurrection;
- a completed journey from a cache hit keeps existing IDP/ownership/target call counts;
- stale refresh failure never serves stale or progresses to target;
- cache/provider errors contain no raw payload, endpoint, authorization, URI, or private
  exception detail.

### 14.2 Ordered provider failure proofs

For each operation `i`, prove operations before and including `i` are called once,
operations after `i` are zero, cache write is zero, IDP/ownership/target are zero, and a
pre-existing stale entry remains unchanged. Preserve the existing D-029 distinction:
valid missing expected ownership is `PARTIAL / REVIEW_REQUIRED`; transport/shape errors
are technical failure.

### 14.3 Later commands

Run focused checks first, then the applicable full matrix. Exact test counts are derived
from collection on the tested revision, never copied from historical reports.

```powershell
python -m pytest apps/backend/tests/test_phase16_registry_cache.py -q
python -m pytest apps/backend/tests/test_phase09_jurisdiction_gateway.py apps/backend/tests/test_phase10_registry_acquisition.py apps/backend/tests/test_onboarding_resilience.py apps/backend/tests/test_acra_modes.py -q
python -m pytest apps/backend/tests/test_phase12_persistence.py apps/backend/tests/test_zero_touch_orchestration.py -q
python -m pytest apps/backend/tests -q
python -m ruff check apps/backend/app apps/backend/tests scripts
python -m mypy apps/backend/app
python scripts/check_project_state.py
python scripts/check_architecture.py
python scripts/check_secrets.py
python scripts/run_physical_mongo_tests.py --timeout-seconds 900
```

The physical runner is required only after the Phase 16 suite and allowlist are added.
It must report every collected owned physical test executed with zero failures, errors,
or skips, plus verified cleanup. Missing Mongo infrastructure is a missing-evidence
blocker for durable readiness, not permission to skip or claim memory parity.

If a later approved API/type or frontend change is integrated, install nothing in this
planner run. The integration owner must restore the repository-pinned frontend
dependencies through the authorized workflow and then run focused frontend tests, the
full frontend suite, typecheck, and build.

Before PR readiness, and only in a separately authorized execution/publication run:

```powershell
python scripts/pre_pr_check.py
```

Also complete
`.agents/skills/integration-safe-development/references/PRE_PR_CHECKLIST.md`, compare
latest `origin/main`, and obtain a fresh independent QG on the exact reviewed content.

## 15. API, schema, configuration, and provider effects

| Surface | Smallest-slice effect |
|---|---|
| Public API endpoints/request | None. No forced-refresh flag or route. |
| Public response | None required. Existing original `retrieved_at` remains truthful; internal case binding is persisted. |
| Domain model | Add strict shared-entry/key/policy/use-binding models and optional case binding. |
| Case-envelope schema | v3 -> v4 with exact non-rewriting v1/v2/v3 compatibility. |
| Cache schema | New independent v1 separate collection/repository. |
| Configuration | Disabled-by-default Mock cache, approved fixed duration, separate Mongo collection. |
| Provider connector | No new endpoint/call shape. Add only explicit internal cache identity metadata. |
| Mapping/business rule | No ACRA-to-canonical mapping, source precedence, UBO, reconciliation, readiness, or target change. Freshness is a provisional cache-eligibility rule only. |
| Authorization | None in core. Existing auth/team creation/access gates remain mandatory. Conditional force requires its own capability. |
| Provider status | Mock stays Mock; generic sandbox Partial; BizFile Dormant; no Live claim. |
| Architecture | One new backend cache/acquisition coordinator and one shared repository owner; ADR required. |

## 16. Security and data boundaries

- Cache only normalized validated complete bundles, never raw provider responses,
  headers, tokens, source endpoint URLs, or private error detail.
- The cache has no route, browser query, arbitrary key, team listing, or user-controlled
  provider/schema namespace.
- Existing authentication and `creation_team` checks occur before the acquisition path.
  A cache hit never grants access to another case.
- Shared Mock reuse across teams is still an owner decision because source sharing and
  future live licensing are policy questions, even though the fixture data is synthetic.
- Browser projection continues omitting `registry_source_link`; safe cache-use metadata
  is not exposed in the core slice.
- Wrong-scope/key entries fail closed. A caller cannot choose a URL, provider, module,
  credential, environment, schema version, dataset namespace, or freshness duration.
- Mongo failure never falls back to process memory. Disabled cache mode is explicit
  compatibility behavior, not failure fallback.

## 17. Explicit non-goals

- No live ACRA, BizFile activation, new foreign registry, ACRA+, or sandbox contract
  inference.
- No raw response cache, per-operation cache, mixed bundle, external Redis, distributed
  lock, Mongo transaction, outbox, scheduler, worker, TTL job, OCDD, periodic refresh,
  perpetual KYC, or existing-case reassessment.
- No second router, canonical mapper, ownership engine, authorization owner, workflow
  coordinator, persistence model for cases, or target ledger.
- No source-precedence, fuzzy identity, validation winner, UBO threshold, readiness,
  approval, risk, priority, SLA, or retention-policy invention.
- No frontend React Query change and no assertion that its 45-second cache is Registry
  freshness.
- No update of an existing case after shared-cache refresh.
- No case-delete cascade into shared registry snapshots without separate retention
  authority.
- No Camunda work, dependency installation, external provider/database call, or UI lane
  modification in this planning run.

## 18. Stop conditions

Stop the dependent implementation when:

- O-16-01 through O-16-04 are not explicitly approved or conflict with a newly supplied
  sponsor direction;
- “90 days” and “three calendar months” are treated as interchangeable;
- a cache lookup would occur before auth/team, jurisdiction, route, or identifier gates;
- provider/environment/schema/dataset identity cannot be established before lookup;
- raw provider data or a partial/failed bundle would be stored;
- cache and case evidence cannot remain separate and immutable;
- Mongo implementation would require upsert, silent fallback, read repair, unsafe DB
  cleanup, or `clm_poc` access;
- public forced refresh lacks a distinct capability and explicit role authority;
- a stale entry would be served after failed refresh;
- existing-case reconciliation/ownership/readiness/target state would be rewritten;
- physical Mongo restart/CAS/cleanup evidence is required but unavailable;
- latest-main or the parallel UI lane changes a shared owner in a way that invalidates
  this file map or acceptance contract.

A stop blocks only its dependent lane. It does not block current-source analysis,
Mock-disabled compatibility, unrelated UI rework, or documentation of the unresolved
decision.

## 19. Self-review pressure test

| Challenge | Planner conclusion |
|---|---|
| Stale-data false success | Prevented: stale is never served; refresh failure stops the new case and retains but does not use the old entry. |
| Cross-team disclosure | Core cache has no API and case access remains authoritative. Cross-team Mock reuse is still explicitly owner-gated; sandbox/live reuse is blocked. |
| Mixed provenance | Prevented by complete-bundle-only storage and exact provider/environment/contract/dataset key validation. |
| Mutable per-case evidence | Prevented by defensive deep copy plus immutable use binding; shared refresh never rewrites cases. |
| Duplicate acquisition | Prevented within the accepted single-process POC by keyed single-flight; no distributed exactly-once claim. |
| Failed-refresh target progression | Prevented: any provider/cache failure stops before IDP, ownership, readiness, and target. |
| Test-only assumptions as runtime guarantee | Avoided: injected clocks/barriers prove deterministic logic; direct test adapters without explicit cache identity bypass cache; multi-instance single-flight is explicitly not claimed. |
| Second canonical owner | Avoided: router, adapter, mapper, case evidence, authorization, workflow, ownership, and target ledger remain existing owners. |
| Architecture entropy | Bounded to one coordinator, one repository port, two adapters, one separate Mongo collection, and one ADR. No new dependency. |
| Retention conflated with freshness | Avoided: expiry is ineligibility only; purge/scheduling is excluded. |

**Plan pressure result:** proceed only after the four core owner decisions. The proposed
file boundary is the lowest-entropy design that provides durable memory/Mongo parity
without using case evidence as a cache or pushing policy into connectors/routes.

## 20. Implementable versus externally blocked

### IMPLEMENTABLE AFTER OWNER APPROVAL

After O-16-01 through O-16-04 are durably approved as provisional project choices:

- disabled-by-default, Mock-only complete-bundle cache;
- fixed UTC freshness evaluation and exact expiry boundary;
- separate memory/Mongo repository and cache schema v1;
- case envelope v4 with immutable use binding and v1/v2/v3 read compatibility;
- process-local per-key single-flight and Mongo CAS;
- hit/miss/stale/failure/restart/deletion evidence;
- no public refresh API and no frontend change;
- ADR, contract profile, configuration reference, tests, physical Mongo proof, POC
  regression, and fresh independent QG.

### BLOCKED BY SPECIFIC EXTERNAL AUTHORITY

- Any sandbox/live ACRA caching, storage, endpoint/schema assumption, licensing claim,
  or interoperability proof: Q-012 plus provider/storage authority.
- Production cross-team/user sharing, retention, deletion, audit, encryption-location,
  or cache purge policy: sponsor/privacy/governance authority under Q-013/Q-015 and a
  new explicit cache question.
- Manual forced refresh and role assignment: owner approval plus Q-016-aligned authority;
  a separate backend capability is required.
- Existing-case refresh/reassessment, periodic/scheduled refresh, OCDD, or perpetual KYC:
  sponsor scope, evidence, workflow, retention, and target-boundary authority.
- Three-calendar-month semantics: an explicit policy decision defining calendar
  arithmetic.
- Provider-effective timestamps: an authoritative provider field/contract.

## 21. Execution and review recommendation

- Planning/architecture decision: Sol High is appropriate because this crosses provider,
  persistence, evidence, concurrency, and authority boundaries.
- Implementation: one Sol High writer on a newly authorized feature branch/worktree,
  with no concurrent writer on shared backend/config/persistence files.
- Optional specialists: narrow read-only persistence/security review only if the host
  actually exposes them; no multi-writer implementation.
- Independent QG: a fresh Sol High reviewer for persistence/external-boundary/adverse
  paths. A focused Medium review is insufficient if the final slice includes Mongo
  schema/CAS or forced-refresh authorization.
- Publication/integration: separate role after exact independent `PASS`; no self-approval,
  push, PR, or merge authority is granted by this plan.

## 22. Exact owner decisions and next authorized action

The owner must answer:

1. Approve or reject fresh reuse for **synthetic Mock ACRA only**, with cache disabled by
   default until explicitly configured.
2. Approve a fixed elapsed duration and its exact value. The planner recommends fixed
   seconds; `90 * 24h` is a candidate, not an approved fact. State explicitly whether
   calendar-month behavior is rejected.
3. Approve or reject backend-global cross-case/team/user reuse of synthetic Mock
   snapshots behind normal case access.
4. Approve or reject the bounded retention rule: one current complete entry per exact
   key, successful-refresh replacement only, expiry without deletion, no case-delete
   cascade, no TTL/purge/scheduler.
5. Separately decide whether Director-only forced refresh on **new-case creation** is in
   Phase 16 or deferred. Deferral does not block the core slice.

After decisions 1–4 are recorded, the next authorized action is a fresh implementation
run using this handoff, beginning with baseline revalidation and the ADR/contract profile.
Until then, no runtime cache policy may be adopted.
