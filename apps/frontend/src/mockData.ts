/**
 * Temporary visualization scaffolding: sample data for the new
 * queue/case-detail/onboarded/audit/policy screens, used ONLY as a fallback
 * when the real backend endpoint is unreachable (see api.ts). Remove once
 * those endpoints exist for real -- this is not meant to ship long-term.
 */
import type {
  AuditEntry,
  CaseListItem,
  ClientRecord,
  PolicyResponse,
  Reviewer,
  ZeroTouchCaseSummary,
} from "./types";

export const MERIDIAN_CASE_ID = "CLM-0431";
export const COASTLINE_CASE_ID = "CLM-0402";

export const mockCases: CaseListItem[] = [
  {
    case_id: MERIDIAN_CASE_ID,
    requested_uen: "201834567K",
    company_name: "Meridian Trade Pte Ltd",
    jurisdiction: "SG",
    status: "RUNNING",
    current_stage: "OWNERSHIP",
    assigned_to: null,
    created_at: "2026-08-28T09:12:00+08:00",
    updated_at: "2026-08-28T09:15:00+08:00",
  },
  {
    case_id: COASTLINE_CASE_ID,
    requested_uen: "612345678",
    company_name: "Coastline Freight Pty Ltd",
    jurisdiction: "AU",
    status: "WAITING_FOR_REVIEW",
    current_stage: "OWNERSHIP",
    assigned_to: "J. Halloran",
    created_at: "2026-07-21T16:12:00+10:00",
    updated_at: "2026-08-28T10:04:00+10:00",
  },
  {
    case_id: "CLM-0396",
    requested_uen: "198802345H",
    company_name: "Telok Ayer Trading Pte Ltd",
    jurisdiction: "SG",
    status: "REWORK_REQUIRED",
    current_stage: "DOCUMENT",
    assigned_to: "L. Mercer",
    created_at: "2026-06-30T00:00:00+08:00",
    updated_at: "2026-08-28T00:00:00+08:00",
  },
  {
    case_id: "CLM-0418",
    requested_uen: "53298716M",
    company_name: "Kallang Metalworks LLP",
    jurisdiction: "SG",
    status: "COMPLETED",
    current_stage: "COMPLETE",
    assigned_to: null,
    created_at: "2026-08-04T00:00:00+08:00",
    updated_at: "2026-08-27T00:00:00+08:00",
  },
];

