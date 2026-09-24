# Case Activity query profile

## Status and boundary

This project-defined POC contract covers `GET /api/clm/zero-touch/activity` and its
bounded CSV representation at `GET /api/clm/zero-touch/activity.csv`. Both expose only
retained zero-touch automation timeline events already stored with a case. They are not
sponsor approval of production audit, retention, actor attribution, immutability,
exactly-once delivery, compliance, or a complete operational event history.

The canonical owner remains the existing zero-touch aggregate. `CaseQueryService` owns
authorization and bounded metadata resolution; the portfolio repository owns the
memory/Mongo read. This profile adds no event store, schema version, index, migration,
provider operation, workflow action, or target operation. Schema v5 is owned by the
case-envelope/intelligence change; this read surface only validates and projects it.

## Request

| Input | Contract |
|---|---|
| `case_id` | Optional canonical UUID. An absent, deleted, or inaccessible selected case returns the same safe 404. |
| `team_filter` | Existing Director-only semantics: omitted/`all`, exact known team, or `unassigned`. Ordinary team users cannot override scope. |
| `action` | Optional `CREATED`, `DOCUMENT`, `RECONCILIATION`, `OWNERSHIP`, `TARGET`, or `COMPLETED` presentation bucket. Buckets retain their existing overlap. |
| `stage` | Optional exact existing `AutomationStage`. |
| `outcome` | Optional exact existing `EventOutcome`. |
| `from` / `to` | Optional timezone-aware instants normalized to UTC. The interval is from-inclusive and to-exclusive; if both exist, `from < to`. |
| `limit` | Integer 1–100; default 50. |
| `offset` | Integer 0–10000; default 0. |

All filters intersect before pagination. “All” is represented by omission. Unknown
enums, malformed UUIDs or dates, naive dates, invalid windows, out-of-range paging, and
query-shaped injection strings return safe 422 responses. The contract accepts no
free-text search, sort expression, regex, SQL/Mongo fragment, or caller-supplied scope.

## Response

The response is `{ items, offset, limit, has_more }`. `has_more` is determined with at
most `limit + 1` rows; there is no total or total-pages estimate. Empty matches return an
empty successful page. Each item contains only:

- `case_id`, source-local `sequence`, `timestamp`, `event_type`, `status`, `stage`,
  `outcome`, `code`, and the existing bounded safe `message`;
- `current_priority` and `current_client_scope_label`, explicitly current metadata rather
  than event-time values.

The UI key is `(case_id, sequence)`. Messages are rendered as escaped text and are not
placed in URLs, logs, HTML, or analytics. No source payload, document content, evidence
body, cache key, endpoint reference, target request/response, token, hash, note, actor,
or invented identifier is returned.

The CSV endpoint is available only as the same authorized, filtered, bounded page. It
uses fixed safe columns and a static filename, emits canonical UTC timestamps and
standard CSV quoting, and returns `Cache-Control: no-store` plus
`X-Content-Type-Options: nosniff`. Formula-significant content beginning with `=`, `+`,
`-`, or `@` after any Unicode whitespace/control prefix is neutralized. It does not
export note text, raw evidence, source/provider payloads, credentials, or an unbounded
history.

## Ordering, paging, and validation

Global order is timestamp descending, canonical case UUID ascending, then sequence
descending. Memory and Mongo use the same rule. Stored canonical UTC strings are compared
at fixed six-digit fractional precision, preserving microseconds; timestamps do not prove
cross-case causal order.

Every request is independently authorized before event processing. Memory scopes cases
before inspecting events. Mongo first matches the server-authored case/team visibility,
then projects only required identity/schema/revision, current metadata, and event fields.
One bounded aggregation validates scoped candidate metadata and every projected event,
filters/sorts/pages in Mongo, and transfers at most `limit + 1` rows plus a bounded invalid
signal. Supported case envelopes v1-v5 remain readable without rewrite. Malformed scoped
identity, schema, revision, array, sequence, enum, timestamp, bounded string, or source
identity fails closed as a sanitized availability error; malformed other-team data does
not affect an ordinary team query.

The validation boundary is the scoped projected envelope/event data needed by this read.
It does not certify unprojected fields or the whole database. A bounded reply and one
aggregation do not imply constant-time scanning.

## Honest live-view limits

Offset pages are a live view, not a frozen snapshot. With unchanged data, traversal is
deterministic. Concurrent insertion or deletion can move page boundaries. At offset
10000 the UI disables further Next navigation and asks the user to narrow filters; it
does not claim the end of all retained history. Explicit refresh returns to page one.
Case deletion removes the corresponding available history. CSV export retains the same
live-view and pagination limits and does not claim to be a complete compliance archive.
