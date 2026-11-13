# Current Project State

This is the concise operational snapshot of what is true in the tracked repository.
It is not a sponsor contract, phase report, or substitute for current source and tests.

## Verification metadata

Current assignment baseline verified on2026-10-10: merged PR80
`e799d74063678bb0eccbea445d5ab3c8628dd2c0`, post-merge push37954652603
SUCCESS (seven jobs). Grouped review is an uncommitted candidate with acceptance
owned by its current implementation/simulation/performance/IDP/independent reports.
Historical verification metadata follows.

PR #77 was human squash-merged on 2026-10-08 at inspected main
`8fb5a43c26efd5ef9f513b37fd9478e555cb4eb4`. Closeout state is
**merged-and-verified**. Post-merge main push CI
[37742194816](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/actions/runs/37742194816)
completed **SUCCESS**: backend, frontend, local-ocr, phase12-mongo, security,
demo-lifecycle-windows and e2e all passed. This is post-merge CI evidence for that
exact SHA; it does not establish sponsor/UAT approval or Live interoperability.

Recovery is current main behavior: bounded lost-confirmation observation uses GETs
only; uncertain Shell/Policy recovery preserves the original submission and confirmation.
Director recovery remains TARGET_RECOVERY capability-gated with backend currentness,
identity and locked reauthorization. Customer Search does not prove Policy success.
Recovery never replays an uncertain target mutation; explicit same-intent continuation
performs only remaining approved work. Unsupported or incompatible uncertainty remains
blocked with Director escalation. The [recovery runbook](integration/GOLDTIER_RELIABILITY_RECOVERY_UX.md)
and [Policy recovery history](integration/GOLDTIER_POLICY_PROVIDER_RECOVERY.md) retain
original assignment provenance. Implementation acceptance remains attributed to the
[reliability/recovery gate](../.ai-pipeline/reports/GOLDTIER_RELIABILITY_RECOVERY_UX_QUALITY_GATE.md)
and the final [Round 2 PASS](../.ai-pipeline/reports/PR77_E2E_ISOLATION_ROUND2_QUALITY_GATE.md)
for reviewed identity `df3ea779d1d6c28fc287437aabeb3880837e069f661157e84c1a577fec6d9b70`.
Provider classifications, sponsor decisions/questions and canonical owners are unchanged.

Earlier assignment and verification provenance below retains its original dates and
baselines. Candidate/unmerged descriptions in that chronology refer to those historical
checkpoints, not pending PR #77 work or the current verified main baseline.

The owner-assigned database-first happy-path candidate starts at inspected main
`771a9696e1e31e3865da4fbbb3f9b33b5959cb6a` on
`fix/zero-touch-registry-reuse-happy-path`. D-069/ADR-010 enable ordinary non-production
Mock cache reuse and four complete synthetic local seeds in the existing owner.
Fresh seeded cases perform zero ACRA operations; GoldTier is never preseeded.
Successful NO_MATCH progression and failed Search target blocking retain current truth.
Fresh evidence and independent review are bound to this task's reports; historical
verified-main/provider metadata below is preserved. No external interoperability claim.


The unmerged post-UAT candidate on
`fix/post-uat-document-ownership-goldtier-ux` starts at inspected main
`ae27654a075f13354364e86ec8fe5a81d24777d4`. It extends existing owners for
independent document auto-confirm, optional ownership notes, automatic guarded Garden
LOCAL fixture composition, ID-first completed details and explicit exact-ID completed
Sandbox verification. Evidence and independent verdict belong to its current task
reports; historical main/provider classifications below are unchanged. No new external
interoperability, production, legal UBO, GoldTier KYC or approval claim follows.

The unmerged 2026-10-05 post-closeout remediation starts from inspected main
`1e0600335a0c7677b5cd5d5c9dd8401dfaf3b90f`. Its
[existing-customer delta](integration/GOLDTIER_EXISTING_CUSTOMER_RESOLUTION.md)
adds independent Search-blocked document review, retained candidate identity fields,
and creator/version-bound CONFIRMED_EXISTING receipts in current schema9. Provider
classifications and historical main verification metadata below are unchanged; its
fresh tests/gate do not become new external interoperability or merged-main evidence.

The earlier main source baseline was inspected on 2026-10-05 at
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
  "case_envelope_schema_version": 20,
  "verified_date": "2026-10-08",
  "verified_main_sha": "8fb5a43c26efd5ef9f513b37fd9478e555cb4eb4",
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
persistence constant. The D-076 source introduced case envelope v11 (optional frozen
ownership-discovery policy and discovery audit). D-077 introduced v12 (optional hybrid
overlay classification, per-issuer official lookup/identity basis, evidence separation and
labelled synthetic-basis comparison). D-079 introduced v13 (official shareholder rows
without an entity profile). D-080 uses v14 (their source share class) and strictly
reads valid legacy v1..v13 without read-time rewrite, as defined by `CASE_SNAPSHOT_SCHEMA_VERSION`
in `apps/backend/app/persistence/models.py` and the version-specific decoders in
`apps/backend/app/persistence/mongo_case_store.py`. This documents existing compatibility;
no migration or persistence behavior is changed by this refresh. Historical tests and
independent gates remain tied to their recorded content; Phase 25 and Phase 26 have separate evidence.

## Current status

PR95 Dashboard v2 integration/remediation is an unmerged candidate from assigned
main`cc10a2b626ef92d2dd44600d488c1f15cc4f04f8` and PR95
`1c1fd9fbf1a68f79137d150ac8609cf811b10938`. The existing dashboard owner projects
selected creator cohorts, retained timings, exception history and creator/resolver
workload in memory/Mongo with existing backend RBAC. The API retains all-history default totals and its original UTC daily trend; v2
explicitly requests30 selected Singapore created dates. New metrics are additive,
as recorded in the current access contract. Existing Assistant behavior is retained.
Acceptance belongs only to the task's final implementation and independent gate
reports. This candidate does not change the historical verified-main metadata,
provider classifications, schema10, connectors or sponsor decisions.


PR #77 reliability/recovery is merged and verified on the main baseline above.
The current recovery runbook and exact acceptance/CI references are linked in
Verification metadata; the earlier closeout checkpoints below retain their own evidence.

### Historical PR #70 / Phase27 closeout checkpoint

Phase25/26 is complete and merged through PR #70. The PR #69-to-#70 diff is
16 documentation/evidence files only; product behavior, schema9, provider modes,
configuration and canonical owners are unchanged. The historical
[final independent PASS](../.ai-pipeline/reports/PHASE_25_26_FINAL_QUALITY_GATE.md)
remains bound to its recorded candidate, rather than becoming a Phase27 verdict.

At that checkpoint, the explicitly assigned Phase27 was on `feat/phase27-final-delivery-closeout` from
the then-inspected PR #70 baseline. Its [truth inventory](demo/PHASE_27_TRUTH_INVENTORY.md)
and [manual checklist](demo/PHASE_27_MANUAL_UAT_CHECKLIST.md) distinguish current
source, newly executed automated pre-UAT and agent UI outcomes (16 PASS/0 FAIL/5
NOT_RUN; HUMAN_EXECUTED0). Two bounded presentation defects were fixed/retested;
Phase27A has [fresh independent exact PASS](../.ai-pipeline/reports/PHASE_27A_RECHECK_QUALITY_GATE.md)
with P0/P1/P2=0/0/0 after bounded encoding repair. Owner-assigned27B synchronizes
current architecture/demo/limitations/questions and the
[final project closeout](FINAL_PROJECT_CLOSEOUT.md). The two UI fixes were accepted branch content pending merge at that checkpoint.
27B/27C/final gate and local commits retain their own evidence/barriers.
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