export const mockClients: ClientRecord[] = [
  {
    client_id: "AU-10428",
    case_id: COASTLINE_CASE_ID,
    company_name: "Coastline Freight Pty Ltd",
    jurisdiction: "AU",
    risk_rating: "MEDIUM",
    onboarded_at: "2026-08-28T11:58:00+10:00",
    next_review_date: "2027-08-28",
    re_screening_cadence_months: 1,
    loops_count: 2,
    human_touches: 1,
    elapsed_time_ms: 604_800_000,
    registration_id: "612 345 678",
    registration_id_label: "ACN",
    entity_type: "Australian Proprietary Company, limited by shares",
    registry_status: "Registered",
    registration_date: "04 Feb 2019",
    registered_address: "Level 9, 240 Queen Street, Brisbane QLD 4001",
    principal_place_of_business: "17 Export Drive, Pinkenba QLD 4008",
    financial_year_end: "30 June",
    tax_residency: "Australia",
    issued_capital: "AUD 1,200,000",
    issued_shares: "1,200,000 ordinary",
    principal_activity: "5212 — Freight forwarding",
    secondary_activity: "5309 — Port and water transport support",
    countries_of_operation: "Australia, Singapore, New Zealand",
    expected_annual_volume: "AUD 20–26 million",
    directors: [
      { name: "Tan Wei Lin", identification: "S8134●●●G", date_of_birth: "1981", appointed: "04 Feb 2019", source: "ASIC" },
      { name: "Priya Raghavan", identification: "M4088●●●P", date_of_birth: "1974", appointed: "02 Jun 2021", source: "Directors_ID_2026 p1" },
    ],
    beneficial_owners: [
      { owner: "Coastline Group Pty Ltd", holding: "74%", type: "Corporate", path: "Direct", source: "ASIC" },
      { owner: "R. Whitlam", holding: "41%", type: "Individual", path: "via Coastline Group", source: "Ownership provider" },
    ],
    relationship: {
      purpose: "Trade finance and FX settlement",
      source_of_funds: "Operating revenue",
      primary_contact: "D. Marchetti — Finance Director",
      contact_email: "finance@coastlinefreight.com.au",
      onboarded_by: "L. Mercer",
    },
    documents: [
      { name: "ASIC_extract.pdf", note: "ASIC" },
      { name: "Constitution.pdf", note: "3 values" },
      { name: "Directors_ID_2026.pdf", note: "current" },
      { name: "Directors_ID.pdf", note: "superseded" },
      { name: "Proof_of_address.pdf", note: "3 values" },
    ],
    onboarding_record: [
      { stage: "1 · Registry verification", method: "Automatic", cleared_at: "28 Aug, 11:49" },
      { stage: "2 · Document and data", method: "Automatic", cleared_at: "28 Aug, 11:50" },
      { stage: "3 · Screening", method: "Reviewed · J. Halloran", cleared_at: "28 Aug, 11:51" },
      { stage: "4 · Risk and approval", method: "Automatic", cleared_at: "28 Aug, 11:57" },
    ],
    check_results: [
      { check: "Registration ID format", outcome: "Pass" },
      { check: "Registry record match", outcome: "14 of 14" },
      { check: "Document completeness", outcome: "3 of 3" },
      { check: "Data consistency", outcome: "Resolved" },
      { check: "Director ID validity", outcome: "Valid to 2031" },
      { check: "Sanctions and PEP", outcome: "Cleared" },
      { check: "Adverse media", outcome: "Clear" },
      { check: "Risk classification", outcome: "Medium" },
    ],
    since_onboarding: [
      { date: "28 Aug 2026", event: "Monthly re-screening · clear" },
      { date: "28 Aug 2026", event: "Record written to the client database" },
    ],
  },
  {
    client_id: "SG-10419",
    case_id: "CLM-0361",
    company_name: "Anson Road Capital Pte Ltd",
    jurisdiction: "SG",
    risk_rating: "HIGH",
    onboarded_at: "2026-08-19T00:00:00+08:00",
    next_review_date: "2027-02-19",
    re_screening_cadence_months: 1,
    loops_count: 1,
    human_touches: 0,
    elapsed_time_ms: null,
    registration_id: "200912345R",
    registration_id_label: "UEN",
    entity_type: "Private Company Limited by Shares",
    registry_status: "Live",
    registration_date: "12 Mar 2009",
    registered_address: "1 Anson Road #18-01, Singapore 079909",
    principal_place_of_business: "1 Anson Road #18-01, Singapore 079909",
    financial_year_end: "31 December",
    tax_residency: "Singapore",
    issued_capital: "SGD 2,000,000",
    issued_shares: "2,000,000 ordinary",
    principal_activity: "64200 — Activities of holding companies",
    secondary_activity: null,
    countries_of_operation: "Singapore, Hong Kong",
    expected_annual_volume: "SGD 40–60 million",
    directors: [
      { name: "Ho Meng Kiat", identification: "S7522●●●F", date_of_birth: "1975", appointed: "12 Mar 2009", source: "ACRA" },
    ],
    beneficial_owners: [
      { owner: "Anson Holdings Ltd (HK)", holding: "88%", type: "Corporate", path: "Direct", source: "ACRA" },
    ],
    relationship: {
      purpose: "Investment holding and treasury",
      source_of_funds: "Shareholder capital",
      primary_contact: "Ho Meng Kiat — Director",
      contact_email: "meng.kiat@ansonroad.example",
      onboarded_by: "L. Mercer",
    },
    documents: [
      { name: "Bizfile_200912345R.pdf", note: "ACRA" },
      { name: "Constitution.pdf", note: "2 values" },
    ],
    onboarding_record: [
      { stage: "1 · Registry verification", method: "Automatic", cleared_at: "19 Aug, 09:10" },
      { stage: "2 · Document and data", method: "Automatic", cleared_at: "19 Aug, 09:12" },
      { stage: "3 · Screening", method: "Automatic", cleared_at: "19 Aug, 09:14" },
      { stage: "4 · Risk and approval", method: "Automatic", cleared_at: "19 Aug, 09:20" },
    ],
    check_results: [
      { check: "Registration ID format", outcome: "Pass" },
      { check: "Registry record match", outcome: "18 of 18" },
      { check: "Sanctions and PEP", outcome: "Cleared" },
      { check: "Risk classification", outcome: "High" },
    ],
    since_onboarding: [{ date: "19 Aug 2026", event: "Record written to the client database" }],
  },
  {
    client_id: "SG-10417",
    case_id: "CLM-0354",
    company_name: "Sembawang Marine Supplies Pte Ltd",
    jurisdiction: "SG",
    risk_rating: "LOW",
    onboarded_at: "2026-08-11T00:00:00+08:00",
    next_review_date: "2029-08-11",
    re_screening_cadence_months: 1,
    loops_count: 1,
    human_touches: 0,
    elapsed_time_ms: null,
    registration_id: "201422876W",
    registration_id_label: "UEN",
    entity_type: "Private Company Limited by Shares",
    registry_status: "Live",
    registration_date: "05 Jun 2014",
    registered_address: "12 Sembawang Way, Singapore 758462",
    principal_place_of_business: "12 Sembawang Way, Singapore 758462",
    financial_year_end: "31 December",
    tax_residency: "Singapore",
    issued_capital: "SGD 300,000",
    issued_shares: "300,000 ordinary",
    principal_activity: "46691 — Wholesale of marine equipment and supplies",
    secondary_activity: null,
    countries_of_operation: "Singapore",
    expected_annual_volume: "SGD 4–6 million",
    directors: [
      { name: "Lim Boon Huat", identification: "S8811●●●C", date_of_birth: "1988", appointed: "05 Jun 2014", source: "ACRA" },
    ],
    beneficial_owners: [
      { owner: "Lim Boon Huat", holding: "100%", type: "Individual", path: "Direct", source: "ACRA" },
    ],
    relationship: {
      purpose: "Trade finance",
      source_of_funds: "Operating revenue",
      primary_contact: "Lim Boon Huat — Director",
      contact_email: "boonhuat@sembawangmarine.example",
      onboarded_by: "L. Mercer",
    },
    documents: [{ name: "Bizfile_201422876W.pdf", note: "ACRA" }],
    onboarding_record: [
      { stage: "1 · Registry verification", method: "Automatic", cleared_at: "11 Aug, 10:02" },
      { stage: "2 · Document and data", method: "Automatic", cleared_at: "11 Aug, 10:04" },
      { stage: "3 · Screening", method: "Automatic", cleared_at: "11 Aug, 10:05" },
      { stage: "4 · Risk and approval", method: "Automatic", cleared_at: "11 Aug, 10:09" },
    ],
    check_results: [
      { check: "Registration ID format", outcome: "Pass" },
      { check: "Sanctions and PEP", outcome: "Cleared" },
      { check: "Risk classification", outcome: "Low" },
    ],
    since_onboarding: [{ date: "11 Aug 2026", event: "Record written to the client database" }],
  },
];

