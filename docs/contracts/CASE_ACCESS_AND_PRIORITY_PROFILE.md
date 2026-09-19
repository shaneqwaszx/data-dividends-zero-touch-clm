# Case Access and Priority Profile

## Current identity and team authority

This is **PROJECT-DEFINED POC BEHAVIOR PENDING SPONSOR CONFIRMATION**. The
backend team and profile repositories are the runtime authority. The five Phase 13
identities retain their user IDs, roles, and persisted assignments; `hr-admin` is added
as an administration-only identity.

| User ID | Role | Team |
|---|---|---|
| `maya-lim` | `CLIENT_ONBOARDER` | `TEAM_A` |
| `ethan-tan` | `RELATIONSHIP_MANAGER` | `TEAM_A` |
| `sophia-ng` | `CLIENT_ONBOARDER` | `TEAM_B` |
| `ryan-lee` | `RELATIONSHIP_MANAGER` | `TEAM_B` |
| `olivia-koh` | `DIRECTOR` | none/global |
| `hr-admin` | `HR` | none/administration-only |

`TEAM_A` is displayed as Alpha and `TEAM_B` as Beta. Their persisted IDs are not
migrated. New server-generated IDs match `TEAM_<24 uppercase hex>` and inherit no
existing cases. Current team display metadata is repository data rather than access
authority; case access always uses exact canonical stored team-ID equality.

## Capability and case-access contract

- Client Onboarders and Relationship Managers may access only exact own-team cases.
- Directors have global case access, including legacy unassigned cases.
- HR has no case list, detail, creation, mutation, Dashboard, Onboarded, or Audit
  authority. An HR direct case lookup uses the same `404 CASE_NOT_FOUND` projection as
  an absent case.
- Inaccessible and absent case IDs have the identical non-enumerating projection.
- Team-scoped creation derives the team from the authenticated profile. Director
  creation requires an existing canonical team.
- No route reassigns or shares a case. HR profile administration may change a user's
  future authority, increments `security_version`, and invalidates existing sessions.

`GET /api/clm/zero-touch/cases` and Dashboard/Onboarded reads accept a Director-only
`team_filter`: `all`, `unassigned`, or a canonical existing team ID. Team-scoped actors
cannot use the filter. Filtering is performed by backend query services before
projection or aggregation; frontend filtering is not an authority boundary.

## Priority contract

Case create accepts optional strict integer `priority` in `[1, 10]` or null. Priority
updates accept the same values. Numeric strings, booleans, floats, collections, and
out-of-range values are rejected. Lists authorize and filter before applying
`priority_filter`, `priority_sort`, and canonical ordering:

1. prioritised before unprioritised;
2. priority descending;
3. automation `updated_at` descending;
4. canonical string `case_id` descending.

Priority does not change workflow stage, readiness, target execution, SLA,
escalation, notification, or due dates.

## Session and browser protections

Authentication loads the current persisted account for every request. Opaque
process-local session records retain only bounded session metadata, `user_id`, and the
account `security_version`; they are not permanent profile snapshots. A missing
account or version mismatch removes the stale session and returns the fixed `401`.
Role/team changes also attempt explicit revocation. One active session per user,
session rotation, dummy-hash unknown-user handling, generic login failure,
session-bound CSRF, cookie behavior, and exact Origin/Referer checks remain in force.

Sensitive review/rework mutations capture only the request session token and then load
the current session/profile and case access again inside the owning case lock immediately
before actionable evidence is read. This applies to field review, replacement and
targeted retry, reconciliation resolution, and explicit start/resume. Revoked or stale
sessions receive the fixed `401`; an actor who no longer has case scope receives the
same safe `404 CASE_NOT_FOUND` as an absent case, with no evidence or target mutation.

Browser-safe profiles never contain passwords, credential hashes, sessions, CSRF
values, or secret configuration.

## Persistence compatibility

New case snapshots use schema version 3 and contain an immutable
`CasePolicySnapshot`. Exact schema-v1 and schema-v2 records remain readable, bind the
fixed legacy `0.85` IDP and `25.000000` inclusive UBO thresholds in memory, and are not
rewritten by reads. Existing team IDs and priorities retain their prior meaning.

## Dashboard contract

Dashboard calculations occur only after authorization and the Director team filter.
The response carries backend-authored team/scope metadata, UTC `data_as_of`, canonical
status and priority counts, completion ratio, authorized team counts, bounded recent
case projections, and a zero-filled 30-day UTC trend. The endpoint is provider-free
and read-only. Team-scoped responses contain no global or other-team totals or case
data; HR is denied.
