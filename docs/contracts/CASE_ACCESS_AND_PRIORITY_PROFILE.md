# Case Access and Priority Profile

## Current identity and team authority

This is **PROJECT-DEFINED POC BEHAVIOR PENDING SPONSOR CONFIRMATION**. The
backend team and profile repositories are the runtime authority. The five Phase 13
identities retain their user IDs, roles, and persisted assignments; `hr-admin` is added
as an administration-only identity and `support-user` (D-103) as a knowledge-review-only
identity.

| User ID | Role | Team |
|---|---|---|
| `maya-lim` | `CLIENT_ONBOARDER` | `TEAM_A` |
| `ethan-tan` | `RELATIONSHIP_MANAGER` | `TEAM_A` |
| `sophia-ng` | `CLIENT_ONBOARDER` | `TEAM_B` |
| `ryan-lee` | `RELATIONSHIP_MANAGER` | `TEAM_B` |
| `olivia-koh` | `DIRECTOR` | none/global |
| `hr-admin` | `HR` | none/administration-only |
| `support-user` | `SUPPORT` | none/knowledge support only |

`SUPPORT` has no `CASE_ACCESS`: no portfolio, case pages or case mutation. Its
`KNOWLEDGE_CASE_READ` capability admits only `GET /api/clm/zero-touch/cases/{case_id}` and
`GET /api/onboarding/cases/{case_id}/documents` (route access `CASE_READ`), so the AI
Assistant can redact a knowledge fix against the request's case; every other case route
answers as absent (D-103).

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

The case-list route also accepts an optional exact `attention_type` from the existing
`BusinessExceptionType` enum. It is applied only after role/team authorization to the
bounded portfolio projection and composes by intersection with the existing filters.
Omission preserves the existing result set and order. Each row reports unique retained
`OPEN` business-exception types in canonical enum-declaration order; resolved/cancelled
history is excluded, while the existing exception count continues to count actual open
records. An empty list means only that no open business exception is recorded. It does
not assert health, completion, approval, risk, urgency, or absence of technical/recovery
attention. No assignment, SLA, escalation, notification, or approval authority is added.

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

PR95 Dashboard v2 is a project-defined operational read model. Authorization and
Director `team_filter` run before `scope=team|mine` and created-date filtering.
`mine` case counts/lists mean immutable creator equals the authenticated user; legacy unknown creator
is never inferred. HR is denied, RM/onboarder scope remains exact own-team, and
inaccessible case activity retains the same safe `404` as an absent case.

`date_range=7d|30d|90d|all` defaults to `all` for backward compatibility.
Dashboard v2 explicitly requests `30d` on initial load. Bounded ranges include exactly N Singapore
calendar dates ending today, using the existing UTC+08:00 half-open portfolio bounds.
Totals, lists and metric denominators all use this same selected case set; `all`
includes historical cases. Weekly completion buckets remain eight UTC Monday weeks
within that selected set. A case created before the selected range is excluded even
if completed recently. No completion-date cohort is implied.

The original `historical_trend` schema and calculation remain: 30 zero-filled UTC
calendar days through `data_as_of`, counting creation and recorded completion dates
over the full authorized view before the new created-date cohort filter. Thus a case
created 45 days ago and completed today still contributes to the legacy completion
trend even when the v2 selected 30-day cohort excludes it. Callers without new
parameters retain all-history totals and existing default team scope.
New `view`, `zero_touch_rate`, `timing`, `stage_timing`, `exception_breakdown`,
`weekly_onboarded`, `workload_by_person` and `scoped_cases` fields are additive.
The shipped browser and shared types consume v2 atomically. Recent cases are capped
at 10, active cases at 5, selected cases at 200, and slowest stage cases at 3. Counts use
the full selected cohort even when lists are truncated.

Zero-touch rate is completed cases with zero recorded exception interventions divided
by completed cases; empty denominator gives 0. Final human Review & Send remains
required and is not an exception intervention. Means use recorded non-null workflow-start-to-completion durations;
intake before start is excluded, and unknown timings stay null. Progress is recorded automated stages / 6, capped at 100,
with COMPLETED always 100. It is a project-defined display metric, not approval proof.
Stage timing groups recorded processing-attempt durations by retained blocker history;
it excludes waiting and resolution time.
Exceptions include retained history; none of these metrics is a sponsor SLA,
compliance calculation, staff-performance rating or Live-integration claim.

