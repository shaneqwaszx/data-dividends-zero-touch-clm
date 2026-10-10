import type { ReviewDecisionBatch } from "./types";
import { nextPollingDelay } from "./automationPolling";
import type {
  AuthSession,
  CasePriorityResult,
  ClmCaseSummary,
  DocumentProcessingRecord,
  DashboardSnapshot,
  DocumentFieldKey,
  MockIdpScenario,
  MockOwnershipScenario,
  MockScenarioDiscovery,
  OnboardingCase,
  OwnershipAnalysisRecord,
  ReviewDecision,
  ReconciliationDecisionAction,
  ExceptionResolutionAction,
  ZeroTouchCaseSummary,
  BusinessExceptionType,
  ZeroTouchCaseListItem,
  ZeroTouchDemoScenario,
  SimulationProfile,
  UatEvidenceExport,
  TeamId,
  AuthenticatedTeam,
  AdminTeam,
  AdminProfile,
  PolicyCatalogue,
  PolicyImpact,
  ClassifierBenchmark,
  PolicyAuthority,
  PolicyValue,
  Role,
  AutomationStage,
  CaseActivityAction,
  CaseActivityPage,
  CasePortfolioPage,
  EventOutcome,
  OnboardingIntelligenceRecord,
  GoldTierSandboxStatus,
  GoldTierSandboxSearchInput,
  GoldTierSandboxSearchResult,
  GoldTierSandboxDryRunInput,
  GoldTierSandboxDryRunResult,
  AcraDiagnosticOperation,
  AcraDiagnosticResult,
  AcraDiagnosticStatus,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
let activeCsrfToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;
let authenticatedTransportGeneration = 0;

export function configureAuthenticatedTransport(options: {
  csrfToken: string | null;
  onUnauthorized: (() => void) | null;
}): void {
  authenticatedTransportGeneration += 1;
  activeCsrfToken = options.csrfToken;
  unauthorizedHandler = options.onUnauthorized;
}

async function fetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const requestTransportGeneration = authenticatedTransportGeneration;
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && activeCsrfToken) {
    headers.set("X-CSRF-Token", activeCsrfToken);
  }
  const response = await globalThis.fetch(input, {
    ...init,
    headers,
    credentials: "include",
  });
  if (
    response.status === 401
    && requestTransportGeneration === authenticatedTransportGeneration
  ) {
    unauthorizedHandler?.();
  }
  return response;
}

// Reuse the session owner for read-only consumers such as Copilot.
export { fetch as authenticatedFetch };

export async function login(userId: string, credential: string): Promise<AuthSession> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, "password": credential }),
  });
  return parseResponse<AuthSession>(response);
}

export async function fetchCurrentSession(): Promise<AuthSession> {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`);
  return parseResponse<AuthSession>(response);
}

export async function logout(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/auth/logout`, { method: "POST" });
  if (!response.ok) await parseResponse<never>(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let code: string | null = null;
    let message = `Application API request failed (${response.status}).`;
    let detail: ApiErrorDetail | null = null;
    try {
      const payload = (await response.json()) as {
        detail?: ApiErrorDetail | string;
      };
      if (typeof payload.detail === "object" && payload.detail) {
        code = payload.detail.code ?? null;
        message = payload.detail.message ?? message;
        detail = payload.detail;
      }
    } catch {
      // Preserve the fixed local fallback; never project response bodies.
    }
    throw new ApiError(message, response.status, code, detail);
  }
  return (await response.json()) as T;
}

export interface ApiErrorDetail {
  code?: string;
  message?: string;
  case_id?: string;
  document_id?: string;
  correlation_id?: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string | null,
    readonly detail: ApiErrorDetail | null = null,
  ) {
    super(message);
  }
}

