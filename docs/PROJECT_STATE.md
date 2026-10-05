# Current Project State

This is the concise operational snapshot of what is true in the tracked repository.
It is not a sponsor contract, phase report, or substitute for current source and tests.

## Verification metadata

The current main source baseline was inspected on 2026-10-05 at
`4ee8819d7404d6442e064fd60dcee03ccc84cf11` (merged PR #70, Phase25/26 POC hardening and sponsor demo readiness).
PR #68 and PR #69 evidence retains its original tested/reviewed identity. The earlier
[combined FAIL](../.ai-pipeline/reports/ONBOARDING_INTELLIGENCE_FINAL_QUALITY_GATE.md)
is historical; the separately authorized
[P2 remediation PASS](../.ai-pipeline/reports/ONBOARDING_INTELLIGENCE_P2_REMEDIATION_QUALITY_GATE.md)
closed its two findings before the human merge. That narrow PASS does not replace
the historical whole-program verdict.

Phase 25 independently passed post-merge validation on the exact PR #69 source tree.
Three retained original `clm_poc` cases (schemas 2, 2 and 8) decoded without writes.
An exact disposable clone then supported normal composition, authenticated HTTP and
actual frontend inspection of all three cases, plus RM/Director/HR session checks.
Original collection counts, raw document fingerprints and index metadata were unchanged
before/after; the clone was deleted after review. Original data was read, never mutated.
This is bounded compatibility evidence, not a newly executed full main suite or legal
approval. See the [Phase 26 implementation record](../.ai-pipeline/reports/PHASE_26_IMPLEMENTATION.md)
for current program evidence and the [Phase 27 handoff](PHASE_27_HANDOFF.md).


PR #65 was human squash-merged on 2026-10-01 at
`4a206a3a3c4c91b06cec99e26a44016a74d8d2ce`. Its inspected tree
`01bd239ee8dcd05ca663e9aaadfe6518c3c4940e` exactly matches the accepted
feature head `6c8fecbc96254ddf70109ab174ffc011c9bd2fe5`. The previously
uncommitted zero-touch remediation is now accepted on main, including clean-field
automatic confirmation, exception-driven interventions, Garden LOCAL ownership
recovery, active/history projections, revision guards and bounded E2E orchestration.
Acceptance is POC Mock/Local/Partial evidence, not sponsor or Live approval.

Accepted pre-merge PR run
[36852119580](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/actions/runs/36852119580)
passed all six lanes. Its identical-tree browser execution completed 26 selectors /
27 tests; disposable mongo:7 execution completed nine suites / 38 passed / zero
skips. These are attributed to the PR head and merge-preview tree, not presented as
a newly executed post-merge runtime suite. Local post-merge governance inspection
establishes the main baseline below; no provider/database operation was required.

Historical verification provenance is retained: the preceding snapshot was inspected
on 2026-09-29 against main `d23d7b7335ba402b071191821c35e4f5e879ed7c`.
Earlier phase/closeout reports and provider classifications remain unchanged.

```json project-state
{
  "schema_version": 1,
  "case_envelope_schema_version": 9,
  "verified_date": "2026-10-05",
  "verified_main_sha": "4ee8819d7404d6442e064fd60dcee03ccc84cf11",
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
persistence constant. Current inspected main uses schema9 and strictly reads valid
legacy schemas1..8 without read-time rewrite. Historical tests and independent gates
remain tied to their recorded content; Phase 25 and Phase 26 have separate evidence.

## Current status

### PR #70 merged; Phase27A independently accepted; Phase27 closeout branch

Phase25/26 is complete and merged through PR #70. The PR #69-to-#70 diff is
16 documentation/evidence files only; product behavior, schema9, provider modes,
configuration and canonical owners are unchanged. The historical
[final independent PASS](../.ai-pipeline/reports/PHASE_25_26_FINAL_QUALITY_GATE.md)
remains bound to its recorded candidate, rather than becoming a Phase27 verdict.

The explicitly assigned Phase27 is on `feat/phase27-final-delivery-closeout` from
this inspected main baseline. Its [truth inventory](demo/PHASE_27_TRUTH_INVENTORY.md)
and [manual checklist](demo/PHASE_27_MANUAL_UAT_CHECKLIST.md) distinguish current
source, newly executed automated pre-UAT and agent UI outcomes (16 PASS/0 FAIL/5
NOT_RUN; HUMAN_EXECUTED0). Two bounded presentation defects were fixed/retested;
Phase27A has [fresh independent exact PASS](../.ai-pipeline/reports/PHASE_27A_RECHECK_QUALITY_GATE.md)
with P0/P1/P2=0/0/0 after bounded encoding repair. Owner-assigned27B synchronizes
current architecture/demo/limitations/questions and the
[final project closeout](FINAL_PROJECT_CLOSEOUT.md). The two UI fixes are accepted
branch content pending merge, not newly merged main behavior.27B/27C/final gate
and local commits retain their own evidence/barriers.
[BarrierB exact PASS](../.ai-pipeline/reports/PHASE_27B_QUALITY_GATE.md) accepted the
documentation; [27C](../.ai-pipeline/reports/PHASE_27C_REGRESSION.md) passed135 affected
backend,505 frontend and the required lint/type/build/contracts/governance/browser
checks. Final independent closeout acceptance and authorized local commits remain
separate from this pre-final candidate checkpoint.
No sponsor question or provider classification changes through this metadata sync.

### PR #69 merged — onboarding intelligence and Sandbox submission

The three-session program from `feat/onboarding-intelligence-goldtier-sandbox` is
included in inspected main through PR #69. Its historical gates remain distinct. The [bounded planner](../.ai-pipeline/001_planner/ONBOARDING_INTELLIGENCE_GOLDTIER_SANDBOX_PLAN.md)
records Session 1 independent PASS on its exact 60-path candidate after one bounded
documentation remediation; the S1 gate is historical evidence for those bytes only.
Session 2 received fresh independent PASS after one bounded duplicate-table remediation.
Its exact reviewed 147-path candidate and subsequent Session 3 changes are distinct.
Session 3 adds truthful ledger-derived submission states and a bounded read-only
uncertain-identity observation through normal Sandbox composition. On 2026-10-04,
the one owner-authorized synthetic acceptance completed actual XPI Search, Shell,
required Policy and exact-ID readback for customer `143887`. The application retained
SUBMISSION_CONFIRMED, a finalized successful ledger and exact document/ownership
evidence after restart without new provider calls. Amend was not required. The
[external receipt](../.ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S3_EXTERNAL_RECEIPT.json)
and [durable proof](../.ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S3_DURABLE_ACCEPTANCE_PROOF.json)
record these bounded Sandbox observations. The cumulative content and final executed
checks are indexed by the [final manifest](../.ai-pipeline/reports/ONBOARDING_INTELLIGENCE_FINAL_MANIFEST.json)
and [check index](../.ai-pipeline/reports/ONBOARDING_INTELLIGENCE_FINAL_CHECKS.json).
The historical combined gate failed; the later authorized narrow P2 remediation
passed, as linked above. Human integration through PR #69 is complete. This task
adds bounded post-merge validation and documentation; it grants no further external calls.

The merged Session 1 implementation retains structured document observations and
provenance across same-case identity correction. The existing document owner compares
them with the newly verified canonical identity; existing reconciliation/orchestration
owners recompute dependent state and resume until the next authoritative blocker.
This uses retained extraction rather than retained upload bytes or a new OCR claim.
Replacement-document semantics and target no-replay remain separate.

Cases and Onboarded offer server-side Created from / Created to filters over the
authoritative automation `created_at`. Both selected Singapore calendar days are
inclusive under the explicit UTC+08:00 convention: from 00:00 inclusive through the
day after Created to at 00:00 exclusive. Actor/team scope remains backend-owned;
the paged portfolio applies date predicates before ordering, offset and limit.
Date bounds participate in authenticated query identity and cancellation.

Under D-062 and the explicit current program authority, Review & Send is the final
local human approval for the reviewed submission. The Session 1 presentation ends at
Final review & send and has no second local unresolved approval stage. GoldTier-internal
approval, regulatory approval and actual external delivery remain separate evidence.
Session 1 gate/browser/physical evidence is attributed to the program's original reports;
Session 2 adds native-first/local OCR and creator-reviewed document ownership evidence;
the separate S2 independent gate passed its recorded round1 content. Session 3 proves
one bounded synthetic parent-customer Sandbox delivery, not GoldTier KYC/approval,
Ready-for-Approval, related-party objects, original-file transfer or Live operation.
Camunda is unimplemented and outside this program.

### Phase 24 accepted on inspected main

The Phase24/24C package merged through PR #67 adds same-case registry verification and entered/document/other UEN choices, dependency
recomputation with identity-bound ownership history, bounded scalar evidence and a
deterministic semantic tagger (`ML_RUNTIME_NOT_AVAILABLE`), and seven accessible ordered
disclosures ending in Review & Send. Its source/test/review identity and verification
limits remain attributed to the Phase24 handoff and independent gates; their execution evidence
is not silently transferred to the later A–G or current program evidence. Provider classifications remain unchanged.

Actual October 1-2 official ACRA Marketplace Mock discovery made 24 token/read attempts:
22 HTTP responses and two pre-response TLS failures. The private seven-page sample
catalogue was inspected only to identify candidate UENs. A fresh Garden acquisition
fed four role observations through canonical normalization and deterministic tagging:
review required, zero candidates, no numeric numerator or denominator. Documented
fallbacks did not supply a supported coherent same-entity quantitative case; no
official percentage or UBO candidate is claimed. The catalogue does not resolve
Q-012 authority for partner/member/group or capital/denominator contracts.
See [sanitized receipt](development/PHASE_24_ACRA_DISCOVERY.md) and
[proposed tagger boundary](decisions/ADR-008_OWNERSHIP_EVIDENCE_TAGGING.md).

The repository is a synthetic, local/sandbox-shaped proof of concept for Singapore
new-to-bank corporate onboarding. The supported happy path can reach
`COMPLETED / MOCK_GOLDTIER_SUBMITTED`; that means the credential-free Mock target path
completed after local submission confirmation. It does not mean regulatory approval,
GoldTier-internal approval, legal UBO determination, Ready-for-Approval, or live interoperability.

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
  existing customers reuse only prior finalized same-ID target proof and skip duplicate
  Shell/new Policy. The G branch acquires required current registry/cache evidence before
  ownership, validates it against the searched identity, and preserves failure precedence.
  No-match may later create Shell/Policy after readiness/confirmation. Ambiguous/failed
  Search permits independent evidence under D-061 while all target mutations stay blocked. Provider-verified recovery retains the
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
- The PR #68 inspector retained an unresolved external human-approval presentation
  after technical completion. The merged Session 1 implementation replaces that local presentation
  with Final review & send under D-062/current owner authority; there is no second local
  approval requirement. The technical event table uses fixed event codes/types,
  never retained free-text event messages.
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

The bounded D-061 package, originally developed in the 2026-09-29 candidate on
`feat/recoverable-onboarding-final-review`, is now included in the inspected PR #65
merged-main baseline. It adds same-case identity correction and read-only
Search recheck; independent evidence continuation for ambiguous as well as failed
Search; fixed D-056 policy rebind; pre-confirm KYC/segment editing; reviewed local
manual economic-interest evidence; versioned explanatory blocker-decision metadata;
and an exact server-authored final review whose durable confirmation is enforced under
lock before every target write path. HR gains a read-only ACRA diagnostic surface using
the same composed connector and no case access. Acceptance establishes POC behavior;
it does not establish provider-write authorization, Live integration, regulatory or
GoldTier-internal approval, or sponsor policy.
The accepted POC final review includes legal form, owning team, and section-level
routes to the existing identity, classification, and document owners. It routes to the
manual-ownership evidence owner only when the server's typed recovery projection
authorizes `MANUAL_OWNERSHIP_EVIDENCE`; otherwise it truthfully labels ownership as
review-only. Before confirmation, identity correction remains same-case and
backend-validated; it cancels stale confirmation state, performs only a read-only Search
recheck, and invalidates dependent evidence. Confirmed or submitted projections cannot
expose those edit actions.

Historical post-merge main CI run `36452914032` for baseline
`d23d7b7335ba402b071191821c35e4f5e879ed7c` passed on its second attempt. The
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
     -> exact verified prior target: retain same-ID proof; skip Shell/new Policy;
        acquire required current registry/cache evidence and validate searched identity
     -> no match: closed SG registry router and optional exact-key Mock cache
        -> configured synthetic Mock, official API Marketplace Mock, or generic sandbox-shaped acquisition
        -> canonical legal entity and normalized registry evidence
     -> ambiguous: independent eligible registry/documents/evidence may continue;
        customer identity remains under review and every target mutation is blocked
     -> technical Search failure: retain case and continue independent ACRA, document,
        reconciliation, and ownership evidence; target identity remains unresolved,
        then terminate at the Search blocker with no Shell/Policy/Amend mutation
  -> bounded document intake and local deterministic extraction
  -> source-neutral reconciliation and review/resume where required
  -> registry-fed deterministic Decimal ownership graph analysis
  -> versioned advisory entity resolution, UBO assistance, and mock risk
  -> readiness and immutable target snapshot
  -> Review & Send: final local human approval and retained dispatch confirmation
  -> incremental GoldTier Mock-default or explicit XPI-sandbox target checkpoints:
     Shell/Policy for new customers; Amend when required (always for D2 Mock,
     conditional under D-063 for XPI); same-ID read-back after required operations,
     all with the same retained no-replay recovery ledger
  -> authorized bounded case portfolio/dashboard/activity and detailed evidence views
```

Technical composition is centered in `apps/backend/app/main.py`,
`apps/backend/app/composition.py`, and `apps/backend/app/persistence/composition.py`.
Business behavior stays in domain/services; adapters stay at connector/persistence
boundaries.

## Slice-D D2 local Mock accepted on main — 2026-10-04

The D2 implementation included in PR #68 retains bounded customer facts inside the existing Mock
connector and uses the existing target ledger for successful identity readback after
required Amend. Policy remains technical POLICY_CREATED with accepted ACRA external-key
binding. Prior verified-case reuse also requires finalized same-ID readback ledger proof;
a configured provider match alone requires review. A fresh connector loses runtime
provider facts and cannot fabricate missing Policy/Amend/readback success or replay an
uncertain ledger attempt. No runtime seed/reset endpoint, provider history, database,
workflow/task/RFA/approval state, Sandbox fallback or external call is added. Mock remains
PROJECT_OWNED / LOCAL / IN_PROCESS / NO_HTTP / NO_AUTH / PROCESS_LOCAL. D1 observed only
NO_MATCH and established no new API semantics. Exact D2 verification/review provenance
belongs to [the D2 report](../.ai-pipeline/reports/POST_PHASE24_SLICE_D2_IMPLEMENTATION.md);
earlier main/phase acceptance remains attributed to its original tree. D2's feature-branch
independent PASS and the final cumulative A–G PASS preceded the human merge through PR #68.
These historical receipts are not a new execution against the later PR #69 implementation.

## Current External Integration Truth

| Boundary | Active/default | Other implemented seam | Classification | What is proved |
|---|---|---|---|---|
| ACRA | `mock` | generic `sandbox` connector | Mock active; sandbox partial | Synthetic ACRA-shaped behavior and adapter isolation |
| ACRA API Marketplace Mock | explicit opt-in | fixed official Mock token/entity/shareholder transport with no fallback | Mock / Observed interoperability | Authorized token plus strict entity/shareholder success; Garden shareholders empty; no ownership-percentage authority and not Live |
| Registry cache | disabled | opt-in synthetic and official API Marketplace Mock | User-authorized POC, Phase24C accepted main | Normalized operation-prefix/definitive-negative schema2, frozen ACTIVE freshness/TTL, COMPLETE-only binding and bounded process-local single-flight; historical branch extensions retain their own review identities |
| ACRA BizFile | none | module exists but is not composed | Dormant | Focused adapter code/tests only, not runtime availability |
| IDP/OCR | `local_pdf_text` | Mock fault/demo provider | Local POC / Mock | S2 independent PASS; native-first PDF/DOCX/TXT plus actual local Tesseract scanned PDF/PNG/JPEG/TIFF. Host OCR runtime absent; isolated Docker runtime and current checks have explicit receipts in the final check index. |
| Ownership | registry evidence into local engine | Mock fault/demo provider | Local / Mock support | Deterministic Decimal graph analysis, not an external service |
| GoldTier | `mock` default | XPI `sandbox` mode | Mock active; sandbox partial | Ordered target behavior through one retained recovery ledger |
| GoldTier XPI sandbox | none | explicit `sandbox` mode | Partial | Supplied-route Search/customer mutation adapter, strict safe projection, target-policy blocking and no-replay; the merged S3 implementation retained one fresh synthetic parent Shell/Policy/exact-ID readback and retained confirmed state across restart. Historical Garden Amend remains failed. RP/file transfer, KYC/approval/RFA and Live interoperability remain unproved |
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

The provider matrix above is Observed. The historical official ACRA Mock `401` is failure evidence; later authorized
strict successful Mock observations are separately recorded, and neither is Live. Thresholds, role behavior, policy defaults,
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
- One schema-versioned case envelope (current schema v9) owns durable case
  state. Strict v1/v2/v3/v4/v5/v6/v7/v8 reads preserve absent historical fields, including v4
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
- The optional Mock registry cache has a separate schema-v1/v2 repository/collection.
  Schema1 reads remain complete-only; schema2 stores normalized successful operation
  prefixes and definitive NOT_FOUND. Only complete fresh bundles bind to a case. It has no cross-collection
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
- HR administers synthetic profiles/teams and can draft/edit/default-reset/submit
  business policy proposals, without case access or activation authority. Independent
  Director approval alone activates a proposal under existing authorization and CAS.

## Major current capabilities

- Controlled Singapore/ACRA routing with no implicit source precedence.
- Four-operation Mock registry acquisition with truthful complete/partial/failure
  evidence and downstream call stopping.
- Optional backend-global reuse of fresh normalized synthetic and official API
  Marketplace Mock operations, with exact namespace isolation, complete-only case
  bindings, definitive negative TTL and bounded process-local single-flight.
- PDF, DOCX and UTF-8 TXT technical intake with strict size/structure handling.
- Deterministic local extraction and field provenance.
- Source-neutral reconciliation with explicit bounded actions and resume, including
  case-scoped comparison against current registry acquisition evidence. Exact verified
  Mock target reuse skips duplicate Shell/Policy while the existing acquisition/cache
  owner supplies current evidence under the case's frozen registry policy.
- Deterministic Decimal direct/indirect ownership paths and provisional UBO candidates.
- Immutable per-case IDP/UBO, advisory-intelligence, registry TTL and deterministic
  classifier policy snapshot with approved active-version identity.
- Explainable source-neutral entity resolution, ML-assisted UBO advice, and bounded mock
  advisory risk, all with permanent non-authority labels and synthetic model cards.
- Ordered Mock target execution with no-replay recovery states.
- Accepted POC operator recovery controls: same-case identity correction and
  read-only Search recheck, bounded policy rebind, pre-confirm classification edits,
  reviewed local ownership evidence, truthful decision metadata, and accessible
  problem-stage navigation to the existing owners.
- Accepted POC final review and durable target confirmation, revalidated under the
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
  existing-case reassessment, background refresh, TTL deletion, or cache administration API.
  Frozen POC definitive-negative evidence TTL is implemented and is distinct from deletion/retention.
- No ASIC/Malaysia/Hong Kong registry adapter in active runtime.
- No `createRelationship` or multi-level hierarchy creation through GoldTier.
- No sponsor-approved final UBO, document, source-authority, RBAC, retention, deletion,
  review, or Ready-for-Approval policy.
- No arbitrary blocker override, free-form canonical editing, general provider-recovery
  attestation, automatic Search retry, autonomous approval, or complete human exception
  workbench. Accepted recovery actions remain the explicit typed D-061 paths.
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

- Q-012 is partially resolved for bounded official Mock token request/response, raw-token header,
  and successful profile/officer/sample operations. It remains open for authoritative subscriber/
  Production contracts, partner/member ownership denominators, broader not-found/errors, rate/retry,
  TLS/mTLS/private-CA and approved access. Garden role evidence is not numeric partnership ownership.
- Q-008/D-018 blocks real GoldTier/PingFed authentication material and containment.
- Q-001/Q-002/Q-006/Q-007 block Ready-for-Approval, hierarchy retrieval, related-party
  semantics, and final Singapore target mappings.
- Q-003/Q-005/Q-013/Q-014/Q-015 block final document scope, validation/source authority,
  privacy/retention, confidence/reviewer policy, and jurisdiction/reconciliation authority.
- Q-004 remains partially resolved: D-062 confirms the bounded inclusive >=25% default;
  complete legal/control/evidence and production UBO policy remain open.
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

The three-session program is merged through PR #69 and Phase25/26 is complete
through PR #70. The owner has assigned [Phase27](PHASE_27_HANDOFF.md): final agent UI
UAT, architecture/demo documentation and closeout, with explicit A/B/final independent
barriers and local commit only after final PASS. Phase27A has fresh independent exact PASS after truthful agent UI results,
bounded product retests and prose encoding repair;27B/27C retain separate barriers. No feature expansion or external provider execution is authorized.
The following broader packages require separate authorization:

PR #65's accepted POC onboarding/final-review implementation and independent gate
are complete. Further work requires a separately authorized package. Official-Mock
demo-pack completeness remains evidence-dependent: no absent supplied fixture,
screenshot, declaration, README, or validation artefact may be invented.

1. Sponsor contract/access reconciliation for ACRA and GoldTier/PingFed.
2. Sponsor-confirmed legal/controller, reviewer and retention policy design; target
   Ready-for-Approval only where an authoritative target contract requires it.
3. Authoritative external-provider work only after contract, security and credential
   prerequisites are satisfied.
4. Measured hotspot or production-scale portfolio/activity work if evidence shows need.

Camunda remains unimplemented and is outside the current authorized program.

Every new package requires a bounded planner handoff, change classification, relevant
skill, proportional verification, and independent quality gate.

## Phase24C accepted-main delta — 2026-10-02

D-064 implements HR proposal/edit/default-reset/submit and independent Director decision
through existing policy/capability/repository owners. RM/onboarder are policy-view only;
legacy direct activation/showcase routes are denied. Approval alone changes global ACTIVE
for new cases. In-flight/completed case snapshots retain their identity/version/value/time;
D-056 target-only rebind preserves these frozen business values. Thirty-five seeded rules
include actual registry TTL and semantic classifier consumers. Version2 parameterized
semantic tags expose score/threshold/reasons/evidence/rule/policy metadata; 14-example
synthetic metrics and read-only impact simulation are not trained-model/legal accuracy.
Policy UI uses the five specified business categories and before-after Director review.
Phase24C introduced schema8 reads1..7 without rewrite; current PR #69 schema9 reads1..8; policy/cache schema2 stay separate under
existing strict CAS. Sandbox/Live cache and final autonomous approval remain unavailable.
Phase24C is accepted through merged PR #67 at the inspected main baseline. Its original
implementation, gate and external evidence retain their own execution identities.

## Slice E policy impact accepted on main — 2026-10-04

The Policy tab now offers on-demand deterministic explainable comparison beneath the
existing PolicyManagementService. Eight core editable parameters receive authoritative
synthetic scenario evaluation;13 active intelligence parameters expose changed values/
coupling and NOT_ASSESSED. Six fixed technical definitions and eight protected target
parameters remain outside editable impact behavior. The fixed inclusive ownership
comparator is preserved. Positive Decimal thresholds use the existing engine; zero is
explicitly unknown because the current policy and engine domains disagree.

The named bounded fixture pack supplies document/registry/negative/ownership outcomes
and the existing14-example classifier. Before/after counts and macro/micro metric deltas
are synthetic only. The UI shows current/default/base/proposed, descriptive materiality,
reason codes, stages, transitions, unknowns and approval boundary in accessible details.
HR and different Director use the same comparison evidence at the same aggregate
revision. No automatic policy/case approval, production forecast, persistent monitor,
case-population scan or external provider call is added. Historical comparison never
rebases a stale proposal; existing cases remain frozen on activation.

Implementation evidence and exact candidate identity are recorded in
.ai-pipeline/reports/POST_PHASE24_SLICE_E_IMPLEMENTATION.md and the Slice-E manifest.
Slice E received independent PASS on its exact cumulative feature-branch candidate; A/B/C/D
accepted anchors are preserved. Slice F then closed the inherited Phase07 exact-asset allowlist
blocker and received fresh remediation-round-1 PASS. Historical reports preserve earlier failures.
Mock/Local/Sandbox/Live classifications and all provider runtime status remain unchanged.
Slice E alone granted no publication authority. The subsequent cumulative A–G candidate
received exact final independent PASS and was human-merged through PR #68. Its historical
verification evidence remains separate from the later PR #69 and Phase25/26 evidence.
