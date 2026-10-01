# Overnight ACRA + GoldTier Demo Readiness Report

Date: 2026-10-01 (Asia/Singapore). This is a local implementation/evidence handoff.
Historical reports and original provider receipts are preserved.

## 1. Executive Summary

STATUS: **BLOCKED** for the required exact network-backed acceptance claim.

Local defects were reproduced and fixed: asynchronous document-review skipping,
physical runner false PASS with partial skips, outdated threshold authority/copy, and
a completion-cache race. The backend could complete while a late pre-confirmation
GET replaced its completed UI summary. Deterministic adverse tests now pass.

The new authorized ACRA session made exactly token 1 / entity 2 / shareholders 1,
all HTTP 200. Its browser verifier timed out without retaining the exact-case journey.
That case's completion cannot be certified. Immediate and delayed normalized replays
complete, but they are explicitly offline evidence, not replacement network proof.

Physical Mongo passed locally: 38/38, nine suites, zero skips/errors. Actual GoldTier
Sandbox Search passed directly and through the normal console UI, without fallback.
Conditional external mutations were not dispatched: independent pre-mutation **FAIL**
identified unproved current mapping/screening, active durable ledger and XPI idempotency.

## 2. Candidate Identity

- Branch: `fix/demo-happy-path-stabilization`.
- Accepted base, HEAD and local origin/main:
  `efc31f450f0103766fa812bc0aa80754f801dbe9`.
- Final 61-path source/content digest:
  `11fc4d703a845b7bc0412154aceb7f595091b2e428c490c9e398246debd244ff`.
- Complete reviewed path-to-file-hash inventory: `tmp/OVERNIGHT_SOURCE_MANIFEST.json`.
  Digest is SHA256 of sorted compact JSON mapping repository paths to raw-file SHA256.
  Independent gates, historical acquisition reports and this results-only handoff are
  separate from the source digest; provider/harness evidence is separately frozen.
- Index remains empty. No commit, push, PR, merge, fetch, branch change, worktree,
  reset, stash or clean was performed.

The complete candidate retains the earlier Garden source, fixtures, UI and reports.
New continuation changes own CLM readiness warnings/tests, policy defaults/tests,
Review & Send copy/tests, centralized query publication, Garden browser regressions,
physical runner/tests, dated authority records, current contract reconciliation and
the demo guide. Full path inventory is in the source manifest.

API/type: earlier Garden additions retained; this continuation adds no shared schema
or enum. Durable schema/repository/index/CAS: no continuation change. Connector and
mapping: no continuation runtime change. Configuration: process-only observations;
no persistent settings changed. Business authority: dated >=25% clarification.
Auth/security: scoped query cancellation/revision protection; backend remains owner.
Architecture: existing owners retained. Provider status: actual bounded observations
only; no Production/Live promotion. Runtime: fresh 25% warning assessment and cache
completion behavior changed. Legacy catalogues, snapshots and warnings remain readable.

## 3. ACRA Official Mock

New session `72aa5c0cc2e2d036`, fixed host `api-sandbox.bizfile.gov.sg`:

| Operation | Actual wire count | HTTP |
|---|---:|---|
| OAuth token | 1 | 200 |
| entityBasicInformation | 2 | 200, 200 |
| coShareholdersDetails | 1 | 200 |
| LLP / Capital / Relationships | 0 | Not dispatched |

Strict company decoding retained UEN `11111999A`, `GARDEN BUSINESS`, PARTNERSHIP,
registration date 1974-09-28, represented address 306C XYZ LINK / #03-21 / ABC GARDEN /
333333. Entity status was omitted/null. SG remains a project-derived default where
the provider omitted the country. No officer personal data or raw body was retained.

The earlier official session independently retained four decoded officers, EMPTY
shareholders and unsupported Relationships. The new session retained HTTP evidence
and company projection but lost the browser acquisition summary; its decoded officer
count and shareholder outcome are therefore **not certified from this new receipt**.
Do not assume EMPTY from prior history. Relationships remained zero-call by guard.
No Production/Live ACRA claim is made.

