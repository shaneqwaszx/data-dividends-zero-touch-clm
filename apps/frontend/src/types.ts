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

export type TeamId = string;
export type Role = "CLIENT_ONBOARDER" | "RELATIONSHIP_MANAGER" | "DIRECTOR" | "HR" | "SUPPORT";
export type Capability =
  | "POLICY_VIEW"
  | "POLICY_MUTATE"
  | "POLICY_APPROVE"
  | "CASE_ACCESS"
  | "CASE_GLOBAL"
  | "TARGET_RECOVERY"
  | "IDENTITY_ADMIN"
  | "TEAM_ADMIN"
  | "PROVIDER_SANDBOX_TEST"
  | "MODEL_CONFIG_MANAGE"
  | "KNOWLEDGE_REVIEW"
  | "KNOWLEDGE_CASE_READ";

export interface AuthenticatedTeam {
  team_id: TeamId;
  display_name: string;
  team_type: string;
  client_scope_label: string;
  description: string;
}

export interface AuthenticatedProfile {
  user_id: string;
  display_name: string;
  role: Role;
  team_id: TeamId | null;
  team_display_name: string | null;
  team_type: string | null;
  team_description: string;
  client_scope_label: string;
  capabilities: Capability[];
}

export interface AdminTeam extends AuthenticatedTeam {
  active: true;
  version: number;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
}

export interface AdminProfile {
  user_id: string;
  display_name: string;
  role: Role;
  team_id: TeamId | null;
  team_display_name: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
}

export type PolicyValue =
  | { type: "BOOLEAN"; value: boolean }
  | { type: "INTEGER"; value: number }
  | { type: "DECIMAL"; value: string }
  | { type: "STRING"; value: string }
  | { type: "STRING_LIST"; value: string[] };

export type PolicyAuthority =
  | "SPONSOR_DOCUMENTED"
  | "SPONSOR_SUPPLIED"
  | "SPONSOR_EXAMPLE"
  | "SANDBOX_OBSERVED"
  | "USER_AUTHORIZED_POC"
  | "PROJECT_DEFINED_PROVISIONAL"
  | "INDUSTRY_PRACTICE"
  | "TBD_SPONSOR";

export interface PolicyRule {
  policy_id: string;
  category: string;
  name: string;
  description: string;
  value: PolicyValue;
  value_type: PolicyValue["type"];
  default_value: PolicyValue;
  minimum: string | number | null;
  maximum: string | number | null;
  allowed_values: string[];
  classifications: Array<
    | "PROJECT_DEFAULT"
    | "PENDING_SPONSOR_CONFIRMATION"
    | "SYSTEM_DERIVED"
    | "DISPLAY_ONLY_NOT_RUNTIME_ENFORCED"
  >;
  authority: PolicyAuthority | null;
  default_authority: PolicyAuthority | null;
  enforcement: "RUNTIME_ENFORCED" | "DISPLAY_SHOWCASE_ONLY" | "NOT_EDITABLE";
  version: number;
  created_at: string;
  updated_at: string;
  updated_by: string;
}

export interface PolicyCatalogue {
  catalogue_id: string;
  version: number;
  active_version?: number;
  active_identity?: string;
  active_origin?: "DEFAULT" | "APPROVED" | "MIGRATED";
  active_effective_at?: string | null;
  proposals?: PolicyProposal[];
  superseded_versions?: Array<{ version: number; status: "SUPERSEDED"; rules: PolicyRule[]; superseded_at: string }>;
  rules: PolicyRule[];
  created_at: string;
  updated_at: string;
  updated_by: string;
}

export interface AuthSession {
  profile: AuthenticatedProfile;
  csrf_token: string;
}

export interface CasePriorityResult {
  case_id: string;
  team_id: TeamId | null;
  priority: number | null;
  updated_at: string;
}

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
  registry_provider_mode?: "LOCAL_MOCK" | "API_MARKETPLACE_MOCK" | "API_MARKETPLACE_PROTOCOL_TEST" | "GENERIC_SANDBOX";
  target_system: "GOLDTIER";
  target_environment: "MOCK" | "SANDBOX";
  target_provider_classification: "MOCK" | "SANDBOX_PARTIAL";
  idp_system: "IDP";
  idp_environment: "MOCK" | "LOCAL";
  idp_provider: "MOCK_IDP" | "LOCAL_PDF_TEXT";
  idp_review_confidence_threshold: number;
  ownership_system: "OWNERSHIP_PROVIDER";
  ownership_environment: "MOCK";
  ubo_ownership_threshold_percent: string;
  persistence: "Process-local" | "Mongo-backed durable POC";
}

export interface GoldTierSandboxStatus {
  configured: boolean;
  mode: "MOCK" | "SANDBOX";
  classification: "MOCK" | "SANDBOX_PARTIAL";
  safe_host: string | null;
  writes_enabled: boolean;
  timeout_seconds: number;
  max_response_bytes: number;
  last_diagnostic_at: string | null;
  blocker: string | null;
  customer_operations: "AVAILABLE" | "PARTIAL";
  related_party_operations: "BLOCKED_CONTRACT";
  blocker_code: "BLOCKED_CHILD_ID_LIFECYCLE";
  required_authority: "SPONSOR_CONFIRMATION";
  related_party_blocker: "BLOCKED_CHILD_ID_LIFECYCLE";
  vocabulary_version: string;
  kyc_customer_types: string[];
  client_segments: string[];
  timeline: GoldTierSandboxDiagnosticEvent[];
}

export interface GoldTierSandboxDiagnosticEvent {
  event_id: string;
  action: "STATUS" | "SEARCH" | "DRY_RUN" | "WRITE_BLOCKED";
  outcome: "SUCCEEDED" | "FAILED" | "BLOCKED";
  code: string;
  occurred_at: string;
}

export interface GoldTierSandboxSearchInput {
  goldtier_id?: string;
  legal_name?: string;
  country_of_incorporation?: string;
  group_company_name?: string;
}

export interface GoldTierSandboxSearchCandidate {
  party_id: string;
  registration_number: string | null;
  country: string | null;
  legal_name: string | null;
  legal_form: string | null;
  registered_address: string | null;
}

export interface GoldTierSandboxSearchResult {
  status: string;
  count: number;
  candidates: GoldTierSandboxSearchCandidate[];
  elapsed_ms: number;
  entity_resolution: string;
}

export interface GoldTierSandboxTestValues {
  kyc_customer_type: string;
  client_segment: string;
  customer_external_system: string;
  registration_type: string;
  policy: string;
  booking_entity: string;
  account_entity_type?: string;
  product_type?: string;
}

export interface GoldTierSandboxDryRunInput {
  search: GoldTierSandboxSearchInput;
  test_values: GoldTierSandboxTestValues;
}

export interface GoldTierSandboxPreviewField {
  target_field: string;
  value: string | null;
  provenance: string;
  authority: string;
  required: boolean;
  missing: boolean;
  validation: "VALID" | "MISSING" | "INVALID";
}

