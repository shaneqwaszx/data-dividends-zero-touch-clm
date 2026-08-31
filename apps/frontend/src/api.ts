import {
  advanceMockCase,
  assignMockReviewer,
  createMockPendingCase,
  getMockSessionCase,
  mockAuditEntries,
  mockCases,
  mockClients,
  mockPolicy,
  mockReviewers,
  resolveMockException,
  resubmitMockCase,
  returnMockForRework,
} from "./mockData";
import type {
  AuditEntry,
  CaseListItem,
  ClientRecord,
  ClmCaseSummary,
  DocumentProcessingRecord,
  DocumentFieldKey,
  MockIdpScenario,
  MockOwnershipScenario,
  MockScenarioDiscovery,
  OnboardingCase,
  OwnershipAnalysisRecord,
  PolicyResponse,
  ReviewDecision,
  ExceptionResolutionAction,
  Reviewer,
  ZeroTouchCaseSummary,
  ZeroTouchDemoScenario,
  SimulationProfile,
  UatEvidenceExport,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let code: string | null = null;
    let message = `Application API request failed (${response.status}).`;
    try {
      const payload = (await response.json()) as {
        detail?: { code?: string; message?: string } | string;
      };
      if (typeof payload.detail === "object" && payload.detail) {
        code = payload.detail.code ?? null;
        message = payload.detail.message ?? message;
      }
    } catch {
      // Preserve the fixed local fallback; never project response bodies.
    }
    throw new ApiError(message, response.status, code);
  }
  return (await response.json()) as T;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string | null,
  ) {
    super(message);
  }
}

export async function createZeroTouchCase(
  uen: string,
  demoScenario?: ZeroTouchDemoScenario,
  countryOfIncorporation?: "SG" | "AU" | "MY" | "HK",
): Promise<ZeroTouchCaseSummary> {
  const demo = demoScenario !== undefined;
  try {
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
        }),
        signal: AbortSignal.timeout(800),
      },
    );
    return await parseResponse<ZeroTouchCaseSummary>(response);
  } catch {
    // TEMPORARY: visualization fallback when no backend is reachable at all
    // (the dev proxy itself returns a 500 ApiError, not a network exception,
    // when nothing is listening on the target port -- so this can't safely
    // distinguish "no backend" from "backend returned a real error" the way
    // the read-only mock fallbacks below try to).
    return createMockPendingCase(uen, countryOfIncorporation ?? "");
  }
}

export async function attachZeroTouchDocument(
  caseId: string,
  file: File,
  demo: boolean,
): Promise<ZeroTouchCaseSummary> {
  try {
    const response = await fetch(
      `${API_BASE_URL}${demo ? "/api/demo" : "/api"}/clm/zero-touch/cases/${caseId}/documents`,
      {
        method: "POST",
        headers: {
          "Content-Type": file.type || "application/pdf",
          "X-Document-Name": file.name,
        },
        body: file,
        signal: AbortSignal.timeout(800),
      },
    );
    return await parseResponse<ZeroTouchCaseSummary>(response);
  } catch (error) {
    // TEMPORARY: visualization fallback -- advances the mock case created above.
    // See the comment in createZeroTouchCase on why this can't reliably tell
    // "no backend" apart from a real ApiError through the dev proxy.
    const advanced = advanceMockCase(caseId);
    if (advanced) return advanced;
    throw error;
  }
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
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}`,
      { signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(800)]) : AbortSignal.timeout(800) },
    );
    return await parseResponse<ZeroTouchCaseSummary>(response);
  } catch (error) {
    // TEMPORARY: visualization fallback for mock/session cases in mockData.ts,
    // only when the backend is genuinely unreachable -- any other case id
    // still surfaces the real error.
    const mock = getMockSessionCase(caseId);
    if (mock) return mock;
    throw error;
  }
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
  try {
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
        signal: AbortSignal.timeout(800),
      },
    );
    return await parseResponse<ZeroTouchCaseSummary>(response);
  } catch (error) {
    // TEMPORARY: visualization fallback -- see the comment in createZeroTouchCase.
    const resolved = resolveMockException(summary.case.case_id);
    if (resolved) return resolved;
    throw error;
  }
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

export interface CaseListFilters {
  status?: string;
  jurisdiction?: string;
  assignedTo?: string;
}

function buildQuery(params: Record<string, string | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) query.set(key, value);
  }
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}

export async function fetchCases(filters: CaseListFilters = {}): Promise<CaseListItem[]> {
  const query = buildQuery({
    status: filters.status,
    jurisdiction: filters.jurisdiction,
    assigned_to: filters.assignedTo,
  });
  try {
    const response = await fetch(`${API_BASE_URL}/api/cases${query}`, { signal: AbortSignal.timeout(800) });
    return await parseResponse<CaseListItem[]>(response);
  } catch {
    // TEMPORARY: visualization fallback until this endpoint is built. See mockData.ts.
    return mockCases.filter(
      (item) =>
        (!filters.status || item.status === filters.status) &&
        (!filters.jurisdiction || item.jurisdiction === filters.jurisdiction),
    );
  }
}

export async function fetchClients(filters: CaseListFilters = {}): Promise<ClientRecord[]> {
  const query = buildQuery({ jurisdiction: filters.jurisdiction });
  try {
    const response = await fetch(`${API_BASE_URL}/api/clients${query}`, { signal: AbortSignal.timeout(800) });
    return await parseResponse<ClientRecord[]>(response);
  } catch {
    // TEMPORARY: visualization fallback until this endpoint is built. See mockData.ts.
    return mockClients.filter(
      (client) => !filters.jurisdiction || client.jurisdiction === filters.jurisdiction,
    );
  }
}

export async function fetchClient(clientId: string): Promise<ClientRecord> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}`, { signal: AbortSignal.timeout(800) });
    return await parseResponse<ClientRecord>(response);
  } catch (error) {
    // TEMPORARY: visualization fallback until this endpoint is built. See mockData.ts.
    const match = mockClients.find((client) => client.client_id === clientId);
    if (match) return match;
    throw error;
  }
}

