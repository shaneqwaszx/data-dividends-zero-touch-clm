# Phase 13 Case Priority, Authentication, and Team RBAC

## Scope

Phase 13 adds a bounded local-POC authentication boundary, five fixed synthetic user
profiles, two fixed teams, server-owned case visibility, and nullable priority. It does
not change Registry, document, reconciliation, ownership, readiness, or Mock GoldTier
workflow decisions and does not claim production IAM or compliance authorization.

## Request boundary

`POST /api/auth/login` is the only public `/api` operation. Every other `/api` route is
authenticated by one middleware boundary. The server keeps only a SHA-256 digest of an
opaque random session token and issues the token in a host-only, HttpOnly,
`SameSite=Strict`, `/api` cookie. Sessions have an eight-hour absolute lifetime, are
process-local, and rotate on login. Unsafe methods also require the session-bound
`X-CSRF-Token`. A request may contain at most one physical Origin field and at most one
physical Referer field; duplicates fail closed even when their values are identical.
Browser Origin/Referer values, when supplied, must match an exact configured origin.
Referer may include a path and query but not a fragment. Request `Host` is never a trust
input. Development/test owns exact backend and Vite loopback origins; production
requires an explicit canonical HTTPS origin and fails before persistence initialization
if it is absent or malformed.

The route classifier assigns every protected operation to actor-only or case-scoped
access. Case-scoped authorization loads the canonical onboarding aggregate and returns
the same fixed `404 CASE_NOT_FOUND` response for absent and inaccessible cases. Client
headers and query parameters never supply identity, role, or team authority.

## Teams and access

The persisted fixed POC teams remain `TEAM_A` and `TEAM_B`. Their browser names are
DBS Corporate Onboarding and OCBC Corporate Onboarding; both have type Corporate
Client Onboarding and DBS/OCBC client coverage respectively. Client Onboarder and
Relationship Manager profiles can see and mutate only cases whose immutable canonical
`team_id` matches their profile. Director has global visibility, including schema-v1
legacy cases whose team is null, and has the same existing mutation surface. Team users
cannot enumerate legacy unassigned cases. Team-scoped actors create into their own team;
Director must explicitly select a team. There is no reassignment, sharing, multi-team
membership, maker-checker, or separate role-based mutation matrix.

## Priority and persistence

Priority is either null or a strict integer from 1 through 10. It affects portfolio
ordering only: non-null first, higher value first, then the accepted automation
`updated_at` and canonical `case_id` descending tie-breaks. Priority changes update the
case/event audit evidence but not automation workflow state or automation `updated_at`.
The canonical create request accepts the same optional strict value and passes it through
the existing zero-touch, CLM, and onboarding creation chain, so the first persisted
`OnboardingCase` already owns the requested priority. Omission and explicit null both
produce null. Existing PATCH behavior remains available for later reprioritisation.

Historical list priority filters and ascending/descending priority sort are applied by
the backend only after the actor's authorized portfolio has been established. Unset
priority remains last in either direction; Dashboard top-active ordering is unchanged.

Mongo envelope schema version 2 stores `team_id` and priority. Exact schema-v1 envelopes
are strictly decoded to an in-memory null/null representation without read-time rewrite.
Unknown versions, unknown fields, invalid teams, invalid priorities, and storage identity
mismatches fail closed. Memory and Mongo repositories enforce team immutability.

## Frontend boundary

The browser restores `/api/auth/me` into React memory only. The authenticated workspace
is not mounted until restoration succeeds. All API calls use credentialed fetch through
one transport; unsafe requests receive the in-memory CSRF value. A `401` clears the
sensitive shell and returns to sign-in. No token, CSRF value, password, role, or team is
stored in local/session storage or treated as browser authority. Queue, Onboarded,
detail, and audit views show server-returned scope and priority and preserve backend
ordering. Normal New Onboarding shows the authenticated profile's canonical team name,
or the Director's explicit backend-authored team choice, plus an optional priority
selector. Creation uses one POST and renders the returned case priority without a
follow-up priority mutation.

## Synthetic showcase portfolio

The authenticated seeder signs in as synthetic Director `olivia-koh`, creates missing
cases with priority in the canonical request, then attaches one bounded fictional PDF
through the existing demo document API. The registered `STRAIGHT_THROUGH` providers and
normal orchestration must return `COMPLETED` with CLM status
`MOCK_GOLDTIER_SUBMITTED`; the seeder never assigns terminal state. It reuses an exact
team/UEN/priority/success match when available, uses the existing priority PATCH only to
reconcile a selected reused mismatch, and fails nonzero unless one valid showcase case
exists for every intended pair. Unrelated shared historical cases, including colliding
team/UEN records, are not deleted or rewritten.

## Historical dashboard read model

`GET /api/clm/zero-touch/dashboard` is an authenticated actor-only route. The dedicated
dashboard service consumes `CaseQueryService`, so canonical case-team authorization is
applied before totals, exact automation-status counts, priorities 10 through 1 plus
unset, team counts, recent cases, top active cases, and the 30-day UTC created/completed
trend are calculated. A team response contains only its own team metadata and records;
Director receives both team counts and authorized legacy history.

Dashboard reads call no Registry, IDP, ownership, reconciliation, or GoldTier provider
and do not query Mongo directly. The same repository abstraction serves memory and
Mongo modes. Mongo makes the historical view durable across backend restart; memory
mode remains process-local. Completion rate is only the factual ratio of canonical
`COMPLETED` cases to authorized cases, with zero for an empty scope. It is not an SLA,
approval, risk, productivity, or regulatory KPI.

## Deliberate limitations

This is local scrypt/password and process-local session infrastructure for a synthetic
demo. It is not PingFed/SSO, MFA, OAuth, a production session store, production RBAC,
rate limiting, account lockout, assignment, SLA, escalation, notification, or a
regulatory audit solution. The provisional policy remains subject to Q-016.
The Dashboard is a V1 operational read model, not an analytics warehouse, production BI
platform, configurable KPI system, or source of truth separate from canonical cases.
