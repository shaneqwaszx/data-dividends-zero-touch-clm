# Persistence and Recovery Profile

## Configuration contract

| Mode | Requirement | Restart behavior | Availability behavior |
|---|---|---|---|
| `memory` | none | all cases are process-local and lost | Mongo is never contacted |
| `mongo` | valid `MONGO_URI` | structured case state survives | startup/write fails closed; no memory fallback |

`MONGO_DATABASE` and `MONGO_CASE_COLLECTION` are bounded backend-only namespace names.
The execution profile exposes only `Process-local` or `Mongo-backed durable POC`.

## Durable contract

One case envelope (currently schema v6) contains revision, onboarding and Registry evidence,
ordered document records and supersession links, reconciliation outcomes/decisions,
ownership evidence, CLM and automation checkpoints, target execution ledger, safe demo
scenario metadata, an optional immutable case-bound advisory-intelligence projection,
and timestamps. Every nested case/submission/intelligence identity must agree.
Mongo `_id` must be the canonical UUID string equal to the envelope `case_id`. Missing,
non-string, malformed, noncanonical, or mismatched keys are invalid persisted data on
every read path and during startup. Unknown versions or invalid nested aggregates are
not interpreted, repaired, or automatically migrated. Strict v1-v5 reads migrate only
in memory to the current type; schema-v4 cases retain `intelligence = null`, are not
recomputed from current policy, and are not rewritten by a read. Schema v6 additionally
retains bounded initial identity/Search, existing-target provenance, lifecycle-resolved
operations, separate Shell/Policy provider-verified recovery facts, and an optional
provider-verified Amend-failure fact in the same envelope.

## Operation safety

Target ledger transitions are `IN_PROGRESS` → `TARGET_OUTCOME_RECORDED` → `FINALIZED`.
Intent and each ordered operation marker are durable before a provider call. A restart
with `IN_PROGRESS` plus an attempted operation means the outcome is uncertain; automatic
replay is prohibited. A recorded outcome permits only receipt/finalisation recovery.
Deterministic idempotency identifiers are retained, but no external idempotency support
or exactly-once guarantee is claimed.

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
