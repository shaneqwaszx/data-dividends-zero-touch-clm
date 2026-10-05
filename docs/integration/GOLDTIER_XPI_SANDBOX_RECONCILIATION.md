# GoldTier XPI Sandbox Reconciliation

Date: 2026-09-24
Branch: `feature/pre-phase22-capability-expansion`
Baseline: `3ca232b58c3842f413c4552dbd3b85aabea4591c`

## Outcome

Post-UAT candidate (2026-10-05): completed Sandbox cases with retained ID expose
explicit read-only exact-ID verification through the existing XPI Search owner.
It performs one goldTierID Search, writes no ledger/submission facts and returns
bounded verified/review/unavailable evidence. It never resolves uncertain mutation,
replays Shell/Policy/Amend, changes target ID or establishes downstream KYC/approval.
Current implementation/browser checks use offline transports; no fresh external
Garden/ACRA/GoldTier observation is claimed. Historical evidence below is preserved.

Current post-closeout clarification (2026-10-05):
[existing-customer resolution and API-family note](GOLDTIER_EXISTING_CUSTOMER_RESOLUTION.md)
records bounded sponsor answers and offline remediation. It supersedes the earlier
blanket inability to confirm a name-only candidate, not historical Garden failure,
uncertainty, no-replay, provider classifications or external-call authorization.

`SANDBOX_PARTIAL_IMPLEMENTED / ONE_CUSTOMER_SHELL_OUTCOME_UNCERTAIN_NO_REPLAY /
CUSTOMER_LIFECYCLE_INCOMPLETE / RELATED_PARTY_BLOCKED`

## 2026-10-04 new synthetic S3 acceptance

The historical Garden chronology below remains unchanged. Under the separate current
owner program and exact fresh PRE_MUTATION: PASS, one new synthetic identity
`ZERO TOUCH POC ACCEPTANCE 9CD9A457 / 202655266Z` completed the existing case-ledger
path. Two bounded Search calls returned NO_MATCH; Shell and required Policy each ran
once; exact-ID readback ran once. All five calls returned HTTP200. Customer ID `143887`
is retained with SHELL_CREATED, POLICY_CREATED, AMEND_NOT_REQUIRED, VERIFIED readback
and a FINALIZED SUCCESS receipt. An absent Policy ID stays null. Normal API restart
retained SUBMISSION_CONFIRMED and exact document/creator-reviewed ownership evidence
without further provider calls. No additional external attempt is authorized.

The [safe external receipt](../../.ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S3_EXTERNAL_RECEIPT.json)
and [durable proof](../../.ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S3_DURABLE_ACCEPTANCE_PROOF.json)
establish this bounded parent-customer Sandbox observation. Registry input was explicitly
Mock synthetic, not an official registered business. RP child lifecycle and original-file
upload remain unsupported; KYC, approval, Ready-for-Approval and production/Live remain
unproved. This success does not alter Garden143878, replay any historical mutation or
close the production/authentication/relationship questions. Final combined acceptance
of the uncommitted candidate remains separately gated.

## 2026-09-27 authenticated-portal recovery continuation (historical checkpoint)

This section preserves the state at that checkpoint. The 2026-09-28 continuation below
supersedes its then-current persistence and orchestration limitations without rewriting
the historical provider chronology.

The existing authenticated `anz-nutmeg` portal session was available for a bounded,
read-only recovery investigation. The single Garden result visibly binds GoldTier ID
`143878`, legal name `GARDEN BUSINESS`, registration number `11111999A`, legal country
Singapore, KYC Customer Type `Partnership - Unregulated`, entity type `Shell Record`,
and one DSD cross-reference. The customer audit contains one `Requested` event at
21:45:48 by the API-connect user, aligned to the uncertain Shell attempt. The lifecycle
status audit is empty. Portal policy scaffolding includes Singapore with a 21:45:49
create timestamp but no policy status and no requested flags; this is not evidence that
the application's Create Customer Policy operation ran. Registration type and the
configured booking-entity value were not independently visible and are not inferred.

This portal evidence is sufficient to classify ID `143878` as
`EXACT_RECOVERY_PROVED`; it improves provider-side identity evidence but does not make
the original Shell response definitive. The acceptance harness composed an
`InMemoryTargetExecutionRepository`, returned immediately after the uncertain Shell,
and retained the attempted/completed prefix only in sanitized task evidence. No
durable original Shell checkpoint exists to transition. Recreating that checkpoint or
inserting `143878` into a new ledger would violate the explicit no-reset,
no-recreation, and no-manual-substitution constraints. Therefore Shell was not replayed
or marked complete, and Policy, Amend, read-back, and the second Garden onboarding were
not attempted.