export const mockReviewers: Reviewer[] = [
  { reviewer_id: "j.halloran", display_name: "J. Halloran", open_exception_count: 3 },
  { reviewer_id: "a.devereux", display_name: "A. Devereux", open_exception_count: 5 },
  { reviewer_id: "m.okonkwo", display_name: "M. Okonkwo", open_exception_count: 1 },
  { reviewer_id: "s.kaur", display_name: "S. Kaur", open_exception_count: 0 },
];

export const mockAuditEntries: AuditEntry[] = [
  { entry_id: "1", case_id: COASTLINE_CASE_ID, timestamp: "2026-08-28T11:58:00+10:00", action: "COMPLETE", actor: "System", description: "Status Completed · client record AU-10428 written", loop_number: 2 },
  { entry_id: "2", case_id: COASTLINE_CASE_ID, timestamp: "2026-08-28T11:57:00+10:00", action: "APPROVE", actor: "System", description: "Stage 4 cleared · risk classification Medium", loop_number: 2 },
  { entry_id: "3", case_id: COASTLINE_CASE_ID, timestamp: "2026-08-28T11:51:00+10:00", action: "APPROVE", actor: "System", description: "Stage 3 cleared · PEP match resolved, date of birth 1974", loop_number: 2 },
  { entry_id: "4", case_id: COASTLINE_CASE_ID, timestamp: "2026-08-28T11:49:00+10:00", action: "SUBMIT", actor: "L. Mercer", description: "Resubmitted · pipeline restarted at stage 1", loop_number: 2 },
  { entry_id: "5", case_id: COASTLINE_CASE_ID, timestamp: "2026-08-28T11:20:00+10:00", action: "RETURN", actor: "J. Halloran", description: "Stage 3 returned · document insufficient · 2 items flagged", loop_number: 1 },
  { entry_id: "6", case_id: COASTLINE_CASE_ID, timestamp: "2026-08-28T10:41:00+10:00", action: "ASSIGN", actor: "L. Mercer", description: "Stage 3 exception assigned to J. Halloran", loop_number: 1 },
  { entry_id: "7", case_id: COASTLINE_CASE_ID, timestamp: "2026-07-21T16:12:00+10:00", action: "CREATE", actor: "L. Mercer", description: "Case created · ACN 612 345 678 · Australia", loop_number: 1 },
];

