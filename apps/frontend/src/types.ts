export type WorkflowState =
  | "REQUESTED"
  | "REGISTRY_FETCHED"
  | "VALIDATED"
  | "GT_SEARCHED"
  | "GT_SHELL_CREATED"
  | "GT_POLICY_CREATED"
  | "GT_ENRICHED"
  | "COMPLETED"
  | "REVIEW_REQUIRED"
  | "FAILED";

export interface MockScenario {
  uen: string;
  label: string;
  expected_outcome: string;
  description: string;
}

export interface SimulationProfile {
  is_simulated: true;
  registry_system: "ACRA";
  registry_environment: "MOCK" | "SANDBOX";
  target_system: "GOLDTIER";
  target_environment: "MOCK";
  idp_system: "IDP";
  idp_environment: "MOCK" | "LOCAL";
  idp_provider: "MOCK_IDP" | "LOCAL_PDF_TEXT";
  idp_review_confidence_threshold: number;
  ownership_system: "OWNERSHIP_PROVIDER";
  ownership_environment: "MOCK";
  ubo_ownership_threshold_percent: string;
}

export interface MockScenarioDiscovery {
  simulation: SimulationProfile;
  scenarios: MockScenario[];
}

export interface RegisteredAddress {
  address_line_1: string;
  address_line_2: string | null;
  postal_code: string;
  country_code: string;
}

export interface CanonicalEntity {
  registration_number: string;
  legal_name: string | null;
  country_of_incorporation: string | null;
  party_type: string | null;
  registration_date: string | null;
  entity_status: string | null;
  registered_address: RegisteredAddress | null;
  source: {
    source_system: "ACRA";
    environment: "MOCK" | "SANDBOX";
    retrieved_at: string;
  };
}

export type RegistryOperation =
  | "ENTITY_PROFILE"
  | "OFFICERS"
  | "OWNERSHIP_PARTIES"
  | "RELATIONSHIPS";

export interface RegistryEvidenceProvenance {
  provider: "ACRA";
  environment: "MOCK" | "SANDBOX";
  operation: RegistryOperation;
  retrieved_at: string;
  evidence_reference: string;
}

export interface RegistryAcquisition {
  requested_identifier: string;
  status: "COMPLETE" | "PARTIAL" | "FAILED";
  officers: Array<{
    officer_id: string;
    name: string;
    role: string;
    appointment_date: string | null;
    cessation_date: string | null;
    country: string | null;
    provenance: RegistryEvidenceProvenance;
  }>;
  ownership_parties: Array<{
    party_id: string;
    party_type: "NATURAL_PERSON" | "LEGAL_ENTITY";
    name: string;
    registration_identifier: string | null;
    country: string | null;
    ownership_percentage: string | null;
    provenance: RegistryEvidenceProvenance;
  }>;
  relationships: Array<{
    relationship_id: string;
    owned_entity_id: string;
    owner_party_id: string;
    relationship_type: "SHARE_OWNERSHIP";
    ownership_percentage: string;
    provenance: RegistryEvidenceProvenance;
  }>;
  operation_results: Array<{
    operation: RegistryOperation;
    status: "COMPLETE" | "EMPTY" | "FAILED" | "NOT_ATTEMPTED";
    record_count: number;
    provenance: RegistryEvidenceProvenance | null;
    error: { code: string; message: string } | null;
  }>;
  issues: Array<{ code: string; message: string }>;
  retrieved_at: string;
}

export interface WorkflowEvent {
  sequence: number;
  stage: WorkflowState;
  outcome: "SUCCEEDED" | "PARTIAL" | "REVIEW_REQUIRED" | "FAILED";
  timestamp: string;
  case_id: string;
  correlation_id: string;
  code: string | null;
  message: string;
}