Additive insight fields (defaulted, so older callers keep working) use the same selected
case set. Each stage row adds `reached_count` (cases with a recorded duration or a retained
blocker at that stage) and `resolution_mean_ms`/`resolution_count` (RESOLVED blockers raised at
that stage). These are reported separately from processing time, which still excludes waiting.
Each exception row adds `open_count`, `resolved_count`, `mean_fix_ms` and `total_fix_ms`.
CANCELLED blockers count only toward `count`, and the existing frequency order is unchanged.
Fix and resolution times use the workload fix-time arithmetic: elapsed resolution minus
blocker creation, in exact floored milliseconds, not active working time. Each weekly bucket
adds `zero_touch_count`: its completed cases with zero recorded exception interventions. Each
team row adds `status_breakdown` and `zero_touch_count`. The browser derives open, blocked,
weekly zero-touch rate and per-stage pass-without-stopping share from these counts; a week
or team without completions shows no rate rather than 0%.

Management fields (D-127, `PROJECT_DEFINED_PROVISIONAL`, display-only) are additive.
`attention_policy` returns the rules the response used. `kpis` covers the selected case set:
open, running, blocked (`WAITING_FOR_REVIEW`, `RECOVERY_PENDING`, `TECHNICAL_FAILURE`) and
awaiting-review counts; completions; zero-touch rate; mean summed recorded step processing of
completed cases; mean creation-to-completion time; SLA met count and compliance; and overdue,
at-risk and high-attention open cases. Rates and means are null without a denominator.
`previous_period` is present only for a bounded `date_range`. It covers the equally long run
of Singapore calendar days immediately before the selected window, applies the same
authorization and `scope` rules, and reports completion figures only.
Open-case SLA counts are omitted there because they would be read at the current instant.
Case items add `jurisdiction`, `sla_status`, `sla_due_at`, `attention_level`,
`attention_reasons`, `open_exception_types` and `oldest_open_blocker_age_ms`. An OPEN blocker
created after the observation fails closed as `DASHBOARD_UNAVAILABLE`. Stage rows add
`processing_total_ms`, `resolution_total_ms` and `open_blocked_count` (cases whose blocker at
that step is still OPEN). Exception rows add `by_jurisdiction`,
`unresolved_jurisdiction_count` and `weekly_counts`, aligned with the eight weekly buckets by
blocker creation week. Weekly rows add `mean_end_to_end_ms`. Workload rows add running,
blocked, overdue and high-attention creator counts. Team rows add `sla_met_count`, `overdue_count`,
`high_attention_count`, `mean_end_to_end_ms`, `resolved_blockers` and `mean_fix_ms` over that
team's cases in the selected set. As before, they appear only in the `team` view and only for
teams the actor can see. `rework` counts cases with two or more
retained blockers at the same step. No field is a sponsor SLA, compliance result,
staff-performance rating or approval signal.

Workload open/completed case counts belong to the immutable creator. Fix counts and
mean fix time belong to the last recorded resolver, once per RESOLVED exception,
within the authorized/date-selected case cohort, including a teammate's created cases.
Mine returns only the requesting actor's workload row; its own resolver aggregate
still includes authorized teammate cases, while its creator counts and case lists
remain creator-only. Other-team and excluded-date fixes never enter that aggregate.
Only actor evidence recorded at/after retained resolution can attribute that fix;
earlier draft decisions and cancelled/open blockers are excluded. Missing historical
actor evidence remains unattributed. Display names use the existing
synthetic profile labels, with recorded identifiers for other actors. Mine view uses
the authenticated actor's workload row by ID, never array position. Timing is elapsed
recorded resolution time minus blocker creation, not active working time.

Memory and Mongo expose the validated nullable creator internally; Mongo portfolio
projections and activity aggregation enforce schema 9/10 identity grammar and reject
later creator fields on schemas 1..8. The activity `created_by` filter intersects role,
team, case, action, stage, outcome and date filters before paging. It is a creator
filter, not event-actor attribution. No schema version, migration or write changes.
The endpoint is provider-free and read-only; no out-of-scope totals or identities are
returned. Case/scoped automation aggregation remains linear in retained POC inventory.

Dashboard case items add `case_elapsed_ms` from the canonical case timing projection.
All case lists and creator oldest-open values share the response `data_as_of` instant.
The browser renders, sorts and filters these returned durations without using its clock;
completed cases use completion minus creation. Invalid chronology or persistence reads
return a sanitized `503 DASHBOARD_UNAVAILABLE`, without retained facts or private errors.

The single dashboard observation follows both retained input reads. Cohort calendar
bounds and the legacy UTC trend use that final observation, including midnight
interleavings. Resolution elapsed values and means use exact integer milliseconds,
flooring sub-millisecond remainders without a floating-point conversion.