export async function createZeroTouchCase(
  uen: string,
  demoScenario?: ZeroTouchDemoScenario,
  countryOfIncorporation?: "SG" | "AU" | "MY" | "HK",
  teamId?: TeamId,
  priority?: number | null,
  legalName?: string,
): Promise<ZeroTouchCaseSummary> {
  const demo = demoScenario !== undefined;
  const response = await fetch(
    `${API_BASE_URL}${demo ? "/api/demo" : "/api"}/clm/zero-touch/cases`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        uen,
        ...(countryOfIncorporation
          ? { country_of_incorporation: countryOfIncorporation }
          : {}),
        ...(legalName ? { legal_name: legalName } : {}),
        ...(demo ? { scenario: demoScenario } : {}),
        ...(teamId ? { team_id: teamId } : {}),
        ...(priority !== undefined && priority !== null ? { priority } : {}),
      }),
    },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export async function updateCasePriority(
  caseId: string,
  priority: number | null,
): Promise<CasePriorityResult> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/priority`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ priority }),
    },
  );
  return parseResponse<CasePriorityResult>(response);
}

export async function deleteZeroTouchCase(caseId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}`, {
    method: "DELETE",
  });
  if (!response.ok) await parseResponse<never>(response);
}

export async function fetchIntelligence(
  caseId: string,
  signal?: AbortSignal,
): Promise<OnboardingIntelligenceRecord | null> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/intelligence`,
    { signal },
  );
  if (response.status === 404) return null;
  return parseResponse<OnboardingIntelligenceRecord>(response);
}

export async function attachZeroTouchDocument(
  caseId: string,
  file: File,
  demo: boolean,
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}${demo ? "/api/demo" : "/api"}/clm/zero-touch/cases/${caseId}/documents`,
    {
      method: "POST",
      headers: {
        "Content-Type": file.type || "application/pdf",
        "X-Document-Name": file.name,
      },
      body: file,
    },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export async function intakeZeroTouchDocument(
  caseId: string,
  file: File,
  demo: boolean,
): Promise<DocumentProcessingRecord> {
  const diagnosticRequestId = import.meta.env.VITE_E2E_DIAGNOSTICS === "1"
    ? crypto.randomUUID()
    : null;
  const diagnosticMilestone = (milestone: string, status?: number) => {
    if (!diagnosticRequestId) return;
    console.info("E2E_DIAG", JSON.stringify({
      milestone,
      request_id: diagnosticRequestId,
      method: "POST",
      route_family: "/api[/demo]/clm/zero-touch/cases/{case_id}/intake/documents",
      case_id: caseId,
      monotonic_ms: Math.round(performance.now()),
      ...(status === undefined ? {} : { status }),
    }));
  };
  diagnosticMilestone("BROWSER_UPLOAD_DISPATCHED");
  const response = await fetch(
    `${API_BASE_URL}${demo ? "/api/demo" : "/api"}/clm/zero-touch/cases/${caseId}/intake/documents`,
    {
      method: "POST",
      headers: {
        "Content-Type": file.type,
        "X-Document-Name": file.name,
        ...(diagnosticRequestId ? { "X-E2E-Request-ID": diagnosticRequestId } : {}),
      },
      body: file,
    },
  );
  diagnosticMilestone("BROWSER_UPLOAD_RESPONSE_HEADERS", response.status);
  const record = await parseResponse<DocumentProcessingRecord>(response);
  diagnosticMilestone("BROWSER_UPLOAD_RESPONSE_COMPLETE", response.status);
  return record;
}

export async function retryZeroTouchIntakeDocument(
  caseId: string,
  failedDocumentId: string,
  file: File,
  demo: boolean,
): Promise<DocumentProcessingRecord> {
  const response = await fetch(
    `${API_BASE_URL}${demo ? "/api/demo" : "/api"}/clm/zero-touch/cases/${caseId}/intake/documents/${failedDocumentId}/retry`,
    {
      method: "POST",
      headers: {
        "Content-Type": file.type,
        "X-Document-Name": file.name,
      },
      body: file,
    },
  );
  return parseResponse<DocumentProcessingRecord>(response);
}