The newly authorized POC intent was GoldTier-first: bounded initial identity precedes
Search; exact match skips bootstrap ACRA acquisition and Shell; no match proceeds to
the official ACRA Marketplace Mock; ambiguous results stop for review. At that
historical checkpoint, runtime source remained ACRA-first. The later 2026-09-28
candidate implements the clarified order and exact-existing state reuse.

The two sponsor artefacts named by the assignment became available and were reconciled
against the current source, historical EDS contract, decisions, and open questions:

- `GoldTier APIs_Guideline.pdf`, SHA-256
  `b4fedf629019d17a33c05d74a248fcf4973aef740c491e91dc63ce7d6c06ef55`;
- `GoldTier APIs.postman_collection.json`, SHA-256
  `e0c20335213e15cf566ea45b262e4e3f2c3cd27d326330c2e7c1b73c1a71a708`.

No sponsor credential, header value, portal password, raw provider body, or customer
record is copied into this document or the repository. The detailed field analysis is
in `GOLDTIER_XPI_MAPPING_MATRIX.md`.

## Contract result

The files define a six-operation XPI sandbox dialect under `/gt-xpi/v1`:

| Operation | Method and route | Implemented boundary |
|---|---|---|
| Customer search | `GET /customers/search` | Strict query DTO and bounded safe candidate projection |
| Customer create | `POST /customers/create` | Strict DTO, mapper, write opt-in, existing target ledger |
| Customer policy | `POST /customers/createPolicy` | Strict DTO, case-bound target policy, existing target ledger |
| Customer amend | `POST /customers/amendCustomer` | Strict DTO, case-bound target policy, existing target ledger |
| Related-party policy | `POST /relatedParties/createPolicy` | Strict local DTO only; external dispatch blocked |
| Related-party amend | `POST /relatedParties/amendRelatedParty` | Strict local DTO only; external dispatch blocked |

This dialect is not the historical EDS-shaped Mock contract. It therefore has focused
XPI DTO/mapper/connector modules and an explicit composition branch. Mock remains the
default and never acts as a sandbox failure fallback.

## Runtime ownership

- The existing `GoldTierConnector` boundary remains the only target port.
- The existing target ledger remains the only order, intent, outcome, recovery, and
  no-replay owner.
- The existing policy catalogue supplies eight explicit authority-labelled target
  values and freezes them into each new case.
- The existing entity-resolution owner evaluates bounded search candidates. Only an
  exact identifier/country match may reuse an existing party; every other candidate
  result stops at review with zero target mutations.
- The existing case-scoped CLM plan exposes a bounded preview. It contains mapped
  values, provenance, authority, missing status, validation, and policy version, but no
  transport identity or raw provider response.
- Schema v6 remains the one case-envelope owner. Earlier schema-v1 through schema-v5
  records remain readable without rewrite; recovery and GoldTier-first fields do not
  introduce another persistence or replay owner.

## Transport and security boundary

The XPI transport enforces HTTPS, TLS 1.3, certificate verification, redirects off,
bounded timeout, bounded response retention, strict URL/query construction, and fixed
safe errors. The sponsor-supplied `user_id` value is backend-only. Collection `noauth`
metadata is sandbox evidence only and does not establish production no-auth behavior or
replace PingFed.

Mutation timeout, transport ambiguity, cancellation, oversized response, or malformed
post-acceptance response is an uncertain outcome. The attempted ledger entry remains
`IN_PROGRESS`; no automatic replay or Mock fallback occurs.

## 2026-09-28 provider-verified recovery continuation

Authenticated portal evidence from the preceding session proved ID `143878` is exact
Garden by ID, legal name, UEN, Singapore country, DSD linkage, Shell Record state, and
aligned creation audit. The new schema-v6 ledger therefore records the original Shell as
attempted/uncertain and a separate `PROVIDER_VERIFIED_RECOVERY` fact with
`HISTORICAL_LOCAL_LEDGER_LOST` origin and `replayed=false`; it never states that the Shell
response returned the ID. The recovery fact and ID survived Mongo restart, and the case
projection was repaired idempotently to the recovered-Shell state without another Shell
call.