The Cases page (All cases / In progress / Onboarded views; the separate Onboarded page was
removed) offers server-side Created from / Created to filters over the
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
  separate memory/Mongo cache persistence. Current `auto` mode enables reuse only in
  non-production Mock lanes; explicit `disabled` remains supported.
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
| Registry cache | `auto` in non-production Mock lanes | explicit disabled/legacy Mock modes; synthetic and official API Marketplace Mock | User-authorized POC, Phase24C accepted main | Normalized operation-prefix/definitive-negative schema2, frozen ACTIVE freshness/TTL, COMPLETE-only binding and bounded process-local single-flight; historical branch extensions retain their own review identities |
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
- One schema-versioned case envelope (current schema v14) owns durable case
  state. Strict legacy v1..v13 reads preserve absent historical fields, including v4
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
- The structured metadata above (`verified_main_sha` `8fb5a43`, 2026-10-08) predates many
  merged PRs (for example #100 to #119); a full snapshot refresh is outstanding. Dated merged
  sections such as the AI Assistant Phase B section record their own deltas meanwhile.

## Next candidate work packages

PR #77 recovery is merged current behavior and is complete, not a pending candidate.
This docs-only refresh authorizes no next development phase or external execution.
The earlier [Phase27 handoff](PHASE_27_HANDOFF.md) and gates retain their historical
assignment/evidence boundaries. Existing bounded debt remains below; every package
requires separate authorization:

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
5. AI Assistant Phase B follow-ups: the owner's D-092 acceptance decision, an authorized
   live P06#2 check, and the owner-scored answer-quality items, each with owner-approved
   wording and its own independent gate.

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
Phase24C introduced schema8 reads1..7 without rewrite; PR #69 introduced schema9 reads1..8; policy/cache schema2 stay separate under
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

## Historical target-classification continuation — 2026-10-05

The owner-assigned second commit continues ccff7471 on the existing database-first branch.
Schema10 extends existing document/case owners with source-labelled classification;
strict schemas1..9 remain read-only compatible with unknown/empty new evidence.
Submission readiness separates final confirmation; classification saves are local and
actual uncertain attempts remain frozen/no-replay. Alpha remains60/40; Beta/Gamma have
six ultimate people, Gamma is a synthetic Partnership; separate Government classification
has no supported government-control ownership claim. Provider modes/statuses and
historical verified-main metadata above are unchanged. Fresh continuation checks and
independent verdict belong to its separate report, not the previous accepted commit.

2026-10-06 owner-authorized follow-up candidate: current classification conflict is
explicit, and USER/DOCUMENT choices bind trusted evidence identity. Same-value fresh
manual review is supported; later trusted evidence invalidates it. Currentness governs
readiness and confirmation before snapshot/ledger writes in both modes. Provider
classifications, target mapping, approval limits, fixtures and threshold are unchanged.
Historical protected DB non-access remains NOT_CERTIFIED and is owner-accepted as a
documented historical execution uncertainty. The new gate requires current execution
isolation; protected/owner database investigation and dotenv read remain prohibited.

## Historical main-integration candidate — 2026-10-06

At that checkpoint, fetch confirmed origin/main 1fc097f12c84af52b1e6d70a336cc22b03f3bef4
(read-only AI Assistant PR74). The feature at859f218 integrates that commit
through a conflict-free merge while preserving both accepted feature commits.
At that checkpoint, the local merge required fresh independent PASS and owner review
before publication.
No exact-file overlap; shared frontend root/proxy/session/case context is reviewed.
Bounded adaptations reuse the existing authenticated transport for AI Assistant 401 cleanup,
align guide/pending-step wording with current backend/UI projections, and contain
inaccessible-case404 and cancelled responses in the existing local conversation owner.
Schema10, source fingerprints, classification review/currentness, final Send, ledger
no-replay, fixtures, mappings and provider labels are preserved. That integration's
evidence and independent verdict belong to ZERO_TOUCH_COPILOT_MAIN_INTEGRATION reports;
historical main/feature gates and provider verification metadata above are unchanged.

## Synthetic company pack correction - unmerged candidate, 2026-10-09

The owner clarification supersedes the earlier MockAcraConnector candidate and its
historical PASS. Four new fictional companies extend the existing eight-company
LOCAL_SYNTHETIC_UAT_V1 manual seed owner (ADR-010/D-069). Normal configuration remains
api_marketplace_mock/mongo/auto. Fresh COMPLETE exact-UEN seeds yield CACHE_HIT without
Marketplace token or HTTP requests; missing/stale seeds use the configured provider.
The existing coordinator, repository, Decimal engine and target ledger own the flow.
No new provider, schema, mapping, business rule, authorization, automatic startup seed
or Live capability is introduced. Browser bindings disclose only an allowlisted local
seed namespace while configured-provider and original provenance remain distinct.
Historical reports apply only to their original bytes and requirements. Corrected
verification belongs to SYNTHETIC_COMPANY_PACK_CORRECTION reports.
See [the operator guide](demo/SYNTHETIC_COMPANY_PACK.md).

## Blocker-resolution candidate - 2026-10-10

Verified assignment baseline: merged PR80 e799d74063678bb0eccbea445d5ab3c8628dd2c0;
post-merge push37954652603 succeeded. The isolated, uncommitted blocker-resolution
candidate repairs PDFium CRLF classification, regenerates the four synthetic company
PDFs with explicit Company - Private / Corporate, adds local drafts and grouped review,
and focuses actual current controls. Provider matrix, schema10, provisional Decimal UBO,
final Review & Send and sponsor questions are unchanged. Drafts are tab-local; grouped
section retention is resumable and is not an atomic transaction. Fresh implementation,
simulation, performance, IDP and independent gate reports own candidate evidence. No
commit/push/PR/merge or real provider write is authorized by this assignment.

## Sponsor demo expansion - unmerged candidate, 2026-10-10

The owner addendum adds current creator Final Review edits through existing authorities,
fresh readiness/confirmation, and four separate native sponsor PDFs: Aurora202400019S,
Pacific202400015O, Straits202400016P and Meridian202400017Q. Legacy Orion and eight default
seeds remain. Four recoverable blocker cases and four automatic LOCAL-seed happy cases
are exercised through actual browser HTTP and disposable physical Mongo with strict
offline provider transports. The configured modes remain Marketplace Mock/Mongo/auto
and XPI Sandbox; no external provider write occurs. Real Sandbox UAT is NOT_VERIFIED.
No schema, mapper, Decimal policy, provider capability or sponsor-controlled rule changes.
Expanded source/evidence acceptance requires SPONSOR_DEMO_FINAL_QUALITY_GATE.md; the prior
blocker gate certifies only its historical frozen package.


## Ownership presentation and document continuation candidate — 2026-10-12

Owner-assigned bounded hotfix on feat/ownership-ubo-doc-review-streamline from freshly
fetched PR82 main a6c80d2f20048ce64b3f6184df34c098f8fff4ab. Current implementation
arranges retained graph relationships into a bounded responsive explorer, with collapsible
levels, person selection and original backend path/aggregate values. Ownership and Final
Review share a provisional qualifying-natural-person summary. Unknown intermediate values
stay unknown; there is no browser calculator or legal UBO determination.

The existing zero-touch owner continues complete current grouped review confirmations,
explicit slot replacements and successful final failed-intake retries. Independent evidence
blockers and final target confirmation remain. Lineage/receipts, lock/currentness/CAS,
section persistence and the target ledger remain unchanged. No new source winner,
provider/schema/configuration/mapping/threshold/auth grant is introduced. Initial
multi-document intake remains explicit; additional uploads are not implicit replacement.
Acceptance belongs to the task's fresh implementation evidence and independent gate,
not prior reports. Publication is reserved for separate owner approval under the
superseding principal-engineering brief. Provider classifications and sponsor questions
remain unchanged; no external provider mutation or Live interoperability is tested.

The initial independent candidate gate failed on independent failed-sibling recovery.
The bounded remediation preserves PENDING and targeted retry across grouped confirmation,
replacement and dependent-refresh recovery. Its narrow existing document-reupload
transition guard admits RESUMING at DOCUMENT, retaining prefix/event validation;
statuses, schema and general transition table remain unchanged. Only the fresh remediation
gate can accept the changed candidate; the original FAIL is retained as history.

The owner-authorized overnight release closure addresses ODS-FQG-03 with structured,
disjoint presentation occurrence keys for client, retained paths and unlinked holders.
Selection, collapse and graph-refresh reconciliation share that identity; backend IDs,
Decimal values and provenance remain unchanged. The independent valid-source selection
probe is now GREEN and normally discovered coverage includes sentinel/delimiter IDs,
repeated paths and refresh. Real authenticated keyboard/mobile/reload verification uses
the existing manual-evidence API with a valid root relationship and LOCAL declaration
provenance. Acceptance remains conditional on a fresh independent combined PASS; all
historical FAIL reports remain immutable. Normal scoped commit/push/PR is now expressly
authorized after local publication gates and latest-main integration, with human merge.

## PR83 initial-intake P1 remediation candidate - 2026-10-12

Post-publication review4243047623 identifies initial grouped decisions bypassing explicit
count-bound intake completion. The owner-authorized remaining remediation distinguishes
unstarted PENDING_INPUTS from existing started-workflow recovery. Initial decisions,
replacement and failed-upload retry retain evidence without starting automation; missing
count on initial resume is rejected through the existing incomplete-intake409. Correct
explicit completion and genuine recovery still continue through existing orchestration.
The case-page initial action accepts a user-entered intended count instead of count-free
resume, using existing backend timing for presentation. No persisted/API schema, provider,
mapping, ownership policy, authorization owner or target-ledger change is introduced.
Accepted replacement/retry503, failed siblings, original A01-A07/B01-B12 and root-ID
selection remain regression requirements. Historical PASS does not accept changed bytes;
publication depends on the separately assigned fresh PR83 P1 independent gate and checks.

## Five-layer hybrid Marketplace overlay - unmerged candidate, 2026-10-23

Candidate D-077 on `feat/acra-marketplace-hybrid-five-layer-ubo-20261023` from main
`24c3de385ba5cda099a3dc3b1b266fdf93aa4738`: explicit official-lane setting
`ACRA_MARKETPLACE_OWNERSHIP_OVERLAY=hybrid_direct_overlay` (default unchanged), whitelisted
Garden-direct and five-layer scenarios, cache-first official issuer lookups,
LOCAL_SYNTHETIC_RELATIONSHIP links, always REVIEW_REQUIRED, schema 12, and the uploadable
`five-layer-marketplace-hybrid-client.pdf`. Provider classifications are unchanged; the
hybrid lane is not Live. Its offline browser/API evidence uses an allowlisted protocol
transport (AUTOMATED_OFFLINE_SIMULATION). No live Marketplace Mock probe ran in the
implementing session (NOT_RUN_CREDENTIALS). See `demo/FIVE_LAYER_ACRA_HYBRID_DEMO.md`.

## Official shareholder evidence without an entity profile - unmerged candidate, 2026-10-24

Candidate D-079 on `feat/sim-lim-official-shareholder-evidence-20261024`, from main
`2d8b84af46f2ac0f1d94965ca638e1cd7a1c7e54`.
- **Behaviour:** in the official Marketplace lane, a non-overlay corporate holder with an
  empty entity-basic profile keeps its official `coShareholdersDetails` rows as
  `official_shareholders` beside the graph, without identity, legal form or percentages.
  The example is SIM LIM `111111111M`, from Garden's direct overlay. The case stays
  REVIEW_REQUIRED.
- **Persistence:** registry cache schema 3; case envelope schema 13.
- **Providers:** classifications are unchanged.
- **Evidence:** offline only (AUTOMATED_OFFLINE_SIMULATION). No live Marketplace call was
  made in the implementing session.

## Share-class retention on official shareholder rows - unmerged candidate, 2026-10-24

Candidate D-080 on `feat/sim-lim-acra-ownership-followthrough-20261024`, from main
`ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322` (D-079 merged).
- **Behaviour:** D-079 rows also keep each row's source `share_type` and `currency`. When
  current rows mix classes, the denominator-required issue says so. No arithmetic changes.
- **Persistence:** registry cache schema 4 (`MARKETPLACE_SHAREHOLDERS_V2`); case envelope
  schema 14.
- **Providers:** classifications are unchanged.
- **Evidence:** D-080 itself has offline tests only. An owner-authorized bounded
  read-only Marketplace **Mock** run (2 token requests, 7 GETs) used the pre-D-080 (D-079)
  code. It retained SIM LIM's four rows in a fresh Garden onboarding, observed their share
  classes, and found `coCapitalDetails` empty. This is Mock interoperability only, never
  Live.
- **D-081 (same candidate, owner scope correction):** in the opt-in hybrid overlay lane
  only, retained current rows also become labelled `LOCAL_POC_ASSUMED_EQUAL_UNITS` links.
  Each issuer's own active units form the denominator, and the existing six-decimal rule and
  engine apply. Garden → SIM LIM gives ABCD123 51.13636375%. Every result stays
  REVIEW_REQUIRED, and the creator cannot keep or redeclare POC links unchanged (409);
  nothing is ACRA-verified.
- **D-082 (candidate, opt-in, default off):** the eligible Garden POC analysis is accepted
  at readiness only (state, issues and classifications stay review). Target confirmation
  is still required, and no provisional UBO id reaches the Mock snapshot.
- **D-085 (candidate, same opt-in):** replaces D-082's Garden-only officer-role allowlist
  with a reusable contract. A trusted catalogue scenario declares its accepted POC
  assumptions, and eligibility evaluates actual review causes. Garden qualifies; the D-077
  five-layer scenario declares nothing. Case envelope 15. A bounded read-only Marketplace
  Mock probe (2026-10-25, 1 token + 18 GETs) found no ACRA-backed multi-layer chain
  supportable without overriding official holder facts (`INSUFFICIENT_MARKETPLACE_MOCK_DATA`).
- **D-086 (candidate):** the five-layer simulation is presented as "Multi-layer ownership
  simulation calculated" (presentation-only `simulation_calculated`; readiness unchanged),
  and an operator-selected `OPQ_GARDEN_SIM_LIM_V1` scenario links OPQ to Garden at an
  owner-declared 100% (no units), reusing Garden's register and SIM LIM's official rows. It
  calculates; Garden's retained Owner roles first blocked POC readiness (fail closed).
- **D-087 (candidate):** the OPQ scenario's trusted declaration names Garden's `OWNER` roles
  as descriptive intermediate context (`DESCRIPTIVE_INTERMEDIATE_OFFICER_ROLES`), so a fresh
  Scenario B case with the opt-in policy is POC-accepted, ownership-READY and waits for
  explicit target confirmation. Undeclared issuers or role kinds still block.
- **D-088 (candidate):** official Marketplace Mock `businessProfile` read for
  scenario-named corporate holders only (cache schema 5, contract
  `MARKETPLACE_BUSINESS_PROFILE_V1`). Status-free rows that exactly equal one compatible
  issued class attach as `LOCAL_POC_ISSUED_CAPITAL_BASIS` links under the declared
  `ISSUED_CAPITAL_DENOMINATOR` assumption. One owner-authorized read: 1 token + 1 GET.
- **D-089 (candidate):** the `OPQ_GARDEN_ABC_V1` variant (selector
  `garden_abc_multi_holder`), owner-declared OPQ -> Garden 50% / ABC COMPANY 50%. Results:
  ABC holder 50, ABCD123 25.568181875, LIM CHOON HUAT 18.75, TAN WEI LING and EFGH2345
  2.8409090625. POC-accepted, ownership READY, waits for explicit confirmation.

## AI Assistant Phase B merged - 2026-10-27

Merged and verified on main `728b30f197d94f4d361741f832bba7f3f19708f0`: PR #118 (squash
`8d68506`, tree `53f1735` = reviewed head `bd554ce`) and PR #119 (squash `728b30f`, tree
`b4f54b1` = reviewed head `556860c`). This section records only the AI Assistant delta. The
structured `verified_main_sha` baseline above is unchanged (`8fb5a43`); a full snapshot refresh
across the intervening merges is outstanding (see architectural debt).
- **Decisions:** D-092 is PROPOSED (P1 to P10) and not sponsor policy; D-091 stays accepted
  for its dormant scope only; ADR-012 Amendment 2 records the new conditional lines.
