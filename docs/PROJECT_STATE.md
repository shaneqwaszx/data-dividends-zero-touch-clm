# Current Project State

This is the concise operational snapshot of what is true in the tracked repository.
It is not a sponsor contract, phase report, or substitute for current source and tests.

## Verification metadata

```json project-state
{
  "schema_version": 1,
  "case_envelope_schema_version": 7,
  "verified_date": "2026-09-29",
  "verified_main_sha": "d23d7b7335ba402b071191821c35e4f5e879ed7c",
  "verification_status": "verified-against-main",
  "providers": {
    "registry": {"name": "ACRA", "mode": "mock", "classification": "MOCK"},
    "registry_api_marketplace_mock": {"name": "ACRA_API_MARKETPLACE_MOCK", "mode": "api_marketplace_mock", "classification": "MOCK"},
    "registry_sandbox": {"name": "ACRA_GENERIC_SANDBOX", "mode": "sandbox", "classification": "PARTIAL"},
    "registry_bizfile": {"name": "ACRA_BIZFILE", "mode": "dormant", "classification": "DORMANT"},
    "idp": {"name": "LOCAL_PDF_TEXT", "mode": "local_pdf_text", "classification": "LOCAL"},
    "idp_fault": {"name": "MOCK_IDP", "mode": "mock", "classification": "MOCK"},
    "ownership": {"name": "DECIMAL_GRAPH_ENGINE", "mode": "local", "classification": "LOCAL"},
    "target": {"name": "GOLDTIER", "mode": "mock", "classification": "MOCK"},
    "target_sandbox": {"name": "GOLDTIER_XPI", "mode": "sandbox", "classification": "PARTIAL"}
  },
  "persistence": {"default": "memory", "supported": ["memory", "mongo"]},
  "identity": {
    "account_source": "bootstrap_repositories",
    "session_store": "process_local",
    "production_sso": "not_implemented"
  },
  "workflow_engine": {"camunda": "not_implemented"},
  "open_sponsor_questions": ["Q-001", "Q-002", "Q-003", "Q-004", "Q-005", "Q-006", "Q-007", "Q-008", "Q-009", "Q-010", "Q-011", "Q-012", "Q-013", "Q-014", "Q-015", "Q-016", "Q-017", "Q-018"]
}
```

`verified_main_sha` identifies the main baseline inspected for this snapshot. Feature
branch HEADs are not expected to equal it. The snapshot becomes stale when accepted
main behavior changes without a closeout refresh, not merely when a feature commit is
created. A later documentation-only closeout commit does not replace the inspected
behavioral baseline. `schema_version` versions this metadata format;
`case_envelope_schema_version` is independently checked against the canonical
persistence constant.

## Current status

The repository is a synthetic, local/sandbox-shaped proof of concept for Singapore
new-to-bank corporate onboarding. The supported happy path can reach
`COMPLETED / MOCK_GOLDTIER_SUBMITTED`; that means the credential-free Mock target path
completed. It does not mean customer approval, compliance approval, legal UBO
determination, Ready-for-Approval, or live interoperability.

Major implemented phases are:

- Phase 01–02: vertical slice, Mock ACRA, strict mapping, safe failure behavior, and a
  generic sandbox-shaped ACRA seam.
- Phase 03–04: bounded document extraction/review and deterministic Decimal ownership
  graph/UBO-candidate analysis.
- Phase 05–08: staged readiness, replay-aware Mock GoldTier execution, zero-touch
  exception/resume, input-driven synthetic evidence, and demo/UAT evidence.
- Phase 09–11: source-aware jurisdiction resolution, Singapore registry routing,
  expanded Mock acquisition, and source-neutral reconciliation.
- Pre-Phase 12 and Phase 12: multi-document workspace plus explicit memory/Mongo
  durable POC persistence and restart recovery.
- Phase 13–14: local authentication/RBAC/team priority, dashboard/portfolio read model,
  permanent authorized deletion, and session-memory React Query caching.
- Phase 14.5: repository-backed synthetic team/profile administration, typed policy
  catalogue, and immutable per-case policy snapshots.
- Phase 15A: authority-labelled evidence terminology and future-policy boundaries,
  without adding runtime ageing, supplied-risk, or production-handoff behavior.
- Phase 15B: current-evidence-only review mutation, fail-closed reviewed-value
  reconciliation, partial-review blocking, failed-replacement reupload recovery, and
  bounded repeat/resume recovery under the existing target no-replay ledger.