export const mockPolicy: PolicyResponse = {
  jurisdiction_rules: [
    { jurisdiction: "SG", implemented: true, id_label: "UEN", registry: "ACRA", ubo_threshold_percent: "25" },
    { jurisdiction: "AU", implemented: false, id_label: null, registry: null, ubo_threshold_percent: null },
    { jurisdiction: "MY", implemented: false, id_label: null, registry: null, ubo_threshold_percent: null },
    { jurisdiction: "HK", implemented: false, id_label: null, registry: null, ubo_threshold_percent: null },
  ],
  pipeline: {
    stages: ["REGISTRY", "DOCUMENT", "OWNERSHIP", "READINESS", "MOCK_GOLDTIER"],
    screening_auto_clear_threshold: 0.75,
    idp_review_confidence_threshold: 0.85,
    registry_snapshot_staleness_limit_days: 30,
    zero_touch_max_transitions_per_run: 12,
  },
  roles: { reviewer_count: mockReviewers.length, self_review_blocked: true },
  scheduler: {
    next_review_months_low: 36,
    next_review_months_medium: 12,
    next_review_months_high: 6,
    rescreening_cadence_months: 1,
  },
};

function buildMockZeroTouchSummary(options: {
  caseId: string;
  uen: string;
  legalName: string;
  jurisdiction: "SG" | "AU";
  status: ZeroTouchCaseSummary["status"];
  currentStage: ZeroTouchCaseSummary["current_stage"];
  completedStages: ZeroTouchCaseSummary["completed_stages"];
  withException: boolean;
}): ZeroTouchCaseSummary {
  const now = "2026-08-28T10:04:00+10:00";
  const onboardingCase: ZeroTouchCaseSummary["case"] = {
    case_id: options.caseId,
    source_case_id: options.caseId,
    correlation_id: options.caseId,
    requested_uen: options.uen,
    jurisdiction_resolution: {
      status: "RESOLVED",
      resolved_jurisdiction: options.jurisdiction,
      observations: [],
      resolved_at: now,
    },
    registry_route: {
      status: options.jurisdiction === "SG" ? "SELECTED" : "PROVIDER_NOT_IMPLEMENTED",
      jurisdiction: options.jurisdiction,
      provider: options.jurisdiction === "SG" ? "ACRA" : null,
      decided_at: now,
    },
    state: "VALIDATED",
    entity: {
      registration_number: options.uen,
      legal_name: options.legalName,
      country_of_incorporation: options.jurisdiction,
      party_type: options.jurisdiction === "SG" ? "Private Company Limited by Shares" : "Australian Proprietary Company",
      registration_date: "2018-03-14",
      entity_status: "Live",
      registered_address: {
        address_line_1: options.jurisdiction === "SG" ? "12 Marina View #23-01" : "Level 9, 240 Queen Street",
        address_line_2: null,
        postal_code: options.jurisdiction === "SG" ? "018961" : "4001",
        country_code: options.jurisdiction,
      },
      source: {
        source_system: "ACRA",
        environment: "MOCK",
        retrieved_at: now,
      },
    },
    registry_acquisition: {
      requested_identifier: options.uen,
      status: "COMPLETE",
      officers: [
        {
          officer_id: "officer-1",
          name: "Tan Wei Lin",
          role: "Director",
          appointment_date: "2018-03-14",
          cessation_date: null,
          country: options.jurisdiction,
          provenance: { provider: "ACRA", environment: "MOCK", operation: "OFFICERS", retrieved_at: now, evidence_reference: "mock-officer-1" },
        },
        {
          officer_id: "officer-2",
          name: "Priya Raghavan",
          role: "Director",
          appointment_date: "2021-06-02",
          cessation_date: null,
          country: "IN",
          provenance: { provider: "ACRA", environment: "MOCK", operation: "OFFICERS", retrieved_at: now, evidence_reference: "mock-officer-2" },
        },
      ],
      ownership_parties: [],
      relationships: [],
      operation_results: [],
      issues: [],
      retrieved_at: now,
    },
    goldtier_result: null,
    events: [],
    error: null,
    created_at: now,
    updated_at: now,
  };

  const clm: ZeroTouchCaseSummary["clm"] = {
    case: onboardingCase,
    orchestration_id: options.caseId,
    correlation_id: options.caseId,
    version: 3,
    status: options.status === "COMPLETED" ? "MOCK_GOLDTIER_SUBMITTED" : "REVIEW_REQUIRED",
    readiness: {
      policy_version: "PHASE_05_POC_V1",
      registry: { status: "READY", reference_id: null },
      document: { status: "READY", reference_id: null },
      ownership: { status: options.withException ? "REVIEW_REQUIRED" : "READY", reference_id: null },
      goldtier: { status: options.status === "COMPLETED" ? "SUBMITTED" : "NOT_SUBMITTED", reference_id: null },
      blockers: options.withException ? ["OWNERSHIP_REVIEW_REQUIRED"] : [],
      warnings: [],
      evaluated_at: now,
    },
    submission_plan: {
      environment: "MOCK",
      base_operations: ["search_party", "create_shell_customer", "create_policy", "amend_party"],
      match_found_behavior: "REVIEW_REQUIRED_NO_WRITES",
      related_party_integration: "PENDING_SPONSOR_CONFIRMATION",
      real_ready_for_approval: "NOT_AVAILABLE",
    },
    related_party_preparation: null,
    submission: null,
    goldtier_result: null,
    timeline: [],
    error: null,
    created_at: now,
    updated_at: now,
  };

  return {
    case: onboardingCase,
    clm,
    automation_id: options.caseId,
    version: 3,
    status: options.status,
    current_stage: options.currentStage,
    completed_stages: options.completedStages,
    loop_number: options.withException ? 2 : 1,
    loop_history: options.withException
      ? [{ loop_number: 1, completed_stages: ["REGISTRY", "DOCUMENT"], ended_at: "2026-08-28T11:20:00+10:00" }]
      : [],
    active_exceptions: options.withException
      ? [
          {
            exception_id: "exc-1",
            case_id: options.caseId,
            exception_type: "OWNERSHIP_REVIEW_REQUIRED",
            stage: "OWNERSHIP",
            status: "OPEN",
            blocker_code: "OWNERSHIP_REVIEW_REQUIRED",
            blocker_codes: ["OWNERSHIP_REVIEW_REQUIRED"],
            explanation:
              "Possible PEP match on a director, score 0.82, above the 0.75 auto-clear threshold. The date of birth on the register (1974) differs from the document (1979), and the document expired, so the divergence cannot be verified.",
            evidence_version: "ownership:exc-1:1",
            automation_version: 3,
            evidence: [
              {
                reference_id: "officer-2",
                field_key: "date_of_birth",
                registry_value: "1974",
                document_value: "1979",
                confidence: 0.82,
                comparison: "MISMATCH",
              },
            ],
            available_actions: ["ASSIGN_REVIEWER", "RETURN_FOR_REWORK", "CLEAR_AS_FALSE_POSITIVE"],
            created_at: now,
            resolved_at: null,
            resolution: null,
            assignee: "J. Halloran",
            rework_reason: null,
            rework_comment: null,
            flagged_fields: ["date_of_birth"],
            loop_number: 1,
          },
        ]
      : [],
    technical_failure: null,
    metrics: {
      automated_stages_completed: options.completedStages.length,
      human_interventions: options.withException ? 1 : 0,
      exceptions_raised: options.withException ? 1 : 0,
      exceptions_resolved: 0,
      final_outcome: options.status === "COMPLETED" ? "MOCK_GOLDTIER_SUBMITTED" : null,
      total_duration_ms: options.status === "COMPLETED" ? 604_800_000 : null,
      stage_durations_ms: {},
    },
    target_operations: [],
    timeline: [],
    created_at: now,
    updated_at: now,
  };
}

