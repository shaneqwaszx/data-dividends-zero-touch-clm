# Case Access and Priority Profile

## Fixed identities

The backend owns exactly five explicitly synthetic profiles:

| User ID | Display name | Role | Internal team |
|---|---|---|---|
| `maya-lim` | Maya Lim | `CLIENT_ONBOARDER` | `TEAM_A` |
| `ethan-tan` | Ethan Tan | `RELATIONSHIP_MANAGER` | `TEAM_A` |
| `sophia-ng` | Sophia Ng | `CLIENT_ONBOARDER` | `TEAM_B` |
| `ryan-lee` | Ryan Lee | `RELATIONSHIP_MANAGER` | `TEAM_B` |
| `olivia-koh` | Olivia Koh | `DIRECTOR` | none/global |

`TEAM_A` is presented as DBS Corporate Onboarding and `TEAM_B` as OCBC Corporate
Onboarding. Both use the team type Corporate Client Onboarding, with DBS and OCBC client
coverage respectively. User IDs, role names, persisted team IDs, and client-scope labels
are closed server-side values. Passwords are supplied only as scrypt hashes through
backend configuration.

## Access contract

- Team actors may list, read, and use existing mutation routes only for an exact
  canonical case-team match.
- Director may list, read, and use existing mutation routes for all cases, including
  legacy unassigned records.
- Inaccessible and absent case IDs have the identical `404 CASE_NOT_FOUND` projection.
- A team actor's supplied creation team is rejected; the server assigns its profile
  team. Director creation requires `TEAM_A` or `TEAM_B` explicitly.
- `team_id` cannot be changed after first persistence, including from null to non-null.
- No route reassigns or shares a case.

## Priority contract

The canonical case-create JSON accepts optional `priority`. Omitted or explicit null is
stored as null; otherwise the value must be a strict JSON integer in `[1, 10]`. The
initial `OnboardingCase` is persisted with that value in the same creation operation.
Numeric strings, booleans, and floats are not coerced. Existing clients that omit the
field remain compatible.

`PATCH /api/clm/zero-touch/cases/{case_id}/priority` accepts JSON
`{"priority": null}` or a strict JSON integer in `[1, 10]`. Floats, booleans, strings,
collections, values below 1, and values above 10 are rejected. Any actor with access to
the case may change or clear priority under the case lock.

Lists are filtered for access before any status or priority selection and ordering.
`GET /api/clm/zero-touch/cases` accepts `priority_filter=all|prioritised|unset|1..10` and
`priority_sort=highest_first|lowest_first`. Invalid values receive `422`. Unset always
sorts after numbered priorities. The default canonical order remains:

1. prioritised before unprioritised;
2. priority descending;
3. automation `updated_at` descending;
4. canonical string `case_id` descending.

Status filtering does not alter this ordering. Priority never changes workflow stage,
readiness, target execution, SLA, escalation, notification, or due dates.

The normal browser create flow has no POST-then-PATCH sequence. It submits the optional
priority once, keeps team authority server-side, and renders the priority returned by
the create response.

## Session and CSRF contract

Login returns the authenticated profile plus a session-bound CSRF value and sets an
opaque session cookie. `/api/auth/me` returns the same bounded response. Logout revokes
the server record and expires the cookie. Invalid/unknown credentials, invalid/expired
sessions, cross-team access, and malformed security inputs use fixed safe errors without
echoing secrets or internal details.

Origin/Referer validation accepts only configured exact origins. Each request may contain
zero or one physical Origin field and zero or one physical Referer field; any duplicate
field fails closed regardless of ordering, capitalization, or identical values. Request
`Host` and forwarding headers cannot extend this allowlist. Origin must be exactly
`scheme://host[:port]`; a same-origin Referer may contain a path and query but no
fragment. Production requires an explicit HTTPS canonical origin and receives no
development-origin trust. Foreign, duplicate, or malformed values fail with
`CSRF_VALIDATION_FAILED`, and authenticated unsafe requests still require the
session-bound CSRF token.

## Persistence compatibility

New writes use strict envelope schema version 2. Exact version-1 documents remain
readable as `team_id=null, priority=null` and are not rewritten by reads. Team actors do
not see those records; Director does. Invalid or unknown storage is unavailable rather
than repaired heuristically.

## Dashboard read contract

`GET /api/clm/zero-touch/dashboard` accepts no actor, role, team, or scope parameters.
The authenticated server actor is the only authority. The response contains:

- backend-authored scope and team display metadata;
- a UTC `data_as_of` timestamp;
- total/completed/non-completed and prioritised/unprioritised counts plus the factual
  completion ratio;
- one count for every canonical `AutomationStatus`;
- priority counts for 10 through 1 and unset;
- only authorized team counts;
- at most ten recent cases and five non-completed cases in canonical priority order;
- a zero-filled 30-day UTC created/completed trend from persisted automation timestamps.

All calculation occurs after `CaseQueryService` authorization. Team responses contain
no global or other-team total, distribution, case identifier, UEN, name, or trend data.
The endpoint is provider-free and read-only in both memory and Mongo modes. Optional
safe case fields remain null when absent; no provider is called to enrich them.