- **Service behaviour:** answer quality only. Rule 17 makes "I can't answer that from this
  case's data." exclusive. New conditional allowed lines: the non-live ACRA registry source
  line, "This case cannot name any UBOs yet because the UBO check has not run." (only with
  `OWNERSHIP_REQUIRED` and ownership `MISSING`) and the topic-only "Marking the UBO check as
  complete is not offered to you on this case." Targeted steering requires no line. The
  exact-line guard, sentence checks, case-data fallback, answer records, RBAC and GET-only CLM
  access are unchanged. Owner-approved prompt bound 9,250; measured prompt 9,218.
- **Remote inference:** the service's OpenRouter profile stays DORMANT. Only the offline
  evaluation harness (`apps/assistant/scripts/evaluate_answers.py`) can open a live path, behind the D-091
  and D-092 decisions named in the process environment, the approved endpoint record
  (`deepinfra/bf16`), a healthy budget ledger, a fail-closed preflight, per-call
  generation-metadata verification, and an explicit `--questions` manifest with a matching
  `--expect-count`.
- **Evidence:** 28 owner-run synthetic calls to `openai/gpt-oss-120b` on DeepInfra, all
  provider- and cost-verified, US$0.00586987 in total (ledger cap US$1.00). This is synthetic
  external evaluation evidence (D-092), never Live CLM behaviour; no provider classification
  in the metadata changes. Owner human scoring of the original 17-question comparison (single
  rater, git-ignored artifacts): GPT-OSS 120B 2.51 vs Ministral-3 8B 2.35 overall.