export async function completeZeroTouchIntake(
  caseId: string,
  expectedDocumentCount: number,
  demo: boolean,
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}${demo ? "/api/demo" : "/api"}/clm/zero-touch/cases/${caseId}/intake/complete`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_document_count: expectedDocumentCount }),
    },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export type PriorityFilter = "all" | "prioritised" | "unset" | `${1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10}`;
export type PrioritySort = "highest_first" | "lowest_first";

export interface CasePortfolioFilters {
  status?: ZeroTouchCaseListItem["status"];
  priority: PriorityFilter;
  prioritySort: PrioritySort;
  teamFilter?: string;
  attentionType?: BusinessExceptionType;
  jurisdiction?: "SG" | "AU" | "MY" | "HK";
  search?: string;
  createdFrom?: string;
  createdTo?: string;
  limit?: number;
  offset?: number;
}

export async function fetchCasePortfolio(
  filters: CasePortfolioFilters,
  signal?: AbortSignal,
): Promise<CasePortfolioPage> {
  const query = new URLSearchParams();
  if (filters.status) query.set("status", filters.status);
  if (filters.priority !== "all") query.set("priority_filter", filters.priority);
  if (filters.prioritySort !== "highest_first") {
    query.set("priority_sort", filters.prioritySort);
  }
  if (filters.teamFilter && filters.teamFilter !== "all") {
    query.set("team_filter", filters.teamFilter);
  }
  if (filters.attentionType) query.set("attention_type", filters.attentionType);
  if (filters.jurisdiction) query.set("jurisdiction", filters.jurisdiction);
  if (filters.createdFrom) query.set("created_from", filters.createdFrom);
  if (filters.createdTo) query.set("created_to", filters.createdTo);
  const normalizedSearch = filters.search?.trim();
  if (normalizedSearch) query.set("search", normalizedSearch);
  if (filters.limit !== undefined && filters.limit !== 50) {
    query.set("limit", String(filters.limit));
  }
  if (filters.offset !== undefined && filters.offset !== 0) {
    query.set("offset", String(filters.offset));
  }
  const suffix = query.size ? `?${query.toString()}` : "";
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/case-portfolio${suffix}`,
    { signal },
  );
  return parseResponse<CasePortfolioPage>(response);
}

export interface CaseActivityFilters {
  caseId?: string;
  teamFilter?: string;
  action?: CaseActivityAction;
  stage?: AutomationStage;
  outcome?: EventOutcome;
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}

function caseActivityQuery(filters: CaseActivityFilters, explicitPaging: boolean): string {
  const query = new URLSearchParams();
  if (filters.caseId) query.set("case_id", filters.caseId);
  if (filters.teamFilter && filters.teamFilter !== "all") {
    query.set("team_filter", filters.teamFilter);
  }
  if (filters.action) query.set("action", filters.action);
  if (filters.stage) query.set("stage", filters.stage);
  if (filters.outcome) query.set("outcome", filters.outcome);
  if (filters.from) query.set("from", filters.from);
  if (filters.to) query.set("to", filters.to);
  if (filters.limit !== undefined && (explicitPaging || filters.limit !== 50)) {
    query.set("limit", String(filters.limit));
  }
  if (filters.offset !== undefined && (explicitPaging || filters.offset !== 0)) {
    query.set("offset", String(filters.offset));
  }
  return query.size ? `?${query.toString()}` : "";
}

export function caseActivityExportUrl(filters: CaseActivityFilters): string {
  return `${API_BASE_URL}/api/clm/zero-touch/activity.csv${caseActivityQuery(filters, true)}`;
}

export async function fetchCaseActivity(
  filters: CaseActivityFilters,
  signal?: AbortSignal,
): Promise<CaseActivityPage> {
  const suffix = caseActivityQuery(filters, false);
  const response = await fetch(`${API_BASE_URL}/api/clm/zero-touch/activity${suffix}`, {
    signal,
  });
  return parseResponse<CaseActivityPage>(response);
}

