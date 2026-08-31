# Phase 12 — Durable CLM Case Persistence & Restart Recovery

## Goal and acceptance boundary

Add an explicit `memory`/`mongo` persistence choice without changing the accepted
Singapore Mock ACRA → document → reconciliation → ownership → CLM → Mock GoldTier
business flow. In Mongo mode, a new application composition connected to the same
store must reconstruct the same case and must not invoke providers merely to list or
open it. Mongo unavailability and invalid persisted data fail closed. This remains a
single-application-instance durable POC, not a distributed workflow engine.

## Inspected process-local state inventory

The baseline contains 13 mutable process-local maps:

1. onboarding cases (`InMemoryOnboardingCaseRepository._cases`);
2. document records (`InMemoryDocumentProcessingRepository._records`);
3. document insertion sequence (`_insertion_sequence`);
4. ownership records (`InMemoryOwnershipAnalysisRepository._records`);
5. reconciliation records (`InMemoryReconciliationRepository._records`);
6. CLM orchestration records (`InMemoryClmOrchestrationRepository._records`);
7. zero-touch automation records (`InMemoryZeroTouchAutomationRepository._records`);
8. target execution ledger (`OnboardingService._execution_ledger`);
9. ownership-provider factories (`InMemoryOwnershipProviderBindingResolver._factories`);
10. per-case demo scenario (`ZeroTouchDemoControl._scenarios`);
11. demo finalisation fault counters (`_finalization_failures_remaining`);
12. Mock GoldTier party/external-key correlation (`_external_key_by_party_id`); and
13. per-case in-process locks (`OnboardingService._case_locks`).

Items 1–8 and 10 are authoritative for restart behavior and will be persisted. Item 9
will be replaced in Mongo mode by deterministic typed binding identifiers that recreate
only the supported registry-acquisition or Mock ownership providers. Items 11–13 remain
runtime-only: injected failures do not need to be replayed after their retained target
outcome, Mock connector correlation is never used to resume an uncertain mutation, and
locks are recreated per process. An uncertain target ledger blocks replay instead.

## Persistence boundary and storage design

Business services continue to depend on repository interfaces. A persistence
composition selects existing in-memory repositories or Mongo infrastructure adapters.
All Mongo adapters share one `MongoCaseStore`; business services do not receive PyMongo
collections.

Mongo stores one bounded `clm_case_snapshots` document per `case_id`:

```text
_id / case_id
schema_version = 1
revision
onboarding
documents[]                         # array order is insertion order
ownership?
reconciliation?
clm?
automation?
target_executions[]
demo_scenario?
created_at / updated_at
```

The unique `_id` is the case identifier. Bounded indexes support `automation.status`,
`updated_at`, and target submission lookup. No TTL index is created. One envelope avoids
cross-collection transactions and makes the legal-name plus reconciliation decision a
single-document commit.

## Persistence DTO and schema version

The envelope is an explicit Pydantic persistence DTO with `extra="forbid"`, bounded
arrays, `schema_version`, and typed domain fields. Writes use JSON-mode primitives:
UUIDs are strings, Decimals are exact strings, and datetimes are UTC ISO-8601 values.
Reads validate the schema version before strict envelope/domain reconstruction.
Unknown versions, malformed enums, and invalid nested aggregates raise controlled
persistence errors; the stored document is not deleted, repaired, or rewritten.

## Optimistic concurrency and atomicity

Every envelope mutation performs compare-and-set using `_id` plus the previously read
`revision`; success increments `revision` once. A zero-match write is a persistence
conflict, never unconditional last-write-wins. Existing aggregate versions remain the
business-level expected-version checks for ownership, reconciliation, CLM, and
automation.

The Phase 11 canonical legal-name and reconciliation decision path receives a Mongo
unit of work. It validates current onboarding/reconciliation fingerprints and versions,
then replaces both envelope fields in one CAS update. A conflict or injected persistence
failure commits neither half. In-memory mode retains the accepted shared-lock rollback
unit of work.

The supported runtime remains one application instance. CAS detects cross-process stale
writes, but this phase does not add distributed locks, scheduling, or exactly-once
distributed execution.

## Restart-state semantics