export interface GoldTierSandboxDryRunOperation {
  operation: string;
  fields: GoldTierSandboxPreviewField[];
  missing_fields: string[];
  validation: "VALID" | "MISSING" | "INVALID";
}

export interface GoldTierSandboxDryRunResult {
  operations: GoldTierSandboxDryRunOperation[];
  dispatch_ready: boolean;
  blocker: string | null;
}

export type AcraDiagnosticOperation =
  | "ENTITY_PROFILE"
  | "OFFICERS"
  | "SHAREHOLDERS"
  | "LLP_HIGHLIGHTS"
  | "CAPITAL_DETAILS"
  | "RELATIONSHIPS";

export type AcraDiagnosticOutcome =
  | "COMPLETE"
  | "EMPTY"
  | "PARTIAL"
  | "NOT_FOUND"
  | "FAILED"
  | "UNSUPPORTED"
  | "INVALID_REQUEST"
  | "CANCELLED"
  | "RATE_LIMITED";

export interface AcraDiagnosticReceipt {
  diagnostic_id: string;
  provider: "ACRA_MOCK" | "ACRA_API_MARKETPLACE_MOCK" | "ACRA_GENERIC_SANDBOX";
  classification: "MOCK" | "PARTIAL";
  operation: AcraDiagnosticOperation;
  request_reference: string;
  started_at: string;
  completed_at: string;
  outcome: AcraDiagnosticOutcome;
  code: string;
  provider_called: boolean;
  record_count: number;
}

export interface AcraDiagnosticStatus {
  configuration: {
    provider: AcraDiagnosticReceipt["provider"];
    mode: "mock" | "api_marketplace_mock" | "sandbox";
    classification: "MOCK" | "PARTIAL";
    configured: boolean;
    safe_host: string | null;
    client_id_present: boolean;
    secret_key_present: boolean;
    generic_auth_present: boolean;
    timeout_seconds: number;
    max_response_bytes: number;
  };
  connectivity: "NOT_CHECKED" | "LAST_CHECK_SUCCEEDED" | "LAST_CHECK_FAILED";
  last_actual_check_at: string | null;
  cancellation_semantics: "PRE_DISPATCH_ONLY_IN_FLIGHT_USES_TIMEOUT";
  coverage: Array<{
    operation: AcraDiagnosticOperation;
    availability: "SUPPORTED" | "UNSUPPORTED";
    reason_code: string;
  }>;
  samples: Array<{
    uen: string;
    legal_name: string;
    classification: "PROFILE_VERIFIED" | "DOCUMENTED_SAMPLE_CANDIDATE";
    operations: AcraDiagnosticOperation[];
    limitation_codes: string[];
  }>;
  timeline: AcraDiagnosticReceipt[];
}

export interface AcraDiagnosticResult {
  requested_uen: string | null;
  operation: AcraDiagnosticOperation;
  outcome: AcraDiagnosticOutcome;
  code: string;
  message: string;
  missing_fields: string[];
  company: {
    uen: string;
    legal_name: string;
    country_code: string;
    entity_type: string;
    registration_date: string | null;
    entity_status: string | null;
    registered_address: {
      address_line_1: string;
      address_line_2: string | null;
      postal_code: string;
      country_code: string;
    } | null;
    source_environment: "MOCK" | "SANDBOX";
    retrieved_at: string;
  } | null;
  officers: Array<{
    officer_id: string;
    name: string;
    role: string;
    appointment_date: string | null;
    cessation_date: string | null;
    country: string | null;
  }>;
  shareholders: Array<{
    party_id: string;
    party_type: "NATURAL_PERSON" | "LEGAL_ENTITY";
    name: string;
    registration_identifier: string | null;
    country: string | null;
    source_category: string | null;
    source_status: string | null;
    share_allotted: string | null;
    ownership_percentage: string | null;
  }>;
  receipt: AcraDiagnosticReceipt;
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
    source_category?: string | null;
    source_status?: string | null;
    share_allotted?: string | null;
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
    status: "COMPLETE" | "EMPTY" | "FAILED" | "NOT_ATTEMPTED" | "UNSUPPORTED";
    record_count: number;
    provenance: RegistryEvidenceProvenance | null;
    error: { code: string; message: string } | null;
  }>;
  issues: Array<{ code: string; message: string }>;
  retrieved_at: string;
}

