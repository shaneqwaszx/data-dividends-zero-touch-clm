# Phase 11 Reconciliation Profile

This is a project-owned POC contract pending sponsor confirmation under Q-015.

| Field | Normalization | Outcomes | Backend actions |
|---|---|---|---|
| `legal_name` | trim, collapse whitespace, uppercase | all five | conflict: keep Registry or use one unambiguous Document value |
| `registration_identifier` | remove whitespace, uppercase, bounded exact grammar | all five | conflict: keep Registry only |
| `registered_address` | existing whitespace/case normalization, exact comparison | all five | conflict: keep Registry only |
| `country_of_incorporation` | uppercase two/three-letter code, exact comparison | all five | conflict: keep Registry only |

`MISSING_IN_SOURCE`, `UNVERIFIABLE`, and `INVALID` advertise no value-selection action;
replacement evidence is required. `POSSIBLY_STALE`, fuzzy matching, geocoding,
confidence-wins, newest-wins, Registry-wins, Document-wins, arbitrary canonical patch,
and corrected-value entry are not supported.

Field results and discrepancies derive their outcome from the retained observation
validity and normalized values. `CONFLICT` therefore requires distinct usable values;
unusable evidence produces one `MISSING_IN_SOURCE`, `UNVERIFIABLE`, or `INVALID`
current discrepancy for that field and cannot also advertise a conflict action. Domain
construction and repository retrieval/save revalidate the complete aggregate, its
lowercase 64-hex fingerprints, current field/discrepancy links, actions, decisions, and
case status.

`USE_DOCUMENT_VALUE` first prepares and validates both the canonical legal-name
candidate and reconciliation decision. A shared-lock process-local unit of work then
commits both in-memory repositories or restores both before releasing the lock. This is
atomic for recoverable in-process failures only; it is not crash-safe or restart-durable.
An idempotent duplicate is accepted only while the same discrepancy remains current and
the case, document versions, reconciliation version, fingerprint, and action still match.

The browser receives normalized values, source kind/system/environment, UTC time,
opaque safe reference, genuine provider confidence, validity, outcome, status, allowed
actions, and a decision summary. It never receives raw PDF text, a raw ACRA payload,
provider URL, credential, exception detail, private authority digest, or reviewer
identity. The resolution fingerprint is an opaque safe binding value, not an authority
or live-integration claim.

All data is process-local and synthetic/Mock or Local POC evidence. Restart is the only
reset and loses reconciliation state, canonical/decision transaction context, and replay
protection. Q-015 remains open; no source or reviewer authority is implied.
