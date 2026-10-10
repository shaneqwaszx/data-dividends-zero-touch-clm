# Persistence and Recovery Profile

## Configuration contract

| Mode | Requirement | Restart behavior | Availability behavior |
|---|---|---|---|
| `memory` | none | all cases are process-local and lost | Mongo is never contacted |
| `mongo` | valid `MONGO_URI` | structured case state survives | startup/write fails closed; no memory fallback |

`MONGO_DATABASE` and `MONGO_CASE_COLLECTION` are bounded backend-only namespace names.
The execution profile exposes only `Process-local` or `Mongo-backed durable POC`.

## Durable contract

The post-closeout schema9 additive Search extension retains initial provider
registration/country tuples and an optional CLM creator receipt with the distinct
CONFIRMED_EXISTING disposition. Legacy absence is unknown evidence, never inferred
confirmation. The existing codec/CAS/lock owners retain the receipt before stage
projection; an interrupted projection can be reconstructed without provider replay.
No schema migration, historical-envelope rewrite, envelope-version change or repository
fallback is introduced. Recovering an interrupted confirmation may save only the local
automation projection under the existing case lock/CAS owner.
Old application binaries do not understand newly written confirmed-existing values.

One case envelope (S2 candidate schema v9) contains revision, onboarding and Registry evidence,
ordered document records and supersession links, reconciliation outcomes/decisions,
ownership evidence, CLM and automation checkpoints, target execution ledger, safe demo
scenario metadata, an optional immutable case-bound advisory-intelligence projection,
and timestamps. Every nested case/submission/intelligence identity must agree.
Mongo `_id` must be the canonical UUID string equal to the envelope `case_id`. Missing,
non-string, malformed, noncanonical, or mismatched keys are invalid persisted data on
every read path and during startup. Unknown versions or invalid nested aggregates are
not interpreted, repaired, or automatically migrated. Strict v1-v8 reads migrate only
in memory to the current type; schema-v4 cases retain `intelligence = null`, are not
recomputed from current policy, and are not rewritten by a read. Schema v6 additionally
retains bounded initial identity/Search, existing-target provenance, lifecycle-resolved
operations, separate Shell/Policy provider-verified recovery facts, and an optional
provider-verified Amend-failure fact in the same envelope. Schema v7 additionally
retains bounded identity-correction/Search-recheck attempts, policy-rebind history,
manual local ownership-review evidence and prior terminal analysis history, immutable
blocker-decision metadata, and the exact target-dispatch confirmation. These are
additive facts inside the same envelope, not new persistence, ownership, authorization,
or replay authorities.

## Operation safety

Target ledger transitions are `IN_PROGRESS` → `TARGET_OUTCOME_RECORDED` → `FINALIZED`.
Intent and each ordered operation marker are durable before a provider call. A restart
with `IN_PROGRESS` plus an attempted operation means the outcome is uncertain; automatic
replay is prohibited. A recorded outcome permits only receipt/finalisation recovery.
Deterministic idempotency identifiers are retained, but no external idempotency support
or exactly-once guarantee is claimed.

Before the ledger can dispatch Shell, Policy, or Amend, schema v7 requires a current
target confirmation bound to the reviewed server projection, actor, event/CLM versions,
destination, warnings, provider classification, and digest. Relevant case, evidence,
classification, or policy change invalidates the confirmation. Every write path
reauthorizes and revalidates it within the case lock/CAS boundary; restart does not
weaken the gate. Confirmation performs a forced read-only Search recheck first; a
material result change leaves the refreshed plan unconfirmed and records no target
mutation intent. The reviewed mapper projection and retained dispatch snapshot share the
stable case-acceptance timestamp for `sourceContext.acceptedAt`, and every transmitted
preview field is included in the confirmation digest.

Provider-verified recovery does not rewrite an uncertain response. It retains the
attempted-but-not-definitive mutation, appends exact later provider evidence, marks the
operation lifecycle-resolved, and records `replayed=false`. The recovered ID is not
described as a mutation response. For the bounded Garden continuation, a second recovery
fact may resolve the retained uncertain Policy only when provider evidence binds ID
`143878`, Policy `Singapore`, and status `Requested`; the status proves a provider-side
request, not approval/completion/activation. Shell and Policy recovery facts must survive
restart together before Amend is eligible, and neither operation becomes replayable.
If the one retained uncertain Amend is later proved failed by sanitized provider audit,
the same ledger may retain `PROVIDER_VERIFIED_FAILURE`, normalized status
`PROVIDER_VALIDATION_FAILED`, the original provider status spelling, and
`replayed=false`. Amend remains attempted but neither definitively complete nor
lifecycle-resolved; read-back stays blocked, while the current outcome is no longer
reported as merely transport-uncertain.
Real external acceptance uses Mongo; unit tests may continue to use memory repositories.