## 4. Exact Network-Backed Garden Journey

| Stage | New actual network session | Current offline evidence |
|---|---|---|
| Case creation | Normal UI initiated; exact case ID not retained | PASS, exact ID retained |
| ACRA | Four authorized HTTP 200 requests; strict company projection retained | Explicit captured/protocol test lane |
| Document | Not independently retained before timeout | All four fields final; REVIEWED V9 |
| Reconciliation | Not certified | Actual captured address conflict resolved through normal UI |
| Supplementary ownership | Not certified | Exact document ID/version bound; LOCAL user declaration |
| Decimal UBO | Not certified for this network case | PASS, structured 60/40 declaration |
| Classification | Not certified | Explicit operator choices saved, no automatic business mapping |
| Readiness / Review & Send | Not certified | Current evidence and server preview inspected |
| Explicit confirmation | Not certified | Normal UI POST; no hidden state mutation |
| Local Mock target | Not certified | COMPLETED, zero blockers; canonical entity unchanged |
| Cases / Onboarded | Not certified | Exact same ID verified through APIs and UI links |

The network browser subprocess hit its 360-second limit; the then-current verifier
emitted JSON only at exit and lost intermediate stage evidence. Its memory process
closed. No second network session or replay of external operations was attempted.

Offline delayed acquisition subsequently reproduced backend COMPLETED with absent UI
completion. Two failing-first unit tests and a failing-first ordinary-query browser
test proved the stale cache race. Confirmation now cancels the exact scoped detail GET
before publishing; the existing shared publisher rejects lower automation revisions.
Current delayed replay passes. The harness now checkpoints sanitized progress at each
action and preserves it on parent timeout. This fixes future evidence loss without
inventing evidence for the closed network case.

## 5. Physical Mongo

Local disposable `mongo:7`: **PASS**, collected 38 / passed 38 / failed 0 / errors 0 /
skipped 0, across nine canonical suites. Docker engine 29.8.1 was available. One uniquely
named container used an OS-assigned loopback port, no existing mounts or user database;
only repository-generated allowlisted database names were cleaned by test owners.
The exact owned container was removed. Unrelated containers were preserved.

Atlas: **NOT USED** for this task's observations or destructive verification.
Normal MONGO_URI / `clm_poc`: not used. Local physical evidence precedes later pure
policy wording/warning and frontend-cache edits; persistence owners, schemas, CAS,
indexes and physical-suite files were unchanged afterward. No additional container was
created. Existing GitHub CI physical acceptance remains required on separately
authorized publication; no current remote CI result is claimed.

## 6. GoldTier Authoritative Contract

Retain current Singapore XPI Sandbox runtime under `/{environment}/gt-xpi/v1` with
backend-only `user_id`. Source, D-048/D-055-D-060, recorded guide/collection hashes and
actual Search observations support that dialect. `/v1/eds`, OAuth2 and Idempotency-Key
belong to the separate EDS reference/Mock contract; do not combine their guarantees.

Current original XPI guide/collection and original `GT_DataMapping_ANZ.xlsx` were not
available in the explicitly inspected sponsor directory/archives. The structural
authority table and limitations are in
`docs/integration/GOLDTIER_CURRENT_CONTRACT_AND_SCREENING_RECONCILIATION.md`.
No migration or runtime dialect defect was established.

## 7. GoldTier Excel Mapping

The read-only parser inspected `GoldTier_EDS_Data_Dictionary.xlsx` and corrected EDS
schemas. The workbook identifies a derived Claude-assisted BA mapping; confidence is
not API requiredness. Exact sheet/cell references are recorded in the reconciliation.

| Subject | Current XPI input classification | Ownership conclusion |
|---|---|---|
| PEP | NOT_IN_CURRENT_CONTRACT | D; internal/downstream ownership unproved, E clarification |
| Sanctions | NOT_IN_CURRENT_CONTRACT | D/E; historical sanctioned locations are not screening results |
| Adverse media | NOT_IN_CURRENT_CONTRACT | D/E; no mandatory current input established |
| Risk rating/score | NOT_IN_CURRENT_CONTRACT | D/E; reported GoldTier risk is not independently proved |
| Source of wealth | NOT_IN_CURRENT_CONTRACT | D; historical EDS optional enrichment, not current required input |
| Source of funds | NOT_IN_CURRENT_CONTRACT | D; historical EDS optional enrichment, not current required input |

