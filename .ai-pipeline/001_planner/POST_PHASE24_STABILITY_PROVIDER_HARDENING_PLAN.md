# Post-Phase24 stability and provider hardening: diagnosis and proposed plan

Date: 2026-10-02 (Asia/Singapore).
Status: PLANNING CHECKPOINT - user approval required before Slice A.
This is the proposed program and current diagnostic handoff, not implementation,
independent Quality Gate acceptance, or publication readiness.

## Goal, architecture and compatibility boundary

Goal: stable local startup, truthful official ACRA Marketplace Mock evidence,
reproducible upload/demo journeys, usable current blocker recovery, realistic local
GoldTier Mock behavior, and explainable policy-impact simulation.

Extend the existing persistence converter, registry/cache coordinator, Decimal
ownership engine, blocker-decision policy, target connector/ledger and policy owner.
One coordinator writes implementation. Specialists and mini-gate reviewers are
read-only. No second state machine, ownership calculator, cache, authorization,
persistence authority or provider fallback.

Tech stack remains existing Python/FastAPI/Pydantic/PyMongo, React/TypeScript,
TanStack Query, Vitest and configured Playwright. No dependency upgrades.

Keep schema 8, strict legacy guards, frozen historical policy, identity/revision CAS,
insert-only create, update-only mutation, no resurrection, target no-replay, scoped
frontend state and backend authorization. No schema bump or original-data migration
is proposed for the reproduced v7 defect. Normal public/browser model exclusions
remain intact.

Scope naming is a bounded post-Phase24 maintenance program. No Phase25 designation
is inferred from chronology. Current merged documentation retains stale
candidate/pending-gate wording; source and current contracts take precedence.

## TaskStartSnapshot and evidence identity

| Item | Observed value |
|---|---|
| Normal main checkout | C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm |
| Main state at preflight and fetch | clean, on main |
| BASE_SHA / source HEAD / fetched origin/main | 707765b1d51172c64b851c9e46e68b3c23006789 |
| Task worktree | C:/Users/shane/.codex-clean2/worktrees/post-phase24-stability-provider-hardening/data-dividends-zero-touch-clm |
| Task branch | feat/post-phase24-stability-provider-hardening |
| Worktree before this planner file | clean, no source changes |
| Git owner | coordinator; existing worktrees preserved |
| Specialist route actually dispatched | four fresh GPT-6.1 Sol / Extra High read-only agents |
| Scheduling | three specialists concurrently, fourth when a worker slot opened |
| Coordinator model | current chat model; its exact model/effort cannot be independently read or switched here |

Fetched origin successfully. Managed worktree was created from origin/main and the
requested branch created in it. No reset, clean, stash or main checkout changes.
Current-source inspection and fresh diagnostic tests refer to the unchanged SHA above.
Historical Phase24C PASS is context, not this program's independent verdict.

Change classes conservatively selected:
PERSISTENCE, EXTERNAL_PROVIDER, BACKEND_DOMAIN, BACKEND_API, FRONTEND_UI,
FRONTEND_STATE_CACHE, AUTH_RBAC_SECURITY, ARCHITECTURE_REFACTOR, CI_TOOLING, DOCS_ONLY.
The dev_context selector ran with one argument for each affected class.

## Baseline and authority read-set

Controlling assignment: user attachment 5077a4fe-1f14-4c80-836b-bd9e67f1ca73,
especially IMPORTANT SESSION CONTROL. It requires completing preflight, all four
investigations and coordinator reconciliation, then waiting for explicit approval
before Slice A.

Read root/backend/frontend AGENTS, DEVELOPMENT_WORKFLOW, ARCHITECTURE, PROJECT_STATE,
CODEX_WORKFLOW, .ai-pipeline/README, repository skill routing, branch protocol and
OPEN_QUESTIONS. Specialists read their scoped current contracts, decisions, owners
and tests. Relevant baseline includes PERSISTENCE_RECOVERY_PROFILE,
POLICY_ACTIVATION_CONTRACT, POLICY_TEAM_IDENTITY_ADMIN_PROFILE, D-061/D-063/D-064,
current ACRA and GoldTier contracts, and Phase24C planner/nearest accepted gate.

Scope-specific worktree, persistence, external-provider, frontend cache, security,
architecture, debugging, continuity, planning and verification workflows informed
this analysis. These workflows do not grant implementation or publication authority.

## Reconciled diagnosis

