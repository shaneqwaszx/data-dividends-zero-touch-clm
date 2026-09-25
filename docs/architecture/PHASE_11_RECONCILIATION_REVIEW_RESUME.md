# Phase 11 Multi-Source Reconciliation, Review, and Resume

## Boundary

Phase 11 inserts one source-neutral, process-local reconciliation checkpoint after
Registry and Document/IDP evidence and before Ownership:

```text
jurisdiction -> registry acquisition -> document/IDP
             -> reconciliation -> ownership -> readiness -> Mock GoldTier
```

The checkpoint compares only `legal_name`, `registration_identifier`,
`registered_address`, and `country_of_incorporation`. Officer, shareholder,
ownership, UBO, and target reconciliation are outside this phase.

## Evidence and comparison

`ReconciliationObservation` retains an immutable raw backend value, safe normalized
value, source kind, provider/environment where supplied, UTC observation time, opaque
reference, genuine provider confidence, and validity. Browser projection excludes the
raw backend value and exposes only normalized bounded evidence.

The deterministic rules reuse the existing document normalizer:

- legal name: trim, collapse whitespace, and compare case-insensitively;
- registration identifier: remove whitespace, uppercase, validate the bounded
  identifier grammar, and compare exactly;
- country: collapse/uppercase, require a bounded two- or three-letter code, and compare
  exactly;
- address: reuse the current whitespace/case normalization and exact comparison; no
  geocoder or fuzzy service is used.

Outcomes are `MATCH`, `REGISTRY_ONLY`, `MISSING_IN_SOURCE`, `CONFLICT`,
`UNVERIFIABLE`, and `INVALID`.
Low-confidence provider evidence retains its supplied confidence and is
`UNVERIFIABLE`. One current field/evidence set has one derived outcome and at most one
current discrepancy. A low-confidence value that also differs therefore remains one
actionless `UNVERIFIABLE` discrepancy; it cannot simultaneously establish an actionable
valid-vs-valid `CONFLICT`. Independent problems in different fields remain separate.
No freshness outcome or source-precedence rule exists. `REGISTRY_ONLY` is narrowly
derived for an absent registered address when all current document profiles make it
optional; it retains the missing document observation and usable registry observation
without fabricating a match or document value. A supplied address is still compared,
and legacy required-address profiles still block on absence.

## Discrepancies and decisions

Every blocking non-match creates a first-class discrepancy with retained observations, status,
backend-authored actions, evidence fingerprint, and optional decision. Superseded
document discrepancies are cancelled, not deleted; the document and discrepancy
history remain process-local.

The field result derives its outcome from the observations. The discrepancy re-derives
the same outcome and its exact allowed actions. The case aggregate requires every
current blocking field to link to the matching current discrepancy, rejects unrelated
open discrepancies, and derives `MATCHED`, `REVIEW_REQUIRED`, or `RESOLVED` semantics
from those links/statuses. Repository reads and writes revalidate nested instances and
lowercase 64-hex fingerprints, so forged summary states cannot clear reconciliation.

The bounded actions are:

- `KEEP_REGISTRY_VALUE` for a usable value conflict;
- `USE_DOCUMENT_VALUE` only for a legal-name conflict with one unambiguous usable
  document value.

The current flat document address cannot safely reconstruct the structured canonical
address. A document registration identifier would contradict the request-bound ACRA
acquisition identity, and a different country would invalidate the Singapore route.
Those fields therefore do not advertise `USE_DOCUMENT_VALUE`. Missing, invalid, and
unverifiable values advertise no value-selection action and require replacement
evidence. Corrected-value entry is not implemented.

No action implies production reviewer authority. Decisions retain no invented name or
email and are explicit current-POC operator actions pending Q-015.

## Canonical update and resume

`USE_DOCUMENT_VALUE` reaches canonical data only through the typed backend resolution
service. `OnboardingService.prepare_reconciled_value` is side-effect-free,
fingerprint-bound, field-enum-bound, text-bounded, and re-runs canonical validation.
The proposed canonical case and reconciliation decision are fully validated before a
shared-lock process-local unit of work writes either store. Every recoverable first-write,
second-write, or post-write failure restores both snapshots before the lock is released;
the visible result is therefore both committed or neither committed. Registry acquisition
and Document/IDP evidence remain unchanged, while the retained decision records the
selected observation, value, time, version, and fingerprint.

Resolving one of several discrepancies keeps the automation in
`WAITING_FOR_REVIEW`. Resolving the final blocker moves through `RESUMING`, re-enters
the existing Document checkpoint, and then continues to the existing Ownership,
readiness, and Mock GoldTier services. Unchanged reads do not call Registry or IDP.
Existing ownership repository checks, stage-prefix rules, CLM snapshotting, and target
ledger protections prevent duplicate Ownership or Mock GoldTier work.

A duplicate service decision returns the existing decision only if the discrepancy is
still current and the case, current documents/event counts, reconciliation version,
fingerprint, and action all match. Replacement or canonical/evidence change makes the old
decision stale even when its historical discrepancy remains retained.

## API and frontend

The zero-touch case summary includes safe reconciliation status, field outcomes,
normalized observations, discrepancy states, allowed actions, and decision summaries.
The dedicated resolution endpoint is case-, discrepancy-, automation-version-,
reconciliation-version-, enum-, and fingerprint-bound. It accepts no arbitrary JSON
patch. Raw PDF text, raw ACRA payloads, raw provider URLs, credentials, internal
exceptions, and reviewer identity are absent.

The frontend panel presents Registry and Document observations symmetrically, shows all
field outcomes and provenance summaries, renders only backend-advertised actions, and
shows the retained decision after resolution. It does not label either source as the
master or build a general exception dashboard.

## Persistence and sponsor boundary

All reconciliation observations, discrepancies, decisions, versions, coordinated commit
snapshots/locks, and resume protection are in memory for one process. The unit of work is
atomic only against recoverable in-process faults while the process remains alive;
restart loses all state and is not crash recovery. MongoDB remains a diagnostic-only
script boundary. Q-012 still blocks live ACRA binding and Q-015 still blocks production
source authority, authenticated reviewer authority, audit retention, and durable resume
policy.
