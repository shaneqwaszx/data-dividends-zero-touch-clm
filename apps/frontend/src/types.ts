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
  idp_environment: "MOCK";
  idp_review_confidence_threshold: number;
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
  state: WorkflowState;
  entity: CanonicalEntity | null;
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
  updated_at: string;
}