| Finding | Classification | Evidence and minimum response |
|---|---|---|
| Valid populated v7 envelopes fail v8 conversion | Confirmed defect | persistence/models.py:420-421 dumps the public model, omitting nested exclude=True fields. Preserve validated typed fields using the existing v5/v6 conversion pattern. |
| Reported four original v7 records | Unverified correspondence | Original database was not accessed. The deterministic source defect is proven independently; matching original failures needs sanitized error locations/types only. Do not label original records corrupt or intermediate. |
| Literal corrupted punctuation | Confirmed defect | api_models.py:818/939/982 bad dash; 1900/1958/1959 bad middle dot; current ZERO_TOUCH_AUTOMATION_POLICY.md:1 bad dash. Fix source and add scoped guard/decoded-JSON tests. |
| Optional Amend shown NOT_REACHED | Confirmed projection defect | onboarding.py:2333-2353 retains AMEND_NOT_REQUIRED with no attempted call; main.py:849-953 omits its SKIPPED projection. Use retained ledger/outcome evidence, with zero Amend calls. |
| Search text denies available browser recheck | Confirmed stale copy | CaseStatePanels.tsx:290 contradicts existing IdentityCorrectionForm/API bounded read-only recheck. Correct wording and route to existing recovery. |
| Garden partnership percentages/relationships | External contract blocker | Legal-form guard is correct. People/Officers request-side operations lack exact ownership response/economic/control authority. Keep Q-012 open and LOCAL reviewed supplementary evidence. |
| Second official company | External sample/contract blocker | Supplied basic/shareholder/capital sample UEN sets have no common member. Existing shareholder/capital examples lack same-UEN basic identity; other basic identities classify OTHER or business/partnership. No suitable official company is currently proved. |
| Complete official cache binding | Unsupported current acquisition capability | Official relationships remain unsupported; cached PARTIAL prefixes may suppress transport but cannot become a COMPLETE case binding. |
| Stateful/reusable GoldTier Mock | Enhancement | Current Mock Search uses fixed keys; Shell does not retain customer identity; Policy retains only partial-failure lookup state. Composed Mock has no actual verified readback. |
| Explainable policy monitor | Enhancement | Existing proposal_impact already returns changed/current/default/proposed and before/after metrics/runtime samples. Extend it; do not rebuild the policy system. |
| Existing NO_MATCH/cache/progress semantics | Preserve | NO_MATCH succeeds; cache reuse satisfies acquisition as COMPLETE; exact existing customer legitimately skips ACRA/Shell/Policy; progress already counts COMPLETE/EMPTY/SKIPPED. |

### Mongo forensic evidence

MongoCaseStore._persistence_value deliberately retains persistence-only fields.
The v7 converter's public model_dump removes automation.ownership_provider_binding_id,
exception authoritative_evidence_digest, reconciliation fingerprints, raw observation
values and source record IDs. normalized_value itself remains, but its validation
requires the accompanying raw_value.

A minimal legitimate v7 pending-automation fixture passes legacy model validation,
recursive unknown-field rejection and Phase24C legacy guards. Conversion fails with:
loc=("automation","ownership_provider_binding_id"), type="missing".
The codec projects the failure as PersistenceDataInvalidError.

Five existing synthetic scenarios reproduced conversion failures:
STRAIGHT_THROUGH and OWNERSHIP_CYCLE: 16 errors each;
LOW_CONFIDENCE and DOCUMENT_DISCREPANCY: 20 each;
TECHNICAL_FAILURE: one missing binding.
In-memory typed-field construction passes all five. Minimal persistence serialization
matches the original except schema_version; the source input is unchanged. Missing
binding, unknown nested fields and cross-case identities still fail closed.

Existing physical coverage is insufficient: the genuine v7 Phase24C test is staged-only;
a test with a v7 title now asserts a stored schema 8. Add populated true-v7 restart
coverage rather than relying on those titles.

### Encoding and blocker inventory evidence

The specialist's tracked active-scope audit covered 255 files. No invalid UTF-8,
replacement characters or frontend source literal hits were found. The defect is
specific source literals; no global charset/JSON serializer change is justified.

Reuse blocker_decision_policy: 26 rule groups / 56 supported OPEN codes at this SHA.
Coverage includes 19 BusinessExceptionType values, 17 readiness blocker values and
five document auto-clear blockers. Six warnings and one auto-confirm note are separate
nonblocking projections. Declared support does not prove a current action: evaluation
intersects available actions, current bindings and required inputs, and rejects unknown
or mismatched decisions.

## Change necessity, owners and execution order

A no-code workaround cannot preserve missing historical persisted evidence or correct
the optional-Amend projection. Owner-local source repairs are necessary for those
defects. Catalogue/demo improvements should reuse existing owners; absent provider
contracts require documentation/questions, not speculative connector code.