- `PENDING_INPUTS`, `WAITING_FOR_REVIEW`, `COMPLETED`, `TECHNICAL_FAILURE`, and
  `RECOVERY_PENDING` reconstruct unchanged.
- Case history and the review queue are derived from durable automation plus onboarding
  state; reads perform no Registry, IDP, Ownership, or GoldTier work.
- Completed registry acquisition, document evidence, reconciliation, ownership, CLM,
  automation, and target execution records are reused.
- Provider bindings are stable typed identifiers. The safe demo scenario is retained so
  deterministic demo input can continue after restart without persisting provider
  objects or credentials.
- A document left `UPLOADED`/`PROCESSING` has no retained raw bytes. Startup/recovery
  projects it to a controlled retry-required failed record; only that document may be
  re-uploaded.
- `RUNNING`/`RESUMING` is not automatically scheduled at startup. Existing explicit
  start/resume/review/replacement APIs remain the progression boundary.

## Side-effect recovery model

The target ledger becomes a repository. The immutable submission and deterministic
idempotency bindings are persisted before execution. Before each Mock GoldTier mutation,
the ordered operation marker is durably persisted; after the call, the safe bounded
target outcome is persisted before rich receipt/finalisation.

On restart:

- `FINALIZED` returns the retained receipt with no connector call;
- `TARGET_OUTCOME_RECORDED` permits receipt/finalisation recovery only;
- `IN_PROGRESS` with an attempted operation is uncertain and is never replayed. The
  automation is retained/projected as controlled recovery pending and explicit reads
  remain side-effect free;
- a definitively `NOT_STARTED` submission may execute only through an explicit existing
  progression action.

This is replay prevention for the bounded POC, not a claim that external providers
honor idempotency or that execution is exactly once.

## Document retention boundary

Mongo never stores PDF/DOCX/TXT bytes, ZIP members, the full extracted body, or raw IDP
or Registry payloads. It stores only the already bounded structured fields, confidence,
provenance, events, review decisions, file display metadata, and replacement links.
Completed structured evidence survives restart without re-upload. Work interrupted
before that durable checkpoint requires retry/re-upload because the bytes are gone.

## Configuration and startup

- `CLM_PERSISTENCE_MODE=memory` (default): existing process-local behavior; Mongo is not
  required.
- `CLM_PERSISTENCE_MODE=mongo`: `MONGO_URI` is required; bounded
  `MONGO_DATABASE` and `MONGO_CASE_COLLECTION` settings select the namespace.
- Mongo mode pings the server, validates/creates bounded indexes, and validates stored
  envelopes before accepting workflow operations. Missing/unreachable Mongo fails
  application composition with a safe error and never falls back to memory.
- Execution profile exposes only `Process-local` or `Mongo durable POC`; health and API
  errors never expose URI, database credentials, or raw PyMongo text.

## Migration strategy

Schema version 1 is the only accepted representation. No general migrator, destructive
repair, automatic reset, retention job, or purge UI is introduced. A later incompatible
version requires an explicit reviewed migration phase.

## Tests and verification

Focused tests will cover DTO round trips and corruption, memory/Mongo configuration,
CAS conflicts, atomic reconciliation, all required terminal states, multi-case ordering,
registry/document/reconciliation/ownership/CLM/automation/target reconstruction,
replacement chains, deterministic provider bindings, raw-data exclusion, read-only
case list/review/detail, uncertain side-effect recovery, and composition A → composition
B restart behavior.

A real Mongo integration suite will use an isolated `clm_phase12_test_<id>` database and
delete only that namespace. CI will supply a Mongo service to that bounded job. The
normal test suite remains memory-only. Full Phase 09/10/11, Pre-Phase 12, backend,
frontend, contract, secret, dependency, lifecycle, and whitespace checks remain required.

## Explicit non-goals

No live/official ACRA or ACRA+, foreign registry, real GoldTier/PingFed,
`createRelationship`, GridFS/blob retention, raw KYC retention, production RBAC,
reviewer identity, notifications/SLA, retention/deletion policy, backup/restore,
automatic migration platform, distributed locks/workers/queues, HA, regulatory audit
certification, Ready-for-Approval, source-precedence change, or UBO-policy change.
Q-012 and Q-015 remain open.