## Excluded data

Raw uploaded bytes, full extracted bodies, raw external payloads, secrets, authorization,
Mongo connection strings, provider instances, and UI/session state are forbidden from
the envelope. An interrupted current document without structured evidence therefore
becomes `FAILED / DOCUMENT_REUPLOAD_REQUIRED`; automation returns to
`PENDING_INPUTS / DOCUMENT`. Ordinary intake remains closed while this condition exists.
Targeted same-case retry supersedes only the affected record, preserves completed
evidence/history, and must finish for every affected document before intake completion.

Field review, reconciliation refresh, and automation checkpoint updates use the same
durable case envelope and revision CAS but are currently saved through their existing
section repositories in sequence. They are not a cross-section Mongo transaction.
Each durable checkpoint is monotonic: current document lineage is written first,
reconciliation is fingerprinted from that evidence, then stale automation exceptions
are cancelled before progression. An exact repeated review or explicit `/resume`
repairs an interrupted later checkpoint. Multi-instance simultaneous field-review
exactly-once behavior is not claimed without physical Mongo race evidence.

A rejected reconciliation request/CAS save, reconciliation infrastructure failure,
authorization failure, or automation checkpoint CAS save stops that request. Previously
durable evidence may remain, but blockers and the automation checkpoint remain intact;
ownership and target work are not invoked, and the failed prerequisite is not retried
within the same request. Progression begins only after reconciliation and automation
checkpoint saves are both accepted. This monotonic sequential recovery rule is
owner-authorized project behavior, not a cross-section transaction or sponsor-confirmed
policy.

`PENDING_INPUTS / DOCUMENT_REUPLOAD_REQUIRED` is reserved for a replacement whose
current failed record was durably accepted with `IDP_PROCESSING_FAILED`. Repository/CAS
or other infrastructure rejection does not enter that recovery state and leaves the
existing automation checkpoint and blockers unchanged.

## Phase24C additive envelope/control-plane amendment — 2026-10-02

Phase24C case writes used schema8, adding frozen registry/classifier parameters and policy
identity plus optional version2 semantic score/threshold/policy/reason metadata. Schemas
1..7 read into the current type in memory only and retain absent parameters as legacy
behavior; no active-policy lookup, case rewrite or automatic reclassification occurs.
New non-null parameters/version2 tags in an old envelope fail closed. Schema7 keeps all
accepted recovery/confirmation/stage facts. Same identities, strict integer discriminator,
CAS/no resurrection, ledger/no replay, minimized browser cache projection and explicit
memory/Mongo modes remain. The separate policy singleton has explicit schema2 proposals,
ACTIVE/superseded versions, approval metadata and append-only audit; the separate cache
collection has explicit schema2 normalized prefixes/definitive absence. Neither is a
new persistence owner. Physical evidence requires fresh allowlisted disposable databases.

## S2 additive envelope amendment — 2026-10-04 candidate

Schema9 adds immutable server-authored case creator; document version/page/quality/method,
score formula/raw OCR/candidates and proposed ownership observations; current/prior source
bindings, discrepancies, original supplements and manual source-choice receipts. The
same envelope owns all evidence. Original bytes, full text, temporary paths and raw OCR
TSV remain transient. Schema1..8 reject explicit new fields even null/empty and reject
the new AMBIGUOUS reconciliation marker; they read in memory without rewrite, creator
inference, metadata invention, policy activation or reclassification.

Every proposed observation must match its retained document ID/version and page;
current/prior ownership copies must equal original observations. Discrepancies and
manual receipts reference retained observations and document event counts. Ambiguous
reconciliation must bind an original field with multiple candidates. Creator identity
is immutable in memory/Mongo and included in envelope CAS. Restore cannot change creator
or resurrect a deleted case. Existing insert-only create, update-only mutation and strict
identity/revision CAS remain. Physical evidence uses fresh allowlisted disposable databases.

Before any target intent/submission, creator revisions preserve prior analysis/receipts,
clear stale readiness/confirmation under the owning lock, and recalculate through the
single Decimal engine. Any retained target execution freezes this edit. Sequential
checkpoint failure stays fail closed; it is not a cross-section Mongo transaction.

## Schema10 target-selection amendment — 2026-10-05 continuation