KYC type, client segment and policy have documented current XPI minimum/selection
requirements. ANZSIC is optional for Amend; no SG SSIC conversion was invented.
No duplicate screening, EDD workflow or unsupported risk field was implemented.

## 8. GoldTier Sandbox Connection

Safe host: `portal.gt.deltacapita.net`; environment `anz-nutmeg`; dialect XPI;
mode Sandbox; backend `user_id` authentication; writes disabled; memory persistence.

New synthetic identity: `ZERO TOUCH SYNTHETIC ACCEPTANCE 779F8111C9CE06A6`.
One direct actual-backend connector Search and one normal HR console UI Search both
returned HTTP 200 / NO_MATCH / zero candidates. Total Search **2**, Mock fallback **no**.
No customer payload or credentials were retained. Screenshot shows empty synthetic
Search in the actual console.

Automatic review rejected the initially proposed Garden read, interpreting the latest
authorization as synthetic-only. It was removed. A subsequent local hostname guard
stopped before dispatch because the permitted Sandbox hostname does not contain the
literal word sandbox; the corrected guard pins exact host/environment. These rejected
and local zero-dispatch attempts are separate from actual Search evidence.

## 9. GoldTier Customer Field Matrix

| Operation | Exact source/payload summary | Authority and response | Retry / uncertainty |
|---|---|---|---|
| Search | Synthetic legalName plus SG | Current XPI query DTO; bounded 200 list; actual NO_MATCH | Max two initial reads, already consumed; no blank/enumerating search |
| Shell | Reviewed synthetic canonical legal name/UEN/address/SG; ACRA registrationType, DSD external system and unique case key; explicit KYC type/segment | Current minimum and case-bound mapping; require safe issued ID | One attempt only after all prerequisites; uncertainty stops every later write, never auto-replay |
| Policy | Retained issued ID/same case key; DSD, Singapore, ANZBGL (Singapore Branch); account/product empty only where supported | Immutable reviewed policy; current decoder permits optional policy ID, upstream completion unproved | One attempt; uncertain outcome stops and requires read-only recovery |
| Amend | Exact retained ID, Singapore policy; omit unsupported enrichment | Current guide minimum; conditional SG requirements remain unresolved | One attempt; validation failure is not a blind retry trigger |
| Readback/Search | Exact retained issued ID | One bounded exact candidate required; existence alone does not prove Policy/Amend fields | Up to two separately bounded reads after safe writes; zero dispatched |

Full field-source/requiredness/response limitations and the eight prerequisite table
are in the current reconciliation. This is a **blocked plan**, not a mutation-ready
payload. Provider idempotency, current requiredness and complete business readback must
be proved rather than inferred from EDS or HTTP 200.

## 10. GoldTier Remaining Write Gap

Classification: CONNECTION_CORRECT_LIFECYCLE_NOT_FULLY_VERIFIED;
HISTORICAL_GARDEN_NO_REPLAY; current mutation contract/mapping/ownership limitations.
No wrong dialect or local auth/response/mapping defect was established.

The independent pre-mutation reviewer returned **FAIL**. Synthetic NO_MATCH passed;
complete current mutation mapping, screening ownership, process write enablement,
active durable operation ledger and provider XPI idempotency remain unproved. A removed
physical-test service proves persistence capability, not an active mutation ledger.
Local no-replay is not upstream duplicate suppression. Consent is acknowledged; facts
required by that consent remain missing. No new consent request can substitute for them.

## 11. Garden Existing-Customer Target Plan

Preserve historical uncertain Shell, recovered Policy Requested and failed Amend.
Future bounded read-only Search must prove exact identity/retained provider ID; name
alone is insufficient. Skip Shell only through the existing authoritative resolver.
Requested policy evidence does not prove approval/activation. Determine policy and
readback state before considering any separately authorized continuation. Never reset,
recreate or substitute ledger evidence to replay Garden. This task made no Garden
Sandbox read or write, no Shell replay, and no related-party call.