- Development tooling: repository-only Playwright, guarded browser-network, physical
  Mongo, read-only GitHub PR/CI, and Windows lifecycle verification support. This is
  development infrastructure, not business or product functionality.
- Phase 15C: React Router URL navigation, deep-link/history-safe case identity, stale
  callback isolation, and truthful Vite development history fallback behavior.
- Phase 16 accepted on main: opt-in complete synthetic Mock ACRA snapshot reuse with
  exact-key isolation, fixed elapsed-time freshness, per-case evidence bindings, and
  separate memory/Mongo cache persistence. Disabled mode remains the default.
- The Case Evidence & Explainability Workbench and blocker-aware Attention Queue are
  accepted on main through PR #45. The queue is an authorized current-state portfolio
  projection; it is not a risk score, SLA, assignment engine, or workflow owner.
- Phase 17 Case Activity & Audit Explorer is accepted on main at the inspected
  `94af55ab03391dd6e4a24f6b8db6096d9c56f69b` baseline. It is a bounded live offset
  view of retained automation events only: it has no actor attribution, CSV export,
  retention/archive policy, production compliance-audit claim, or snapshot isolation,
  and case deletion removes the available history.
- Phase 18 Case Portfolio Search & Pagination is accepted on main at the inspected
  `b69fee6f475bfa32160a6d4acb9784edf3f4ff69` baseline. It preserves the legacy array
  endpoint while adding one authorized, bounded, live offset-paged search surface.
- Phase 19 Factual Case Timing is accepted on main at the corrected post-PR49 baseline
  `c2929043968ab540f873ccffa69142380c2da056`. Backend-authored age/duration remains
  factual only. The deterministic injected clock propagates through the canonical
  `ZeroTouchOrchestrator` clock seam, while true chronology violations still fail
  closed. No timing-policy, SLA, escalation, approval, or risk behavior was added.
- The pre-Phase 22 capability checkpoint accepted on main adds a case-bound
  advisory-intelligence owner,
  schema-v5 persistence, typed entity/risk review stops, two synthetic SME scenarios,
  safe intelligence UI, a versioned synthetic evaluation, and bounded authorized CSV
  activity export. It activates no external provider and adds no assignment/SLA owner.
- The same accepted pre-Phase 22 checkpoint adds an explicit GoldTier XPI sandbox lane
  behind the existing connector/mapper/ledger owners. Mock remains the default. XPI is
  `SANDBOX_PARTIAL`, uses a backend-only `user_id` header and TLS-1.3-only bounded
  transport and exposes a safe case request preview. The corrected OpenAPI 1.0.0 owns
  exact KYC/Client Segment vocabularies (17/23). Singapore fixes
  `registrationType=ACRA`, `customerExternalSystem=DSD`, `policy=Singapore`, and
  `bookingEntity=ANZBGL (Singapore Branch)`; KYC type and segment are validated,
  write-once case decisions rather than global defaults. Related-party dispatch remains
  blocked on child-ID lifecycle evidence.
- The final pre-Phase 22 checkpoint accepted on main makes the collection-observed empty
  `accountEntityType` and `productType` values compatible without treating either as
  sponsor vocabulary, and adds one backend-authored safe pipeline projection consumed
  by the optional visual inspector. On 2026-09-27, configured application-connector
  Searches reached the real `anz-nutmeg` XPI sandbox and returned no match, including
  a fresh Search for the official-Mock Garden Singapore identity. No mutation had been
  sent at that checkpoint. The accepted checkpoint adds case-bound classification, fixed
  Singapore policy values, and a strict post-Amend read-back checkpoint; external
  acceptance evidence remains distinct from implementation evidence.
- The accepted checkpoint freezes GoldTier provider identity in the retained CLM
  submission plan. Submission input derives from that plan; the mapper and connector
  are checked only for compatibility before ledger/network activity. Mock/Sandbox drift fails closed,
  and schema-v6 rejects contradictory plan/input/matching-ledger combinations. Exact
  schema-v1 through schema-v5 reads remain supported without rewrite.
