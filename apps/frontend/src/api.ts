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
  ZeroTouchCaseListItem,
  ZeroTouchDemoScenario,
  SimulationProfile,
  UatEvidenceExport,
  TeamId,
  AuthenticatedTeam,
  AdminTeam,
  AdminProfile,
  PolicyCatalogue,
  PolicyValue,
  Role,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
let activeCsrfToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function configureAuthenticatedTransport(options: {
  csrfToken: string | null;
  onUnauthorized: (() => void) | null;
}): void {
  activeCsrfToken = options.csrfToken;
  unauthorizedHandler = options.onUnauthorized;
}

async function fetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
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
  if (response.status === 401) unauthorizedHandler?.();
  return response;
}

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
  const response = await fetch(
    `${API_BASE_URL}${demo ? "/api/demo" : "/api"}/clm/zero-touch/cases/${caseId}/intake/documents`,
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

export async function fetchZeroTouchCases(
  status?: ZeroTouchCaseListItem["status"],
  priority: PriorityFilter = "all",
  prioritySort: PrioritySort = "highest_first",
  teamFilter?: string,
): Promise<ZeroTouchCaseListItem[]> {
  const query = new URLSearchParams();
  if (status) query.set("status", status);
  if (priority !== "all") query.set("priority_filter", priority);
  if (prioritySort !== "highest_first") query.set("priority_sort", prioritySort);
  if (teamFilter && teamFilter !== "all") query.set("team_filter", teamFilter);
  const suffix = query.size ? `?${query.toString()}` : "";
  const response = await fetch(`${API_BASE_URL}/api/clm/zero-touch/cases${suffix}`);
  return parseResponse<ZeroTouchCaseListItem[]>(response);
}

export async function fetchDashboard(teamFilter?: string): Promise<DashboardSnapshot> {
  const query = teamFilter && teamFilter !== "all"
    ? `?team_filter=${encodeURIComponent(teamFilter)}`
    : "";
  const response = await fetch(`${API_BASE_URL}/api/clm/zero-touch/dashboard${query}`);
  return parseResponse<DashboardSnapshot>(response);
}

export async function replaceZeroTouchDocument(
  caseId: string,
  documentId: string,
  eventCount: number,
  file: File,
): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/documents/${documentId}/replacement`,
    {
      method: "POST",
      headers: {
        "Content-Type": file.type || "application/pdf",
        "X-Document-Name": file.name,
        "X-Document-Event-Count": String(eventCount),
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

export async function fetchExecutionProfile(): Promise<SimulationProfile> {
  const response = await fetch(`${API_BASE_URL}/api/system/execution-profile`);
  return parseResponse<SimulationProfile>(response);
}

export async function resumeZeroTouchCase(caseId: string): Promise<ZeroTouchCaseSummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/resume`,
    { method: "POST" },
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

export async function fetchDocuments(caseId: string): Promise<DocumentProcessingRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/onboarding/cases/${caseId}/documents`);
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
): Promise<OwnershipAnalysisRecord | null> {
  const response = await fetch(`${API_BASE_URL}/api/onboarding/cases/${caseId}/ownership`);
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

export async function fetchPolicies(): Promise<PolicyCatalogue> {
  return parseResponse<PolicyCatalogue>(await fetch(`${API_BASE_URL}/api/policies`));
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