// TEMPORARY: session-only mock case store so the Home flow can be visualized
// end-to-end (create -> attach document -> exception) with no backend running.
// Not persisted, not authoritative -- discarded on page reload.
const mockSessionCases = new Map<string, ZeroTouchCaseSummary>();

export function createMockPendingCase(
  uen: string,
  jurisdiction: "" | "SG" | "AU" | "MY" | "HK",
): ZeroTouchCaseSummary {
  const caseId = `CLM-${Math.floor(1000 + Math.random() * 9000)}`;
  const summary = buildMockZeroTouchSummary({
    caseId,
    uen,
    legalName: uen,
    jurisdiction: jurisdiction === "AU" ? "AU" : "SG",
    status: "PENDING_INPUTS",
    currentStage: "DOCUMENT",
    completedStages: ["REGISTRY"],
    withException: false,
  });
  mockSessionCases.set(caseId, summary);
  return summary;
}

export function advanceMockCase(caseId: string): ZeroTouchCaseSummary | null {
  const current = mockSessionCases.get(caseId);
  if (!current) return null;
  const advanced: ZeroTouchCaseSummary = {
    ...current,
    status: "WAITING_FOR_REVIEW",
    current_stage: "OWNERSHIP",
    completed_stages: ["REGISTRY", "DOCUMENT"],
    active_exceptions: [
      {
        exception_id: `${caseId}-exc-1`,
        case_id: caseId,
        exception_type: "OWNERSHIP_REVIEW_REQUIRED",
        stage: "OWNERSHIP",
        status: "OPEN",
        blocker_code: "OWNERSHIP_REVIEW_REQUIRED",
        blocker_codes: ["OWNERSHIP_REVIEW_REQUIRED"],
        explanation:
          "Possible PEP match on a director, score 0.82, above the 0.75 auto-clear threshold. Needs a current identity document or a reviewer's judgement.",
        evidence_version: `ownership:${caseId}:1`,
        automation_version: current.version,
        evidence: [],
        available_actions: ["ASSIGN_REVIEWER", "RETURN_FOR_REWORK", "CLEAR_AS_FALSE_POSITIVE"],
        created_at: new Date().toISOString(),
        resolved_at: null,
        resolution: null,
        assignee: null,
        rework_reason: null,
        rework_comment: null,
        flagged_fields: [],
        loop_number: 1,
      },
    ],
    updated_at: new Date().toISOString(),
  };
  mockSessionCases.set(caseId, advanced);
  return advanced;
}