Implementation route after approval: coordinator inline, with read-only specialists
and fresh independent mini-gates. No multiple implementation writers.
User-requested failing-first regressions apply to each behavioral slice; verify the
failure, make the smallest owner repair, then run focused/neighboring checks.

| Order | Slice | Proposed bounded delta | Likely owners/files |
|---|---|---|---|
| 1 | A: startup/compatibility/encoding | Typed v7 conversion; genuine populated legacy regression/restart tests; corrupted literal repair; scoped encoding guard and decoded API assertions | persistence/models.py, test_phase12_persistence.py, test_phase12_real_mongo.py, api_models.py, current automation-policy contract and relevant projection tests |
| 2 | B: registry/demo evidence | Preserve partnership guards; prepare Garden supplementary-evidence journey; warm distinct synthetic cache sample through existing coordinator; record second-company authority gap | registry adapter/acquisition/cache tests, existing fixture/generator owners, demo matrix and Q-012 |
| 3 | C: blocker/progress semantics | Generate/test catalogue from current blocker owner; map current available UI recovery; optional-Amend SKIPPED projection; stale Search copy; retain existing neutral statuses/progress | blocker_decision_policy.py and tests, zero_touch_orchestration action projection, main.py target projection, api_models.py, CaseStatePanels/CaseDetail and existing browser tests |
| 4 | D: GoldTier study and Mock realism | Read-only portal study; local synthetic customer records and deterministic ambiguity/full-Amend failure; actual Mock readback through existing ledger; maintain legacy injections | mock_goldtier.py, existing mapper/onboarding/target ledger, connector/CLM/zero-touch tests |
| 5 | E: policy impact advisor | Read-only helper under PolicyManagementService; named fixture transitions, metric deltas, reasons/materiality and qualitative cache implications; shared HR/Director evidence | policy_management.py, existing tagger/evaluators, API projection/types, PolicyRules and policy tests |
| 6 | F: demo pack | Actual synthetic uploads; exact steps/states/call counts/actions/environment truth; bind expected rows to tested scenarios | apps/backend/tests/fixtures/uat, existing generation scripts, docs/demo/POST_PHASE24_DEMO_MATRIX.md and BLOCKER_RECTIFICATION_GUIDE.md |
| 7 | G: limitations/questions/final gates | Classify FIXABLE_NOW / NEEDS_CONTRACT / NEEDS_SPONSOR_POLICY / NEEDS_EXTERNAL_ACCESS / OUT_OF_SCOPE_PRODUCTION; document missing fact, safe behavior, minimum answer and unblocked work | OPEN_QUESTIONS, decision/authority records as required, accepted-state context, combined gate/publication handoff |

Each major slice ends with focused verification and a fresh independent read-only
mini-gate. Supported findings return to the coordinator for bounded remediation and
fresh review. Freeze candidate identity before review; changed content invalidates its
old verdict. Do not broaden changes into central-file refactors or dependency churn.

### Slice A acceptance and test matrix

1. Encode a true populated schema7 synthetic fixture through the persistence serializer.
   Reproduce the missing-field failure with a failing regression before the repair.
2. Construct schema8 from validated typed fields, matching v5/v6. Use normal validated
   construction, not model_construct, public-dump serialization or weakened guards.
3. Test supported schema1..8 readers using their exact historical shapes; preserve all
   retained nested fields, revision, policy thresholds and historical absent parameters.
4. Assert no input/storage rewrite and no current ACTIVE-policy lookup. API/browser
   exclusions must remain excluded.
5. Reject missing/unknown/malformed versions, nested fields, identity mismatches,
   missing hidden evidence and smuggled Phase24C parameters/version2 tags.
6. Physical restart covers real stored schema7 automation/reconciliation/exception,
   identity/history/confirmation and target uncertainty. Prove no provider replay.
7. Fix only demonstrated active punctuation; guard the demonstrated corrupt codepoint
   sequences, allow valid Unicode and assert decoded JSON titles/separators.
8. Run startup against representative disposable legacy data. The user's original
   configuration/database startup is not yet executed or certified here.

Repair retirement: replace the lossy v7 conversion only. Retain promised legacy readers;
do not remove public model exclusions or historical evidence artefacts.

## Mongo strategy and current capabilities

No original clm_poc, .env, Mongo URI, raw document/provider payload or private credential
was accessed by the coordinator or specialist. The ACRA specialist inspected only
minimum exact private collection/catalogue operation metadata in memory; no private
file was copied to the worktree and no raw body or person data was reported.