The first real Policy request was persisted as intent and sent once. Its network outcome
remains uncertain. Later authenticated read-only portal evidence proved one Singapore
Policy request on ID `143878`, status `Requested`. The same durable ledger now retains a
separate `POLICY / PROVIDER_VERIFIED_RECOVERY / UNCERTAIN_DURABLE_LEDGER` fact with that
policy/status and `replayed=false`. A separate-process Mongo reload proved both recovery
facts, ID `143878`, attempted `SEARCH,SHELL,POLICY`, definitive `SEARCH`, lifecycle-
resolved `SEARCH,SHELL,POLICY`, and no Amend attempt survived restart.

After the configured connector/environment/ID/recovery/no-prior-Amend and sanitized-
preview checks passed, exactly one ledger-owned Amend was attempted. Its transport
outcome was uncertain, so the runner stopped without read-back or second onboarding and
the ledger retained attempted `SEARCH,SHELL,POLICY,AMEND`, definitive `SEARCH`, and
lifecycle-resolved `SEARCH,SHELL,POLICY`. Read-only portal audit on the same ID then
showed one `API Connect Amendment:GARDEN BUSINESS` sequence: `Created` at 08:47:48 and
`Valdiation Failed` at 08:47:49 on 2026-09-28. This is provider-side failed-Amend
evidence, not success. Amend must not be replayed; post-Amend read-back and the second
Garden onboarding remain blocked. No Mock fallback, Shell replay, or Policy replay
occurred.

The same retained ledger now records a separate Amend
`PROVIDER_VERIFIED_FAILURE / PROVIDER_VALIDATION_FAILED` fact, preserves the provider
spelling only as sanitized evidence, and keeps `replayed=false`. A zero-network recording
run and a separate-process verification both reloaded that exact fact from Mongo. Amend
remains attempted but is neither definitively complete nor lifecycle-resolved.

The exact sanitized request reconstructed from the immutable submission and mapper was
`goldTierId=143878` and `policy=Singapore`; `anzsic` and `groupCompanyName` were omitted,
with no null or empty fields. The XPI guideline requires the existing ID and Policy and
describes ANZSIC/GCN updates only "as required". The Postman example contains all four
fields but is supporting example evidence, not proof that the latter two are universally
mandatory. The corrected standalone OpenAPI 1.0.0 is the separate EDS dialect and cannot
silently add its `partyType`/`sourceContext` body to the XPI endpoint. The current mapping
matrix therefore supports the two-field request and continues to prohibit invented
ANZSIC or group-company values.

The Amendment task detail exposes status `KYC Edit Pool`, reason "This amendment was
automatically generated by the API", and the safe text "Amendment requires a KYC user."
Its document and requirement dependency tables contain zero items; its audit Reason and
Output cells are blank. No failed field, validation rule, policy-state prerequisite,
ANZSIC/GCN requirement, booking-entity requirement, or atomic no-application guarantee
is exposed. Root-cause classification is therefore `E. INSUFFICIENT_EVIDENCE`, not a
proved local mapping defect, provider-state rule, Singapore-authority gap, or sandbox
defect. A new Amend remains unauthorized until the API owner supplies the validation
reason, confirms the first request did not apply and defines XPI retry/idempotency
semantics, and any corrected business field has explicit Singapore authority.

## Historical sandbox observations

Before the authorized mutation attempt, seven bounded, read-only customer searches were
executed with raw responses discarded. Each returned HTTP 200 with an empty JSON array.
The last three ran on 2026-09-27 through the configured `OnboardingService` and actual
XPI connector rather than a direct diagnostic client:

| Query class | Result |
|---|---|
| Unique synthetic legal name | No match |
| Synthetic legal name plus Singapore incorporation | No match |
| Unique synthetic group-company name | No match |
| Syntactically safe impossible GoldTier ID | No match |
| Final POC synthetic legal name plus Singapore incorporation | No match |
| Historical Australia-aligned diagnostic legal name plus incorporation | No match; not a Singapore mapping source |
| Official-Mock Garden Singapore identity after the UEN clarification | No match |

An omitted/blank query and undocumented registration-number query were not sent because
either could unintentionally enumerate customer data if the server ignored the filter.
During the later bounded Garden acceptance attempt, another fresh application-service
Search returned `NO_MATCH / 0`. After the single Shell attempt became uncertain,
read-only recovery Searches found one candidate named `GARDEN BUSINESS`, GoldTier ID
`143878`; an ID-based Search returned the same ID and name. Both responses omitted the
registration number, country, and address. They therefore do not prove that `143878`
is the Shell-created customer or an exact canonical Garden match. Raw responses were
discarded. Production interoperability remains unproved.