export async function fetchZeroTouchCases(
  status?: ZeroTouchCaseListItem["status"],
  priority: PriorityFilter = "all",
  prioritySort: PrioritySort = "highest_first",
  teamFilter?: string,
  signal?: AbortSignal,
  attentionType?: BusinessExceptionType,
  createdFrom?: string,
  createdTo?: string,
): Promise<ZeroTouchCaseListItem[]> {
  const query = new URLSearchParams();
  if (status) query.set("status", status);
  if (priority !== "all") query.set("priority_filter", priority);
  if (prioritySort !== "highest_first") query.set("priority_sort", prioritySort);
  if (teamFilter && teamFilter !== "all") query.set("team_filter", teamFilter);
  if (attentionType) query.set("attention_type", attentionType);
  if (createdFrom) query.set("created_from", createdFrom);
  if (createdTo) query.set("created_to", createdTo);
  const suffix = query.size ? `?${query.toString()}` : "";
  const response = await fetch(`${API_BASE_URL}/api/clm/zero-touch/cases${suffix}`, { signal });
  return parseResponse<ZeroTouchCaseListItem[]>(response);
}

export async function fetchDashboard(teamFilter?: string, signal?: AbortSignal): Promise<DashboardSnapshot> {
  const query = teamFilter && teamFilter !== "all"
    ? `?team_filter=${encodeURIComponent(teamFilter)}`
    : "";
  const response = await fetch(`${API_BASE_URL}/api/clm/zero-touch/dashboard${query}`, { signal });
  return parseResponse<DashboardSnapshot>(response);
}

