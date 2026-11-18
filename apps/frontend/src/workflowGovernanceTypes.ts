// Frozen workflow-governance API contract (C0, ADR-017 §6). Mirrors
// apps/backend/app/api_workflow_governance_models.py and app/domain/workflow_governance.py.
// Changing it needs a contract-change note (docs/contracts/WORKFLOW_GOVERNANCE_API.md).
// Authorization is backend-authoritative: the can_* flags only shape the UI.

import type { WorkflowField, WorkflowStage } from "./workflowApi";

export type ProposalState = "DRAFT" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "WITHDRAWN" | "STALE";
export type ProposalKind = "CHANGE" | "RESTORE_VERSION" | "RESET_TO_DEFAULT" | "DEACTIVATE" | "REACTIVATE";
export type ProposalOrigin = "GOVERNED" | "PRE_GOVERNANCE_DRAFT";
export type VersionOrigin = "GOVERNED_APPROVAL" | "PRE_GOVERNANCE_DIRECTOR_ACTIVATION" | "EMERGENCY_FALLBACK";
export type DecisionOutcome = "APPROVE" | "REJECT";
export type RatchetRule = "RR-1" | "RR-2" | "RR-3" | "RR-4" | "RR-5" | "RR-6" | "RR-7" | "RR-8" | "RR-9" | "RR-10";
/** CC-8 (ADR-018 §4.4): APPLICABILITY_BROADENED joined with its WorkflowCompare.tsx label (M3-E). */
export const APPLICABILITY_BROADENED = "APPLICABILITY_BROADENED";
export type PermanentObligationChange = "NEW_REQUIRED_STAGE" | "NEW_REQUIRED_FIELD" | "TIGHTENED" | typeof APPLICABILITY_BROADENED;
/** Kept as an alias for code written against the CC-8 export; identical to PermanentObligationChange. */
export type PermanentObligationChangeM3 = PermanentObligationChange;
export type DiffChange = "ADDED" | "REMOVED" | "CHANGED" | "UNCHANGED";

export const GOVERNANCE_ERROR_CODES = [
  "WORKFLOW_PROPOSAL_OPEN",
  "WORKFLOW_PROPOSAL_STALE",
  "WORKFLOW_PROPOSAL_NOT_FOUND",
  "WORKFLOW_PROPOSAL_STATE_INVALID",
  "WORKFLOW_PROPOSAL_CONTENT_CHANGED",
  "WORKFLOW_PROPOSAL_KIND_NOT_AVAILABLE",
  "WORKFLOW_PROPOSAL_INVALID",
  "WORKFLOW_PROPOSAL_EMPTY",
  "WORKFLOW_REQUIRED_OBLIGATION_REMOVED",
  "WORKFLOW_REQUIRED_OBLIGATION_WEAKENED",
  "WORKFLOW_PERMANENT_OBLIGATION_ACKNOWLEDGEMENT_REQUIRED",
  "WORKFLOW_SELF_DECISION_REFUSED",
  "WORKFLOW_PROPOSAL_TOO_LARGE",
  "WORKFLOW_HISTORY_UNAVAILABLE",
  "WORKFLOW_GOVERNANCE_NOT_MIGRATED",
  "WORKFLOW_DRAFT_NOT_RELEASABLE",
  "WORKFLOW_RUN_CONFIRMATION_IN_PROGRESS",
  "WORKFLOW_NOTICES_UNACKNOWLEDGED",
  "WORKFLOW_ROUTE_RETIRED",
] as const;
export type GovernanceErrorCode = (typeof GOVERNANCE_ERROR_CODES)[number];

export const PERMANENT_OBLIGATION_WARNING =
  "Once approved, this required step or field can never be removed or weakened in the product.";

export interface ObligationKey { stage_id: string; field_id: string | null }

export interface PermanentObligation {
  key: ObligationKey;
  change: PermanentObligationChange;
  stage_name: string;
  field_label: string | null;
  detail: string;
}

export interface VersionProvenance {
  version: number;
  origin: VersionOrigin;
  author_id: string | null;
  approved_by: string | null;
  proposal_id: string | null;
  activated_by: string | null;
  published_at: string;
  note: string | null;
}

