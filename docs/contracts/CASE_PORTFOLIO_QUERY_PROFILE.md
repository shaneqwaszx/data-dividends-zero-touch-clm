# Case Portfolio query profile

## Status and boundary

This project-defined POC contract covers `GET /api/clm/zero-touch/case-portfolio`.
It is an authorized, bounded read of current case summaries. It does not add assignment,
risk, SLA, approval, escalation, analytics, workflow, provider, retention, or Live
integration behavior. The compatible `GET /api/clm/zero-touch/cases` array response
remains unchanged and accepts the same optional creation-date bounds.

`CaseQueryService` owns actor/team scope and typed query composition. The existing
portfolio repository owns the memory or Mongo read. The endpoint returns the existing
bounded portfolio item projection in `{ items, offset, limit, has_more }`; it does not
decode detail aggregates or call providers, ownership analysis, workflow, target
execution, registry cache, or a persistence write.

## Request

| Input | Contract |
|---|---|
| `status` | Optional exact existing `AutomationStatus`. |
| `progress` | Optional `in_progress` (every status except `COMPLETED`) or `onboarded` (`COMPLETED` only). Intersects with `status`; any other value returns 422. Memory and Mongo apply the same single `automation.status` predicate after scope. |
| `priority_filter` | Existing `all`, `prioritised`, `unset`, or exact P1–P10 semantics. Default `all`. |
| `priority_sort` | Existing `highest_first` or `lowest_first`. Default `highest_first`. |
| `team_filter` | Existing Director-only exact team/`unassigned` semantics. Ordinary team actors cannot override scope. |
| `attention_type` | Optional exact existing `BusinessExceptionType`; only a correlated OPEN exception matches. |
| `jurisdiction` | Optional exact existing `JurisdictionCode`. A label does not activate a provider route. |
| `search` | Optional trimmed literal case-insensitive substring over requested registration ID, legal name, and canonical case UUID; maximum 128 characters. |
| `created_from` | Optional ISO date; includes midnight at the start of this Singapore UTC+08:00 calendar day. |
| `created_to` | Optional ISO date; includes this Singapore UTC+08:00 day through the instant before the next midnight. |
| `limit` | Integer 1–100; default 50. |
| `offset` | Integer 0–10000; default 0. |

Creation bounds use authoritative `automation.created_at`, normalized to UTC for reads.
An omitted bound is open-ended. Reversed, malformed or unrepresentable bounds return
safe 422 errors. Scope is resolved first; bounds intersect before sorting/pagination
in memory and Mongo. No schema, index, case timestamp or write behavior changes.

All filters intersect before paging. “All” is omission except for the existing explicit
priority defaults. Whitespace-only search becomes absent. Search is never interpreted as
regex, Mongo/SQL syntax, a glob, URL, field selector, or expression. Mongo escapes every
regular-expression metacharacter. The shared pattern owner expands each ASCII letter to
an explicit pair such as `[aA]` and escapes every non-ASCII code point literally. Memory
and Mongo use that same case-sensitive pattern, so their regex engines do not own case
semantics. This is ASCII-case-insensitive, not locale-aware or full-Unicode folding:
`ß` is not `ss`, and `i` is not `İ` or `ı`. Invalid enums, lengths, and paging values
receive the existing safe 422 validation behavior.

Server-authored authorization scope is resolved before case content can affect a result
or data-dependent error. Corrupt out-of-scope records cannot affect an ordinary team
actor's read.

## Ordering and paging

Prioritised rows precede unset rows. The selected numeric direction applies only to
non-null priorities. Equal priorities are ordered by `updated_at` descending and then
canonical case UUID string descending. Unset rows use the same recency/UUID tie order
after every prioritised row. Memory and Mongo implement this same order.

Every page applies scope and all predicates before sorting, offset, and a `limit + 1`
lookahead. `has_more` is derived from that lookahead. There is no total, approximate
count, or total-pages claim. Offset traversal is a live view rather than snapshot
isolation; concurrent mutations can move page membership. At offset 10000, the UI stops
forward traversal and asks the user to narrow the search or filters when lookahead still
finds data.

## Persistence and failure behavior

Memory examines only authorized cases before building content projections. Mongo uses
one read-only aggregation: an initial scope match, a pre-projection validity marker for
optional source containers, strict projected-candidate validation, composed
exact/literal predicates, deterministic sort, skip, `limit + 1`, and the bounded
portfolio projection. It uses neither row-detail fan-out nor `$out`/`$merge`, and it
never falls back to memory. Supported case envelopes v1–v4 remain readable.

Malformed authorized projected data fails closed as a sanitized availability error;
it is not silently omitted into a false partial page. The validation boundary covers
the fields required for this read and does not certify unprojected data. A bounded reply
and one aggregation do not imply constant-time scan cost, an index-backed SLA, or
production-scale performance.

Expected corrupt-data, unsupported-schema, and persistence-unavailable failures at the
HTTP boundary return status 503 with fixed detail code `CASE_PORTFOLIO_UNAVAILABLE` and
message `The case portfolio is temporarily unavailable.` Raw persistence detail is not
returned, and no error is converted to an empty or partial page.

## Frontend/session behavior

The Cases page uses a fixed page size of 50 and a 300 ms search debounce. Its query key
contains authenticated user, status, progress view, priority filter, priority sort, team, attention
type, jurisdiction, normalized search, both creation-date bounds, offset, and limit.
The Show control (All cases / In progress / Onboarded) sends `progress`; the Onboarded view fixes Status to
`COMPLETED`. There is no separate Onboarded page; old `/onboarded` links redirect to Cases. Changing any presentation
dimension resets the offset. Previous-key rows are hidden while a new search is being
debounced; GET cancellation retains `AbortSignal`.

All case-summary mutations invalidate the authenticated user's common case-list family.
Deletion first cancels that family, removes the deleted case from every cached page
envelope and incompatible supporting cache, then refetches active pages. Existing logout,
401, identity replacement, and session-change cancellation/clearing remain authoritative.