Current schema10 retains bounded document classification observations and case selections
with DOCUMENT/USER source separated from policy authority. Document choices bind their
original observation/value/method/quality/score/page/version and event count; case values
match case-bound target policy. Strict schemas1..9 reject explicit later fields even null
or empty and decode to empty/unknown evidence in memory without rewrite or reclassification.
Schema9 retains all accepted creator/extraction/ownership/Search fields. Same envelope,
CAS, insert-only/update-only and no-resurrection/no-replay owners; no new repository or
read-time migration. Older binaries cannot decode schema10 writes.

## Schema10 current-evidence review binding — 2026-10-06

The same still-uncommitted schema10 selection carries evidence_fingerprint and USER
actor_id alongside existing value/timestamp/policy/vocabulary/document audit. DOCUMENT
receipts bind the trusted current evidence identity without impersonating a user.
Absent earlier schema10 bindings remain unknown and stale, never inferred or rewritten
on read. Schemas1..9 remain strict read-only-compatible and reject later selection fields.
Assessment is derived by the document owner; no duplicate persisted assessment/cache
owner or new schema version. Existing envelope/CAS/create/update/delete/freeze invariants
remain. Stale conflict, fresh review and later invalidation survive physical restart;
startup/GET do not rewrite valid case documents to fabricate currentness.

## Provider-verified Policy recovery candidate — 2026-10-06

The explicit owner remediation from main `529efea` permits either definitive
SEARCH/SHELL or definitive SEARCH with provider-recovered SHELL before exactly one
unresolved POLICY. Only Requested provider evidence bound to the frozen current
case/target policy and retained ID is accepted. Normal Shell stays SHELL_CREATED;
completed SEARCH/SHELL remain definitive, while POLICY gains a separate recovery
fact and lifecycle resolution. No Policy ID is fabricated and no HTTP call occurs.

The existing ZeroTouchOrchestrator reconciles only the matching target-uncertainty
technical failure through its existing RESUMING and RECOVERY_PENDING transitions.
Its original failure event survives; identical retry can finish interrupted local
checkpoint retention. Explicit resume uses the original confirmation/input/intent,
skips resolved mutations and follows the existing frozen Amend/readback plan.
Manual CLM submissions retain the same recovery API without requiring or fabricating
automation; their existing CLM owner continues the frozen submission explicitly.
The route retains TARGET_RECOVERY and locked session/team authorization; HR does not
gain case access. There is no browser provider-evidence form in this candidate.

Safe future incremental uncertainty reasons use existing case event codes with bounded
TIMEOUT, TRANSPORT, RESPONSE_DECODE, RESPONSE_TOO_LARGE, UNEXPECTED_STATUS or UNKNOWN
suffixes. They retain no private exception/payload/header and change no replay rule.
No new envelope field/schema, migration, timeout setting or provider claim is added.
See [the recovery operator boundary](../integration/GOLDTIER_POLICY_PROVIDER_RECOVERY.md).

## Grouped review checkpoint candidate - 2026-10-10

ADR-011 extends existing owners without a new schema or repository. All document groups
are prepared and validated before the first write. Each affected document is retained
once; a partial failure leaves ordinary reviewed receipts and blocked automation. Exact
unchanged repeats are idempotent and can complete the checkpoint after restart. Changed
source/review choices are rejected. Reconciliation/automation retention follows only after
every document write succeeds. Reconciliation groups use the existing one-envelope UoW.
There is no cross-document/document-reconciliation-automation transaction. Continuation
is at most once per completed group and never authorizes GoldTier submission. Physical
evidence uses only new allowlisted disposable databases. Existing CAS/deletion/freeze
semantics, target intent/ledger ordering, schema10 and strict historical reads remain.

If a source-group UoW commits before automation retention fails, the API returns a
technical failure while the canonical/source receipts remain retained. Explicit Resume
reads those receipts and repairs the outstanding checkpoint. A changed canonical legal
name requires the existing read-only Search recheck; no target mutation repairs review.
An old group whose case-event count changed is stale, rather than an exact retry.

## Final Review evidence revision candidate - 2026-10-10

The existing owners may supersede a current document before target execution, retaining
document lineage and a RESUMING/DOCUMENT section checkpoint before the CLM readiness
refresh. Current automation/CLM/case-event/document versions and locked creator
reauthorization guard replacement. Interrupted refresh remains explicitly resumable;
physical restart must retain the checkpoint, lineage and no target call. Fresh document
classification/readiness replace the previous confirmation; stale confirmation fails.
The new document_replacement_authorized API capability is derived and is not a durable
schema field. Schema10, CAS/create/update/delete, historical reads, the single repository
owner and target ledger freeze/no-replay rules are unchanged.