- The current main checkpoint moves the first read-only GoldTier Search ahead of
  ACRA bootstrap by retaining bounded initial legal-name/UEN/country identity. Exact
  existing customers reuse only a prior same-ID verified canonical target state and skip
  ACRA/Shell/new-policy creation before same-ID Amend/read-back; no-match cases alone
  acquire ACRA and may later create Shell then Policy; ambiguous candidates stop before
  ACRA and all mutation. Provider-verified recovery retains the
  original uncertain Shell attempt and later exact provider identity as separate durable
  facts; it never represents the recovered ID as a Shell response. Shell, Policy, Amend,
  and read-back remain under the one target ledger and uncertain mutations are not
  automatically replayed.
- In the bounded Garden acceptance on 2026-09-28, the uncertain Policy attempt was
  provider-verified read-only as one `Singapore / Requested` request on ID `143878` and
  retained without replay. Both Shell and Policy recoveries survived a separate-process
  Mongo reload. Exactly one later Amend was attempted through the ledger; its transport
  result was uncertain, and portal audit showed `Created` followed by `Valdiation Failed`.
  The same ledger now durably retains that later evidence as
  `PROVIDER_VERIFIED_FAILURE / PROVIDER_VALIDATION_FAILED`, with the original uncertain
  transport chronology and `replayed=false`; Amend remains non-complete and non-resolved.
  The reconstructed request contained only `goldTierId=143878` and `policy=Singapore`.
  Portal detail exposed no failed field or rule, so diagnosis is
  `E. INSUFFICIENT_EVIDENCE`. No second Garden external onboarding, successful same-ID
  read-back, Live claim, or final acceptance PASS follows from this evidence.
- The main demo document now defaults to the project-defined COI profile: legal name,
  registration number, and jurisdiction are required, while address is optional and
  remains Registry evidence if absent. The target catalogue preserves the fixed SG POC
  values, exact current vocabularies, case-bound KYC/segment decisions, and
  empty-compatible optional account/product fields.
- HR alone has `PROVIDER_SANDBOX_TEST` and still has no `CASE_ACCESS`. The HR console
  exposes safe GoldTier status, bounded read-only Search, offline request preview/dry
  run, and a process-local safe timeline. Standalone writes are blocked by the existing
  case-ledger boundary; related-party dispatch remains blocked on child-ID lifecycle.
- The backend-authored pipeline inspector now ends with an explicit unresolved human-
  approval boundary after technical completion. Its technical event table renders only
  fixed event codes/types, never retained free-text event messages.
- The official ACRA API Marketplace Mock has the explicit opt-in mode
  `api_marketplace_mock`, distinct from local `mock` and generic `sandbox`. Authorized
  bounded Mock observations prove the exact token response shape plus strict entity and
  shareholder interoperability for approved Mock identities. Tokens remain memory-only,
  the downstream header is raw `token`, and there is no fallback. Garden shareholders
  were explicitly empty and no compatible ownership denominator was established, so
  relationship acquisition remains partial and stops truthfully. Q-012 remains open;
  this lane is Mock, not Sandbox or Live.
- PR #62 is accepted on main. Director team selection is explicit and blank by default,
  with no silent Alpha/Beta fallback; Director/RM deletion remains backend-authorized.
  GoldTier Search `NO_MATCH` remains the normal new-customer path, while ambiguous
  Search retains the case/evidence and blocks target mutation. Technical Search failure
  remains distinct from customer absence: safe independent ACRA, document,
  reconciliation, and ownership evidence may continue, but unresolved Search produces
  zero Shell/Policy/Amend calls. Pipeline statuses distinguish `FAILED`, `BLOCKED`,
  `NOT_REACHED`, and `REVIEW_REQUIRED`; the current blocker follows workflow order, and
  problem-stage controls navigate to their real diagnostic or resolution owners.
  D-060 and the ADR-006 amendment govern the failed-Search evidence continuation.
  These operator-recovery controls do not make all ordinary blockers user-resolvable
  and do not add a late Search retry, editable final review, or pre-write GoldTier
  confirmation.