export interface RegistryEvidenceBinding {
  synthetic_seed_namespace?: "LOCAL_SYNTHETIC_UAT_V1" | null;
  disposition: "PROVIDER_FETCH" | "CACHE_HIT";
  bound_to_case_at: string;
  expires_at: string;
  freshness_policy_id: "MOCK_ACRA_FIXED_90D" | "MOCK_ACRA_APPROVED_POLICY";
  freshness_policy_version: number;
  freshness_duration_seconds: number;
  freshness_comparator: "EVALUATION_NOW_LT_EXPIRES_AT";
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
  created_by_actor_id?: string | null;
  team_id: TeamId | null;
  priority: number | null;
  client_scope_label: string | null;
  source_case_id: string;
  correlation_id: string;
  requested_uen: string;
  initial_identity?: {
    legal_name: string;
    registration_number: string;
    country_of_incorporation: string;
    /** D-114: omitted for COMPANY, the default. */
    entity_category?: EntityCategory;
  } | null;
  identity_corrections?: Array<{
    correction_id: string;
    actor_id: string;
    evidence_type: "OPERATOR_VERIFIED_SOURCE" | "USER_SUPPLIED_CORRECTION_POC";
    previous_identity: {
      legal_name: string;
      registration_number: string;
      country_of_incorporation: string;
    } | null;
    corrected_identity: {
      legal_name: string;
      registration_number: string;
      country_of_incorporation: string;
    };
    previous_search_request_id: string | null;
    corrected_at: string;
  }>;
  target_dispatch_confirmation?: {
    confirmation_id: string;
    actor_id: string;
    confirmed_at: string;
    case_event_count: number;
    clm_version: number | null;
    destination: "GOLDTIER_MOCK" | "GOLDTIER_XPI_SANDBOX";
    warnings: string[];
    review_digest: string;
    classification: "USER_AUTHORIZED_POC";
  } | null;
  policy_snapshot_revision?: number;
  policy_rebind?: PolicyRebindMetadata;
  policy_snapshot?: {
    snapshot_label: string;
    catalogue_version: number;
    idp_review_confidence_threshold: string;
    ubo_threshold_percent: string;
    comparator: "GREATER_THAN_OR_EQUAL_TO";
    bound_at: string;
  };
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
  registry_evidence_binding?: RegistryEvidenceBinding | null;
  goldtier_result: {
    party_id: string;
    shell_status: string;
    policy_id: string | null;
    policy_status: string | null;
    amend_status: string | null;
    readback_party_id?: string | null;
    readback_status?: string | null;
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

export interface ExtractionMetadata {
  extraction_method?: "UNKNOWN" | "NATIVE_PDF_TEXT" | "NATIVE_DOCX_TEXT" | "NATIVE_TXT_TEXT" | "LOCAL_TESSERACT_OCR";
  extraction_quality?: "UNKNOWN" | "HIGH" | "LOW" | "UNAVAILABLE" | "AMBIGUOUS";
  score_kind?: "LEGACY_UNSPECIFIED" | "DETERMINISTIC_EVIDENCE_SCORE";
  score_formula?: "LEGACY_UNSPECIFIED" | "LABEL_SCORE" | "LABEL_SCORE_TIMES_OCR_MEAN_OVER_100";
  raw_ocr_mean_confidence?: number | null;
  raw_ocr_word_count?: number | null;
}

export interface DocumentOwnershipObservation extends ExtractionMetadata {
  observation_id: string;
  document_id: string;
  document_version: 1;
  page_number: number;
  source_reference: string;
  evidence_score: number;
  owner_name: string;
  owner_type: "NATURAL_PERSON" | "LEGAL_ENTITY" | null;
  owner_registration_identifier: string | null;
  owned_entity_name: string | null;
  owned_entity_registration_identifier: string | null;
  share_count: string | null;
  explicit_percentage: string | null;
  explicit_total_shares: string | null;
  share_class: string | null;
  as_of_date: string | null;
  decision_state: "PROPOSED";
}

export interface OwnershipDocumentBinding { document_id: string; event_count: number }
export interface OwnershipDocumentDiscrepancy {
  observation_id: string;
  document_id: string;
  document_version: 1;
  agreement: "MATCH" | "MISMATCH" | "NOT_COMPARABLE" | "AMBIGUOUS";
  compared_relationship_ids: string[];
  current_percentage: string | null;
  proposed_percentage: string | null;
  reason_code: "OWNERSHIP_PROPOSAL_REVIEW_REQUIRED" | "OWNERSHIP_DOCUMENT_CONFLICT" | "OWNERSHIP_DOCUMENT_INCOMPLETE" | "OWNERSHIP_DOCUMENT_AMBIGUOUS"
    | "PARTNERSHIP_AGREEMENT_SHARE"; // D-101
  verification_state: "REVIEW_REQUIRED" | "REVIEWED";
}

export interface DocumentProcessingRecord {
  review_source_fingerprint?: string | null;
  case_id: string;
  document_id: string;
  document_version?: 1 | null;
  pages?: Array<ExtractionMetadata & { page_number: number; source_reference: string }>;
  ownership_observations?: DocumentOwnershipObservation[];
  correlation_id: string;
  display_name: string;
  media_type:
    | "application/pdf"
    | "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    | "text/plain"
    | "image/png"
    | "image/jpeg"
    | "image/tiff";
  size_bytes?: number;
  profile: "PROVISIONAL_CORPORATE";
  provider_environment: "MOCK" | "LOCAL" | "SANDBOX" | "LIVE" | null;
  state: DocumentProcessingState;
  completion_method?: "AUTO_CONFIRMED" | "HUMAN_REVIEWED" | "EXCEPTION_RESOLVED" | null;
  semantic_completion?: "RECONCILIATION_RESOLVED" | null;
  reconciliation_version?: number | null;
  fields: Array<ExtractionMetadata & {
    candidates?: Array<ExtractionMetadata & { value: string; page_number: number; source_reference: string }>;
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
    // D-086: an owner-declared overlay percentage (never an ACRA quantity).
    owner_declared_percentage?: boolean;
  };
}

export interface OwnershipEntityEffectiveInterest {
  party_id: string;
  effective_ownership_percent: string;
  paths: OwnershipPath[];
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
  // Hybrid lanes only: the backend's comparison on the declared assumed basis. It is never
  // a UBO classification and never changes the formal count or readiness.
  synthetic_basis_threshold_result?: "MET" | "NOT_MET" | "INDETERMINATE" | null;
}

export type OwnershipDiscoveryOutcome =
  | "CACHE_HIT"
  | "FETCHED"
  | "DEFERRED_BELOW_TRACE_THRESHOLD"
  | "DEPTH_LIMIT"
  | "BUSINESS_BUDGET"
  | "HARD_LIMIT"
  | "UNVERIFIED_UEN"
  | "FOREIGN_UNSUPPORTED"
  | "UNSUPPORTED_LEGAL_FORM"
  | "NOT_FOUND"
  | "PROVIDER_UNSUPPORTED"
  | "PROVIDER_PARTIAL"
  | "PROVIDER_FAILED"
  | "PROVIDER_INVALID"
  | "CACHE_FAILURE";

/** Backend corporate discovery audit; Decimal strings are displayed, never recalculated. */
export interface OwnershipDiscoveryAudit {
  method: "REGISTRY_CORPORATE_DISCOVERY_V1";
  trace_threshold_percent: string;
  ubo_threshold_percent: string;
  max_corporate_depth: number;
  call_budget_enabled: boolean;
  call_budget_max: number;
  graph_complete: boolean;
  classification_certainty: "COMPLETE" | "BOUNDED_NO_THRESHOLD_CHANGE" | "UNCERTAIN";
  unresolved_upper_bound_percent?: string | null;
  registry_lookups: number;
  provider_backed_lookups: number;
  cache_hits: number;
  records: Array<{
    party_id: string;
    display_name: string;
    registration_number?: string | null;
    depth: number;
    outcome: OwnershipDiscoveryOutcome;
    max_effective_percent?: string | null;
    reason_code?: string | null;
    // Hybrid lane: the issuer's identity source and its official registry legal form.
    identity_basis?: "OFFICIAL_MOCK_ENTITY_PROFILE" | "LOCAL_SYNTHETIC_IDENTITY" | null;
    official_legal_form?: "COMPANY" | "BUSINESS_PARTNERSHIP" | "LLP" | "LP" | "OTHER" | null;
    // D-088: a scenario-named issuer's official businessProfile, kept as returned.
    official_business_profile?: {
      entity_name: string;
      company_type?: string | null;
      status_of_company?: string | null;
      shareholders: Array<{
        display_name: string; source_category: string; provider_status?: string | null;
        number_of_shares: string; share_type?: string | null; currency?: string | null;
        assumed_current: boolean;
      }>;
      issued_share_capital: Array<{ share_type?: string | null; currency?: string | null; number_of_shares?: string | null }>;
      source_operation: "BUSINESS_PROFILE";
      environment: "MOCK";
    } | null;
  }>;
  unresolved_person_party_ids: string[];
  overlay_scenario_id?: string | null;
  topology_complete?: boolean | null;
}

export interface OwnershipAnalysisRecord {
  version?: number;
  document_observations?: DocumentOwnershipObservation[];
  document_bindings?: OwnershipDocumentBinding[];
  document_discrepancies?: OwnershipDocumentDiscrepancy[];
  source_classification?: "SINGLE_SOURCE" | "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT";
  supplemental_parties?: OwnershipParty[];
  supplemental_relationships?: OwnershipRelationship[];
  supplemental_evidence?: NonNullable<OwnershipAnalysisRecord["evidence"]>;
  manual_review_receipt?: ManualOwnershipReviewReceipt | null;
  // D-082: the persisted acceptance and whether the backend honours it now (authority).
  poc_acceptance?: OwnershipPocAcceptance | null;
  poc_basis_accepted?: boolean;
  // Presentation only: a declared-overlay simulation whose arithmetic completed; never
  // readiness, verification or acceptance.
  simulation_calculated?: boolean;
  // D-086 presentation only: engine path products reaching each intermediate entity.
  entity_effective_interests?: OwnershipEntityEffectiveInterest[];
  prior_analyses?: Array<Pick<OwnershipAnalysisRecord, "version" | "analysis_id" | "root_party_id" | "provider_name" | "provider_environment" | "state" | "parties" | "relationships" | "candidates" | "issues" | "created_at" | "analyzed_at" | "evidence" | "manual_review_receipt" | "document_observations" | "document_bindings" | "document_discrepancies" | "source_classification" | "supplemental_parties" | "supplemental_relationships" | "supplemental_evidence">>;
  legal_form?: "COMPANY" | "BUSINESS_PARTNERSHIP" | "LLP" | "LP" | "OTHER" | null;
  evidence?: Array<{
    evidence_id: string; entity_identifier: string | null; party_id: string;
    kind: string; raw_value: string; numeric_value: string | null;
    source_operation: string; provider: string; environment: string; retrieved_at: string;
  }>;
  tagging?: {
    method: "DETERMINISTIC_RULES"; runtime_status: "ML_RUNTIME_NOT_AVAILABLE";
    tags: Array<{ tag: string; reason_code: string; evidence_ids: string[]; confidence: string;
      rule_version: string; case_version: number; evidence_version: number;
      score?: string | null; threshold?: string | null; policy_version?: number | null; reason_codes?: string[] }>;
  } | null;
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
      | "CONTRADICTORY_OWNERSHIP_EVIDENCE"
      | "CYCLE_DETECTED"
      | "INCOMPLETE_LEGAL_ENTITY"
      | "OWNERSHIP_DENOMINATOR_REQUIRED"
      | "OWNERSHIP_REQUIRED"
      | "UBO_REVIEW_REQUIRED"
      | "OWNERSHIP_METHOD_UNSUPPORTED"
      | "MAXIMUM_DEPTH_EXCEEDED"
      | "PATH_LIMIT_EXCEEDED"
      | "CORPORATE_OWNERSHIP_UNRESOLVED"
      | "PERSON_IDENTITY_UNRESOLVED";
    message: string;
    affected_party_ids: string[];
  }>;
  discovery?: OwnershipDiscoveryAudit | null;
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
      | "OWNERSHIP_ANALYSIS_FAILED"
      | "OWNERSHIP_SOURCE_REPLACED";
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

export interface PolicyRebindMetadata {
  revision: number;
  configuration_status: "CURRENT_ACCEPTED_POC" | "REQUIRES_REBIND";
  accepted_poc_fields: string[];
  editable_fields: string[];
  upstream_fields: string[];
  unavailable_fields: string[];
  last_rebound_by: string | null;
  last_rebound_at: string | null;
  last_rationale: string | null;
  last_changed_fields: string[];
}

export type PocAssumption =
  | "SIMULATED_RELATIONSHIPS"
  | "EQUAL_UNIT_DENOMINATOR"
  | "DESCRIPTIVE_OFFICER_ROLES"
  | "UNCLASSIFIED_LEGAL_FORM"
  | "DESCRIPTIVE_INTERMEDIATE_OFFICER_ROLES"
  | "ISSUED_CAPITAL_DENOMINATOR";

export interface OwnershipPocAcceptance {
  policy: "D082_HYBRID_POC_EQUAL_UNITS_V1" | "D085_SCENARIO_DECLARED_POC_BASIS_V1";
  accepted_at: string;
  case_id: string;
  analysis_id: string;
  ownership_version: number;
  identity_registration_number: string;
  identity_correction_version: number;
  overlay_scenario_id: string;
  accepted_issue_codes: string[];
  poc_relationship_ids: string[];
  descriptive_current_role_count: number;
  descriptive_ceased_role_count: number;
  descriptive_intermediate_current_role_count?: number;
  descriptive_intermediate_ceased_role_count?: number;
  issued_capital_relationship_ids?: string[];
  accepted_assumptions?: PocAssumption[];
  basis_fingerprint: string;
}

export interface ManualOwnershipReviewReceipt {
  case_id: string;
  actor_id: string;
  reviewed_at: string;
  rationale: string | null;
  evidence_document_id: string;
  evidence_document_version: number;
  evidence_reference: string;
  source_type: "USER_SUPPLIED_DECLARATION";
  source_selection?: "USER_SUPPLIED_DECLARATION" | "CURRENT_EVIDENCE" | "DOCUMENT_OBSERVATIONS";
  observed_document_versions?: OwnershipDocumentBinding[];
  selected_observation_ids?: string[];
  replaced_analysis_id?: string | null;
  replaced_ownership_version?: number | null;
  provider_name: "MANUAL_DECLARATION_POC";
  provider_environment: "LOCAL";
  as_of_date: string;
}

export interface OwnershipRecoveryProjection {
  analysis_id: string;
  version: number;
  state: OwnershipAnalysisState;
  manual_evidence_action: "MANUAL_OWNERSHIP_EVIDENCE" | null;
  review_receipt: ManualOwnershipReviewReceipt | null;
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

export interface GoldTierPreviewField {
  target_field: string;
  value: string | null;
  provenance:
    | "CANONICAL_EVIDENCE"
    | "REGISTRY"
    | "DOCUMENT"
    | "ENTITY_RESOLUTION"
    | "POLICY"
    | "USER_INPUT"
    | "SYSTEM_DERIVED"
    | "SPONSOR_SUPPLIED"
    | "SANDBOX_OBSERVED"
    | "INDUSTRY_PRACTICE";
  authority:
    | "CANONICAL_EVIDENCE"
    | PolicyAuthority;
  required: boolean;
  missing: boolean;
  validation: "VALID" | "MISSING" | "INVALID";
}

export interface GoldTierRequestPreviewData {
  environment: "MOCK" | "SANDBOX";
  policy_version: number;
  operations: Array<{
    operation: "SEARCH" | "SHELL" | "POLICY" | "AMEND" | "READBACK";
    fields: GoldTierPreviewField[];
    missing_fields: string[];
    validation: "VALID" | "MISSING" | "INVALID";
  }>;
  dispatch_ready: boolean;
}

export interface GoldTierSubmissionPlan {
  environment: "MOCK" | "SANDBOX";
  provider_classification: "MOCK" | "SANDBOX_PARTIAL";
  base_operations: string[];
  match_found_behavior: "REVIEW_REQUIRED_NO_WRITES" | "EXACT_MATCH_REUSE_ELSE_REVIEW_NO_WRITES";
  related_party_integration: "PENDING_SPONSOR_CONFIRMATION" | "BLOCKED_CHILD_ID_LIFECYCLE";
  real_ready_for_approval: "NOT_AVAILABLE";
  request_preview: GoldTierRequestPreviewData | null;
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
  target_search_checkpoint?: {
    request_id: string;
    identity_fingerprint: string;
    provider_mode: "MOCK" | "SANDBOX";
    provider_classification: "MOCK" | "SANDBOX_PARTIAL";
    status: "COMPLETED" | "REVIEW_REQUIRED" | "FAILED" | "STALE";
    disposition: "NO_MATCH" | "EXACT_MATCH" | "CONFIRMED_EXISTING" | "REVIEW_REQUIRED" | "FAILED";
    provider_outcome: string;
    status_code: number;
    candidate_count: number;
    candidates: Array<{
      party_id: string;
      registration_number: string | null;
      country: string | null;
      legal_name: string | null;
      legal_form: string | null;
      registered_address: string | null;
    }>;
    selected_party_id: string | null;
    resolution_outcome: string | null;
    code: string | null;
    message: string;
    searched_at: string;
  } | null;
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
  | "GOLDTIER_SEARCH"
  | "DOCUMENT"
  | "OWNERSHIP"
  | "READINESS"
  | "MOCK_GOLDTIER"
  | "COMPLETE";

export type EventOutcome = "SUCCEEDED" | "PARTIAL" | "REVIEW_REQUIRED" | "FAILED";

export type ProcessingNodeStatus =
  | "UNSUPPORTED"
  | "COMPLETE"
  | "IN_PROGRESS"
  | "EMPTY"
  | "SKIPPED"
  | "REVIEW_REQUIRED"
  | "BLOCKED"
  | "FAILED"
  | "NOT_REACHED";

export interface ProcessingNode {
  node_id: string;
  label: string;
  status: ProcessingNodeStatus;
  provider?: string | null;
  environment?: string | null;
  operation?: string | null;
  backend_stage?: AutomationStage | null;
  timestamp?: string | null;
  safe_result?: string | null;
  record_count?: number | null;
  blocker_code?: string | null;
  retained_goldtier_id?: string | null;
  children: ProcessingNode[];
}

export type CaseActivityAction =
  | "CREATED"
  | "DOCUMENT"
  | "RECONCILIATION"
  | "OWNERSHIP"
  | "INTELLIGENCE"
  | "TARGET"
  | "COMPLETED";

export interface CaseActivityItem {
  case_id: string;
  sequence: number;
  timestamp: string;
  event_type: string;
  status: AutomationStatus;
  stage: AutomationStage;
  outcome: EventOutcome;
  code: string | null;
  message: string;
  current_priority: number | null;
  current_client_scope_label: string | null;
}

export interface CaseActivityPage {
  items: CaseActivityItem[];
  offset: number;
  limit: number;
  has_more: boolean;
}

/** D-101 derived, server-owned labels for the partnership and Government demo entity types. */
export interface GovernmentStatusProjection {
  state: "EVIDENCE_REQUIRED" | "CONFIRMATION_REQUIRED" | "CONFIRMED";
  document_id: string | null;
  document_event_count: number | null;
  founding_instrument: string | null;
  confirmed_by_actor_id: string | null;
  confirmed_at: string | null;
}

/** D-114: the RM's entity type; GOVERNMENT is read only from the government register, never ACRA. */
export type EntityCategory = "COMPANY" | "PARTNERSHIP" | "GOVERNMENT";

export interface EntityTypeBasis {
  entity_type: "PARTNERSHIP" | "GOVERNMENT";
  label: string;
  partnership_state?: "AWAITING_RM_CONFIRMATION" | "RM_CONFIRMED" | null;
  government_status: GovernmentStatusProjection | null;
}

export const BUSINESS_EXCEPTION_TYPES = [
  "REGISTRY_REVIEW_REQUIRED",
  "JURISDICTION_UNRESOLVED",
  "JURISDICTION_CONFLICT",
  "REGISTRY_PROVIDER_NOT_IMPLEMENTED",
  "REGISTRY_IDENTIFIER_NOT_ELIGIBLE",
  "DOCUMENT_SOURCE_CONFLICT",
  "DOCUMENT_LOW_CONFIDENCE",
  "DOCUMENT_REQUIRED_FIELD_MISSING",
  "DOCUMENT_REVIEW_REQUIRED",
  "RECONCILIATION_INVALID",
  "OWNERSHIP_CYCLE",
  "OWNERSHIP_INCOMPLETE",
  "OWNERSHIP_REVIEW_REQUIRED",
  "GOVERNMENT_STATUS_REQUIRED",
  "ENTITY_RESOLUTION_REVIEW_REQUIRED",
  "MOCK_RISK_REVIEW_REQUIRED",
  "EXISTING_PARTY_REVIEW_REQUIRED",
  "TARGET_PARTIAL_REVIEW_REQUIRED",
  "TARGET_CLASSIFICATION_REQUIRED",
  "TARGET_CONFIRMATION_REQUIRED",
] as const;

export type BusinessExceptionType = (typeof BUSINESS_EXCEPTION_TYPES)[number];

export const BUSINESS_EXCEPTION_TYPE_LABELS: Record<BusinessExceptionType, string> = {
  REGISTRY_REVIEW_REQUIRED: "Registry review required",
  JURISDICTION_UNRESOLVED: "Jurisdiction unresolved",
  JURISDICTION_CONFLICT: "Jurisdiction conflict",
  REGISTRY_PROVIDER_NOT_IMPLEMENTED: "Registry provider not implemented",
  REGISTRY_IDENTIFIER_NOT_ELIGIBLE: "Registry identifier not eligible",
  DOCUMENT_SOURCE_CONFLICT: "Document source conflict",
  DOCUMENT_LOW_CONFIDENCE: "Document low confidence",
  DOCUMENT_REQUIRED_FIELD_MISSING: "Document required field missing",
  DOCUMENT_REVIEW_REQUIRED: "Document review required",
  RECONCILIATION_INVALID: "Reconciliation invalid",
  OWNERSHIP_CYCLE: "Ownership cycle",
  OWNERSHIP_INCOMPLETE: "Ownership incomplete",
  OWNERSHIP_REVIEW_REQUIRED: "Ownership review required",
  GOVERNMENT_STATUS_REQUIRED: "Government status confirmation required",
  ENTITY_RESOLUTION_REVIEW_REQUIRED: "Entity resolution review required",
  MOCK_RISK_REVIEW_REQUIRED: "Mock advisory risk review required",
  EXISTING_PARTY_REVIEW_REQUIRED: "Existing party review required",
  TARGET_PARTIAL_REVIEW_REQUIRED: "Target partial review required",
  TARGET_CLASSIFICATION_REQUIRED: "Target classification required",
  TARGET_CONFIRMATION_REQUIRED: "Target confirmation required",
};

export type ZeroTouchDemoScenario =
  | "SME_STRAIGHT_THROUGH"
  | "SME_AMBIGUOUS_ENTITY"
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
  | "USE_DOCUMENT_VALUE"
  | "REQUEST_ADDITIONAL_INFORMATION";

export type ReconciliationField =
  | "legal_name"
  | "registration_identifier"
  | "registered_address"
  | "country_of_incorporation";

export type ReconciliationDecisionAction =
  | "KEEP_REGISTRY_VALUE"
  | "USE_DOCUMENT_VALUE";

export interface ReconciliationObservation {
  observation_id: string;
  field_name: ReconciliationField;
  normalized_value: string | null;
  source_kind: "USER_INPUT" | "REGISTRY" | "DOCUMENT_IDP" | "EXISTING_CASE";
  source_system: string | null;
  environment: string | null;
  observed_at: string;
  evidence_reference: string | null;
  document_id?: string | null;
  document_display_name?: string | null;
  confidence: number | null;
  validity: "VALID" | "MISSING" | "INVALID" | "UNVERIFIABLE" | "AMBIGUOUS";
}

export interface ReconciliationDecision {
  action: ReconciliationDecisionAction;
  selected_observation_id: string;
  selected_value: string;
  decided_at: string;
  reconciliation_version: number;
}

export interface ReconciliationDiscrepancy {
  discrepancy_id: string;
  field_name: ReconciliationField;
  outcome: "CONFLICT" | "MISSING_IN_SOURCE" | "UNVERIFIABLE" | "INVALID";
  observations: ReconciliationObservation[];
  status: "OPEN" | "RESOLVED" | "CANCELLED";
  allowed_actions: ReconciliationDecisionAction[];
  evidence_fingerprint: string;
  decision: ReconciliationDecision | null;
}

export interface ReconciliationSummary {
  reconciliation_id: string;
  version: number;
  status: "NOT_STARTED" | "MATCHED" | "REVIEW_REQUIRED" | "RESOLVED" | "FAILED";
  source_document_ids: string[];
  source_document_event_counts: number[];
  fields: Array<{
    field_name: ReconciliationField;
    observations: ReconciliationObservation[];
    outcome: "MATCH" | "REGISTRY_ONLY" | "CONFLICT" | "MISSING_IN_SOURCE" | "UNVERIFIABLE" | "INVALID";
    document_required?: boolean;
    discrepancy_id: string | null;
  }>;
  discrepancies: ReconciliationDiscrepancy[];
  updated_at: string;
}

export interface ZeroTouchException {
  exception_id: string;
  case_id: string;
  exception_type: BusinessExceptionType;
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
  decisions?: BlockerDecisionRecord[];
  created_at: string;
  resolved_at: string | null;
  resolution: ExceptionResolutionAction | null;
}

export interface HumanInterventionProjection {
  existing_customer_confirmation_action?: "CONFIRM_EXISTING_GOLDTIER_CUSTOMER" | null;
  blocker_class?: "WARNING" | "RECOVERABLE_INPUT" | "HUMAN_DECISION" | "WAITING_EXTERNAL" | "HARD_SAFETY_STOP";
  evidence_actions?: Array<{ target: "DOCUMENTS" | "OWNERSHIP_DETAILS" | "OWNERSHIP_UPLOAD" | "CLASSIFICATION" | "IDENTITY" | "REVIEW_SEND"; label: string }>;
  intervention_id: string;
  owning_stage: AutomationStage;
  owning_stage_label: string;
  title: string;
  blocker_code: string;
  explanation: string;
  required_evidence_or_input: string[];
  authorized_actions: Array<{
    action: ExceptionResolutionAction;
    label: string;
    description: string;
  }>;
  no_action_reason: string | null;
  expected_next_step: string;
  candidate_summaries: Array<{
    party_id: string;
    registration_number: string | null;
    country: string | null;
    legal_name: string | null;
    legal_form: string | null;
  }>;
  decisions?: BlockerDecisionRecord[];
  dependent_stages?: string[];
  backend_mutation_owner?: string;
  resolution_condition?: string;
  resume_target?: AutomationStage | null;
}

export type BlockerDecisionClassification =
  | "AUTO_RESOLVED_WITH_NOTE"
  | "CONTINUE_WITH_WARNING"
  | "USER_ACTION_REQUIRED"
  | "EXTERNAL_DEPENDENCY"
  | "HARD_STOP";

export type BlockerDecisionOwner =
  | "CASE_OPERATOR"
  | "DOCUMENT_REVIEW_OWNER"
  | "IDENTITY_REVIEW_OWNER"
  | "REGISTRY_INTEGRATION_OWNER"
  | "OWNERSHIP_REVIEW_OWNER"
  | "POLICY_OWNER"
  | "TARGET_OPERATIONS_OWNER"
  | "TARGET_PROVIDER_OWNER";

export type ResumeTransition =
  | "NO_AUTOMATIC_RESUME"
  | "RECHECK_FROM_STAGE"
  | "REPLACE_EVIDENCE_AND_RECHECK"
  | "APPLY_AUTHORIZED_DECISION_AND_RECHECK"
  | "VERIFY_WITHOUT_REPLAY"
  | "CONTINUE_INDEPENDENT_EVIDENCE_ONLY"
  | "RETAIN_NOTE_WITHOUT_WORKFLOW_CHANGE";

export interface BlockerDecisionRecord {
  decision_id: string;
  case_id: string;
  exception_id: string | null;
  evidence_version: string;
  automation_version: number;
  recorded_at: string;
  metadata: {
    blocker_code: string;
    exception_type: BusinessExceptionType | null;
    classification: BlockerDecisionClassification;
    policy_version: string;
    rule_version: string;
    owner: BlockerDecisionOwner;
    minimum_inputs: string[];
    permitted_actions: string[];
    currently_available_actions: string[];
    resume_stage: AutomationStage | null;
    resume_transition: ResumeTransition;
    resume_ready: boolean;
    invalidated_dependencies: string[];
    explanation: string;
    unknowns: string[];
  };
  actor_id: string | null;
  reviewer_id: string | null;
}

export interface TargetClassificationSelection {
  field_key: "kyc_customer_type" | "client_segment";
  value: string;
  source: "DOCUMENT" | "USER";
  document_evidence: {
    document_id: string; document_version: number; document_event_count: number;
    page_number: number; source_reference: string; extraction_method: string;
    extraction_quality: string; evidence_score: number; extracted_exact_value: string;
  } | null;
  evidence_fingerprint?: string | null; actor_id?: string | null;
  classified_at: string; policy_version: number; vocabulary_version: string;
}

export interface GoldTierTargetClassificationField {
  selection?: TargetClassificationSelection | null;
  allowed_values: string[];
  selected_value: string | null;
  authority: string | null;
  required: true;
}

export interface GoldTierTargetClassification {
  evidence_state?: "NO_EVIDENCE" | "PARTIAL" | "SAFE_CANDIDATE" | "CONFLICT" | "UNSAFE" | null;
  evidence_fingerprint?: string | null;
  current?: boolean | null;
  review_required?: boolean;
  evidence_values?: Partial<Record<"kyc_customer_type" | "client_segment", string[]>>;
  state?: "CURRENT" | "REVIEW_REQUIRED" | "CONFLICT";
  vocabulary_version: string;
  editable: boolean;
  kyc_customer_type: GoldTierTargetClassificationField;
  client_segment: GoldTierTargetClassificationField;
}

export interface ClassificationConsistencyAdvisory {
  status: "COMPATIBLE" | "OPERATOR_REVIEW" | "UNKNOWN_LEGAL_FORM";
  title: string;
  explanation: string;
  blocking: false;
  authority: "PROJECT_ADVISORY_ONLY";
}

export interface ZeroTouchCaseSummary {
  target_submission?: {
    submission_id: string | null;
    state: "NOT_SUBMITTED" | "SENDING" | "SUBMISSION_CONFIRMED" | "SUBMISSION_FAILED"
      | "SUBMISSION_OUTCOME_UNCERTAIN" | "FINALIZATION_PENDING";
    goldtier_id: string | null;
    status_check_available: boolean;
    recovery_operation?: "SHELL" | "POLICY" | null;
    recovery_available?: boolean;
    provider_policy?: string | null;
    uncertainty_reason?: string | null;
    ledger_state?: string | null;
    attempted_operations?: string[];
    definitively_completed_operations?: string[];
    lifecycle_resolved_operations?: string[];
    verification_available?: boolean;
    customer_handling?: "EXISTING_REUSED" | "NEW_CREATED" | null;
  } | null;
  evidence_decision_authorized?: boolean;
  document_replacement_authorized?: boolean;
  document_refresh_recovery?: { can_resume: boolean } | null;
  ownership_edit_authorized?: boolean;
  entity_type_basis?: EntityTypeBasis | null;
  case: OnboardingCase;
  clm: ClmCaseSummary;
  automation_id: string;
  version: number;
  status: AutomationStatus;
  current_stage: AutomationStage;
  completed_stages: AutomationStage[];
  active_exceptions: ZeroTouchException[];
  historical_exceptions?: ZeroTouchException[];
  non_blocking_decisions?: BlockerDecisionRecord[];
  interventions?: HumanInterventionProjection[];
  target_classification: GoldTierTargetClassification;
  classification_consistency?: ClassificationConsistencyAdvisory;
  ownership_recovery?: OwnershipRecoveryProjection | null;
  reconciliation: ReconciliationSummary | null;
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
    operation: "SEARCH" | "SHELL" | "POLICY" | "AMEND" | "READBACK";
    status:
      | "NOT_ATTEMPTED"
      | "IN_PROGRESS"
      | "OUTCOME_UNCERTAIN"
      | "NO_MATCH"
      | "MATCH_FOUND"
      | "SKIPPED"
      | "RECOVERED"
      | "REVIEW_REQUIRED"
      | "CREATED"
      | "SUCCESS"
      | "FAILED";
  }>;
  stage_order_version: 1 | 2;
  processing_pipeline: ProcessingNode[];
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
  timing: CaseDetailTiming;
}

export interface CaseTiming {
  case_elapsed_ms: number;
  time_since_last_update_ms: number;
  automation_elapsed_ms: number | null;
  recorded_total_duration_ms: number | null;
}

export interface CaseDetailTiming extends CaseTiming {
  observed_at: string;
}

export interface ZeroTouchCaseListItem {
  case_id: string;
  team_id: TeamId | null;
  client_scope_label: string | null;
  priority: number | null;
  requested_uen: string;
  legal_name: string | null;
  status: AutomationStatus;
  current_stage: AutomationStage;
  updated_at: string;
  active_exception_count: number;
  active_exception_types: BusinessExceptionType[];
  human_interventions: number;
  final_outcome: string | null;
  resolved_jurisdiction: "SG" | "AU" | "MY" | "HK" | null;
  created_at: string;
  completed_at: string | null;
  mock_goldtier_party_id: string | null;
}

export type EntityResolutionOutcome =
  | "EXACT_MATCH"
  | "PROBABLE_MATCH"
  | "REVIEW_REQUIRED"
  | "NO_MATCH"
  | "CONFLICT";

export interface OnboardingIntelligenceRecord {
  case_id: string;
  version: number;
  input_fingerprint: string;
  policy_catalogue_version: number;
  model_bundle_version: "onboarding-intelligence-v1";
  entity_resolution: {
    outcome: EntityResolutionOutcome;
    selected_candidate_id: string | null;
    source_reference: string | null;
    candidates: Array<{
      candidate_id: string;
      probability: string;
      assessed_weight: string;
      corroborating_feature_count: number;
      features: Array<{
        name: string;
        assessment: "ASSESSED" | "NOT_ASSESSED" | "CONFLICT";
        agreement: string | null;
        weight: string;
      }>;
      top_contributing_features: string[];
      source_reference: string | null;
    }>;
    reason_codes: string[];
    model_version: "entity-resolution-linear-v1";
    assistance_label: "ML_ASSISTED";
    disclaimer: "NOT_IDENTITY_AUTHORITY";
  } | null;
  ubo_advice: Array<{
    party_id: string;
    probability: string | null;
    label: "LIKELY_UBO" | "REVIEW" | "UNLIKELY_UBO";
    authoritative_ownership_percent: string;
    reason_codes: string[];
    model_version: "ubo-advisory-linear-v1";
    assistance_label: "ML_ASSISTED";
    disclaimer: "NOT_LEGAL_UBO_DETERMINATION";
  }>;
  mock_risk: {
    score: number | null;
    band: "LOW" | "MEDIUM" | "HIGH" | "NOT_ASSESSED";
    signal_assessments: Record<string, string>;
    reason_codes: string[];
    not_assessed_signals: string[];
    model_version: "mock-advisory-risk-rules-v1";
    label: "MOCK_ADVISORY_RISK";
    disclaimer: "NOT_COMPLIANCE_DECISION";
    blocks_readiness: boolean;
  } | null;
  evaluated_at: string;
}

export interface CasePortfolioItem extends ZeroTouchCaseListItem {
  timing: CaseTiming;
}

export interface CasePortfolioPage {
  observed_at: string;
  items: CasePortfolioItem[];
  offset: number;
  limit: number;
  has_more: boolean;
}

export interface DashboardScope {
  actor_role: AuthenticatedProfile["role"];
  access: "TEAM" | "GLOBAL";
  team_id: TeamId | null;
  team_display_name: string | null;
  client_scope_label: string;
}

export interface DashboardCaseItem {
  case_id: string;
  requested_uen: string;
  legal_name: string | null;
  team_id: TeamId | null;
  team_display_name: string | null;
  priority: number | null;
  status: AutomationStatus;
  current_stage: AutomationStage;
  progress_percent: number;
  final_outcome: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  case_elapsed_ms: number;
  delay_note: string | null;
  created_by_display_name: string | null;
}

export interface DashboardTimingSummary {
  mean_total_duration_ms: number | null;
  zero_touch_mean_duration_ms: number | null;
  zero_touch_count: number;
  blocked_mean_duration_ms: number | null;
  blocked_count: number;
}

export interface DashboardStageCaseTiming {
  case_id: string;
  requested_uen: string;
  legal_name: string | null;
  duration_ms: number;
  had_blocker: boolean;
}

export interface DashboardStageTiming {
  stage: AutomationStage;
  clean_mean_ms: number | null;
  clean_count: number;
  with_blocker_mean_ms: number | null;
  with_blocker_count: number;
  combined_mean_ms: number | null;
  blocked_count: number;
  top_cases: DashboardStageCaseTiming[];
}

export interface DashboardExceptionCount {
  exception_type: BusinessExceptionType;
  count: number;
}

export type JurisdictionCode = "SG" | "AU" | "MY" | "HK";

export interface DashboardWeeklyOnboarded {
  week_start: string;
  by_jurisdiction: Partial<Record<JurisdictionCode, number>>;
  unresolved_count: number;
}

export interface DashboardWorkloadRow {
  user_id: string;
  display_name: string;
  open_cases: number;
  oldest_open_age_ms: number | null;
  completed_cases: number;
  blockers_resolved: number;
  mean_fix_time_ms: number | null;
}

export interface DashboardTrendDay {
  day: string;
  created_count: number;
  completed_count: number;
}

export interface DashboardSnapshot {
  historical_trend: DashboardTrendDay[];
  scope: DashboardScope;
  view: "team" | "mine";
  data_as_of: string;
  totals: {
    total_cases: number;
    completed_cases: number;
    non_completed_cases: number;
    completion_rate: number;
    prioritised_cases: number;
    unprioritised_cases: number;
  };
  zero_touch_rate: number;
  timing: DashboardTimingSummary;
  status_breakdown: Array<{ status: AutomationStatus; count: number }>;
  priority_breakdown: Array<{ priority: number | null; count: number }>;
  team_breakdown: Array<{
    team_id: TeamId;
    team_display_name: string;
    client_scope_label: string;
    count: number;
  }>;
  stage_timing: DashboardStageTiming[];
  exception_breakdown: DashboardExceptionCount[];
  weekly_onboarded: DashboardWeeklyOnboarded[];
  workload_by_person: DashboardWorkloadRow[];
  recent_cases: DashboardCaseItem[];
  top_active_cases: DashboardCaseItem[];
  scoped_cases: DashboardCaseItem[];
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

export interface PolicyProposal {
  proposal_id: string;
  version: number;
  base_active_version: number;
  proposer_id: string;
  status: "DRAFT" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED";
  rules: PolicyRule[];
  reason: string;
  created_at: string;
  updated_at: string;
  decided_by: string | null;
  decided_at: string | null;
  decision_reason: string | null;
  activated_version: number | null;
}
export interface ClassifierBenchmark {
  label: string; benchmark_id: string; benchmark_hash: string; rule_version: string;
  policy_version: number; scope: string; support: number; exact_accuracy: number;
  classes: Array<{ label: string; precision: number; recall: number; f1: number; support: number }>;
  confusion_matrix: Record<string, Record<string, number>>;
  macro: { precision: number; recall: number; f1: number };
  micro: { precision: number; recall: number; f1: number };
}
export type ImpactMateriality = "NO_OBSERVED_CHANGE" | "LOW" | "MODERATE" | "HIGH" | "NOT_ASSESSED";
export interface ImpactOutcome {
  label: string; value: string | null; score: string | null; threshold: string | null;
  reason_codes: string[]; automatic: boolean | null; review_required: boolean | null;
  provisional_candidate: boolean | null; cache_reuse: boolean | null;
}
export interface ImpactScenario {
  fixture_id: string; stage: "REGISTRY" | "DOCUMENT" | "OWNERSHIP" | "CLASSIFIER" | "INTELLIGENCE" | "READINESS";
  effect: "AUTOMATIC_REVIEW" | "PROVISIONAL_CANDIDATE" | "CACHE_ONLY" | "ADVISORY";
  before: ImpactOutcome; after: ImpactOutcome;
}
export interface ImpactChange {
  policy_id: string; name: string; current: PolicyValue; base: PolicyValue;
  default: PolicyValue; proposed: PolicyValue; direction: "INCREASE" | "DECREASE" | "VALUE_CHANGE";
  stages: ImpactScenario["stage"][]; assessment: "ASSESSED" | "NOT_ASSESSED";
  materiality: ImpactMateriality; effect: ImpactScenario["effect"] | "NOT_ASSESSED";
  scenario_ids: string[]; coupled_policy_ids: string[]; reason_codes: string[]; limitations: string[];
}
export type PolicyImpactVersionContext = "ACTIVE_BASE" | "RETAINED_BASE" | "PROSPECTIVE_UNRESERVED" | "ACTIVATED_PROPOSAL";
export interface PolicyImpact {
  proposal_id: string; proposal_version: number; catalogue_version: number;
  base_active_version: number; current_active_version: number; stale: boolean;
  comparison_basis: "ACTIVE_PROPOSAL_BASE" | "RETAINED_PROPOSAL_BASE"; comparison_identity: string;
  label: string; changes: ImpactChange[];
  before: { policy_version_context: PolicyImpactVersionContext; classifier: ClassifierBenchmark; runtime: PolicyRuntimeImpact };
  after: { policy_version_context: PolicyImpactVersionContext; classifier: ClassifierBenchmark; runtime: PolicyRuntimeImpact };
  advisor: {
    fixture_set_id: "SYNTHETIC_POLICY_IMPACT_V1"; fixture_set_hash: string;
    scope: string; classifier_scope: string; materiality: ImpactMateriality; reason_codes: string[];
    scenarios: ImpactScenario[];
    automation_delta: Record<string, { before: number | null; after: number | null; delta: number | null }>;
    automation_direction: "MORE_AUTOMATIC" | "LESS_AUTOMATIC" | "NO_OBSERVED_CHANGE" | "NOT_ASSESSED";
    review_direction: "MORE_REVIEW" | "LESS_REVIEW" | "NO_OBSERVED_CHANGE" | "NOT_ASSESSED";
    registry_reuse_direction: "MORE_RESTRICTIVE_REUSE" | "LESS_RESTRICTIVE_REUSE" | "NO_OBSERVED_CHANGE";
    negative_reuse_direction: "MORE_RESTRICTIVE_REUSE" | "LESS_RESTRICTIVE_REUSE" | "NO_OBSERVED_CHANGE";
    classifier_metric_delta: Record<string, number>;
    unknown_impacts: Array<{ concept: string; status: "NOT_ASSESSED"; reason_code: "IMPACT_NOT_ASSESSED"; limitation: string }>;
    limits: Record<string, number>;
  };
}
export interface PolicyRuntimeImpact {
  registry_freshness_seconds: number; not_found_ttl_seconds: number;
  document_auto_confirm: boolean[]; ownership_numeric_candidates: (boolean | null)[];
}

export interface ReviewDecisionBatch {
  expected_automation_version: number;
  expected_case_event_count: number;
  documents?: {
    document_id: string;
    expected_event_count: number;
    source_fingerprint: string;
    decisions: { field_key: DocumentFieldKey; decision: ReviewDecision; corrected_value?: string; note?: string }[];
  }[];
  reconciliation?: { discrepancy_id: string; action: ReconciliationDecisionAction; evidence_fingerprint: string }[];
  expected_reconciliation_version?: number;
}
