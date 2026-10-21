# Documentation Index

A map of `docs/`. Documents are grouped by purpose. Each folder separates **current**
material (describes the system as it is now) from **point-in-time records** (gates,
remediation notes and phase snapshots that were accurate on their date).

When documents disagree, follow the precedence order in [`AGENTS.md`](../AGENTS.md):
current source and tests win over any document, and historical records never override
current ones.

## Start here

| Document | Purpose |
|---|---|
| [`PROJECT_STATE.md`](PROJECT_STATE.md) | Current capabilities, provider modes, open blockers |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Canonical owners, dependencies and invariants |
| [`DEVELOPMENT_WORKFLOW.md`](DEVELOPMENT_WORKFLOW.md) | Change classes, required checks, task lifecycle |
| [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) | Background on the sponsor problem and project phases |
| [`FINAL_DELIVERABLE_INDEX.md`](FINAL_DELIVERABLE_INDEX.md) | Curated list of handoff deliverables |

Also at this level:

- [`CODEX_WORKFLOW.md`](CODEX_WORKFLOW.md) adapts the development workflow for
  coordinating coding agents.
- [`FINAL_PROJECT_CLOSEOUT.md`](FINAL_PROJECT_CLOSEOUT.md) and
  [`PHASE_27_HANDOFF.md`](PHASE_27_HANDOFF.md) are the Phase 27 closeout records
  (2026-10-05).

## Folders

### `architecture/` — design by phase

- **Current:** [`FINAL_POC_ARCHITECTURE.md`](architecture/FINAL_POC_ARCHITECTURE.md). The
  living architecture is [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).
- **Point-in-time:** `PHASE_01_*` … `PHASE_14_5_*` and `PRE_PHASE_12_*`, one design
  record per phase.
- `architecture/ARCHITECTURE.md` is the original **Phase 00** design. It is not the
  same file as `docs/ARCHITECTURE.md`.

### `contracts/` — data, API and policy contracts

- Provider and data profiles: `ACRA_*`, `GOLDTIER_*`, `IDP_*`, `OWNERSHIP_UBO_PROFILE`,
  `RECONCILIATION_PROFILE`, `MULTI_DOCUMENT_INTAKE_PROFILE`,
  `REGISTRY_CACHE_FRESHNESS_PROFILE`.
- Case behavior: `CASE_*`, `CLM_READINESS_POLICY`, `PERSISTENCE_RECOVERY_PROFILE`,
  `ZERO_TOUCH_AUTOMATION_POLICY`, `INTEGRATION_ADAPTER_CONTRACTS`.
- Policy: `POLICY_*` and `EXTERNAL_PROVIDER_ACTIVATION_CONTRACT`.
- The `*.json` files are machine-read registries and schemas used by the `check_*` and
  `validate_*` scripts.

### `decisions/` — architecture decision records

- `ADR-001` … `ADR-011`, one per decision.
- [`DECISION_LOG.md`](decisions/DECISION_LOG.md) is a running log.
- `ADR_TEMPLATE.md` is the template for new ADRs.

### `sponsor-questions/` — what the sponsor still has to confirm

- [`OPEN_QUESTIONS.md`](sponsor-questions/OPEN_QUESTIONS.md) — open sponsor questions
- `PHASE_07_SPONSOR_DEPENDENCY_MATRIX.md`
- `PHASE_20_POLICY_DECISION_PACKET.md`

### `integration/` — replacing mocks with real providers

- **Handoff set:** `INTEGRATION_HANDOFF`, `PROVIDER_REPLACEMENT_GUIDE`,
  `ADAPTER_CONFORMANCE_CHECKLIST`, `API_HANDOFF`, `CONFIGURATION_REFERENCE`,
  `FAILURE_RECOVERY_GUIDE`.
- **Provider notes:**
  - ACRA: `ACRA_*`
  - GoldTier: `GOLDTIER_*`
  - Other: `EXTERNAL_PROVIDER_SECRET_SECURITY_RUNBOOK`,
    `PHASE_21_PROVIDER_ACTIVATION_PACKET`, `ONBOARDING_INTELLIGENCE_S3_FIELD_MATRIX`,
    `CAMUNDA_OBSERVER_OFFLINE_SPIKE`.
- **Frontend feature notes:** `AM_*`, `AM03_*`, `PROGRESSIVE_DISCLOSURE_FOUNDATION`,
  `FRONTEND_UX_REFINEMENT`, `GARDEN_UEN_PARTIAL_RESUME`, `PR84_REVIEW_REMEDIATION`.
  These describe recent UI behavior; `PROJECT_STATE.md` does not link them yet.

### `demo/` — running and presenting the demo

- **Current:**
  - [`DEMO_RUNBOOK.md`](demo/DEMO_RUNBOOK.md)
  - [`SPONSOR_DEMO_SCRIPT.md`](demo/SPONSOR_DEMO_SCRIPT.md)
  - `FINAL_SPONSOR_DEMO_RUNBOOK`, `FINAL_UAT_ACCEPTANCE_MATRIX`,
    `FINAL_POC_LIMITATIONS_AND_NEXT_STEPS`
  - `SYNTHETIC_COMPANY_PACK`, `ZERO_TOUCH_DATABASE_HAPPY_PATH_UAT`
  - `PHASE_27_*`