The 2026-09-29 working candidate on
`feat/recoverable-onboarding-final-review` implements the bounded D-061 package on top
of that accepted main baseline. It adds same-case identity correction and read-only
Search recheck; independent evidence continuation for ambiguous as well as failed
Search; fixed D-056 policy rebind; pre-confirm KYC/segment editing; reviewed local
manual economic-interest evidence; versioned explanatory blocker-decision metadata;
and an exact server-authored final review whose durable confirmation is enforced under
lock before every target write path. HR gains a read-only ACRA diagnostic surface using
the same composed connector and no case access. This is an implementation candidate
pending an independent quality gate, not an accepted-main, provider-write, Live,
approval, or sponsor-policy claim.
The working candidate's final review includes legal form, owning team, and section-level
routes to the existing identity, classification, and document owners. It routes to the
manual-ownership evidence owner only when the server's typed recovery projection
authorizes `MANUAL_OWNERSHIP_EVIDENCE`; otherwise it truthfully labels ownership as
review-only. Before confirmation, identity correction remains same-case and
backend-validated; it cancels stale confirmation state, performs only a read-only Search
recheck, and invalidates dependent evidence. Confirmed or submitted projections cannot
expose those edit actions.

Post-merge main CI run `36452914032` for this SHA passed on its second attempt. The
initial Windows demo-lifecycle attempt failed because local lifecycle ports were
already occupied; after the ports were freed, the exact local 23/23 lifecycle suite
passed and the GitHub rerun passed all six jobs: backend, frontend, e2e, security,
phase12-mongo, and demo-lifecycle-windows. The first failure is retained as a
transient environment incident, not a product defect.

Phase 20 Sponsor Policy Authority Gate is accepted on main at
`5039c7e548dfae1eeb8ad600f128ef374e3a6f2a`. D-009 confirms only that human exception
review is allowed/expected; reviewer role, four-eyes/separation, dispositions,
retention, approval, and other policy details remain unresolved. No runtime business
policy was activated. The policy-authority registry and checker remain authoritative.
Q-001 through Q-018 remain open. Phase 21 External Integration Activation Readiness is
accepted on main at `ef338c9b7926a298e8987acb975fd93c96ed2bfb`. It adds strict provider-
readiness and sanitized-evidence governance, CI/tooling checks, an activation packet,
and a secret-security runbook. It activates no provider and changes no connector,
composition, API, persistence, frontend, target-ledger, RBAC, mapping, auth, or runtime
business-policy behavior. Generic ACRA remains Partial, BizFile remains Dormant, and
PingFed/production GoldTier remain Not Implemented. The later accepted XPI adapter is a
separate sponsor sandbox lane only; it does not alter Phase 21's Live-readiness result.

The Case Evidence & Explainability Workbench accepted through PR #43 adds a read-only
presentation of the minimized nullable Mock-only registry-binding projection,
backend-authored Decimal ownership paths, and typed workflow, blocker, readiness, and
target-ledger state. Original registry operation provenance remains distinct from
case-use metadata, and a missing binding remains unknown/unrecorded rather than proving
a miss, disabled cache, provider fetch, freshness, or current validity. Exploration
does not rerun a provider, ownership analysis, workflow operation, or target operation.

Existing authorization, review/recovery, query, navigation, ownership-calculation, and
target-ledger owners remain authoritative. Cache remains disabled by default, and the
workbench changes neither cache policy nor persistence schema. It adds no approval,
compliance/risk, legal UBO, production, Live-provider, or sponsor-policy claim. Guarded
browser acceptance ran with cache disabled; provider-fetch and cache-hit projections
were covered through backend/API and frontend contract evidence. The manual demo
instructions are not executed acceptance evidence.

## Current runtime pipeline

```text
authenticated browser/API request
  -> current process-local session, profile, team and capabilities
  -> backend authorization and creation/portfolio scope
  -> immutable case policy snapshot
  -> bounded initial identity plus jurisdiction observations and resolver
  -> early read-only GoldTier Search
     -> exact verified prior target: hydrate existing state; skip ACRA/Shell/new Policy
     -> no match: closed SG registry router and optional exact-key Mock cache
        -> configured synthetic Mock, official API Marketplace Mock, or generic sandbox-shaped acquisition
        -> canonical legal entity and normalized registry evidence
     -> ambiguous: retain case documents/evidence while customer identity stays under
        review; stop before ACRA and every target mutation
     -> technical Search failure: retain case and continue independent ACRA, document,
        reconciliation, and ownership evidence; target identity remains unresolved,
        then terminate at the Search blocker with no Shell/Policy/Amend mutation
  -> bounded document intake and local deterministic extraction
  -> source-neutral reconciliation and review/resume where required
  -> registry-fed deterministic Decimal ownership graph analysis
  -> versioned advisory entity resolution, UBO assistance, and mock risk
  -> readiness and immutable target snapshot
  -> incremental GoldTier Mock-default or explicit XPI-sandbox target checkpoints:
     Shell/Policy/Amend for new customers, Amend for exact existing customers, then
     same-ID read-back, all with the same retained no-replay recovery ledger
  -> authorized bounded case portfolio/dashboard/activity and detailed evidence views
```

