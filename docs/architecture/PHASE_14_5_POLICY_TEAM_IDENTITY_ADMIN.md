# Phase 14.5 Policy, Team, and Identity Administration

Phase 14.5 introduces three global persistence owners alongside, but outside, the case
envelope: `clm_admin_teams`, `clm_admin_profiles`, and the singleton
`clm_admin_policies` catalogue. Memory and Mongo implementations share repository
contracts, compare-and-swap versions, defensive validation, and bounded append-only
audit events. Case deletion or recovery never owns these global records.

Profile authority changes use one repository-owned mutation. In memory, one
repository-wide `RLock` covers target/version loading, the HR population check, and the
profile/security-version/audit commit. Mongo uses the shared administration store's
process-local lock around the same check and target CAS. This guarantees the last-HR
invariant within the supported single-process POC application boundary; it is not a
distributed or multi-instance IAM guarantee.

Authentication remains local POC authentication. A session stores only a digest, user
ID, account security version, timestamps, and CSRF token. Every authenticated request
reloads the profile and team from the repository. A role/team administration change
increments the security version and revokes all current process-local sessions for the
affected user. HR is synthetic and has identity/team administration plus policy-read
capabilities, but explicit zero case access and no policy mutation.

`TEAM_A` and `TEAM_B` remain persisted compatibility IDs, displayed as Alpha and Beta.
New IDs are server-generated as `TEAM_<24 uppercase hex>`. Runtime projections resolve
the canonical directory. Both display name and client coverage label have persisted,
backend-derived Unicode-normalized, whitespace-collapsed, case-folded uniqueness keys
in memory and unique Mongo indexes. Director portfolio requests may use `team_filter=all`,
`unassigned`, or a canonical team ID; actor authorization precedes filter validation and
application. Team actors cannot supply the parameter. Cases, Dashboard, and Onboarded
share the same backend query owner.

The policy catalogue starts with the exact eight rules recorded in the Phase 14.5
planner. Relationship Manager and Director may compare-and-swap edit only the IDP
confidence and UBO percentage runtime rules. System-derived rules are immutable, and
custom rules are forced to display-only. Resets are explicit versioned audit actions.
User-authored showcase string values and string-list items must match the strict safe
plain-text grammar; expression/script punctuation and code-like prefixes fail closed.
System-owned typed enum/list values remain governed by their canonical rule metadata.

The Policy UI exposes backend-permitted custom showcase editing to Relationship
Managers and Directors while keeping the non-runtime label visible. Single-rule and
whole-catalogue resets use accessible confirmation dialogs. Cancel and Escape issue no
mutation, confirmation is single-flight, and a `409` causes one authoritative catalogue
refetch with no automatic mutation retry. Row editors resynchronize from the returned
or refetched server catalogue.

Before Registry processing, onboarding copies the catalogue version, IDP threshold,
UBO threshold, fixed inclusive comparator, and binding timestamp into
`OnboardingCase.policy_snapshot`. Document assessment, reconciliation, CLM readiness,
zero-touch exceptions, and ownership load use this immutable snapshot. Ownership
analysis then uses the threshold retained on its analysis record. Policy edits never
reinterpret an existing case.

New durable case envelopes use schema v3. Strict schema-v1 and schema-v2 readers attach
`LEGACY_PHASE13_DEFAULTS_V1` (`0.85`, `25.000000`, inclusive) in memory and do not write
during a read. A later legitimate case mutation persists the validated v3 aggregate
without changing those bound values.

New API routes are:

- `GET /api/teams/options`
- `GET|POST /api/admin/teams`
- `PATCH /api/admin/teams/{team_id}`
- `GET|POST /api/admin/profiles`
- `PATCH /api/admin/profiles/{user_id}`
- `GET|POST /api/policies`
- `GET|PATCH /api/policies/{policy_id}`
- `POST /api/policies/{policy_id}/reset`
- `POST /api/policies/reset`

All routes remain inside the central session, CSRF, and exact Origin/Referer boundary.
Responses and audit metadata cannot contain passwords, password hashes, session tokens,
CSRF values, or connection details.