export interface OnboardingCase {
  case_id: string;
  source_case_id: string;
  correlation_id: string;
  requested_uen: string;
  jurisdiction_resolution?: {
    status: "RESOLVED" | "UNRESOLVED" | "CONFLICT";
    resolved_jurisdiction: "SG" | "AU" | "MY" | "HK" | null;
    observations: Array<{
      jurisdiction: "SG" | "AU" | "MY" | "HK";
      source:
        | "USER_INPUT"
        | "IDENTIFIER_FORMAT"
        | "EXISTING_CASE"
        | "DOCUMENT_IDP"
        | "UPSTREAM_SYSTEM";
      observed_at: string;
      evidence_reference: string | null;
      confidence: number | null;
    }>;
    resolved_at: string;
  } | null;
  registry_route?: {
    status: "SELECTED" | "PROVIDER_NOT_IMPLEMENTED";
    jurisdiction: "SG" | "AU" | "MY" | "HK";
    provider: "ACRA" | null;
    decided_at: string;
  } | null;
  state: WorkflowState;
  entity: CanonicalEntity | null;
  registry_acquisition?: RegistryAcquisition | null;
  goldtier_result: {
    party_id: string;
    shell_status: string;
    policy_id: string | null;
    policy_status: string | null;
    amend_status: string | null;
  } | null;
  events: WorkflowEvent[];
  error: { code: string; message: string } | null;
  created_at: string;
  updated_at: string;
}

export type MockIdpScenario =
  | "ALL_FIELDS_MATCH"
  | "FIELD_MISMATCH"
  | "LOW_CONFIDENCE"
  | "MISSING_FIELD"
  | "PROCESSOR_FAILURE";

export type DocumentProcessingState =
  | "UPLOADED"
  | "PROCESSING"
  | "REVIEW_REQUIRED"
  | "REVIEWED"
  | "FAILED";

export type DocumentFieldKey =
  | "registration_number"
  | "legal_name"
  | "registered_address"
  | "country_of_incorporation";

export type ComparisonStatus =
  | "MATCH"
  | "MISMATCH"
  | "MISSING_FROM_DOCUMENT"
  | "MISSING_FROM_REGISTRY"
  | "NOT_COMPARABLE";

export type FieldReviewStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "CORRECTED";

export type ReviewDecision = "ACCEPTED" | "REJECTED" | "CORRECTED";

export interface DocumentProcessingRecord {
  case_id: string;
  document_id: string;
  correlation_id: string;
  display_name: string;
  media_type: "application/pdf";
  profile: "PROVISIONAL_CORPORATE";
  provider_environment: "MOCK" | "LOCAL" | "SANDBOX" | "LIVE" | null;
  state: DocumentProcessingState;
  fields: Array<{
    field_key: DocumentFieldKey;
    original_extracted_value: string | null;
    normalized_value: string | null;
    confidence: number;
    provenance: {
      provider: string;
      environment: "MOCK" | "LOCAL" | "SANDBOX" | "LIVE";
      page_number: number | null;
      source_reference: string;
    };
    canonical_value: string | null;
    comparison_status: ComparisonStatus;
    review_status: FieldReviewStatus;
    reviewed_value: string | null;
    reviewed_at: string | null;
    review_note: string | null;
  }>;
  events: Array<{
    sequence: number;
    event_type:
      | "DOCUMENT_UPLOADED"
      | "DOCUMENT_PROCESSING_STARTED"
      | "DOCUMENT_PROCESSED"
      | "DOCUMENT_REVIEW_REQUIRED"
      | "DOCUMENT_FIELD_ACCEPTED"
      | "DOCUMENT_FIELD_REJECTED"
      | "DOCUMENT_FIELD_CORRECTED"
      | "DOCUMENT_REVIEW_COMPLETED"
      | "DOCUMENT_AUTO_CONFIRMED"
      | "DOCUMENT_EXCEPTION_RESOLVED"
      | "DOCUMENT_SUPERSEDED"
      | "DOCUMENT_PROCESSING_FAILED";
    state: DocumentProcessingState;
    outcome: "SUCCEEDED" | "PARTIAL" | "REVIEW_REQUIRED" | "FAILED";
    timestamp: string;
    case_id: string;
    document_id: string;
    correlation_id: string;
    field_key: DocumentFieldKey | null;
    code: string | null;
    message: string;
  }>;
  error: { code: string; message: string } | null;
  created_at: string;
  processed_at: string | null;
  reviewed_at: string | null;
  supersedes_document_id?: string | null;
  superseded_by_document_id?: string | null;
  superseded_at?: string | null;
  updated_at: string;
}

