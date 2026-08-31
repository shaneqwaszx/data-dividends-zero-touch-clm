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
Unknown versions or invalid nested aggregates are not interpreted or automatically
migrated.

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
the envelope. An interrupted document without structured evidence therefore requires
explicit re-upload.

