# Phase 12 — Durable Persistence and Restart Recovery

## Boundary

Phase 12 makes authoritative structured CLM case state durable when explicitly
configured. It does not change Registry, document/reconciliation, ownership, CLM, or
Mock GoldTier business policy.

```text
Business services
      |
existing repository interfaces
      |
      +-- memory repositories (default; cleared by restart)
      `-- Mongo adapters
              |
       one clm_case_snapshots envelope per case
```

The envelope has `schema_version=1`, a case ID, a revision, timestamps, and typed
onboarding, ordered document, reconciliation, ownership, CLM, automation, safe demo
binding, and target-execution sections. UUID, exact Decimal, and UTC datetime values use
controlled string representations. Every read reconstructs the strict persistence DTO
and domain aggregates; unknown or malformed data fails closed without destructive
repair. Mongo `_id` is part of that trust boundary: it must be a canonical UUID string
and exactly equal `str(case_id)`. The store rejects missing, non-string, malformed,
noncanonical, or mismatched identities on startup, direct reads, lists, and secondary
lookups; it never normalizes or repairs them.

## Concurrency and coordinated decisions

Every write filters by `case_id` and the current envelope `revision`, then increments
the revision. Existing aggregate versions continue to reject stale ownership,
reconciliation, CLM, and automation transitions. Phase 11's legal-name update and
reconciliation decision are written together by one envelope CAS, so no half-state is
observable after a conflict or failed write.

This is a single-application-instance POC. Revision checks detect stale cross-process
writes but do not provide distributed locks, a scheduler, active-active execution, or
distributed exactly-once semantics.

## Restart model

- `PENDING_INPUTS`, `WAITING_FOR_REVIEW`, `COMPLETED`, `TECHNICAL_FAILURE`, and
  `RECOVERY_PENDING` remain queryable with the same case/evidence identifiers.
- Dashboard, Review, case, document, and evidence reads use stored state only and never
  invoke Registry, IDP, Ownership, or GoldTier.
- Completed Registry acquisition, structured document evidence, reconciliation,
  ownership, and target outcomes are reused.
- A current uploaded/processing document left before a structured checkpoint has no
  retained bytes. It becomes `FAILED / DOCUMENT_REUPLOAD_REQUIRED`, while the owning
  automation returns to `PENDING_INPUTS` at `DOCUMENT` with a safe recovery event.
  Completed current documents remain unchanged. Ordinary unrelated intake is rejected
  while any mandatory reupload remains; targeted same-case retry supersedes each failed
  record individually. Only after every affected document is replaced may normal intake
  completion continue.
- A target intent left `IN_PROGRESS` after an attempted operation becomes controlled
  recovery pending. It is not automatically replayed. A retained target outcome may
  complete receipt/finalisation only.

## Retention and security

The envelope excludes raw PDF/DOCX/TXT bytes, OOXML members, full extracted text, raw
Registry/IDP/GoldTier payloads, credentials, Mongo URI, provider objects, stack traces,
and browser state. It retains only bounded structured evidence and safe technical
history needed by the accepted flow. No TTL, automatic purge, GridFS, or destructive
migration exists because retention/deletion policy remains sponsor-dependent.

Mongo mode is a durable local POC, not production KYC storage, a regulatory audit
repository, production HA, backup/restore, or Ready-for-Approval.
