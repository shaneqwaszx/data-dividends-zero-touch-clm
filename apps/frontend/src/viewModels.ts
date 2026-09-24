import type {
  AutomationStage,
  DocumentProcessingRecord,
  OwnershipAnalysisRecord,
  CasePortfolioItem,
  SimulationProfile,
  ZeroTouchCaseListItem,
  ZeroTouchCaseSummary,
} from "./types";
import { targetOutcomeLabel } from "./shared";

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
  };
}

export interface OnboardedRowView {
  case_id: string;
  mock_goldtier_party_id: string | null;
  company_name: string | null;
  registration_id: string;
  jurisdiction: string | null;
  risk_rating: null;
  onboarded_at: string;
  next_review_date: null;
  priority: number | null;
  client_scope_label: string | null;
}

export function mapCompletedCaseToOnboardedRow(
  item: ZeroTouchCaseListItem,
): OnboardedRowView {
  return {
    case_id: item.case_id,
    mock_goldtier_party_id: item.mock_goldtier_party_id,
    company_name: item.legal_name,
    registration_id: item.requested_uen,
    jurisdiction: item.resolved_jurisdiction,
    risk_rating: null,
    onboarded_at: item.completed_at ?? item.updated_at,
    next_review_date: null,
    priority: item.priority,
    client_scope_label: item.client_scope_label,
  };
}

function formatAddress(summary: ZeroTouchCaseSummary): string | null {
  const address = summary.case.entity?.registered_address;
  if (!address) return null;
  return [
    address.address_line_1,
    address.address_line_2,
    address.postal_code,
    address.country_code,
  ].filter(Boolean).join(", ");
}

export interface ClientDetailView {
  mock_goldtier_party_id: string | null;
  case_id: string;
  company_name: string | null;
  jurisdiction: string | null;
  status: ZeroTouchCaseSummary["status"];
  onboarded_at: string;
  risk_rating: null;
  next_review_date: null;
  registration_id: string;
  entity_type: string | null;
  registry_status: string | null;
  registration_date: string | null;
  registered_address: string | null;
  directors: Array<{
    name: string;
    identification: string | null;
    date_of_birth: null;
    appointed: string | null;
    source: string;
  }>;
  beneficial_owners: Array<{
    owner: string;
    holding: string;
    type: string;
    path: string;
    source: string;
  }>;
  documents: Array<{ name: string; note: string; details: string }>;
  onboarding_record: Array<{ stage: string; method: string; cleared_at: string }>;
  check_results: Array<{ check: string; outcome: string }>;
  since_onboarding: Array<{ date: string; event: string }>;
  human_touches: number;
  elapsed_time_ms: number | null;
  registry_operations: Array<{ operation: string; status: string; record_count: number; provenance: string }>;
  target_operations: Array<{ operation: string; status: string }>;
  readiness_blockers: string[];
  readiness_warnings: string[];
  final_outcome: string | null;
}

export function mapZeroTouchCaseToClientDetail(
  summary: ZeroTouchCaseSummary,
  documents: DocumentProcessingRecord[],
  ownership: OwnershipAnalysisRecord | null,
): ClientDetailView {
  const acquisition = summary.case.registry_acquisition;
  const completionByStage = new Map<AutomationStage, string>();
  for (const event of summary.timeline) {
    if (event.outcome === "SUCCEEDED") completionByStage.set(event.stage, event.timestamp);
  }
  const completionEvent = [...summary.timeline].reverse().find(
    (event) => event.event_type === "MOCK_SUBMISSION_COMPLETED",
  );
  return {
    mock_goldtier_party_id: summary.case.goldtier_result?.party_id ?? null,
    case_id: summary.case.case_id,
    company_name: summary.case.entity?.legal_name ?? null,
    jurisdiction: summary.case.jurisdiction_resolution?.resolved_jurisdiction ?? null,
    status: summary.status,
    onboarded_at: completionEvent?.timestamp ?? summary.updated_at,
    risk_rating: null,
    next_review_date: null,
    registration_id: summary.case.entity?.registration_number ?? summary.case.requested_uen,
    entity_type: summary.case.entity?.party_type ?? null,
    registry_status: summary.case.entity?.entity_status ?? null,
    registration_date: summary.case.entity?.registration_date ?? null,
    registered_address: formatAddress(summary),
    directors: (acquisition?.officers ?? []).map((officer) => ({
      name: officer.name,
      identification: null,
      date_of_birth: null,
      appointed: officer.appointment_date,
      source: `${officer.provenance.provider} ${officer.provenance.environment}`,
    })),
    beneficial_owners: (ownership?.candidates ?? [])
      .filter((candidate) => candidate.classification === "PROVISIONAL_UBO_CANDIDATE")
      .map((candidate) => ({
        owner: candidate.party.display_name,
        holding: `${candidate.aggregated_ownership_percent}%`,
        type: "Provisional UBO candidate",
        path: candidate.paths.map((path) => path.calculation).join("; ") || "Direct evidence unavailable",
        source: ownership?.provider_name
          ? `${ownership.provider_name} ${ownership.provider_environment ?? ""}`.trim()
          : "Not available in current POC",
      })),
    documents: documents.map((document) => ({
      name: document.display_name,
      note: document.superseded_by_document_id
        ? "Superseded evidence"
        : `${document.state} · ${document.media_type}`,
      details: `${document.provider_environment ?? "—"} · ${document.fields.length} field(s) · ${document.fields.map((field) => `${field.field_key} ${Math.round(field.confidence * 100)}% ${field.comparison_status}`).join("; ") || "no field evidence"}`,
    })),
    onboarding_record: summary.completed_stages.map((stage) => ({
      stage: stage.replaceAll("_", " "),
      method: "Backend automation",
      cleared_at: completionByStage.get(stage) ?? "—",
    })),
    check_results: [
      { check: "Registry", outcome: summary.clm.readiness.registry.status },
      { check: "Documents", outcome: summary.clm.readiness.document.status },
      { check: "Ownership", outcome: summary.clm.readiness.ownership.status },
      { check: "Target readiness", outcome: summary.clm.readiness.goldtier.status },
      { check: "Reconciliation", outcome: summary.reconciliation?.status ?? "NOT STARTED" },
    ],
    since_onboarding: summary.timeline.map((event) => ({
      date: event.timestamp,
      event: event.message,
    })),
    human_touches: summary.metrics.human_interventions,
    elapsed_time_ms: summary.metrics.total_duration_ms,
    registry_operations: (acquisition?.operation_results ?? []).map((operation) => ({
      operation: operation.operation,
      status: operation.status,
      record_count: operation.record_count,
      provenance: operation.provenance
        ? `${operation.provenance.provider} ${operation.provenance.environment} · ${operation.provenance.evidence_reference}`
        : "—",
    })),
    target_operations: summary.target_operations,
    readiness_blockers: summary.clm.readiness.blockers,
    readiness_warnings: summary.clm.readiness.warnings,
    final_outcome: summary.metrics.final_outcome
      ? targetOutcomeLabel(
          summary.metrics.final_outcome,
          summary.clm.submission_plan.environment,
        )
      : null,
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
