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
