# Policy, Team, and Identity Administration Profile

## Authority and scope

This contract records **PROJECT-DEFINED POC BEHAVIOR PENDING SPONSOR
CONFIRMATION**. Global administration is separate from case envelopes and is owned by
team, profile, and policy repositories with memory and Mongo implementations.

The backend capability matrix is authoritative:

| Role | Case access | Policy read | Business proposal | Policy decision | Profile/team admin |
|---|---|---|---|---|---|
| `CLIENT_ONBOARDER` | own team | yes | no | no | no |
| `RELATIONSHIP_MANAGER` | own team | yes | no | no | no |
| `DIRECTOR` | global | yes | no | independent approve/reject | no |
| `HR` | none | yes | own draft/edit/reset/submit | no | yes |

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

Case review/rework endpoints perform that next version/profile check again inside the
case mutation lock. Therefore a profile role/team/security-version change committed
after request-entry authorization but before mutation invalidates the action without
creating a reviewer/assignee identity or persisting actor attribution.

The last-HR check is part of the repository-owned profile authority mutation. Target
load/version validation, self-demotion validation, HR population evaluation, and the
version/security-version/audit commit share one repository-wide lock in memory and one
application-process administration lock plus target CAS in Mongo. This is atomic for
the supported single-process POC repository boundary, not distributed IAM atomicity.

## Policy catalogue

The catalogue is a strict singleton with at most 64 typed rules and catalogue/rule
optimistic versions. It accepts no executable expressions or arbitrary nested JSON.
The current catalogue has 39 seed rules (see the Phase24C and recursive ownership
amendments below). The historical first 21 definitions, including 13 intelligence rules,
are:

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
9. `ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD` — editable project default `0.85`.
10. `ENTITY_RESOLUTION_REVIEW_THRESHOLD` — editable project default `0.60`.
11. `ENTITY_RESOLUTION_AMBIGUITY_MARGIN` — editable project default `0.03`.
12. `ENTITY_RESOLUTION_IDENTIFIER_WEIGHT` — editable project default `0.55`.
13. `ENTITY_RESOLUTION_NAME_WEIGHT` — editable project default `0.25`.
14. `ENTITY_RESOLUTION_ADDRESS_WEIGHT` — editable project default `0.10`.
15. `ENTITY_RESOLUTION_LEGAL_FORM_WEIGHT` — editable project default `0.05`.
16. `ENTITY_RESOLUTION_INCORPORATION_DATE_WEIGHT` — editable project default `0.05`.
17. `UBO_ADVISORY_LIKELY_THRESHOLD` — editable project default `0.65`.
18. `UBO_ADVISORY_UNLIKELY_THRESHOLD` — editable project default `0.35`.
19. `MOCK_RISK_MEDIUM_THRESHOLD` — editable project default `30`.
20. `MOCK_RISK_HIGH_THRESHOLD` — editable project default `60`.
21. `MOCK_RISK_BLOCKS_READINESS` — editable project default `false`.

The entity weights must total one, review/auto-match and low/high threshold ordering
must remain valid, and every intelligence value retains its project-defined POC label.

HR alone prepares business proposals. Director alone approves/rejects another actor's
submitted current-base proposal. Every mutation reauthorizes inside the service lock
and uses aggregate/proposal CAS. Stale versions return409 POLICY_VERSION_CONFLICT,
without retry or last-write wins. Legacy direct edit/reset/showcase endpoints deny all
roles. Historical safe display-only rules remain readable with no runtime effect.

Reset stages the defined default in a proposal; ACTIVE values change only after
independent approval. Browser confirmation supports Cancel/Escape/focus restoration
and a duplicate-submit guard. Conflict refreshes authoritative catalogue truth.
Read-only users see current/default/formula/description/Affects/version; HR sees
proposed values/reason/submit; Director sees before-after synthetic impact and decision.

## Runtime snapshot boundary

Each new case binds the IDP confidence and UBO percentage rules plus all 13 intelligence
rules, registry freshness/definitive-negative TTL, semantic classifier parameters, the fixed
inclusive comparator, ACTIVE identity/catalogue label/version and UTC `bound_at` into
an immutable case snapshot before registry processing. Entity resolution, UBO advice,
and mock advisory risk persist their policy-derived weights, thresholds, model versions,
and readiness flag consistently with that snapshot. Later catalogue mutations affect
only subsequently created cases. Legacy schema-v1/v2 cases use the fixed synthetic
legacy snapshot; schema-v3/v4 cases have no intelligence policy or projection. Reads do
not rewrite a legacy envelope merely to advance its schema.

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

## Phase24C policy amendment — 2026-10-02

The current policy authority matrix supersedes the earlier policy-mutate column:
HR may draft/edit/reset-through-proposal/submit; Director may approve/reject another
user's submitted current-base proposal; RM/onboarder read only. HR still has no case
access. Director gains POLICY_APPROVE and loses POLICY_MUTATE. Current catalogue has
35 seeds: the earlier 29 plus registry freshness days (90), NOT_FOUND TTL seconds (600),
semantic kind/binding/confidence weights (0.50/0.25/0.25, sum exactly one), and semantic
threshold (0.50). Every editable rule is runtime enforced; arbitrary showcase creation
and direct activation are retired, and all target/provider/security definitions are
not business editable. Historical display rules remain readable.

Policy schema2 separates aggregate CAS version from ACTIVE version. Proposals (max64),
superseded active versions (max64), and append-only audit (max256) fail closed on capacity,
unknown/invalid state, UTC/chronology mismatch, duplicate activation or inconsistent
approval history. Historical schema1/absent-version catalogues retain their stored
values; exact supported 8/21/29-seed prefixes plus historical display rules gain missing
runtime definitions once. Partial/unknown runtime catalogues fail closed. No global
approval changes historical case snapshots. See POLICY_ACTIVATION_CONTRACT.md/D-064.

## Recursive ownership discovery amendment — 2026-10-23

Four project-defined, editable, runtime-enforced Ownership rules are appended (39 seeds):
`OWNERSHIP_TRACE_THRESHOLD_PERCENT` (10.000000, range 0.000001-100, never above the
active UBO threshold), `OWNERSHIP_DISCOVERY_MAX_CORPORATE_DEPTH` (5, range 1-7, below the
unchanged 8-edge calculation ceiling), `OWNERSHIP_REGISTRY_CALL_BUDGET_ENABLED` (false)
and `OWNERSHIP_REGISTRY_CALL_BUDGET_MAX` (10, range 1-32; counts provider-backed corporate
issuer acquisitions, not cache hits). Submission, approval, impact and case snapshots
reject a trace threshold above the effective UBO threshold. New case snapshots freeze
these values as `ownership_discovery`; historical snapshots without it keep root-only
ownership semantics and never acquire subsidiaries.

An exact 35-seed prefix gains the four rules once. When the catalogue has no proposals,
superseded versions or approved activation, the existing rebuild applies. Otherwise
catalogue schema 3 records an audited `MIGRATED` activation: active values are kept, the
replaced active rules become a retained superseded version, decided or already-stale
proposals are retained unchanged, and undecided proposals on the replaced base are
rebased by adding only the new default rules. No new value is approved automatically.
