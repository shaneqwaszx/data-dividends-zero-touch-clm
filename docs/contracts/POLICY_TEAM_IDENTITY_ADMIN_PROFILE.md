# Policy, Team, and Identity Administration Profile

## Authority and scope

This contract records **PROJECT-DEFINED POC BEHAVIOR PENDING SPONSOR
CONFIRMATION**. Global administration is separate from case envelopes and is owned by
team, profile, and policy repositories with memory and Mongo implementations.

The backend capability matrix is authoritative:

| Role | Case access | Policy read | Policy mutate | Profile/team admin |
|---|---|---|---|---|
| `CLIENT_ONBOARDER` | own team | yes | no | no |
| `RELATIONSHIP_MANAGER` | own team | yes | yes | no |
| `DIRECTOR` | global | yes | yes | no |
| `HR` | none | yes | no | yes |

HR is separate from, and not senior to, Director. User/team deletion, deactivation,
password reset, production IAM, and case reassignment are outside this phase.

## Team administration

`TEAM_A` and `TEAM_B` remain the persisted seed IDs and are displayed as Alpha and
Beta. New teams are created only by the server with a cryptographically random ID
matching `^TEAM_[A-F0-9]{24}$`. Normalized display names are unique. Teams remain
active and may be created or have metadata updated; they cannot be deleted or
deactivated. A new team starts with zero inherited cases. The backend derives and
persists both `normalized_display_name` and `normalized_client_scope_label` using NFKC
Unicode normalization, trim, whitespace collapse, and case-folding. Both keys are
unique; request DTOs reject browser-authored normalized fields.

Every team record carries strict metadata, optimistic `version`, UTC timestamps,
creator/updater IDs, and bounded append-only allowlisted audit events.

## Profile and authentication administration

Bootstrap inserts the five established case identities plus `hr-admin` only when
missing. Mongo-persisted hashes are authoritative after insertion and are never
overwritten from changed environment settings. Missing or malformed required seed
state fails closed.

User IDs are immutable and match `^[a-z][a-z0-9-]{2,31}$`. Client Onboarders and RMs
require an existing team; Directors and HR require a null team. Initial passwords are
12–128 characters, are hashed with the established scrypt format, and only the encoded
hash is persisted. Passwords and hashes are excluded from API, error, log, repr, and
audit projections.

HR may create profiles, edit display names, roles, and team assignments, and create
another HR. HR cannot self-demote, and an update cannot leave zero HR accounts.
Authority-changing updates increment profile `security_version`; authentication then
revokes the user's current process-local session and rejects any racing stale session
on its next version check.

The last-HR check is part of the repository-owned profile authority mutation. Target
load/version validation, self-demotion validation, HR population evaluation, and the
version/security-version/audit commit share one repository-wide lock in memory and one
application-process administration lock plus target CAS in Mongo. This is atomic for
the supported single-process POC repository boundary, not distributed IAM atomicity.

## Policy catalogue

The catalogue is a strict singleton with at most 64 typed rules and catalogue/rule
optimistic versions. It accepts no executable expressions or arbitrary nested JSON.
The eight seed rules are:

1. `DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD` — editable, runtime-enforced, default
   `0.85`.
2. `OWNERSHIP_UBO_THRESHOLD_PERCENT` — editable, runtime-enforced, default
   `25.000000`.
3. `OWNERSHIP_UBO_COMPARATOR` — fixed inclusive comparator.
4. `REGISTRY_SUPPORTED_JURISDICTIONS` — fixed `SG`.
5. `REGISTRY_PROVIDER` — fixed `ACRA`.
6. `DOCUMENT_SUPPORTED_MEDIA_TYPES` — fixed PDF, DOCX, UTF-8 TXT.
7. `WORKFLOW_SUPPORTED_STAGES` — fixed current supported stages.
8. `RECONCILIATION_SOURCE_PRECEDENCE` — fixed `NONE`.

Only RMs and Directors may mutate policy. Custom rules are forced by the backend to
`DISPLAY_SHOWCASE_ONLY` and cannot affect workflow execution. Stale expected catalogue
or rule versions return `409 POLICY_VERSION_CONFLICT`; no silent retry or last-write
wins is allowed.

Each user-authored showcase `STRING` value and `STRING_LIST` item must match
`^[A-Za-z0-9][A-Za-z0-9 _./:+%-]{0,127}$` and must not use code-like expression
prefixes. Quotes, backticks, grouping brackets, semicolons, equals, angle brackets,
backslashes, pipes, ampersands, and dollar interpolation therefore fail closed. This
does not reinterpret system-controlled enum/list values or add any execution path.

Single reset requires `RESET_POLICY_DEFAULT`; whole-catalogue reset requires
`RESET_ALL_POLICY_DEFAULTS`. Resets restore project defaults, retain custom showcase
rules, increment versions, and append audit evidence. These are not represented as
sponsor-approved defaults.

In the browser, RM and Director can edit backend-permitted runtime and custom showcase
rules; custom rules remain visibly labelled showcase-only and non-runtime. Single and
whole reset actions require an accessible confirmation. Cancel/Escape produce no
mutation, confirm is guarded against duplicate submission, and `409` triggers one
authoritative catalogue refetch without retrying the stale mutation. Client Onboarder
and HR retain read-only catalogue access.

## Runtime snapshot boundary

Only the IDP confidence and UBO percentage rules affect onboarding runtime. Each new
case binds those values, the fixed inclusive comparator, catalogue label/version, and
UTC `bound_at` into an immutable case snapshot before registry processing. Later
catalogue mutations affect only subsequently created cases. Legacy schema-v1/v2 cases
use the fixed synthetic legacy snapshot and are never rewritten merely by reading.

## Persistence and audit

Mongo uses `clm_admin_teams`, `clm_admin_profiles`, and `clm_admin_policies`, separate
from `clm_case_snapshots`. Team display names and coverage labels each have a unique
normalized index, alongside the bounded active/name index; profiles use the role/team
index; the singleton policy catalogue needs no secondary index. Startup strictly
decodes all stored team records before index creation, so a missing or inconsistent
derived key fails closed. Memory repositories apply the same normalization, uniqueness,
defensive-copy, version-CAS, and audit-prefix rules.

Audit events are allowlisted, append-only, and capped at 256. A mutation fails closed
at capacity; old events are not discarded. Audit never contains passwords, credential
hashes, session/CSRF data, Mongo connection data, or arbitrary model dumps.