## Historical mutation decision

Exactly one customer Shell network request was attempted after the fresh Garden Search
returned `NO_MATCH`. Its outcome is uncertain: the target ledger records attempted
operations `SEARCH, SHELL`, but only `SEARCH` as definitively completed. The Shell did
not return a safely retainable GoldTier ID, and it must not be replayed. No Policy,
Amend, post-Amend read-back, or related-party request was sent.

The customer path now satisfies the local DTO, SG/ACRA mapping, preview, ledger,
fail-closed, and no-replay prerequisites. `registrationType=ACRA`, unchanged UEN,
`DSD`, `Singapore`, and `ANZBGL (Singapore Branch)` are retained with their bounded
authorities; the collection-observed empty `accountEntityType`/`productType` fields
remain compatible. Exact 17-value KYC and 23-value Client Segment vocabularies are
backend-owned, with one validated write-once selection per case.
The authorized Garden-only values `Partnership - Unregulated` and
`Commercial SBB (Small Business Banking)` were bound per case with authority
`USER_AUTHORIZED_POC`; they are neither global defaults nor ACRA-derived. The fresh
application-service Search reached the actual XPI sandbox and returned `NO_MATCH / 0`
without Mock fallback. The subsequent one-Shell uncertain outcome stopped the ledger
before Policy and Amend. The later discovery of ID `143878` is recovery evidence only;
it is not a retained Shell result and cannot bypass exact entity resolution. The same
ledger remains the sole owner of any authorized recovery and continuation.

The preferred SIM LIM official-Mock candidate was also tested with strict same-entity
binding. Shareholder retrieval returned four records with share-count evidence, but the
entity-profile operation returned no record and same-UEN capital returned no matching
entity. The counts therefore have neither a provider-backed canonical root/address nor
a compatible denominator, and no ownership percentage or relationship was derived.

Related-party execution remains additionally blocked because the supplied contract
requires `childId` but provides no conclusive child-identity creation/retrieval
lifecycle. Relationship value authority is also unresolved. Local DTO validation is not
evidence that the related-party operation is safe to dispatch.

The HR Sandbox Console exposes these as separate backend-authored readiness states:
customer operations are `PARTIAL`, while related-party operations are
`BLOCKED_CONTRACT` with blocker `BLOCKED_CHILD_ID_LIFECYCLE` and required authority
`SPONSOR_CONFIRMATION`. This is a contract/lifecycle blocker, not evidence of a network
connectivity problem.

The future safe architecture is to obtain an authoritative child customer identity
from a sponsor-confirmed create/search/read-back lifecycle, durably bind that identity
to the case-owned party evidence, and pass only that exact ID to the ledger-owned
related-party operation. Parent-ID substitution, local/random child-ID generation, and
any relationship write before that authority exists remain prohibited. No
related-party network call is made by the current runtime.

## Classification and remaining authority

- Provider: `GOLDTIER_XPI`
- Mode: explicit `sandbox`
- Classification: `SANDBOX_PARTIAL`
- Configured POC runtime: XPI Sandbox; credential-free source-code default remains Mock
- PingFed/production authentication: not implemented
- Live interoperability: not proved
- Customer mutation evidence: Shell attempted once/uncertain and later exact-provider
  recovered with no replay; Policy attempted once/uncertain then portal-verified as one
  `Singapore / Requested` request and recovered with no replay; Amend attempted once,
  transport-uncertain, then portal-observed as `Created` followed by `Valdiation Failed`
  and durably reconciled as `PROVIDER_VERIFIED_FAILURE`; no Amend replay or post-Amend
  read-back
- Recovery Search evidence: ID `143878`, same returned ID/name on ID Search; API-only
  identity remains incomplete
- Portal recovery evidence: exact Garden identity and one Singapore/Requested Policy
  proved read-only; the later failed Amendment audit is retained as sanitized failure
  evidence and has not been rewritten as success
- Related-party mutation evidence: blocked
- Q-016-dependent workflow mutations: deferred
- Phase 22: on hold

ADR-004 and decisions D-048/D-056/D-057 record the architecture boundary. Production
selection authority, PingFed/authentication, child-ID lifecycle, relationship semantics,
and production handoff remain open.