export type MockOwnershipScenario =
  | "DIRECT_OWNER"
  | "INDIRECT_OWNER"
  | "MULTIPLE_PATHS"
  | "BELOW_THRESHOLD"
  | "INCOMPLETE_CHAIN"
  | "CYCLE"
  | "PROVIDER_FAILURE";

export type OwnershipAnalysisState =
  | "LOADING"
  | "LOADED"
  | "ANALYZING"
  | "REVIEW_REQUIRED"
  | "ANALYZED"
  | "FAILED";

export interface OwnershipParty {
  party_id: string;
  display_name: string;
  party_type: "LEGAL_ENTITY" | "NATURAL_PERSON";
  registration_number: string | null;
  country: string | null;
}

export interface OwnershipRelationship {
  relationship_id: string;
  parent_party_id: string;
  child_party_id: string;
  ownership_percent: string;
  relationship_type: "OWNERSHIP";
  basis: "SHARE_OWNERSHIP";
  provenance: {
    provider: string;
    environment: "MOCK" | "LOCAL" | "SANDBOX" | "LIVE";
    sourced_at: string;
  };
}

export interface OwnershipPath {
  path_id: string;
  edges: Array<{
    relationship_id: string;
    parent_party_id: string;
    parent_display_name: string;
    child_party_id: string;
    child_display_name: string;
    ownership_percent: string;
  }>;
  effective_ownership_percent: string;
  is_direct: boolean;
  calculation: string;
}

export interface OwnershipCandidate {
  party: OwnershipParty;
  direct_ownership_percent: string;
  indirect_ownership_percent: string;
  aggregated_ownership_percent: string;
  threshold_percent: string;
  threshold_comparator: "GREATER_THAN_OR_EQUAL_TO";
  threshold_result: "MET" | "NOT_MET" | "INDETERMINATE";
  classification:
    | "PROVISIONAL_UBO_CANDIDATE"
    | "BELOW_PROVISIONAL_THRESHOLD"
    | "REVIEW_REQUIRED"
    | "INDETERMINATE";
  paths: OwnershipPath[];
}

export interface OwnershipAnalysisRecord {
  case_id: string;
  analysis_id: string;
  correlation_id: string;
  root_party_id: string | null;
  provider_name: string | null;
  provider_environment: "MOCK" | "LOCAL" | "SANDBOX" | "LIVE" | null;
  state: OwnershipAnalysisState;
  parties: OwnershipParty[];
  relationships: OwnershipRelationship[];
  candidates: OwnershipCandidate[];
  issues: Array<{
    code:
      | "CYCLE_DETECTED"
      | "INCOMPLETE_LEGAL_ENTITY"
      | "MAXIMUM_DEPTH_EXCEEDED"
      | "PATH_LIMIT_EXCEEDED";
    message: string;
    affected_party_ids: string[];
  }>;
  threshold_percent: string;
  threshold_comparator: "GREATER_THAN_OR_EQUAL_TO";
  events: Array<{
    sequence: number;
    event_type:
      | "OWNERSHIP_LOAD_STARTED"
      | "OWNERSHIP_LOADED"
      | "OWNERSHIP_ANALYSIS_STARTED"
      | "OWNERSHIP_ANALYSIS_COMPLETED"
      | "OWNERSHIP_REVIEW_REQUIRED"
      | "OWNERSHIP_ANALYSIS_FAILED";
    state: OwnershipAnalysisState;
    outcome: "SUCCEEDED" | "PARTIAL" | "REVIEW_REQUIRED" | "FAILED";
    timestamp: string;
    case_id: string;
    analysis_id: string;
    correlation_id: string;
    code: string | null;
    message: string;
    party_count: number | null;
    relationship_count: number | null;
    candidate_count: number | null;
  }>;
  error: { code: string; message: string } | null;
  created_at: string;
  loaded_at: string | null;
  analyzed_at: string | null;
  updated_at: string;
}