export interface AuditLogFilters {
  caseId?: string;
  action?: string;
}

export async function fetchAuditLog(filters: AuditLogFilters = {}): Promise<AuditEntry[]> {
  const query = buildQuery({ case_id: filters.caseId, action: filters.action });
  try {
    const response = await fetch(`${API_BASE_URL}/api/audit${query}`, { signal: AbortSignal.timeout(800) });
    return await parseResponse<AuditEntry[]>(response);
  } catch {
    // TEMPORARY: visualization fallback until this endpoint is built. See mockData.ts.
    return mockAuditEntries.filter(
      (entry) =>
        (!filters.caseId || entry.case_id === filters.caseId) &&
        (!filters.action || entry.action === filters.action),
    );
  }
}

export function auditExportUrl(filters: AuditLogFilters = {}): string {
  const query = buildQuery({ case_id: filters.caseId, action: filters.action });
  return `${API_BASE_URL}/api/audit/export.csv${query}`;
}

export async function fetchReviewers(): Promise<Reviewer[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/reviewers`, { signal: AbortSignal.timeout(800) });
    return await parseResponse<Reviewer[]>(response);
  } catch {
    // TEMPORARY: visualization fallback until this endpoint is built. See mockData.ts.
    return mockReviewers;
  }
}

export async function fetchPolicy(): Promise<PolicyResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/policy`, { signal: AbortSignal.timeout(800) });
    return await parseResponse<PolicyResponse>(response);
  } catch {
    // TEMPORARY: visualization fallback until this endpoint is built. See mockData.ts.
    return mockPolicy;
  }
}

export async function assignReviewer(
  summary: ZeroTouchCaseSummary,
  exceptionId: string,
  reviewerId: string,
  note?: string,
): Promise<ZeroTouchCaseSummary> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/clm/zero-touch/cases/${summary.case.case_id}/exceptions/${exceptionId}/assign`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reviewer_id: reviewerId,
          expected_automation_version: summary.version,
          ...(note ? { note } : {}),
        }),
        signal: AbortSignal.timeout(800),
      },
    );
    return await parseResponse<ZeroTouchCaseSummary>(response);
  } catch (error) {
    // TEMPORARY: visualization fallback -- see the comment in createZeroTouchCase.
    const assigned = assignMockReviewer(summary.case.case_id, exceptionId, reviewerId);
    if (assigned) return assigned;
    throw error;
  }
}

export async function returnForRework(
  summary: ZeroTouchCaseSummary,
  exceptionId: string,
  reason: string,
  comment: string,
  flaggedFields: string[],
): Promise<ZeroTouchCaseSummary> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/clm/zero-touch/cases/${summary.case.case_id}/exceptions/${exceptionId}/return-for-rework`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reason,
          comment,
          flagged_fields: flaggedFields,
          expected_automation_version: summary.version,
        }),
        signal: AbortSignal.timeout(800),
      },
    );
    return await parseResponse<ZeroTouchCaseSummary>(response);
  } catch (error) {
    // TEMPORARY: visualization fallback -- see the comment in createZeroTouchCase.
    const returned = returnMockForRework(summary.case.case_id, exceptionId, reason, comment, flaggedFields);
    if (returned) return returned;
    throw error;
  }
}

export async function resubmitCase(summary: ZeroTouchCaseSummary): Promise<ZeroTouchCaseSummary> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/clm/zero-touch/cases/${summary.case.case_id}/resubmit`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_automation_version: summary.version }),
        signal: AbortSignal.timeout(800),
      },
    );
    return await parseResponse<ZeroTouchCaseSummary>(response);
  } catch (error) {
    // TEMPORARY: visualization fallback -- see the comment in createZeroTouchCase.
    const resubmitted = resubmitMockCase(summary.case.case_id);
    if (resubmitted) return resubmitted;
    throw error;
  }
}