export function getMockSessionCase(caseId: string): ZeroTouchCaseSummary | null {
  return mockSessionCases.get(caseId) ?? mockZeroTouchSummaries[caseId] ?? null;
}

export const mockZeroTouchSummaries: Record<string, ZeroTouchCaseSummary> = {
  [MERIDIAN_CASE_ID]: buildMockZeroTouchSummary({
    caseId: MERIDIAN_CASE_ID,
    uen: "201834567K",
    legalName: "Meridian Trade Pte Ltd",
    jurisdiction: "SG",
    status: "RUNNING",
    currentStage: "OWNERSHIP",
    completedStages: ["REGISTRY", "DOCUMENT"],
    withException: false,
  }),
  [COASTLINE_CASE_ID]: buildMockZeroTouchSummary({
    caseId: COASTLINE_CASE_ID,
    uen: "612345678",
    legalName: "Coastline Freight Pty Ltd",
    jurisdiction: "AU",
    status: "WAITING_FOR_REVIEW",
    currentStage: "OWNERSHIP",
    completedStages: ["REGISTRY", "DOCUMENT"],
    withException: true,
  }),
};

// Seed the mutable session store with the static demo cases too, so acting on
// them (assign/return/clear/resubmit) from the Cases queue persists just like
// a freshly created case does.
for (const [caseId, caseSummary] of Object.entries(mockZeroTouchSummaries)) {
  if (!mockSessionCases.has(caseId)) mockSessionCases.set(caseId, caseSummary);
}

