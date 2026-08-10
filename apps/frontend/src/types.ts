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