- **Generated:** `BLOCKER_RECTIFICATION_GUIDE.md` is built by
  `scripts/generate_blocker_rectification_guide.py`, and a backend test fails if the two
  differ. Edit the generator, not the guide.
- **Point-in-time:**
  - Phase demos: `ATTENTION_QUEUE_DEMO`, `EVIDENCE_WORKBENCH_DEMO`,
    `PHASE_17_ACTIVITY_DEMO`, `PHASE_18_CASE_PORTFOLIO_DEMO`,
    `PRE_PHASE22_INTELLIGENCE_DEMO`.
  - Snapshots: `PRE_PHASE22_CAPABILITY_STATUS_MATRIX`, `POST_PHASE24_DEMO_MATRIX`,
    `FINAL_POST_PHASE24_RELEASE_SUMMARY`.

### `uat/` — user-acceptance catalogues

- `PHASE_07_UAT_CATALOGUE.md` is the catalogue the delivery tests check for.
- `PHASE_08_UAT_CATALOGUE.md` is a point-in-time catalogue; the current matrix is
  `demo/FINAL_UAT_ACCEPTANCE_MATRIX.md`.

### `development/` — tooling, process and quality records

- **How-to and policy:**
  - [`DEVELOPMENT_TOOLING_RUNBOOK.md`](development/DEVELOPMENT_TOOLING_RUNBOOK.md)
  - `BRANCH_MERGE_PROTOCOL`, `TOOLING_AND_MCP`, `IMMUTABLE_ARCHIVE_WHITESPACE_POLICY`
  - `LOCAL_OCR_SETUP`, `GARDEN_DEMO_GUIDE`, `GOLDTIER_SANDBOX_ACCEPTANCE_RUNBOOK`
- **Point-in-time records:** quality gates, remediation rounds and acceptance reports.
  - `*_QUALITY_GATE*` and `*_GATE`
  - `ACCEPTED_CANDIDATE_*`, `CI_PUBLICATION_REMEDIATION_*`, `E2E_DEADLINE_RELIABILITY*`
  - `FINAL_PROVIDER_*`, `GARDEN_*` reports
  - `GOLDTIER_CONTRACT_CLOSURE_*`, `GOLDTIER_UNCERTAIN_SHELL_*`
  - `OFFICIAL_*`, `OVERNIGHT_*`, `PHASE_24_ACRA_DISCOVERY`,
    `POST_PHASE24_GOLDTIER_SANDBOX_OBSERVATION`, `ZERO_TOUCH_EXCEPTION_*`

### Smaller folders

| Folder | Contents |
|---|---|
| `security/` | [`POC_SECURITY_BOUNDARIES.md`](security/POC_SECURITY_BOUNDARIES.md) |
| `models/` | Model cards for the advisory intelligence in `apps/backend/app/domain/onboarding_intelligence.py`: [entity resolution](models/ENTITY_RESOLUTION_MODEL_CARD.md), [mock advisory risk](models/MOCK_ADVISORY_RISK_MODEL_CARD.md), [UBO advisory](models/UBO_ADVISORY_MODEL_CARD.md) |
| `research/` | [`INDUSTRY_STANDARD_USAGE.md`](research/INDUSTRY_STANDARD_USAGE.md): which external standards the POC uses, and how far |
| `evidence/` | Sanitized ACRA Marketplace Mock receipt, checked by `scripts/validate_acra_marketplace_mock_evidence.py` |
| `test-plan/` | Test strategy notes by phase |
| `aegis/` | Planning and work-log records written with the Aegis method pack. Advisory only; not authority |
| `archive/` | Superseded documents; see [`archive/README.md`](archive/README.md) |

## Files that code reads

Scripts and tests open these paths directly, so rename or delete them only together with
the code that reads them:

- `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DEVELOPMENT_WORKFLOW.md`, `CODEX_WORKFLOW.md`
  (`scripts/dev_context.py`, `scripts/check_project_state.py`, `tests/test_dev_context.py`).
- `contracts/*.json`, `evidence/*.json`, `sponsor-questions/*`, and the contracts
  `POLICY_AUTHORITY_MATRIX`, `POLICY_ACTIVATION_CONTRACT`,
  `POLICY_TEAM_IDENTITY_ADMIN_PROFILE` and `CASE_ACTIVITY_QUERY_PROFILE`
  (`check_policy_authority.py`, `check_external_provider_readiness.py` and the
  `validate_*` scripts).
- The Phase 07 handoff set in `integration/`, `demo/`, `uat/`, `security/` and
  `architecture/FINAL_POC_ARCHITECTURE.md`, plus `FINAL_DELIVERABLE_INDEX.md`
  (`tests/test_phase_07_delivery_assets.py`).
- Phase 03/04/06 architecture and contract documents (`tests/contract/`).
- `demo/BLOCKER_RECTIFICATION_GUIDE.md` (backend blocker-catalogue test).
- `development/BRANCH_MERGE_PROTOCOL.md` (`scripts/dev_context.py --full`).