Technical composition is centered in `apps/backend/app/main.py`,
`apps/backend/app/composition.py`, and `apps/backend/app/persistence/composition.py`.
Business behavior stays in domain/services; adapters stay at connector/persistence
boundaries.

## Current External Integration Truth

| Boundary | Active/default | Other implemented seam | Classification | What is proved |
|---|---|---|---|---|
| ACRA | `mock` | generic `sandbox` connector | Mock active; sandbox partial | Synthetic ACRA-shaped behavior and adapter isolation |
| ACRA API Marketplace Mock | explicit opt-in | fixed official Mock token/entity/shareholder transport with no fallback | Mock / Observed interoperability | Authorized token plus strict entity/shareholder success; Garden shareholders empty; no ownership-percentage authority and not Live |
| Registry cache | disabled | opt-in synthetic Mock only | Project-defined POC | Complete normalized Mock snapshots under exact identity and fixed elapsed-time freshness |
| ACRA BizFile | none | module exists but is not composed | Dormant | Focused adapter code/tests only, not runtime availability |
| IDP/OCR | `local_pdf_text` | Mock fault/demo provider | Local POC / Mock | Deterministic extraction from supported synthetic documents |
| Ownership | registry evidence into local engine | Mock fault/demo provider | Local / Mock support | Deterministic Decimal graph analysis, not an external service |
| GoldTier | `mock` default | XPI `sandbox` mode | Mock active; sandbox partial | Ordered target behavior through one retained recovery ledger |
| GoldTier XPI sandbox | none | explicit `sandbox` mode | Partial | Supplied-route Search/customer mutation adapter, early Search orchestration, strict safe projection, target-policy blocking, and no-replay semantics; one bounded Garden sequence recovered Shell/Policy without replay and retained a failed Amend validation, but no successful customer lifecycle/read-back or Live interoperability is proved |
| PingFed | none | future placeholders only | Not implemented | No token retrieval or authenticated target connection |
| MongoDB | memory by default | explicit `mongo` mode | Optional local infrastructure | Single-instance durable POC behavior when configured |
| Camunda | none | none | Not implemented | No runtime workflow-engine integration |
| Production IdP/SSO | none | local bootstrap identities | Local POC | Process-local opaque sessions and backend RBAC |

No row classified Mock, Local, Partial, Dormant, or Not implemented may be presented as
Live. Tool or credential availability alone would not change this classification;
authorized contract and execution evidence are required.

## Evidence authority labels

- **Observed:** source, tests, configuration, or composition directly establish it.
- **Project-defined / provisional:** implemented POC behavior recorded in contracts or
  decisions, pending sponsor confirmation.
- **Sponsor-confirmed:** a direct sponsor clarification recorded in the decision log.
- **Unknown / blocked:** the sponsor/API owner has not supplied sufficient authority or
  usable access evidence.

The provider matrix above is Observed. The official ACRA Mock `401` is only
`OFFICIAL_MOCK_OBSERVED` failure evidence. Thresholds, role behavior, policy defaults,
reconciliation actions, and deletion governance are mostly project-defined/provisional.
GoldTier amend path, first-level related-party limit, lack of hierarchy creation,
PingFed target, TLS 1.3 requirement, ACRA proof labeling, and UTC sourcing guidance have
recorded sponsor confirmation. The XPI `user_id` sandbox header is artefact-observed,
not PingFed or production authentication. Live ACRA/GoldTier binding and production policy remain
unknown or blocked.

## Persistence modes

- `memory` is the default. State and sessions are process-local and a backend restart
  clears them.
- `mongo` is explicit. Missing/invalid configuration, startup validation, reads, or
  writes fail closed and never fall back to memory.