export async function replaceZeroTouchDocument(
  caseId: string,
  documentId: string,
  eventCount: number,
  file: File,
  context?: ZeroTouchCaseSummary,
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/documents/${documentId}/replacement`,
    {
      method: "POST",
      headers: {
        "Content-Type": file.type || "application/pdf",
        "X-Document-Name": file.name,
        "X-Document-Event-Count": String(eventCount),
        ...(context ? {
          "X-Automation-Version": String(context.version),
          "X-Clm-Version": String(context.clm.version),
          "X-Case-Event-Count": String(context.case.events.length),
        } : {}),
      },
      body: file,
    },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export async function fetchZeroTouchCase(
  caseId: string,
  signal?: AbortSignal,
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}`,
    { signal },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export async function fetchExecutionProfile(signal?: AbortSignal): Promise<SimulationProfile> {
  const response = await fetch(`${API_BASE_URL}/api/system/execution-profile`, { signal });
  return parseResponse<SimulationProfile>(response);
}

export async function fetchGoldTierSandboxStatus(
  signal?: AbortSignal,
): Promise<GoldTierSandboxStatus> {
  const response = await fetch(`${API_BASE_URL}/api/admin/goldtier-sandbox/status`, { signal });
  return parseResponse<GoldTierSandboxStatus>(response);
}

export async function searchGoldTierSandbox(
  input: GoldTierSandboxSearchInput,
): Promise<GoldTierSandboxSearchResult> {
  const response = await fetch(`${API_BASE_URL}/api/admin/goldtier-sandbox/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<GoldTierSandboxSearchResult>(response);
}

export async function dryRunGoldTierSandbox(
  input: GoldTierSandboxDryRunInput,
): Promise<GoldTierSandboxDryRunResult> {
  const response = await fetch(`${API_BASE_URL}/api/admin/goldtier-sandbox/dry-run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<GoldTierSandboxDryRunResult>(response);
}

export async function resumeZeroTouchCase(caseId: string): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/resume`,
    { method: "POST" },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export async function updateGoldTierTargetClassification(
  caseId: string,
  input: {
    kyc_customer_type: string;
    client_segment: string;
    expected_automation_version: number;
    expected_case_event_count: number;
    expected_classification_evidence_fingerprint?: string | null;
  },
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/target-classification`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export async function fetchAcraDiagnosticStatus(
  signal?: AbortSignal,
): Promise<AcraDiagnosticStatus> {
  const response = await fetch(`${API_BASE_URL}/api/admin/acra/status`, { signal });
  return parseResponse<AcraDiagnosticStatus>(response);
}

export async function lookupAcraDiagnostic(
  input: { uen: string; operation: AcraDiagnosticOperation },
  signal?: AbortSignal,
): Promise<AcraDiagnosticResult> {
  const response = await fetch(`${API_BASE_URL}/api/admin/acra/lookup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal,
  });
  return parseResponse<AcraDiagnosticResult>(response);
}

export interface TargetDispatchConfirmationInput {
  expected_automation_version: number;
  expected_clm_version: number;
  expected_case_event_count: number;
}

export async function confirmZeroTouchTargetDispatch(
  caseId: string,
  input: TargetDispatchConfirmationInput,
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/target-confirmation`,
    {
      method: "POST",
      // Stop waiting for a missing response; CaseDetail observes retained state, never reposts.
      signal: AbortSignal.timeout(nextPollingDelay(3)),
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export interface IdentitySearchRecheckInput {
  legal_name: string;
  registration_number: string;
  country_of_incorporation: "SG";
  expected_automation_version: number;
  expected_clm_version: number;
  expected_case_event_count: number;
}

export interface TargetStatusCheckResult {
  submission_id: string;
  checked_at: string;
  verified_party_id?: string | null;
  result: "NO_MATCH" | "IDENTITY_UNVERIFIED" | "CUSTOMER_IDENTITY_VERIFIED"
    | "AMBIGUOUS" | "CHECK_FAILED";
  message: string;
}

export interface CompletedTargetVerificationResult {
  submission_id: string;
  goldtier_id: string;
  checked_at: string;
  result: "VERIFIED" | "REQUIRES_REVIEW" | "UNAVAILABLE";
  legal_name: string | null;
  registration_number: string | null;
  country: string | null;
}

export type TargetSearchObservation = TargetStatusCheckResult | CompletedTargetVerificationResult;

export interface TargetRecoveryInput {
  expected_submission_id: string;
  operation: "SHELL" | "POLICY";
  recovered_party_id: string;
  origin: "UNCERTAIN_DURABLE_LEDGER";
  provider_policy?: string;
  provider_policy_status?: "Requested";
}

export async function recoverZeroTouchTarget(
  caseId: string, input: TargetRecoveryInput,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/target-recovery`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) },
  );
  await parseResponse<unknown>(response);
}

export async function verifyCompletedGoldTier(
  caseId: string, submissionId: string, signal?: AbortSignal,
): Promise<CompletedTargetVerificationResult> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/verify-goldtier`,
    {
      method: "POST", signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_submission_id: submissionId }),
    },
  );
  return parseResponse<CompletedTargetVerificationResult>(response);
}

export async function checkZeroTouchTargetStatus(
  caseId: string, submissionId: string, signal?: AbortSignal,
): Promise<TargetStatusCheckResult> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/target-status-check`,
    {
      method: "POST", signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_submission_id: submissionId }),
    },
  );
  return parseResponse<TargetStatusCheckResult>(response);
}

export async function confirmExistingGoldTierCustomer(
  summary: ZeroTouchCaseSummary, rationale: string,
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${summary.case.case_id}/confirm-existing-customer`,
    {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        search_request_id: summary.clm.target_search_checkpoint?.request_id,
        expected_automation_version: summary.version,
        expected_clm_version: summary.clm.version,
        expected_case_event_count: summary.case.events.length,
        rationale,
      }),
    },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export async function recheckZeroTouchIdentitySearch(
  caseId: string,
  input: IdentitySearchRecheckInput,
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/identity-search-recheck`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export async function correctRegistryIdentity(
  caseId: string, input: IdentitySearchRecheckInput & {
    choice: "ENTERED" | "DOCUMENT" | "OTHER";
    document_id?: string; expected_document_event_count?: number;
  },
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(`${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/registry-identity`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
  });
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export interface ManualOwnershipEvidenceInput {
  source_selection?: "USER_SUPPLIED_DECLARATION" | "CURRENT_EVIDENCE" | "DOCUMENT_OBSERVATIONS";
  observed_document_versions?: Array<{ document_id: string; event_count: number }>;
  selected_observation_ids?: string[];
  root_registration_number: string;
  evidence_document_id: string;
  evidence_document_version: number;
  as_of_date: string;
  rationale?: string | null;
  root_party_id: string;
  parties: Array<{
    party_id: string;
    display_name: string;
    party_type: "LEGAL_ENTITY" | "NATURAL_PERSON";
    registration_number: string | null;
    country: string | null;
  }>;
  relationships: Array<{
    relationship_id: string;
    parent_party_id: string;
    child_party_id: string;
    ownership_percent: string;
    relationship_type: "DIRECT_ECONOMIC_INTEREST";
  }>;
  expected_automation_version: number;
  expected_ownership_version: number;
  expected_case_event_count: number;
}

export async function submitManualOwnershipEvidence(
  caseId: string,
  input: ManualOwnershipEvidenceInput,
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/manual-ownership-evidence`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export interface PolicyRebindInput {
  rationale: string;
  expected_automation_version: number;
  expected_clm_version: number;
  expected_case_event_count: number;
}

export async function rebindZeroTouchPolicy(
  caseId: string,
  input: PolicyRebindInput,
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/policy-rebind`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export async function fetchUatEvidence(caseId: string): Promise<UatEvidenceExport> {
  const response = await fetch(
    `${API_BASE_URL}/api/demo/clm/zero-touch/cases/${caseId}/uat-evidence`,
  );
  return parseResponse<UatEvidenceExport>(response);
}

export async function resolveZeroTouchException(
  summary: ZeroTouchCaseSummary,
  exceptionId: string,
  action: ExceptionResolutionAction,
  evidenceVersion: string,
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${summary.case.case_id}/exceptions/${exceptionId}/resolve`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        expected_automation_version: summary.version,
        evidence_version: evidenceVersion,
      }),
    },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export async function resolveReconciliationDiscrepancy(
  summary: ZeroTouchCaseSummary,
  discrepancyId: string,
  action: ReconciliationDecisionAction,
  reconciliationVersion: number,
  evidenceFingerprint: string,
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${summary.case.case_id}/reconciliation/discrepancies/${discrepancyId}/resolve`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        expected_automation_version: summary.version,
        expected_reconciliation_version: reconciliationVersion,
        evidence_fingerprint: evidenceFingerprint,
      }),
    },
  );
  return parseResponse<ZeroTouchCaseSummary>(response);
}

export async function fetchMockScenarios(): Promise<MockScenarioDiscovery> {
  const response = await fetch(`${API_BASE_URL}/api/onboarding/mock-scenarios`);
  return parseResponse<MockScenarioDiscovery>(response);
}

export async function createOnboardingCase(
  uen: string,
  countryOfIncorporation?: "SG" | "AU" | "MY" | "HK",
): Promise<OnboardingCase> {
  const response = await fetch(`${API_BASE_URL}/api/onboarding/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      uen,
      ...(countryOfIncorporation
        ? { country_of_incorporation: countryOfIncorporation }
        : {}),
    }),
  });
  return parseResponse<OnboardingCase>(response);
}

