import type {
  AutomationStage,
  CasePortfolioItem,
  SimulationProfile,
  ZeroTouchCaseListItem,
} from "./types";

export interface CaseRowView {
  case_id: string;
  requested_uen: string;
  company_name: string | null;
  jurisdiction: string | null;
  status: ZeroTouchCaseListItem["status"];
  current_stage: ZeroTouchCaseListItem["current_stage"];
  created_at: string | null;
  updated_at: string;
  completed_at: string | null;
  timing: CasePortfolioItem["timing"] | null;
  active_exception_count: number;
  active_exception_types: ZeroTouchCaseListItem["active_exception_types"];
  human_interventions: number;
  final_outcome: string | null;
  priority: number | null;
  client_scope_label: string | null;
  /** The party ID GoldTier returned (Mock or Sandbox), for looking the customer up there. */
  goldtier_party_id: string | null;
}

export function mapZeroTouchCaseToCaseRow(
  item: ZeroTouchCaseListItem | CasePortfolioItem,
): CaseRowView {
  return {
    case_id: item.case_id,
    requested_uen: item.requested_uen,
    company_name: item.legal_name,
    jurisdiction: item.resolved_jurisdiction,
    status: item.status,
    current_stage: item.current_stage,
    created_at: item.created_at,
    updated_at: item.updated_at,
    completed_at: item.completed_at,
    timing: "timing" in item ? item.timing : null,
    active_exception_count: item.active_exception_count,
    active_exception_types: item.active_exception_types,
    human_interventions: item.human_interventions,
    final_outcome: item.final_outcome,
    priority: item.priority,
    client_scope_label: item.client_scope_label,
    goldtier_party_id: item.mock_goldtier_party_id ?? null,
  };
}

export type PolicyClassification =
  | "REAL"
  | "DERIVED"
  | "PENDING SPONSOR CONFIRMATION"
  | "UNAVAILABLE";

export interface ClassifiedPolicyValue<T = string> {
  value: T;
  classification: PolicyClassification;
}

export interface PolicyView {
  open_questions: Array<ClassifiedPolicyValue>;
  jurisdiction_rules: Array<{
    jurisdiction: "SG" | "AU" | "MY" | "HK";
    implemented: ClassifiedPolicyValue<boolean>;
    id_label: ClassifiedPolicyValue;
    registry: ClassifiedPolicyValue;
    ubo_threshold_percent: ClassifiedPolicyValue;
  }>;
  pipeline: {
    stages: ClassifiedPolicyValue<AutomationStage[]>;
    screening_auto_clear_threshold: ClassifiedPolicyValue;
    idp_review_confidence_threshold: ClassifiedPolicyValue<number>;
    registry_snapshot_staleness_limit_days: ClassifiedPolicyValue;
  };
  roles: {
    reviewer_count: ClassifiedPolicyValue;
    self_review_blocked: ClassifiedPolicyValue;
  };
  scheduler: {
    next_review_months_low: ClassifiedPolicyValue;
    next_review_months_medium: ClassifiedPolicyValue;
    next_review_months_high: ClassifiedPolicyValue;
    rescreening_cadence_months: ClassifiedPolicyValue;
  };
  execution: {
    registry: ClassifiedPolicyValue;
    idp: ClassifiedPolicyValue;
    ownership: ClassifiedPolicyValue;
    target: ClassifiedPolicyValue;
    persistence: ClassifiedPolicyValue;
  };
}

export function mapExecutionProfileToPolicy(profile: SimulationProfile): PolicyView {
  const unavailable = "Not available in current POC";
  const classified = <T,>(value: T, classification: PolicyClassification): ClassifiedPolicyValue<T> => ({ value, classification });
  return {
    open_questions: [
      classified("Q-012 · authoritative ACRA API, authentication, and TLS details remain open.", "PENDING SPONSOR CONFIRMATION"),
      classified("Q-015 · source precedence and authenticated reviewer authority remain open.", "PENDING SPONSOR CONFIRMATION"),
      classified("Sponsor-approved UBO and production business-rule decisions remain open.", "PENDING SPONSOR CONFIRMATION"),
    ],
    jurisdiction_rules: (["SG", "AU", "MY", "HK"] as const).map((jurisdiction) => ({
      jurisdiction,
      implemented: classified(jurisdiction === "SG", "DERIVED"),
      id_label: classified(jurisdiction === "SG" ? "UEN" : unavailable, jurisdiction === "SG" ? "DERIVED" : "UNAVAILABLE"),
      registry: classified(jurisdiction === "SG" ? profile.registry_system : unavailable, jurisdiction === "SG" ? "DERIVED" : "UNAVAILABLE"),
      ubo_threshold_percent: classified(profile.ubo_ownership_threshold_percent, "REAL"),
    })),
    pipeline: {
      stages: classified(["REGISTRY", "DOCUMENT", "OWNERSHIP", "READINESS", "MOCK_GOLDTIER", "COMPLETE"], "DERIVED"),
      screening_auto_clear_threshold: classified(unavailable, "UNAVAILABLE"),
      idp_review_confidence_threshold: classified(profile.idp_review_confidence_threshold, "REAL"),
      registry_snapshot_staleness_limit_days: classified(unavailable, "UNAVAILABLE"),
    },
    roles: {
      reviewer_count: classified(unavailable, "UNAVAILABLE"),
      self_review_blocked: classified("Pending sponsor confirmation", "PENDING SPONSOR CONFIRMATION"),
    },
    scheduler: {
      next_review_months_low: classified(unavailable, "UNAVAILABLE"),
      next_review_months_medium: classified(unavailable, "UNAVAILABLE"),
      next_review_months_high: classified(unavailable, "UNAVAILABLE"),
      rescreening_cadence_months: classified(unavailable, "UNAVAILABLE"),
    },
    execution: {
      registry: classified(`${profile.registry_system} ${profile.registry_environment}`, "REAL"),
      idp: classified(`${profile.idp_provider} ${profile.idp_environment}`, "REAL"),
      ownership: classified(`${profile.ownership_system} ${profile.ownership_environment}`, "REAL"),
      target: classified(`${profile.target_system} ${profile.target_environment}`, "REAL"),
      persistence: classified(profile.persistence, "REAL"),
    },
  };
}