- One schema-versioned case envelope (working-candidate schema v7) owns durable case
  state. Strict v1/v2/v3/v4/v5/v6 reads preserve absent historical fields, including v4
  `intelligence = null`, without a read-only persistence rewrite. Automation records
  persist a separate stage-order version: a missing value is the pre-Search v1 order,
  while newly authored records use v2. A safe non-terminal v1 continuation is rebased in
  one CAS mutation to the earliest unproved v2 stage and must actually execute Search;
  it is never labelled Search-complete during decode or recovery. Historical terminal
  outcomes remain terminal, while historical in-flight target attempts remain uncertain
  and non-replayable. Early Search and incremental ledger fields therefore remain
  explicit schema-v6 fields without hiding the stage-order semantic change. Schema v6
  adds bounded initial identity/Search evidence, existing-target provenance, lifecycle-
  resolved operation markers, provider-verified recovery evidence, and an optional
  provider-verified Amend-failure fact. Schema v7 adds bounded correction/recheck,
  policy-rebind, manual-ownership, blocker-decision, and target-confirmation facts; it
  does not add another repository, policy, authorization, or mutation owner.
  Repository adapters preserve revision compare-and-set, insert-only creation,
  update-only mutation, strict identity binding, and replay-aware recovery.
- The optional Mock registry cache has a separate schema-v1 repository/collection and
  persists complete normalized synthetic bundles only. It has no cross-collection
  transaction, TTL, deletion cascade, or distributed exactly-once guarantee.
- Global team/profile/policy records use separate bounded repository owners.
- Raw uploads, full extracted text, raw external payloads, credentials, sessions, and
  connection strings are excluded from case envelopes.
- Physical tests use generated allowlisted `clm_p12_*`, `clm_p13_*`, or newer explicitly
  approved disposable names. `clm_poc` is never a physical test/cleanup database. The
  guarded runner owns an explicit suite inventory and reports dynamic collection and
  execution counts. Phase 18 acceptance registered seven suites and its remediated
  candidate evidence executed 27 collected, 27 passed with zero failures, errors, or
  skips. Phase 19 registered an eighth suite for bounded timing projection. Its
  execution counts remain revision-specific evidence in the Phase 19 reports, not a
  future contract.

## Authentication, authorization and administration

- Six synthetic bootstrap identities and repository-backed profiles/teams are used.
- Authentication uses password hashes and opaque process-local sessions; this is not
  production IAM, SSO, or an external identity provider.
- Backend capabilities and case access are authoritative. Frontend visibility is only
  presentational.
- Cross-team and absent case IDs share the same safe 404 behavior.
- Team assignment is canonical server state. Director filters are validated and
  applied by backend query services.
- Sensitive mutations re-authorize within the owning case or repository lock/CAS
  boundary.
- HR administers synthetic profiles/teams and reads policies but has no case access or
  runtime policy mutation authority.

## Major current capabilities

- Controlled Singapore/ACRA routing with no implicit source precedence.
- Four-operation Mock registry acquisition with truthful complete/partial/failure
  evidence and downstream call stopping.
- Optional backend-global reuse of fresh complete synthetic Mock registry snapshots,
  with exact identity isolation and immutable per-case source/cache-use evidence.
- PDF, DOCX and UTF-8 TXT technical intake with strict size/structure handling.
- Deterministic local extraction and field provenance.
- Source-neutral reconciliation with explicit bounded actions and resume, including
  case-scoped comparison against retained prior-case canonical evidence when an exact
  verified existing target is reused and fresh ACRA bootstrap is skipped.
- Deterministic Decimal direct/indirect ownership paths and provisional UBO candidates.
- Immutable per-case IDP/UBO and advisory-intelligence policy snapshot.
- Explainable source-neutral entity resolution, ML-assisted UBO advice, and bounded mock
  advisory risk, all with permanent non-authority labels and synthetic model cards.
- Ordered Mock target execution with no-replay recovery states.
- Working-candidate operator recovery controls: same-case identity correction and
  read-only Search recheck, bounded policy rebind, pre-confirm classification edits,
  reviewed local ownership evidence, truthful decision metadata, and accessible
  problem-stage navigation to the existing owners.
- Working-candidate final review and durable target confirmation, revalidated under the
  case lock before every Shell, Policy, or Amend dispatch. Exact preview/snapshot parity
  includes the stable case-acceptance `sourceContext.acceptedAt`, and all transmitted
  preview fields are digest-bound.
- HR-only safe ACRA status and bounded read-only lookup using the exact composed
  connector, with no case access or provider mutation.