export type GovernanceEventKind =
  | "MIGRATED" | "WORKFLOW_CREATED" | "PROPOSAL_CREATED" | "PROPOSAL_EDITED" | "PROPOSAL_SUBMITTED"
  | "PROPOSAL_WITHDRAWN" | "PROPOSAL_APPROVED" | "PROPOSAL_REJECTED" | "PROPOSAL_STALE"
  | "VERSION_PUBLISHED" | "DRAFT_RELEASED" | "DRAFT_COPIED" | "EMERGENCY_FALLBACK" | "NOTICE_RAISED"
  | "NOTICE_ACKNOWLEDGED" | "DEACTIVATED" | "REACTIVATED";

export interface GovernanceEvent {
  sequence: number;
  occurred_at: string;
  actor_id: string | null;
  kind: GovernanceEventKind;
  proposal_id: string | null;
  version: number | null;
  summary: string;
  archived: boolean;
}

export interface GovernanceNotice {
  notice_id: string;
  kind: GovernanceEventKind;
  raised_at: string;
  raised_by: string;
  version: number;
  reason: string;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
}

export interface ProposalResponse {
  proposal_id: string;
  workflow_id: string;
  kind: ProposalKind;
  state: ProposalState;
  origin: ProposalOrigin;
  revision: number;
  base_version: number;
  stages: WorkflowStage[];
  note: string | null;
  author_id: string | null;
  legacy_editor: string | null;
  created_at: string;
  updated_at: string;
  last_activity_at: string;
  submitted_at: string | null;
  content_hash: string | null;
  decided_at: string | null;
  decided_by: string | null;
  decision_reason: string | null;
  published_version: number | null;
  stale_by_version: number | null;
  restore_target_version?: number | null; // CC-6 (additive, optional)
  copied_from?: string | null;
  released_by?: string | null;
  release_reason?: string | null;
  can_edit: boolean;
  can_submit: boolean;
  can_withdraw: boolean;
  can_decide: boolean;
}

export interface DecidedProposalSummary {
  proposal_id: string;
  kind: ProposalKind;
  state: ProposalState;
  origin: ProposalOrigin;
  author_id: string | null;
  decided_by: string | null;
  decided_at: string | null;
  ended_at: string;
  published_version: number | null;
}

export interface BaselineSummary {
  seeded_from_version: number | null;
  updated_at_version: number | null;
  required_stages: number;
  required_fields: number;
}

export interface WorkflowGovernanceView {
  migrated: boolean;
  latest_version: number;
  open_proposal: ProposalResponse | null;
  decided_proposals: DecidedProposalSummary[];
  version_provenance: VersionProvenance[];
  baseline: BaselineSummary;
  recent_events: GovernanceEvent[];
  unacknowledged_notices: GovernanceNotice[];
  can_create_proposal: boolean;
}

// --- Requests ---

export interface CreateProposalRequest {
  kind?: ProposalKind;
  expected_workflow_revision: number;
  stages?: WorkflowStage[] | null;
  restore_target_version?: number | null;
  note?: string | null;
}

export interface UpdateProposalRequest {
  expected_workflow_revision: number;
  expected_proposal_revision: number;
  stages: WorkflowStage[];
  note?: string | null;
}

export interface ValidateProposalRequest { stages?: WorkflowStage[] | null }

export interface SimulateProposalRequest { stages?: WorkflowStage[] | null; scenario_ids?: string[] }

export interface SubmitProposalRequest {
  expected_workflow_revision: number;
  expected_proposal_revision: number;
  content_hash: string;
}

export interface WithdrawProposalRequest {
  expected_workflow_revision: number;
  expected_proposal_revision: number;
}

export interface DecisionRequest {
  outcome: DecisionOutcome;
  reason: string; // 10-240 characters after trimming
  expected_workflow_revision: number;
  expected_proposal_revision: number;
  content_hash: string;
  acknowledged_permanent_obligations: ObligationKey[]; // APPROVE: exactly the set; REJECT: []
}

// --- Validation and simulation ---

export interface ValidationIssue {
  code: string;
  rule: RatchetRule | null;
  stage_id: string | null;
  field_id: string | null;
  message: string;
}

export interface ValidationReport {
  valid: boolean;
  content_hash: string;
  encoded_bytes: number;
  max_encoded_bytes: number;
  base_version: number;
  active_version: number;
  issues: ValidationIssue[];
  permanent_obligations: PermanentObligation[];
}

