# Phase 11 Reconciliation Profile

This is a project-owned POC contract pending sponsor confirmation under Q-015.

| Field | Normalization | Outcomes | Backend actions |
|---|---|---|---|
| `legal_name` | trim, collapse whitespace, uppercase | standard five only | conflict: keep Registry or use one unambiguous Document value |
| `registration_identifier` | remove whitespace, uppercase, bounded exact grammar | standard five only | conflict: keep Registry only |
| `registered_address` | existing whitespace/case normalization, exact comparison | standard five plus `REGISTRY_ONLY` for an absent optional COI address | conflict: keep Registry only |
| `country_of_incorporation` | uppercase two/three-letter code, exact comparison | standard five only | conflict: keep Registry only |

`MISSING_IN_SOURCE`, `UNVERIFIABLE`, and `INVALID` advertise no value-selection action;
replacement evidence is required. `POSSIBLY_STALE`, fuzzy matching, geocoding,
confidence-wins, newest-wins, Registry-wins, Document-wins, arbitrary canonical patch,
and corrected-value entry as a reconciliation-resolution action are not supported.

`REGISTRY_ONLY` is the sole non-match, non-blocking outcome. It is valid only for
`registered_address` when every current document profile makes that field optional, the
registry retains a usable address, and the document supplies no address value. It does
not copy the registry value into document evidence or establish global Registry
precedence. A supplied mismatching, invalid, or unverifiable document address remains a
normal blocker. The legacy `PROVISIONAL_CORPORATE` profile still requires address.

Document observations apply the current bounded field-review state. Accepted fields use
the immutable original extraction and provider provenance. A safe correction uses the
separate reviewed value with `HUMAN_REVIEW` / `DOCUMENT_REVIEW_CORRECTION` provenance
and no inherited provider confidence. Rejected evidence is missing; missing or
low-confidence original evidence remains unusable even after a recorded correction.
Once any field review begins, remaining pending fields are `UNVERIFIABLE` until every
required field is final, so partial review cannot resume automation.

Field results and discrepancies derive their outcome from the retained observation
validity and normalized values. `CONFLICT` therefore requires distinct usable values;
required unusable evidence produces one `MISSING_IN_SOURCE`, `UNVERIFIABLE`, or `INVALID`
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
actions, per-field document requiredness, and a decision summary. It never receives raw PDF text, a raw ACRA payload,
provider URL, credential, exception detail, private authority digest, or reviewer
identity. The resolution fingerprint is an opaque safe binding value, not an authority
or live-integration claim.

Evidence remains synthetic/Mock or Local POC evidence. Memory mode is process-local;
explicit Mongo mode durably retains the reconciliation aggregate and its evidence
fingerprint. Q-015 remains open; no final source or reviewer authority is implied.

When field review asks reconciliation to refresh current observations, a repository/CAS
request rejection or infrastructure failure is a failed prerequisite. The orchestration
boundary surfaces the typed safe failure, preserves its current blockers, and performs
no ownership or target progression. It does not substitute an empty discrepancy set or
retry reconciliation invisibly in the same request; a later exact review repeat or
explicit `/resume` may reconcile the already durable document decision.