- Memory/Mongo repository parity, case deletion, portfolio projection, dashboard, team
  filtering, priority, retained-event activity, bounded authorized CSV activity export,
  advisory projection persistence, and session-scoped query caching.
- Backend-authored factual case timing is accepted on main: one
  UTC observation per response, deterministic non-negative durations, fail-closed
  chronology, neutral UI labels, and no browser-clock authority or SLA inference.
- Safe synthetic UAT evidence and Windows demo lifecycle tooling.

## Current explicit non-capabilities

- No proven live ACRA, PingFed, GoldTier, external ownership, vendor OCR, production
  SSO/IdP, or Camunda connection.
- No sandbox/live registry caching, production sharing/retention policy, forced refresh,
  existing-case reassessment, background refresh, TTL, or cache administration API.
- No ASIC/Malaysia/Hong Kong registry adapter in active runtime.
- No `createRelationship` or multi-level hierarchy creation through GoldTier.
- No sponsor-approved final UBO, document, source-authority, RBAC, retention, deletion,
  review, or Ready-for-Approval policy.
- No arbitrary blocker override, free-form canonical editing, general provider-recovery
  attestation, automatic Search retry, autonomous approval, or complete human exception
  workbench. The candidate recovery actions are only the explicit typed D-061 paths.
- No autonomous approval, production risk/compliance engine, legal UBO determination, production
  audit repository, distributed workflow, or multi-instance exactly-once guarantee.
- No full analytics/MIS platform or full Exception Workbench.

## Phase 15A sponsor rebaseline (provisional / authority-labelled)

**Observed current implementation:** onboarding starts when a user supplies the
onboarding package: a registration identifier and supporting corporate documents. The
POC processes that supplied package; it does not claim upstream document solicitation
or collection. ACRA is Mock by default, its generic sandbox-shaped seam is partial,
BizFile is dormant, IDP is local deterministic, GoldTier is Mock by default, and the
optional XPI lane is Partial sandbox only. No Live ACRA, Live GoldTier, or Live PingFed
connection is proved.

**Project/sponsor direction and provisional UAT presentation:** LOW/MEDIUM/HIGH as a
supplied-risk direction remains unimplemented. A separate local `MOCK_ADVISORY_RISK`
projection now scores only available POC evidence and is permanently labelled
`NOT_COMPLIANCE_DECISION`; missing signals remain `NOT_ASSESSED`, and readiness blocking
defaults false. This does not answer Q-017. Separately, current manual UAT presents ordering-only case
priority as Low/Medium/High/Unset. The nullable 1–10 API/Mongo field remains compatible:
canonical writes are 1/5/10 and legacy reads map 1–3/4–7/8–10 to the three tiers. This
project-defined presentation has no risk, SLA, routing, escalation, approval, or
regulatory meaning and Q-016 remains open. Synthetic Mock ACRA caching is now optional POC
behavior under owner-approved O-16-01 through O-16-04: the exact fixed interval is
7,776,000 seconds (90 elapsed 24-hour periods). It is not calendar months, an ACRA
validity rule, production policy, or sponsor-confirmed authority.

**Future/KIV and open authority:** there is no ageing/SLA, OCDD, periodic refresh, or
perpetual-KYC runtime. The implemented external Zero-Touch -> Mock GoldTier sequence
is POC architecture only; its production deployment and handoff boundary remain open
pending sponsor authority.

## Phase 15B review/rework stabilization

Review mutations are limited to current evidence; superseded document records remain
historical lineage. Reviewed values enter reconciliation only through the existing
bounded decision rules, with fail-closed evidence, canonical, version, and fingerprint
checks. Partial review remains blocking and cannot silently clear another document,
reconciliation, ownership, or workflow blocker.

A failed replacement remains the current failed record and returns the case to targeted
reupload/retry rather than leaving an active exception bound to superseded evidence.
Explicit repeat/resume paths are bounded and idempotent: they repair supported
interrupted checkpoints or return the current state, while the target ledger remains
the sole owner of target ordering and no-replay behavior. This is monotonic sequential
recoverability for the single-instance POC; it is not distributed transaction
atomicity, exactly-once execution, final reviewer assignment, source precedence, or
final approval.

## Repository and development tooling

The repository includes an exact-pinned Playwright Chromium E2E harness with guarded
browser network policy, an explicit guarded physical-Mongo suite inventory with dynamic
counts,
read-only GitHub PR/CI inspection tooling, and hardened Windows demo lifecycle
verification. These capabilities support local development, CI, and verification;
they do not add a product workflow, business capability, Live provider integration, or
sponsor-approved behavior.