export type ClmStatus =
  | "COLLECTING_EVIDENCE"
  | "REVIEW_REQUIRED"
  | "READY_FOR_MOCK_SUBMISSION"
  | "SUBMITTING"
  | "MOCK_GOLDTIER_SUBMITTED"
  | "FAILED";

export type ReadinessStageStatus =
  | "READY"
  | "MISSING"
  | "IN_PROGRESS"
  | "REVIEW_REQUIRED"
  | "FAILED"
  | "BLOCKED"
  | "NOT_SUBMITTED"
  | "SUBMITTED";

export interface ClmStageReadiness {
  status: ReadinessStageStatus;
  reference_id: string | null;
}

export interface GoldTierSubmissionPlan {
  environment: "MOCK";
  base_operations: string[];
  match_found_behavior: "REVIEW_REQUIRED_NO_WRITES";
  related_party_integration: "PENDING_SPONSOR_CONFIRMATION";
  real_ready_for_approval: "NOT_AVAILABLE";
}

export interface ClmCaseSummary {
  case: OnboardingCase;
  orchestration_id: string;
  correlation_id: string;
  version: number;
  status: ClmStatus;
  readiness: {
    policy_version: string;
    registry: ClmStageReadiness;
    document: ClmStageReadiness;
    ownership: ClmStageReadiness;
    goldtier: ClmStageReadiness;
    blockers: string[];
    warnings: string[];
    evaluated_at: string;
  };
  submission_plan: GoldTierSubmissionPlan;
  related_party_preparation: {
    provisional_candidate_count: number;
    internal_party_ids: string[];
    analysis_reference: string;
    mapping_status: "PENDING_SPONSOR_CONFIRMATION";
    write_status: "RELATED_PARTY_WRITE_NOT_EXECUTED";
  } | null;
  submission: {
    snapshot_id: string;
    submission_id: string;
    created_at: string;
    readiness_policy_version: string;
    document_reference_count: number;
    ownership_reference_id: string;
  } | null;
  goldtier_result: OnboardingCase["goldtier_result"];
  timeline: Array<{
    sequence: number;
    event_type:
      | "CLM_CASE_CREATED"
      | "REGISTRY_READY"
      | "CLM_REVIEW_REQUIRED"
      | "CLM_CASE_FAILED"
      | "READINESS_EVALUATED"
      | "MOCK_SUBMISSION_STARTED"
      | "MOCK_TARGET_EXECUTION_RECORDED"
      | "MOCK_SUBMISSION_COMPLETED"
      | "CLM_SUBMISSION_FAILED";
    status: ClmStatus;
    outcome: "SUCCEEDED" | "PARTIAL" | "REVIEW_REQUIRED" | "FAILED";
    timestamp: string;
    case_id: string;
    orchestration_id: string;
    correlation_id: string;
    code: string | null;
    message: string;
  }>;
  error: { code: string; message: string } | null;
  created_at: string;
  updated_at: string;
}

export type AutomationStatus =
  | "PENDING_INPUTS"
  | "RUNNING"
  | "WAITING_FOR_REVIEW"
  | "RESUMING"
  | "RECOVERY_PENDING"
  | "COMPLETED"
  | "TECHNICAL_FAILURE";

export type AutomationStage =
  | "REGISTRY"
  | "DOCUMENT"
  | "OWNERSHIP"
  | "READINESS"
  | "MOCK_GOLDTIER"
  | "COMPLETE";