## 12. User Policy Clarifications Applied

D-062 dated 2026-10-01 records sponsor-confirmed aggregated ownership >=25% inclusive.
Other configured thresholds and complete legal/control tests remain distinct unresolved
authority. Fresh 25% readiness omits the legacy unconfirmed warning; edited thresholds
retain it. Historical records/catalogues are preserved and UI copy remains readable.

KYC is onboarding evidence preparation. No separate KYC/compliance approver or mandatory
four-eyes stage is required for this POC. RM/onboarder final action confirms submission,
not regulatory approval. No second final-approval workflow was added. Ready-for-Approval
is not a local prerequisite unless required by the actual external API; no such action
was established in inspected current material. EDD remains out of scope. Local risk/ML
is advisory; no arbitrary probability blocker or authoritative regulatory risk claim
was introduced. GoldTier built-in risk and screening ownership remain reported/unproved.

## 13. Performance / UX

Pending document controls now wait for the actual current card, field and version;
server-final fields may be skipped, pending fields cannot silently disappear. Exact
reviewed version reaches the manual receipt. Reconciliation waits for fresh authoritative
state. Confirmation is explicit and provider labels separate actual official Mock,
offline synthetic protocol, local/manual evidence and target Mock/Sandbox.

Before: old ready detail GET could remove completed overview after confirmation.
After: exact scoped GET cancellation and revision guard retain completion. The durable
test holds WAITING_FOR_REVIEW v7, confirms, releases it and verifies same completed ID
in both views. No mutation retry or frontend authorization was added.

All five widths 360/768/1280/1440/1920 and CSS 200% passed in offline acceptance;
safe replay screenshots capture Review & Send only and exclude officer records.
Focus navigation retains zero additional calls; measured local timings include UI waits
and are not external latency benchmarks. Browser console Search proves actual Sandbox
classification and no fallback. No production-ready performance claim is made.

## 14. Tests

| Check | Result |
|---|---|
| Full non-physical backend | PASS; 1532 collected, 1494 passed, 38 opt-in physical skips |
| Canonical physical Mongo | PASS; 38/38, nine suites, zero skips/errors/failures |
| Contract suite | PASS; 44 |
| Affected tooling/security tests | PASS; 134 |
| Focused CLM warning regression/service | PASS; 71, including failing-first 25/non25 tests |
| Policy/checker focused slice | PASS; 64 |
| Physical runner unit regressions | PASS; 17, mixed-skip test failed before fix |
| Full final frontend | PASS; 381 across 32 files |
| Cache/auth focused | PASS; 43, two stale-response tests failed before fix |
| Final Garden browser | PASS; 5, delayed-doc and held-old-GET tests failed before fix |
| Captured immediate/delayed full replay | PASS; zero external calls, explicitly offline |
| Actual ACRA network acquisition | Four HTTP 200; full exact journey NOT CERTIFIED |
| Actual GoldTier connector + console | PASS; two synthetic Search NO_MATCH, zero writes |
| Ruff | PASS |
| Strict mypy | PASS; 112 source files |
| Frontend typecheck / build | PASS |
| Policy / architecture / provider readiness / secret scan | PASS |
| Project-state snapshot checker | Pre-existing GOVERNANCE_BASELINE FAIL |
| Tracked + explicit new-file whitespace | PASS |

The project-state checker references historical main SHA
`d23d7b7335ba402b071191821c35e4f5e879ed7c`, not reachable from the user-accepted local
origin/main. No fetch or snapshot rewrite was authorized. The first non-physical wrapper
incorrectly forced Mock IDP and produced 13 harness-environment failures; after restoring
canonical LOCAL_PDF_TEXT with dotenv/Atlas still blocked, the broad backend passed.
Only newly changed/failed frontend surfaces were repeated after the cache fix.
No skipped/unexecuted physical evidence is counted as PASS.

