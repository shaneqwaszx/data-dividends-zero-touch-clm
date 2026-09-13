# Architecture Workspace

The Phase 00 architecture baseline is documented in [ARCHITECTURE.md](ARCHITECTURE.md).
Implemented phase boundaries are documented in
[PHASE_01_VERTICAL_SLICE.md](PHASE_01_VERTICAL_SLICE.md) and
[PHASE_02_ACRA_INGESTION.md](PHASE_02_ACRA_INGESTION.md), followed by the supplementary
document boundary in [PHASE_03_IDP_REVIEW.md](PHASE_03_IDP_REVIEW.md).
Phase 04's ownership-only deterministic calculation boundary is documented in
[PHASE_04_RELATED_PARTIES_UBO.md](PHASE_04_RELATED_PARTIES_UBO.md). The staged Phase 05
composition is documented in [PHASE_05_CLM_ORCHESTRATION.md](PHASE_05_CLM_ORCHESTRATION.md),
and the server-driven Phase 06 path in
[PHASE_06_ZERO_TOUCH_ORCHESTRATION.md](PHASE_06_ZERO_TOUCH_ORCHESTRATION.md). Phase 09's
source-aware country decision and Singapore-only provider routing boundary is in
[PHASE_09_JURISDICTION_GATEWAY.md](PHASE_09_JURISDICTION_GATEWAY.md). Phase 10's
project-owned multi-step Mock ACRA acquisition and registry-to-existing-ownership seam
is in [PHASE_10_EXPANDED_REGISTRY_ACQUISITION.md](PHASE_10_EXPANDED_REGISTRY_ACQUISITION.md).
Phase 11's source-neutral field reconciliation, explicit decision, canonical update,
and resume boundary is in
[PHASE_11_RECONCILIATION_REVIEW_RESUME.md](PHASE_11_RECONCILIATION_REVIEW_RESUME.md).
The bounded refinement before Phase 12 adds a process-local case index/review queue and
explicit multi-document intake boundary in
[PRE_PHASE_12_CLM_WORKSPACE_MULTIDOC.md](PRE_PHASE_12_CLM_WORKSPACE_MULTIDOC.md).
Phase 12's explicit memory/Mongo repository composition, single-envelope CAS boundary,
and conservative restart recovery are documented in
[PHASE_12_DURABLE_PERSISTENCE_RESTART_RECOVERY.md](PHASE_12_DURABLE_PERSISTENCE_RESTART_RECOVERY.md).
Phase 13's local authentication, centralized case authorization, immutable team scope,
priority ordering, and schema-v2 compatibility boundary are documented in
[PHASE_13_CASE_PRIORITY_AUTH_RBAC.md](PHASE_13_CASE_PRIORITY_AUTH_RBAC.md).
Phase 14.5's persistent identity/team administration, typed policy catalogue, dynamic
Director filter, and immutable schema-v3 case policy binding are documented in
[PHASE_14_5_POLICY_TEAM_IDENTITY_ADMIN.md](PHASE_14_5_POLICY_TEAM_IDENTITY_ADMIN.md).
Phase 14's projected portfolio read model, session-memory query cache, explicit
create/update lifecycle, and authorized hard-delete boundary are documented in
[PHASE_14_CASE_MANAGEMENT_PERFORMANCE.md](PHASE_14_CASE_MANAGEMENT_PERFORMANCE.md).

Later phases should update that baseline only when an approved planner handoff introduces a new boundary or decision.