export async function fetchOnboardingCase(caseId: string): Promise<OnboardingCase> {
  const response = await fetch(`${API_BASE_URL}/api/onboarding/cases/${caseId}`);
  return parseResponse<OnboardingCase>(response);
}

export async function createClmCase(
  uen: string,
  countryOfIncorporation?: "SG" | "AU" | "MY" | "HK",
): Promise<ClmCaseSummary> {
  const response = await fetch(`${API_BASE_URL}/api/clm/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      uen,
      ...(countryOfIncorporation
        ? { country_of_incorporation: countryOfIncorporation }
        : {}),
    }),
  });
  return parseResponse<ClmCaseSummary>(response);
}

export async function fetchClmCase(caseId: string): Promise<ClmCaseSummary> {
  const response = await fetch(`${API_BASE_URL}/api/clm/cases/${caseId}`);
  return parseResponse<ClmCaseSummary>(response);
}

export async function evaluateClmReadiness(caseId: string): Promise<ClmCaseSummary> {
  const response = await fetch(`${API_BASE_URL}/api/clm/cases/${caseId}/readiness/evaluate`, {
    method: "POST",
  });
  return parseResponse<ClmCaseSummary>(response);
}

export async function submitClmCase(caseId: string): Promise<ClmCaseSummary> {
  const response = await fetch(`${API_BASE_URL}/api/clm/cases/${caseId}/submit`, {
    method: "POST",
  });
  return parseResponse<ClmCaseSummary>(response);
}

export async function fetchDocuments(
  caseId: string,
  signal?: AbortSignal,
): Promise<DocumentProcessingRecord[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/onboarding/cases/${caseId}/documents`,
    { signal },
  );
  return parseResponse<DocumentProcessingRecord[]>(response);
}

