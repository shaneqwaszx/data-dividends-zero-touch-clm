# External Contract Workspace

Phase 0 must produce the canonical contract baseline here.

Expected output:

`docs/contracts/GOLDTIER_CONTRACT_BASELINE.md`

The baseline should reconcile:
- sponsor clarifications
- standalone OpenAPI files
- combined OpenAPI bundle
- JSON request/response examples
- EDS-GoldTier specification
- data dictionary
- connection/Postman examples

Do not silently choose between conflicting artefacts. Record discrepancies and the reason for the chosen canonical behaviour.

Phase 02's explicitly provisional ACRA source-to-canonical field boundary is recorded
in `ACRA_CANONICAL_MAPPING.md`. It must not be treated as an ACRA-published API schema;
the exact subscribed endpoint/auth/response contract remains Q-012.
The sponsor-readable current synthetic retrieval surface, field coverage, scenarios,
errors, explicit omissions, and future `TBD_SPONSOR` mapping boundary are in
`ACRA_MOCK_API_PROFILE.md`. Phase 10 expands that profile with four project-owned Mock
operations, strict bounded DTOs, empty/partial/failure semantics, normalized evidence,
and registry-to-existing-ownership integration; none is an authoritative ACRA API claim.

Phase 03's synthetic IDP provider/API boundary is recorded in
`IDP_REVIEW_CONTRACT.md`; its four-field project-defined profile, threshold,
normalization, comparison, and review rules are recorded in `IDP_FIELD_PROFILE.md`.
Neither is a sponsor document schema or vendor OCR contract; Q-003, Q-005, Q-013, and
Q-014 remain unresolved.

Phase 04's source-neutral party/relationship, Decimal path/aggregation, provisional
threshold, cycle/incomplete, provenance, and graph-limit rules are recorded in
`OWNERSHIP_UBO_PROFILE.md`. They are project-defined pending Q-002/Q-004/Q-006/Q-007,
not a sponsor-approved UBO or GoldTier hierarchy contract.

Phase 05's staged readiness and target preparation are recorded in
`CLM_READINESS_POLICY.md` and `GOLDTIER_SUBMISSION_PREPARATION.md`. Phase 06's
provisional automatic-continuation, exception, and replay rules are recorded in
`ZERO_TOUCH_AUTOMATION_POLICY.md`; replaceable provider expectations are recorded in
`INTEGRATION_ADAPTER_CONTRACTS.md`. They do not resolve the open sponsor questions.

Phase 12's schema-version, configuration, structured-data retention, restart, and
side-effect replay boundaries are recorded in `PERSISTENCE_RECOVERY_PROFILE.md`. It is a
local durable POC contract, not a sponsor-approved retention/audit standard.

Phase 13's fixed synthetic identity/team policy, non-enumerating case access, strict
nullable priority, canonical ordering, and schema-v1/v2 compatibility are recorded in
`CASE_ACCESS_AND_PRIORITY_PROFILE.md`. These are project-defined POC rules pending
Q-016, not production RBAC, assignment, SLA, or identity governance.

Phase 14.5's repository-backed teams/profiles, HR capability boundary, typed policy
catalogue, and immutable schema-v3 case policy snapshot are recorded in
`POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md`. These remain project-defined POC behavior
pending sponsor confirmation, not production IAM or approved compliance policy.

Phase 16's disabled-by-default, synthetic Mock-only shared registry snapshot boundary,
fixed elapsed freshness rule, exact-key isolation, immutable case binding, and
memory/Mongo failure semantics are recorded in `REGISTRY_CACHE_FRESHNESS_PROFILE.md`.
They are provisional project-owner-approved POC behavior, not an ACRA validity,
licensing, production-sharing, or retention policy.

Phase 18's authorized bounded search/pagination behavior is recorded in
`CASE_PORTFOLIO_QUERY_PROFILE.md`. Phase 19's backend-authored observation instant,
deterministic duration formulas, fail-closed chronology rules, response compatibility,
and neutral presentation semantics are recorded in `CASE_TIMING_PROFILE.md`. These are
factual POC projections, not sponsor-approved SLA, risk, compliance, productivity, or
deadline policy.

Phase 20's sponsor-policy authority boundary is recorded in
`POLICY_AUTHORITY_MATRIX.md`, `POLICY_ACTIVATION_CONTRACT.md`,
`POLICY_FUTURE_ACCEPTANCE_SCENARIOS.md`, `POLICY_DECISION_TRACEABILITY.md`, and the
strict machine-readable `policy_authority_registry.json`. These artefacts classify
authority and define future decision prerequisites; they do not answer open sponsor
questions or activate runtime policy. The sponsor-readable response packet is
`../sponsor-questions/PHASE_20_POLICY_DECISION_PACKET.md`.

Phase 21's external-provider activation boundary is recorded in
`EXTERNAL_PROVIDER_ACTIVATION_CONTRACT.md`, the strict
`external_provider_readiness_registry.json`, and the sanitized
`external_provider_evidence.schema.json`. The provider registry and checker classify
current Mock/Local/Partial/Dormant/Not-Implemented truth; they do not activate a real
provider or replace the policy-authority registry. The sponsor/integration packet is
`../integration/PHASE_21_PROVIDER_ACTIVATION_PACKET.md`.
Evidence profile v2 is intentionally incompatible with the earlier candidate profile:
it replaces permissive reference strings plus blacklist inspection with finite
vocabularies, canonical UUIDs, and control-free, calendar-valid UTC instants enforced
consistently by JSON Schema and Python. Duplicate keys fail with constant non-echoing
diagnostics at both direct and imported loader boundaries. Adding a new operation,
contract, or mapping reference requires an explicit schema/validator change and review.
The same v2 contract binds complete records to four current credential-free provider
profiles; blocked/sandbox/future/real providers cannot produce schema-valid evidence.