const COMPLETED_STAGES: ZeroTouchCaseSummary["completed_stages"] = [
  "REGISTRY",
  "DOCUMENT",
  "OWNERSHIP",
  "READINESS",
  "MOCK_GOLDTIER",
];

/** Resolves the given exception (any action) by clearing it and completing the case. */
export function resolveMockException(caseId: string): ZeroTouchCaseSummary | null {
  const current = mockSessionCases.get(caseId);
  if (!current) return null;
  const resolved: ZeroTouchCaseSummary = {
    ...current,
    status: "COMPLETED",
    current_stage: "COMPLETE",
    completed_stages: COMPLETED_STAGES,
    active_exceptions: [],
    metrics: {
      ...current.metrics,
      human_interventions: current.metrics.human_interventions + 1,
      exceptions_resolved: current.metrics.exceptions_resolved + 1,
      automated_stages_completed: COMPLETED_STAGES.length,
      final_outcome: "MOCK_GOLDTIER_SUBMITTED",
    },
    updated_at: new Date().toISOString(),
  };
  mockSessionCases.set(caseId, resolved);
  return resolved;
}

export function assignMockReviewer(
  caseId: string,
  exceptionId: string,
  reviewerId: string,
): ZeroTouchCaseSummary | null {
  const current = mockSessionCases.get(caseId);
  if (!current) return null;
  const reviewer = mockReviewers.find((item) => item.reviewer_id === reviewerId);
  const updated: ZeroTouchCaseSummary = {
    ...current,
    active_exceptions: current.active_exceptions.map((exception) =>
      exception.exception_id === exceptionId
        ? { ...exception, assignee: reviewer?.display_name ?? reviewerId }
        : exception,
    ),
    updated_at: new Date().toISOString(),
  };
  mockSessionCases.set(caseId, updated);
  return updated;
}

export function returnMockForRework(
  caseId: string,
  exceptionId: string,
  reason: string,
  comment: string,
  flaggedFields: string[],
): ZeroTouchCaseSummary | null {
  const current = mockSessionCases.get(caseId);
  if (!current) return null;
  const updated: ZeroTouchCaseSummary = {
    ...current,
    status: "REWORK_REQUIRED",
    active_exceptions: current.active_exceptions.map((exception) =>
      exception.exception_id === exceptionId
        ? { ...exception, rework_reason: reason, rework_comment: comment, flagged_fields: flaggedFields }
        : exception,
    ),
    updated_at: new Date().toISOString(),
  };
  mockSessionCases.set(caseId, updated);
  return updated;
}

export function resubmitMockCase(caseId: string): ZeroTouchCaseSummary | null {
  const current = mockSessionCases.get(caseId);
  if (!current) return null;
  const resubmitted: ZeroTouchCaseSummary = {
    ...current,
    status: "COMPLETED",
    current_stage: "COMPLETE",
    completed_stages: COMPLETED_STAGES,
    loop_number: current.loop_number + 1,
    loop_history: [
      ...current.loop_history,
      {
        loop_number: current.loop_number,
        completed_stages: current.completed_stages,
        ended_at: new Date().toISOString(),
      },
    ],
    active_exceptions: [],
    metrics: {
      ...current.metrics,
      exceptions_resolved: current.metrics.exceptions_resolved + current.active_exceptions.length,
      automated_stages_completed: COMPLETED_STAGES.length,
      final_outcome: "MOCK_GOLDTIER_SUBMITTED",
    },
    updated_at: new Date().toISOString(),
  };
  mockSessionCases.set(caseId, resubmitted);
  return resubmitted;
}