export async function uploadDocument(
  caseId: string,
  file: File,
  scenario: MockIdpScenario,
): Promise<DocumentProcessingRecord> {
  const response = await fetch(`${API_BASE_URL}/api/demo/onboarding/cases/${caseId}/documents`, {
    method: "POST",
    headers: {
      "Content-Type": file.type || "application/pdf",
      "X-Document-Name": file.name,
      "X-Mock-IDP-Scenario": scenario,
    },
    body: file,
  });
  return parseResponse<DocumentProcessingRecord>(response);
}

export async function reviewDocument(
  caseId: string,
  documentId: string,
  fieldKey: DocumentFieldKey,
  decision: ReviewDecision,
  correctedValue?: string,
  note?: string,
): Promise<DocumentProcessingRecord> {
  const response = await fetch(
    `${API_BASE_URL}/api/onboarding/cases/${caseId}/documents/${documentId}/reviews`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        field_key: fieldKey,
        decision,
        ...(correctedValue ? { corrected_value: correctedValue } : {}),
        ...(note ? { note } : {}),
      }),
    },
  );
  return parseResponse<DocumentProcessingRecord>(response);
}

export async function fetchOwnership(
  caseId: string,
  signal?: AbortSignal,
): Promise<OwnershipAnalysisRecord | null> {
  const response = await fetch(
    `${API_BASE_URL}/api/onboarding/cases/${caseId}/ownership`,
    { signal },
  );
  if (response.status === 404) return null;
  return parseResponse<OwnershipAnalysisRecord>(response);
}

export async function loadMockOwnership(
  caseId: string,
  scenario: MockOwnershipScenario,
): Promise<OwnershipAnalysisRecord> {
  const response = await fetch(
    `${API_BASE_URL}/api/demo/onboarding/cases/${caseId}/ownership/load`,
    {
      method: "POST",
      headers: { "X-Mock-Ownership-Scenario": scenario },
    },
  );
  return parseResponse<OwnershipAnalysisRecord>(response);
}

export async function analyzeOwnership(caseId: string): Promise<OwnershipAnalysisRecord> {
  const response = await fetch(
    `${API_BASE_URL}/api/onboarding/cases/${caseId}/ownership/analyze`,
    { method: "POST" },
  );
  return parseResponse<OwnershipAnalysisRecord>(response);
}

export async function fetchTeamOptions(): Promise<AuthenticatedTeam[]> {
  return parseResponse<AuthenticatedTeam[]>(await fetch(`${API_BASE_URL}/api/teams/options`));
}

export async function fetchAdminTeams(): Promise<AdminTeam[]> {
  return parseResponse<AdminTeam[]>(await fetch(`${API_BASE_URL}/api/admin/teams`));
}

