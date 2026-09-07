# Case Access and Priority Profile

## Fixed identities

The backend owns exactly five synthetic profiles: Client Onboarder and Relationship
Manager for each of `TEAM_A`/DBS and `TEAM_B`/OCBC, plus one teamless Director. User IDs,
role names, team IDs, and client-scope labels are closed server-side values. Passwords
are supplied only as scrypt hashes through backend configuration.

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

`PATCH /api/clm/zero-touch/cases/{case_id}/priority` accepts JSON
`{"priority": null}` or a strict JSON integer in `[1, 10]`. Floats, booleans, strings,
collections, values below 1, and values above 10 are rejected. Any actor with access to
the case may change or clear priority under the case lock.

Lists are filtered for access before ordering. Their canonical order is:

1. prioritised before unprioritised;
2. priority descending;
3. automation `updated_at` descending;
4. canonical string `case_id` descending.

Status filtering does not alter this ordering. Priority never changes workflow stage,
readiness, target execution, SLA, escalation, notification, or due dates.

## Session and CSRF contract

Login returns the authenticated profile plus a session-bound CSRF value and sets an
opaque session cookie. `/api/auth/me` returns the same bounded response. Logout revokes
the server record and expires the cookie. Invalid/unknown credentials, invalid/expired
sessions, cross-team access, and malformed security inputs use fixed safe errors without
echoing secrets or internal details.

## Persistence compatibility

New writes use strict envelope schema version 2. Exact version-1 documents remain
readable as `team_id=null, priority=null` and are not rewritten by reads. Team actors do
not see those records; Director does. Invalid or unknown storage is unavailable rather
than repaired heuristically.
