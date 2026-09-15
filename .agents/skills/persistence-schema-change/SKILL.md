---
name: persistence-schema-change
description: "Use when changing durable case/admin schemas, repository create/update/delete semantics, Mongo indexes, CAS/revisions, migrations, restart recovery, read compatibility, or persisted ownership."
---

# Persistence Schema Change

## Trigger

Use for any durable field/version/index/repository/CAS/recovery/deletion change or a new
persistence owner. Do not use for memory-only domain fields that cannot enter storage.

## Purpose

Preserve strict schema identity, explicit compatibility, CAS, restart behavior and
anti-resurrection while proving physical Mongo behavior only in safe disposable databases.

## Inputs

- field/aggregate semantics and authority;
- current/legacy schema versions and repository contracts;
- affected readers, writers, projections, recovery and deletion paths;
- migration/read-compatibility and rollback requirements.

## Mandatory context

Read repository constitution/state/architecture/workflow, persistence contract and
decision, `persistence/models.py`, Mongo stores/adapters/composition, memory repositories,
physical safety harness/tests, affected services, and `architecture-change-review` if
ownership changes.

## Preconditions

- Field meaning, type, default/null behavior and authority are explicit.
- The change cannot be satisfied without modifying durable state.
- Current schema/CAS/create/update/delete/restart invariants are mapped.
- A physical test is relevant and can use a generated allowlisted disposable database.

## Analysis steps

1. Map before/after envelope/admin schema, version discriminator, IDs, field bounds and
   nested invariants. Identify every reader/writer/projection.
2. Choose compatibility deliberately: strict old-version reader, explicit migration, or
   rejection. A convenient default is not compatibility unless authority defines it.
3. Preserve identity binding and reject unknown/malformed fields/versions. Reads must
   not silently rewrite unless an explicit migration owns that write.
4. Keep create insert-only and update update-only. No save/upsert may recreate a missing
   or deleted case.
5. Preserve expected revision/CAS for every mutation, atomic unit-of-work boundary and
   conflict/error mapping. Cover concurrent stale writers.
6. Trace restart reconstruction, incomplete work, retained target intent/outcome and
   no-provider-replay behavior.
7. Trace deletion through every aggregate/global owner and prove stale writes cannot
   resurrect it. Case deletion must not delete global admin state.
8. Compare memory/Mongo semantic parity; document intentional infrastructure differences.
9. Define physical database name through the existing safety helper. Generate a new
   allowlisted `clm_p12_*`, `clm_p13_*`, or explicitly phase-approved equivalent. Reject
   `clm_poc`, user-selected/general names and unresolved variables before connection.
10. Run write/restart/read/adverse/CAS/delete tests. Cleanup only the validated generated
    database and verify it is absent; report safe identifiers/counts, never URI/credentials.
11. Run affected security, regression, governance, CI-equivalent and independent QG.

`PARTIAL` permits only explicitly enumerated authority-independent analysis, fixtures or
test scaffolding that does not change runtime persistence. It cannot authorize a schema
or default, upsert, compatibility behavior, migration, runtime composition, merge/
readiness claim, or deferral of required physical restart and cleanup evidence.

## Allowed changes

- Versioned strict schema/model, repository adapters, safe indexes and compatibility readers.
- Explicit bounded migration when authorized, tested and recoverable.
- Synthetic fixtures and generated-database physical tests through the safety harness.

## Forbidden changes

- Upsert replacing distinct insert/update semantics.
- Silent memory fallback from Mongo or Mongo access in API routes.
- Implicit default that invents historical business data.
- Read-time repair/rewrite without an authorized migration.
- Raw provider/document/secret/session/URI data in persistence or evidence.
- Any test, drop, cleanup or mutation of `clm_poc` or a non-allowlisted database.
- Broad collection/database cleanup based on glob, user input or unresolved variable.

## Stop conditions

Stop when semantics/default/migration authority is ambiguous, compatibility cannot be
proved, CAS/identity would weaken, upsert is demanded, restart/no-replay behavior is
unclear, generated database safety cannot be validated, cleanup absence cannot be
verified, or required physical evidence is unavailable. Mark readiness partial/blocked.

## Required tests

- old/current/new/missing/malformed/unknown schema decode;
- identity/nested binding and field-bound validation;
- create collision, update-missing, CAS conflict and concurrent stale writer;
- memory/Mongo parity and failure-without-fallback;
- restart reconstruction and provider/target no-replay;
- deletion and stale anti-resurrection;
- index/startup validation where changed;
- physical Mongo using a generated allowlisted database plus cleanup verification;
- full affected backend, mypy, Ruff, security, governance and independent QG.

## Required evidence

- schema/compatibility/migration matrix and owner map;
- CAS/create/update/delete invariants;
- restart/no-replay and memory/Mongo parity results;
- generated safe database identifier class (not URI), cleanup attempts and absence proof;
- exact checks, failures, residual risk and rollback/retirement plan.

## Expected report

```text
PERSISTENCE CHANGE: PROCEED | PARTIAL | STOP
Schema/version:
Field authority / compatibility:
Readers / writers / owners:
CAS / create / update:
Restart / no-replay:
Deletion / anti-resurrection:
Physical database safety:
Tests / cleanup verification:
Risks / blockers:
```

## Handoff format

Give the implementer exact schema/model/repository files, compatibility table, CAS and
anti-resurrection rules, physical harness command and test matrix. Give QG sanitized
restart/cleanup evidence and uncovered modes. Give the owner only manual Mongo service/
secret provisioning requirements; never include a URI or authorize `clm_poc` access.