## 15. Independent Quality Gate

Historical Garden and official evidence gates remain preserved. The current independent
pre-mutation review is **FAIL**, so all external mutations were withheld. The new local
cache finding was independently reproduced by a specialist, remediated by the coordinator,
and its failing-first deterministic browser test passed after remediation.

Fresh final combined review, by a reviewer with no implementation role, returned exact
**FAIL** in `OVERNIGHT_ACRA_GOLDTIER_FINAL_QUALITY_GATE.md`. No new reproducible local
defect remained. The required exact network-backed case journey is unproved and the
conditional GoldTier mutation prerequisites remain blocked; neither was waived.
Independent checks passed: 121 backend, 43 frontend, five browser tests and 17 physical
runner unit tests. Seven safe screenshots were inspected. Three scanner matches in
ignored harnesses were adjudicated as ephemeral random credential generation/transient
STDIN forwarding, not persisted secrets. Source/evidence manifests had zero drift,
Git/index stayed unchanged and explicit whitespace checks passed. Final gate report
SHA256: `9751c62fabb7a9e37356f57a70aea17434978edb4d1ac99ff2a4d3799d05a0cd`.

## 16. External Activity

Current overnight session only: ACRA token **1**, ACRA entity reads **2**, shareholders
**1**, Relationships/LLP/Capital **0**. GoldTier synthetic reads **2**, Shell/Policy/
Amend/readback mutations **0**, Garden calls **0**, related-party **0**, Production/
PingFed **0**, other external writes **0**. No external customer was created/deleted.
Rejected and local guard attempts made zero provider requests.

## 17. Final Capability Matrix

| Capability | Current result |
|---|---|
| ACRA OFFICIAL MARKETPLACE MOCK | PARTIAL current acceptance; acquisition HTTP/company subset verified |
| GARDEN EXACT NETWORK HAPPY PATH | FAIL / NOT CERTIFIED |
| GARDEN HUMAN INTERVENTION | PASS offline, not new exact-network proof |
| UBO | PASS local Decimal engine, >=25% inclusive authority |
| GOLDTIER SANDBOX CONNECTION | VERIFIED, direct and normal console |
| GOLDTIER FIELD MAPPING | PARTIAL for complete external lifecycle |
| PEP / SANCTIONS / ADVERSE MEDIA OWNERSHIP | UNRESOLVED |
| GOLDTIER FULL EXTERNAL LIFECYCLE | BLOCKED, NOT EXECUTED |
| PHYSICAL MONGO | PASS locally; remote CI unobserved |
| NORMAL DEMO COMPOSITION | Actual ACRA official Mock + local Mock GoldTier + LOCAL document/Decimal/manual evidence |
| Normal Sandbox mutation demo | Not enabled; read-only Sandbox separately verified |
| PRODUCTION/LIVE | NOT CLAIMED |
| PUBLICATION | NOT REQUESTED; index empty |

## 18. Exact Next Action

Independent final review is complete, with no remaining reproduced local finding.
The corrected cache and checkpointing harness need **one newly authorized
ACRA session** to certify a fresh exact network-backed case: token <=1, entity <=2,
shareholders <=1; all other provider operations/external target writes zero. The existing
session budget is exhausted and its ephemeral case cannot be reconstructed as proof.
No repeat network session is implied by this handoff.

For GoldTier, obtain the current original XPI mutation contract/mapping and sponsor
screening ownership, prove idempotency/uncertain-response and field-readback semantics,
and provision an explicitly authorized active durable mutation ledger. Re-review all
eight prerequisites before dispatching the already conditionally authorized synthetic
identity lifecycle. Proposed maximum remains Search 2 / Shell 1 / Policy 1 / Amend 1 /
readback-Search 2, zero Garden/RP/Production writes; initial two Searches are consumed
by this session. Shell uncertainty stops every later write with no auto-replay; Policy
uncertainty stops for read-only recovery; Amend validation does not permit blind retry.
Do not delete the external customer without explicit sponsor safe-deletion contract.
There is no fully safe mutation-ready payload while these factual prerequisites fail.
