# Persistence and Recovery Profile

## Configuration contract

| Mode | Requirement | Restart behavior | Availability behavior |
|---|---|---|---|
| `memory` | none | all cases are process-local and lost | Mongo is never contacted |
| `mongo` | valid `MONGO_URI` | structured case state survives | startup/write fails closed; no memory fallback |

`MONGO_DATABASE` and `MONGO_CASE_COLLECTION` are bounded backend-only namespace names.
The execution profile exposes only `Process-local` or `Mongo-backed durable POC`.

## Durable contract

One case envelope contains schema version 1, revision, onboarding and Registry evidence,
ordered document records and supersession links, reconciliation outcomes/decisions,
ownership evidence, CLM and automation checkpoints, target execution ledger, safe demo
scenario metadata, and timestamps. Every nested case/submission identity must agree.
Mongo `_id` must be the canonical UUID string equal to the envelope `case_id`. Missing,
non-string, malformed, noncanonical, or mismatched keys are invalid persisted data on
every read path and during startup. Unknown versions or invalid nested aggregates are
not interpreted, repaired, or automatically migrated.

## Operation safety

Target ledger transitions are `IN_PROGRESS` → `TARGET_OUTCOME_RECORDED` → `FINALIZED`.
Intent and each ordered operation marker are durable before a provider call. A restart
with `IN_PROGRESS` plus an attempted operation means the outcome is uncertain; automatic
replay is prohibited. A recorded outcome permits only receipt/finalisation recovery.
Deterministic idempotency identifiers are retained, but no external idempotency support
or exactly-once guarantee is claimed.

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