export async function createAdminTeam(input: {
  display_name: string;
  client_scope_label: string;
  description?: string;
}): Promise<AdminTeam> {
  const response = await fetch(`${API_BASE_URL}/api/admin/teams`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<AdminTeam>(response);
}

export async function updateAdminTeam(
  teamId: TeamId,
  input: { expected_version: number; display_name?: string; client_scope_label?: string; description?: string | null },
): Promise<AdminTeam> {
  const response = await fetch(`${API_BASE_URL}/api/admin/teams/${encodeURIComponent(teamId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<AdminTeam>(response);
}

export async function fetchAdminProfiles(): Promise<AdminProfile[]> {
  return parseResponse<AdminProfile[]>(await fetch(`${API_BASE_URL}/api/admin/profiles`));
}

export async function createAdminProfile(input: {
  user_id: string;
  display_name: string;
  role: Role;
  team_id: TeamId | null;
  password: string;
}): Promise<AdminProfile> {
  const response = await fetch(`${API_BASE_URL}/api/admin/profiles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<AdminProfile>(response);
}

export async function updateAdminProfile(
  userId: string,
  input: { expected_version: number; display_name?: string; role?: Role; team_id?: TeamId | null },
): Promise<AdminProfile> {
  const response = await fetch(`${API_BASE_URL}/api/admin/profiles/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<AdminProfile>(response);
}

export async function fetchPolicies(signal?: AbortSignal): Promise<PolicyCatalogue> {
  return parseResponse<PolicyCatalogue>(await fetch(`${API_BASE_URL}/api/policies`, { signal }));
}

export async function createShowcasePolicy(input: {
  expected_catalogue_version: number;
  policy_id: string;
  category: string;
  name: string;
  description: string;
  value: PolicyValue;
}): Promise<PolicyCatalogue> {
  const response = await fetch(`${API_BASE_URL}/api/policies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<PolicyCatalogue>(response);
}

export async function updatePolicy(
  policyId: string,
  input: {
    expected_catalogue_version: number;
    expected_rule_version: number;
    value: PolicyValue;
    name?: string;
    description?: string;
    authority?: PolicyAuthority;
  },
): Promise<PolicyCatalogue> {
  const response = await fetch(`${API_BASE_URL}/api/policies/${encodeURIComponent(policyId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<PolicyCatalogue>(response);
}

export async function resetPolicy(
  policyId: string,
  catalogueVersion: number,
  ruleVersion: number,
): Promise<PolicyCatalogue> {
  const response = await fetch(`${API_BASE_URL}/api/policies/${encodeURIComponent(policyId)}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      expected_catalogue_version: catalogueVersion,
      expected_rule_version: ruleVersion,
      confirmation: "RESET_POLICY_DEFAULT",
    }),
  });
  return parseResponse<PolicyCatalogue>(response);
}

export async function resetAllPolicies(catalogueVersion: number): Promise<PolicyCatalogue> {
  const response = await fetch(`${API_BASE_URL}/api/policies/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      expected_catalogue_version: catalogueVersion,
      confirmation: "RESET_ALL_POLICY_DEFAULTS",
    }),
  });
  return parseResponse<PolicyCatalogue>(response);
}

export interface PolicyProposalInput {
  expected_catalogue_version: number; changes: Record<string, PolicyValue>;
  reset_ids?: string[]; reason: string; expected_proposal_version?: number;
}
export async function savePolicyProposal(input: PolicyProposalInput, proposalId?: string): Promise<PolicyCatalogue> {
  return parseResponse<PolicyCatalogue>(await fetch(`${API_BASE_URL}/api/policies/proposals${proposalId ? `/${encodeURIComponent(proposalId)}` : ""}`, {
    method: proposalId ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
  }));
}
export async function submitPolicyProposal(proposalId: string, catalogueVersion: number, proposalVersion: number): Promise<PolicyCatalogue> {
  return parseResponse<PolicyCatalogue>(await fetch(`${API_BASE_URL}/api/policies/proposals/${encodeURIComponent(proposalId)}/submit`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ expected_catalogue_version: catalogueVersion, expected_proposal_version: proposalVersion }),
  }));
}
export async function decidePolicyProposal(proposalId: string, catalogueVersion: number, proposalVersion: number, approve: boolean, reason: string): Promise<PolicyCatalogue> {
  return parseResponse<PolicyCatalogue>(await fetch(`${API_BASE_URL}/api/policies/proposals/${encodeURIComponent(proposalId)}/decision`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ expected_catalogue_version: catalogueVersion, expected_proposal_version: proposalVersion, approve, reason }),
  }));
}
export async function fetchPolicyImpact(proposalId: string, signal?: AbortSignal): Promise<PolicyImpact> {
  return parseResponse<PolicyImpact>(await fetch(`${API_BASE_URL}/api/policies/proposals/${encodeURIComponent(proposalId)}/impact`, { signal }));
}
export async function fetchClassifierBenchmark(signal?: AbortSignal): Promise<ClassifierBenchmark> {
  return parseResponse<ClassifierBenchmark>(await fetch(`${API_BASE_URL}/api/policies/classifier-benchmark`, { signal }));
}

export async function confirmReviewDecisions(caseId: string, batch: ReviewDecisionBatch): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(`${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/review-decisions`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(batch),
  });
  return parseResponse<ZeroTouchCaseSummary>(response);
}
