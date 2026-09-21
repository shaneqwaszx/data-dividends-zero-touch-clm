# Case Timing Profile

## Status and authority

This profile records Phase 19 project-defined POC presentation semantics for factual
case timing. It is not a sponsor-approved SLA, ageing policy, risk indicator, workflow
deadline, staff-performance metric, compliance decision, or production monitoring
contract.

The backend is the sole timing authority. A browser renders returned durations and never
recalculates them from its own clock. Every response uses one server-authored UTC
`observed_at`; a cached response remains a fixed observation until a refresh returns a
new response.

## Authoritative inputs and formulas

The projection uses only retained case/automation facts and one observation instant:

| Field | Formula | Meaning |
|---|---|---|
| `case_elapsed_ms` | `(completed_at ?? observed_at) - created_at` | completed case duration or active case age |
| `time_since_last_update_ms` | `observed_at - updated_at` | elapsed time since the retained aggregate update |
| `automation_elapsed_ms` | `(completed_at ?? observed_at) - started_at`, or `null` when no start exists | bounded automation elapsed time |
| `recorded_total_duration_ms` | retained `automation.metrics.total_duration_ms` unchanged | recorded total automated processing duration |

Durations are non-negative integer milliseconds. Sub-millisecond remainders are floored;
values are never rounded up, clamped, synthesized, or inferred from unrelated fields.
`recorded_total_duration_ms` is not recomputed from timestamps.

All timestamps must be timezone-aware UTC. The projection fails closed when retained
facts cannot support truthful timing, including an update or start before creation, a
future update/start/completion relative to `observed_at`, completion before creation or
automation start, a negative duration, or a malformed retained total. It does not repair
or hide invalid chronology.

## API compatibility

- `GET /api/clm/zero-touch/case-portfolio` returns `observed_at` exactly once at page
  level. Each item contains the four-field `timing` projection. Mongo performs the
  existing one scoped bounded aggregation per page; there is no detail-read fan-out.
- `GET /api/clm/zero-touch/cases/{case_id}` returns one backend-authored `timing`
  object containing `observed_at` and the same four fields. This avoids browser-time
  arithmetic on the Case Detail view.
- `GET /api/clm/zero-touch/cases` retains its existing array DTO exactly and gains no
  timing fields.
- Invalid portfolio timing returns the existing sanitized
  `CASE_PORTFOLIO_UNAVAILABLE` 503 response. Invalid detail timing returns the sanitized
  `CASE_TIMING_UNAVAILABLE` 503 response. Neither response exposes retained data or
  persistence details.

The portfolio remains authorized, filtered, ordered, paged, cached, invalidated, and
deleted under the existing Phase 18 and session-scoped React Query semantics. Phase 19
does not add polling, timers, background refresh, a new query key, or a write path.

## Display semantics

The UI labels an unfinished case value `Case age` and a completed value `Case duration`.
It labels the update delta `Last updated`, and formats exact returned milliseconds as
`< 1s`, seconds, minutes/seconds, hours/minutes, or days/hours. Neutral labels do not
classify a value as late, overdue, healthy, breached, on time, or within an SLA.

Per-stage values remain the durations already recorded by the orchestration owner around
successfully completed automated processing attempts. They do not measure full residence
time in a workflow stage, human waiting time, vendor response obligations, total case
duration, or accumulated time across retries. Missing automation start or total duration
is displayed as `Not started` or `Not recorded`; it is not replaced by zero.

## Explicit non-goals

This profile adds no current-stage age, status age, target/deadline, breach state,
traffic-light health, escalation, alert, notification, management KPI, predictive
estimate, historical time series, analytics store, migration, index, schema-version
bump, provider call, or workflow mutation.