## Phase 15C frontend URL navigation

The frontend uses exact `react-router` 7.18.4 in declarative `BrowserRouter` mode.
Browser location is the sole page and case-navigation identity, and `NavLink`/`Link`
navigation supports direct links, refresh, new-tab links, and browser Back/Forward
without making route entry a business mutation. Case detail actions are isolated by
case/action generation so a stale action from a previously displayed case cannot be
published against the current route. Retained-intake callbacks use the same generation
principle so stale work from an earlier intake cannot alter a later intake identity.

Local development uses Vite 7.1.11 with `appType: "mpa"` and Vite-first request
handling. Only a positively admitted unresolved document-navigation request may receive
the SPA entry document; API requests, existing or missing resources/file requests, and
unsafe methods retain truthful Vite/proxy/not-found/method behavior. Equivalent
production-host history fallback remains unverified and outside Phase 15C scope.

## Current open sponsor blockers

- Q-012 is partially resolved for official Mock request-side token facts; it still
  blocks authoritative/live ACRA binding, successful operation and token-response
  schemas, downstream token semantics, access/secret delivery, errors, rate/retry
  limits, TLS/mTLS/private-CA requirements, related operations, and sandbox proof.
- Q-008/D-018 blocks real GoldTier/PingFed authentication material and containment.
- Q-001/Q-002/Q-006/Q-007 block Ready-for-Approval, hierarchy retrieval, related-party
  semantics, and final Singapore target mappings.
- Q-003/Q-005/Q-013/Q-014/Q-015 block final document scope, validation/source authority,
  privacy/retention, confidence/reviewer policy, and jurisdiction/reconciliation authority.
- Q-004 blocks final legal UBO threshold/control policy.
- Q-016 blocks production identity, role, assignment, prioritization, and admin policy.
- Q-017 blocks supplied LOW/MEDIUM/HIGH risk input authority: its producer/source,
  validation/provenance, update authority, workflow reactions, EDD/approval, and
  readiness-blocking semantics remain unresolved. The local mock advisory score is a
  project-defined demonstration and not the supplied risk input requested by Q-017.
- Q-018 blocks the production Zero-Touch / GoldTier deployment and handoff boundary.
  The current external Zero-Touch -> Mock GoldTier sequence is POC architecture; its
  production placement (external versus inside/alongside GoldTier), handoff point,
  transferred state/evidence, and ownership remain unresolved.
- Q-009/Q-010/Q-011 retain contract value/mandatory-field/corrected-artefact questions.

Consult `docs/sponsor-questions/OPEN_QUESTIONS.md` for exact wording and current status.

## Current architectural debt

- `apps/backend/app/main.py` and `apps/frontend/src/App.tsx` are composition hot spots.
- Historical phase documents repeat current-state claims and may be stale; this file and
  current source now provide the short operational route.
- `ownership_connector_mode` remains Mock-named configuration while normal ownership
  uses registry evidence and the local engine; future change must reconcile rather than
  add another engine.
- Generic ACRA sandbox behavior is only partial for expanded operations; BizFile remains
  intentionally dormant.
- Mongo and administration atomicity are single-process POC guarantees, not distributed
  guarantees.
- Production-scale portfolio/activity indexing, snapshot traversal, retention/archive,
  and broader performance work remain intentionally deferred.

## Next candidate work packages

These are candidates, not authorization to implement:

1. **Recoverable onboarding + final review/confirmation independent quality gate and
   bounded remediation.** The D-061 implementation is a working candidate, not accepted
   main. Official-Mock demo-pack completeness remains evidence-dependent: no absent
   supplied fixture, screenshot, declaration, README, or validation artefact may be
   invented.
2. Sponsor contract/access reconciliation for ACRA and GoldTier/PingFed.
3. Sponsor-confirmed Ready-for-Approval/reviewer/retention policy design.
4. Authoritative external-provider work only after contract, security and credential
   prerequisites are satisfied.
5. Camunda runtime integration remains a separate optional, requirements-dependent
   package and is not implemented.
6. Measured hotspot or production-scale portfolio/activity work if evidence shows need.

Every new package requires a bounded planner handoff, change classification, relevant
skill, proportional verification, and independent quality gate.
