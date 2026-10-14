# AM Wave 1 review and date behavior

Owner assignment: 14 October 2026 replacement brief v2. This bounded release covers
AM-05, AM-09, AM-10 and AM-14, preserving AM-15 optional-note behavior. AM-18 remains
open: the exact new-customer and verified existing-customer Mock journeys did not
reproduce the reported failure. This document does not close all AM requests.

## Registry provenance

Registry acquisition, operation, case-use and expiry times display in Asia/Singapore,
labelled SGT (UTC+08:00). The technical timestamp disclosure retains each original
ISO UTC string, including fractional precision. Missing/malformed provenance is
unavailable; it does not establish freshness. Recorded cache disposition remains
backend-owned and the existing validity-at-use disclaimer remains visible. No stored
time, freshness calculation or provider request behavior changes.

## Manual ownership dates

A new manual declaration defaults to today's Singapore calendar date, regardless of
browser timezone. An existing receipt retains its historical date. Explicit user date
edits survive rerenders and source switches within the existing case-bound form.
Current evidence with a retained receipt and selected document observations with one
known common date display that source date read-only. Different/unknown source dates
require an explicit review-decision date; original observation dates remain unchanged.

The existing backend no-future-date guard now compares a date-only declaration against
the Singapore calendar day. This intentionally supersedes its UTC-day interpretation,
which rejected the Singapore date between midnight and 08:00. UTC review-instant and
currentness checks remain intact. Graph, identity, binding and exact total validation
remain in their existing owners. An empty reviewer note is permitted; a supplied note
retains its current validation. This does not resolve every AM-16 report.

## Document review drafts

The actual BlockerDecisionReview fieldsets use the existing responsive two-column
grid above 900px and one column at or below 900px. Long values wrap; field order,
fieldset/legend semantics, existing navigation and sticky rail are retained.

Accept all eligible undecided suggestions fills only pending document drafts that
already expose ACCEPTED under the per-field contract. Reject all undecided suggestions
fills undecided pending document drafts. Existing decisions, corrections and notes
are preserved. Filled/skipped/remaining counts describe the local action. Missing
suggestions are never accepted; a low-confidence acceptance does not remove the
backend replacement/currentness policy. Neither action is offered for source decisions.

Bulk clicks issue no mutation. The existing single Confirm applies the exact eligible
batch; normal backend continuation and residual blockers remain authoritative.
GoldTier Review & Send remains separate. Busy/unauthorized controls remain disabled.
The existing case/actor/version/document-fingerprint key retires drafts; there is no
browser persistence, second decision store or shared server-cache change.

## Boundaries

API/shared types, durable schema/CAS, connector, configuration, mapping, authentication,
authorization, architecture and provider classifications are unchanged. Runtime/UI
behavior and the calendar basis of the existing future-date rule changed as described.
The >=25% aggregate comparator, provisional ownership meaning, source-action authority,
count-bound initial intake, explicit Send, frozen intent and target no-replay are retained.
Singapore ACRA remains the sole route; evidence here is offline Mock/Local only.