export type ZeroTouchDemoScenario =
  | "STRAIGHT_THROUGH"
  | "DOCUMENT_DISCREPANCY"
  | "MULTIPLE_DOCUMENT_BLOCKERS"
  | "LOW_CONFIDENCE"
  | "LOW_CONFIDENCE_DOCUMENT"
  | "OWNERSHIP_CYCLE"
  | "OWNERSHIP_EXCEPTION"
  | "OWNERSHIP_INCOMPLETE"
  | "MULTIPLE_OWNERSHIP_PATHS"
  | "EXISTING_PARTY"
  | "TARGET_FAILURE"
  | "PARTIAL_AMEND"
  | "RECOVERY"
  | "TECHNICAL_FAILURE";

export type ExceptionResolutionAction =
  | "KEEP_REGISTRY_VALUE"
  | "REQUEST_ADDITIONAL_INFORMATION";

export interface ZeroTouchException {
  exception_id: string;
  case_id: string;
  exception_type: string;
  stage: AutomationStage;
  status: "OPEN" | "RESOLVED" | "CANCELLED";
  blocker_code: string;
  blocker_codes: string[];
  explanation: string;
  evidence_version: string;
  automation_version: number;
  evidence: Array<{
    reference_id: string | null;
    field_key: string | null;
    registry_value: string | null;
    document_value: string | null;
    confidence: number | null;
    comparison: string | null;
    source?: string | null;
    observed_value?: string | null;
    observed_at?: string | null;
    evidence_reference?: string | null;
  }>;
  available_actions: ExceptionResolutionAction[];
  created_at: string;
  resolved_at: string | null;
  resolution: ExceptionResolutionAction | null;
}

export interface ZeroTouchCaseSummary {
  case: OnboardingCase;
  clm: ClmCaseSummary;
  automation_id: string;
  version: number;
  status: AutomationStatus;
  current_stage: AutomationStage;
  completed_stages: AutomationStage[];
  active_exceptions: ZeroTouchException[];
  technical_failure: { code: string; message: string } | null;
  metrics: {
    automated_stages_completed: number;
    human_interventions: number;
    exceptions_raised: number;
    exceptions_resolved: number;
    final_outcome: string | null;
    total_duration_ms: number | null;
    stage_durations_ms: Partial<Record<AutomationStage, number>>;
  };
  target_operations: Array<{
    operation: "SEARCH" | "SHELL" | "POLICY" | "AMEND";
    status:
      | "NOT_ATTEMPTED"
      | "IN_PROGRESS"
      | "NO_MATCH"
      | "MATCH_FOUND"
      | "CREATED"
      | "SUCCESS"
      | "FAILED";
  }>;
  timeline: Array<{
    sequence: number;
    event_type: string;
    status: AutomationStatus;
    stage: AutomationStage;
    outcome: "SUCCEEDED" | "PARTIAL" | "REVIEW_REQUIRED" | "FAILED";
    timestamp: string;
    case_id: string;
    code: string | null;
    message: string;
  }>;
  created_at: string;
  updated_at: string;
}

export interface UatEvidenceExport {
  evidence_schema: "PHASE_07_UAT_EVIDENCE_V1";
  uat_case_id: string;
  scenario: ZeroTouchDemoScenario;
  case_id: string;
  synthetic_uen: string;
  final_state: AutomationStatus;
  current_stage: AutomationStage;
  completed_stages: AutomationStage[];
  active_blockers: string[];
  human_interventions: number;
  exceptions_raised: number;
  exceptions_resolved: number;
  stage_durations_ms: Partial<Record<AutomationStage, number>>;
  total_duration_ms: number | null;
  target_calls: string[];
  target_outcome: string | null;
  warnings: string[];
  environment: SimulationProfile;
  timeline: Array<{
    event_type: string;
    stage: AutomationStage;
    status: AutomationStatus;
    outcome: string;
    timestamp: string;
    code: string | null;
    message: string;
  }>;
  exported_at: string;
}