Prefer deterministic sanitized fixtures already reproduced. Provision a task-owned
Mongo service and newly generated allowlisted databases through mongo_test_safety.
Use process-memory connection provisioning, write/restart/read/adverse/CAS/deletion
checks and verified cleanup absence. Never connect a test to clm_poc.

The canonical nine-suite physical wrapper currently omits Phase24C's additional suite.
Place the new v7 test in an already registered suite; run the Phase24C suite explicitly
in final verification, or deliberately register it with runner tests.

Observed runtimes: Python3.12.10, Node22.23.3, npm10.9.9. Main .venv supplies executable/
dependencies only; worktree imports remain authoritative. Worktree node_modules is
absent; bootstrap from unchanged lockfile before frontend tests, with no upgrades.
Browser control and managed-worktree tools are exposed. Browser/portal login and Mongo
connectivity are not proved in this session. Docker engine probing was permission-denied
under the current sandbox; later provisioning requires narrow authorized tool access.
No shared ports or database/server were reserved or changed during planning.

## ACRA call budget and demo truth

Planning external ACRA calls: 0. Ordinary tests remain offline.

If fresh Garden official-Mock acceptance is demonstrably required after offline checks
and approved implementation, announce exact operations/sample/need/ceiling first:
Garden11111999A, OAuth at most1 and entityBasicInformation calls at most2
(profile and officers): maximum3 HTTP requests, no retries/token refresh.
The current task conditionally authorizes bounded read-only official Mock verification;
a separate announcement identifies its exact use. No call is authorized by elapsed time.

Second-company network budget remains0 until one supported coherent company sample and
exact dependent schemas are supplied. Any later candidate/shareholder/capital budget
must be separately specified after that authority is reconciled. Repeated catalogue
probing cannot supply missing semantics. People, LLP, relationships, production/live
endpoints, GoldTier/PingFed and external mutation calls are0 in this ACRA verification.

Garden11111999A stays PARTNERSHIP. Official identity/officer evidence plus explicitly
reviewed synthetic client ownership declaration can complete local Mock GoldTier
submission; it does not establish official percentages, legal UBO or final approval.
Existing offline Garden PDFs are protocol-fixture documents; do not present their
synthetic address as actual official evidence. Prepare a matching current synthetic
client document, using the accepted COI profile and preserving real reconciliation.

The second official-company journey is blocked, not fulfilled. Request a same-UEN basic
company profile/officers and any supported ownership schema/sample; if quantitative
ownership is absent, a supported coherent identity plus truthful manual remediation
may be sufficient. Never combine unrelated sample UENs or fabricate provenance.

Third sample: existing synthetic Merlion202400001A, distinct from Garden and the future
second company. Warm COMPLETE evidence through the normal owner in
MOCK_ACRA_SYNTHETIC_V1, then create a separate case with CACHE_HIT and0 new ACRA calls.
If Mongo caching is configured, prove reuse across repository restart. Label it
synthetic Mock. Official cached PARTIAL-prefix suppression is separate evidence and
cannot be called COMPLETE official cache binding.

## GoldTier browser study and Mock boundaries

Portal URL/manual authenticated login is a prerequisite for the study; no separately
supplied access or authenticated state is assumed available in this chat.
Use browser tooling only at the supplied sandbox portal. Stop at login and have the
user enter credentials manually. Inspect only authorized synthetic/sandbox records,
read-only. Do not inspect cookies, tokens, storage or auth headers. Avoid screenshots
with credentials or private record data; retain sanitized observations only.

Checklist: navigation/workflow concepts; customer identity/search filters; existing
versus new customer display; overview fields; visible lifecycle/policy/task/amend/audit
states; correlation identifiers for synthetic cases; explicit validation reasons and
visibly evidenced Ready-for-Approval terminology. Portal UI does not establish API
schema, idempotency, legal approval or safe retry semantics. If browser tooling fails,
provide the checklist for manual observation rather than guessing.

Enhance Mock records only from current accepted request fields and observed/authorized
concepts. Shell has no UEN; successful Policy's accepted external key supplies that
binding. Do not derive UEN from source_case_id. Use existing ledger readback/operation
fields and strict response validators. Test new customer, exact reuse, ambiguity,
Policy failure, full/partial Amend failure, duplicate/concurrent dispatch and no replay.

Initial Mock customer state is process-local and must say so. Cross-process persistent
Mock provider state is a separate architecture/persistence decision, not presumed here.
Durable case ledger restart/no-replay still requires physical evidence. Sandbox remains
SANDBOX_PARTIAL and never falls back to Mock. Existing optional Amend stays optional.

## Policy advisor scope

Keep current proposal/approval/activation owner and frozen case policy. The advisor is
a pure read-only helper, not a persisted monitor, scheduler, trained ML model, compliance
score or new policy authority.

