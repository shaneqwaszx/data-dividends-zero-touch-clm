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
`X-CSRF-Token`; browser Origin/Referer values, when supplied, must be same-origin.

The route classifier assigns every protected operation to actor-only or case-scoped
access. Case-scoped authorization loads the canonical onboarding aggregate and returns
the same fixed `404 CASE_NOT_FOUND` response for absent and inaccessible cases. Client
headers and query parameters never supply identity, role, or team authority.

## Teams and access

The fixed POC teams are `TEAM_A` (DBS) and `TEAM_B` (OCBC). Client Onboarder and
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
ordering.

## Deliberate limitations

This is local scrypt/password and process-local session infrastructure for a synthetic
demo. It is not PingFed/SSO, MFA, OAuth, a production session store, production RBAC,
rate limiting, account lockout, assignment, SLA, escalation, notification, or a
regulatory audit solution. The provisional policy remains subject to Q-016.