export interface SimulationScenario {
  scenario_id: string;
  label: string;
  description: string;
  legal_form: SimulationLegalForm;
  synthetic: true;
}

export interface SimulatedStep {
  node_id: string;
  name: string;
  added: boolean;
  blocks_send: boolean;
  required_field_labels: string[];
}

export interface SimulationOutcome {
  scenario: SimulationScenario;
  steps: SimulatedStep[];
  held_before_send: boolean;
  summary: string;
}

export interface SimulationResult { synthetic: true; content_hash: string; outcomes: SimulationOutcome[] }

// --- Director views ---

export interface ChangeCounts {
  stages_added: number;
  stages_removed: number;
  stages_changed: number;
  fields_added: number;
  fields_removed: number;
  fields_changed: number;
}

export interface ApprovalInboxItem {
  workflow_id: string;
  workflow_name: string;
  use_case: string;
  is_onboarding: boolean;
  workflow_revision: number;
  proposal: ProposalResponse;
  active_version: number;
  changes: ChangeCounts;
  permanent_obligation_count: number;
}

export interface ApprovalInboxResponse { items: ApprovalInboxItem[] }

export interface FieldDiff {
  field_id: string;
  change: DiffChange;
  before: WorkflowField | null;
  after: WorkflowField | null;
}

export interface StageDiff {
  stage_id: string;
  change: DiffChange;
  name_before: string | null;
  name_after: string | null;
  after_node_id_before: string | null;
  after_node_id_after: string | null;
  blocks_send_before: boolean;
  blocks_send_after: boolean;
  fields: FieldDiff[];
}

export interface WorkflowVersionDetail {
  version: number;
  stages: WorkflowStage[];
  activated_at: string;
  activated_by: string;
}

export interface AffectedCases { open_runs_on_active_version: number; counted_at: string }

export interface ComparisonResponse {
  workflow_id: string;
  workflow_name: string;
  is_onboarding: boolean;
  workflow_revision: number;
  proposal: ProposalResponse;
  active_version: WorkflowVersionDetail | null;
  active_provenance: VersionProvenance | null;
  stages: StageDiff[];
  locked_stages: [string, string][];
  validation: ValidationReport;
  permanent_obligations: PermanentObligation[];
  permanent_obligation_warning: string;
  affected_cases: AffectedCases;
}

export interface PublicationReport {
  published_version: number;
  cases_past_first_write_under_earlier_version: number;
  cases_authorised_under_earlier_version: number;
  cases_possibly_authorised: number;
  counted_at: string;
}

export interface DecisionResponse {
  proposal: ProposalResponse;
  workflow_revision: number;
  active_version: number;
  published_version: number | null;
  provenance: VersionProvenance | null;
  publication_report: PublicationReport | null;
}

export interface GovernanceErrorBody {
  code: string;
  message: string;
  rule: RatchetRule | null;
  issues: ValidationIssue[];
}

// Key lists checked against the shared fixtures (workflowGovernanceContract.test.ts).
export const PROPOSAL_RESPONSE_KEYS = [
  "proposal_id", "workflow_id", "kind", "state", "origin", "revision", "base_version", "stages", "note",
  "author_id", "legacy_editor", "created_at", "updated_at", "last_activity_at", "submitted_at",
  "content_hash", "decided_at", "decided_by", "decision_reason", "published_version", "stale_by_version",
  "restore_target_version", "copied_from", "released_by", "release_reason",
  "can_edit", "can_submit", "can_withdraw", "can_decide",
] as const satisfies readonly (keyof ProposalResponse)[];
export const COMPARISON_RESPONSE_KEYS = [
  "workflow_id", "workflow_name", "is_onboarding", "workflow_revision", "proposal", "active_version",
  "active_provenance", "stages", "locked_stages", "validation", "permanent_obligations",
  "permanent_obligation_warning", "affected_cases",
] as const satisfies readonly (keyof ComparisonResponse)[];
export const VALIDATION_REPORT_KEYS = [
  "valid", "content_hash", "encoded_bytes", "max_encoded_bytes", "base_version", "active_version", "issues",
  "permanent_obligations",
] as const satisfies readonly (keyof ValidationReport)[];
export const DECISION_RESPONSE_KEYS = [
  "proposal", "workflow_revision", "active_version", "published_version", "provenance", "publication_report",
] as const satisfies readonly (keyof DecisionResponse)[];
export const GOVERNANCE_VIEW_KEYS = [
  "migrated", "latest_version", "open_proposal", "decided_proposals", "version_provenance", "baseline",
  "recent_events", "unacknowledged_notices", "can_create_proposal",
] as const satisfies readonly (keyof WorkflowGovernanceView)[];