Show parameter current/default/proposed values, affected stage, named synthetic fixture
old/new outcomes, newly automatic/review/candidate transitions, precision/recall/F1
deltas and benchmark identity, explanatory reason codes, and deterministic descriptive
materiality. Use existing evaluator functions/owners; no second ownership calculation.
More automation alone is not evidence of beneficial or compliant results.

Registry freshness/negative TTL may show qualitative reuse/miss direction or outcomes
at defined synthetic evidence ages. Do not invent production call-volume forecasts.
HR edits/simulates; a different Director sees the same current evidence before decision.
Threshold below/equal/above, coupled values, stale proposals, repeated read-only calls,
actor/session changes, late responses and old-case freeze require tests.

## Verification, expected cost and risk

Fresh planning evidence actually executed:
- coordinator: test_phase24c_policy.py,13 passing tests, one existing deprecation warning;
- persistence specialist:42 selected persistence regressions pass, same warning;
- five deterministic v7 failure/counterfactual probes plus missing/unknown/cross-case
  adversarial checks, no stored artefacts or source edits;
- tracked encoding/source/contract inspection by the four specialists.
No full backend/frontend/browser/physical/external acceptance or new independent gate
has run for this program.

Focused commands after approval use the main .venv executable with worktree PYTHONPATH,
Python-B/PYTHONDONTWRITEBYTECODE and pytest -p no:cacheprovider. Examples:
- pytest apps/backend/tests/test_phase12_persistence.py -q -p no:cacheprovider
- pytest apps/backend/tests/test_phase24c_policy.py -q -p no:cacheprovider
- pytest apps/backend/tests/test_blocker_decision_policy.py -q -p no:cacheprovider
- pytest apps/backend/tests/test_goldtier_xpi_sandbox.py -q -p no:cacheprovider
- pytest apps/backend/tests/test_phase24c_registry.py -q -p no:cacheprovider
- npm test -- <affected Vitest file>; npm run typecheck; npm run build
- scripts/run_e2e.py --grep <affected scenarios> using isolated owning lifecycle
- scripts/run_physical_mongo_tests.py --timeout-seconds900
- pytest apps/backend/tests/test_phase24c_real_mongo.py -q -p no:cacheprovider

Final combined: full backend/frontend, typecheck/build, Ruff/strict mypy, contracts,
architecture/project-state/policy-authority/provider-readiness/tooling/secret checks,
complete tracked/new-file whitespace review, physical suites with0 skips and cleanup
absence, GoldTier scenarios, full configured isolated E2E at least twice, and bounded
official-Mock acceptance only where evidence is actually required. No arbitrary sleeps,
retry storms or assertion weakening. Review exact changed content independently.

Cost estimate, not an SLA or fresh PASS: nearest Phase24C gate recorded backend~344s,
root governance~77s, frontend~7s, focused18-test browser~46s, plus physical/build/static
checks. Full isolated E2E x2 and independent reruns dominate final verification; reserve
tens of minutes per combined gate, with additional time for setup, review and remediation.
Implementation is a multi-slice program, not a single quick repair. Timing/sample/tool
uncertainty prevents a reliable total completion estimate.

Primary regression risks: hidden persistence evidence disclosure/loss; historical
policy reinterpretation; weakened corruption guards; incorrect skip precedence around
uncertain ledger outcomes; stale/cross-case UI publication; misleading complete official
cache provenance; Mock duplicate/search/readback behavior; advisory impact described as
compliance; accidental external calls or private fixture contamination.
Owner-local changes and the listed adverse tests constrain those risks.

## Resume state and next authorized action

Completed: fetch/main/worktree/branch verification; four fresh read-only investigations;
source-proven diagnosis; reconciled proposed slices and test/authority boundaries.
Pending: explicit user approval before Slice A.
Blocked dependent lanes: second coherent official-company evidence; new partnership/
capital/control authority; supplied portal/manual login; physical infrastructure proof.

This planner is the only intended repository change at the checkpoint. API/types,
schema, connectors, configuration, business rules, mappings, auth/security,
architecture/provider classification and product runtime remain unchanged.
No commit, push, PR, merge or product implementation occurred.

After approval, execute Slice A with one writer and fresh independent mini-gate.
Keep later slices bounded by their contracts and readiness. Only an unchanged exact
independent combined PASS permits the separately assigned publication run:
fetch/assess latest main, scoped commits, clean committed pre-PR/checklist, authorized
push/PR and CI observation. Resolve the commit-before-clean-pre-PR ordering prescribed
by the current branch protocol. Human owner merges. Do not publish or merge now.