- **Checks and CI:** independent QGs R1 to R7, R9 and a post-integration gate passed (R8 failed on two
  Medium docs findings, fixed and re-gated by R9); the
  integrated candidate's full assistant suite had 2,186 of 2,200 passing (14 Windows
  `Errno 24` failures that pass in isolation). Hosted CI for both PRs was
  `HOSTED_CI_NOT_EXECUTED - BILLING/INFRASTRUCTURE BLOCKED` (0 steps); the repository owner (`shaneqwaszx`) merged both PRs with
  that limitation documented in each PR description.
- **Open:** D-092 acceptance; live verification of P06#2; owner-scored follow-ups (entity
  status vs registry connection, director evidence, GoldTier handoff, unrelated disclaimers,
  UEN meaning); the Low findings listed in PRs #118 and #119.

## AI Assistant model management (D-093) merged - 2026-10-27

Merged to main `c36b8aff5213037d9ed0710e69f8b9afc7c8c614` by the repository owner
(`shaneqwaszx`) on 2026-10-27. PR #121 (branch `feat/assistant-model-management-20261027`)
was squash-merged with a single parent, `176e09b`; its tree, `5e259da`, equals the reviewed
head `d57856d`. The branch started from main `23c45a7` and integrated main `176e09b`
(PR #122, D-092 P11 to P14) by merge, without conflicts. This section records only the
D-093 delta. The structured `verified_main_sha` baseline above is unchanged (`8fb5a43`).
- **Decisions:** D-093 accepted by the owner for the local-only POC scope (ADR-012
  Amendment 4). D-091 and D-092 (PROPOSED) unchanged. As merged, D-093 manages only
  IT-configured local loopback models and remote inference stayed unavailable to the
  service. The later D-094 (PR #123, next section) is a separate, off-by-default local
  synthetic OpenRouter test exception; D-093 is unchanged for local profiles.
- **Behaviour:** HR (new backend capability `MODEL_CONFIG_MANAGE`, HR only) can test,
  technically qualify, activate and roll back IT-configured local loopback models on the new
  **AI Models** page; the `AI_ASSISTANT_LLM_*` model remains the baseline and the fallback.
  Off unless `AI_ASSISTANT_MODEL_PROFILES_FILE` is set. Prompts, catalog, topic routing,
  guardrails, retrieval, knowledge publishing and CLM access are unchanged.
- **New owners:** `model_catalog`, `model_admin` (active-model holder and API),
  `model_admin_store` (SQLite state and audit under `apps/assistant/data/models/`),
  `model_qualification`; the harness side runs in its own process
  (`apps/assistant/scripts/qualify_model.py`).
- **Evidence:** offline tests (fake and loopback model servers) plus two implementer `LOCAL`
  runs of the real service, qualification process and Ollama 0.40.10 (`llama3.1:8b`, server
  started with a 16,384-token context, synthetic scenarios only): declared 16,384 passed every
  gate (84/84 turns, capacity verified at 16,334 tokens, 0 unsafe displayed lines, line
  validity 0.817, G-5 reported 0.214) and activation without the acknowledgement was refused;
  declared 32,768 failed G-7 with `TRUNCATION_DETECTED`. No remote or paid call was made.
  After integrating PR #122 the answer-code basis changed (`59a3bcd4…`): the earlier
  qualification showed as out of date and activation was refused (`NOT_QUALIFIED`); a fresh
  LOCAL qualification of the same profile passed every gate (84/84 turns, 0 unsafe displayed
  lines, line validity 0.808, G-5 reported 0.214, capacity verified, 0 drifted turns), then
  activation with the acknowledgement and rollback succeeded. A developer browser smoke test
  of the AI Models page (RM/Director refused, HR flow end to end) passed on `aea87b9`.
  Answer quality `NOT_SCORED` (gold stub). Not Live evidence.
- **CI:** hosted CI was not executed (billing/infrastructure blocked); the owner merged with
  that limitation.
- **Open:** rerun hosted CI once billing access returns after 1 November 2026; Low
  follow-ups F-7, N-1, N-2 and O-1; owner gold labels (A-6) before answer quality can be
  scored; any model activated through management must be re-qualified after a later change
  to the answer code.

## AI Assistant D-094 local synthetic test mode merged - 2026-10-28

Merged to main `9a0dcd5f1af78214e987e38aab3b62f92a0cf168` by the repository owner
(`shaneqwaszx`) on 2026-10-28. PR #123 was squash-merged with a single parent, `c36b8af`. Its
tree, `57f59a2`, equals the reviewed head `0f6e081`: product commit `71e4654` plus a
report-only commit. This section records only the D-094 delta. The structured
`verified_main_sha` baseline above is unchanged (`8fb5a43`).
- **Decisions:** D-094 (owner-authorised, local development scope only). D-091 and D-093 are
  unchanged apart from D-094 T3. D-092 is still PROPOSED.
- **Behaviour:** off by default. With D-094 configured on a loopback development set-up, HR
  can test (preflight, no inference), qualify (a paid, counted Phase B manifest with gate G-8,
  every call verified), activate and roll back GPT-OSS 120B via OpenRouter on the existing
  AI Models page. The existing chat uses it only when the whole prompt is inside the
  generated synthetic boundary (GARDEN BUSINESS, ACRA MOCK, fixture documents and values,
  seeded viewers, repository knowledge, synthetic vocabulary). Anything else gets the
  case-data answer and sends nothing. Earlier qualifications become out of date.
- **New owners:** `ai_assistant/remote_test.py`, `ai_assistant/synthetic_boundary.py` (with
  its generated `synthetic_boundary.json` and `scripts/build_synthetic_boundary.py`), and
  `ai_assistant/remote_checks.py`, which moved unchanged from the harness.
- **Offline evidence:**
  - Tests used a mock OpenRouter, a fake public listing, a synthetic ledger and a fake CLM
    backend.
  - The full assistant suite ran 2,442 tests. 14 failed, all Windows `Errno 24`. The same 14
    test IDs also fail on main `c36b8af`, and they pass in isolation.
  - Frontend: 1,123 tests passed.
  - A real-stack browser E2E ran with a mocked OpenRouter.
  - Independent Quality Gates R1, R2 and R4 failed and R3 passed with minor fixes; each
    was remediated, and R5 passed. The pre-PR check passed.
- **Paid smoke test (owner-approved, 2026-10-28, head `0f6e081`):**
  - Set-up: the real assistant, the backend in memory mode with ACRA MOCK, the Vite
    frontend, and real OpenRouter `openai/gpt-oss-120b` on `deepinfra/bf16`.
  - HR's connection test passed, and the qualification `P01#1,P02#0` passed G-1 to G-8,
    with G-8 showing 2/2 calls verified. HR then activated the model.
  - On a fresh GARDEN BUSINESS case, all four RM questions were answered by the model with
    the D-094 notice. The directors question received the decline "I can't answer that from
    this case's data."
  - A negative control ("Is Tan Ah Kow a director?") was refused with
    `SYNTHETIC_TEXT_NOT_APPROVED` and sent nothing.
  - Rollback returned to the local `ministral-3:8b`.
  - There were 6 calls (ledger rows 29 to 34). All were settled and verified for provider
    (DeepInfra), model and cost, US$0.001076 in total.
  - The ledger's committed spend is now US$0.006960, against a cap lowered to US$0.105884.
  - This is synthetic external evaluation on the owner's machine, never Live CLM behaviour.
    No provider classification in the metadata changes.
- **CI:** hosted CI was `HOSTED_CI_NOT_EXECUTED - BILLING/INFRASTRUCTURE BLOCKED`: push run
  40609162932 and `pull_request` run 40609235296, each 9 jobs with 0 steps. The owner
  accepted a temporary exception for this PR. Hosted CI is to be rerun once billing access
  returns after 1 November 2026.
- **Open:**
  - Rerun hosted CI.
  - The six optional advisories from the Quality Gates: R5-A1, R4-A1, R4-A2, R4-A3, R3-A1
    and R2-5.
  - Find out why the directors question declined.
  - The owner's decision on D-092 (still PROPOSED).
- **Known limit:** a typed question is screened against accidental entry, not deliberate
  encoding, so it cannot be proven synthetic.
  - What gets through: a name made of ordinary English words, numbers spelled out as words,
    and number groups spread over several requests (the cap is per request).
  - What the screen allows: only printable ASCII plus named typographic marks, words from
    the synthetic vocabulary, and at most three number groups across the user turns, never
    two side by side.

## AI Assistant D-095 development synthetic mode, key sources and daily cap (branch, not merged) - 2026-10-28

Branch `claude/gracious-lovelace-bjvh2z` from main `7119905`. This section records only the
D-095 delta; nothing here is merged or Live.
- **Decisions:** D-095 (owner-directed, local development scope only; DECISION_LOG). D-094 is
  unchanged without the new flag and stays the fallback. D-091 X3 is amended for the key
  sources (V8). D-092 is still PROPOSED. The owner accepted the D-095 direction and the V6
  officer wording at the PR #126 review and required V2 document provenance by SHA-256.
- **Behaviour:** off by default. With `AI_ASSISTANT_SYNTHETIC_DEV_DECISION=D-095` on a ready
  D-094 set-up, the existing chat may use GPT-OSS 120B on any verified synthetic development
  case (approved Mock ACRA company, documents whose backend-computed SHA-256 is a tracked
  synthetic fixture's, grounded typed values,
  Mock GoldTier ids, seeded viewers, repository knowledge, no personal identifiers in the
  question). The ledger enforces at most US$1.00 reserved plus settled per Singapore day for
  every remote call. The OpenRouter key may come from the environment, the git-ignored `.env`
  or HR (memory only). AI Models shows the key status (never the key) and the spending view.
- **New owners:** `ai_assistant/synthetic_eligibility.py` (with its generated
  `synthetic_eligibility.json` and `scripts/build_synthetic_eligibility.py`) and
  `ai_assistant/key_sources.py`. Backend: `DocumentProcessingRecord.content_sha256` (computed
  at upload), case snapshot schema 16 (strict schema-15 reader), and the case-scoped
  `GET /api/onboarding/cases/{case_id}/document-digests` route.
- **D-096 HR spending controls (same branch):** HR sets on AI Models the daily limit (US$0 to
  US$1.00 per Singapore day), the calls per activation (1 to 200) and the existing ledger's
  lifetime cap (opening usage up to US$1.00 above it; a raise needs confirmation and passing
  reconciliation checks), and can refresh the OpenRouter key limit read-only. Stored in the
  model state database (`spending_controls`, CAS), applied to the active model per request
  without a restart, new activation or requalification; spend and call counts are never
  reset. No qualification-basis file changed (basis hash unchanged), so existing
  qualifications stay current.
- **Open:** owner squash merge (agents do not merge); hosted CI is
  `HOSTED_CI_NOT_EXECUTED - BILLING/INFRASTRUCTURE BLOCKED` on `c1d9069` (no runner assigned,
  0 steps) and needs the owner's PR-specific manual-CI exception and a rerun after
  1 November 2026; the owner's decision on the repeated-US$1.00-days proposal (DECISION_LOG
  D-095 B1 to B6); **deferred verification risk (PR #126 only):** physical Mongo evidence for
  schema 16 (suite `apps/backend/tests/test_document_digests_real_mongo.py`, owned by
  `scripts/run_physical_mongo_tests.py`) is NOT RUN (no MongoDB in the cloud session); the
  approved immediate use is local memory mode; run the suite before any Mongo-mode use; any
  paid run needs T7 approval.

## AI Assistant D-097 GPT-OSS naming, optional Fast configuration, answer progress and latency (branch, not merged) - 2026-10-28

Branch `claude/gracious-lovelace-bjvh2z` restarted from main `025ebc7` (PR #126, D-095/D-096,
squash-merged). Delta only; nothing here is merged or Live.
- **Decision:** D-097 (owner-authorised, local development scope). Evidence:
  `.ai-pipeline/reports/D097_GPT_OSS_LATENCY_FAST_MODE_AND_NAMING.md`.
- **Behaviour:** AI Models names the remote model *GPT-OSS 120B — Balanced* with provider,
  framework, reasoning and external-inference scope shown separately (profile id and
  fingerprint unchanged). Optional *GPT-OSS 120B — Fast* (reasoning low,
  `AI_ASSISTANT_REMOTE_LOW_REASONING_PROFILE_ENABLED`, off by default) with its own fingerprint
  and its own required qualification. The chat replaces "Thinking…" with observed stages and
  elapsed time, and adds "What this answer used". Generation metadata is read every second
  for the first 10 s within the unchanged 120 s bound (−1.9 s for a quick follow-up, offline).
- **Qualification:** basis `2bd93aeb8886…` unchanged; the existing Balanced qualification stays
  current. Fast is unqualified.
- **New tool:** `apps/assistant/scripts/benchmark_chat_latency.py` (offline, mock provider).
- **Open:** owner merge; a bounded paid Medium-vs-Low comparison needs T7 approval; the
  basis-file improvements in the D-097 report need a paid requalification decision; the D-095
  section above still reads "branch, not merged" (closeout refresh for PR #126 pending).

## AI Assistant D-098 qualification recovery, GPT-OSS-only fallback and flexible limits (branch, not merged) - 2026-10-28

Branch `feat/d098-ai-model-recovery-budget-controls`, built on PR #127's head `65535ce` and
integrated with main `f88e170` (#127's squash merge, the same tree). The owner chose it as the
canonical D-098 (Option A) and proposed replacement for draft PR #128, with #128's lifetime-cap
compare-and-set and fail-closed start-up ported. Delta only; nothing here is merged or Live.
- **Decision:** D-098 (owner-authorised, local development scope). Evidence:
  `.ai-pipeline/reports/D098_AI_MODEL_RECOVERY_AND_BUDGET_CONTROLS.md`.
- **Behaviour:** the sign-in page says why a session ended (closed reason header; lifetime and
  one-session-per-account unchanged). Qualifications left without a supervisor close as
  interrupted, never restarted. AI Models adds *Model health and recovery* (classified
  outcome, failed gates, earlier-pass validity, paid-call estimate, retry or escalation), a
  paid-run confirmation with a budget pre-check, an *AI unavailable* state instead of any
  substitute model, and flexible daily and lifetime limits (US$1.00 default, no US$1 ceiling;
  raises confirmed and gated on a finite, verified OpenRouter key limit; strictest wins).
  The chat labels case-data guidance as not AI-generated.
- **Qualification:** basis `2bd93aeb8886…` → `b4049047884e…` (budget and preflight files):
  every earlier GPT-OSS qualification is out of date on this code; an active GPT-OSS
  configuration starts as *AI unavailable*. Paid requalification of Balanced (and Fast if
  used) is required after integration and needs owner approval; none was run.
- **Persistence:** model state SQLite only: `qualifications.supervised_at` added in place; the
  `spending_controls` table rebuilt once without the US$1 CHECK, keeping its row. No Mongo
  or case-data change.
- **Also (Option A):** lifetime-cap changes are compare-and-set in the ledger; start-up never
  stands in another model for GPT-OSS (unreadable state, failed or conflicting revert
  writes, lost audit entries all handled); the spending view shows the key's own limit,
  usage and reset; an exhausted key is an owner action.
- **Open:** owner review of the replacement draft PR against main and closure of PR #128;
  owner merge; then the separately authorised Windows-local paid requalification.

## AI Assistant D-099 Claude Sonnet 5.5 under Anthropic-specific safeguards (PR #130, merged to main `d949edb`) - 2026-10-29

Branch `feat/assistant-claude-sonnet-console` (PR #130, merged to main `d949edb`). Delta only;
nothing here is activated or Live, and no paid call was made.
- **Decision:** D-099 (PROPOSED) with Option B (owner-approved policy, implemented offline):
  Anthropic-specific safeguards that are **not equivalent** to OpenRouter's. Evidence:
  `.ai-pipeline/reports/D099_OPTION_B_IMPLEMENTATION.md`.
- **Provider status:** Anthropic Messages API for Claude Sonnet 5.5 Balanced/Fast is **Mock**
  only here (offline tests); runtime composition exists behind the D-099 gate but is not
  activated. GPT-OSS/OpenRouter status unchanged.
- **Behaviour:** both Claude configurations are selectable only on a development machine with
  D-099, the D-094 interlock, four owner attestations, a dedicated workspace id and its
  attested monthly limit (at most US$5.00). Each call needs the synthetic boundary, an
  inference key (Admin keys refused), the separate Anthropic ledger (lifetime ceiling
  US$5.00, US$1.00 a day, 20 calls per activation), reconciliation within 7 days (24 hours for
  paid runs, activation and cap raises) and a free model read naming the workspace. Replies
  are verified in-band; anything uncertain is charged in full and stops later calls. No
  automatic switch to GPT-OSS or any other model.
- **Qualification:** basis `b4049047884e…` → `adec795f61bd…` (boundary words and the Claude
  modules) → `33f602653de7…` (D-099-FU1 multi-turn conversion): every GPT-OSS qualification
  is out of date once merged.
- **D-099-FU1 (2026-10-29, offline):** Claude follow-up questions are sent; the service's
  own knowledge, topic and case page terms messages after the history become top-level system
  blocks (unchanged, in order); any other prompt shape is refused before any reservation.
- **Persistence:** a second git-ignored SQLite ledger file (its path must differ from the GPT-OSS ledger's); `budget.PROFILES` gains the
  Anthropic profile (existing OpenRouter ledgers unchanged). No Mongo or case-data change.
- **Open:** HR key entry and HR-editable Claude limits stay deferred with the D-100 UI work.
- **Status update (2026-10-29):** PR #130 was merged to main `d949edb`, including D-099-FU2
  (the Anthropic-specific *Run Test connection first* refusal message). D-099 stays PROPOSED;
  nothing is activated or Live. The paid GPT-OSS requalification on basis `33f602653de7…`
  and Claude's own paid qualification each still need separate owner approval.

## AI Assistant D-100 AI Model Console Phase 1 integrated with D-099 (draft PR #131, not merged) - 2026-10-29

Delta only; nothing here is merged, activated or Live, and no paid call was made.
- **D-100 Phase 1 (draft PR #131, PROPOSED):** AI Models becomes the AI Model Console (section
  menu over Models & Overview, Providers, Spending & Limits, Qualifications & Recovery, Audit
  History; `?section=` on the existing capability-checked route). Presentation only: no API,
  qualification, gating, limit, key or permission change. Evidence:
  `.ai-pipeline/reports/D100_AI_CONSOLE_PHASE1_REQG.md` (re-QG PASS).
- **Integration with D-099 (on PR #131's branch after PR #130 merged):** main `d949edb`
  (D-099 with D-099-FU1 and FU2) merged into D-100 Phase 1, with
  narrow D-100 compatibility fixes for Claude: the paid-qualification confirmation and the
  activation warning also cover the Anthropic deployment, with Claude's own wording (separate
  ledger, GPT-OSS limits never apply, no automatic switch); the Option B readiness codes are
  named; shared spending codes are worded per provider; the inspector shows provider,
  reasoning and thinking; Spending & Limits states that its controls are GPT-OSS only. No
  backend, API or spending-control change; FU2's Anthropic-specific refusal is shown as
  written. The qualification basis stays `33f602653de7…`. Evidence:
  `.ai-pipeline/reports/D099_D100_INTEGRATION.md`.
- **Open:** owner review and merge of PR #131; D-100 Phase 2, HR key entry and HR-editable
  Claude limits are not started.

## AI Assistant D-100 AI Model Console Phases 2 to 4 (local branch, not published) - 2026-10-29

Delta only. PR #131 (Phase 1 with D-099) is merged to main `90115e4`. Phases 2 to 4 are local
commits on `feat/d100-ai-console-phases-2-4`; nothing is pushed, activated or Live, and no paid
call was made. Presentation only: no API, schema, qualification, gate, limit, key, permission,
routing or backend change; the qualification basis stays `33f602653de7…`.
- **Phase 2:** Providers shows one card per provider (OpenRouter, Anthropic API, server-configured models)
  with each configuration's availability and last connection test and who manages what (HR on
  the page, an operator on the server, the key or workspace owner at the provider). Claude
  Balanced and Fast are two configurations of one Anthropic provider. Spending & Limits keeps
  the HR-editable GPT-OSS panel and adds a read-only Claude panel with only the server's
  paid-qualification figures; the server sends no Claude key status, usage, headroom or
  reconciliation time, and the page says so.
- **Phase 3:** recovery cards show technical qualification, answer quality and availability
  apart, raw server codes, gates and provider troubleshooting; unqualified Claude
  configurations are listed (I-1) and start only through the paid confirmation; provider
  wording follows the configuration, or names no provider when it is unknown (M-1); Claude is
  never sent to the GPT-OSS spending controls (M-2).
- **Phase 4:** Audit History searches and filters only the events the browser loaded (the
  server's most recent 100) and says so; the dialog background is inert with scroll locked
  (D3); a closing dialog never pulls focus out of a newer one (D5); badge variants are
  unit-tested (D6); console text meets 4.5:1.
- **Open:** independent Quality Gate, owner review and publication authorisation. HR key entry
  and HR-editable Claude limits stay deferred (they need new backend authority).

## Zero-touch D-101 Partnership and Government entity types (branch, not merged) - 2026-10-30

- **Branch `feat/zero-touch-entity-types` (D-101 candidate, owner approval in chat 2026-10-29;
  Shane to confirm):** the database demo set covers one clean case per entity type. Company
  (Alpha) is unchanged.
- **Partnership (Gamma `209990103C`):** registry partners by name and role only; shares come from
  a reviewed partnership agreement, are suggested only, and count after the RM submits them
  through the existing manual ownership evidence path. Fail-closed cross-checks: partner sets,
  duplicates, positive shares, a Decimal total of 100, and declaration = agreement.
- **Government (DEMO PARKS FYP TEST AUTHORITY `T99GB0105G`, renumbered by D-114):** local synthetic identity labelled
  "not ACRA-registered; government status from reviewed document". The Ownership & UBO stage
  holds a Government status step (`GOVERNMENT_STATUS_REQUIRED`), met only by a reviewed status
  document plus an explicit RM confirmation; readiness then records 0 UBO candidates. Replaces the
  classification-only `209990105E` fixture. D-125 (candidate, case schema v20): the RM also keys in
  the founding statute (matched to the document's Founding Instrument after normalisation), an
  optional section and the RM-asserted type of body; older confirmations must be confirmed again.
- **Shared:** a bounded KYC type / legal form compatibility table (mismatch UNSAFE; unknown form
  UNSAFE for automatic candidates only), a new `GOVERNMENT` registry legal form, case snapshot
  schema v17, and regenerated D-094 synthetic boundary and eligibility manifests.
- **Done:** database-classification Partnership and Government journeys rewritten (E2E); integrated
  acceptance run locally.
- **Open:** independent Quality Gate to PASS, pre-PR and publication authorisation.

## AI Assistant D-102 Claude ceiling US$30.00 and HR-editable Claude limits (local branch, uncommitted) - 2026-10-29

Delta only. Branch `feat/claude-hr-spending-d102` from main `d90ab6a`; nothing committed, pushed,
activated or Live, and no paid or network call was made.
- **Decision:** D-102 (PROPOSED): Claude's ceilings US$30.00 lifetime / US$5.00 a day (20 calls
  unchanged); HR sets Claude's daily allowance, calls and Anthropic ledger cap on Spending &
  Limits via Claude-only routes; raises (daily, calls or lifetime) need confirmation and a
  24-hour reconciliation; a strictly lower lifetime cap is always allowed.
- **Independent QG:** CONDITIONAL PASS on `f1d32387…` (Low findings only); L1 to L3 remediated
  at the owner's direction, L4 recorded in D-102 without change; re-review of the amended
  candidate pending.
- **Changed:** API (two PUT routes; `claude` block in the budget view), persistence (new
  `claude_spending_controls` table in the model admin SQLite, additive), configuration bounds,
  business rule (spending ceilings), frontend (editable Claude panel). No auth/RBAC, connector,
  mapping or architecture change; GPT-OSS behaviour unchanged.
- **Qualification:** basis `33f602653de7…` → `4c54e4dd9dbd…`.
- **Open:** independent Quality Gate, owner acceptance of D-102, commit/publication
  authorisation; then the separately approved paid qualifications.

## AI Assistant D-102 owner acceptance and latest-main integration (branch `feat/claude-hr-spending-d102-int`, not published) - 2026-10-30

Delta only. D-102 is ACCEPTED by the owner for synthetic-only FYP development (including the
tightened Claude call-limit raise). The reviewed commit `93d154d` (content `e4f58e36…`, re-QG
PASS) is cherry-picked onto main `2911b54` (PR #133): application code and tests are
byte-identical; `docs/PROJECT_STATE.md` merged without conflict, keeping both histories.
Nothing is pushed, activated or Live; no paid or network call was made.
- **Evidence:** `.ai-pipeline/reports/D102_QUALITY_GATE.md`, `D102_REQG.md` and
  `D102_INTEGRATION.md`. The full assistant suite is not a clean PASS on this machine (14
  Windows `Errno 24` failures, identical on main, passing alone).
- **Blocker found on main (not D-102):** main `2911b54` fails
  `test_the_boundary_file_is_current`: PR #133 added the backend string `onboarded`, so the
  synthetic boundary needs regenerating (one new code word; the qualification basis moves).
  Not changed here; it needs an owner decision.
- **Open:** that boundary decision, independent integration QG, `pre_pr_check.py`, owner
  publication authorisation, then the separately approved paid requalifications.

## AI Assistant D-102 re-integrated after PR #134 (branch `feat/claude-hr-spending-d102-int2`, not published) - 2026-10-30

Delta only. PR #134 (synthetic boundary `onboarded`) is merged to main `25ed072`, resolving the
boundary blocker recorded above. D-102's two integration commits are replayed onto it with
byte-identical content; the synthetic boundary is current and the qualification basis is
`65f22e46c509…`. Evidence `.ai-pipeline/reports/D102_INTEGRATION_R2.md`; the full assistant
suite still has the 14 Windows `Errno 24` failures (not a clean PASS).
- **Open:** independent integration QG, owner publication authorisation, then the separately
  approved paid requalifications.

## AI Assistant D-104 data access policy and provider-neutral D-095 (branch `feat/assistant-data-access-policy`, uncommitted) - 2026-10-30

Delta only. Owner-authorised direction:
- AI Models gains *Data Access & Privacy* ("Restrict AI to verified synthetic cases").
  OpenRouter, Anthropic and any model on a non-loopback endpoint (with or without model
  management) are locked to verified synthetic cases. A loopback local model answers every authorised case by default (D-093
  unchanged) and is restricted when HR says so or when the policy is unreadable.
- D-104 A1: Claude's D-095 mode no longer depends on OpenRouter's endpoint, reasoning settings
  or attestations. GPT-OSS's mode is unchanged.
- Each policy change and its audit row are written atomically.
- The qualification basis moves `65f22e46c509…` → `598cfe14753d…`, so every current
  qualification, including Claude Balanced's, goes out of date once this runs.
- Evidence class: offline mock and local only.
- **Open:** independent QG of the final candidate, the owner's commit and publication
  authorisation, `pre_pr_check.py` on the commit, then separately approved paid requalification.

## AI Assistant D-106 HR session keys and qualification progress (branch `feat/assistant-session-credentials-int` on main `1c6ec4f`, uncommitted) - 2026-10-30

Delta only. Owner-approved (D-106):
- AI Models → Providers has a key section for OpenRouter and one for Anthropic (shared by
  Claude Balanced and Fast). Each has a masked input, Save for Session, Clear Session Key and
  Test Connection, and shows the key's source, status, expiry and fallback.
- Key order: HR session key, then the process environment, then `.env`. The HR key lives in
  memory only and is checked against that HR session's own `/api/auth/me` before each use.
  Sign-out, expiry, revocation, Clear or a restart drops it. A server key is used after it only
  once the provider's existing preflight identity checks pass. A qualification process gets
  the key on standard input only.
- Qualifications & Recovery shows a spinner, server turn counts as a progress bar
  (indeterminate without a total), the provider, the stage, the active model and the final result.
- The qualification basis moves `2c9d72cf0ae4…` → `7e386b8a69e1…`, so Claude Balanced needs
  one new authorised technical qualification on the merged code.
- Evidence class: offline mock and local only.
- **Open:** independent QG, owner publication authorisation, `pre_pr_check.py`, owner merge,
  then the authorised Claude Balanced qualification, activation and one Garden RM verification.

## AI Assistant D-107 Claude set up by HR (branch `feat/assistant-claude-hr-enablement`, integrated onto main `c6b37f2` as `feat/assistant-claude-hr-enablement-int`) - 2026-10-30

Delta only. Owner-approved (D-107):
- HR sets Claude up on Providers → Anthropic. HR reads the workspace the key reports (free),
  confirms the owner's four statements and monthly limit, and enables Claude for verified
  synthetic cases. The record lives in the model state database with an audit row; no decision
  or attestation setting is needed. Without a record the D-099 environment configuration still
  applies.
- The D-091/D-092/D-094/D-095 decision names are replaced for Claude by the runtime checks they
  stood for (model on, loopback CLM backend, local origins). The workspace pin, Claude's ledger
  and limits, reconciliation, the D-095 checks and the no-switch rule are unchanged.
- Data Access & Privacy separates "provider enabled" from "verified synthetic cases only".
- The qualification basis moves `7e386b8a69e1…` → `80448c6d7d61…`; on main `c6b37f2` (D-101) `5adfe7ec2c58…` → `5dc26b296026…`.
- Evidence class: offline mock and local only.
- **Open:** independent QG, owner publication authorisation, `pre_pr_check.py`, owner merge,
  then HR setup, one authorised Claude Balanced qualification, activation and one Garden RM
  verification.

## AI Assistant D-108/D-109 persistent data root in use and cutover closure (branch `feat/b0-storage-cutover-closure`, uncommitted) - 2026-10-31

Delta only. Owner-approved (D-109; D-108 merged as PR #143):
- The owner's local assistant runs on a protected per-user data root outside the repository
  (Assignment 2). Stores were copied with the SQLite backup API and verified by logical
  fingerprint; the earlier stores and launchers are unchanged history. Recovery is forward only.
- One approved paid case question on a verified synthetic case passed on the new root. A
  separate, unapproved Claude Fast requalification (2 paid calls) is recorded as a deviation and
  was not activated. Activation, qualifications in force, breakers and limits are unchanged.
- New operator tools `apps/assistant/scripts/storage/` (backup, fingerprint, data-root check)
  with tests on synthetic stores, a parameterised launcher template, runbook section 7.2 in
  `docs/integration/AI_MODEL_CONFIGURATION.md` and sanitised evidence
  `docs/evidence/B0_STORAGE_CUTOVER_2026-10-31.md`.
- The qualification basis is unchanged (`5dc26b296026…`); no runtime code changed.
- Evidence class: Local. Claude ledger reconciliation is due under a separate authorisation.
- **Open:** independent QG, `pre_pr_check.py`, owner publication authorisation and merge.

## AI Assistant B2 answer quality and B3 final validation (branches `feat/b2-assistant-quality`, `feat/b3-final-validation`, local commits) - 2026-10-31

Delta only:
- B2-0: the Claude benchmark harness is on the main line (offline transport tests); degraded-mode
  retrieval is measured per role with a regression gate (recall@3 0.96 with past cases, correct
  "nothing" 1.00); the service adds about 82 ms around an instant model. The owner's 17 scored
  Sonnet Fast answers are attributed: every gap that cost acceptance is a missing approved
  catalog line or one dropped offered refusal, all in basis files, so D-111 (PROPOSED) lists
  the exact changes, the qualification questions and the paid steps. Nothing in D-111 is
  implemented; the basis (`5dc26b296026...`) and every guardrail are unchanged.
- B3: `docs/demo/AI_ASSISTANT_FINAL_UAT.md` and
  `docs/evidence/AI_ASSISTANT_FINAL_VALIDATION_2026-10-31.md` record what passed offline and
  what is NOT EXECUTED (live reconciliation, paid steps, restart and persistence, full
  lifecycle E2E without Mongo and Tesseract, semantic retrieval).
- **Open (owner):** D-111 decisions; publication and merge of the three branches.

## AI Assistant D-118 paid-model sessions and guided setup, simplified for the POC (branch `feat/d118-paid-sessions`, PR #156) - 2026-11-04

Delta only. Owner direction "Final Scope Correction: Simplify for FYP POC" (amends D-118):

- **Guided flow.** AI Models opens on *Set up AI*: select, key, run qualification, activate.
  US$5.00 is the default and maximum session allowance. The free check runs first, then one paid
  consent.
- **Fresh stores.** Session stores (`data/budget/sessions/...`) are created from the console,
  with no CLI and no migration. Earlier-design ledgers are refused as `LEGACY_STORE` and never
  used. `archive_accounting_stores.py` copies them non-destructively.
- **No reconciliation dependency.** Every session store is provider-capped. Claude has no windows,
  OpenRouter usage does not have to match, and limit raises need no reconciliation; P1 and D-110
  are optional. The provider's limit is the backstop.
- **Stops.** HR resumes financial stops in the console, keeping every charge. Routing and
  integrity stops go to the owner via `resume-after-review`. Nothing is retried automatically.
- **Removed.** `ledger_migration.py`, `migrate-v2`, the Claude opening question and the OpenRouter
  automatic reconciliation.
- **Basis.** Moves `77e50313a62c…` → `17a3172e1607…` (`code_vocabulary` only).
- **Evidence class:** Local (mock providers, disposable stores).
- **Not done (owner):** archiving or switching the owner's live stores, paid requalification,
  restart, merge.

## AI Assistant B1 Phase B: HR reconciliation of the Claude ledger, D-110 (branch `feat/b1b-hr-reconciliation`, local commits) - 2026-10-31

Delta only. D-110 owner-approved for development 2026-10-31 (Q12 clarified):
- New `ai_assistant/claude_reconciliation.py` (not a basis file) and routes `GET|POST
  .../budget/claude/reconciliation[/preview|/apply|/runs/{run}/resolve]`, HR only. The existing
  `BudgetLedger.reconcile` stays the accounting rule; a subclass checks the previewed state and
  exactly what was written inside its one write transaction.
- A cross-process reconcile lock and a durable intent marker beside the Claude ledger; the
  operator's script takes the same lock and refuses while a marker exists (owner override
  recorded); new script commands `verify`, `runs`, `resolve-report`, `owner-close`,
  `attest-legacy-retired`.
- Q12: a run is applied only when commit and attribution are proven, failed only when
  non-commit is proven, otherwise unresolved for the owner; LEDGER_BUSY never decides a run.
- Spending & Limits gains the HR reconcile form (preview, typed-figure confirmation, runs,
  resolve). No release, breaker reset, limit change or deadline extension by HR.
- Basis unchanged (`5dc26b296026…`); synthetic boundary current. Evidence class: Local.
- **Open (owner):** S1 to S3, the P1 attestation, publication, merge, an approved assistant
  restart, and the first live reconciliation before 2026-11-07 09:42:37 SGT (or the CLI fallback).

## AI Assistant B1 Phase A: read-only Claude ledger view (branch `feat/b1-claude-ledger-view`, uncommitted) - 2026-10-31

Delta only. Owner-approved (B1 Phase A only; Phase B reconciliation is not implemented):
- `GET /assistant/admin/models/budget` adds `claude.reconciliation`: key alias, last
  reconciliation, chat (7-day) and paid (24-hour) window end times and freshness, the
  ledger's estimate of the key's cumulative usage (baseline + charged since), open
  reservations and call counts by state and verification. HR only (`MODEL_CONFIG_MANAGE`).
- Read-only: the ledger is read without recovery, the GPT-OSS ledger is never read, and no
  route, authority, limit, breaker or reconciliation rule changed.
- Spending & Limits shows the figures in a read-only Claude panel with overdue warnings, times
  labelled SGT, and the ledger baseline apart from Anthropic's last report (a kept overcount is
  shown and explained; a mismatch in the sums is flagged).
- QG L1: all Claude ledger figures in one response come from one ledger state (reads bracketed by
  SQLite `data_version` on a read-only connection, re-read on change, withheld if unstable).
- The qualification basis is unchanged (`5dc26b296026…`) and the synthetic boundary is current.
- Evidence class: offline mock and local only.
- **Open:** independent QG, owner publication authorisation, `pre_pr_check.py`, owner merge;
  the running assistant shows the view only after an owner-approved restart.

## AI Assistant D-118 usability remediation (branch `fix/d118-setup-usability`) - 2026-11-04

Delta only, within D-118 (decision log: usability remediation U1 to U4):

- **Root cause.** The paid question list defaulted to empty, so the US$1.00 qualification showed
  "—" and was refused as "no room". It is now the approved `P01#1,P02#0` (two calls) by default.
- **Named causes.** The estimate carries `limits`, `blocking` and `unavailable`. The session
  allowance counts. Store and setup states are never reported as a budget shortfall.
- **Wizard.** It needs a passed connection check before step 3, shows the cost and limits, and
  can create a missing Claude session store for an existing record.
- **Evidence.** `apps/assistant/tests/ui_stack.py` runs the real assistant with mock providers
  for `e2e/ai-models-setup-real-stack.e2e.ts` (scenarios A to H). Class: Local.
- **Basis.** Unchanged.

## Dashboard management view, D-127 provisional SLA/attention and ADR-015 AI insights (branch `feat/dashboard-insights-cases-paging`, committed `69c0784`, not published) - 2026-11-13

Delta only. The Onboarding Dashboard adds management KPIs, a previous-period comparison
(bounded ranges only), an onboarding funnel, a turnaround trend, processing vs waiting per
step, exceptions by country, rework, team comparison, workload running/blocked/
overdue counts and All cases triage (country, attention, SLA and exception filters; highest
attention first). The Cases tab shows 10 rows per page.

Director only: a "Needs your action" card lists GoldTier recovery cases and policy proposals
awaiting their decision (the Policy page rule), and team comparison adds SLA, overdue, high
attention, end-to-end and blocker fix time. Proposals load through a read-only `/api/policies`
query keyed by the signed-in user; if it fails, only that card says so.

- **Authority.** SLA (10-day target from creation), at-risk, attention level and rework follow
  D-127, `PROJECT_DEFINED_PROVISIONAL`. They are display and ordering only, with no workflow,
  readiness, routing, approval or GoldTier effect. Q-016 stays open; there is no assignee, so
  workload uses the creator.
- **AI insights (ADR-015, D-128).** Browser rules turn the all-time dashboard figures into
  findings and send only those to `POST /assistant/dashboard/insights` in the AI Assistant
  service. The local model writes them, or the active API-key model (Claude, GPT-OSS) under
  D-122 and its spending limits, with the local model as fallback (D-128 I7). Paid dashboard
  calls share the chatbot's call limit and allowance and can briefly make Claude refuse a
  chatbot question as busy (owner-accepted). Every number
  in the reply is checked against the findings; a rejected or failed reply hides the panel.
  One model request runs at
  a time and results are cached per user for 30 minutes. Directors get Director findings
  (recovery cases, policy proposals, team gaps) first. Advisory only: no case, approval or
  GoldTier effect, and the CLM backend stays model-free. Class: Local (the API-key path is
  covered by tests with fake models only; no paid call was made).
- **Not included.** Dashboard chat and recommended actions. Weekly targets and workload
  utilisation have no defined target or capacity data.
- **Sample data.** The fixed, unlabelled sample portfolio mirrors every new figure. A
  previous-period comparison is not shown while it is overlaid. RMs and onboarders see the same
  view, limited to their own team's sample and real cases; the Director sees all teams.
- **Evidence.** Class: Local. Backend `test_dashboard_insights.py` and `test_phase13_dashboard.py`;
  frontend `dashboardInsights.test.tsx`, `SampleCaseDetail.test.tsx`, `AiInsights.test.tsx` and
  `onboardingSample.test.tsx`; assistant `test_dashboard_insights.py`.