// --- M2 contract addendum (CC-4): recovery and administration ---

export interface EmergencyFallbackRequest {
  reason: string; // 10-240 characters after trimming
  expected_workflow_revision: number;
  target: "VERSION" | "DEFAULT";
  target_version?: number | null; // required when target === "VERSION"
}

export interface EmergencyFallbackResponse {
  workflow_revision: number;
  active_version: number;
  published_version: number;
  provenance: VersionProvenance;
  notice: GovernanceNotice;
  staled_proposal_ids: string[];
  publication_report: PublicationReport | null;
}

export interface ReleaseDraftRequest { reason: string; expected_workflow_revision: number; expected_proposal_revision: number }

export interface CopyProposalRequest { expected_workflow_revision: number; note?: string | null }

export interface WorkflowVersionResponse {
  workflow_id: string;
  version: WorkflowVersionDetail;
  provenance: VersionProvenance | null;
  is_active: boolean;
}

export interface NoticeItem { workflow_id: string; workflow_name: string; workflow_revision: number; notice: GovernanceNotice }

export interface NoticeListResponse { items: NoticeItem[] }

export interface AcknowledgeNoticeRequest { workflow_id: string; expected_workflow_revision: number }

export const DRAFT_RELEASE_AFTER_DAYS = 14;

// --- M3 (ADR-018, contract CC-8): conditional, add-only applicability ---

/** The selectable legal forms: the backend RegistryLegalForm without OTHER (B5). */
export const CONDITIONAL_LEGAL_FORMS = ["BUSINESS_PARTNERSHIP", "COMPANY", "GOVERNMENT", "LLP", "LP"] as const;
export type ConditionalLegalForm = (typeof CONDITIONAL_LEGAL_FORMS)[number];
export type SimulationLegalForm = ConditionalLegalForm | "UNVERIFIED" | "OTHER";

/** Onboarding anchors at which conditional content is allowed (B2). */
export const CONDITIONAL_ONBOARDING_ANCHORS = [
  "ACRA_REGISTRY",
  "DOCUMENT_IDP",
  "RECONCILIATION",
  "OWNERSHIP_UBO",
  "ADVISORY",
  "GOLDTIER_DETAILS",
] as const;

/** A send hold, not a governance error code (ADR-018 §6). */
export const HOLD_APPLICABILITY_BASIS_CONFLICT = "WORKFLOW_APPLICABILITY_BASIS_CONFLICT";

export type ApplicabilityBasisStatus = "REGISTRY_BOUND" | "UNVERIFIED";
export type ApplicabilityBasisReason =
  | "REGISTRY_BINDING" | "NO_ENTITY" | "NO_BINDING" | "OTHER_FORM" | "CONFLICTING_CLASSIFICATION"
  | "AMBIGUOUS_BINDING" | "TOO_LATE_TO_NARROW" | "NO_CASE_RECORD" | "READ_FAILED";
export type SourceEnvironment = "MOCK" | "SANDBOX";

export interface RunBasisConflictView {
  detected_at: string;
  observed_status: ApplicabilityBasisStatus;
  observed_legal_form: ConditionalLegalForm | null;
  escalated: boolean;
  escalated_by: string | null;
  escalated_at: string | null;
}

export interface RunApplicabilityView {
  status: ApplicabilityBasisStatus;
  legal_form: ConditionalLegalForm | null;
  reason: ApplicabilityBasisReason;
  source_environment: SourceEnvironment | null;
  frozen: boolean;
  /** The effective basis: null means every conditional step applies. */
  effective_legal_form: ConditionalLegalForm | null;
  conflict: RunBasisConflictView | null;
}

export const RUN_APPLICABILITY_VIEW_KEYS = [
  "status", "legal_form", "reason", "source_environment", "frozen", "effective_legal_form", "conflict",
] as const;

export interface ApplicabilityEscalationRequest { run_id: string; expected_revision: number; reason: string }
